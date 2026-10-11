"""Race-layout furniture for the Lake Murray loop — the PURE geometry (no bpy), ledger 0047.

Three kinds of furniture, every one a swept strip authored in the ENGINE frame (x = E, y = up,
z = N) and emitted into Blender by `tools/author_race_furniture_blend.py` with the (x, z, y) remap
and REVERSED winding (LAWS L6: the remap is a reflection):

  centre K-rail chain   `1WALL_race_kbar_<street>_<k>`   Kevin's concrete_barrier_4m.obj silhouette
                                                        swept along `barrier_bands.json` centre runs,
                                                        nose-to-nose with the median islands, continuous
                                                        round the three interior corners, tapered free ends
  kerb-line barriers    `1WALL_race_edge_<L|R>_<street>_<k>`  the same strip on BOTH curb faces, every
                                                        street incl. Alvarado, gapped only inside the
                                                        declared bridge spans (the authored rails are the
                                                        barrier there), straight across every mouth
  race kerbs            `1KERB_race_<apexvertex>_<in|out>`  a 1.0 m x 0.05 m flat rumble strip ON the
                                                        pavement inboard of the edge strip at the five
                                                        corners the sign detector finds (|D| >= 45 deg)

Why strips and not 2,100+ instanced modules: ~130k positions in ~30 objects (each <= MAX_RINGS_PER_OBJECT
rings, flat-shaded render verts well under the exporter's 65,535 split) versus ~2.2 M positions; every
reference measured (SRP, nohesi, Macau, rt_california) ships strips/sheets. The texture tiles at the
module pitch (u = arc / 4.04 m) so the joints still read every 4.04 m.

Everything here is testable without Blender: the Blender tool only supplies the deck height per ring
(a BVH ray onto ROAD/CURB) and turns the (verts, faces, uvs) into mesh objects. The corner detector is
tools/place_signs.py's, imported READ-ONLY (that file belongs to the signs workflow).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO / "tools") not in sys.path:
    sys.path.insert(0, str(AIROSO / "tools"))

# ---------------------------------------------------------------------------------------------
# constants — the spec (ledger 0047 FINAL SPEC) in one place
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")   # upper-case prefix test; the export split keys on these
LIFT = 0.10              # the road ribbon rides +0.10 over centerline y (build_loop_blend.py:654)
BURY_M = 0.05            # strip base sunk this far into the deck (drive_test floating 0.8 m / audit E read 'grounded')
MODULE_PITCH_M = 4.04    # concrete_barrier_4m.obj is 4.04 m long: the texture tiles at that pitch
BARRIER_H = 1.20         # Kevin's module is 1.202 m tall (Q5 offers 0.81-1.07 real K-rail: ONE constant)
# measured half-profile of assets/models/concrete_barrier_4m.obj (249 v): (lateral, height) bottom->top.
# The 1.16/1.20 top chamfer is collapsed into one point so a ring is 10 vertices (10 quads/station).
HALF_PROFILE = ((0.335, 0.00), (0.335, 0.12), (0.164, 0.38), (0.137, 0.47), (0.080, 1.20))
BARRIER_HALF_W = HALF_PROFILE[0][0]
NOSE_HALF = 0.25         # tools/author_median_blend.py NOSE_HALF — the island nose the chain butts into
NOSE_H = 0.30            # chain height at the shared nose vertex (island curb top is 0.18 above the deck)
NOSE_TAPER_RINGS = 3     # the nose ring + the two before it taper 0.335 -> 0.25 / 1.20 -> 0.30
FREE_END_H = 0.30        # free ends (v780 / v4440 / bridge-span gaps): 3-ring height taper 1.20 -> 0.30
FREE_TAPER_RINGS = 3
MAX_RINGS_PER_OBJECT = 800   # 10 quads x 2 tris x 3 flat render verts = 60/ring -> 48,000 + caps < 65,535
EDGE_INSET_M = 0.82      # road mode: the strip's road-side face at half_w - 0.82 (curb-side face at half_w - 0.15)
EDGE_WALK_CENTRE_M = 0.445   # walk mode: strip centre at half_w + 0.445 on the sidewalk top (road-side face half_w + 0.11)
KERB_W = 1.0
KERB_H = 0.05            # flat low kerb: below audit K's KERB_STAND_M 0.10 and drive_test's severe step 6 cm
KERB_RAMP_W = 0.10       # rideable lane-side ramp
KERB_CLEAR_M = 0.05      # kerb outer edge 0.05 m clear of the edge strip's road-side face
KERB_STEP_M = 0.3
KERB_TILE_M = 1.0        # kerb_diffuse.png stripes: one tile per metre along
KERB_TAPER_STATIONS = 3
KERB_DEFL_MIN_DEG = 45.0
KERB_EXT_MIN_M, KERB_EXT_MAX_M = 10.0, 30.0   # outside kerb symmetric extension E = clamp(2 R_apex, 10, 30)
CAR_HALF_W = 0.95        # spawn clearance: a 1.9 m car
SPAWN_MARGIN_M = 0.30
COLLIDER_BELOW_M, COLLIDER_ABOVE_M = 0.30, 2.50   # optional invisible sheet (Q11, OFF by default)
STREETS = (("alvarado", 0, 759), ("college", 760, 1514), ("navajo", 1515, 2320),
           ("jackson", 2321, 3297), ("lakemurray", 3298, 4498))
# the spec's centre runs, closed vertex intervals ending ON the island nose vertices (used only when
# data/barrier_bands.json is absent and --standin-bands is given)
SPEC_CENTRE_RUNS = ((780, 846), (1073, 1096), (1258, 1374), (1487, 1540), (1739, 2183), (2297, 4440))
SPEC_CHAIN_LEN_M = 8525.0
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")


# ---------------------------------------------------------------------------------------------
# centreline helpers
def load_centerline(proj):
    local = json.loads((Path(proj) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    return pts, widths


def unique_count(pts):
    """vertices before the repeated closure vertex (v4498 == v0 on SD)"""
    n = len(pts)
    if n > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6:
        return n - 1
    return n


def stations(pts):
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return st


def tangent(pts, k, m):
    """unit tangent at vertex k from pts[k-1] -> pts[k+1] on the closed ring of m unique vertices"""
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    dx, dz = b[0] - a[0], b[2] - a[2]
    d = math.hypot(dx, dz) or 1.0
    return dx / d, dz / d


def left_normal(tx, tz):
    """left of forward travel (x = E, z = N); right = the negative"""
    return -tz, tx


def street_slug(name):
    """'Lake Murray Boulevard' -> 'lakemurray': a mesh-name-safe token (no spaces, no suffix word)"""
    drop = ("road", "avenue", "drive", "boulevard", "blvd", "rd", "ave", "dr")
    words = [w for w in name.lower().replace("-", " ").split() if w not in drop]
    return "".join(ch for ch in "".join(words) if ch.isalnum()) or "loop"


def street_table(bands=None):
    """[(slug, i, j)]: the declaration's `streets` table when the bands carry one (tools/barrier_bands.py
    puts the boundaries at the corner apexes), else the spec's measured table — so an object's street
    token and split point come from the same file the gates read"""
    rows = (bands or {}).get("streets") or []
    if rows:
        return [(street_slug(r["street"]), int(r["vertex_from"]), int(r["vertex_to"])) for r in rows]
    return list(STREETS)


def street_of(k, table=None):
    for name, i, j in (table or STREETS):
        if i <= k <= j:
            return name
    return "loop"


def is_race_name(name):
    return name.upper().startswith(RACE_PREFIXES)


def yaw_blender(tx, tz, direction="forward"):
    """Blender rotation_euler.z for a facing dummy: the exporter's (x, z, -y) conversion makes
    atan2(tx, -tz) the kn5-frame travel heading (measured: deepforest +1.00, today's SD -0.91)"""
    yaw = math.atan2(tx, -tz)
    return yaw + math.pi if direction == "reverse" else yaw


# ---------------------------------------------------------------------------------------------
# the profile and the sweep
def ring_profile(lat_scale=1.0, height=BARRIER_H):
    """closed 10-vertex ring in the cross-section plane: (lat, h), lat > 0 = LEFT of travel.
    Order: right base -> up the right face -> across the top -> down the left face -> (bottom edge
    closes back to the right base). Scaled proportionally for the nose taper."""
    hs = height / BARRIER_H
    right = [(-lat * lat_scale, h * hs) for lat, h in HALF_PROFILE]
    left = [(lat * lat_scale, h * hs) for lat, h in reversed(HALF_PROFILE)]
    return right + left


def ring_perimeter_v(ring):
    """v coordinate (0..1) around the ring by cumulative perimeter"""
    cum = [0.0]
    for i in range(1, len(ring)):
        cum.append(cum[-1] + math.hypot(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]))
    L = cum[-1] or 1.0
    return [c / L for c in cum]


