import os
import traceback
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from config import common_config, lqconfig_qt
from crawler.qt.lq_league_crawler import LeagueCrawler
from lq.dao import MatchDao
from lq.extract import MatchJS
from lq.formate import model
from utils import sql_util, js2pyUtil, fileUtil
from utils.webUtil import WebUtil


SOURCE_NAMESPACE = "titan_basketball"

LEAGUE_METADATA_COLUMNS = {
    "logo": "ADD COLUMN `logo` varchar(255) CHARACTER SET utf8 NULL",
    "logo_url": "ADD COLUMN `logo_url` varchar(255) CHARACTER SET utf8 NULL",
    "source_namespace": "ADD COLUMN `source_namespace` varchar(64) CHARACTER SET utf8 NULL",
    "source_entity_id": "ADD COLUMN `source_entity_id` varchar(64) CHARACTER SET utf8 NULL",
    "captured_at": "ADD COLUMN `captured_at` datetime NULL",
    "recorded_at": "ADD COLUMN `recorded_at` datetime NULL",
    "updated_at": "ADD COLUMN `updated_at` datetime NULL",
    "source_state_valid_at": "ADD COLUMN `source_state_valid_at` datetime NULL",
    "source_url_or_operation": "ADD COLUMN `source_url_or_operation` varchar(255) CHARACTER SET utf8 NULL",
    "collection_status": "ADD COLUMN `collection_status` varchar(32) CHARACTER SET utf8 NULL",
    "has_data": "ADD COLUMN `has_data` tinyint(4) NULL",
}


