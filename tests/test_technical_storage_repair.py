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
