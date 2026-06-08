import re
import threading
from bs4 import BeautifulSoup
from config import lqconfig_qt, common_config
from lq.dao import MatchDao
from utils import js2pyUtil, sql_util, fileUtil
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


# 更新让分/大小赔率变化记录（365+Crown）
def upOddsDetail():
    print(getNowTime() + " 开始更新篮球比分变化记录")
    fileUtil.logLine(lqconfig_qt.update_log, ['开始更新篮球比分变化记录'])

    sqlCrown = "SELECT asian.oddsID, asian.scheduleID, asian.companyID, asian.finished_in " \
               "FROM lq_AsianOdds as asian " \
               "left JOIN `lq_schedule` as sche on sche.scheduleID = asian.ScheduleID " \
               "WHERE CompanyID=3 and finished_gun in(0,1) and sche.MatchState not in(-4,-5,-6) "
    # 获取bet365未完成采集比赛列表
    sql365 = "SELECT asian.oddsID, asian.scheduleID, asian.companyID, asian.finished_in " \
             "FROM lq_AsianOdds as asian " \
             "left JOIN `lq_schedule` as sche on sche.scheduleID = asian.ScheduleID " \
             "WHERE asian.CompanyID=8 and asian.finished_gun in(0,1) and sche.MatchState not in(-4,-5,-6) "

    odds_365 = sql_util.select_Execute(sql365, isdict=True)
    print("odds_365", len(odds_365))
    odds_crown = sql_util.select_Execute(sqlCrown, isdict=True)
    print("odds_crown", len(odds_crown))
    # 更新365变化记录（更新365让分记录，会同步更新大小变化记录）
    threads = []
    if len(odds_365) > 0:
        bet365 = threading.Thread(target=AsianTotalDetails.task_asianTotal_matchs, args=(odds_365,))
        threads.append(bet365)
    # 更新皇冠变化记录（更新3让分记录，会同步更新大小变化记录）
    if len(odds_crown) > 0:
        sb = threading.Thread(target=AsianTotalDetails.task_asianTotal_matchs, args=(odds_crown,))
        threads.append(sb)
    # 启动线程
    for t in threads:
        t.start()
    # 等待所有线程完成
    for t in threads:
        t.join()
    fileUtil.logLine(lqconfig_qt.update_log, ["篮球比分变化记录结束更新"])
    print(getNowTime() + " 篮球比分变化记录开始更新")


