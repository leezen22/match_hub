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

# lq_schedule.technical_f / textlive_f
# 0 = pending: 未采集
# 1 = refreshable: 已采到数据，但非终局比赛仍允许继续刷新
# 2 = done: 已完成，不再采集；是否有实体数据看 *_has_data
ENRICHMENT_FLAG_PENDING = 0
ENRICHMENT_FLAG_REFRESHABLE = 1
ENRICHMENT_FLAG_DONE = 2

# Realtime enrichment league ids.
# Directly edit this list when you want the default enrichment task to focus on
# high-priority leagues. Less important leagues can be updated later with
# `enrichment-pending --all-leagues` or `enrichment-pending --league-ids 2,5,7`.
REALTIME_ENRICHMENT_LEAGUE_IDS = (
    2,  # leagueId=2
    1,  # leagueId=1
    # 5,  # leagueId=5
    # 7,  # leagueId=7
)

# Realtime basic information league ids.
# Used by basic-info / roster-info when no --league-id is provided.
REALTIME_BASIC_INFO_LEAGUE_IDS = (
    2,  # leagueId=2
    1,  # leagueId=1
    # 5,  # leagueId=5
    # 7,  # leagueId=7
)


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

    summary = {
        "matches": 0,
        "missing": 0,
        "partscore": 0,
        "asian": 0,
        "total": 0,
        "details": 0,
        "enrichment": 0,
        "skipped_idle": 0,
    }
    for matchId in scheduleIdArr:
        schedulesql = "SELECT scheduleID, leagueId,matchState,matchTime,partscore_f,asianodds_f,totalodds_f," \
                      "homeScore1,homeScore2,homeScore3,homeScore4,awayScore1,awayScore2,awayScore3,awayScore4," \
                      "technical_f,textlive_f FROM `lq_schedule`" \
                      " WHERE matchState>=-1 and scheduleId = {0} order by matchTime ASC ".format(matchId)
        scheduleMatchList = sql_util.select_rows(schedulesql)
        if len(scheduleMatchList) == 0:
            summary["missing"] += 1
            print("比赛不存在或状态不在更新范围，跳过: " + str(matchId))
            continue

        summary["matches"] += 1
        match = scheduleMatchList[0]
        match_state = match[2]
        match_time = match[3]
        partscore_f = match[4]
        asianodds_f = match[5]
        totalodds_f = match[6]
        score_parts = match[7:15]
        technical_f = match[15]
        textlive_f = match[16]
        did_work = False

        if _should_update_part_score(match_state, match_time, partscore_f, score_parts):
            up_score_batch([matchId])
            summary["partscore"] += 1
            did_work = True
        else:
            print("小节比分未到更新时间或已完成，跳过: " + str(matchId))

        if _is_pending_flag(asianodds_f, pending_values=(0, 1, 4)):
            upAsianOddsBymid(matchId, asianodds_f)
            summary["asian"] += 1
            did_work = True
        else:
            print("亚盘赔率已完成，跳过: " + str(matchId))

        if _is_pending_flag(totalodds_f, pending_values=(0, 1, 4)):
            upTotalOddsBymid(matchId, totalodds_f)
            summary["total"] += 1
            did_work = True
        else:
            print("大小分赔率已完成，跳过: " + str(matchId))

        if _has_pending_2in1_details(matchId):
            up_2in1Details_by_match(matchId, 8, 3)
            up_2in1Details_by_match(matchId, 3, 3)
            summary["details"] += 1
            did_work = True
        else:
            print("赔率变化详情已完成或无赔率记录，跳过: " + str(matchId))

        if _should_update_enrichment(match_state, technical_f, textlive_f):
            update_match_enrichment(matchId)
            summary["enrichment"] += 1
            did_work = True
        else:
            print("技术统计/事件无需更新，跳过: {0}, reason={1}".format(
                matchId,
                _enrichment_skip_reason(match_state, technical_f, textlive_f),
            ))

        if not did_work:
            summary["skipped_idle"] += 1

    print("比赛数据更新汇总: {0}".format(summary))
    return summary


