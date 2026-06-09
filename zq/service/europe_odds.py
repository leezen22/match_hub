import os
from datetime import datetime
from pathlib import Path
from config import zqconfig_qt
from crawler.qt.zq_europe_odds_crawler import EuropeOddsCrawler
from crawler.qt.zq_total_odds_crawler import TotalOddsCrawler
from utils import js2pyUtil, sql_util, sql_util_local
from utils.dateUtil import utc2local, getNowTime
from utils.fileUtil import dirFiles
from utils.webUtil import WebUtil


class EuropeOddsZq(object):

    # 赛前欧赔赔率信息
    @staticmethod
    def task_upodds_byfile():
        year = input("请输入比赛时间时间(年)： ")
        files = dirFiles(zqconfig_qt.europjs_dir + year + "\\", [])
        count = len(files)
        for file in files:
            EuropeOddsZq.upOdds_byFile(file)
            count = count - 1
            print("剩余", count, getNowTime(), file)

    @staticmethod
    def up_europeDetail(data, kind):
        matchState = data['matchState']
        details = data['detail']
        details_pre = details['pre']
        details_gun = details['gun']
        count_pre = len(details['pre'])
        count_gun = len(details['gun'])
        oddsID = data['oddsID']
        oddsID_Q = data['oddsID_Q']
        hasPre = data['hasPre']
        hasGun = data['hasGun']
        hasFirst = data['hasFirst']
        hasHalf = data['hasHalf']
        hasSecond = data['hasSecond']

        columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'homeWin', 'standoff',
                   'awayWin', 'isBet', 'modifyTime', 'oddsID_Q']

        # 采集源包含赛前+赛中，采集成功且未结束采集
        if kind == 2 and data['state'] == 1 and (data['finished_gun'] in [0, 1]):
            if count_pre + count_gun > 0:
                finished_pre = data['finished_pre']
                finished_gun = data['finished_gun']
                # 防止数据紊乱，更新前先更新状态，防止下次更新数据时，数据重复
                if data['hasPre'] == 1 and finished_pre == 0:
                    finished_pre = 1
                if data['hasGun'] == 1 and finished_gun == 0:
                    finished_gun = 1

                if finished_pre != data['finished_pre'] or finished_gun != data['finished_gun']:
                    sql_util.upData('zq_europe',
                                    {'finished_pre': finished_pre, 'finished_gun': finished_gun},
                                    {'oddsID': oddsID})

                # ---- 插入数据范围判断，避免完全匹配更新------
                # 数据包含赛前变化记录
                if hasPre == 1:
                    if data['finished_pre'] == 0 and data['finished_gun'] == 0:
                        result = sql_util.insetMany('zq_europeDetail', columns, details_pre + details_gun)
                    else:
                        sql = "select count(*) from zq_europeDetail where oddsID={0}".format(oddsID)
                        old = sql_util.select(sql)
                        count_old = old[0][0]
                        if (count_pre + count_gun) > count_old:
                            new = (details_pre + details_gun)[count_old:]
                            result = sql_util.insetMany('zq_europeDetail', columns, new)
                        # 不插入数据
                        else:
                            result = True
                # 只有赛中，无赛前
                elif hasPre == 0 and hasGun == 1:
                    if data['finished_pre'] == 0 and data['finished_gun'] == 0:
                        result = sql_util.insetMany('zq_europeDetail', columns, details_pre + details_gun)
                    else:
                        inSql = " select count(*) from zq_europeDetail where oddsID={0} " \
                                "and matchState in {1} ".format(oddsID, "(1,2,3)")
                        old_in = sql_util.select_rows(inSql)
                        count_oldIn = old_in[0][0]
                        new_in = details_gun[count_oldIn:]
                        result = sql_util.insetMany('zq_europeDetail', columns, new_in)
                # 无数据，不插入数据
                else:
                    result = True
            else:
                result = True

            # 更新采集状态
            if (matchState == -1 or matchState == -10) and result:
                if hasGun == 0:
                    finished_gun = 3
                else:
                    finished_gun = 2

                if hasPre == 1:
                    finished_pre = 2
                else:
                    finished_pre = data['finished_pre']

                sql_util.upData('zq_europe',
                                {'finished_pre': finished_pre, 'finished_gun': finished_gun, 'hasPre': hasPre,
                                 'hasGun': hasGun, 'hasFirst': hasFirst, 'hasHalf': hasHalf, 'hasSecond': hasSecond},
                                {'oddsID': oddsID})

    @staticmethod
    def insert_europeDetail_batch(data, kind):
        isUP = False
        try:
            columns = ['oddsID', 'matchState', 'happenTime', 'oddsType', 'homeScore', 'awayScore', 'homeWin',
                       'standoff',
                       'awayWin', 'isBet', 'modifyTime', 'oddsID_Q']
            # 采集源包含赛前+赛中
            if kind == 2:
                isUP = sql_util.insetMany('zq_europeDetail', columns, data)
        except Exception as e:
            print(e)
        return isUP

    @staticmethod
    def task_loadjs_europe():
        star = input("请输入开始时间(年)： ")
        startTime = "{0}-01-01 00:00:00".format(star)
        end = input("请输入结束时间(年)： ")
        endTime = "{0}-01-01 00:00:00".format(end)
        # and sche.leagueId not in (8, 10, 11, 31, 34, 36, 67, 103)
        sql = " SELECT sche.matchID, sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueId," \
              "sche.subLeagueID, lea.type,sche.partScore_f,sche.eurOdds_f,sche.totalOdds_f,sche.HomeTeam," \
              "sche.AwayTeam,sche.eurOdds_f " \
              "FROM `zq_schedule` AS sche " \
              "LEFT JOIN zq_league AS lea " \
              "ON sche.LeagueID =lea.LeagueID " \
              "WHERE sche.MatchState=-1 and eurOdds_f in(0) and matchTime>='{0}' and matchTime<'{1}' " \
              "ORDER BY sche.matchTime ASC ".format(startTime, endTime)
        matchs = sql_util.select(sql)
        count = len(matchs)
        print(count, sql)
        EuropeOddsZq.load_europejs_odds(matchs, isproxy=False)

    @staticmethod
    def get_odds_byfile(filepath, matchID, scheduleID):
        result = {'state': 0, 'odds': [], 'detail': []}
        europe_odds_list = []
        oddsdetails = []
        # detail = {}
        try:
            fixed_content = " var ScheduleID; var game; var gameDetail;"
            file = open(filepath, 'r', encoding='utf-8')
            jscontent = file.read()
            jscontent = fixed_content + jscontent
            file.close()
            parse_result = js2pyUtil.js2c(
                jscontent,
                source=filepath,
                required_names=("MatchTime", "game"),
            )
            if parse_result[0] != 1:
                return result
            context = parse_result[1]
            utctime_str = context.MatchTime
            matchTime = EuropeOddsZq.getLocaltime(utctime_str)
            currentScheduleID = context.ScheduleID
            oddsIDDict = {}
            if context.game and scheduleID == currentScheduleID:
                game = context.game
                for data in game:
                    odds = data.split("|")
                    if odds[23] == '1' or odds[22] == '1':
                        companyID = odds[0]
                        oddsID_Q = odds[1]

                        odds[20] = EuropeOddsZq.getLocaltime(odds[20]).strftime("%Y-%m-%d %H:%M:%S")
                        odds[21] = odds[21].split("(")[0]
                        del odds[23]
                        del odds[22]
                        del odds[2]
                        for i in range(0, len(odds)):
                            if odds[i] == '':
                                odds[i] = None
                        odds = odds + [matchID, scheduleID]
                        oddsIDDict[oddsID_Q] = int(companyID)
                        europe_odds_list.append(odds)
            if context.gameDetail and scheduleID == currentScheduleID:
                gameDetail = context.gameDetail
                for data in gameDetail:
                    data2 = data.split("^")
                    oddsID_Q = data2[0]
                    oddID_details = []
                    if oddsID_Q in oddsIDDict.keys():
                        companyID = oddsIDDict[oddsID_Q]
                        # 数据异常则修复，无异常返回原数据
                        fixe_data = EuropeOddsZq.fixed_detail(data2[1])
                        details_data = fixe_data.split(";")
                        for item in details_data:
                            odds_detail = item.split("|")
                            if len(odds_detail) == 4 or len(odds_detail) == 7:
                                modifyTime = odds_detail[3]
                                modifyTime_fixed = EuropeOddsZq.getModifyTime(matchTime, modifyTime, '即')
                                odds_detail[3] = modifyTime_fixed
                                if len(odds_detail) == 4:
                                    odds_detail = odds_detail + [None, None, None]
                                odds_detail = odds_detail + [oddsID_Q, matchID, scheduleID, companyID]
                                oddID_details.append(odds_detail)
                        oddID_details.reverse()
                        # detail[oddsID] = oddID_details
                        oddsdetails = oddsdetails + oddID_details


        except Exception as e:
            print([e, filepath])
            os.remove(filepath)
        else:
            result['state'] = 1
            result['scheduleID'] = currentScheduleID
            result['matchID'] = matchID
            result['odds'] = europe_odds_list
            # result['detail'] = detail
            result['detail'] = oddsdetails
        return result

    @staticmethod
    def fixed_detail(details_str):
        handList = []
        detail_list = details_str.split(";")
        for data in detail_list:
            detail = data.split("|")
            if len(detail) >= 4:
                modifytime = detail[3]
                if len(modifytime) > 11:
                    handList.append(modifytime)
        for item in handList:
            fiexd = item[0:11] + ";" + item[11:]
            details_str = details_str.replace(item, fiexd)
        return details_str

    @staticmethod
    def load_europejs_odds(matchs, isproxy):
        count = len(matchs)
        for match in matchs:
            # result = {'state': 2, 'odds': [],'oddsdetail':[]}
            matchID = match[0]
            scheduleID = match[1]
            matchTime = match[2]
            matchYear = matchTime.year
            season = match[4]
            leagueID = match[5]
            headers = zqconfig_qt.headers_europe
            referer = zqconfig_qt.europe_url + str(scheduleID) + ".htm"
            headers['Referer'] = referer
            file_url = zqconfig_qt.europejs_url + str(scheduleID) + ".js"
            file_dir = "{0}{1}\\{2}\\{3}\\".format(zqconfig_qt.europjs_dir, matchYear, leagueID, season)
            # zqconfig_qt.europjs_dir + str(leagueID) + "\\" + season + "\\"
            file_name = "{0}_{1}".format(matchID, scheduleID) + ".js"
            filePath = file_dir + file_name
            if not Path(filePath).exists():
                result = WebUtil.loadFileByName(file_url, filePath, headers, isProxy=isproxy)
                print('剩余', count, [getNowTime(), result, match])
                if result == 1:
                    EuropeOddsZq.upOdds_byFile(filePath)
                if result == 4:
                    sql_util.upData('zq_schedule', {'eurOdds_f': 4}, {'matchID': matchID})
            else:
                EuropeOddsZq.upOdds_byFile(filePath)
            count = count - 1

    # 逻辑未做历史判断更新
    @staticmethod
    def upOdds_byFile(filePath):
        fileName = os.path.basename(filePath).split(".")[0]
        matchID = int(fileName.split("_")[0])
        scheduleID = int(fileName.split("_")[1])
        sql = "SELECT eurodds_f,matchState,matchTime FROM `zq_schedule` WHERE matchID={0}".format(matchID)
        data = sql_util.select_rows(sql)
        # if len(data) > 0 and data[0][0] != 2 and data[0][1] == -1:
        if len(data) > 0 and data[0][1] == -1:
            year = data[0][2].year
            detail_tableName = "zq_europeDetail_{0}".format(year)
            result = EuropeOddsZq.get_odds_byfile(filePath, matchID, scheduleID)
            if result['state'] == 1 and scheduleID == result['scheduleID']:
                odds_keys = EuropeOddsZq.get_odds_columns()
                detail_keys = EuropeOddsZq.get_detail_columns()
                odds_values = result['odds']
                detail_values = result['detail']
                # 插入成功标记
                result_odds = False
                result_detail = False
                sql_util.upData('zq_schedule', {'eurodds_f': 1}, {'matchID': matchID})
                if data[0][0] == 0:
                    result_odds = sql_util.insetMany('zq_europe', odds_keys, odds_values)
                    if result_odds:
                        result_detail = sql_util.insetMany(detail_tableName, detail_keys, detail_values)
                    else:
                        result_detail = False

                elif data[0][0] == 1:
                    select_europe_sql = "SELECT count(*) FROM zq_europe WHERE matchID= {0}".format(matchID)
                    select_europe_result = sql_util.select_rows(select_europe_sql)
                    select_detail_sql = " SELECT count(*) FROM {0} WHERE oddsID_Q in " \
                                        "(SELECT OddsID_Q FROM zq_europe WHERE matchID = {1})" \
                        .format(detail_tableName, matchID)
                    select_detail_result = sql_util.select_rows(select_detail_sql)
                    count_detail = select_detail_result[0][0]
                    count_europe = select_europe_result[0][0]
                    if count_europe == 0:
                        result_odds = sql_util.insetMany('zq_europe', odds_keys, odds_values)
                    else:
                        result_odds = True
                    if count_detail == 0:
                        if result_odds:
                            result_detail = sql_util.insetMany(detail_tableName, detail_keys, detail_values)
                        else:
                            result_detail = False
                    else:
                        result_detail = True
                else:
                    result_odds = True
                    select_detail_sql = " SELECT count(*) FROM {0} WHERE oddsID_Q in " \
                                        "(SELECT OddsID_Q FROM zq_europe WHERE matchID = {1})" \
                        .format(detail_tableName, matchID)
                    select_detail_result = sql_util.select_rows(select_detail_sql)
                    count_detail = select_detail_result[0][0]
                    if count_detail == 0:
                        if result_odds:
                            result_detail = sql_util.insetMany(detail_tableName, detail_keys, detail_values)
                        else:
                            result_detail = False
                    else:
                        result_detail = True

                if data[0][1] == -1:
                    if result_odds:
                        # 标记 赛前欧赔初盘/即时盘 采集 完成
                        sql_util.upData('zq_schedule', {'eurOdds_f': 2}, {'matchID': matchID})
                    else:
                        sql_util.upData('zq_schedule', {'eurOdds_f': 1}, {'matchID': matchID})
                        print(['初/即 插入数据异常', matchID, scheduleID, result_odds, result_detail])
                    if result_detail:
                        # 标记赛前欧赔变化记录采集 完成
                        sql_util.upData('zq_europe', {'finished_pre': 2, 'hasPre': 1}, {'matchID': matchID})
                    else:
                        sql_util.upData('zq_europe', {'finished_pre': 0}, {'matchID': matchID})
                        print(['变化记录 插入数据异常', matchID, scheduleID, result_odds, result_detail])

                if result_odds and result_detail:
                    os.remove(filePath)
            else:
                if os.path.exists(filePath):
                    os.remove(filePath)

    @staticmethod
    def upOdds_byMatchs(matchs):
        for match in matchs:
            matchid = match['scheduleID']
            season = match['matchSeason']
            leagueid = match['leagueID']
            eurodds_f = match['eurodds_f']
            file_dir = zqconfig_qt.europjs_dir + str(leagueid) + "\\" + season + "\\"
            file_name = str(matchid) + ".js"
            filePath = file_dir + file_name
            if Path(filePath).exists() and eurodds_f == 0:
                print(filePath)
                result = EuropeOddsZq.get_odds_byfile(filePath)
                if result['state'] == 1:
                    matchid = result['matchid']
                    sql_util.upData('zq_schedule', {'eurodds_f': 1}, {'ScheduleID': matchid})
                    odds_keys = EuropeOddsZq.get_odds_columns()
                    detail_keys = EuropeOddsZq.get_detail_columns()
                    odds_values = result['odds']
                    detail_values = result['detail']
                    result_odds = sql_util.insetMany('zq_europe', odds_keys, odds_values)
                    result_detail = sql_util.insetMany('zq_europedetail', detail_keys, detail_values)
                    if result_odds and result_detail:
                        sql_util.upData('zq_schedule', {'eurodds_f': 2}, {'ScheduleID': matchid})
                        os.remove(filePath)
                    else:
                        print(['插入数据异常', matchid, result_odds, result_detail])

    @staticmethod
    def getLocaltime(utctime_str):
        t2 = utctime_str.split(",")
        month = int(t2[1].split('-')[0])
        utc_tm = datetime(int(t2[0]), month, int(t2[2]), int(t2[3]), int(t2[4]), int(t2[5]))
        localtime = utc2local(utc_tm)
        return localtime

    @staticmethod
    def getModifyTime(matchTime, modifyTime, oddsType):
        match_y = matchTime.year
        match_m = matchTime.month
        modify_m = int(modifyTime[0:2])
        if oddsType == '即' and modify_m > match_m:
            modify_y = match_y - 1
        elif oddsType == '滚' and modify_m < match_m and modify_m == 1:
            modify_y = match_y + 1
        else:
            modify_y = match_y
        modifyTime = str(modify_y) + '-' + modifyTime
        return modifyTime

    @staticmethod
    def get_odds_columns():
        columns = ['companyID', 'oddsID_Q',
                   'firstHomeWin', 'firstStandoff', 'firstAwayWin', 'probability_H0', 'probability_T0',
                   'probability_G0', 'back_F',
                   'homeWin', 'standoff', 'awayWin', 'probability_H1', 'probability_T1', 'probability_G1', 'back',
                   'kelly_Home', 'kelly_Off', 'kelly_Away', 'modifyTime', 'companyName', 'matchID', 'scheduleID']
        return columns

    @staticmethod
    def get_detail_columns():
        columns = ['homeWin', 'standoff', 'awayWin', 'modifyTime', 'kelly_Home', 'kelly_Off', 'kelly_Away',
                   'oddsID_Q', 'matchID', 'scheduleID', 'companyID']
        return columns

    @staticmethod
    def local_detail_byFile():
        year = input("请输入比赛时间时间(年)： ")
        files = dirFiles(zqconfig_qt.europjs_dir + year + "\\", [])
        count = len(files)
        for file in files:
            EuropeOddsZq.local_upDetail_byFile(file)
            count = count - 1
            print("剩余", count, getNowTime(), file)

    @staticmethod
    def local_upDetail_byFile(filePath):
        fileName = os.path.basename(filePath).split(".")[0]
        matchID = int(fileName.split("_")[0])
        scheduleID = int(fileName.split("_")[1])
        sql = "SELECT eurodds_f,matchState,matchTime FROM `zq_schedule` WHERE matchID={0}".format(matchID)
        data = sql_util_local.select_rows(sql)
        # if len(data) > 0 and data[0][0] != 2 and data[0][1] == -1:
        if len(data) > 0 and data[0][1] == -1:
            year = data[0][2].year
            detail_tableName = "zq_europeDetail_{0}".format(year)
            result = EuropeOddsZq.get_odds_byfile(filePath, matchID, scheduleID)
            if result['state'] == 1 and scheduleID == result['scheduleID']:
                odds_keys = EuropeOddsZq.get_odds_columns()
                detail_keys = EuropeOddsZq.get_detail_columns()
                odds_values = result['odds']
                detail_values = result['detail']
                # 插入成功标记
                result_odds = False
                result_detail = False
                sql_util_local.upData('zq_schedule', {'eurodds_f': 1}, {'matchID': matchID})
                if data[0][0] == 0:
                    result_odds = sql_util_local.insetMany('zq_europe', odds_keys, odds_values)
                    if result_odds:
                        result_detail = sql_util_local.insetMany(detail_tableName, detail_keys, detail_values)
                    else:
                        result_detail = False

                elif data[0][0] == 1:
                    select_europe_sql = "SELECT count(*) FROM zq_europe WHERE matchID= {0}".format(matchID)
                    select_europe_result = sql_util_local.select_rows(select_europe_sql)
                    select_detail_sql = " SELECT count(*) FROM {0} WHERE oddsID_Q in " \
                                        "(SELECT OddsID_Q FROM zq_europe WHERE matchID = {1})" \
                        .format(detail_tableName, matchID)
                    select_detail_result = sql_util_local.select_rows(select_detail_sql)
                    count_detail = select_detail_result[0][0]
                    count_europe = select_europe_result[0][0]
                    if count_europe == 0:
                        result_odds = sql_util_local.insetMany('zq_europe', odds_keys, odds_values)
                    else:
                        result_odds = True
                    if count_detail == 0:
                        if result_odds:
                            result_detail = sql_util_local.insetMany(detail_tableName, detail_keys, detail_values)
                        else:
                            result_detail = False
                    else:
                        result_detail = True
                else:
                    result_odds = True
                    select_detail_sql = " SELECT count(*) FROM {0} WHERE oddsID_Q in " \
                                        "(SELECT OddsID_Q FROM zq_europe WHERE matchID = {1})" \
                        .format(detail_tableName, matchID)
                    select_detail_result = sql_util_local.select_rows(select_detail_sql)
                    count_detail = select_detail_result[0][0]
                    if count_detail == 0:
                        if result_odds:
                            result_detail = sql_util_local.insetMany(detail_tableName, detail_keys, detail_values)
                        else:
                            result_detail = False
                    else:
                        result_detail = True

                if data[0][1] == -1:
                    if result_odds:
                        # 标记 赛前欧赔初盘/即时盘 采集 完成
                        sql_util_local.upData('zq_schedule', {'eurOdds_f': 2}, {'matchID': matchID})
                    else:
                        sql_util_local.upData('zq_schedule', {'eurOdds_f': 1}, {'matchID': matchID})
                        print(['初/即 插入数据异常', matchID, scheduleID, result_odds, result_detail])
                    if result_detail:
                        # 标记赛前欧赔变化记录采集 完成
                        sql_util_local.upData('zq_europe', {'finished_pre': 2, 'hasPre': 1}, {'matchID': matchID})
                    else:
                        sql_util_local.upData('zq_europe', {'finished_pre': 1}, {'matchID': matchID})
                        print(['变化记录 插入数据异常', matchID, scheduleID, result_odds, result_detail])

                if result_odds and result_detail:
                    os.remove(filePath)
            else:
                if os.path.exists(filePath):
                    os.remove(filePath)

    @staticmethod
    def up_odds_web(start_time=None):
        if start_time:
            str_start = "and MatchTime>='{0}'".format(start_time)
        else:
            str_start = ''
        sql = "SELECT sche.MatchID,sche.ScheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.LeagueId,sche.SubLeagueID, " \
              "lea.Type,sche.Partscore_f,sche.Eurodds_f,sche.HomeTeam,sche.AwayTeam " \
              "FROM `zq_schedule` AS sche LEFT JOIN zq_league AS lea ON sche.LeagueID =lea.LeagueID " \
              "WHERE sche.MatchState=-1 and sche.Eurodds_f IN(0,1) {0} " \
              "ORDER BY sche.MatchTime ASC".format(str_start)
        results = sql_util.select(sql)
        print("开始更新欧赔初盘：{0}".format(len(results)))
        for item in results:
            print(item)
            matchID = item[0]
            scheduleID = item[1]
            matchState = item[3]
            finished = item[9]
            eurCrawler = EuropeOddsCrawler(matchID, scheduleID, matchState, finished)
            oddsData = eurCrawler.qt_web_get(hasDetail=True)
            if oddsData['state'] == 1:
                sql_util.upData('zq_schedule', {'eurodds_f': 1}, {'ScheduleID': scheduleID})
                oddsList = oddsData['odds']
                if finished == 0:
                    sql_util.insertDatas('zq_europe', oddsList)
                else:
                    for odds in oddsList:
                        condition = {'ScheduleID': scheduleID, 'CompanyID': odds['companyId']}
                        results2 = sql_util.select_table_rows('zq_europe', ['OddsID'], condition, isDis=True)
                        if len(results2) > 0:
                            sql_util.upData('zq_europe', odds, condition)
                        else:
                            sql_util.insertData('zq_europe', odds)
                if matchState in (-1, -10):
                    sql_util.upData('zq_schedule', {'eurodds_f': 2}, {'ScheduleID': scheduleID})
            elif matchState == -1 and oddsData['state'] == 0:
                sql_util.upData('zq_schedule', {'eurodds_f': 4}, {'ScheduleID': scheduleID})