def taper(idx, n, start_kind, end_kind):
    """(lat_scale, height) of ring idx in a run of n rings; ends are 'nose' or 'free'"""
    ls, h = 1.0, BARRIER_H
    for d, kind in ((idx, start_kind), (n - 1 - idx, end_kind)):
        if kind == "nose" and d < NOSE_TAPER_RINGS:
            f = d / NOSE_TAPER_RINGS
            ls = min(ls, NOSE_HALF / BARRIER_HALF_W + (1.0 - NOSE_HALF / BARRIER_HALF_W) * f)
            h = min(h, NOSE_H + (BARRIER_H - NOSE_H) * f)
        elif kind == "free" and d < FREE_TAPER_RINGS:
            f = d / FREE_TAPER_RINGS
            h = min(h, FREE_END_H + (BARRIER_H - FREE_END_H) * f)
    return ls, h


def strip_mesh(rings, cap_start, cap_end, u_scale=MODULE_PITCH_M):
    """A closed swept solid from ring records. Each ring: dict(cx, cz, y, tx, tz, lat, ls, h, arc).
    Returns (verts, faces, uvs) in the ENGINE frame with OUTWARD normals under the right-hand rule
    (the Blender tool remaps + reverses). u = arc / u_scale, v = perimeter fraction."""
    verts, faces, uvs = [], [], []
    P = len(ring_profile())
    rows = []
    for r in rings:
        prof = ring_profile(r["ls"], r["h"])
        vv = ring_perimeter_v(prof)
        lx, lz = left_normal(r["tx"], r["tz"])
        base = len(verts)
        u = r["arc"] / u_scale
        for (lat, h), v in zip(prof, vv):
            off = r["lat"] + lat
            verts.append((r["cx"] + lx * off, r["y"] + h, r["cz"] + lz * off))
            uvs.append((u, v))
        rows.append(base)
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(P):
            j = (i + 1) % P
            faces.append((a + i, a + j, b + j, b + i))
    # end caps: zig-zag between the two mirrored sides (the jersey profile has a shallow concave kink
    # at the toe, so a fan from one vertex could overlap; the ladder never does). The ring order
    # (right base -> up -> over the top -> down the left) is CLOCKWISE seen from +t, so the plain
    # ladder faces -t: right for the START cap, reversed for the END cap (tests/tools/test_race_furniture
    # pins it: every directed edge matched once, volume > 0).
    def ladder(base, reverse):
        tris = []
        lo, hi = 0, P - 1
        while hi - lo > 1:
            tris.append((base + lo, base + hi, base + lo + 1))
            lo += 1
            if hi - lo > 1:
                tris.append((base + lo, base + hi, base + hi - 1))
                hi -= 1
        return [tuple(reversed(t)) for t in tris] if reverse else tris
    if cap_start and rows:
        faces += ladder(rows[0], reverse=False)    # faces -t
    if cap_end and rows:
        faces += ladder(rows[-1], reverse=True)    # faces +t
    return verts, faces, uvs


