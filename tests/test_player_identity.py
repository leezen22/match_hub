import sys
import types
from concurrent.futures import ThreadPoolExecutor
import os
import uuid

import pytest

if 'js2py' not in sys.modules:
    stub = types.ModuleType('js2py')
    stub.EvalJs = object
    sys.modules['js2py'] = stub

from lq.service import player_identity as identity
from lq.service.technical import Technical
from lq.service.roster import _upsert_player_profile
from scripts.repair_lq_player_identities import verify_evidence


@pytest.mark.parametrize('value', [None, 0, -1, '', '1.0', 1.5, True, '0001', '1 OR 1', 2147483648])
def test_invalid_source_ids_are_not_guessed(value):
    with pytest.raises(identity.PlayerIdentityError):
        identity.source_player_id(value)


def test_raw_package_evidence_requires_source_identity_and_player_section():
    fragment = '^'.join(['42', 'Name'] + ['0'] * 22)
    row = {'playerID': 42, 'scheduleID': 1, 'rawData': fragment, 'rawCaptureID': 'cap'}
    assert verify_evidence([row], {1: ('cap', 'match$' + fragment + '!totals!end$away')}) == (row, None)
    assert verify_evidence([row], {1: ('other', 'match$' + fragment + '!totals!end$away')})[0] is None
    assert verify_evidence([dict(row, playerID=43)], {})[1] == 'technical_raw_identity_mismatch'
    assert verify_evidence([dict(row, isUnknown=1)], {})[1] == 'source_player_marked_unknown'
    assert verify_evidence([dict(row, isUnknown=1), row],
                           {1: ('cap', 'match$' + fragment + '!totals!end$away')}) == (row, None)
    assert verify_evidence([row], {1: ('cap', fragment)})[0] is None


def technical_stubs(monkeypatch):
    writes = []
    monkeypatch.setattr('lq.service.technical.sql_util.select', lambda sql: [(1, 1, 10, 20, '2026', None)])
    monkeypatch.setattr(Technical, 'technical_match', lambda *a, **k: {
        'requestOk': True, 'rawTech': 'original facts', 'matchID': 1, 'sourceUrl': 'source',
        'sourceOperation': 'technical', 'captureID': 'cap', 'capturedAt': None,
        'players': [{'playerID': 42, 'scheduleID': 1, 'score': 25, 'teamID': 10}],
        'teams': [], 'teamPeriodRows': []})
    monkeypatch.setattr('lq.service.technical.sql_util.replace_table_row',
                        lambda table, condition, row: writes.append((table, row)) or True)
    monkeypatch.setattr('lq.service.technical.sql_util.replace_table_rows',
                        lambda table, condition, rows: writes.append((table, rows)) or True)
    return writes


def test_identity_db_failure_retains_raw_and_previous_technical_facts(monkeypatch):
    writes = technical_stubs(monkeypatch)
    def fail(*a):
        raise RuntimeError('identity DB unavailable')
    monkeypatch.setattr('lq.service.technical.register_technical_identities', fail)
    result = Technical.upMatchTechnical(1)
    assert result['request_ok'] is False
    assert [table for table, _ in writes] == ['lq_matchtechnic_raw']
    assert writes[0][1]['rawTech'] == 'original facts'
    assert result['identity_diagnostics'][0]['retry_required'] is True


def test_identity_diagnostics_preserve_unresolved_original_facts(monkeypatch):
    writes = technical_stubs(monkeypatch)
    monkeypatch.setattr('lq.service.technical.register_technical_identities',
                        lambda *a: [{'playerID': 42, 'reason': 'source_identity_conflict'}])
    result = Technical.upMatchTechnical(1)
    assert result['identity_diagnostics'][0]['reason'] == 'source_identity_conflict'
    assert writes[-1][1] == [{'playerID': 42, 'scheduleID': 1, 'score': 25, 'teamID': 10}]


def test_registration_completes_before_technical_persistence(monkeypatch):
    writes = technical_stubs(monkeypatch)
    def register(*args):
        assert [table for table, _ in writes] == ['lq_matchtechnic_raw']
        writes.append(('identity_committed', None))
        return []
    monkeypatch.setattr('lq.service.technical.register_technical_identities', register)
    assert Technical.upMatchTechnical(1)['request_ok'] is True
    assert [table for table, _ in writes] == ['lq_matchtechnic_raw', 'identity_committed', 'lq_playertechnic']