def _is_pending_flag(value, pending_values=(0, 1)):
    try:
        return int(value) in pending_values
    except Exception:
        return True


def _has_pending_2in1_details(schedule_id):
    from utils import sql_util

    rows = sql_util.select_rows(
        """
        SELECT 1
        FROM lq_totalodds AS tot
        LEFT JOIN lq_AsianOdds AS asian
          ON asian.companyId=tot.companyId AND asian.matchId=tot.matchId
        LEFT JOIN lq_schedule AS sche
          ON sche.matchId=tot.matchId
        WHERE sche.scheduleID={0}
          AND sche.matchState>=-1
          AND tot.companyId IN (3,8)
          AND (
            tot.finished_pre IN (0,1) OR tot.finished_gun IN (0,1)
            OR asian.finished_pre IN (0,1) OR asian.finished_gun IN (0,1)
          )
        LIMIT 1
        """.format(int(schedule_id))
    )
    return len(rows) > 0


def _should_update_enrichment(match_state, technical_f, textlive_f):
    return (
        _is_terminal_match_state(match_state)
        and (
            _is_pending_flag(technical_f, pending_values=(ENRICHMENT_FLAG_PENDING, ENRICHMENT_FLAG_REFRESHABLE))
            or _is_pending_flag(textlive_f, pending_values=(ENRICHMENT_FLAG_PENDING, ENRICHMENT_FLAG_REFRESHABLE))
        )
    )


def _enrichment_skip_reason(match_state, technical_f, textlive_f):
    if not _is_terminal_match_state(match_state):
        return "not_finished"
    if (
            not _is_pending_flag(technical_f, pending_values=(ENRICHMENT_FLAG_PENDING, ENRICHMENT_FLAG_REFRESHABLE))
            and not _is_pending_flag(textlive_f, pending_values=(ENRICHMENT_FLAG_PENDING, ENRICHMENT_FLAG_REFRESHABLE))):
        return "already_done"
    return "not_required"


def _should_update_part_score(match_state, match_time, partscore_f=None, score_parts=None):
    if match_time is None or match_time > datetime.now():
        return False
    if int(match_state) == -2:
        return False
    if partscore_f != 2:
        return True
    return int(match_state) == -1 and _has_incomplete_part_scores(score_parts)


def _has_incomplete_part_scores(score_parts):
    return score_parts is not None and any(value is None for value in score_parts)

def update_schedule_js():
    from lq.service.schedulejs import upScheJs

    upScheJs()


def update_team_info(league_id, version=None):
    from lq.service.league import LQleague

    return LQleague.updateTeamInfo(league_id, version=version)


