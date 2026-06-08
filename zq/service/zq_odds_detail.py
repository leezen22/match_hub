import threading
import traceback
from datetime import datetime
from bs4 import BeautifulSoup
from config import common_config, scrawler_config
from utils import sql_util
from utils.fileUtil import logLine
from utils.webUtil import WebUtil


class OddsDetailZq(object):
    @staticmethod
    def get_detail_byEurope(companyID, euro, isProxy):
        asiaEurope = {3: 545, 8: 281, 1: 80, 12: 90, 14: 81, 17: 517, 22: 16, 23: 499,
                      24: 18, 31: 474, 35: 659, 42: 976}
        scheduleID = euro[0]
        matchTime = euro[1]
        matchState = euro[2]
        "https://vip.titan007.com/changeDetail/3in1Odds.aspx?id=2513309&companyid=3&l=0"
        # Crown,bet365,澳门,易胜博,韦德, 明生,10BET, 金宝博, 12Bet, 利记, 盈禾, 18Bet
        details = {'state': 0, 'scheduleID': scheduleID, 'companyID': companyID, 'matchState': matchState}
        url = "http://vip.titan007.com/changeDetail/3in1Odds.aspx?id={0}&companyid={1}&l=0".format(scheduleID, companyID)
        Referer = "http://vip.titan007.com/AsianOdds_n.aspx?id={0}".format(scheduleID)
        Host = "vip.titan007.com"
        headers = {'Host': Host, 'Referer': Referer}
        response = WebUtil.requests_get(url, headers=headers, isProxy=isProxy)
        state = response[0]
        if state == 1 and response[1] == '':
            collect = {'state': 1, 'scheduleID': scheduleID, 'companyID': companyID, 'matchTime': matchTime,
                       'matchState': matchState, 'oddsID': None, 'finished_pre': None, 'finished_gun': None,
                       'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasFirst': 0, 'hasSecond': 0, 'detail': []}
            details['asian'] = collect
            details['total'] = collect
            details['europe'] = collect

        if state == 1 and response[1] != '':
            try:
                content = response[1]
                soup = BeautifulSoup(content, 'html.parser')
                tables = soup.find_all('table', class_='gts')
                count = len(tables)
                # print(count)
                threads = []
                if count == 0:
                    tips = "响应内容异常, {0},{1}".format(companyID, euro)
                    print(tips)
                    return details

                if count > 0:
                    asianThread = DetailThread(OddsDetailZq.get_asian_detail,
                                             args=(tables[0], scheduleID, companyID, matchTime, matchState))
                    threads.append(asianThread)
                if count > 1:
                    totalThread = DetailThread(OddsDetailZq.get_total_detail,
                                               args=(tables[1], scheduleID, companyID, matchTime, matchState))
                    threads.append(totalThread)
                if count > 2 and (companyID in asiaEurope):
                    eurThread = DetailThread(OddsDetailZq.get_euroDetail_OddsID,
                                             args=(tables[2], euro))
                    threads.append(eurThread)
                # 启动线程
                for t in threads:
                    t.start()
                # 等待所有线程完成
                for t in threads:
                    t.join()
                if count > 0:
                    details['asian'] = asianThread.get_result()
                if count > 1:
                    details['total'] = totalThread.get_result()
                if count > 2:
                    details['europe'] = eurThread.get_result()
            except Exception as e:
                print(e)
                logLine(common_config.exception, ['detail', scheduleID, companyID, matchTime, matchState, e])
            else:
                details['state'] = 1
        return details

    # 公司ID以让分和大小为标准，欧指需单独转化
    @staticmethod
    def get_detail(scheduleID, companyID, matchTime, matchState=None):
        asiaEurope = {3: 545, 8: 281, 1: 80, 12: 90, 14: 81, 17: 517, 22: 16, 23: 499,
                      24: 18, 31: 474, 35: 659, 42: 976}
        # Crown,bet365,澳门,易胜博,韦德, 明生,10BET, 金宝博, 12Bet, 利记, 盈禾, 18Bet
        details = {'state': 0, 'scheduleID': scheduleID, 'companyID': companyID, 'matchState': matchState}
        url = "{0}?id=2399315&companyid=3&l=0".format(scrawler_config.qt_zq_web_3in1_url,scheduleID, companyID)
        Referer = "{0}?id={1}".format(scrawler_config.qt_zq_web_asianOdds_url, scheduleID)
        Host = scrawler_config.qt_zq_web_host
        headers = {'Host': Host, 'Referer': Referer}
        response = WebUtil.requests_get(url, headers=headers)
        state = response[0]
        if state == 1 and response[1] == '':
            collect = {'state': 1, 'scheduleID': scheduleID, 'companyID': companyID, 'matchTime': matchTime,
                       'matchState': matchState, 'oddsID': None, 'finished_pre': None, 'finished_gun': None,
                       'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasFirst': 0, 'hasSecond': 0, 'detail': []}
            details['asian'] = collect
            details['total'] = collect
            details['europe'] = collect

        if state == 1 and response[1] != '':
            try:
                content = response[1]
                soup = BeautifulSoup(content, 'html.parser')
                tables = soup.find_all('table', class_='gts')
                count = len(tables)
                threads = []
                if count > 0:
                    asianThread = DetailThread(OddsDetailZq.get_asian_detail,
                                             args=(tables[0], scheduleID, companyID, matchTime, matchState))
                    threads.append(asianThread)
                if count > 1:
                    totalThread = DetailThread(OddsDetailZq.get_total_detail,
                                               args=(tables[1], scheduleID, companyID, matchTime, matchState))
                    threads.append(totalThread)
                if count > 2 and (companyID in asiaEurope):
                    eurThread = DetailThread(OddsDetailZq.get_euro_detail,
                                             args=(tables[2], scheduleID, asiaEurope[companyID], matchTime, matchState))
                    threads.append(eurThread)
                # 启动线程
                for t in threads:
                    t.start()
                # 等待所有线程完成
                for t in threads:
                    t.join()
                if count > 0:
                    details['asian'] = asianThread.get_result()
                if count > 1:
                    details['total'] = totalThread.get_result()
                if count > 2:
                    details['europe'] = eurThread.get_result()
            except Exception as e:
                print(e)
                excepstr = traceback.format_exc()
                print(excepstr)
                logLine(common_config.exception, ['detail', scheduleID, companyID, matchTime, matchState, e])
            else:
                details['state'] = 1
        return details

    @staticmethod
    def get_asian_detail(soup, scheduleID, companyID, matchTime, matchState=None):
        collect = {'state': 2, 'scheduleID': scheduleID, 'companyID': companyID,
                   'matchTime': matchTime, 'matchState': matchState, 'oddsID': None, 'finished_pre': None,
                   'finished_gun': None, 'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasHalf': 0, 'hasSecond': 0,
                   'detail': []}
        asian_sql = "SELECT oddsID,companyID,finished_pre,finished_gun,hasPre,hasIn,hasFirst,hasHalf,hasSecond " \
                  "FROM zq_AsianOdds " \
                  "WHERE scheduleID ={0} and companyID={1}".format(scheduleID, companyID)
        result = sql_util.select_Execute(asian_sql)
        if len(result) > 0:
            oddsID = result[0][0]
            collect['oddsID'] = oddsID
            collect['finished_pre'] = result[0][2]
            collect['finished_gun'] = result[0][3]
        if collect['finished_gun'] in [0, 1]:
            data = OddsDetailZq.collect_detail(soup, oddsID, matchTime, 1)
            collect['state'] = data['state']
            collect['detail'] = data['detail']
            if data['hasPre'] == 1:
                collect['hasPre'] = 1
            else:
                collect['hasPre'] = result[0][4]
            collect['hasIn'] = data['hasIn']
            collect['hasFirst'] = data['hasFirst']
            collect['hasHalf'] = data['hasHalf']
            collect['hasSecond'] = data['hasSecond']
        return collect

    @staticmethod
    def get_total_detail(soup, scheduleID, companyID, matchTime, matchState=None):
        collect = {'state': 2, 'scheduleID': scheduleID, 'companyID': companyID,
                   'matchTime': matchTime, 'matchState': matchState, 'oddsID': None, 'finished_pre': None,
                   'finished_gun': None, 'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasHalf': 0, 'hasSecond': 0,
                   'detail': []}
        total_sql = "SELECT oddsID,companyID,finished_pre,finished_gun,hasPre,hasIn,hasFirst,hasHalf,hasSecond " \
                    "FROM zq_totalScore " \
                    "WHERE scheduleID ={0} and companyID={1}".format(scheduleID, companyID)
        result = sql_util.select_Execute(total_sql)
        if len(result) > 0:
            oddsID = result[0][0]
            collect['oddsID'] = oddsID
            collect['finished_pre'] = result[0][2]
            collect['finished_gun'] = result[0][3]
        if collect['finished_gun'] in [0, 1]:
            data = OddsDetailZq.collect_detail(soup, oddsID, matchTime, 2)
            collect['state'] = data['state']
            collect['detail'] = data['detail']
            if data['hasPre'] == 1:
                collect['hasPre'] = 1
            else:
                collect['hasPre'] = result[0][4]
            collect['hasIn'] = data['hasIn']
            collect['hasFirst'] = data['hasFirst']
            collect['hasHalf'] = data['hasHalf']
            collect['hasSecond'] = data['hasSecond']
        return collect

    @staticmethod
    def get_euroDetail_OddsID(soup, euro):
        scheduleID = euro[0]
        matchTime = euro[1]
        matchState = euro[2]
        companyID = euro[3]
        oddsID = euro[4]
        oddsID_Q = euro[5]
        finished_pre = euro[6]
        finished_gun = euro[7]
        hasPre = euro[8]
        hasIn = euro[9]
        hasFirst = euro[10]
        hasHalf = euro[11]
        hasSecond = euro[12]
        collect = {'state': 2, 'scheduleID': scheduleID, 'companyID': companyID, 'matchTime': matchTime,
                   'matchState': matchState, 'oddsID': oddsID, 'finished_pre': finished_pre, 'oddsID_Q': oddsID_Q,
                   'finished_gun': finished_gun, 'hasPre': hasPre, 'hasIn': hasIn, 'hasFirst': hasFirst,
                   'hasHalf': hasHalf, 'hasSecond': hasSecond,
                   'detail': []}
        if collect['finished_gun'] in [0, 1]:
            data = OddsDetailZq.collect_detail(soup, oddsID, matchTime, 3, oddsID_Q)
            collect['state'] = data['state']
            collect['detail'] = data['detail']
            if data['hasPre'] == 1:
                collect['hasPre'] = 1
            collect['hasIn'] = data['hasIn']
            collect['hasFirst'] = data['hasFirst']
            collect['hasHalf'] = data['hasHalf']
            collect['hasSecond'] = data['hasSecond']
        return collect

    @staticmethod
    def get_euro_detail(soup, scheduleID, companyID, matchTime, matchState=None):
        collect = {'state': 2, 'scheduleID': scheduleID, 'companyID': companyID, 'matchTime': matchTime,
                   'matchState': matchState, 'oddsID': None, 'finished_pre': None, 'oddsID_Q': None,
                   'finished_gun': None, 'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasHalf': 0, 'hasSecond': 0,
                   'detail': []}
        eur_sql = "SELECT oddsID,companyID,finished_pre,finished_gun,hasPre,hasIn,hasFirst,hasHalf,hasSecond,oddsID_Q " \
                  "FROM zq_europe " \
                  "WHERE scheduleID ={0} and companyID={1}".format(scheduleID, companyID)
        result = sql_util.select_Execute(eur_sql)
        if len(result) > 0:
            oddsID = result[0][0]
            oddsID_Q = result[0][9]
            collect['oddsID'] = oddsID
            collect['oddsID_Q'] = oddsID_Q
            collect['finished_pre'] = result[0][2]
            collect['finished_gun'] = result[0][3]
        if collect['finished_gun'] in [0, 1]:
            data = OddsDetailZq.collect_detail(soup, oddsID, matchTime, 3, oddsID_Q)
            collect['state'] = data['state']
            collect['detail'] = data['detail']
            if data['hasPre'] == 1:
                collect['hasPre'] = 1
            else:
                collect['hasPre'] = result[0][4]
            collect['hasIn'] = data['hasIn']
            collect['hasFirst'] = data['hasFirst']
            collect['hasHalf'] = data['hasHalf']
            collect['hasSecond'] = data['hasSecond']
        return collect

    @staticmethod
    # kind 1亚指 2 大小 3 欧赔
    def collect_detail(soup, oddsID, matchTime, kind, oddID_Q=None):
        collect = {'state': 2, 'oddsID': oddsID, 'hasPre': 0, 'hasIn': 0, 'hasFirst': 0, 'hasHalf': 0, 'hasSecond': 0,
                   'detail': [], 'oddsID_Q': oddID_Q}
        pre_details = []
        in_details = []
        # 是否包含赛前赔率
        hasPre = 0
        # 是否包含滚球赔率
        hasIn = 0
        # 上半场是否有记录
        hasFirst = 0
        # 中场是否有记录
        hasHalf = 0
        # 下半场是否有记录
        hasSecond = 0
        matchState = 0
        try:
            trs = soup.find_all('tr')
            count = len(trs)
            if count > 1:
                items = []
                for i in range(1, count):
                    item = []
                    tds = trs[i].selectData('td')
                    for td in tds:
                        item.append(td.text)
                    items.append(item)
                items.reverse()

                # 验证第一条数据，过滤残缺数据比赛
                if items[0][6] == '即' or items[0][6] == '早':
                    isCollect = True
                    matchState = 0
                elif items[0][6] == '滚' and items[0][0] != '中场' and items[0][0] != '' and int(items[0][0]) < 45:
                    isCollect = True
                    matchState = 1
                else:
                    isCollect = False

                if isCollect:
                    recentFirstTime = None
                    for item in items:
                        detail = [oddsID, None, None, None, None, None, None, None, None, None, None]
                        # 欧赔变化记录添加球探ID标记
                        if kind == 3:
                            detail.append(oddID_Q)
                        # detail = 'oddsID', 'matchState' ,'happenTime', 'oddsType', 'homeScore', 'awayScore',
                        # 'homeWin', 'standOff', 'awayWin', 'isBet', 'modifyTime',

                        # 获取变化时间
                        if item[5] != '' and len(item[5]) == 10:
                            modifyTime_str = item[5][0:5] + ' ' + item[5][5:10]
                            fixed = OddsDetailZq.getModifyTime(matchTime, modifyTime_str, item[6])
                            modifyTime = datetime.strptime(fixed, '%Y-%m-%d %H:%M')
                            detail[10] = modifyTime
                        else:
                            modifyTime = None
                        # 比赛状态纠正，变化时间>=45，比赛状态上半场，距离上次变化时间间隔超过4分钟
                        if matchState == 1 and recentFirstTime and modifyTime and item[0] != '中场' \
                                and item[0] != '' and int(item[0]) >= 45 \
                                and (modifyTime - recentFirstTime).seconds >= 240:
                            matchState = 3

                        # 状态和发生时间
                        if item[0].strip() == '中场':
                            matchState = 2
                        elif item[0].strip() != '':
                            happenTime = int(item[0])
                            detail[2] = happenTime
                            if matchState == 0 and happenTime <= 45:
                                matchState = 1
                            if matchState == 2:
                                matchState = 3
                        if item[1] != '-':
                            scores = item[1].split("-")
                            detail[4] = int(scores[0])
                            detail[5] = int(scores[1])

                        if item[2] != '':
                            detail[6] = float(item[2])

                        if item[3] == '封':
                            detail[9] = 0
                        else:
                            detail[9] = 1
                            if kind == 1:
                                detail[7] = OddsDetailZq.getGoal(item[3])
                            elif kind == 2:
                                goals = item[3].split("/")
                                if len(goals) > 1:
                                    detail[7] = float(goals[0]) + 0.25
                                else:
                                    detail[7] = float(goals[0])
                            else:
                                detail[7] = float(item[3])

                        if item[4] != '':
                            detail[8] = float(item[4])

                        # 盘口类型
                        if item[6] == '早':
                            detail[3] = 0
                            hasPre = 1
                        elif item[6] == '即':
                            detail[3] = 1
                            hasPre = 1
                        elif item[6] == '滚':
                            detail[3] = 2
                            hasIn = 1
                        else:
                            detail[3] = -1

                        if matchState == 1 and modifyTime:
                            recentFirstTime = modifyTime

                        detail[1] = matchState
                        if matchState == 1:
                            hasFirst = 1
                        if matchState == 2:
                            hasHalf = 1
                        if matchState == 3:
                            hasSecond = 1

                        if detail[3] == 0 or detail[3] == 1:
                            pre_details.append(detail)
                        elif detail[3] == 2:
                            in_details.append(detail)

        except Exception as e:
            print(e)
            excepstr = traceback.format_exc()
            print(excepstr)
            print(item)
            logLine(common_config.exception, ['detail', oddsID, kind, e])
        else:
            collect['state'] = 1
            collect['detail'] = {'pre': pre_details, 'in': in_details}
            collect['hasPre'] = hasPre
            collect['hasIn'] = hasIn
            collect['hasFirst'] = hasFirst
            collect['hasHalf'] = hasHalf
            collect['hasSecond'] = hasSecond
        return collect

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

    @staticmethod
    def getGoal(panKou):
        goalDict = {'平手': 0.0, '平手/半球': 0.25, '半球': 0.5, '半球/一球': 0.75, '一球': 1.0, '一球/球半': 1.25,
                    '球半': 1.5, '球半/两球': 1.75, '两球': 2.0, '两球/两球半': 2.25, '两球半': 2.5, '两球半/三球': 2.75,
                    '三球': 3.0, '三球/三球半': 3.25, '三球半': 3.5, '三球半/四球': 3.75, '四球': 4.0, '四球/四球半': 4.25,
                    '四球半': 4.5, '四球半/五球': 4.75, '五球': 5.0, '五球/五球半': 5.25, '五球半': 5.5, '五球半/六球': 5.75,
                    '六球': 6.0, '六球/六球半': 6.25, '六球半': 6.5, '六球半/七球': 6.75, '七球': 7.0, '七球/七球半': 7.25,
                    '七球半': 7.5, '七球半/八球': 7.75, '八球': 8.0, '八球/八球半': 8.25, '八球半': 8.5, '八球半/九球': 8.75,
                    '九球': 9.0, '九球/九球半': 9.25, '九球半': 9.5, '九球半/十球': 9.75, '十球': 10.0}
        if panKou[0:2] == '受让':
            if panKou[2:] in goalDict:
                goal = -float(goalDict[panKou[2:]])
            else:
                goal = -float(panKou[2:-1])
        else:
            if panKou in goalDict:
                goal = float(goalDict[panKou])
            else:
                goal = float(panKou[0:-1])
        return goal


class DetailThread(threading.Thread):
    def __init__(self, func, args=()):
        super(DetailThread, self).__init__()
        self.func = func
        self.args = args
        self.result = None

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        threading.Thread.join(self)
        try:
            return self.result
        except Exception as e:
            print(e)
            return None



    # OddsDetailZq.get_detail(239931, 3, "2024-02-27 04:00", matchState=None)