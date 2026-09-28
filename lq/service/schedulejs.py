import os
from datetime import datetime, timedelta

from config import common_config, lqconfig_qt
from lq.service.league import LQleague
from utils import fileUtil, sql_util, js2pyUtil
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil

_SCHEDULE_CRAWLER_TRACKING_COLUMNS_READY = False

# lq_schedule_crawler.state
# 0 = disabled: manually disabled, do not fetch automatically.
# 1 = active: schedule JS may still change and should be fetched by active tasks.
# 2 = finished: schedule JS is stable enough to skip normal active fetching.
SCHEDULE_CRAWLER_STATE_DISABLED = 0
SCHEDULE_CRAWLER_STATE_ACTIVE = 1
SCHEDULE_CRAWLER_STATE_FINISHED = 2
PRESEASON_REGULAR_SCHEDULE_FINISH_GRACE_DAYS = 7
PLAYOFF_SCHEDULE_FINISH_GRACE_DAYS = 14


def _get_task_time(task):
    result = sql_util.select_table_rows(
        'lq_note',
        ['ID', 'task', 'lastUpdateTime'],
        {'task': task},
        isDis=True,
    )
    if len(result) == 0:
        return datetime(2000, 1, 1)
    return result[0][2]


def _advance_task_time(task, current_time):
    sql_util.upData('lq_note', {'lastUpdateTime': current_time}, {'task': task})


def upScheJs():
    fileUtil.logLine(lqconfig_qt.update_log, "start update lq schedule js")
    print(getNowTime() + ' start update lq schedule js')

    _ensure_schedule_crawler_tracking_columns()
    success_count = 0
    skipped_count = 0
    failed_urls = []
    sclasslist = LQleague.getLeaguesOfWebsite()
    now = datetime.now()
    for sclass in sclasslist:
        webjslist = LQleague.getSchejsPending(sclass)
        for schejs_url, schejs_path in webjslist:
            if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
                skipped_count += 1
                continue
            result = upScheJS_season_result(schejs_url, schejs_path)
            if result["ok"]:
                success_count += 1
            else:
                failed_urls.append(schejs_url)
            if result["skipped"]:
                skipped_count += 1

    if failed_urls:
        print("schedule js update has failed urls: failed={0}".format(len(failed_urls)))
        for failed_url in failed_urls:
            print("schedule js failed: {0}".format(failed_url))
    _advance_task_time('schedulejs', getNowTime())
    print(getNowTime() + ' finish update lq schedule js, success={0}, skipped={1}, failed={2}'.format(
        success_count,
        skipped_count,
        len(failed_urls),
    ))


def upScheJsLocal():
    fileUtil.logLine(lqconfig_qt.update_log, "start update lq schedule js from db pending")
    print(getNowTime() + ' start update lq schedule js from db pending')

    _ensure_schedule_crawler_tracking_columns()
    sql_schejs = (
        "SELECT scheKey FROM lq_schedule_crawler "
        "WHERE matchSeason in ('25', '25-26', '26', '26-27') and state=1"
    )
    result_s = sql_util.select_rows(sql_schejs)
    failed_urls = []
    now = datetime.now()
    for schejs in result_s:
        item = schejs[0].split("#")
        season = item[1]
        filename = item[2]
        schejs_url = lqconfig_qt.scheWebdir + season + "/" + filename
        schejs_path = lqconfig_qt.schelocaldir + season + "/" + filename
        if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
            continue
        result = upScheJS_season_result(schejs_url, schejs_path)
        if not result["ok"]:
            failed_urls.append(schejs_url)

    if failed_urls:
        print("schedule js local update has failed urls: failed={0}".format(len(failed_urls)))
        for failed_url in failed_urls:
            print("schedule js failed: {0}".format(failed_url))
    _advance_task_time('schedulejs', getNowTime())


