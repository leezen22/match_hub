import os
import threading
from zq.service.schedulejs import upLeagueScheJs, upLeagueScheByFile


class upLeaguejsThread(threading.Thread):
    # 继承父类threading.Thread
    def __init__(self, league, lastUpdate):
        threading.Thread.__init__(self)
        # self.threadID = threadID
        self.league = league
        self.lastUpdate = lastUpdate

    def run(self):  # 把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        upLeagueScheJs(self.league, self.lastUpdate)


# 更新指定赛程JS文件比赛
class upLeagueThread(threading.Thread):
    # 继承父类threading.Thread
    def __init__(self, filepath, old, lastUpdate):
        threading.Thread.__init__(self)
        # self.threadID = threadID
        self.filepath = filepath
        self.old = old
        self.lastUpdate = lastUpdate

    def run(self):  # 把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        isUpdated = upLeagueScheByFile(self.filepath, self.old, self.lastUpdate)
        if isUpdated:
            os.remove(self.filepath)
# if __name__ == '__main__':
#     upScheByfiles()
#     filepath= "E:\\sports\zuqiu\\pending\\matchResult\\new\\2024\\s136.js"
#     matchs = getSche(filepath)
#     print(matchs)