import sys
import types


if "js2py" not in sys.modules:
    js2py_stub = types.ModuleType("js2py")
    js2py_stub.EvalJs = object
    sys.modules["js2py"] = js2py_stub

from lq.service.technical import Technical, _new_capture_metadata, _qualify_player_plus_minus


def test_full_game_totals_are_not_overwritten_by_conflicting_comparison(monkeypatch):
    # Source match 728868: the comparison block repeats 3P as FG, but the
    # explicit team-total rows contain the correct full-game FG operands.
    home = '240^43^81^8^27^26^32^12^40^52^31^22^11^21^9^120'
    away = '240^42^98^11^39^15^21^13^22^35^26^25^10^13^4^110'
    periods = ('0!0^8^27^11^39^29.6^28.2,1^8^27^11^39^29.6^28.2,2^26^32^15^21'
               '!!1!0^13^25^13^25,1^1^7^3^11,2^5^5^6^6'
               '!!2!0^11^21^11^24,1^3^9^5^12,2^6^7^4^5'
               '!!3!0^9^15^9^28,1^1^1^0^10,2^9^12^1^3'
               '!!4!0^10^20^9^21,1^3^10^3^6,2^6^8^4^7')
    raw = 'header$' + home + '!rates$' + away + '!rates$$' + periods
    monkeypatch.setattr(Technical, '_fetch_technical_js', staticmethod(
        lambda _: ('https://example.test/728868.js', raw, True)))

    result = Technical.technical_match((728868, 363413, 21, 13, '2026-27', None))
    rows = {(r['period'], r['isHome']): r for r in result['teamPeriodRows']}

    assert (rows[0, 1]['shoot_Hit'], rows[0, 1]['shoot']) == (43, 81)
    assert (rows[0, 0]['shoot_Hit'], rows[0, 0]['shoot']) == (42, 98)
    assert (rows[0, 0]['threeMin_Hit'], rows[0, 0]['threeMin']) == (11, 39)
    assert (rows[1, 0]['shoot_Hit'], rows[1, 0]['shoot']) == (13, 25)
    assert rows[0, 0]['score'] == 110
    assert rows[0, 0]['loseScore'] == 120
    assert result['rawTech'] == raw
    assert rows[0, 0]['rawData'] == periods.split('!!')[0]
    assert {r['rawCaptureID'] for r in rows.values()} == {result['captureID']}


def test_unverified_team_total_does_not_replace_comparison_values():
    periods = [{'period': 0, 'isHome': 1, 'shoot_Hit': 8, 'shoot': 27,
                'rob': 3, 'rawData': 'original comparison'}]
    teams = [{'isHome': 1, 'shoot_Hit': 0, 'shoot': None},
             {'isHome': 0, 'shoot_Hit': 42, 'shoot': 98}]
    result = Technical._merge_full_team_rows(periods, teams)
    assert result[0]['shoot_Hit'] == 8
    assert result[0]['shoot'] == 27
    assert result[0]['rob'] == 3
    assert result[0]['rawData'] == 'original comparison'
    assert result[1]['period'] == 0 and result[1]['shoot'] == 98
    assert periods[0]['shoot_Hit'] == 8
    assert teams[0]['shoot'] is None


def test_fg_as_three_point_recovery_requires_valid_totals_and_matching_three_points():
    fields = ('shoot_Hit', 'shoot', 'threeMin_Hit', 'threeMin', 'punishBall_Hit', 'punishBall')
    team = dict(zip(fields, (20, 40, 4, 12, 8, 12)), isHome=1, score=52)
    comparison = {**team, 'period': 0, 'shoot_Hit': 4, 'shoot': 12}
    quarters = [dict(zip(fields, (5, 10, 1, 3, 2, 3)), isHome=1, period=p) for p in range(1, 5)]
    assert Technical._verified_full_game_shooting(team, comparison, quarters)
    assert Technical._verified_full_game_shooting(team, comparison, [])
    assert Technical._verified_full_game_shooting({**team, 'score': 53}, comparison, quarters)
    assert Technical._verified_full_game_shooting(team, {**comparison, 'punishBall': 13}, quarters)
    assert not Technical._verified_full_game_shooting({**team, 'shoot': None}, comparison, quarters)
    assert not Technical._verified_full_game_shooting(team, {**comparison, 'threeMin': 13}, quarters)
    assert not Technical._verified_full_game_shooting({**team, 'shoot_Hit': 41}, comparison, quarters)
    assert not Technical._verified_full_game_shooting(team, {**comparison, 'shoot_Hit': 19}, quarters)


def test_missing_total_keeps_real_zero_from_comparison():
    result = Technical._merge_full_team_rows(
        [{'period': 0, 'isHome': 1, 'shoot_Hit': 0, 'shoot': 0}],
        [{'isHome': 1, 'shoot_Hit': None}, {'isHome': 0, 'shoot_Hit': None}])
    assert result[0]['shoot_Hit'] == 0 and result[0]['shoot'] == 0


