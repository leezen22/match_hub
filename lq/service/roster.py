import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin

from config import lqconfig_qt
from lq.service.team import _asset_url, _int_or_none, _parse_datetime, _short_season, _to_list, _update_payload, _value
from scripts.migrate_lq_basic_information_tables import migrate
from utils import js2pyUtil, sql_util
from utils.webUtil import WebUtil


SOURCE_NAMESPACE = "titan_basketball"
TITAN_PAGE_BASE_URL = "https://nba.titan007.com"
USD_SALARY_LEAGUE_IDS = {1, 2, 34, 42, 54}
PLAYER_PHOTO_CACHE = {}


def update_team_roster(team_id, version=None, fetch_photos=True, run_migrate=True):
    if run_migrate:
        migrate()
    context, source_url, captured_at = fetch_team_detail_context(team_id, version=version)
    arr_league = _to_list(context.arrLeague)
    team_summary = _to_list(context.teamSummary)
    players = _to_list(context.teamPlayers)

    league_id = int(arr_league[0])
    resolved_team_id = int(team_summary[0]) if team_summary else int(team_id)
    season = str(arr_league[4]) if len(arr_league) > 4 else ""
    source_state_valid_at = _parse_datetime(getattr(context, "teamLastUpdateTime", None))
    recorded_at = _now()

    rows = [
        _player_row(
            player,
            league_id,
            resolved_team_id,
            season,
            source_url,
            captured_at,
            recorded_at,
            source_state_valid_at,
            fetch_photos,
        )
        for player in players
    ]
    roster_hash = _roster_hash(rows)
    previous_batch = _latest_success_batch(league_id, resolved_team_id, season)
    previous_hash = previous_batch.get("roster_hash") if previous_batch else None
    previous_batch_id = previous_batch.get("snapshot_batch_id") if previous_batch else None
    current_missing = not _current_has_scope(league_id, resolved_team_id, season)
    changed = 1 if roster_hash != previous_hash or current_missing else 0
    snapshot_batch_id = _snapshot_batch_id(league_id, resolved_team_id, season, captured_at, roster_hash)

    _upsert_roster_batch(
        snapshot_batch_id,
        league_id,
        resolved_team_id,
        season,
        roster_hash,
        captured_at,
        recorded_at,
        source_state_valid_at,
        source_url,
        1 if len(rows) > 0 else 0,
        changed,
        previous_batch_id,
    )

    for row in rows:
        _upsert_player_profile(row)

    if changed:
        for row in rows:
            _insert_roster_snapshot(snapshot_batch_id, row)
        _refresh_roster_current(snapshot_batch_id, league_id, resolved_team_id, season, rows, captured_at, source_url)
    else:
        _touch_roster_current(league_id, resolved_team_id, season, captured_at, source_url)
        _refresh_roster_current_profiles(league_id, resolved_team_id, season, rows)
    relation_result = _sync_player_team_relations(
        rows,
        league_id,
        resolved_team_id,
        season,
        captured_at,
        recorded_at,
        source_state_valid_at,
        source_url,
    )

    print("basketball team roster update finished: team_id={0}, league_id={1}, season={2}, players={3}, changed={4}, relation_active={5}, relation_inactive={6}".format(
        resolved_team_id,
        league_id,
        season,
        len(rows),
        changed,
        relation_result["active"],
        relation_result["inactive"],
    ))
    return {
        "team_id": resolved_team_id,
        "league_id": league_id,
        "season": season,
        "players": len(rows),
        "changed": changed,
        "snapshot_batch_id": snapshot_batch_id,
        "source_url_or_operation": source_url,
        "relation": relation_result,
    }


