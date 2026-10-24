"""Replay a stored source package through the real pending-enrichment entrypoint."""
import os
import sys
import types
import uuid

import pytest

if 'js2py' not in sys.modules:
    stub = types.ModuleType('js2py')
    stub.EvalJs = object
    sys.modules['js2py'] = stub

import lq_update
from lq.service.technical import Technical
from lq.service.player_identity import register_technical_identities
from utils import sql_util


@pytest.fixture
def enrichment_db(monkeypatch):
    if os.environ.get('MATCH_HUB_IDENTITY_DB_TEST') != '1':
        pytest.skip('set MATCH_HUB_IDENTITY_DB_TEST=1 for isolated MySQL replay')
    connect = sql_util._connect
    originals = ['lq_player_profile', 'lq_schedule', 'lq_matchtechnic_raw', 'lq_playertechnic',
                 'lq_teamtechnic_period', 'lq_textlive_raw', 'lq_textlive']
    prefix = 'test_enrich_' + uuid.uuid4().hex[:10] + '_'
    tables = {name: prefix + str(index) for index, name in enumerate(originals)}
    connection = connect()
    created = []
    opened = []
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT scheduleID,sourceUrl,rawTech FROM lq_matchtechnic_raw WHERE matchID=341139')
        source = cursor.fetchone()
        assert source and source[2], 'original case package required for replay'
        schedule_id, source_url, raw = source
        for original, isolated in tables.items():
            cursor.execute('CREATE TABLE ' + isolated + ' LIKE ' + original)
            created.append(isolated)
        cursor.execute('INSERT INTO ' + tables['lq_schedule'] + ' SELECT * FROM lq_schedule WHERE scheduleID=%s',
                       (schedule_id,))
        cursor.execute('UPDATE ' + tables['lq_schedule'] + ' SET technical_f=0,textlive_f=2,matchState=-1')
        connection.commit()

        class Cursor:
            def __init__(self, cursor): self.cursor = cursor
            def execute(self, query, args=None):
                for original in sorted(tables, key=len, reverse=True):
                    query = query.replace(original, tables[original])
                return self.cursor.execute(query, args)
            def __getattr__(self, name): return getattr(self.cursor, name)

        class Connection:
            def __init__(self, **kwargs):
                self.connection = connect(**kwargs)
                opened.append(self.connection)
            def cursor(self, *args): return Cursor(self.connection.cursor(*args))
            def __getattr__(self, name): return getattr(self.connection, name)

        monkeypatch.setattr(sql_util, '_connect', Connection)
        monkeypatch.setattr(Technical, '_fetch_technical_js', lambda sid: (source_url, raw, True))
        yield Connection, schedule_id
    finally:
        for test_connection in opened:
            if test_connection.open:
                test_connection.close()
        connection.rollback()
        for isolated in reversed(created):
            connection.cursor().execute('DROP TABLE ' + isolated)
        connection.close()


def run_pending():
    return lq_update.update_enrichment_pending(all_leagues=True, start_match_time='1900-01-01',
                                             until_match_time='2100-01-01', limit=1)


def test_pending_entrypoint_registers_missing_players_and_preserves_ids(enrichment_db):
    connect, sid = enrichment_db
    assert run_pending() == [sid]
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT playerID,id,position,shirtNumber,activeStatus,collection_status FROM lq_player_profile')
    profiles = cursor.fetchall()
    assert len(profiles) == 22
    assert all(row[2:] == (None, None, None, 'identity_only') for row in profiles)
    initial_ids = {row[0]: row[1] for row in profiles}
    cursor.execute('SELECT COUNT(*),COUNT(p.id) FROM lq_playertechnic t '
                   'LEFT JOIN lq_player_profile p ON p.playerID=t.playerID')
    assert cursor.fetchone() == (22, 22)
    cursor.execute('SELECT technical_f FROM lq_schedule WHERE scheduleID=%s', (sid,))
    assert cursor.fetchone()[0] == lq_update.ENRICHMENT_FLAG_DONE
    connection.close()
    assert run_pending() == []
    assert lq_update.update_match_technical(sid, force=True)['request_ok'] is True
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT playerID,id FROM lq_player_profile')
    assert dict(cursor.fetchall()) == initial_ids
    connection.close()


def test_text_only_pending_does_not_recollect_completed_technical(enrichment_db, monkeypatch):
    connect, sid = enrichment_db
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('UPDATE lq_schedule SET technical_f=2,textlive_f=0')
    connection.commit()
    connection.close()
    def unexpected_fetch(*args):
        pytest.fail('completed technical must not be fetched')
    monkeypatch.setattr(Technical, '_fetch_technical_js', unexpected_fetch)
    monkeypatch.setattr(Technical, 'text_live', lambda sid: {
        'requestOk': True, 'events': [], 'rawTextLive': ''})
    assert run_pending() == [sid]
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM lq_player_profile')
    assert cursor.fetchone()[0] == 0
    connection.close()


def test_identity_database_failure_keeps_pending_even_without_team_rows(enrichment_db, monkeypatch):
    connect, sid = enrichment_db
    monkeypatch.setattr(Technical, '_parse_team_technical', lambda *args, **kwargs: {})
    monkeypatch.setattr(Technical, '_parse_period_technical', lambda *args, **kwargs: [])
    def fail(*args):
        raise RuntimeError('identity DB unavailable')
    monkeypatch.setattr('lq.service.technical.register_technical_identities', fail)
    assert run_pending() == [sid]
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT technical_f FROM lq_schedule WHERE scheduleID=%s', (sid,))
    assert cursor.fetchone()[0] == lq_update.ENRICHMENT_FLAG_PENDING
    cursor.execute('SELECT COUNT(*) FROM lq_matchtechnic_raw')
    assert cursor.fetchone()[0] == 1
    cursor.execute('SELECT COUNT(*) FROM lq_playertechnic')
    assert cursor.fetchone()[0] == 0
    connection.close()
    monkeypatch.setattr('lq.service.technical.register_technical_identities', register_technical_identities)
    assert run_pending() == [sid]
    connection = connect()
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM lq_player_profile')
    assert cursor.fetchone()[0] == 22
    cursor.execute('SELECT technical_f FROM lq_schedule WHERE scheduleID=%s', (sid,))
    assert cursor.fetchone()[0] == lq_update.ENRICHMENT_FLAG_DONE
    connection.close()
