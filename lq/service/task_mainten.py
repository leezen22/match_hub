import os
import utils.fileUtil
import utils.js2pyUtil
from config import lqconfig_qt
from lq.extract import MatchJS
from utils import sql_util


def upScheTaskByFlag(filepath, flag):
    filename = os.path.basename(filepath)
    leagueID = filename.split('.')[0].split('_')[0][1:]
    season = os.path.dirname(filepath).split("/")[-1]
    seapath = lqconfig_qt.seajslocaldir + "sea" + leagueID + ".js"
    scheKey = leagueID + '#' + season + '#' + filename
    condition = {'scheKey': scheKey}
    keys = ['ID', 'scheKey', 'leagueID', 'matchSeason', 'fileName', 'schePath', 'schePath', 'sche_f']
    relsult = sql_util.select_table_rows('lq_schedule_crawler', keys, condition)
    if len(relsult) == 0:
        scheinfo = {}
        scheinfo['scheKey'] = scheKey
        scheinfo['leagueID'] = leagueID
        scheinfo['matchSeason'] = season
        scheinfo['fileName'] = filename
        scheinfo['schePath'] = filepath
        scheinfo['seaPath'] = seapath
        scheinfo['sche_f'] = flag
        sql_util.insertData('lq_scheTask', scheinfo)
    else:
        sql_util.upData('lq_schedule_crawler', {'sche_f': flag}, condition)


def upSeasonTask(filepath):
    # seasonInfo = get_seajsTag(filepath)
    context = utils.js2pyUtil.jsLocjs(filepath)
    seasondatas = context.arrSeason
    for data in seasondatas:
        stask = {}
        season = data[0]
        filename = os.path.basename(filepath)
        leagueID = filename.split('.')[0][3:]
        condition = {'leagueID': leagueID, 'matchSeason': season}
        keys = ['ID', 'leagueID', 'matchSeason', 'seasonPath', 'season_f']
        relsult = sql_util.select_table_rows('lq_season_crawler', keys, condition)
        stask['leagueID'] = leagueID
        stask['matchSeason'] = season
        stask['seasonPath'] = filename
        if len(relsult) > 0 and relsult[0][4] == 2:
            pass
        else:
            years = season.split('-')
            if len(years) == 0:
                finished = 2
            elif len(years) == 1 and int(years[0]) <= 2019:
                finished = 2
            elif len(years) == 2 and int(years[-1]) <= 2019:
                finished = 2
            else:
                finished = 1
            stask['season_f'] = finished

            if len(relsult) == 0:
                sql_util.insertData('lq_season_crawler', stask)
            elif finished == 2:
                sql_util.upData('lq_season_crawler', stask, condition)
            else:
                pass


def getFinishedTag(schepath):
    matchs = MatchJS.getMatchFromFile(schepath)
    sign = 2
    for match in matchs:
        if match['matchState'] not in [-1, -4]:
            sign = 1
            break
    return sign


def upScheTask(filepath):
    scheinfo = {}
    filename = os.path.basename(filepath)
    sclassId = filename.split('.')[0].split('_')[0][1:]
    season = os.path.dirname(filepath).split("/")[-1]
    seapath = lqconfig_qt.seajslocaldir + "sea" + sclassId + ".js"
    scheKey = sclassId + '#' + season + '#' + filename
    condition = {'scheKey': scheKey}
    keys = ['ID', 'scheKey', 'sclassID', 'matchSeason', 'fileName', 'schePath', 'schePath', 'sche_f']
    relsult = sql_util.select_table_rows('lq_schedule_crawler', keys, condition)
    if len(relsult) > 0 and relsult[0][7] == 2:
        pass
    else:
        finished = getFinishedTag(filepath)
        upScheTaskByFlag(filepath, finished)
