from datetime import datetime, timedelta
import os
import traceback
from pathlib import Path

from bs4 import BeautifulSoup

from config import common_config, zqconfig_qt
from utils import fileUtil, js2pyUtil, sql_util
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil
from zq.extract.scheduleJs import getSche
from zq.service import task_state
from zq.service.match import upMatchByOne


ZQ_JS_PREFIX = "var jh = new Object();\n"
_ZQ_SCHETASK_TRACKING_COLUMNS_READY = False

# zq_scheTask.state
# 0 = disabled/error, do not fetch automatically.
# 1 = active, schedule JS may still change.
# 2 = finished, schedule JS is stable enough to skip normal active fetching.
SCHETASK_STATE_DISABLED = 0
SCHETASK_STATE_ACTIVE = 1
SCHETASK_STATE_FINISHED = 2
# Keep completed football schedule files active for 30 days because postponed
# or supplemental matches may be added after the apparent final match.
LEAGUE_SCHEDULE_FINISH_GRACE_DAYS = 30
CUP_SCHEDULE_FINISH_GRACE_DAYS = 30


def _with_zq_prefix(webcontent):
    return ZQ_JS_PREFIX + (webcontent or "").lstrip("\ufeff")


def _get_task_time(task):
    result = sql_util.select_table_rows(
        'zq_note',
        ['ID', 'task', 'lastUpdateTime'],
        {'task': task},
        isDis=True,
    )
    if len(result) == 0:
        return datetime(2000, 1, 1)
    return result[0][2]


def _advance_task_time(task, current_time):
    sql_util.upData('zq_note', {'lastUpdateTime': current_time}, {'task': task})


def _schedule_work_path(schejs_url):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    return os.path.join(zqconfig_qt.schedule_js_work_dir, season, filename)


def _parse_schedule_content(content, source):
    return js2pyUtil.js2c(
        content,
        source=source,
        required_names=("lastUpdateTime", "arrLeague", "arrTeam", "jh", "arrCupKind", "arrSubLeague"),
    )


def upScheJS():
    _ensure_schetask_tracking_columns()
    last_update_local = _get_task_time('schedulejs')
    next_task_time = last_update_local
    headers = dict(zqconfig_qt.headers)
    headers['Referer'] = zqconfig_qt.ziliao
    result = js2pyUtil.jsyWebjs(zqconfig_qt.ziliao_jsurl, headers, required_names=("arr",))
    context = result[1]
    if result[0] == 1 and context != '':
        try:
            countrys = context.arr
            for country in countrys:
                league_list = country[4]
                for league in league_list:
                    leagueinfo = league.split(",")
                    league_id = leagueinfo[0]
                    league_type = leagueinfo[2]
                    if_have_sub = leagueinfo[3]
                    seasons = leagueinfo[4:] if zqconfig_qt.enable_finished_season_backfill else [leagueinfo[4]]
                    for season in seasons:
                        schejs_list = getSchedulePending(league_id, league_type, season, if_have_sub)
                        for schejs_url, schejs_path, weburl in schejs_list:
                            if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, datetime.now()):
                                continue
                            last_update_web = upScheJS_season(
                                schejs_url,
                                schejs_path,
                                weburl,
                                last_update_local,
                            )
                            if last_update_web is not None and last_update_web > next_task_time:
                                next_task_time = last_update_web
        except Exception as e:
            fileUtil.logLine(common_config.exception, ['zq.upScheJS', repr(e), traceback.format_exc()])
            print(e)
            print(traceback.format_exc())
    _advance_task_time('schedulejs', next_task_time)


def upScheJS_local():
    _ensure_schetask_tracking_columns()
    last_update_local = _get_task_time('schedulejs')
    next_task_time = last_update_local
    sql_schejs = (
        "SELECT leagueID,matchSeason,fileName,state FROM zq_schetask "
        "WHERE matchSeason in ('2025', '2026', '2027', '2025-2026', '2026-2027') and state=1"
    )
    result = sql_util.select_rows(sql_schejs)
    for item in result:
        season = item[1]
        filename = item[2]
        league_id = item[0]
        schejs_url = zqconfig_qt.scheWebdir + season + "/" + filename
        schejs_path = zqconfig_qt.schelocaldir + season + "/" + filename
        weburl = zqconfig_qt.league_web_schedir + season + "/" + str(league_id) + ".html"
        if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, datetime.now()):
            continue
        last_update_web = upScheJS_season(schejs_url, schejs_path, weburl, last_update_local)
        if last_update_web is not None and last_update_web > next_task_time:
            next_task_time = last_update_web
    _advance_task_time('schedulejs', next_task_time)


