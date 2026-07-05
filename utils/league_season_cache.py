from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "league_metadata"
DEFAULT_TTL_HOURS = int(os.getenv("MATCH_HUB_LEAGUE_CACHE_TTL_HOURS", "24"))


def get_cached_league_seasons(
        sport: str,
        league_id: int,
        fetcher: Callable[[], list[str]],
        *,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        force_refresh: bool = False) -> list[str]:
    cache_path = CACHE_DIR / f"{sport}_league_seasons.json"
    league_key = str(int(league_id))
    if not force_refresh:
        cached = _read_cached_seasons(cache_path, league_key, ttl_hours=ttl_hours, allow_expired=False)
        if cached is not None:
            return cached

    try:
        seasons = fetcher()
    except Exception:
        stale = _read_cached_seasons(cache_path, league_key, ttl_hours=ttl_hours, allow_expired=True)
        if stale is not None:
            return stale
        raise

    _write_cached_seasons(cache_path, sport, league_key, seasons, ttl_hours)
    return seasons


def _read_cached_seasons(
        cache_path: Path,
        league_key: str,
        *,
        ttl_hours: int,
        allow_expired: bool) -> list[str] | None:
    payload = _read_payload(cache_path)
    if payload is None:
        return None
    leagues = payload.get("leagues")
    if not isinstance(leagues, dict):
        return None
    item = leagues.get(league_key)
    if not isinstance(item, dict):
        return None
    try:
        fetched_at = datetime.fromisoformat(item["fetched_at"])
    except Exception:
        return None
    if not allow_expired and datetime.now() - fetched_at > timedelta(hours=ttl_hours):
        return None
    seasons = item.get("seasons")
    if not isinstance(seasons, list):
        return None
    return [str(value) for value in seasons if str(value) != ""]


def _write_cached_seasons(cache_path: Path, sport: str, league_key: str, seasons: list[str], ttl_hours: int) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_payload(cache_path) or {
        "sport": sport,
        "ttl_hours": ttl_hours,
        "leagues": {},
    }
    payload["sport"] = sport
    payload["ttl_hours"] = ttl_hours
    leagues = payload.setdefault("leagues", {})
    leagues[league_key] = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "seasons": [str(value) for value in seasons if str(value) != ""],
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_payload(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None
