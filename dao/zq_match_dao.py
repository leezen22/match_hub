from utils import sql_util


class ZqMatchDao(object):
    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_rows('zq_schedule', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_dicts('zq_schedule', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        if isDict:
            return ZqMatchDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return ZqMatchDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)
