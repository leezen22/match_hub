from lq.service import league


def test_backfill_marks_only_leagues_with_persisted_txtlive(monkeypatch):
    writes = []

    monkeypatch.setattr(league, "_ensure_lq_league_metadata_schema", lambda: None)
    monkeypatch.setattr(
        league.sql_util,
        "select_dicts",
        lambda sql: (
            [{"match_id": 11}, {"match_id": 12}, {"match_id": 13}]
            if "DISTINCT matchID" in sql
            else []
            if "txtlive_source_capability IN" in sql
            else (
                [{"match_id": 11, "league_id": 81}, {"match_id": 12, "league_id": 81}]
                if "11,12" in sql
                else [{"match_id": 13, "league_id": 99}]
            )
        ),
    )
    monkeypatch.setattr(league.sql_util, "select", lambda _sql: [(81,), (99,)])
    monkeypatch.setattr(league.sql_util, "upData", lambda table, payload, where: writes.append((table, payload, where)))

    result = league.backfill_league_txtlive_capability(batch_size=2)

    assert result["status"] == "completed"
    assert result["league_count"] == 2
    assert [item["league_id"] for item in result["updated"]] == [81, 99]
    assert all(row[1]["txtlive_source_capability"] == "available" for row in writes)
    assert [row[1]["txtlive_capability_event_match_count"] for row in writes] == [2, 1]


def test_update_rejects_legacy_capability_values():
    for status in ("partial", "none", "source_unavailable"):
        try:
            league.update_league_txtlive_capability(1, status)
        except ValueError as exc:
            assert str(exc) == "invalid_txtlive_source_capability"
        else:
            raise AssertionError("legacy status should be rejected")
