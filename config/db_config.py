from pathlib import Path
import importlib.util
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

DATABASES = {
    "default": {
        "host": "",
        "user": "",
        "passwd": "",
        "port": "",
        "db": "",
    },
    "local": {
        "host": "",
        "user": "",
        "passwd": "",
        "port": "",
        "db": "",
    },
    "ali": {
        "host": "",
        "user": "",
        "passwd": "",
        "port": "",
        "db": "",
    },
}

DEFAULT_DB_PROFILE = "default"
LOCAL_CONFIG_LOADED = False
ENV_CONFIG_LOADED = False

_DB_ENV_FIELDS = {
    "host": "HOST",
    "user": "USER",
    "passwd": "PASSWORD",
    "port": "PORT",
    "db": "NAME",
}


def _strip_env_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def _load_env_file(path=ENV_PATH):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _strip_env_value(value))


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


def _env_key(profile, field):
    return "MATCH_HUB_DB_{0}_{1}".format(profile.upper(), _DB_ENV_FIELDS[field])


def _apply_env_config():
    global DEFAULT_DB_PROFILE, ENV_CONFIG_LOADED
    if os.getenv("MATCH_HUB_DB_PROFILE"):
        DEFAULT_DB_PROFILE = os.getenv("MATCH_HUB_DB_PROFILE")
        ENV_CONFIG_LOADED = True

    for profile, values in DATABASES.items():
        for field in _DB_ENV_FIELDS:
            value = os.getenv(_env_key(profile, field))
            if value is None:
                continue
            if field == "port" and value != "":
                values[field] = int(value)
            else:
                values[field] = value
            ENV_CONFIG_LOADED = True


def _validate_config(profile, config):
    missing = [key for key in ("host", "user", "passwd", "db") if not config.get(key)]
    if missing:
        raise ValueError(
            "Database profile {0} missing required config fields: {1}".format(
                profile, ", ".join(missing)
            )
        )
    if config.get("port") in ("", None):
        raise ValueError("Database profile {0} missing required config field: port".format(profile))


_load_env_file()
_load_local_config()
_apply_env_config()


def get_db_config(profile=None):
    name = profile or os.getenv("MATCH_HUB_DB_PROFILE") or DEFAULT_DB_PROFILE
    if name not in DATABASES:
        raise KeyError("Database profile not found: {0}".format(name))
    config = dict(DATABASES[name])
    _validate_config(name, config)
    return config


def local_config_path() -> Path:
    return Path(__file__).with_name("db_config.local.py")


def env_config_path() -> Path:
    return ENV_PATH