def upActiveScheJs(league_ids=None, all_leagues=False, limit=None, season_count=3, now=None):
    fileUtil.logLine(lqconfig_qt.update_log, "start update active lq schedule js")
    print(getNowTime() + ' start update active lq schedule js')

    _ensure_schedule_crawler_tracking_columns()
    _discover_due_playoff_schedule_js(league_ids=league_ids, all_leagues=all_leagues, now=now)

    rows = _select_active_schedule_js_rows(
        league_ids=league_ids,
        all_leagues=all_leagues,
        limit=limit,
        season_count=season_count,
        now=now,
    )
    summary = {"selected": len(rows), "success": 0, "updated": 0, "skipped": 0, "failed": 0}
    for row in rows:
        result = upScheJS_season_result(row['scheUrl'], row['schePath'])
        if result["ok"]:
            summary["success"] += 1
            if result["skipped"]:
                summary["skipped"] += 1
            else:
                summary["updated"] += 1
        else:
            summary["failed"] += 1

    _advance_task_time('schedulejs', getNowTime())
    print(getNowTime() + ' finish update active lq schedule js: {0}'.format(summary))
    return summary


def normalize_historical_schedule_states(
        league_ids=None,
        all_leagues=False,
        keep_recent_seasons=3,
        now=None):
    """Close stale historical schedule JS rows using only local schedule data."""
    _ensure_schedule_crawler_tracking_columns()
    now = now or datetime.now()
    rows = _select_schedule_crawler_rows_for_state_maintenance(
        league_ids=league_ids,
        all_leagues=all_leagues,
    )
    recent_seasons = _recent_local_schedule_seasons_by_league(
        sorted({int(row['leagueId']) for row in rows if row.get('leagueId') is not None}),
        keep_recent_seasons,
    )
    summary = {"scanned": 0, "closed": 0, "kept_active": 0, "skipped_recent": 0}
    for row in rows:
        summary["scanned"] += 1
        allowed_recent = recent_seasons.get(int(row['leagueId']), set())
        if str(row.get('matchSeason')) in allowed_recent:
            summary["skipped_recent"] += 1
            continue
        if _is_schedule_row_locally_finished(row, now):
            sql_util.upData('lq_schedule_crawler', {
                'state': SCHEDULE_CRAWLER_STATE_FINISHED,
            }, {'scheKey': row['scheKey']})
            summary["closed"] += 1
        else:
            summary["kept_active"] += 1
    print("historical schedule state normalization finished: {0}".format(summary))
    return summary


def _select_schedule_crawler_rows_for_state_maintenance(league_ids=None, all_leagues=False):
    if not all_leagues and not league_ids:
        return []
    where = ["state={0}".format(SCHEDULE_CRAWLER_STATE_ACTIVE)]
    if league_ids and not all_leagues:
        where.append("leagueId in({0})".format(",".join(str(int(item)) for item in league_ids)))
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime "
        "FROM lq_schedule_crawler WHERE {where} ORDER BY leagueId,matchSeason,fileName".format(
            where=" and ".join(where)
        )
    )
    return [_normalize_active_schedule_row(row) for row in rows]


def upScheJS_season(schejsUrl, schejsPath, lastUpdate_local=None):
    result = upScheJS_season_result(schejsUrl, schejsPath, lastUpdate_local)
    return result["last_update_web"]


def _schedule_work_path(schejs_url):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    return os.path.join(lqconfig_qt.schedule_js_work_dir, str(season), filename)


def prepare_schedule_js_for_update(schejs_url, schejs_path, force=False, now=None):
    """Fetch a schedule JS only when it is due, then return the work file to consume."""
    _ensure_schedule_crawler_tracking_columns()
    now = now or datetime.now()
    work_path = _schedule_work_path(schejs_url)
    sche_key = _schedule_key_from_url(schejs_url)
    _ensure_schedule_crawler_row(sche_key, schejs_url, schejs_path)
    row = _schedule_crawler_row(sche_key)

    if os.path.exists(work_path):
        return {"should_parse": True, "work_path": work_path, "reason": "pending_work", "result": None}

    if not force:
        if _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
            return {"should_parse": False, "work_path": work_path, "reason": "locally_finished", "result": None}
        if row and int(row.get('state') or 0) == SCHEDULE_CRAWLER_STATE_FINISHED:
            return {"should_parse": False, "work_path": work_path, "reason": "state_finished", "result": None}
        if row and not _is_schedule_js_due(row, now):
            return {"should_parse": False, "work_path": work_path, "reason": "not_due", "result": None}

    result = upScheJS_season_result(schejs_url, schejs_path)
    return {
        "should_parse": os.path.exists(work_path),
        "work_path": work_path,
        "reason": "fetched" if result.get("ok") and not result.get("skipped") else "unchanged_or_failed",
        "result": result,
    }


