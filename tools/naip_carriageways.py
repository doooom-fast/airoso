"""Each freeway carriageway's paved edges, measured off NAIP (ledger 0080 phase 2a; Kevin 2026-11-05: "I just want
real" — the carriageway widths are measured, not lane counts x 3.66 m + shoulders).

The image is the measurement; the OSM centreline only says where to look. NAIP 2022 (USDA FSA, public domain, 0.6 m,
four bands: R, G, B, near infrared) is read from Microsoft's Planetary Computer data API (``.npy`` crops, cached), in
the draft's own local frame (scripts.geometry.projection: x = east, z = north, metres about network.local.json's
origin, the equirectangular projection the draft projected OSM with).

At every STEP_M of each carriageway's line, and on both sides, the image is read across the road every SAMPLE_M out
to SCAN_M. Each sample is classed:
  vegetation  NDVI = (NIR - R) / (NIR + R) >= VEG_NDVI
  pavement    NDVI < PAVE_NDVI, unsaturated (max(R, G, B) - min(R, G, B) <= PAVE_SAT) and not dark shadow
              (mean(R, G, B) >= PAVE_MIN)
  other       dirt, roofs, shadow, water
The PAVED EDGE on a side is where pavement stops: the first offset past which BREAK_M of consecutive samples are not
pavement. Read outward from the centreline, so a car or a lane line (both paved-adjacent) never ends the pavement.
Where the two carriageways' lines are close the scan from one runs into the other's pavement; the MEDIAN is then read
between the two lines: a run of non-pavement there of at least BREAK_M is an unpaved median (each carriageway's inner
edge is where its pavement stops), and none is a PAVED median: one paved width, whose barrier stands on the line
midway between the two pavements' centres unless the image shows its bright concrete top (BARRIER_* below).

Every number in UPPER CASE is [invented] tuning of a colour reader (fleet/GATES-CHANGELOG.md 2026-11-05, 2a); what the
image shows is the measurement, and the overview crops written beside the output are there to be checked by eye.

    python tools/naip_carriageways.py <draft-dir> <out-dir> [--cache DIR] [--items ID,ID] [--config track.config.json]

<draft-dir> holds network.local.json, centerline.local.json (the line) and connectors.local.json (the connectors).
Writes <out-dir>/carriageway_edges.naip.json: per carriageway per station [s, x, z, left edge, right edge, median,
barrier], offsets in metres from the line (left positive), plus the run statistics. numpy + Pillow; reads the network.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{w},{s},{e},{n}/{px}x{py}.npy"
ITEMS = [  # NAIP 2022 (0.6 m) over the I 8 corridor: the latest year the Planetary Computer holds for San Diego
    ("ca_m_3211715_sw_11_060_20220425", (-117.252299, 32.748082, -117.185247, 32.814447)),
    ("ca_m_3211715_se_11_060_20220425", (-117.189807, 32.748084, -117.122737, 32.814415)),
    ("ca_m_3211716_sw_11_060_20220425", (-117.12725, 32.748163, -117.06029, 32.814353)),
]
TILE_M = 600.0           # the crop's side (1,000 px at 0.6 m)
MPP = 0.6                # NAIP 2022's ground sample distance in California

STEP_M = 5.0             # [invented] station spacing along each line
SAMPLE_M = 0.3           # [invented] half the GSD: sample spacing across
SCAN_M = 30.0            # [invented] how far out from the line a side is read
VEG_NDVI = 0.12          # [invented]
PAVE_NDVI = 0.08         # [invented]
PAVE_SAT = 40            # [invented] 8-bit max - min of R, G, B
PAVE_MIN = 55            # [invented] 8-bit mean of R, G, B (darker = shadow, not pavement)
BREAK_M = 1.2            # [invented] two GSDs of not-pavement ends the pavement
BARRIER_MIN = 175        # [invented] 8-bit mean of R, G, B for a concrete barrier's sunlit top
BARRIER_BAND_M = 1.5     # [invented] how far from the median's midline the barrier's top is sought


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def _get(url, timeout=120, retries=4):
    from scripts.tls import https_context
    last = None
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout, context=https_context()) as r:
                return r.read()
        except Exception as e:  # a busy API: back off and retry, one request at a time
            last = e
            time.sleep(3 + 5 * k)
    raise RuntimeError(f"{url}: {last}")


class Mosaic:
    """NAIP crops in the local frame: tiles TILE_M on a side on a fixed grid, fetched on demand and cached."""

    def __init__(self, origin, cache: Path):
        self.lon0, self.lat0 = float(origin["lon"]), float(origin["lat"])
        self.mx, self.my = mpd(self.lat0)
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.tiles = {}
        self.fetched = []

    def _ll(self, x, z):
        return self.lon0 + x / self.mx, self.lat0 + z / self.my

    def _item(self, lon, lat):
        for it, (w, s, e, n) in ITEMS:
            if w + 0.002 <= lon <= e - 0.002 and s + 0.002 <= lat <= n - 0.002:
                return it
        return None

    def tile(self, i, j):
        if (i, j) in self.tiles:
            return self.tiles[(i, j)]
        x0, z0 = i * TILE_M, j * TILE_M
        W, S = self._ll(x0, z0)
        E, N = self._ll(x0 + TILE_M, z0 + TILE_M)
        item = self._item((W + E) / 2, (S + N) / 2)
        px = int(round(TILE_M / MPP))
        f = self.cache / f"naip_{i}_{j}.npy"
        if not f.exists():
            if item is None:
                self.tiles[(i, j)] = None
                return None
            q = urllib.parse.urlencode({"collection": "naip", "item": item, "assets": "image",
                                        "asset_bidx": "image|1,2,3,4", "nodata": 0})
            url = DATA.format(w=f"{W:.8f}", s=f"{S:.8f}", e=f"{E:.8f}", n=f"{N:.8f}", px=px, py=px) + "?" + q
            arr = np.load(io.BytesIO(_get(url)))
            np.save(f, arr[:4])
            self.fetched.append(f.name)
            print(f"[naip] tile {i},{j} {item}", flush=True)
        a = np.load(f)
        # a non-zero 4th band everywhere = the item covers the tile; edge tiles are masked by nodata 0
        self.tiles[(i, j)] = (a.astype(np.float32), item)
        return self.tiles[(i, j)]

    def sample(self, xs, zs):
        """(N, 4) R, G, B, NIR at local points (nearest pixel; NaN where no image)."""
        xs = np.asarray(xs, float)
        zs = np.asarray(zs, float)
        out = np.full((len(xs), 4), np.nan, np.float32)
        I = np.floor(xs / TILE_M).astype(int)
        J = np.floor(zs / TILE_M).astype(int)
        px = int(round(TILE_M / MPP))
        for key in set(zip(I.tolist(), J.tolist())):
            t = self.tile(*key)
            if t is None:
                continue
            a = t[0]
            m = (I == key[0]) & (J == key[1])
            c = np.clip(((xs[m] - key[0] * TILE_M) / MPP).astype(int), 0, px - 1)
            r = np.clip(((key[1] * TILE_M + TILE_M - zs[m]) / MPP).astype(int), 0, px - 1)
            v = a[:, r, c].T
            v[(v == 0).all(axis=1)] = np.nan
            out[m] = v
        return out


def classify(px):
    """0 other, 1 pavement, 2 vegetation, -1 no image."""
    r, g, b, n = px[:, 0], px[:, 1], px[:, 2], px[:, 3]
    ndvi = (n - r) / np.maximum(1.0, n + r)
    rgb = px[:, :3]
    sat = rgb.max(axis=1) - rgb.min(axis=1)
    mean = rgb.mean(axis=1)
    cls = np.zeros(len(px), np.int8)
    cls[(ndvi < PAVE_NDVI) & (sat <= PAVE_SAT) & (mean >= PAVE_MIN)] = 1
    cls[ndvi >= VEG_NDVI] = 2
    cls[np.isnan(r)] = -1
    return cls, mean


def frames(pts):
    """Per point: station, unit tangent, unit LEFT normal (x east, z north: left of travel = (-tz, tx))."""
    P = np.asarray([[p[0], p[2]] for p in pts], float)
    d = np.gradient(P, axis=0)
    t = d / np.maximum(1e-9, np.linalg.norm(d, axis=1))[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    return P, s, t, nrm


def resample(P, s, nrm, step):
    S = np.arange(0.0, s[-1] + 1e-6, step)
    X = np.interp(S, s, P[:, 0])
    Z = np.interp(S, s, P[:, 1])
    nx = np.interp(S, s, nrm[:, 0])
    nz = np.interp(S, s, nrm[:, 1])
    L = np.maximum(1e-9, np.hypot(nx, nz))
    return S, np.stack([X, Z], 1), np.stack([nx / L, nz / L], 1)


def edge_out(cls, offs, start_k):
    """From index start_k (the line) outward: the last pavement offset before BREAK_M of not-pavement."""
    nb = int(round(BREAK_M / SAMPLE_M))
    last = None
    run = 0
    for k in range(start_k, len(cls)):
        if cls[k] == 1:
            last = offs[k]
            run = 0
        elif cls[k] == -1:
            return None
        else:
            run += 1
            if run >= nb and last is not None:
                return last
            if run >= nb and last is None:
                return None
    return None                      # paved all the way out: not an edge (another road, a lot)


PAIR_M = 45.0            # [invented] two carriageways within this of each other are read as one section
REACH_M = 60.0           # [invented] the scan's reach either side when a partner is near
OUT_LO_M = 3.0           # [invented] a read edge is kept only within the draft's half-width - OUT_LO_M ..
OUT_HI_M = 6.0           # [invented]  .. + OUT_HI_M (wider = another pavement: a ramp, a lot; narrower = a car's shadow)
BARRIER_DELTA = 25       # [invented] the barrier's top reads this much brighter than the pavement around it
SMOOTH_N = 7             # [invented] running median over 7 stations (35 m) of every edge offset
FILL_M = 60.0            # [invented] an unread run up to this long is interpolated between its read ends
MIN_BARRIER_M = 20.0     # [invented] a median barrier run shorter than this is not built (a gap in the reading)
# Caltrans Concrete Barrier Type 60 (Standard Plans A76A; the 1999 edition's "Type 60", the 2026 edition's sheet A76A
# "Type 60M"): 36 in (0.914 m) high, a single slope 9.1 deg from vertical (Caltrans Roadside Safety Research Group,
# "Type 60 median barrier MASH 2016"), 610 mm wide at the base (the Type 60 family's, FHWA / Caltrans); the top is what
# the slope leaves: 0.610 - 2 x 0.914 x tan(9.1 deg) = 0.317 m. The sheet's own drawing was not read (its DGN is
# compressed): owed, ledger 0080.
BARRIER_H_M = 0.914
BARRIER_BASE_M = 0.610
BARRIER_TOP_M = round(BARRIER_BASE_M - 2 * BARRIER_H_M * math.tan(math.radians(9.1)), 3)
BARRIER_CLEAR_M = 0.3    # [invented] each carriageway's inner edge stands this far off the barrier's foot: the assembler's
#                          line smoothing moves a swept edge by up to ~0.15 m (ws10: pavement began 0.16 m from the
#                          barrier's centre at p5), and the edge strip (0.1 m at road level + the 0.3 m grade strip)
#                          then runs to under the barrier, so neither pavement is ever under the barrier's body


def _outward(cls, mean, offs, k0, sg):
    if sg > 0:
        return cls[k0:], mean[k0:], offs[k0:] - offs[k0]
    return cls[k0::-1], mean[k0::-1], offs[k0] - offs[k0::-1]


def _nearest(PP, q):
    d = np.hypot(PP[:, 0] - q[0], PP[:, 1] - q[1])
    j = int(np.argmin(d))
    return j, float(d[j])


def read_sections(mosaic, cw: dict):
    """cw: {name: (points, widths, partner name or None)}. Per carriageway per station: the two sides' readings."""
    offs = np.arange(-REACH_M, REACH_M + 1e-6, SAMPLE_M)
    k0 = int(np.argmin(np.abs(offs)))
    lines = {}
    for name, (pts, widths, _p) in cw.items():
        P, s, _t, N = frames(pts)
        S, Q, Nn = resample(P, s, N, STEP_M)
        lines[name] = {"P": P, "s": s, "N": N, "S": S, "Q": Q, "Nn": Nn, "W": np.interp(S, s, np.asarray(widths, float))}
    out = {}
    for name, (_pts, _w, partner) in cw.items():
        L = lines[name]
        PP = lines[partner]["Q"] if partner else None
        rows = []
        for i in range(len(L["S"])):
            q, n = L["Q"][i], L["Nn"][i]
            cls, mean = classify(mosaic.sample(q[0] + offs * n[0], q[1] + offs * n[1]))
            d = None
            if PP is not None:
                j, dist = _nearest(PP, q)
                if dist < PAIR_M:
                    d = float(np.dot(PP[j] - q, n))
            half = float(L["W"][i]) / 2.0
            side = {}
            for sg in (1, -1):
                c, m, o = _outward(cls, mean, offs, k0, sg)
                if d is not None and np.sign(d) == sg and abs(d) > 1.0:
                    D = abs(d)
                    kd = int(np.argmin(np.abs(o - D)))
                    e1 = edge_out(c, o, 0)
                    e2 = edge_out(c[kd::-1], D - o[kd::-1], 0)
                    if e1 is not None and e2 is not None and e1 < D - e2 and half - OUT_LO_M <= e1 <= half + OUT_HI_M:
                        side[sg] = ["unpaved median", round(e1, 2), None]
                        continue
                    if e1 is not None and e2 is not None and e1 < D - e2:
                        side[sg] = ["unread", None, None]
                        continue
                    band = np.abs(o - D / 2.0) <= BARRIER_BAND_M
                    pave = (c[:kd + 1] == 1)
                    base = float(np.median(m[:kd + 1][pave])) if pave.any() else float("nan")
                    kb = int(np.argmax(np.where(band, m, -1)))
                    seen = bool(m[kb] >= base + BARRIER_DELTA)
                    bar = float(o[kb]) if seen else D / 2.0
                    side[sg] = ["barrier seen" if seen else "barrier at the midline",
                                round(bar - BARRIER_BASE_M / 2.0 - BARRIER_CLEAR_M, 2),
                                round(bar, 2)]
                else:
                    e = edge_out(c, o, 0)
                    if e is None or not (half - OUT_LO_M <= e <= half + OUT_HI_M):
                        side[sg] = ["unread", None, None]
                    else:
                        side[sg] = ["read", round(e, 2), None]
            rows.append([round(float(L["S"][i]), 1), round(float(q[0]), 2), round(float(q[1]), 2),
                         None if d is None else round(d, 2), side[1], side[-1]])
        out[name] = rows
    return out, lines


