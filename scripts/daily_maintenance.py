#!/usr/bin/env python3
"""Daily Match Hub maintenance entrypoint.

The service is intentionally generic. It currently runs only the Basketball
schedule discovery/parse flow:

1. update_schedule_js_active(all_leagues=True, season_count=3)
2. update_schedule()

It is safe to run from launchd/cron/Task Scheduler. A local lock prevents
overlapping runs, and a state file prevents duplicate successful runs within
the configured interval.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = PROJECT_ROOT / "data" / "locks"
LOCK_PATH = LOCK_DIR / "daily_maintenance.lock"
STATE_DIR = PROJECT_ROOT / "data" / "state"
STATE_PATH = STATE_DIR / "daily_maintenance.json"
DEFAULT_MIN_INTERVAL_HOURS = 24


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print("{0} daily maintenance state ignored: {1}".format(_timestamp(), repr(exc)))
        return {}


def _write_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(STATE_PATH)


def _should_skip_for_interval(state, min_interval_hours):
    last_success_at = _parse_timestamp(state.get("last_success_at"))
    if last_success_at is None:
        return False, None
    elapsed_hours = (datetime.now() - last_success_at).total_seconds() / 3600
    if elapsed_hours < float(min_interval_hours):
        return True, elapsed_hours
    return False, elapsed_hours


def _run_step(name, callback):
    started_at = datetime.now()
    print("{0} daily maintenance step started: {1}".format(_timestamp(), name))
    try:
        callback()
    except Exception as exc:
        detail = traceback.format_exc()
        print("{0} daily maintenance step failed: {1}, error={2}".format(_timestamp(), name, repr(exc)))
        print(detail)
        return {
            "name": name,
            "ok": False,
            "started_at": started_at.isoformat(timespec="seconds"),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "error": repr(exc),
        }
    print("{0} daily maintenance step finished: {1}".format(_timestamp(), name))
    return {
        "name": name,
        "ok": True,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


class _RunLock:
    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def __enter__(self):
        self.file = self.path.open("w")
        self.file.write("0")
        self.file.flush()
        self.file.seek(0)
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.file.close()
                self.file = None
                return False
        else:
            import fcntl

            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.file.close()
                self.file = None
                return False
        return True

    def __exit__(self, exc_type, exc, tb):
        if self.file is None:
            return
        if sys.platform == "win32":
            import msvcrt

            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        self.file.close()


def _parse_args():
    parser = argparse.ArgumentParser(description="Run daily Match Hub maintenance safely.")
    parser.add_argument(
        "--min-interval-hours",
        type=float,
        default=DEFAULT_MIN_INTERVAL_HOURS,
        help="Skip when the previous successful run is newer than this many hours. Default: 24.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even when the previous successful run is within the minimum interval.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sys.path.insert(0, str(PROJECT_ROOT))
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    with _RunLock(LOCK_PATH) as locked:
        if not locked:
            print("{0} daily maintenance skipped: previous run still active".format(_timestamp()))
            return 0

        state = _load_state()
        should_skip, elapsed_hours = _should_skip_for_interval(state, args.min_interval_hours)
        if should_skip and not args.force:
            print(
                "{0} daily maintenance skipped: last success {1:.2f} hours ago, min interval={2}".format(
                    _timestamp(),
                    elapsed_hours,
                    args.min_interval_hours,
                )
            )
            state["last_skip_at"] = datetime.now().isoformat(timespec="seconds")
            state["last_skip_reason"] = "min_interval"
            _write_state(state)
            return 0

        print("{0} daily maintenance started".format(_timestamp()))
        from lq_update import update_schedule, update_schedule_js_active

        tasks = [
            (
                "basketball.update_schedule_js_active",
                lambda: update_schedule_js_active(all_leagues=True, season_count=3),
            ),
            ("basketball.update_schedule", update_schedule),
        ]
        steps = [_run_step(name, callback) for name, callback in tasks]
        ok = all(step["ok"] for step in steps)
        state.update({
            "last_attempt_at": datetime.now().isoformat(timespec="seconds"),
            "last_result": "success" if ok else "failed",
            "steps": steps,
        })
        if ok:
            state["last_success_at"] = datetime.now().isoformat(timespec="seconds")
        _write_state(state)

        if not ok:
            print("{0} daily maintenance failed".format(_timestamp()))
            return 1

        print("{0} daily maintenance finished".format(_timestamp()))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
