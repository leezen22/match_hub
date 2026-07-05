import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

from config import zqconfig_qt
from utils import fileUtil

DEFAULT_ODDS_START_TIME = '2026-06-05 00:00:00'

LEAGUE_NAME_ALIASES = {
    "世亚预": "亚洲预选",
    "世界杯亚洲区预选赛": "亚洲预选",
    "世界杯亚洲区预选": "亚洲预选",
    "亚洲世界杯预选赛": "亚洲预选",
    "亚洲预选赛": "亚洲预选",
    "世欧预": "欧洲预选",
    "世界杯欧洲区预选赛": "欧洲预选",
}


def _pending_schedule_files():
    files = []
    if os.path.isdir(zqconfig_qt.schedule_js_work_dir):
        files.extend(fileUtil.dirFiles(zqconfig_qt.schedule_js_work_dir, []))
    return files


def update_schedule_js():
    from zq.service.schedulejs import upScheJS

    upScheJS()


def update_schedule_js_local():
    from zq.service.schedulejs import upScheJS_local

    upScheJS_local()


def update_schedule():
    from zq.service.schedule import upSchedule

    while 1:
        upSchedule()
        files = _pending_schedule_files()
        if len(files)<5:
            print(files)
        if len(files) == 0:
            break


def update_score():
    from zq.service.schedule import upMatchScore

    upMatchScore()


def update_odds(start_time=DEFAULT_ODDS_START_TIME):
    from zq.service.asian_odds import AsianOddsZq
    from zq.service.total_odds import TotalOddsZq
    from zq.service.zq_up_odds import upAsianTotalDetails

    TotalOddsZq.up_odds_mobile(start_time)
    AsianOddsZq.up_odds_mobile(start_time)
    TotalOddsZq.up_half_odds_mobile(start_time)
    AsianOddsZq.up_half_odds_mobile(start_time)
    upAsianTotalDetails(3, start_time)
    TotalOddsZq.update_halfgoals(start_time)


def run_all(start_time=DEFAULT_ODDS_START_TIME):
    update_schedule_js()
    update_schedule()
    update_score()
    update_odds(start_time)


def update_schedule_by_league_season(league_id, season, league_type=None, if_have_sub=None):
    from zq.service import schedulejs

    resolved = _resolve_league_by_id(league_id)
    if resolved is not None:
        if league_type is None:
            league_type = resolved["league_type"]
        if if_have_sub is None:
            if_have_sub = resolved["if_have_sub"]
    if league_type is None or if_have_sub is None:
        raise ValueError("could not resolve football league metadata for league_id={}".format(league_id))

    forced_last_update = datetime(2000, 1, 1)
    schejs_list = schedulejs.getSchedulePending(league_id, league_type, season, if_have_sub)
    fetched_count = 0
    parsed_count = 0
    for schejs_url, schejs_path, weburl in schejs_list:
        last_update_web = schedulejs.upScheJS_season(schejs_url, schejs_path, weburl, forced_last_update)
        if last_update_web is None:
            continue
        fetched_count += 1
        work_path = schedulejs._schedule_work_path(schejs_url)
        print("start update football schedule file: " + work_path)
        if schedulejs.upLeagueScheByFile(work_path, 0, forced_last_update):
            parsed_count += 1
            if os.path.exists(work_path):
                os.remove(work_path)
    print("football schedule league-season update finished: fetched={0}, parsed={1}".format(
        fetched_count,
        parsed_count,
    ))


def update_league_season_data(
        league_id,
        season,
        league_type=None,
        if_have_sub=None,
        include_schedule=True,
        include_finished=False,
        limit=None,
        until_match_time=None,
        until_days=3):
    if include_schedule:
        update_schedule_by_league_season(league_id, season, league_type, if_have_sub)

    resolved_until_match_time = _resolve_until_match_time(until_match_time, until_days)
    matches = _select_matches_by_league_season(
        league_id,
        season,
        include_finished=include_finished,
        limit=limit,
        until_match_time=resolved_until_match_time,
    )
    if len(matches) == 0:
        print("no football schedule ids need local db data update: league_id={0}, season={1}, until_match_time={2}".format(
            league_id, season, resolved_until_match_time
        ))
        return
    print("start football league-season local db data update: league_id={0}, season={1}, count={2}, until_match_time={3}".format(
        league_id, season, len(matches), resolved_until_match_time
    ))
    update_match_data(matches)
    print("football league-season local db data update finished: count={0}".format(len(matches)))