class AsianTotalDetails(object):

    @staticmethod
    def task_asianTotal_matchs(matchs):
        for match in matchs:
            scheduleID = match['scheduleID']
            companyID = match['companyID']
            AsianTotalDetails.up_asianTotal_match(scheduleID, companyID)

    # 更新让分和总分变化记录
    @staticmethod
    def up_asianTotal_match(scheduleID, companyID):
        asian_result = sql_util.selectData('lq_asianOdds',
                                         ['OddsID', 'ScheduleID', 'CompanyID', 'finished_gun'],
                                         {'ScheduleID': scheduleID, 'CompanyID': companyID}, 0)
        total_result = sql_util.selectData('lq_totalodds',
                                           ['OddsID', 'ScheduleID', 'CompanyID', 'finished_gun'],
                                           {'ScheduleID': scheduleID, 'CompanyID': companyID}, 0)
        asian_count = len(asian_result)
        total_count = len(total_result)
        # 第二版处理方案当前指数公司 比赛让分和大小都无开盘
        if (asian_count > 0 and asian_result[0][3] != 2) or (total_count > 0 and total_result[0][3] != 2):
            details = AsianTotalDetails.collect_asian_total_detail(scheduleID, companyID)
            if details['state'] == 1:
                threads = []
                matchState = details['matchState']
                if asian_count > 0 and asian_result[0][3] != 2:
                    asian_oddsid = asian_result[0][0]
                    asian_details = details['asian']
                    asian_thread = threading.Thread(target=AsianTotalDetails.up_asian_details,
                                                  args =(asian_details, asian_oddsid, scheduleID, companyID, matchState))
                    threads.append(asian_thread)
                if total_count > 0 and total_result[0][3] != 2:
                    total_oddsid = total_result[0][0]
                    total_details = details['total']
                    total_thread = threading.Thread(target=AsianTotalDetails.up_total_details,
                                                    args=(
                                                    total_details, total_oddsid, scheduleID, companyID, matchState))
                    threads.append(total_thread)
                # 启动线程
                for t in threads:
                    t.start()
                # 等待所有线程完成
                for t in threads:
                    t.join()

    @staticmethod
    def up_asian_details(asian_details, asian_oddsID, scheduleID, companyID, matchState):
        asian_detail_columns = ['oddsID', 'type', 'matchState', 'happenTime', 'homeScore', 'awayScore', 'isBet',
                              'homeOdds', 'goal', 'awayOdds', 'oddsType', 'modifyTime']
        asian_count_web = len(asian_details)
        sql_asiancount = "SELECT COUNT(*) FROM lq_AsianOddsDetail WHERE oddsID={0}".format(asian_oddsID)
        asiancount_local = sql_util.select(sql_asiancount)[0][0]
        if asian_count_web > int(asiancount_local):
            asian_detail_new = asian_details[asiancount_local:]
            sql_util.upData('lq_AsianOdds',
                            {'finished_gun': 1, 'finished_pre': 1},
                            {'oddsID': asian_oddsID})
            sql_util.insetMany('lq_AsianOddsDetail', asian_detail_columns, asian_detail_new)
        elif asian_count_web < int(asiancount_local):
            print('AsianDetails collect:' + str([asiancount_local, asian_count_web, scheduleID, companyID]))
            delsql = 'DELETE FROM lq_AsianOddsDetail WHERE oddsID={0}'.format(asian_oddsID)
            sql_util.sqlExecute(delsql)
            sql_util.upData('lq_AsianOdds',
                            {'finished_gun': 1, 'finished_pre': 1},
                            {'oddsID': asian_oddsID})
            sql_util.insetMany('lq_AsianOddsDetail', asian_detail_columns, asian_details)

        if matchState in [-1, -4]:
            sql_util.upData('lq_AsianOdds',
                            {'finished_gun': 2, 'finished_pre': 2},
                            {'oddsID': asian_oddsID})

    @staticmethod
    def up_total_details(total_details, total_oddsID, scheduleID, companyID, matchState):
        total_detail_columns = ['oddsID', 'type', 'matchState', 'happenTime', 'homeScore', 'awayScore', 'isBet',
                                'highOdds', 'goal', 'lowOdds', 'oddsType', 'modifyTime']

        totalCount_web = len(total_details)
        sql_totalCount = "SELECT COUNT(*) FROM lq_totaloddsdetail WHERE oddsID={0}".format(total_oddsID)
        totalCount_local = sql_util.select(sql_totalCount)[0][0]
        if totalCount_web > int(totalCount_local):
            total_detail_new = total_details[totalCount_local:]
            sql_util.upData('lq_totalodds',
                            {'finished_gun': 1, 'finished_pre': 1},
                            {'oddsID': total_oddsID})
            sql_util.insetMany('lq_totaloddsDetail', total_detail_columns, total_detail_new)
        elif totalCount_web < totalCount_local:
            print('totalDetail collect:' + str([totalCount_local, totalCount_web, scheduleID, companyID]))
            delSql = 'DELETE FROM lq_totaloddsDetail WHERE oddsID={0}'.format(total_oddsID)
            sql_util.sqlExecute(delSql)
            sql_util.upData('lq_totalodds',
                            {'finished_gun': 1, 'finished_pre': 1},
                            {'oddsID': total_oddsID})
            sql_util.insetMany('lq_totaloddsDetail', total_detail_columns, total_details)
        # 更新采集状态
        if matchState in [-1, -4]:
            sql_util.upData('lq_totalodds',
                            {'finished_gun': 2, 'finished_pre': 2},
                            {'oddsID': total_oddsID})

    # 获取让分和总分变化记录
    @staticmethod
    def collect_asian_total_details(scheduleID, companyID):
        mstate = lqconfig_qt.matchstate
        details = {'asian': [], 'total': [], 'state': 0}
        matchState = MatchDao.selectMatch({'scheduleID': scheduleID})[0][3]
        details['matchState'] = matchState
        url = lqconfig_qt.AsianOddsDetail + '?' + 'id=' + str(scheduleID) + '&' + 'cid=' + str(
            companyID) + '&' + 't=6'
        print(url)
        asianResults = sql_util.selectData('lq_AsianOdds', ['OddsID', 'ScheduleID', 'CompanyID'],
                                         {'ScheduleID': scheduleID, 'CompanyID': companyID}, 1)
        scoreResults = sql_util.selectData('lq_totalodds', ['OddsID', 'ScheduleID', 'CompanyID'],
                                           {'ScheduleID': scheduleID, 'CompanyID': companyID}, 1)
        if len(asianResults) > 0:
            asian_oddsID = asianResults[0][0]
        else:
            asian_oddsID = None
        if len(scoreResults) > 0:
            total_oddsID = scoreResults[0][0]
        else:
            total_oddsID = None
        # 让分和总分赔率表无公司开盘信息
        if len(asianResults) == 0 and len(scoreResults) == 0:
            return details
        # 让分和总分至少开了一个，开始解析变化记录页面
        else:
            response = WebUtil.requests_get(url, headers=lqconfig_qt.headers)
            state = response[0]
            content = response[1]
            if state == 1 and content != '':
                try:
                    fixed = re.sub(r'</td>\r\n(.*?)<tr(.*?)bgcolor="#FFFFFF">',
                                   '</td>\r\n</tr>\r\n<tr bgcolor="#FFFFFF">',
                                   content)
                    soup = BeautifulSoup(fixed, 'html.parser')
                    result = sql_util.selectData('lq_schedule', ['scheduleID', 'MatchTime', 'MatchState'],
                                                 {'scheduleID': int(scheduleID)}, 0)
                    matchtime = result[0][1]
                    tables = soup.find_all('table', class_='jtd')
                    if len(tables) > 0 and asian_oddsID:
                        asianOdds = AsianTotalDetails.getAsianDetails(tables[0], mstate, asian_oddsID, matchtime)
                        details['asian'] = asianOdds
                    if len(tables) > 1 and total_oddsID:
                        totalOdds = AsianTotalDetails.getTotalDetails(tables[1], mstate, total_oddsID, matchtime)
                        details['total'] = totalOdds
                except Exception as e:
                    js2pyUtil.logLine(common_config.lq_oddsdetail_fail, [scheduleID, companyID, e])
                else:
                    details['state'] = 1
        return details

    # 获取让分变化记录
    @staticmethod
    def getAsianDetails(soup, stateDict, oddsID, matchTime):
        # keys:oddsID,type,matchState,remainTime,homeScore,awayScore,isBet,homeOdds,AsianOdds,awayOdds,oddsType,modifyTime
        asianlist = []
        trs = soup.find_all('tr')
        count = len(trs)
        # 标题栏占用长度度2
        if count > 2:
            # 因最新的记录页面最上面显示，所以倒叙读取
            for i in range(2, count):
                type = 6
                matchState = None
                happenTime = None
                homeScore = None
                awayScore = None
                isBet = None
                homeOdds = None
                goal = None
                awayOdds = None
                oddsType = None
                modifyTime = None
                tds = trs[i].select('td')
                data0 = tds[0].text
                if data0 == '':
                    matchState = 0
                else:
                    time = data0.split(' ')
                    if len(time) == 1:
                        matchState = stateDict[time[0]]
                    else:
                        matchState = stateDict[time[0]]
                        if len(time[1].replace(" ", "")) > 0:
                            happenTime = time[1]
                data1 = tds[1].text
                if data1 != '-' and data1 != '':
                    homeScore = data1.split('-')[0]
                    awayScore = data1.split('-')[1]
                data2 = tds[2].text
                if data2 != '':
                    homeOdds = data2
                data3 = tds[3].text
                if data3 == '封':
                    isBet = 0
                else:
                    if data3 != '':
                        goal = data3
                        isBet = 1
                data4 = tds[4].text
                if data4 != '':
                    awayOdds = data4
                data6 = tds[6].text
                if data6 == '滚':
                    oddsType = '2'
                elif data6 == '即':
                    oddsType = '1'
                else:
                    pass
                data5 = tds[5].text
                if data5 != '':
                    modifyTime = data5[0:5] + ' ' + data5[5:10]
                    modifyTime = AsianTotalDetails.getModifyTime(matchTime, modifyTime, data6)
                detail = [oddsID, type, matchState, happenTime, homeScore, awayScore, isBet, homeOdds, goal,
                          awayOdds, oddsType, modifyTime]
                asianlist.append(detail)
        asianlist.reverse()
        return asianlist

    # 获取大小让分记录
    @staticmethod
    def getTotalDetails(soup, stateDict, oddsID, matchTime):
        totalList = []
        trs = soup.find_all('tr')
        count = len(trs)
        # 标题栏占用长度度2
        if count > 2:
            for i in range(2, count):
                kind = 6
                # detail = [oddsID, 6, None, None, None, None, None, None, None, None, None, None]
                # # oddsID,type,matchState,happenTime,homeScore, awayScore,isBet,highOdds,totalScore,lowOdds, oddsType,modifyTime
                matchState = None
                happenTime = None
                homeScore = None
                awayScore = None
                isBet = None
                highOdds = None
                goal = None
                lowOdds = None
                oddsType = None
                modifyTime = None
                tds = trs[i].select('td')
                data0 = tds[0].text
                if data0 == '':
                    detail[2]
                    matchState = 0
                else:
                    time = data0.split(' ')
                    if len(time) == 1:
                        matchState = stateDict[time[0]]
                    else:
                        matchState = stateDict[time[0]]
                        if len(time[1].replace(" ", "")) > 0:
                            happenTime = time[1]
                data1 = tds[1].text
                if data1 != '-' and data1 != '':
                    homeScore = data1.split('-')[0]
                    awayScore = data1.split('-')[1]
                data2 = tds[2].text
                if data2 != '':
                    highOdds = data2
                data3 = tds[3].text
                if data3 == '封':
                    isBet = 0
                else:
                    if data3 != '':
                        goal = data3
                        isBet = 1
                data4 = tds[4].text
                if data4 != '':
                    lowOdds = data4
                data6 = tds[6].text
                if data6 == '滚':
                    oddsType = '2'
                elif data6 == '即':
                    oddsType = '1'
                else:
                    pass
                data5 = tds[5].text
                if data5 != '':
                    modifyTime = data5[0:5] + ' ' + data5[5:10]
                    modifyTime = AsianTotalDetails.getModifyTime(matchTime, modifyTime, data6)

                detail = [oddsID, kind, matchState, happenTime, homeScore, awayScore, isBet, highOdds, goal,
                          lowOdds,
                          oddsType, modifyTime]
                totalList.append(detail)
        # 因最新的记录页面最上面显示，所以倒叙读取
        totalList.reverse()
        return totalList

    # 根据比赛开始时间(datetime), 补充变化时间‘年’
    @staticmethod
    def getModifyTime(matchTime, modifyTime, oddsType):
        match_y = matchTime.year
        match_m = matchTime.month
        modify_m = int(modifyTime[0:2])
        if oddsType == '即' and modify_m > match_m:
            modify_y = match_y - 1
        elif oddsType == '滚' and modify_m < match_m and modify_m == 1:
            modify_y = match_y + 1
        else:
            modify_y = match_y
        modifyTime = str(modify_y) + '-' + modifyTime
        return modifyTime

# if __name__ == '__main__':
#     oddsData = AsianTotalDetails.collect_asian_total_details(533095,3)
#     print(oddsData)