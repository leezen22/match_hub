import argparse
import json
import os
import re
import sys
import threading
from datetime import datetime, timedelta
from typing import Any, Tuple, cast

LEAGUE_NAME_ALIASES = {
    "wnba": "WNBA",
    "w.n.b.a": "WNBA",
    "美国女子职业篮球联赛": "WNBA",
    "美国女子篮球职业联赛": "WNBA",
    "美国女篮职业联赛": "WNBA",
    "美国女篮联赛": "WNBA",
    "美职女篮": "WNBA",
    "美國女子職業籃球聯賽": "WNBA",
    "美國女籃職業聯賽": "WNBA",
}


# ------------------------------------------实时维护联赛范围-------------------------------------

# 根据联赛ID和赛季更新小节比分
def up_score_batch(scheduleIdArr):
    from lq.parshtml import part_score
    from utils import sql_util

    updated_count = 0
    skipped_count = 0
    for matchID in scheduleIdArr:
        partdDct = part_score.get_PartScore(matchID)
        if len(partdDct) == 0:
            skipped_count += 1
            print("小节比分无可更新数据，跳过: " + str(matchID))
            continue
        sql_util.upData('lq_schedule', partdDct, {'scheduleID': matchID})
        updated_count += 1
    print("小节比分更新完成: matches={0}, updated={1}, skipped_empty={2}".format(
        scheduleIdArr,
        updated_count,
        skipped_count,
    ))


