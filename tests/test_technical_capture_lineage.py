import sys
import types


if "js2py" not in sys.modules:
    js2py_stub = types.ModuleType("js2py")
    js2py_stub.EvalJs = object
    sys.modules["js2py"] = js2py_stub

from lq.service.technical import Technical, _new_capture_metadata


def test_technical_match_propagates_one_capture_to_all_structured_rows(monkeypatch):
    monkeypatch.setattr(
        Technical,
        "_fetch_technical_js",
        staticmethod(lambda schedule_id: ("https://example.test/technical.js", "match$home$away$extra$period", True)),
    )
    monkeypatch.setattr(
        Technical,
        "_parse_team_technical",
        staticmethod(lambda match, data, team, is_home: {"teamID": match[2] if is_home else match[3], "isHome": is_home}),
    )
    monkeypatch.setattr(
        Technical,
        "_parse_player_technical",
        staticmethod(lambda match, team, is_home: [{"playerID": 100 + is_home}]),
    )
    monkeypatch.setattr(
        Technical,
        "_parse_period_technical",
        staticmethod(lambda match, period: [{"teamID": match[2], "period": 1}]),
    )
    monkeypatch.setattr(Technical, "_merge_full_team_rows", staticmethod(lambda rows, teams: rows))
    monkeypatch.setattr(Technical, "_merge_supplemental_team_tech", staticmethod(lambda rows, extra: rows))

    result = Technical.technical_match((718457, 718457, 1, 2, "2025-26", None))

    assert result["captureID"]
    assert result["capturedAt"]
    assert result["sourceOperation"] == "lq_technical_team"
    assert {row["rawCaptureID"] for row in result["teamPeriodRows"]} == {result["captureID"]}
    assert {row["rawCaptureID"] for row in result["players"]} == {result["captureID"]}


def test_text_live_propagates_one_capture_to_all_events(monkeypatch):
    monkeypatch.setattr(
        "lq.service.technical.sql_util.select",
        lambda sql: [(718457, 718457)],
    )
    monkeypatch.setattr(
        Technical,
        "_fetch_txt_live_js",
        staticmethod(lambda schedule_id: ("https://example.test/text-live.js", "payload", True)),
    )
    monkeypatch.setattr(
        Technical,
        "_parse_txt_live_events",
        staticmethod(lambda schedule_id, match_id, content: [{"liveID": 1}, {"liveID": 2}]),
    )

    result = Technical.text_live(718457)

    assert result["captureID"]
    assert result["capturedAt"]
    assert result["sourceOperation"] == "lq_text_live"
    assert {row["rawCaptureID"] for row in result["events"]} == {result["captureID"]}


def test_failed_fetch_does_not_create_capture_metadata():
    assert _new_capture_metadata(False) == {"captureID": None, "capturedAt": None}
