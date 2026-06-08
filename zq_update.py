from config import zqconfig_qt
from utils import sql_util, fileUtil
from zq.service.asian_odds import AsianOddsZq
from zq.service.schedule import upSchedule, upMatchScore
from zq.service.schedulejs import upScheJS, upScheJS_local
from zq.service.total_odds import TotalOddsZq
from zq.service.zq_st_goals import TotalStZq
from zq.service.zq_up_odds import upAsianTotalDetails


def _pending_schedule_files():
    files = []
    for path in [zqconfig_qt.schedule_js_work_dir] + [
        zqconfig_qt.schejs_pending + subdir for subdir in zqconfig_qt.schedule_js_legacy_pending_dirs
    ]:
        import os
        if os.path.isdir(path):
            files.extend(fileUtil.dirFiles(path, []))
    return files

if __name__ == '__main__':
    upScheJS()
    upScheJS_local()
    while 1:
        upSchedule()
        files = _pending_schedule_files()
        if len(files)<5:
            print(files)
        if len(files) == 0:
            break
    upMatchScore()
    TotalOddsZq.up_odds_mobile('2026-05-05 00:00:00')
    AsianOddsZq.up_odds_mobile('2026-05-05 00:00:00')
    upAsianTotalDetails(3, '2026-05-05 00:00:00')
    TotalOddsZq.update_halfgoals('2026-05-05 00:00:00')

    # TotalStZq.update_half_st('2026-04-20 00:00:00')
    # TotalStZq.update_st('2026-04-20 00:00:00')
    # TotalStZq.judgeHit()