def upActiveScheJS(league_ids=None, all_leagues=False, limit=None, season_count=3, now=None):
    _ensure_schetask_tracking_columns()
    now = now or datetime.now()
    rows = _select_active_schedule_js_rows(
        league_ids=league_ids,
        all_leagues=all_leagues,
        limit=limit,
        season_count=season_count,
        now=now,
    )
    summary = {"selected": len(rows), "success": 0, "updated": 0, "skipped": 0, "failed": 0}
    for row in rows:
        result = upScheJS_season_result(row['scheUrl'], row['schePath'], row.get('webUrl'))
        if result["ok"]:
            summary["success"] += 1
            if result["skipped"]:
                summary["skipped"] += 1
            else:
                summary["updated"] += 1
        else:
            summary["failed"] += 1
    _advance_task_time('schedulejs', getNowTime())
    print("finish active football schedule js update: {0}".format(summary))
    return summary


def normalize_historical_schedule_states(league_ids=None, all_leagues=False, keep_recent_seasons=3, now=None):
    _ensure_schetask_tracking_columns()
    rows = _select_schetask_rows_for_state_maintenance(league_ids=league_ids, all_leagues=all_leagues)
    recent_seasons = _recent_schetask_seasons_by_league(
        sorted({int(row['leagueId']) for row in rows if row.get('leagueId') is not None}),
        keep_recent_seasons,
    )
    summary = {
        "scanned": 0,
        "closed": 0,
        "closed_without_local_schedule": 0,
        "kept_active": 0,
        "skipped_recent": 0,
    }
    closed_keys = []
    for row in rows:
        summary["scanned"] += 1
        allowed_recent = recent_seasons.get(int(row['leagueId']), set())
        if str(row.get('matchSeason')) in allowed_recent:
            summary["skipped_recent"] += 1
            continue
        # A work file is a downloaded snapshot waiting for update_schedule().
        # Never close its task during maintenance, even when its season is old.
        if _schedule_work_file_exists(row):
            summary["kept_active"] += 1
            continue
        closed_keys.append(row['scheKey'])
        summary["closed"] += 1
        if row.get('persistedSourceLastUpdateTime') is None:
            summary["closed_without_local_schedule"] += 1
    _batch_mark_schedule_states(closed_keys, SCHETASK_STATE_FINISHED)
    print("football historical schedule state normalization finished: {0}".format(summary))
    return summary


def upLeagueScheByFile(file_path, isExist, lastUpdateTime):
    isUpdated = False
    if os.path.exists(file_path):
        matchs = getSche(file_path)
        isFinished = 2
        if matchs[0] == 'fail':
            fileUtil.logLine(common_config.zq_extract_fail, [file_path])
            task_state.upScheTaskByFlag(file_path, 0)
        else:
            for match in matchs[1]:
                if match['MatchState'] in [-1, -10]:
                    match['Partscore_F'] = 2
                upMatchByOne(match)
                if match['MatchState'] not in [-1, -10]:
                    isFinished = 1
            if len(matchs[1]) == 0:
                task_state.upScheTaskByFlag(file_path, 0)
            isUpdated = _mark_schedule_file_persisted(file_path, matchs[1])
    return isUpdated


def upLeagueScheJs(league, lastUpdate):
    leagueinfo = league.split(",")
    league_id = leagueinfo[0]
    league_type = leagueinfo[2]
    if_have_sub = leagueinfo[3]
    seasons = leagueinfo[4:] if zqconfig_qt.enable_finished_season_backfill else [leagueinfo[4]]
    for season in seasons:
        schejs_list = getSchedulePending(league_id, league_type, season, if_have_sub)
        for schejs_url, schejs_path, weburl in schejs_list:
            upScheJS_season(schejs_url, schejs_path, weburl, lastUpdate)


def upScheJS_season(schejsUrl, schejsPath, weburl, lastUpdate_local=None):
    result = upScheJS_season_result(schejsUrl, schejsPath, weburl, lastUpdate_local)
    return result["last_update_web"]


