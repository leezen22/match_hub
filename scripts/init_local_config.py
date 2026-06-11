import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    sample_path = PROJECT_ROOT / ".env.sample"
    target_path = PROJECT_ROOT / ".env"
    if target_path.exists():
        print("Local .env already exists:", target_path)
        print("No changes made.")
        return
    shutil.copyfile(sample_path, target_path)
    print("Created local .env:", target_path)
    print("Fill this file before running update tasks.")


if __name__ == "__main__":
    main()
