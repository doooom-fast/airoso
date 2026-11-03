"""Assign REAL per-vertex road widths from OSM lanes — Sand Creek et al. felt like half the real road
space because every vertex was a flat ``default_width_m``. This map-matches the EXISTING centerline
(keeps the route) to OSM drivable ways per vertex, computes curb-to-curb pavement width from each way's
``lanes``/class, smooths the transitions, and rewrites ``data/centerline.local.json`` widths_m in place.

OSM has no ``width`` tags on these streets but tags ``lanes`` on the arterials; residential side streets
are untagged (→ class default). Width = ``max(lanes, class-min) × lane_w + class curb-to-curb allowance``
(parking/turn/shoulder), so a primary arterial (Colorado Blvd, Quebec) comes out ~2× a side street, matching
reality. Also detects OSM junction nodes near the centerline and writes ``data/intersections.local.json`` for
build_mesh to lay paved intersection pads.

    python -m scripts.gps.widths_from_osm tracks/sand-creek
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scripts.tls import https_context

Vertex = tuple[float, float]
LANE_W = 3.5
# class → (minimum lane count, curb-to-curb allowance beyond the lanes: parking/turn/shoulder/gutter, m)
CLASS = {
    "motorway": (4, 4.0), "trunk": (4, 4.0), "primary": (4, 6.0), "secondary": (3, 5.0),
    "tertiary": (2, 4.0), "unclassified": (2, 3.0), "residential": (2, 4.0), "service": (1, 1.5),
}
# The default table is tuned for URBAN US arterials (parking/turn lanes, 4-lane trunk floors). On a
# rural/mountain route those assumptions systematically over-widen: the Lariat Trail is a 6.5 m
# mountain road, not an 11 m boulevard, and 2-lane US-40 is not an 18 m runway. Select with
# route.width_profile = "mountain" in track.config.json — narrower lanes (3.0 m), no urban
# allowances, class minimums at the rural reality (2 lanes).
MOUNTAIN_LANE_W = 3.0
MOUNTAIN_CLASS = {
    "motorway": (2, 3.0), "trunk": (2, 3.0), "primary": (2, 4.0), "secondary": (2, 3.0),
    "tertiary": (2, 0.5), "unclassified": (2, 0.3), "residential": (2, 0.0), "service": (1, 1.0),
}
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
           "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
# A mirror is a separate Overpass server that copies OSM on its own schedule, and one that has
# stopped copying keeps answering with old data. 2026-10-11: overpass.kumi.systems served OSM as of
# 2026-07-28 while overpass-api.de was minutes old, and this module fell back to it without a word
# (the July Lariat snapshot holds OSM as of 2026-07-02, fetched 07-27). A live answer whose
# osm3s.timestamp_osm_base is older than this is never written to the width snapshot unless forced.
# Healthy mirrors lag minutes to hours; a week behind means the copying stopped.
# Per track: route.osm_max_age_days. One-off override: --allow-stale-osm. A snapshot already on
# disk is never judged by age: pinning old data on purpose is what the snapshot is for.
OSM_MAX_AGE_DAYS = 7.0
_RETRY_PAUSE_S = 2.0


def haversine_m(a: Vertex, b: Vertex) -> float:
    r = 6_371_000.0
    (lo1, la1), (lo2, la2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
DRIVABLE = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|service"


def osm_base(payload: dict) -> str | None:
    """The OSM data timestamp an Overpass answer was computed from (``osm3s.timestamp_osm_base``):
    how current the server's copy of OSM is, not when it was fetched. ``None`` if absent."""
    return ((payload or {}).get("osm3s") or {}).get("timestamp_osm_base")


def osm_age_days(payload: dict, now: datetime | None = None) -> float | None:
    """Age in days of the payload's OSM data (``None`` when the timestamp is missing or unreadable)."""
    try:
        t = datetime.strptime(osm_base(payload), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return ((now or datetime.now(timezone.utc)) - t).total_seconds() / 86400.0


def _too_old(age: float | None, max_age_days: float | None) -> bool:
    """Unknown age counts as too old: freshness that cannot be shown is not assumed."""
    return max_age_days is not None and (age is None or age > max_age_days)


def _describe(payload: dict, age: float | None) -> str:
    base = osm_base(payload)
    if age is not None:
        when = f"OSM data as of {base} ({age:.1f} days old)"
    elif base:
        when = f"OSM data timestamp unreadable ({base!r})"
    else:
        when = "OSM data timestamp MISSING (no osm3s.timestamp_osm_base)"
    remark = (payload or {}).get("remark")
    return when + (f"; server remark: {remark}" if remark else "")


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or url


def _overpass(query: str, *, timeout: int = 120, max_age_days: float | None = None) -> tuple[dict, str]:
    """POST ``query`` to the mirrors in order and return ``(payload, mirror_url)``.

    Every failure, every fallback and the OSM data timestamp of the answer are printed. With
    ``max_age_days``, an answer older than that (or without a timestamp) is set aside and the next
    mirror is tried; if no mirror answers fresh, the freshest stale answer is returned and the caller
    decides (:func:`fetch_ways` refuses to snapshot it unless forced)."""
    last = None
    stale: list[tuple[float, dict, str]] = []
    for m in MIRRORS:
        for attempt in range(2):
            try:
                req = urllib.request.Request(m, data=query.encode(), headers={"User-Agent": "k10-colorado/1.0"})
                d = json.load(urllib.request.urlopen(req, timeout=timeout, context=https_context()))
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  [widths_from_osm] {_host(m)} failed (try {attempt + 1}/2): {e}")
                time.sleep(_RETRY_PAUSE_S)
                continue
            age = osm_age_days(d)
            role = "primary" if m == MIRRORS[0] else f"FALLBACK mirror (not {_host(MIRRORS[0])})"
            print(f"  [widths_from_osm] {_host(m)} answered, {role}: {_describe(d, age)}")
            if _too_old(age, max_age_days):
                print(f"  [widths_from_osm] {_host(m)} fails the {max_age_days:g}-day freshness limit; "
                      f"trying the next mirror")
                stale.append((age if age is not None else float("inf"), d, m))
                break
            return d, m
    if stale:
        _, d, m = min(stale, key=lambda s: s[0])
        return d, m
    raise SystemExit(f"overpass unreachable (all mirrors): {last}")


def fetch_ways(bbox: tuple[float, float, float, float], cache=None, *,
               max_age_days: float | None = OSM_MAX_AGE_DAYS, allow_stale: bool = False) -> list[dict]:
    """Every drivable OSM way in bbox WITH the tags we need: id, name, highway, lanes, width, node ids, geom.

    ``cache`` snapshots the raw payload so a width pass is reproducible without live Overpass — OSM
    is mutable, and a lane retag silently changes every width on the track (L2). Keyed by a
    fingerprint of the query, so a changed bbox re-fetches instead of reusing the wrong snapshot.

    A live answer whose OSM data is older than ``max_age_days`` (or carries no timestamp) is NOT
    written to ``cache``: the stage stops (SystemExit) naming the mirror and its data timestamp,
    unless ``allow_stale``. ``max_age_days=None`` means no limit. Without a ``cache`` it only warns.
    The snapshot records which mirror answered (``source``) and its data timestamp (``osm_base``)."""
    s, w, n, e = bbox
    q = (f'[out:json][timeout:120];(way["highway"~"^({DRIVABLE})(_link)?$"]({s},{w},{n},{e}););out geom;')
    d = None
    fp = hashlib.sha256(q.encode()).hexdigest()[:16]
    if cache is not None:
        cache = Path(cache)
        if cache.is_file():
            try:
                snap = json.loads(cache.read_text(encoding="utf-8"))
                if snap.get("query_fingerprint") == fp:
                    print(f"  [widths_from_osm] using cached snapshot {cache.name} "
                          f"(fetched {snap.get('fetched_utc','?')} from {snap.get('source', 'an unrecorded mirror')}, "
                          f"OSM data as of {osm_base(snap['payload']) or 'unknown'})")
                    d = snap["payload"]
                else:
                    print(f"  [widths_from_osm] {cache.name} is for a different bbox — re-fetching")
            except (json.JSONDecodeError, KeyError):
                pass
    if d is None:
        d, mirror = _overpass(q, max_age_days=max_age_days)
        age = osm_age_days(d)
        stale = _too_old(age, max_age_days)
        if stale:
            what = (f"the freshest answer came from {mirror} with {_describe(d, age)}, "
                    f"older than the {max_age_days:g}-day limit (route.osm_max_age_days)")
            if cache is not None and not allow_stale:
                raise SystemExit(
                    f"[widths_from_osm] REFUSING to snapshot {cache.name}: {what}. Writing it would pin "
                    f"old OSM tags under a current query fingerprint. Retry later, raise "
                    f"route.osm_max_age_days, or re-run with --allow-stale-osm to snapshot it anyway.")
            print(f"  [widths_from_osm] WARNING {what}"
                  + (" - snapshotting it anyway (allow_stale)" if cache is not None else ""))
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            snap = {"query_fingerprint": fp,
                    "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "source": mirror, "osm_base": osm_base(d),
                    "bbox": [s, w, n, e], "payload": d}
            if stale:
                snap["stale_allowed"] = True
            cache.write_text(json.dumps(snap), encoding="utf-8")
            print(f"  [widths_from_osm] snapshotted {len(d.get('elements',[]))} ways from {_host(mirror)} "
                  f"(OSM data as of {osm_base(d) or 'unknown'}) -> {cache.name}")
    ways = []
    for el in d.get("elements", []):
        if el.get("type") != "way" or "geometry" not in el:
            continue
        t = el.get("tags", {})
        ways.append({"id": el["id"], "name": t.get("name"), "ref": t.get("ref"), "highway": t.get("highway"),
                     "lanes": t.get("lanes"), "width": t.get("width"), "nodes": el.get("nodes", []),
                     "geom": [(g["lon"], g["lat"]) for g in el["geometry"]]})
    return ways


def pavement_width(way: dict | None, profile: str = "urban") -> float:
    """Curb-to-curb metres for an OSM way (or a sane default if unmatched)."""
    table, lane_w = (MOUNTAIN_CLASS, MOUNTAIN_LANE_W) if profile == "mountain" else (CLASS, LANE_W)
    if way is None:
        return 6.5 if profile == "mountain" else 9.0
    if way.get("width"):
        try:
            return float(str(way["width"]).split()[0])
        except ValueError:
            pass
    hw = way.get("highway", "residential")
    if hw.endswith("_link"):                   # interchange ramp: one lane + shoulder, either profile
        return round(lane_w + 2.0, 1)
    cmin, extra = table.get(hw, (2, 3.0))
    # An explicit lanes tag is ground truth — a tagged 2-lane secondary is 2 lanes, not the class
    # floor (flooring turned Sand Creek's tagged 1- and 2-lane streets into 15.5 m highways).
    # The class floor only fills in when OSM doesn't say.
    try:
        lanes = max(int(way["lanes"]), 1)
    except (TypeError, ValueError):
        lanes = cmin
    return round(lanes * lane_w + extra, 1)


def _match_per_vertex(cl: list[Vertex], ways: list[dict], *, max_snap_m: float = 26.0, min_run: int = 5):
    """Nearest OSM way index per centerline vertex (−1 = off-network), de-jittered into runs ≥ min_run."""
    lat0 = sum(p[1] for p in cl) / len(cl)
    kx = 111320.0 * math.cos(math.radians(lat0)); ky = 110540.0; lon0 = cl[0][0]

    def loc(lon, lat):
        return ((lon - lon0) * kx, (lat - lat0) * ky)

    segs = []  # (ax, ay, bx, by, way_idx)
    for wi, wv in enumerate(ways):
        xy = [loc(lo, la) for lo, la in wv["geom"]]
        for i in range(len(xy) - 1):
            segs.append((xy[i][0], xy[i][1], xy[i + 1][0], xy[i + 1][1], wi))
    idx = []
    for lon, lat in cl:
        px, py = loc(lon, lat)
        best_d2, best_wi = max_snap_m * max_snap_m, -1
        for ax, ay, bx, by, wi in segs:
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            cx, cy = ax + t * dx, ay + t * dy
            d2 = (px - cx) ** 2 + (py - cy) ** 2
            if d2 < best_d2:
                best_d2, best_wi = d2, wi
        idx.append(best_wi)
    # de-jitter: replace runs shorter than min_run with the previous kept way
    out = idx[:]
    i = 0
    n = len(out)
    while i < n:
        j = i
        while j < n and out[j] == out[i]:
            j += 1
        if j - i < min_run and i > 0:
            for k in range(i, j):
                out[k] = out[i - 1]
        i = j
    return out


def _smooth(vals: list[float], win: int = 9) -> list[float]:
    n = len(vals); h = win // 2
    return [sum(vals[max(0, i - h):min(n, i + h + 1)]) / (min(n, i + h + 1) - max(0, i - h)) for i in range(n)]


MAJOR = {"motorway", "trunk", "primary", "secondary", "tertiary"}   # "real" intersections cross these


def road_ident(wv: dict, wi: int = -1) -> str:
    """One ROAD's identity across the OSM ways it is split into: its name, else its ref, else the way itself. OSM
    splits a street wherever a tag changes, at every bridge end and at every side street; the same name/ref continuing
    is one road (detect_turn_corners, from the Lariat's switchbacks; detect_junctions since ledger 0070 B1)."""
    return (wv.get("name") or wv.get("ref") or f"way{wv.get('id', wi)}").strip().lower()


def lanes_tag(wv: dict | None) -> int | None:
    """The way's OSM ``lanes`` tag (both directions), or None where untagged (ledger 0070 B2: the paint's lane count)."""
    try:
        return max(int(wv["lanes"]), 1) if wv and wv.get("lanes") else None
    except (TypeError, ValueError):
        return None


def detect_junctions(ways: list[dict], cl: list[Vertex], *, near_m: float = 16.0,
                     profile: str = "urban") -> list[dict]:
    """Real intersections the circuit drives THROUGH: OSM nodes where ≥2 DISTINCT ARTERIAL (tertiary+) roads meet,
    within ``near_m`` of the racing line — the corners where the circuit turns street-to-street and the
    major crossings, NOT every minor residential T-junction. Returns ``[{idx, size}]`` — the centerline
    vertex index nearest the junction + the intersection's pavement size — used to FLARE the road ribbon
    width there (one continuous surface, no overlapping pad → no bumps).

    DISTINCT ROADS, NOT WAYS (ledger 0070 B1): counting ways flared every node where OSM merely splits one arterial (a tag
    change, a bridge end, a side street's node): on Sand Creek 0.33.0, 50 of the 64 flared nodes were a bare way split
    (32) or a minor side street on one arterial (18). The arterial ways at the node must carry >= 2 road identities
    (road_ident); a residential side street is never one, since only MAJOR ways are counted."""
    from collections import defaultdict
    node_ll: dict[int, Vertex] = {}
    node_ways: dict[int, list[int]] = defaultdict(list)
    for wi, wv in enumerate(ways):
        for nid, (lo, la) in zip(wv.get("nodes", []), wv["geom"]):
            node_ll[nid] = (lo, la)
            node_ways[nid].append(wi)
    lat0 = sum(p[1] for p in cl) / len(cl)
    kx = 111320.0 * math.cos(math.radians(lat0)); ky = 110540.0
    clx = [c[0] * kx for c in cl]; clz = [c[1] * ky for c in cl]
    out: list[dict] = []
    for nid, wl in node_ways.items():
        major = {wi for wi in wl if ways[wi].get("highway") in MAJOR}
        if len({road_ident(ways[wi], wi) for wi in major}) < 2:
            continue
        lo, la = node_ll[nid]
        nx, nz = lo * kx, la * ky
        best_k, best_d2 = -1, near_m * near_m
        for k in range(len(cl)):
            d2 = (nx - clx[k]) ** 2 + (nz - clz[k]) ** 2
            if d2 < best_d2:
                best_d2, best_k = d2, k
        if best_k >= 0:
            out.append({"idx": best_k, "size": max(pavement_width(ways[wi], profile) for wi in major) + 3.0})
    return out


PADDED_RADIUS_M = 30.0   # [invented] route.padded_corners' default reach: a flare whose vertex is this near the corner node


def detect_turn_corners(ways: list[dict], cl: list[Vertex], *, profile: str = "urban",
                        kink_deg: float = 45.0, near_m: float = 16.0,
                        padded: list | None = None) -> list[dict]:
    """Corners where the LAP ITSELF turns street-to-street hard — junction-grade pavement
    regardless of road class. detect_junctions gates on >=2 ARTERIAL ways, which misses a
    minor-street corner mouth entirely (Kevin: "a corner at the bottom of the hill that is
    impossible to make ... treat it like a wide intersection"). A heading kink > kink_deg
    concentrated within +-12 m, at a vertex near an OSM node shared by >=2 drivable ways,
    is a paved corner — flare it like an intersection. Mountain hairpins never trigger:
    they are one way bending back on itself, not two ways sharing a node.

    ``padded`` (ledger 0070 D-pads, opt-in per track: route.padded_corners): [(lon, lat, radius_m)] — a corner whose
    vertex lies within radius_m of one is NOT flared: an authored junction pad owns that pavement (REALISM §8), and a
    flare swept under it is a second, overlapping surface. Absent or empty: byte-identical to before."""
    from collections import defaultdict
    lat0 = sum(p[1] for p in cl) / len(cl)
    kx = 111320.0 * math.cos(math.radians(lat0)); ky = 110540.0
    xs = [c[0] * kx for c in cl]; zs = [c[1] * ky for c in cl]
    st = [0.0]
    for i in range(1, len(cl)):
        st.append(st[-1] + math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]))
    node_ll: dict = {}
    node_ways: dict = defaultdict(set)
    for wi, wv in enumerate(ways):
        for nid, (lo, la) in zip(wv.get("nodes", []), wv["geom"]):
            node_ll[nid] = (lo * kx, la * ky)
            node_ways[nid].add(wi)

    def _ident(wi):
        return road_ident(ways[wi], wi)

    # >=2 DISTINCT ROADS at the node — OSM splits one road into multiple ways at every junction
    # node, so counting ways flags every hairpin of a split mountain road as a 'corner' (the
    # Lariat's switchbacks all got 14 m junction pads). Same name/ref continuing = one road.
    shared = [(node_ll[nid], ws) for nid, ws in node_ways.items()
              if len({_ident(w) for w in ws}) >= 2]

    def hd(i):
        a, b = max(0, i - 2), min(len(cl) - 1, i + 2)
        return math.atan2(zs[b] - zs[a], xs[b] - xs[a])

    out: list[dict] = []
    i, n = 0, len(cl)
    while i < n:
        j0 = i
        while j0 > 0 and st[i] - st[j0] < 12.0:
            j0 -= 1
        j1 = i
        while j1 < n - 1 and st[j1] - st[i] < 12.0:
            j1 += 1
        d = abs((math.degrees(hd(j1) - hd(j0)) + 180.0) % 360.0 - 180.0)
        if d > kink_deg:
            px, pz = xs[i], zs[i]
            near = [ws for (qx, qz), ws in shared if (qx - px) ** 2 + (qz - pz) ** 2 <= near_m * near_m]
            if near:
                if any((lo * kx - px) ** 2 + (la * ky - pz) ** 2 <= r * r for lo, la, r in (padded or ())):
                    i = j1 + 5  # a padded corner: the pad is its pavement, no flare (route.padded_corners)
                    continue
                wset = set().union(*near)
                two = sorted((pavement_width(ways[w], profile) for w in wset), reverse=True)[:2]
                out.append({"idx": i, "size": round(max(14.0, sum(two) * 0.9), 1)})
                i = j1 + 5      # one corner, one flare
                continue
        i += 1
    return out


def flare_widths(widths: list[float], cl: list[Vertex], junctions: list[dict], *, blend_m: float = 7.0) -> list[float]:
    """Widen the road at each junction to the intersection's pavement size, tapering back to the street
    width over ``blend_m`` — a smooth flare baked INTO the ribbon width (no overlapping pad, so no bump).
    Half the pad extends ahead/behind the junction along the road; the taper reaches ``blend_m`` past that."""
    lat0 = sum(p[1] for p in cl) / len(cl)
    kx = 111320.0 * math.cos(math.radians(lat0)); ky = 110540.0
    arc = [0.0]
    for i in range(1, len(cl)):
        arc.append(arc[-1] + math.hypot((cl[i][0] - cl[i - 1][0]) * kx, (cl[i][1] - cl[i - 1][1]) * ky))
    out = widths[:]
    n = len(widths)
    # LAP WRAP. Arc distance alone makes the start/finish line the far end of the track from
    # itself, so a junction sitting near the seam flares one side and cannot reach the other:
    # Lake Murray's width collapsed 26.98 -> 17.00 m across the seam, jumping each ribbon edge 5 m
    # sideways in one 2.4 m step (a 0.43 m severe step, its worst). Fourth instance of this defect
    # class after the elevation profile, the drive test's speed stencil and the ribbon tangent.
    _closed = (len(cl) > 2 and abs(cl[0][0] - cl[-1][0]) < 1e-9 and abs(cl[0][1] - cl[-1][1]) < 1e-9)
    _lap = arc[-1] or 1.0
    for j in junctions:
        k = min(j["idx"], n - 1)
        size = j["size"]
        half = size / 2.0                                 # full flare within ±half of the junction
        reach = half + blend_m
        for i in range(n):
            d = abs(arc[i] - arc[k])
            if _closed:
                d = min(d, _lap - d)                      # the seam is adjacent to itself
            if d > reach:
                continue
            f = 1.0 if d <= half else max(0.0, 1.0 - (d - half) / blend_m)   # 1 at the box, taper to 0
            out[i] = max(out[i], out[i] + (size - out[i]) * f)              # only ever widens
    return out


