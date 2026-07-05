from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def query_league_metadata(request: str, *, sport: str = "auto", limit: int = 8) -> dict[str, Any]:
    text = request.strip()
    sports = [sport] if sport in ("basketball", "football") else ["basketball", "football"]
    candidates: list[dict[str, Any]] = []
    failures: dict[str, str] = {}

    for item_sport in sports:
        try:
            candidates.extend(_query_sport(text, item_sport))
        except Exception as exc:
            failures[item_sport] = str(exc)

    deduped = _dedupe_candidates(candidates)
    if len(deduped) == 1:
        candidate = _enrich_unique_candidate(deduped[0])
        return {
            "status": "unique",
            "resolver": "match_hub_league_metadata_query",
            **candidate,
            "failures": failures,
        }
    if len(deduped) > 1:
        return {
            "status": "ambiguous",
            "resolver": "match_hub_league_metadata_query",
            "candidates": deduped[:limit],
            "candidate_count": len(deduped),
            "failures": failures,
        }
    return {
        "status": "not_found",
        "resolver": "match_hub_league_metadata_query",
        "failures": failures,
    }


def _query_sport(text: str, sport: str) -> list[dict[str, Any]]:
    if sport == "football":
        import zq_update

        expanded_text = zq_update._expand_league_aliases(text)
        leagues = zq_update._get_leagues_web()
        matches = [
            _compact_league("football", league)
            for league in leagues
            if zq_update._league_name_matches(expanded_text, league["league_name"])
        ]
        return _prefer_longest_name_matches(matches)

    import lq_update

    expanded_text = lq_update._expand_league_aliases(text)
    leagues = lq_update._get_leagues_web()
    matches = []
    for league in leagues:
        match_length = _basketball_league_match_length(lq_update, expanded_text, league)
        if match_length > 0:
            matches.append({**_compact_league("basketball", league), "_match_length": match_length})
    return _prefer_longest_name_matches(matches)


def _compact_league(sport: str, league: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "sport": sport,
        "league_id": int(league["league_id"]),
        "league_name": str(league["league_name"]),
    }
    if sport == "football":
        seasons = _default_seasons(league)
        compact["season"] = seasons[0] if seasons else None
        compact["seasons"] = seasons
        compact["league_type"] = int(league["league_type"])
        compact["if_have_sub"] = int(league["if_have_sub"])
    else:
        seasons = _default_seasons(league)
        compact["season"] = seasons[0] if seasons else None
        compact["seasons"] = seasons
        compact["kind_type"] = int(league["kind_type"])
        for field in [
            "country_id",
            "country_name",
            "country_logo",
            "country_order",
            "source",
            "name_zh_hans",
            "name_zh_hant",
            "name_en",
            "left_data_type",
            "left_country_name_zh_hans",
            "left_country_name_zh_hant",
            "left_country_name_en",
            "left_country_group",
            "left_data_source",
        ]:
            if field in league:
                compact[field] = league[field]
    return compact


def _default_seasons(league: dict[str, Any]) -> list[str]:
    seasons = league.get("seasons")
    if isinstance(seasons, list):
        return [str(value) for value in seasons if str(value) != ""]
    return []


def _enrich_unique_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate["sport"] != "basketball":
        return candidate
    if candidate.get("seasons"):
        return candidate
    try:
        seasons = _resolve_basketball_seasons(candidate["league_id"])
    except Exception as exc:
        return {
            **candidate,
            "season_lookup_error": str(exc),
        }
    return {
        **candidate,
        "season": seasons[0] if seasons else None,
        "seasons": seasons,
    }


def _resolve_basketball_seasons(league_id: int) -> list[str]:
    from config import lqconfig_qt
    from utils import js2pyUtil
    from utils.league_season_cache import get_cached_league_seasons
    from utils.webUtil import WebUtil

    def fetch_seasons() -> list[str]:
        url = lqconfig_qt.seajsWebdir + "sea{}.js".format(int(league_id))
        state, content = WebUtil.requests_get(url, headers=lqconfig_qt.headers, sourceName="query lq seasons")
        if state != 1 or not content:
            raise ValueError("could not fetch Titan season list for league_id={}".format(league_id))
        parsed = js2pyUtil.js2c(content, source=url, required_names=("arrSeason",))
        if parsed[0] != 1:
            raise ValueError("could not parse Titan season list for league_id={}".format(league_id))
        return [str(item[0]) for item in parsed[1].arrSeason if len(item) > 0 and str(item[0]) != ""]

    return get_cached_league_seasons("basketball", int(league_id), fetch_seasons)


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for candidate in candidates:
        key = (candidate["sport"], candidate["league_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append({k: v for k, v in candidate.items() if not k.startswith("_")})
    return deduped


def _prefer_longest_name_matches(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(candidates) <= 1:
        return candidates
    candidates.sort(key=_candidate_match_length, reverse=True)
    max_length = _candidate_match_length(candidates[0])
    return [item for item in candidates if _candidate_match_length(item) == max_length]


def _candidate_match_length(candidate: dict[str, Any]) -> int:
    value = candidate.get("_match_length")
    if isinstance(value, int):
        return value
    return len(_normalize(candidate["league_name"]))


def _basketball_league_match_length(lq_update: Any, text: str, league: dict[str, Any]) -> int:
    best_length = 0
    for field in ["league_name", "name_zh_hans", "name_zh_hant", "name_en"]:
        value = league.get(field)
        if isinstance(value, str) and lq_update._league_name_matches(text, value):
            best_length = max(best_length, len(_normalize(value)))
    return best_length


def _normalize(value: Any) -> str:
    return re.sub(r"[\s_\-\.]+", "", str(value or "").lower())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query match_hub league metadata and return a compact JSON resolution. No DB writes."
    )
    parser.add_argument("request", help="Natural-language league update request or league name.")
    parser.add_argument("--sport", choices=["auto", "basketball", "football"], default="auto")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    print(json.dumps(
        query_league_metadata(args.request, sport=args.sport, limit=args.limit),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
