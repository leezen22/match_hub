from utils import sql_util
from typing import Any, Dict, Literal, Tuple, overload

Row = Tuple[Any, ...]
DictRow = Dict[str, Any]


class LqMatchDao(object):
    @staticmethod
    def select_rows(keys, condition, isDis=False, orderBy='') -> Tuple[Row, ...]:
        return sql_util.select_table_rows('lq_schedule', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def select_dicts(keys, condition, isDis=False, orderBy='') -> Tuple[DictRow, ...]:
        return sql_util.select_table_dicts('lq_schedule', keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    def selectData(keys, condition, isDis=False, isDict=False, orderBy='') -> Any:
        if isDict:
            return LqMatchDao.select_dicts(keys, condition, isDis=isDis, orderBy=orderBy)
        return LqMatchDao.select_rows(keys, condition, isDis=isDis, orderBy=orderBy)

    @staticmethod
    @overload
    def select(sql: str, isdict: Literal[False] = False) -> Tuple[Row, ...]:
        ...

    @staticmethod
    @overload
    def select(sql: str, isdict: Literal[True]) -> Tuple[DictRow, ...]:
        ...

    @staticmethod
    def select(sql, isdict=False):
        result = sql_util.select(sql, isdict)
        return result

    @staticmethod
    def update(data, condition, keys=None, isDict=True, judge=False):
        if judge:
            results = LqMatchDao.select_rows([], condition)
            # 比赛已入库
            if len(results) > 0:
                # 比赛完场或异常
                if data['matchState'] <= 0:
                    sql_util.upData('lq_schedule', data, condition)
                else:
                    pass
            else:
                sql_util.insertData('lq_schedule', data, keys, isDict)
        else:
            sql_util.upData('lq_schedule', data, condition)

    # @staticmethod
    # def judgeUpdate(match):
    #     results = sql_util.selectData('lq_schedule', ['scheduleId', 'matchState', 'matchTime'],
    #                                   {'scheduleId': match['scheduleId']})
    #     # 比赛已入库
    #     if len(results) > 0:
    #         condition = {'scheduleId': match['scheduleId']}
    #         # 比赛完场或异常
    #         if match['matchState'] < 0:
    #             sql_util.upData('lq_schedule', match, condition)
    #         else:
    #             pass
    #     else:
    #         sql_util.insertData('lq_schedule', match)


if __name__ == '__main__':
    # sql语句查询
    select_sql = "select matchID,matchTime from lq_schedule " \
                 "where leagueId={0} and matchSeason='{1}'".format(1, '19-20')
    result = sql_util.select(select_sql, True)
    print(result)
#     # # isdict=True 返回字典数据，
#     # result2 = sql_util.selectData("lq_schedule",
#     #                              ['matchID', 'matchTime'],
#     #                              {'leagueID': 1, 'matchSeason': '19-20'},
#     #                              isDis=False,
#     #                              isdict=True)
#     # print(result2)
#     # 插入json 格式数据，与字段一一对应
#     sql_util.insertData('lq_schedule',
#                         {'matchID': 18900, 'matchTime': '2019-08-01 17:00'},
#                         ['matchID', 'matchTime'], isDict=True)
#
#     # 插入数组 格式数据，与字段一一对应
#     sql_util.insertData('lq_schedule',
#                         {18900, '2019-08-01 17:00'},
#                         ['matchID', 'matchTime'], isDict=False)
#
#     # 更新数据,表名，set数据，条件
#     sql_util.upData('lq_schedule',
#                     {'updateTime': '2019-08-01 17:00'},
#                     {'matchID': 1788819})

# match_api = "http://127.0.0.1:8001/sports/lq/matchs?leagueId={0}".format(1)
# get_response = requests_get(match_api)
# print(get_response)
# sendCode_api = "http://192.168.1.103:8004/user/login/sendVerifyCode"
# data = {'mobile': '15715683869'}
# post_response = requests_post(sendCode_api, data=data)
# print(post_response)
# # string 转json
# data = json.loads(post_response['data'])
# print("code:{0}".format(data['code']))
