"""Fetch the raw drivable street network from OpenStreetMap, live.

Authoritative source, fetched fresh. Unlike the old `network.cache.json` (which
carried only bare coordinate lists), this keeps **node IDs**. Two ways that share
a node are a real junction; that topology is what makes exact intersections
possible downstream, and it is the thing the previous pipeline discarded.

    python tools/fetch_osm.py

Writes data/osm.json  (ways with tags + node refs, and every node's lat/lon).
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Lake Murray / Del Cerro / Alvarado. Same box the v2 build used, so the three
# layouts and the old work are directly comparable.
BBOX = (32.7600, -117.0750, 32.8080, -116.9980)  # S, W, N, E

DRIVABLE = (
    "motorway|trunk|primary|secondary|tertiary|unclassified|residential|"
    "living_street|motorway_link|trunk_link|primary_link|secondary_link|"
    "tertiary_link|road"
)

ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
)

QUERY = f"""
[out:json][timeout:180];
way["highway"~"^({DRIVABLE})$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out body;
>;
out skel qt;
"""


def fetch(query):
    last = None
    for url in ENDPOINTS:
        for attempt in range(2):
            try:
                sys.stderr.write(f"  -> {url} (try {attempt + 1})\n")
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode({"data": query}).encode(),
                    headers={"User-Agent": "airoso-track-builder/0.1 (OSM fetch)"},
                )
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except Exception as exc:  # noqa: BLE001 - report and try the next mirror
                last = exc
                sys.stderr.write(f"     failed: {exc}\n")
                time.sleep(3)
    raise SystemExit(f"all Overpass endpoints failed: {last}")


def main():
    sys.stderr.write("Fetching drivable network from OpenStreetMap...\n")
    raw = fetch(QUERY)

    nodes, ways = {}, []
    for el in raw.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            ways.append(
                {
                    "id": el["id"],
                    "nodes": el["nodes"],
                    "tags": el.get("tags", {}),
                }
            )

    # Overpass returns way-member nodes via the `>;` recursion; anything missing
    # means a truncated response, which must be loud, not silently routed around.
    missing = {n for w in ways for n in w["nodes"] if n not in nodes}
    if missing:
        raise SystemExit(f"TRUNCATED FETCH: {len(missing)} way nodes have no coordinates")

    out = {
        "bbox": list(BBOX),
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node_count": len(nodes),
        "way_count": len(ways),
        "nodes": {str(k): v for k, v in nodes.items()},
        "ways": ways,
    }
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, "osm.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)

    named = {w["tags"].get("name") for w in ways} - {None}
    sys.stderr.write(
        f"OK  {len(ways)} ways / {len(nodes)} nodes / {len(named)} named streets"
        f" -> {path}\n"
    )


if __name__ == "__main__":
    main()