def _runmed(v, n):
    v = np.asarray(v, float)
    out = v.copy()
    h = n // 2
    for i in range(len(v)):
        w = v[max(0, i - h):i + h + 1]
        w = w[~np.isnan(w)]
        out[i] = np.median(w) if len(w) and not np.isnan(v[i]) else np.nan
    return out


def _fill(S, v, default):
    v = np.asarray(v, float).copy()
    ok = ~np.isnan(v)
    nfill = ndef = 0
    i = 0
    while i < len(v):
        if ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(v) and not ok[j + 1]:
            j += 1
        a, b = i - 1, j + 1
        if a >= 0 and b < len(v) and S[b] - S[a] <= FILL_M:
            v[i:j + 1] = np.interp(S[i:j + 1], [S[a], S[b]], [v[a], v[b]])
            nfill += j - i + 1
        else:
            v[i:j + 1] = default[i:j + 1]
            ndef += j - i + 1
        i = j + 1
    return v, nfill, ndef


def edges_of(rows, W):
    """Per station: smoothed left / right offsets (left positive, right as a distance) and how each was got."""
    S = np.array([r[0] for r in rows])
    out = {}
    stats = {}
    for k, sg in ((4, 1), (5, -1)):
        raw = np.array([np.nan if r[k][1] is None else r[k][1] for r in rows])
        sm = _runmed(raw, SMOOTH_N)
        v, nfill, ndef = _fill(S, sm, W / 2.0)
        out[sg] = v
        kinds = {}
        for r in rows:
            kinds[r[k][0]] = kinds.get(r[k][0], 0) + 1
        stats["left" if sg > 0 else "right"] = {"kinds": kinds, "interpolated": nfill, "draft_half_width": ndef}
    return S, out, stats


