#!/usr/bin/python3
import xml.etree.ElementTree as ET

import pymysql
from config.db_config import get_db_config


def main():
    # 读取XML文件，数组存储联赛基本信息
    tree = ET.parse(r'F:\比赛数据提供商\球探数据资料\篮球数据\联赛资料.xml')
    root = tree.getroot()
    leagues = []
    # 解析联赛资料XML文件，数组存储联赛信息
    for elem in root:
        league_data = []
        for elem1 in elem:
            league_data.append(elem1.text)
        leagues.append(tuple(league_data))
    # 打开数据库连接
    db = pymysql.connect(**get_db_config())
    # 使用cursor()方法获取操作游标
    cursor = db.cursor()
    try:
        sql = "insert into lq_sclass(leagueID, COLOR, NAME_SH, NAME_CN, NAME_TW, NAME_EN, SCLASSTYPE,CURRMATCHSEASON, " \
              "COUNTRYID,COUNTRY,CURRYEAR,CURRMONTH,SCLASSKIND,SCLASSTIME ) " \
              "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        # 执行sql语句
        for league in leagues:
            cursor.execute(sql, league)
        # 提交到数据库执行
        db.commit()
    except Exception as e:
        # 如果发生错误则回滚
        db.rollback()
        print(e)
    # 关闭数据库连接
    db.close()
    # 关闭数据库连接


if __name__ == '__main__':
    main()
