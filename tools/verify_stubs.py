"""Gate: every declared PHASE-5 side-road STUB (ledger 0054), measured on the BUILT road — the gate OBJ of the shipped
road kn5 (data/track.obj; the stubs and their barriers ride in the road kn5, so every layout loads them). L5: heights
come from the triangles that ship; data/stubs.plan.json / stubs.built.json / mouths.json only say where to look.

    python tools/verify_stubs.py <project-dir> [--obj data/track.obj] [--json data/verify_stubs.json]
                                [--trees <build>/extension/trees/trees.txt]

Per stub (S1-S7) and per curb cut (S8):
  S1 PRESENT     its mouth is in data/mouths.json with a piece, the authored record is in stubs.built.json, and the
                 built OBJ carries its barrier (1WALL_STUB_<id> triangles)
  S2 MOUTH       tools/verify_mouths.check_mouth on its mouth, unchanged tolerances (mouth line 0.05 m, host lane 0.02 m,
                 notch 0.05 m, approach 3 %-pt/m over the 2.5 m wheelbase, no grass on the approach)
  S3 DRIVABLE    from the mouth line to the barrier's road-side toe, on the centreline and both wheel lines
                 (+-(w/2 - 1 m)) every SAMPLE_M: a 1ROAD sheet under every sample, no step between neighbours over
                 STEP_MAX_M, no grass at/above the road (within GRASS_AT_M); across the carriageway (+-(w/2 - 0.3 m))
                 nothing else — another wall, a post, a house, a TreeFX trunk (--trees) — standing more than
                 OBSTRUCT_M over the road
  S4 SPAN        along the barrier line (the stub's own cross-section at its declared distance) from back of walk to
                 back of walk (half-width + curb face + walk, both sides) every SPAN_STEP_M: the barrier's top stands
                 >= BARRIER_MIN_H_M over the surface — no gap a car fits through, curb to curb and over both walks
  S5 SEATED      every barrier base column (its lowest vertex per SEAT_CELL_M cell) stands within SEAT_FLOAT_M over the
                 stub's surface under it and no deeper than SEAT_SINK_M into it
  S6 HOST LANE   no barrier vertex within the host's pavement + HOST_CLEAR_M (the stub's own road over the host lane
                 is S2's HOST LANE)
  S7 RETURNS     at each corner's arc midpoint: the corner pavement is 1ROAD (no grass at/above it) RETURN_IN_M inside
                 the arc and the curb's walk is 1KERB >= CURB_UP_M over it RETURN_OUT_M outside
  S8 CURB CUT    the host curb top over a driveway stands <= lip + CUT_TOL_M over the road

Writes data/verify_stubs.json; exit 1 on any FAIL, 2 on an input error. With no data/stubs.plan.json: "no stub
declared", exit 0, nothing written. Thresholds marked [INVENTED] are in fleet/GATES-CHANGELOG.md (2026-10-14).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE_M = 0.25
STEP_MAX_M = 0.05         # [INVENTED] neighbouring 0.25 m road samples on a stub differ by at most this
GRASS_AT_M = 0.005        # verify_mouths' GRASS_AT_M
OBSTRUCT_M = 0.05         # [INVENTED] anything but road / paint over the carriageway by more than this obstructs
SPAN_STEP_M = 0.05
BARRIER_MIN_H_M = 0.80    # [INVENTED] the barrier top over the surface along its whole span (real K-rail 0.81-1.07 m)
WALK_M = 1.58             # the connector curb profile: curb face 0.08 + walk 1.5 (build_loop_blend)
SEAT_R_M = 0.45           # a jersey vertex's own toe lies within this in plan (0.255 across + a 0.25 m ring step)
BARRIER_REACH_M = 1.6     # the surface under a barrier vertex is the sheet within this of it (the barrier is 1.2 m)
SEAT_FLOAT_M = 0.05       # the task's seating limit: a base never hovers more than this
SEAT_SINK_M = 0.15        # [INVENTED] ... nor sinks deeper than this (a 0.67 m base on a 15 % grade sinks 0.10)
HOST_CLEAR_M = 1.0        # [INVENTED] barrier vertices stay this far outside the host's pavement edge
RETURN_IN_M = 0.5
RETURN_OUT_M = 0.6
CURB_UP_M = 0.10
ROAD_TOL_M = 0.06
CUT_TOL_M = 0.03
KEEP_M = 60.0
CELL = 2.0
TREE_R_M = 0.35
PAINT = ("MARKINGS", "YLINE", "ROADTEXT")


def _tool(stem, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VM = _tool("verify_mouths", "_verify_mouths_ro")


def classify(name):
    u = name.upper()
    if u.startswith(PAINT):
        return None
    if u.startswith("1WALL_STUB"):
        return "STUB"
    if u.startswith("1ROAD"):
        return "ROAD"
    if u.startswith("1KERB"):
        return "KERB"
    if u.startswith("1GRASS"):
        return "GRASS"
    if u.startswith("GRASS_FAR"):
        return None
    if u.startswith("1WALL"):
        return "WALL"
    return "OTHER"


CLASSES = ("ROAD", "KERB", "GRASS", "STUB", "WALL", "OTHER")


def load_obj(path, centres, keep=KEEP_M):
    """({class: [tri]}, {stub object name: [tri]}) near the centres"""
    V = []
    tris = {c: [] for c in CLASSES}
    by_name = {}
    cur = curname = None
    k2 = keep * keep

    def near(p):
        return any((p[0] - cx) ** 2 + (p[2] - cz) ** 2 <= k2 for cx, cz in centres)

    with open(path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            c2 = line[:2]
            if c2 == "v ":
                q = line.split()
                V.append((float(q[1]), float(q[2]), float(q[3])))
            elif c2 == "o " or c2 == "g ":
                curname = line[2:].strip()
                cur = classify(curname)
            elif c2 == "f " and cur is not None:
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                pts = [V[i - 1] if i > 0 else V[i] for i in idx]
                if any(near(p) for p in pts):
                    for k in range(1, len(pts) - 1):
                        t = (pts[0], pts[k], pts[k + 1])
                        tris[cur].append(t)
                        if cur == "STUB":
                            by_name.setdefault(curname.upper(), []).append(t)
    return tris, by_name


class Field:
    def __init__(self, tris):
        self.cells = {}
        for cls, ts in tris.items():
            for t in ts:
                xs = [p[0] for p in t]
                zs = [p[2] for p in t]
                for ix in range(int(math.floor(min(xs) / CELL)), int(math.floor(max(xs) / CELL)) + 1):
                    for iz in range(int(math.floor(min(zs) / CELL)), int(math.floor(max(zs) / CELL)) + 1):
                        self.cells.setdefault((ix, iz), []).append((cls, t))

    def heights(self, x, z):
        out = {c: [] for c in CLASSES}
        for cls, (a, b, c) in self.cells.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            l3 = 1.0 - l1 - l2
            if min(l1, l2, l3) >= -1e-7:
                out[cls].append(l1 * a[1] + l2 * b[1] + l3 * c[1])
        return out


def _near(vals, ref, reach=1.5):
    """the sheets within `reach` of a reference height (a bridge deck far above / below is another surface)"""
    return [v for v in vals if abs(v - ref) <= reach]


def check_stub(st, sb, mo, piece, host, field, by_name, data, trees):
    fails = []
    rec = {"id": st["id"], "connector": st["connector"], "piece": piece and piece["name"]}
    # S1
    name = ("1WALL_STUB_" + st["id"]).upper()
    wall = by_name.get(name, [])
    rec["S1"] = {"mouth": mo is not None, "built": sb is not None, "barrier_tris": len(wall)}
    if mo is None or piece is None:
        fails.append("S1: no mouth / piece for the stub in data/mouths.json (trim dropped it?)")
    if sb is None:
        fails.append("S1: not in data/stubs.built.json (the author stage did not build it)")
    if not wall:
        fails.append(f"S1: no {name} triangles in the built OBJ")
    if fails:
        rec["fails"] = fails
        rec["fail"] = True
        return rec
    # S2
    pp = VM.Path2(VM.smooth_xz([tuple(q) for q in piece["points_xyz_m"]]), piece["widths_m"])
    m2 = VM.check_mouth(mo, VM_FIELD[0], host, pp, mo["end"], data,
                        exact_deck=any(str(mo.get("connector", "")).startswith(px) for px in EXACT_PX))
    rec["S2"] = {k: m2[k] for k in ("angle_deg", "span_half_m")}
    rec["S2"].update({"mouth_line_max_m": m2["mouth_line"]["max_dev_m"], "host_lane_above_max_m": m2["host_lane"]["max_above_m"],
                      "notch_max_m": m2["notch"]["max_dev_m"], "approach_max_dg_per_m": m2["approach"]["max_dg_per_m"],
                      "fails": m2["fails"]})
    fails += ["S2 " + f for f in m2["fails"]]
    # the stub frame: arc u from the cut along the smoothed piece
    plen = pp.s[-1]
    w = piece["widths_m"][0]
    half = w / 2.0
    u_mouth = float(st["u_mouth_from_cut_m"])
    u_bar = float(st["u_barrier_from_cut_m"])
    toe = u_bar - 0.335 - 0.05
    # S3
    holes = steps = grass = 0
    worst_step = 0.0
    for lat in (-(half - 1.0), 0.0, half - 1.0):
        prev = None
        u = u_mouth
        while u <= toe + 1e-9:
            x, z = pp.point(u, lat)
            h = field.heights(x, z)
            r = h["ROAD"]
            if not r:
                holes += 1
                prev = None
            else:
                y = max(_near(r, prev if prev is not None else max(r)) or r)
                if prev is not None and abs(y - prev) > STEP_MAX_M:
                    steps += 1
                if prev is not None:
                    worst_step = max(worst_step, abs(y - prev))
                if any(g >= y - GRASS_AT_M for g in _near(h["GRASS"], y)):
                    grass += 1
                prev = y
            u += SAMPLE_M
    obst, obst_where = 0, []
    u = u_mouth + 0.5
    while u <= toe + 1e-9:
        lat = -(half - 0.3)
        while lat <= half - 0.3 + 1e-9:
            x, z = pp.point(u, lat)
            h = field.heights(x, z)
            if h["ROAD"]:
                y = max(h["ROAD"])
                for cls in ("WALL", "OTHER", "STUB"):
                    if any(v > y + OBSTRUCT_M for v in _near(h[cls], y, 4.0)):
                        obst += 1
                        if len(obst_where) < 6:
                            obst_where.append([cls, round(u, 2), round(lat, 2)])
                        break
            for t in trees:
                if math.hypot(t["x"] - x, t["z"] - z) <= TREE_R_M:
                    obst += 1
                    if len(obst_where) < 6:
                        obst_where.append(["tree " + t["id"], round(u, 2), round(lat, 2)])
            lat += SAMPLE_M
        u += SAMPLE_M
    rec["S3"] = {"from_m": round(u_mouth, 2), "to_m": round(toe, 2), "holes": holes, "steps_over": steps,
                 "worst_step_m": round(worst_step, 3), "grass_at_or_above": grass, "obstructions": obst,
                 "obstructed_at": obst_where}
    if holes:
        fails.append(f"S3: {holes} samples between the mouth line and the barrier with no road under them")
    if steps:
        fails.append(f"S3: {steps} road steps > {STEP_MAX_M} m (worst {worst_step:.3f} m)")
    if grass:
        fails.append(f"S3: {grass} samples with grass at/above the stub's road")
    if obst:
        fails.append(f"S3: {obst} carriageway samples obstructed before the barrier, e.g. {obst_where[:3]}")
    # S4 — along the stub's own cross-section at u_bar
    (cx, cz), (tx, tz), (nx, nz), wb = pp.frame(u_bar)
    reach = wb / 2.0 + WALK_M
    span_bad, worst_low, n_s = [], None, 0
    o = -reach
    while o <= reach + 1e-9:
        # the barrier's CREST within CREST_SEARCH_M of the declared distance, along the stub (ledger 0054 P3): the
        # author stage stations the barrier on the welded mesh's own rows, and on a steep host the weld's mitre moves
        # the stub's first row up to 0.17 m along it (Laura St off Princess View's 9.6 %) — a cross-section 0.17 m off
        # the crest reads the jersey's sloped face, 0.77 m over the road, not its 1.1 m top
        best = None
        k = -CREST_SEARCH_M
        while k <= CREST_SEARCH_M + 1e-9:
            x, z = cx + nx * o + tx * k, cz + nz * o + tz * k
            h = field.heights(x, z)
            sf = max(h["ROAD"] + h["KERB"], default=None)
            tp = max(wall_heights(wall, x, z), default=None)
            if sf is not None and tp is not None and (best is None or tp - sf > best[1] - best[0]):
                best = (sf, tp)
            k += CREST_STEP_M
        surf, top = best if best is not None else (None, None)
        n_s += 1
        if surf is None or top is None or top - surf < BARRIER_MIN_H_M:
            span_bad.append(round(o, 2))
            hh = None if (surf is None or top is None) else round(top - surf, 3)
            worst_low = hh if worst_low is None or (hh is not None and hh < worst_low) else worst_low
        o += SPAN_STEP_M
    rec["S4"] = {"half_span_m": round(reach, 3), "samples": n_s, "short": len(span_bad), "short_at_m": span_bad[:10],
                 "lowest_short_m": worst_low}
    if span_bad:
        fails.append(f"S4: the barrier does not stand {BARRIER_MIN_H_M} m over the stub at {len(span_bad)} of {n_s} "
                     f"points across back of walk to back of walk (e.g. lateral {span_bad[:5]})")
    # S5 — every barrier vertex's gap over the surface straight under it; the SEAT at a vertex is the least gap within
    # SEAT_R_M of it in plan (from any vertex of the jersey that is the toe of its own ring, the base is 0.67 m wide)
    gaps, unseated, stub_sinks = local_seat(wall, field)
    floats = [g for g in gaps.values()]
    sinks = stub_sinks
    rec["S5"] = {"vertices": len(gaps), "max_float_m": round(max(floats, default=0.0), 4),
                 "max_sink_m": round(max(sinks, default=0.0), 4), "no_surface": unseated}
    if max(floats, default=0.0) > SEAT_FLOAT_M:
        fails.append(f"S5: a barrier base hovers {max(floats):.3f} m over the stub (> {SEAT_FLOAT_M})")
    if max(sinks, default=0.0) > SEAT_SINK_M:
        fails.append(f"S5: a barrier base sinks {max(sinks):.3f} m into the stub (> {SEAT_SINK_M})")
    if unseated:
        fails.append(f"S5: {unseated} barrier vertices with no stub surface under them")
    # S6
    worst = None
    for t in wall:
        for p in t:
            d, i, tt, _lat, _s = host_proj(host, p[0], p[2])
            hh = host_half(host, i, tt)
            g = d - hh
            worst = g if worst is None else min(worst, g)
    rec["S6"] = {"min_off_host_edge_m": round(worst, 3)}
    if worst < HOST_CLEAR_M:
        fails.append(f"S6: a barrier vertex stands {worst:.2f} m off the host's pavement edge (< {HOST_CLEAR_M})")
    # S7
    rows7 = []
    for c in sb.get("corners", []):
        O = c["O"]
        R = c["radius_m"]
        a0 = math.atan2(c["A"][1] - O[1], c["A"][0] - O[0])
        a1 = math.atan2(c["B"][1] - O[1], c["B"][0] - O[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        am = a0 + da / 2.0
        ex, ez = O[0] + R * math.cos(am), O[1] + R * math.sin(am)
        ux, uz = math.cos(am), math.sin(am)               # outward from O = INTO the pavement
        pin = (ex + ux * RETURN_IN_M, ez + uz * RETURN_IN_M)
        pedge = (ex + ux * 0.05, ez + uz * 0.05)
        pout = (ex - ux * RETURN_OUT_M, ez - uz * RETURN_OUT_M)
        hi, he, ho = field.heights(*pin), field.heights(*pedge), field.heights(*pout)
        road = max(hi["ROAD"], default=None)
        edge = max(he["ROAD"], default=None)
        kerb = max(ho["KERB"], default=None)
        gin = max(hi["GRASS"], default=None)
        bad = []
        if road is None:
            bad.append("no corner pavement inside the arc")
        elif gin is not None and gin >= road - GRASS_AT_M:
            bad.append(f"grass {gin - road:+.3f} m at/above the corner pavement")
        if kerb is None or edge is None or kerb - edge < CURB_UP_M:
            bad.append("no raised curb walk outside the arc" if kerb is None or edge is None
                       else f"the walk stands only {kerb - edge:.3f} m over the pavement's edge")
        rows7.append({"edge": c["edge"], "radius_m": R, "road": None if road is None else round(road, 3),
                      "walk_over_edge_m": None if (kerb is None or edge is None) else round(kerb - edge, 3), "fails": bad})
        fails += [f"S7 corner {c['edge']:+d}: {b}" for b in bad]
    rec["S7"] = rows7
    rec["fails"] = fails
    rec["fail"] = bool(fails)
    return rec


def local_seat(wall, field, r=None):
    """({vertex: least gap over the surface within r of it in plan}, vertices with no surface under them)"""
    r = SEAT_R_M if r is None else r
    gap = {}
    unseated = 0
    stub_sinks = []
    for v in {p for t in wall for p in t}:
        h = field.heights(v[0], v[2])
        # the stub's own surfaces (road, curb, walk, verge); the ground only where neither reaches (the barrier's ends,
        # which may stand buried in a bank — that is no hover, so only the stub's surfaces count a SINK)
        st = _near(h["ROAD"] + h["KERB"], v[1], BARRIER_REACH_M)
        sv = st or _near(h["GRASS"], v[1], BARRIER_REACH_M)
        if not sv:
            unseated += 1
            continue
        gap[v] = v[1] - max(sv)
        if st:
            stub_sinks.append(max(st) - v[1])
    grid = {}
    for v in gap:
        grid.setdefault((int(math.floor(v[0] / r)), int(math.floor(v[2] / r))), []).append(v)
    out = {}
    for v in gap:
        gx, gz = int(math.floor(v[0] / r)), int(math.floor(v[2] / r))
        out[v] = min(gap[q] for i in (-1, 0, 1) for j in (-1, 0, 1) for q in grid.get((gx + i, gz + j), ())
                     if math.hypot(q[0] - v[0], q[2] - v[2]) <= r)
    return out, unseated, stub_sinks


def wall_heights(wall, x, z):
    out = []
    for a, b, c in wall:
        if min(a[0], b[0], c[0]) > x or max(a[0], b[0], c[0]) < x or min(a[2], b[2], c[2]) > z or max(a[2], b[2], c[2]) < z:
            continue
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1.0 - l1 - l2
        if min(l1, l2, l3) >= -1e-7:
            out.append(l1 * a[1] + l2 * b[1] + l3 * c[1])
    return out


def host_proj(path2, x, z):
    best = None
    for i in range(len(path2.p) - 1):
        a, b = path2.p[i], path2.p[i + 1]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            continue
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
        d = math.hypot(x - (a[0] + dx * t), z - (a[2] + dz * t))
        if best is None or d < best[0]:
            best = (d, i, t, 0.0, 0.0)
    return best


def host_half(path2, i, t):
    j = min(len(path2.w) - 1, i + 1)
    return (path2.w[i] * (1 - t) + path2.w[j] * t) / 2.0


def check_cut(cc, field, host):
    i = min(range(len(host.p)), key=lambda k: (host.p[k][0] - cc["cut_xz"][0]) ** 2 + (host.p[k][2] - cc["cut_xz"][1]) ** 2)
    x, z = cc["cut_xz"]
    (px, pz), _t, (nx, nz), wd = host.frame(host.s[i])
    side = int(cc["side"])
    road_p = (px + nx * side * (wd / 2.0 - 0.3), pz + nz * side * (wd / 2.0 - 0.3))
    kerb_p = (px + nx * side * (wd / 2.0 + 0.5), pz + nz * side * (wd / 2.0 + 0.5))
    r = max(field.heights(*road_p)["ROAD"], default=None)
    k = max(field.heights(*kerb_p)["KERB"], default=None)
    fails = []
    if r is None or k is None:
        fails.append("S8: no host road / curb at the cut")
    else:
        # the walk 0.5 m out sits on the apron slope: lip + (0.42 of the way up the walk) at most
        lim = r + cc["lip_m"] + CUT_TOL_M + 0.14 * 0.5 / 1.58
        if k > lim:
            fails.append(f"S8: the curb over the driveway stands {k - r:.3f} m over the road (> {lim - r:.3f})")
    return {"id": cc["id"], "road": r, "kerb": k, "fails": fails, "fail": bool(fails)}


VM_FIELD = [None]
CREST_SEARCH_M = 0.3      # [invented] S4 reads the barrier's crest within this of its declared distance along the stub
CREST_STEP_M = 0.05
EXACT_PX = []             # route.weld_exact_deck (set by verify()): S2 reads the host deck as verify_mouths does


def host_path(hosts, conns, hn, cut_xz):
    """the host's path as built: MAINLINE, a connector by name, or (ledger 0054 P3) the piece trim renamed <name>#k
    nearest the cut"""
    if hn in hosts:
        return hosts[hn]
    cand = [c for c in conns if c["name"] == hn or c["name"].startswith(hn + "#")]
    if not cand:
        raise LookupError(f"host {hn!r} not found")
    hc = min(cand, key=lambda c: min(math.hypot(q[0] - cut_xz[0], q[2] - cut_xz[1]) for q in c["points_xyz_m"]))
    hosts[hn] = VM.Path2(hc["points_xyz_m"], hc["widths_m"])
    return hosts[hn]


def verify(project: Path, obj: Path | None = None, trees_txt: Path | None = None) -> dict | None:
    data = project / "data"
    pp = data / "stubs.plan.json"
    if not pp.exists():
        return None
    plan = json.loads(pp.read_text(encoding="utf-8"))
    cfgp = project / "track.config.json"
    EXACT_PX[:] = [str(x) for x in ((json.loads(cfgp.read_text(encoding="utf-8")).get("route") or {})
                                    .get("weld_exact_deck") or [])] if cfgp.exists() else []
    bp = data / "stubs.built.json"
    built = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {"stubs": []}
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8")).get("mouths", [])
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8")).get("connectors", [])
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    obj = obj or data / "track.obj"
    if not obj.exists():
        raise FileNotFoundError(f"no {obj}")
    centres = [tuple(s["cut_xz"]) for s in plan["stubs"]] + [tuple(c["cut_xz"]) for c in plan.get("curb_cuts", [])]
    tris, by_name = load_obj(obj, centres)
    field = Field(tris)
    VM_FIELD[0] = VM.Field(VM.load_obj(obj, centres))
    trees = []
    if trees_txt is not None and Path(trees_txt).exists():
        vr = _tool("verify_race", "_verify_race_ro")
        trees = vr.tree_items_from_txt(Path(trees_txt).read_text(encoding="utf-8", errors="replace"))
        trees = [t for t in trees if any(math.hypot(t["x"] - cx, t["z"] - cz) <= KEEP_M for cx, cz in centres)]
    hosts = {"MAINLINE": VM.Path2(local["points_xyz_m"], local["widths_m"])}
    rows = []
    for st in plan["stubs"]:
        mo = next((m for m in mouths if str(m.get("connector")) == st["connector"] and m.get("piece")), None)
        piece = next((c for c in conns if mo and c["name"] == mo["piece"]), None)
        sb = next((s for s in built.get("stubs", []) if s["id"] == st["id"]), None)
        rows.append(check_stub(st, sb, mo, piece, host_path(hosts, conns, st.get("host", "MAINLINE"), st["cut_xz"]),
                               field, by_name, data, trees))
    cut_rows = [check_cut(cc, field, host_path(hosts, conns, cc.get("host", "MAINLINE"), cc["cut_xz"]))
                for cc in plan.get("curb_cuts", [])]
    return {"obj": obj.name, "stubs": rows, "curb_cuts": cut_rows,
            "fail": any(r["fail"] for r in rows) or any(r["fail"] for r in cut_rows),
            "thresholds": {"step_max_m_invented": STEP_MAX_M, "obstruct_m_invented": OBSTRUCT_M,
                           "barrier_min_h_m_invented": BARRIER_MIN_H_M, "seat_float_m": SEAT_FLOAT_M,
                           "seat_sink_m_invented": SEAT_SINK_M, "host_clear_m_invented": HOST_CLEAR_M,
                           "grass_at_m": GRASS_AT_M, "trees_checked": len(trees)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--obj", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--trees", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    if not (proj / "data" / "stubs.plan.json").exists():
        print("[verify_stubs] no data/stubs.plan.json — no stub declared, nothing to verify")
        return 0
    trees = Path(a.trees) if a.trees else None
    if trees is None:
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
        cand = proj / "build" / str(cfg.get("slug", "")) / "extension" / "trees" / "trees.txt"
        trees = cand if cand.exists() else None
    try:
        r = verify(proj, Path(a.obj) if a.obj else None, trees)
    except (FileNotFoundError, LookupError) as e:
        print(f"[verify_stubs] INPUT ERROR: {e}")
        return 2
    if r is None:
        print("[verify_stubs] no data/stubs.plan.json — no stub declared, nothing to verify")
        return 0
    out = Path(a.json) if a.json else proj / "data" / "verify_stubs.json"
    out.write_text(json.dumps(r, indent=1), encoding="utf-8")
    for m in r["stubs"]:
        if "S3" in m:
            print(f"[verify_stubs] {m['piece']}: mouth {'FAIL' if m['S2']['fails'] else 'ok'} (line {m['S2']['mouth_line_max_m']} m, "
                  f"approach {100 * m['S2']['approach_max_dg_per_m']:.2f} %/m); drivable {m['S3']['from_m']}-{m['S3']['to_m']} m "
                  f"(holes {m['S3']['holes']}, worst step {m['S3']['worst_step_m']} m, grass {m['S3']['grass_at_or_above']}, "
                  f"obstructions {m['S3']['obstructions']}); barrier span +-{m['S4']['half_span_m']} m short {m['S4']['short']}"
                  f"/{m['S4']['samples']}, seat float {m['S5']['max_float_m']} / sink {m['S5']['max_sink_m']} m, "
                  f"{m['S6']['min_off_host_edge_m']} m off the host edge; returns "
                  f"{', '.join(str(c['radius_m']) for c in m['S7'])} m — {'FAIL' if m['fail'] else 'PASS'}")
        else:
            print(f"[verify_stubs] {m['id']}: FAIL")
        for f in m["fails"]:
            print(f"    FAIL {f}")
    for c in r["curb_cuts"]:
        print(f"[verify_stubs] curb cut {c['id']}: {'FAIL' if c['fail'] else 'PASS'}")
        for f in c["fails"]:
            print(f"    FAIL {f}")
    print(f"[verify_stubs] {len(r['stubs'])} stub(s), {len(r['curb_cuts'])} curb cut(s) on {r['obj']}: "
          f"{'FAIL' if r['fail'] else 'PASS'} -> {out.name}")
    return 1 if r["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