def barrier_runs(rows, line):
    """The median barrier's centre line (x, z) from the line's own readings, as runs of consecutive stations."""
    pts = []
    for i, r in enumerate(rows):
        for k, sg in ((4, 1), (5, -1)):
            if r[k][0].startswith("barrier"):
                pts.append((i, sg, r[k][2]))
    runs, cur = [], []
    for i, sg, b in pts:
        if cur and (i != cur[-1][0] + 1 or sg != cur[-1][1]):
            runs.append(cur)
            cur = []
        cur.append((i, sg, b))
    if cur:
        runs.append(cur)
    out = []
    for run in runs:
        idx = [i for i, _sg, _b in run]
        if line["S"][idx[-1]] - line["S"][idx[0]] < MIN_BARRIER_M:
            continue
        sg = run[0][1]
        bo = _runmed([b for _i, _sg, b in run], SMOOTH_N)
        xz = [[round(float(line["Q"][i][0] + sg * b * line["Nn"][i][0]), 3),
               round(float(line["Q"][i][1] + sg * b * line["Nn"][i][1]), 3)] for i, b in zip(idx, bo)]
        out.append({"stations_m": [float(line["S"][idx[0]]), float(line["S"][idx[-1]])], "side": sg, "xz": xz})
    return out


def _signed_to(xz, q, n):
    """The barrier's nearest point to station q, as a signed offset along the normal n, and its distance along."""
    A = np.asarray(xz, float)
    j, _dist = _nearest(A, q)
    v = A[j] - q
    return float(np.dot(v, n)), abs(float(v[0] * n[1] - v[1] * n[0]))


