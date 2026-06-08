import os
import re
import traceback
from typing import Iterable, Optional

import js2py

from config import common_config
from utils.fileUtil import logLine
from utils.webUtil import WebUtil


HTML_MARKERS = ("<!doctype", "<html", "<head", "<body", "</html>")


def _preview(content: str, limit: int = 300) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    return text[:limit]


def _looks_like_html(content: str) -> bool:
    text = (content or "").lstrip().lower()
    return text.startswith("<") or any(marker in text[:1000] for marker in HTML_MARKERS)


def is_probable_js(content: str, required_names: Optional[Iterable[str]] = None) -> bool:
    if not content or _looks_like_html(content):
        return False

    if required_names:
        return any(name in content for name in required_names)

    js_markers = ("var ", "function ", "const ", "let ", "arr", "=")
    return any(marker in content for marker in js_markers)


def parse_js_content(content: str, source: str, required_names: Optional[Iterable[str]] = None):
    result = [0, ""]
    content = (content or "").lstrip("\ufeff")
    if not content:
        logLine(common_config.js2pyweb_e, ["EMPTY_JS_CONTENT", source])
        return result

    if not is_probable_js(content, required_names=required_names):
        logLine(common_config.js2pyweb_e, ["NON_TARGET_JS_CONTENT", source, _preview(content)])
        return result

    try:
        context = js2py.EvalJs()
        context.execute(content)
    except Exception as e:
        logLine(
            common_config.js2pyweb_e,
            ["JS_PARSE_FAILED", source, repr(e), _preview(content), traceback.format_exc()],
        )
        print("JS parse failed: {0}".format(source))
        print(e)
    else:
        result = [1, context]
    return result


# Parse remote JS and return [state, context].
def jsyWebjs(url, headers, required_names: Optional[Iterable[str]] = None):
    webResponse = WebUtil.requests_get(url, headers, sourceName="js2py remote js")
    state = webResponse[0]
    webContent = webResponse[1]
    if state != 1:
        logLine(common_config.js2pyweb_e, ["HTTP_REQUEST_FAILED", url, state])
        return [0, ""]
    return parse_js_content(webContent, url, required_names=required_names)


def js2c(content, source="inline js", required_names: Optional[Iterable[str]] = None):
    return parse_js_content(content, source, required_names=required_names)


def jsLocjs(filepath):
    context = ""
    if not os.path.exists(filepath):
        logLine(common_config.js2pylocal_e, ["LOCAL_JS_FILE_NOT_FOUND", filepath])
        return context

    size = os.path.getsize(filepath)
    if size <= 0:
        logLine(common_config.js2pylocal_e, ["EMPTY_LOCAL_JS_FILE", filepath])
        return context

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            jscontent = file.read()
        result = parse_js_content(jscontent, filepath)
        if result[0] == 1:
            context = result[1]
        else:
            logLine(common_config.js2pylocal_e, ["LOCAL_JS_PARSE_FAILED", filepath])
    except Exception as e:
        print(e)
        logLine(common_config.js2pylocal_e, [filepath, repr(e), traceback.format_exc()])
    return context


# def getValue(context, atr):
#     try:
#         atr_value = context.atr
#     except Exception as e:
#         print(e)
#         atr_value = None
#     return atr_value
