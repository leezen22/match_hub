import re
from datetime import datetime
from urllib.parse import urljoin

from config import lqconfig_qt
from utils import js2pyUtil, sql_util
from utils.webUtil import WebUtil


SOURCE_NAMESPACE = "titan_basketball"
TITAN_IMAGE_BASE_URL = "https://nba.titan007.com"

TEAM_COLUMNS = {
    "ID": "ADD COLUMN `ID` int(11) NOT NULL",
    "leagueID": "ADD COLUMN `leagueID` int(11) NULL",
    "locationID": "ADD COLUMN `locationID` int(11) NULL",
    "matchAddrID": "ADD COLUMN `matchAddrID` int(2) unsigned zerofill NULL",
    "name_f": "ADD COLUMN `name_f` varchar(50) CHARACTER SET utf8 NULL DEFAULT ''",
    "name_js": "ADD COLUMN `name_js` varchar(50) CHARACTER SET utf8 NULL",
    "name_j": "ADD COLUMN `name_j` varchar(50) CHARACTER SET utf8 NULL",
    "name_e": "ADD COLUMN `name_e` varchar(50) CHARACTER SET utf8 NULL",
    "name_ft": "ADD COLUMN `name_ft` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名繁体简称'",
    "name_jt": "ADD COLUMN `name_jt` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名简体短名备用'",
    "name_et": "ADD COLUMN `name_et` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名英文简称'",
    "url": "ADD COLUMN `url` varchar(50) CHARACTER SET utf8 NULL",
    "city": "ADD COLUMN `city` varchar(50) CHARACTER SET utf8 NULL",
    "gymnasium": "ADD COLUMN `gymnasium` varchar(50) CHARACTER SET utf8 NULL",
    "capacity": "ADD COLUMN `capacity` int(11) NULL",
    "joinYear": "ADD COLUMN `joinYear` smallint(6) NULL",
    "drillmaster": "ADD COLUMN `drillmaster` varchar(20) CHARACTER SET utf8 NULL",
    "masterPic": "ADD COLUMN `masterPic` varchar(50) CHARACTER SET utf8 NULL",
    "matserIntro": "ADD COLUMN `matserIntro` varchar(500) CHARACTER SET utf8 NULL",
    "Introduce": "ADD COLUMN `Introduce` varchar(500) CHARACTER SET utf8 NULL",
    "flag": "ADD COLUMN `flag` varchar(50) CHARACTER SET utf8 NULL",
    "flag_url": "ADD COLUMN `flag_url` varchar(255) CHARACTER SET utf8 NULL",
    "source_team_kind": "ADD COLUMN `source_team_kind` varchar(32) CHARACTER SET utf8 NULL",
    "is_placeholder": "ADD COLUMN `is_placeholder` tinyint(4) NULL",
    "formerGrade": "ADD COLUMN `formerGrade` varchar(500) CHARACTER SET utf8 NULL",
    "firstTime": "ADD COLUMN `firstTime` smallint(6) NULL",
    "source_namespace": "ADD COLUMN `source_namespace` varchar(64) CHARACTER SET utf8 NULL",
    "source_entity_id": "ADD COLUMN `source_entity_id` varchar(64) CHARACTER SET utf8 NULL",
    "captured_at": "ADD COLUMN `captured_at` datetime NULL",
    "recorded_at": "ADD COLUMN `recorded_at` datetime NULL",
    "updated_at": "ADD COLUMN `updated_at` datetime NULL",
    "source_state_valid_at": "ADD COLUMN `source_state_valid_at` datetime NULL",
    "source_url_or_operation": "ADD COLUMN `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL",
    "collection_status": "ADD COLUMN `collection_status` varchar(32) CHARACTER SET utf8 NULL",
    "has_data": "ADD COLUMN `has_data` tinyint(4) NULL",
}

TEAM_INDEXES = {
    "PRIMARY": "ALTER TABLE `lq_team` ADD PRIMARY KEY (`ID`)",
    "idx_lq_team_league": "ALTER TABLE `lq_team` ADD KEY `idx_lq_team_league` (`leagueID`)",
}

