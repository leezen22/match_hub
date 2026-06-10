from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.zq_match_dao import ZqMatchDao
from utils.webUtil import WebUtil


class EuropeDetailCrawler(object):
    def __init__(self, matchId, companyId, scheduleId=None, oddsId=None, matchState=None,
                 matchTime=None, finished_pre=None, finished_in=None):
        self.companyId = companyId
        self.oddsId = oddsId
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.matchTime = matchTime
        self.finished_pre = finished_pre
        self.finished_in = finished_in

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}/{2}.htm".format(scrawler_config.qt_zq_mobile_europeDetail_url,
                                        self.companyId, self.scheduleId)

    @property
    def qt_pre_keys(self):
        keys = [
            'homeWin', 'standOff', 'awayWin',
            'kelly_Home', 'kelly_Off', 'kelly_away',
            'modifyTime',
            'oddsId', 'companyId', 'matchId', 'scheduleId'
        ]
        return keys

    @property
    def qt_mobile_refer(self):
        return "{0}/{1}.htm".format(scrawler_config.qt_zq_mobile_europeOdds_url, self.scheduleId)

    # 采集赛前赔率变化记录
    def qt_mobile_get_detail(self):
        headers = {"Host": self.qt_mobile_host, 'Referer': self.qt_mobile_refer}
        details = {'state': 0, 'matchId': self.matchId, 'companyId': self.companyId,
                   'oddsId': self.oddsId, 'scheduleId': self.scheduleId, 'matchState': self.matchState,
                   'finished_pre': self.finished_pre, 'finished_in': self.finished_in,
                   'keys_pre': self.qt_pre_keys, "pre": []}
        if self.matchState is None:
            result = ZqMatchDao.select_dicts(['matchId', 'matchState'],
                                             {'matchId': self.matchId}, isDis=True)
            matchState = result[0]['matchState']
            details['matchState'] = matchState
        else:
            details['matchState'] = self.matchState
        # 访问篮球亚指页面，response返回页面HTML内容
        webResponse = WebUtil.requests_get(self.qt_mobile_url, headers=headers)
        content = webResponse[1]
        if webResponse[0] == 1 and content != '':
            # 获取页面成功
            try:
                soup = BeautifulSoup(content, 'html.parser')
                tables = soup.find_all(class_='mytable3')
                if len(tables) == 1:
                    table = tables[0]
                elif len(tables) > 1:
                    table = tables[1]
                else:
                    table = None
                if table is not None:
                    # 赔率table tr 标签
                    odds_tr = table.select('tr')
                    counts = len(odds_tr)
                    # 判断让分指数公司列表是否为空，大于1不为空
                    if counts > 0:
                        for i in range(1, counts):
                            tds = odds_tr[i].select('td')
                            if len(tds) < 6:
                                print("zq europe mobile detail row missing cells: scheduleId={0}, companyId={1}, index={2}".format(
                                    self.scheduleId, self.companyId, i))
                                continue
                            homeWin = tds[0].get_text().strip()
                            standOff = tds[1].get_text().strip()
                            awayWin = tds[2].get_text().strip()
                            spans = tds[4].select('span')
                            kelly_Home = spans[0].get_text().strip()
                            kelly_Off = spans[1].get_text().strip()
                            kelly_away = spans[2].get_text().strip()
                            modifyTime_tr = tds[5].get_text().strip().replace('\n', ' ')
                            modifyTime = getModifyTime(self.matchTime, modifyTime_tr, '即')

                            detail = [homeWin, standOff, awayWin,
                                      kelly_Home, kelly_Off, kelly_away, modifyTime,
                                      self.oddsId, self.companyId,  self.matchId, self.scheduleId]
                            # html标签提取数据正常，将公司开盘信息插入赔率列表
                            details['pre'].append(detail)
                    details['pre'].reverse()
                    details['state'] = 1
            except Exception as e:
                # excepstr = traceback.format_exc()
                # logLine(lqconfig_qt.exception, excepstr)
                # 本地记录失败记录
                print("zq europe mobile detail parse failed: scheduleId={0}, companyId={1}, error={2}".format(
                    self.scheduleId, self.companyId, e))
                if details['pre']:
                    details['state'] = 1
        return details


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


if __name__ == '__main__':
    str_p = '2019-05-12 22:00'
    matchTime2 = datetime.strptime(str_p, '%Y-%m-%d %H:%M')
    crawler = EuropeDetailCrawler(199152, 281, 1552518, 89991, -1, matchTime2, 0)
    data = crawler.qt_mobile_get_detail()
    print(data)