def _limit(v, st, pin, rate):
    """Each edge offset changes at most ``rate`` m per m along the line (the port's width_taper rate, ledger 0078
    round 5): a step WIDENS its narrow side (pavement is never cut to make a flare), except that a vertex on the
    barrier never passes it (pin = the barrier face there) and its neighbours close on it at the same rate."""
    v = np.asarray(v, float).copy()
    for _ in range(2):
        for i in range(1, len(v)):                       # forward: widen behind a step up
            v[i] = max(v[i], v[i - 1] - rate * (st[i] - st[i - 1]))
        for i in range(len(v) - 2, -1, -1):              # backward
            v[i] = max(v[i], v[i + 1] - rate * (st[i + 1] - st[i]))
        cap = np.where(np.isnan(pin), np.inf, pin)
        for i in range(1, len(v)):
            cap[i] = min(cap[i], cap[i - 1] + rate * (st[i] - st[i - 1]))
        for i in range(len(v) - 2, -1, -1):
            cap[i] = min(cap[i], cap[i + 1] + rate * (st[i + 1] - st[i]))
        v = np.minimum(v, cap)
    return v


RATE_M_PER_M = 0.1       # reused: lm_intake.width_taper (ledger 0078 round 5, Milford's rate), per edge here
SMOOTH_V = 9             # [invented] running median over 9 vertices (~45 m) of each per-vertex edge offset


