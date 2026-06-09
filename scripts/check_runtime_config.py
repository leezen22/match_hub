import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.db_config import DATABASES, LOCAL_CONFIG_LOADED, get_db_config, local_config_path


def _mask(value):
    text = str(value or "")
    if len(text) <= 2:
        return "*" * len(text)
    return text[:1] + "*" * (len(text) - 2) + text[-1:]


def main():
    path = local_config_path()
    print("Project:", PROJECT_ROOT)
    print("Local DB config:", path)
    print("Local DB config exists:", path.exists())
    print("Local DB config loaded:", LOCAL_CONFIG_LOADED)
    print("Profiles:", ", ".join(sorted(DATABASES.keys())))

    for profile in sorted(DATABASES.keys()):
        config = get_db_config(profile)
        print(
            "{0}: host={1} port={2} db={3} user={4} passwd={5}".format(
                profile,
                config.get("host"),
                config.get("port"),
                config.get("db"),
                config.get("user"),
                _mask(config.get("passwd")),
            )
        )

    if not path.exists():
        print("WARNING: create config/db_config.local.py from config/db_config.sample.py before running updates.")

    print("")
    print("Default no-argument update tasks:")
    print("lq_update.py: schedule-js, schedule, score, odds, details")
    print("zq_update.py: schedule-js, schedule-js-local, schedule, score, odds")
    print("Use a stage argument to run only one task, for example: zq_update.py odds --start-time \"2026-05-05 00:00:00\"")


if __name__ == "__main__":
    main()
