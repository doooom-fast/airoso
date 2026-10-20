"""Every live HTTPS fetch in the engine and tools verifies TLS through ``scripts.tls.https_context()``.

2026-10-11: one expired cross-certificate in the Windows Intermediate store broke Python's default
TLS for overpass-api.de (scripts/tls.py has the diagnosis). P0 routed the four gps-stage fetches
through ``https_context()`` (truststore: the OS verifier, as curl uses), but eight more callers still
used the default context, and ``scripts/elevation/srtm.py`` had turned verification OFF
(``check_hostname=False``, ``CERT_NONE``) to get past the same symptom. These pin:

- a static scan: every ``urlopen`` / ``HTTPSConnection`` / ``HTTPSHandler`` call in scripts/, tools/,
  fleet/ and tracks/ passes ``context=https_context()``; nothing disables verification
  (``CERT_NONE``, ``check_hostname = False``, ``_create_unverified_context``) or builds its own
  context outside scripts/tls.py; nothing fetches through a route that can't take the context
  (``urlretrieve``, ``requests``, ``httpx``). Frozen trees of record are not scanned: Lake Murray's
  quarantined ``scripts-v021/`` build tooling and ``engine-july-snapshot/`` (owned by that track);
- behaviour: each fetch function hands urlopen exactly what ``https_context()`` returns;
- ``https_context()`` itself always verifies (or is ``None``, urllib's verifying default).

No network: urlopen is replaced for the duration of each call. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ("scripts", "tools", "fleet", "tracks")
FROZEN = {"scripts-v021", "engine-july-snapshot", "__pycache__"}
TLS_MODULE = ROOT / "scripts" / "tls.py"
NEEDS_CONTEXT = {"urlopen", "HTTPSConnection", "HTTPSHandler"}
FORBIDDEN_NAMES = {"CERT_NONE", "_create_unverified_context", "urlretrieve"}
OWN_CONTEXT = {"create_default_context", "SSLContext"}
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib3", "aiohttp", "pycurl"}


def _name(node) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_https_context_call(node) -> bool:
    return isinstance(node, ast.Call) and _name(node.func) == "https_context"


def _files():
    for top in SCAN:
        for p in sorted((ROOT / top).rglob("*.py")):
            if FROZEN.intersection(p.relative_to(ROOT).parts):
                continue
            yield p


def _violations(path: Path, root: Path = ROOT) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rel = path.relative_to(root).as_posix()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = _name(node.func)
            if fn in NEEDS_CONTEXT:
                ctx = [k.value for k in node.keywords if k.arg == "context"]
                if not ctx or not _is_https_context_call(ctx[0]):
                    out.append(f"{rel}:{node.lineno} {fn}() without context=https_context()")
            if fn in OWN_CONTEXT and path != TLS_MODULE:
                out.append(f"{rel}:{node.lineno} builds its own TLS context ({fn}); use scripts.tls.https_context()")
        if isinstance(node, (ast.Attribute, ast.Name)) and _name(node) in FORBIDDEN_NAMES:
            out.append(f"{rel}:{node.lineno} uses {_name(node)}")
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Attribute) and t.attr in ("check_hostname", "verify_mode"):
                    out.append(f"{rel}:{node.lineno} sets .{t.attr} (verification is never weakened)")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    out.append(f"{rel}:{node.lineno} imports {a.name} (bypasses scripts.tls)")
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in FORBIDDEN_IMPORTS:
            out.append(f"{rel}:{node.lineno} imports from {node.module} (bypasses scripts.tls)")
    return out


def test_every_https_call_in_the_repo_goes_through_https_context():
    files = list(_files())
    assert len(files) > 100, "the scan found too few files - wrong root?"
    bad = [v for f in files for v in _violations(f)]
    assert not bad, "TLS rule (scripts/tls.py):\n  " + "\n  ".join(bad)


def test_the_scan_catches_what_it_claims_to():
    """The checker itself: each forbidden form is flagged, the approved form is not."""
    import tempfile
    cases = {
        "ok.py": ("import urllib.request\nfrom scripts.tls import https_context\n"
                  "urllib.request.urlopen('https://x', timeout=5, context=https_context())\n", 0),
        "bare.py": ("import urllib.request\nurllib.request.urlopen('https://x', timeout=5)\n", 1),
        "ctx.py": ("import ssl, urllib.request\nc = ssl.create_default_context()\nc.check_hostname = False\n"
                   "c.verify_mode = ssl.CERT_NONE\nurllib.request.urlopen('https://x', context=c)\n", 5),
        "req.py": ("import requests\nrequests.get('https://x')\n", 1),
        "retr.py": ("from urllib.request import urlretrieve\nurlretrieve('https://x', 'f')\n", 1),
    }
    with tempfile.TemporaryDirectory() as t:
        for name, (src, want) in cases.items():
            p = Path(t) / name
            p.write_text(src, encoding="utf-8")
            got = _violations(p, root=Path(t))
            assert len(got) == want, (name, got)


def test_srtm_no_longer_disables_verification():
    src = (ROOT / "scripts" / "elevation" / "srtm.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    code = src.split('"""', 2)[2]                       # the docstring tells the history; the code may not
    assert "CERT_NONE" not in code and "check_hostname" not in code and "import ssl" not in code
    assert not any(isinstance(n, ast.Name) and n.id == "_ctx" for n in ast.walk(tree))
    from scripts.elevation import srtm
    assert not hasattr(srtm, "_ctx")


