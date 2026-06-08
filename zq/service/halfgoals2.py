import datetime
import time
from crawler.qt.zq_halfodds_crawler import get_halfodds_goals
from utils import sql_util


def update_halfgoals():
    sql = "SELECT matchID, scheduleID,leagueID,matchTime,homeScore,awayScore,homeHalf,awayHalf,matchState,halfgoals_f " \
          "FROM zq_schedule " \
          "WHERE matchState=-1 and halfgoals_f=0 and matchTime >= '2024-01-01 00:00' " \
          "order by matchTime ASC"
    results = sql_util.select_rows(sql)
    print("更新比赛数量：{0}".format(len(results)))
    for item in results:
        schedulID = item[1]
        # matchState = item[8]
        sqltemp1 = "SELECT COUNT(*) FROM zq_halfgoals_3 where scheduleID = {0}".format(schedulID)
        count = sql_util.select_rows(sqltemp1)[0][0]
        oddsdata = get_halfodds_goals(schedulID, 3)
        if count > 0:
            pass
        elif oddsdata is not None:
            oddsArr = oddsdata.reverse()
            odds_items = []
            for i in range(0, len(oddsArr)):
                odds_dict = {'MatchID': item[0], 'ScheduleID': schedulID, 'CompanyID': 3,
                             'HomeOdds': oddsArr[i]['HomeOdds'], 'PanKou': oddsArr[i]['PanKou'],
                             'AwayOdds': oddsArr[i]['AwayOdds'], 'MatchState': 1}
                strp_time = oddsArr[i]['ModifyTime']
                if oddsArr[i]['IsClosed'] == '封':
                    odds_dict['IsClosed'] = 1
                else:
                    odds_dict['IsClosed'] = 0
                odds_dict['HomeScore'] = 0
                odds_dict['AwayScore'] = 0
                if oddsArr[i]['Score'] == '早':
                    odds_dict['OddsType'] = 0
                elif oddsArr[i]['Score'] == '即':
                    odds_dict['OddsType'] = 1
                else:
                    odds_dict['OddsType'] = 2
                    goalsArr = oddsArr[i]['Score'].split('-')
                    odds_dict['HomeScore'] = goalsArr[0]
                    odds_dict['AwayScore'] = goalsArr[1]
                if len(oddsArr[i]['HappenTime']) == 0:
                    odds_dict['HappenTime'] = 0
                elif oddsArr[i]['HappenTime'] == '中场':
                    odds_dict['HappenTime'] = 45
                    odds_dict['MatchState'] = 2
                else:
                    odds_dict['HappenTime'] = int(oddsArr[i]['HappenTime'])
                odds_dict['ModifyTime'] = datetime.datetime(int(strp_time[0:4]), int(strp_time[4:6]),
                                                            int(strp_time[6:8]), int(strp_time[8:10]),
                                                            int(strp_time[10:12]), int(strp_time[12:14]))
                odds_items.append(
                    [odds_dict['MatchID'], odds_dict['ScheduleID'], odds_dict['CompanyID'], odds_dict['OddsType'],
                     odds_dict['HappenTime'], odds_dict['HomeOdds'],
                     odds_dict['PanKou'], odds_dict['AwayOdds'], odds_dict['HomeScore'], odds_dict['AwayScore'],
                     odds_dict['IsClosed'], odds_dict['ModifyTime'], odds_dict['MatchState']])
                keys = ['MatchID', 'ScheduleID', 'CompanyID', 'OddsType', 'HappenTime', 'HomeOdds', 'PanKou',
                        'AwayOdds', 'HomeScore', 'AwayScore', 'IsClosed', 'ModifyTime', 'MatchState']
            if len(odds_items) > 0:
                sql_util.insetMany('zq_halfgoals_3', keys, odds_items)
                selct1 = " select from zq_schedule2 where"
                sqltemp1 = "update zq_schedule set halfgoals_f =2 where scheduleID= {0}".format(schedulID)
                sql_util.sqlExecute(sqltemp1)
            else:
                sqltemp1 = "update zq_schedule set halfgoals_f =3 where scheduleID= {0}".format(schedulID)
                sql_util.sqlExecute(sqltemp1)
            print(odds_items)
            # keys = ['AwayOdds', 'HappenTime', 'HomeOdds', 'IsClosed','ModifyTime', 'PanKou', 'HomeScore', 'AwayScore', 'scheduleID']
        else:
            sqltemp1 = "update zq_schedule set halfgoals_f =4 where scheduleID= {0}".format(schedulID)
            sql_util.sqlExecute(sqltemp1)
        time.sleep(1)