def prepare_schedule_js_for_update(schejs_url, schejs_path, weburl, force=False, now=None):
    """Fetch a schedule JS only when it is due, then return the work file to consume."""
    _ensure_schetask_tracking_columns()
    now = now or datetime.now()
    work_path = _schedule_work_path(schejs_url)
    sche_key = _schedule_key_from_url(schejs_url)
    _ensure_schetask_row(sche_key, schejs_url, schejs_path)
    row = _schetask_row(sche_key)

    if os.path.exists(work_path):
        return {"should_parse": True, "work_path": work_path, "reason": "pending_work", "result": None}

    if not force:
        if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
            return {"should_parse": False, "work_path": work_path, "reason": "locally_finished", "result": None}
        if row and int(row.get('state') or 0) == SCHETASK_STATE_FINISHED:
            return {"should_parse": False, "work_path": work_path, "reason": "state_finished", "result": None}
        if row and not _is_schedule_js_due(row, now):
            return {"should_parse": False, "work_path": work_path, "reason": "not_due", "result": None}

    result = upScheJS_season_result(schejs_url, schejs_path, weburl)
    return {
        "should_parse": os.path.exists(work_path),
        "work_path": work_path,
        "reason": "fetched" if result.get("ok") and not result.get("skipped") else "unchanged_or_failed",
        "result": result,
    }


def upScheJS_season_result(schejsUrl, schejsPath, weburl, lastUpdate_local=None):
    _ensure_schetask_tracking_columns()
    headers = dict(zqconfig_qt.headers)
    headers['Referer'] = weburl
    work_path = _schedule_work_path(schejsUrl)
    sche_key = _schedule_key_from_url(schejsUrl)
    source_times = _get_schedule_source_times(sche_key)
    persisted_source_time = source_times["persisted"]
    result = {"ok": False, "skipped": False, "last_update_web": None, "sche_key": sche_key}
    webresponse = WebUtil.requests_get(schejsUrl, headers=headers, sourceName='zq.upSchedulejs')
    if webresponse[0] != 1 or webresponse[1] == '':
        fileUtil.logLine(common_config.httpRequest_fail, ['zq.schedule_js_http_failed', schejsUrl, webresponse[0]])
        _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, repr(webresponse[0]))
        return result

    content = _with_zq_prefix(webresponse[1])
    parse_result = _parse_schedule_content(content, schejsUrl)
    if parse_result[0] != 1:
        fileUtil.logLine(common_config.js2pyweb_e, ['zq.schedule_js_parse_failed', schejsUrl])
        _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, "parse failed")
        return result

    webcontext = parse_result[1]
    last_update_web = datetime.strptime(webcontext.lastUpdateTime, "%Y-%m-%d %H:%M:%S")
    result["ok"] = True
    result["last_update_web"] = last_update_web
    pending_exists = os.path.exists(work_path)
    fetched_source_time = source_times["fetched"]
    if pending_exists and (fetched_source_time is None or last_update_web <= fetched_source_time):
        result["pending"] = True
    elif persisted_source_time is None or last_update_web > persisted_source_time:
        fileUtil.fileWrite(work_path, "w", content)
        if zqconfig_qt.keep_schedule_js_cache and os.path.exists(work_path):
            fileUtil.copyfile(work_path, schejsPath)
        print("update: {0}".format(schejsUrl))
    else:
        result["skipped"] = True
    _mark_schedule_js_success(sche_key, schejsUrl, schejsPath, last_update_web)
    return result


def getSchedulePending(leagueId, Type, season, ifHaveSub, include_finished=False):
    pending_list = []
    seafilename = 'sea' + str(leagueId) + '.js'
    seajs_url = zqconfig_qt.seajsWebdir + seafilename
    condition = {'leagueId': leagueId, 'matchSeason': season}
    keys = ['ID', 'leagueId', 'matchSeason', 'seasonPath', 'state']
    result = sql_util.select_table_rows('zq_seasonTask', keys, condition)
    if len(result) == 0:
        stask = {
            'leagueId': leagueId,
            'matchSeason': season,
            'seasonPath': seafilename,
            'state': 1,
        }
        sql_util.insertData('zq_seasonTask', stask)
    elif result[0][4] == 2 and not zqconfig_qt.enable_finished_season_backfill and not include_finished:
        return pending_list

    pending_list = getMRJSPending(leagueId, season, Type, ifHaveSub, include_finished=include_finished)
    return pending_list