def update_all_team_rosters(limit=None, offset=0, missing_only=False, fetch_photos=True, league_id=None):
    migrate()
    where = [
        "t.collection_status='success'",
        "COALESCE(t.is_placeholder,0)=0",
    ]
    if league_id is not None:
        where.append("t.leagueID={0}".format(int(league_id)))
    teams = sql_util.select_dicts(
        "SELECT DISTINCT t.ID,t.leagueID,t.name_j FROM lq_team t "
        "LEFT JOIN lq_team_league_relation r ON r.teamID=t.ID AND r.relationStatus='active' "
        "WHERE {0} ORDER BY t.leagueID,t.ID".format(" AND ".join(where))
    )
    if missing_only:
        collected_team_ids = {
            int(row["teamID"])
            for row in sql_util.select_dicts(
                "SELECT DISTINCT teamID FROM lq_team_roster_snapshot_batch "
                "WHERE source_namespace='{0}' AND collection_status='success'".format(SOURCE_NAMESPACE)
            )
        }
        teams = [team for team in teams if int(team["ID"]) not in collected_team_ids]
    if offset:
        teams = teams[int(offset):]
    if limit is not None:
        teams = teams[:int(limit)]

    total = len(teams)
    success = 0
    failed = 0
    failures = []
    for index, team in enumerate(teams, start=1):
        team_id = int(team["ID"])
        try:
            print("start basketball roster update: {0}/{1}, team_id={2}, team_name={3}".format(
                index,
                total,
                team_id,
                team.get("name_j"),
            ))
            update_team_roster(team_id, fetch_photos=fetch_photos, run_migrate=False)
            success += 1
        except Exception as exc:
            failed += 1
            failures.append({"team_id": team_id, "team_name": team.get("name_j"), "error": str(exc)})
            _record_roster_failure(team)
    print("basketball all roster update finished: total={0}, success={1}, failed={2}".format(total, success, failed))
    return {"total": total, "success": success, "failed": failed, "failures": failures}


def update_player_profile_photos(
        limit=None,
        offset=0,
        missing_only=True,
        workers=1,
        batch_size=20,
        batch_sleep=3,
        retry_failed=False,
        max_batch_failed_ratio=0.5):
    migrate()
    _backfill_existing_player_photo_status()
    where = "WHERE player_url IS NOT NULL AND player_url<>''"
    if missing_only:
        retry_failed_sql = " OR photo_collection_status='failed'" if retry_failed else ""
        where += (
            " AND (photo_collection_status IS NULL{0} "
            "OR (photo_collection_status='success_with_data' AND (playerPic_url IS NULL OR playerPic_url='')))"
        ).format(retry_failed_sql)
    sql = "SELECT playerID,player_url FROM lq_player_profile {0} ORDER BY id".format(where)
    if limit is not None:
        sql += " LIMIT {0}, {1}".format(int(offset or 0), int(limit))
    elif offset:
        sql += " LIMIT {0}, 18446744073709551615".format(int(offset))
    rows = sql_util.select_dicts(sql)
    total = len(rows)
    success = 0
    empty = 0
    failed = 0
    workers = max(1, int(workers or 1))
    batch_size = max(1, int(batch_size or 1))
    batch_sleep = max(0, float(batch_sleep or 0))
    max_batch_failed_ratio = max(0, min(1, float(max_batch_failed_ratio)))
    stopped_early = False

    for start in range(0, total, batch_size):
        batch = rows[start:start + batch_size]
        batch_success = 0
        batch_empty = 0
        batch_failed = 0
        if workers == 1:
            statuses = [
                _update_one_player_photo(row, start + offset_index, total)
                for offset_index, row in enumerate(batch, start=1)
            ]
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(_update_one_player_photo, row, start + offset_index, total)
                    for offset_index, row in enumerate(batch, start=1)
                ]
                statuses = [future.result() for future in as_completed(futures)]

        for status in statuses:
            if status == "success_with_data":
                success += 1
                batch_success += 1
            elif status == "success_empty":
                empty += 1
                batch_empty += 1
            else:
                failed += 1
                batch_failed += 1

        if len(batch) >= 5 and batch_failed / float(len(batch)) >= max_batch_failed_ratio:
            stopped_early = True
            print("basketball player photo update stopped by failure circuit breaker: batch_start={0}, batch_size={1}, batch_failed={2}".format(
                start + 1,
                len(batch),
                batch_failed,
            ), flush=True)
            break
        if start + batch_size < total and batch_sleep:
            time.sleep(batch_sleep)

    print("basketball player photo update finished: total={0}, success_with_data={1}, success_empty={2}, failed={3}, stopped_early={4}".format(
        total,
        success,
        empty,
        failed,
        stopped_early,
    ), flush=True)
    return {
        "total": total,
        "success_with_data": success,
        "success_empty": empty,
        "failed": failed,
        "stopped_early": stopped_early,
    }


