import os
from datetime import datetime

from config import lqconfig_qt
from lq.dao import MatchDao
from lq.extract.MatchJS import getMatchFromFile
from lq.service import tag_mainten
from lq.service.league import LQleague
from utils import fileUtil, sql_util
from utils.dateUtil import getNowTime


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


def _pending_files(*subdirs):
    files = []
    for subdir in subdirs:
        path = os.path.join(lqconfig_qt.schejslocaldir_p, subdir)
        if os.path.isdir(path):
            files.extend(fileUtil.dirFiles(path, []))
    return files


def _schedule_work_files():
    if os.path.isdir(lqconfig_qt.schedule_js_work_dir):
        return fileUtil.dirFiles(lqconfig_qt.schedule_js_work_dir, [])
    return []


def upSchedule():
    fileUtil.logLine(lqconfig_qt.update_log, "start parse lq schedule js")
    print(getNowTime() + ' start parse lq schedule js')
    last_update_local = _get_task_time('schedule')
    update_time_sche = getNowTime()

    pending_files = _schedule_work_files()
    pending_files.extend(_pending_files(*lqconfig_qt.schedule_js_legacy_pending_dirs))
    for file in pending_files:
        print('start update schedule file: ' + file)
        is_updated = upScheduleByFile(file, 0, last_update_local)
        if is_updated and os.path.exists(file):
            os.remove(file)

    print(getNowTime() + ' finish parse lq schedule js')
    sql_util.upData('lq_note', {'lastUpdateTime': update_time_sche}, {'task': 'schedule'})


def upScheduleOfLeague(sclassID, kindtype):
    filelist = LQleague.getLocalfiles(sclassID, kindtype)
    update_time_local = _get_task_time('schedule')
    for file in filelist:
        upScheduleByFile(file, 1, update_time_local)


def upScheduleByFile(file, flag, updateTime_local):
    isUpdated = False
    matchlist = getMatchFromFile(file)
    isfinished = 2
    filename = os.path.basename(file)
    kindType = filename[0]
    if kindType == 'l':
        data = filename.split('_')
        matchkind = data[1][0]
    else:
        matchkind = '0'

    for match in matchlist:
        matchtime = datetime.strptime(match['matchTime'], "%Y-%m-%d %H:%M")
        between = (updateTime_local - matchtime).days
        if flag == 1 and between >= 1300 and match['matchState'] == -1:
            pass
        else:
            MatchDao.upMachByOne(match)
        if match['matchState'] not in [-1, -4]:
            isfinished = 1

    if isfinished == 2 and matchkind == '1':
        tag_mainten.upScheTaskByFlag(file, isfinished)
    if len(matchlist) > 0:
        isUpdated = True
    return isUpdated