def update_match_data(matches):
    from crawler.qt.zq_score_crawler import ScoreCrawler
    from zq.oddsUtil_zq import OddsUtil
    from zq.service.asian_odds import AsianOddsZq
    from zq.service.total_odds import TotalOddsZq
    from utils import sql_util

    for match in matches:
        schedule_id = match[0]
        match_time = match[1]
        match_state = match[2]
        partscore_f = match[7]
        asianodds_f = match[8]
        totalodds_f = match[9]
        print(match)

        if partscore_f != 2 and _should_update_score(match_time):
            score = ScoreCrawler(schedule_id).qt_web_get()
            if len(score) > 0 and score.get("MatchState") != 0:
                if match_state in (-1, -10):
                    score["partscore_f"] = 2
                sql_util.upData("zq_schedule", score, {"ScheduleID": schedule_id})
            else:
                print("足球比分无可更新数据，跳过: " + str(schedule_id))
        else:
            print("足球比分未到更新时间或已完成，跳过: " + str(schedule_id))

        if asianodds_f != 2:
            data_asian = AsianOddsZq.get_asian_odds(match, None, isproxy=False, proxy=None)
            print(data_asian)
            if data_asian["state"] == 1:
                OddsUtil.up_asia_odds(schedule_id, asianodds_f, match_state, data_asian["odds"])
            elif match_state in (-1, -10) and data_asian["state"] == 0:
                sql_util.upData("zq_schedule", {"asianodds_f": 4}, {"ScheduleID": schedule_id})

        if totalodds_f != 2:
            data_total = TotalOddsZq.get_total_odds(match, None, isproxy=False, proxy=None)
            print(data_total)
            if data_total["state"] == 1:
                OddsUtil.up_total_dds(schedule_id, totalodds_f, match_state, data_total["odds"])
            elif match_state in (-1, -10) and data_total["state"] == 0:
                sql_util.upData("zq_schedule", {"totalodds_f": 4}, {"ScheduleID": schedule_id})

    _update_football_odds_details(matches, 3)


def parse_natural_update_request(
        request,
        league_id=None,
        season=None,
        league_type=None,
        if_have_sub=None,
        action=None,
        include_finished=False,
        limit=None,
        until_match_time=None,
        until_days=3):
    text = str(request or "").strip()
    resolved_league_id = league_id if league_id is not None else _parse_league_id(text)
    resolved_season = season or _parse_season(text)
    resolved_action = action or _parse_action(text)
    resolved_league_type = league_type
    resolved_if_have_sub = if_have_sub
    resolved_league = None

    if resolved_league_id is None:
        resolved_league = _resolve_league_from_name(text)
        if resolved_league is None:
            raise ValueError("missing required fields: league_id")
        resolved_league_id = resolved_league["league_id"]
    if resolved_league is None:
        resolved_league = _resolve_league_by_id(resolved_league_id)
    if resolved_league is None:
        raise ValueError("could not resolve football league metadata for league_id={}".format(resolved_league_id))
    if resolved_league_type is None:
        resolved_league_type = resolved_league["league_type"]
    if resolved_if_have_sub is None:
        resolved_if_have_sub = resolved_league["if_have_sub"]
    if resolved_season is None:
        resolved_season = resolved_league["seasons"][0]

    stage = "schedule-league-season" if resolved_action == "schedule" else "league-season-data"
    resolved_until_match_time = None
    if stage == "league-season-data":
        resolved_until_match_time = _resolve_until_match_time(until_match_time, until_days)

    command = [
        "zq_update.py",
        stage,
        "--league-id",
        str(resolved_league_id),
        "--season",
        str(resolved_season),
        "--league-type",
        str(resolved_league_type),
        "--if-have-sub",
        str(resolved_if_have_sub),
    ]
    if stage == "league-season-data":
        if _skip_schedule(text):
            command.append("--skip-schedule")
        if include_finished or _include_finished(text):
            command.append("--include-finished")
        if limit is not None:
            command.extend(["--limit", str(limit)])
        if until_match_time is not None:
            command.extend(["--until-time", str(until_match_time)])
        elif until_days is not None:
            command.extend(["--until-days", str(until_days)])

    return {
        "request": text,
        "sport": "football",
        "action": resolved_action,
        "stage": stage,
        "league_id": resolved_league_id,
        "league_name": resolved_league["league_name"],
        "season": resolved_season,
        "league_type": resolved_league_type,
        "if_have_sub": resolved_if_have_sub,
        "include_finished": bool(include_finished or _include_finished(text)),
        "skip_schedule": bool(_skip_schedule(text)),
        "limit": limit,
        "match_time_upper_bound": resolved_until_match_time,
        "match_time_upper_bound_policy": "current_time_plus_{}_days".format(until_days) if stage == "league-season-data" and until_match_time is None and until_days is not None else None,
        "command": command,
        "will_write_local_db": True,
        "writer_project": "match_hub",
        "boundary": "match_hub parses and executes football local DB update requests; reports must still enforce time-boundary consumption.",
    }