def up_2in1Details_by_match(scheduleId,companyId, scope):
    from crawler.qt.lq_2in1_detail_crawler import Lq2in1Crawler
    from lq.service.lqodds import LqOddsService
    from utils import sql_util

    # scope = 3
    sql = """SELECT sche.matchId,sche.scheduleId,sche.matchState,sche.matchTime,
            tot.companyId,
            tot.oddsId as total_oddsId ,
            tot.finished_pre as total_finished_pre,
            tot.finished_gun as total_finished_gun,
            asian.oddsId as asian_oddsId,
            asian.finished_pre as asian_finished_pre,
            asian.finished_gun as asian_finished_gun
            FROM lq_totalodds as tot 
            LEFT JOIN lq_AsianOdds as asian
            on asian.companyId = tot.companyId and asian.matchId = tot.matchId
            left JOIN `lq_schedule` as sche 
            on sche.matchId = tot.matchId
            WHERE tot.companyId={1} and (tot.finished_gun in(0,1) or asian.finished_gun in(0,1)) 
            and sche.scheduleId={0}
            and sche.matchState >=-1 order by sche.matchtime ASC
        """.format(scheduleId, companyId)
    results = cast(Tuple[Tuple[Any, ...], ...], sql_util.select_rows(sql))
    size = len(results)
    for item in results:
        print(str(companyId) + "变化记录剩余比赛：" + str(size) + ",最新 ：" + str(item))
        matchId = item[0]
        scheduleId = item[1]
        matchState = item[2]
        matchTime = item[3]
        companyId = item[4]
        total_oddsId = item[5]
        total_finished_pre = item[6]
        total_finished_gun = item[7]
        asian_oddsId = item[8]
        asian_finished_pre = item[9]
        asian_finished_gun = item[10]
        crawler = Lq2in1Crawler(matchId, companyId, scheduleId, asian_oddsId, total_oddsId, matchState, matchTime,
                                asian_finished_pre=asian_finished_pre, asian_finished_gun=asian_finished_gun,
                                total_finished_pre=total_finished_pre, total_finished_gun=total_finished_gun)
        collectData = crawler.qt_web_get(scope=scope)
        threads = []
        if scope != 2:
            if 'asian' in collectData.keys() and collectData['asian']['state'] == 1 and \
                    collectData['asian']['finished_pre'] in (0, 1):
                asian_pre_thread = threading.Thread(target=LqOddsService.up_asianPre_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_pre_thread)
            if 'total' in collectData.keys() and collectData['total']['state'] == 1 and \
                    collectData['total']['finished_pre'] in (0, 1):
                total_pre_thread = threading.Thread(target=LqOddsService.up_totalPre_details,
                                                    args=(collectData['total'],))
                threads.append(total_pre_thread)

        if scope != 1:
            if 'asian' in collectData.keys() and collectData['asian']['state'] == 1 and \
                    collectData['asian']['finished_gun'] in (0, 1):
                asian_gun_thread = threading.Thread(target=LqOddsService.up_asianGun_details,
                                                    args=(collectData['asian'],))
                threads.append(asian_gun_thread)
            if 'total' in collectData.keys() and collectData['total']['state'] == 1 and \
                    collectData['total']['finished_gun'] in (0, 1):
                total_gun_thread = threading.Thread(target=LqOddsService.up_totalGun_details,
                                                    args=(collectData['total'],))
                threads.append(total_gun_thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        size = size - 1


def up_match_data(scheduleIdArr):
    from lq.dao.AsianOddsDao import upAsianOddsBymid
    from lq.dao.TotalScoreDao import upTotalOddsBymid
    from utils import sql_util

    # scheduleIdArr= ['1716532','1756832']
    # now = datetime.now()
    # time = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
    # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    # time2 = "'" + (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    # and leagueID in (1, 2, 5, 7, 14, 15, 19, 25, 20, 28, 22)
    for matchId in scheduleIdArr:
        schedulesql = "SELECT scheduleID, leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                      " WHERE matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        asiansql = "SELECT scheduleID, leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE asianodds_f in(0,1) and matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        totalsql = "SELECT scheduleID,leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
                   " WHERE totalodds_f in(0,1) and matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        # totalsql= {}
        scheduleMatchList = sql_util.select_rows(schedulesql)
        asianMatchList = sql_util.select_rows(asiansql)
        print(scheduleMatchList)
        if len(scheduleMatchList) > 0 and scheduleMatchList[0][4] != 2 and _should_update_part_score(scheduleMatchList[0][2], scheduleMatchList[0][3]):
            up_score_batch([matchId])
        else:
            print("小节比分未到更新时间或已完成，跳过: " + str(matchId))
        print(asianMatchList)
        totalMatchList = sql_util.select_rows(totalsql)
        print(totalMatchList)
        if len(asianMatchList)>0:
            match=asianMatchList[0]
            if match[5] != 2:
                upAsianOddsBymid(match[0], match[5])
        if len(totalMatchList)>0:
            match=totalMatchList[0]
            if match[6] != 2:
                # 比赛ID，更新状态
                upTotalOddsBymid(match[0], match[6])

        up_2in1Details_by_match(matchId, 8, 3)
        up_2in1Details_by_match(matchId, 3, 3)
        if len(scheduleMatchList) > 0 and _is_terminal_match_state(scheduleMatchList[0][2]):
            update_match_enrichment(matchId)
        else:
            print("技术统计/事件未完场，跳过: " + str(matchId))


def _should_update_part_score(match_state, match_time):
    if match_time is None or match_time > datetime.now():
        return False
    return int(match_state) != -2

def update_schedule_js():
    from lq.service.schedulejs import upScheJs

    upScheJs()


def update_schedule():
    from lq.service.schedule import upSchedule

    upSchedule()


def _schedule_work_path(schejs_url):
    from config import lqconfig_qt

    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    return os.path.join(lqconfig_qt.schedule_js_work_dir, str(season), filename)


def update_schedule_by_league_season(league_id, season, kind_type):
    from lq.service.league import LQleague
    from lq.service.schedule import upScheduleByFile
    from lq.service.schedulejs import upScheJS_season

    forced_last_update = datetime(2000, 1, 1)
    schejs_list = LQleague.getScheJS(int(league_id), str(season), int(kind_type))
    if len(schejs_list) == 0:
        print("no schedule js found: league_id={0}, season={1}, kind_type={2}".format(
            league_id, season, kind_type
        ))
        return

    fetched_count = 0
    parsed_count = 0
    for schejs_url, schejs_path in schejs_list:
        last_update_web = upScheJS_season(schejs_url, schejs_path, forced_last_update)
        if last_update_web is None:
            continue

        fetched_count += 1
        work_path = _schedule_work_path(schejs_url)
        if not os.path.exists(work_path):
            print("schedule js work file missing after fetch: {0}".format(work_path))
            continue

        print('start update schedule file: ' + work_path)
        is_updated = upScheduleByFile(work_path, 0, forced_last_update)
        if is_updated:
            parsed_count += 1
            if os.path.exists(work_path):
                os.remove(work_path)

    print("schedule league-season update finished: fetched={0}, parsed={1}".format(
        fetched_count, parsed_count
    ))


def update_schedule_recent_seasons(league_id, kind_type, season_count=3):
    seasons = _resolve_recent_seasons(league_id, season_count=season_count)
    for season in seasons:
        update_schedule_by_league_season(league_id, season, kind_type)
    print("schedule recent seasons update finished: league_id={0}, seasons={1}".format(
        league_id, seasons
    ))


def _season_values(season):
    from lq.formate.model import changeSeason

    raw_season = str(season)
    compact_season = changeSeason(raw_season)
    return sorted({raw_season, compact_season})


def _select_schedule_ids_by_league_season(
        league_id,
        season,
        include_finished=False,
        limit=None,
        start_match_time=None,
        until_match_time=None):
    from utils import sql_util

    season_values = _season_values(season)
    quoted_seasons = ",".join("'{}'".format(sql_util.safe(value)) for value in season_values)
    where = [
        "leagueId={}".format(int(league_id)),
        "matchSeason in ({})".format(quoted_seasons),
    ]
    if start_match_time is not None:
        where.append("matchTime >= '{}'".format(sql_util.safe(str(start_match_time))))
    if until_match_time is not None:
        where.append("matchTime <= '{}'".format(sql_util.safe(str(until_match_time))))
    if not include_finished:
        where.append(
            "("
            "matchState>-1 "
            "or partscore_f in(0,1) "
            "or asianodds_f in(0,1,4) "
            "or totalodds_f in(0,1,4) "
            "or technical_f in(0,1) "
            "or textlive_f in(0,1)"
            ")"
        )
    sql = (
        "SELECT scheduleID FROM lq_schedule WHERE {where} "
        "ORDER BY matchTime ASC"
    ).format(where=" and ".join(where))
    if limit is not None:
        sql += " LIMIT {}".format(int(limit))
    rows = sql_util.select_rows(sql)
    return [str(row[0]) for row in rows]


def update_league_season_data(
        league_id,
        season,
        kind_type,
        include_schedule=True,
        include_finished=False,
        limit=None,
        start_match_time=None,
        until_match_time=None,
        until_days=3):
    if include_schedule:
        update_schedule_by_league_season(league_id, season, kind_type)

    resolved_until_match_time = _resolve_until_match_time(until_match_time, until_days)
    schedule_ids = _select_schedule_ids_by_league_season(
        league_id,
        season,
        include_finished=include_finished,
        limit=limit,
        start_match_time=start_match_time,
        until_match_time=resolved_until_match_time,
    )
    if len(schedule_ids) == 0:
        print("no schedule ids need local db data update: league_id={0}, season={1}, start_match_time={2}, until_match_time={3}".format(
            league_id, season, start_match_time, resolved_until_match_time
        ))
        return

    print("start league-season local db data update: league_id={0}, season={1}, count={2}, start_match_time={3}, until_match_time={4}".format(
        league_id, season, len(schedule_ids), start_match_time, resolved_until_match_time
    ))
    up_match_data(schedule_ids)
    print("league-season local db data update finished: count={0}".format(len(schedule_ids)))


def update_league_recent_seasons_data(
        league_id,
        kind_type,
        include_schedule=True,
        include_finished=False,
        limit=None,
        start_match_time=None,
        until_match_time=None,
        until_days=3,
        season_count=3):
    seasons = _resolve_recent_seasons(league_id, season_count=season_count)
    for season in seasons:
        update_league_season_data(
            league_id,
            season,
            kind_type,
            include_schedule=include_schedule,
            include_finished=include_finished,
            limit=limit,
            start_match_time=start_match_time,
            until_match_time=until_match_time,
            until_days=until_days,
        )
    print("league recent seasons local db data update finished: league_id={0}, seasons={1}".format(
        league_id, seasons
    ))


def parse_natural_update_request(
        request,
        league_id=None,
        season=None,
        kind_type=None,
        action=None,
        include_finished=False,
        limit=None,
        start_match_time=None,
        until_match_time=None,
        until_days=3,
        season_count=3):
    text = str(request or "").strip()
    resolved_league_id = league_id if league_id is not None else _parse_league_id(text)
    requested_season = season or _parse_season(text)
    resolved_season = requested_season
    resolved_action = action or _parse_action(text)
    resolved_kind_type = kind_type if kind_type is not None else _parse_kind_type(text)
    resolved_league = None

    missing = []
    if resolved_league_id is None:
        resolved_league = _resolve_league_from_name(text)
        if resolved_league is not None:
            resolved_league_id = resolved_league["league_id"]
            if kind_type is None and resolved_kind_type is None:
                resolved_kind_type = resolved_league["kind_type"]
        else:
            missing.append("league_id")
    if missing:
        raise ValueError("missing required fields: {}".format(", ".join(missing)))
    if resolved_kind_type is None:
        resolved_league = resolved_league or _resolve_league_by_id(resolved_league_id)
        if resolved_league is None:
            raise ValueError("could not resolve Titan kind_type for league_id={}".format(resolved_league_id))
        resolved_kind_type = resolved_league["kind_type"]
    recent_seasons = _resolve_recent_seasons(resolved_league_id, season_count=season_count)
    if resolved_season is not None:
        _ensure_recent_season_or_error(resolved_league_id, resolved_season, recent_seasons)

    if resolved_action == "schedule":
        stage = "schedule-league-season" if resolved_season is not None else "schedule-recent-seasons"
    else:
        stage = "league-season-data" if resolved_season is not None else "league-recent-seasons-data"
    resolved_until_match_time = None
    if stage in ("league-season-data", "league-recent-seasons-data"):
        resolved_until_match_time = _resolve_until_match_time(until_match_time, until_days)
    command = [
        "lq_update.py",
        stage,
        "--league-id",
        str(resolved_league_id),
        "--kind-type",
        str(resolved_kind_type),
    ]
    if resolved_season is not None:
        command.extend(["--season", str(resolved_season)])
    if stage in ("league-season-data", "league-recent-seasons-data"):
        if _skip_schedule(text):
            command.append("--skip-schedule")
        if include_finished or _include_finished(text):
            command.append("--include-finished")
        if limit is not None:
            command.extend(["--limit", str(limit)])
        if start_match_time is not None:
            command.extend(["--start-time", str(start_match_time)])
        if until_match_time is not None:
            command.extend(["--until-time", str(until_match_time)])
        elif until_days is not None:
            command.extend(["--until-days", str(until_days)])
    if stage in ("schedule-recent-seasons", "league-recent-seasons-data") and season_count is not None:
        command.extend(["--season-count", str(season_count)])

    return {
        "request": text,
        "action": resolved_action,
        "stage": stage,
        "league_id": resolved_league_id,
        "league_name": resolved_league["league_name"] if resolved_league is not None else _resolve_league_name_by_id(resolved_league_id),
        "season": resolved_season,
        "recent_seasons": recent_seasons,
        "season_policy": "only_current_and_previous_2_seasons",
        "kind_type": resolved_kind_type,
        "include_finished": bool(include_finished or _include_finished(text)),
        "skip_schedule": bool(_skip_schedule(text)),
        "limit": limit,
        "season_count": int(season_count),
        "match_time_lower_bound": start_match_time,
        "match_time_upper_bound": resolved_until_match_time,
        "match_time_upper_bound_policy": "current_time_plus_{}_days".format(until_days) if stage == "league-season-data" and until_match_time is None and until_days is not None else None,
        "command": command,
        "will_write_local_db": True,
        "writer_project": "match_hub",
        "boundary": "match_hub parses and executes local DB update requests; reports must still enforce time-boundary consumption.",
    }


def run_natural_update_request(
        request,
        execute=False,
        league_id=None,
        season=None,
        kind_type=None,
        action=None,
        include_finished=False,
        limit=None,
        start_match_time=None,
        until_match_time=None,
        until_days=3,
        season_count=3):
    plan = parse_natural_update_request(
        request,
        league_id=league_id,
        season=season,
        kind_type=kind_type,
        action=action,
        include_finished=include_finished,
        limit=limit,
        start_match_time=start_match_time,
        until_match_time=until_match_time,
        until_days=until_days,
        season_count=season_count,
    )
    if execute:
        if plan["stage"] == "schedule-league-season":
            update_schedule_by_league_season(plan["league_id"], plan["season"], plan["kind_type"])
        elif plan["stage"] == "schedule-recent-seasons":
            update_schedule_recent_seasons(plan["league_id"], plan["kind_type"], season_count=plan["season_count"])
        elif plan["stage"] == "league-season-data":
            update_league_season_data(
                plan["league_id"],
                plan["season"],
                plan["kind_type"],
                include_schedule=not plan["skip_schedule"],
                include_finished=plan["include_finished"],
                limit=plan["limit"],
                start_match_time=plan["match_time_lower_bound"],
                until_match_time=plan["match_time_upper_bound"],
                until_days=None,
            )
        else:
            update_league_recent_seasons_data(
                plan["league_id"],
                plan["kind_type"],
                include_schedule=not plan["skip_schedule"],
                include_finished=plan["include_finished"],
                limit=plan["limit"],
                start_match_time=plan["match_time_lower_bound"],
                until_match_time=plan["match_time_upper_bound"],
                until_days=None,
                season_count=plan["season_count"],
            )
    return plan


def _parse_league_id(text):
    patterns = [
        r"(?:league[-_\s]?id|sclassid|SclassID|联赛\s*id|联赛ID|联赛编号)\s*[:=：]?\s*(\d+)",
        r"(?:联赛|杯赛)\s*(\d{2,6})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _league_name_matches(text, league_name):
    normalized_text = _normalize_league_name(text)
    normalized_name = _normalize_league_name(league_name)
    if not normalized_name:
        return False
    return normalized_name in normalized_text


def _normalize_league_name(value):
    text = str(value or "").lower()
    for token in [
        "更新",
        "赛季",
        "赛程",
        "本地db",
        "本地 db",
        "数据库",
        "落库",
        "数据",
        "联赛",
        "杯赛",
        "比赛",
        "全部",
        "完整",
        " ",
        "\t",
        "\n",
        "：",
        ":",
        "-",
        "_",
    ]:
        text = text.replace(token, "")
    return text


def _resolve_league_from_name(text):
    leagues = _get_leagues_web()
    expanded_text = _expand_league_aliases(text)
    matches = [league for league in leagues if _league_match_length(expanded_text, league) > 0]
    if not matches:
        return None
    matches.sort(key=lambda item: _league_match_length(expanded_text, item), reverse=True)
    return matches[0]


def _resolve_league_name_by_id(league_id):
    resolved = _resolve_league_by_id(league_id)
    if resolved is None:
        return None
    return resolved["league_name"]


def _resolve_league_by_id(league_id):
    if league_id is None:
        return None
    for league in _get_leagues_web():
        if int(league["league_id"]) == int(league_id):
            return league
    return None


def _league_match_length(text, league):
    best_length = 0
    for field in ["league_name", "name_zh_hans", "name_zh_hant", "name_en"]:
        value = league.get(field)
        if isinstance(value, str) and _league_name_matches(text, value):
            best_length = max(best_length, len(_normalize_league_name(value)))
    return best_length


def _get_leagues_web():
    from crawler.qt.lq_league_crawler import LeagueCrawler
    from utils.league_cache import get_cached_leagues

    def fetch_leagues():
        return LeagueCrawler().get_league_metadata_web()

    return get_cached_leagues("basketball", fetch_leagues, validator=_has_basketball_league_seasons)


def _has_basketball_league_seasons(leagues):
    return any(
        isinstance(league.get("seasons"), list)
        and len(league["seasons"]) > 0
        and isinstance(league.get("name_en"), str)
        and league["name_en"] != ""
        for league in leagues
    )


def _expand_league_aliases(text):
    expanded = str(text or "")
    normalized_text = _normalize_league_name(text)
    for alias, canonical in LEAGUE_NAME_ALIASES.items():
        if _normalize_league_name(alias) in normalized_text:
            expanded = "{} {}".format(expanded, canonical)
    return expanded


def _parse_season(text):
    match = re.search(r"(?<!\d)(\d{4}\s*-\s*\d{4}|\d{2}\s*-\s*\d{2})(?!\d)\s*(?:赛季|season)?", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    match = re.search(r"(?:season|赛季)\s*[:=：]?\s*(?<!\d)(\d{4}|\d{2})(?!\d)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(?<!\d)(\d{4}|\d{2})(?!\d)\s*赛季", text)
    if match:
        return match.group(1)
    return None


def _resolve_until_match_time(until_match_time=None, until_days=3):
    if until_match_time is not None:
        return str(until_match_time)
    if until_days is None:
        return None
    return (datetime.now() + timedelta(days=int(until_days))).strftime("%Y-%m-%d %H:%M:%S")


def _resolve_latest_season(league_id):
    return _resolve_recent_seasons(league_id, season_count=1)[0]


def _resolve_recent_seasons(league_id, season_count=3):
    from config import lqconfig_qt
    from utils import js2pyUtil
    from utils.webUtil import WebUtil

    season_limit = int(season_count)
    if season_limit <= 0:
        raise ValueError("season_count must be greater than 0")
    url = lqconfig_qt.seajsWebdir + "sea{}.js".format(int(league_id))
    state, content = WebUtil.requests_get(url, headers=lqconfig_qt.headers, sourceName="resolve lq season")
    if state != 1 or not content:
        raise ValueError("could not fetch Titan season list for league_id={}".format(league_id))
    parsed = js2pyUtil.js2c(content, source=url, required_names=("arrSeason",))
    if parsed[0] != 1:
        raise ValueError("could not parse Titan season list for league_id={}".format(league_id))
    seasons = [str(item[0]) for item in parsed[1].arrSeason if len(item) > 0]
    if not seasons:
        raise ValueError("Titan season list is empty for league_id={}".format(league_id))
    return seasons[:season_limit]


def _ensure_recent_season_or_error(league_id, season, recent_seasons=None):
    recent = recent_seasons or _resolve_recent_seasons(league_id)
    requested_values = set(_season_values(season))
    allowed_values = set()
    for value in recent:
        allowed_values.update(_season_values(value))
    if requested_values.isdisjoint(allowed_values):
        raise ValueError(
            "season {0} is outside allowed range for league_id={1}; allowed recent seasons={2}".format(
                season,
                league_id,
                recent,
            )
        )


def _parse_action(text):
    lowered = text.lower()
    data_words = ["本地db", "本地 db", "数据库", "落库", "全部数据", "完整数据", "比分", "赔率", "详情"]
    if any(word in lowered for word in data_words):
        return "data"
    if "赛程" in text or "schedule" in lowered:
        return "schedule"
    return "data"


def _parse_kind_type(text):
    lowered = text.lower()
    match = re.search(r"(?:kind[-_\s]?type|league[-_\s]?kind|联赛类型|赛程类型)\s*[:=：]?\s*([12])", lowered, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _skip_schedule(text):
    lowered = text.lower()
    return "不更新赛程" in text or "skip schedule" in lowered


def _include_finished(text):
    lowered = text.lower()
    return any(word in lowered for word in ["包含完场", "包括完场", "全量", "include finished", "all finished"])


def update_score():
    from lq.service.partscore import upPartscore

    upPartscore()


def update_odds():
    from lq.service.lqodds import LqOddsService

    LqOddsService.upOdds()


def update_details():
    from lq.service.lqodds import LqOddsService

    LqOddsService.up_2in1Details_byCid(8, 3)
    LqOddsService.up_2in1Details_byCid(3, 3)


def _is_terminal_match_state(match_state):
    try:
        return int(match_state) in (-1, -4)
    except Exception:
        return False


def _flag_after_collect(result, match_state):
    if not result.get("request_ok"):
        return None
    return 2 if _is_terminal_match_state(match_state) else 1


def _match_enrichment_state(schedule_id):
    from utils import sql_util

    rows = sql_util.select_dicts(
        "SELECT scheduleID,matchState,technical_f,textlive_f FROM lq_schedule WHERE scheduleID={0}".format(
            int(schedule_id)
        )
    )
    if len(rows) == 0:
        return None
    return rows[0]


def update_match_technical(schedule_id, force=False, match_state=None):
    from lq.service.technical import Technical
    from utils import sql_util

    state = _match_enrichment_state(schedule_id)
    if state is None:
        print("technical update skipped, match not found: scheduleID={0}".format(schedule_id))
        return {"state": 0, "request_ok": False, "skipped": True, "reason": "match_not_found"}
    if not force and int(state.get("technical_f") or 0) == 2:
        print("technical update skipped, already finished: scheduleID={0}".format(schedule_id))
        return {"state": 1, "request_ok": True, "skipped": True, "reason": "already_finished"}

    result = Technical.upMatchTechnical(schedule_id)
    resolved_match_state = match_state if match_state is not None else state.get("matchState")
    next_flag = _flag_after_collect(result, resolved_match_state)
    if next_flag is not None:
        sql_util.upData('lq_schedule', {
            'technical_f': next_flag,
            'teamTech': 1 if next_flag == 2 and result.get("periods", 0) > 0 else 0,
            'teamtechnic_has_data': 1 if result.get("periods", 0) > 0 else 0,
            'playertechnic_has_data': 1 if result.get("players", 0) > 0 else 0,
        }, {'scheduleID': schedule_id})
    print("technical update finished: scheduleID={0}, teams={1}, players={2}, periods={3}".format(
        schedule_id,
        result.get("teams", 0),
        result.get("players", 0),
        result.get("periods", 0),
    ))
    return result


def update_match_text_live(schedule_id, force=False, match_state=None):
    from lq.service.technical import Technical
    from utils import sql_util

    state = _match_enrichment_state(schedule_id)
    if state is None:
        print("text live update skipped, match not found: scheduleID={0}".format(schedule_id))
        return {"state": 0, "request_ok": False, "skipped": True, "reason": "match_not_found"}
    if not force and int(state.get("textlive_f") or 0) == 2:
        print("text live update skipped, already finished: scheduleID={0}".format(schedule_id))
        return {"state": 1, "request_ok": True, "skipped": True, "reason": "already_finished"}

    result = Technical.upMatchTextLive(schedule_id)
    resolved_match_state = match_state if match_state is not None else state.get("matchState")
    next_flag = _flag_after_collect(result, resolved_match_state)
    if next_flag is not None:
        sql_util.upData('lq_schedule', {
            'textlive_f': next_flag,
            'textlive_has_data': 1 if result.get("events", 0) > 0 else 0,
        }, {'scheduleID': schedule_id})
    print("text live update finished: scheduleID={0}, events={1}".format(
        schedule_id,
        result.get("events", 0),
    ))
    return result


def update_match_enrichment_task(schedule_id, include_technical=True, include_text_live=True, force=False):
    state = _match_enrichment_state(schedule_id)
    if state is None:
        print("enrichment update skipped, match not found: scheduleID={0}".format(schedule_id))
        return {"technical": None, "text_live": None, "skipped": True, "reason": "match_not_found"}

    technical = None
    text_live = None
    if include_technical:
        technical = update_match_technical(schedule_id, force=force, match_state=state.get("matchState"))
    if include_text_live:
        text_live = update_match_text_live(schedule_id, force=force, match_state=state.get("matchState"))
    return {"technical": technical, "text_live": text_live}


def update_match_enrichment(schedule_id, force=False):
    return update_match_enrichment_task(schedule_id, force=force)


def update_enrichment_pending(
        league_id=None,
        season=None,
        season_count=None,
        start_match_time=None,
        until_match_time=None,
        limit=None):
    from utils import sql_util

    columns = {row["Field"] for row in sql_util.select_dicts("SHOW COLUMNS FROM `lq_schedule`")}
    if "technical_f" not in columns or "textlive_f" not in columns:
        print("enrichment pending update skipped, run scripts/migrate_lq_technical_event_tables.py first")
        return []

    should_apply_default_window = start_match_time is None and until_match_time is None and season is None and season_count is None
    if start_match_time is None and should_apply_default_window:
        start_match_time = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    if until_match_time is None and should_apply_default_window:
        until_match_time = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    where = [
        "matchState in(-1,-4)",
        "(technical_f in(0,1) or textlive_f in(0,1))",
    ]
    if start_match_time is not None:
        where.append("matchTime >= '{}'".format(sql_util.safe(str(start_match_time))))
    if until_match_time is not None:
        where.append("matchTime <= '{}'".format(sql_util.safe(str(until_match_time))))
    if league_id is not None:
        where.insert(0, "leagueId={}".format(int(league_id)))
    if season is not None:
        season_values = _season_values(season)
        quoted_seasons = ",".join("'{}'".format(sql_util.safe(value)) for value in season_values)
        where.append("matchSeason in ({})".format(quoted_seasons))
    elif league_id is not None and season_count is not None:
        season_values = []
        for recent_season in _resolve_recent_seasons(league_id, season_count=season_count):
            season_values.extend(_season_values(recent_season))
        quoted_seasons = ",".join("'{}'".format(sql_util.safe(value)) for value in sorted(set(season_values)))
        where.append("matchSeason in ({})".format(quoted_seasons))
    sql = (
        "SELECT scheduleID FROM lq_schedule WHERE {where} "
        "ORDER BY matchTime ASC"
    ).format(where=" and ".join(where))
    if limit is not None:
        sql += " LIMIT {}".format(int(limit))

    rows = sql_util.select_rows(sql)
    schedule_ids = [row[0] for row in rows]
    if len(schedule_ids) == 0:
        print("no pending enrichment matches: league_id={0}, season={1}, season_count={2}, start_match_time={3}, until_match_time={4}".format(
            league_id, season, season_count, start_match_time, until_match_time
        ))
        return []

    print("start pending enrichment update: league_id={0}, season={1}, season_count={2}, count={3}, start_match_time={4}, until_match_time={5}".format(
        league_id, season, season_count, len(schedule_ids), start_match_time, until_match_time
    ))
    for schedule_id in schedule_ids:
        update_match_enrichment(schedule_id)
    print("pending enrichment update finished: count={0}".format(len(schedule_ids)))
    return schedule_ids


def run_all(league_id=None, season=None, season_count=None, start_match_time=None, until_match_time=None, limit=None):
    update_schedule_js()
    update_schedule()
    update_score()
    update_odds()
    update_details()
    update_enrichment_pending(
        league_id=league_id,
        season=season,
        season_count=season_count,
        start_match_time=start_match_time,
        until_match_time=until_match_time,
        limit=limit,
    )


def main():
    parser = argparse.ArgumentParser(description="Run basketball update tasks.")
    parser.add_argument(
        "stage",
        nargs="?",
        default="all",
        choices=[
            "all",
            "schedule-js",
            "schedule",
            "score",
            "odds",
            "details",
            "technical",
            "text-live",
            "enrichment",
            "enrichment-pending",
            "schedule-local",
            "schedule-league-season",
            "schedule-recent-seasons",
            "league-season-data",
            "league-recent-seasons-data",
            "request",
        ],
        help="Task stage to run. Default: all.",
    )
    parser.add_argument("request_text", nargs="*", help="Natural-language request for the request stage.")
    parser.add_argument("--league-id", type=int, help="Titan basketball league/SclassID.")
    parser.add_argument("--season", help="Season, for example 2026 or 2025-2026.")
    parser.add_argument(
        "--kind-type",
        type=int,
        default=None,
        choices=[1, 2],
        help="Titan league kind: 1=league, 2=cup. If omitted for a league-specific command, resolve from Titan league metadata.",
    )
    parser.add_argument(
        "--skip-schedule",
        action="store_true",
        help="For league-season-data, skip the schedule refresh before selecting local DB rows.",
    )
    parser.add_argument(
        "--include-finished",
        action="store_true",
        help="For league-season-data, include finished rows even when local update flags are closed.",
    )
    parser.add_argument("--limit", type=int, help="Limit selected schedule ids for league-season-data.")
    parser.add_argument("--schedule-id", type=int, help="Titan basketball scheduleID for single-match enrichment tasks.")
    parser.add_argument("--force", action="store_true", help="For single-match enrichment tasks, ignore finished flags and collect again.")
    parser.add_argument("--start-time", help="For league data updates, only select matches at or after this matchTime.")
    parser.add_argument("--until-time", help="For score/odds/detail data updates, only select matches at or before this matchTime.")
    parser.add_argument(
        "--until-days",
        type=int,
        default=3,
        help="For score/odds/detail data updates, default upper bound is now plus this many days. Default: 3.",
    )
    parser.add_argument(
        "--season-count",
        type=int,
        default=3,
        help="For recent-season basketball updates, include current season plus this many total recent seasons. Default: 3.",
    )
    parser.add_argument("--action", choices=["schedule", "data"], help="Override parsed natural-language action.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="For request stage, execute the parsed update. Without this, dry-run only.",
    )
    args = parser.parse_args()

    if args.stage == "all":
        run_all(
            league_id=args.league_id,
            season=args.season,
            season_count=args.season_count,
            start_match_time=args.start_time,
            until_match_time=args.until_time,
            limit=args.limit,
        )
    elif args.stage == "schedule-js":
        update_schedule_js()
    elif args.stage == "schedule":
        update_schedule()
    elif args.stage == "score":
        update_score()
    elif args.stage == "odds":
        update_odds()
    elif args.stage == "details":
        update_details()
    elif args.stage == "technical":
        if args.schedule_id is None:
            parser.error("technical requires --schedule-id")
        update_match_technical(args.schedule_id, force=args.force)
    elif args.stage == "text-live":
        if args.schedule_id is None:
            parser.error("text-live requires --schedule-id")
        update_match_text_live(args.schedule_id, force=args.force)
    elif args.stage == "enrichment":
        if args.schedule_id is None:
            parser.error("enrichment requires --schedule-id")
        update_match_enrichment(args.schedule_id, force=args.force)
    elif args.stage == "enrichment-pending":
        update_enrichment_pending(
            league_id=args.league_id,
            season=args.season,
            season_count=args.season_count,
            start_match_time=args.start_time,
            until_match_time=args.until_time,
            limit=args.limit,
        )
    elif args.stage == "schedule-local":
        from lq.service.schedulejs import upScheJsLocal

        upScheJsLocal()
    elif args.stage == "schedule-league-season":
        if args.league_id is None or args.season is None:
            parser.error("schedule-league-season requires --league-id and --season")
        try:
            _ensure_recent_season_or_error(args.league_id, args.season, _resolve_recent_seasons(args.league_id, args.season_count))
        except ValueError as exc:
            parser.error(str(exc))
        kind_type = args.kind_type if args.kind_type is not None else _resolve_kind_type_by_league_id_or_error(parser, args.league_id)
        update_schedule_by_league_season(args.league_id, args.season, kind_type)
    elif args.stage == "schedule-recent-seasons":
        if args.league_id is None:
            parser.error("schedule-recent-seasons requires --league-id")
        kind_type = args.kind_type if args.kind_type is not None else _resolve_kind_type_by_league_id_or_error(parser, args.league_id)
        update_schedule_recent_seasons(args.league_id, kind_type, season_count=args.season_count)
    elif args.stage == "league-season-data":
        if args.league_id is None or args.season is None:
            parser.error("league-season-data requires --league-id and --season")
        try:
            _ensure_recent_season_or_error(args.league_id, args.season, _resolve_recent_seasons(args.league_id, args.season_count))
        except ValueError as exc:
            parser.error(str(exc))
        kind_type = args.kind_type if args.kind_type is not None else _resolve_kind_type_by_league_id_or_error(parser, args.league_id)
        update_league_season_data(
            args.league_id,
            args.season,
            kind_type,
            include_schedule=not args.skip_schedule,
            include_finished=args.include_finished,
            limit=args.limit,
            start_match_time=args.start_time,
            until_match_time=args.until_time,
            until_days=args.until_days,
        )
    elif args.stage == "league-recent-seasons-data":
        if args.league_id is None:
            parser.error("league-recent-seasons-data requires --league-id")
        kind_type = args.kind_type if args.kind_type is not None else _resolve_kind_type_by_league_id_or_error(parser, args.league_id)
        update_league_recent_seasons_data(
            args.league_id,
            kind_type,
            include_schedule=not args.skip_schedule,
            include_finished=args.include_finished,
            limit=args.limit,
            start_match_time=args.start_time,
            until_match_time=args.until_time,
            until_days=args.until_days,
            season_count=args.season_count,
        )
    elif args.stage == "request":
        request = " ".join(args.request_text).strip()
        if not request:
            parser.error("request stage requires natural-language request text")
        try:
            plan = run_natural_update_request(
                request,
                execute=args.execute,
                league_id=args.league_id,
                season=args.season,
                kind_type=args.kind_type,
                action=args.action,
                include_finished=args.include_finished,
                limit=args.limit,
                start_match_time=args.start_time,
                until_match_time=args.until_time,
                until_days=args.until_days,
                season_count=args.season_count,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps({**plan, "executed": bool(args.execute)}, ensure_ascii=False, indent=2))
    # LQleague.getSchejsPending([1,'NBA',1])

    # scheduleIdArr=['716461','716852','716893','716682','704952','704953','716927','704954','714911','716514','716933','716934','667640']
    # up_match_data(scheduleIdArr)


def _resolve_kind_type_by_league_id_or_error(parser, league_id):
    resolved = _resolve_league_by_id(league_id)
    if resolved is None:
        parser.error("could not resolve Titan kind_type for --league-id {}".format(league_id))
    return resolved["kind_type"]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        from lq.service.schedulejs import upScheJsLocal

        # update_schedule_js()
        # upScheJsLocal()
        # update_schedule()
        # update_score()
        # update_odds()
        # update_details()
        update_enrichment_pending(league_id=2, season_count=3)
