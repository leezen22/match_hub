import json
from datetime import datetime
from bs4 import BeautifulSoup
from config import zqconfig_qt, common_config
from crawler.qt.zq_asian_odds_crawler import AsianOddsCrawler
from utils import sql_util
from utils.fileUtil import logLine
from utils.webDriver import WebDriver
from utils.webUtil import WebUtil
from zq.oddsUtil_zq import OddsUtil


class AsianOddsZq(object):

    # 三合一页面 单场比赛让分变化记录数据更新
    @staticmethod
    def up_AsianDetail(data, kind):
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
        asian_pre_table = 'zq_asianOdds_pre_{0}'.format(companyID)
        asian_gun_table = 'zq_asianOdds_gun_{0}'.format(companyID)

        # 采集源包含赛前+赛中，采集成功且未结束采集
        if oddsID and data['state'] == 1 and kind == 2:
            if (count_pre + count_gun) > 0:
                finished_pre = data['finished_pre']
                finished_gun = data['finished_gun']
                # 防止数据紊乱，更新前先更新状态，防止下次更新数据时，数据重复
                if data['hasPre'] == 1 and finished_pre == 0:
                    finished_pre = 1
                if data['hasGun'] == 1 and finished_gun == 0:
                    finished_gun = 1

                if finished_pre != data['finished_pre'] or finished_gun != data['finished_gun']:
                    sql_util.upData('zq_asianOdds',
                                    {'finished_pre': finished_pre, 'finished_gun': finished_gun},
                                    {'oddsID': oddsID})


                # ---- 插入数据范围判断，避免完全匹配更新------
                # 数据包含赛前变化记录
                if data['hasPre'] == 1 and data['finished_pre'] == 0:
                    isUpdated = sql_util.insetMany(asian_pre_table, data['keys_pre'], data['pre'])
                elif data['hasPre'] == 1 and data['finished_pre'] == 1:
                    sql = "select count(*) from {0} where oddsID={1}".format(asian_pre_table,oddsID)
                    old = sql_util.select(sql)
                    count_old = old[0][0]
                    if count_pre > count_old:
                        new = data['pre'][count_old:]
                        isUpdated = sql_util.insetMany(asian_pre_table, data['keys_pre'], new)
                        # 不插入数据
                    else:
                        isUpdated = True
                else:
                    isUpdated = True

                if data['hasGun'] == 1 and data['finished_gun'] == 0:
                    isUpdated = sql_util.insetMany(asian_gun_table, data['keys_gun'], data['gun'])
                elif data['hasGun'] == 1 and data['finished_gun'] == 1:
                    sql = "select count(*) from {0} where oddsID={1}".format(asian_gun_table,oddsID)
                    old = sql_util.select(sql)
                    count_old = old[0][0]
                    if count_pre > count_old:
                        new = data['gun'][count_old:]
                        isUpdated = sql_util.insetMany(asian_gun_table, data['keys_gun'], new)
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

                sql_util.upData('zq_asianOdds',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasGun': hasGun, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})

    # 三合一页面 多场比赛变化数据批量插入,(finished_pre ==0 and finished_gun==0)
    @staticmethod
    def insert_asianDetail_batch(data, kind):
        isUP = False
        try:
            columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal',
                       'downOdds', 'isBet', 'modifyTime']
            # 采集源包含赛前+赛中
            if kind == 2:
                isUP = sql_util.insetMany('zq_AsianOddsDetail', columns, data)
        except Exception as e:
            print(e)
        return isUP

    @staticmethod
    def up_asian_detail(data, kind):
        details = data['detail']
        matchstate = data['matchState']
        oddsID = data['oddsID']
        columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal',
                   'downOdds', 'isBet', 'modifyTime']
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

            sql_util.upData('zq_AsianOdds',
                            {'finished_pre': finished_pre, 'finished_gun': finished_gun},
                            {'oddsID': oddsID})
            # 状态未采集
            if finished_pre == 0 and data['finished_gun'] == 0:
                result = sql_util.insetMany('zq_AsianOddsDetail', columns, details)
            # 过去曾采集
            else:
                count = len(details)
                sql = " select count(*) from zq_AsianOddsDetail where oddsID={0} ".format(oddsID)
                old = sql_util.select_Execute(sql)
                count_old = old[0][0]
                if count > count_old:
                    new = details[count_old:count]
                    result = sql_util.insetMany('zq_AsianOddsDetail', columns, new)
            if (matchstate == -1 or matchstate == -10) and result:
                sql_util.upData('zq_AsianOdds', {'finished_pre': 2, 'finished_gun': 2}, {'oddsID': oddsID})


    @staticmethod
    def get_asian_odds(match, driver, isproxy, proxy):
        result = {'state': 2, 'odds': []}
        matchid = match[0]
        homeTeam = match[10]
        awayTeam = match[11]
        headers = zqconfig_qt.headers_odds
        referer = OddsUtil.getRefer(match[4], match[6], match[3], match[5])
        headers['Referer'] = referer
        url = zqconfig_qt.asianscore_url + "?id=" + str(matchid)
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
            result_check = OddsUtil.AsiaOddsCheck(matchid, homeTeam, awayTeam, soup)
            if result_check is False:
                result['state'] = 0
            else:
                odds_collect = OddsUtil.collect_odds(matchid, soup)
                if odds_collect['state'] == 0:
                    result['state'] = 2
                else:
                    result['state'] = 1
                    result['odds'] = odds_collect['odds']
        return result


    @staticmethod
    def get_deail(oddsid, matchid, companyid, finished_pre=None, finished_gun=None, isproxy=False):
        result = {'state': 2, 'oddsID': oddsid, 'matchID': matchid, 'companyID': companyid,
                  'finished_pre': finished_pre, 'finished_gun': finished_gun, 'detail': []}
        url = "{0}&scheid={1}&companyid={2}".format(zqconfig_qt.masiandetail_url, matchid, companyid)
        headers = zqconfig_qt.m_detail_headers
        headers['Referer'] = "{0}{1}.htm".format(zqconfig_qt.m_aisan, matchid)
        response = WebUtil.requests_get(url, headers, isProxy=isproxy, sleep=False)

        if response[0] == 1:
            try:
                details = []
                data = json.loads(response[1])
                data.reverse()
                recentFirstTime = None
                if len(data) > 0 and (data[0]['Score'] == '即' or data[0]['Score'] == '早'):
                    # 赔率记录完整
                    matchState = 0
                    for item in data:
                        detail = [oddsid, None, None, None, None, None, None, None, None, None, None]
                        # detail = 'oddsID', 'matchState' ,'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal', 'downOdds',
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
    def up_asian_details(data, kind):
        result = False
        details = data['detail']
        columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'upOdds', 'goal',
                   'downOdds', 'isBet', 'modifyTime']
        # 采集源包含赛前+赛中
        if kind == 2:
            result = sql_util.insetMany('zq_AsianOddsDetail', columns, details)
        return {'isUP': result, 'oddsIDList': data['oddsIDList']}

    @staticmethod
    def up_odds_mobile(start_time=None):
        if start_time:
            str_start = "and MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''
        sql = "SELECT sche.MatchID,sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueId,sche.subLeagueID, " \
              "lea.type,sche.partscore_f,sche.asianOdds_f,sche.totalodds_f,sche.HomeTeam,sche.AwayTeam " \
              "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
              "WHERE sche.MatchState=-1 and sche.asianodds_f IN(0,1) {0} " \
              "ORDER BY sche.MatchTime ASC".format(str_start)
        results = sql_util.select(sql)
        print("开始更新让球初盘：{0}".format(len(results)))
        for item in results:
            print(item)
            matchID = item[0]
            scheduleID = item[1]
            matchState = item[3]
            finished = item[9]
            asianCrawler = AsianOddsCrawler(matchID, scheduleID, matchState, finished)
            oddsData = asianCrawler.qt_mobile_get()
            # print(oddsData)
            if oddsData['state'] == 1:
                sql_util.upData('zq_schedule', {'asianodds_f': 1}, {'ScheduleID': scheduleID})
                oddsList = oddsData['odds']
                if finished == 0:
                    sql_util.insertDatas('zq_asianodds', oddsList)
                else:
                    for odds in oddsList:
                        condition = {'ScheduleID': scheduleID, 'CompanyID': odds['companyId']}
                        results2 = sql_util.select_table_rows('zq_asianodds', ['OddsID'], condition, isDis=True)
                        if len(results2) > 0:
                            sql_util.upData('zq_asianodds', odds, condition)
                        else:
                            sql_util.insertData('zq_asianodds', odds)
                if matchState in (-1, -10):
                    sql_util.upData('zq_schedule', {'asianodds_f': 2}, {'ScheduleID': scheduleID})
            elif matchState == -1 and oddsData['state'] == 0:
                sql_util.upData('zq_schedule', {'asianodds_f': 4}, {'ScheduleID': scheduleID})
            # time.sleep(1)


# if __name__ == '__main__':
#     AsianOddsZq.up_odds_mobile('2023-06-01 00:00:00')
#
#     # sql = " SELECT sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueId,sche.subLeagueID," \
#     #           "lea.type,sche.partscore_f,sche.asianOdds_f,sche.totalodds_f,sche.HomeTeam,sche.AwayTeam " \
#     #           "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
#     #           "WHERE MatchTime>='2024-01-01 00:00:00' and sche.MatchState=-1 " \
#     #           "and (sche.asianOdds_f IN(0,1) OR sche.totalodds_f IN(0,1)) " \
#     #           "ORDER BY sche.MatchTime DESC "
#     # matchs = sql_util.select(sql)
#     matchs = [[2520790, datetime(2024, 2, 29, 10, 15), -1, '2024', 344, None, 2, 0, 0, 0, '纳什威尔', '摩卡']]
#     for match in matchs:
#         print(match)
#         data_asian = AsianOddsZq.get_asian_odds(match, None, isproxy=False, proxy=None)
#         print(data_asian)
#         time.sleep(5)
#     "https://m.titan007.com/HandicapDataInterface.ashx?scheid=2408361&type=1&oddskind=0&isHalf=0&flesh=1709214009000"
