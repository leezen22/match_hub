import os
import shutil
from config import common_config
from utils.dateUtil import getNowTime

def rotate_log_if_needed(file_path, max_bytes=None, backup_count=None):
    max_bytes = common_config.LOG_MAX_BYTES if max_bytes is None else max_bytes
    backup_count = common_config.LOG_BACKUP_COUNT if backup_count is None else backup_count
    if max_bytes <= 0 or backup_count < 1 or not os.path.exists(file_path):
        return
    if os.path.getsize(file_path) < max_bytes:
        return

    oldest = "{0}.{1}".format(file_path, backup_count)
    if os.path.exists(oldest):
        os.remove(oldest)
    for index in range(backup_count - 1, 0, -1):
        src = "{0}.{1}".format(file_path, index)
        dest = "{0}.{1}".format(file_path, index + 1)
        if os.path.exists(src):
            os.replace(src, dest)
    os.replace(file_path, "{0}.1".format(file_path))


# 按行记录日志
def logLine(file, logContent):
    logContent = str([getNowTime(), logContent]) + ', \n'
    rotate_log_if_needed(file)
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