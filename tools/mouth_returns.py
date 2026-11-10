"""Through-mouth CORNER RETURNS: the pure half (no bpy) of tools/mouth_returns_blend.py, shared with
tools/gap_mouths_blend.py, tools/strip_seam_blend.py, tools/verify_mouth_corners.py and the tests (ledger 0086).

Kevin, 2026-11-07, on Sand Creek's grid streets: "They don't connect to the main road very well at all", "Doesn't
connect, floats", "Actually LM works, it's SC"; shown the fix, "Yes, build it". Ledger 0086 found every one of Sand
Creek's 113 mouths square and sunk: the street's no-curb edge strip runs to the cut and falls 0.16-0.22 m beside the host
edge, gap_mouths deletes the host's strip GAP_CORNER_M past it, and the prep lifts the ground in that gap to the road's
height - 0.02: a trench with a grass wall at its end, and the host's slab edge in the air over it (corner lip median
0.175 m, Lake Murray's 0.033 m).

Lake Murray's stubs (ledger 0054 Phase 5, tools/author_stubs_blend.py + tools/stub_geom.py) are the reference for "works":
a circular return from the host's edge round into the street's, the corner paved under it, the ground pinned to it.
This module carries that to THROUGH mouths, opt-in by `route.mouth_returns` (connector-name prefixes):

  * the circle's radius is MEASURED per corner (tools/mouth_radii.py off NAIP 2023; `route.mouth_radii_file`), not
    derived from the gap window as a stub's is; so the return starts at A* = K + tH a (tH = R / tan(phi / 2)), wherever
    that falls between two host rows, and runs straight along the host's edge from the host's own curb row A just past
    it (the "head"). A corner the imagery did not measure takes the median of the measured corners on the same host,
    else of all of them, and says so;
  * the edge profile is the track's (Sand Creek: route.edge, no curb, falling 0.20 m over 1.5 m), carried round the
    corner as it is: the grass meet keeps its own height (stub_geom.return_stations(meet_h=None)) and the ground is
    seamed along the return's lip (tools/strip_seam_blend.py, `strip_seam.connectors`) instead;
  * no barrier, no stub length: the street goes on.

Engine frame throughout: x east, y up, z north. A host / piece "row" is the assembler's (tools/mouth_weld.py layout).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

RETURNS_FILE = "data/mouth_returns.json"
DEFAULT_RADII = "source/mouth_radii.naip.json"
EDGE_FIT_FROM_M = 8.0    # the street's edge line is fitted on rows at least this far out AND past the weld's re-spread
EDGE_FIT_TO_M = 22.0     # [invented] ... and no further (a through street may curve; a stub was fitted to its end)
EDGE_FIT_ROWS = 3
MIN_TAIL_ROWS = 3        # J must leave at least this many street rows past it


def config(cfg):
    """(prefixes, radii file) from track.config.json route.mouth_returns (a list of connector-name prefixes, or
    {"prefixes": [...], "radii_file": ...}) and route.mouth_radii_file; ([], None) when not declared"""
    r = (cfg.get("route") or {}).get("mouth_returns")
    if not r:
        return [], None
    if isinstance(r, dict):
        pre = list(r.get("prefixes") or [])
        rf = r.get("radii_file")
    else:
        pre = list(r)
        rf = None
    rf = rf or (cfg.get("route") or {}).get("mouth_radii_file") or DEFAULT_RADII
    return pre, rf


def skip_list(cfg):
    """route.mouth_returns_skip: [{"piece", "end", "why"}] -> {(piece, end): why}; the named mouths get no returns (a
    mouth whose ground is owed separately, where a return would only move the defect: ledger 0086's owed spots)"""
    out = {}
    for r in (cfg.get("route") or {}).get("mouth_returns_skip") or []:
        if not r.get("why"):
            raise ValueError(f"route.mouth_returns_skip {r}: every row names its why")
        out[(r["piece"], r["end"])] = r["why"]
    return out


def selected(mo, prefixes):
    name = str(mo.get("piece") or mo.get("connector") or "")
    return any(name.startswith(p) for p in prefixes)


def corner_key(piece, end, e):
    return f"{piece}|{end}|{int(e):+d}"


def radius_for(radii, key, host):
    """(R, source): the measured radius, else the median of the measured corners on the same host, else of all"""
    rec = (radii or {}).get(key)
    if rec and rec.get("measured"):
        return float(rec["radius_m"]), "measured"
    same = sorted(float(r["radius_m"]) for r in (radii or {}).values() if r.get("measured") and r.get("host") == host)
    pool = same or sorted(float(r["radius_m"]) for r in (radii or {}).values() if r.get("measured"))
    if not pool:
        return None, "none measured"
    m = len(pool)
    med = pool[m // 2] if m % 2 else 0.5 * (pool[m // 2 - 1] + pool[m // 2])
    why = (rec or {}).get("why", "not in the radii file")
    return med, (f"median of {len(same)} measured on {host}" if same else f"median of all {m} measured") + f" ({why})"


def load_radii(proj: Path, rel):
    p = proj / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("corners") or {}


def load_returns(proj: Path):
    """data/mouth_returns.json, or None (no returns declared: every reader keeps its old behaviour)"""
    p = proj / RETURNS_FILE
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def host_arcs(hpts, mh, closed):
    arc = [0.0]
    for i in range(1, mh + (1 if closed else 0)):
        a, b = hpts[i - 1], hpts[i % len(hpts)]
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return arc


def signed_off(arc_q, c, lap):
    """arc_q - c, wrapped onto (-lap/2, lap/2] on a closed host"""
    d = arc_q - c
    if lap:
        d = (d + lap / 2.0) % lap - lap / 2.0
    return d


def rows_between(arc, mh, closed, c, lo, hi):
    """host rows whose signed arc offset from c is within [lo, hi] (lo <= 0 <= hi)"""
    lap = arc[mh] if closed and len(arc) > mh else None
    return {q for q in range(mh) if lo - 1e-6 <= signed_off(arc[q], c, lap) <= hi + 1e-6}


def walk_polyline(poly, closed, q0, t0, dist, direction):
    """from param (segment q0, t0) on the polyline `poly` (engine points; closed = wraps), walk `dist` metres of plan arc
    in `direction` (+1 rows up, -1 down): (point (x, y, z), segment, t). None when an open polyline ends first."""
    n = len(poly)
    q, t = q0, t0
    left = dist
    while True:
        a = poly[q % n]
        b = poly[(q + 1) % n]
        L = math.hypot(b[0] - a[0], b[2] - a[2])
        if direction > 0:
            room = (1.0 - t) * L
            if left <= room + 1e-12:
                tt = t + (left / L if L > 1e-12 else 0.0)
                return tuple(a[k] + (b[k] - a[k]) * tt for k in range(3)), q, tt
            left -= room
            q += 1
            t = 0.0
            if not closed and q >= n - 1:
                return None
            q %= n
        else:
            room = t * L
            if left <= room + 1e-12:
                tt = t - (left / L if L > 1e-12 else 0.0)
                return tuple(a[k] + (b[k] - a[k]) * tt for k in range(3)), q, tt
            left -= room
            q -= 1
            t = 1.0
            if not closed and q < 0:
                return None
            q %= n


def project_polyline(poly, closed, x, z, rows=None):
    """nearest point on the polyline (plan): (distance, segment, t); `rows` limits the segments searched"""
    n = len(poly)
    best = None
    segs = rows if rows is not None else range(n if closed else n - 1)
    for q in segs:
        if not closed and not (0 <= q < n - 1):
            continue
        a, b = poly[q % n], poly[(q + 1) % n]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            continue
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
        d = math.hypot(x - (a[0] + dx * t), z - (a[2] + dz * t))
        if best is None or d < best[0]:
            best = (d, q % n, t)
    return best


def paint_window(mo, host_pts, host_closed, returns_rec=None):
    """(c, lo, hi): the host arc station of the cut and the signed arc offsets of the opening where the host's edge line
    is broken (road_markings.gap_mouths). A mouth with returns: from A* to A* (the paint stops where the return starts,
    as real paint does at a curb return); else the opening itself: the connector's half-width / sin(angle) either side."""
    mh = len(host_pts) - 1 if host_closed else len(host_pts)
    arc = host_arcs(host_pts, mh, host_closed)
    seg = int(mo["host_seg"])
    j = min(seg + 1, len(arc) - 1)
    c = arc[seg] + (arc[j] - arc[seg]) * float(mo["host_t"])
    sin_a = max(math.sin(math.radians(max(1.0, min(90.0, float(mo.get("angle_deg") or 90.0))))), 0.05)
    hw = float(mo["connector_width_m"]) / 2.0 / sin_a
    lo, hi = -hw, hw
    if returns_rec:
        pw = returns_rec.get("paint_window_off")
        if pw:
            lo, hi = min(lo, pw[0]), max(hi, pw[1])
    return c, lo, hi