TEAM_LEAGUE_RELATION_COLUMNS = {
    "source_namespace": "ADD COLUMN `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL",
    "source_entity_id": "ADD COLUMN `source_entity_id` varchar(128) CHARACTER SET utf8 NOT NULL",
    "teamID": "ADD COLUMN `teamID` int(11) NOT NULL",
    "leagueID": "ADD COLUMN `leagueID` int(11) NOT NULL",
    "season": "ADD COLUMN `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT ''",
    "validFrom": "ADD COLUMN `validFrom` datetime NULL",
    "validTo": "ADD COLUMN `validTo` datetime NULL",
    "relationStatus": "ADD COLUMN `relationStatus` varchar(32) CHARACTER SET utf8 NULL",
    "captured_at": "ADD COLUMN `captured_at` datetime NULL",
    "recorded_at": "ADD COLUMN `recorded_at` datetime NULL",
    "updated_at": "ADD COLUMN `updated_at` datetime NULL",
    "source_state_valid_at": "ADD COLUMN `source_state_valid_at` datetime NULL",
    "source_url_or_operation": "ADD COLUMN `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL",
    "collection_status": "ADD COLUMN `collection_status` varchar(32) CHARACTER SET utf8 NULL",
    "has_data": "ADD COLUMN `has_data` tinyint(4) NULL",
}

TEAM_LEAGUE_RELATION_INDEXES = {
    "PRIMARY": "ALTER TABLE `lq_team_league_relation` ADD PRIMARY KEY (`source_namespace`,`source_entity_id`)",
    "idx_lq_team_league_relation_team": (
        "ALTER TABLE `lq_team_league_relation` ADD KEY `idx_lq_team_league_relation_team` (`teamID`)"
    ),
    "idx_lq_team_league_relation_league": (
        "ALTER TABLE `lq_team_league_relation` ADD KEY `idx_lq_team_league_relation_league` (`leagueID`,`season`)"
    ),
}

TEAM_TEXT_COLUMN_DDL = {
    "name_f": "`name_f` varchar(50) CHARACTER SET utf8 NULL DEFAULT '' COMMENT '球队的繁体队名'",
    "name_js": "`name_js` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名简体简称'",
    "name_j": "`name_j` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名简体全称'",
    "name_e": "`name_e` varchar(50) CHARACTER SET utf8 NULL COMMENT '英文名'",
    "name_ft": "`name_ft` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名繁体简称'",
    "name_jt": "`name_jt` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名简体短名备用'",
    "name_et": "`name_et` varchar(50) CHARACTER SET utf8 NULL COMMENT '队名英文简称'",
    "url": "`url` varchar(50) CHARACTER SET utf8 NULL COMMENT '球队英文官方网站'",
    "city": "`city` varchar(50) CHARACTER SET utf8 NULL COMMENT '主场城市'",
    "gymnasium": "`gymnasium` varchar(50) CHARACTER SET utf8 NULL COMMENT '主场所在的体育馆'",
    "drillmaster": "`drillmaster` varchar(20) CHARACTER SET utf8 NULL COMMENT '教练'",
    "masterPic": "`masterPic` varchar(50) CHARACTER SET utf8 NULL COMMENT '目前教练的照片'",
    "matserIntro": "`matserIntro` varchar(500) CHARACTER SET utf8 NULL COMMENT '目前教练的简介'",
    "Introduce": "`Introduce` varchar(500) CHARACTER SET utf8 NULL COMMENT '球队的简要介绍'",
    "flag": "`flag` varchar(50) CHARACTER SET utf8 NULL COMMENT '球队标志的存放地址'",
    "flag_url": "`flag_url` varchar(255) CHARACTER SET utf8 NULL COMMENT '球队标志完整地址'",
    "source_team_kind": "`source_team_kind` varchar(32) CHARACTER SET utf8 NULL COMMENT 'Titan球队类型标记: team/placeholder'",
    "formerGrade": "`formerGrade` varchar(500) CHARACTER SET utf8 NULL COMMENT '球队历史战绩'",
    "source_namespace": "`source_namespace` varchar(64) CHARACTER SET utf8 NULL",
    "source_entity_id": "`source_entity_id` varchar(64) CHARACTER SET utf8 NULL",
    "source_url_or_operation": "`source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL",
    "collection_status": "`collection_status` varchar(32) CHARACTER SET utf8 NULL",
}