def getMRJSPending(leagueId, season, Type, ifHaveSub, include_finished=False):
    match_result_js_list = []
    pending_js_list = []
    headers = dict(zqconfig_qt.headers)
    if str(Type) == '2':
        schejs_url = zqconfig_qt.scheWebdir + season + "/c" + str(leagueId) + ".js"
        schejs_path = os.path.join(zqconfig_qt.schelocaldir, season, "c" + str(leagueId) + ".js")
        weburl = zqconfig_qt.cup_web_schedir + season + "/" + str(leagueId) + ".html"
        match_result_js_list.append([schejs_url, schejs_path, weburl])
    elif str(Type) == '1' and str(ifHaveSub) == '0':
        weburl = zqconfig_qt.league_web_schedir + season + "/" + str(leagueId) + ".html"
        schejs_url = zqconfig_qt.scheWebdir + season + "/s" + str(leagueId) + ".js"
        schejs_path = os.path.join(zqconfig_qt.schelocaldir, season, "s" + str(leagueId) + ".js")
        match_result_js_list.append([schejs_url, schejs_path, weburl])
    elif str(Type) == '1' and str(ifHaveSub) == '1':
        weburl = zqconfig_qt.sub_web_schedir + season + "/" + str(leagueId) + ".html"
        default_url = zqconfig_qt.sub_web_schedir + season + "/" + str(leagueId) + '.html'
        default_sche = findScheJS(default_url, zqconfig_qt.headers)
        headers['Referer'] = weburl
        if len(default_sche) > 0:
            try:
                url = zqconfig_qt.host_zuqiu + default_sche
                webresponse = WebUtil.requests_get(url, headers=headers, sourceName='getMRJSPending')
                if webresponse[0] == 1 and webresponse[1] != '':
                    content = _with_zq_prefix(webresponse[1])
                    parse_result = _parse_schedule_content(content, url)
                    if parse_result[0] != 1:
                        return pending_js_list
                    context = parse_result[1]
                    subleagues = getSubleague(context)
                    if subleagues:
                        for league in subleagues:
                            sub_id = str(league[0])
                            weburl = zqconfig_qt.sub_web_schedir + season + "/" + str(
                                leagueId) + '_' + sub_id + ".html"
                            schejs_url = zqconfig_qt.scheWebdir + season + "/s" + str(
                                leagueId) + '_' + sub_id + ".js"
                            schejs_path = os.path.join(
                                zqconfig_qt.schelocaldir,
                                season,
                                "s" + str(leagueId) + '_' + sub_id + ".js",
                            )
                            match_result_js_list.append([schejs_url, schejs_path, weburl])
                    else:
                        weburl = zqconfig_qt.league_web_schedir + season + "/" + str(leagueId) + ".html"
                        schejs_url = zqconfig_qt.scheWebdir + season + "/s" + str(leagueId) + ".js"
                        schejs_path = os.path.join(zqconfig_qt.schelocaldir, season, "s" + str(leagueId) + ".js")
                        match_result_js_list.append([schejs_url, schejs_path, weburl])
            except Exception as e:
                fileUtil.logLine(
                    common_config.js2pyweb_e,
                    ['getMRJSPending', url, [leagueId, season, Type, ifHaveSub], repr(e)],
                )

    for match_result_js in match_result_js_list:
        filename = os.path.basename(match_result_js[0].split('?')[0])
        sche_key = str(leagueId) + "#" + season + "#" + filename
        condition = {'scheKey': sche_key}
        keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'state']
        result = sql_util.select_table_rows('zq_scheTask', keys, condition)
        if len(result) > 0 and result[0][7] == 2 and not zqconfig_qt.enable_finished_season_backfill and not include_finished:
            pass
        else:
            if len(result) == 0:
                scheinfo = {
                    'scheKey': sche_key,
                    'leagueId': leagueId,
                    'matchSeason': season,
                    'fileName': filename,
                    'schePath': match_result_js[1],
                    'scheUrl': match_result_js[0],
                    'state': 1,
                }
                sql_util.insertData('zq_scheTask', scheinfo)
            pending_js_list.append(match_result_js)
    return pending_js_list


def findScheJS(pageurl, headers):
    target_src = ''
    try:
        webresponse = WebUtil.requests_get(pageurl, headers=headers, sourceName='zq normal default page')
        if webresponse[0] != 1:
            fileUtil.logLine(common_config.httpRequest_fail, ['zq.findScheJS', pageurl, webresponse[0]])
        elif webresponse[1] != '':
            soup = BeautifulSoup(webresponse[1], 'html.parser')
            for script in soup.find_all('script'):
                url = script.get('src')
                if url and 'jsData/matchResult' in url:
                    target_src = url
    except Exception as e:
        fileUtil.logLine(common_config.exception, ['findScheJS', repr(e), traceback.format_exc()])
        print(e)
        print(traceback.format_exc())
    return target_src


