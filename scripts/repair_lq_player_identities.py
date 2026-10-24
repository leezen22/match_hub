"""Audit technical source identities; --execute registers raw-verified gaps only."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lq.service.player_identity import SOURCE_NAMESPACE, ensure_player_identity, source_player_id
from utils import sql_util


def profile_map(cursor):
    cursor.execute('SELECT source_entity_id,id,playerID FROM lq_player_profile WHERE source_namespace=%s',
                   (SOURCE_NAMESPACE,))
    return {str(row[0]): (row[1], row[2]) for row in cursor.fetchall()}


def coverage(cursor, profiles):
    cursor.execute('SELECT playerID,COUNT(*) FROM lq_playertechnic GROUP BY playerID')
    counts = cursor.fetchall()
    missing = {pid: count for pid, count in counts
               if pid and pid > 0 and (str(pid) not in profiles or profiles[str(pid)][1] != pid)}
    return {'source_players': len(counts), 'technical_rows': sum(n for _, n in counts),
            'missing_source_players': len(missing), 'missing_technical_rows': sum(missing.values()),
            'invalid_source_rows': sum(n for pid, n in counts if not pid or pid <= 0)}, missing


def verify_evidence(rows, raw_packages):
    """Names never resolve identities. Require source IDs and an original package."""
    verified = []
    known_rows = 0
    for row in rows:
        pid = source_player_id(row['playerID'])
        if row.get('isUnknown'):
            continue
        known_rows += 1
        fragments = (row.get('rawData') or '').split('||')
        if any(len(part.split('^')) < 24 or part.split('^')[0] != str(pid) for part in fragments):
            return None, 'technical_raw_identity_mismatch'
        package = raw_packages.get(row['scheduleID'])
        if not package:
            continue
        capture_id, content = package
        if row.get('rawCaptureID') and row['rawCaptureID'] != capture_id:
            continue
        sections = (content or '').split('$')
        # Only the home/away player sections qualify, excluding team totals.
        player_items = set()
        for section in sections[1:3]:
            player_items.update(section.split('!')[:-2])
        if all(part in player_items for part in fragments):
            verified.append(row)
    if not verified:
        return None, ('no_matching_original_technical_package' if known_rows else 'source_player_marked_unknown')
    return max(verified, key=lambda row: row['scheduleID']), None


def run(execute=False, batch_size=100):
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'execute': execute,
              'registered': [], 'pending': []}
    connection = sql_util._connect()
    try:
        cursor = connection.cursor()
        before_profiles = profile_map(cursor)
        report['before'], missing = coverage(cursor, before_profiles)
        cursor.execute('CHECKSUM TABLE lq_playertechnic')
        report['technical_checksum_before'] = cursor.fetchone()[1]
        # End the read snapshot so concurrent registrations become visible.
        connection.commit()
        player_ids = sorted(missing)
        for offset in range(0, len(player_ids), batch_size):
            chunk = player_ids[offset:offset + batch_size]
            cursor.execute('SELECT playerID,scheduleID,rawData,rawCaptureID,isUnknown,playerName,playerNameTrad,playerNameEn '
                           'FROM lq_playertechnic WHERE playerID IN ({})'.format(','.join(['%s'] * len(chunk))), chunk)
            fields = [col[0] for col in cursor.description]
            by_player = defaultdict(list)
            for values in cursor.fetchall():
                row = dict(zip(fields, values))
                by_player[row['playerID']].append(row)
            schedules = sorted({row['scheduleID'] for rows in by_player.values() for row in rows})
            packages = {}
            for start in range(0, len(schedules), 100):
                ids = schedules[start:start + 100]
                cursor.execute('SELECT scheduleID,captureID,rawTech FROM lq_matchtechnic_raw '
                               'WHERE scheduleID IN ({})'.format(','.join(['%s'] * len(ids))), ids)
                packages.update({sid: (capture, raw) for sid, capture, raw in cursor.fetchall()})
            for pid in chunk:
                evidence, reason = verify_evidence(by_player[pid], packages)
                if reason:
                    report['pending'].append({'source_player_id': pid, 'technical_rows': missing[pid], 'reason': reason})
                    continue
                item = {'source_player_id': pid, 'technical_rows': missing[pid],
                        'evidence_schedule_id': evidence['scheduleID'],
                        'raw_capture_id': packages[evidence['scheduleID']][0],
                        'raw_sha256': hashlib.sha256(packages[evidence['scheduleID']][1].encode()).hexdigest()}
                try:
                    if execute:
                        item['public_player_id'] = ensure_player_identity(cursor, pid, evidence)
                        connection.commit()
                    report['registered'].append(item)
                except Exception as error:
                    connection.rollback()
                    report['pending'].append(dict(item, reason=str(error)))
            connection.commit()
            print('identity audit: {}/{}'.format(min(offset + batch_size, len(player_ids)), len(player_ids)),
                  file=sys.stderr, flush=True)
        after_profiles = profile_map(cursor)
        report['after'], _ = coverage(cursor, after_profiles)
        report['existing_ids_preserved'] = all(after_profiles.get(key) == value for key, value in before_profiles.items())
        cursor.execute('CHECKSUM TABLE lq_playertechnic')
        report['technical_checksum_after'] = cursor.fetchone()[1]
        report['technical_facts_unchanged'] = (report['technical_checksum_before'] is not None
                                              and report['technical_checksum_before'] == report['technical_checksum_after'])
        report['boucher_public_player_id'] = after_profiles.get('5294', (None,))[0]
        if not report['existing_ids_preserved'] or not report['technical_facts_unchanged']:
            report['verification_error'] = 'identity or technical facts changed during repair; investigate'
        return report
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--report', required=True)
    parser.add_argument('--batch-size', type=int, default=100)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error('--batch-size must be positive')
    report = run(args.execute, args.batch_size)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('registered', 'pending')}, ensure_ascii=False))
    if report.get('verification_error') or (args.execute and report['after']['missing_source_players']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