def kerb_mesh(stations_, side, u_scale=KERB_TILE_M):
    """Open rumble-strip profile per station: lane lip (0, 0) -> ramp top (0.10, h) -> outer top
    (1.0, h) -> outer base (1.0, 0), offsets OUTWARD from the lane lip. Each station: dict(cx, cz, y,
    tx, tz, lip (lateral of the lane lip, signed +left), h, arc). u across the profile, v = arc / 1 m."""
    verts, faces, uvs = [], [], []
    prof = ((0.0, 0.0), (KERB_RAMP_W, 1.0), (KERB_W, 1.0), (KERB_W, 0.0))
    us = (0.0, 0.1, 0.9, 1.0)
    rows = []
    for s in stations_:
        lx, lz = left_normal(s["tx"], s["tz"])
        base = len(verts)
        for (o, hf), u in zip(prof, us):
            off = s["lip"] + side * o
            verts.append((s["cx"] + lx * off, s["y"] + hf * s["h"], s["cz"] + lz * off))
            uvs.append((u, s["arc"] / u_scale))
        rows.append(base)
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(3):
            q = (a + i, a + i + 1, b + i + 1, b + i)
            faces.append(q if side > 0 else (q[0], q[3], q[2], q[1]))
    return verts, faces, uvs


def to_blender(verts, faces):
    """engine (x, y_up, z_north) -> Blender (x, z_north, y_up) is a reflection: reverse every face"""
    return [(x, z, y) for (x, y, z) in verts], [tuple(reversed(f)) for f in faces]


def signed_volume(verts, faces):
    """divergence-theorem volume of a closed triangulated/quad mesh: > 0 when normals point outward"""
    vol = 0.0
    for f in faces:
        for k in range(1, len(f) - 1):
            a, b, c = verts[f[0]], verts[f[k]], verts[f[k + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                    + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return vol


def face_normal(verts, f):
    a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])


# ---------------------------------------------------------------------------------------------
# bands: the declaration the gates read (written by tools/barrier_bands.py — the data agent's file)
def load_bands(proj):
    p = Path(proj) / "data" / "barrier_bands.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def intervals(flags, m, wrap=True):
    """maximal [i, j] intervals (inclusive, on the ring of m vertices) where flags[k] is truthy;
    a run crossing the seam is returned as one interval with j < i"""
    on = [bool(flags[k]) for k in range(m)]
    if all(on):
        return [(0, m - 1)]
    if not any(on):
        return []
    start = next(k for k in range(m) if not on[k]) if wrap else 0
    out, cur = [], None
    for q in range(m):
        k = (start + q) % m if wrap else q
        if on[k]:
            if cur is None:
                cur = [k, k]
            else:
                cur[1] = k
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur is not None:
        out.append(tuple(cur))
    return out


def walk(i, j, m):
    """vertex indices from i to j inclusive, wrapping past the seam when j < i"""
    if j >= i:
        return list(range(i, j + 1))
    return list(range(i, m)) + list(range(0, j + 1))