def test_https_context_always_verifies():
    from scripts.tls import https_context
    ctx = https_context()
    if ctx is None:              # truststore not installed: urllib's own (verifying) default is used
        return
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


# --- behaviour: what each fetch function hands to urlopen -------------------------------------------

SENTINEL = object()


def _png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buf, "PNG")
    return buf.getvalue()


def _contexts_used(module, call, body: bytes) -> list:
    """Run ``call()`` with ``module.https_context`` returning SENTINEL and urlopen recording the
    ``context`` it was given (``"MISSING"`` when none), answering ``body``."""
    seen = []

    def fake_urlopen(req, *a, **k):
        seen.append(k.get("context", "MISSING"))
        return io.BytesIO(body)

    saved_open, saved_ctx = urllib.request.urlopen, module.https_context
    urllib.request.urlopen = fake_urlopen
    module.https_context = lambda: SENTINEL
    try:
        call()
    finally:
        urllib.request.urlopen = saved_open
        module.https_context = saved_ctx
    return seen


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"_tool_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_fetch_function_passes_the_https_context():
    from scripts.elevation import srtm, usgs_3dep
    from scripts.environment import buildings, zones
    from scripts.game import build_seed, map_overlay
    from scripts.gps import overpass, street_labels, widths_from_osm
    from scripts.trace import osm as trace_osm
    fetch_osm = _load_tool("fetch_osm")

    empty = json.dumps({"elements": []}).encode()
    bbox = (39.70, -105.25, 39.75, -105.20)
    cases = [
        ("buildings.fetch_buildings", buildings, lambda: buildings.fetch_buildings(bbox, retries=1), empty),
        ("zones.fetch_zones", zones, lambda: zones.fetch_zones(bbox, retries=1), empty),
        ("trace.osm.fetch_drivable", trace_osm, lambda: trace_osm.fetch_drivable(bbox, retries=1), empty),
        ("build_seed._fetch_osm_elements", build_seed, lambda: build_seed._fetch_osm_elements(["way/1"]), empty),
        ("map_overlay._fetch_tile", map_overlay, lambda: map_overlay._fetch_tile(1, 0, 0), _png()),
        ("usgs_3dep._sample_batch", usgs_3dep, lambda: usgs_3dep._sample_batch([(-105.2, 39.7)], retries=1),
         json.dumps({"samples": [{"location": {"x": -105.2, "y": 39.7}, "value": "1800.0"}]}).encode()),
        ("srtm._otd_batch", srtm, lambda: srtm._otd_batch([(6.94, 50.33)], dataset="srtm30m", retries=1),
         json.dumps({"status": "OK", "results": [{"elevation": 600.0}]}).encode()),
        ("srtm._meteo_batch", srtm, lambda: srtm._meteo_batch([(6.94, 50.33)], retries=1),
         json.dumps({"elevation": [600.0]}).encode()),
        # tools/fetch_osm fetches through widths_from_osm._overpass since ledger 0054 P0 (the 7-day guard): its
        # context is that module's https_context()
        ("tools/fetch_osm.fetch", widths_from_osm, lambda: fetch_osm.fetch("[out:json];", max_age_days=None), empty),
        ("overpass.fetch_ways", overpass, lambda: overpass.fetch_ways(bbox, ["X"], retries=1), empty),
        ("overpass._post", overpass, lambda: overpass._post("[out:json];", retries=1), empty),
        ("street_labels._fetch_named_highways", street_labels,
         lambda: street_labels._fetch_named_highways(bbox, retries=1), empty),
        ("widths_from_osm._overpass", widths_from_osm, lambda: widths_from_osm._overpass("[out:json];"),
         json.dumps({"elements": [], "osm3s": {"timestamp_osm_base": "2026-10-11T19:28:01Z"}}).encode()),
    ]
    for label, module, call, body in cases:
        seen = _contexts_used(module, call, body)
        assert seen, f"{label}: never called urlopen"
        assert all(c is SENTINEL for c in seen), f"{label}: urlopen got {seen}, not https_context()"
