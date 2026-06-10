from utils import sql_util


class LqTotalOddsDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_totalodds', data, keys, isDict)

    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_rows('lq_totalodds', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_dicts('lq_totalodds', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        if isDict:
            return LqTotalOddsDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return LqTotalOddsDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            results = LqTotalOddsDao.select_rows([], condition)
            if len(results) > 0:
                sql_util.upData('lq_totalodds', data, condition)
            else:
                sql_util.insertData('lq_totalodds', data, keys, isDict)
        else:
            sql_util.upData('lq_totalodds', data, condition)

    @staticmethod
    def select(sql, isDict=False):
        results = sql_util.select(sql, isDict)
        return results
