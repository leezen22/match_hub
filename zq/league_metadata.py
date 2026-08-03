from __future__ import annotations

import re

from bs4 import BeautifulSoup

from config import zqconfig_qt
from utils import js2pyUtil
from utils.webUtil import WebUtil


def resolve_league_detail_by_id(league_id):
    """Resolve missing Football metadata from one identity-bound Titan page."""

    resolved_league_id = int(league_id)
    season_url = zqconfig_qt.seajsWebdir + "sea{}.js".format(resolved_league_id)
    season_state, season_content = WebUtil.requests_get(
        season_url,
        headers=zqconfig_qt.headers,
        sourceName="zq league detail seasons",
    )
    if season_state != 1 or not season_content:
        return None
    parsed_seasons = js2pyUtil.js2c(
        season_content,
        source=season_url,
        required_names=("arrSeason",),
    )
    if parsed_seasons[0] != 1:
        return None
    seasons = [
        str(item)
        for item in parsed_seasons[1].arrSeason
        if str(item).strip()
    ]
    if not seasons:
        return None

    season = seasons[0]
    page_url = (
        zqconfig_qt.league_web_schedir
        + season
        + "/"
        + str(resolved_league_id)
        + ".html"
    )
    page_state, page_content = WebUtil.requests_get(
        page_url,
        headers=zqconfig_qt.headers,
        sourceName="zq league detail page",
    )
    if page_state != 1 or not page_content:
        return None
    soup = BeautifulSoup(page_content, "html.parser")
    inline_script = "\n".join(
        script.get_text(" ", strip=True)
        for script in soup.find_all("script")
        if not script.get("src")
    )
    page_league_id = _required_inline_int(inline_script, "SclassID")
    page_sub_league_id = _required_inline_int(inline_script, "SubSclassID")
    page_season = _required_inline_text(inline_script, "selectSeason")
    if page_league_id != resolved_league_id:
        raise ValueError(
            "football league detail identity conflict for league_id={}".format(
                resolved_league_id
            )
        )
    if page_season != season:
        raise ValueError(
            "football league detail season conflict for league_id={}".format(
                resolved_league_id
            )
        )

    references = []
    reference_pattern = re.compile(
        r"/jsData/matchResult/{}/([sc]){}(?:_([0-9]+))?\.js(?:\?.*)?$".format(
            re.escape(season),
            resolved_league_id,
        ),
        re.IGNORECASE,
    )
    for script in soup.find_all("script"):
        source = str(script.get("src") or "")
        match = reference_pattern.match(source)
        if match:
            references.append((match.group(1).lower(), match.group(2)))
    unique_references = sorted(set(references))
    if len(unique_references) != 1:
        raise ValueError(
            "football league detail schedule reference is not unique for league_id={}".format(
                resolved_league_id
            )
        )
    schedule_kind, source_sub_league_id = unique_references[0]
    league_type, if_have_sub = _schedule_scope(
        schedule_kind,
        source_sub_league_id,
        page_sub_league_id,
        resolved_league_id,
    )

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    title_match = re.search(
        r"{}赛季(.+?)赛程".format(re.escape(season)),
        title,
    )
    league_name = title_match.group(1).strip() if title_match else None
    return {
        "league_id": resolved_league_id,
        "league_name": league_name,
        "league_type": league_type,
        "if_have_sub": if_have_sub,
        "seasons": seasons,
        "metadata_binding_status": "detail_page_resolved",
    }


def _schedule_scope(
        schedule_kind,
        source_sub_league_id,
        page_sub_league_id,
        league_id):
    if schedule_kind == "c":
        if page_sub_league_id != 0 or source_sub_league_id is not None:
            raise ValueError(
                "football cup detail contains unsupported sub-league binding for league_id={}".format(
                    league_id
                )
            )
        return 2, 0
    if source_sub_league_id is None:
        if page_sub_league_id != 0:
            raise ValueError(
                "football league detail sub-league binding conflict for league_id={}".format(
                    league_id
                )
            )
        return 1, 0
    if int(source_sub_league_id) != page_sub_league_id or page_sub_league_id <= 0:
        raise ValueError(
            "football league detail sub-league binding conflict for league_id={}".format(
                league_id
            )
        )
    return 1, 1


def _required_inline_int(script, variable_name):
    match = re.search(
        r"\b{}\s*=\s*([0-9]+)\s*;".format(re.escape(variable_name)),
        script,
    )
    if not match:
        raise ValueError("football league detail missing {}".format(variable_name))
    return int(match.group(1))


def _required_inline_text(script, variable_name):
    match = re.search(
        r"\b{}\s*=\s*['\"]([^'\"]+)['\"]\s*;".format(
            re.escape(variable_name)
        ),
        script,
    )
    if not match:
        raise ValueError("football league detail missing {}".format(variable_name))
    return match.group(1).strip()
