from utils import sql_util


class LqEurDetailDao(object):
    @staticmethod
    def insert(companyId, data, keys=None, isDict=True, isPre=True):
        if isPre:
            tableName = "lq_europe_pre_{0}".format(companyId)
        else:
            tableName = "lq_europe_gun_{0}".format(companyId)
        sql_util.insertData(tableName, data, keys, isDict)

    @staticmethod
    def insertMany(companyId, data, keys=None, isDict=True, isPre=True):
        if isPre:
            tableName = "lq_europe_pre_{0}".format(companyId)
        else:
            tableName = "lq_europe_gun_{0}".format(companyId)
        sql_util.insetMany(tableName, keys, data)

    @staticmethod
    def update(companyId, data, condition, keys=None, isDict=True, judge=False, isPre=True):
        if isPre:
            tableName = "lq_europe_pre_{0}".format(companyId)
        else:
            tableName = "lq_europe_gun_{0}".format(companyId)
        if judge:
            results = sql_util.select_table_rows(tableName, [], condition)
            # 比赛已入库
            if len(results) > 0:
                sql_util.upData(tableName, data, condition)
            else:
                sql_util.insertData(tableName, data, keys, isDict)
        else:
            sql_util.upData(tableName, data, condition)

    @staticmethod
    def select(sql, isDict=False):
        results = sql_util.select(sql, isDict)
        return results
