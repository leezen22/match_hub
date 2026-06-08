from pathlib import Path
import importlib.util
import os


DATABASES = {
    "default": {
        "host": "127.0.0.1",
        "user": "root",
        "passwd": "change-me",
        "port": 3306,
        "db": "xiaoqiu",
    },
    "local": {
        "host": "127.0.0.1",
        "user": "root",
        "passwd": "change-me",
        "port": 3306,
        "db": "xiaoqiu",
    },
    "ali": {
        "host": "example.mysql.rds.aliyuncs.com",
        "user": "change-me",
        "passwd": "change-me",
        "port": 3306,
        "db": "xiaoqiu",
    },
}

DEFAULT_DB_PROFILE = "default"
LOCAL_CONFIG_LOADED = False


def _load_local_config():
    global DATABASES, DEFAULT_DB_PROFILE, LOCAL_CONFIG_LOADED
    local_path = Path(__file__).with_name("db_config.local.py")
    if not local_path.exists():
        return

    spec = importlib.util.spec_from_file_location("match_hub_db_config_local", local_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "DATABASES"):
        DATABASES = module.DATABASES
        LOCAL_CONFIG_LOADED = True
    if hasattr(module, "DEFAULT_DB_PROFILE"):
        DEFAULT_DB_PROFILE = module.DEFAULT_DB_PROFILE


_load_local_config()


def get_db_config(profile=None):
    name = profile or os.getenv("MATCH_HUB_DB_PROFILE") or DEFAULT_DB_PROFILE
    if name not in DATABASES:
        raise KeyError("Database profile not found: {0}".format(name))
    return dict(DATABASES[name])


def local_config_path() -> Path:
    return Path(__file__).with_name("db_config.local.py")
