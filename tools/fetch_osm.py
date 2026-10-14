"""Fetch the raw drivable street network from OpenStreetMap, live — with a freshness guard.

Authoritative source, fetched fresh. Unlike the old `network.cache.json` (which
carried only bare coordinate lists), this keeps **node IDs**. Two ways that share
a node are a real junction; that topology is what makes exact intersections
possible downstream, and it is the thing the previous pipeline discarded.

    python tools/fetch_osm.py                                  # the original Lake Murray box -> data/osm.json
    python tools/fetch_osm.py --bbox S W N E --out <file.json> [--service] [--max-age-days 7] [--allow-stale-osm]

Writes ``nodes`` (id -> [lon, lat]), ``ways`` (id, node refs, tags) — the schema ``tools/network.py`` reads —
plus ``node_tags`` (id -> tags, for every node that carries any: signals, crossings, stops) and the provenance
of the answer: which Overpass server gave it (``source``), the OSM data timestamp it was computed from
(``osm_base``), the query and its fingerprint, and the freshness limit it was held to.

FRESHNESS (ledger 0054 P0 step 3, 2026-10-14). This script used to fall back across three Overpass servers with no
staleness check: a mirror that has stopped copying OSM keeps answering with old data (2026-10-11: one served OSM as
of 2026-07-28 while the primary was minutes old). It now fetches through ``scripts.gps.widths_from_osm._overpass``
— the same server list, TLS verified (``scripts.tls.https_context``), every fallback printed — and REFUSES to write
an answer whose OSM data is older than ``--max-age-days`` (default 7, ``widths_from_osm.OSM_MAX_AGE_DAYS``) or has
no timestamp, unless ``--allow-stale-osm`` (then the file records ``stale_allowed: true``).
"""

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
if os.path.dirname(HERE) not in sys.path:      # run as `python tools/fetch_osm.py`: the repo root
    sys.path.insert(0, os.path.dirname(HERE))  # holds scripts.gps / scripts.tls

from scripts.gps import widths_from_osm as wfo  # noqa: E402  (guarded Overpass; OS-verified TLS, never unverified)

# Lake Murray / Del Cerro / Alvarado. Same box the v2 build used, so the three
# layouts and the old work are directly comparable.
BBOX = (32.7600, -117.0750, 32.8080, -116.9980)  # S, W, N, E

DRIVABLE = (
    "motorway|trunk|primary|secondary|tertiary|unclassified|residential|"
    "living_street|motorway_link|trunk_link|primary_link|secondary_link|"
    "tertiary_link|road"
)
# --service adds service ways (driveways, the quarry drive at Mission Gorge / J3, parking aisles): the
# see-only junction arms of ledger 0054 A1 are drawn from them
SERVICE = "|service"


def query_for(bbox, service: bool = False) -> str:
    s, w, n, e = bbox
    hw = DRIVABLE + (SERVICE if service else "")
    # `out body` on the recursed nodes (not `skel`): their tags are where OSM keeps signals and crossings
    return (f"[out:json][timeout:180];\n"
            f"way[\"highway\"~\"^({hw})$\"]({s},{w},{n},{e});\n"
            f"out body;\n>;\nout body qt;\n")


QUERY = query_for(BBOX)


def fetch(query, *, max_age_days=wfo.OSM_MAX_AGE_DAYS, allow_stale=False):
    """``(payload, server_url)`` from the guarded Overpass client. An answer older than ``max_age_days`` (or
    without an OSM data timestamp) stops the script (SystemExit) unless ``allow_stale``; ``max_age_days=None``
    means no limit."""
    payload, mirror = wfo._overpass(query, timeout=180, max_age_days=max_age_days)
    age = wfo.osm_age_days(payload)
    if wfo._too_old(age, max_age_days):
        what = (f"the freshest answer came from {mirror} with {wfo._describe(payload, age)}, older than the "
                f"{max_age_days:g}-day limit")
        if not allow_stale:
            raise SystemExit(f"[fetch_osm] REFUSING to write it: {what}. Retry later, or re-run with "
                             f"--allow-stale-osm to keep it anyway (recorded as stale_allowed).")
        sys.stderr.write(f"[fetch_osm] WARNING {what} - kept anyway (--allow-stale-osm)\n")
    return payload, mirror


def to_snapshot(raw, bbox, query, mirror, max_age_days, stale_allowed=False):
    nodes, node_tags, ways = {}, {}, []
    for el in raw.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
            if el.get("tags"):
                node_tags[el["id"]] = el["tags"]
        elif el["type"] == "way":
            ways.append({"id": el["id"], "nodes": el["nodes"], "tags": el.get("tags", {})})

    # Overpass returns way-member nodes via the `>;` recursion; anything missing
    # means a truncated response, which must be loud, not silently routed around.
    missing = {n for w in ways for n in w["nodes"] if n not in nodes}
    if missing:
        raise SystemExit(f"TRUNCATED FETCH: {len(missing)} way nodes have no coordinates")
    out = {
        "bbox": list(bbox),
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": mirror,
        "osm_base": wfo.osm_base(raw),
        "osm_age_days": wfo.osm_age_days(raw),
        "max_age_days": max_age_days,
        "tls": "verified (scripts.tls.https_context via scripts.gps.widths_from_osm._overpass)",
        "query": query,
        "query_fingerprint": hashlib.sha256(query.encode()).hexdigest()[:16],
        "node_count": len(nodes),
        "way_count": len(ways),
        "nodes": {str(k): v for k, v in nodes.items()},
        "node_tags": {str(k): v for k, v in node_tags.items()},
        "ways": ways,
    }
    if stale_allowed:
        out["stale_allowed"] = True
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), default=None)
    ap.add_argument("--out", default=None, help="output JSON (default: <repo>/data/osm.json)")
    ap.add_argument("--service", action="store_true", help="include highway=service ways")
    ap.add_argument("--max-age-days", type=float, default=wfo.OSM_MAX_AGE_DAYS,
                    help=f"refuse OSM data older than this (default {wfo.OSM_MAX_AGE_DAYS:g})")
    ap.add_argument("--allow-stale-osm", action="store_true")
    a = ap.parse_args(argv)
    bbox = tuple(a.bbox) if a.bbox else BBOX
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise SystemExit(f"--bbox must be S W N E with S < N and W < E, got {bbox}")
    query = query_for(bbox, a.service)
    sys.stderr.write("Fetching drivable network from OpenStreetMap...\n")
    raw, mirror = fetch(query, max_age_days=a.max_age_days, allow_stale=a.allow_stale_osm)
    stale = wfo._too_old(wfo.osm_age_days(raw), a.max_age_days)
    out = to_snapshot(raw, bbox, query, mirror, a.max_age_days, stale_allowed=stale)
    path = a.out or os.path.join(DATA, "osm.json")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)

    named = {w["tags"].get("name") for w in out["ways"]} - {None}
    sys.stderr.write(
        f"OK  {out['way_count']} ways / {out['node_count']} nodes / {len(named)} named streets from "
        f"{wfo._host(mirror)} (OSM data as of {out['osm_base']}) -> {path}\n"
    )


if __name__ == "__main__":
    main()