def apply(pts, widths, S, edges, line, barriers, own_rows):
    """Shift each vertex to the measured pavement's centre and give it the measured width; a carriageway beside a
    barrier run takes its inner edge from that run (the same barrier for both carriageways)."""
    P, s, N = line["P"], line["s"], line["N"]
    Lw = np.interp(s, S, edges[1])
    Rw = np.interp(s, S, edges[-1])
    pinL = np.full(len(pts), np.nan)
    pinR = np.full(len(pts), np.nan)
    for i in range(len(pts)):
        for br in barriers:
            off, along = _signed_to(br["xz"], P[i], N[i])
            if along <= STEP_M and abs(off) < PAIR_M / 2:
                inner = abs(off) - BARRIER_BASE_M / 2.0 - BARRIER_CLEAR_M
                if off > 0:
                    pinL[i] = inner
                else:
                    pinR[i] = inner
                break
    Lw = np.where(np.isnan(pinL), Lw, pinL)
    Rw = np.where(np.isnan(pinR), Rw, pinR)
    Lw = _limit(_runmed(Lw, SMOOTH_V), s, _runmed(pinL, 3), RATE_M_PER_M)
    Rw = _limit(_runmed(Rw, SMOOTH_V), s, _runmed(pinR, 3), RATE_M_PER_M)
    n_bar = int((~np.isnan(pinL)).sum() + (~np.isnan(pinR)).sum())
    c = (Lw - Rw) / 2.0
    new = []
    for i, p in enumerate(pts):
        new.append([round(float(p[0] + c[i] * N[i][0]), 3), p[1], round(float(p[2] + c[i] * N[i][1]), 3)])
    w = [round(float(a + b), 3) for a, b in zip(Lw, Rw)]
    return new, w, n_bar, c


