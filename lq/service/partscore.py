# 按照联赛ID和联赛类型，通过本地赛程JS文件更新赛程信息
from datetime import datetime, timedelta
from typing import Any, Tuple, cast

from config import lqconfig_qt
from crawler.qt.lq_score_crawler import get_part_score
from lq.dao import MatchDao
from lq.parshtml import part_score
from utils import sql_util, fileUtil
from utils.dateUtil import getNowTime


# 五、完场和正在进行比赛，小节比分信息；
def upPartscore():
    # 比赛开始时间小于等于当前时间 且 比分采集状态为0 的比赛
    # current_time = "'" + CommonUtil.gettime() + "'"
    fileUtil.logLine(lqconfig_qt.update_log, ['开始篮球更新小节比分'])
    now = datetime.now()
    time0 = "'" + now.strftime("%Y-%m-%d %H:%M:%S") + "'"
    time1 = "'" + (now + timedelta(days=-60)).strftime("%Y-%m-%d %H:%M:%S") + "'"
    # time1 = "'2008-01-01 00:00'"
    # 采集任务未完成，且比赛状态完场或进行中，且比赛日期小于当前时间
    incomplete_finished_score = (
        "matchState=-1 and partscore_f=2 and "
        "(homeScore1 is null or homeScore2 is null or homeScore3 is null or homeScore4 is null "
        "or awayScore1 is null or awayScore2 is null or awayScore3 is null or awayScore4 is null)"
    )
    sql = "SELECT scheduleID, leagueId, matchState,matchTime FROM `lq_schedule` WHERE matchState >= -1 " + \
          "and (partscore_f in(0,1) or (" + incomplete_finished_score + "))" + \
          "AND matchTime <=" + time0 + " AND matchtime >= " + time1 + " ORDER BY matchTime DESC"
    # print(sql)
    matchs = sql_util.select(sql)
    size = len(matchs)
    print("开始更新小节比分：" + str(size))
    for match in matchs:
        matchstate = match[2]
        condition = {'scheduleID': match[0]}
        partdict = part_score.get_PartScore(match[0])
        if matchstate in (-1, -4):
            # partdict['MatchState'] = matchstate
            partdict['partscore_f'] = 2
        if len(partdict) > 0:
            sql_util.upData('lq_schedule', partdict, condition)
        size = size - 1
        print("比分待更新数量：" + str(size))
    print(getNowTime() + " 比分更新成功")


# 根据联赛ID和赛季更新小节比分
def upPartScore(leagueID, seasons):
    matchList: Tuple[Tuple[Any, ...], ...] = ()
    if seasons == '':
        condition = {'leagueID': leagueID}
        matchList = cast(Tuple[Tuple[Any, ...], ...], MatchDao.selectMatch(condition))
    else:
        for season in seasons:
            condition = {'leagueID': leagueID, 'matchSeason': season}
            matchList = matchList + cast(Tuple[Tuple[Any, ...], ...], MatchDao.selectMatch(condition))
    print("比赛数量：" + str(len(matchList)))
    for match in matchList:
        matchID = match[0]
        partdDct = get_part_score(matchID)
        sql_util.upData('lq_schedule', partdDct, {'scheduleID': matchID})
    print("小节比分更新成功；" + "联赛：" + str(leagueID) + "赛季：" + ",".join(seasons))




