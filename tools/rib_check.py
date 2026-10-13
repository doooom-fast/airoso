"""Washboard / staircase ribbing on the BUILT terrain — ledger 0046 fix round 2 (the visual lens's "6 to 10 parallel steps").

READ-ONLY on the gate OBJ (data/track.obj, kn5_to_gate_obj of the shipped road kn5 — L5: the artifact, never the
data that placed it). What it looks for, in plain terms: the terrain is a lattice of 5 / 20 / 40 m cells. A real
slope, bank or valley wider than two cells bends SMOOTHLY from one lattice node to the next. A feature NARROWER than
two cells (a 7 m concrete channel, a 3 m ditch, a bench) cannot be drawn by the lattice: sampled at points, it lands in
one node and misses the next, and the triangles between them fold up-down-up — the staircase the eye reads as ribs.
That up-down-up is the lattice's highest representable frequency (period two cells, "Nyquist"), so the detector is a
zig-zag of the second difference along every lattice row and column:

    d2(k) = h(k-1) - 2 h(k) + h(k+1)     (one cell apart, the row's own spacing)
    a RIB NODE is k where d2(k) and d2(k+1) have opposite signs and both exceed RIB_M in size

A smooth valley gives d2 of one sign across its floor; a slope break gives one spike of d2 and nothing either side;
only a sub-cell feature gives the alternation. A rib that continues STRAIGHT into the neighbouring parallel row is a
feature running along a lattice axis (a median wall, a bench beside the freeway): drawn as one straight ridge — too
narrow for the cells, but not a staircase — and reported apart. A STAIRCASE rib shifts sideways from row to row: a
slanting feature folded cell by cell, the washboard. Only staircase ribs at the finest step are gated. Rows are walked at each tier's own spacing (5, 20 and 40 m: 2, 8 and 16
base units) and only where no finer node lies between (so a 20 m step never skips over 5 m nodes).

A second, triangle-level measure: in a plain square cell the two triangles fold along one diagonal. If that diagonal
joins the two corners that differ MORE in height than the other two (a CROSS-GRAIN fold: down the slope, across a
channel), the fold crosses the feature in every cell it passes and draws the same staircase even from good heights.

    python tools/rib_check.py <project> [--obj <gate obj>] [--json <out>] [--box name:x0:x1:z0:z1 ...]

Reports both measures by amplitude and by pavement distance, the densest 50 m hotspots, each --box, and the alternation
at the 20 / 40 m steps (natural hill roughness at that scale — information, not gated). Ground within NEAR_M of a
pavement (1ROAD / 1KERB vertices) is counted apart: it is the graded near-road surface criterion 7 holds to v0.17.1
and the drive gates measure. Exit 1 when more than MAX_RIBS 5 m staircase rib nodes over RIB_M, or more than MAX_FOLDS
cross-grain cells over FOLD_M, lie beyond NEAR_M (fleet/GATES-CHANGELOG.md 2026-10-13; all four numbers invented,
measured on the 2026-10-12 build that showed the ribs and on the fix).
A third measure (ledger 0046 fix round 4) reads BETWEEN the nodes: STEP JOGS. A sharp riser (a cut-slope bench, a
drainage ledge, 4-6 m tall and ~1.5 m wide in 3DEP) crossing the 5 m lattice at a slant cannot be drawn by the lattice:
it sits between the same two rows of nodes for several cells, then jumps a whole row. The lattice-node measures above
read it as a straight ridge with an occasional staircase node, so round 3 passed a washboard the visual lens could see
from the College Ave deck. Scan lines a quarter cell off every 5 m lattice line cut the BUILT finest-tier triangles;
each riser crossing (a run as steep as JOG_SLOPE, dropping JOG_DROP_M within JOG_RUN_MAX_M) is followed from line to
line, and a JOG is a step between consecutive crossings that outruns the riser's own pace by JOG_M. A washboard is a
neighbourhood of them: exit 1 when more than MAX_JOG_CLUSTER jogs beyond NEAR_M lie within JOG_CLUSTER_M of one jog.
Frame: local, x = E, y = up, z = N; the lattice frame is data/terrain.tiers.json.gz "frame".
"""
from __future__ import annotations

