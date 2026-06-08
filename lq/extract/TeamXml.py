#!/usr/bin/python3
import xml.etree.ElementTree as ET

import pymysql
from config.db_config import get_db_config

# 读取XML文件，数组存储联赛基本信息
tree = ET.parse('E:/人工采集/球队数据/team20191017.xml')
root = tree.getroot()
team_list = []
# 解析联赛资料XML文件，数组存储联赛信息
for elem in root:
    teamdata = []
    for elem1 in elem:
        teamdata.append(elem1.text)
    team_list.append(tuple(teamdata))
# print(team_list)
# 打开数据库连接
db = pymysql.connect(**get_db_config())
# 使用cursor()方法获取操作游标
cursor = db.cursor()
try:
    sql = "INSERT INTO lq_team(ID, SCLASSID, NAME_JS, NAME_J, NAME_F, NAME_E, FLAG, " \
          "LOCATIONID, MATCHADDRID, URL, CITY, Gymnasium, Capacity, JOINYEAR, FIRSTTIME, Drillmaster) " \
          "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    # 执行sql语句
    for team in team_list:
        # teamID= list(team)[0]
        # print(teamID)
        cursor.execute(sql, team)
    # 提交到数据库执行
    db.commit()
except Exception as e:
    # 如果发生错误则回滚
    db.rollback()
    print(e)
# 关闭数据库连接
db.close()
# 关闭数据库连接
