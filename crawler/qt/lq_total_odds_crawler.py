import traceback
from bs4 import BeautifulSoup
from config import scrawler_config, lqconfig_qt
from dao.lq_match_dao import LqMatchDao
from utils.fileUtil import logLine
from utils.webUtil import WebUtil


class TotalScoreCrawler(object):
    def __init__(self, matchId, scheduleId=None, matchState=None, finished=None):
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.finished = finished

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_web_host(self):
        return scrawler_config.qt_lq_web_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_lq_mobile_totalOdds_url, self.scheduleId)

    @property
    def qt_web_url(self):
        return "{0}?id={1}".format(scrawler_config.qt_lq_web_totalOdds_url, self.scheduleId)

    def qt_web_get(self):
        headers = {"Host": self.qt_web_host}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'finished': self.finished,
                    "odds": []}
        if self.matchState is None:
            result = LqMatchDao.select_dicts(['matchId', 'matchState'], {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            # companyDict = {'澳门': 1, '皇冠': 3, 'SB': 3, '立博': 4,
            #                'bet365': 8, '易胜博': 2, '韦德': 9, '利记': 31}
            # lqconfig_qt.companys[CompanyName]
            # 获取页面成功
            try:
                soup = BeautifulSoup(content, 'html.parser')
                # 赔率table tr 标签
                odds_tr = soup.select('body table#odds tr')
                counts = len(odds_tr)
                # 判断让分指数公司列表是否为空，大于2不为空
                if counts > 2:
                    for i in range(2, counts):
                        tds = odds_tr[i].select('td')
                        # 多盘口让分指数，tr标签有classs属性
                        if odds_tr[i].has_attr('optimize') or tds[1].find('span') is None:
                            pass
                        # 无class属性，tr则为主盘口
                        else:
                            # companyId = tds[1].find('span').get('companyid')
                            companyName = tds[0].get_text().replace("\r\n", "").strip()
                            if companyName in lqconfig_qt.companys.keys():
                                companyId = lqconfig_qt.companys[companyName]
                            else:
                                companyId = None
                            highOdds_F = tds[2].get_text().replace("\r\n", "").strip()
                            totalScore_F = tds[3].get_text().replace("\r\n", "").strip()
                            lowOdds_F = tds[4].get_text().replace("\r\n", "").strip()
                            highOdds = tds[8].get_text().replace("\r\n", "").strip()
                            totalScore = tds[9].get_text().replace("\r\n", "").strip()
                            lowOdds = tds[10].get_text().replace("\r\n", "").strip()
                            highOdds_R = tds[5].get_text().replace("\r\n", "").strip()
                            totalScore_R = tds[6].get_text().replace("\r\n", "").strip()
                            lowOdds_R = tds[7].get_text().replace("\r\n", "").strip()
                            time_data = tds[11].get_text().replace(u'\xa0', u'').strip().split(" ")
                            if len(time_data) > 2:
                                modifyTime = '{0} {1}'.format(time_data[0], time_data[1])
                            else:
                                modifyTime = None
                            company_oddsData = [self.matchId, self.scheduleId, companyId, companyName,
                                                highOdds_F, totalScore_F, lowOdds_F,
                                                highOdds, totalScore, lowOdds,
                                                highOdds_R, totalScore_R, lowOdds_R,
                                                modifyTime]
                            keys = [
                                'matchId', 'scheduleId', 'companyId', 'companyName',
                                'highOdds_F', 'goal_F', 'lowOdds_F',
                                'highOdds', 'goal', 'lowOdds',
                                'highOdds_R', 'goal_R', 'lowOdds_R',
                                'modifyTime'
                            ]
                            oddsDict = {}
                            for j in range(0, len(company_oddsData)):
                                if company_oddsData[j] != '' and company_oddsData[j] is not None:
                                    oddsDict[keys[j]] = company_oddsData[j]
                                # html标签提取数据正常，将公司开盘信息插入赔率列表
                            if len(oddsDict) > 5 and companyId is not None:
                                oddsData['odds'].append(oddsDict)
            except Exception as e:
                excepstr = traceback.format_exc()
                print("lq total web odds parse failed: scheduleId={0}, error={1}".format(self.scheduleId, e))
                if oddsData['odds']:
                    oddsData['state'] = 1
            else:
                oddsData['state'] = 1
        # 返回亚指开盘公司初盘和终盘盘口
        elif webResponse[0] == 4:
            oddsData['state'] = 4
        return oddsData

    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host}
        oddsData = {'state': 0, 'matchId': self.matchId, 'scheduleId': self.scheduleId,
                    'matchState': self.matchState, 'finished': self.finished,
                    "odds": []}
        if self.matchState is None:
            result = LqMatchDao.select_dicts(['matchId', 'matchState'],
                                             {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            oddsData['matchState'] = matchState
        else:
            oddsData['matchState'] = self.matchState
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_mobile_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            # 获取页面成功
            try:
                soup = BeautifulSoup(content, 'html.parser')
                table = soup.find('table', id='oTable')
                if table is not None:
                    # companyDict = {'澳门': 1, '皇冠': 3, 'SB': 3, '立博': 4,
                    #                'bet365': 8, '易胜博': 2, '韦德': 9, '利记': 31}
                    # 赔率table tr 标签
                    odds_tr = table.select('tr')
                    counts = len(odds_tr)
                    # 判断让分指数公司列表是否为空，大于1不为空
                    if counts > 1:
                        for i in range(1, counts):
                            tds = odds_tr[i].select('td')
                            # spans = odds_tr[i].select('span')
                            companyName = tds[0].get_text().strip()
                            # companyId = lqconfig_qt.companys[companyName]
                            if companyName in lqconfig_qt.companys.keys():
                                companyId = lqconfig_qt.companys[companyName]
                            else:
                                companyId = None
                            spans_td1 = tds[1].select('span')
                            spans_td2 = tds[2].select('span')
                            highOdds_F = spans_td1[0].get_text().strip()
                            totalScore_F = spans_td1[1].get_text().strip()
                            lowOdds_F = spans_td1[2].get_text().strip()
                            highOdds = spans_td2[0].get_text().strip()
                            totalScore = spans_td2[1].get_text().strip()
                            lowOdds = spans_td2[2].get_text().strip()
                            company_oddsData = [self.matchId, self.scheduleId, companyId, companyName,
                                                highOdds_F, totalScore_F, lowOdds_F,
                                                highOdds, totalScore, lowOdds]
                            keys = [
                                'matchId', 'scheduleId', 'companyId', 'companyName',
                                'highOdds_F', 'goal_F', 'lowOdds_F',
                                'highOdds', 'goal', 'lowOdds'
                            ]
                            oddsDict = {}
                            for j in range(0, len(company_oddsData)):
                                if company_oddsData[j] != '' and company_oddsData[j] is not None:
                                    oddsDict[keys[j]] = company_oddsData[j]
                            if len(oddsDict) > 5 and companyId is not None:
                                oddsData['odds'].append(oddsDict)
                else:
                    return oddsData
            except Exception as e:
                # excepstr = traceback.format_exc()
                # logLine(lqconfig_qt.exception, excepstr)
                # 本地记录失败记录
                print("lq total mobile odds parse failed: scheduleId={0}, error={1}".format(self.scheduleId, e))
                if oddsData['odds']:
                    oddsData['state'] = 1
                # 获取页面成功
            else:
                oddsData['state'] = 1
        elif webResponse[0] == 4:
            oddsData['state'] = 4
        return oddsData

    # @property
    # def qt_web_keys(self):
    #     keys = [
    #         'matchId', 'scheduleId', 'companyId', 'companyName',
    #         'highOdds_F', 'goal_F', 'lowOdds_F',
    #         'highOdds', 'goal', 'lowOdds',
    #         'highOdds_R', 'goal_R', 'lowOdds_R',
    #         'modifyTime'
    #     ]
    #     return keys
    #
    # @property
    # def qt_mobile_keys(self):
    #     keys = [
    #         'matchId', 'scheduleId', 'companyId', 'companyName',
    #         'highOdds_F', 'goal_F', 'lowOdds_F',
    #         'highOdds', 'goal', 'lowOdds'
    #     ]
    #     return keys


if __name__ == '__main__':
    cawler = TotalScoreCrawler(199152, 366987, -1)
    data = cawler.qt_web_get()
    print(data)
