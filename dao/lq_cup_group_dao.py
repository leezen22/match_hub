from utils import sql_util


class LqCupGroupDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_cup_group', data, keys, isDict)

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            result = sql_util.selectData('lq_cup_group', [], condition)
            if len(result) > 0:
                sql_util.upData('lq_cup_group', data, condition)
            else:
                sql_util.insertData('lq_cup_group', data, keys, isDict)
        else:
            sql_util.upData('lq_cup_group', data, condition)
