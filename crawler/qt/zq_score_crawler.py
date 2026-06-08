import datetime
import random
import time

import requests
from config import scrawler_config, common_config


class ScoreCrawler(object):
    def __init__(self, scheduleId, matchId=None):
        self.scheduleId = scheduleId
        self.matchId = matchId

    @property
    def qt_mobile_host(self):
        return scrawler_config.qt_mobile_host

    @property
    def qt_mobile_url(self):
        return "{0}/get?id={1}".format(scrawler_config.qt_zq_mobile_flash, self.scheduleId)

    @property
    def qt_mobile_refer(self):
        refer = "{0}/{1}.htm".format(scrawler_config.qt_lq_mobile_zhiBo_url, self.scheduleId)
        return refer

    @property
    def qt_web_host(self):
        return scrawler_config.qt_zq_live_host

    @property
    def qt_web_url(self):
        weburl = ''
        try:
            sd = str(self.scheduleId)
            weburl = "{0}/phone/txt/analysisheader/cn/{1}/{2}/{3}.txt".format(scrawler_config.qt_zq_web_livestatic,sd[0:1],sd[1:3],sd)
        except Exception as e:
            print(e)
        return weburl

    @property
    def qt_web_refer(self):
        refer = "{0}/{1}sb.htm".format(scrawler_config.qt_zq_web_livedetail, self.scheduleId)
        return refer

    def qt_mobile_get(self):
        headers = {"Host": self.qt_mobile_host,
                   "Referer": self.qt_mobile_refer,
                   "User-Agent": random.choice(common_config.mobile_agents),
                   }
        score = {}
        try:
            response = requests.get(self.qt_mobile_url, headers=headers)
            if response.status_code == 200 and len(response.text) > 0:
                score = {'ScheduleId': self.scheduleId, 'HomeScore': 0, 'GuestScore': 0, 'HomeHalf': 0, 'AwayHalf': 0}
                flashdata = response.text
                scoredata = flashdata.split('!')[0]
                arr = scoredata.split("^")
                score['HomeScore'] = int(arr[6])
                score['AwayScore'] = int(arr[7])
                if arr[15].strip() != '':
                    score['HomeHalf'] = int(arr[15])
                if arr[16].strip() != '':
                    score['AwayHalf'] = int(arr[16])
                score['MatchState'] = int(arr[8])
                if arr[10].strip() != '':
                    t2 = arr[10].split(",")
                    matchTime2 = datetime.datetime(int(t2[0]), int(t2[1]) + 1, int(t2[2]), int(t2[3]), int(t2[4]),
                                                   int(t2[5]))
                    score['MatchTime2'] = matchTime2
        except Exception as e:
            print(e)
        return score

    def qt_web_get(self):
        headers = {"Referer": self.qt_web_refer, "User-Agent": random.choice(common_config.web_agents)}
        score = {}
        try:
            response = requests.get(self.qt_web_url, headers=headers)
            if response.status_code == 200 and len(response.text) > 0:
                score = {'ScheduleId': self.scheduleId, 'HomeScore': 0, 'AwayScore': 0, 'HomeHalf': 0, 'AwayHalf': 0}
                txtdata = response.text
                arr = txtdata.split("^")
                score['MatchState'] = int(arr[4])
                score['HomeScore'] = int(arr[10])
                score['AwayScore'] = int(arr[11])
                if arr[26].strip() != '':
                    score['HomeHalf'] = int(arr[26])
                if arr[27].strip() != '':
                    score['AwayHalf'] = int(arr[27])
                # score['MatchState'] = int(arr[8])
                if arr[5].strip() != '':
                    # t2 = arr[25].split(",")
                    # matchTime2 = datetime.datetime(int(t2[0]), int(t2[1]) + 1, int(t2[2]), int(t2[3]), int(t2[4]), int(t2[5]))
                    matchTime2 = datetime.datetime.strptime(arr[5], "%Y%m%d%H%M%S")
                    score['MatchTime2'] = matchTime2

        except Exception as e:
            print("ScoreCrawler()")
            print(e)
        return score


    # def qt_web_get(self):
# if __name__ == '__main__':
#     scoreCrawler = ScoreCrawler(2501615)
#     score = scoreCrawler.qt_mobile_get()
#     print(score)
#     score = scoreCrawler.qt_web_get()
#     print(score)
    # sd = str(2513041)
