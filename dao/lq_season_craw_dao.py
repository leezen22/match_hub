from utils import sql_util


class SeasonCrawDao(object):

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy='', ):
        result = sql_util.selectData('lq_season_crawler', keys, condition, isDis, isDict, orderBy)
        return result

    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_season_crawler', data, keys, isDict)