def run_natural_update_request(
        request,
        execute=False,
        league_id=None,
        season=None,
        league_type=None,
        if_have_sub=None,
        action=None,
        include_finished=False,
        limit=None,
        until_match_time=None,
        until_days=3):
    plan = parse_natural_update_request(
        request,
        league_id=league_id,
        season=season,
        league_type=league_type,
        if_have_sub=if_have_sub,
        action=action,
        include_finished=include_finished,
        limit=limit,
        until_match_time=until_match_time,
        until_days=until_days,
    )
    if execute:
        if plan["stage"] == "schedule-league-season":
            update_schedule_by_league_season(
                plan["league_id"],
                plan["season"],
                plan["league_type"],
                plan["if_have_sub"],
            )
        else:
            update_league_season_data(
                plan["league_id"],
                plan["season"],
                plan["league_type"],
                plan["if_have_sub"],
                include_schedule=not plan["skip_schedule"],
                include_finished=plan["include_finished"],
                limit=plan["limit"],
                until_match_time=plan["match_time_upper_bound"],
                until_days=None,
            )
    return plan


def _select_matches_by_league_season(league_id, season, include_finished=False, limit=None, until_match_time=None):
    from utils import sql_util

    where = [
        "sche.LeagueID={}".format(int(league_id)),
        "sche.MatchSeason='{}'".format(sql_util.safe(str(season))),
    ]
    if until_match_time is not None:
        where.append("sche.MatchTime <= '{}'".format(sql_util.safe(str(until_match_time))))
    if not include_finished:
        where.append(
            "("
            "sche.MatchState>-1 "
            "or sche.partscore_f in(0,1) "
            "or sche.asianodds_f in(0,1,4) "
            "or sche.totalodds_f in(0,1,4)"
            ")"
        )
    sql = (
        "SELECT sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.LeagueID,"
        "sche.SubLeagueID,lea.type,sche.partscore_f,sche.asianodds_f,sche.totalodds_f,"
        "sche.HomeTeam,sche.AwayTeam "
        "FROM zq_schedule AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID=lea.LeagueID "
        "WHERE {where} ORDER BY sche.MatchTime ASC"
    ).format(where=" AND ".join(where))
    if limit is not None:
        sql += " LIMIT {}".format(int(limit))
    return sql_util.select_rows(sql)