def upScheJS_season_result(schejsUrl, schejsPath, lastUpdate_local=None):
    _ensure_schedule_crawler_tracking_columns()
    pending_path = _schedule_work_path(schejsUrl)
    sche_key = _schedule_key_from_url(schejsUrl)
    source_times = _get_schedule_source_times(sche_key)
    persisted_source_time = source_times["persisted"]
    result = {"ok": False, "skipped": False, "last_update_web": None, "sche_key": sche_key}

    try:
        webresponse = WebUtil.requests_get(
            schejsUrl,
            headers=_schedule_js_headers(schejsUrl),
            timeout=(10, 20),
            sourceName='collect schedule js',
            trust_env=False,
        )
        state = webresponse[0]
        webcontent = webresponse[1]
        if state == 0:
            fileUtil.logLine(common_config.lq_rank_fail, [schejsUrl, schejsPath])
            _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, "empty proxy state")
            return result
        if state != 1 or webcontent == '':
            _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, "request failed or empty content: state={0}".format(state))
            return result

        parse_result = js2pyUtil.js2c(
            webcontent,
            source=schejsUrl,
            required_names=("lastUpdateTime", "arrData", "arrLeague", "playoffsList"),
        )
        if parse_result[0] != 1:
            fileUtil.logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_PARSE_SKIPPED", schejsUrl])
            _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, "parse failed")
            return result

        webcontext = parse_result[1]
        last_update_web = datetime.strptime(webcontext.lastUpdateTime, "%Y-%m-%d %H:%M:%S")
        result["ok"] = True
        result["last_update_web"] = last_update_web
        # A work file is an unconsumed delivery. Never let a source timestamp
        # suppress it after a process interruption.
        pending_exists = os.path.exists(pending_path)
        fetched_source_time = source_times["fetched"]
        if pending_exists and (fetched_source_time is None or last_update_web <= fetched_source_time):
            result["skipped"] = False
            result["pending"] = True
        elif persisted_source_time is None or last_update_web > persisted_source_time:
            fileUtil.fileWrite(pending_path, "w", webcontent)
            if lqconfig_qt.keep_schedule_js_cache and os.path.exists(pending_path):
                fileUtil.copyfile(pending_path, schejsPath)
            print("update: {0}".format(schejsUrl))
        else:
            result["skipped"] = True
        _mark_schedule_js_success(sche_key, schejsUrl, schejsPath, last_update_web)
        return result
    except Exception as e:
        fileUtil.logLine(common_config.exception, ["SCHEDULE_JS_UPDATE_FAILED", schejsUrl, repr(e)])
        print("failed: {0}".format(schejsUrl))
        print(e)
        _mark_schedule_js_failed(sche_key, schejsUrl, schejsPath, repr(e))
        return result


def _ensure_schedule_crawler_tracking_columns():
    global _SCHEDULE_CRAWLER_TRACKING_COLUMNS_READY
    if _SCHEDULE_CRAWLER_TRACKING_COLUMNS_READY:
        return
    columns = {row[0] for row in sql_util.select_rows("SHOW COLUMNS FROM lq_schedule_crawler")}
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
        sql_util.sqlExecute("ALTER TABLE lq_schedule_crawler {0}".format(clause))
    _SCHEDULE_CRAWLER_TRACKING_COLUMNS_READY = True


def _schedule_key_from_url(schejs_url):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    if filename.startswith('l'):
        league_id = filename.split('_')[0][1:]
    elif filename.startswith('c'):
        league_id = filename.split('.')[0][1:]
    else:
        league_id = ''
    return "{0}#{1}#{2}".format(league_id, season, filename)