def update_team_info(league_id, version=None):
    ensure_lq_team_schema()
    ensure_lq_team_league_relation_schema()
    context, source_url, captured_at = fetch_team_info_context(league_id, version=version)
    arr_league = _to_list(context.arrLeague)
    arr_team = _to_list(context.arrTeam)
    resolved_league_id = int(arr_league[0]) if arr_league else int(league_id)
    season = str(arr_league[4]) if len(arr_league) > 4 else ""
    source_state_valid_at = _parse_datetime(getattr(context, "lastUpdateTime", None))
    recorded_at = _now()
    _upsert_league_from_team_info(arr_league, source_url, captured_at, recorded_at, source_state_valid_at)
    rows = [
        _team_row(team, resolved_league_id, source_url, captured_at, recorded_at, source_state_valid_at)
        for team in arr_team
    ]

    inserted = 0
    updated = 0
    for row in rows:
        result = sql_util.select_table_rows("lq_team", ["ID"], {"ID": row["ID"]})
        if len(result) > 0:
            sql_util.upData("lq_team", _update_payload(row), {"ID": row["ID"]})
            updated += 1
        else:
            sql_util.insertData("lq_team", row)
            inserted += 1
    relation_result = _sync_team_league_relations(
        rows,
        resolved_league_id,
        season,
        source_url,
        captured_at,
        recorded_at,
        source_state_valid_at,
    )

    print("basketball team info update finished: league_id={0}, season={1}, teams={2}, inserted={3}, updated={4}, relation_active={5}, relation_inactive={6}".format(
        resolved_league_id,
        season,
        len(rows),
        inserted,
        updated,
        relation_result["active"],
        relation_result["inactive"],
    ))
    return {
        "league_id": resolved_league_id,
        "season": season,
        "teams": len(rows),
        "inserted": inserted,
        "updated": updated,
        "relation": relation_result,
    }


def update_league_info_from_team_info(league_id, version=None):
    context, source_url, captured_at = fetch_team_info_context(league_id, version=version)
    arr_league = _to_list(context.arrLeague)
    source_state_valid_at = _parse_datetime(getattr(context, "lastUpdateTime", None))
    recorded_at = _now()
    _upsert_league_from_team_info(arr_league, source_url, captured_at, recorded_at, source_state_valid_at)
    print("basketball league detail update finished: league_id={0}, source={1}".format(
        int(arr_league[0]) if arr_league else int(league_id),
        source_url,
    ))
    return {
        "league_id": int(arr_league[0]) if arr_league else int(league_id),
        "source_url_or_operation": source_url,
        "collection_status": "success",
        "has_data": 1 if arr_league else 0,
    }


def mark_team_info_collection_failed(league_id, error, source_url=None):
    ensure_lq_league_logo_schema()
    now = _now()
    url = source_url or urljoin(lqconfig_qt.lanqurl, "/cn/TeamInfo.aspx?SclassID={0}".format(int(league_id)))
    row = {
        "source_namespace": SOURCE_NAMESPACE,
        "source_entity_id": str(int(league_id)),
        "captured_at": now,
        "updated_at": now,
        "source_url_or_operation": url,
        "collection_status": "failed",
        "has_data": 0,
    }
    result = sql_util.select_table_rows("lq_league", ["leagueID"], {"leagueID": int(league_id)})
    if len(result) > 0:
        sql_util.upData("lq_league", row, {"leagueID": int(league_id)})
    else:
        row["leagueID"] = int(league_id)
        sql_util.insertData("lq_league", row)
    print("basketball team info collection failed: league_id={0}, error={1}".format(league_id, error))


def maintain_basic_information_records(mark_legacy=True):
    from lq.service.league import ensure_basic_information_schema

    ensure_basic_information_schema()
    asset_result = backfill_basic_information_asset_urls()
    legacy_result = mark_legacy_basic_information() if mark_legacy else {"league_legacy": 0, "team_legacy": 0}
    summary = summarize_basic_information_status()
    result = {
        "asset_url_backfill": asset_result,
        "legacy_mark": legacy_result,
        "summary": summary,
    }
    print("basketball basic information maintenance finished: {0}".format(result))
    return result


