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


def _schedule_work_files():
    if os.path.isdir(lqconfig_qt.schedule_js_work_dir):
        return fileUtil.dirFiles(lqconfig_qt.schedule_js_work_dir, [])
    return []


def upSchedule():
    fileUtil.logLine(lqconfig_qt.update_log, "start parse lq schedule js")
    print(getNowTime() + ' start parse lq schedule js')
    last_update_local = _get_task_time('schedule')
    update_time_sche = getNowTime()

    for file in _schedule_work_files():
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

    if kindType == 'l' and matchkind == '2':
        _close_removed_playoff_placeholders(matchlist)

    if isfinished == 2 and matchkind == '1':
        tag_mainten.upScheTaskByFlag(file, isfinished)
    if len(matchlist) > 0:
        isUpdated = True
    return isUpdated


def _close_removed_playoff_placeholders(matchlist):
    playoff_groups = {}
    for match in matchlist:
        playoffs_id = match.get('playoffsID')
        if playoffs_id is None:
            continue
        key = (match.get('leagueID'), match.get('matchSeason'), playoffs_id)
        playoff_groups.setdefault(key, set()).add(int(match['scheduleID']))

    for (league_id, season, playoffs_id), active_schedule_ids in playoff_groups.items():
        if not active_schedule_ids:
            continue

        schedule_ids = ",".join(str(schedule_id) for schedule_id in sorted(active_schedule_ids))
        sql = (
            "SELECT scheduleID FROM lq_schedule "
            "WHERE leagueID={league_id} and matchSeason='{season}' and playoffsID={playoffs_id} "
            "and matchState=0 and scheduleID not in ({schedule_ids})"
        ).format(
            league_id=int(league_id),
            season=sql_util.safe(str(season)),
            playoffs_id=int(playoffs_id),
            schedule_ids=schedule_ids,
        )
        stale_rows = sql_util.select_rows(sql)
        for row in stale_rows:
            schedule_id = int(row[0])
            sql_util.upData(
                'lq_schedule',
                {
                    'matchState': -4,
                    'remainTime': '',
                    'partscore_f': 2,
                    'asianodds_f': 2,
                    'totalodds_f': 2,
                    'eurOdds_f': 2,
                    'updateTime': getNowTime(),
                },
                {'scheduleID': schedule_id},
            )
            print("close removed playoff placeholder schedule: scheduleID={0}, playoffsID={1}".format(
                schedule_id,
                playoffs_id,
            ))
