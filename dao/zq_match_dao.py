from utils import sql_util


class ZqMatchDao(object):
    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        result = sql_util.selectData('zq_schedule', keys, condition, isDis, isDict, orderBy)
        return result
