from utils import sql_util


class LqNoteDao(object):
    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_rows('lq_note', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy=''):
        return sql_util.select_table_dicts('lq_note', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        if isDict:
            return LqNoteDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return LqNoteDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def update(data, condition):
        sql_util.upData("lq_note", data, condition)