def _schedule_row_from_url(schejs_url, schejs_path=None):
    season = schejs_url.split('/')[-2]
    filename = os.path.basename(schejs_url.split('?')[0])
    sche_key = _schedule_key_from_url(schejs_url)
    league_id = sche_key.split('#', 1)[0]
    return {
        'scheKey': sche_key,
        'leagueId': int(league_id) if str(league_id).isdigit() else league_id,
        'matchSeason': season,
        'fileName': filename,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
    }


def _close_schedule_js_if_locally_finished(schejs_url, schejs_path, now):
    row = _schedule_row_from_url(schejs_url, schejs_path)
    if not _is_schedule_row_locally_finished(row, now):
        return False
    _ensure_schedule_crawler_row(row['scheKey'], schejs_url, schejs_path)
    sql_util.upData('lq_schedule_crawler', {
        'state': SCHEDULE_CRAWLER_STATE_FINISHED,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
    }, {'scheKey': row['scheKey']})
    print("skip finished schedule js: {0}".format(schejs_url))
    return True


def _schedule_js_headers(schejs_url):
    headers = dict(lqconfig_qt.headers)
    headers.update({
        "Accept": "application/javascript,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": _schedule_js_referer(schejs_url),
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    })
    return headers


def _schedule_js_referer(schejs_url):
    season = schejs_url.split('/')[-2]
    page_season = _schedule_page_season(season)
    filename = os.path.basename(schejs_url.split('?')[0])
    if filename.startswith('l'):
        parts = filename[:-3].split('_')
        league_id = parts[0][1:]
        match_kind = parts[1] if len(parts) > 1 else '1'
        page = 'Playoffs.aspx' if match_kind == '2' else 'Preseason.aspx' if match_kind == '3' else 'Normal.aspx'
        return "https://nba.titan007.com/cn/{0}?SclassID={1}&MatchSeason={2}".format(page, league_id, page_season)
    return "https://nba.titan007.com/"


def _ensure_schedule_crawler_row(sche_key, schejs_url, schejs_path):
    rows = sql_util.select_rows("SELECT ID FROM lq_schedule_crawler WHERE scheKey='{0}'".format(sql_util.safe(sche_key)))
    if rows:
        return
    league_id, season, filename = sche_key.split('#', 2)
    sql_util.insertData('lq_schedule_crawler', {
        'scheKey': sche_key,
        'leagueId': league_id,
        'matchSeason': season,
        'fileName': filename,
        'schePath': schejs_path,
        'scheUrl': schejs_url,
        'seaPath': lqconfig_qt.seajsWebdir + "sea" + league_id + ".js",
        'state': SCHEDULE_CRAWLER_STATE_ACTIVE,
    })


def _schedule_crawler_row(sche_key):
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,state,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime FROM lq_schedule_crawler WHERE scheKey='{0}' LIMIT 1".format(
            sql_util.safe(sche_key)
        )
    )
    if not rows:
        return None
    return _normalize_active_schedule_row(rows[0])


def _get_schedule_source_times(sche_key):
    rows = sql_util.select_rows(
        "SELECT sourceLastUpdateTime,fetchedSourceLastUpdateTime,persistedSourceLastUpdateTime "
        "FROM lq_schedule_crawler WHERE scheKey='{0}'".format(sql_util.safe(sche_key))
    )
    if not rows:
        return {"fetched": None, "persisted": None}
    return {
        "fetched": rows[0][1] or rows[0][0],
        "persisted": rows[0][2],
    }


def _get_schedule_source_time(sche_key):
    return _get_schedule_source_times(sche_key)["persisted"]


def _mark_schedule_js_success(sche_key, schejs_url, schejs_path, source_last_update_time):
    _ensure_schedule_crawler_row(sche_key, schejs_url, schejs_path)
    sql_util.upData('lq_schedule_crawler', {
        'sourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'fetchedSourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'lastFetchTime': getNowTime(),
        'lastSuccessTime': getNowTime(),
        'lastError': None,
        'failCount': 0,
        'scheUrl': schejs_url,
        'schePath': schejs_path,
    }, {'scheKey': sche_key})


