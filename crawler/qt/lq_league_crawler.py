from config import scrawler_config
from utils import js2pyUtil
from utils.webUtil import WebUtil


class LeagueCrawler(object):

    def __init__(self):
        pass

    @property
    def qt_web_host(self):
        return scrawler_config.qt_lq_web_host

    @property
    def qt_web_url(self):
        return scrawler_config.qt_lq_league_js

    @property
    def qt_web_referer(self):
        return scrawler_config.qt_lq_league_referer

    def get_leagues_web(self):
        headers = {"Host": self.qt_web_host,'Referer': self.qt_web_referer}
        webResponse = WebUtil.requests_get(self.qt_web_url, headers=headers, sourceName="lq league list")
        content = webResponse[1]
        leagueList = []
        if webResponse[0] == 1 and content != '':
            try:
                parse_result = js2pyUtil.js2c(content, source=self.qt_web_url, required_names=("arr",))
                if parse_result[0] != 1:
                    return leagueList
                context = parse_result[1]
                countrys = context.arr
                for country in countrys:
                    items = country[4]
                    for item in items:
                        arr = item.split(',')
                        # 提取联赛基本信息
                        leagueId = arr[0]
                        leagueName = arr[1]
                        leagueKind = arr[2]
                        leagueList.append([int(leagueId), leagueName, int(leagueKind)])
            except Exception as e:
                print(e)
        return leagueList


# if __name__ == '__main__':
#     crawler = LeagueCrawler()
#     leagues = crawler.get_leagues_web()
#     print(leagues)
