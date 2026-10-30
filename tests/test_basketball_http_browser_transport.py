"""Basketball source transport keeps routing and TLS validation explicit."""
from types import SimpleNamespace

import pytest

from utils.webUtil import WebUtil


@pytest.mark.parametrize('statuses, expected_calls, state', [([200], 1, 1), ([503, 200], 2, 1), ([403], 1, 4)])
def test_browser_transport_preserves_proxy_environment_and_verified_tls(monkeypatch, statuses, expected_calls, state):
    from curl_cffi import requests as browser_requests
    from utils import webUtil
    options, calls = [], []
    responses = iter(statuses)
    class Session:
        def __init__(self, **kwargs): options.append(kwargs)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(status_code=next(responses), text='source', encoding='utf-8')
    monkeypatch.setattr(browser_requests, 'Session', Session)
    monkeypatch.setattr(webUtil.requests, 'get', lambda *a, **k: pytest.fail('must use browser transport'))
    monkeypatch.setattr(webUtil, 'logLine', lambda *args: None)
    result = WebUtil.requests_get('https://nba.titan007.com/test', browser_tls=True,
                                 timeout=(30,60), retry_time=2, sleep=False)
    assert result[0] == state
    assert len(calls) == expected_calls
    assert all(o == {'impersonate':'chrome','trust_env':True,'verify':True} for o in options)
    assert all(c['timeout'] == (30,60) and c['proxies'] is None for c in calls)


def test_browser_transport_retries_connection_failure(monkeypatch):
    from curl_cffi import requests as browser_requests
    from utils import webUtil
    calls = []
    class Session:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args, **kwargs):
            calls.append(1)
            raise ConnectionError('failed')
    monkeypatch.setattr(browser_requests, 'Session', Session)
    monkeypatch.setattr(webUtil, 'logLine', lambda *args: None)
    assert WebUtil.requests_get('https://nba.titan007.com/test', browser_tls=True, sleep=False)[0] == 4
    assert len(calls) == 2


def test_single_match_score_uses_https_and_browser_transport(monkeypatch):
    from lq.parshtml import part_score
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return [4, '']
    monkeypatch.setattr(WebUtil, 'requests_get', get)
    assert part_score.get_PartScore(722257) == {}
    assert calls[0][0] == 'https://nba.titan007.com/cn/Tech/TechTxtLive.aspx?matchid=722257'
    assert calls[0][1]['browser_tls'] is True