def mark_schedule_js_persisted(sche_key, source_last_update_time, state, schejs_url=None, schejs_path=None):
    """Mark a downloaded schedule JS as consumed by update_schedule()."""
    _ensure_schedule_crawler_tracking_columns()
    _ensure_schedule_crawler_row(sche_key, schejs_url or '', schejs_path or '')
    payload = {
        'persistedSourceLastUpdateTime': source_last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
        'state': int(state),
    }
    if schejs_url is not None:
        payload['scheUrl'] = schejs_url
    if schejs_path is not None:
        payload['schePath'] = schejs_path
    sql_util.upData('lq_schedule_crawler', payload, {'scheKey': sche_key})


def _mark_schedule_js_failed(sche_key, schejs_url, schejs_path, error):
    _ensure_schedule_crawler_row(sche_key, schejs_url, schejs_path)
    sql_util.sqlExecute(
        "UPDATE lq_schedule_crawler "
        "SET lastFetchTime='{now}', lastError='{error}', failCount=COALESCE(failCount,0)+1, "
        "scheUrl='{url}', schePath='{path}' "
        "WHERE scheKey='{sche_key}'".format(
            now=sql_util.safe(getNowTime()),
            error=sql_util.safe(str(error)[:2000]),
            url=sql_util.safe(str(schejs_url)),
            path=sql_util.safe(str(schejs_path)),
            sche_key=sql_util.safe(str(sche_key)),
        )
    )


def _select_active_schedule_js_rows(league_ids=None, all_leagues=False, limit=None, season_count=3, now=None):
    now = now or datetime.now()
    if not all_leagues and not league_ids:
        return []
    where = [
        "state={0}".format(SCHEDULE_CRAWLER_STATE_ACTIVE),
        "schePath IS NOT NULL",
    ]
    if league_ids and not all_leagues:
        where.append("leagueId in({0})".format(",".join(str(int(item)) for item in league_ids)))
    rows = sql_util.select_dicts(
        "SELECT scheKey,leagueId,matchSeason,fileName,scheUrl,schePath,failCount,lastFetchTime,"
        "persistedSourceLastUpdateTime "
        "FROM lq_schedule_crawler WHERE {where} ORDER BY lastFetchTime ASC, updateTime ASC".format(
            where=" and ".join(where)
        )
    )
    rows = [_normalize_active_schedule_row(row) for row in rows]
    rows = _filter_recent_schedule_rows(rows, season_count=season_count)
    rows = _close_locally_finished_schedule_rows(rows, now)
    selected = [row for row in rows if _is_schedule_js_due(row, now)]
    if limit is not None:
        selected = selected[:int(limit)]
    return selected


def _close_locally_finished_schedule_rows(rows, now):
    active_rows = []
    for row in rows:
        if _is_schedule_row_locally_finished(row, now):
            sql_util.upData('lq_schedule_crawler', {
                'state': SCHEDULE_CRAWLER_STATE_FINISHED,
            }, {'scheKey': row['scheKey']})
            continue
        active_rows.append(row)
    return active_rows


def _is_schedule_row_locally_finished(row, now):
    if _schedule_work_file_exists(row):
        return False
    scope = _schedule_row_match_scope(row)
    if scope is None:
        return False
    where = [
        "leagueID={0}".format(int(row['leagueId'])),
        "matchSeason='{0}'".format(sql_util.safe(str(row['matchSeason']))),
        "matchKind={0}".format(int(scope['match_kind'])),
    ]
    if scope.get('month') is not None:
        where.append("MONTH(matchTime)={0}".format(int(scope['month'])))
    rows = sql_util.select_rows(
        "SELECT COUNT(*),SUM(CASE WHEN matchState IN (-1,-4) THEN 1 ELSE 0 END),MAX(matchTime) "
        "FROM lq_schedule WHERE {where}".format(where=" AND ".join(where))
    )
    if not rows:
        return False
    total, terminal_count, max_match_time = rows[0]
    if not total or max_match_time is None:
        return False
    if int(terminal_count or 0) < int(total):
        return False
    grace_days = _schedule_finish_grace_days(int(scope['match_kind']))
    return max_match_time <= now - timedelta(days=grace_days)


