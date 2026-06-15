import os
from pathlib import Path

import utils.fileUtil
import utils.js2pyUtil
from config import lqconfig_qt
from lq.extract import MatchJS
from utils import sql_util


def upScheTaskByFlag(filepath, flag):
    filename = os.path.basename(filepath)
    leagueId = filename.split('.')[0].split('_')[0][1:]
    season = Path(filepath).parent.name
    seapath = lqconfig_qt.seajslocaldir + "sea" + leagueId + ".js"
    scheKey = leagueId + '#' + season + '#' + filename
    condition = {'scheKey': scheKey}
    keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'state']
    relsult = sql_util.select_table_rows('lq_schedule_crawler', keys, condition)
    if len(relsult) == 0:
        scheinfo = {}
        scheinfo['scheKey'] = scheKey
        scheinfo['leagueId'] = leagueId
        scheinfo['matchSeason'] = season
        scheinfo['fileName'] = filename
        scheinfo['schePath'] = filepath
        scheinfo['seaPath'] = seapath
        scheinfo['state'] = flag
        sql_util.insertData('lq_schedule_crawler', scheinfo)
    else:
        sql_util.upData('lq_schedule_crawler', {'state': flag}, condition)


def upSeasonTask(filepath):
    # seasonInfo = get_seajsTag(filepath)
    context = utils.js2pyUtil.jsLocjs(filepath)
    seasonArr = context.arrSeason
    for data in seasonArr:
        stask = {}
        season = data[0]
        filename = os.path.basename(filepath)
        leagueId = filename.split('.')[0][3:]
        condition = {'leagueId': leagueId, 'matchSeason': season}
        keys = ['ID', 'leagueId', 'matchSeason', 'seasonPath', 'state']
        relsult = sql_util.select_table_rows('lq_season_crawler', keys, condition)
        stask['leagueId'] = leagueId
        stask['matchSeason'] = leagueId
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
            stask['state'] = finished

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
        if match['MatchState'] not in [-1, -4]:
            sign = 1
            break
    return sign


def upScheTask(filepath):
    scheinfo = {}
    filename = os.path.basename(filepath)
    sclassId = filename.split('.')[0].split('_')[0][1:]
    season = Path(filepath).parent.name
    seapath = lqconfig_qt.seajslocaldir + "sea" + sclassId + ".js"
    scheKey = sclassId + '#' + season + '#' + filename
    condition = {'scheKey': scheKey}
    keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'state']
    relsult = sql_util.select_table_rows('lq_schedule_crawler', keys, condition)
    if len(relsult) > 0 and relsult[0][7] == 2:
        pass
    else:
        finished = getFinishedTag(filepath)
        upScheTaskByFlag(filepath, finished)
