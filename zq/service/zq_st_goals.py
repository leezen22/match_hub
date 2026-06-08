from crawler.qt.zq_score_crawler import ScoreCrawler
from utils import sql_util


class TotalStZq(object):

    @staticmethod
    def update_half_st(start_time=None):

        if start_time:
            str_start = "and zs.MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''

        sql1 = "SELECT DISTINCT h.ScheduleID From (SELECT h3.ScheduleID " \
               "FROM zq_halfgoals_3 as h3 left JOIN zq_schedule as zs on h3.ScheduleID = zs.ScheduleID " \
               "WHERE zs.st_half_f=0 and HomeHalf is not NULL and zs.matchState=-1 {0} ORDER BY zs.matchTime ASC) as h".format(str_start)
        results1 = sql_util.select(sql1)
        print("上半场策略待判断数量：{0}".format(len(results1)))
        for match in results1:
            scheduleID = match[0]
            sql2 = "SELECT zc.MatchID,zc.ScheduleID,zc.LeagueID,zc.HomeScore,zc.AwayScore,zc.HomeHalf,zc.AwayHalf,zc.MatchTime,zl.nameChsShort " \
                   "FROM zq_schedule as zc " \
                   "LEFT JOIN zq_league as zl on zc.LeagueID = zl.LeagueID " \
                   "WHERE zc.ScheduleID = {0}".format(scheduleID)
            results2 = sql_util.select(sql2, True)
            item = results2[0]
            mdict = TotalStZq.judge_half_result(item['ScheduleID'])
            if mdict['Hit1'] == 1:
                sql3 = "SELECT za.ScheduleID, " \
                       "za.homeOdds_F as EarlyHomeOdds, za.Goal_F as EarlyPanKou, za.AwayOdds_F as EarlyAwayOdds, " \
                       "za.homeOdds as EarlyHomeOdds2, za.Goal as EarlyPanKou2, za.AwayOdds as EarlyAwayOdds2, " \
                       "zt.HighOdds_F as EarlyHighOdds, zt.Goal_F as EarlyGoal, zt.LowOdds as EarlyLowOdds," \
                       "zt.HighOdds as EarlyHighOdds2, zt.Goal as EarlyGoal2, zt.LowOdds as EarlyLowOdds2 " \
                       "FROM zq_totalscore as zt LEFT JOIN zq_asianodds as za ON zt.scheduleID= za.scheduleID and zt.companyID=za.companyID " \
                       "WHERE za.scheduleID={0} and za.companyID=3 ".format(scheduleID)
                results3 = sql_util.select(sql3, True)
                if len(results3) > 0:
                    mdict['EarlyHighOdds'] = results3[0]['EarlyHighOdds']
                    mdict['EarlyGoal'] = results3[0]['EarlyGoal']
                    mdict['EarlyLowOdds'] = results3[0]['EarlyLowOdds']
                    mdict['EarlyHighOdds2'] = results3[0]['EarlyHighOdds2']
                    mdict['EarlyGoal2'] = results3[0]['EarlyGoal2']
                    mdict['EarlyLowOdds2'] = results3[0]['EarlyLowOdds2']
                    mdict['EarlyHomeOdds'] = results3[0]['EarlyHomeOdds']
                    mdict['EarlyPanKou'] = results3[0]['EarlyPanKou']
                    mdict['EarlyAwayOdds'] = results3[0]['EarlyAwayOdds']
                    mdict['EarlyHomeOdds2'] = results3[0]['EarlyHomeOdds2']
                    mdict['EarlyPanKou2'] = results3[0]['EarlyPanKou2']
                    mdict['EarlyAwayOdds2'] = results3[0]['EarlyAwayOdds2']
                mdict['MatchID'] = item['MatchID']
                mdict['LeagueID'] = item['LeagueID']
                mdict['HomeScore'] = item['HomeScore']
                mdict['AwayScore'] = item['AwayScore']
                mdict['HomeHalf'] = item['HomeHalf']
                mdict['AwayHalf'] = item['AwayHalf']
                mdict['MatchTime'] = item['MatchTime']
                mdict['WeekDay'] = item['MatchTime'].weekday() + 1
                mdict['LeagueName'] = item['nameChsShort']
                goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['Goal1']
                mdict['Yield1'] = cal_yield(goal_diff)
                mdict['Kind'] = 1
                if mdict['Hit75'] == 1:
                    goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['Goal75']
                    mdict['Yield75'] = cal_yield(goal_diff)
                if mdict['Hit05'] == 1:
                    goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['Goal05']
                    mdict['Yield05'] = cal_yield(goal_diff)
                print(mdict)
                sql_util.insertData('zq_st_goals', mdict, None, isDict=True)
            up_sql = "Update zq_schedule set st_half_f=1 WHERE ScheduleID ={0}".format(item['ScheduleID'])
            sql_util.sqlExecute(up_sql)

    @staticmethod
    def update_st(start_time=None):
        if start_time:
            str_start = "and zs.MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''

        sql1 = "SELECT DISTINCT ts.ScheduleID From (SELECT zt3.ScheduleID " \
               "FROM zq_totalscore_gun_3 as zt3 left JOIN zq_schedule as zs on zt3.ScheduleID = zs.ScheduleID " \
               "WHERE zs.st_f=0 and zs.matchState=-1 and zs.HomeHalf is not NULL and zs.HomeScore is not NULL {0} ORDER BY zs.matchTime ASC) as ts".format(str_start)
        results1 = sql_util.select(sql1)
        print("全场策略待判断比赛数量：{0}".format(len(results1)))
        for match in results1:
            scheduleID = match[0]
            sql2 = "SELECT zc.MatchID,zc.ScheduleID,zc.LeagueID,zc.HomeScore,zc.AwayScore,zc.HomeHalf,zc.AwayHalf,zc.MatchTime,zl.nameChsShort " \
                   "FROM zq_schedule as zc " \
                   "LEFT JOIN zq_league as zl on zc.LeagueID = zl.LeagueID and zc.HomeHalf is not NULL and zc.HomeScore is not NULL " \
                   "WHERE zc.ScheduleID = {0}".format(scheduleID)
            results2 = sql_util.select(sql2, True)
            item = results2[0]
            mdict = TotalStZq.judge_st_result(item['ScheduleID'])
            # print(mdict)
            if mdict['Hit1'] == 1:
                sql3 = "SELECT za.ScheduleID, " \
                       "za.homeOdds_F as EarlyHomeOdds, za.Goal_F as EarlyPanKou, za.AwayOdds_F as EarlyAwayOdds, " \
                       "za.homeOdds as EarlyHomeOdds2, za.Goal as EarlyPanKou2, za.AwayOdds as EarlyAwayOdds2, " \
                       "zt.HighOdds_F as EarlyHighOdds, zt.Goal_F as EarlyGoal, zt.LowOdds as EarlyLowOdds," \
                       "zt.HighOdds as EarlyHighOdds2, zt.Goal as EarlyGoal2, zt.LowOdds as EarlyLowOdds2 " \
                       "FROM zq_totalscore as zt LEFT JOIN zq_asianodds as za ON zt.scheduleID= za.scheduleID and zt.companyID=za.companyID " \
                       "WHERE za.scheduleID={0} and za.companyID=3 ".format(scheduleID)
                results3 = sql_util.select(sql3, True)
                if len(results3) > 0:
                    mdict['EarlyHighOdds'] = results3[0]['EarlyHighOdds']
                    mdict['EarlyGoal'] = results3[0]['EarlyGoal']
                    mdict['EarlyLowOdds'] = results3[0]['EarlyLowOdds']
                    mdict['EarlyHighOdds2'] = results3[0]['EarlyHighOdds2']
                    mdict['EarlyGoal2'] = results3[0]['EarlyGoal2']
                    mdict['EarlyLowOdds2'] = results3[0]['EarlyLowOdds2']
                    mdict['EarlyHomeOdds'] = results3[0]['EarlyHomeOdds']
                    mdict['EarlyPanKou'] = results3[0]['EarlyPanKou']
                    mdict['EarlyAwayOdds'] = results3[0]['EarlyAwayOdds']
                    mdict['EarlyHomeOdds2'] = results3[0]['EarlyHomeOdds2']
                    mdict['EarlyPanKou2'] = results3[0]['EarlyPanKou2']
                    mdict['EarlyAwayOdds2'] = results3[0]['EarlyAwayOdds2']
                mdict['MatchID'] = item['MatchID']
                mdict['LeagueID'] = item['LeagueID']
                mdict['HomeScore'] = item['HomeScore']
                mdict['AwayScore'] = item['AwayScore']
                mdict['HomeHalf'] = item['HomeHalf']
                mdict['AwayHalf'] = item['AwayHalf']
                mdict['MatchTime'] = item['MatchTime']
                mdict['WeekDay'] = item['MatchTime'].weekday() + 1
                mdict['LeagueName'] = item['nameChsShort']
                goal_diff = item['HomeScore'] + item['AwayScore'] - mdict['Goal1']
                mdict['Yield1'] = cal_yield(goal_diff)
                mdict['Kind'] = 6
                if mdict['Hit75'] == 1:
                    goal_diff = item['HomeScore'] + item['AwayScore'] - mdict['Goal75']
                    mdict['Yield75'] = cal_yield(goal_diff)
                if mdict['Hit05'] == 1:
                    goal_diff = item['HomeScore'] + item['AwayScore'] - mdict['Goal05']
                    mdict['Yield05'] = cal_yield(goal_diff)
                print(mdict)
                sql_util.insertData('zq_st_goals', mdict, None, isDict=True)
            up_sql = "Update zq_schedule set st_f=1 WHERE ScheduleID ={0}".format(item['ScheduleID'])
            sql_util.sqlExecute(up_sql)

    @staticmethod
    def judge_half_result(scheduleID):
        sql = "SELECT MatchID,ScheduleID,CompanyID,OddsType,HappenTime,HighOdds,Goal,LowOdds,HomeScore,AwayScore,IsBet,ModifyTime,MatchState,OddsType " \
              "FROM zq_halfgoals_3 " \
              "WHERE scheduleID={0} and Goal >0 " \
              "ORDER BY ID ASC".format(scheduleID)
        stdict = {'ScheduleID': scheduleID, 'Hit1': 0, 'HappenTime1': 0, 'HomeScore1': 0, 'AwayScore1': 0,
                  'HighOdds1': 0, 'Goal1': 0, 'LowOdds1': 0, 'Yield1': 0,
                  'Hit75': 0, 'HappenTime75': 0, 'HomeScore75': 0, 'AwayScore75': 0, 'HighOdds75': 0, 'Goal75': 0,
                  'LowOdds75': 0, 'Yield75': 0,
                  'Hit05': 0, 'HappenTime05': 0, 'HomeScore05': 0, 'AwayScore05': 0, 'HighOdds05': 0, 'Goal05': 0,
                  'LowOdds05': 0, 'Yield05': 0,
                  'EarlyHighOddsHalf': 0, 'EarlyGoalHalf': 0, 'EarlyLowOddsHalf': 0, 'EarlyHighOddsHalf2': 0,
                  'EarlyGoalHalf2': 0, 'EarlyLowOddsHalf2': 0}
        odds_data = sql_util.select(sql, True)
        if len(odds_data) > 0 and odds_data[0]['OddsType'] in [0,1]:
            early_odds = odds_data[0]
            stdict['EarlyHighOddsHalf'] = early_odds['HighOdds']
            stdict['EarlyGoalHalf'] = early_odds['Goal']
            stdict['EarlyLowOddsHalf'] = early_odds['LowOdds']
        for item in odds_data:
            goal_diff = float(item['Goal']) - item['HomeScore'] - item['AwayScore']
            if item['IsBet'] == 0:
                pass
            elif item['OddsType'] == 1:
                stdict['EarlyHighOddsHalf2'] = item['HighOdds']
                stdict['EarlyGoalHalf2'] = item['Goal']
                stdict['EarlyLowOddsHalf2'] = item['LowOdds']
            elif stdict['Hit1'] == 0 and item['OddsType'] == 2:
                if 0 < goal_diff < 1:
                    # msg = "上半场盘口偏小1：" + str(scheduleID)
                    # print(msg)
                    break
                # elif int(item['HappenTime']) < 1 and goal_diff == 1:
                #     # msg = "上半场提前降盘1：" + str(scheduleID)
                #     # print(msg)
                #     break
                elif int(item['HappenTime']) >= 0 and goal_diff == 1:
                    # msg = "上半场触发策略1：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore1'] = item['HomeScore']
                    stdict['AwayScore1'] = item['AwayScore']
                    stdict['HighOdds1'] = item['HighOdds']
                    stdict['Goal1'] = item['Goal']
                    stdict['LowOdds1'] = item['LowOdds']
                    stdict['HappenTime1'] = item['HappenTime']
                    stdict['Hit1'] = 1
            elif stdict['Hit1'] == 1 and item['OddsType'] == 2 and stdict['Hit75'] == 0:
                if 0 < goal_diff < 0.75:
                    # msg = "上半场盘口偏小0.75：" + str(scheduleID)
                    # print(msg)
                    break
                elif goal_diff == 0.75:
                    # msg = "上半场触发策略75：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore75'] = item['HomeScore']
                    stdict['AwayScore75'] = item['AwayScore']
                    stdict['HighOdds75'] = item['HighOdds']
                    stdict['Goal75'] = item['Goal']
                    stdict['LowOdds75'] = item['LowOdds']
                    stdict['HappenTime75'] = item['HappenTime']
                    stdict['Hit75'] = 1
            elif stdict['Hit1'] == 1 and item['OddsType'] == 2 and stdict['Hit75'] == 1 and stdict['Hit05'] == 0:
                if 0 < goal_diff < 0.5:
                    # msg = "上半场盘口偏小0.5：" + str(scheduleID)
                    # print(msg)
                    break
                elif goal_diff == 0.5:
                    # msg = "上半场触发策略0.5：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore05'] = item['HomeScore']
                    stdict['AwayScore05'] = item['AwayScore']
                    stdict['HighOdds05'] = item['HighOdds']
                    stdict['Goal05'] = item['Goal']
                    stdict['LowOdds05'] = item['LowOdds']
                    stdict['HappenTime05'] = item['HappenTime']
                    stdict['Hit05'] = 1
                    break
        return stdict

    @staticmethod
    def judge_st_result(scheduleID):
        sql = "SELECT MatchID,ScheduleID,CompanyID,OddsType,HappenTime,HighOdds,Goal,LowOdds,HomeScore,AwayScore,IsBet,ModifyTime,MatchState,OddsType " \
              "FROM zq_totalscore_gun_3 " \
              "WHERE scheduleID={0} and Goal >0 " \
              "ORDER BY ID ASC".format(scheduleID)
        stdict = {'ScheduleID': scheduleID, 'Hit1': 0, 'HappenTime1': 0, 'HomeScore1': 0, 'AwayScore1': 0,
                  'HighOdds1': 0, 'Goal1': 0, 'LowOdds1': 0, 'Yield1': 0,
                  'Hit75': 0, 'HappenTime75': 0, 'HomeScore75': 0, 'AwayScore75': 0, 'HighOdds75': 0, 'Goal75': 0,
                  'LowOdds75': 0, 'Yield75': 0,
                  'Hit05': 0, 'HappenTime05': 0, 'HomeScore05': 0, 'AwayScore05': 0, 'HighOdds05': 0, 'Goal05': 0,
                  'LowOdds05': 0, 'Yield05': 0,
                  'EarlyHighOdds': 0, 'EarlyGoal': 0, 'EarlyLowOdds': 0, 'EarlyHighOdds2': 0, 'EarlyGoal2': 0,
                  'EarlyLowOdds2': 0}
        odds_data = sql_util.select(sql, True)
        if len(odds_data) > 0 and odds_data[0]['OddsType'] == 0:
            early_odds = odds_data[0]
            stdict['EarlyHighOdds'] = early_odds['HighOdds']
            stdict['EarlyGoal'] = early_odds['Goal']
            stdict['EarlyLowOdds'] = early_odds['LowOdds']
        for item in odds_data:
            goal_diff = float(item['Goal']) - item['HomeScore'] - item['AwayScore']
            if item['IsBet'] == 0:
                pass
            elif item['OddsType'] == 1:
                stdict['EarlyHighOdds2'] = item['HighOdds']
                stdict['EarlyGoal2'] = item['Goal']
                stdict['EarlyLowOdds2'] = item['LowOdds']
            elif stdict['Hit1'] == 0 and item['OddsType'] == 2:
                if 0 < goal_diff < 1:
                    # msg = "盘口偏小1：" + str(scheduleID)
                    # print(msg)
                    break
                elif item['HappenTime'] and int(item['HappenTime']) < 1 and goal_diff == 1:
                    # msg = "提前降盘1：" + str(scheduleID)
                    # print(msg)
                    break
                elif item['HappenTime'] and int(item['HappenTime']) >= 1 and goal_diff == 1:
                    # msg = "触发策略1：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore1'] = item['HomeScore']
                    stdict['AwayScore1'] = item['AwayScore']
                    stdict['HighOdds1'] = item['HighOdds']
                    stdict['Goal1'] = item['Goal']
                    stdict['LowOdds1'] = item['LowOdds']
                    stdict['HappenTime1'] = item['HappenTime']
                    stdict['Hit1'] = 1
            elif stdict['Hit1'] == 1 and item['OddsType'] == 2 and stdict['Hit75'] == 0:
                if goal_diff < 0.75:
                    # msg = "上半场盘口偏小0.75：" + str(scheduleID)
                    # print(msg)
                    break
                elif goal_diff == 0.75:
                    # msg = "上半场触发策略75：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore75'] = item['HomeScore']
                    stdict['AwayScore75'] = item['AwayScore']
                    stdict['HighOdds75'] = item['HighOdds']
                    stdict['Goal75'] = item['Goal']
                    stdict['LowOdds75'] = item['LowOdds']
                    stdict['HappenTime75'] = item['HappenTime']
                    stdict['Hit75'] = 1
            elif stdict['Hit1'] == 1 and item['OddsType'] == 2 and stdict['Hit75'] == 1 and stdict['Hit05'] == 0:
                if goal_diff < 0.5:
                    # msg = "上半场盘口偏小0.5：" + str(scheduleID)
                    # print(msg)
                    break
                elif goal_diff == 0.5:
                    # msg = "上半场触发策略0.5：" + str(scheduleID)
                    # print(msg)
                    stdict['HomeScore05'] = item['HomeScore']
                    stdict['AwayScore05'] = item['AwayScore']
                    stdict['HighOdds05'] = item['HighOdds']
                    stdict['Goal05'] = item['Goal']
                    stdict['LowOdds05'] = item['LowOdds']
                    stdict['HappenTime05'] = item['HappenTime']
                    stdict['Hit05'] = 1
                    break
        return stdict

    @staticmethod
    def judgeHit():
        sql = "SELECT ID,Kind,ScheduleID,Goal FROM zq_st_goals_hit where yield is Null or homeScore is NuLL "
        results = sql_util.select(sql, True)
        for item in results:
            scheduleID = item['ScheduleID']
            scoreCrawler = ScoreCrawler(scheduleID)
            score = scoreCrawler.qt_web_get()
            y = None
            if score == {}:
                pass
            elif score['MatchState'] == -1:
                hitDict = {'HomeScore': score['HomeScore'], 'AwayScore': score['AwayScore'],
                           'HomeHalf': score['HomeHalf'], 'AwayHalf': score['AwayHalf']}
                if item['Kind'] == 1:
                    goal_diff = score['HomeHalf'] + score['AwayHalf'] - item['Goal']
                    y = cal_yield(goal_diff)
                    hitDict['yield'] = y
                elif item['Kind'] == 6:
                    goal_diff = score['HomeScore'] + score['AwayScore'] - item['Goal']
                    y = cal_yield(goal_diff)
                    hitDict['yield'] = y
            elif score['MatchState'] == 1:
                hitDict = {}
                goal_diff = score['HomeScore'] + score['AwayScore'] - item['Goal']
                if goal_diff > 0.25:
                    hitDict['yield'] = y
            elif score['MatchState'] in [2, 3]:
                hitDict = {'HomeHalf': score['HomeHalf'], 'AwayHalf': score['AwayHalf']}
                if item['Kind'] == 1:
                    goal_diff = score['HomeHalf'] + score['AwayHalf'] - item['Goal']
                    y = cal_yield(goal_diff)
                    hitDict['yield'] = y
                if item['Kind'] == 6 and score['HomeScore'] + score['AwayScore'] - item['Goal'] > 0.25:
                    goal_diff = score['HomeScore'] + score['AwayScore'] - item['Goal']
                    y = cal_yield(goal_diff)
                    hitDict['yield'] = y
            else:
                hitDict = {}

            if y is not None and len(hitDict) > 0:
                sql_util.upData('zq_st_goals_hit', hitDict, {'ID': item['ID']})
    # @staticmethod
    # def HitByStFilter(stDict):
    #     sql = ""
    #     results = sql_util.select(sql, isdict=False)
    #     for item in results:
    #         kind = item['kind']==1:
    #
    # def HitHalf1(st):
    #     if st['']


