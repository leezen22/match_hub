from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "league_metadata"
DEFAULT_TTL_HOURS = int(os.getenv("MATCH_HUB_LEAGUE_CACHE_TTL_HOURS", "24"))


def get_cached_leagues(
        sport: str,
        fetcher: Callable[[], list[dict[str, Any]]],
        *,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        force_refresh: bool = False,
        validator: Callable[[list[dict[str, Any]]], bool] | None = None) -> list[dict[str, Any]]:
    cache_path = CACHE_DIR / f"{sport}_leagues.json"
    if not force_refresh:
        cached = _read_cache(cache_path, ttl_hours=ttl_hours, allow_expired=False)
        if cached is not None and (validator is None or validator(cached)):
            return cached

    try:
        leagues = fetcher()
    except Exception:
        stale = _read_cache(cache_path, ttl_hours=ttl_hours, allow_expired=True)
        if stale is not None and (validator is None or validator(stale)):
            return stale
        raise

    _write_cache(cache_path, sport, leagues, ttl_hours)
    return leagues


def _read_cache(cache_path: Path, *, ttl_hours: int, allow_expired: bool) -> list[dict[str, Any]] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
        if not allow_expired and datetime.now() - fetched_at > timedelta(hours=ttl_hours):
            return None
        leagues = payload.get("leagues")
        if isinstance(leagues, list):
            return leagues
    except Exception:
        return None
    return None


def _write_cache(cache_path: Path, sport: str, leagues: list[dict[str, Any]], ttl_hours: int) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sport": sport,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "ttl_hours": ttl_hours,
        "count": len(leagues),
        "leagues": leagues,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
