import random
import re
import threading
from bs4 import BeautifulSoup
import requests

from config import scrawler_config, common_config
from utils import sql_util


# from src.utils.webUtil import WebUtil


# Web二合一页面，多线程可自定义爬取变化记录内容
class Lq2in1Crawler(object):
    # scope, 采集内容 1赛前，2赛中，3 赛前+赛中，默认赛前
    def __init__(self, matchId, companyId, scheduleId=None,
                 asian_oddsId=None, total_oddsId=None,
                 matchState=None, matchTime=None,
                 asian_finished_pre=None, asian_finished_gun=None,
                 total_finished_pre=None, total_finished_gun=None):
        self.companyId = companyId
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.asian_oddsId = asian_oddsId
        self.total_oddsId = total_oddsId
        self.matchState = matchState
        self.matchTime = matchTime
        self.asian_finished_pre = asian_finished_pre
        self.asian_finished_gun = asian_finished_gun
        self.total_finished_pre = total_finished_pre
        self.total_finished_gun = total_finished_gun

    @property
    def qt_web_host(self):
        return scrawler_config.qt_lq_web_host

    @property
    def qt_web_url(self):
        return "{0}?Id={1}&cId={2}&t=6".format(scrawler_config.qt_lq_web_2in1_url, self.scheduleId, self.companyId)

    @property
    def qt_pre_asian_keys(self):
        keys = [
            'homeOdds', 'goal', 'awayOdds',
            'modifyTime', 'oddsType', 'isBet',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    @property
    def qt_gun_asian_keys(self):
        keys = [
            'homeOdds', 'goal', 'awayOdds',
            'modifyTime', 'oddsType', 'isBet',
            'matchState', 'happenTime', 'homeScore', 'awayScore',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    @property
    def qt_pre_total_keys(self):
        keys = [
            'highOdds', 'goal', 'lowOdds',
            'modifyTime', 'oddsType', 'isBet',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    @property
    def qt_gun_total_keys(self):
        keys = [
            'highOdds', 'goal', 'lowOdds',
            'modifyTime', 'oddsType', 'isBet',
            'matchState', 'happenTime', 'homeScore', 'awayScore',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    # scope=1 赛前, scope=2 滚球, scope=3 赛前+赛中
    def qt_web_get(self, scope=2, hasAsian=True, hasTotal=True,):
        headers = {"Host": self.qt_web_host}
        details = {'state': 0, 'matchId': self.matchId, 'companyId': self.companyId, 'scheduleId': self.scheduleId,
                   'matchState': self.matchState}
        headers['User-Agent'] = random.choice(common_config.web_agents)
        if self.matchState is None:
            result = sql_util.select_table_dicts(
                'lq_schedule',
                ['matchId', 'matchState'],
                {'matchId': self.matchId},
                isDis=True,
            )
            if not result:
                return details
            matchState = result[0]['matchState']
            details['matchState'] = matchState
        else:
            details['matchState'] = self.matchState
        if self.matchTime is None:
            result = sql_util.select_table_dicts(
                'lq_schedule',
                ['matchId', 'matchTime'],
                {'matchId': self.matchId},
                isDis=True,
            )
            if not result:
                return details
            matchTime = result[0]['matchTime']
            details['matchTime'] = matchTime
        else:
            details['matchTime'] = self.matchTime

        response = requests.get(self.qt_web_url, headers=headers,timeout=5)
        state = response.status_code
        content = response.text.strip()
        # print(state, content)
        # response = WebUtil.requests_get(self.qt_web_url, headers=headers)
        # state = response[0]
        # content = response[1]
        # if state == 1 and content != '':
        if state == 200 and content != '':
            try:
                fixed = re.sub(r'</td>\r\n(.*?)<tr(.*?)bgcolor="#FFFFFF">',
                               '</td>\r\n</tr>\r\n<tr bgcolor="#FFFFFF">',
                               content)
                soup = BeautifulSoup(fixed, 'html.parser')
                tables = soup.find_all('table', class_='jtd')
                threads = []
                if hasAsian:
                    asianThread = DetailThread(collect_detail,
                                               args=(tables[0], scope, self.asian_oddsId,
                                                     self.matchId,  self.scheduleId, self.companyId,
                                                     details['matchTime']))

                    threads.append(asianThread)
                if hasTotal:
                    totalThread = DetailThread(collect_detail,
                                               args=(tables[1], scope, self.total_oddsId,
                                                     self.matchId, self.scheduleId, self.companyId,
                                                     details['matchTime']))
                    threads.append(totalThread)
                # 启动线程
                for t in threads:
                    t.start()
                # 等待所有线程完成
                for t in threads:
                    t.join()

                if hasAsian:
                    details['asian'] = asianThread.get_result()
                    # details['asian'] = {}
                    details['asian']['finished_pre'] = self.asian_finished_pre
                    details['asian']['finished_gun'] = self.asian_finished_gun
                    details['asian']['matchState'] = self.matchState
                    if scope != 2:
                        details['asian']['keys_pre'] = self.qt_pre_asian_keys
                    if scope != 1:
                        details['asian']['keys_gun'] = self.qt_gun_asian_keys

                if hasTotal:
                    details['total'] = totalThread.get_result()
                    # details['total'] = {}
                    details['total']['finished_pre'] = self.total_finished_pre
                    details['total']['finished_gun'] = self.total_finished_gun
                    details['total']['matchState'] = self.matchState
                    if scope != 2:
                        details['total']['keys_pre'] = self.qt_pre_total_keys
                    if scope != 1:
                        details['total']['keys_gun'] = self.qt_gun_total_keys

            except Exception as e:
                print(e)
            else:
                details['state'] = 1
        return details


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


# 获取变化记录
def collect_detail(soup, scope, oddsId, matchId, scheduleId=None,
                   companyId=None, matchTime=None):
    detail = {'state': 0, 'oddsId': oddsId, 'matchId': matchId, 'scheduleId': scheduleId, 'companyId': companyId}
    matchStateDict = scrawler_config.lq_matchState
    try:
        trs = soup.find_all('tr')
        count = len(trs)
        # 标题栏占用长度度2
        pre = []
        gun = []
        hasPre = 0
        # 是否包含滚球赔率
        hasGun = 0
        # 上半场是否有记录
        hasFirst = 0
        hasSecond = 0
        # 中场是否有记录
        hasHalf = 0
        # 下半场是否有记录
        hasThird = 0
        hasFour = 0
        if count > 2:
            odds_trs = trs[2:]
            if matchTime is None:
                result = sql_util.select_table_dicts(
                    'lq_schedule',
                    ['matchId', 'matchTime'],
                    {'matchId': matchId},
                    isDis=True,
                )
                if not result:
                    return detail
                matchTime = result[0]['matchTime']
            for tr in odds_trs:
                tds = tr.select('td')
                data0 = tds[0].text
                happenTime = None
                if data0 == '':
                    matchState = 0
                else:
                    time = data0.split(' ')
                    if len(time) == 1:
                        matchState = matchStateDict[time[0]]
                    else:
                        matchState = matchStateDict[time[0]]
                        if len(time[1].replace(" ", "")) > 0:
                            happenTime = time[1]

                if scope == 2 and matchState == 0:
                    break

                if (scope == 1 and matchState == 0) or (scope == 2 and matchState != 0) or scope == 3:
                    data1 = tds[1].text
                    if data1 != '-' and data1 != '':
                        homeScore = data1.split('-')[0]
                        awayScore = data1.split('-')[1]
                    else:
                        homeScore = None
                        awayScore = None
                    data2 = tds[2].text
                    if data2 != '':
                        odds1 = data2
                    else:
                        odds1 = None
                    data3 = tds[3].text.strip()
                    if data3 == '' or data3 == '封':
                        isBet = 0
                        goal = None
                    else:
                        goal = data3
                        isBet = 1
                    data4 = tds[4].text
                    if data4 != '':
                        odds2 = data4
                    else:
                        odds2 = None
                    data6 = tds[6].text
                    if data6 == '滚':
                        oddsType = '2'
                        hasGun = 1
                    elif data6 == '即':
                        oddsType = '1'
                        hasPre = 1
                    else:
                        oddsType = '0'
                        hasPre = 1

                    if matchState == 1:
                        hasFirst = 1
                    if matchState == 2:
                        hasSecond = 1
                    if matchState == 3:
                        hasThird = 1
                    if matchState == 4:
                        hasFour = 1
                    if matchState == 50:
                        hasHalf = 1

                    data5 = tds[5].text
                    if data5 != '':
                        modifyTime = data5[0:5] + ' ' + data5[5:10]
                        modifyTime = getModifyTime(matchTime, modifyTime, data6)
                    else:
                        modifyTime = None

                    if matchState == 0:
                        odds_data = [odds1, goal, odds2,
                                     modifyTime, oddsType, isBet,
                                     oddsId, companyId, matchId, scheduleId, 6]
                        pre.append(odds_data)
                    else:
                        odds_data = [odds1, goal, odds2,
                                     modifyTime, oddsType, isBet,
                                     matchState, happenTime, homeScore, awayScore,
                                     oddsId, companyId, matchId, scheduleId, 6]
                        gun.append(odds_data)
        pre.reverse()
        gun.reverse()
        detail['state'] = 1
        if scope != 2:
            detail['hasPre'] = hasPre
            detail['pre'] = pre
        if scope != 1:
            detail['hasGun'] = hasGun
            detail['hasFirst'] = hasFirst
            detail['hasSecond'] = hasSecond
            detail['hasHalf'] = hasHalf
            detail['hasThird'] = hasThird
            detail['hasFour'] = hasFour
            detail['gun'] = gun
    except Exception as e:
        print(e)
    return detail


def getModifyTime(mtime, modifyTime_str, oddsType):
    match_y = mtime.year
    match_m = mtime.month
    modify_m = int(modifyTime_str[0:2])
    if oddsType == '即' and modify_m > match_m:
        modify_y = match_y - 1
    elif oddsType == '滚' and modify_m < match_m and modify_m == 1:
        modify_y = match_y + 1
    else:
        modify_y = match_y
    modifyTime = str(modify_y) + '-' + modifyTime_str
    return modifyTime


# if __name__ == '__main__':
#     """companyId, matchId, scheduleId=None,
#                  scope=2,
#                  asian_oddsId=None, total_oddsId=None,
#                  matchState=None, matchTime=None,
#                  hasAsian=True, hasTotal=True,
#                  asian_finished_pre=None, asian_finished_gun=None,
#                  total_finished_pre=None, total_finished_gun=None"""
#     str_p = '2026-05-17 13:05'
#     matchTime2 = datetime.strptime(str_p, '%Y-%m-%d %H:%M')
#     detailCrawler = Lq2in1Crawler(716648, 3, 716648, matchTime=matchTime2, matchState=0)
#     data = detailCrawler.qt_web_get(scope=3)
#     print(data)