def judge_half_result(scheduleID):
    sql = "SELECT MatchID,ScheduleID,CompanyID,OddsType,HappenTime,HomeOdds,PanKou,AwayOdds,HomeScore,AwayScore,IsClosed,ModifyTime,MatchState,OddsType " \
          "FROM zq_halfgoals_3 " \
          "WHERE scheduleID={0} and PanKou >0 " \
          "ORDER BY ID ASC".format(scheduleID)
    stdict = {'ScheduleID': scheduleID, 'Hith1': 0, 'HappenTimeh1': 0, 'HomeScoreh1': 0, 'AwayScoreh1': 0, 'HomeOddsh1':0, 'PanKouh1': 0, 'AwayOddsh1': 0, 'Yieldh1': 0,
              'Hith75': 0, 'HappenTimeh75': 0, 'HomeScoreh75': 0, 'AwayScoreh75': 0, 'HomeOddsh75': 0, 'PanKouh75': 0, 'AwayOddsh75': 0, 'Yieldh75': 0,
              'Hith05': 0, 'HappenTimeh05': 0, 'HomeScoreh05': 0, 'AwayScoreh05': 0, 'HomeOddsh05': 0, 'PanKouh05': 0, 'AwayOddsh05': 0, 'Yieldh05': 0,
              'EarlyHomeOddsHalf': 0, 'EarlyPanKouHalf': 0, 'EarlyAwayOddsHalf': 0}
    odds_data = sql_util.select(sql, True)
    if len(odds_data) > 0 and odds_data[0]['OddsType'] != 2:
        early_odds = odds_data[0]
        stdict['EarlyHomeOddsHalf'] = early_odds['HomeOdds']
        stdict['EarlyPanKouHalf'] = early_odds['PanKou']
        stdict['EarlyAwayOddsHalf'] = early_odds['AwayOdds']

    for item in odds_data:
        goal_diff = float(item['PanKou']) - item['HomeScore'] - item['AwayScore']
        if stdict['Hith1'] == 0 and item['OddsType'] == 2:
            if 0 < goal_diff < 1:
                # msg = "上半场盘口偏小1：" + str(scheduleID)
                # print(msg)
                break
            elif int(item['HappenTime']) < 15 and goal_diff == 1:
                # msg = "上半场提前降盘1：" + str(scheduleID)
                # print(msg)
                break
            elif int(item['HappenTime']) >= 15 and goal_diff == 1:
                # msg = "上半场触发策略1：" + str(scheduleID)
                # print(msg)
                stdict['HomeScoreh1'] = item['HomeScore']
                stdict['AwayScoreh1'] = item['AwayScore']
                stdict['HomeOddsh1'] = item['HomeOdds']
                stdict['PanKouh1'] = item['PanKou']
                stdict['AwayOddsh1'] = item['AwayOdds']
                stdict['HappenTimeh1'] = item['HappenTime']
                stdict['Hith1'] = 1
        elif stdict['Hith1'] == 1 and stdict['Hith75'] == 0:
            if goal_diff < 0.75:
                # msg = "上半场盘口偏小0.75：" + str(scheduleID)
                # print(msg)
                break
            elif goal_diff == 0.75:
                # msg = "上半场触发策略75：" + str(scheduleID)
                # print(msg)
                stdict['HomeScoreh75'] = item['HomeScore']
                stdict['AwayScoreh75'] = item['AwayScore']
                stdict['HomeOddsh75'] = item['HomeOdds']
                stdict['PanKouh75'] = item['PanKou']
                stdict['AwayOddsh75'] = item['AwayOdds']
                stdict['HappenTimeh75'] = item['HappenTime']
                stdict['Hith75'] = 1

        elif stdict['Hith1'] == 1 and stdict['Hith75'] == 1 and stdict['Hith05'] == 0:
            if goal_diff < 0.5:
                # msg = "上半场盘口偏小0.5：" + str(scheduleID)
                # print(msg)
                break
            elif goal_diff == 0.5:
                # msg = "上半场触发策略0.5：" + str(scheduleID)
                # print(msg)
                stdict['HomeScoreh05'] = item['HomeScore']
                stdict['AwayScoreh05'] = item['AwayScore']
                stdict['HomeOddsh05'] = item['HomeOdds']
                stdict['PanKouh05'] = item['PanKou']
                stdict['AwayOddsh05'] = item['AwayOdds']
                stdict['HappenTimeh05'] = item['HappenTime']
                stdict['Hith05'] = 1
                break
    return stdict


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


