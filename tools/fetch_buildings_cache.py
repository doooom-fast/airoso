"""Fetch OSM building footprints into the San Diego assembler's buildings-cache schema — 7-day guarded.

Ledger 0054 P0 step 7 (2026-10-14). ``data/buildings.cache.json`` (read by scripts-v021 build_loop_blend.build_buildings,
which keeps a footprint within 120 m of the loop) was fetched once over the loop's old box and stops at 32.808 N; no
tool in either repo wrote it. This one writes the same schema — a JSON list of ``{"building", "levels", "height",
"geom": [[lon, lat], ...]}`` per OSM ``way["building"]`` (``levels`` = ``building:levels``, both as OSM's strings or
null), in the order Overpass returns them — through ``scripts.gps.widths_from_osm._overpass`` (TLS verified, every
fallback printed), refusing OSM data older than ``--max-age-days`` (default 7) unless ``--allow-stale-osm``.

The cache file stays a bare list (the assembler iterates it); the provenance goes beside it in ``<out>.provenance.json``:
server, OSM data timestamp, query, bbox, counts, and — with ``--compare <old cache>`` — how many of the old cache's
footprints are still in OSM exactly (same tag, levels, height and vertices), inside the old cache's extent.

    python tools/fetch_buildings_cache.py --bbox S W N E --out <cache.json> [--compare <old cache.json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
from scripts.gps import widths_from_osm as wfo  # noqa: E402


def query_for(bbox) -> str:
    s, w, n, e = bbox
    return f'[out:json][timeout:240];way["building"]({s},{w},{n},{e});out geom;'


def to_cache(payload: dict) -> list[dict]:
    out = []
    for el in payload.get("elements", []):
        if el.get("type") != "way" or not el.get("geometry"):
            continue
        t = el.get("tags", {})
        out.append({"building": t.get("building"), "levels": t.get("building:levels"), "height": t.get("height"),
                    "geom": [[g["lon"], g["lat"]] for g in el["geometry"]]})
    return out


def _key(b: dict) -> str:
    return json.dumps([b.get("building"), b.get("levels"), b.get("height"), b["geom"]])


def compare(old: list[dict], new: list[dict]) -> dict:
    """the old cache's footprints still present exactly in the new one, and the new ones inside the old extent"""
    lats = [p[1] for b in old for p in b["geom"]]
    lons = [p[0] for b in old for p in b["geom"]]
    s, n, w, e = min(lats), max(lats), min(lons), max(lons)
    newk = {_key(b) for b in new}
    oldk = {_key(b) for b in old}
    inside = [b for b in new if all(s <= p[1] <= n and w <= p[0] <= e for p in b["geom"])]
    return {"old_count": len(old), "old_extent_swne": [s, w, n, e],
            "old_still_exact": sum(1 for b in old if _key(b) in newk),
            "new_inside_old_extent": len(inside),
            "new_inside_old_extent_not_in_old": sum(1 for b in inside if _key(b) not in oldk)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare", default=None, help="an older cache to report against (read only)")
    ap.add_argument("--max-age-days", type=float, default=wfo.OSM_MAX_AGE_DAYS)
    ap.add_argument("--allow-stale-osm", action="store_true")
    a = ap.parse_args(argv)
    bbox = tuple(a.bbox)
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        print(f"[buildings] --bbox must be S W N E with S < N and W < E, got {bbox}")
        return 2
    out = Path(a.out)
    if a.compare and Path(a.compare).resolve() == out.resolve():
        print("[buildings] --out must not be the --compare cache (the old cache is read only)")
        return 2
    q = query_for(bbox)
    payload, mirror = wfo._overpass(q, timeout=240, max_age_days=a.max_age_days)
    age = wfo.osm_age_days(payload)
    stale = wfo._too_old(age, a.max_age_days)
    if stale and not a.allow_stale_osm:
        print(f"[buildings] REFUSING to write {out.name}: {mirror} answered with {wfo._describe(payload, age)}, older "
              f"than the {a.max_age_days:g}-day limit. Retry later, or --allow-stale-osm.")
        return 1
    cache = to_cache(payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cache), encoding="utf-8")
    prov = {"what": "OSM way[building] footprints, scripts-v021 build_loop_blend buildings-cache schema "
                    "(building, levels = building:levels, height, geom [lon, lat])",
            "tool": "tools/fetch_buildings_cache.py (ledger 0054 P0 step 7)",
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": mirror,
            "osm_base": wfo.osm_base(payload), "osm_age_days": age, "max_age_days": a.max_age_days,
            "tls": "verified (scripts.tls.https_context via scripts.gps.widths_from_osm._overpass)",
            "bbox_swne": list(bbox), "query": q, "query_fingerprint": hashlib.sha256(q.encode()).hexdigest()[:16],
            "count": len(cache), "cache_md5": hashlib.md5(out.read_bytes()).hexdigest()}
    if stale:
        prov["stale_allowed"] = True
    if a.compare:
        old = json.loads(Path(a.compare).read_text(encoding="utf-8"))
        prov["compare"] = {"old_cache": Path(a.compare).name, **compare(old, cache)}
    Path(str(out) + ".provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print(f"[buildings] {len(cache)} footprints from {wfo._host(mirror)} (OSM data as of {prov['osm_base']}) -> {out}"
          + (f"; vs {prov['compare']['old_cache']}: {prov['compare']['old_still_exact']} of "
             f"{prov['compare']['old_count']} unchanged" if a.compare else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
