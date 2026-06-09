from utils import sql_util


class LqPlayoffsDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_playoffs', data, keys, isDict)

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=True):
        if judge:
            result = sql_util.select_table_rows('lq_playoffs', [], condition)
            if len(result) > 0:
                sql_util.upData('lq_playoffs', data, condition)
            else:
                sql_util.insertData('lq_playoffs', data, keys, isDict)
        else:
            sql_util.upData('lq_playoffs', data, condition)
