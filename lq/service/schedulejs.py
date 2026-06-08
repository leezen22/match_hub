import os
from datetime import datetime

from config import common_config, lqconfig_qt
from lq.service.league import LQleague
from utils import fileUtil, sql_util, js2pyUtil
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


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

    last_update_local = _get_task_time('schedulejs')
    next_task_time = last_update_local
    sclasslist = LQleague.getLeaguesOfWebsite()
    for sclass in sclasslist:
        webjslist = LQleague.getSchejsPending(sclass)
        for schejs_url, schejs_path in webjslist:
            last_update_web = upScheJS_season(schejs_url, schejs_path, last_update_local)
            if last_update_web is not None and last_update_web > next_task_time:
                next_task_time = last_update_web

    _advance_task_time('schedulejs', next_task_time)
    print(getNowTime() + ' finish update lq schedule js')


def upScheJsLocal():
    fileUtil.logLine(lqconfig_qt.update_log, "start update lq schedule js from db pending")
    print(getNowTime() + ' start update lq schedule js from db pending')

    last_update_local = _get_task_time('schedulejs')
    next_task_time = last_update_local
    sql_schejs = (
        "SELECT scheKey FROM lq_schedule_crawler "
        "WHERE matchSeason in ('25', '25-26', '26', '26-27') and state=1"
    )
    result_s = sql_util.select_rows(sql_schejs)
    for schejs in result_s:
        item = schejs[0].split("#")
        season = item[1]
        filename = item[2]
        schejs_url = lqconfig_qt.scheWebdir + season + "/" + filename
        schejs_path = lqconfig_qt.schelocaldir + season + "/" + filename
        last_update_web = upScheJS_season(schejs_url, schejs_path, last_update_local)
        if last_update_web is not None and last_update_web > next_task_time:
            next_task_time = last_update_web

    _advance_task_time('schedulejs', next_task_time)


def upScheJS_season(schejsUrl, schejsPath, lastUpdate_local):
    season = schejsUrl.split('/')[-2]
    filename = os.path.basename(schejsUrl.split('?')[0])
    pending_path = os.path.join(lqconfig_qt.schedule_js_work_dir, str(season), filename)

    try:
        webresponse = WebUtil.requests_get(
            schejsUrl,
            headers=lqconfig_qt.headers,
            sourceName='collect schedule js',
        )
        state = webresponse[0]
        webcontent = webresponse[1]
        if state == 0:
            fileUtil.logLine(common_config.lq_rank_fail, [schejsUrl, schejsPath])
            return None
        if state != 1 or webcontent == '':
            return None

        parse_result = js2pyUtil.js2c(
            webcontent,
            source=schejsUrl,
            required_names=("lastUpdateTime", "arrData", "arrLeague", "playoffsList"),
        )
        if parse_result[0] != 1:
            fileUtil.logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_PARSE_SKIPPED", schejsUrl])
            return None

        webcontext = parse_result[1]
        last_update_web = datetime.strptime(webcontext.lastUpdateTime, "%Y-%m-%d %H:%M:%S")
        if last_update_web > lastUpdate_local:
            fileUtil.fileWrite(pending_path, "w", webcontent)
            if lqconfig_qt.keep_schedule_js_cache and os.path.exists(pending_path):
                fileUtil.copyfile(pending_path, schejsPath)
            print("update: {0}".format(schejsUrl))
        return last_update_web
    except Exception as e:
        fileUtil.logLine(common_config.exception, ["SCHEDULE_JS_UPDATE_FAILED", schejsUrl, repr(e)])
        print("failed: {0}".format(schejsUrl))
        print(e)
        return None
