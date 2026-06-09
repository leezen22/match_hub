from utils import sql_util


class SeasonCrawDao(object):
    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_rows('lq_season_crawler', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_dicts('lq_season_crawler', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy='', ):
        if isDict:
            return SeasonCrawDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return SeasonCrawDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_season_crawler', data, keys, isDict)