def _update_one_player_photo(row, index, total):
    player_id = int(row["playerID"])
    player_url = row["player_url"]
    try:
        print("start basketball player photo update: {0}/{1}, player_id={2}".format(
            index,
            total,
            player_id,
        ), flush=True)
        photo = _fetch_player_photo_from_url(player_url)
        if not photo.get("request_ok"):
            raise ValueError("player photo page request failed")
        if photo.get("url"):
            _update_player_photo(player_id, photo, player_url, "success_with_data", 1)
            return "success_with_data"
        _update_player_photo_collection_status(player_id, player_url, "success_empty", 0)
        return "success_empty"
    except Exception:
        _update_player_photo_collection_status(player_id, player_url, "failed", 0)
        return "failed"


def _backfill_existing_player_photo_status():
    now = _now()
    sql_util.sqlExecute(
        "UPDATE lq_player_profile SET "
        "photo_collection_status='success_with_data', "
        "photo_has_data=1, "
        "photo_updated_at='{0}', "
        "photo_source_url_or_operation=COALESCE(player_url, source_url_or_operation) "
        "WHERE photo_collection_status IS NULL "
        "AND playerPic_url IS NOT NULL AND playerPic_url<>''".format(now)
    )


def fetch_team_detail_context(team_id, version=None):
    content, source_url, captured_at = fetch_team_detail_js(team_id, version=version)
    result = js2pyUtil.js2c(content, source=source_url, required_names=("arrLeague", "teamSummary", "teamPlayers"))
    if result[0] != 1:
        raise ValueError("could not parse basketball team detail js for team_id={0}".format(team_id))
    return result[1], source_url, captured_at


def fetch_team_detail_js(team_id, version=None):
    captured_at = _now()
    url = urljoin(lqconfig_qt.lanqurl, "/jsData/teamInfo/teamDetail/td{0}.js".format(int(team_id)))
    if version:
        url = url + "?version=" + str(version)
    response = WebUtil.requests_get(
        url,
        headers=_team_detail_headers(team_id),
        timeout=20,
        retry_time=3,
        sourceName="lq team roster",
    )
    if response[0] != 1:
        raise ValueError("could not fetch basketball team detail js: {0}".format(url))
    return response[1], url, captured_at


def _team_detail_headers(team_id):
    headers = dict(lqconfig_qt.headers)
    headers["Referer"] = urljoin(lqconfig_qt.lanqurl, "/cn/Team/Lineup.aspx?TeamID={0}".format(int(team_id)))
    headers["Accept"] = "*/*"
    return headers


def _player_row(player, league_id, team_id, season, source_url, captured_at, recorded_at, source_state_valid_at,
                fetch_photos=True):
    player_id = _int_or_none(_value(player, 0))
    nationality = _value(player, 15) or []
    annual_salary = _value(player, 14)
    player_url = urljoin(
        TITAN_PAGE_BASE_URL,
        "/cn/Team/player.aspx?playerid={0}&TeamID={1}".format(player_id, int(team_id)),
    )
    player_photo = _fetch_player_photo(player_id, team_id, player_url) if fetch_photos else {"path": None, "url": None}
    annual_salary_currency, annual_salary_display = _annual_salary_unit(league_id, annual_salary)
    return {
        "playerID": player_id,
        "source_namespace": SOURCE_NAMESPACE,
        "source_entity_id": str(player_id),
        "leagueID": int(league_id),
        "teamID": int(team_id),
        "season": season,
        "playerName": _value(player, 1),
        "playerNameTrad": _value(player, 2),
        "playerNameEn": _value(player, 3),
        "shortName": _value(player, 4),
        "shortNameTrad": _value(player, 5),
        "shortNameEn": _value(player, 6),
        "shirtNumber": _value(player, 7),
        "position": _value(player, 8),
        "birthDate": _date_or_none(_value(player, 9)),
        "height": _value(player, 10),
        "weight": _value(player, 11),
        "experience": _value(player, 12),
        "contractUntil": _date_or_none(_value(player, 13)),
        "annualSalary": annual_salary,
        "annualSalaryCurrency": annual_salary_currency,
        "annualSalaryDisplay": annual_salary_display,
        "playerPic": player_photo.get("path"),
        "playerPic_url": player_photo.get("url"),
        "nationality": _value(nationality, 0),
        "nationalityTrad": _value(nationality, 1),
        "nationalityEn": _value(nationality, 2),
        "draftInfo": _value(player, 16),
        "player_url": player_url,
        "rosterStatus": "active",
        "activeStatus": "active",
        "captured_at": captured_at,
        "recorded_at": recorded_at,
        "updated_at": recorded_at,
        "source_state_valid_at": source_state_valid_at,
        "source_url_or_operation": source_url,
        "collection_status": "success",
        "has_data": 1,
        "rawData": json.dumps(player, ensure_ascii=False),
    }


def _fetch_player_photo(player_id, team_id, player_url):
    if player_id is None:
        return {"path": None, "url": None}
    key = (int(player_id), int(team_id))
    if key in PLAYER_PHOTO_CACHE:
        return PLAYER_PHOTO_CACHE[key]
    response = WebUtil.requests_get(
        player_url,
        headers=_player_page_headers(team_id),
        timeout=20,
        retry_time=2,
        sourceName="lq player profile page",
    )
    photo_path = None
    photo_url = None
    if response[0] == 1 and response[1]:
        match = re.search(r'<img\s+src="([^"]*/files/Player/[^"]+)"', response[1], flags=re.IGNORECASE)
        if match:
            photo_path = match.group(1).strip()
            photo_url = _asset_url(photo_path)
    PLAYER_PHOTO_CACHE[key] = {"path": photo_path, "url": photo_url}
    return PLAYER_PHOTO_CACHE[key]


def _fetch_player_photo_from_url(player_url):
    response = WebUtil.requests_get(
        player_url,
        headers=dict(lqconfig_qt.headers),
        timeout=20,
        retry_time=2,
        sourceName="lq player profile photo page",
    )
    photo_path = None
    photo_url = None
    request_ok = response[0] == 1 and bool(response[1]) and not _looks_like_block_page(response[1])
    if request_ok:
        match = re.search(r'<img\s+src="([^"]*/files/Player/[^"]+)"', response[1], flags=re.IGNORECASE)
        if match:
            photo_path = match.group(1).strip()
            photo_url = _asset_url(photo_path)
    return {"path": photo_path, "url": photo_url, "request_ok": request_ok}


def _looks_like_block_page(content):
    text = str(content or "")[:2000].lower()
    markers = [
        "captcha",
        "forbidden",
        "access denied",
        "访问过于频繁",
        "验证码",
        "安全验证",
    ]
    return any(marker in text for marker in markers)


def _update_player_photo(player_id, photo, player_url=None, collection_status="success_with_data", has_data=1):
    now = _now()
    payload = {
        "playerPic": photo.get("path"),
        "playerPic_url": photo.get("url"),
        "photo_collection_status": collection_status,
        "photo_has_data": has_data,
        "photo_captured_at": now,
        "photo_updated_at": now,
        "photo_source_url_or_operation": player_url,
        "updated_at": now,
    }
    sql_util.upData(
        "lq_player_profile",
        _update_payload(payload),
        {"source_namespace": SOURCE_NAMESPACE, "source_entity_id": str(int(player_id))},
    )
    sql_util.upData(
        "lq_team_roster_current",
        _update_payload({
            "playerPic": photo.get("path"),
            "playerPic_url": photo.get("url"),
            "updated_at": now,
        }),
        {"source_namespace": SOURCE_NAMESPACE, "playerID": int(player_id)},
    )


def _update_player_photo_collection_status(player_id, player_url, collection_status, has_data):
    now = _now()
    payload = {
        "photo_collection_status": collection_status,
        "photo_has_data": has_data,
        "photo_captured_at": now,
        "photo_updated_at": now,
        "photo_source_url_or_operation": player_url,
        "updated_at": now,
    }
    sql_util.upData(
        "lq_player_profile",
        _update_payload(payload),
        {"source_namespace": SOURCE_NAMESPACE, "source_entity_id": str(int(player_id))},
    )


def _player_page_headers(team_id):
    headers = dict(lqconfig_qt.headers)
    headers["Referer"] = urljoin(lqconfig_qt.lanqurl, "/cn/Team/Lineup.aspx?TeamID={0}".format(int(team_id)))
    return headers


