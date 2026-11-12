"""Client tests with a fake HTTP session. No network."""
import json

from src.kalshi.client import KalshiClient


class FakeResp:
    def __init__(self, code, payload=None):
        self.status_code, self._p, self.text = code, payload or {}, json.dumps(payload or {})

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, script):
        self.script, self.calls, self.headers = list(script), [], {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return self.script.pop(0)


def mk(tmp_path, script):
    c = KalshiClient(raw_dir=tmp_path, min_gap=0.0, session=FakeSession(script))
    return c


def test_backoff_on_429_then_success(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    c = mk(tmp_path, [FakeResp(429), FakeResp(429), FakeResp(200, {"ok": 1})])
    assert c.get("/x") == {"ok": 1}
    assert c.n_429 == 2 and c.n_requests == 3


def test_cursor_paging_merges_pages(tmp_path):
    c = mk(tmp_path, [FakeResp(200, {"events": [{"a": 1}], "cursor": "c1"}),
                      FakeResp(200, {"events": [{"a": 2}], "cursor": ""})])
    ev = c.events("S")
    assert ev == [{"a": 1}, {"a": 2}]
    assert c.s.calls[1][1]["cursor"] == "c1"
    # second call is served from the cache: no new HTTP calls
    assert c.events("S") == ev and len(c.s.calls) == 2


def test_candles_cached_and_resumable(tmp_path):
    m = {"ticker": "S-26AUG26-T90", "open_time": "2026-08-25T14:00:00Z", "close_time": "2026-08-27T04:00:00Z",
         "_tier": "historical"}
    c = mk(tmp_path, [FakeResp(200, {"candlesticks": [{"end_period_ts": 1}]})])
    assert c.candles("S", m) == [{"end_period_ts": 1}]
    assert "/historical/markets/S-26AUG26-T90/candlesticks" in c.s.calls[0][0]
    assert c.candles_path("S", m["ticker"]).exists()
    assert c.candles("S", m) == [{"end_period_ts": 1}] and len(c.s.calls) == 1


def test_candles_fall_back_to_other_tier_on_404(tmp_path):
    m = {"ticker": "S-26OCT01-T70", "open_time": "2026-09-30T14:00:00Z", "close_time": "2026-10-02T04:00:00Z",
         "_tier": "historical"}
    c = mk(tmp_path, [FakeResp(404), FakeResp(200, {"candlesticks": []})])
    assert c.candles("S", m) == []
    assert "/series/S/markets/S-26OCT01-T70/candlesticks" in c.s.calls[1][0]
