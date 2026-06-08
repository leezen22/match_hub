from datetime import datetime
import os
import traceback
from pathlib import Path

from bs4 import BeautifulSoup

from config import common_config, zqconfig_qt
from utils import fileUtil, js2pyUtil, sql_util
from utils.webUtil import WebUtil
from zq.extract.scheduleJs import getSche
from zq.service import task_state
from zq.service.match import upMatchByOne


ZQ_JS_PREFIX = "var jh = new Object();\n"


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
        last_update_web = upScheJS_season(schejs_url, schejs_path, weburl, last_update_local)
        if last_update_web is not None and last_update_web > next_task_time:
            next_task_time = last_update_web
    _advance_task_time('schedulejs', next_task_time)


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
            isUpdated = True
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


def upScheJS_season(schejsUrl, schejsPath, weburl, lastUpdate_local):
    headers = dict(zqconfig_qt.headers)
    headers['Referer'] = weburl
    work_path = _schedule_work_path(schejsUrl)
    webresponse = WebUtil.requests_get(schejsUrl, headers=headers, sourceName='zq.upSchedulejs')
    if webresponse[0] != 1 or webresponse[1] == '':
        fileUtil.logLine(common_config.httpRequest_fail, ['zq.schedule_js_http_failed', schejsUrl, webresponse[0]])
        return None

    content = _with_zq_prefix(webresponse[1])
    parse_result = _parse_schedule_content(content, schejsUrl)
    if parse_result[0] != 1:
        fileUtil.logLine(common_config.js2pyweb_e, ['zq.schedule_js_parse_failed', schejsUrl])
        return None

    webcontext = parse_result[1]
    last_update_web = datetime.strptime(webcontext.lastUpdateTime, "%Y-%m-%d %H:%M:%S")
    if last_update_web > lastUpdate_local:
        fileUtil.fileWrite(work_path, "w", content)
        if zqconfig_qt.keep_schedule_js_cache and os.path.exists(work_path):
            fileUtil.copyfile(work_path, schejsPath)
        print("update: {0}".format(schejsUrl))
    return last_update_web


def getSchedulePending(leagueId, Type, season, ifHaveSub):
    pending_list = []
    seafilename = 'sea' + str(leagueId) + '.js'
    seajs_url = zqconfig_qt.seajsWebdir + seafilename
    seajs_path = zqconfig_qt.seajslocaldir + seafilename
    condition = {'leagueId': leagueId, 'matchSeason': season}
    keys = ['ID', 'leagueId', 'matchSeason', 'seasonPath', 'state']
    result = sql_util.select_table_rows('zq_seasonTask', keys, condition)
    if len(result) == 0:
        WebUtil.loadFileByName(seajs_url, seajs_path, zqconfig_qt.headers)
        stask = {
            'leagueId': leagueId,
            'matchSeason': season,
            'seasonPath': seajs_path,
            'state': 1,
        }
        sql_util.insertData('zq_seasonTask', stask)
    elif result[0][4] == 2 and not zqconfig_qt.enable_finished_season_backfill:
        return pending_list

    pending_list = getMRJSPending(leagueId, season, Type, ifHaveSub)
    return pending_list


def getMRJSPending(leagueId, season, Type, ifHaveSub):
    match_result_js_list = []
    pending_js_list = []
    headers = dict(zqconfig_qt.headers)
    if str(Type) == '2':
        schejs_url = zqconfig_qt.scheWebdir + season + "/c" + str(leagueId) + ".js"
        schejs_path = zqconfig_qt.schelocaldir + season + "\\c" + str(leagueId) + ".js"
        weburl = zqconfig_qt.cup_web_schedir + season + "/" + str(leagueId) + ".html"
        match_result_js_list.append([schejs_url, schejs_path, weburl])
    elif str(Type) == '1' and str(ifHaveSub) == '0':
        weburl = zqconfig_qt.league_web_schedir + season + "/" + str(leagueId) + ".html"
        schejs_url = zqconfig_qt.scheWebdir + season + "/s" + str(leagueId) + ".js"
        schejs_path = zqconfig_qt.schelocaldir + season + "\\s" + str(leagueId) + ".js"
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
                            schejs_path = zqconfig_qt.schelocaldir + season + "\\s" + str(
                                leagueId) + '_' + sub_id + ".js"
                            match_result_js_list.append([schejs_url, schejs_path, weburl])
                    else:
                        weburl = zqconfig_qt.league_web_schedir + season + "/" + str(leagueId) + ".html"
                        schejs_url = zqconfig_qt.scheWebdir + season + "/s" + str(leagueId) + ".js"
                        schejs_path = zqconfig_qt.schelocaldir + season + "\\s" + str(leagueId) + ".js"
                        match_result_js_list.append([schejs_url, schejs_path, weburl])
            except Exception as e:
                fileUtil.logLine(
                    common_config.js2pyweb_e,
                    ['getMRJSPending', url, [leagueId, season, Type, ifHaveSub], repr(e)],
                )

    for match_result_js in match_result_js_list:
        filename = os.path.basename(match_result_js[1])
        sche_key = str(leagueId) + "#" + season + "#" + filename
        condition = {'scheKey': sche_key}
        keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'state']
        result = sql_util.select_table_rows('zq_scheTask', keys, condition)
        if len(result) > 0 and result[0][7] == 2 and not zqconfig_qt.enable_finished_season_backfill:
            pass
        else:
            if len(result) == 0:
                scheinfo = {
                    'scheKey': sche_key,
                    'leagueId': leagueId,
                    'matchSeason': season,
                    'fileName': filename,
                    'schePath': match_result_js[1],
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
