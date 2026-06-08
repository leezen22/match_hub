import os
from pathlib import Path

import utils.fileUtil
import utils.js2pyUtil
from utils import sql_util
from zq.extract import scheduleJs


def upSeasonState(filepath):
    context = utils.js2pyUtil.jsLocjs(filepath)
    seasons = context.arrSeason
    for season in seasons:
        stask = {}
        filename = os.path.basename(filepath)
        leagueId = filename.split('.')[0][3:]
        condition = {'leagueId': leagueId, 'matchSeason': season}
        keys = ['ID', 'leagueId', 'matchSeason', 'seasonPath', 'state']
        relsult = sql_util.select_table_rows('zq_seasonTask', keys, condition)
        stask['leagueId'] = leagueId
        stask['matchSeason'] = season
        stask['seasonPath'] = filepath
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
                sql_util.insertData('zq_seasonTask', stask)
            elif finished == 2:
                sql_util.upData('zq_seasonTask', stask, condition)
            else:
                pass


def upScheTaskByFlag(filepath, flag):
    filename = os.path.basename(filepath)
    leagueId = filename.split('.')[0].split('_')[0][1:]
    season = Path(filepath).parent.name
    seapath = "sea" + leagueId + ".js"
    scheKey = leagueId + '#' + season + '#' + filename
    condition = {'scheKey': scheKey}
    filepath2 = season + "\\" + filename
    keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'state']
    relsult = sql_util.select_table_rows('zq_scheTask', keys, condition)
    if len(relsult) == 0:
        scheinfo = {}
        scheinfo['scheKey'] = scheKey
        scheinfo['leagueId'] = leagueId
        scheinfo['matchSeason'] = season
        scheinfo['fileName'] = filename
        scheinfo['schePath'] = filepath2
        scheinfo['seaPath'] = seapath
        scheinfo['state'] = flag
        sql_util.insertData('zq_scheTask', scheinfo)
    else:
        sql_util.upData('zq_scheTask', {'state': flag}, condition)


def getFileSate(filepath):
    filedata = scheduleJs.getSche(filepath)
    matchs = filedata[1]
    status = filedata[0]
    if status == 'fail':
        sign = 0
        print("状态异常：" + filepath)
    else:
        sign = 2
        for match in matchs:
            if match['MatchState'] not in [-1, -10]:
                sign = 1
                return sign
    return sign
