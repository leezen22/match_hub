import random
import time
from datetime import datetime
from datetime import timedelta
from typing import Any, Tuple, cast

from lq.dao import MatchDao
from lq.parshtml import odds_asian
from utils import sql_util


# 根据比赛ID更细亚指让分 初盘/终盘 赔率
def upAsianOddsBymid(scheduleID, finished):
    asianOddsDict = odds_asian.get_asianodds(scheduleID)
    print("{0},{1}".format(scheduleID, asianOddsDict))
    if asianOddsDict['state'] != 0:
        if len(asianOddsDict['odds']) > 0:
            sql_util.upData('lq_schedule', {'asianodds_f': 1}, {'scheduleID': scheduleID})
            if finished == 0:
                sql_util.insertDatas('lq_asianOdds', asianOddsDict['odds'])
            elif finished == 1:
                for asianOdds in asianOddsDict['odds']:
                    results = cast(Tuple[Tuple[Any, ...], ...],
                                   sql_util.select_table_rows(
                                       'lq_asianOdds',
                                       ['oddsID'],
                                       {'scheduleID': asianOdds['ScheduleID'],
                                        'companyID': asianOdds['CompanyID']},
                                       isDis=True,
                                   ))
                    asianOdds['modifyTime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if len(results) > 0:
                        condition = {'scheduleID': asianOdds['ScheduleID'], 'companyID': asianOdds['CompanyID']}
                        sql_util.upData('lq_asianOdds', asianOdds, condition)
                    else:
                        sql_util.insertData('lq_asianOdds', asianOdds)
            else:
                pass
        if asianOddsDict['matchstate'] in (-1, -4):
            sql_util.upData('lq_schedule', {'asianodds_f': 2}, {'scheduleID': scheduleID})


def upAsianOddsByMatchs(matchs):
    matchs_size = len(matchs)
    for match in matchs:
        if match[5] != 2:
            upAsianOddsBymid(match[0], match[5])
            # time.sleep(random.uniform(1, 3))
        matchs_size = matchs_size -1
        time.sleep(random.uniform(1, 3))
        print("让分剩余比赛数量：" + str(matchs_size))


# 根据联赛ID和赛季列表删除让分指数及其变化记录
def delAsianOdds(leagueId, seasons):
    for season in seasons:
        condition = {'leagueId': leagueId, 'matchSeason': season}
        matchs = cast(Tuple[Tuple[Any, ...], ...], MatchDao.selectMatch(condition))
        for match in matchs:
            delAsianOddsBymid(match[0])


# 根据比赛ID删除让分赔率信息
def delAsianOddsBymid(matchid):
    oddslist = cast(Tuple[Tuple[Any, ...], ...],
                    sql_util.select_table_rows(
                        'lq_AsianOdds',
                        ['oddsID', 'scheduleID', 'companyID'],
                        {'scheduleID': matchid},
                        isDis=True,
                    ))
    for odds in oddslist:
        sql_util.delData('asianOddsdetail', {'oddsID': odds[0]})
    sql_util.delData('lq_asianOdds', {'scheduleID': matchid})


# if __name__ == '__main__':
#     upAsianOddsBymid(664161, 1)
#     now = datetime.now()
#     # time = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
#     # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"
#     time2 = "'" + (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S") + "'"
#     asiansql = "SELECT scheduleId, leagueId,MatchState,MatchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
#                " WHERE asianodds_f in(0,1) and MatchState>=-1 and leagueID in (1,2,5,7,14,15,19,25) and MatchTime < " + time2
#     # totalsql = "SELECT scheduleID,leagueId,MatchState,MatchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`"\
#     #            " WHERE totalodds_f in(0,1) and MatchState>=-2  and leagueID=2 and MatchTime < " + time2
#     matchs = sql_util.select(asiansql)
#     # threads = []
#     # 更新让分赔率线程
#     if len(matchs) > 0:
#         upAsianOddsByMatchs(matchs)
