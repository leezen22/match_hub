from datetime import datetime
from utils import sql_util


def upMatchByOne(match):
    results = sql_util.select_table_rows(
        'zq_schedule',
        ['ScheduleID', 'MatchState', 'MatchTime'],
        {'ScheduleID': match['ScheduleID']},
        isDis=True,
    )
    # 比赛已入库
    if len(results) > 0:
        condition = {'ScheduleID': match['ScheduleID']}
        if match['MatchState'] == 0 and datetime.strptime(match['MatchTime'], "%Y-%m-%d %H:%M") != results[0][2]:
            sql_util.upData('zq_schedule', match, condition)
        # 比赛完场或异常
        elif match['MatchState'] < 0:
            sql_util.upData('zq_schedule', match, condition)
    # 比赛未入本地库
    else:
        sql_util.insertData('zq_schedule', match)