def diagnose_titan_team_info_request(league_id=1, version=None, trust_env=True):
    import os
    import re
    from urllib.parse import urljoin

    from config import lqconfig_qt
    from utils.webUtil import WebUtil

    from lq.service.team import TITAN_BASIC_TIMEOUT, TITAN_VERSION_TIMEOUT, _current_titan_version, _team_headers

    proxy_env = {
        key: value
        for key, value in os.environ.items()
        if "proxy" in key.lower()
    }
    page_url = urljoin(lqconfig_qt.lanqurl, "/cn/TeamInfo.aspx?SclassID={0}".format(int(league_id)))
    print("diagnose titan team info request: league_id={0}, version={1}, trust_env={2}".format(
        int(league_id),
        version,
        trust_env,
    ), flush=True)
    print("proxy env: {0}".format(proxy_env), flush=True)
    print("page url: {0}".format(page_url), flush=True)

    resolved_version = version
    page_response = WebUtil.requests_get(
        page_url,
        headers=_team_headers(league_id),
        timeout=TITAN_VERSION_TIMEOUT,
        retry_time=1,
        sleep=False,
        sourceName="diagnose lq team info page",
        trust_env=trust_env,
    )
    print("page response: state={0}, content_len={1}".format(
        page_response[0],
        len(page_response[1] or ""),
    ), flush=True)
    if page_response[0] == 1 and resolved_version is None:
        match = re.search(r"/jsData/teamInfo/ti{0}\.js\?version=([0-9]+)".format(int(league_id)), page_response[1])
        resolved_version = match.group(1) if match else None
        print("resolved version: {0}".format(resolved_version), flush=True)
    if resolved_version is None:
        resolved_version = _current_titan_version()
        print("fallback version: {0}".format(resolved_version), flush=True)

    js_url = urljoin(lqconfig_qt.lanqurl, "/jsData/teamInfo/ti{0}.js".format(int(league_id)))
    if resolved_version:
        js_url = js_url + "?version=" + str(resolved_version)
    print("js url: {0}".format(js_url), flush=True)
    js_response = WebUtil.requests_get(
        js_url,
        headers=_team_headers(league_id),
        timeout=TITAN_BASIC_TIMEOUT,
        retry_time=1,
        sleep=False,
        sourceName="diagnose lq team info js",
        trust_env=trust_env,
    )
    content = js_response[1] or ""
    print("js response: state={0}, content_len={1}, preview={2}".format(
        js_response[0],
        len(content),
        content[:160].replace("\n", " ").replace("\r", " "),
    ), flush=True)
    return {
        "page_state": page_response[0],
        "page_len": len(page_response[1] or ""),
        "js_state": js_response[0],
        "js_len": len(content),
        "js_url": js_url,
        "proxy_env": proxy_env,
    }


def update_league_info(league_id=None, version=None):
    from lq.service.league import LQleague

    return LQleague.updateLeagueInfo(league_id=league_id, version=version)


def update_basic_info(
        league_id=None,
        league_ids=None,
        version=None,
        limit=None,
        offset=0,
        update_roster=True,
        roster_missing_only=False,
        fetch_photos=False,
        mark_legacy=True,
        all_leagues=False):
    result = {"league_info": update_league_info(league_id=league_id, version=version)}
    if league_id is not None:
        result["team_info"] = update_team_info(league_id, version=version)
    elif not all_leagues:
        resolved_league_ids = _resolve_basic_info_league_ids(league_ids)
        team_results = {}
        for resolved_league_id in resolved_league_ids:
            team_results[resolved_league_id] = update_team_info(resolved_league_id, version=version)
        result["team_info"] = team_results
    else:
        result["team_info"] = update_all_team_info(limit=limit)
    if update_roster:
        if league_id is not None or all_leagues:
            result["roster_info"] = update_roster_info(
                league_id=league_id,
                limit=limit,
                offset=offset,
                missing_only=roster_missing_only,
                fetch_photos=fetch_photos,
                all_leagues=all_leagues,
            )
        else:
            roster_results = {}
            for resolved_league_id in _resolve_basic_info_league_ids(league_ids):
                roster_results[resolved_league_id] = update_roster_info(
                    league_id=resolved_league_id,
                    limit=limit,
                    offset=offset,
                    missing_only=roster_missing_only,
                    fetch_photos=fetch_photos,
                )
            result["roster_info"] = roster_results
    result["maintenance"] = update_basic_information_maintenance(mark_legacy=mark_legacy)
    print("basketball basic information update finished: {0}".format(result))
    return result


def update_all_team_info(limit=None):
    from lq.service.league import LQleague
    from lq.service.team import mark_team_info_collection_failed

    leagues = LQleague.getLeaguesOfWebsite()
    if limit is not None:
        leagues = leagues[:int(limit)]

    total = len(leagues)
    success = 0
    failed = 0
    failures = []
    for index, league in enumerate(leagues, start=1):
        league_id = int(league["league_id"])
        try:
            print("start basketball team info update: {0}/{1}, league_id={2}, league_name={3}".format(
                index,
                total,
                league_id,
                league.get("league_name"),
            ))
            update_team_info(league_id)
            success += 1
        except Exception as exc:
            failed += 1
            failures.append({"league_id": league_id, "league_name": league.get("league_name"), "error": str(exc)})
            mark_team_info_collection_failed(league_id, str(exc))

    print("basketball all team info update finished: total={0}, success={1}, failed={2}".format(
        total,
        success,
        failed,
    ))
    return {"total": total, "success": success, "failed": failed, "failures": failures}


