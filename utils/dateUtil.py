import json
import time
from datetime import timedelta, datetime


def utc2local(utc_dtm):
    # UTC 时间转本地时间（ +8:00 ）
    # local_tm = datetime.fromtimestamp(0)
    # utc_tm = datetime.utcfromtimestamp(0)
    # offset = local_tm - utc_tm
    # # print(type(offset))
    # local_dtm = utc_dtm + offset
    local_dtm = utc_dtm + timedelta(hours=8)
    return local_dtm


def local2utc( local_dtm ):
    # 本地时间转 UTC 时间（ -8:00 ）
    utc_dtm = datetime.utcfromtimestamp(local_dtm.timestamp())
    return utc_dtm


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


def getNowTime():
    timeStr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return timeStr