def test_transaction_retries_deadlock_and_surfaces_permanent_failure(monkeypatch):
    events = []
    class Connection:
        def cursor(self): return self
        def commit(self): events.append('commit')
        def rollback(self): events.append('rollback')
        def close(self): events.append('close')
    monkeypatch.setattr(identity.sql_util, '_connect', Connection)
    def work(cursor):
        if not events:
            raise identity.OperationalError(1213, 'deadlock')
        return 42
    assert identity.identity_transaction(work) == 42
    assert events == ['rollback', 'close', 'commit', 'close']
    def fail(cursor):
        raise RuntimeError('permanent failure')
    with pytest.raises(RuntimeError, match='permanent failure'):
        identity.identity_transaction(fail)


@pytest.fixture
def identity_db(monkeypatch):
    """Opt-in MySQL integration, isolated clone; never alter production profiles."""
    if os.environ.get('MATCH_HUB_IDENTITY_DB_TEST') != '1':
        pytest.skip('set MATCH_HUB_IDENTITY_DB_TEST=1 for isolated MySQL checks')
    original_connect = identity.sql_util._connect
    table = 'test_player_identity_' + uuid.uuid4().hex[:16]
    connection = original_connect()
    with connection.cursor() as cursor:
        cursor.execute('CREATE TABLE ' + table + ' LIKE lq_player_profile')
    connection.close()

    class Cursor:
        def __init__(self, cursor): self.cursor = cursor
        def execute(self, query, args=None):
            return self.cursor.execute(query.replace('lq_player_profile', table), args)
        def __getattr__(self, name): return getattr(self.cursor, name)

    class Connection:
        def __init__(self): self.connection = original_connect()
        def cursor(self): return Cursor(self.connection.cursor())
        def __getattr__(self, name): return getattr(self.connection, name)

    monkeypatch.setattr(identity.sql_util, '_connect', Connection)
    try:
        yield Connection
    finally:
        connection = original_connect()
        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE ' + table)
        connection.close()


def test_mysql_concurrent_registration_and_profile_enrichment_preserve_id(identity_db):
    def register(index):
        rows = [{'playerID': 5294, 'playerNameEn': 'Chris Boucher',
                 'scheduleID': index, 'teamID': index, 'position': 'historical', 'shirtNumber': '99'}]
        assert identity.register_technical_identities(rows) == []
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(register, range(16)))
    connection = identity_db()
    cursor = connection.cursor()
    cursor.execute('SELECT id,playerID,position,shirtNumber,activeStatus,birthDate FROM lq_player_profile')
    rows = cursor.fetchall()
    assert len(rows) == 1
    public_id = rows[0][0]
    assert rows[0][1:] == (5294, None, None, None, None)
    connection.close()
    _upsert_player_profile({'source_namespace': identity.SOURCE_NAMESPACE, 'source_entity_id': '5294',
                            'playerID': 5294, 'playerNameEn': 'Chris Boucher', 'height': '206',
                            'collection_status': 'success', 'has_data': 1})
    register(100)
    connection = identity_db()
    cursor = connection.cursor()
    cursor.execute('SELECT id,height,collection_status FROM lq_player_profile')
    assert cursor.fetchall() == ((public_id, '206', 'success'),)
    connection.close()


def test_mysql_conflicts_and_invalid_ids_are_diagnosed(identity_db):
    connection = identity_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO lq_player_profile (playerID,source_namespace,source_entity_id) VALUES (99,%s,'42')",
                   (identity.SOURCE_NAMESPACE,))
    connection.commit()
    connection.close()
    errors = identity.register_technical_identities([{'playerID': 42}, {'playerID': None}])
    assert len(errors) == 2
    assert any('source_identity_conflict' in error['reason'] for error in errors)
    assert any('invalid_source_player_id' in error['reason'] for error in errors)


def test_mysql_same_name_never_merges_distinct_source_ids(identity_db):
    identity.register_technical_identities([{'playerID': 101, 'playerName': 'Same Name'},
                                            {'playerID': 102, 'playerName': 'Same Name'}])
    connection = identity_db()
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*),COUNT(DISTINCT id) FROM lq_player_profile')
    assert cursor.fetchone() == (2, 2)
    connection.close()