def update_roster_info(
        team_id=None,
        version=None,
        limit=None,
        offset=0,
        missing_only=False,
        fetch_photos=True,
        league_id=None,
        league_ids=None,
        all_leagues=False):
    from lq.service.roster import update_all_team_rosters, update_team_roster

    if team_id is not None:
        return update_team_roster(team_id, version=version, fetch_photos=fetch_photos)
    if league_id is None and not all_leagues:
        results = {}
        for resolved_league_id in _resolve_basic_info_league_ids(league_ids):
            results[resolved_league_id] = update_all_team_rosters(
                limit=limit,
                offset=offset,
                missing_only=missing_only,
                fetch_photos=fetch_photos,
                league_id=resolved_league_id,
            )
        return results
    return update_all_team_rosters(
        limit=limit,
        offset=offset,
        missing_only=missing_only,
        fetch_photos=fetch_photos,
        league_id=league_id,
    )


def update_player_photo_info(
        limit=None,
        offset=0,
        missing_only=True,
        workers=1,
        batch_size=20,
        batch_sleep=3,
        retry_failed=False,
        max_batch_failed_ratio=0.5):
    from lq.service.roster import update_player_profile_photos

    return update_player_profile_photos(
        limit=limit,
        offset=offset,
        missing_only=missing_only,
        workers=workers,
        batch_size=batch_size,
        batch_sleep=batch_sleep,
        retry_failed=retry_failed,
        max_batch_failed_ratio=max_batch_failed_ratio,
    )


def update_basic_information_maintenance(mark_legacy=True):
    from lq.service.team import maintain_basic_information_records

    return maintain_basic_information_records(mark_legacy=mark_legacy)


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
    state, content = WebUtil.requests_get(
        url,
        headers=lqconfig_qt.headers,
        timeout=(30, 60),
        retry_time=1,
        sleep=False,
        sourceName="resolve lq season",
    )
    if state != 1 or not content:
        raise ValueError("could not fetch Titan season list for league_id={}".format(league_id))
    parsed = js2pyUtil.js2c(content, source=url, required_names=("arrSeason",))
    if parsed[0] != 1:
        raise ValueError("could not parse Titan season list for league_id={}".format(league_id))
    seasons = [str(item[0]) for item in parsed[1].arrSeason if len(item) > 0]
    if not seasons:
        raise ValueError("Titan season list is empty for league_id={}".format(league_id))
    return seasons[:season_limit]


def _resolve_enrichment_league_ids(league_ids=None):
    if league_ids is None:
        league_ids = REALTIME_ENRICHMENT_LEAGUE_IDS
    if isinstance(league_ids, str):
        league_ids = _parse_league_ids(league_ids)
    return sorted({int(item) for item in league_ids if str(item).strip()})


def _resolve_basic_info_league_ids(league_ids=None):
    if league_ids is None:
        league_ids = REALTIME_BASIC_INFO_LEAGUE_IDS
    if isinstance(league_ids, str):
        league_ids = _parse_league_ids(league_ids)
    return sorted({int(item) for item in league_ids if str(item).strip()})


def _parse_league_ids(value):
    if value is None:
        return []
    return [
        int(item.strip())
        for item in str(value).split(",")
        if item.strip()
    ]


def _league_recent_season_where(league_ids, season_count, sql_util):
    clauses = []
    for resolved_league_id in league_ids:
        season_values = []
        for recent_season in _resolve_recent_seasons(resolved_league_id, season_count=season_count):
            season_values.extend(_season_values(recent_season))
        quoted_seasons = ",".join("'{}'".format(sql_util.safe(value)) for value in sorted(set(season_values)))
        clauses.append("(leagueId={0} and matchSeason in ({1}))".format(resolved_league_id, quoted_seasons))
    return "({})".format(" or ".join(clauses)) if clauses else None


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


