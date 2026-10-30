import sys

import pytest

import lq_update
from scripts import migrate_lq_technical_event_tables as migration


def test_raw_data_widening_is_verified_and_idempotent(monkeypatch):
    state = {"Type": "varchar(255)"}
    writes = []
    monkeypatch.setattr(migration.sql_util, "select_dicts", lambda _sql: [dict(state)])

    def execute(sql):
        writes.append(sql)
        state["Type"] = "text"

    monkeypatch.setattr(migration.sql_util, "sqlExecute", execute)
    migration.widen_team_period_raw_data()
    migration.widen_team_period_raw_data()
    assert writes == ["ALTER TABLE `lq_teamtechnic_period` MODIFY COLUMN `rawData` TEXT NULL"]


@pytest.mark.parametrize("column_type", ["text", "mediumtext", "longtext"])
def test_existing_text_capacity_is_not_narrowed(monkeypatch, column_type):
    monkeypatch.setattr(migration.sql_util, "select_dicts", lambda _sql: [{"Type": column_type}])
    monkeypatch.setattr(migration.sql_util, "sqlExecute", lambda _sql: pytest.fail("unexpected schema write"))
    migration.widen_team_period_raw_data()


def test_unsuccessful_widening_fails_closed(monkeypatch):
    monkeypatch.setattr(migration.sql_util, "select_dicts", lambda _sql: [{"Type": "varchar(255)"}])
    monkeypatch.setattr(migration.sql_util, "sqlExecute", lambda _sql: None)
    with pytest.raises(RuntimeError, match="did not persist"):
        migration.widen_team_period_raw_data()


@pytest.mark.parametrize("request_ok", [True, False])
def test_technical_cli_propagates_persistence_status(monkeypatch, request_ok):
    monkeypatch.setattr(sys, "argv", ["lq_update.py", "technical", "--schedule-id", "663582"])
    monkeypatch.setattr(lq_update, "update_match_technical", lambda *_a, **_k: {"request_ok": request_ok})
    if request_ok:
        lq_update.main()
    else:
        with pytest.raises(SystemExit) as error:
            lq_update.main()
        assert error.value.code == 1


@pytest.mark.parametrize('match_state', [-1, '-1', -4, 0, 4])
@pytest.mark.parametrize('request_ok', [True, False])
@pytest.mark.parametrize('has_data', [True, False])
def test_technical_completion_requires_success_and_finished_match(monkeypatch, match_state, request_ok, has_data):
    from lq.service.technical import Technical
    from utils import sql_util

    writes = []
    monkeypatch.setattr(lq_update, '_match_enrichment_state', lambda sid: {
        'matchState': match_state, 'technical_f': lq_update.ENRICHMENT_FLAG_PENDING,
    })
    monkeypatch.setattr(Technical, 'upMatchTechnical', lambda sid: {
        'request_ok': request_ok, 'players': 22 if has_data else 0,
        'periods': 2 if has_data else 0, 'teams': 2 if has_data else 0,
    })
    monkeypatch.setattr(sql_util, 'upData', lambda table, row, condition: writes.append(row))
    result = lq_update.update_match_technical(663734)
    assert result['request_ok'] is request_ok
    if not request_ok:
        assert writes == []
    else:
        expected = lq_update.ENRICHMENT_FLAG_DONE if str(match_state) == '-1' else lq_update.ENRICHMENT_FLAG_REFRESHABLE
        assert writes[0]['technical_f'] == expected
        assert writes[0]['teamTech'] == int(expected == lq_update.ENRICHMENT_FLAG_DONE and has_data)


@pytest.mark.parametrize('source_state', [-1, 2])
def test_enrichment_refreshes_score_before_both_modules(monkeypatch, source_state):
    calls = []
    monkeypatch.setattr(lq_update, '_match_enrichment_state', lambda sid: {'matchState': 0})
    def score(ids):
        calls.append(('score', ids))
        return {123: {'request_ok': True, 'match_state': source_state}}
    monkeypatch.setattr(lq_update, 'up_score_batch', score)
    def collect(sid, **kwargs):
        assert calls[0] == ('score', [123])
        assert kwargs['match_state'] == source_state
        assert kwargs['completion_allowed'] is True
        calls.append(('collect', sid))
        return {'request_ok': True}
    monkeypatch.setattr(lq_update, 'update_match_technical', collect)
    monkeypatch.setattr(lq_update, 'update_match_text_live', collect)
    result = lq_update.update_match_enrichment(123)
    assert result['score']['request_ok'] is True
    assert len(calls) == 3


