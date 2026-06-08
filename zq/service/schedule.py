import os
from datetime import datetime, timedelta

from config import zqconfig_qt
from crawler.qt.zq_score_crawler import ScoreCrawler
from utils import dateUtil, fileUtil, sql_util
from utils.dateUtil import getNowTime
from zq.thread import schethread


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


def _dir_files_if_exists(path):
    if os.path.isdir(path):
        return fileUtil.dirFiles(path, [])
    return []


def _pending_files():
    files = []
    for file in _dir_files_if_exists(zqconfig_qt.schedule_js_work_dir):
        files.append([file, 0])
    for subdir in zqconfig_qt.schedule_js_legacy_pending_dirs:
        path = os.path.join(zqconfig_qt.schejs_pending, subdir)
        for file in _dir_files_if_exists(path):
            files.append([file, 1 if subdir == 'exist' else 0])
    return files


def upSchedule():
    updateTime_sche = dateUtil.getNowTime()
    lastUpdate_local = _get_task_time('schedule')
    files = _pending_files()
    count = len(files)
    number_thread = 8
    remain = len(files)
    index = 0
    while remain > 0:
        print([count, remain])
        threads = []
        number = number_thread if remain > number_thread else remain
        for i in range(0, number):
            filepath = files[index + i][0]
            old = files[index + i][1]
            thread = schethread.upLeagueThread(filepath, old, lastUpdate_local)
            threads.append(thread)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        index = index + number
        remain = remain - number
    sql_util.upData('zq_note', {'lastUpdateTime': updateTime_sche}, {'task': 'schedule'})


def upMatchScore():
    print('start update zq match score')
    now = datetime.now()
    time0 = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
    time1 = "'" + (now + timedelta(days=-360)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    sql = "SELECT scheduleID, leagueId, matchState,matchTime FROM `zq_schedule` WHERE matchState > -1 and partscore_f in(0,1)" + \
          "AND matchTime <=" + time0 + " AND matchtime >= " + time1 + " ORDER BY matchTime DESC"
    matchs = sql_util.select_rows(sql)
    size = len(matchs)
    for match in matchs:
        print(match)
        matchstate = match[2]
        condition = {'scheduleID': match[0]}
        scoreCrawler = ScoreCrawler(match[0])
        score = scoreCrawler.qt_web_get()
        if score != {}:
            if matchstate in (-1, -4):
                score['partscore_f'] = 2
            if len(score) > 0 and score['MatchState'] != 0:
                sql_util.upData('zq_schedule', score, condition)
            size = size - 1
            print("remaining matches: " + str(size))
    print(getNowTime() + " score update success")
