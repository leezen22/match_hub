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
        return [
            [item["league_id"], item["league_name"], item["kind_type"]]
            for item in self.get_league_metadata_web()
        ]

    def get_league_metadata_web(self):
        headers = {"Host": self.qt_web_host,'Referer': self.qt_web_referer}
        left_data = self._get_left_data_by_league_id(headers)
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
                    country_id = str(country[0]) if len(country) > 0 else ""
                    country_name = str(country[1]) if len(country) > 1 else ""
                    country_logo = str(country[2]) if len(country) > 2 else ""
                    country_order = int(country[3]) if len(country) > 3 and str(country[3]).isdigit() else None
                    items = country[4]
                    for item in items:
                        arr = item.split(',')
                        # 提取联赛基本信息
                        leagueId = arr[0]
                        leagueName = arr[1]
                        leagueKind = arr[2]
                        leagueList.append({
                            "league_id": int(leagueId),
                            "league_name": leagueName,
                            "kind_type": int(leagueKind),
                            "seasons": [str(value) for value in arr[3:] if str(value) != ""],
                            "country_id": country_id,
                            "country_name": country_name,
                            "country_logo": country_logo,
                            "country_order": country_order,
                            "source": self.qt_web_url,
                            **left_data.get(int(leagueId), {}),
                        })
            except Exception as e:
                print(e)
        return leagueList

    def _get_left_data_by_league_id(self, headers):
        webResponse = WebUtil.requests_get(
            scrawler_config.qt_lq_left_data_js,
            headers=headers,
            sourceName="lq left league data",
        )
        content = webResponse[1]
        metadata = {}
        if webResponse[0] != 1 or content == '':
            return metadata
        try:
            parse_result = js2pyUtil.js2c(
                content,
                source=scrawler_config.qt_lq_left_data_js,
                required_names=("arrArea",),
            )
            if parse_result[0] != 1:
                return metadata
            for area in parse_result[1].arrArea:
                for country in area:
                    country_name_zh_hans = str(country[0]) if len(country) > 0 else ""
                    country_name_zh_hant = str(country[1]) if len(country) > 1 else ""
                    country_name_en = str(country[2]) if len(country) > 2 else ""
                    country_group = int(country[3]) if len(country) > 3 and str(country[3]).lstrip("-").isdigit() else None
                    leagues = country[4] if len(country) > 4 else []
                    for league in leagues:
                        if len(league) < 5:
                            continue
                        league_id = int(league[0])
                        metadata[league_id] = {
                            "name_zh_hans": str(league[1]),
                            "name_zh_hant": str(league[2]),
                            "name_en": str(league[3]),
                            "left_data_type": int(league[4]) if str(league[4]).lstrip("-").isdigit() else None,
                            "left_country_name_zh_hans": country_name_zh_hans,
                            "left_country_name_zh_hant": country_name_zh_hant,
                            "left_country_name_en": country_name_en,
                            "left_country_group": country_group,
                            "left_data_source": scrawler_config.qt_lq_left_data_js,
                        }
        except Exception as e:
            print(e)
        return metadata


# if __name__ == '__main__':
#     crawler = LeagueCrawler()
#     leagues = crawler.get_leagues_web()
#     print(leagues)
