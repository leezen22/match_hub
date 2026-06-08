from config import zqconfig_qt
from utils import sql_util
from utils.js2pyUtil import jsLocjs


def upleagueInfo():
    filepath = zqconfig_qt.ziliao_jspath
    context = jsLocjs(filepath)
    countrys = context.arr
    for i in range(0, len(countrys)):
        leagueList = countrys[i][4]
        countryID = countrys[i][0].split('_')[-1]
        countryCn = countrys[i][1]
        areaId = countrys[i][3]
        countryLogo = "http://zq.win007.com/Image/info/{0}".format(countrys[i][2])
        # 联赛列表
        for league in leagueList:
            # print(league)
            # 更新联赛JS文件，杯赛+无子联赛联赛

            leagueinfo = league.split(",")
            leagueId = leagueinfo[0]
            nameChsShort = leagueinfo[1]
            leagueType = leagueinfo[2]
            # ifHaveSub = leagueinfo[3]
            sql = "SELECT * FROM zq_league WHERE leagueID ={0}".format(leagueId)
            result = sql_util.select(sql)
            if len(result) == 0:
                print([leagueId,nameChsShort,leagueType,countryID,countryCn,areaId,countryLogo])
                sql_util.insertData('zq_league',[leagueId,nameChsShort,leagueType,countryID,countryCn,areaId,countryLogo],
                                          ['leagueID','nameChsShort','type','countryID','countryCn','areaId','countryLogo'],isDict=False)