def backfill_basic_information_asset_urls():
    league_logo = _execute_counted(
        "UPDATE lq_league SET logo_url=CONCAT('{0}', logo), updated_at='{1}' "
        "WHERE logo IS NOT NULL AND logo<>'' AND (logo_url IS NULL OR logo_url='') "
        "AND logo NOT LIKE 'http://%' AND logo NOT LIKE 'https://%'".format(
            TITAN_IMAGE_BASE_URL,
            _now(),
        )
    )
    team_flag = _execute_counted(
        "UPDATE lq_team SET flag_url=CONCAT('{0}', flag), updated_at='{1}' "
        "WHERE flag IS NOT NULL AND flag<>'' AND (flag_url IS NULL OR flag_url='') "
        "AND flag NOT LIKE 'http://%' AND flag NOT LIKE 'https://%'".format(
            TITAN_IMAGE_BASE_URL,
            _now(),
        )
    )
    player_pic = _execute_counted(
        "UPDATE lq_player_profile SET playerPic_url=CONCAT('{0}', playerPic), updated_at='{1}' "
        "WHERE playerPic IS NOT NULL AND playerPic<>'' AND (playerPic_url IS NULL OR playerPic_url='') "
        "AND playerPic NOT LIKE 'http://%' AND playerPic NOT LIKE 'https://%'".format(
            TITAN_IMAGE_BASE_URL,
            _now(),
        )
    )
    return {
        "league_logo_url": league_logo,
        "team_flag_url": team_flag,
        "player_pic_url": player_pic,
    }


def mark_legacy_basic_information():
    now = _now()
    league_legacy = _execute_counted(
        "UPDATE lq_league SET "
        "source_namespace='{source_namespace}', "
        "source_entity_id=CAST(leagueID AS CHAR), "
        "updated_at='{now}', "
        "source_url_or_operation='legacy:lq_league', "
        "collection_status='legacy', "
        "has_data=1 "
        "WHERE collection_status IS NULL AND leagueID IS NOT NULL".format(
            source_namespace=SOURCE_NAMESPACE,
            now=now,
        )
    )
    team_legacy = _execute_counted(
        "UPDATE lq_team SET "
        "source_namespace='{source_namespace}', "
        "source_entity_id=CAST(ID AS CHAR), "
        "updated_at='{now}', "
        "source_url_or_operation='legacy:lq_team', "
        "collection_status='legacy', "
        "has_data=1 "
        "WHERE collection_status IS NULL AND ID IS NOT NULL".format(
            source_namespace=SOURCE_NAMESPACE,
            now=now,
        )
    )
    return {
        "league_legacy": league_legacy,
        "team_legacy": team_legacy,
    }


def summarize_basic_information_status():
    return {
        "league_status": _group_counts("lq_league", "collection_status"),
        "team_status": _group_counts("lq_team", "collection_status"),
        "player_status": _group_counts("lq_player_profile", "collection_status"),
        "player_photo_status": _group_counts("lq_player_profile", "photo_collection_status"),
        "roster_batch_status": _group_counts("lq_team_roster_snapshot_batch", "collection_status"),
        "remaining_roster_teams": _scalar(
            "SELECT count(*) FROM lq_team t WHERE t.collection_status='success' "
            "AND COALESCE(t.is_placeholder,0)=0 "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM lq_team_roster_snapshot_batch b "
            "  WHERE b.teamID=t.ID AND b.collection_status='success'"
            ")"
        ),
        "league_without_logo_url": _scalar(
            "SELECT count(*) FROM lq_league WHERE collection_status='success' "
            "AND (logo_url IS NULL OR logo_url='')"
        ),
        "team_without_flag_url": _scalar(
            "SELECT count(*) FROM lq_team WHERE collection_status='success' "
            "AND COALESCE(is_placeholder,0)=0 AND (flag_url IS NULL OR flag_url='')"
        ),
        "player_without_photo_url": _scalar(
            "SELECT count(*) FROM lq_player_profile WHERE collection_status='success' "
            "AND (playerPic_url IS NULL OR playerPic_url='')"
        ),
    }


