from datetime import datetime
from bs4 import BeautifulSoup
from config import scrawler_config
from dao.lq_match_dao import LqMatchDao
from utils.fileUtil import logLine
from utils.webUtil import WebUtil


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


class TotalDetailCrawler(object):
    def __init__(self, matchId, companyId, scheduleId=None, oddsId=None, matchState=None,
                 matchTime=None, finished_pre=None, finished_gun=None):
        self.companyId = companyId
        self.oddsId = oddsId
        self.matchId = matchId
        self.scheduleId = scheduleId
        self.matchState = matchState
        self.matchTime = matchTime
        self.finished_pre = finished_pre
        self.finished_gun = finished_gun

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_mobile_url(self):
        return "{0}/{1}/{2}.htm".format(scrawler_config.qt_lq_mobile_totalDetail_url,
                                        self.companyId, self.scheduleId)

    @property
    def qt_mobile_keys(self):
        keys = [
            'matchId', 'scheduleId', 'companyId', 'oddsId',
            'highOdds', 'goal', 'lowOdds',
            'isBet', 'oddsType', 'kind', 'modifyTime'
        ]
        return keys

    def qt_mobile_pre_detail(self):
        headers = {"Host": self.qt_mobile_host}
        details = {'state': 0, 'companyId': self.companyId, 'oddsId': self.oddsId,
                   'matchId': self.matchId, 'scheduleId': self.scheduleId,
                   'matchState': self.matchState,
                   'finished_pre': self.finished_pre, 'finished_gun': self.finished_gun,
                   'keys_pre': self.qt_mobile_keys, "pre": []}
        if self.matchState is None:
            result = LqMatchDao.selectData(['matchId', 'matchState'],
                                           {'matchId': self.matchId}, isDis=True, isDict=True)
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
                table = soup.find(id='hTable')
                if table is not None:
                    # 赔率table tr 标签
                    odds_tr = table.select('tr')
                    counts = len(odds_tr)
                    # 判断让分指数公司列表是否为空，大于1不为空
                    if counts > 0:
                        oddsTypeDict = {'即': 1, '滚': 2, '早': 0}
                        for i in range(0, counts):
                            tds = odds_tr[i].select('td')
                            # spans = odds_tr[i].select('span')
                            oddsType_str = tds[0].get_text().strip()
                            oddsType = oddsTypeDict[oddsType_str]
                            highOdds = tds[1].get_text().strip()
                            goal = tds[2].get_text().strip()
                            lowOdds = tds[3].get_text().strip()
                            modifyTime_tr = tds[4].get_text().strip()
                            modifyTime = getModifyTime(self.matchTime, modifyTime_tr, oddsType_str)

                            detail = [self.matchId, self.scheduleId, self.companyId, self.oddsId,
                                      highOdds, goal, lowOdds, 1, oddsType, 6, modifyTime
                                      ]
                            for j in range(0, len(detail)):
                                if detail[j] == '':
                                    detail[j] = None
                                # html标签提取数据正常，将公司开盘信息插入赔率列表
                            if oddsType == 0 or oddsType == 1:
                                details['pre'].append(detail)
                else:
                    return details
            except Exception as e:
                # 本地记录失败记录
                print(e)
                # 获取页面成功
            else:
                details['pre'].reverse()
                details['state'] = 1

        # 返回亚指开盘公司初盘和终盘盘口
        return details


if __name__ == '__main__':
    str_p = '2020-02-08 03:05'
    matchTime2 = datetime.strptime(str_p, '%Y-%m-%d %H:%M')
    detailCrawler = TotalDetailCrawler(9, 196002, 362944, 646672, -1, matchTime2, 0)
    data = detailCrawler.qt_mobile_pre_detail()
    print(data)