def standin_bands(pts, widths, island_w, mouths, spans, race_cfg=None, corners=None):
    """A STAND-IN for data/barrier_bands.json built from the spec's vertex runs (centre chain), the
    declared bridge spans (edge gaps) and the detector's corners (kerbs). Used only when the data
    agent's file is absent and the caller passes --standin-bands; flagged `_standin: true`."""
    race_cfg = race_cfg or {}
    n = len(pts)
    m = unique_count(pts)
    st = stations(pts)
    runs_c = [tuple(r) for r in race_cfg.get("centre_runs") or SPEC_CENTRE_RUNS]
    centre_w = [0.0] * n
    bw = float(race_cfg.get("barrier_width_m", 2 * BARRIER_HALF_W))
    for i, j in runs_c:
        for k in walk(i, j, m):
            centre_w[k] = bw
    inset = float(race_cfg.get("edge_inset_m", EDGE_INSET_M))
    edge_inset = [inset] * n
    for s0, s1 in spans:
        for k in range(n):
            if s0 <= st[k] <= s1:
                edge_inset[k] = 0.0
    centre_w[n - 1] = centre_w[0]
    edge_inset[n - 1] = edge_inset[0]
    runs = [{"kind": "centre", "i": i, "j": j, "street": street_of(i)} for i, j in runs_c]
    for side in ("L", "R"):
        for i, j in intervals(edge_inset, m):
            runs.append({"kind": f"edge_{side}", "i": i, "j": j, "street": street_of(i)})
    closed = []
    for mo in mouths:
        if mo.get("host") != "MAINLINE":
            continue
        k = int(mo["host_vertex"])
        side = int(mo["side"])
        nv = int(math.ceil((float(mo["connector_width_m"]) / 2.0 + 3.0) / 3.0))
        poly = []
        for q in (k - nv, k, k + nv):
            q %= m
            tx, tz = tangent(pts, q, m)
            lx, lz = left_normal(tx, tz)
            lat = side * (widths[q] / 2.0 - inset + BARRIER_HALF_W)
            poly.append([round(pts[q][0] + lx * lat, 3), round(pts[q][2] + lz * lat, 3)])
        closed.append({"connector": mo.get("connector"), "host_vertex": k, "side": side, "xz": poly})
    chain_len = sum(st[j] - st[i] if j >= i else st[m] - st[i] + st[j] for i, j in runs_c)
    out = {
        "_standin": True,
        "_doc": "STAND-IN written by tools/race_furniture.standin_bands from the spec's vertex runs — "
                "replace with tools/barrier_bands.py's measured file before any ship run",
        "centre_w_by_vertex": centre_w,
        "edge_inset_by_vertex": edge_inset,
        "runs": runs,
        "closed_mouths": closed,
        "kerbs": [{"apex": kb["apex_vertex"], "side": kb["side"], "i": kb["i"], "j": kb["j"], "kind": kb["kind"]}
                  for c in (corners or []) for kb in c["kerbs"]],
        "params": {"edge_mode": race_cfg.get("edge_mode", "road"), "edge_inset_m": inset,
                   "barrier_width_m": bw, "barrier_height_m": float(race_cfg.get("barrier_height_m", BARRIER_H)),
                   "module_pitch_m": MODULE_PITCH_M, "chain_length_m": round(chain_len, 1),
                   "bridge_spans_m": [list(s) for s in spans]},
    }
    return out


def check_bands(bands, pts, island_w):
    """the band writer's self-gates, re-run on whatever file we were handed; returns a list of problems"""
    n = len(pts)
    m = unique_count(pts)
    cw = bands["centre_w_by_vertex"]
    probs = []
    if len(cw) != n:
        return [f"centre_w_by_vertex has {len(cw)} entries, centerline {n}"]
    runs_c = [(r["i"], r["j"]) for r in bands.get("runs", []) if r["kind"] == "centre"] or \
             intervals(cw, m)
    ends = {i for i, _ in runs_c} | {j for _, j in runs_c}
    on_island = [k for k in range(m) if cw[k] > 0 and island_w[k] > 0 and k not in ends]
    if on_island:
        probs.append(f"{len(on_island)} centre verts on an island beyond the nose (first {on_island[:5]})")
    on_alv = [k for k in range(0, 780) if cw[k] > 0]
    if on_alv:
        probs.append(f"{len(on_alv)} centre verts on Alvarado/the hairpin flare v0-779 (first {on_alv[:5]})")
    st = stations(pts)
    chain_len = sum(st[j] - st[i] if j >= i else st[m] - st[i] + st[j] for i, j in runs_c)
    if abs(chain_len - SPEC_CHAIN_LEN_M) > 60.0:
        probs.append(f"chain length {chain_len:.0f} m vs spec {SPEC_CHAIN_LEN_M:.0f} +- 60")
    return probs


# ---------------------------------------------------------------------------------------------
# ring plans: WHERE every ring goes (the Blender tool adds y and emits the mesh)
def _plan_run(pts, widths, m, st, ks, lat_fn, start_kind, end_kind, height, kind, street, side, run):
    rings = []
    arc = 0.0
    prev = None
    for idx, k in enumerate(ks):
        if prev is not None:
            arc += math.hypot(pts[k][0] - pts[prev][0], pts[k][2] - pts[prev][2])
        prev = k
        tx, tz = tangent(pts, k, m)
        ls, h = taper(idx, len(ks), start_kind, end_kind)
        rings.append({"k": k, "s": st[k], "cx": pts[k][0], "cz": pts[k][2], "y_hint": pts[k][1] + LIFT,
                      "tx": tx, "tz": tz, "lat": lat_fn(k), "ls": ls, "h": h * (height / BARRIER_H),
                      "arc": arc})
    return {"kind": kind, "street": street, "side": side, "run": list(run), "rings": rings,
            "start_kind": start_kind, "end_kind": end_kind}


def split_plan(plan, max_rings=MAX_RINGS_PER_OBJECT):
    """split one run into objects of <= max_rings rings; neighbours SHARE their boundary ring (zero
    gap, no cap); only the run's true ends get a cap"""
    rings = plan["rings"]
    if len(rings) <= max_rings:
        return [dict(plan, cap_start=True, cap_end=True, part=0)]
    n_parts = math.ceil((len(rings) - 1) / (max_rings - 1))
    step = math.ceil((len(rings) - 1) / n_parts)
    parts = []
    a = 0
    p = 0
    while a < len(rings) - 1:
        b = min(len(rings) - 1, a + step)
        parts.append(dict(plan, rings=rings[a:b + 1], cap_start=(a == 0), cap_end=(b == len(rings) - 1), part=p))
        a = b
        p += 1
    return parts


