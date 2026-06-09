from utils import sql_util


class LqEuropeOddsDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_europe', data, keys, isDict)

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            results = sql_util.select_table_rows('lq_europe', [], condition)
            # 比赛已入库
            if len(results) > 0:
                sql_util.upData('lq_europe', data, condition)
            else:
                sql_util.insertData('lq_europe', data, keys, isDict)
        else:
            sql_util.upData('lq_europe', data, condition)

    @staticmethod
    def select(sql, isDict=False):
        results = sql_util.select(sql, isDict)
        return results
