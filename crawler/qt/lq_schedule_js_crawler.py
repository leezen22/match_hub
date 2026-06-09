import os
import traceback
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from config import common_config, scrawler_config
from dao.lq_schedule_craw_dao import ScheduleCrawDao
from dao.lq_season_craw_dao import SeasonCrawDao
from utils import js2pyUtil
from utils.fileUtil import fileWrite, logLine
from utils.webUtil import WebUtil


class ScheduleJSCrawler(object):
    def __init__(self, leagueId, leagueType, matchSeason=None):
        self.leagueId = leagueId
        self.leagueType = leagueType
        self.matchSeason = matchSeason

    @property
    def qt_web_header(self):
        header = {'Host': scrawler_config.qt_lq_web_host, 'Referer': scrawler_config.qt_lq_web_home}
        return header

    def qt_load_scheJS(self):
        state = 0
        if self.leagueType == 1:
            loadLeagueJS(self.leagueId, self.matchSeason, self.qt_web_header)
        else:
            loadCupJS(self.leagueId, self.matchSeason, self.qt_web_header)
        return state

    def getScheJSPend(self):
        resultData = {'state': 0, 'data': []}
        pendList = []
        # 联赛赛季信息JS文件
        seaFilename = "sea{0}.js".format(self.leagueId)
        seaJSUrl = "{0}/{1}".format(scrawler_config.qt_lq_web_seasonJS_bdir, seaFilename)
        seaJSPath = "{0}\\{1}".format(scrawler_config.lq_seasonJS_local_dir, seaFilename)
        webResponse = WebUtil.requests_get(seaJSUrl, headers=self.qt_web_header)
        webContent = webResponse[1]
        if webResponse[0] == 1 and webContent != '':
            try:
                fileWrite(seaJSPath, "w", webContent)
                parseResult = js2pyUtil.js2c(
                    webContent,
                    source=seaJSUrl,
                    required_names=("arrSeason",),
                )
                if parseResult[0] != 1:
                    logLine(common_config.js2pyweb_e, ["SEASON_JS_PARSE_SKIPPED", seaJSUrl])
                    return resultData
                webContext = parseResult[1]
                arrSeason_web = webContext.arrSeason
                season = arrSeason_web[0][0]
                scraw = {}
                condition = {'leagueId': self.leagueId, 'matchSeason': season}
                keys = ['Id', 'leagueId', 'matchSeason', 'seasonPath', 'season_f']
                seasonCraw_result = SeasonCrawDao.select_rows(keys, condition)
                if not (len(seasonCraw_result) > 0 and seasonCraw_result[0][4] == 2):
                    if len(seasonCraw_result) == 0:
                        scraw['leagueId'] = self.leagueId
                        scraw['matchSeason'] = season
                        scraw['seasonPath'] = seaJSPath
                        scraw['season_f'] = 1
                        SeasonCrawDao.insert(scraw)
                    jsData = getScheJS(self.leagueId, self.leagueType, season, self.qt_web_header)
                    if jsData[0] != 0:
                        scheJSList = jsData[1]
                        for scheJS in scheJSList:
                            filename = os.path.basename(scheJS[1])
                            scheKey = str(self.leagueId) + "#" + str(changeSeason(season)) + "#" + filename
                            condition = {'scheKey': scheKey}
                            keys = ['Id', 'scheKey', 'leagueId', 'matchSeason', 'fileName',
                                    'schePath', 'schePath', 'sche_f']
                            # 查询更新进度
                            scheCraw_result = ScheduleCrawDao.select_rows(keys, condition)
                            if len(scheCraw_result) == 0 or scheCraw_result[0][7] != 2:
                                pendList.append(scheJS)
                                if len(scheCraw_result) == 0:
                                    keys = ['scheKey', 'leagueId', 'matchSeason', 'fileName',
                                            'schePath', 'seaPath', 'sche_f']
                                    value = [scheKey, self.leagueId, season, filename, scheJS[1], seaJSPath, 1]
                                    # 同步赛程更新进度
                                    ScheduleCrawDao.insert(value, keys, isDict=False)
                        state = 1
                    else:
                        state = 0
                else:
                    state = 1
                resultData['state'] = state
                resultData['data'] = pendList
            except Exception as e:
                logLine(common_config.js2pyweb_e, ["SEASON_JS_PROCESS_FAILED", seaJSUrl, repr(e), traceback.format_exc()])
                print(e)
        return resultData

    def getScheJSList(self):
        result = getScheJS(self.leagueId, self.leagueType, self.matchSeason, self.qt_web_header)
        return result


