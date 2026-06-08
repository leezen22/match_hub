import datetime
from zq.service.schedulejs import upLeagueScheByFile

def upScheByfiles():
    filesArr = []
    lastUpdateTime = datetime.datetime.strptime("2024-02-28 10:02:58", "%Y-%m-%d %H:%M:%S")
    for item in filesArr:
        filepath = item[1][1]
        isExist = 1
        upLeagueScheByFile(filepath, isExist, lastUpdateTime)


if __name__ == '__main__':
    upScheByfiles()