import gzip
import json
import math
import sys
from array import array
from pathlib import Path

TERRAIN = ("1GRASS", "GRASS_FAR")
PAVEMENT = ("1ROAD", "1KERB")
STEPS = (2, 8, 16)          # base units: 5, 20, 40 m cells (Lake Murray's tiers; any even step works)
RIB_M = 2.0                 # a staircase rib: both alternating second differences over this (m) [invented]
MAX_RIBS = 100              # staircase rib nodes allowed beyond NEAR_M [invented] — the 2026-10-12 build (ship9) has 331,
                            # the fix round 2 build 53 (GATES-CHANGELOG 2026-10-13 has the calibration, including a
                            # first 4 m / 150 cut on every rib that could not tell the two apart)
FOLD_M = 1.0                # cross-grain fold: the chosen diagonal's height difference exceeds the other's by this [invented]
MAX_FOLDS = 100             # cross-grain cells allowed beyond NEAR_M [invented]; ship9 15,856, the fix 33
NEAR_M = 20.0               # criterion 7's near-road band (ledger 0046)
# STEP JOGS (ledger 0046 fix round 4): a sharp riser at a slant, drawn as a staircase. Read on the BUILT surface itself
# (scan lines through the triangles), so a riser drawn through break-line vertices between the lattice nodes is seen
# as drawn — the lattice-node measures above cannot see between the nodes. All [invented]:
JOG_CELL_MAX_M = 7.6        # finest-tier triangles only (a 5 m cell's diagonal is 7.1 m; 20 m cells are 20+ m)
JOG_SLOPE = 0.7             # a riser segment is at least this steep (35 degrees)
JOG_DROP_M = 2.0            # ... and the riser drops at least this much (RIB_M's scale)
JOG_RUN_MAX_M = 8.0         # ... within this far along the line (a riser, not a hillside)
JOG_LINK_M = 8.0            # the same riser on the next line lies within this along it
JOG_DY_M = 3.0              # ... and within this in height at its half-drop
JOG_M = 2.0                 # a jog: a step between consecutive crossings beyond the riser's own pace by this
                            # (a row is 5 m; a straight riser at any angle steps exactly at its pace)
JOG_CLUSTER_M = 75.0        # a WASHBOARD: the jogs within this radius of one another...
MAX_JOG_CLUSTER = 5         # ... more than this many of them (the lens saw 6-10 parallel steps; the round-3 build
                            # holds 7 within 75 m at two places, the break-line build 4)
ON_LATTICE = 0.01           # a vertex is a lattice node when its (I, J) is within this of an integer
AMPS = (0.5, 1.0, 2.0, 4.0)


def read_obj(path: Path):
    """(terrain vertices [(x, y, z)], terrain triangles [(a, b, c)] indexing them, pavement vertices [(x, z)])"""
    xs, ys, zs = array("d"), array("d"), array("d")
    ter, pav = set(), set()
    tfaces = []
    cur = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            c = line[:2]
            if c == "v ":
                p = line.split()
                xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
            elif c == "f ":
                if cur is None:
                    continue
                idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
                cur.update(idx)
                if cur is ter:
                    tfaces.extend((idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1))
            elif c in ("o ", "g "):
                name = line[2:].strip()
                cur = ter if name.startswith(TERRAIN) else (pav if name.startswith(PAVEMENT) else None)
    order = sorted(ter)
    remap = {v: n for n, v in enumerate(order)}
    return ([(xs[i], ys[i], zs[i]) for i in order], [(remap[a], remap[b], remap[c]) for a, b, c in tfaces],
            [(xs[i], zs[i]) for i in sorted(pav)])


