from __future__ import annotations

import re
from datetime import datetime

import pymysql
from bs4 import BeautifulSoup

from config import scrawler_config
from config.db_config import get_db_config
from utils.webUtil import WebUtil


REALTIME_URL = "{}/vbsxml/bfdata_ut.js".format(scrawler_config.qt_zq_web_ji.rstrip("/"))
ANALYSIS_HEADER_URL = (
    "{}/phone/txt/analysisheader/cn/{{prefix1}}/{{prefix2}}/{{schedule_id}}.txt"
).format(scrawler_config.qt_zq_web_livestatic.rstrip("/"))

_REALTIME_ROW = re.compile(r"A\[\d+\]=\"([^\"]*)\"\.split\('\^'\);")
_MATCH_COUNT = re.compile(r"\bmatchcount\s*=\s*(\d+)\s*;")
_FOOTBALL_STATES = {-14, -13, -12, -11, -10, -1, 0, 1, 2, 3, 4, 5}


def build_live_match_bootstrap_plan(
    schedule_id,
    realtime_content,
    analysis_content,
    league_metadata,
):
    """Build an identity-verified, schedule-only Football bootstrap plan."""

    resolved_schedule_id = _positive_int(schedule_id, "schedule_id")
    realtime = _parse_realtime_match(realtime_content, resolved_schedule_id)
    analysis = _parse_analysis_header(analysis_content, resolved_schedule_id)
    metadata = _validate_league_metadata(league_metadata)

    _require_equal("league_id", realtime["league_id"], analysis["league_id"])
    _require_equal("league_id", realtime["league_id"], metadata["league_id"])
    _require_equal("season", realtime["season"], metadata["season"])
    _require_equal("season", realtime["season"], str(analysis["match_time"].year))
    _require_equal("home_team_id", realtime["home_team_id"], analysis["home_team_id"])
    _require_equal("away_team_id", realtime["away_team_id"], analysis["away_team_id"])
    _require_name_equal("league_name", realtime["league_name"], analysis["league_name"])
    _require_name_equal("league_name", realtime["league_name"], metadata["league_name"])
    _require_name_equal("home_team", realtime["home_team"], analysis["home_team"])
    _require_name_equal("away_team", realtime["away_team"], analysis["away_team"])
    _validate_realtime_match_time(realtime, analysis["match_time"])
    _validate_lifecycle_order(realtime, analysis)

    return {
        "status": "ready",
        "operation": "football_live_match_schedule_bootstrap",
        "schedule_id": resolved_schedule_id,
        "identity_verification": "realtime_analysis_header_league_detail_agree",
        "lifecycle_observation": {
            "realtime_state": realtime["match_state"],
            "analysis_state": analysis["match_state"],
            "selected_state": analysis["match_state"],
            "realtime_state_reference_time": realtime["state_reference_time"],
            "analysis_updated_at": analysis["updated_at"],
            "selection_basis": "identity-bound analysis header is not older than realtime state reference",
        },
        "league_row": {
            "leagueID": realtime["league_id"],
            "nameChs": analysis["league_name"],
            "nameChsShort": analysis["league_name"],
            "type": metadata["league_type"],
            "currSeason": realtime["season"],
            "ifHaveSub": metadata["if_have_sub"],
        },
        "team_rows": [
            {
                "teamId": analysis["home_team_id"],
                "leagueId": realtime["league_id"],
                "nameChs": analysis["home_team"],
                "nameCht": analysis["home_team_traditional"],
            },
            {
                "teamId": analysis["away_team_id"],
                "leagueId": realtime["league_id"],
                "nameChs": analysis["away_team"],
                "nameCht": analysis["away_team_traditional"],
            },
        ],
        "schedule_row": {
            "scheduleID": resolved_schedule_id,
            "leagueID": realtime["league_id"],
            "matchSeason": realtime["season"],
            "homeTeamID": analysis["home_team_id"],
            "awayTeamID": analysis["away_team_id"],
            "matchTime": analysis["match_time"],
            "matchState": analysis["match_state"],
            "homeTeam": analysis["home_team"],
            "awayTeam": analysis["away_team"],
        },
        "excluded": [
            "score",
            "penalty_score",
            "odds",
            "technical_statistics",
            "events",
            "runtime",
            "cache",
        ],
        "provenance": {
            "realtime_url": REALTIME_URL,
            "analysis_header_url": _analysis_header_url(resolved_schedule_id),
            "league_metadata_status": metadata["metadata_binding_status"],
        },
        "time_semantics": {
            "source_timezone": "UTC+08:00",
            "storage_timezone": "UTC+08:00",
            "storage_representation": "naive_datetime",
            "match_time_basis": "identity-bound analysis header verified against realtime calendar and clock",
        },
    }