class LQleague(object):
    @staticmethod
    def updateTeamInfo(league_id, version=None):
        from lq.service.team import update_team_info

        return update_team_info(league_id, version=version)

    @staticmethod
    def updateLeagueDetailInfo(league_id, version=None):
        from lq.service.team import update_league_info_from_team_info

        return update_league_info_from_team_info(league_id, version=version)

    @staticmethod
    def updateLeagueInfo(league_id=None, version=None):
        ensure_basic_information_schema()
        leagues = LQleague.getLeaguesOfWebsite()
        captured_at = _now()
        recorded_at = _now()
        inserted = 0
        updated = 0
        for league in leagues:
            row = LQleague._league_row(league, captured_at, recorded_at)
            result = sql_util.select_dicts(
                "SELECT leagueID,name_en FROM lq_league WHERE leagueID={0}".format(int(row["leagueID"]))
            )
            if len(result) > 0:
                if _should_preserve_existing_name_en(result[0].get("name_en"), row.get("name_en"), row.get("name_sh")):
                    row.pop("name_en", None)
                sql_util.upData("lq_league", _update_payload(row), {"leagueID": row["leagueID"]})
                updated += 1
            else:
                sql_util.insertData("lq_league", row)
                inserted += 1
        print("basketball league info update finished: leagues={0}, inserted={1}, updated={2}".format(
            len(leagues),
            inserted,
            updated,
        ))
        result = {"leagues": len(leagues), "inserted": inserted, "updated": updated}
        if league_id is not None:
            result["league_detail"] = LQleague.updateLeagueDetailInfo(league_id, version=version)
        return result

    @staticmethod
    def _league_row(league, captured_at, recorded_at):
        league_id = int(league["league_id"])
        return {
            "leagueID": league_id,
            "name_sh": _empty_to_none(league.get("league_name")),
            "name_cn": _empty_to_none(league.get("name_zh_hans") or league.get("league_name")),
            "name_tw": _empty_to_none(league.get("name_zh_hant")),
            "name_en": _empty_to_none(league.get("name_en")),
            "name_twsh": _empty_to_none(league.get("name_zh_hant")),
            "name_ensh": _empty_to_none(league.get("name_en")),
            "country": _empty_to_none(league.get("left_country_name_zh_hans") or league.get("country_name")),
            "countryID": _parse_country_id(league.get("country_id")),
            "leagueKind": int(league["kind_type"]),
            "source_namespace": SOURCE_NAMESPACE,
            "source_entity_id": str(league_id),
            "captured_at": captured_at,
            "recorded_at": recorded_at,
            "updated_at": recorded_at,
            "source_state_valid_at": None,
            "source_url_or_operation": _empty_to_none(league.get("source")),
            "collection_status": "success",
            "has_data": 1,
        }

    @staticmethod
    def getSchejsPending(sclass):
        pendinglist = []
        leagueId, kind_type = LQleague._schedule_league_values(sclass)
        # 联赛赛季信息JS文件
        seafilename = 'sea' + str(leagueId) + '.js'
        seajsUrl = lqconfig_qt.seajsWebdir + seafilename
        webresponse = WebUtil.requests_get(seajsUrl, headers=lqconfig_qt.headers,
                                           sourceName='update_lanqiu.getSchejsPending ')
        webcontent = webresponse[1]
        if webresponse[0] == 1 and webcontent != '':
            try:
                parse_result = js2pyUtil.js2c(webcontent, source=seajsUrl, required_names=("arrSeason",))
                if parse_result[0] != 1:
                    fileUtil.logLine(common_config.js2pyweb_e, ["LQ_SEASON_JS_PARSE_SKIPPED", seajsUrl])
                    return pendinglist
                webcontext = parse_result[1]
                arrSeason_web = webcontext.arrSeason
                for seasondata in arrSeason_web:
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
                            stask['seasonPath'] = seafilename
                            stask['state'] = 1
                            sql_util.insertData('lq_season_crawler', stask)
                        scheJSList = LQleague.getScheJS(leagueId, season, kind_type)
                        for schejs in scheJSList:
                            filename = os.path.basename(schejs[1])
                            scheKey = str(leagueId) + "#" + str(model.changeSeason(season)) + "#" + filename
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
                                                'schePath': schejs[1], 'seaPath': seajsUrl, 'state': 1}
                                    sql_util.insertData('lq_schedule_crawler', scheinfo)
            except Exception as e:
                fileUtil.logLine(common_config.js2pyweb_e, ["LQ_SCHEJS_PENDING_FAILED", seajsUrl, repr(e), traceback.format_exc()])
                print(e)
        return pendinglist

    @staticmethod
    def _schedule_league_values(sclass):
        if isinstance(sclass, dict):
            return int(sclass["league_id"]), int(sclass["kind_type"])
        return int(sclass[0]), int(sclass[2])

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
                    arr_league = _get_js_value(scheContext, 'arrLeague', [])
                    haveMk = arr_league[11] if len(arr_league) > 11 else ''
                    ymlist = _get_js_value(scheContext, 'ymList', [])
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
            season_path = model.changeSeason(season)

            def append_schedule_src(sche_src):
                if not sche_src:
                    return
                filename = os.path.basename(sche_src.split('?')[0])
                if not filename.endswith('.js'):
                    return
                js_url = urljoin(lqconfig_qt.lanqurl, sche_src)
                js_path = lqconfig_qt.schelocaldir + season_path + '/' + filename
                item = [js_url, js_path]
                if item not in jsfilelist:
                    jsfilelist.append(item)

            # 本联赛赛季常规赛赛程默认地址
            defaulturl1 = lqconfig_qt.lanqurl + '/cn/Normal.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            defaulturl3 = lqconfig_qt.lanqurl + '/cn/Preseason.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            defaulturl2 = lqconfig_qt.lanqurl + '/cn/Playoffs.aspx?SclassID=' + str(leagueId) + '&MatchSeason=' + str(
                season)
            scheSrc = LQleague.findScheJS(defaulturl1, lqconfig_qt.headers)
            # print([leagueId, season, type, defaulturl, scheSrc])
            if scheSrc == '':
                append_schedule_src(LQleague.findScheJS(defaulturl3, lqconfig_qt.headers))
                append_schedule_src(LQleague.findScheJS(defaulturl2, lqconfig_qt.headers))
                return jsfilelist
            sche_url = urljoin(lqconfig_qt.lanqurl, scheSrc)
            parse_result = js2pyUtil.jsyWebjs(
                sche_url,
                lqconfig_qt.headers,
                required_names=("arrLeague", "arrData", "ymList"),
            )
            scheContext = parse_result[1]
            if parse_result[0] == 1 and scheContext != '':
                try:
                    arr_league = _get_js_value(scheContext, 'arrLeague', [])
                    haveMk = arr_league[11] if len(arr_league) > 11 else ''
                    ymlist = _get_js_value(scheContext, 'ymList', [])
                    # 获取常规赛赛程JS文件地址信息
                    if len(ymlist) == 0:
                        fileUtil.logLine(common_config.js2pyweb_e, ["LQ_GET_SCHEJS_YMLIST_MISSING", sche_url])
                        append_schedule_src(scheSrc)
                    else:
                        for ym in ymlist:
                            filename = 'l' + str(leagueId) + '_' + '1' + '_' + str(ym[0]) + '_' + str(ym[1]) + '.js'
                            jsUrl = lqconfig_qt.scheWebdir + season_path + '/' + filename
                            jsPath = lqconfig_qt.schelocaldir + season_path + '/' + filename
                            jsfilelist.append([jsUrl, jsPath])
                    # 获取季前赛赛程JS文件地址信息
                    if '3' in haveMk:
                        filename = 'l' + str(leagueId) + '_' + '3' + '.js'
                        jsUrl = lqconfig_qt.scheWebdir + season_path + '/' + filename
                        jsPath = lqconfig_qt.schelocaldir + season_path + '/' + filename
                        item = [jsUrl, jsPath]
                        if item not in jsfilelist:
                            jsfilelist.append(item)
                    # 获取季后赛赛程JS文件地址信息
                    if '2' in haveMk:
                        filename = 'l' + str(leagueId) + '_' + '2' + '.js'
                        jsUrl = lqconfig_qt.scheWebdir + season_path + '/' + filename
                        jsPath = lqconfig_qt.schelocaldir + season_path + '/' + filename
                        item = [jsUrl, jsPath]
                        if item not in jsfilelist:
                            jsfilelist.append(item)
                except Exception as e:
                    fileUtil.logLine(common_config.js2pyweb_e, ["LQ_GET_SCHEJS_CONTEXT_ERROR", sche_url, repr(e), traceback.format_exc()])
                    append_schedule_src(scheSrc)
                    print(e)
            else:
                append_schedule_src(scheSrc)
                append_schedule_src(LQleague.findScheJS(defaulturl3, lqconfig_qt.headers))
                append_schedule_src(LQleague.findScheJS(defaulturl2, lqconfig_qt.headers))
        # 杯赛
        elif type == 2:
            filename = 'c' + str(leagueId) + '.js'
            season_path = model.changeSeason(season)
            cupJSurl = lqconfig_qt.scheWebdir + season_path + '/' + filename
            jsPath = lqconfig_qt.schelocaldir + season_path + '/' + filename
            jsfilelist.append([cupJSurl, jsPath])
        else:
            pass
        return jsfilelist

    # 根据联赛ID、赛季、联赛类型获取 赛程JS本地文件列表
    @staticmethod
    def getLocalfiles(sclassID, kindtype):
        fileList = []
        context = js2pyUtil.jsLocjs(lqconfig_qt.seajslocaldir + 'sea' + str(sclassID) + '.js')
        seasonlist = _get_js_value(context, 'arrSeason') if context else None
        if seasonlist is None:
            return fileList
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
        seasonlist = _get_js_value(context, 'arrSeason') if context else None
        if seasonlist is None:
            return fileList
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
        leagues = crawler.get_league_metadata_web()
        return leagues