def chain_plans(pts, widths, island_w, bands, height=BARRIER_H):
    m = unique_count(pts)
    st = stations(pts)
    cw = bands["centre_w_by_vertex"]
    runs = [(r["i"], r["j"]) for r in bands.get("runs", []) if r["kind"] == "centre"] or intervals(cw, m)
    table = street_table(bands)
    plans = []
    for i, j in runs:
        ks = walk(i, j, m)
        sk = "nose" if island_w[i] > 0 else "free"
        ek = "nose" if island_w[j] > 0 else "free"
        plan = _plan_run(pts, widths, m, st, ks, lambda k: 0.0, sk, ek, height, "chain", street_of(i, table), "C", (i, j))
        plans += split_plan(plan)
    return plans


def edge_lateral(half_w, inset, mode):
    """lateral (unsigned) of the strip CENTRE for a road half-width"""
    if mode == "walk":
        return half_w + EDGE_WALK_CENTRE_M
    return half_w - inset + BARRIER_HALF_W


def edge_plans(pts, widths, bands, mode="road", height=BARRIER_H):
    """both curb faces: one swept run per edge interval (the gaps are the declared bridge spans, free
    tapered ends), folded rings dropped on the WHOLE run first, then cut at street boundaries (the
    boundary ring shared: zero gap, no cap) so every object is named for its street"""
    m = unique_count(pts)
    st = stations(pts)
    ei = bands["edge_inset_by_vertex"]
    table = street_table(bands)
    plans = []
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        for i, j in intervals(ei, m):
            ks = walk(i, j, m)
            whole = _plan_run(pts, widths, m, st, ks,
                              lambda k, s=sgn: s * edge_lateral(widths[k] / 2.0, ei[k] or EDGE_INSET_M, mode),
                              "free", "free", height, "edge", street_of(ks[0], table), side, (i, j))
            rings, skipped = drop_folded_rings(whole["rings"])
            pieces, cur = [], [rings[0]]
            for r in rings[1:]:
                cur.append(r)
                if street_of(r["k"], table) != street_of(cur[0]["k"], table) and r is not rings[-1]:
                    pieces.append(cur)
                    cur = [r]
            pieces.append(cur)
            for pi, pr in enumerate(pieces):
                sk = "free" if pi == 0 else "join"
                ek = "free" if pi == len(pieces) - 1 else "join"
                plan = dict(whole, rings=pr, street=street_of(pr[0]["k"], table), run=(pr[0]["k"], pr[-1]["k"]),
                            start_kind=sk, end_kind=ek, fold_skipped=(skipped if pi == 0 else 0))
                for part in split_plan(plan):
                    part["cap_start"] = part["cap_start"] and sk == "free"
                    part["cap_end"] = part["cap_end"] and ek == "free"
                    plans.append(part)
    return plans


# ---------------------------------------------------------------------------------------------
# corners -> race kerbs (tools/place_signs.py's detector, read-only)
def detect_kerb_corners(pts, widths, bands, min_defl=KERB_DEFL_MIN_DEG):
    import place_signs as ps   # noqa: E402  (the signs workflow's file; imported, never edited)
    rb = ps.Ribbon("MAINLINE", pts, widths, True)
    cw = bands["centre_w_by_vertex"]
    out = []
    for c in ps.detect_corners(rb):
        if abs(c["D_deg"]) < min_defl:
            continue
        apex_v = rb.vertex(c["apex"])
        inside = "L" if c["sign"] > 0 else "R"
        outside = "R" if inside == "L" else "L"
        E = max(KERB_EXT_MIN_M, min(KERB_EXT_MAX_M, 2.0 * c["R_apex_m"]))
        pc, pt = c["PC"], c["PT"]
        arc = (pt - pc) % rb.n
        kerbs = [{"apex_vertex": apex_v, "apex_station": c["apex"], "side": outside, "kind": "out",
                  "s0": (pc - E) % rb.L, "s1": (pc + arc + E) % rb.L,
                  "i": rb.vertex(int(round(pc - E))), "j": rb.vertex(int(round(pc + arc + E)))}]
        chained = cw[apex_v] > 0
        if not chained:
            kerbs.append({"apex_vertex": apex_v, "apex_station": c["apex"], "side": inside, "kind": "in",
                          "s0": float(pc), "s1": float((pc + arc) % rb.L),
                          "i": rb.vertex(pc), "j": rb.vertex(pt)})
        out.append({"apex_vertex": apex_v, "apex_station": c["apex"], "sign": c["sign"], "R_apex_m": round(c["R_apex_m"], 1),
                    "D_deg": round(c["D_deg"], 1), "PC": pc, "PT": pt, "arc_m": arc, "E_m": round(E, 1),
                    "chained": chained, "kerbs": kerbs})
    return rb, out