def run_live_match_bootstrap(schedule_id, *, execute=False):
    from zq.league_metadata import resolve_league_detail_by_id

    resolved_schedule_id = _positive_int(schedule_id, "schedule_id")
    realtime_url = "{}?r=007{}000".format(
        REALTIME_URL,
        int(datetime.now().timestamp()),
    )
    realtime_content = _fetch_text(
        realtime_url,
        headers={
            "Host": scrawler_config.qt_zq_live_host,
            "Referer": "https://live.titan007.com/oldIndexall.aspx",
        },
        source_name="football live match bootstrap realtime",
    )
    analysis_url = _analysis_header_url(resolved_schedule_id)
    analysis_content = _fetch_text(
        analysis_url,
        headers={
            "Referer": "{}/{}sb.htm".format(
                scrawler_config.qt_zq_web_livedetail.rstrip("/"),
                resolved_schedule_id,
            )
        },
        source_name="football live match bootstrap analysis header",
    )
    realtime = _parse_realtime_match(realtime_content, resolved_schedule_id)
    metadata = resolve_league_detail_by_id(realtime["league_id"])
    if metadata is None:
        raise ValueError("football live match bootstrap league metadata unavailable")
    plan = build_live_match_bootstrap_plan(
        resolved_schedule_id,
        realtime_content,
        analysis_content,
        metadata,
    )
    plan["provenance"]["realtime_url"] = realtime_url
    if execute:
        plan["persistence"] = persist_live_match_bootstrap(plan)
        plan["executed"] = True
    else:
        plan["persistence"] = inspect_live_match_bootstrap(plan)
        plan["executed"] = False
    return plan


def inspect_live_match_bootstrap(plan):
    connection = _connect()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            existing = _load_existing(cursor, plan)
            _validate_existing(existing, plan)
            return {
                "status": "dry_run",
                "will_insert": _missing_rows(existing, plan),
                "transaction_required": True,
            }
    finally:
        connection.close()


