import argparse
import sys
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import lqconfig_qt, scrawler_config
from utils import js2pyUtil
from utils.webUtil import WebUtil


def find_schedule_js_src(page_content):
    soup = BeautifulSoup(page_content, "html.parser")
    for script in soup.find_all("script"):
        src = script.get("src")
        if src and "jsData/matchResult" in src:
            return src
    return ""


def infer_required_names(url, content=""):
    if "LeagueSeason" in url or "arrSeason" in content[:1000]:
        return ("arrSeason",)
    if "matchResult" in url:
        return ("arrLeague", "ymList", "arrData", "lastUpdateTime", "playoffsList")
    return ("arrSeason", "arrLeague", "ymList", "arrData", "lastUpdateTime")


def diagnose_page(page_url):
    print("Checking schedule page:")
    print(page_url)
    response = WebUtil.requests_get(page_url, headers=lqconfig_qt.headers, sourceName="diagnose lq schedule page")
    state, content = response[0], response[1]
    if state != 1:
        print("HTTP_REQUEST_FAILED")
        return 1
    if not content:
        print("HTTP_OK_BUT_EMPTY_CONTENT")
        return 1

    sche_src = find_schedule_js_src(content)
    if not sche_src:
        print("HTTP_OK_BUT_TARGET_JS_NOT_FOUND")
        print(content[:300].replace("\n", " "))
        return 1

    js_url = urljoin(scrawler_config.qt_lq_web_home, sche_src)
    return diagnose_js(js_url)


def diagnose_js(js_url):
    print("Checking basketball JS:")
    print(js_url)
    response = WebUtil.requests_get(js_url, headers=lqconfig_qt.headers, sourceName="diagnose lq schedule js")
    state, content = response[0], response[1]
    if state != 1:
        print("HTTP_REQUEST_FAILED")
        return 1
    if not content:
        print("HTTP_OK_BUT_EMPTY_CONTENT")
        return 1
    required_names = infer_required_names(js_url, content)
    if not js2pyUtil.is_probable_js(content, required_names=required_names):
        print("HTTP_OK_BUT_CONTENT_IS_NOT_TARGET_JS")
        print(content[:300].replace("\n", " "))
        return 1

    parse_result = js2pyUtil.js2c(
        content,
        source=js_url,
        required_names=required_names,
    )
    if parse_result[0] != 1:
        print("JS_CONTENT_FOUND_BUT_JS2PY_PARSE_FAILED")
        return 1

    print("OK_TARGET_JS_PARSED")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Diagnose lq schedule page/js loading and js2py parsing.")
    parser.add_argument("--page-url", help="normal.aspx page URL that should contain schedule JS script")
    parser.add_argument("--js-url", help="direct schedule JS URL")
    args = parser.parse_args()

    if args.js_url:
        raise SystemExit(diagnose_js(args.js_url))
    if args.page_url:
        raise SystemExit(diagnose_page(args.page_url))

    parser.error("Provide --page-url or --js-url")


if __name__ == "__main__":
    main()