def _update_football_odds_details(matches, company_id):
    from crawler.qt.zq_3in1_detail_crawler import DetailCrawler
    from zq.service.asian_odds import AsianOddsZq
    from zq.service.total_odds import TotalOddsZq
    from utils import sql_util

    schedule_ids = [str(match[0]) for match in matches]
    if len(schedule_ids) == 0:
        return
    schedule_id_values = ",".join(schedule_ids)
    sql = (
        "SELECT zt.matchID,zt.scheduleID,zc.matchState,zc.matchTime,zt.companyID,"
        "zt.oddsID as ztoddsID,zt.finished_pre as zt_pre,zt.finished_gun as zt_gun,"
        "za.oddsID as zaoddsID,za.finished_pre as za_pre,za.finished_gun as za_gun "
        "FROM zq_totalscore as zt "
        "LEFT JOIN zq_schedule as zc on zt.scheduleID = zc.scheduleID "
        "LEFT JOIN zq_asianodds as za on za.scheduleID = zt.scheduleID and zt.companyID = za.companyID "
        "WHERE zt.companyID={0} and zt.scheduleID in ({1}) "
        "AND (zt.finished_pre in (0,1) or zt.finished_gun in (0,1,4) or za.finished_pre in (0,1) or za.finished_gun in (0,1)) "
        "ORDER BY zc.matchTime ASC"
    ).format(int(company_id), schedule_id_values)
    results = sql_util.select_rows(sql)
    print("开始更新足球变化记录：{0}".format(len(results)))
    for item in results:
        print(item)
        detail_crawler = DetailCrawler(
            item[4],
            item[0],
            item[1],
            matchState=item[2],
            matchTime=item[3],
            total_oddsId=item[5],
            total_finished_pre=item[6],
            total_finished_gun=item[7],
            asian_oddsId=item[8],
            asian_finished_pre=item[9],
            asian_finished_gun=item[10],
        )
        data = detail_crawler.qt_web_get(3, True, True, False)
        if data["state"] == 1:
            if detail_crawler.asian_oddsId and (
                    detail_crawler.asian_finished_pre in [0, 1]
                    or detail_crawler.asian_finished_gun in [0, 1]):
                AsianOddsZq.up_AsianDetail(data["asian"], 2)
            if detail_crawler.total_oddsId and (
                    detail_crawler.total_finished_pre in [0, 1]
                    or detail_crawler.total_finished_gun in [0, 1]):
                TotalOddsZq.up_totalDetail(data["total"], 2)


def _should_update_score(match_time):
    return match_time is not None and match_time <= datetime.now()


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


def _parse_action(text):
    lowered = text.lower()
    data_words = ["本地db", "本地 db", "数据库", "落库", "全部数据", "完整数据", "比赛信息", "比分", "赔率", "详情"]
    if any(word in lowered for word in data_words):
        return "data"
    if "赛程" in text or "schedule" in lowered:
        return "schedule"
    return "data"


def _skip_schedule(text):
    lowered = text.lower()
    return "不更新赛程" in text or "skip schedule" in lowered


def _include_finished(text):
    lowered = text.lower()
    return any(word in lowered for word in ["包含完场", "包括完场", "全量", "include finished", "all finished"])