def test_score_failure_does_not_close_or_block_other_modules(monkeypatch):
    monkeypatch.setattr(lq_update, '_match_enrichment_state', lambda sid: {'matchState': -1})
    monkeypatch.setattr(lq_update, 'up_score_batch', lambda ids: {123: {'request_ok': False}})
    def technical(sid, **kwargs):
        assert kwargs['completion_allowed'] is False
        raise RuntimeError('technical failed')
    def text(sid, **kwargs):
        assert kwargs['completion_allowed'] is False
        assert kwargs['match_state'] is None
        return {'request_ok': True}
    monkeypatch.setattr(lq_update, 'update_match_technical', technical)
    monkeypatch.setattr(lq_update, 'update_match_text_live', text)
    result = lq_update.update_match_enrichment(123)
    assert result['technical']['request_ok'] is False
    assert result['text_live']['request_ok'] is True


@pytest.mark.parametrize('module', ['technical', 'text_live'])
def test_unverified_score_does_not_use_old_finished_state(monkeypatch, module):
    from lq.service.technical import Technical
    from utils import sql_util
    writes = []
    monkeypatch.setattr(lq_update, '_match_enrichment_state', lambda sid: {
        'matchState': -1, 'technical_f': 0, 'textlive_f': 0})
    monkeypatch.setattr(Technical, 'upMatchTechnical', lambda sid: {'request_ok': True})
    monkeypatch.setattr(Technical, 'upMatchTextLive', lambda sid: {'request_ok': True})
    monkeypatch.setattr(sql_util, 'upData', lambda table, row, condition: writes.append(row))
    getattr(lq_update, 'update_match_' + module)(123, completion_allowed=False)
    assert writes[0]['technical_f' if module == 'technical' else 'textlive_f'] == 1


@pytest.mark.parametrize('request_ok', [True, False])
@pytest.mark.parametrize('state', [-1, 0, 2, -4])
@pytest.mark.parametrize('has_data', [True, False])
def test_collection_flag_requires_success_and_finished_state(request_ok, state, has_data):
    flag = lq_update._flag_after_collect({'request_ok': request_ok}, state, has_data)
    assert flag == (None if not request_ok else 2 if state == -1 else 1)


@pytest.mark.parametrize('persisted', [True, False])
def test_single_score_refresh_checks_persistence(monkeypatch, persisted):
    from lq.parshtml import part_score
    from utils import sql_util
    source = {'matchState': -1, 'homeScore': '110', 'awayScore': '108'}
    monkeypatch.setattr(part_score, 'get_PartScore', lambda sid: source)
    monkeypatch.setattr(sql_util, 'upData', lambda *a: None)
    monkeypatch.setattr(sql_util, 'select_dicts', lambda sql: [source if persisted else {**source, 'matchState': 0}])
    result = lq_update.up_score_batch([123])[123]
    assert result['request_ok'] is persisted
    assert result['match_state'] == (-1 if persisted else None)


def test_score_network_failure_preserves_retry(monkeypatch):
    from lq.parshtml import part_score
    def fail(sid):
        raise ConnectionError('source unavailable')
    monkeypatch.setattr(part_score, 'get_PartScore', fail)
    assert lq_update.up_score_batch([123])[123]['request_ok'] is False


def test_single_match_tool_checks_identity_before_collection(monkeypatch):
    from utils import sql_util
    monkeypatch.setattr(sql_util, 'select_dicts', lambda sql: [{'matchID': 42}])
    monkeypatch.setattr(lq_update, 'update_match_enrichment', lambda *a, **k: pytest.fail('identity mismatch'))
    with pytest.raises(ValueError, match='binding_mismatch'):
        lq_update.update_match_facts(123, expected_match_id=43)


@pytest.mark.parametrize('success', [True, False])
def test_single_match_tool_preserves_independent_module_results(monkeypatch, success):
    from utils import sql_util
    monkeypatch.setattr(sql_util, 'select_dicts', lambda sql: [{'matchID': 42}])
    packet = {'score': {'request_ok': True}, 'technical': {'request_ok': True},
              'text_live': {'request_ok': success}}
    def update(sid, force):
        assert sid == 123 and force is False
        return packet
    monkeypatch.setattr(lq_update, 'update_match_enrichment', update)
    result = lq_update.update_match_facts(123, expected_match_id=42)
    assert result['request_ok'] is success
    assert result['technical']['request_ok'] is True


@pytest.mark.parametrize('success', [True, False])
def test_single_match_json_cli_reports_partial_failure(monkeypatch, capsys, success):
    from scripts import update_basketball_match_facts as cli
    def update(sid, expected_match_id, force):
        assert (sid, expected_match_id, force) == (123, 42, False)
        print('private collection diagnostic')
        return {'request_ok': success, 'technical': {'request_ok': True}}
    monkeypatch.setattr(lq_update, 'update_match_facts', update)
    monkeypatch.setattr(sys, 'argv', ['tool', '--schedule-id', '123', '--expected-match-id', '42'])
    assert cli.main() == (0 if success else 1)
    captured = capsys.readouterr()
    import json
    assert json.loads(captured.out)['request_ok'] is success
    assert 'private collection diagnostic' in captured.err