def update_st_results():

    sql1 = "SELECT DISTINCT h.ScheduleID From (SELECT h3.ScheduleID " \
           "FROM zq_halfgoals_3 as h3 left JOIN zq_schedule as zs on h3.ScheduleID = zs.ScheduleID " \
           "WHERE zs.st_half_f=0 and zs.matchState=-1 ORDER BY zs.matchTime ASC) as h"
    results1 = sql_util.select(sql1)
    print("剩余比赛数量：{0}".format(len(results1)))
    for match in results1:
        scheduleID = match[0]
        sql2 = "SELECT zc.MatchID,zc.ScheduleID,zc.LeagueID,zc.HomeScore,zc.AwayScore,zc.HomeHalf,zc.AwayHalf,zc.MatchTime,zl.nameChsShort " \
               "FROM zq_schedule as zc " \
               "LEFT JOIN zq_league as zl on zc.LeagueID = zl.LeagueID " \
               "WHERE zc.ScheduleID = {0}".format(scheduleID)
        results2 = sql_util.select(sql2, True)
        item = results2[0]
        mdict = judge_half_result(item['ScheduleID'])
        if mdict['Hith1'] == 1:
            mdict['MatchID'] = item['MatchID']
            mdict['LeagueID'] = item['LeagueID']
            mdict['HomeScore'] = item['HomeScore']
            mdict['AwayScore'] = item['AwayScore']
            mdict['HomeHalfScore'] = item['HomeHalf']
            mdict['AwayHalfScore'] = item['AwayHalf']
            mdict['MatchTime'] = item['MatchTime']
            mdict['WeekDay'] = item['MatchTime'].weekday() + 1
            mdict['LeagueName'] = item['nameChsShort']
            goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['PanKouh1']
            mdict['Yieldh1'] = cal_yield(goal_diff)
            if mdict['Hith75'] == 1:
                goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['PanKouh75']
                mdict['Yieldh75'] = cal_yield(goal_diff)
            if mdict['Hith05'] == 1:
                goal_diff = item['HomeHalf'] + item['AwayHalf'] - mdict['PanKouh05']
                mdict['Yieldh05'] = cal_yield(goal_diff)
            print(mdict)
            sql_util.insertData('zq_st_half', mdict, None, isDict=True)
        up_sql = "Update zq_schedule set st_half_f=1 WHERE ScheduleID ={0}".format(item['ScheduleID'])
        sql_util.sqlExecute(up_sql)


# if __name__ == '__main__':
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
    #     if mdict['Hith75'] == 1:
    #         "SELECT MatchID, ScheduleID,LeagueID,HomeScore,AwayScore,HomeHalf,AwayHalf,MatchTime From "
    #         print(mdict)
    # arr = ['2538477', '2543445', '2543444', '2534172', '2544022', '2544148', '2544050']
    # for scheduleID in arr:
    #     mdict = judge_half_result(scheduleID)
    #     print(mdict)
