def apply_declared_kerbs(rb, corners, bands):
    """The declaration wins: where data/barrier_bands.json carries a `kerbs` run for the same
    (apex, side) — tools/barrier_bands.py's [PC-E, PT+E] / [PC, PT], already clipped for bridge
    clearance (the seam corner's outside kerb starts at v4492, after the I-8 span, not v4484) — its
    i/j replace the detector's own so the authored kerb IS the declared band (the median_zone
    precedent). Kinds 'outside'/'inside' map to 'out'/'in'. Stations come from the ribbon's own
    cumulative length (rb.cum[k]), the frame the detector's PC/PT live in. Returns the declared runs
    nothing in the detector's corner table matched (an author-time warning; verify_race's gate)."""
    KIND = {"outside": "out", "inside": "in", "out": "out", "in": "in"}
    declared = {(int(kb["apex"]), str(kb["side"]).upper()): kb for kb in (bands.get("kerbs") or [])}
    matched = set()
    n = len(rb.raw)
    for c in corners:
        for kb in c["kerbs"]:
            d = declared.get((c["apex_vertex"], kb["side"]))
            if d is None:
                continue
            i, j = int(d["i"]) % n, int(d["j"]) % n
            kb.update({"i": i, "j": j, "s0": float(rb.cum[i]), "s1": float(rb.cum[j]),
                       "kind": KIND.get(str(d.get("kind", kb["kind"])).lower(), kb["kind"]), "declared": True})
            matched.add((c["apex_vertex"], kb["side"]))
    return [d for key, d in declared.items() if key not in matched]


def kerb_plans(rb, corners, bands, mode="road"):
    """0.3 m stations along each kerb run: lane lip at half_w - inset - KERB_CLEAR - KERB_W (road
    mode) or half_w - 0.05 - KERB_W (walk mode); height tapers over the first/last 3 stations"""
    cw_ei = bands["edge_inset_by_vertex"]
    plans = []
    for c in corners:
        for kb in c["kerbs"]:
            s0, s1 = kb["s0"], kb["s1"]
            length = (s1 - s0) % rb.L
            n_st = max(2, int(length / KERB_STEP_M) + 1)
            sgn = 1.0 if kb["side"] == "L" else -1.0
            sts = []
            for q in range(n_st):
                s = (s0 + q * KERB_STEP_M) % rb.L if q < n_st - 1 else s1
                x, z, y, w, vf = rb._interp(s)
                xa, za = rb._interp((s - 1.0) % rb.L)[:2]
                xb, zb = rb._interp((s + 1.0) % rb.L)[:2]
                tx, tz = xb - xa, zb - za
                L = math.hypot(tx, tz) or 1.0
                k = int(round(vf)) % len(rb.raw)
                inset = cw_ei[k] or EDGE_INSET_M
                half = w / 2.0
                outer = half - inset - KERB_CLEAR_M if mode == "road" else half - 0.05
                d = min(q, n_st - 1 - q)
                h = max(0.005, KERB_H * min(1.0, (d + 0.5) / KERB_TAPER_STATIONS))
                sts.append({"s": s, "k": k, "cx": x, "cz": z, "y_hint": y + LIFT, "tx": tx / L, "tz": tz / L,
                            "lip": sgn * (outer - KERB_W), "h": h, "arc": q * KERB_STEP_M})
            sts, skipped = drop_folded_stations(sts, sgn)
            plans.append({"kind": "kerb", "apex": kb["apex_vertex"], "side": kb["side"], "sub": kb["kind"],
                          "run": [kb["i"], kb["j"]], "stations": sts, "length_m": round(length, 1),
                          "fold_skipped": skipped})
    return plans


def drop_folded_rings(rings):
    """The strip-ring form of drop_folded_stations: at an inside apex whose raw local radius is under
    the ~8 m lip offset (Navajo/Jackson, Jackson/Lake Murray, the seam, the hairpin's inner curl) the
    offset path runs backwards for a ring or three and a swept strip there is a knot of overlapping
    faces, a sharp V the driver would hit; dropping those rings chords the wall across the fold at the
    lip's own crossing point. The chain (lat 0) never folds. Returns (rings, n_dropped)."""
    if len(rings) < 3:
        return rings, 0
    def pos(r):
        lx, lz = left_normal(r["tx"], r["tz"])
        return r["cx"] + lx * r["lat"], r["cz"] + lz * r["lat"]
    keep, dropped = [rings[0]], 0
    for r in rings[1:]:
        px, pz = pos(keep[-1])
        x, z = pos(r)
        if (x - px) * r["tx"] + (z - pz) * r["tz"] < 0.0:
            dropped += 1
            continue
        keep.append(r)
    if len(keep) < 2:
        return rings, 0
    return keep, dropped


def drop_folded_stations(sts, sgn):
    """Where the pavement lip's local radius goes negative (the hairpin's inside lip: R 9.4 m apex
    on a 30 m flare) the offset path runs BACKWARDS against the centreline tangent and the ribbon
    folds over itself; a kerb swept there zig-zags inside the fold. Those stations are dropped (the
    prep's bury-cull would discard their faces anyway); the strip then joins the fold's entry to its
    exit, which coincide where the lip path crosses itself. Returns (stations, n_dropped)."""
    if len(sts) < 3:
        return sts, 0
    def lip_xz(s):
        lx, lz = left_normal(s["tx"], s["tz"])
        mid = s["lip"] + sgn * KERB_W / 2.0
        return s["cx"] + lx * mid, s["cz"] + lz * mid
    keep = [sts[0]]
    dropped = 0
    for s in sts[1:]:
        px, pz = lip_xz(keep[-1])
        x, z = lip_xz(s)
        if (x - px) * s["tx"] + (z - pz) * s["tz"] < 0.0:
            dropped += 1
            continue
        keep.append(s)
    if len(keep) < 2:
        return sts, 0
    return keep, dropped