def _schedule_finish_grace_days(match_kind):
    if int(match_kind) == 2:
        return PLAYOFF_SCHEDULE_FINISH_GRACE_DAYS
    return PRESEASON_REGULAR_SCHEDULE_FINISH_GRACE_DAYS


def _schedule_row_match_scope(row):
    filename = str(row.get('fileName') or '')
    if not filename.startswith('l'):
        return None
    parts = filename[:-3].split('_')
    if len(parts) < 2:
        return None
    match_kind = int(parts[1])
    scope = {'match_kind': match_kind}
    if match_kind == 1 and len(parts) >= 4:
        scope['month'] = int(parts[3])
    return scope


def _normalize_active_schedule_row(row):
    sche_url, sche_path = _schedule_url_path_from_row(row)
    if row.get('scheUrl') != sche_url or row.get('schePath') != sche_path:
        sql_util.upData('lq_schedule_crawler', {
            'scheUrl': sche_url,
            'schePath': sche_path,
        }, {'scheKey': row['scheKey']})
        row = dict(row)
        row['scheUrl'] = sche_url
        row['schePath'] = sche_path
    return row


def _schedule_url_path_from_row(row):
    season = str(row.get('matchSeason') or '')
    filename = str(row.get('fileName') or '')
    if (not season or not filename) and row.get('scheKey'):
        _league_id, season, filename = str(row['scheKey']).split('#', 2)
    sche_url = lqconfig_qt.scheWebdir + season + '/' + filename
    sche_path = lqconfig_qt.schelocaldir + season + '/' + filename
    return sche_url, sche_path


def _filter_recent_schedule_rows(rows, season_count=3):
    if season_count is None:
        return rows
    season_limit = int(season_count)
    if season_limit <= 0 or not rows:
        return []
    league_ids = sorted({int(row['leagueId']) for row in rows if row.get('leagueId') is not None})
    recent_seasons = _recent_local_schedule_seasons_by_league(league_ids, season_limit)
    filtered = []
    for row in rows:
        allowed_seasons = recent_seasons.get(int(row['leagueId']))
        if allowed_seasons is None:
            continue
        if str(row.get('matchSeason')) in allowed_seasons:
            filtered.append(row)
    return filtered


def _recent_local_schedule_seasons_by_league(league_ids, season_count):
    if not league_ids:
        return {}
    rows = sql_util.select_rows(
        "SELECT leagueID,matchSeason,MAX(matchTime) AS maxMatchTime "
        "FROM lq_schedule WHERE leagueID IN ({league_ids}) "
        "GROUP BY leagueID,matchSeason ORDER BY leagueID ASC,maxMatchTime DESC".format(
            league_ids=",".join(str(int(league_id)) for league_id in league_ids)
        )
    )
    seasons_by_league = {}
    for league_id, season, _max_match_time in rows:
        league_key = int(league_id)
        seasons = seasons_by_league.setdefault(league_key, set())
        if len(seasons) < season_count:
            seasons.add(str(season))
    return seasons_by_league


def _is_schedule_js_due(row, now):
    if _schedule_work_file_exists(row):
        return True
    last_fetch_time = row.get('lastFetchTime')
    if last_fetch_time is None:
        return True
    return last_fetch_time <= now - _schedule_fetch_interval(row)


def _schedule_work_file_exists(row):
    season = str(row.get('matchSeason') or '')
    filename = str(row.get('fileName') or '')
    if not season or not filename:
        return False
    return os.path.exists(os.path.join(lqconfig_qt.schedule_js_work_dir, season, filename))


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
    filename = str(row.get('fileName') or '')
    if filename.endswith('_2.js'):
        return timedelta(minutes=3)
    return timedelta(minutes=10)


