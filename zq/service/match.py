from datetime import datetime
from utils import sql_util


SCHEDULE_REFRESH_FIELDS = [
    'MatchState',
    'MatchTime',
    'HomeTeamID',
    'AwayTeamID',
    'HomeTeam',
    'AwayTeam',
    'HomeScore',
    'AwayScore',
    'HomeHalf',
    'AwayHalf',
    'Home_Red',
    'Away_Red',
    'Home_order',
    'Away_order',
    'goal',
    'goalhalf',
    'total',
    'totalhalf',
    'Round',
    'Grouping',
    'groupingId',
    'grouping2',
]


def upMatchByOne(match):
    results = sql_util.select_table_dicts(
        'zq_schedule',
        ['ScheduleID'] + [field + ' AS ' + field for field in SCHEDULE_REFRESH_FIELDS],
        {'ScheduleID': match['ScheduleID']},
        isDis=True,
    )
    # 比赛已入库
    if len(results) > 0:
        condition = {'ScheduleID': match['ScheduleID']}
        if match['MatchState'] == 0 and _schedule_fields_changed(match, results[0]):
            sql_util.upData('zq_schedule', match, condition)
        # 比赛完场或异常
        elif match['MatchState'] < 0:
            sql_util.upData('zq_schedule', match, condition)
    # 比赛未入本地库
    else:
        sql_util.insertData('zq_schedule', match)


def _schedule_fields_changed(new_match, old_match):
    for field in SCHEDULE_REFRESH_FIELDS:
        if field not in new_match:
            continue
        if _normalize_schedule_value(new_match[field]) != _normalize_schedule_value(old_match.get(field)):
            return True
    return False


def _normalize_schedule_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if value is None:
        return None
    return str(value).strip()
