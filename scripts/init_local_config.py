import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.db_config import local_config_path


def main():
    sample_path = PROJECT_ROOT / "config" / "db_config.sample.py"
    target_path = local_config_path()
    if target_path.exists():
        print("Local config already exists:", target_path)
        print("No changes made.")
        return
    shutil.copyfile(sample_path, target_path)
    print("Created local config:", target_path)
    print("Edit this file before running update tasks.")


if __name__ == "__main__":
    main()
