from utils import sql_util
from typing import Any, Dict, Literal, Tuple, overload

Row = Tuple[Any, ...]
DictRow = Dict[str, Any]


class LqAsianOddsDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_AsianOdds', data, keys, isDict)

    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy='') -> Tuple[Row, ...]:
        return sql_util.select_table_rows('lq_AsianOdds', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy='') -> Tuple[DictRow, ...]:
        return sql_util.select_table_dicts('lq_AsianOdds', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy='') -> Any:
        if isDict:
            return LqAsianOddsDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return LqAsianOddsDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            results = LqAsianOddsDao.select_rows([], condition)
            # 比赛已入库
            if len(results) > 0:
                sql_util.upData('lq_AsianOdds', data, condition)
            else:
                sql_util.insertData('lq_AsianOdds', data, keys, isDict)
        else:
            sql_util.upData('lq_AsianOdds', data, condition)

    @staticmethod
    @overload
    def select(sql: str, isDict: Literal[False] = False) -> Tuple[Row, ...]:
        ...

    @staticmethod
    @overload
    def select(sql: str, isDict: Literal[True]) -> Tuple[DictRow, ...]:
        ...

    @staticmethod
    def select(sql, isDict=False):
        results = sql_util.select(sql, isDict)
        return results
