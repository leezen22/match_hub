from utils import sql_util


class LqNoteDao(object):

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy=''):
        result = sql_util.selectData('lq_note', keys, condition, isDis, isDict, orderBy)
        return result

    @staticmethod
    def update(data, condition):
        sql_util.upData("lq_note", data, condition)