def update_score(lookback_days=14):
    from lq.service.partscore import upPartscore

    upPartscore(lookback_days=lookback_days)


def update_odds(lookback_days=14, until_days=1, schedule_ids=None):
    from lq.service.lqodds import LqOddsService

    LqOddsService.upOdds(
        lookback_days=lookback_days,
        until_days=until_days,
        schedule_ids=schedule_ids,
    )


def update_details(lookback_days=14, until_days=1, schedule_ids=None):
    from lq.service.lqodds import LqOddsService

    LqOddsService.up_2in1Details_byCid(
        8, 3, lookback_days=lookback_days, until_days=until_days, schedule_ids=schedule_ids
    )
    LqOddsService.up_2in1Details_byCid(
        3, 3, lookback_days=lookback_days, until_days=until_days, schedule_ids=schedule_ids
    )


def _parse_schedule_ids(value):
    if value is None:
        return None
    values = []
    for item in str(value).split(","):
        text = item.strip()
        if not text or not text.isdigit() or int(text) <= 0:
            raise ValueError("schedule ids must be comma-separated positive integers")
        values.append(int(text))
    return sorted(set(values))


def _is_terminal_match_state(match_state):
    try:
        return int(match_state) in (-1, -4)
    except Exception:
        return False


def _flag_after_collect(result, match_state, has_data):
    if not result.get("request_ok"):
        if _is_terminal_match_state(match_state) and not has_data:
            return ENRICHMENT_FLAG_DONE
        return None
    if not has_data:
        return ENRICHMENT_FLAG_DONE
    return ENRICHMENT_FLAG_DONE if _is_terminal_match_state(match_state) else ENRICHMENT_FLAG_REFRESHABLE


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
    if not force and int(state.get("technical_f") or 0) == ENRICHMENT_FLAG_DONE:
        print("technical update skipped, already finished: scheduleID={0}".format(schedule_id))
        return {"state": 1, "request_ok": True, "skipped": True, "reason": "already_finished"}

    result = Technical.upMatchTechnical(schedule_id)
    resolved_match_state = match_state if match_state is not None else state.get("matchState")
    has_team_data = result.get("periods", 0) > 0
    has_player_data = result.get("players", 0) > 0
    next_flag = _flag_after_collect(result, resolved_match_state, has_team_data or has_player_data)
    if next_flag is not None:
        sql_util.upData('lq_schedule', {
            'technical_f': next_flag,
            'teamTech': 1 if next_flag == ENRICHMENT_FLAG_DONE and has_team_data else 0,
            'teamtechnic_has_data': 1 if has_team_data else 0,
            'playertechnic_has_data': 1 if has_player_data else 0,
        }, {'scheduleID': schedule_id})
    print("technical update finished: scheduleID={0}, request_ok={1}, flag={2}, teams={3}, players={4}, periods={5}".format(
        schedule_id,
        result.get("request_ok"),
        next_flag,
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
    if not force and int(state.get("textlive_f") or 0) == ENRICHMENT_FLAG_DONE:
        print("text live update skipped, already finished: scheduleID={0}".format(schedule_id))
        return {"state": 1, "request_ok": True, "skipped": True, "reason": "already_finished"}

    result = Technical.upMatchTextLive(schedule_id)
    resolved_match_state = match_state if match_state is not None else state.get("matchState")
    has_data = result.get("events", 0) > 0
    next_flag = _flag_after_collect(result, resolved_match_state, has_data)
    if next_flag is not None:
        sql_util.upData('lq_schedule', {
            'textlive_f': next_flag,
            'textlive_has_data': 1 if has_data else 0,
        }, {'scheduleID': schedule_id})
    print("text live update finished: scheduleID={0}, request_ok={1}, flag={2}, events={3}".format(
        schedule_id,
        result.get("request_ok"),
        next_flag,
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
        league_ids=None,
        season=None,
        season_count=None,
        start_match_time=None,
        until_match_time=None,
        limit=None,
        all_leagues=False):
    from utils import sql_util

    columns = {row["Field"] for row in sql_util.select_dicts("SHOW COLUMNS FROM `lq_schedule`")}
    if "technical_f" not in columns or "textlive_f" not in columns:
        print("enrichment pending update skipped, run scripts/migrate_lq_technical_event_tables.py first")
        return []

    sql_util.sqlExecute(
        "UPDATE lq_schedule SET technical_f={done} "
        "WHERE technical_f={refreshable} "
        "AND COALESCE(teamtechnic_has_data,0)=0 "
        "AND COALESCE(playertechnic_has_data,0)=0".format(
            done=ENRICHMENT_FLAG_DONE,
            refreshable=ENRICHMENT_FLAG_REFRESHABLE,
        )
    )
    sql_util.sqlExecute(
        "UPDATE lq_schedule SET textlive_f={done} "
        "WHERE textlive_f={refreshable} "
        "AND COALESCE(textlive_has_data,0)=0".format(
            done=ENRICHMENT_FLAG_DONE,
            refreshable=ENRICHMENT_FLAG_REFRESHABLE,
        )
    )

    should_apply_default_window = start_match_time is None and until_match_time is None and season is None and season_count is None
    if start_match_time is None and should_apply_default_window:
        start_match_time = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    if until_match_time is None and should_apply_default_window:
        until_match_time = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    where = [
        "matchState in(-1,-4)",
        "(technical_f in({pending},{refreshable}) or textlive_f in({pending},{refreshable}))".format(
            pending=ENRICHMENT_FLAG_PENDING,
            refreshable=ENRICHMENT_FLAG_REFRESHABLE,
        ),
    ]
    if start_match_time is not None:
        where.append("matchTime >= '{}'".format(sql_util.safe(str(start_match_time))))
    if until_match_time is not None:
        where.append("matchTime <= '{}'".format(sql_util.safe(str(until_match_time))))
    if league_id is not None:
        where.insert(0, "leagueId={}".format(int(league_id)))
        resolved_league_ids = [int(league_id)]
    elif not all_leagues:
        resolved_league_ids = _resolve_enrichment_league_ids(league_ids)
        if resolved_league_ids:
            where.insert(0, "leagueId in({})".format(",".join(str(item) for item in resolved_league_ids)))
    else:
        resolved_league_ids = []
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
    elif resolved_league_ids and season_count is not None:
        season_where = _league_recent_season_where(resolved_league_ids, season_count, sql_util)
        if season_where is not None:
            where.append(season_where)
    sql = (
        "SELECT scheduleID FROM lq_schedule WHERE {where} "
        "ORDER BY matchTime ASC"
    ).format(where=" and ".join(where))
    if limit is not None:
        sql += " LIMIT {}".format(int(limit))

    rows = sql_util.select_rows(sql)
    schedule_ids = [row[0] for row in rows]
    if len(schedule_ids) == 0:
        print("no pending enrichment matches: league_ids={0}, season={1}, season_count={2}, start_match_time={3}, until_match_time={4}, all_leagues={5}".format(
            resolved_league_ids, season, season_count, start_match_time, until_match_time, all_leagues
        ))
        return []

    print("start pending enrichment update: league_ids={0}, season={1}, season_count={2}, count={3}, start_match_time={4}, until_match_time={5}, all_leagues={6}".format(
        resolved_league_ids, season, season_count, len(schedule_ids), start_match_time, until_match_time, all_leagues
    ))
    for schedule_id in schedule_ids:
        update_match_enrichment(schedule_id)
    print("pending enrichment update finished: count={0}".format(len(schedule_ids)))
    return schedule_ids


def run_all(
        league_id=None,
        season=None,
        season_count=None,
        start_match_time=None,
        until_match_time=None,
        limit=None,
        score_lookback_days=14,
        odds_lookback_days=14,
        odds_until_days=1,
        details_lookback_days=14,
        details_until_days=1):
    update_schedule_js()
    update_schedule()
    update_score(lookback_days=score_lookback_days)
    update_odds(lookback_days=odds_lookback_days, until_days=odds_until_days)
    update_details(lookback_days=details_lookback_days, until_days=details_until_days)


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
            "league-info",
            "team-info",
            "basic-info",
            "roster-info",
            "photo-info",
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
    parser.add_argument(
        "--league-ids",
        help="Comma-separated Titan basketball league/SclassID list, for example 2,5,7.",
    )
    parser.add_argument(
        "--all-leagues",
        action="store_true",
        help="For enrichment-pending, ignore realtime league defaults and scan all leagues.",
    )
    parser.add_argument("--team-id", type=int, help="Titan basketball TeamID.")
    parser.add_argument("--version", help="Titan team-info js version, for example 2026072009.")
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
    parser.add_argument("--offset", type=int, default=0, help="For roster-info/basic-info batch updates, skip this many selected rows.")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="For roster-info, only update teams without active player-team relation rows.",
    )
    parser.add_argument(
        "--skip-photo",
        action="store_true",
        help="For roster-info, skip player detail page photo fetch and only persist core profile/roster/relation data.",
    )
    parser.add_argument(
        "--skip-roster",
        action="store_true",
        help="For basic-info, skip team roster/player profile update after league/team update.",
    )
    parser.add_argument(
        "--with-photos",
        action="store_true",
        help="For basic-info, fetch player detail pages to fill player photos.",
    )
    parser.add_argument(
        "--skip-legacy",
        action="store_true",
        help="For basic-info, do not mark pre-existing null-status league/team rows as legacy.",
    )
    parser.add_argument(
        "--all-photos",
        action="store_true",
        help="For photo-info, refresh all player photos instead of only missing playerPic_url rows.",
    )
    parser.add_argument(
        "--photo-workers",
        type=int,
        default=1,
        help="For photo-info, concurrent player detail page workers. Default: 1.",
    )
    parser.add_argument(
        "--photo-batch-size",
        type=int,
        default=20,
        help="For photo-info, submit this many player requests per batch. Default: 20.",
    )
    parser.add_argument(
        "--photo-batch-sleep",
        type=float,
        default=3,
        help="For photo-info, seconds to sleep between batches. Default: 3.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="For photo-info, include previous failed photo requests. Default skips failed rows.",
    )
    parser.add_argument(
        "--photo-max-batch-failed-ratio",
        type=float,
        default=0.5,
        help="For photo-info, stop early when a batch failure ratio reaches this value. Default: 0.5.",
    )
    parser.add_argument("--schedule-id", type=int, help="Titan basketball scheduleID for single-match enrichment tasks.")
    parser.add_argument(
        "--schedule-ids",
        help="Comma-separated exact-identity-verified scheduleIDs for bounded odds/details updates.",
    )
    parser.add_argument("--force", action="store_true", help="For single-match enrichment tasks, ignore finished flags and collect again.")
    parser.add_argument("--start-time", help="For league data updates, only select matches at or after this matchTime.")
    parser.add_argument("--until-time", help="For score/odds/detail data updates, only select matches at or before this matchTime.")
    parser.add_argument(
        "--score-lookback-days",
        type=int,
        default=14,
        help="For score updates, only look back this many days. Default: 14.",
    )
    parser.add_argument(
        "--odds-lookback-days",
        type=int,
        default=14,
        help="For odds updates, only look back this many days. Default: 14.",
    )
    parser.add_argument(
        "--odds-until-days",
        type=int,
        default=1,
        help="For odds updates, select matches before now plus this many days. Default: 1.",
    )
    parser.add_argument(
        "--details-lookback-days",
        type=int,
        default=14,
        help="For odds detail updates, only look back this many days. Default: 14.",
    )
    parser.add_argument(
        "--details-until-days",
        type=int,
        default=1,
        help="For odds detail updates, select matches before now plus this many days. Default: 1.",
    )
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
            score_lookback_days=args.score_lookback_days,
            odds_lookback_days=args.odds_lookback_days,
            odds_until_days=args.odds_until_days,
            details_lookback_days=args.details_lookback_days,
            details_until_days=args.details_until_days,
        )
    elif args.stage == "schedule-js":
        update_schedule_js()
    elif args.stage == "schedule":
        update_schedule()
    elif args.stage == "score":
        update_score(lookback_days=args.score_lookback_days)
    elif args.stage == "odds":
        update_odds(
            lookback_days=args.odds_lookback_days,
            until_days=args.odds_until_days,
            schedule_ids=_parse_schedule_ids(args.schedule_ids),
        )
    elif args.stage == "details":
        update_details(
            lookback_days=args.details_lookback_days,
            until_days=args.details_until_days,
            schedule_ids=_parse_schedule_ids(args.schedule_ids),
        )
    elif args.stage == "technical":
        if args.schedule_id is None:
            parser.error("technical requires --schedule-id")
        update_match_technical(args.schedule_id, force=args.force)
    elif args.stage == "text-live":
        if args.schedule_id is None:
            parser.error("text-live requires --schedule-id")
        update_match_text_live(args.schedule_id, force=args.force)
    elif args.stage == "league-info":
        update_league_info(league_id=args.league_id, version=args.version)
    elif args.stage == "team-info":
        if args.league_id is None:
            parser.error("team-info requires --league-id")
        update_team_info(args.league_id, version=args.version)
    elif args.stage == "basic-info":
        update_basic_info(
            args.league_id,
            league_ids=args.league_ids,
            version=args.version,
            limit=args.limit,
            offset=args.offset,
            update_roster=not args.skip_roster,
            roster_missing_only=args.missing_only,
            fetch_photos=args.with_photos,
            mark_legacy=not args.skip_legacy,
            all_leagues=args.all_leagues,
        )
    elif args.stage == "roster-info":
        update_roster_info(
            team_id=args.team_id,
            version=args.version,
            limit=args.limit,
            offset=args.offset,
            missing_only=args.missing_only,
            fetch_photos=not args.skip_photo,
            league_id=args.league_id,
            league_ids=args.league_ids,
            all_leagues=args.all_leagues,
        )
    elif args.stage == "photo-info":
        update_player_photo_info(
            limit=args.limit,
            offset=args.offset,
            missing_only=not args.all_photos,
            workers=args.photo_workers,
            batch_size=args.photo_batch_size,
            batch_sleep=args.photo_batch_sleep,
            retry_failed=args.retry_failed,
            max_batch_failed_ratio=args.photo_max_batch_failed_ratio,
        )
    elif args.stage == "enrichment":
        if args.schedule_id is None:
            parser.error("enrichment requires --schedule-id")
        update_match_enrichment(args.schedule_id, force=args.force)
    elif args.stage == "enrichment-pending":
        update_enrichment_pending(
            league_id=args.league_id,
            league_ids=args.league_ids,
            season=args.season,
            season_count=args.season_count,
            start_match_time=args.start_time,
            until_match_time=args.until_time,
            limit=args.limit,
            all_leagues=args.all_leagues,
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
        # Default direct-run path: update match state, score, odds and odds detail data.
        # update_schedule_js()
        # update_schedule()
        update_score(lookback_days=14)
        update_odds(lookback_days=14, until_days=1)
        update_details(lookback_days=14, until_days=1)

        # all_leagues=True

        # Optional enrichment, run when you want technical stats and text-live events.

       
        # update_enrichment_pending()
        # update_enrichment_pending(league_id=2, season_count=3)
         # update_enrichment_pending(all_leagues=True)

        # Optional league/team/player basic information tasks.
        update_basic_info(all_leagues=True)
        update_roster_info(all_leagues=True,missing_only=True, fetch_photos=False)
