
# 通过sql语句完成查询，isdict True 返回字典数据
import pymysql
from config.db_config import get_db_config
from pymysql.converters import escape_string

DB_PROFILE = "local"


def _connect(connect_timeout=None):
    config = get_db_config(DB_PROFILE)
    if connect_timeout is not None:
        config["connect_timeout"] = connect_timeout
    return pymysql.connect(**config)


def select(sql, isdict=False):
    results = select_Execute(sql, isdict)
    return results


def select_rows(sql):
    return select_Execute(sql, isdict=False)


def select_dicts(sql):
    return select_Execute(sql, isdict=True)


def select_table_rows(table, keys, condition, isDis=False, orderBy=''):
    return selectData(table, keys, condition, isDis=isDis, isdict=False, orderBy=orderBy)


def select_table_dicts(table, keys, condition, isDis=False, orderBy=''):
    return selectData(table, keys, condition, isDis=isDis, isdict=True, orderBy=orderBy)


def insetMany(table, keys, datas):
    result = False
    try:
        values = []
        for i in range(0, len(keys)):
            values.append('%s')
        # 打开数据库连接
        db = _connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()
        sql = "INSERT INTO " + table + "(" + ",".join(keys) + ") VALUES (" + ",".join(values) + ")"
        cursor.executemany(sql, datas)
        db.commit()
    except Exception as e:
        db.rollback()
        print(table, sql)
        print(e)
    else:
        db.close()
        result = True
    return result


# 插入数据，table 表名，datalist：元数据是字典的list
def insertData(table, data, keys=None, isDict=True):
    finished = False
    try:
        if isDict:
            inSql = get_i_sql(table, data)
        else:
            inSql = " INSERT INTO {0} ({1}) VALUES ({2}) ".format(table, ",".join(keys),
                                                                  ",".join(list_2_values(data)))
        sqlExecute(inSql)
    except Exception as e:
        print(e)
    else:
        finished = True
    return finished

def insertDatas(table, datas):
    finished = False
    try:
        # 打开数据库连接
        db = reConndb()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()
        for data in datas:
            insql = get_i_sql(table, data)
            cursor.execute(insql)
        db.commit()
    except Exception as e:
        db.rollback()
        print(e)
    else:
        db.close()
        finished = True
    return finished

# 单条更新
def upData(table, data, condition):
    try:
        upsql = get_u_sql(table, data, condition)
        sqlExecute(upsql)
    except Exception as e:
        print(e)
    else:
        pass


# 查找数据
def selectData(table, keys, condition, isDis=False, isdict=False, orderBy=''):
    sql = get_s_sql(table, keys, condition, isdistinct=isDis)
    if orderBy != '':
        sql = sql + " " + orderBy
    results = select_Execute(sql, isdict)
    return results


# 批量更新数据
def updateData(table, datalist, conditionList):
    counts = len(datalist)
    if counts > 0:
        for i in range(counts):
            upsql = get_u_sql(table, datalist[i], conditionList[i])
            sqlExecute(upsql)
    else:
        pass


# 删除数据
def delData(table, condition):
    delSql = get_d_sql(table, condition)
    sqlExecute(delSql)


def sqlExecute(sql):
    # 打开数据库连接
    db = _connect()
    # 使用cursor()方法获取操作游标
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        # 如果发生错误则回滚
        db.rollback()
        print(sql)
        print(e)
    # 关闭数据库连接
    db.close()
    # 关闭数据库连接


def select_Execute(sql, isdict=False):
    results = []
    try:
        db = reConndb()
        if db:
            # 使用cursor()方法获取操作游标
            if isdict:
                cursor = db.cursor(pymysql.cursors.DictCursor)
            else:
                cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            db.close()
    except Exception as e:
        db.close()
        print(sql)
        print(e)
    return results


def reConndb():
    # 数据库连接重试功能和连接超时功能的DB连接
    conn_status = True
    max_retries_count = 10  # 设置最大重试次数
    conn_retries_count = 0  # 初始重试次数
    conn_timeout = 5  # 连接超时时间为5秒

    while conn_status and conn_retries_count <= max_retries_count:
        try:
            conn = _connect(connect_timeout=conn_timeout)
            _conn_status = False
            # 如果conn成功则_status为设置为False则退出循环，返回db连接对象
            return conn
        except Exception as e:
            conn_retries_count += 1
            if conn_retries_count == 10:
                print(e)
                print("数据库连接异常，已超过最大重试次数")
    return None


def safe(s):
    return escape_string(s)


# 表/字典数据 拼接SQL插入语句
def get_i_sql(table, dict):
    sql = 'insert into %s set ' % table
    sql += dict_2_str(dict)
    return sql


# 表/list/formate/ 查询表数据
def get_s_sql(table, keys, conditions, isdistinct=False):
    if isdistinct:
        sql = 'select distinct %s ' % ",".join(keys)
    else:
        if len(keys) == 0:
            sql ='select  * '
        else:
            sql = 'select  %s ' % ",".join(keys)
    sql += ' from %s ' % table
    if conditions:
        sql += ' where %s ' % dict_2_str_and(conditions)
    return sql

# 表/更新字段/查询条件 更新表数据
def get_u_sql(table, value, conditions):
    '''
    生成update的sql语句
    @table，查询记录的表名
    @value，formate,需要更新的字段
    @conditions,插入的数据，字典
    '''
    sql = 'update %s set ' % table
    sql += dict_2_str(value)
    if conditions:
        sql += ' where %s ' % dict_2_str_and(conditions)
    return sql

# 表/查询条件 输出表数据
def get_d_sql(table, condition):
    '''
        生成detele的sql语句
    @table，查询记录的表名
    @conditions,插入的数据，字典
    '''
    sql = 'delete from  %s  ' % table
    if condition:
        sql += ' where %s ' % dict_2_str_and(condition)
    return sql


# 字典数据转换
def dict_2_str(dictin):
    '''
    将字典变成，key='value',key='value' 的形式
    '''
    tmplist = []
    for k, v in dictin.items():
        if isinstance(v, int) or isinstance(v, float):
            tmp = "%s=%s" % (str(k), v)
        else:
            tmp = "%s='%s'" % (str(k), safe(str(v)))
        tmplist.append(' ' + tmp + ' ')
    return ','.join(tmplist)

# 字典数据转换and
def dict_2_str_and(dictin):
    '''
    将字典变成，key='value' and key='value'的形式
    '''
    tmplist = []
    for k, v in dictin.items():
        if isinstance(v, int) or isinstance(v, float):
            tmp = "%s=%s" % (str(k), v)
        else:
            tmp = "%s='%s'" % (str(k), safe(str(v)))
        tmplist.append(' ' + tmp + ' ')
    return ' and '.join(tmplist)


def list_2_values(data):
    values = []
    for item in data:
        if isinstance(item, int) or isinstance(item, float):
            tmp = str(item)
        else:
            tmp = "'" + str(item) + "'"
        values.append(tmp)
    return values
# def insertdatas(table, datas):
#     try:
#         # 打开数据库连接
#         db = _connect()
#         # 使用cursor()方法获取操作游标
#         cursor = db.cursor()
#         for data in datas:
#             insql = get_i_sql(table, data)
#             cursor.execute(insql)
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         print(e)
#     else:
#         db.close()