# ledger 0080 2a round 3: the assembler (scripts-v021 build_loop_blend) smooths every line horizontally before it sweeps
# it (the line: route.smooth_sigma_pts / smooth_passes; a connector: sigma 1.5, 1 pass, hard-coded there), so a measured
# edge pinned BARRIER_CLEAR_M off the barrier's foot can still be swept onto it (ws12: audit D 128, the line moved up to
# 0.26 m toward the barrier at line s 5,891, 6,359, 6,549, 6,754, 10,289, 10,349; WB's edge on a barrier run's first,
# ragged reading at WB s 4,045). The clamp below predicts that sweep with the assembler's own function and narrows a
# vertex (both edges, about the smoothed centre) until its swept inner edge, and the chord to each neighbour, stand
# BARRIER_CLEAR_M off every barrier run's foot; neighbours close on it at the width_taper rate (both sides) so the
# intake's taper does not widen it back.
ASM_SMOOTH = ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py"
CONN_SMOOTH = (1.5, 1)   # build_loop_blend's connector smoothing (sigma_pts, passes), hard-coded there


def _asm_smooth(pts, sigma, passes):
    import importlib.util
    spec = importlib.util.spec_from_file_location("v021_smooth", ASM_SMOOTH)
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    return [tuple(q) for q in sm.smooth_centerline([tuple(q) for q in pts], sigma_pts=sigma, passes=passes)]


def clear_of_barrier(pts, widths, barriers, sigma, passes):
    """Narrow ``widths`` where the swept (smoothed) ribbon's edge would stand within BARRIER_BASE_M / 2 +
    BARRIER_CLEAR_M of a barrier run. Returns (widths, vertices narrowed, the largest cut)."""
    sp = np.asarray([(q[0], q[2]) for q in _asm_smooth(pts, sigma, passes)], float)
    w = np.asarray(widths, float).copy()
    need = BARRIER_BASE_M / 2.0 + BARRIER_CLEAR_M
    segs = np.asarray([(a[0], a[1], b[0], b[1]) for br in barriers for a, b in zip(br["xz"], br["xz"][1:])], float)
    if not len(segs):
        return w, 0, 0.0
    n = len(sp)
    t = np.zeros((n, 2))
    t[1:-1] = sp[2:] - sp[:-2]
    t[0], t[-1] = sp[1] - sp[0], sp[-1] - sp[-2]
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)

    def dist(q):
        ax, az, bx, bz = segs.T
        dx, dz = bx - ax, bz - az
        L2 = np.maximum(dx * dx + dz * dz, 1e-12)
        u = np.clip(((q[0] - ax) * dx + (q[1] - az) * dz) / L2, 0.0, 1.0)
        return float(np.min(np.hypot(q[0] - ax - u * dx, q[1] - az - u * dz)))

    cap = np.full(n, np.inf)
    for i in range(n):
        for sg in (1.0, -1.0):
            hw = w[i] / 2.0
            # the edge at this vertex and the chords' midpoints to its neighbours, cut back 0.05 m at a time
            while hw > 0.5:
                pts_e = [sp[i] + sg * hw * nrm[i]]
                for j in (i - 1, i + 1):
                    if 0 <= j < n:
                        pts_e.append(0.5 * (sp[i] + sg * hw * nrm[i] + sp[j] + sg * (w[j] / 2.0) * nrm[j]))
                if min(dist(q) for q in pts_e) >= need:
                    break
                hw -= 0.05
            if hw < w[i] / 2.0:
                cap[i] = min(cap[i], 2.0 * hw)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(sp, axis=0).T))])
    for i in range(1, n):
        cap[i] = min(cap[i], cap[i - 1] + 2 * RATE_M_PER_M * (s[i] - s[i - 1]))
    for i in range(n - 2, -1, -1):
        cap[i] = min(cap[i], cap[i + 1] + 2 * RATE_M_PER_M * (s[i + 1] - s[i]))
    new = np.minimum(w, cap)
    cut = w - new
    return new, int((cut > 1e-6).sum()), float(cut.max()) if len(cut) else 0.0