def ensure_lq_team_schema():
    if not _table_exists("lq_team"):
        sql_util.sqlExecute(
            "CREATE TABLE `lq_team` (`ID` int(11) NOT NULL, PRIMARY KEY (`ID`)) "
            "ENGINE=InnoDB DEFAULT CHARSET=utf8"
        )

    columns = set(_columns("lq_team"))
    for column, ddl in TEAM_COLUMNS.items():
        if column not in columns:
            print("add lq_team.{0}".format(column))
            sql_util.sqlExecute("ALTER TABLE `lq_team` {0}".format(ddl))

    column_charsets = _column_charsets("lq_team")
    for column, ddl in TEAM_TEXT_COLUMN_DDL.items():
        if column in column_charsets and column_charsets[column] not in ("utf8", "utf8mb3", "utf8mb4"):
            print("modify lq_team.{0} charset utf8".format(column))
            sql_util.sqlExecute("ALTER TABLE `lq_team` MODIFY COLUMN {0}".format(ddl))

    indexes = set(_indexes("lq_team"))
    for index_name, ddl in TEAM_INDEXES.items():
        if index_name not in indexes:
            print("add lq_team index {0}".format(index_name))
            sql_util.sqlExecute(ddl)


def ensure_lq_team_league_relation_schema():
    if not _table_exists("lq_team_league_relation"):
        sql_util.sqlExecute(
            """
            CREATE TABLE `lq_team_league_relation` (
              `source_namespace` varchar(64) CHARACTER SET utf8 NOT NULL,
              `source_entity_id` varchar(128) CHARACTER SET utf8 NOT NULL,
              `teamID` int(11) NOT NULL,
              `leagueID` int(11) NOT NULL,
              `season` varchar(20) CHARACTER SET utf8 NOT NULL DEFAULT '',
              `validFrom` datetime NULL,
              `validTo` datetime NULL,
              `relationStatus` varchar(32) CHARACTER SET utf8 NULL,
              `captured_at` datetime NULL,
              `recorded_at` datetime NULL,
              `updated_at` datetime NULL,
              `source_state_valid_at` datetime NULL,
              `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL,
              `collection_status` varchar(32) CHARACTER SET utf8 NULL,
              `has_data` tinyint(4) NULL,
              PRIMARY KEY (`source_namespace`,`source_entity_id`),
              KEY `idx_lq_team_league_relation_team` (`teamID`),
              KEY `idx_lq_team_league_relation_league` (`leagueID`,`season`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8
            """
        )
        return

    columns = set(_columns("lq_team_league_relation"))
    for column, ddl in TEAM_LEAGUE_RELATION_COLUMNS.items():
        if column not in columns:
            print("add lq_team_league_relation.{0}".format(column))
            sql_util.sqlExecute("ALTER TABLE `lq_team_league_relation` {0}".format(ddl))

    indexes = set(_indexes("lq_team_league_relation"))
    for index_name, ddl in TEAM_LEAGUE_RELATION_INDEXES.items():
        if index_name not in indexes:
            print("add lq_team_league_relation index {0}".format(index_name))
            sql_util.sqlExecute(ddl)


def fetch_team_info_context(league_id, version=None):
    team_js, source_url, captured_at = fetch_team_info_js(league_id, version=version)
    result = js2pyUtil.js2c(team_js, source=source_url, required_names=("arrLeague", "arrTeam"))
    if result[0] != 1:
        raise ValueError("could not parse basketball team info js for league_id={0}".format(league_id))
    return result[1], source_url, captured_at


def ensure_lq_league_logo_schema():
    columns = {row[0] for row in sql_util.select("SHOW COLUMNS FROM `lq_league`")}
    if "logo" not in columns:
        print("add lq_league.logo")
        sql_util.sqlExecute("ALTER TABLE `lq_league` ADD COLUMN `logo` varchar(255) CHARACTER SET utf8 NULL")
    if "logo_url" not in columns:
        print("add lq_league.logo_url")
        sql_util.sqlExecute("ALTER TABLE `lq_league` ADD COLUMN `logo_url` varchar(255) CHARACTER SET utf8 NULL")


def fetch_team_info_js(league_id, version=None):
    captured_at = _now()
    if version is None:
        version = _resolve_team_info_version(league_id)
    url = urljoin(lqconfig_qt.lanqurl, "/jsData/teamInfo/ti{0}.js".format(int(league_id)))
    if version:
        url = url + "?version=" + str(version)
    response = WebUtil.requests_get(
        url,
        headers=_team_headers(league_id),
        timeout=20,
        retry_time=3,
        sourceName="lq team info",
    )
    if response[0] != 1:
        raise ValueError("could not fetch basketball team info js: {0}".format(url))
    return response[1], url, captured_at


