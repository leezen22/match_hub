import argparse
import os
import sys

from config import zqconfig_qt
from utils import fileUtil
from zq.service.asian_odds import AsianOddsZq
from zq.service.schedule import upSchedule, upMatchScore
from zq.service.schedulejs import upScheJS, upScheJS_local
from zq.service.total_odds import TotalOddsZq
from zq.service.zq_st_goals import TotalStZq
from zq.service.zq_up_odds import upAsianTotalDetails

DEFAULT_ODDS_START_TIME = '2026-05-05 00:00:00'


def _pending_schedule_files():
    files = []
    if os.path.isdir(zqconfig_qt.schedule_js_work_dir):
        files.extend(fileUtil.dirFiles(zqconfig_qt.schedule_js_work_dir, []))
    return files


def update_schedule_js():
    upScheJS()


def update_schedule_js_local():
    upScheJS_local()


def update_schedule():
    while 1:
        upSchedule()
        files = _pending_schedule_files()
        if len(files)<5:
            print(files)
        if len(files) == 0:
            break


def update_score():
    upMatchScore()


def update_odds(start_time=DEFAULT_ODDS_START_TIME):
    TotalOddsZq.up_odds_mobile(start_time)
    AsianOddsZq.up_odds_mobile(start_time)
    upAsianTotalDetails(3, start_time)
    TotalOddsZq.update_halfgoals(start_time)


def run_all(start_time=DEFAULT_ODDS_START_TIME):
    update_schedule_js()
    update_schedule()
    update_score()
    update_odds(start_time)


def main():
    parser = argparse.ArgumentParser(description="Run football update tasks.")
    parser.add_argument(
        "stage",
        nargs="?",
        default="all",
        choices=["all", "schedule-js", "schedule-js-local", "schedule", "score", "odds"],
        help="Task stage to run. Default: all.",
    )
    parser.add_argument(
        "--start-time",
        default=DEFAULT_ODDS_START_TIME,
        help="Start time for odds tasks.",
    )
    args = parser.parse_args()

    if args.stage == "all":
        run_all(args.start_time)
    elif args.stage == "schedule-js":
        update_schedule_js()
    elif args.stage == "schedule-js-local":
        update_schedule_js_local()
    elif args.stage == "schedule":
        update_schedule()
    elif args.stage == "score":
        update_score()
    elif args.stage == "odds":
        update_odds(args.start_time)

    # TotalStZq.update_half_st('2026-04-20 00:00:00')
    # TotalStZq.update_st('2026-04-20 00:00:00')
    # TotalStZq.judgeHit()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        update_schedule_js()
        update_schedule_js_local()
        update_schedule()
        update_score()
        update_odds(DEFAULT_ODDS_START_TIME)
        # TotalStZq.update_st('2026-04-20 00:00:00')
        # TotalStZq.judgeHit()
