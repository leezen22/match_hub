# 按照联赛和联赛类型解析本地赛程信息,全量更新到数据库
import datetime

from crawler.qt.lq_score_crawler import get_part_score
from utils import sql_util


# from src.lq.lq_score_crawler import get_PartScore

# 根据字典参数筛选
def selectMatch(condition):
    results = sql_util.select_table_rows(
        'lq_schedule',
        ['scheduleID', 'leagueId', 'matchSeason', 'matchState', 'partscore_f', 'asianodds_f', 'totalodds_f', 'matchID'],
        condition,
        isDis=True,
    )
    return results


# 解析赛程JS文件获取赛程信息，执行判断更新
def upMatchBychejs(matchlist):
    for match in matchlist:
        upMachByOne(match)


def upMachByOne(match):
    results = sql_util.select_table_rows(
        'lq_schedule',
        ['scheduleID', 'matchState', 'matchTime'],
        {'scheduleID': match['scheduleID']},
        isDis=True,
    )
    condition = {'scheduleID': match['scheduleID']}
    # 比赛未入本地库
    if len(results) == 0:
        sql_util.insertData('lq_schedule', match)
    # 如果比赛未开始，但比赛改期，也需要更新
    elif match['matchState'] == 0 and datetime.datetime.strptime(match['matchTime'], "%Y-%m-%d %H:%M") != results[0][2]:
        # results[0][2]:
        sql_util.upData('lq_schedule', match, condition)
    # 比赛已入库，最新完场或异常， 比赛未开或进行中,不更新。
    elif match['matchState'] < 0 and match['matchState'] != results[0][1] and results[0][1] != -6:
        sql_util.upData('lq_schedule', match, condition)


# 比赛不存在，插入更新比赛
def InSchedule(matchlist):
    for match in matchlist:
        sql_util.insertDatas('lq_schedule', [match])


# 完善比赛小节和加时比分呢
def UpPartScore(matchlist):
    quarterscores = []
    conditions = []
    for match in matchlist:
        quarterdict = get_part_score(match[0])
        quarterscores.append(quarterdict)
        conditions.append({'scheduleID': match[0]})
    sql_util.updateData('lq_schedule', quarterscores, conditions)