if __name__ == '__main__':
    # EuropeOddsZq.up_odds_web('2025-07-01 00:00:00')
#     print('')
    # filePath = "E:\\sports\zuqiu\\1x2\\2020\\969\\2019-2020\\1202260_1783339.js"
    # matchID = 12022
    # scheduleID = 1783339
    # result = EuropeOddsZq.get_odds_byfile(filePath, matchID, scheduleID)
    # print("s")
    # filepath = "E:\\sports\\zuqiu\\1x2\\10\\2019-2020\\11.js"
    # result = EuropeOdds.get_odds_byfile(filepath)
    # if result['state'] == 1:
    #     matchid = result['matchid']
    #     sql_util_zq.upData('zq_schedule', {'eurodds_f': 1}, {'ScheduleID': matchid})
    #     odds_keys = EuropeOdds.get_odds_columns()
    #     detail_keys = EuropeOdds.get_detail_columns()
    #     odds_values = result['odds']
    #     detail_values = result['detail']
    #     sql_util_zq.insetMany('zq_europe', odds_keys, odds_values)
    #     sql_util_zq.insetMany('zq_europedetail', detail_keys, detail_values)
    #     sql_util_zq.upData('schedule', {'eurodds_f': 2}, {'ScheduleID': matchid})
    companyIds=[[281, 8],[115,9],[545,3]]
    for ar in companyIds:
        # companyIds2=
        sql1 = "SELECT scheduleID,oddsID FROM zq_europe_{0} WHERE goal is NULL ORDER BY oddsID ASC".format(ar[0])
        s1 = sql_util.select(sql1)
        for item1 in s1:
            scheduleID = item1[0]
            totalCrawler = TotalOddsCrawler(matchID, scheduleID, -1)
            oddsData = totalCrawler.qt_mobile_get()
            print(oddsData)
            # sql3 = "SELECT ID,scheduleID FROM zq_europe_{0} WHERE scheduleId={1} ORDER BY ID ASC".format(ar[0],scheduleID)
            # s3 = sql_util.select(sql3)
            # if len(s3)>1:
            #     id1= s3[0][0]
            #     sql4 = "DELETE FROM zq_europe_{0} WHERE scheduleID={2} and ID>{1}".format(ar[0], id1, scheduleID)
            #     sql_util.sqlExecute(sql4)

            sql2 = "SELECT highOdds_F, goal_F, lowOdds_F, highOdds, goal, lowOdds FROM zq_totalScore " \
                   "WHERE scheduleId={1} and companyId={0} and goal>0 and goal_F>0  ".format(ar[1],scheduleID)
            s2= sql_util.select(sql2,isDict=True)
            if len(s2)>0:
                print([ar[0], item1])
                earlyOdds= s2[0]
                sql_util.upData('zq_europe_{0}'.format(ar[0]), earlyOdds, {'ScheduleID': scheduleID})