def loadLeagueJS(leagueId, season, headers):
    state = 0
    # 本联赛赛季常规赛赛程地址
    url = "{0}?MatchSeason={1}&Sclassid={2}".format(scrawler_config.qt_lq_web_normal, season, leagueId)
    scheSrc = findScheJS(url, headers)
    season2 = changeSeason(season)
    if len(scheSrc) > 0:
        result = js2pyUtil.jsyWebjs(
            urljoin(scrawler_config.qt_lq_web_home, scheSrc),
            headers,
            required_names=("arrLeague", "ymList"),
        )
        scheContext = result[1]
        if result[0] != 0:
            try:
                haveMk = scheContext.arrLeague[11]
                ymList = scheContext.ymList
                # 下载常规赛赛程
                loadRegularJS(leagueId, season2, ymList, headers)
                if '3' in haveMk:
                    # 下载联赛季前赛赛程
                    loadPreJS(leagueId, season2, headers)
                if '2' in haveMk:
                    # 下载联赛季后赛赛程
                    loadPlayoffJS(leagueId, season2, headers)
                state = 1
            except Exception as e:
                logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_CONTEXT_ERROR", url, repr(e), traceback.format_exc()])
                print(e)
    else:
        logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_SRC_NOT_FOUND", url])
    return state


def getScheJS(leagueId, leagueType, season, headers):
    state = 0
    jsFileList = []
    # 联赛
    if leagueType == 1:
        # 本联赛赛季常规赛赛程默认地址
        defaultUrl = "{0}?SclassID={2}&MatchSeason={1}".format(scrawler_config.qt_lq_web_normal, season, leagueId)
        scheSrc = findScheJS(defaultUrl, headers)
        if len(scheSrc) == 0:
            logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_SRC_NOT_FOUND", defaultUrl])
            return [state, jsFileList]
        parseResult = js2pyUtil.jsyWebjs(
            urljoin(scrawler_config.qt_lq_web_home, scheSrc),
            headers,
            required_names=("arrLeague", "ymList"),
        )
        scheContext = parseResult[1]
        if parseResult[0] == 1 and scheContext != '':
            try:
                haveMk = scheContext.arrLeague[11]
                ymlist = scheContext.ymList
                # 获取常规赛赛程JS文件地址信息
                for ym in ymlist:
                    season = changeSeason(season)
                    jsUrl = "{0}/{1}/l{2}_1_{3}_{4}.js".format(scrawler_config.qt_lq_web_scheJS_dir,
                                                               season, leagueId, ym[0], ym[1])
                    jsPath = "{0}\\{1}\\l{2}_1_{3}_{4}.js".format(scrawler_config.lq_scheJS_local_dir,
                                                                season, leagueId, ym[0], ym[1])
                    jsFileList.append([jsUrl, jsPath])
                # 获取季前赛赛程JS文件地址信息
                if '3' in haveMk:
                    jsUrl = "{0}/{1}/l{2}_3.js".format(scrawler_config.qt_lq_web_scheJS_dir, season, leagueId)
                    jsPath = "{0}\\{1}\\l{2}_3.js".format(scrawler_config.lq_scheJS_local_dir, season, leagueId)
                    jsFileList.append([jsUrl, jsPath])
                # 获取季后赛赛程JS文件地址信息
                if '2' in haveMk:
                    jsUrl = "{0}/{1}/l{2}_2.js".format(scrawler_config.qt_lq_web_scheJS_dir, season, leagueId)
                    jsPath = "{0}\\{1}\\l{2}_2.js".format(scrawler_config.lq_scheJS_local_dir, season, leagueId)
                    jsFileList.append([jsUrl, jsPath])
                state = 1
            except Exception as e:
                logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_CONTEXT_ERROR", defaultUrl, repr(e), traceback.format_exc()])
                print(e)
    # 杯赛
    else:
        season2 = changeSeason(season)
        cupJSUrl = "{0}/{1}/c{2}.js".format(scrawler_config.qt_lq_web_scheJS_dir, season2, leagueId)
        jsPath = "{0}\\{1}\\c{2}.js".format(scrawler_config.lq_scheJS_local_dir, season2, leagueId)
        jsFileList.append([cupJSUrl, jsPath])
        state = 1
    return [state, jsFileList]


