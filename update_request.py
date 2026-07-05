from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

BASKETBALL_KEYWORDS = [
    "basketball",
    "nba",
    "wnba",
    "cba",
    "ncaab",
    "ncaaw",
    "篮球",
    "籃球",
    "男篮",
    "女篮",
    "男籃",
    "女籃",
    "美职篮",
    "美職籃",
    "美职女篮",
    "美国女子职业篮球联赛",
    "美国女子篮球职业联赛",
]

FOOTBALL_KEYWORDS = [
    "football",
    "soccer",
    "zq",
    "足球",
    "世亚预",
    "亚洲预选",
    "世界杯亚洲区预选",
    "世欧预",
    "欧洲预选",
    "世界杯欧洲区预选",
    "世预赛",
    "世界杯预选",
    "中超",
    "英超",
    "西甲",
    "德甲",
    "意甲",
    "法甲",
    "欧冠",
    "欧联",
    "亚冠",
    "亚洲杯",
    "欧洲杯",
]


def parse_update_request(
        request: str,
        *,
        sport: str = "auto",
        league_id: int | None = None,
        season: str | None = None,
        kind_type: int | None = None,
        league_type: int | None = None,
        if_have_sub: int | None = None,
        action: str | None = None,
        include_finished: bool = False,
        limit: int | None = None,
        until_time: str | None = None,
        until_days: int | None = 3) -> dict[str, Any]:
    text = request.strip()
    resolved_sport = _resolve_sport_from_request(
        text,
        sport=sport,
        kind_type=kind_type,
        league_type=league_type,
        if_have_sub=if_have_sub,
    )
    if resolved_sport is None:
        return _resolve_by_upstream_metadata(
            text,
            league_id=league_id,
            season=season,
            action=action,
            include_finished=include_finished,
            limit=limit,
            until_time=until_time,
            until_days=until_days,
        )
    command = [_entrypoint_for_sport(resolved_sport), "request", text]
    if league_id is not None:
        command.extend(["--league-id", str(league_id)])
    if season is not None:
        command.extend(["--season", str(season)])
    if resolved_sport == "football":
        resolved_league_type = league_type if league_type is not None else kind_type
        if resolved_league_type is not None:
            command.extend(["--league-type", str(resolved_league_type)])
        if if_have_sub is not None:
            command.extend(["--if-have-sub", str(if_have_sub)])
    else:
        if kind_type is not None:
            command.extend(["--kind-type", str(kind_type)])
    if action is not None:
        command.extend(["--action", str(action)])
    if include_finished:
        command.append("--include-finished")
    if limit is not None:
        command.extend(["--limit", str(limit)])
    if _parse_action(text, action) == "data":
        if until_time is not None:
            command.extend(["--until-time", str(until_time)])
        elif until_days is not None:
            command.extend(["--until-days", str(until_days)])
    return {
        "request": text,
        "sport": resolved_sport,
        "entrypoint": command[0],
        "stage": "request",
        "action": _parse_action(text, action),
        "command": command,
        "will_write_local_db": True,
        "writer_project": "match_hub",
        "boundary": "match_hub detects sport from natural language and delegates to the sport-specific Titan updater.",
    }


def parse_structured_update_request(
        *,
        sport: str,
        league_id: int,
        season: str | None = None,
        kind_type: int | None = None,
        league_type: int | None = None,
        if_have_sub: int | None = None,
        action: str = "data",
        include_finished: bool = False,
        limit: int | None = None,
        until_time: str | None = None,
        until_days: int | None = 3) -> dict[str, Any]:
    resolved_sport = _resolve_sport("", sport)
    if resolved_sport == "football":
        from zq_update import parse_natural_update_request

        resolved_league_type = league_type if league_type is not None else kind_type
        plan = parse_natural_update_request(
            "",
            league_id=league_id,
            season=season,
            league_type=resolved_league_type,
            if_have_sub=if_have_sub,
            action=action,
            include_finished=include_finished,
            limit=limit,
            until_match_time=until_time,
            until_days=until_days,
        )
    else:
        from lq_update import parse_natural_update_request

        plan = parse_natural_update_request(
            "",
            league_id=league_id,
            season=season,
            kind_type=kind_type,
            action=action,
            include_finished=include_finished,
            limit=limit,
            until_match_time=until_time,
            until_days=until_days,
        )
    return {
        **plan,
        "request": None,
        "sport": resolved_sport,
        "input_mode": "structured",
        "entrypoint": _entrypoint_for_sport(resolved_sport),
        "boundary": "match_hub received structured sport/league parameters and delegated directly to the sport-specific Titan updater.",
    }