def _normalize_league_name(value):
    text = str(value or "").lower()
    for token in [
        "更新",
        "赛季",
        "赛程",
        "比赛信息",
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


def _expand_league_aliases(text):
    expanded = str(text or "")
    normalized_text = _normalize_league_name(text)
    for alias, canonical in LEAGUE_NAME_ALIASES.items():
        if _normalize_league_name(alias) in normalized_text:
            expanded = "{} {}".format(expanded, canonical)
    return expanded


def _league_name_matches(text, league_name):
    normalized_text = _normalize_league_name(text)
    normalized_name = _normalize_league_name(league_name)
    if not normalized_name:
        return False
    return normalized_name in normalized_text


def _resolve_league_from_name(text):
    leagues = _get_leagues_web()
    expanded_text = _expand_league_aliases(text)
    matches = [league for league in leagues if _league_name_matches(expanded_text, league["league_name"])]
    if not matches:
        return None
    matches.sort(key=lambda item: len(_normalize_league_name(item["league_name"])), reverse=True)
    return matches[0]


def _resolve_league_by_id(league_id):
    if league_id is None:
        return None
    for league in _get_leagues_web():
        if int(league["league_id"]) == int(league_id):
            return league
    return None


def _get_leagues_web():
    from utils import js2pyUtil
    from utils.league_cache import get_cached_leagues
    from utils.webUtil import WebUtil

    def fetch_leagues():
        state, content = WebUtil.requests_get(
            zqconfig_qt.ziliao_jsurl,
            headers=zqconfig_qt.headers,
            sourceName="zq league list",
        )
        if state != 1 or not content:
            raise ValueError("could not fetch football league list")
        parsed = js2pyUtil.js2c(content, source=zqconfig_qt.ziliao_jsurl, required_names=("arr",))
        if parsed[0] != 1:
            raise ValueError("could not parse football league list")
        leagues = []
        for country in parsed[1].arr:
            for league in country[4]:
                parts = str(league).split(",")
                if len(parts) < 5:
                    continue
                leagues.append(
                    {
                        "league_id": int(parts[0]),
                        "league_name": str(parts[1]),
                        "league_type": int(parts[2]),
                        "if_have_sub": int(parts[3]),
                        "seasons": [str(item) for item in parts[4:] if str(item) != ""],
                    }
                )
        return leagues

    return get_cached_leagues("football", fetch_leagues)


def main():
    parser = argparse.ArgumentParser(description="Run football update tasks.")
    parser.add_argument(
        "stage",
        nargs="?",
        default="all",
        choices=[
            "all",
            "schedule-js",
            "schedule-js-local",
            "schedule",
            "score",
            "odds",
            "schedule-league-season",
            "league-season-data",
            "request",
        ],
        help="Task stage to run. Default: all.",
    )
    parser.add_argument("request_text", nargs="*", help="Natural-language request for the request stage.")
    parser.add_argument("--league-id", type=int, help="Titan football league/SclassID.")
    parser.add_argument("--season", help="Season, for example 2026 or 2025-2026.")
    parser.add_argument("--league-type", type=int, choices=[1, 2], help="Titan football league type: 1=league, 2=cup.")
    parser.add_argument("--if-have-sub", type=int, choices=[0, 1], help="Titan football sub-league flag.")
    parser.add_argument("--skip-schedule", action="store_true", help="For league-season-data, skip schedule refresh.")
    parser.add_argument("--include-finished", action="store_true", help="For league-season-data, include final rows even when flags are closed.")
    parser.add_argument("--limit", type=int, help="Limit selected schedule ids for league-season-data.")
    parser.add_argument("--until-time", help="For score/odds/detail updates, only select matches at or before this matchTime.")
    parser.add_argument(
        "--until-days",
        type=int,
        default=3,
        help="For score/odds/detail data updates, default upper bound is now plus this many days. Default: 3.",
    )
    parser.add_argument("--action", choices=["schedule", "data"], help="Override parsed natural-language action.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="For request stage, execute the parsed update. Without this, dry-run only.",
    )
    parser.add_argument(
        "--start-time",
        default=DEFAULT_ODDS_START_TIME,
        help="Start time for odds tasks.",
    )
    args = parser.parse_args()

    if args.stage == "all":
        run_all(args.start_time)
    elif args.stage == "schedule-js":
        update_schedule_js()
    elif args.stage == "schedule-js-local":
        update_schedule_js_local()
    elif args.stage == "schedule":
        update_schedule()
    elif args.stage == "score":
        update_score()
    elif args.stage == "odds":
        update_odds(args.start_time)
    elif args.stage == "schedule-league-season":
        if args.league_id is None or args.season is None:
            parser.error("schedule-league-season requires --league-id and --season")
        update_schedule_by_league_season(args.league_id, args.season, args.league_type, args.if_have_sub)
    elif args.stage == "league-season-data":
        if args.league_id is None or args.season is None:
            parser.error("league-season-data requires --league-id and --season")
        update_league_season_data(
            args.league_id,
            args.season,
            args.league_type,
            args.if_have_sub,
            include_schedule=not args.skip_schedule,
            include_finished=args.include_finished,
            limit=args.limit,
            until_match_time=args.until_time,
            until_days=args.until_days,
        )
    elif args.stage == "request":
        request = " ".join(args.request_text).strip()
        if not request:
            parser.error("request stage requires natural-language request text")
        plan = run_natural_update_request(
            request,
            execute=args.execute,
            league_id=args.league_id,
            season=args.season,
            league_type=args.league_type,
            if_have_sub=args.if_have_sub,
            action=args.action,
            include_finished=args.include_finished,
            limit=args.limit,
            until_match_time=args.until_time,
            until_days=args.until_days,
        )
        print(json.dumps({**plan, "executed": bool(args.execute)}, ensure_ascii=False, indent=2))

    # TotalStZq.update_half_st('2026-04-20 00:00:00')
    # TotalStZq.update_st('2026-04-20 00:00:00')
    # TotalStZq.judgeHit()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        update_schedule_js()
        # update_schedule_js_local()
        update_schedule()
        update_score()
        update_odds(DEFAULT_ODDS_START_TIME)
    # TotalStZq.update_st('2026-04-20 00:00:00')
    # TotalStZq.judgeHit()