def getSubleague(context):
    try:
        return context.arrSubLeague
    except Exception:
        return None


def _ensure_schetask_tracking_columns():
    global _ZQ_SCHETASK_TRACKING_COLUMNS_READY
    if _ZQ_SCHETASK_TRACKING_COLUMNS_READY:
        return
    columns = {row[0] for row in sql_util.select_rows("SHOW COLUMNS FROM zq_scheTask")}
    ddl = []
    if "sourceLastUpdateTime" not in columns:
        ddl.append("ADD COLUMN sourceLastUpdateTime datetime NULL")
    if "fetchedSourceLastUpdateTime" not in columns:
        ddl.append("ADD COLUMN fetchedSourceLastUpdateTime datetime NULL")
    if "persistedSourceLastUpdateTime" not in columns:
        ddl.append("ADD COLUMN persistedSourceLastUpdateTime datetime NULL")
    if "lastFetchTime" not in columns:
        ddl.append("ADD COLUMN lastFetchTime datetime NULL")
    if "lastSuccessTime" not in columns:
        ddl.append("ADD COLUMN lastSuccessTime datetime NULL")
    if "lastError" not in columns:
        ddl.append("ADD COLUMN lastError text NULL")
    if "failCount" not in columns:
        ddl.append("ADD COLUMN failCount int NOT NULL DEFAULT 0")
    for clause in ddl:
        sql_util.sqlExecute("ALTER TABLE zq_scheTask {0}".format(clause))
    _ZQ_SCHETASK_TRACKING_COLUMNS_READY = True


def _schedule_key_from_url(schejs_url):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    league_id = _league_id_from_filename(filename)
    return "{0}#{1}#{2}".format(league_id, season, filename)


def _league_id_from_filename(filename):
    name = os.path.basename(filename).split('.')[0]
    if name.startswith(('s', 'c')):
        return name.split('_')[0][1:]
    return ''


def _schedule_row_from_url(schejs_url, schejs_path=None, weburl=None):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    sche_key = _schedule_key_from_url(schejs_url)
    league_id = _league_id_from_filename(filename)
    return {
        'scheKey': sche_key,
        'leagueId': int(league_id) if str(league_id).isdigit() else league_id,
        'matchSeason': season,
        'fileName': filename,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
        'webUrl': weburl,
    }


def _ensure_schetask_row(sche_key, schejs_url, schejs_path):
    rows = sql_util.select_rows("SELECT ID FROM zq_scheTask WHERE scheKey='{0}'".format(sql_util.safe(sche_key)))
    if rows:
        return
    league_id, season, filename = sche_key.split('#', 2)
    sql_util.insertData('zq_scheTask', {
        'scheKey': sche_key,
        'leagueId': league_id,
        'matchSeason': season,
        'fileName': filename,
        'schePath': schejs_path,
        'scheUrl': schejs_url,
        'seaPath': 'sea' + str(league_id) + '.js',
        'state': SCHETASK_STATE_ACTIVE,
    })


def _schetask_row(sche_key):
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,state,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime FROM zq_scheTask WHERE scheKey='{0}' LIMIT 1".format(
            sql_util.safe(sche_key)
        )
    )
    if not rows:
        return None
    row = _normalize_active_schedule_row(rows[0])
    _sche_url, _sche_path, weburl = _schedule_url_path_from_row(row)
    row['webUrl'] = weburl
    return row


def _get_schedule_source_times(sche_key):
    rows = sql_util.select_rows(
        "SELECT sourceLastUpdateTime,fetchedSourceLastUpdateTime,persistedSourceLastUpdateTime "
        "FROM zq_scheTask WHERE scheKey='{0}'".format(sql_util.safe(sche_key))
    )
    if not rows:
        return {"fetched": None, "persisted": None}
    return {"fetched": rows[0][1] or rows[0][0], "persisted": rows[0][2]}


def _mark_schedule_js_success(sche_key, schejs_url, schejs_path, source_last_update_time):
    _ensure_schetask_row(sche_key, schejs_url, schejs_path)
    sql_util.upData('zq_scheTask', {
        'sourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'fetchedSourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'lastFetchTime': getNowTime(),
        'lastSuccessTime': getNowTime(),
        'lastError': None,
        'failCount': 0,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
    }, {'scheKey': sche_key})