def _upsert_player_profile(row):
    profile = {
        key: row.get(key)
        for key in [
            "playerID", "source_namespace", "source_entity_id", "playerName", "playerNameTrad", "playerNameEn",
            "shortName", "shortNameTrad", "shortNameEn", "birthDate", "height", "weight", "nationality",
            "nationalityTrad", "nationalityEn", "position", "shirtNumber", "playerPic", "playerPic_url",
            "player_url", "experience", "contractUntil", "annualSalary", "annualSalaryCurrency",
            "annualSalaryDisplay", "draftInfo", "rawData", "activeStatus", "captured_at",
            "recorded_at", "updated_at", "source_state_valid_at", "source_url_or_operation", "collection_status",
            "has_data",
        ]
    }
    condition = {"source_namespace": SOURCE_NAMESPACE, "source_entity_id": row["source_entity_id"]}
    result = sql_util.select_table_dicts("lq_player_profile", ["playerID", "playerPic"], condition)
    if len(result) > 0:
        sql_util.upData("lq_player_profile", _player_profile_update_payload(profile, result[0]), condition)
    else:
        sql_util.insertData("lq_player_profile", profile)


def _upsert_roster_batch(snapshot_batch_id, league_id, team_id, season, roster_hash, captured_at, recorded_at,
                         source_state_valid_at, source_url, has_data, changed, previous_batch_id):
    row = {
        "snapshot_batch_id": snapshot_batch_id,
        "source_namespace": SOURCE_NAMESPACE,
        "leagueID": int(league_id),
        "teamID": int(team_id),
        "season": season,
        "roster_hash": roster_hash,
        "captured_at": captured_at,
        "recorded_at": recorded_at,
        "updated_at": recorded_at,
        "source_state_valid_at": source_state_valid_at,
        "source_url_or_operation": source_url,
        "collection_status": "success",
        "has_data": has_data,
        "changed_from_previous": changed,
        "previous_snapshot_batch_id": previous_batch_id,
    }
    result = sql_util.select_table_rows("lq_team_roster_snapshot_batch", ["snapshot_batch_id"], {"snapshot_batch_id": snapshot_batch_id})
    if len(result) > 0:
        sql_util.upData("lq_team_roster_snapshot_batch", _update_payload(row), {"snapshot_batch_id": snapshot_batch_id})
    else:
        sql_util.insertData("lq_team_roster_snapshot_batch", row)


def _insert_roster_snapshot(snapshot_batch_id, row):
    snapshot = _roster_payload(row)
    snapshot["snapshot_batch_id"] = snapshot_batch_id
    result = sql_util.select_table_rows(
        "lq_team_roster_snapshot",
        ["snapshot_batch_id"],
        {"snapshot_batch_id": snapshot_batch_id, "playerID": row["playerID"]},
    )
    if len(result) == 0:
        sql_util.insertData("lq_team_roster_snapshot", snapshot)


def _refresh_roster_current(snapshot_batch_id, league_id, team_id, season, rows, captured_at, source_url):
    seen = [str(row["playerID"]) for row in rows if row.get("playerID") is not None]
    if seen:
        sql_util.sqlExecute(
            "UPDATE lq_team_roster_current SET rosterStatus='inactive', latest_checked_at='{0}', updated_at='{0}' "
            "WHERE source_namespace='{1}' AND leagueID={2} AND teamID={3} AND season='{4}' "
            "AND playerID NOT IN ({5})".format(
                captured_at,
                SOURCE_NAMESPACE,
                int(league_id),
                int(team_id),
                sql_util.safe(season),
                ",".join(seen),
            )
        )
    for row in rows:
        current = _roster_payload(row)
        current["latest_snapshot_batch_id"] = snapshot_batch_id
        current["latest_captured_at"] = captured_at
        current["latest_checked_at"] = captured_at
        current["updated_at"] = captured_at
        condition = {
            "source_namespace": SOURCE_NAMESPACE,
            "leagueID": int(league_id),
            "teamID": int(team_id),
            "season": season,
            "playerID": row["playerID"],
        }
        result = sql_util.select_table_rows("lq_team_roster_current", ["playerID"], condition)
        if len(result) > 0:
            sql_util.upData("lq_team_roster_current", _update_payload(current), condition)
        else:
            sql_util.insertData("lq_team_roster_current", current)


