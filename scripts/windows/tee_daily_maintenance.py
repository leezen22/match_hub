"""Show maintenance output in the console and keep bounded log files."""

import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config import common_config
from scripts.daily_maintenance import main


class TeeStream:
    def __init__(self, console, path):
        self.console = console
        self.lock = threading.Lock()
        self.handler = RotatingFileHandler(
            path,
            maxBytes=common_config.LOG_MAX_BYTES,
            backupCount=common_config.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )

    def write(self, value):
        if not value:
            return 0
        with self.lock:
            self.console.write(value)
            self.console.flush()
            if self.handler.maxBytes > 0 and self.handler.stream.tell() + len(value.encode("utf-8")) > self.handler.maxBytes:
                self.handler.doRollover()
            self.handler.stream.write(value)
            self.handler.flush()
        return len(value)

    def flush(self):
        with self.lock:
            self.console.flush()
            self.handler.flush()

    @property
    def encoding(self):
        return self.console.encoding

    def isatty(self):
        return self.console.isatty()

    def close(self):
        self.handler.close()


if __name__ == "__main__":
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout = TeeStream(stdout, log_dir / "daily_maintenance.out.log")
    sys.stderr = TeeStream(stderr, log_dir / "daily_maintenance.err.log")
    try:
        exit_code = main()
    except BaseException:
        traceback.print_exc(file=sys.stderr)
        exit_code = 1
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout, sys.stderr = stdout, stderr
    raise SystemExit(exit_code)
