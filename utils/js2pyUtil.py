import os
import re
import sys
import threading
import traceback
from typing import Iterable, Optional

import js2py

from config import common_config
from utils.fileUtil import logLine
from utils.webUtil import WebUtil


HTML_MARKERS = ("<!doctype", "<html", "<head", "<body", "</html>")
JS2PY_EXEC_LOCK = threading.RLock()
JS_START_MARKERS = ("var ", "const ", "let ", "function ")


def _normalize_js_content(content: str) -> str:
    text = (content or "").lstrip("\ufeff")
    # Some Titan JS responses are UTF-8 with BOM, but requests may decode them
    # as a legacy charset and leave mojibake before the first statement.
    for marker in JS_START_MARKERS:
        index = text.find(marker)
        if 0 <= index <= 8:
            return text[index:]
    index = text.find("ar ")
    if 0 <= index <= 8:
        return "v" + text[index:]
    return text


def _split_top_level_statements(content: str):
    statements = []
    start = 0
    quote = None
    escaped = False
    depth = 0
    for index, char in enumerate(content):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"', "`"):
            quote = char
            continue
        if char in "([{":
            depth += 1
            continue
        if char in ")]}" and depth > 0:
            depth -= 1
            continue
        if char == ";" and depth == 0:
            statement = content[start:index + 1].strip()
            if statement:
                statements.append(statement)
            start = index + 1

    rest = content[start:].strip()
    if rest:
        statements.append(rest)
    return statements


def _execute_js(content: str):
    context = js2py.EvalJs()
    context.execute(content)
    return context


def _execute_js_by_statement(content: str):
    context = js2py.EvalJs()
    for statement in _split_top_level_statements(content):
        context.execute(statement)
    return context


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
    content = _normalize_js_content(content)
    if not content:
        logLine(common_config.js2pyweb_e, ["EMPTY_JS_CONTENT", source])
        return result

    if not is_probable_js(content, required_names=required_names):
        logLine(common_config.js2pyweb_e, ["NON_TARGET_JS_CONTENT", source, _preview(content)])
        return result

    try:
        with JS2PY_EXEC_LOCK:
            context = _execute_js(content)
    except Exception as e:
        try:
            with JS2PY_EXEC_LOCK:
                context = _execute_js_by_statement(content)
        except Exception as fallback_error:
            logLine(
                common_config.js2pyweb_e,
                [
                    "JS_PARSE_FAILED",
                    source,
                    repr(e),
                    "FALLBACK_FAILED",
                    repr(fallback_error),
                    _preview(content),
                    traceback.format_exc(),
                ],
            )
            print("JS parse failed: {0}".format(source), file=sys.stderr)
            print(fallback_error, file=sys.stderr)
        else:
            logLine(common_config.js2pyweb_e, ["JS_PARSE_FALLBACK_OK", source, repr(e)])
            result = [1, context]
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
        print("LOCAL_JS_READ_OR_PARSE_FAILED filepath={0} error={1}".format(filepath, e))
        logLine(common_config.js2pylocal_e, [filepath, repr(e), traceback.format_exc()])
    return context


# def getValue(context, atr):
#     try:
#         atr_value = context.atr
#     except Exception as e:
#         print(e)
#         atr_value = None
#     return atr_value
