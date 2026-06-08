import json
from datetime import datetime
from config import scrawler_config
from dao.zq_match_dao import ZqMatchDao
from utils.webUtil import WebUtil


class TotalDetailCrawler(object):
    def __init__(self, scheduleId, companyId, hasType=3, matchId=None,
                 oddsId=None, matchState=None,
                 matchTime=None, finished_pre=None, finished_gun=None):
        self.companyId = companyId
        self.oddsId = oddsId
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.hasType = hasType
        self.matchState = matchState
        self.matchTime = matchTime
        self.finished_pre = finished_pre
        self.finished_gun = finished_gun

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_zq_live_host
    @property
    def qt_mobile_url(self):
        return "{0}&scheid={1}&companyid={2}".format(scrawler_config.qt_zq_mobile_totalDetail_url,
                                                  self.scheduleId, self.companyId)

    @property
    def qt_web_url(self):
        return "{0}?id={1}&companyid={2}&l=0".format(scrawler_config.qt_zq_web_toalDetails_url,self.scheduleId, self.companyId)

    @property
    def qt_pre_keys(self):
        keys = [
            'highOdds', 'goal', 'lowOdds',
            'modifyTime', 'oddsType', 'isBet',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    @property
    def qt_gun_keys(self):
        keys = [
            'highOdds', 'goal', 'lowOdds',
            'modifyTime', 'oddsType', 'isBet',
            'matchState', 'happenTime', 'homeScore', 'awayScore',
            'oddsId', 'companyId', 'matchId', 'scheduleId', 'kind'
        ]
        return keys

    # 只包含赛前初盘+即时盘，无滚球盘口
    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host}
        details = {'state': 0, 'matchId': self.matchId, 'companyId': self.companyId,
                   'scheduleId': self.scheduleId, 'oddsId': self.oddsId,
                   'matchState': self.matchState}
        if self.hasType == 1:
            details['finished_pre'] = self.finished_pre
            details['keys_pre'] = self.qt_pre_keys
            details['pre'] = []
        elif self.hasType == 2:
            details['finished_gun'] = self.finished_gun
            details['keys_gun'] = self.qt_gun_keys
            details['gun'] = []
        else:
            details['finished_pre'] = self.finished_pre
            details['finished_gun'] = self.finished_gun
            details['keys_pre'] = self.qt_pre_keys
            details['pre'] = []
            details['keys_gun'] = self.qt_gun_keys
            details['gun'] = []
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_mobile_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            try:
                jsonData = json.loads(webResponse[1])
                jsonData.reverse()
                if len(jsonData) > 0 and (jsonData[0]['Score'] == '即' or jsonData[0]['Score'] == '早'):
                    details['state'] = 1
                    matchState = 0
                    recentFirstTime = None
                    for item in jsonData:
                        # 比赛状态，发生时间
                        if item['ModifyTime'] != '':
                            modifyTime = datetime.strptime(item['ModifyTime'], '%Y%m%d%H%M%S')
                            # modifyTime = str(modifyTime)
                        else:
                            modifyTime = None
                        # 赔率记录完整
                        if matchState == 1 and recentFirstTime and modifyTime and item['HappenTime'] != '中场' \
                                and item['HappenTime'] != '' and int(item['HappenTime']) >= 45 \
                                and (modifyTime - recentFirstTime).seconds >= 240:
                            matchState = 3

                        happenTime = None
                        if item['HappenTime'].strip() == '中场':
                            matchState = 2
                        elif item['HappenTime'].strip() != '':
                            happenTime = int(item['HappenTime'])
                            if matchState == 0 and happenTime <= 45:
                                matchState = 1
                            if matchState == 2:
                                matchState = 3

                        if (self.hasType == 1 and matchState == 0) \
                                or (self.hasType == 2 and matchState != 0) \
                                or self.hasType == 3:
                            # 盘口类型，主队进球数，客队进球数
                            homeScore = None
                            awayScore = None
                            if item['Score'] == '早':
                                oddsType = 0
                            elif item['Score'] == '即':
                                oddsType = 1
                            else:
                                scores = item['Score'].split("-")
                                oddsType = 2
                                homeScore = scores[0]
                                awayScore = scores[1]

                            # 主队赔率、盘口、客队赔率
                            highOdds = item['HomeOdds']
                            goal = item['PanKou']
                            lowOdds = item['AwayOdds']

                            # 1 开盘 0 封盘
                            if item['IsClosed'] == '封':
                                isBet = 0
                            else:
                                isBet = 1

                            if matchState == 1 and modifyTime:
                                recentFirstTime = modifyTime

                            if self.hasType != 2:
                                detail = [highOdds, goal, lowOdds,
                                          modifyTime, oddsType, isBet,
                                          self.oddsId, self.companyId, self.matchId, self.scheduleId, 6]
                                details['pre'].append(detail)
                            elif self.hasType != 1:
                                detail = [highOdds, goal, lowOdds,
                                          modifyTime, oddsType, isBet,
                                          matchState, happenTime, homeScore, awayScore,
                                          self.oddsId, self.companyId, self.matchId, self.scheduleId, 6]
                                details['gun'].append(detail)
                            else:
                                pass
                        elif self.hasType == 1 and matchState != 0:
                            break
                        else:
                            pass
                else:
                    details['state'] = 0
            except Exception as e:
                print(e)
        # 返回亚指开盘公司初盘和终盘盘口
        return details


    def qt_web_get(self):
        headers = {"Host": self.qt_web_host}
        details = {'state': 0, 'matchId': self.matchId, 'companyId': self.companyId,
                   'scheduleId': self.scheduleId, 'oddsId': self.oddsId,
                   'matchState': self.matchState}
        if self.hasType == 1:
            details['finished_pre'] = self.finished_pre
            details['keys_pre'] = self.qt_pre_keys
            details['pre'] = []
        elif self.hasType == 2:
            details['finished_gun'] = self.finished_gun
            details['keys_gun'] = self.qt_gun_keys
            details['gun'] = []
        else:
            details['finished_pre'] = self.finished_pre
            details['finished_gun'] = self.finished_gun
            details['keys_pre'] = self.qt_pre_keys
            details['pre'] = []
            details['keys_gun'] = self.qt_gun_keys
            details['gun'] = []
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            try:
                jsonData = json.loads(webResponse[1])
                jsonData.reverse()
                if len(jsonData) > 0 and (jsonData[0]['Score'] == '即' or jsonData[0]['Score'] == '早'):
                    details['state'] = 1
                    matchState = 0
                    recentFirstTime = None
                    for item in jsonData:
                        # 比赛状态，发生时间
                        if item['ModifyTime'] != '':
                            modifyTime = datetime.strptime(item['ModifyTime'], '%Y%m%d%H%M%S')
                            # modifyTime = str(modifyTime)
                        else:
                            modifyTime = None
                        # 赔率记录完整
                        if matchState == 1 and recentFirstTime and modifyTime and item['HappenTime'] != '中场' \
                                and item['HappenTime'] != '' and int(item['HappenTime']) >= 45 \
                                and (modifyTime - recentFirstTime).seconds >= 240:
                            matchState = 3

                        happenTime = None
                        if item['HappenTime'].strip() == '中场':
                            matchState = 2
                        elif item['HappenTime'].strip() != '':
                            happenTime = int(item['HappenTime'])
                            if matchState == 0 and happenTime <= 45:
                                matchState = 1
                            if matchState == 2:
                                matchState = 3

                        if (self.hasType == 1 and matchState == 0) \
                                or (self.hasType == 2 and matchState != 0) \
                                or self.hasType == 3:
                            # 盘口类型，主队进球数，客队进球数
                            homeScore = None
                            awayScore = None
                            if item['Score'] == '早':
                                oddsType = 0
                            elif item['Score'] == '即':
                                oddsType = 1
                            else:
                                scores = item['Score'].split("-")
                                oddsType = 2
                                homeScore = scores[0]
                                awayScore = scores[1]

                            # 主队赔率、盘口、客队赔率
                            highOdds = item['HomeOdds']
                            goal = item['PanKou']
                            lowOdds = item['AwayOdds']

                            # 1 开盘 0 封盘
                            if item['IsClosed'] == '封':
                                isBet = 0
                            else:
                                isBet = 1

                            if matchState == 1 and modifyTime:
                                recentFirstTime = modifyTime

                            if self.hasType != 2:
                                detail = [highOdds, goal, lowOdds,
                                          modifyTime, oddsType, isBet,
                                          self.oddsId, self.companyId, self.matchId, self.scheduleId, 6]
                                details['pre'].append(detail)
                            elif self.hasType != 1:
                                detail = [highOdds, goal, lowOdds,
                                          modifyTime, oddsType, isBet,
                                          matchState, happenTime, homeScore, awayScore,
                                          self.oddsId, self.companyId, self.matchId, self.scheduleId, 6]
                                details['gun'].append(detail)
                            else:
                                pass
                        elif self.hasType == 1 and matchState != 0:
                            break
                        else:
                            pass
                else:
                    details['state'] = 0
            except Exception as e:
                print(e)
        # 返回亚指开盘公司初盘和终盘盘口
        return details


if __name__ == '__main__':
    """
        def __init__(self, companyId, matchId, scheduleId=None,
                 hasType=3,
                 oddsId=None, matchState=None,
                 matchTime=None, finished_pre=None, finished_gun=None):"""
    detailCrawler = TotalDetailCrawler(1736607, 3, 2)
    data = detailCrawler.qt_mobile_get()
    print(data)
    # t = time.time()
    # print(int(t)*1000)