def cal_yield(goal_diff):
    yiedld = 4
    if goal_diff < -0.25:
        yiedld = -1
    elif goal_diff == -0.25:
        yiedld = -0.5
    elif goal_diff == 0:
        yiedld = 0
    elif goal_diff == 0.25:
        yiedld = 0.5
    elif goal_diff > 0.25:
        yiedld = 1
    return yiedld


# if __name__ == '__main__':
#     TotalStZq.judgeHit()
#     sql1 = "SELECT DISTINCT ScheduleID FROM zq_st_goals"
#     results = sql_util.select(sql1)
#     for item in results:
#         scheduleID = item[0]
#         sql3 = "SELECT za.ScheduleID, " \
#                "za.homeOdds_F as EarlyHomeOdds, za.Goal_F as EarlyPanKou, za.AwayOdds_F as EarlyAwayOdds, " \
#                "za.homeOdds as EarlyHomeOdds2, za.Goal as EarlyPanKou2, za.AwayOdds as EarlyAwayOdds2, " \
#                "zt.HighOdds_F as EarlyHighOdds, zt.Goal_F as EarlyGoal, zt.LowOdds as EarlyLowOdds," \
#                "zt.HighOdds as EarlyHighOdds2, zt.Goal as EarlyGoal2, zt.LowOdds as EarlyLowOdds2 " \
#                "FROM zq_totalscore as zt LEFT JOIN zq_asianodds as za ON zt.scheduleID= za.scheduleID and zt.companyID=za.companyID " \
#                "WHERE za.scheduleID={0} and za.companyID=3 ".format(scheduleID)
#         results3 = sql_util.select(sql3, True)
#         if len(results3) > 0:
#             mdict = {}
#             mdict['EarlyHighOdds'] = results3[0]['EarlyHighOdds']
#             mdict['EarlyGoal'] = results3[0]['EarlyGoal']
#             mdict['EarlyLowOdds'] = results3[0]['EarlyLowOdds']
#             mdict['EarlyHighOdds2'] = results3[0]['EarlyHighOdds2']
#             mdict['EarlyGoal2'] = results3[0]['EarlyGoal2']
#             mdict['EarlyLowOdds2'] = results3[0]['EarlyLowOdds2']
#             mdict['EarlyHomeOdds'] = results3[0]['EarlyHomeOdds']
#             mdict['EarlyPanKou'] = results3[0]['EarlyPanKou']
#             mdict['EarlyAwayOdds'] = results3[0]['EarlyAwayOdds']
#             mdict['EarlyHomeOdds2'] = results3[0]['EarlyHomeOdds2']
#             mdict['EarlyPanKou2'] = results3[0]['EarlyPanKou2']
#             mdict['EarlyAwayOdds2'] = results3[0]['EarlyAwayOdds2']
#             sql_util.upData('zq_st_goals',mdict,{'ScheduleID':scheduleID})
#     sql3 = "SELECT za.ScheduleID, " \
#            "za.homeOdds_F as EarlyHomeOdds, za.Goal_F as EarlyPanKou, za.AwayOdds_F as EarlyAwayOdds, " \
#            "za.homeOdds as EarlyHomeOdds2, za.Goal as EarlyPanKou2, za.AwayOdds as EarlyAwayOdds2, " \
#            "zt.HighOdds_F as EarlyHighOdds, zt.Goal_F as EarlyGoal, zt.LowOdds as EarlyLowOdds," \
#            "zt.HighOdds as EarlyHighOdds2, zt.Goal as EarlyGoal2, zt.LowOdds as EarlyLowOdds2 " \
#            "FROM zq_totalscore as zt LEFT JOIN zq_asianodds as za ON zt.scheduleID= za.scheduleID and zt.companyID=za.companyID " \
#            "WHERE za.scheduleID=2389580 and za.companyID=3 "
#     print(sql3)
#     judge_half_result(2389580)
#     update_halfgoals()
#     update_st_results()
    # mdict = judge_half_result(2414473)
#   print(mdict)
    # print(datetime.datetime.now().weekday())
    # mdict = judge_half_result(2508785)
    # print()
    # sql1 = "SELECT DISTINCT scheduleID FROM zq_halfgoals_3 where oddsType=2"
    # results = sql_util_local.select(sql1)
    # for item in results:
    #     scheduleID = item[0]
    #     mdict = judge_half_result(scheduleID)
    #     if mdict['Hit75'] == 1:
    #         "SELECT MatchID, ScheduleID,LeagueID,HomeScore,AwayScore,HomeHalf,AwayHalf,MatchTime From "
    #         print(mdict)
    # arr = ['2538477', '2543445', '2543444', '2534172', '2544022', '2544148', '2544050']
    # for scheduleID in arr:
    #     mdict = judge_half_result(scheduleID)
    #     print(mdict)
