def persist_live_match_bootstrap(plan):
    connection = _connect()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            existing = _load_existing(cursor, plan, lock=True)
            _validate_existing(existing, plan)
            inserted = []
            if existing["league"] is None:
                _insert(cursor, "zq_league", plan["league_row"])
                inserted.append("zq_league")
            for index, team in enumerate(plan["team_rows"]):
                if existing["teams"][index] is None:
                    _insert(cursor, "zq_team", team)
                    inserted.append("zq_team:{}".format(team["teamId"]))
            if existing["schedule"] is None:
                _insert(cursor, "zq_schedule", plan["schedule_row"])
                inserted.append("zq_schedule")
            cursor.execute(
                "SELECT matchID FROM zq_schedule WHERE scheduleID=%s",
                (plan["schedule_id"],),
            )
            schedule = cursor.fetchone()
            if schedule is None:
                raise RuntimeError("football live match bootstrap schedule insert not observable")
        connection.commit()
        return {
            "status": "committed",
            "inserted": inserted,
            "system_match_id": int(schedule["matchID"]),
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _parse_realtime_match(content, schedule_id):
    text = str(content or "")
    count_match = _MATCH_COUNT.search(text)
    rows = _REALTIME_ROW.findall(text)
    if count_match is None or int(count_match.group(1)) != len(rows):
        raise ValueError("football realtime batch incomplete")
    selected = [row.split("^") for row in rows if row.split("^", 1)[0] == str(schedule_id)]
    if len(selected) != 1:
        raise ValueError("football realtime schedule identity is not unique")
    row = selected[0]
    if len(row) < 69:
        raise ValueError("football realtime row is incomplete")
    return {
        "schedule_id": _positive_int(row[0], "realtime_schedule_id"),
        "league_name": _plain_name(row[2]),
        "home_team": _plain_name(row[5]),
        "away_team": _plain_name(row[8]),
        "time_label": row[11].strip(),
        "state_reference_time": _parse_realtime_reference_time(row[12]),
        "match_state": _football_state(row[13], "realtime_match_state"),
        "month_day": row[36].strip(),
        "home_team_id": _positive_int(row[37], "realtime_home_team_id"),
        "away_team_id": _positive_int(row[38], "realtime_away_team_id"),
        "season": row[43].strip(),
        "league_id": _positive_int(row[45], "realtime_league_id"),
    }


def _parse_analysis_header(content, schedule_id):
    row = str(content or "").strip().split("^")
    if len(row) < 73:
        raise ValueError("football analysis header is incomplete")
    parsed_schedule_id = _positive_int(row[72], "analysis_schedule_id")
    _require_equal("schedule_id", schedule_id, parsed_schedule_id)
    return {
        "schedule_id": parsed_schedule_id,
        "home_team": _plain_name(row[0]),
        "away_team": _plain_name(row[1]),
        "home_team_traditional": _plain_name(row[2]),
        "away_team_traditional": _plain_name(row[3]),
        "match_state": _football_state(row[4], "analysis_match_state"),
        "match_time": datetime.strptime(row[5], "%Y%m%d%H%M%S"),
        "league_id": _positive_int(row[13], "analysis_league_id"),
        "league_name": _plain_name(row[15]),
        "home_team_id": _positive_int(row[17], "analysis_home_team_id"),
        "away_team_id": _positive_int(row[18], "analysis_away_team_id"),
        "updated_at": datetime.strptime(row[25], "%Y%m%d%H%M%S"),
    }


def _validate_league_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("football league metadata is required")
    seasons = [str(value).strip() for value in metadata.get("seasons", []) if str(value).strip()]
    if len(seasons) == 0:
        raise ValueError("football league metadata seasons are required")
    return {
        "league_id": _positive_int(metadata.get("league_id"), "metadata_league_id"),
        "league_name": _plain_name(metadata.get("league_name")),
        "league_type": _allowed_int(metadata.get("league_type"), "metadata_league_type", {1, 2}),
        "if_have_sub": _allowed_int(metadata.get("if_have_sub"), "metadata_if_have_sub", {0, 1}),
        "season": seasons[0],
        "metadata_binding_status": str(metadata.get("metadata_binding_status") or "unknown"),
    }


def _validate_realtime_match_time(realtime, match_time):
    if realtime["season"] != str(match_time.year):
        raise ValueError("football match time season conflict")
    if realtime["time_label"] != match_time.strftime("%H:%M"):
        raise ValueError("football match time clock conflict")
    if realtime["month_day"] != "{}-{}".format(match_time.month, match_time.day):
        raise ValueError("football match time calendar conflict")


def _validate_lifecycle_order(realtime, analysis):
    if analysis["updated_at"] < realtime["state_reference_time"]:
        raise ValueError("football lifecycle evidence time order conflict")


def _load_existing(cursor, plan, lock=False):
    suffix = " FOR UPDATE" if lock else ""
    cursor.execute(
        "SELECT leagueID,nameChs,nameChsShort,type,currSeason,ifHaveSub "
        "FROM zq_league WHERE leagueID=%s" + suffix,
        (plan["league_row"]["leagueID"],),
    )
    league = cursor.fetchone()
    teams = []
    for team in plan["team_rows"]:
        cursor.execute(
            "SELECT teamId,leagueId,nameChs,nameCht FROM zq_team WHERE teamId=%s" + suffix,
            (team["teamId"],),
        )
        teams.append(cursor.fetchone())
    cursor.execute(
        "SELECT matchID,scheduleID,leagueID,matchSeason,homeTeamID,awayTeamID,"
        "matchTime,homeTeam,awayTeam FROM zq_schedule WHERE scheduleID=%s" + suffix,
        (plan["schedule_id"],),
    )
    return {"league": league, "teams": teams, "schedule": cursor.fetchone()}


def _validate_existing(existing, plan):
    if existing["league"] is not None:
        _validate_row_identity(
            "league",
            existing["league"],
            plan["league_row"],
            ("leagueID", "nameChs", "type"),
        )
    for current, expected in zip(existing["teams"], plan["team_rows"]):
        if current is not None:
            _validate_row_identity(
                "team",
                current,
                expected,
                ("teamId", "nameChs"),
            )
    if existing["schedule"] is not None:
        _validate_row_identity(
            "schedule",
            existing["schedule"],
            plan["schedule_row"],
            (
                "scheduleID",
                "leagueID",
                "matchSeason",
                "homeTeamID",
                "awayTeamID",
                "matchTime",
                "homeTeam",
                "awayTeam",
            ),
        )


def _validate_row_identity(kind, current, expected, fields):
    for field in fields:
        current_value = current.get(field)
        expected_value = expected.get(field)
        if isinstance(current_value, datetime) and isinstance(expected_value, datetime):
            equal = current_value.replace(microsecond=0) == expected_value.replace(microsecond=0)
        elif field in ("nameChs", "homeTeam", "awayTeam"):
            equal = _normalized_name(current_value) == _normalized_name(expected_value)
        else:
            equal = str(current_value) == str(expected_value)
        if not equal:
            raise ValueError("football {} identity conflict: {}".format(kind, field))


def _missing_rows(existing, plan):
    missing = []
    if existing["league"] is None:
        missing.append("zq_league")
    for index, current in enumerate(existing["teams"]):
        if current is None:
            missing.append("zq_team:{}".format(plan["team_rows"][index]["teamId"]))
    if existing["schedule"] is None:
        missing.append("zq_schedule")
    return missing


def _insert(cursor, table, row):
    fields = list(row)
    placeholders = ",".join(["%s"] * len(fields))
    cursor.execute(
        "INSERT INTO {} ({}) VALUES ({})".format(table, ",".join(fields), placeholders),
        tuple(row[field] for field in fields),
    )


def _fetch_text(url, *, headers, source_name):
    state, content = WebUtil.requests_get(url, headers=headers, sourceName=source_name)
    if state != 1 or not content:
        raise ValueError("football live match bootstrap source unavailable: {}".format(source_name))
    return content


def _analysis_header_url(schedule_id):
    text = str(schedule_id)
    if len(text) < 3:
        raise ValueError("schedule_id must have at least three digits")
    return ANALYSIS_HEADER_URL.format(
        prefix1=text[0:1],
        prefix2=text[1:3],
        schedule_id=text,
    )


def _connect():
    return pymysql.connect(**get_db_config("default"))


def _plain_name(value):
    text = BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)
    if not text:
        raise ValueError("football identity name is required")
    return text