def _touch_roster_current(league_id, team_id, season, captured_at, source_url):
    sql_util.sqlExecute(
        "UPDATE lq_team_roster_current SET latest_checked_at='{0}', updated_at='{0}', "
        "source_url_or_operation='{1}', collection_status='success', has_data=1 "
        "WHERE source_namespace='{2}' AND leagueID={3} AND teamID={4} AND season='{5}'".format(
            captured_at,
            sql_util.safe(source_url),
            SOURCE_NAMESPACE,
            int(league_id),
            int(team_id),
            sql_util.safe(season),
        )
    )


def _refresh_roster_current_profiles(league_id, team_id, season, rows):
    for row in rows:
        condition = {
            "source_namespace": SOURCE_NAMESPACE,
            "leagueID": int(league_id),
            "teamID": int(team_id),
            "season": season,
            "playerID": row["playerID"],
        }
        current = _roster_payload(row)
        for key in [
            "captured_at", "source_state_valid_at", "source_url_or_operation", "collection_status", "has_data",
        ]:
            current.pop(key, None)
        existing = sql_util.select_table_dicts("lq_team_roster_current", ["playerID", "playerPic"], condition)
        if existing:
            sql_util.upData("lq_team_roster_current", _player_profile_update_payload(current, existing[0]), condition)


def _sync_player_team_relations(rows, league_id, team_id, season, captured_at, recorded_at, source_state_valid_at,
                                source_url):
    current_player_ids = {int(row["playerID"]) for row in rows if row.get("playerID") is not None}
    inserted = 0
    updated = 0
    reactivated = 0

    for player_id in sorted(current_player_ids):
        source_entity_id = _player_team_relation_source_id(player_id, team_id, league_id, season)
        condition = {
            "source_namespace": SOURCE_NAMESPACE,
            "source_entity_id": source_entity_id,
        }
        existing = sql_util.select_table_dicts(
            "lq_player_team_competition_relation",
            ["relationStatus", "validFrom"],
            condition,
        )
        row = {
            "source_namespace": SOURCE_NAMESPACE,
            "source_entity_id": source_entity_id,
            "playerID": int(player_id),
            "teamID": int(team_id),
            "leagueID": int(league_id),
            "season": season or "",
            "validFrom": captured_at,
            "validTo": None,
            "relationStatus": "active",
            "captured_at": captured_at,
            "recorded_at": recorded_at,
            "updated_at": recorded_at,
            "source_state_valid_at": source_state_valid_at,
            "source_url_or_operation": source_url,
            "collection_status": "success",
            "has_data": 1,
        }
        if existing:
            update_row = _update_payload(row)
            if existing[0].get("relationStatus") == "active":
                if existing[0].get("validFrom") is not None:
                    update_row.pop("validFrom", None)
            else:
                reactivated += 1
            sql_util.upData("lq_player_team_competition_relation", update_row, condition)
            updated += 1
        else:
            sql_util.insertData("lq_player_team_competition_relation", row)
            inserted += 1

    inactive = _deactivate_missing_player_team_relations(
        current_player_ids,
        league_id,
        team_id,
        season,
        captured_at,
        recorded_at,
        source_state_valid_at,
        source_url,
    )
    return {
        "active": len(current_player_ids),
        "inserted": inserted,
        "updated": updated,
        "reactivated": reactivated,
        "inactive": inactive,
    }


def _deactivate_missing_player_team_relations(current_player_ids, league_id, team_id, season, captured_at,
                                              recorded_at, source_state_valid_at, source_url):
    sql = (
        "SELECT source_entity_id,playerID FROM `lq_player_team_competition_relation` "
        "WHERE source_namespace='{0}' AND leagueID={1} AND teamID={2} AND season='{3}' "
        "AND relationStatus='active'"
    ).format(
        sql_util.safe(SOURCE_NAMESPACE),
        int(league_id),
        int(team_id),
        sql_util.safe(season or ""),
    )
    active_rows = sql_util.select_dicts(sql)
    inactive = 0
    for row in active_rows:
        player_id = int(row["playerID"])
        if player_id in current_player_ids:
            continue
        sql_util.upData(
            "lq_player_team_competition_relation",
            {
                "relationStatus": "inactive",
                "validTo": captured_at,
                "captured_at": captured_at,
                "updated_at": recorded_at,
                "source_state_valid_at": source_state_valid_at,
                "source_url_or_operation": source_url,
                "collection_status": "success",
                "has_data": 0,
            },
            {
                "source_namespace": SOURCE_NAMESPACE,
                "source_entity_id": row["source_entity_id"],
            },
        )
        inactive += 1
    return inactive


