import os
from datetime import datetime, timedelta

from config import lqconfig_qt
from lq.dao import MatchDao
from lq.extract.MatchJS import getMatchFromFile
from lq.service.league import LQleague
from lq.service.schedulejs import (
    SCHEDULE_CRAWLER_STATE_ACTIVE,
    SCHEDULE_CRAWLER_STATE_FINISHED,
    _schedule_key_from_url,
    _season_end_year,
    mark_schedule_js_persisted,
)
from utils import fileUtil, sql_util, js2pyUtil
from utils.dateUtil import getNowTime

PRESEASON_REGULAR_SCHEDULE_FINISH_GRACE_DAYS = 14
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


def _schedule_work_files():
    if os.path.isdir(lqconfig_qt.schedule_js_work_dir):
        return fileUtil.dirFiles(lqconfig_qt.schedule_js_work_dir, [])
    return []


def upSchedule():
    fileUtil.logLine(lqconfig_qt.update_log, "start parse lq schedule js")
    print(getNowTime() + ' start parse lq schedule js')
    last_update_local = _get_task_time('schedule')
    update_time_sche = getNowTime()

    files = _schedule_work_files()
    summary = {"selected": len(files), "success": 0, "failed": 0}
    for file in files:
        print('start update schedule file: ' + file)
        is_updated = upScheduleByFile(file, 0, last_update_local)
        if is_updated:
            summary["success"] += 1
            if os.path.exists(file):
                os.remove(file)
        else:
            summary["failed"] += 1
            print('schedule file retained for retry: ' + file)

    print(getNowTime() + ' finish parse lq schedule js: ' + str(summary))
    sql_util.upData('lq_note', {'lastUpdateTime': update_time_sche}, {'task': 'schedule'})
    return summary


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

    if len(matchlist) > 0:
        isUpdated = _up_schedule_crawler_state(file, matchlist, kindType, matchkind)
    return isUpdated


def _up_schedule_crawler_state(file, matchlist, kind_type, match_kind):
    state = _resolve_schedule_crawler_state(
        matchlist,
        kind_type,
        match_kind,
        season_expired=_is_file_season_label_expired(file),
    )
    source_time = _schedule_file_source_time(file)
    if source_time is None:
        print("schedule JS persisted marker skipped, source timestamp unavailable: {0}".format(file))
        return False
    sche_key = _schedule_key_from_file(file)
    mark_schedule_js_persisted(
        sche_key,
        source_time,
        state,
        schejs_url=_schedule_url_from_file(file),
        schejs_path=file,
    )
    rows = sql_util.select_rows(
        "SELECT persistedSourceLastUpdateTime FROM lq_schedule_crawler WHERE scheKey='{0}'".format(
            sql_util.safe(sche_key)
        )
    )
    persisted_time = rows[0][0] if rows else None
    if str(persisted_time) != source_time.strftime("%Y-%m-%d %H:%M:%S"):
        print("schedule JS persisted marker failed; file retained: {0}".format(file))
        return False
    return True


def _schedule_key_from_file(file):
    return _schedule_key_from_url(_schedule_url_from_file(file))


def _schedule_url_from_file(file):
    filename = os.path.basename(file)
    season = os.path.basename(os.path.dirname(file))
    return lqconfig_qt.scheWebdir + season + '/' + filename


def _schedule_file_source_time(file):
    try:
        context = js2pyUtil.jsLocjs(file)
        value = getattr(context, 'lastUpdateTime', None)
        if value is None or str(value) == '':
            return None
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except Exception as exc:
        print("schedule JS source timestamp parse failed: {0}, error={1}".format(file, exc))
        return None


def _resolve_schedule_crawler_state(matchlist, kind_type, match_kind, season_expired=False):
    if season_expired:
        return SCHEDULE_CRAWLER_STATE_FINISHED
    if not matchlist:
        return SCHEDULE_CRAWLER_STATE_ACTIVE
    if any(match.get('matchState') not in (-1, -4) for match in matchlist):
        return SCHEDULE_CRAWLER_STATE_ACTIVE
    if not _is_schedule_past_finish_grace(matchlist, match_kind):
        return SCHEDULE_CRAWLER_STATE_ACTIVE
    return SCHEDULE_CRAWLER_STATE_FINISHED


def _is_file_season_label_expired(file):
    season_end_year = _season_end_year(os.path.basename(os.path.dirname(file)))
    if season_end_year is None:
        return False
    return season_end_year < datetime.now().year


def _is_schedule_past_finish_grace(matchlist, match_kind):
    match_times = []
    for match in matchlist:
        match_time = match.get('matchTime')
        if not match_time:
            continue
        if isinstance(match_time, datetime):
            match_times.append(match_time)
        else:
            match_times.append(datetime.strptime(str(match_time), "%Y-%m-%d %H:%M"))
    if not match_times:
        return False
    grace_days = PLAYOFF_SCHEDULE_FINISH_GRACE_DAYS if str(match_kind) == '2' else PRESEASON_REGULAR_SCHEDULE_FINISH_GRACE_DAYS
    return max(match_times) <= datetime.now() - timedelta(days=grace_days)


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