# ---------------------------------------------------------------------------------------------
# names
def object_name(plan):
    if plan["kind"] == "chain":
        return f"1WALL_race_kbar_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "edge":
        return f"1WALL_race_edge_{plan['side']}_{plan['street']}_{plan['run'][0]}_{plan['part']}"
    if plan["kind"] == "kerb":
        return f"1KERB_race_{plan['apex']}_{plan['sub']}"
    if plan["kind"] == "collider":
        return f"1WALL_racecol_{plan['part']}"
    raise ValueError(plan["kind"])


# ---------------------------------------------------------------------------------------------
# spawn clearance (grid / pit exclusions): nothing of a layout's grid or pit row may stand in a strip
def nearest_vertex(pts, m, x, z, cells=None):
    best, bi = float("inf"), 0
    for k in range(m):
        d = (pts[k][0] - x) ** 2 + (pts[k][2] - z) ** 2
        if d < best:
            best, bi = d, k
    return bi


def spawn_clearance(pts, widths, bands, dummies, mode="road"):
    """(hard, notes): hard = a car on this spawn OVERLAPS a strip (never ship); notes = clear by
    less than SPAWN_MARGIN_M (Q6: walk mode gives Alvarado's outer grid column 1.0 m more)"""
    m = unique_count(pts)
    cw, ei = bands["centre_w_by_vertex"], bands["edge_inset_by_vertex"]
    hard, notes = [], []
    for name, p in dummies.items():
        if name.startswith("_") or not any(name.startswith(f) for f in FACING):
            continue
        x, y, z = p
        k = nearest_vertex(pts, m, x, z)
        tx, tz = tangent(pts, k, m)
        lx, lz = left_normal(tx, tz)
        lat = (x - pts[k][0]) * lx + (z - pts[k][2]) * lz
        half = widths[k] / 2.0
        face = (half - (ei[k] or EDGE_INSET_M)) if mode == "road" else half + 0.11
        clear = face - (abs(lat) + CAR_HALF_W)
        if clear < 0:
            hard.append(f"{name} at v{k} lat {lat:+.2f}: car edge {abs(lat) + CAR_HALF_W:.2f} m overlaps the edge-strip face {face:.2f} m")
        elif clear < SPAWN_MARGIN_M:
            notes.append(f"{name} at v{k} lat {lat:+.2f}: {clear:.2f} m clear of the edge-strip face ({face:.2f} m)")
        if cw[k] > 0:
            clear_c = abs(lat) - CAR_HALF_W - cw[k] / 2.0
            if clear_c < 0:
                hard.append(f"{name} at v{k} lat {lat:+.2f}: overlaps the centre chain")
            elif clear_c < SPAWN_MARGIN_M:
                notes.append(f"{name} at v{k} lat {lat:+.2f}: {clear_c:.2f} m clear of the centre chain")
    return hard, notes


# ---------------------------------------------------------------------------------------------
# dry-run dummies (the spec's grids) — tools/layout_dummies.py is the real producer (another agent)
def synth_dummies(pts, widths, layout, n_pits=8):
    """FULL dummy set for one layout in the engine frame + the underscore keys the spec names.
    Grid: pole at grid_vertex, +offset right of THIS layout's travel; AC_START_g at pole - 5.5 g m in
    two staggered columns (lane centre +- 1.4 m); pits single file at the lane centre 45 + 7 (p+1) m
    behind; AC_TIME_0 at line_vertex across the full width; sectors at sector_vertices."""
    m = unique_count(pts)
    st = stations(pts)
    rev = layout.get("direction") == "reverse"
    sgn = -1.0 if rev else 1.0           # vertex index step along travel
    s = layout["start"]
    out, yaw, vtx, rot = {}, {}, {}, {}

    def at(k, right_m, lift=LIFT + 0.30):
        k %= m
        tx, tz = tangent(pts, k, m)
        if rev:
            tx, tz = -tx, -tz
        rx, rz = tz, -tx                 # right of travel
        p = pts[k]
        return [round(p[0] + rx * right_m, 3), round(p[1] + lift, 3), round(p[2] + rz * right_m, 3)], (tx, tz)

    def behind_vertex(k0, metres):
        """the vertex `metres` behind k0 in the direction of travel"""
        target = st[k0] - sgn * metres
        best, bk = float("inf"), k0
        for k in range(m):
            d = abs(st[k] - target)
            if d < best:
                best, bk = d, k
        return bk

    def facing(name, k, right_m):
        p, (tx, tz) = at(k, right_m)
        out[name] = p
        yaw[name] = round(math.degrees(math.atan2(tx, -tz)), 3)
        vtx[name] = k % m
        rot[name] = right_m

    off = float(s["offset_right_m"])
    g0 = int(s["grid_vertex"])
    facing("AC_START_0", g0, off)
    facing("AC_HOTLAP_START_0", g0, off)
    for g in range(1, n_pits):
        k = behind_vertex(g0, 5.5 * g)
        facing(f"AC_START_{g}", k, off + (1.4 if g % 2 else -1.4))
    for p in range(n_pits):
        k = behind_vertex(g0, 45.0 + 7.0 * (p + 1))
        facing(f"AC_PIT_{p}", k, off)
    line = int(s["line_vertex"])
    gates = [line] + [int(v) for v in s.get("sector_vertices", [])]
    for gi, k in enumerate(gates):
        half = widths[k % m] / 2.0 - 0.3
        pl, _ = at(k, -half, LIFT)       # left of travel
        pr, _ = at(k, +half, LIFT)
        out[f"AC_TIME_{gi}_L"] = pl
        out[f"AC_TIME_{gi}_R"] = pr
        vtx[f"AC_TIME_{gi}_L"] = vtx[f"AC_TIME_{gi}_R"] = k % m
    out["_layout"] = layout["id"]
    out["_direction"] = layout.get("direction", "forward")
    out["_synthesised"] = True
    out["_doc"] = ("SYNTHESISED for a dry run by tools/race_furniture.synth_dummies from layouts[].start — "
                   "tools/layout_dummies.py is the producer of record; underscore keys are not dummies")
    out["_yaw_deg"] = yaw
    out["_vertex"] = vtx
    out["_right_of_travel_m"] = rot
    return out


def dummies_positions(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------------------------
def plan_all(proj, bands, mode="road", height=BARRIER_H, kerbs=True):
    """everything the Blender tool needs, plus the corner table for the report"""
    pts, widths = load_centerline(proj)
    mb = json.loads((Path(proj) / "data" / "median_bands.json").read_text(encoding="utf-8"))
    island_w = mb["island_w_by_vertex"]
    if len(island_w) != len(pts):
        raise SystemExit(f"[race] median_bands {len(island_w)} vs centerline {len(pts)} vertices")
    plans = chain_plans(pts, widths, island_w, bands, height) + edge_plans(pts, widths, bands, mode, height)
    corners = []
    if kerbs:
        rb, corners = detect_kerb_corners(pts, widths, bands)
        for d in apply_declared_kerbs(rb, corners, bands):
            print(f"[race] WARNING declared kerb apex v{d.get('apex')} {d.get('side')} {d.get('kind')} "
                  f"matches no detected corner — not authored")
        plans += kerb_plans(rb, corners, bands, mode)
    return pts, widths, island_w, plans, corners


if __name__ == "__main__":
    # CLI: write a stand-in bands file / synthesised dummies into a (scratch) project and print the plan
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--standin-bands", action="store_true", help="write data/barrier_bands.json (stand-in) if absent")
    ap.add_argument("--synth-dummies", action="store_true", help="write data/dummies_<id>.json (synthesised) if absent")
    ap.add_argument("--edge-mode", default=None, choices=["road", "walk"])
    a = ap.parse_args()
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    race_cfg = cfg.get("race", {}) or {}
    pts, widths = load_centerline(proj)
    mode = a.edge_mode or race_cfg.get("edge_mode", "road")
    bands = load_bands(proj)
    if bands is None and a.standin_bands:
        mb = json.loads((proj / "data" / "median_bands.json").read_text(encoding="utf-8"))
        mouths = json.loads((proj / "data" / "mouths.json").read_text(encoding="utf-8")).get("mouths", [])
        spans = json.loads((proj / "data" / "bridge.spans.auto.json").read_text(encoding="utf-8"))
        tmp = standin_bands(pts, widths, mb["island_w_by_vertex"], mouths, spans, dict(race_cfg, edge_mode=mode))
        _, corners = detect_kerb_corners(pts, widths, tmp)
        bands = standin_bands(pts, widths, mb["island_w_by_vertex"], mouths, spans, dict(race_cfg, edge_mode=mode), corners)
        (proj / "data" / "barrier_bands.json").write_text(json.dumps(bands), encoding="utf-8")
        print(f"[race] wrote STAND-IN data/barrier_bands.json: chain {bands['params']['chain_length_m']} m, "
              f"{len(bands['runs'])} runs, {len(bands['closed_mouths'])} closed mouths, {len(bands['kerbs'])} kerbs")
    if a.synth_dummies:
        for lo in cfg.get("layouts", []):
            p = proj / "data" / f"dummies_{lo['id']}.json"
            if p.exists() or not lo.get("start"):
                continue
            p.write_text(json.dumps(synth_dummies(pts, widths, lo), indent=1), encoding="utf-8")
            print(f"[race] wrote SYNTHESISED {p.name} ({lo.get('direction', 'forward')})")
    if bands is not None:
        mb = json.loads((proj / "data" / "median_bands.json").read_text(encoding="utf-8"))
        for pr in check_bands(bands, pts, mb["island_w_by_vertex"]):
            print(f"[race] bands: {pr}")
        _, _, _, plans, corners = plan_all(proj, bands, mode)
        for c in corners:
            print(f"[race] corner apex v{c['apex_vertex']} R {c['R_apex_m']} m D {c['D_deg']} deg "
                  f"{'chained' if c['chained'] else 'open'} -> {[k['side'] + '/' + k['kind'] for k in c['kerbs']]}")
        print(f"[race] {len(plans)} objects planned: "
              f"{sum(1 for p in plans if p['kind'] == 'chain')} chain, {sum(1 for p in plans if p['kind'] == 'edge')} edge, "
              f"{sum(1 for p in plans if p['kind'] == 'kerb')} kerb")