def overlap_report(line, partners):
    """At each line vertex beside a partner: the gap between the two pavements, measured along the line's normal
    (negative = they overlap: what 2a's red audit was made of)."""
    lp = line["points_xyz_m"]
    P, s, _t, N = frames(lp)
    gaps = []
    for c in partners:
        Q, _s2, _t2, N2 = frames(c["points_xyz_m"])
        W2 = np.asarray(c["widths_m"], float)
        for i in range(len(P)):
            j, dist = _nearest(Q, P[i])
            if dist >= PAIR_M:
                continue
            d = float(np.dot(Q[j] - P[i], N[i]))
            gap = abs(d) - line["widths_m"][i] / 2.0 - W2[j] / 2.0
            gaps.append((round(float(s[i]), 1), round(gap, 2)))
    neg = [g for g in gaps if g[1] < -0.05]
    return {"paired_stations": len(gaps), "overlap_stations": len(neg),
            "worst_m": min((g[1] for g in gaps), default=None),
            "overlaps_s_gap": neg[:40]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    draft, out = Path(argv[0]), Path(argv[1])
    cache = Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else out / "naip_cache"
    nloc = json.loads((draft / "network.local.json").read_text(encoding="utf-8"))
    mos = Mosaic(nloc["origin"], cache)
    line_p = draft / "centerline.local.json"
    conn_p = draft / "connectors.local.json"
    line = json.loads(line_p.read_text(encoding="utf-8"))
    conns = json.loads(conn_p.read_text(encoding="utf-8"))
    cw = {"line": (line["points_xyz_m"], line["widths_m"], None)}
    for c in conns["connectors"]:
        if c.get("network"):
            cw[c["name"]] = (c["points_xyz_m"], c["widths_m"], "line")
    first = [k for k in cw if k != "line"]
    if first:
        cw["line"] = (line["points_xyz_m"], line["widths_m"], first[0])
    rows, lines = read_sections(mos, cw)
    # the line's horizontal smoothing in the assembler (route.smooth_sigma_pts / smooth_passes; v021's defaults 2.0 / 2)
    route = {}
    if "--config" in argv:
        route = json.loads(Path(argv[argv.index("--config") + 1]).read_text(encoding="utf-8")).get("route") or {}
    line_smooth = (float(route.get("smooth_sigma_pts", 2.0)), int(route.get("smooth_passes", 2)))
    barriers = barrier_runs(rows["line"], lines["line"]) if first else []
    rep = {"tool": "tools/naip_carriageways.py", "ledger": "0080 phase 2a",
           "imagery": "USDA FSA NAIP 2022 (0.6 m, R G B NIR), Microsoft Planetary Computer: " + ", ".join(i for i, _b in ITEMS),
           "params": {k: globals()[k] for k in ("STEP_M", "SAMPLE_M", "SCAN_M", "VEG_NDVI", "PAVE_NDVI", "PAVE_SAT",
                                                   "PAVE_MIN", "BREAK_M", "BARRIER_DELTA", "BARRIER_BAND_M", "PAIR_M",
                                                   "REACH_M", "OUT_LO_M", "OUT_HI_M", "SMOOTH_N", "FILL_M",
                                                   "MIN_BARRIER_M", "BARRIER_CLEAR_M", "SMOOTH_V")},
           "_invented": "every params value: tuning of a colour reader (fleet/GATES-CHANGELOG.md 2026-11-05, 2a)",
           "barrier": {"type": "Caltrans Concrete Barrier Type 60 (Standard Plans A76A)", "height_m": BARRIER_H_M,
                       "base_m": BARRIER_BASE_M, "top_m": BARRIER_TOP_M, "face_deg_from_vertical": 9.1},
           "carriageways": {}, "barrier_runs": barriers}
    new_line = dict(line)
    new_conns = {"connectors": []}
    for name, (pts, widths, _p) in cw.items():
        S, edges, stats = edges_of(rows[name], lines[name]["W"])
        npts, nw, nbar, c = apply(pts, widths, S, edges, lines[name], barriers if name != "line" or True else [], rows[name])
        sig, pas = line_smooth if name == "line" else CONN_SMOOTH
        nw_c, n_cut, max_cut = clear_of_barrier(npts, nw, barriers, sig, pas)
        nw = [round(float(x), 3) for x in nw_c]
        if n_cut:
            print(f"[naip_carriageways] {name}: {n_cut} vertices narrowed (max {max_cut:.2f} m) so the swept edge stands "
                  f"{BARRIER_CLEAR_M} m off the barrier's foot (the assembler's smoothing, sigma {sig}, {pas} pass(es))")
        dw = np.asarray(nw) - np.asarray(widths, float)
        rep["carriageways"][name] = {**stats, "stations": len(S), "vertices_on_a_barrier": nbar,
                                     "narrowed_clear_of_barrier": {"vertices": n_cut, "max_m": round(max_cut, 3),
                                                                   "smoothing": [sig, pas]},
                                     "shift_m_p5_p50_p95": [round(float(np.percentile(c, q)), 2) for q in (5, 50, 95)],
                                     "width_minus_draft_m_p5_p50_p95": [round(float(np.percentile(dw, q)), 2) for q in (5, 50, 95)],
                                     "width_m_min_max": [round(min(nw), 2), round(max(nw), 2)],
                                     "rows": rows[name]}
        if name == "line":
            new_line["points_xyz_m"] = npts
            new_line["widths_m"] = nw
            new_line["_measured"] = "tools/naip_carriageways.py (ledger 0080 2a): moved to the NAIP pavement's centre, NAIP widths"
        else:
            rec = next(dict(c) for c in conns["connectors"] if c["name"] == name)
            rec["points_xyz_m"], rec["widths_m"] = npts, nw
            from tools.network_connectors import one_way_paint
            rec["paint"] = one_way_paint(nw)
            new_conns["connectors"].append(rec)
        print(f"[naip_carriageways] {name}: {len(S)} stations; left {stats['left']['kinds']}, right {stats['right']['kinds']}; "
              f"width - draft p50 {rep['carriageways'][name]['width_minus_draft_m_p5_p50_p95'][1]} m; {nbar} vertices on a barrier")
    for c in conns["connectors"]:
        if not c.get("network"):
            new_conns["connectors"].append(c)
    # the check the measurement is for: the line's left pavement edge vs each partner's nearest pavement edge
    if new_conns["connectors"] and first:
        rep["overlap"] = overlap_report(new_line, [c for c in new_conns["connectors"] if c.get("network")])
        print(f"[naip_carriageways] carriageways overlapping: {rep['overlap']['overlap_stations']} of "
              f"{rep['overlap']['paired_stations']} paired stations (worst {rep['overlap']['worst_m']} m)")
    print(f"[naip_carriageways] median barrier: {len(barriers)} run(s), "
          f"{sum(b['stations_m'][1] - b['stations_m'][0] for b in barriers):.0f} m")
    out.mkdir(parents=True, exist_ok=True)
    (out / "centerline.measured.local.json").write_text(json.dumps(new_line), encoding="utf-8")
    (out / "connectors.measured.local.json").write_text(json.dumps(new_conns), encoding="utf-8")
    (out / "median_barrier.json").write_text(json.dumps({"barrier": rep["barrier"], "runs": barriers}), encoding="utf-8")
    rep["inputs"] = {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in (line_p, conn_p)}
    rep["outputs"] = {f: hashlib.md5((out / f).read_bytes()).hexdigest()
                      for f in ("centerline.measured.local.json", "connectors.measured.local.json", "median_barrier.json")}
    rep["tiles"] = sorted(p.name for p in cache.glob("naip_*.npy"))
    (out / "carriageway_edges.naip.json").write_text(json.dumps(rep), encoding="utf-8")


if __name__ == "__main__":
    main()