def _discover_due_playoff_schedule_js(league_ids=None, all_leagues=False, now=None):
    now = now or datetime.now()
    for league in _active_playoff_leagues(league_ids=league_ids, all_leagues=all_leagues):
        league_id = int(league['league_id'])
        if int(league.get('kind_type') or 1) != 1:
            continue
        season = _latest_local_league_season(league_id)
        if season is None:
            continue
        regular_end_time = _regular_season_end_time(league_id, season)
        if regular_end_time is None or now < regular_end_time:
            continue
        if not _should_discover_playoff_js(league_id, season, now):
            continue
        _discover_playoff_schedule_js(league_id, season)


def _active_playoff_leagues(league_ids=None, all_leagues=False):
    if not all_leagues and not league_ids:
        return []
    leagues = LQleague.getLeaguesOfWebsite()
    if all_leagues:
        return leagues
    allowed_ids = {int(item) for item in league_ids or []}
    return [league for league in leagues if int(league['league_id']) in allowed_ids]


def _latest_local_league_season(league_id):
    rows = sql_util.select_rows(
        "SELECT matchSeason FROM lq_schedule WHERE leagueID={0} GROUP BY matchSeason ORDER BY MAX(matchTime) DESC LIMIT 1".format(
            int(league_id)
        )
    )
    return rows[0][0] if rows else None


def _regular_season_end_time(league_id, season):
    rows = sql_util.select_rows(
        "SELECT MAX(matchTime) FROM lq_schedule "
        "WHERE leagueID={0} AND matchSeason='{1}' AND (playoffsID IS NULL OR playoffsID=0)".format(
            int(league_id),
            sql_util.safe(str(season)),
        )
    )
    return rows[0][0] if rows and rows[0][0] is not None else None


def _should_discover_playoff_js(league_id, season, now):
    filename = 'l{0}_2.js'.format(int(league_id))
    rows = sql_util.select_dicts(
        "SELECT lastFetchTime,failCount FROM lq_schedule_crawler "
        "WHERE leagueId={0} AND matchSeason='{1}' AND fileName='{2}' LIMIT 1".format(
            int(league_id),
            sql_util.safe(str(season)),
            sql_util.safe(filename),
        )
    )
    if not rows or rows[0].get('lastFetchTime') is None:
        return True
    return _is_schedule_js_due({
        'fileName': filename,
        'failCount': rows[0].get('failCount'),
        'lastFetchTime': rows[0].get('lastFetchTime'),
    }, now)


def _discover_playoff_schedule_js(league_id, season):
    season_path = str(season)
    page_season = _schedule_page_season(season_path)
    page_url = lqconfig_qt.lanqurl + '/cn/Playoffs.aspx?SclassID={0}&MatchSeason={1}'.format(
        int(league_id),
        page_season,
    )
    sche_src = LQleague.findScheJS(page_url, lqconfig_qt.headers)
    if not sche_src:
        return None
    sche_url = _absolute_schedule_url(sche_src)
    filename = os.path.basename(sche_src.split('?')[0])
    sche_path = lqconfig_qt.schelocaldir + season_path + '/' + filename
    result = upScheJS_season_result(sche_url, sche_path)
    print("playoff schedule js discover/update: leagueId={0}, season={1}, ok={2}, skipped={3}, url={4}".format(
        league_id,
        season,
        result.get('ok'),
        result.get('skipped'),
        sche_url,
    ))
    return result


def _schedule_page_season(season):
    season_text = str(season)
    if len(season_text) == 2 and season_text.isdigit():
        return '20' + season_text
    if len(season_text) == 5 and season_text[2] == '-':
        first, second = season_text.split('-', 1)
        if first.isdigit() and second.isdigit():
            return '20{0}-20{1}'.format(first, second)
    return season_text


def _absolute_schedule_url(sche_src):
    if sche_src.startswith('http://') or sche_src.startswith('https://'):
        return sche_src
    return lqconfig_qt.lanqurl + sche_src if sche_src.startswith('/') else lqconfig_qt.lanqurl + '/' + sche_src
