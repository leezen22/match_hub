from utils import sql_util_local
from utils.dateUtil import getNowTime


def upEuropePre(companyID):
    columns = ['OddsID_Q', 'homeWin', 'standoff', 'awayWin', 'matchState', 'happenTime',
               'homeScore', 'awayScore', 'type', 'isBet', 'oddsType', 'kelly_Home', 'kelly_Away', 'modifyTime']
    tableName = "zq_totalScore_pre_{0}".format(companyID)

    sql = "select oddsID,oddsID_Q,companyID FROM zq_europe WHERE companyID={0}".format(companyID)
    result = sql_util_local.select(sql)
    details = []
    oddsIDList = []
    remain = len(result)
    print(companyID, remain)
    current = 0
    for data in result:
        oddsID = data[0]
        oddsID_Q = data[1]
        sql2 = """select zd.OddsID_Q,zd.homeWin,zd.standoff,zd.awayWin,zd.matchState,zd.happenTime, 
        zd.homeScore,zd.awayScore,zd.type,zd.isBet,zd.oddsType,zd.kelly_Home,zd.kelly_Off,
        zd.kelly_Away,zd.modifyTime
        FROM zq_europeDetail as zd 
        WHERE zd.oddsID_Q={0}""".format(oddsID_Q)
        result2 = sql_util_local.select(sql2)
        count = len(result2)
        if count > 0:
            current = current + count
            details = details + list(result2)
            oddsIDList.append(oddsID)
        print(companyID, "剩余", remain, '已收集', current, data)
        if len(details) > 5000:
            # print([companyID, oddsIDList])
            # sql_util.insetMany(tableName, columns, details)
            # if len(oddsIDList) > 0:
            #     oddsID_str = "({0})".format(",".join(oddsIDList))
            #     upSql = " update zq_europe set finished_pre=2, hasPre=1 where oddsID in {0}".format(oddsID_str)
            #     sql_util.sqlExecute(upSql)
            print(getNowTime(), " 本轮结束, 当前剩余", remain, data)
            details = []
            current = 0
            oddsIDList = []
        remain = remain - 1


# if __name__ == '__main__':
#     companys = [281, 545, 115, 104, 81, 82, 90, 80, 474, 517]
#     upEuropePre(281)

    # for companyID in companys:
