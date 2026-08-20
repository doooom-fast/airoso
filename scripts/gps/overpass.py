"""Overpass API queries: fetch named route roads within a bounding box.

The map screenshot is only a selection aid — this is where real geometry enters the pipeline.
Uses the standard library (urllib) so Phase 1 runs with no third-party deps. Overpass rejects
requests that lack a ``User-Agent`` (HTTP 406), so we always send one, and we retry on the
transient 504s the public instance occasionally returns.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
import urllib.parse
import urllib.request

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "prodrive-ac-builder/0.1 (https://github.com/k10-motorsports/prodrive-ac-builder)"

# (lon, lat) vertex; a way is a list of them; bbox is (south, west, north, east)
Vertex = tuple[float, float]


def build_query(bbox: tuple[float, float, float, float], road_names: list[str], timeout: int = 90) -> str:
    """Build an Overpass QL query: every named way (clipped to bbox), returned with geometry.

    A ``"ref:US 40"`` entry matches by the ``ref`` tag instead of ``name`` — how numbered highways
    whose ways are unnamed in OSM (rural US routes) get onto a route. Motorways are excluded from
    ref matches so a US-route ref that rides an interstate concurrency never drags the freeway in.
    An ``"id:123,456"`` entry selects explicit way ids — for the nameless, refless pieces a real
    route needs (interchange ramps: the Lariat lap leaves US-6 on the 19th St off-ramp).
    """
    south, west, north, east = bbox
    bb = f"({south},{west},{north},{east})"
    clauses = ""
    for n in road_names:
        if n.startswith("ref:"):
            ref_re = json.dumps(f"(^|;)\\s*{re.escape(n[4:])}\\s*(;|$)")
            clauses += f'  way["highway"]["highway"!~"motorway"]["ref"~{ref_re}]{bb};\n'
        elif n.startswith("id:"):
            clauses += f'  way(id:{n[3:]});\n'
        else:
            clauses += f'  way["highway"]["name"={json.dumps(n)}]{bb};\n'
    return f"[out:json][timeout:{timeout}];\n(\n{clauses});\nout geom;"


def fetch_ways(
    bbox: tuple[float, float, float, float],
    road_names: list[str],
    *,
    retries: int = 3,
    cache=None,
) -> dict[str, list[list[Vertex]]]:
    """Run the query and return ``{name: [way, ...]}``; each way is a list of (lon, lat).

    ``cache``: a path to snapshot the raw Overpass payload into. OSM is a MUTABLE external
    database, so a track whose geometry comes from it is only reproducible while nobody edits the
    ways it names — retag County Road 116 or the Lariat's ways and the track silently rebuilds
    different, with no way to see what changed (L2 wants config + sources to be enough). The
    snapshot is keyed by a fingerprint of the actual query, so changing the route or bbox ignores
    the old file instead of quietly reusing it. Delete the file to re-fetch.
    """
    query = build_query(bbox, road_names)
    fingerprint = hashlib.sha256(query.encode()).hexdigest()[:16]
    if cache is not None:
        cache = Path(cache)
        if cache.is_file():
            try:
                snap = json.loads(cache.read_text(encoding="utf-8"))
                if snap.get("query_fingerprint") == fingerprint:
                    print(f"  [overpass] using cached snapshot {cache.name} "
                          f"({len(snap['payload'].get('elements', []))} elements, "
                          f"fetched {snap.get('fetched_utc', '?')})")
                    return _parse_payload(snap["payload"], road_names)
                print(f"  [overpass] {cache.name} is for a different query — re-fetching")
            except (json.JSONDecodeError, KeyError):
                print(f"  [overpass] {cache.name} unreadable — re-fetching")
    body = urllib.parse.urlencode({"data": query}).encode()
    payload: dict = {}
    for attempt in range(retries):
        req = urllib.request.Request(
            OVERPASS_URL,
            data=body,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=150) as resp:
                payload = json.loads(resp.read().decode())
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))  # back off on transient 504/timeout

    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"query_fingerprint": fingerprint,
                                     "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                     "bbox": list(bbox), "road_names": list(road_names),
                                     "payload": payload}), encoding="utf-8")
        print(f"  [overpass] snapshotted {len(payload.get('elements', []))} elements -> {cache.name}")
    return _parse_payload(payload, road_names)


def _parse_payload(payload: dict, road_names: list[str]) -> dict[str, list[list[Vertex]]]:
    out: dict[str, list[list[Vertex]]] = {n: [] for n in road_names}
    refs = {n: n[4:] for n in road_names if n.startswith("ref:")}
    ids = {n: {int(i) for i in n[3:].split(",")} for n in road_names if n.startswith("id:")}
    for el in payload.get("elements", []):
        if el.get("type") != "way":
            continue
        tags = el.get("tags", {})
        geom = [(g["lon"], g["lat"]) for g in el.get("geometry") or []]
        if len(geom) < 2:
            continue
        name = tags.get("name")
        if name in out:
            out[name].append(geom)
        way_refs = [r.strip() for r in (tags.get("ref") or "").split(";")]
        for entry, ref in refs.items():
            if ref in way_refs and "motorway" not in (tags.get("highway") or ""):
                out[entry].append(geom)
        for entry, wanted in ids.items():
            if el.get("id") in wanted:
                out[entry].append(geom)
    return out


# Drivable highway classes to map-match a GPS drive against (excludes footways/cycleways/paths).
DRIVABLE = ("motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|"
            "tertiary|tertiary_link|residential|unclassified|service|living_street|road")


def _post(query: str, *, retries: int = 3) -> dict:
    """POST an Overpass QL query and return the parsed JSON (shared HTTP + retry plumbing)."""
    body = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(retries):
        req = urllib.request.Request(
            OVERPASS_URL, data=body,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return {}


def fetch_drivable_ways(bbox: tuple[float, float, float, float], *, timeout: int = 120) -> list[dict]:
    """Every drivable OSM way in the bbox, for map-matching: ``[{id, name, highway, geom:[(lon,lat)]}]``.
    Unlike :func:`fetch_ways` (named route roads only), this pulls the whole road network so a recorded
    drive can be snapped onto it regardless of what the streets are called."""
    s, w, n, e = bbox
    query = (f'[out:json][timeout:{timeout}];\n'
             f'way["highway"~"^({DRIVABLE})$"]({s},{w},{n},{e});\nout geom;')
    payload = _post(query)
    out: list[dict] = []
    for el in payload.get("elements", []):
        if el.get("type") != "way":
            continue
        geom = [(g["lon"], g["lat"]) for g in el.get("geometry") or []]
        if len(geom) >= 2:
            out.append({"id": el.get("id"), "name": el.get("tags", {}).get("name"),
                        "highway": el.get("tags", {}).get("highway"), "geom": geom})
    return out


def fetch_highways_by_class(
    bbox: tuple[float, float, float, float],
    classes: list[str],
    *,
    refs: list[str] | None = None,
    timeout: int = 180,
) -> list[dict]:
    """Every OSM way whose ``highway`` tag is one of ``classes`` inside bbox (s,w,n,e), with geometry
    and the tags a freeway network cares about. This is how the ``osm-network`` source pulls a whole
    freeway box (motorway + motorway_link) straight from OSM: mainlines (both carriageways) AND every
    ramp / interchange connector, since on/off ramps and cloverleaf N<->S connectors are all
    ``motorway_link`` ways.

    ``refs`` (e.g. ``["I 5", "I 8", "CA 52", "CA 163"]``) restricts the MAINLINE ways (non-``*_link``)
    to those exact OSM ``ref`` tags, so a parallel freeway threading the same box (e.g. I-805) is
    excluded without touching the ramps — link/ramp ways are kept regardless (their orphans are pruned
    later by the largest-connected-component filter). Returns
    ``[{id, name, ref, highway, layer, bridge, geom:[(lon,lat)]}]``."""
    s, w, n, e = bbox
    rx = "|".join(classes)
    query = (f'[out:json][timeout:{timeout}];\n'
             f'way["highway"~"^({rx})$"]({s},{w},{n},{e});\nout geom;')
    payload = _post(query)
    refset = set(refs) if refs else None
    out: list[dict] = []
    for el in payload.get("elements", []):
        if el.get("type") != "way":
            continue
        geom = [(g["lon"], g["lat"]) for g in el.get("geometry") or []]
        if len(geom) < 2:
            continue
        tags = el.get("tags", {})
        hw = str(tags.get("highway", ""))
        if refset is not None and not hw.endswith("_link") and tags.get("ref") not in refset:
            continue   # a mainline carriageway that isn't one of the requested freeways -> skip
        out.append({"id": el.get("id"), "name": tags.get("name"), "ref": tags.get("ref"),
                    "highway": tags.get("highway"), "layer": tags.get("layer"),
                    "bridge": tags.get("bridge"), "geom": geom})
    return out


def fetch_drivable_ways(bbox: tuple[float, float, float, float], *, timeout: int = 120) -> list[dict]:
    """Every drivable OSM way in the bbox, for map-matching: ``[{id, name, highway, geom:[(lon,lat)]}]``.
    Unlike :func:`fetch_ways` (named route roads only), this pulls the whole road network so a recorded
    drive can be snapped onto it regardless of what the streets are called."""
    s, w, n, e = bbox
    query = (f'[out:json][timeout:{timeout}];\n'
             f'way["highway"~"^({DRIVABLE})$"]({s},{w},{n},{e});\nout geom;')
    payload = _post(query)
    out: list[dict] = []
    for el in payload.get("elements", []):
        if el.get("type") != "way":
            continue
        geom = [(g["lon"], g["lat"]) for g in el.get("geometry") or []]
        if len(geom) >= 2:
            out.append({"id": el.get("id"), "name": el.get("tags", {}).get("name"),
                        "highway": el.get("tags", {}).get("highway"), "geom": geom})
    return out