def run_update_request(**kwargs: Any) -> dict[str, Any]:
    execute = bool(kwargs.pop("execute", False))
    structured = bool(kwargs.pop("structured", False))
    if structured:
        kwargs.pop("request", None)
        plan = parse_structured_update_request(**kwargs)
        if execute:
            _execute_structured_plan(**kwargs)
        return {
            **plan,
            "executed": execute,
        }
    plan = parse_update_request(**kwargs)
    if plan["stage"] in ("ambiguous-sport", "unresolved-sport"):
        output = {
            **plan,
            "python": sys.executable,
            "full_command": None,
            "executed": False,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    full_command = [sys.executable, *plan["command"]]
    if execute:
        full_command.append("--execute")
    elif plan["stage"] != "request":
        return {
            **plan,
            "python": sys.executable,
            "full_command": full_command,
            "executed": False,
        }
    output = {
        **plan,
        "python": sys.executable,
        "full_command": full_command,
        "executed": execute,
    }
    if execute:
        result = subprocess.run(
            full_command,
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        output.update({"returncode": result.returncode})
        if result.returncode != 0:
            output["stderr"] = result.stderr
            print(json.dumps(output, ensure_ascii=False, indent=2))
            raise SystemExit(result.returncode)
    else:
        result = subprocess.run(
            full_command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        output.update({
            "dry_run_returncode": result.returncode,
            "dry_run_stdout": result.stdout,
            "dry_run_stderr": result.stderr,
        })
        if result.returncode == 0:
            try:
                output["dry_run_plan"] = json.loads(result.stdout)
            except json.JSONDecodeError:
                output["dry_run_plan"] = None
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            raise SystemExit(result.returncode)
    return output


def _execute_structured_plan(**kwargs: Any) -> None:
    sport = _resolve_sport("", kwargs["sport"])
    common = {
        "request": "",
        "execute": True,
        "league_id": kwargs["league_id"],
        "season": kwargs.get("season"),
        "action": kwargs.get("action"),
        "include_finished": kwargs.get("include_finished", False),
        "limit": kwargs.get("limit"),
        "until_match_time": kwargs.get("until_time"),
        "until_days": kwargs.get("until_days"),
    }
    if sport == "football":
        from zq_update import run_natural_update_request

        run_natural_update_request(
            **common,
            league_type=kwargs.get("league_type") if kwargs.get("league_type") is not None else kwargs.get("kind_type"),
            if_have_sub=kwargs.get("if_have_sub"),
        )
    else:
        from lq_update import run_natural_update_request

        run_natural_update_request(
            **common,
            kind_type=kwargs.get("kind_type"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a natural-language local DB update request to the basketball or football updater.")
    parser.add_argument("request", nargs="?", default="", help="Natural-language request, for example: 帮我更新 wnba 本地比赛信息 / 更新 世亚预 比赛信息")
    parser.add_argument("--structured", action="store_true", help="Use structured sport/league parameters directly instead of parsing request text.")
    parser.add_argument("--sport", choices=["auto", "basketball", "football"], default="auto")
    parser.add_argument("--league-id", type=int, default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--kind-type", type=int, choices=[1, 2], default=None)
    parser.add_argument("--league-type", type=int, choices=[1, 2], default=None)
    parser.add_argument("--if-have-sub", type=int, choices=[0, 1], default=None)
    parser.add_argument("--action", choices=["schedule", "data"], default=None)
    parser.add_argument("--include-finished", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--until-time", default=None)
    parser.add_argument("--until-days", type=int, default=3)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.structured and args.sport == "auto":
        parser.error("--structured requires --sport basketball or --sport football")
    if args.structured and args.league_id is None:
        parser.error("--structured requires --league-id")
    if not args.structured and not args.request:
        parser.error("request is required unless --structured is used")

    output = run_update_request(
        request=args.request,
        structured=args.structured,
        sport=args.sport,
        league_id=args.league_id,
        season=args.season,
        kind_type=args.kind_type,
        league_type=args.league_type,
        if_have_sub=args.if_have_sub,
        action=args.action,
        include_finished=args.include_finished,
        limit=args.limit,
        until_time=args.until_time,
        until_days=args.until_days,
        execute=args.execute,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _entrypoint_for_sport(sport: str) -> str:
    if sport == "football":
        return "zq_update.py"
    return "lq_update.py"


def _resolve_sport(text: str, sport: str = "auto") -> str | None:
    if sport != "auto":
        return sport
    basketball_score = _sport_keyword_score(text, BASKETBALL_KEYWORDS)
    football_score = _sport_keyword_score(text, FOOTBALL_KEYWORDS)
    if football_score > basketball_score:
        return "football"
    if basketball_score > football_score:
        return "basketball"
    return None


def _resolve_sport_from_request(
        text: str,
        *,
        sport: str,
        kind_type: int | None,
        league_type: int | None,
        if_have_sub: int | None) -> str | None:
    if sport != "auto":
        return sport
    if league_type is not None or if_have_sub is not None:
        return "football"
    keyword_sport = _resolve_sport(text, sport)
    if keyword_sport is not None:
        return keyword_sport
    if kind_type is not None:
        return "basketball"
    return None


def _resolve_by_upstream_metadata(
        text: str,
        *,
        league_id: int | None,
        season: str | None,
        action: str | None,
        include_finished: bool,
        limit: int | None,
        until_time: str | None,
        until_days: int | None) -> dict[str, Any]:
    candidates = []
    failures = {}
    try:
        from lq_update import parse_natural_update_request as parse_basketball

        plan = parse_basketball(
            text,
            league_id=league_id,
            season=season,
            action=action,
            include_finished=include_finished,
            limit=limit,
            until_match_time=until_time,
            until_days=until_days,
        )
        candidates.append({**plan, "sport": "basketball", "entrypoint": "lq_update.py"})
    except Exception as exc:
        failures["basketball"] = str(exc)
    try:
        from zq_update import parse_natural_update_request as parse_football

        plan = parse_football(
            text,
            league_id=league_id,
            season=season,
            action=action,
            include_finished=include_finished,
            limit=limit,
            until_match_time=until_time,
            until_days=until_days,
        )
        candidates.append({**plan, "sport": "football", "entrypoint": "zq_update.py"})
    except Exception as exc:
        failures["football"] = str(exc)

    if len(candidates) == 1:
        return {
            **candidates[0],
            "input_mode": "natural_language_upstream_resolved",
            "boundary": "match_hub resolved sport by probing basketball and football Titan metadata; only one sport matched.",
        }
    if len(candidates) > 1:
        return {
            "request": text,
            "sport": None,
            "stage": "ambiguous-sport",
            "action": _parse_action(text, action),
            "league_id": league_id,
            "candidates": [
                {
                    "sport": item["sport"],
                    "league_id": item.get("league_id"),
                    "league_name": item.get("league_name"),
                    "season": item.get("season"),
                    "stage": item.get("stage"),
                    "command": item.get("command"),
                }
                for item in candidates
            ],
            "failures": failures,
            "command": None,
            "will_write_local_db": False,
            "writer_project": "match_hub",
            "error": "ambiguous_sport",
            "message": "Both basketball and football metadata matched this request. Add --sport basketball or --sport football, or use --structured with explicit sport and league id.",
        }
    return {
        "request": text,
        "sport": None,
        "stage": "unresolved-sport",
        "action": _parse_action(text, action),
        "league_id": league_id,
        "failures": failures,
        "command": None,
        "will_write_local_db": False,
        "writer_project": "match_hub",
        "error": "unresolved_sport",
        "message": "Neither basketball nor football metadata could resolve this request. Add --sport and a valid league name or league id.",
    }


def _sport_keyword_score(text: str, keywords: list[str]) -> int:
    normalized = _normalize_sport_text(text)
    score = 0
    for keyword in keywords:
        token = _normalize_sport_text(keyword)
        if token and token in normalized:
            score += max(1, len(token))
    return score


def _normalize_sport_text(text: str) -> str:
    return re.sub(r"[\s_\-\.]+", "", str(text or "").lower())


def _parse_action(text: str, action: str | None = None) -> str:
    if action is not None:
        return action
    lowered = text.lower()
    data_words = ["本地db", "本地 db", "数据库", "落库", "全部数据", "完整数据", "比赛信息", "比分", "赔率", "详情"]
    if any(word in lowered for word in data_words):
        return "data"
    if "赛程" in text or "schedule" in lowered:
        return "schedule"
    return "data"


if __name__ == "__main__":
    main()