def lattice(verts, frame, on_lines=None):
    """({(I, J): y} for every terrain vertex on the base lattice (first one wins at a tile seam), [key or None] per
    vertex). ``on_lines`` (a dict, filled when given): every vertex that lies ON a lattice line between nodes — a
    break-line vertex (ledger 0046 fix round 4) — as {(axis, line): [position along it, base units]}, axis 0 = a row
    of constant J (positions in I), 1 = a column of constant I"""
    x0, z0, ux, uz = frame
    out, keys = {}, []
    for x, y, z in verts:
        fi, fj = (x - x0) / ux, (z - z0) / uz
        I, J = round(fi), round(fj)
        on_i, on_j = abs(fi - I) < ON_LATTICE, abs(fj - J) < ON_LATTICE
        if on_i and on_j:
            out.setdefault((I, J), y)
            keys.append((I, J))
        else:
            keys.append(None)
            if on_lines is not None and (on_i or on_j):
                if on_j:
                    on_lines.setdefault((0, J), []).append(fi)
                else:
                    on_lines.setdefault((1, I), []).append(fj)
    if on_lines is not None:
        for k in on_lines:
            on_lines[k].sort()
    return out, keys


def _drawn_between(on_lines, ax, line, a, b):
    """True when a break-line vertex lies on lattice line ``line`` strictly between positions a < b: the surface
    there is drawn through it, not the straight line the two nodes imply"""
    import bisect
    v = on_lines.get((ax, line)) if on_lines else None
    if not v:
        return False
    k = bisect.bisect_right(v, a + 1e-6)
    return k < len(v) and v[k] < b - 1e-6


def cross_grain(tris, keys, H, amp_min=0.0):
    """[(I, J, r, excess)] for every square lattice cell meshed as two triangles whose shared diagonal joins the
    corners that differ MORE in height than the other two by ``excess`` > amp_min: the fold runs across the
    ground's grain (down the slope, across a channel) instead of along it — the triangulation half of a staircase.
    (I, J) is the cell's SW corner, r its side in base units."""
    by_diag = {}
    for t in tris:
        k = [keys[v] for v in t]
        if None in k:
            continue
        for a in range(3):
            p, q, o = k[a], k[(a + 1) % 3], k[(a + 2) % 3]
            dI, dJ = abs(p[0] - q[0]), abs(p[1] - q[1])
            if dI and dI == dJ and (o[0] in (p[0], q[0])) and (o[1] in (p[1], q[1])) and o not in (p, q):
                d = (min(p, q), max(p, q))
                by_diag.setdefault(d, []).append(o)
                break
    out = []
    for (p, q), opp in by_diag.items():
        if len(opp) != 2 or opp[0] == opp[1]:
            continue
        hp, hq, h0, h1 = H.get(p), H.get(q), H.get(opp[0]), H.get(opp[1])
        if None in (hp, hq, h0, h1):
            continue
        ex = abs(hp - hq) - abs(h0 - h1)
        if ex > amp_min:
            r = abs(p[0] - q[0])
            out.append((min(p[0], q[0]), min(p[1], q[1]), r, ex))
    return out


