"""A SWITCHBACK PLATFORM AS A PAD, FROM ITS MEASURED OUTLINE: the graded surface traced on the turn's lidar ground
(ledger 0078 round 13).

A switchback whose graded platform is not a circle (Under the Dragon's Douglas Creek: the lidar's outside edge fits a
circle only within 1.57 m rms, so tools/switchback_fit.py refuses it, its 1.0 m rule unchanged) is built the way round 7
built the Lariat's junction mouths: one deck out to its measured outline, on its measured ground, the lap cut at two of
its own rows (tools/lm_pads_blend.py, the draft step `lm_pads`). This tool makes the measurement, the pad record that
step reads (source/pads/<id>.json, the same shape as tools/draft_pad_outline.py's).

THE OUTLINE. Across the line at every lap vertex between the two cuts (and SUB_RAYS rays between vertices), the graded
surface is measured the way tools/road_seek.py measures the bench, on the turn's lidar class-2 grids
(data/lidar/<source>_<id>.npz, tools/lidar_turns.py; read as tools/switchback_measure.py reads them): the road's plane
fitted road_seek.BENCH_CORE_M either side of the line, and how far each way the ground stays within road_seek.BENCH_TOL_M
of it. A side whose bench ends at a face (road_seek.FACE_DROP_M off the plane road_seek.FACE_RUN_M past the end: the cut
bank, the fill slope) is measured there. A side whose bench ends without a face is measured where the graded surface
ends in NAIP if that comes first (the gravel's edge, the cached road_seek tiles: the bench on level ground can run on
into a level fan or a hairpin's level inside), else where the bench ends. A side whose bench runs on past
road_seek.BENCH_MAX_M is measured by NAIP alone, and without NAIP it is the line's own half width (unmeasured, and
reported). The rays' quads are rasterised (MASK_M), clipped to the kept sides of the two lap cuts (draft_pads.lap_cut),
traced (draft_pads.trace_boundary), smoothed (OUTLINE_SIGMA_M; the cut lines kept straight) and resampled (OUTLINE_STEP_M).

THE DECK. A grid (DECK_CELL_M) over the outline: each node the height at the node of the plane fitted (draft_pads.
plane_height, its one trimmed refit) to the lidar cell means within DECK_R_M that lie on the graded surface (the mask:
never the face beyond it), draft_pad_outline.py's numbers.

THE LANE. Per vertex between the cuts, the measured edges along its own normal ("lap"): tools/lm_engine_intake.py
(lm_intake.pad_widths) gives the lane there the widest width CENTRED ON THE LINE that both measured edges allow
(2 x the nearer edge), never wider than measured, and no wider than lm_intake.width_taper allows from its neighbours:
drive_test's wheel paths and its corner rule then read the platform the deck is built on.

    python tools/bench_pad.py <port-track-dir> --line <ws>/data/centerline.local.json \
        --raw <ws>/data/centerline.raw.local.json --id DC --cuts K0 K1 --node K [--cache <road_seek tile dir>]

<ws> is a workshop the same port was drafted into (without this pad): --line is the line the assembler swept the ROAD
along and wrote back (data/centerline.local.json after build_loop_blend: the line lm_pads cuts and drive_test reads), --raw
the intake's own line it smoothed (centerline.raw.local.json). The cuts and the lap vertices are their shared indices; the
edges are measured on the swept line, and each lap vertex also records its raw position, which the intake checks (a record
measured on another line is refused).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

SUB_RAYS = 4             # rays per vertex interval (every ~0.7 m along a ~3 m station)
EDGE_MEDIAN = 5          # [invented] each side's edge is the running median of this many rays (~3 m along)
RAY_STEP_M = 0.5         # road_seek's bench step
NAIP_STEP_M = 0.5
NAIP_REACH_M = 20.0      # [invented] the NAIP read this far along a ray side
NAIP_RUN = 3             # [invented] the gravel's edge: 3 samples (1.5 m) in a row darker or lighter than half-way
NAIP_MIN_CONTRAST = 20.0  # [invented] grey levels between the road and the ground beyond it, or NAIP measures nothing
MASK_M = 0.25            # draft_pad_outline.py's GRID_M
OUTLINE_SIGMA_M = 1.0    # draft_pad_outline.py's SMOOTH_M
OUTLINE_STEP_M = 0.75    # draft_pad_outline.py's STEP_M (JUNCTIONS rule 5)
DECK_CELL_M = 0.5        # draft_pad_outline.py's
DECK_R_M = 2.0           # draft_pad_outline.py's
DECK_EXTRA_M = 1.0       # deck nodes this far outside the outline still read (the deck's triangles reach its edge)
UNC_M = 0.5              # the outline's uncertainty: one lidar cell and the bench's 0.5 m step


class Lidar:
    """every data/lidar/*.npz grid of the port, merged (the mean where they overlap): tools/lidar_turns.py's local frame"""

    def __init__(self, files):
        import numpy as np
        gs = [np.load(f) for f in files]
        self.c = float(gs[0]["cell_m"])
        self.x0 = min(float(g["x0"]) for g in gs)
        self.z0 = min(float(g["z0"]) for g in gs)
        x1 = max(float(g["x0"]) + g["ground"].shape[1] * self.c for g in gs)
        z1 = max(float(g["z0"]) + g["ground"].shape[0] * self.c for g in gs)
        self.nx, self.nz = int(round((x1 - self.x0) / self.c)), int(round((z1 - self.z0) / self.c))
        acc = np.zeros((self.nz, self.nx)); cnt = np.zeros((self.nz, self.nx))
        for g in gs:
            a = g["ground"]
            i0 = int(round((float(g["x0"]) - self.x0) / self.c)); j0 = int(round((float(g["z0"]) - self.z0) / self.c))
            ok = np.isfinite(a)
            acc[j0:j0 + a.shape[0], i0:i0 + a.shape[1]][ok] += a[ok]
            cnt[j0:j0 + a.shape[0], i0:i0 + a.shape[1]][ok] += 1
        self.g = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
        self.files = [Path(f).name for f in files]
        self.points = int(sum(int(g["points"]) for g in gs))
        self.ept = str(gs[0]["ept"])

    def at(self, x, z):
        """switchback_measure.LidarGround.at: the mean of the cells with ground nearest (x, z), 3 x 3 else 5 x 5"""
        import numpy as np
        i, j = int((x - self.x0) / self.c), int((z - self.z0) / self.c)
        if not (0 <= i < self.nx and 0 <= j < self.nz):
            return None
        for r in (0, 1, 2):
            blk = self.g[max(0, j - r):j + r + 1, max(0, i - r):i + r + 1]
            ok = np.isfinite(blk)
            if ok.any():
                return float(blk[ok].mean())
        return None


def bench_side(G, q, n, sgn, a, b):
    """road_seek's bench on one side: (end, bounded by a face, ran on past BENCH_MAX)"""
    import road_seek as rs
    e = 0.0
    while e < rs.BENCH_MAX_M:
        t = sgn * (e + RAY_STEP_M)
        v = G.at(q[0] + n[0] * t, q[1] + n[1] * t)
        if v is None or abs(v - (a + b * t)) >= rs.BENCH_TOL_M:
            break
        e += RAY_STEP_M
    tq = sgn * (e + rs.FACE_RUN_M)
    v = G.at(q[0] + n[0] * tq, q[1] + n[1] * tq)
    face = e < rs.BENCH_MAX_M and v is not None and abs(v - (a + b * tq)) >= rs.FACE_DROP_M
    return e, face, e >= rs.BENCH_MAX_M


def naip_edge(R, q, n, sgn):
    """where the road's NAIP tone ends along one side: the first NAIP_RUN samples in a row past half-way from the road's
    own tone (the median within BENCH_CORE_M of the line) to the ground's (the far quartile on that side); None where the
    two differ by less than NAIP_MIN_CONTRAST"""
    import road_seek as rs
    core = sorted(v for v in (R.at(q[0] + n[0] * t * 0.5, q[1] + n[1] * t * 0.5)[1]
                              for t in range(-int(2 * rs.BENCH_CORE_M), int(2 * rs.BENCH_CORE_M) + 1)) if v is not None)
    prof = [R.at(q[0] + n[0] * sgn * u, q[1] + n[1] * sgn * u)[1]
            for u in [k * NAIP_STEP_M for k in range(int(NAIP_REACH_M / NAIP_STEP_M) + 1)]]
    if not core or any(v is None for v in prof):
        return None
    road = core[len(core) // 2]
    far = sorted(prof[len(prof) // 2:])
    ground = far[len(far) // 4] if road > far[len(far) // 2] else far[3 * len(far) // 4]
    if abs(road - ground) < NAIP_MIN_CONTRAST:
        return None
    half = (road + ground) / 2.0
    off = [(v < half) if road > ground else (v > half) for v in prof]
    for k in range(len(off) - NAIP_RUN + 1):
        if all(off[k:k + NAIP_RUN]):
            return max(0.0, k * NAIP_STEP_M - NAIP_STEP_M / 2.0)
    return None


def measure_ray(G, R, q, n, half_w):
    """[(edge_m, source) for the right (-) and left (+) sides] at q along normal n"""
    import road_seek as rs
    ts, hs = [], []
    t = -rs.BENCH_CORE_M
    while t <= rs.BENCH_CORE_M + 1e-9:
        v = G.at(q[0] + n[0] * t, q[1] + n[1] * t)
        if v is not None:
            ts.append(t); hs.append(v)
        t += RAY_STEP_M
    if len(ts) < 3:
        return None
    a, b, _r = rs._fit(ts, hs)
    out = []
    for sgn in (-1.0, 1.0):
        e, face, ran_on = bench_side(G, q, n, sgn, a, b)
        ne = naip_edge(R, q, n, sgn) if R is not None else None
        if face:
            out.append((e, "lidar face"))
        elif not ran_on:
            out.append((ne, "naip") if ne is not None and ne < e else (e, "lidar bench end"))
        elif ne is not None:
            out.append((ne, "naip"))
        else:
            out.append((half_w, "unmeasured: the line's half width"))
    return out


def measure(P, W, G, R, k0, k1, node):
    import numpy as np
    import draft_pads as dp
    n_ = len(P)

    def tan(i):
        a, b = P[max(i - 1, 0)], P[min(i + 1, n_ - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return tx / L, tz / L
    rays, lap = [], []
    for k in range(k0, k1 + 1):
        for f in ([j / SUB_RAYS for j in range(SUB_RAYS)] if k < k1 else [0.0]):
            t0, t1 = tan(k), tan(min(k + 1, n_ - 1))
            tx, tz = t0[0] * (1 - f) + t1[0] * f, t0[1] * (1 - f) + t1[1] * f
            L = math.hypot(tx, tz)
            nrm = (-tz / L, tx / L)
            kk = min(k + 1, n_ - 1)
            q = (P[k][0] + (P[kk][0] - P[k][0]) * f, P[k][2] + (P[kk][2] - P[k][2]) * f)
            m = measure_ray(G, R, q, nrm, W[k] / 2.0)
            if m is None:
                raise SystemExit(f"[bench-pad] FATAL: no lidar ground at the line at vertex {k} (+{f}): the turn's grid "
                                 f"does not cover the pad")
            if f == 0.0:
                lap.append((k, len(rays)))
            rays.append((q, nrm, m))
    # each side's edge read as the running median of EDGE_MEDIAN rays (one ray's 0.5 m bench step or a shrub's shadow in
    # NAIP is not the platform's shape)
    hm = EDGE_MEDIAN // 2
    med = []
    for j in range(len(rays)):
        win = rays[max(0, j - hm):j + hm + 1]
        med.append([(sorted(w[2][s][0] for w in win)[len(win) // 2], rays[j][2][s][1]) for s in (0, 1)])
    rays = [(q, nrm, m) for (q, nrm, _m), m in zip(rays, med)]
    lap = [{"k": k, "xz": [round(P[k][0], 4), round(P[k][2], 4)],
            "edge_m": [round(-rays[j][2][0][0], 2), round(rays[j][2][1][0], 2)],
            "source": [rays[j][2][0][1], rays[j][2][1][1]]} for k, j in lap]
    # the mask: every quad between consecutive rays, clipped to the kept sides of the two lap cuts
    cuts = [dp.lap_cut(P, k0, node), dp.lap_cut(P, k1, node)]
    ends = [(q[0] - nrm[0] * m[0][0], q[1] - nrm[1] * m[0][0], q[0] + nrm[0] * m[1][0], q[1] + nrm[1] * m[1][0])
            for q, nrm, m in rays]
    xs_all = [e[0] for e in ends] + [e[2] for e in ends]
    zs_all = [e[1] for e in ends] + [e[3] for e in ends]
    bx0, bx1 = min(xs_all) - 2.0, max(xs_all) + 2.0
    bz0, bz1 = min(zs_all) - 2.0, max(zs_all) + 2.0
    xs = np.arange(bx0, bx1, MASK_M) + MASK_M / 2
    ys = np.arange(bz0, bz1, MASK_M) + MASK_M / 2
    gx, gy = np.meshgrid(xs, ys)
    mask = np.zeros(gx.shape, dtype=bool)
    for (r0x, r0z, l0x, l0z), (r1x, r1z, l1x, l1z) in zip(ends, ends[1:]):
        for tri in (((r0x, r0z), (l0x, l0z), (l1x, l1z)), ((r0x, r0z), (l1x, l1z), (r1x, r1z))):
            mask |= dp.in_ring_grid(list(tri), gx, gy)
        for (ax, az, bxx, bzz) in ((r0x, r0z, l0x, l0z),):
            mask |= dp.segment_band((ax, az), (bxx, bzz), gx, gy, MASK_M * 0.75)
    mask |= dp.segment_band(ends[-1][:2], ends[-1][2:], gx, gy, MASK_M * 0.75)
    for c, e in zip(cuts, (ends[0], ends[-1])):   # only next to the cut's own ray: a hairpin's other leg lies behind
        mask &= dp.half_plane_mask(c, gx, gy) | ~dp.segment_band(e[:2], e[2:], gx, gy, 1.0)   # the in-cut's line
    from scipy import ndimage
    lab, nlab = ndimage.label(mask)
    if nlab > 1:                                   # the piece the line runs through
        qn = rays[len(rays) // 2][0]
        keep = lab[int((qn[1] - bz0) / MASK_M), int((qn[0] - bx0) / MASK_M)]
        mask = lab == keep
    mask = ndimage.binary_fill_holes(mask)
    ring = dp.trace_boundary(mask.tolist(), list(xs), list(ys))
    ring = dp.smooth_ring(ring, OUTLINE_SIGMA_M, keep_on=cuts, pin=cuts)
    ring = dp.resample_ring(ring, OUTLINE_STEP_M)
    ring = [dp.snap(p, cuts) for p in ring]
    if dp.ring_area(ring) < 0:
        ring.reverse()
    # the deck: plane fits to the lidar cell means on the graded surface (the mask), within DECK_R_M of each node
    dil = ndimage.binary_dilation(mask, iterations=int(round(DECK_EXTRA_M / MASK_M)))
    gi = np.arange(G.nx); gj = np.arange(G.nz)
    cx = G.x0 + (gi + 0.5) * G.c; cz = G.z0 + (gj + 0.5) * G.c
    CX, CZ = np.meshgrid(cx, cz)
    mi = np.clip(((CX - bx0) / MASK_M).astype(int), 0, mask.shape[1] - 1)
    mj = np.clip(((CZ - bz0) / MASK_M).astype(int), 0, mask.shape[0] - 1)
    inbox = (CX >= bx0) & (CX < bx1) & (CZ >= bz0) & (CZ < bz1)
    on = inbox & mask[mj, mi] & np.isfinite(G.g)
    px, pz, ph = CX[on], CZ[on], G.g[on]
    rx = [p[0] for p in ring]; rz = [p[1] for p in ring]
    e0, n0 = math.floor(min(rx)) - 1.0, math.floor(min(rz)) - 1.0
    nx = int(math.ceil((max(rx) + 1.0 - e0) / DECK_CELL_M)) + 1
    ny = int(math.ceil((max(rz) + 1.0 - n0) / DECK_CELL_M)) + 1
    deck = []
    for j in range(ny):
        row = []
        for i in range(nx):
            x, z = e0 + i * DECK_CELL_M, n0 + j * DECK_CELL_M
            mi_, mj_ = int((x - bx0) / MASK_M), int((z - bz0) / MASK_M)
            if not (0 <= mi_ < dil.shape[1] and 0 <= mj_ < dil.shape[0]) or not dil[mj_, mi_]:
                row.append(None)
                continue
            sel = (px - x) ** 2 + (pz - z) ** 2 <= DECK_R_M * DECK_R_M
            v = dp.plane_height([(float(a) - x, float(b) - z, float(h)) for a, b, h in zip(px[sel], pz[sel], ph[sel])])
            row.append(None if v is None else round(v, 3))
        deck.append(row)
    srcs = {}
    for r in rays:
        for e, s in r[2]:
            srcs[s] = srcs.get(s, 0) + 1
    return ring, {"e0": round(e0, 3), "n0": round(n0, 3), "cell_m": DECK_CELL_M, "nx": nx, "ny": ny, "y": deck}, lap, srcs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--line", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--cuts", type=int, nargs=2, required=True)
    ap.add_argument("--node", type=int, required=True)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args(argv)
    import numpy as np
    import road_seek as rs
    import draft_pads as dp
    port = Path(a.port)
    line = json.loads(Path(a.line).read_text(encoding="utf-8"))
    P = [tuple(p) for p in line["points_xyz_m"]]
    W = line["widths_m"]
    k0, k1 = a.cuts
    if not k0 < a.node < k1:
        raise SystemExit("[bench-pad] the node must lie strictly between the cuts")
    files = sorted((port / "data" / "lidar").glob("*.npz"))
    if not files:
        raise SystemExit(f"[bench-pad] {port}/data/lidar has no grid (tools/lidar_turns.py on the PC)")
    G = Lidar(files)
    R = None
    if a.cache:
        keys = rs.tiles_for(P[k0:k1 + 1], 40.0)
        tiles = {}
        for k in keys:
            f = Path(a.cache) / f"t_{k[0]}_{k[1]}.npz"
            if f.exists():
                d = np.load(f)
                tiles[k] = (d["dem"], d["img"])
        if len(tiles) != len(keys):
            raise SystemExit(f"[bench-pad] {len(keys) - len(tiles)} NAIP tile(s) missing from {a.cache} (tools/road_seek.py --cache)")
        R = rs.Raster(tiles)
    ring, deck, lap, srcs = measure(P, W, G, R, k0, k1, a.node)
    raw = json.loads(Path(a.raw).read_text(encoding="utf-8"))["points_xyz_m"]
    if len(raw) != len(P):
        raise SystemExit(f"[bench-pad] --raw has {len(raw)} points, --line {len(P)}")
    for x in lap:
        x["raw_xz"] = [round(raw[x["k"]][0], 4), round(raw[x["k"]][2], 4)]
    filled = sum(v is not None for r in deck["y"] for v in r)
    rec = {
        "id": a.id, "node": a.node, "cuts": [k0, k1], "sealed": [],
        "outline_en": [[round(p[0], 3), round(p[1], 3)] for p in ring],
        "outline_flags_paint": [],
        "deck": deck,
        "lap": lap,
        "source": {"kind": "lidar_grid", "files": G.files, "ept": G.ept, "ground_points": G.points,
                   "naip": "road_seek tiles (USGSNAIPImagery)" if R is not None else None,
                   "edges": srcs,
                   "method": "tools/bench_pad.py (road_seek's bench on lidar class-2 ground, the gravel's NAIP edge where no "
                             "face bounds it; class-2 plane deck)",
                   "params": {k: globals()[k] for k in ("SUB_RAYS", "NAIP_REACH_M", "NAIP_RUN", "NAIP_MIN_CONTRAST",
                                                        "MASK_M", "OUTLINE_SIGMA_M", "OUTLINE_STEP_M", "DECK_CELL_M",
                                                        "DECK_R_M")},
                   "measured_on": "the swept line (the assembler's data/centerline.local.json); raw_xz: the intake's line (centerline.raw.local.json) the intake checks"},
        "uncertainty_m": {"outline": UNC_M},
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = port / "source" / "pads" / f"{a.id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, separators=(",", ":")), encoding="utf-8")
    wl = [x["edge_m"][1] - x["edge_m"][0] for x in lap]
    print(f"[bench-pad] {a.id}: cuts v{k0} / v{k1}, node v{a.node}; outline {len(ring)} points, {dp.ring_area(ring):.0f} m2; "
          f"deck {deck['nx']} x {deck['ny']} @ {DECK_CELL_M} m ({filled} nodes with a height); platform "
          f"{min(wl):.1f}..{max(wl):.1f} m across; edges by {srcs} -> {out}")


if __name__ == "__main__":
    main()