def _mark_schedule_js_failed(sche_key, schejs_url, schejs_path, error):
    _ensure_schetask_row(sche_key, schejs_url, schejs_path)
    sql_util.sqlExecute(
        "UPDATE zq_scheTask "
        "SET lastFetchTime='{now}', lastError='{error}', failCount=COALESCE(failCount,0)+1, "
        "scheUrl='{url}', schePath='{path}' WHERE scheKey='{sche_key}'".format(
            now=sql_util.safe(getNowTime()),
            error=sql_util.safe(str(error)[:2000]),
            url=sql_util.safe(str(schejs_url)),
            path=sql_util.safe(str(schejs_path)),
            sche_key=sql_util.safe(str(sche_key)),
        )
    )


def _mark_schedule_js_persisted(sche_key, source_last_update_time, state, schejs_url=None, schejs_path=None):
    _ensure_schetask_tracking_columns()
    _ensure_schetask_row(sche_key, schejs_url or '', schejs_path or '')
    payload = {
        'persistedSourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'state': int(state),
    }
    if schejs_url is not None:
        payload['scheUrl'] = schejs_url
    if schejs_path is not None:
        payload['schePath'] = schejs_path
    sql_util.upData('zq_scheTask', payload, {'scheKey': sche_key})


def _mark_schedule_file_persisted(file_path, matches):
    source_time = _schedule_file_source_time(file_path)
    if source_time is None:
        print("football schedule JS persisted marker skipped, source timestamp unavailable: {0}".format(file_path))
        return False
    state = _resolve_schedule_state(matches, file_path)
    _mark_schedule_js_persisted(
        _schedule_key_from_file(file_path),
        source_time,
        state,
        schejs_url=_schedule_url_from_file(file_path),
        schejs_path=file_path,
    )
    return True


def _schedule_file_source_time(file_path):
    try:
        context = js2pyUtil.jsLocjs(file_path)
        value = getattr(context, 'lastUpdateTime', None)
        if value is None or str(value) == '':
            return None
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except Exception as exc:
        print("football schedule JS source timestamp parse failed: {0}, error={1}".format(file_path, exc))
        return None


def _schedule_key_from_file(file_path):
    filename = os.path.basename(file_path)
    season = Path(file_path).parent.name
    return "{0}#{1}#{2}".format(_league_id_from_filename(filename), season, filename)


def _schedule_url_from_file(file_path):
    filename = os.path.basename(file_path)
    season = Path(file_path).parent.name
    return zqconfig_qt.scheWebdir + season + '/' + filename


def _resolve_schedule_state(matches, file_path):
    if not matches:
        return SCHETASK_STATE_ACTIVE
    if any(match.get('MatchState') not in (-1, -10) for match in matches):
        return SCHETASK_STATE_ACTIVE
    max_match_time = _max_match_time(matches)
    if max_match_time is None:
        return SCHETASK_STATE_ACTIVE
    grace_days = _schedule_finish_grace_days(os.path.basename(file_path))
    if max_match_time > datetime.now() - timedelta(days=grace_days):
        return SCHETASK_STATE_ACTIVE
    return SCHETASK_STATE_FINISHED


def _max_match_time(matches):
    values = []
    for match in matches:
        match_time = match.get('MatchTime')
        if not match_time:
            continue
        if isinstance(match_time, datetime):
            values.append(match_time)
        else:
            values.append(datetime.strptime(str(match_time), "%Y-%m-%d %H:%M"))
    return max(values) if values else None


def _schedule_finish_grace_days(filename):
    return CUP_SCHEDULE_FINISH_GRACE_DAYS if str(filename).startswith('c') else LEAGUE_SCHEDULE_FINISH_GRACE_DAYS


def _select_active_schedule_js_rows(league_ids=None, all_leagues=False, limit=None, season_count=3, now=None):
    _ensure_schetask_tracking_columns()
    now = now or datetime.now()
    if not all_leagues and not league_ids:
        return []
    where = ["state={0}".format(SCHETASK_STATE_ACTIVE)]
    if league_ids and not all_leagues:
        where.append("leagueId in({0})".format(",".join(str(int(item)) for item in league_ids)))
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime FROM zq_scheTask WHERE {where} "
        "ORDER BY lastFetchTime ASC, updateTime ASC".format(where=" AND ".join(where))
    )
    rows = [_normalize_active_schedule_row(row) for row in rows]
    rows = _filter_recent_schedule_rows(rows, season_count=season_count)
    rows = _close_locally_finished_schedule_rows(rows, now)
    selected = [row for row in rows if _is_schedule_js_due(row, now)]
    if limit is not None:
        selected = selected[:int(limit)]
    return selected


