# -*- coding:utf-8 -*-
import datetime
import math

from config import ob_config
import json
import base64
import gzip
from io import BytesIO
import requests


class LqOBCrawler(object):

    @staticmethod
    def TournamentMatchesPB():
        matcheInfo = {}
        try:
            lc_param = {
                "apiType": 1,
                "cuid": "513587838747936485",
                "euid": "3020102",
                "orpt": "7",
                "pids": "",
                "sort": 1,
                "tid": "",
            }
            schedule_url = "{0}/{1}".format(ob_config.ob_api, "yewu11/v2/w/structureTournamentMatchesPB")
            res = requests.post(url= schedule_url, headers=ob_config.headers, data=json.dumps(lc_param))
            # print(res.text['msg'])
            resData = json.loads(res.text)
            # print(my_dict['data'])
            base64_data = resData['data']
            # # 首先，将Base64编码的数据解码成二进制数据
            binary_data = base64.b64decode(base64_data)
            # 使用gzip解压缩数据
            # gzip解压缩需要一个文件类对象，因此我们使用BytesIO将二进制数据转换为一个文件类对象
            with gzip.GzipFile(fileobj=BytesIO(binary_data), mode='rb') as file:
                decompressed_data = file.read()
            # 解压缩后的数据是二进制格式，根据需要转换或处理这些数据
            # 例如，如果你知道数据是字符串，可以解码它来获取原始文本
            decompressed_text = decompressed_data.decode('utf-8')
            matchesInfoRaw = json.loads(decompressed_text)
            liveArr = []
            noliveArr = []
            for item in matchesInfoRaw['livedata']:
                ScheduleID = item['mids']
                LeagueName = item['tn']
                LeagueID = item['tid']
                d = {'scheduleId':ScheduleID,'leagueName':LeagueName,'leagueId':LeagueID}
                liveArr.append(d)
            for item in matchesInfoRaw['nolivedata']:
                ScheduleID = item['mids']
                LeagueName = item['tn']
                LeagueID = item['tid']
                d = {'scheduleId': ScheduleID, 'leagueName': LeagueName, 'leagueId': LeagueID}
                noliveArr.append(d)
            matcheInfo = {'livedata': liveArr, 'nolivedata': noliveArr}
        except Exception as e:
            print(e)
        return matcheInfo

    @staticmethod
    def MatchBaseInfoByMidsPB(mArr):
        matchBaseInfo = {}
        mids = ','.join(str(i) for i in mArr)
        param = {
              "mids": mids,
              "cuid": "513587838747936485",
              "euid": "3020102",
              "orpt": "7",
              "sort": 1,
              "pids": "",
              "cos": 0}
        oddsInfo2PB_url = "{0}/{1}".format(ob_config.ob_api, "yewu11/v1/w/structureMatchBaseInfoByMidsPB")
        res = requests.post(url=oddsInfo2PB_url, headers=ob_config.headers, data=json.dumps(param))
        # print(res.text['msg'])
        resData = json.loads(res.text)
        # print(my_dict['data'])
        base64_data = resData['data']
        # print(oddsDict)
        # # 首先，将Base64编码的数据解码成二进制数据
        binary_data = base64.b64decode(base64_data)
        # 使用gzip解压缩数据
        # gzip解压缩需要一个文件类对象，因此我们使用BytesIO将二进制数据转换为一个文件类对象
        with gzip.GzipFile(fileobj=BytesIO(binary_data), mode='rb') as file:
            decompressed_data = file.read()
        # 解压缩后的数据是二进制格式，根据需要转换或处理这些数据
        # 例如，如果你知道数据是字符串，可以解码它来获取原始文本
        decompressed_text = decompressed_data.decode('utf-8')
        baseInfoDict = json.loads(decompressed_text)
        # print(baseInfoDict)
        baseInfoArr = []
        baseInfo = baseInfoDict['data']
        # print(baseInfo)
        for item in baseInfo:
            try:
                HomeTeam = item['mhn']
                AwayTeam = item['man']
                ScheduleID = item['mid']
                MatchTime = datetime.datetime.fromtimestamp(int(item['mgt']) // 1000).strftime('%Y-%m-%d %H:%M')
                asianOddsArr = []
                totalOddsArr = []

                asianOddsInfo = item['hpsData'][0]['hps'][1]['hl']
                if 'ol' in asianOddsInfo.keys():
                    HomeOdds = round(asianOddsInfo['ol'][0]['ov'] / 100000 - 1, 2)
                    Goal = float(asianOddsInfo['ol'][1]['onb'])
                    AwayOdds = round(asianOddsInfo['ol'][1]['ov'] / 100000 - 1, 2)
                    d = {'homeOdds': HomeOdds, 'goal': Goal, 'awayOdds': AwayOdds}
                    asianOddsArr.append(d)

                totalOddsInfo = item['hpsData'][0]['hps'][2]['hl']
                if 'ol' in totalOddsInfo.keys():
                    HighOdds = round(totalOddsInfo['ol'][0]['ov'] / 100000 - 1, 2)
                    Goal = float(totalOddsInfo['ol'][1]['onb'])
                    LowOdds = round(totalOddsInfo['ol'][1]['ov'] / 100000 - 1, 2)
                    d = {'highOdds': HighOdds, 'goal': Goal, 'lowOdds': LowOdds}
                    totalOddsArr.append(d)

                asianOddsInfo2 = item['hpsData'][0]['hpsAdd'][1]['hl']
                for i in range(0, len(asianOddsInfo2)):
                    od = asianOddsInfo2[i]
                    HomeOdds = round(od['ol'][0]['ov'] / 100000 - 1, 2)
                    Goal = float(od['ol'][1]['onb'])
                    AwayOdds = round(od['ol'][1]['ov'] / 100000 - 1, 2)
                    d = {'homeOdds': HomeOdds, 'goal': Goal, 'awayOdds': AwayOdds}
                    asianOddsArr.append(d)

                totalOddsInfo2 = item['hpsData'][0]['hpsAdd'][2]['hl']
                for i in range(0, len(totalOddsInfo2)):
                    od = totalOddsInfo2[i]
                    HighOdds = round(od['ol'][0]['ov'] / 100000 - 1, 2)
                    Goal = float(od['ol'][1]['onb'])
                    LowOdds = round(od['ol'][1]['ov'] / 100000 - 1, 2)
                    d = {'highOdds': HighOdds, 'goal': Goal, 'lowOdds': LowOdds}
                    totalOddsArr.append(d)

                odds = {'homeTeam': HomeTeam, 'awayTeam': AwayTeam, 'matchTime': MatchTime, 'scheduleId': ScheduleID,
                        'leagueName': item['tn'], 'leagueId': item['tid'],
                        'odds': {'asianOdds': asianOddsArr, 'totalOdds': totalOddsArr}}
                baseInfoArr.append(odds)
            except Exception as e:
                print(e)
            matchBaseInfo = {'status': 1, 'matches': baseInfoArr}
        return matchBaseInfo

    @staticmethod
    def getMatchOddsInfo2PB(scheduleId):
        oddsInfoDict = {}
        param = {
            "baseParam": {
                "cuid": "513587838747936485",
                "euid": "3020102",
                "orpt": "7",
                "sort": 1,
                "cos": 0,
                "pids": ""
            },
            "mcid": "0",
            "mid": scheduleId,
            "cuid": "513587838747936485"
        }
        oddsInfo2PB_url = "{0}/{1}".format(ob_config.ob_api, "yewu11/v1/w/matchDetail/getMatchOddsInfo2PB")
        try:
            res = requests.post(url=oddsInfo2PB_url, headers=ob_config.headers, data=json.dumps(param))
            # print(res.text['msg'])
            resData = json.loads(res.text)
            # print(my_dict['data'])
            base64_data = resData['data']
            # print(oddsDict)
            # # 首先，将Base64编码的数据解码成二进制数据
            binary_data = base64.b64decode(base64_data)
            # 使用gzip解压缩数据
            # gzip解压缩需要一个文件类对象，因此我们使用BytesIO将二进制数据转换为一个文件类对象
            with gzip.GzipFile(fileobj=BytesIO(binary_data), mode='rb') as file:
                decompressed_data = file.read()
            # 解压缩后的数据是二进制格式，根据需要转换或处理这些数据
            # 例如，如果你知道数据是字符串，可以解码它来获取原始文本
            decompressed_text = decompressed_data.decode('utf-8')
            oddsInfoDict = json.loads(decompressed_text)
            asianOddsArr = []
            asianOddsInfo = oddsInfoDict['plays'][0]['hl']
            for item in asianOddsInfo:
                HomeOdds = round(item['ol'][0]['obv']/100000 - 1, 2)
                Goal = float(item['ol'][1]['on'])
                AwayOdds = round(item['ol'][1]['obv']/100000 - 1, 2)
                d = {'homeOdds': HomeOdds, 'goal': Goal, 'awayOdds':AwayOdds }
                asianOddsArr.append(d)

            totalOddsInfo = oddsInfoDict['plays'][1]['hl']
            totalOddsArr = []
            for item in totalOddsInfo:
                HighOdds = round(item['ol'][0]['obv']/100000 - 1, 2)
                Goal = float(item['ol'][1]['on'])
                LowOdds = round(item['ol'][1]['obv']/100000 - 1, 2)
                d = {'highOdds': HighOdds, 'goal': Goal, 'lowOdds': LowOdds}
                totalOddsArr.append(d)
            oddsInfoDict = {'asianOdds': asianOddsArr, 'totalOdds': totalOddsArr}
        except Exception as e:
            pass
        return oddsInfoDict

    @staticmethod
    def MatchBaseInfoOB():
        matches = LqOBCrawler.TournamentMatchesPB()
        matchBaseInfo = []
        mArr = []
        for item in matches['livedata']:
            mArr.append(str(item['scheduleId']))
        # for item in matches['nolivedata']:
        #     mArr.append(str(item['scheduleId']))
        size = 30
        # print(len(mArr))
        p = math.ceil(len(mArr)/size)
        for i in range(0, p):
            start = i * size
            if (i + 1) * size <= len(mArr):
                end = (i + 1) * size
            else:
                end = len(mArr)
            # print("{0}:{1}".format(start,end))
            mArr_p = mArr[start:end]
            info = LqOBCrawler.MatchBaseInfoByMidsPB(mArr_p)
            # print(info)
            if 'matches' in info.keys():
                matchBaseInfo = matchBaseInfo + info['matches']
        return matchBaseInfo


# if __name__ == '__main__':
    # mArr = ["3342731"]
    # baseInfo = {'data': [{'mcid': '  ', 'tnjc': 'NBA', 'cos': False, 'csna': '篮球', 'tid': '132', 'mst': '0', 'srid': '1969657', 'mcg': 3, 'atf': '1', 'gcs': 0, 'mc': 29, 'mf': False, 'mgt': '1712098800000', 'maid': '14690', 'hpsPns': [{'hids': 1, 'hpid': '37', 'hpon': 3, 'hpn': '全场独赢', 'mid': '3317439', 'hmm': 0, 'hshow': 'Yes', 'hpnb': '全场独赢', 'hpt': 3, 'hsw': '1,4,5'}, {'hids': 1, 'hpid': '39', 'hpon': 1, 'hpn': '全场让分', 'mid': '3317439', 'hmm': 1, 'hshow': 'Yes', 'hpnb': '让分', 'hpt': 2, 'hsw': '1,2,3,4,5,6'}, {'hids': 1, 'hpid': '38', 'hpon': 2, 'hpn': '全场大小', 'mid': '3317439', 'hmm': 1, 'hshow': 'Yes', 'hpnb': '总分', 'hpt': 5, 'hsw': '1,2,3,4,5,6'}, {'hids': 1, 'hpid': '198', 'hpon': 4, 'hpn': '多伦多猛龙 总分', 'mid': '3317439', 'hmm': 1, 'hshow': 'Yes', 'hpnb': '球队总分', 'hpt': 5, 'hsw': '1,2,3,4,5,6'}, {'hids': 1, 'hpid': '199', 'hpon': 5, 'hpn': '洛杉矶湖人 总分', 'mid': '3317439', 'hmm': 1, 'hshow': 'Yes', 'hpnb': '球队总分', 'hpt': 5, 'hsw': '1,2,3,4,5,6'}], 'mct': 0, 'tlev': 1, 'mhlut': '', 'mo': 0, 'ctt': 0, 'mp': 1, 'csid': '2', 'ms': 0, 'mle': 7, 'lvs': -1, 'sort': 100, 'malu': ['group1/M00/00/3A/CgURt18ZA3KANxYHAAAUdf-7VMU913.png'], 'hpsData': [{'hps': [{'chpid': '37', 'hpid': '37', 'hl': {'hid': '147229253554734892', 'hs': 0, 'hmt': 1, 'ol': [{'oid': '143156151245735104', 'os': 1, 'otd': 225, 'ot': '1', 'ov': 610000, 'onb': '', 'on': '多伦多猛龙', 'onbl': '', 'cds': 'PA', 'ots': 'T1'}, {'oid': '142104131332758895', 'os': 1, 'otd': 226, 'ot': '2', 'ov': 111000, 'onb': '', 'on': '洛杉矶湖人', 'onbl': '', 'cds': 'PA', 'ots': 'T2'}]}}, {'chpid': '39', 'hpid': '39', 'hl': {'hid': '143481102558532417', 'hs': 0, 'hv': '12.5', 'hmt': 1, 'hn': 1, 'ol': [{'oid': '142316570544831137', 'os': 1, 'otd': 155, 'ot': '1', 'ov': 191000, 'onb': '+12.5', 'on': '+12.5', 'onbl': '', 'cds': 'PA', 'ots': 'T1'}, {'oid': '144653384358701010', 'os': 1, 'otd': 156, 'ot': '2', 'ov': 197000, 'onb': '-12.5', 'on': '-12.5', 'onbl': '', 'cds': 'PA', 'ots': 'T2'}]}}, {'chpid': '38', 'hpid': '38', 'hl': {'hid': '143151401513034911', 'hs': 0, 'hv': '231.5', 'hmt': 1, 'hn': 1, 'ol': [{'oid': '145460722537834836', 'os': 1, 'otd': 153, 'ot': 'Over', 'ov': 189000, 'onb': '231.5', 'on': '大 231.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '144334754965400415', 'os': 1, 'otd': 154, 'ot': 'Under', 'ov': 197000, 'onb': '231.5', 'on': '小 231.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}}, {'chpid': '198', 'hpid': '198', 'hl': {'hid': '144922512005353351', 'hs': 0, 'hv': '109.5', 'hmt': 1, 'hn': 1, 'ol': [{'oid': '145555605050975324', 'os': 1, 'otd': 617, 'ot': 'Over', 'ov': 186000, 'onb': '109.5', 'on': '大 109.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '145543634678429172', 'os': 1, 'otd': 618, 'ot': 'Under', 'ov': 186000, 'onb': '109.5', 'on': '小 109.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}}, {'chpid': '199', 'hpid': '199', 'hl': {'hid': '149408030204535481', 'hs': 0, 'hv': '122', 'hmt': 1, 'hn': 1, 'ol': [{'oid': '141103062917762233', 'os': 1, 'otd': 619, 'ot': 'Over', 'ov': 176000, 'onb': '122', 'on': '大 122', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '140174061575561328', 'os': 1, 'otd': 620, 'ot': 'Under', 'ov': 196000, 'onb': '122', 'on': '小 122', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}}], 'hpsAdd': [{'chpid': '37', 'hpid': '37', 'hlnm': 0, 'hl': []}, {'chpid': '39', 'hpid': '39', 'hlnm': 2, 'hl': [{'hid': '143004421441410413', 'hs': 0, 'hv': '11.5', 'hmt': 1, 'hn': 2, 'ol': [{'oid': '144600317561159830', 'os': 1, 'otd': 155, 'ot': '1', 'ov': 206000, 'onb': '+11.5', 'on': '+11.5', 'onbl': '', 'cds': 'PA', 'ots': 'T1'}, {'oid': '141507459414150556', 'os': 1, 'otd': 156, 'ot': '2', 'ov': 182000, 'onb': '-11.5', 'on': '-11.5', 'onbl': '', 'cds': 'PA', 'ots': 'T2'}]}, {'hid': '141555342930540013', 'hs': 0, 'hv': '13.5', 'hmt': 1, 'hn': 3, 'ol': [{'oid': '142377233550556420', 'os': 1, 'otd': 155, 'ot': '1', 'ov': 176000, 'onb': '+13.5', 'on': '+13.5', 'onbl': '', 'cds': 'PA', 'ots': 'T1'}, {'oid': '143230201162211250', 'os': 1, 'otd': 156, 'ot': '2', 'ov': 213000, 'onb': '-13.5', 'on': '-13.5', 'onbl': '', 'cds': 'PA', 'ots': 'T2'}]}]}, {'chpid': '38', 'hpid': '38', 'hlnm': 2, 'hl': [{'hid': '140845834116905206', 'hs': 0, 'hv': '232.5', 'hmt': 1, 'hn': 2, 'ol': [{'oid': '149105074957024684', 'os': 1, 'otd': 153, 'ot': 'Over', 'ov': 199000, 'onb': '232.5', 'on': '大 232.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '145232203434794893', 'os': 1, 'otd': 154, 'ot': 'Under', 'ov': 187000, 'onb': '232.5', 'on': '小 232.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}, {'hid': '145485737110370758', 'hs': 0, 'hv': '230.5', 'hmt': 1, 'hn': 3, 'ol': [{'oid': '149202172212901451', 'os': 1, 'otd': 153, 'ot': 'Over', 'ov': 179000, 'onb': '230.5', 'on': '大 230.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '149898436634746069', 'os': 1, 'otd': 154, 'ot': 'Under', 'ov': 207000, 'onb': '230.5', 'on': '小 230.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}]}, {'chpid': '198', 'hpid': '198', 'hlnm': 2, 'hl': [{'hid': '141925570144545314', 'hs': 0, 'hv': '110.5', 'hmt': 1, 'hn': 2, 'ol': [{'oid': '140632657719906324', 'os': 1, 'otd': 617, 'ot': 'Over', 'ov': 202000, 'onb': '110.5', 'on': '大 110.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '144246162458475032', 'os': 1, 'otd': 618, 'ot': 'Under', 'ov': 170000, 'onb': '110.5', 'on': '小 110.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}, {'hid': '141315747259455144', 'hs': 0, 'hv': '108.5', 'hmt': 1, 'hn': 3, 'ol': [{'oid': '148068765528071312', 'os': 1, 'otd': 617, 'ot': 'Over', 'ov': 170000, 'onb': '108.5', 'on': '大 108.5', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '147790491506541886', 'os': 1, 'otd': 618, 'ot': 'Under', 'ov': 202000, 'onb': '108.5', 'on': '小 108.5', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}]}, {'chpid': '199', 'hpid': '199', 'hlnm': 2, 'hl': [{'hid': '147232159473541436', 'hs': 0, 'hv': '123', 'hmt': 1, 'hn': 2, 'ol': [{'oid': '144270365222629136', 'os': 1, 'otd': 619, 'ot': 'Over', 'ov': 202000, 'onb': '123', 'on': '大 123', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '147110552253104702', 'os': 1, 'otd': 620, 'ot': 'Under', 'ov': 170000, 'onb': '123', 'on': '小 123', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}, {'hid': '147445313335924940', 'hs': 0, 'hv': '121', 'hmt': 1, 'hn': 3, 'ol': [{'oid': '141593900873144509', 'os': 1, 'otd': 619, 'ot': 'Over', 'ov': 170000, 'onb': '121', 'on': '大 121', 'onbl': '大 ', 'cds': 'PA', 'ots': 'T1'}, {'oid': '140253121411454592', 'os': 1, 'otd': 620, 'ot': 'Under', 'ov': 202000, 'onb': '121', 'on': '小 121', 'onbl': '小 ', 'cds': 'PA', 'ots': 'T2'}]}]}]}], 'lurl': 'group1/M00/0C/0A/CgURtWAvZRKAAP05AAAKcU1DEiA490.png', 'mprmc': 'PA', 'mhn': '多伦多猛龙', 'betAmount': '1223.32', 'cds': 'R01', 'frmhn': ['D'], 'operationTournamentSort': 6, 'mhs': 0, 'mlet': '12:00', 'hpsCorner': [], 'mhid': '18934', 'mrmc': '', 'mid': '3317439', 'mess': 1, 'mmp': '0', 'operationHotSortTop': 0, 'mms': 1, 'mbmty': 1, 'regionIdSort': 9, 'pmms': 0, 'mhlu': ['group1/M00/00/40/CgURtV8oGryANNuYAABxlQlkxcE014.png'], 'seid': '126149', 'malut': '', 'man': '洛杉矶湖人', 'frman': ['L'], 'mat': '', 'mng': 0, 'mststr': '0', 'mvs': -1, 'mearlys': 1, 'tf': False, 'th': 1, 'mfo': '', 'mft': 7, 'tn': 'NBA 美国职业篮球联赛', 'msc': []}], 'pagedata': {'liveCto': 0, 'cto': '0'}}
    # print(baseInfo)
    # matches = LqOBCrawler.TournamentMatchesPB()
    # print(matches)
    # oddsInfo = LqOBCrawler.getMatchOddsInfo2PB('3342731')
    # print(oddsInfo)
    # LqOBCrawler.MatchBaseInfoByMidsPB(mArr)
    # oddsInfo = LqOBCrawler.MatchBaseInfoOB()
    # print(oddsInfo)
#     scoreCrawler = ScoreCrawler(2501615)
#     score = scoreCrawler.qt_mobile_get()
#     print(score)
#     score = scoreCrawler.qt_web_get()
#     print(score)
    # sd = str(2513041)