def _resolve_team_info_version(league_id):
    url = urljoin(lqconfig_qt.lanqurl, "/cn/TeamInfo.aspx?SclassID={0}".format(int(league_id)))
    response = WebUtil.requests_get(
        url,
        headers=_team_headers(league_id),
        timeout=20,
        retry_time=3,
        sourceName="lq team info page",
    )
    if response[0] != 1:
        return None
    match = re.search(r"/jsData/teamInfo/ti{0}\.js\?version=([0-9]+)".format(int(league_id)), response[1])
    return match.group(1) if match else None


def _team_headers(league_id):
    headers = dict(lqconfig_qt.headers)
    headers["Referer"] = urljoin(lqconfig_qt.lanqurl, "/cn/TeamInfo.aspx?SclassID={0}".format(int(league_id)))
    headers["Accept"] = "*/*"
    return headers


def _team_row(team, league_id, source_url, captured_at, recorded_at, source_state_valid_at):
    team_id = _int_or_none(team[0])
    flag = _value(team, 9)
    source_team_kind = _source_team_kind(team)
    return {
        "ID": team_id,
        "leagueID": int(league_id),
        "name_j": _value(team, 1),
        "name_f": _value(team, 2),
        "name_e": _value(team, 3),
        "name_js": _value(team, 4),
        "name_ft": _value(team, 5),
        "name_et": _value(team, 6),
        "locationID": _int_or_none(_value(team, 7)),
        "matchAddrID": _int_or_none(_value(team, 8)),
        "flag": flag,
        "flag_url": _asset_url(flag),
        "source_team_kind": source_team_kind,
        "is_placeholder": 1 if source_team_kind == "placeholder" else 0,
        "source_namespace": SOURCE_NAMESPACE,
        "source_entity_id": str(team_id),
        "captured_at": captured_at,
        "recorded_at": recorded_at,
        "updated_at": recorded_at,
        "source_state_valid_at": source_state_valid_at,
        "source_url_or_operation": source_url,
        "collection_status": "success",
        "has_data": 1,
    }


def _source_team_kind(team):
    names = [
        _value(team, index)
        for index in (1, 2, 3, 4, 5, 6)
        if _value(team, index)
    ]
    text = " ".join(str(name) for name in names)
    if re.search(r"(胜者|勝者|败者|敗者|待定|Winner|Loser|\\bTBD\\b)", text, flags=re.IGNORECASE):
        return "placeholder"
    return "team"