def _select_schetask_rows_for_state_maintenance(league_ids=None, all_leagues=False):
    _ensure_schetask_tracking_columns()
    if not all_leagues and not league_ids:
        return []
    where = ["state={0}".format(SCHETASK_STATE_ACTIVE)]
    if league_ids and not all_leagues:
        where.append("leagueId in({0})".format(",".join(str(int(item)) for item in league_ids)))
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime FROM zq_scheTask WHERE {where} ORDER BY leagueId,matchSeason,fileName".format(
            where=" AND ".join(where)
        )
    )
    return rows


def _batch_mark_schedule_states(sche_keys, state):
    if not sche_keys:
        return
    db = None
    try:
        db = sql_util.reConndb()
        cursor = db.cursor()
        cursor.executemany(
            "UPDATE zq_scheTask SET state=%s WHERE scheKey=%s",
            [(int(state), str(sche_key)) for sche_key in sche_keys],
        )
        db.commit()
    except Exception as exc:
        if db:
            db.rollback()
        print("SQL_BATCH_UPDATE_FAILED table=zq_scheTask error={0}".format(exc))
    finally:
        if db:
            db.close()


def _filter_recent_schedule_rows(rows, season_count=3):
    if season_count is None:
        return rows
    season_limit = int(season_count)
    if season_limit <= 0 or not rows:
        return []
    league_ids = sorted({int(row['leagueId']) for row in rows if row.get('leagueId') is not None})
    recent_seasons = _recent_schetask_seasons_by_league(league_ids, season_limit)
    return [
        row for row in rows
        if str(row.get('matchSeason')) in recent_seasons.get(int(row['leagueId']), set())
    ]


def _recent_schetask_seasons_by_league(league_ids, season_count):
    """Return the newest task seasons, including seasons not yet persisted locally."""
    if not league_ids:
        return {}
    rows = sql_util.select_rows(
        "SELECT leagueId,matchSeason FROM zq_scheTask "
        "WHERE leagueId IN ({league_ids}) GROUP BY leagueId,matchSeason".format(
            league_ids=",".join(str(int(league_id)) for league_id in league_ids)
        )
    )
    seasons_by_league = {}
    for league_id, season in rows:
        seasons_by_league.setdefault(int(league_id), set()).add(str(season))
    for league_id, seasons in seasons_by_league.items():
        ordered = sorted(seasons, key=_season_sort_key, reverse=True)
        seasons_by_league[league_id] = set(ordered[:int(season_count)])
    return seasons_by_league


def _season_sort_key(season):
    """Sort both single-year and cross-year season labels by their ending year."""
    values = []
    for value in str(season or '').replace('/', '-').split('-'):
        if value.strip().isdigit():
            year = int(value.strip())
            values.append(year + 2000 if year < 100 else year)
    if not values:
        return (0, 0, str(season or ''))
    return (max(values), min(values), str(season or ''))


def _close_locally_finished_schedule_rows(rows, now):
    schedule_stats = _load_schedule_completion_stats()
    active_rows = []
    closed_keys = []
    for row in rows:
        if _is_schedule_row_locally_finished(row, now, schedule_stats):
            closed_keys.append(row['scheKey'])
            continue
        active_rows.append(row)
    _batch_mark_schedule_states(closed_keys, SCHETASK_STATE_FINISHED)
    return active_rows


def _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
    row = _schedule_row_from_url(schejs_url, schejs_path)
    if not _is_schedule_row_locally_finished(row, now):
        return False
    _ensure_schetask_row(row['scheKey'], schejs_url, schejs_path)
    sql_util.upData('zq_scheTask', {
        'state': SCHETASK_STATE_FINISHED,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
    }, {'scheKey': row['scheKey']})
    print("skip finished football schedule js: {0}".format(schejs_url))
    return True


def _is_schedule_row_locally_finished(row, now, schedule_stats=None):
    if _schedule_work_file_exists(row):
        return False
    if schedule_stats is not None:
        stats = schedule_stats.get(_schedule_stats_key(row))
        if stats is None:
            return False
        total, terminal_count, max_match_time = stats
    else:
        total, terminal_count, max_match_time = _query_schedule_completion_stats(row)
    if not total or max_match_time is None:
        return False
    if int(terminal_count or 0) < int(total):
        return False
    return max_match_time <= now - timedelta(days=_schedule_finish_grace_days(row.get('fileName')))


