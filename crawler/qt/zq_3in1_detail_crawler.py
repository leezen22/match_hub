import threading
import time
from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.zq_match_dao import ZqMatchDao
from utils.dateUtil import getNowTime
from utils.webUtil import WebUtil


# Web三合一页面，多线程可自定义爬取变化记录内容

class DetailCrawler(object):
    # hasType, 采集内容 1赛前，2赛中，3 赛前+赛中，默认赛中
    def __init__(self, companyId, matchId, scheduleId=None,
                 asian_oddsId=None, total_oddsId=None, europe_oddsId=None,
                 matchState=None, matchTime=None,
                 asian_finished_pre=None, asian_finished_gun=None,
                 total_finished_pre=None, total_finished_gun=None,
                 europe_finished_pre=None, europe_finished_gun=None,
                 ):
        self.companyId = companyId
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.asian_oddsId = asian_oddsId
        self.total_oddsId = total_oddsId
        self.europe_oddsId = europe_oddsId
        self.matchState = matchState
        self.matchTime = matchTime
        self.asian_finished_pre = asian_finished_pre
        self.asian_finished_gun = asian_finished_gun
        self.total_finished_pre = total_finished_pre
        self.total_finished_gun = total_finished_gun
        self.europe_finished_pre = europe_finished_pre
        self.europe_finished_gun = europe_finished_gun

    @property
    def qt_web_host(self):
        return scrawler_config.qt_zq_web_host

    @property
    def qt_web_url(self):
        return "{0}?id={1}&companyid={2}".format(scrawler_config.qt_zq_web_3in1_url, self.scheduleId, self.companyId)

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

    @property
    def qt_pre_europe_keys(self):
        keys = [
            'homeWin', 'standOff', 'awayWin',
            'modifyTime', 'oddsType', 'isBet',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    @property
    def qt_gun_europe_keys(self):
        keys = [
            'homeWin', 'standOff', 'awayWin',
            'modifyTime', 'oddsType', 'isBet',
            'matchState', 'happenTime', 'homeScore', 'awayScore',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys
    # hasType, 采集内容 1赛前，2赛中，3 赛前+赛中，默认赛中
    def qt_web_get(self, hasType=2, hasAsian=True, hasTotal=True, hasEurope=True):
        headers = {"Host": self.qt_web_host}
        details = {'state': 0, 'matchId': self.matchId, 'companyId': self.companyId, 'scheduleId': self.scheduleId}
        if self.matchState is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState'], {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            details['matchState'] = matchState
        else:
            details['matchState'] = self.matchState
        if self.matchTime is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchTime'], {'matchId': self.matchId}, isDis=True)
            matchTime = result[0]['matchTime']
            details['matchTime'] = matchTime
        else:
            details['matchTime'] = self.matchTime

        response = WebUtil.requests_get(self.qt_web_url, headers=headers)
        state = response[0]

        if state == 1 and response[1] != '':
            try:
                soup = BeautifulSoup(response[1], 'html.parser')
                tables = soup.find_all('table', class_='gts')
                threads = []
                if hasAsian:
                    asianThread = DetailThread(collect_detail,
                                               args=(tables[0], 1, hasType, self.asian_oddsId,
                                                     self.matchId,  self.scheduleId, self.companyId,
                                                     details['matchTime']))

                    threads.append(asianThread)
                if hasTotal:
                    totalThread = DetailThread(collect_detail,
                                               args=(tables[1], 2, hasType, self.total_oddsId,
                                                     self.matchId,  self.scheduleId, self.companyId,
                                                     details['matchTime']))
                    threads.append(totalThread)
                if hasEurope:
                    europeThread = DetailThread(collect_detail,
                                                args=(tables[2], 3, hasType, self.europe_oddsId,
                                                      self.matchId, self.scheduleId, self.companyId,
                                                      details['matchTime']))
                    threads.append(europeThread)

                # 启动线程
                for t in threads:
                    t.start()
                # 等待所有线程完成
                for t in threads:
                    t.join()

                if hasAsian:
                    details['asian'] = asianThread.get_result()
                    details['asian']['finished_pre'] = self.asian_finished_pre
                    details['asian']['finished_gun'] = self.asian_finished_gun
                    details['asian']['matchState'] = self.matchState
                    if hasType != 2:
                        details['asian']['keys_pre'] = self.qt_pre_asian_keys
                    if hasType != 1:
                        details['asian']['keys_gun'] = self.qt_gun_asian_keys

                if hasTotal:
                    details['total'] = totalThread.get_result()
                    details['total']['finished_pre'] = self.total_finished_pre
                    details['total']['finished_gun'] = self.total_finished_gun
                    details['total']['matchState'] = self.matchState
                    if hasType != 2:
                        details['total']['keys_pre'] = self.qt_pre_total_keys
                    if hasType != 1:
                        details['total']['keys_gun'] = self.qt_gun_total_keys

                if hasEurope:
                    details['europe'] = europeThread.get_result()
                    details['europe']['finished_pre'] = self.europe_finished_pre
                    details['europe']['finished_gun'] = self.europe_finished_gun
                    details['europe']['matchState'] = self.matchState
                    if hasType != 2:
                        details['europe']['keys_pre'] = self.qt_pre_europe_keys
                    if hasType != 1:
                        details['europe']['keys_gun'] = self.qt_gun_europe_keys

                section_states = []
                if hasAsian:
                    section_states.append(details['asian']['state'])
                if hasTotal:
                    section_states.append(details['total']['state'])
                if hasEurope:
                    section_states.append(details['europe']['state'])
                if section_states and all(state == 1 for state in section_states):
                    details['state'] = 1
            except Exception as e:
                print(e)
                time.sleep(1)
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


# kind 1亚指 2 大小 3 欧赔
def collect_detail(soup, kind, hasType, oddsId, matchId, scheduleId=None,
                   companyId=None, matchTime=None):
    detail = {'state': 0, 'oddsId': oddsId, 'matchId': matchId, 'scheduleId': scheduleId, 'companyId': companyId}
    items = []
    try:
        trs = soup.find_all('tr')
        count = len(trs)
        for i in range(1, count):
            item = []
            tds = trs[i].select('td')
            for td in tds:
                item.append(td.text)
            items.append(item)
        items.reverse()
        gun = []
        pre = []
        # 是否包含赛前赔率
        hasPre = 0
        # 是否包含滚球赔率
        hasGun = 0
        # 上半场是否有记录
        hasFirst = 0
        # 中场是否有记录
        hasHalf = 0
        # 下半场是否有记录
        hasSecond = 0
        if len(items) > 0:
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
                    # 获取变化时间
                    if item[5] != '' and len(item[5]) == 10:
                        modifyTime_str = item[5][0:5] + ' ' + item[5][5:10]
                        fixed = getModifyTime(matchTime, modifyTime_str, item[6])
                        modifyTime = datetime.strptime(fixed, '%Y-%m-%d %H:%M')
                    else:
                        modifyTime = None
                    # 比赛状态纠正，变化时间>=45，比赛状态上半场，距离上次变化时间间隔超过4分钟
                    if matchState == 1 and recentFirstTime and modifyTime and item[0] != '中场' \
                            and item[0] != '' and int(item[0]) >= 45 \
                            and (modifyTime - recentFirstTime).seconds >= 240:
                        matchState = 3

                    # 状态和发生时间
                    happenTime = None
                    if item[0].strip() == '中场':
                        matchState = 2
                        happenTime = 45
                    elif item[0].strip() != '':
                        happenTime = int(item[0])
                        if matchState == 0 and happenTime <= 45:
                            matchState = 1
                        if matchState == 2:
                            matchState = 3
                    if hasType == 1 and matchState != 0:
                        break

                    if (hasType == 1 and matchState == 0) or (hasType == 2 and matchState != 0) or hasType == 3:
                        if item[1] != '-':
                            scores = item[1].split("-")
                            homeScore = int(scores[0])
                            awayScore = int(scores[1])
                        else:
                            homeScore = 0
                            awayScore = 0

                        if item[2] != '':
                            odds1 = float(item[2])
                        else:
                            odds1 = 0.00

                        if item[3] == '封':
                            isBet = 0
                            goal = 0.00
                        else:
                            isBet = 1
                            if kind == 1:
                                goal = getGoal(item[3])
                            elif kind == 2:
                                goals = item[3].split("/")
                                if len(goals) > 1:
                                    goal = float(goals[0]) + 0.25
                                else:
                                    goal = float(goals[0])
                            else:
                                goal = float(item[3])

                        if item[4] != '':
                            odds2 = float(item[4])
                        else:
                            odds2 = 0.00

                        # 盘口类型
                        if item[6] == '早':
                            oddsType = 0
                            hasPre = 1
                        elif item[6] == '即':
                            oddsType = 1
                            hasPre = 1
                        elif item[6] == '滚':
                            oddsType = 2
                            hasGun = 1
                        else:
                            oddsType = -1
                        if matchState == 1:
                            hasFirst = 1
                        if matchState == 2:
                            hasHalf = 1
                        if matchState == 3:
                            hasSecond = 1
                        if matchState == 0 and hasType != 2:
                            odds_data = [odds1, goal, odds2,
                                         modifyTime, oddsType, isBet,
                                         oddsId, companyId, matchId, scheduleId, 6]
                            pre.append(odds_data)
                        elif matchState != 0 and hasType != 1:
                            odds_data = [odds1, goal, odds2,
                                         modifyTime, oddsType, isBet,
                                         matchState, happenTime, homeScore, awayScore,
                                         oddsId, companyId, matchId, scheduleId, 6]
                            gun.append(odds_data)
                        else:
                            pass
                        if matchState == 1 and modifyTime:
                            recentFirstTime = modifyTime
            detail['state'] = 1
            if hasType != 2:
                detail['hasPre'] = hasPre
                detail['pre'] = pre
            if hasType != 1:
                detail['hasGun'] = hasGun
                detail['hasFirst'] = hasFirst
                detail['hasHalf'] = hasHalf
                detail['hasSecond'] = hasSecond
                detail['gun'] = gun
        else:
            detail['state'] = 1
            detail['hasPre'] = 0
            detail['pre'] = pre
            detail['hasGun'] = 0
            detail['hasFirst'] = 0
            detail['hasHalf'] = 0
            detail['hasSecond'] = 0
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


# if __name__ == '__main__':
#     print(getNowTime())
#     """matchId, companyId, hasType=2, scheduleId=None,
#                  asian_oddsId=None, total_oddsId=None, europe_oddsId=None,
#                  matchState=None, matchTime=None,
#                  hasAsian=True, hasTotal=True, hasEurope=True,
#                  asian_finished_pre=None, asian_finished_gun=None,
#                  total_finished_pre=None, total_finished_gun=None,
#                  europe_finished_pre=None, europe_finished_gun=None,"""
#     str_p = '2020-05-27 00:30'
#     matchTime2 = datetime.strptime(str_p, '%Y-%m-%d %H:%M')
#     detailCrawler = DetailCrawler(3, 199152, 2513324, matchTime=matchTime2, matchState=-1)
#     data = detailCrawler.qt_web_get(3, True, True, False)
#     print(data)
