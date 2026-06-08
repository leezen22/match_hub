import os
import shutil
from config import common_config
from utils.dateUtil import getNowTime


# 按行记录日志
def logLine(file, logContent):
    logContent = str([getNowTime(), logContent]) + ', \n'
    fileWrite(file, "a+", logContent)


def fileWrite(filePath, model, content):
    result = False
    try:
        fileDir = os.path.dirname(filePath)
        while not os.path.exists(fileDir):
            os.makedirs(fileDir)
        fw = open(filePath, model, encoding="utf-8")
        fw.write(content)
        fw.close()
    except Exception as e:
        print(e)
    else:
        result = True
    return result


def dirFiles(sPath, filesList):
    if os.path.isdir(sPath):
        for sChild in os.listdir(sPath):
            sChildPath = os.path.join(sPath, sChild)
            if os.path.isdir(sChildPath):
                # 迭代
                dirFiles(sChildPath, filesList)
            else:
                filesList.append(sChildPath)
    else:
        filesList.append(sPath)
    return filesList


def copyfile(src, dest):
    dir = os.path.dirname(dest)
    while not os.path.exists(dir):
        os.makedirs(dir)
        break
    shutil.copy(src, dest)


def del_error_file(filepath):
    try:
        with open(filepath, 'r+', encoding="utf-8") as fo:
            content = fo.read()
            fo.close()
            if "对不起" in content or "访问频率" in content:
                print("文件异常删除：" + filepath)
                os.remove(filepath)
                return True
            else:
                return False
    except Exception as e:
        print(e)
        logLine(common_config.fileread_e, "'" + filepath + "'" + ",")
        return False
    else:
        return True