def ribs(H, steps=STEPS, amp_min=min(AMPS), on_lines=None):
    """[(I, J, axis, step, amplitude)] for every rib node: d2 alternates sign between k and k+1 along a row/column
    of nodes ``step`` base units apart with no finer node between, both |d2| over ``amp_min``. A row whose surface
    between those nodes is drawn through break-line vertices (``on_lines``) is not the nodes' straight line and is
    left to the step-jog measure"""
    out = []
    for (I, J), h0 in H.items():
        for ax in (0, 1):
            for r in steps:
                def at(k):
                    return H.get((I + k * r, J) if ax == 0 else (I, J + k * r))
                mid = (I + r // 2, J) if ax == 0 else (I, J + r // 2)
                if mid in H:                       # finer nodes lie between: that row belongs to a finer step
                    continue
                hm, h1, h2 = at(-1), at(1), at(2)
                if hm is None or h1 is None or h2 is None:
                    continue
                mid2 = (I - r // 2, J) if ax == 0 else (I, J - r // 2)
                mid3 = (I + r + r // 2, J) if ax == 0 else (I, J + r + r // 2)
                if mid2 in H or mid3 in H:
                    continue
                if on_lines:
                    line, pos = (J, I) if ax == 0 else (I, J)
                    if _drawn_between(on_lines, ax, line, pos - r, pos + 2 * r):
                        continue
                a = hm - 2.0 * h0 + h1
                b = h0 - 2.0 * h1 + h2
                if a * b < 0.0:
                    amp = min(abs(a), abs(b))
                    if amp > amp_min:
                        out.append((I, J, ax, r, amp))
    return out


def staircase(rows):
    """per rib (I, J, axis, step, amp): True when it is a STAIRCASE rib — the same rib does not continue straight
    into either neighbouring parallel row (a feature running along the lattice axis, e.g. a median wall or a bench
    beside the freeway, is drawn as one straight 1-cell ridge: a feature the cells cannot resolve, but not ribs). A
    slanting feature shifts sideways from row to row, which is what folds it into a staircase."""
    have = {(I, J, ax, r) for I, J, ax, r, _a in rows}
    out = []
    for I, J, ax, r, _a in rows:
        nb = ((I, J - r, ax, r), (I, J + r, ax, r)) if ax == 0 else ((I - r, J, ax, r), (I + r, J, ax, r))
        out.append(not any(k in have for k in nb))
    return out


def scan_profiles(verts, tris, frame, max_extent_m=JOG_CELL_MAX_M):
    """the BUILT surface cut along scan lines a quarter cell off every 5 m lattice line, both ways: {(axis, m):
    [(s0, y0, s1, y1)]} sorted by s, where axis 0 = lines of constant x (profile along z), 1 = constant z (along x),
    m = the line's index (consecutive lines are one 5 m cell apart). Only triangles of the finest tier (horizontal
    extent <= ``max_extent_m``): the staircase is a finest-tier artifact. Exact: each triangle contributes the
    segment where the plane of the line cuts it."""
    x0, z0, ux, uz = frame
    out = {}
    for t in tris:
        P = [verts[v] for v in t]
        xs = [p[0] for p in P]
        zs = [p[2] for p in P]
        if max(xs) - min(xs) > max_extent_m or max(zs) - min(zs) > max_extent_m:
            continue
        for axis, (c0, u, lo, hi) in enumerate(((x0, ux, min(xs), max(xs)), (z0, uz, min(zs), max(zs)))):
            # line m sits at c0 + (2 m + 0.5) u
            m0 = math.ceil(((lo - c0) / u - 0.5) / 2.0)
            m1 = math.floor(((hi - c0) / u - 0.5) / 2.0)
            for m in range(m0, m1 + 1):
                c = c0 + (2 * m + 0.5) * u
                hits = []
                for a in range(3):
                    p, q = P[a], P[(a + 1) % 3]
                    pc, qc = (p[0], q[0]) if axis == 0 else (p[2], q[2])
                    if (pc - c) * (qc - c) < 0.0:
                        f = (c - pc) / (qc - pc)
                        s = (p[2] + f * (q[2] - p[2])) if axis == 0 else (p[0] + f * (q[0] - p[0]))
                        hits.append((s, p[1] + f * (q[1] - p[1])))
                if len(hits) == 2:
                    (sa, ya), (sb, yb) = sorted(hits)
                    if sb - sa > 1e-6:
                        out.setdefault((axis, m), []).append((round(sa, 4), ya, round(sb, 4), yb))
    for k in out:
        out[k] = sorted(set(out[k]))
    return out


def step_events(segs, slope_min=JOG_SLOPE, drop_min=JOG_DROP_M, run_max=JOG_RUN_MAX_M):
    """riser crossings on one scan profile: maximal runs of contiguous segments as steep as ``slope_min`` the same way,
    no longer than ``run_max`` (a riser, not a hillside), dropping ``drop_min`` or more. Returns [(s, y, sign)]: where
    the run has made half its drop, the height there, +1 rising with s / -1 falling"""
    ev = []
    run = []

    def close():
        if not run:
            return
        s0, s1 = run[0][0], run[-1][2]
        drop = run[-1][3] - run[0][1]
        if abs(drop) >= drop_min and s1 - s0 <= run_max:
            half = run[0][1] + drop / 2.0
            for a, ya, b, yb in run:
                if (yb - half) * (ya - half) <= 0.0 and yb != ya:
                    s = a + (half - ya) / (yb - ya) * (b - a)
                    ev.append((s, half, 1 if drop > 0 else -1))
                    break
        run.clear()

    prev_end = None
    for a, ya, b, yb in segs:
        if b - a < 1e-3:
            continue
        sl = (yb - ya) / (b - a)
        sign = 1 if sl > 0 else -1
        steep = abs(sl) >= slope_min
        if run and (not steep or sign != (1 if run[-1][3] > run[-1][1] else -1) or prev_end is None
                    or abs(a - prev_end) > 0.05):
            close()
        if steep:
            run.append((a, ya, b, yb))
        prev_end = b
    close()
    return ev


def step_jogs(profiles, frame, link_m=JOG_LINK_M, dy_m=JOG_DY_M, jog_m=JOG_M):
    """a riser drawn as a STAIRCASE. Each riser crossing is followed from one scan line to the next (same sign,
    within ``link_m`` along the line and ``dy_m`` in height at its half-drop; up to two lines may be skipped, at that
    multiple of the reach: the line where an aliased riser changes rows often shows no single crossing). A real bench
    or channel drifts along the lines at its own steady pace (a straight one at tan(angle) x 5 m per line, a 50 m
    radius bends that by ~0.5 m per line); an aliased one sits between the same two node rows for several cells and
    then jumps a whole 5 m row. So a JOG is a step between two consecutive crossings that moves more than the
    riser's pace over the three lines either side would by ``jog_m`` or more. Returns [(x, z, excess)]."""
    x0, z0, ux, uz = frame
    ev = {k: step_events(v) for k, v in profiles.items()}
    out = []
    used = set()

    def link(e, cand, reach):
        best = None
        for n, c in enumerate(cand):
            if c[2] == e[2] and abs(c[0] - e[0]) <= reach and abs(c[1] - e[1]) <= dy_m:
                d = abs(c[0] - e[0])
                if best is None or d < best[0]:
                    best = (d, n)
        return None if best is None else best[1]

    for axis, m0 in sorted(ev):
        for n0 in range(len(ev[(axis, m0)])):
            if (axis, m0, n0) in used:
                continue
            chain = [(m0, ev[(axis, m0)][n0])]
            used.add((axis, m0, n0))
            m, e = m0, ev[(axis, m0)][n0]
            while True:
                nxt = None
                for step in (1, 2, 3):
                    cand = ev.get((axis, m + step), [])
                    k = link(e, cand, link_m * step)
                    if k is not None and (axis, m + step, k) not in used:
                        nxt = (m + step, k)
                        break
                if nxt is None:
                    break
                m, k = nxt
                e = ev[(axis, m)][k]
                used.add((axis, m, k))
                chain.append((m, e))
            if len(chain) < 3:
                continue
            for q in range(1, len(chain)):
                (ma, ea), (mb, eb) = chain[q - 1], chain[q]
                win = [c for c in chain if ma - 3 <= c[0] <= mb + 3]
                span = win[-1][0] - win[0][0]
                if span < 3:
                    continue
                pace = abs(win[-1][1][0] - win[0][1][0]) / span      # the riser's own drift, m per line
                excess = abs(eb[0] - ea[0]) - pace * (mb - ma)
                if excess >= jog_m:
                    c = (x0 if axis == 0 else z0) + (2 * mb + 0.5) * (ux if axis == 0 else uz)
                    out.append((c, eb[0], excess) if axis == 0 else (eb[0], c, excess))
    return out


class Pavement:
    def __init__(self, pts, cell=10.0):
        self.cell = cell
        self.b = {}
        for x, z in pts:
            self.b.setdefault((math.floor(x / cell), math.floor(z / cell)), []).append((x, z))

    def dist(self, x, z, reach=60.0):
        c = self.cell
        n = int(math.ceil(reach / c))
        i0, j0 = math.floor(x / c), math.floor(z / c)
        best = reach
        for i in range(i0 - n, i0 + n + 1):
            for j in range(j0 - n, j0 + n + 1):
                for px, pz in self.b.get((i, j), ()):
                    d = math.hypot(px - x, pz - z)
                    if d < best:
                        best = d
        return best


def _summ(rows, amps, boxes, gate_amp):
    """rows: (x, z, amp, pavement distance) -> counts by amplitude (beyond / within NEAR_M), hotspots, boxes"""
    rep = {"by_amplitude": {}, "hotspots": [], "boxes": {}}
    for a in amps:
        rep["by_amplitude"][f">{a:g}m"] = {"beyond_near": sum(1 for w in rows if w[2] > a and w[3] > NEAR_M),
                                           "near_road": sum(1 for w in rows if w[2] > a and w[3] <= NEAR_M)}
    cells = {}
    for x, z, amp, d in rows:
        if amp > gate_amp and d > NEAR_M:
            c = cells.setdefault((math.floor(x / 50.0), math.floor(z / 50.0)), [0, 0.0])
            c[0] += 1
            c[1] = max(c[1], amp)
    for (i, j), (n, mx) in sorted(cells.items(), key=lambda kv: (-kv[1][0], kv[0]))[:10]:
        rep["hotspots"].append({"x": i * 50 + 25, "z": j * 50 + 25, "n": n, "max_m": round(mx, 2)})
    for name, bx0, bx1, bz0, bz1 in boxes:
        inb = [w for w in rows if bx0 <= w[0] <= bx1 and bz0 <= w[1] <= bz1]
        rep["boxes"][name] = {**{f">{a:g}m": sum(1 for w in inb if w[2] > a) for a in amps},
                              "max_m": round(max([w[2] for w in inb], default=0.0), 2)}
    return rep


def jog_cluster(rows, radius=JOG_CLUSTER_M):
    """(the most jogs within ``radius`` of one jog, its (x, z)) over [(x, z, ...)]"""
    best = (0, None)
    for a in rows:
        n = sum(1 for b in rows if math.hypot(a[0] - b[0], a[1] - b[1]) <= radius)
        if n > best[0]:
            best = (n, (round(a[0], 1), round(a[1], 1)))
    return best


def run(proj: Path, obj: Path | None = None, boxes=(), rib_m=RIB_M, max_ribs=MAX_RIBS, fold_m=FOLD_M,
        max_folds=MAX_FOLDS, max_cluster=MAX_JOG_CLUSTER):
    proj = Path(proj)
    T = json.loads(gzip.decompress((proj / "data" / "terrain.tiers.json.gz").read_bytes()).decode("utf-8"))
    frame = T["frame"]
    obj = obj or proj / "data" / "track.obj"
    verts, tris, pav = read_obj(obj)
    on_lines = {}
    H, keys = lattice(verts, frame, on_lines)
    P = Pavement(pav)
    x0, z0, ux, uz = frame
    dcache = {}

    def dist(x, z):
        k = (round(x, 1), round(z, 1))
        if k not in dcache:
            dcache[k] = P.dist(x, z)
        return dcache[k]

    nyq = [w for w in ribs(H, amp_min=min(AMPS), on_lines=on_lines)]
    fine_all = [w for w in nyq if w[3] == STEPS[0]]
    st = staircase(fine_all)
    fine = [(x0 + I * ux, z0 + J * uz, amp) for (I, J, ax, r, amp), s_ in zip(fine_all, st) if s_]
    straight = [(x0 + I * ux, z0 + J * uz, amp) for (I, J, ax, r, amp), s_ in zip(fine_all, st) if not s_]
    coarse = {}
    for I, J, ax, r, amp in nyq:
        if r != STEPS[0] and amp > rib_m:
            coarse[f"{r * (ux + uz) / 2:.0f}"] = coarse.get(f"{r * (ux + uz) / 2:.0f}", 0) + 1
    rows_n = [(x, z, a, dist(x, z)) for x, z, a in fine]
    rows_s = [(x, z, a, dist(x, z)) for x, z, a in straight]
    cg = cross_grain(tris, keys, H, amp_min=min(AMPS))
    rows_c = []
    for I, J, r, ex in cg:
        x, z = x0 + (I + r / 2) * ux, z0 + (J + r / 2) * uz
        rows_c.append((x, z, ex, dist(x, z)))
    rep = {"obj": str(obj), "lattice_nodes": len(H), "terrain_vertices": len(verts), "near_m": NEAR_M,
           "nyquist": {"rib_m": rib_m, "max": max_ribs, **_summ(rows_n, AMPS, boxes, rib_m),
                       "coarse_cells_info": coarse,
                       "straight_info": _summ(rows_s, AMPS, boxes, rib_m)["by_amplitude"]},
           "cross_grain": {"fold_m": fold_m, "max": max_folds, **_summ(rows_c, AMPS, boxes, fold_m)}}
    n1 = sum(1 for w in rows_n if w[2] > rib_m and w[3] > NEAR_M)
    n2 = sum(1 for w in rows_c if w[2] > fold_m and w[3] > NEAR_M)
    rep["nyquist"]["gated"] = n1
    rep["cross_grain"]["gated"] = n2
    # step jogs on the built surface (ledger 0046 fix round 4)
    jogs = step_jogs(scan_profiles(verts, tris, frame), frame)
    rows_j = [(x, z, j, dist(x, z)) for x, z, j in jogs]
    far_j = [w for w in rows_j if w[3] > NEAR_M]
    n3, at = jog_cluster(far_j)
    rep["step_jogs"] = {"jog_m": JOG_M, "cluster_m": JOG_CLUSTER_M, "max": max_cluster,
                        **_summ(rows_j, (JOG_M,), boxes, JOG_M - 1e-9), "jogs_beyond_near": len(far_j),
                        "gated": n3, "densest_at": at}
    rep["verdict"] = "PASS" if (n1 <= max_ribs and n2 <= max_folds and n3 <= max_cluster) else "FAIL"
    return rep


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("--"):
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    obj = Path(argv[argv.index("--obj") + 1]) if "--obj" in argv else None
    out = Path(argv[argv.index("--json") + 1]) if "--json" in argv else None
    boxes = []
    for k, a in enumerate(argv):
        if a == "--box":
            n, *v = argv[k + 1].split(":")
            boxes.append((n, *map(float, v)))
    rep = run(proj, obj, boxes)
    print(f"[ribs] {rep['obj']}: {rep['lattice_nodes']} lattice nodes of {rep['terrain_vertices']} terrain vertices")
    for m, lim_m, lim_n in (("nyquist", RIB_M, MAX_RIBS), ("cross_grain", FOLD_M, MAX_FOLDS)):
        r = rep[m]
        for k, v in r["by_amplitude"].items():
            print(f"[ribs] {m:11s} {k:>5}: {v['beyond_near']:6d} beyond {NEAR_M:g} m of a pavement, {v['near_road']:6d} within")
        for h in r["hotspots"][:5]:
            print(f"[ribs] {m:11s} hotspot ({h['x']}, {h['z']}): {h['n']}, max {h['max_m']} m")
        for n, b in r["boxes"].items():
            print(f"[ribs] {m:11s} box {n}: {b}")
        print(f"[ribs] {m:11s} gate: {r['gated']} over {lim_m:g} m beyond "
              f"{NEAR_M:g} m (limit {lim_n})")
    j = rep["step_jogs"]
    for h in j["hotspots"][:5]:
        print(f"[ribs] step_jogs   hotspot ({h['x']}, {h['z']}): {h['n']}, max {h['max_m']} m")
    for n, b in j["boxes"].items():
        print(f"[ribs] step_jogs   box {n}: {b}")
    print(f"[ribs] step_jogs   gate: {j['jogs_beyond_near']} riser jogs (a row jump {JOG_M:g} m past the riser's own "
          f"pace) beyond {NEAR_M:g} m; the densest {JOG_CLUSTER_M:g} m: {j['gated']} at {j['densest_at']} (limit "
          f"{j['max']}) — a sharp bench or channel drawn as a staircase, read on the built surface")
    print(f"[ribs] nyquist straight (along a lattice axis, a ridge not a staircase; not gated): "
          f"{ {k: v['beyond_near'] for k, v in rep['nyquist']['straight_info'].items()} }")
    print(f"[ribs] nyquist at 20/40 m cells (> {RIB_M:g} m; natural hill roughness at that scale, not gated): "
          f"{rep['nyquist']['coarse_cells_info']}")
    print(f"[ribs] {rep['verdict']}")
    if out:
        out.write_text(json.dumps(rep, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