def loadCupJS(leagueId, season, headers):
    season2 = changeSeason(season)
    cupJSUrl = "{0}/{1}/c{2}.js".format(scrawler_config.qt_lq_web_scheJS_dir, season2, leagueId)
    jsDir = "{0}\\{1}\\".format(scrawler_config.lq_scheJS_local_dir, season2)
    state = WebUtil.loadfile(cupJSUrl, jsDir, headers)
    return state


def loadPreJS(leagueId, season, headers):
    jsUrl = "{0}/{1}/l{2}_3.js".format(scrawler_config.qt_lq_web_scheJS_dir, season, leagueId)
    jsDir = "{0}\\{1}\\".format(scrawler_config.lq_scheJS_local_dir, season)
    state = WebUtil.loadfile(jsUrl, jsDir, headers)
    return state


def loadRegularJS(leagueId, season, ymlist, headers):
    state = 0
    if len(ymlist) > 0:
        for ym in ymlist:
            jsUrl = "{0}/{1}/l{2}_1_{3}_{4}.js".format(scrawler_config.qt_lq_web_scheJS_dir,
                                                       season, leagueId, ym[0], ym[1])
            jsDir = "{0}\\{1}\\".format(scrawler_config.lq_scheJS_local_dir, season)
            state = WebUtil.loadfile(jsUrl, jsDir, headers)
    return state


def loadPlayoffJS(leagueId, season, headers):
    jsUrl = "{0}/{1}/l{2}_2.js".format(scrawler_config.qt_lq_web_scheJS_dir, season, leagueId)
    jsDir = "{0}\\{1}\\".format(scrawler_config.lq_scheJS_local_dir, season)
    state = WebUtil.loadfile(jsUrl, jsDir, headers)
    return state


# 通过常规赛默认页面Url查找常规赛默认数据jsUrl
def findScheJS(pageUrl, headers):
    targetSrc = ''
    # print("findschjs:" + pageUrl)
    try:
        webResponse = WebUtil.requests_get(pageUrl, headers=headers, sourceName='normal default page')
        state = webResponse[0]
        webContent = webResponse[1]
        if state != 1:
            logLine(common_config.js2pyweb_e, ["SCHEDULE_PAGE_HTTP_FAILED", pageUrl, state])
        elif webContent == '':
            logLine(common_config.js2pyweb_e, ["SCHEDULE_PAGE_EMPTY", pageUrl])
        elif state == 1:
            soup = BeautifulSoup(webContent, 'html.parser')
            for scrip in soup.find_all('script'):
                url = scrip.get('src')
                if url:
                    partArr = url.partition('jsData/matchResult')
                    if url != partArr[0]:
                        targetSrc = url
            if targetSrc == '':
                logLine(common_config.js2pyweb_e, ["SCHEDULE_JS_SRC_NOT_FOUND", pageUrl, webContent[:300]])
    except Exception as e:
        logLine(common_config.js2pyweb_e, ["SCHEDULE_PAGE_PARSE_FAILED", pageUrl, repr(e), traceback.format_exc()])
        print(e)
        e_str = traceback.format_exc()
        print(e_str)
    return targetSrc


def changeSeason(season):
    if len(season) == 9:
        years = season.split('-')
        newSeason = years[0][2:] + '-' + years[1][2:]
    elif len(season) == 4:
        newSeason = season[2:]
    else:
        newSeason = season
    return newSeason


if __name__ == '__main__':
    crawler = ScheduleJSCrawler(5, 1)
    data2 = crawler.getScheJSPend()
    print(data2)