def _empty_to_none(value):
    value = str(value or "").strip()
    return value if value else None


def _get_js_value(context, name, default=None):
    try:
        return getattr(context, name)
    except Exception:
        return default


def _parse_country_id(value):
    text = str(value or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _should_preserve_existing_name_en(existing, fetched, short_name):
    existing = str(existing or "").strip()
    fetched = str(fetched or "").strip()
    short_name = str(short_name or "").strip()
    if not existing or not fetched:
        return False
    if fetched.lower() == short_name.lower() and len(existing) > len(fetched):
        return True
    return False


def ensure_basic_information_schema():
    _ensure_lq_league_metadata_schema()
    from scripts.migrate_lq_basic_information_tables import migrate

    migrate()


def _ensure_lq_league_metadata_schema():
    columns = set(_columns("lq_league"))
    for column, ddl in LEAGUE_METADATA_COLUMNS.items():
        if column not in columns:
            print("add lq_league.{0}".format(column))
            sql_util.sqlExecute("ALTER TABLE `lq_league` {0}".format(ddl))


def _columns(table):
    return [row[0] for row in sql_util.select("SHOW COLUMNS FROM `{0}`".format(table))]


def _update_payload(row):
    return {
        key: value
        for key, value in row.items()
        if value is not None and key not in ("recorded_at",)
    }


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
