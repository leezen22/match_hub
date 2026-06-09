import os
from datetime import datetime
from pathlib import Path

from config import lqconfig_qt
from utils import js2pyUtil, sql_util
from utils.dateUtil import utc2local, getNowTime
from utils.fileUtil import dirFiles
from utils.webUtil import WebUtil


class EuropeOddsLq(object):

    @staticmethod
    def upodds_byfile():
        files = dirFiles(lqconfig_qt.europjs_dir, [])
        for file in files:
            print(getNowTime(), file)
            EuropeOddsLq.upOdds_byfile(file)

    @staticmethod
    def loadjs_europe():
        year = input("请输入开始时间(年)： ")
        starttime = year + "-01-01 00:00:00"
        # and sche.leagueId not in (8, 10, 11, 31, 34, 36, 67, 103)
        sql = " SELECT sche.scheduleID,sche.MatchTime,sche.MatchState,sche.MatchSeason,sche.leagueID,sche.cupqualifyid," \
              "lea.SclassKind,sche.partscore_f,sche.asianodds_f,sche.totalodds_f,sche.homeTeam,sche.awayTeam,sche.eurodds_f " \
              "FROM `lq_schedule` AS sche LEFT JOIN lq_sclass AS lea ON sche.leagueID =lea.leagueID " \
              "WHERE sche.MatchState=-1 and sche.eurodds_f in(0) and sche.MatchTime>='{0}' ORDER BY sche.MatchTime DESC ".format(
            starttime)
        # sche.leagueID = 1 and
        matchs = sql_util.select(sql)
        count = len(matchs)
        print(count, sql)
        EuropeOddsLq.load_europejs_odds(matchs, isproxy=False)

    @staticmethod
    def upOdds_byfile(filePath):
        matchid = os.path.basename(filePath).split(".")[0]
        sql = "SELECT eurodds_f,matchState FROM `lq_schedule` WHERE scheduleID={0}".format(matchid)
        data = sql_util.select_rows(sql)
        if len(data) > 0 and data[0][0] != 2 and data[0][1] == -1 and os.path.exists(filePath):
            result = EuropeOddsLq.get_odds_byfile(filePath)
            if result['state'] == 1 and matchid == str(result['matchid']):
                odds_keys = EuropeOddsLq.get_odds_columns()
                detail_keys = EuropeOddsLq.get_detail_columns()
                odds_values = result['odds']
                detail_values = result['detail']
                # 插入成功标记
                result_odds = False
                result_detail = False
                sql_util.upData('lq_schedule', {'eurodds_f': 1}, {'ScheduleID': matchid})
                if data[0][0] == 0:
                    result_odds = sql_util.insetMany('lq_europe', odds_keys, odds_values)
                    result_detail = sql_util.insetMany('lq_europedetail', detail_keys, detail_values)
                if data[0][0] == 1:
                    select_europe_sql = "SELECT oddsID_q FROM lq_europe WHERE ScheduleID= {0}".format(matchid)
                    select_europe_result = sql_util.select_rows(select_europe_sql)
                    select_detail_sql = " SELECT * FROM lq_europedetail WHERE OddsID_Q in " \
                                        "(SELECT OddsID_Q FROM lq_europe WHERE scheduleID={0})".format(matchid)
                    select_detail_result = sql_util.select_rows(select_detail_sql)
                    if len(select_europe_result) == 0:
                        result_odds = sql_util.insetMany('lq_europe', odds_keys, odds_values)
                    else:
                        result_odds = True
                    if len(select_detail_result) == 0:
                        result_detail = sql_util.insetMany('lq_europedetail', detail_keys, detail_values)
                    else:
                        result_detail = True
                # 更新正常
                if result_odds and result_detail:
                    # 如果比赛完场
                    if data[0][1] == -1:
                        # 标记 赛前欧赔初盘/即时盘 采集 完成
                        sql_util.upData('lq_schedule', {'eurodds_f': 2}, {'ScheduleID': matchid})
                        # 标记赛前欧赔变化记录采集 完成
                        sql_util.upData('lq_europe', {'finished_pre': 2}, {'ScheduleID': matchid})
                    os.remove(filePath)
                else:
                    print(['插入数据异常', matchid, result_odds, result_detail])
            else:
                os.remove(filePath)

    @staticmethod
    def load_europejs_odds(matchs, isproxy):
        for match in matchs:
            print(match)
            matchid = match[0]
            season = match[3]
            leagueid = match[4]
            headers = lqconfig_qt.headers_europe
            referer = lqconfig_qt.europe_url + str(matchid) + ".htm"
            headers['Referer'] = referer
            file_url = lqconfig_qt.europejs_url + str(matchid)[0:1] + "/" + str(matchid)[1:3] + "/" + str(
                matchid) + ".js"
            file_dir = lqconfig_qt.europjs_dir + str(leagueid) + "\\" + season + "\\"
            file_name = file_url.split('?')[0].split('/')[-1]
            filePath = file_dir + file_name
            if not Path(filePath).exists():
                result = WebUtil.loadfile(file_url, file_dir, headers, isProxy=isproxy, retry_time=2)
                print(result, file_url)
                if result == 1:
                    EuropeOddsLq.upOdds_byfile(filePath)
                # print([gettime(), result, match])
                if result == 4:
                    sql_util.upData('lq_schedule', {'eurodds_f': 4}, {'scheduleID': matchid})
            else:
                EuropeOddsLq.upOdds_byfile(filePath)

    @staticmethod
    def get_odds_byfile(filepath):
        result = {'state': 0, 'odds': [], 'detail': []}
        europe_odds_list = []
        oddsdetails = []
        try:
            fixed_content = " var ScheduleID; var game; var gameDetail;"
            file = open(filepath, 'r', encoding='utf-8')
            jsContent = file.read()
            jsContent = fixed_content + jsContent
            file.close()
            parse_result = js2pyUtil.js2c(
                jsContent,
                source=filepath,
                required_names=("MatchTime", "game"),
            )
            if parse_result[0] != 1:
                return result
            context = parse_result[1]
            utctime_str = context.MatchTime
            matchtime = EuropeOddsLq.getLocaltime(utctime_str)
            ScheduleID = context.ScheduleID
            oddsID_list = []
            if context.game:
                game = context.game
                for item in game:
                    odds = item.split("|")
                    companyid = odds[0]
                    # 主流公司 + 交易所 + 10Bet,立博，金宝博
                    if odds[17] == '1' or odds[18] == '1' or (companyid in ['369', '83', '367']):
                        # 无开盘公司英文名称字段
                        if len(odds) == 19:
                            odds.append(None)
                        odds[15] = EuropeOddsLq.getLocaltime(odds[15]).strftime("%Y-%m-%d %H:%M:%S")
                        odds[16] = odds[16].split("(")[0]
                        odds.append(int(context.ScheduleID))
                        del odds[19]
                        del odds[18]
                        del odds[17]
                        del odds[2]
                        for i in range(0, len(odds)):
                            if odds[i] == '':
                                odds[i] = None
                        oddsID_list.append(odds[1])
                        europe_odds_list.append(odds)
            # 提取赛前变化记录
            if context.gameDetail:
                gameDetail = context.gameDetail
                for item in gameDetail:
                    odds_data = item.split("^")
                    oddsID = odds_data[0]
                    oddID_details = []
                    # 指定开盘公司范围
                    if oddsID in oddsID_list:
                        # 数据异常则修复，无异常返回原数据
                        fixe_data = EuropeOddsLq.fixed_detail(odds_data[1])
                        details_data = fixe_data.split(";")
                        for cell in details_data:
                            detail = cell.split("|")
                            if len(cell) > 0:
                                modifytime = detail[2]
                                modifytime_fixed = EuropeOddsLq.getModifytime(matchtime, modifytime, '即')
                                detail[2] = modifytime_fixed
                                if len(detail) == 3:
                                    detail = detail + [None, None]
                                detail.append(oddsID)
                                # 赔率类型，即时盘
                                detail.append(1)
                                oddID_details.append(detail)
                        oddID_details.reverse()
                    oddsdetails = oddsdetails + oddID_details

        except Exception as e:
            # more = traceback.format_exc()
            # print(more)
            print([e, filepath])
            # os.remove(filepath)
        else:
            result['state'] = 1
            result['matchid'] = ScheduleID
            result['odds'] = europe_odds_list
            result['detail'] = oddsdetails
        return result

    @staticmethod
    def fixed_detail(details_str):
        handList = []
        detail_list = details_str.split(";")
        for data in detail_list:
            detail = data.split("|")
            if len(detail) >= 3:
                modifytime = detail[2]
                if len(modifytime) > 11:
                    handList.append(modifytime)
        for item in handList:
            fiexd = item[0:11] + ";" + item[11:]
            details_str = details_str.replace(item, fiexd)
        return details_str

    @staticmethod
    def get_odds_columns():
        columns = ['companyID', 'oddsID_Q',
                   'FirstHomeWin', 'FirstAwayWin', 'Probability_H0', 'Probability_G0', 'Back_F',
                   'HomeWin', 'AwayWin', 'Probability_H1', 'Probability_G1', 'Back',
                   'Kelly_Home', 'Kelly_Away', 'ModifyTime', 'CompanyName', 'ScheduleID']
        return columns

    @staticmethod
    def get_detail_columns():
        columns = ['HomeWin', 'AwayWin', 'ModifyTime', 'Kelly_Home', 'Kelly_Away', 'OddsID_Q', 'oddsType']
        return columns

    @staticmethod
    def getLocaltime(utctime_str):
        t2 = utctime_str.split(",")
        month = int(t2[1].split('-')[0])
        utc_tm = datetime(int(t2[0]), month, int(t2[2]), int(t2[3]), int(t2[4]), int(t2[5]))
        localtime = utc2local(utc_tm)
        return localtime

    @staticmethod
    def getModifytime(matchtime, modifytime, oddsType):
        match_y = matchtime.year
        match_m = matchtime.month
        modify_m = int(modifytime[0:2])
        if oddsType == '即' and modify_m > match_m:
            modify_y = match_y - 1
        elif oddsType == '滚' and modify_m < match_m and modify_m == 1:
            modify_y = match_y + 1
        else:
            modify_y = match_y
        modifytime = str(modify_y) + '-' + modifytime
        return modifytime


# if __name__ == '__main__':
#     EuropeOddsLq.task_loadjs_europe()