def max_age_from_route(route: dict) -> float:
    """``route.osm_max_age_days`` (a positive number of days), or :data:`OSM_MAX_AGE_DAYS` when absent."""
    v = (route or {}).get("osm_max_age_days")
    if v is None:
        return OSM_MAX_AGE_DAYS
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
        raise ValueError(f"route.osm_max_age_days must be a positive number of days, got {v!r}")
    return float(v)


def build(project_dir: str | Path, *, allow_stale: bool = False, max_age_days: float | None = None) -> dict:
    project = Path(project_dir)
    data = project / "data"
    gj = json.loads((data / "centerline.geojson").read_text())
    feats = gj.get("features", [gj])
    line = next((f for f in feats if f.get("geometry", {}).get("type") == "LineString"), None)
    cl = [(c[0], c[1]) for c in line["geometry"]["coordinates"]]
    local = json.loads((data / "centerline.local.json").read_text())
    n_local = len(local["widths_m"])
    if len(cl) != n_local:
        print(f"  [widths_from_osm] NOTE centerline.geojson has {len(cl)} pts, local has {n_local}; "
              f"matching on the shorter and nearest-resampling widths")
    lons = [c[0] for c in cl]; lats = [c[1] for c in cl]
    pad = 0.0015
    bbox = (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad)
    route = json.loads((project / "track.config.json").read_text()).get("route", {}) or {}
    profile = route.get("width_profile", "urban")
    ways = fetch_ways(bbox, cache=data / "osm.widths.cache.json",
                      max_age_days=max_age_days if max_age_days is not None else max_age_from_route(route),
                      allow_stale=allow_stale)
    # IDENTITY LOCK: freeway-class ways may donate widths ONLY when the route declares them
    # (by name, "ref:NAME" or "id:N,N"). A street circuit beside I-270/US-85 was inheriting
    # freeway widths from nearest-way matching — "sand creek is fucking highways".
    _decl_names, _decl_refs, _decl_ids = set(), set(), set()
    for _r in route.get("roads") or []:
        if _r.startswith("ref:"):
            _decl_refs.add(_r[4:].strip().lower())
        elif _r.startswith("id:"):
            _decl_ids.update(int(t) for t in _r[3:].split(",") if t.strip())
        else:
            _decl_names.add(_r.strip().lower())
    _FREEWAY = {"motorway", "trunk", "motorway_link", "trunk_link"}
    _banned = 0
    _kept = []
    for _w in ways:
        if _w.get("highway") in _FREEWAY:
            _nm = (_w.get("name") or "").strip().lower()
            _rf = (_w.get("ref") or "").strip().lower()
            if _w["id"] not in _decl_ids and _nm not in _decl_names \
                    and not (_rf and any(_rf == d or d in _rf.split(";") for d in _decl_refs)):
                _banned += 1
                continue
        _kept.append(_w)
    if _banned:
        print(f"  [widths_from_osm] identity lock: {_banned} undeclared freeway-class ways excluded from matching")
    ways = _kept
    # cache street geometry for the pack stage's OSM-style preview (no network at pack time)
    (data / "osm.ways.json").write_text(json.dumps(
        [{"highway": w.get("highway"), "geom": w["geom"]} for w in ways]), encoding="utf-8")
    idx = _match_per_vertex(cl, ways)
    widths_cl = [pavement_width(ways[wi] if wi >= 0 else None, profile) for wi in idx]
    widths_cl = _smooth(widths_cl)
    # FLARE the ribbon at the real intersections the circuit drives through (widen the road itself, one
    # continuous surface — NOT an overlapping pad, which poked above the sloped road and read as bumps).
    widths_base_cl = widths_cl[:]        # pre-flare: the street's own line (sidewalks follow THIS)
    lanes_cl = [lanes_tag(ways[wi] if wi >= 0 else None) for wi in idx]   # B2: the paint's lane count per vertex
    junctions = detect_junctions(ways, cl, profile=profile)
    # ledger 0070 D-pads (opt-in): route.padded_corners [{"name", "at": [lat, lon], "radius_m"}] — an authored junction
    # pad owns the pavement there, so neither flare is swept under it (the corner's, nor a junction node's inside it)
    padded = [(float(c["at"][1]), float(c["at"][0]), float(c.get("radius_m", PADDED_RADIUS_M)))
              for c in (route.get("padded_corners") or [])]
    if padded:
        _lat0p = sum(p[1] for p in cl) / len(cl)
        _kxp = 111320.0 * math.cos(math.radians(_lat0p)); _kyp = 110540.0
        _n0 = len(junctions)
        junctions = [j for j in junctions
                     if not any(((cl[j["idx"]][0] - lo) * _kxp) ** 2 + ((cl[j["idx"]][1] - la) * _kyp) ** 2 <= r * r
                                for lo, la, r in padded)]
        print(f"  [widths_from_osm] route.padded_corners: {len(padded)} padded corner(s) — no corner flare there, "
              f"{_n0 - len(junctions)} junction flare(s) inside them dropped")
    corners = detect_turn_corners(ways, cl, profile=profile, padded=padded)
    if corners:
        print(f"  [widths_from_osm] {len(corners)} hard route corners flared to junction grade "
              f"(sizes {[c['size'] for c in corners]})")
    widths_cl = flare_widths(widths_cl, cl, junctions + corners)
    # DECLARED CORNER FLARES ONLY (route.wide_corners: [{station_m, width_m}]). Auto fold
    # widening is OFF: three days of data show a swept ribbon cannot carry junction-width
    # pavement through a fold — every auto-widened fold shipped pleat steps. Corners a DRIVER
    # flags get a taper-aware flare + (in build_mesh) a local plateau and a paved disc.
    _lat0u = sum(p[1] for p in cl) / len(cl)
    _kxu = 111320.0 * math.cos(math.radians(_lat0u)); _kyu = 110540.0
    _stu = [0.0]
    for _i in range(1, len(cl)):
        _stu.append(_stu[-1] + math.hypot((cl[_i][0] - cl[_i - 1][0]) * _kxu,
                                          (cl[_i][1] - cl[_i - 1][1]) * _kyu))
    def _hdu(i):
        a, b = max(0, i - 2), min(len(cl) - 1, i + 2)
        return math.atan2((cl[b][1] - cl[a][1]) * _kyu, (cl[b][0] - cl[a][0]) * _kxu)

    _folds = []
    # AUTO tier restored at rc10 magnitude: folds > 110 deg (±15 m window) get a MODEST 10 m
    # floor — enough to drive (rc10 shipped ~9.6 net there and passed), narrow enough that the
    # fold fans stay at the baseline pleat level. Junction-width corners remain a DRIVER call.
    _i = 0
    while _i < len(cl):
        _j0 = _i
        while _j0 > 0 and _stu[_i] - _stu[_j0] < 15.0:
            _j0 -= 1
        _j1 = _i
        while _j1 < len(cl) - 1 and _stu[_j1] - _stu[_i] < 15.0:
            _j1 += 1
        _du = abs((math.degrees(_hdu(_j1) - _hdu(_j0)) + 180.0) % 360.0 - 180.0)
        if _du > 110.0:
            _folds.append((_i, 10.0, round(_du)))
            while _i < len(cl) - 1 and _stu[_i] - _stu[_j0] < 45.0:
                _i += 1
            continue
        _i += 1
    for _wc in route.get("wide_corners", []) or []:
        _si = min(range(len(cl)), key=lambda k: abs(_stu[k] - float(_wc["station_m"])))
        _folds.append((_si, float(_wc.get("width_m", 14.0)), "declared"))
    for _ai, _tw, _deg in _folds:
        for _i in range(len(cl)):
            _d = max(0.0, abs(_stu[_i] - _stu[_ai]) - 18.0)
            _lb = _tw - 0.14 * _d
            if _lb > widths_cl[_i]:
                widths_cl[_i] = _lb
    if _folds:
        print(f"  [widths_from_osm] declared corner flares: "
              f"{[(round(_stu[a]), w) for a, w, d in _folds]}")
    # resample widths to the LOCAL vertex count if they differ (nearest by fractional index)
    if len(widths_cl) != n_local:
        widths = [widths_cl[min(len(widths_cl) - 1, round(i * (len(widths_cl) - 1) / max(n_local - 1, 1)))]
                  for i in range(n_local)]
    else:
        widths = widths_cl
    widths = [round(w, 2) for w in widths]
    if len(widths_base_cl) != n_local:
        widths_base = [widths_base_cl[min(len(widths_base_cl) - 1,
                       round(i * (len(widths_base_cl) - 1) / max(n_local - 1, 1)))] for i in range(n_local)]
    else:
        widths_base = widths_base_cl
    # THE ORDER (2026-11-01, review of the Lariat integration; ledger 0048 "Started"). These arrays are per
    # centerline.geojson vertex, but centerline.local.json's ring was re-ordered by projection (route.start_at /
    # route.reverse: High Plains by 815 of 1,074 points) AFTER the geojson was written, so writing them 1:1 put every
    # width k vertices off on a rotated ring. projection records the permutation (source_index); it is applied here
    # once, and widths_order says so. A track with no recorded permutation (every track built before 2026-10-29, and
    # any unrotated ring) is the identity: byte-identical but for the new key.
    if len(lanes_cl) != n_local:
        lanes_v = [lanes_cl[min(len(lanes_cl) - 1, round(i * (len(lanes_cl) - 1) / max(n_local - 1, 1)))]
                   for i in range(n_local)]
    else:
        lanes_v = lanes_cl
    from scripts.geometry.projection import in_local_order
    local["widths_base_m"] = [round(w, 2) for w in in_local_order(local, widths_base)]
    local["lanes_osm"] = in_local_order(local, lanes_v)      # ledger 0070 B2: OSM lanes per vertex, None = untagged
    local["widths_m"] = in_local_order(local, widths)
    local["widths_order"] = "local"
    local["default_width_m"] = round(sum(widths) / len(widths), 2)
    (data / "centerline.local.json").write_text(json.dumps(local), encoding="utf-8")
    # the overlapping-pad approach is gone; remove any stale pad file so build_mesh lays none.
    try:
        (data / "intersections.local.json").unlink()
    except OSError:
        pass

    # per-street summary
    from collections import defaultdict
    seg = defaultdict(int)
    for wi in idx:
        seg[wi] += 1
    named = []
    for wi, cnt in sorted(seg.items(), key=lambda x: -x[1]):
        wv = ways[wi] if wi >= 0 else None
        named.append((cnt, (wv or {}).get("name") or ("off-network" if wi < 0 else f"way{wi}"),
                      (wv or {}).get("highway", "-"), (wv or {}).get("lanes", "-"), pavement_width(wv, profile)))
    import statistics
    stats = {"vertices": n_local, "min_w": min(widths), "median_w": statistics.median(widths),
             "max_w": max(widths), "matched_pct": round(100 * sum(1 for w in idx if w >= 0) / len(idx), 1),
             "junctions": len(junctions), "streets": named[:16]}
    return stats


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m scripts.gps.widths_from_osm")
    ap.add_argument("project_dir")
    ap.add_argument("--allow-stale-osm", action="store_true",
                    help="snapshot a live Overpass answer even if its OSM data is older than the limit")
    ap.add_argument("--max-osm-age-days", type=float, default=None,
                    help=f"override route.osm_max_age_days (default {OSM_MAX_AGE_DAYS:g})")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.max_osm_age_days is not None and not a.max_osm_age_days > 0:
        ap.error("--max-osm-age-days must be positive")
    st = build(a.project_dir, allow_stale=a.allow_stale_osm, max_age_days=a.max_osm_age_days)
    print(f"widths_from_osm: {st['vertices']} verts  matched {st['matched_pct']}%  "
          f"width min/median/max = {st['min_w']}/{st['median_w']}/{st['max_w']} m  "
          f"junction flares = {st['junctions']}")
    for cnt, nm, hw, ln, w in st["streets"]:
        print(f"  {cnt:5d}v  {nm:32s} {hw:12s} lanes={ln!s:>3}  -> {w} m")


if __name__ == "__main__":
    main()
