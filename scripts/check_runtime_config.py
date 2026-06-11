import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.db_config import (
    DATABASES,
    ENV_CONFIG_LOADED,
    LOCAL_CONFIG_LOADED,
    env_config_path,
    get_db_config,
    local_config_path,
)


def _mask(value):
    text = str(value or "")
    if len(text) <= 2:
        return "*" * len(text)
    return text[:1] + "*" * (len(text) - 2) + text[-1:]


def main():
    env_path = env_config_path()
    legacy_path = local_config_path()
    print("Project:", PROJECT_ROOT)
    print("Local .env:", env_path)
    print("Local .env exists:", env_path.exists())
    print("Local .env loaded:", ENV_CONFIG_LOADED)
    print("Legacy DB config:", legacy_path)
    print("Legacy DB config exists:", legacy_path.exists())
    print("Legacy DB config loaded:", LOCAL_CONFIG_LOADED)
    print("Profiles:", ", ".join(sorted(DATABASES.keys())))

    for profile in sorted(DATABASES.keys()):
        try:
            config = get_db_config(profile)
        except Exception as e:
            print("{0}: not configured ({1})".format(profile, e))
            continue
        print(
            "{0}: host={1} port={2} db={3} user={4} passwd={5}".format(
                profile,
                _mask(config.get("host")),
                config.get("port"),
                _mask(config.get("db")),
                _mask(config.get("user")),
                _mask(config.get("passwd")),
            )
        )

    if not env_path.exists():
        print("WARNING: create .env from .env.sample before running updates.")

    print("")
    print("Default no-argument update tasks:")
    print("lq_update.py: schedule-js, schedule, score, odds, details")
    print("zq_update.py: schedule-js, schedule-js-local, schedule, score, odds")
    print("Use a stage argument to run only one task, for example: zq_update.py odds --start-time \"2026-05-05 00:00:00\"")


if __name__ == "__main__":
    main()
