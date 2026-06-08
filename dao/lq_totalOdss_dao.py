from utils import sql_util
from typing import Any, Dict, Literal, Tuple, overload

Row = Tuple[Any, ...]
DictRow = Dict[str, Any]


class LqTotalOddsDao(object):
    @staticmethod
    def insert(data, keys=None, isDict=True):
        sql_util.insertData('lq_totalodds', data, keys, isDict)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy='') -> Any:
        data = sql_util.selectData('lq_totalodds', keys, condition, isDis, isDict, orderBy)
        return data

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            results = sql_util.selectData('lq_totalodds', [], condition)
            if len(results) > 0:
                sql_util.upData('lq_totalodds', data, condition)
            else:
                sql_util.insertData('lq_totalodds', data, keys, isDict)
        else:
            sql_util.upData('lq_totalodds', data, condition)

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