def _normalized_name(value):
    return re.sub(r"[\s\-_]+", "", _plain_name(value)).casefold()


def _require_name_equal(field, left, right):
    if _normalized_name(left) != _normalized_name(right):
        raise ValueError("football identity conflict: {}".format(field))


def _require_equal(field, left, right):
    if left != right:
        raise ValueError("football identity conflict: {}".format(field))


def _positive_int(value, field):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("{} must be a positive integer".format(field)) from exc
    if parsed <= 0:
        raise ValueError("{} must be a positive integer".format(field))
    return parsed


def _allowed_int(value, field, allowed):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("{} is invalid".format(field)) from exc
    if parsed not in allowed:
        raise ValueError("{} is invalid".format(field))
    return parsed


def _football_state(value, field):
    return _allowed_int(value, field, _FOOTBALL_STATES)


def _parse_realtime_reference_time(value):
    parts = str(value or "").split(",")
    if len(parts) != 6:
        raise ValueError("football realtime state reference time is invalid")
    try:
        return datetime(
            int(parts[0]),
            int(parts[1]) + 1,
            int(parts[2]),
            int(parts[3]),
            int(parts[4]),
            int(parts[5]),
        )
    except ValueError as exc:
        raise ValueError("football realtime state reference time is invalid") from exc
