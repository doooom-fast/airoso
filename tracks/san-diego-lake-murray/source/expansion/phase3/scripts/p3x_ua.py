"""Force a generic User-Agent on every urllib request made in this process (the repo's fetch tools name their own
client; the Phase 3 data run sends a generic one instead). Import before the tool runs."""
import urllib.request

UA = "data-fetch/1.0"
_Request = urllib.request.Request


class _GenericUA(_Request):
    def __init__(self, url, data=None, headers=None, *a, **k):
        h = {kk: vv for kk, vv in dict(headers or {}).items() if kk.lower() != "user-agent"}
        h["User-Agent"] = UA
        super().__init__(url, data, h, *a, **k)


urllib.request.Request = _GenericUA