def test_collector_corrects_fg_from_players_even_without_explicit_team_totals(monkeypatch):
    player = '^'.join(str(v) for v in [100, 'Name', 'Name', 'Name', 0, 'G', 30,
        5, 10, 1, 3, 2, 2, 0, 1, 1, 1, 0, 0, 0, 0, 13, 1, 'Name', 0, '1', ''])
    other = player.replace('100^', '101^', 1)
    wire = 'header$' + player + '!missing!rates$' + other + '!missing!rates$$0!0^1^3^1^3,1^1^3^1^3'
    monkeypatch.setattr(Technical, '_fetch_technical_js', staticmethod(
        lambda _: ('source', wire, True)))
    for include_players in (False, True):
        result = Technical.technical_match((100, 10, 1, 2, '26-27', None), include_players=include_players)
        assert len(result['teamPeriodRows']) == 2
        assert all((r['shoot_Hit'], r['shoot']) == (5, 10) for r in result['teamPeriodRows'])
        assert len(result['players']) == (2 if include_players else 0)


def test_team_totals_supply_missing_full_game_without_changing_periods():
    periods = [{'period': 1, 'isHome': 1, 'shoot_Hit': 13}]
    teams = [{'isHome': 1, 'shoot_Hit': 43}, {'isHome': 0, 'shoot_Hit': 42}]
    result = Technical._merge_full_team_rows(periods, teams)
    assert result == [periods[0], {**teams[0], 'period': 0}, {**teams[1], 'period': 0}]
    assert Technical._merge_full_team_rows(periods, []) == periods


def test_all_zero_match_plus_minus_is_unknown_before_persistence():
    rows = [
        {"teamID": 1, "plusMinus": 0},
        {"teamID": 2, "plusMinus": 0},
    ]
    _qualify_player_plus_minus(rows)
    assert [row["plusMinus"] for row in rows] == [None, None]


def test_mixed_match_keeps_real_zero_and_signed_plus_minus():
    rows = [
        {"teamID": 1, "plusMinus": 0},
        {"teamID": 1, "plusMinus": 4},
        {"teamID": 2, "plusMinus": -4},
    ]
    _qualify_player_plus_minus(rows)
    assert [row["plusMinus"] for row in rows] == [0, 4, -4]


def test_missing_and_zero_plus_minus_remain_unknown():
    rows = [{"plusMinus": None}, {"plusMinus": 0}]
    _qualify_player_plus_minus(rows)
    assert [row["plusMinus"] for row in rows] == [None, None]


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


def test_technical_persistence_keeps_raw_and_structured_capture_binding(monkeypatch):
    monkeypatch.setattr('lq.service.technical.register_technical_identities', lambda *args: [])
    capture_id = "technical-capture-1"
    raw_writes = []
    structured_writes = []
    monkeypatch.setattr("lq.service.technical.sql_util.select", lambda sql: [(718457, 718457, 1, 2, "2025-26", None)])
    monkeypatch.setattr(
        Technical,
        "technical_match",
        staticmethod(lambda match, include_players: {
            "requestOk": True,
            "matchID": 718457,
            "rawTech": "payload",
            "sourceUrl": "https://example.test/technical.js",
            "sourceOperation": "lq_technical_team",
            "captureID": capture_id,
            "capturedAt": "2026-07-20 01:02:03.123456",
            "teams": [{"teamID": 1}, {"teamID": 2}],
            "teamPeriodRows": [{"teamID": 1, "rawCaptureID": capture_id}],
            "players": [{"playerID": 10, "rawCaptureID": capture_id}],
        }),
    )
    monkeypatch.setattr(
        "lq.service.technical.sql_util.replace_table_row",
        lambda table, condition, data: raw_writes.append((table, data)) or True,
    )
    monkeypatch.setattr(
        "lq.service.technical.sql_util.replace_table_rows",
        lambda table, condition, rows: structured_writes.append((table, rows)) or True,
    )
    monkeypatch.setattr("lq.service.technical.sql_util.upData", lambda *args: None)

    result = Technical.upMatchTechnical(718457)

    assert result["request_ok"] is True
    assert raw_writes[0][1]["captureID"] == capture_id
    assert raw_writes[0][1]["sourceOperation"] == "lq_technical_team"
    assert raw_writes[0][1]["recordedAt"] is not None
    assert {rows[0]["rawCaptureID"] for _, rows in structured_writes} == {capture_id}


def test_event_persistence_keeps_raw_and_structured_capture_binding(monkeypatch):
    capture_id = "event-capture-1"
    raw_writes = []
    structured_writes = []
    monkeypatch.setattr(
        Technical,
        "text_live",
        staticmethod(lambda schedule_id: {
            "requestOk": True,
            "matchID": 718457,
            "rawTextLive": "payload",
            "sourceUrl": "https://example.test/text-live.js",
            "sourceOperation": "lq_text_live",
            "captureID": capture_id,
            "capturedAt": "2026-07-20 01:02:03.123456",
            "events": [{"liveID": 1, "rawCaptureID": capture_id}],
        }),
    )
    monkeypatch.setattr(
        "lq.service.technical.sql_util.replace_table_row",
        lambda table, condition, data: raw_writes.append((table, data)) or True,
    )
    monkeypatch.setattr(
        "lq.service.technical.sql_util.replace_table_rows",
        lambda table, condition, rows: structured_writes.append((table, rows)) or True,
    )

    result = Technical.upMatchTextLive(718457)

    assert result["request_ok"] is True
    assert raw_writes[0][1]["captureID"] == capture_id
    assert raw_writes[0][1]["sourceOperation"] == "lq_text_live"
    assert raw_writes[0][1]["recordedAt"] is not None
    assert structured_writes[0][1][0]["rawCaptureID"] == capture_id