def _player_team_relation_source_id(player_id, team_id, league_id, season):
    return "{0}:{1}:{2}:{3}".format(int(player_id), int(team_id), int(league_id), season or "")


def _roster_payload(row):
    return {
        key: row.get(key)
        for key in [
            "source_namespace", "leagueID", "teamID", "season", "playerID", "source_entity_id", "playerName",
            "playerNameTrad", "playerNameEn", "shortName", "shortNameTrad", "shortNameEn", "shirtNumber",
            "position", "playerPic", "playerPic_url", "player_url", "birthDate", "height", "weight",
            "experience", "contractUntil", "annualSalary", "annualSalaryCurrency", "annualSalaryDisplay",
            "nationality", "nationalityTrad", "nationalityEn", "draftInfo",
            "rawData", "rosterStatus", "captured_at", "source_state_valid_at", "source_url_or_operation",
            "collection_status", "has_data",
        ]
    }


def _latest_success_batch(league_id, team_id, season):
    rows = sql_util.select_dicts(
        "SELECT snapshot_batch_id,roster_hash FROM lq_team_roster_snapshot_batch "
        "WHERE source_namespace='{0}' AND leagueID={1} AND teamID={2} AND season='{3}' "
        "AND collection_status='success' ORDER BY captured_at DESC LIMIT 1".format(
            SOURCE_NAMESPACE,
            int(league_id),
            int(team_id),
            sql_util.safe(season),
        )
    )
    return rows[0] if rows else None


def _current_has_scope(league_id, team_id, season):
    rows = sql_util.select(
        "SELECT COUNT(*) FROM lq_team_roster_current "
        "WHERE source_namespace='{0}' AND leagueID={1} AND teamID={2} AND season='{3}'".format(
            SOURCE_NAMESPACE,
            int(league_id),
            int(team_id),
            sql_util.safe(season),
        )
    )
    return len(rows) > 0 and int(rows[0][0]) > 0


def _record_roster_failure(team):
    now = _now()
    league_id = int(team.get("leagueID") or 0)
    team_id = int(team["ID"])
    season = ""
    snapshot_batch_id = _snapshot_batch_id(league_id, team_id, season, now, "failed")
    row = {
        "snapshot_batch_id": snapshot_batch_id,
        "source_namespace": SOURCE_NAMESPACE,
        "leagueID": league_id,
        "teamID": team_id,
        "season": season,
        "captured_at": now,
        "recorded_at": now,
        "updated_at": now,
        "source_url_or_operation": urljoin(lqconfig_qt.lanqurl, "/cn/Team/Lineup.aspx?TeamID={0}".format(team_id)),
        "collection_status": "failed",
        "has_data": 0,
        "changed_from_previous": 0,
    }
    sql_util.insertData("lq_team_roster_snapshot_batch", row)


def _roster_hash(rows):
    normalized = [
        {
            "playerID": row.get("playerID"),
            "shirtNumber": row.get("shirtNumber"),
            "position": row.get("position"),
            "rosterStatus": row.get("rosterStatus"),
            "contractUntil": row.get("contractUntil"),
            "annualSalary": row.get("annualSalary"),
        }
        for row in sorted(rows, key=lambda item: int(item.get("playerID") or 0))
    ]
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _snapshot_batch_id(league_id, team_id, season, captured_at, roster_hash):
    timestamp = str(captured_at).replace("-", "").replace(":", "").replace(" ", "")
    return "titan_basketball_roster_{0}_{1}_{2}_{3}_{4}".format(
        timestamp,
        int(league_id),
        int(team_id),
        str(season or "").replace("-", ""),
        str(roster_hash or "")[:12],
    )


def _date_or_none(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text


def _annual_salary_unit(league_id, annual_salary):
    if not annual_salary:
        return None, None
    if int(league_id) in USD_SALARY_LEAGUE_IDS:
        return "USD", "{0}万美元".format(annual_salary)
    return None, None


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _player_profile_update_payload(row, existing):
    payload = _update_payload(row)
    existing_pic = str(existing.get("playerPic") or "")
    if row.get("playerPic") is None and re.fullmatch(r"\d+(\.\d+)?", existing_pic):
        payload["playerPic"] = None
        payload["playerPic_url"] = None
    return payload
