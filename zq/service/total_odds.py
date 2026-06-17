import json
import time
from datetime import datetime

from bs4 import BeautifulSoup
from config import zqconfig_qt, common_config
from crawler.qt.zq_halfodds_crawler import get_halfodds_goals
from crawler.qt.zq_total_odds_crawler import TotalOddsCrawler
from utils import sql_util
from utils.fileUtil import logLine
from utils.webDriver import WebDriver
from utils.webUtil import WebUtil
from zq.oddsUtil_zq import OddsUtil


class TotalOddsZq(object):
    @staticmethod
    def _upsert_mobile_odds(scheduleID, oddsList):
        for odds in oddsList:
            condition = {'ScheduleID': scheduleID, 'CompanyID': odds['companyId']}
            results = sql_util.select_table_rows('zq_totalscore', ['OddsID'], condition, isDis=True)
            if len(results) > 0:
                sql_util.upData('zq_totalscore', odds, condition)
            else:
                sql_util.insertData('zq_totalscore', odds)

    @staticmethod
    def up_totalDetail(data, kind):
        matchState = data['matchState']
        companyID = data['companyId']
        count_pre = len(data['pre'])
        count_gun = len(data['gun'])
        oddsID = data['oddsId']
        hasPre = data['hasPre']
        hasGun = data['hasGun']
        hasFirst = data['hasFirst']
        hasHalf = data['hasHalf']
        hasSecond = data['hasSecond']
        total_pre_table = 'zq_totalscore_pre_{0}'.format(companyID)
        total_gun_table = 'zq_totalscore_gun_{0}'.format(companyID)

        # 采集源包含赛前+赛中，采集成功且未结束采集
        if oddsID is not None and data['state'] == 1 and kind == 2:
            if (count_pre + count_gun) > 0:
                finished_pre = data['finished_pre']
                finished_gun = data['finished_gun']
                # 防止数据紊乱，更新前先更新状态，防止下次更新数据时，数据重复
                if data['hasPre'] == 1 and finished_pre == 0:
                    finished_pre = 1
                if data['hasGun'] == 1 and finished_gun == 0:
                    finished_gun = 1

                if finished_pre != data['finished_pre'] or finished_gun != data['finished_gun']:
                    sql_util.upData('zq_totalscore',
                                    {'finished_pre': finished_pre, 'finished_gun': finished_gun},
                                    {'oddsID': oddsID})

                # ---- 插入数据范围判断，避免完全匹配更新------
                # 数据包含赛前变化记录
                if data['hasPre'] == 1 and data['finished_pre'] == 0:
                    isUpdated = sql_util.insetMany(total_pre_table, data['keys_pre'], data['pre'])
                elif data['hasPre'] == 1 and data['finished_pre'] == 1:
                    sql = "select count(*) from {0} where oddsID={1}".format(total_pre_table, oddsID)
                    old = sql_util.select(sql)
                    count_old = old[0][0]
                    if count_pre > count_old:
                        new = data['pre'][count_old:]
                        isUpdated = sql_util.insetMany(total_pre_table, data['keys_pre'], new)
                        # 不插入数据
                    else:
                        isUpdated = True
                else:
                    isUpdated = True

                if data['hasGun'] == 1 and data['finished_gun'] == 0:
                    isUpdated = sql_util.insetMany(total_gun_table, data['keys_gun'], data['gun'])
                elif data['hasGun'] == 1 and data['finished_gun'] == 1:
                    sql = "select count(*) from {0} where oddsID={1}".format(total_gun_table, oddsID)
                    old = sql_util.select(sql)
                    count_old = old[0][0]
                    if count_pre > count_old:
                        new = data['gun'][count_old:]
                        isUpdated = sql_util.insetMany(total_gun_table, data['keys_gun'], new)
                        # 不插入数据
                    else:
                        isUpdated = True
            else:
                isUpdated = True
            # 更新采集状态
            if (matchState == -1 or matchState == -10) and isUpdated:
                if data['hasGun'] == 0:
                    finished_gun = 3
                else:
                    finished_gun = 2

                if data['hasPre'] == 0:
                    finished_pre = 3
                else:
                    finished_pre = 2

                sql_util.upData('zq_totalscore',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasGun': hasGun, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})

    @staticmethod
    def insert_totalDetail_batch(data, kind):
        isUP = False
        try:
            columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal',
                       'downOdds', 'isBet', 'modifyTime']
            # 采集源包含赛前+赛中
            if kind == 2:
                isUP = sql_util.insetMany('zq_TotalScoreDetail', columns, data)
        except Exception as e:
            print(e)
        return isUP

    @staticmethod
    def up_total_detail(data, kind):
        result = False
        details = data['detail']
        finished_gun = data['finished_gun']
        finished_pre = data['finished_pre']
        matchstate = data['matchState']
        oddsID = data['oddsID']
        columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore',
                   'upOdds', 'goal', 'downOdds', 'isBet', 'modifyTime']

        # 采集源包含赛前+赛中
        if kind == 2 and data['finished_gun'] != 2:
            if data['finished_pre'] == 0:
                finished_pre = 1
            else:
                finished_pre = data['finished_pre']
            if data['finished_gun'] == 0:
                finished_gun = 1
            else:
                finished_gun = data['finished_gun']

            sql_util.upData('zq_TotalScore',
                            {'finished_pre': finished_pre, 'finished_gun': finished_gun},
                            {'oddsID': oddsID})

            # 状态未采集
            if finished_pre == 0 and data['finished_gun'] == 0:
                result = sql_util.insetMany('zq_TotalScoreDetail', columns, details)
            # 过去曾采集
            else:
                count = len(details)
                sql = "select count(*) from zq_totalScoreDetail where oddsID={0}".format(oddsID)
                old = sql_util.select_rows(sql)
                count_old = old[0][0]
                if count > count_old:
                    new = details[count_old:count]
                    result = sql_util.insetMany('zq_TotalScoreDetail', columns, new)
            if (matchstate == -1 or matchstate == -10) and result:
                sql_util.upData('zq_TotalScore', {'finished_pre': 2, 'finished_gun': 2}, {'oddsID': oddsID})

        return {'isUP': result, 'matchState': matchstate, 'finished_gun': finished_gun, 'finished_pre': finished_pre}

    @staticmethod
    def get_total_odds(match, driver, isproxy, proxy):
        result = {'state': 2, 'odds': []}
        matchID = match[0]
        homeTeam = match[10]
        awayTeam = match[11]
        headers = zqconfig_qt.headers_odds
        referer = OddsUtil.getRefer(match[4], match[6], match[3], match[5])
        headers['Referer'] = referer
        url = zqconfig_qt.totalscore_url + "?id=" + str(matchID)
        if driver:
            response = WebDriver.driver_get(url, driver)
            html = OddsUtil.get_oddshtml_driver(driver)
        else:
            response = WebUtil.requests_get(url, headers, isProxy=isproxy, proxy=proxy)
            html = response[1]
        # content = response[1]
        # driver代理异常
        if response[0] != 1 or html is None or html == '':
            result['state'] = 0
        else:
            soup = BeautifulSoup(html, 'html.parser')
            result_check = OddsUtil.TotalOddsCheck(matchID, homeTeam, awayTeam, soup)
            if result_check is False:
                result['state'] = 0
            else:
                odds_collect = OddsUtil.collect_odds(matchID, soup)
                if odds_collect['state'] == 0:
                    result['state'] = 2
                else:
                    result['state'] = 1
                    result['odds'] = odds_collect['odds']
        return result

    @staticmethod
    def get_deail(oddsid, matchid, companyid, finished_pre=None, finished_gun=None, isproxy=False):
        result = {'state': 2, 'oddsID': oddsid, 'matchID': matchid, 'companyID': companyid,
                  'finished_pre': finished_pre,
                  'finished_gun': finished_gun, 'detail': []}
        url = "{0}&scheid={1}&companyid={2}".format(zqconfig_qt.mtotaldetail_url, matchid, companyid)
        headers = zqconfig_qt.m_detail_headers
        headers['Referer'] = "{0}{1}.htm".format(zqconfig_qt.m_aisan, matchid)
        response = WebUtil.requests_get(url, headers, isProxy=isproxy, sleep=False)

        if response[0] == 1:
            try:
                details = []
                data = json.loads(response[1])

                data.reverse()
                recentFirstTime = None
                # 数量>0 且第一条记录时赛前盘口
                if len(data) > 0 and (data[0]['Score'] == '即' or data[0]['Score'] == '早'):
                    # 赔率记录完整
                    matchState = 0
                    for item in data:
                        detail = [oddsid, None, None, None, None, None, None, None, None, None, None]
                        # detail = 'oddsID', 'matchState' ,'happenTime', 'oddsType', 'homeScore', 'awayScore',
                        # 'upOdds', 'goal', 'downOdds',
                        # 'isBet', 'modifyTime',
                        # 比赛状态，发生时间
                        if item['ModifyTime'] != '':
                            modifyTime = datetime.strptime(item['ModifyTime'], '%Y%m%d%H%M%S')
                            detail[10] = modifyTime
                        else:
                            modifyTime = None
                        if matchState == 1 and recentFirstTime and modifyTime and item['HappenTime'] != '中场' \
                                and item['HappenTime'] != '' and int(item['HappenTime']) >= 45 \
                                and (modifyTime - recentFirstTime).seconds >= 240:
                            matchState = 3

                        if item['HappenTime'].strip() == '中场':
                            matchState = 2
                        elif item['HappenTime'].strip() != '':
                            remainTime = int(item['HappenTime'])
                            detail[2] = remainTime
                            if matchState == 0 and remainTime <= 45:
                                matchState = 1
                            if matchState == 2:
                                matchState = 3

                        detail[1] = matchState

                        # 盘口类型，主队进球数，客队进球数
                        if item['Score'] == '早':
                            detail[3] = 0
                        elif item['Score'] == '即':
                            detail[3] = 1
                        else:
                            scores = item['Score'].split("-")
                            detail[3] = 2
                            detail[4] = scores[0]
                            detail[5] = scores[1]

                        # 主队赔率、盘口、客队赔率
                        detail[6] = item['HomeOdds']
                        detail[7] = item['PanKou']
                        detail[8] = item['AwayOdds']

                        # 1 开盘 0 封盘
                        if item['IsClosed'] == '封':
                            detail[9] = 0
                        else:
                            detail[9] = 1

                        if matchState == 1 and modifyTime:
                            recentFirstTime = modifyTime
                        details.append(detail)

            except Exception as e:
                print(e)
                logLine(common_config.webresponse, [oddsid, matchid, companyid, finished_pre, finished_gun])
                print(oddsid, matchid, companyid, finished_pre, finished_gun)
            else:
                result['state'] = 1
                result['detail'] = details
        return result

    @staticmethod
    def up_total_details(data, kind):
        result = False
        details = data['detail']
        columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal',
                   'downOdds', 'isBet', 'modifyTime']
        # 采集源包含赛前+赛中
        if kind == 2:
            result = sql_util.insetMany('zq_totalScoreDetail', columns, details)
        return {'isUP': result, 'oddsIDList': data['oddsIDList']}
        # return {'isUP': result, 'matchState': matchstate, 'finished_gun': finished_gun, 'finished_pre': finished_pre}

    @staticmethod
    def update_halfgoals(start_time=None):
        if start_time:
            str_start = "and MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''
        sql = "SELECT matchID, scheduleID,leagueID,matchTime,homeScore,awayScore,homeHalf,awayHalf,matchState,halfgoals_f " \
              "FROM zq_schedule " \
              "WHERE matchState=-1 and halfgoals_f=0  {0}" \
              "order by matchTime ASC".format(str_start)
        results = sql_util.select_rows(sql)
        print("上半场变化记录待更新比赛数量：{0}".format(len(results)))
        for item in results:
            schedulID = item[1]
            # matchState = item[8]
            sqltemp1 = "SELECT COUNT(*) FROM zq_halfgoals_3 where scheduleID = {0}".format(schedulID)
            count = sql_util.select_rows(sqltemp1)[0][0]
            oddsdata = get_halfodds_goals(schedulID, 3)
            if count > 0:
                pass
            elif oddsdata is not None:
                oddsdata.reverse()
                oddsArr = oddsdata
                odds_items = []
                keys = ['MatchID', 'ScheduleID', 'CompanyID', 'OddsType', 'HappenTime', 'HighOdds', 'Goal',
                        'LowOdds', 'HomeScore', 'AwayScore', 'IsBet', 'ModifyTime', 'MatchState']
                for i in range(0, len(oddsArr)):
                    required_fields = ['HomeOdds', 'PanKou', 'AwayOdds', 'ModifyTime', 'Score', 'HappenTime']
                    missing_fields = [field for field in required_fields if field not in oddsArr[i]]
                    if missing_fields:
                        print("zq half goals row missing field: scheduleId={0}, index={1}, fields={2}".format(
                            schedulID, i, missing_fields))
                        continue
                    odds_dict = {'MatchID': item[0], 'ScheduleID': schedulID, 'CompanyID': 3,
                                 'HighOdds': oddsArr[i]['HomeOdds'], 'Goal': oddsArr[i]['PanKou'],
                                 'LowOdds': oddsArr[i]['AwayOdds'], 'MatchState': 1}
                    strp_time = oddsArr[i]['ModifyTime']
                    if oddsArr[i]['IsClosed'] == '封':
                        odds_dict['IsBet'] = 0
                    else:
                        odds_dict['IsBet'] = 1

                    odds_dict['HomeScore'] = 0
                    odds_dict['AwayScore'] = 0

                    if oddsArr[i]['Score'] == '早':
                        odds_dict['OddsType'] = 0
                    elif oddsArr[i]['Score'] == '即':
                        odds_dict['OddsType'] = 1
                    else:
                        odds_dict['OddsType'] = 2
                        goalsArr = oddsArr[i]['Score'].split('-')
                        if len(goalsArr) < 2:
                            print("zq half goals score invalid: scheduleId={0}, index={1}, score={2}".format(
                                schedulID, i, oddsArr[i]['Score']))
                            continue
                        odds_dict['HomeScore'] = goalsArr[0]
                        odds_dict['AwayScore'] = goalsArr[1]

                    if len(oddsArr[i]['HappenTime']) == 0:
                        odds_dict['HappenTime'] = 0
                    elif oddsArr[i]['HappenTime'] == '中场':
                        odds_dict['HappenTime'] = 45
                        odds_dict['MatchState'] = 2
                    else:
                        odds_dict['HappenTime'] = int(oddsArr[i]['HappenTime'])

                    odds_dict['ModifyTime'] = datetime(int(strp_time[0:4]), int(strp_time[4:6]),
                                                       int(strp_time[6:8]), int(strp_time[8:10]),
                                                       int(strp_time[10:12]), int(strp_time[12:14]))
                    odds_items.append(
                        [odds_dict['MatchID'], odds_dict['ScheduleID'], odds_dict['CompanyID'], odds_dict['OddsType'],
                         odds_dict['HappenTime'], odds_dict['HighOdds'],
                         odds_dict['Goal'], odds_dict['LowOdds'], odds_dict['HomeScore'], odds_dict['AwayScore'],
                         odds_dict['IsBet'], odds_dict['ModifyTime'], odds_dict['MatchState']])
                if len(odds_items) > 0:
                    sql_util.insetMany('zq_halfgoals_3', keys, odds_items)
                    sqltemp1 = "update zq_schedule set halfgoals_f =2 where scheduleID= {0}".format(schedulID)
                    sql_util.sqlExecute(sqltemp1)
                else:
                    sqltemp1 = "update zq_schedule set halfgoals_f =3 where scheduleID= {0}".format(schedulID)
                    sql_util.sqlExecute(sqltemp1)
                print(odds_items)
            else:
                sqltemp1 = "update zq_schedule set halfgoals_f =4 where scheduleID= {0}".format(schedulID)
                sql_util.sqlExecute(sqltemp1)
            time.sleep(1)

    @staticmethod
    def up_odds_mobile(start_time=None):
        if start_time:
            str_start = "and MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''
        sql = "SELECT sche.MatchID,sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.LeagueId,sche.SubLeagueID, " \
              "lea.Type,sche.Partscore_f,sche.Totalodds_f,sche.HomeTeam,sche.AwayTeam " \
              "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
              "WHERE sche.MatchState=-1 and sche.Totalodds_f IN(0,1) {0} " \
              "ORDER BY sche.MatchTime ASC".format(str_start)
        results = sql_util.select(sql)
        print("开始更新进球数初盘：{0}".format(len(results)))
        for item in results:
            print(item)
            matchID = item[0]
            scheduleID = item[1]
            matchState = item[3]
            finished = item[9]
            totalCrawler = TotalOddsCrawler(matchID, scheduleID, matchState, finished)
            oddsData = totalCrawler.qt_mobile_get()
            print(oddsData)
            if oddsData['state'] == 1:
                sql_util.upData('zq_schedule', {'totalodds_f': 1}, {'ScheduleID': scheduleID})
                oddsList = oddsData['odds']
                TotalOddsZq._upsert_mobile_odds(scheduleID, oddsList)
                if matchState in (-1, -10):
                    sql_util.upData('zq_schedule', {'totalodds_f': 2}, {'ScheduleID': scheduleID})
            elif matchState == -1 and oddsData['state'] == 0:
                sql_util.upData('zq_schedule', {'totalodds_f': 4}, {'ScheduleID': scheduleID})
            # time.sleep(1)

    @staticmethod
    def up_half_odds_mobile(start_time=None):
        if start_time:
            str_start = "and MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''
        sql = "SELECT sche.MatchID,sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.LeagueId,sche.SubLeagueID, " \
              "lea.Type,sche.Partscore_f,sche.half_totalodds_f,sche.HomeTeam,sche.AwayTeam " \
              "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
              "WHERE sche.MatchState=-1 and sche.half_totalodds_f IN(0,1) {0} " \
              "ORDER BY sche.MatchTime ASC".format(str_start)
        results = sql_util.select(sql)
        print("开始更新半场进球数初盘：{0}".format(len(results)))
        for item in results:
            print(item)
            matchID = item[0]
            scheduleID = item[1]
            matchState = item[3]
            finished = item[9]
            totalCrawler = TotalOddsCrawler(matchID, scheduleID, matchState, finished, is_half=True)
            oddsData = totalCrawler.qt_mobile_get()
            print(oddsData)
            if oddsData['state'] == 1:
                sql_util.upData('zq_schedule', {'half_totalodds_f': 1}, {'ScheduleID': scheduleID})
                TotalOddsZq._upsert_mobile_odds(scheduleID, oddsData['odds'])
                if matchState in (-1, -10):
                    sql_util.upData('zq_schedule', {'half_totalodds_f': 2}, {'ScheduleID': scheduleID})
            elif matchState == -1 and oddsData['state'] == 0:
                sql_util.upData('zq_schedule', {'half_totalodds_f': 4}, {'ScheduleID': scheduleID})

# if __name__ == '__main__':
# scheduleID =2403434, 2023-08-25 23:59:00
# TotalOddsZq.up_odds_mobile('2023-06-01 00:00:00')

# sql1 = "SELECT DISTINCT ScheduleID FROM zq_totalscore WHERE createTime >'2024-02-28 00:00:00' AND createTime <='2024-03-02 01:03:00'"
# results = sql_util.select(sql1)
# for item in results:
#     scheduleID = item[0]0
#     print(scheduleID)
#     sql2 = "UPDATE zq_schedule SET totalodds_f=2 WHERE scheduleID={0}".format(scheduleID)
#     sql_util.sqlExecute(sql2)
