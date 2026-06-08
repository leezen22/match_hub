import os
import traceback
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from config import common_config, lqconfig_qt
from crawler.qt.lq_league_crawler import LeagueCrawler
from lq.dao import MatchDao
from lq.extract import MatchJS
from lq.formate import model
from utils import sql_util, js2pyUtil, fileUtil
from utils.fileUtil import fileWrite
from utils.webUtil import WebUtil


class LQleague(object):
    @staticmethod
    def getSchejsPending(sclass):
        pendinglist = []
        # 联赛赛季信息JS文件
        seafilename = 'sea' + str(sclass[0]) + '.js'
        seajsUrl = lqconfig_qt.seajsWebdir + seafilename
        seajsPath = lqconfig_qt.seajslocaldir + seafilename
        webresponse = WebUtil.requests_get(seajsUrl, headers=lqconfig_qt.headers,
                                           sourceName='update_lanqiu.getSchejsPending ')
        webcontent = webresponse[1]
        if webresponse[0] == 1 and webcontent != '':
            try:
                fileWrite(seajsPath, "w", webcontent)
                parse_result = js2pyUtil.js2c(webcontent, source=seajsUrl, required_names=("arrSeason",))
                if parse_result[0] != 1:
                    fileUtil.logLine(common_config.js2pyweb_e, ["LQ_SEASON_JS_PARSE_SKIPPED", seajsUrl])
                    return pendinglist
                webcontext = parse_result[1]
                arrSeason_web = webcontext.arrSeason
                for seasondata in arrSeason_web:
                    leagueId = sclass[0]
                    season = seasondata[0]
                    season_state = seasondata[1] if len(seasondata) > 1 else 1
                    if season_state == 2 and not lqconfig_qt.enable_finished_season_backfill:
                        continue
                    stask = {}
                    condition = {'leagueId': leagueId, 'matchSeason': season}
                    keys = ['ID', 'leagueId', 'matchSeason', 'seasonPath', 'state']
                    result = sql_util.select_table_rows('lq_season_crawler', keys, condition)
                    should_skip_finished_season = len(result) > 0 and result[0][4] == 2
                    if should_skip_finished_season:
                        pass
                    else:
                        if len(result) == 0:
                            stask['leagueId'] = leagueId
                            stask['matchSeason'] = season
                            stask['seasonPath'] = seajsPath
                            stask['state'] = 1
                            sql_util.insertData('lq_season_crawler', stask)
                        scheJSList = LQleague.getScheJS(sclass[0], season, sclass[2])
                        for schejs in scheJSList:
                            filename = os.path.basename(schejs[1])
                            scheKey = str(sclass[0]) + "#" + str(model.changeSeason(season)) + "#" + filename
                            condition = {'scheKey': scheKey}
                            keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath',
                                    'state']
                            result = sql_util.select_table_rows('lq_schedule_crawler', keys, condition)
                            is_db_finished = len(result) > 0 and result[0][7] == 2
                            if not is_db_finished:
                                pendinglist.append(schejs)
                                if len(result) == 0:
                                    scheinfo = {'scheKey': scheKey, 'leagueId': leagueId,
                                                'matchSeason': model.changeSeason(season), 'fileName': filename,
                                                'schePath': schejs[1], 'seaPath': seajsPath, 'state': 1}
                                    sql_util.insertData('lq_schedule_crawler', scheinfo)
            except Exception as e:
                fileUtil.logLine(common_config.js2pyweb_e, ["LQ_SCHEJS_PENDING_FAILED", seajsUrl, repr(e), traceback.format_exc()])
                print(e)
        return pendinglist

    @staticmethod
    def loadSchejs(seasidlist):
        for seasid in seasidlist:
            if seasid[2] == '1':
                # 下载联赛赛程JS文件
                LQleague.loadLeagueJS(seasid[0], seasid[1])
            elif seasid[2] == '2':
                # 下载杯赛(cup)赛程JS文件
                LQleague.loadCupJS(seasid[0], seasid[1])
            else:
                pass
        print("篮球赛程下载完毕")

    # 下载篮球 【联赛】赛程JS文件
    @staticmethod
    def loadLeagueJS(leagueId, season):
        # 本联赛赛季常规赛赛程地址
        url = lqconfig_qt.lanqurl + '/cn/Normal.aspx?matchSeason=' + str(season) + '&SclassID=' + str(leagueId)
        scheSrc = LQleague.findScheJS(url, lqconfig_qt.headers)
        season2 = model.changeSeason(season)
        if len(scheSrc) > 0:
            parse_result = js2pyUtil.jsyWebjs(
                urljoin(lqconfig_qt.lanqurl, scheSrc),
                lqconfig_qt.headers,
                required_names=("arrLeague", "ymList"),
            )
            scheContext = parse_result[1]
            if parse_result[0] == 1 and scheContext != '':
                try:
                    haveMk = scheContext.arrLeague[11]
                    ymlist = scheContext.ymList
                    # 下载常规赛赛程
                    LQleague.loadRegularJS(leagueId, season2, ymlist)
                    if '3' in haveMk:
                        # 下载联赛季前赛赛程
                        LQleague.loadPreJS(leagueId, season2)
                    if '2' in haveMk:
                        # 下载联赛季后赛赛程
                        LQleague.loadPlayoffJS(leagueId, season2)
                except Exception as e:
                    fileUtil.logLine(common_config.js2pyweb_e, ["LQ_LOAD_LEAGUE_JS_CONTEXT_ERROR", url, repr(e), traceback.format_exc()])
                    print(e)
        else:
            fileUtil.logLine(common_config.js2pyweb_e, ["LQ_SCHEDULE_JS_SRC_NOT_FOUND", url])

    # 下载杯赛JS文件到本地
    @staticmethod
    def loadCupJS(leagueId, season):
        season2 = model.changeSeason(season)
        cupJSurl = lqconfig_qt.scheWebdir + season2 + '/' + 'c' + leagueId + '.js'
        jsDir = lqconfig_qt.schelocaldir + season2 + '/'
        WebUtil.loadfile(cupJSurl, jsDir, lqconfig_qt.headers)

    # --------------------下载联赛文件到本地---------------------------------
    # 下载 【联赛季前赛】文件列表到本地
    @staticmethod
    def loadPreJS(leagueId, season):
        jsUrl = lqconfig_qt.scheWebdir + season + '/l' + str(leagueId) + '_' + '3' + '.js'
        jsDir = lqconfig_qt.schelocaldir + season + '/'
        WebUtil.loadfile(jsUrl, jsDir, lqconfig_qt.headers)

    # 下载 【联赛常规赛】赛程JS文件到本地
    @staticmethod
    def loadRegularJS(leagueId, season, ymlist):
        if len(ymlist) > 0:
            for ym in ymlist:
                jsUrl = lqconfig_qt.scheWebdir + season + '/l' + str(leagueId) + '_' + '1' + '_' + str(
                    ym[0]) + '_' + str(ym[1]) + '.js'
                jsDir = lqconfig_qt.schelocaldir + season + '/'
                WebUtil.loadfile(jsUrl, jsDir, lqconfig_qt.headers)

    # 下载 【联赛季后赛】赛程
    @staticmethod
    def loadPlayoffJS(leagueId, season):
        jsUrl = lqconfig_qt.scheWebdir + season + '/l' + str(leagueId) + '_' + '2' + '.js'
        jsDir = lqconfig_qt.schelocaldir + season + '/'
        WebUtil.loadfile(jsUrl, jsDir, lqconfig_qt.headers)

    # --------------------下载联赛文件到本地---------------------------------

    # 根据联赛ID和赛季获取网站赛程地址列表
    @staticmethod
    def getScheJS(leagueId, season, type):
        jsfilelist = []
        # 联赛
        if type == 1:
            # 本联赛赛季常规赛赛程默认地址
            defaulturl1 = lqconfig_qt.lanqurl + '/cn/Normal.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            defaulturl3 = lqconfig_qt.lanqurl + '/cn/Preseason.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            defaulturl2 = lqconfig_qt.lanqurl + '/cn/Playoffs.aspx.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            urls = [defaulturl1, defaulturl2, defaulturl3]
            for url in urls:
                scheSrc = LQleague.findScheJS(url, lqconfig_qt.headers)
                if scheSrc != '':
                    break
            # print([leagueId, season, type, defaulturl, scheSrc])
            if scheSrc == '':
                return jsfilelist
            parse_result = js2pyUtil.jsyWebjs(
                urljoin(lqconfig_qt.lanqurl, scheSrc),
                lqconfig_qt.headers,
                required_names=("arrLeague", "ymList"),
            )
            scheContext = parse_result[1]
            if parse_result[0] == 1 and scheContext != '':
                try:
                    haveMk = scheContext.arrLeague[11]
                    ymlist = scheContext.ymList
                    # 获取常规赛赛程JS文件地址信息
                    for ym in ymlist:
                        season = model.changeSeason(season)
                        filename = 'l' + str(leagueId) + '_' + '1' + '_' + str(ym[0]) + '_' + str(ym[1]) + '.js'
                        jsUrl = lqconfig_qt.scheWebdir + season + '/' + filename
                        jsPath = lqconfig_qt.schelocaldir + season + '/' + filename
                        jsfilelist.append([jsUrl, jsPath])
                    # 获取季前赛赛程JS文件地址信息
                    if '3' in haveMk:
                        filename = 'l' + str(leagueId) + '_' + '3' + '.js'
                        jsUrl = lqconfig_qt.scheWebdir + season + '/' + filename
                        jsPath = lqconfig_qt.schelocaldir + season + '/' + filename
                        jsfilelist.append([jsUrl, jsPath])
                    # 获取季后赛赛程JS文件地址信息
                    if '2' in haveMk:
                        filename = 'l' + str(leagueId) + '_' + '2' + '.js'
                        jsUrl = lqconfig_qt.scheWebdir + season + '/' + filename
                        jsPath = lqconfig_qt.schelocaldir + season + '/' + filename
                        jsfilelist.append([jsUrl, jsPath])
                except Exception as e:
                    fileUtil.logLine(common_config.js2pyweb_e, ["LQ_GET_SCHEJS_CONTEXT_ERROR", url, repr(e), traceback.format_exc()])
                    print(e)
        # 杯赛
        elif type == 2:
            filename = 'c' + str(leagueId) + '.js'
            season = model.changeSeason(season)
            cupJSurl = lqconfig_qt.scheWebdir + season + '/' + filename
            jsPath = lqconfig_qt.schelocaldir + season + '/' + filename
            jsfilelist.append([cupJSurl, jsPath])
        else:
            pass
        return jsfilelist

    # 根据联赛ID、赛季、联赛类型获取 赛程JS本地文件列表
    @staticmethod
    def getLocalfiles(sclassID, kindtype):
        fileList = []
        context = js2pyUtil.jsLocjs(lqconfig_qt.seajslocaldir + 'sea' + str(sclassID) + '.js')
        if not context or not hasattr(context, 'arrSeason'):
            return fileList
        seasonlist = context.arrSeason
        for season in seasonlist:
            season2 = model.changeSeason(season[0])
            schedir = lqconfig_qt.schelocaldir + season2 + '/'
            if not os.path.isdir(schedir):
                continue
            filepaths = fileUtil.dirFiles(schedir, [])
            for filepath in filepaths:
                filename = os.path.basename(filepath)
                if kindtype == 1:
                    sclasskey = 'l' + str(sclassID)
                else:
                    sclasskey = 'c' + str(sclassID)
                if filename.split('.js')[0].split('_')[0] == sclasskey:
                    fileList.append(filepath)
                else:
                    pass
        return fileList

    # 根据联赛ID和类型获取待处理本地赛程JS文件列表
    @staticmethod
    def getPendingSchejs(sclassID, kindtype):
        fileList = []
        context = js2pyUtil.jsLocjs(lqconfig_qt.seajslocaldir + 'sea' + str(sclassID) + '.js')
        if not context or not hasattr(context, 'arrSeason'):
            return fileList
        seasonlist = context.arrSeason
        for season in seasonlist:
            season2 = model.changeSeason(season[0])
            schedir = os.path.join(lqconfig_qt.schedule_js_work_dir, season2)
            if not os.path.isdir(schedir):
                schedir = lqconfig_qt.schejslocaldir_p + season2 + '/'
            if not os.path.isdir(schedir):
                continue
            # print(schedir)
            filepaths = fileUtil.dirFiles(schedir, [])
            # print(filepaths)
            for filepath in filepaths:
                filename = os.path.basename(filepath)
                if kindtype == 1:
                    sclasskey = 'l' + str(sclassID)
                else:
                    sclasskey = 'c' + str(sclassID)
                if filename.split('.js')[0].split('_')[0] == sclasskey:
                    fileList.append(filepath)
        return fileList

    @staticmethod
    # 获取【联赛季前赛】本地文件列表
    def getPreJS(sclassID, season):
        preList = []
        jsPath = lqconfig_qt.schelocaldir + season + '/l' + str(sclassID) + '_' + '3' + '.js'
        preList.append(jsPath)
        return preList

    @staticmethod
    # 获取【联赛常规赛】本地文件列表
    def getRegularJS(sclassID, season, ymlist):
        schejs = []
        if len(ymlist) > 0:
            for ym in ymlist:
                jsPath = lqconfig_qt.schelocaldir + season + '/l' + str(sclassID) + '_' + '1' + '_' + str(
                    ym[0]) + '_' + str(ym[1]) + '.js'
                schejs.append(jsPath)
        else:
            pass
        return schejs

    @staticmethod
    # 获取【联赛季后赛】本地文件列表
    def getPlayOffJS(sclassID, season):
        schejs = []
        jsPath = lqconfig_qt.schelocaldir + season + '/l' + str(sclassID) + '_' + '2' + '.js'
        schejs.append(jsPath)
        return schejs

    @staticmethod
    def getCupJS(sclassID, season):
        schejs = []
        jsPath = lqconfig_qt.schelocaldir + season + '/c' + str(sclassID) + '.js'
        schejs.append(jsPath)
        return schejs

    # 通过常规赛默认页面Url查找常规赛默认数据jsUrl
    @staticmethod
    def findScheJS(pageurl, headers):
        targetSrc = ''
        try:
            webresponse = WebUtil.requests_get(pageurl, headers=headers, sourceName='normal default page')
            state = webresponse[0]
            webcontent = webresponse[1]
            if state == 1 and webcontent != '':
                soup = BeautifulSoup(webcontent, 'html.parser')
                for scrip in soup.find_all('script'):
                    url = scrip.get('src')
                    if url:
                        partArr = url.partition('jsData/matchResult')
                        if url == partArr[0]:
                            pass
                        else:
                            targetSrc = url
                    else:
                        pass

        except Exception as e:
            excepstr = traceback.format_exc()
            js2pyUtil.logLine(lqconfig_qt.exception, excepstr)
            print(e)
        return targetSrc

    # 根据联赛ID和赛季，获取联赛常规赛年月列表
    def getleagueym(sclassID, season):
        ymlist = []
        url = lqconfig_qt.lanqurl + '/cn/Normal.aspx?matchSeason=' + season + '&SclassID=' + str(sclassID)
        scheSrc = LQleague.findScheJS(url, lqconfig_qt.headers)
        # season2= CommonUtil.changeSeason(season)
        if len(scheSrc) > 0:
            parse_result = js2pyUtil.jsyWebjs(
                urljoin(lqconfig_qt.lanqurl, scheSrc),
                lqconfig_qt.headers,
                required_names=("ymList",),
            )
            scheContext = parse_result[1]
            if parse_result[0] == 1 and scheContext != '':
                try:
                    ymlist = scheContext.ymList
                except Exception as e:
                    print(e)
        return ymlist

    # 检查联赛本地JS赛程信息是否完整
    @staticmethod
    def getMissingMatch(sclassid, type):
        missmatchs = []
        filelist = LQleague.getLocalfiles(sclassid, type)
        for file in filelist:
            matchlist = MatchJS.getMatchFromFile(file)
            for match in matchlist:
                # print(match['ID'])
                result = MatchDao.selectMatch({'scheduleID': match['scheduleID']})
                if len(result) == 0:
                    missmatchs.append({'scheduleID': match['scheduleID'], 'SclassID': sclassid})
        return missmatchs

    @staticmethod
    def getLeaguesOfWebsite():
        crawler = LeagueCrawler()
        leagues = crawler.get_leagues_web()
        return leagues
