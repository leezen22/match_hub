import os

from config import scrawler_config
from utils import sql_util


class ScheduleCrawDao(object):
    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_rows('lq_schedule_crawler', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_dicts('lq_schedule_crawler', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        if isDict:
            return ScheduleCrawDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return ScheduleCrawDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_schedule_crawler', data, keys, isDict)

    @staticmethod
    def upScheCrawByFlag(filepath, flag):
        filename = os.path.basename(filepath)
        leagueId = filename.split('.')[0].split('_')[0][1:]
        season = os.path.dirname(filepath).split("/")[-1]
        seasonPath = "{0}/sea{1}.js".format(scrawler_config.lq_seasonJS_local_dir, leagueId)
        scheKey = leagueId + '#' + season + '#' + filename
        condition = {'scheKey': scheKey}
        keys = ['ID', 'scheKey', 'leagueId', 'matchSeason', 'fileName', 'schePath', 'schePath', 'sche_f']
        relsult = ScheduleCrawDao.select_rows(keys, condition)
        if len(relsult) == 0:
            scheInfo = {'scheKey': scheKey, 'leagueId': leagueId, 'matchSeason': season, 'fileName': filename,
                        'schePath': filepath, 'seaPath': seasonPath, 'sche_f': flag}
            sql_util.insertData('lq_schedule_crawler', scheInfo)
        else:
            sql_util.upData('lq_schedule_crawler', {'sche_f': flag}, condition)


# if __name__ == '__main__':
#     pass
    # sql_util.insertData('cookie', ['uqioowowowornrjrrmmm'], ['cookie'], isDict=False)
