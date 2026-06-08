import random
import time
from datetime import datetime, timedelta
from typing import Any, Tuple, cast

from lq.dao import MatchDao
from lq.parshtml import odds_total
from utils import sql_util


def upTotalOddsBymatchs(matchs):
    matchs_size = len(matchs)
    for match in matchs:
        if match[6] != 2:
            # 比赛ID，更新状态
            upTotalOddsBymid(match[0], match[6])
        matchs_size = matchs_size -1
        print("总分剩余比赛数量：" + str(matchs_size))
        time.sleep(random.uniform(1, 3))

# 根据比赛ID更新大小 初盘/终盘 赔率
def upTotalOddsBymid(scheduleID, finished):
    totaloddsdict = odds_total.get_overdown(scheduleID)
    print("{0},{1}".format(scheduleID, totaloddsdict))
    if totaloddsdict['state'] != 0:
        if len(totaloddsdict['odds']) > 0:
            sql_util.upData('lq_schedule', {'totalodds_f': 1}, {'scheduleID': scheduleID})
            if finished == 0:
                sql_util.insertDatas('lq_totalodds', totaloddsdict['odds'])
            else:
                for odds in totaloddsdict['odds']:
                    results = cast(Tuple[Tuple[Any, ...], ...],
                                   sql_util.select_table_rows(
                                       'lq_totalodds',
                                       ['OddsID'],
                                       {'ScheduleID': odds['ScheduleID'],
                                        'CompanyID': odds['CompanyID']},
                                       isDis=True,
                                   ))
                    odds['ModifyTime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if len(results) > 0:
                        condition = {'ScheduleID': odds['ScheduleID'], 'CompanyID': odds['CompanyID']}
                        sql_util.upData('lq_totalodds', odds, condition)
                    else:
                        sql_util.insertData('lq_totalodds', odds)
        if totaloddsdict['matchstate'] in [-1, -4]:
            sql_util.upData('lq_schedule', {'totalodds_f': 2}, {'scheduleID': scheduleID})
    # SqlUtil.insertDatas('totalscore', oddslist)


# 根据联赛ID和赛季列表删除大小指数及其变化记录
def deltotalOdds(leagueId, seasons):
    for season in seasons:
        condition = {'leagueId': leagueId, 'MatchSeason': season}
        matchs = cast(Tuple[Tuple[Any, ...], ...], MatchDao.selectMatch(condition))
        for match in matchs:
            deltotalOddsBymid(match[0])


# 根据比赛ID删除让分赔率信息
def deltotalOddsBymid(matchid):
    oddslist = cast(Tuple[Tuple[Any, ...], ...],
                    sql_util.select_table_rows(
                        'lq_totalodds',
                        ['OddsID', 'ScheduleID', 'CompanyID'],
                        {'ScheduleID': matchid},
                        isDis=True,
                    ))
    print("删除让分指数：")
    print(oddslist)
    for odds in oddslist:
        sql_util.delData('lq_totaloddsdetail', {'OddsID': odds[0]})
    sql_util.delData('lq_totalodds', {'ScheduleID': matchid})


if __name__ == '__main__':
    upTotalOddsBymid(664161, 0)
#     now = datetime.now()
#     # time = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
#     # time1 = "'" + (now + timedelta(hours=-4)).strftime("%Y-%m-%d %H:%M:%S") + "'"
#     time2 = "'" + (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S") + "'"
#     #
#     # asiansql = "SELECT scheduleId, leagueId,MatchState,MatchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`" \
#     #            " WHERE asianodds_f in(0,1) and MatchState>=-1 and MatchTime < " + time2
#     totalsql = "SELECT scheduleID,leagueId,MatchState,MatchTime,partscore_f,asianodds_f,totalodds_f FROM `lq_schedule`"\
#                " WHERE totalodds_f in(0,1) and MatchState>=-2  and leagueID in (1,2,5,7,14,15,19,25)  and MatchTime < " + time2
#     matchs = sql_util.select(totalsql)
#     threads = []
#     # 更新让分赔率线程
#     if len(matchs) > 0:
#         upOddsBymatchs(matchs)
