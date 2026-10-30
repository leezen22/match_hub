"""Audit full-game FG; --execute repairs only independently verified source totals.

Uses saved captures or --basis players. No network, player writes, period writes,
or changes to missing statistics. A durable journal records each before/after pair.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql
from lq.service.technical import Technical
from utils import sql_util

PLAYER_COLUMNS = ('ID', 'scheduleID', 'teamID', 'playerID', 'shoot_Hit', 'shoot',
                  'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall', 'score')


def plan_player_repairs(source, stored, players):
    """Recover an existing scoring conflict from complete player operands.

    No raw capture is required. This is not permission to replace missing team
    facts, or to assume every team statistic equals the player sum.
    """
    changes = []
    operands = ('shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin')
    for side, team_id in ((1, source['homeTeamID']), (0, source['awayTeamID'])):
        teams = [r for r in stored if r['teamID'] == team_id and r['period'] == 0]
        if len(teams) != 1:
            continue
        row = teams[0]
        if row.get('matchID') != source['matchID'] or any(
                type(row.get(f)) is not int or row[f] < 0 for f in operands):
            continue
        if row['shoot'] == 0:
            continue  # All-zero missing FG is outside the correction scope.
        if row['shoot_Hit'] != row['threeMin_Hit'] or row['shoot'] != row['threeMin']:
            continue
        group = [p for p in players if p['teamID'] == team_id]
        if not group or any(type(p.get('playerID')) is not int or p['playerID'] <= 0 for p in group):
            continue
        if len({p['playerID'] for p in group}) != len(group):
            continue
        if any(type(p.get(f)) is not int or p[f] < 0 for p in group for f in operands):
            continue
        if any(not (p['threeMin_Hit'] <= p['shoot_Hit'] <= p['shoot'] and
                    p['threeMin_Hit'] <= p['threeMin'] <= p['shoot'])
               for p in group):
            continue
        total = {f: sum(p[f] for p in group) for f in operands}
        if any(row[f] != total[f] for f in operands[2:]):
            continue
        if all(row[f] == total[f] for f in operands[:2]):
            continue
        changes.append({'row_id': row['ID'], 'match_id': source['matchID'],
                        'schedule_id': source['scheduleID'], 'team_id': team_id,
                        'raw_capture_id': row.get('rawCaptureID'),
                        'before': [row['shoot_Hit'], row['shoot']],
                        'after': [total['shoot_Hit'], total['shoot']],
                        'player_rows': len(group)})
    return changes, None


def plan_repairs(source, stored):
    parts = (source.get('rawTech') or '').split('$')
    if len(parts) < 5:
        return [], 'source_sections_missing'
    if not source.get('captureID'):
        return [], 'capture_identity_missing'
    match = (source['scheduleID'], source['matchID'], source['homeTeamID'],
             source['awayTeamID'], source['matchSeason'], None)
    periods = Technical._parse_period_technical(match, parts[4])
    changes = []
    for side, section in ((1, parts[1]), (0, parts[2])):
        team = Technical._parse_team_technical(match, parts[0].split('^'), section, side)
        expected_team = source['homeTeamID'] if side else source['awayTeamID']
        rows = [r for r in stored if r['teamID'] == expected_team and r['period'] == 0]
        if len(rows) != 1:
            return [], 'stored_team_identity_not_unique'
        row = rows[0]
        if row.get('matchID') != source['matchID'] or row.get('rawCaptureID') != source['captureID']:
            return [], 'stored_capture_or_match_mismatch'
        if team and all(row.get(f) == team.get(f) for f in ('shoot_Hit', 'shoot')):
            continue
        if not team or not Technical._verified_full_game_shooting(team, row, periods):
            continue
        if any(type(row.get(f)) is not int or row[f] < 0 for f in ('shoot_Hit', 'shoot')):
            continue  # Missing/invalid operands are not repaired as conflicts.
        changes.append({'row_id': row['ID'], 'match_id': source['matchID'],
                        'schedule_id': source['scheduleID'], 'team_id': expected_team,
                        'raw_capture_id': source['captureID'],
                        'before': [row['shoot_Hit'], row['shoot']],
                        'after': [team['shoot_Hit'], team['shoot']]})
    return changes, None


def write_repairs(connection, source, changes, *, player_evidence=None):
    """Lock and recheck evidence/old rows; commit both sides atomically."""
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            if player_evidence is None:
                cursor.execute('SELECT captureID,rawTech FROM lq_matchtechnic_raw WHERE ID=%s FOR UPDATE',
                               (source['ID'],))
                current = cursor.fetchone()
                if not current or any(current[k] != source[k] for k in ('captureID', 'rawTech')):
                    raise RuntimeError('source_changed_since_audit')
            else:
                cursor.execute('SELECT ' + ','.join(PLAYER_COLUMNS) +
                               ' FROM lq_playertechnic WHERE scheduleID=%s ORDER BY ID FOR UPDATE',
                               (source['scheduleID'],))
                if list(cursor.fetchall()) != player_evidence:
                    raise RuntimeError('player_evidence_changed_since_audit')
            cursor.execute('SELECT homeTeamID,awayTeamID,homeScore,awayScore FROM lq_schedule '
                           'WHERE scheduleID=%s AND matchID=%s FOR UPDATE',
                           (source['scheduleID'], source['matchID']))
            current = cursor.fetchone()
            if not current or any(current[k] != source[k] for k in current):
                raise RuntimeError('schedule_changed_since_audit')
            for item in changes:
                cursor.execute('UPDATE lq_teamtechnic_period SET shoot_Hit=%s,shoot=%s '
                               'WHERE ID=%s AND scheduleID=%s AND matchID=%s AND teamID=%s '
                               'AND period=0 AND rawCaptureID <=> %s AND shoot_Hit=%s AND shoot=%s',
                               (*item['after'], item['row_id'], item['schedule_id'], item['match_id'],
                                item['team_id'], item['raw_capture_id'], *item['before']))
                if cursor.rowcount != 1:
                    raise RuntimeError('stored_row_changed_since_audit')
                cursor.execute('SELECT shoot_Hit,shoot FROM lq_teamtechnic_period WHERE ID=%s',
                               (item['row_id'],))
                verified = cursor.fetchone()
                if [verified['shoot_Hit'], verified['shoot']] != item['after']:
                    raise RuntimeError('write_verification_failed')
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def run(report_path, *, execute=False, batch_size=100, basis='raw'):
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'execute': execute,
              'scope': 'verified_full_game_field_goals_only', 'basis': basis, 'scanned_matches': 0,
              'eligible_rows': 0, 'updated_rows': 0, 'changes': [], 'skipped': Counter()}
    connection = sql_util._connect()
    last = 0
    journal_path = report_path.with_suffix('.journal.jsonl')
    try:
        with journal_path.open('x', encoding='utf-8') as journal:
            while True:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    if basis == 'players':
                        cursor.execute('SELECT DISTINCT s.scheduleID AS ID,s.scheduleID,s.matchID,'
                                       's.homeTeamID,s.awayTeamID,s.homeScore,s.awayScore,s.matchSeason '
                                       'FROM lq_schedule s JOIN lq_teamtechnic_period t ON t.scheduleID=s.scheduleID '
                                       'WHERE s.scheduleID>%s AND s.matchState=-1 AND t.period=0 '
                                       'AND (t.shoot_Hit>0 OR t.shoot>0) '
                                       'AND t.shoot_Hit=t.threeMin_Hit AND t.shoot=t.threeMin '
                                       'ORDER BY s.scheduleID LIMIT %s', (last, batch_size))
                    else:
                        cursor.execute('SELECT r.ID,r.scheduleID,r.matchID,r.captureID,r.rawTech,'
                                   's.homeTeamID,s.awayTeamID,s.homeScore,s.awayScore,s.matchSeason '
                                   'FROM lq_matchtechnic_raw r JOIN lq_schedule s '
                                   'ON s.scheduleID=r.scheduleID AND s.matchID=r.matchID '
                                   'WHERE r.ID>%s ORDER BY r.ID LIMIT %s', (last, batch_size))
                    sources = cursor.fetchall()
                connection.commit()
                if not sources:
                    break
                by_schedule = {}
                by_players = {}
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    ids = [source['scheduleID'] for source in sources]
                    cursor.execute('SELECT ID,scheduleID,matchID,teamID,period,score,rawCaptureID,'
                                   'shoot_Hit,shoot,threeMin_Hit,threeMin,punishBall_Hit,punishBall '
                                   'FROM lq_teamtechnic_period WHERE scheduleID IN (' +
                                   ','.join(['%s'] * len(ids)) + ') AND period=0', ids)
                    for row in cursor.fetchall():
                        by_schedule.setdefault(row['scheduleID'], []).append(row)
                    if basis == 'players':
                        cursor.execute('SELECT ' + ','.join(PLAYER_COLUMNS) +
                                       ' FROM lq_playertechnic WHERE scheduleID IN (' +
                                       ','.join(['%s'] * len(ids)) + ') ORDER BY ID', ids)
                        for row in cursor.fetchall():
                            by_players.setdefault(row['scheduleID'], []).append(row)
                connection.commit()
                for source in sources:
                    last = source['ID']
                    report['scanned_matches'] += 1
                    stored = by_schedule.get(source['scheduleID'], [])
                    players = by_players.get(source['scheduleID'], [])
                    changes, reason = (plan_player_repairs(source, stored, players) if basis == 'players'
                                       else plan_repairs(source, stored))
                    if not changes:
                        report['skipped'][reason or 'no_verified_fg_conflict'] += 1
                        continue
                    report['eligible_rows'] += len(changes)
                    evidence = players if basis == 'players' else source['rawTech']
                    encoded = json.dumps(evidence, sort_keys=True) if basis == 'players' else evidence
                    entry = {'match_id': source['matchID'], 'basis': basis, 'evidence_sha256': hashlib.sha256(
                        encoded.encode()).hexdigest(), 'changes': changes}
                    journal.write(json.dumps(dict(entry, state='prepared'), ensure_ascii=False) + '\n')
                    journal.flush()
                    os.fsync(journal.fileno())
                    if execute:
                        write_repairs(connection, source, changes,
                                      player_evidence=players if basis == 'players' else None)
                        report['updated_rows'] += len(changes)
                    journal.write(json.dumps({'match_id': source['matchID'],
                                              'state': 'committed' if execute else 'dry_run'}) + '\n')
                    journal.flush()
                    os.fsync(journal.fileno())
                    report['changes'].append(entry)
                if report['scanned_matches'] % 5000 == 0:
                    print(json.dumps({k: report[k] for k in ('scanned_matches', 'eligible_rows', 'updated_rows')}),
                          file=sys.stderr, flush=True)
    except BaseException as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        connection.close()
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--basis', choices=('raw', 'players'), default='raw')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=100)
    args = parser.parse_args()
    if args.batch_size < 1 or args.report.exists() or args.report.with_suffix('.journal.jsonl').exists():
        parser.error('positive batch size and new report/journal paths required')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = run(args.report, execute=args.execute, batch_size=args.batch_size, basis=args.basis)
    print(json.dumps({k: v for k, v in report.items() if k != 'changes'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