def _sync_team_league_relations(rows, league_id, season, source_url, captured_at, recorded_at, source_state_valid_at):
    current_team_ids = {int(row["ID"]) for row in rows if row.get("ID") is not None}
    inserted = 0
    updated = 0
    reactivated = 0

    for team_id in sorted(current_team_ids):
        source_entity_id = _team_league_relation_source_id(team_id, league_id, season)
        condition = {
            "source_namespace": SOURCE_NAMESPACE,
            "source_entity_id": source_entity_id,
        }
        existing = sql_util.select_table_dicts(
            "lq_team_league_relation",
            ["relationStatus", "validFrom"],
            condition,
        )
        row = {
            "source_namespace": SOURCE_NAMESPACE,
            "source_entity_id": source_entity_id,
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
            sql_util.upData("lq_team_league_relation", update_row, condition)
            updated += 1
        else:
            sql_util.insertData("lq_team_league_relation", row)
            inserted += 1

    inactive = _deactivate_missing_team_league_relations(
        current_team_ids,
        league_id,
        season,
        captured_at,
        recorded_at,
        source_state_valid_at,
        source_url,
    )
    return {
        "active": len(current_team_ids),
        "inserted": inserted,
        "updated": updated,
        "reactivated": reactivated,
        "inactive": inactive,
    }


def _deactivate_missing_team_league_relations(current_team_ids, league_id, season, captured_at, recorded_at,
                                              source_state_valid_at, source_url):
    sql = (
        "SELECT source_entity_id,teamID FROM `lq_team_league_relation` "
        "WHERE source_namespace='{0}' AND leagueID={1} AND season='{2}' AND relationStatus='active'"
    ).format(
        sql_util.safe(SOURCE_NAMESPACE),
        int(league_id),
        sql_util.safe(season or ""),
    )
    active_rows = sql_util.select_dicts(sql)
    inactive = 0
    for row in active_rows:
        team_id = int(row["teamID"])
        if team_id in current_team_ids:
            continue
        sql_util.upData(
            "lq_team_league_relation",
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


def _team_league_relation_source_id(team_id, league_id, season):
    return "{0}:{1}:{2}".format(int(team_id), int(league_id), season or "")


def _upsert_league_from_team_info(arr_league, source_url, captured_at, recorded_at, source_state_valid_at):
    if not arr_league:
        return
    ensure_lq_league_logo_schema()
    league_id = _int_or_none(_value(arr_league, 0))
    if league_id is None:
        return
    logo = _value(arr_league, 6)
    row = {
        "leagueID": league_id,
        "name_cn": _value(arr_league, 1),
        "name_tw": _value(arr_league, 2),
        "name_en": _value(arr_league, 3),
        "currMatchSeason": _short_season(_value(arr_league, 4)),
        "color": _value(arr_league, 5),
        "logo": logo,
        "logo_url": _asset_url(logo),
        "name_sh": _value(arr_league, 7),
        "name_twsh": _value(arr_league, 8),
        "name_ensh": _value(arr_league, 9),
        "leagueKind": _int_or_none(_value(arr_league, 10)),
        "source_namespace": SOURCE_NAMESPACE,
        "source_entity_id": str(league_id),
        "captured_at": captured_at,
        "recorded_at": recorded_at,
        "updated_at": recorded_at,
        "source_state_valid_at": source_state_valid_at,
        "source_url_or_operation": source_url,
        "collection_status": "success",
        "has_data": 1,
    }
    result = sql_util.select_table_rows("lq_league", ["leagueID"], {"leagueID": league_id})
    if len(result) > 0:
        sql_util.upData("lq_league", _update_payload(row), {"leagueID": league_id})
    else:
        sql_util.insertData("lq_league", row)


def _update_payload(row):
    return {
        key: value
        for key, value in row.items()
        if value is not None and key not in ("recorded_at",)
    }


def _table_exists(table):
    result = sql_util.select("SHOW TABLES LIKE '{0}'".format(sql_util.safe(table)))
    return len(result) > 0


def _columns(table):
    return [row[0] for row in sql_util.select("SHOW COLUMNS FROM `{0}`".format(table))]


def _column_charsets(table):
    sql = (
        "SELECT COLUMN_NAME, CHARACTER_SET_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='{0}'"
    ).format(sql_util.safe(table))
    return {row[0]: row[1] for row in sql_util.select(sql)}


def _indexes(table):
    return [row[2] for row in sql_util.select("SHOW INDEX FROM `{0}`".format(table))]


def _execute_counted(sql):
    db = None
    try:
        db = sql_util.reConndb()
        cursor = db.cursor()
        cursor.execute(sql)
        db.commit()
        return cursor.rowcount
    except Exception as exc:
        if db:
            db.rollback()
        print("SQL_COUNTED_EXECUTE_FAILED sql={0} error={1}".format(sql, exc))
        return 0
    finally:
        if db:
            db.close()


def _group_counts(table, column):
    rows = sql_util.select_dicts(
        "SELECT COALESCE({0}, 'NULL') AS status, count(*) AS count "
        "FROM {1} GROUP BY COALESCE({0}, 'NULL') ORDER BY status".format(column, table)
    )
    return {row["status"]: int(row["count"]) for row in rows}


def _scalar(sql):
    rows = sql_util.select_rows(sql)
    return int(rows[0][0]) if rows else 0


def _to_list(value):
    if hasattr(value, "to_list"):
        return value.to_list()
    return list(value)


def _value(items, index):
    if index >= len(items):
        return None
    value = items[index]
    if value == "":
        return None
    return value


def _int_or_none(value):
    if value is None or value == "":
        return None
    return int(value)


def _short_season(value):
    text = str(value or "").strip()
    match = re.match(r"^(\d{4})-(\d{4})$", text)
    if match:
        return "{0}-{1}".format(match.group(1)[2:], match.group(2)[2:])
    return text if text else None


def _asset_url(path):
    text = str(path or "").strip()
    if not text:
        return None
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return urljoin(TITAN_IMAGE_BASE_URL, text)


def _parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