def _schedule_stats_key(row):
    sub_league_id = _sub_league_id_from_filename(row.get('fileName'))
    return (int(row['leagueId']), str(row['matchSeason']), sub_league_id)


def _query_schedule_completion_stats(row):
    where = [
        "leagueID={0}".format(int(row['leagueId'])),
        "matchSeason='{0}'".format(sql_util.safe(str(row['matchSeason']))),
    ]
    sub_league_id = _sub_league_id_from_filename(row.get('fileName'))
    if sub_league_id is not None:
        where.append("subLeagueID={0}".format(int(sub_league_id)))
    rows = sql_util.select_rows(
        "SELECT COUNT(*),SUM(CASE WHEN matchState IN (-1,-10) THEN 1 ELSE 0 END),MAX(matchTime) "
        "FROM zq_schedule WHERE {where}".format(where=" AND ".join(where))
    )
    return rows[0] if rows else (0, 0, None)


def _load_schedule_completion_stats():
    rows = sql_util.select_rows(
        "SELECT leagueID,matchSeason,subLeagueID,COUNT(*),"
        "SUM(CASE WHEN matchState IN (-1,-10) THEN 1 ELSE 0 END),MAX(matchTime) "
        "FROM zq_schedule GROUP BY leagueID,matchSeason,subLeagueID"
    )
    return {
        (int(league_id), str(season), int(sub_league_id) if sub_league_id is not None else None):
        (total, terminal_count, max_match_time)
        for league_id, season, sub_league_id, total, terminal_count, max_match_time in rows
    }


def _sub_league_id_from_filename(filename):
    name = os.path.basename(str(filename or '')).split('.')[0]
    if name.startswith('s') and '_' in name:
        sub_id = name.split('_', 1)[1]
        if sub_id.isdigit():
            return int(sub_id)
    return None


def _schedule_work_file_exists(row):
    season = str(row.get('matchSeason') or '')
    filename = str(row.get('fileName') or '')
    if not season or not filename:
        return False
    return os.path.exists(os.path.join(zqconfig_qt.schedule_js_work_dir, season, filename))


def _is_schedule_js_due(row, now):
    if _schedule_work_file_exists(row):
        return True
    last_fetch_time = row.get('lastFetchTime')
    if last_fetch_time is None:
        return True
    return last_fetch_time <= now - _schedule_fetch_interval(row)


def _schedule_fetch_interval(row):
    fail_count = int(row.get('failCount') or 0)
    if fail_count >= 5:
        return timedelta(hours=2)
    if fail_count == 4:
        return timedelta(hours=1)
    if fail_count == 3:
        return timedelta(minutes=30)
    if fail_count == 2:
        return timedelta(minutes=15)
    if fail_count == 1:
        return timedelta(minutes=5)
    return timedelta(minutes=10)


def _normalize_active_schedule_row(row):
    sche_url, sche_path, weburl = _schedule_url_path_from_row(row)
    if row.get('scheUrl') != sche_url or row.get('schePath') != sche_path:
        sql_util.upData('zq_scheTask', {'scheUrl': sche_url, 'schePath': sche_path}, {'scheKey': row['scheKey']})
        row = dict(row)
        row['scheUrl'] = sche_url
        row['schePath'] = sche_path
    row['webUrl'] = weburl
    return row


def _schedule_url_path_from_row(row):
    season = str(row.get('matchSeason') or '')
    filename = str(row.get('fileName') or '')
    if (not season or not filename) and row.get('scheKey'):
        _league_id, season, filename = str(row['scheKey']).split('#', 2)
    league_id = _league_id_from_filename(filename)
    sche_url = zqconfig_qt.scheWebdir + season + '/' + filename
    sche_path = os.path.join(zqconfig_qt.schelocaldir, season, filename)
    if filename.startswith('c'):
        weburl = zqconfig_qt.cup_web_schedir + season + '/' + str(league_id) + '.html'
    elif _sub_league_id_from_filename(filename) is not None:
        weburl = zqconfig_qt.sub_web_schedir + season + '/' + str(league_id) + '_' + str(_sub_league_id_from_filename(filename)) + '.html'
    else:
        weburl = zqconfig_qt.league_web_schedir + season + '/' + str(league_id) + '.html'
    return sche_url, sche_path, weburl
