"""Write AC ``fast_lane.ai`` (v7) offline from the engine's racing line — R2's keystone.

No k10 track ships an AI line, so nothing can drive them but a human, so no automated in-game
test exists (REALISM.md §7). This retires that: the engine already holds the line in world metres
(``data/finished_centerline.json``: ``points_xyz_m`` + ``widths_m``, the BUILT swept line), and
the .ai binary is documented (fleet/reference/RESEARCH.md §B6, verified against gro-ove/actools
AcTools/AiFile):

    header  : 4×i32   version=7, pointCount, lapTime_ms, sampleCount
    points  : N×20 B  position 3×f32, cumulative length f32, id i32
    extras  : i32 N, then N×18×f32: speed, gas, brake, obsoleteLatG, radius, sideLeft, sideRight,
              camber, direction, normal xyz, length, forwardVector xyz, tag, grade
    trailer : i32 hasGrid (0 — AC/ksEditor rebuilds derived data; see the re-save caveat in B6)

Measured floor (fleet/reference/MEASURED.md §2): every reference ships ~1.5 m point spacing; the
freeroam/traffic trick is ``pit_lane.ai`` = copy of ``fast_lane.ai`` (how point-to-point roads get
working AI). Speed profile is physics-derived from curvature (lat-g cap + braking/accel passes) —
a hypothesis generator: whether the AI actually laps is decided in game, by the harness (rule 0).

    python -m scripts.ac.write_ai_line <project-dir>                    # -> <project>/ai/
    python -m scripts.ac.write_ai_line <project-dir> --layout race_cw   # -> <project>/ai/race_cw/
    python -m scripts.ac.write_ai_line <project-dir> --install <AC-track-dir>
    python -m scripts.ac.write_ai_line <centerline.json> --out <dir> --spacing 1.5

STATUS — READ THIS BEFORE TRUSTING A FILE THIS WRITES (docs/HANDOFF.md:250-255, :284; V3-PLAN:297).
HANDOFF bans *generating AI splines from GPS data* and says to record them in-game. Every line this
module writes is a GENERATED DRAFT from the BUILT centreline (the mesh-frame line the ribbon was
swept along — not lat/lon), with exactly the provenance of the line every V3 install ships today.
It sits under OPEN ledger 0023 (a generated line launches but has never been proven to lap). It
exists so a layout is testable on first load (CSP auto-drive, Race mode reachable). The end state
per HANDOFF is one in-game recording per layout — CSP's recorder writes ``fast_lane.ai.candidate``
into the SELECTED layout's ``<id>/ai/`` — replacing the draft file-for-file. No DoD tier is claimed
on a draft; every draft dir carries an ``ai_draft.json`` saying so.

FRAMES (measured 2026-10-10 on the SD workshop, see ``_to_engine_frame``): the loop prep writes
``finished_centerline.json`` in the KN5 frame (z = −engine z; v0 at z=+1662 while
``centerline.local.json`` has −1662), the July writer's input was the ENGINE frame, and this writer
flips z exactly once at the end. Reading a kn5-frame line and flipping it would ship the ghost
mirror route of ledger 0023, so the input is normalised to the ENGINE frame (x=E, y=up, z=N) first
by comparing it against ``centerline.local.json``; every lane offset and side distance is computed
there (right of travel = (tz, −tx)), then the whole line is mirrored to the kn5 frame once.

LAYOUTS (ledger 0047, three versions of Lake Murray): ``--layout <id>`` takes the direction and the
race-furniture flag from ``track.config.json`` ``layouts[]``, writes ``<project>/ai/<id>/``, and —
with ``--lane-offset auto`` (default) — moves the line into the right-hand carriageway wherever a
divider is declared: a median island (``data/median_bands.json`` ``island_w_by_vertex``) in every
layout, plus the centre barrier chain and the kerb-line barrier inset (``data/barrier_bands.json``
``centre_w_by_vertex`` / ``edge_inset_by_vertex``, written by tools/barrier_bands.py) only for
layouts that load the race kn5 (``race_furniture: true``). Off = the centre of the lane between the
divider face + 0.4 m and the outer barrier face − 0.4 m (17 m road beside the 0.67 m chain with
0.82 m inset: (0.735 + 7.28) / 2 = 4.0 m); 0 where no divider stands (Alvarado: the whole street in
both directions). sideLeft/sideRight become the asymmetric distances to the nearer boundary minus
the margin. A reverse layout is the reversed traversal with its OWN right-of-travel offset — a
distinct file, never a byte-reversed one (every reference's reverse line is a distinct file).
A write-time self-check refuses any line point within 0.6 m of a declared barrier face or on an
island, measured against the per-vertex declaration (not the resampled channels).

L13 applies: a closed lap repeats its first vertex — detect, drop the duplicate, and wrap every
neighbour/distance computation; an open stage wraps nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
from pathlib import Path

G = 9.81
DIVIDER_MARGIN_M = 0.4      # the lane starts this far off a divider face (drive_test's lane margin)
EDGE_MARGIN_M = 0.4         # ... and ends this far off the kerb-line barrier face
LINE_MIN_CLEAR_M = 1.0      # the line itself is never authored closer than this to either face
CHECK_CLEAR_M = 0.6         # write-time self-check: refuse a point closer than this to a face
SMOOTH_HALF_WIN = 6         # lane-offset smoothing window (points at ~1.5 m = ±9 m)
RACE_PREFIXES_DOC = "1WALL_RACE / 1KERB_RACE (the race-furniture kn5 the race layouts load)"


# --- resampling ----------------------------------------------------------------

def _resample(pts: list[list[float]], widths: list[float], spacing: float, closed: bool,
              extra: list[list[float]] | None = None):
    """Linear resample of the polyline (+widths, + any per-vertex channels) to ~spacing metres.

    Returns (pts, widths, ds) — or (pts, widths, ds, extras) when ``extra`` channels are given.
    Every channel is index-aligned with ``pts``. Widths interpolate linearly; the ``extra``
    channels are DECLARATIONS (divider half-width, barrier inset) and take the larger of the two
    bracketing vertices, so a station between an open vertex and a divider vertex is already
    judged as the divider's — the same nearest-vertex reading the write-time check applies."""
    n = len(pts)
    seg = []
    total = 0.0
    m = n if not closed else n  # closed input arrives WITHOUT the duplicate vertex
    for i in range(m - (0 if closed else 1)):
        a, b = pts[i], pts[(i + 1) % n]
        d = math.dist(a, b)
        seg.append(d)
        total += d
    count = max(8, round(total / spacing))
    step = total / count
    chans = [widths] + list(extra or [])
    out_p = []
    out_c: list[list[float]] = [[] for _ in chans]
    i, acc = 0, 0.0
    tgt = 0.0
    steps = count if closed else count + 1
    for _ in range(steps):
        while i < len(seg) and acc + seg[i] < tgt - 1e-9:
            acc += seg[i]; i += 1
        if i >= len(seg):
            out_p.append(list(pts[-1] if not closed else pts[0]))
            for c, ch in enumerate(chans):
                out_c[c].append(ch[-1] if not closed else ch[0])
        else:
            t = (tgt - acc) / seg[i] if seg[i] > 1e-12 else 0.0
            a, b = pts[i], pts[(i + 1) % n]
            out_p.append([a[k] + (b[k] - a[k]) * t for k in range(3)])
            for c, ch in enumerate(chans):
                ca, cb = ch[i], ch[(i + 1) % n]
                out_c[c].append(ca + (cb - ca) * t if c == 0 else max(ca, cb))
        tgt += step
    if extra is None:
        return out_p, out_c[0], step
    return out_p, out_c[0], step, out_c[1:]


def _circumradius(a, b, c) -> float:
    """Radius through three XZ points (planar — banking/grade handled separately)."""
    ax, az, bx, bz, cx, cz = a[0], a[2], b[0], b[2], c[0], c[2]
    d = 2.0 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz))
    if abs(d) < 1e-9:
        return 10000.0
    ux = ((ax * ax + az * az) * (bz - cz) + (bx * bx + bz * bz) * (cz - az)
          + (cx * cx + cz * cz) * (az - bz)) / d
    uz = ((ax * ax + az * az) * (cx - bx) + (bx * bx + bz * bz) * (ax - cx)
          + (cx * cx + cz * cz) * (bx - ax)) / d
    return min(10000.0, math.hypot(ax - ux, az - uz))


# --- lane policy -----------------------------------------------------------------

def lane_offsets(widths: list[float], dh: list[float], inset: list[float]) -> list[float]:
    """Right-of-travel offset of the line at each station, from the declared divider half-width
    ``dh`` (island half or centre-chain half, 0 = none) and the kerb-line barrier ``inset``.

    With a divider the line runs down the centre of the right-hand lane — between the divider face
    + DIVIDER_MARGIN and the outer face − EDGE_MARGIN — and is never authored closer than
    LINE_MIN_CLEAR_M to either face (a lane too narrow for both clearances gets its midpoint).
    Without one the line stays on the centreline (0): a 13 m street is driven whole both ways."""
    out = []
    for w, d, s in zip(widths, dh, inset):
        if d <= 0.0:
            out.append(0.0)
            continue
        face_in, face_out = d, w / 2.0 - s
        o = ((face_in + DIVIDER_MARGIN_M) + (face_out - EDGE_MARGIN_M)) / 2.0
        lo, hi = face_in + LINE_MIN_CLEAR_M, face_out - LINE_MIN_CLEAR_M
        o = (face_in + face_out) / 2.0 if lo > hi else min(max(o, lo), hi)
        out.append(o)
    return out


def _smooth(vals: list[float], half: int, closed: bool) -> list[float]:
    n = len(vals)
    if n == 0 or half <= 0:
        return list(vals)
    out = []
    for i in range(n):
        acc = cnt = 0
        for k in range(i - half, i + half + 1):
            if closed:
                acc += vals[k % n]; cnt += 1
            elif 0 <= k < n:
                acc += vals[k]; cnt += 1
        out.append(acc / cnt)
    return out


def _tangents(pts, closed: bool, ds: float):
    n = len(pts)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    fwd = []
    for i in range(n):
        a, b = pts[idx(i - 1)], pts[idx(i + 1)]
        span = max(1e-6, (2 * ds if closed or 0 < i < n - 1 else ds))
        t = [(b[k] - a[k]) / span for k in range(3)]
        norm = math.sqrt(sum(x * x for x in t)) or 1.0
        fwd.append([x / norm for x in t])
    return fwd


def build_line(pts, widths, *, closed: bool, spacing: float, lat_g: float, decel_g: float,
               accel_g: float, vmax_kmh: float, margin_m: float,
               dh: list[float] | None = None, inset: list[float] | None = None,
               lane_offset: bool = True) -> dict:
    """Build the line in the ENGINE frame (x=E, y=up, z=N; right of travel = (tz, −tx)).

    ``dh``/``inset`` are per-vertex channels aligned with ``pts`` (divider half-width, kerb-line
    barrier inset); ``lane_offset=False`` keeps the line on the centreline whatever they say."""
    n_in = len(pts)
    dh = list(dh) if dh is not None else [0.0] * n_in
    inset = list(inset) if inset is not None else [0.0] * n_in
    if len(dh) != n_in or len(inset) != n_in:
        raise ValueError(f"channel length mismatch: pts {n_in}, dh {len(dh)}, inset {len(inset)}")
    base, widths, ds, (dh, inset) = _resample(pts, widths, spacing, closed, extra=[dh, inset])
    n = len(base)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))

    # lane offset: policy per station, smoothed along the lap, re-clamped so smoothing can never
    # push the line into a divider or the kerb-line barrier
    off = lane_offsets(widths, dh, inset) if lane_offset else [0.0] * n
    if lane_offset and any(o != 0.0 for o in off):
        off = _smooth(off, SMOOTH_HALF_WIN, closed)
        for i in range(n):
            if dh[i] > 0.0:
                lo, hi = dh[i] + LINE_MIN_CLEAR_M, widths[i] / 2.0 - inset[i] - LINE_MIN_CLEAR_M
                off[i] = (dh[i] + widths[i] / 2.0 - inset[i]) / 2.0 if lo > hi else min(max(off[i], lo), hi)
            elif dh[i] == 0.0 and abs(off[i]) > 0.0:
                # smoothing leaked a divider lane onto an undivided station — keep it inside the
                # kerb-line barriers of THIS station, never past them
                off[i] = min(max(off[i], 0.0), max(0.0, widths[i] / 2.0 - inset[i] - LINE_MIN_CLEAR_M))
    base_t = _tangents(base, closed, ds)
    pts = []
    for i in range(n):
        tx, tz = base_t[i][0], base_t[i][2]
        L = math.hypot(tx, tz) or 1.0
        rx, rz = tz / L, -tx / L                    # right of travel, engine frame
        pts.append([base[i][0] + rx * off[i], base[i][1], base[i][2] + rz * off[i]])

    radius = [_circumradius(pts[idx(i - 1)], pts[i], pts[idx(i + 1)]) for i in range(n)]
    for _ in range(2):                                     # light smooth: min of neighbours window
        radius = [min(radius[idx(i - 1)], radius[i], radius[idx(i + 1)]) for i in range(n)]

    vmax = vmax_kmh / 3.6
    v = [min(vmax, math.sqrt(lat_g * G * r)) for r in radius]
    passes = 2 if closed else 1
    for _ in range(passes):                                # backward: braking limit
        for i in range(n - 1, -1, -1):
            vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
            v[i] = min(v[i], math.sqrt(vn * vn + 2 * decel_g * G * ds))
    for _ in range(passes):                                # forward: acceleration limit
        for i in range(n):
            vp = v[idx(i - 1)] if (closed or i > 0) else v[i]
            v[i] = min(v[i], math.sqrt(vp * vp + 2 * accel_g * G * ds))

    length = [i * ds for i in range(n)]
    lap_s = sum(ds / max(v[i], 1.0) for i in range(n if closed else n - 1))

    fwd = _tangents(pts, closed, ds)
    grade, gas, brake = [], [], []
    for i in range(n):
        grade.append(fwd[i][1])
        vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
        acc = (vn * vn - v[i] * v[i]) / (2 * ds)
        brake.append(max(0.0, min(1.0, -acc / (decel_g * G))))
        gas.append(0.0 if brake[-1] > 0.05 else max(0.25, min(1.0, acc / (accel_g * G) + 0.55)))

    # asymmetric sides: distance from the line to the nearer boundary each way, minus the margin.
    # Boundaries (lateral, right positive): divider face / −(w/2 − inset) on the left, w/2 − inset
    # on the right. With no divider and no inset both read w/2 − margin, exactly as before.
    side_l, side_r = [], []
    for i in range(n):
        w, d, s, o = widths[i], dh[i], inset[i], off[i]
        left_b = d if d > 0.0 else -(w / 2.0 - s)
        right_b = w / 2.0 - s
        side_l.append(max(0.5, (o - left_b) - margin_m))
        side_r.append(max(0.5, (right_b - o) - margin_m))
    return {"pts": pts, "v": v, "length": length, "radius": radius, "fwd": fwd, "grade": grade,
            "gas": gas, "brake": brake, "side_l": side_l, "side_r": side_r, "off": off,
            "base": base, "dh": dh, "inset": inset, "widths": widths,
            "ds": ds, "lap_s": lap_s, "closed": closed}


def write_ai(line: dict, out: Path) -> None:
    n = len(line["pts"])
    side_l = line.get("side_l") or line["side"]
    side_r = line.get("side_r") or line["side"]
    buf = bytearray()
    buf += struct.pack("<4i", 7, n, int(line["lap_s"] * 1000), n)
    for i, p in enumerate(line["pts"]):
        buf += struct.pack("<4fi", p[0], p[1], p[2], line["length"][i], i)
    buf += struct.pack("<i", n)
    for i in range(n):
        f = line["fwd"][i]
        buf += struct.pack(
            "<18f",
            line["v"][i], line["gas"][i], line["brake"][i], 0.0,
            line["radius"][i], side_l[i], side_r[i],
            0.0, 0.0,                                  # camber, direction
            0.0, 1.0, 0.0,                             # normal (up)
            line["length"][i],
            f[0], f[1], f[2],
            0.0, line["grade"][i],
        )
    buf += struct.pack("<i", 0)                        # hasGrid = 0
    out.write_bytes(bytes(buf))


def write_sides(line: dict, out_dir: Path) -> None:
    """side_l/side_r.csv — lateral offsets of the drivable edge (the Shift-rebuild inputs).

    Written in the frame ``line`` is in at call time (main calls it after the kn5 flip). In the kn5
    frame (−fz, fx) is the driver's RIGHT, so side_l takes the negative sign."""
    side_l = line.get("side_l") or line["side"]
    side_r = line.get("side_r") or line["side"]
    for name, sign, dist in (("side_l.csv", -1.0, side_l), ("side_r.csv", 1.0, side_r)):
        rows = []
        for i, p in enumerate(line["pts"]):
            f = line["fwd"][i]
            px, pz = -f[2], f[0]
            nrm = math.hypot(px, pz) or 1.0
            o = dist[i] * sign
            rows.append(f"{p[0] + px / nrm * o:.3f},{p[1]:.3f},{p[2] + pz / nrm * o:.3f}")
        (out_dir / name).write_text("\n".join(rows) + "\n", encoding="ascii")


# --- measurement -----------------------------------------------------------------

def grid_alignment(pts: list[list[float]], dummies: dict, closed: bool) -> tuple[float, str] | None:
    """Measure which way the grid faces, against the line's own order (ledger 0026).

    A track's direction is a contract: the grid faces one way and the spline must run the same
    way, or AC's spline-based direction logic contradicts its dummy-based grid and the field
    launches into a ghost route (0023) or is told it is going the wrong way in both directions
    (0026, IMI measured at −0.93). Everything is read in the ENGINE frame — the frame
    ``dummies.json`` / ``dummies_<layout>.json`` are written in, before the kn5 z-mirror; the
    caller normalises ``pts`` to that frame first (``_to_engine_frame``).

    The two track kinds need different rulers, and using the loop's ruler on a stage is wrong:

    * **closed loop** — AC_TIME_0 sits within metres of the grid, so the grid→timing chord IS the
      local heading. Dot it against the tangent at the start. If the timing line turns out to be
      far away the chord is a straight line across a curve and means nothing, so we refuse it
      rather than report a confident-looking number.
    * **point-to-point** — AC_TIME_0 is the *finish*, up to 18 km away (under-the-dragon), and the
      chord is not a heading at all. Direction is instead unambiguous from where the grid sits
      along the line: near index 0 means forward, near the end means reverse.

    Returns (score in [−1, 1], how it was measured), or None when nothing can be measured.
    """
    start = dummies.get("AC_START_0")
    if not start:
        return None
    n = len(pts)
    i = min(range(n), key=lambda k: (pts[k][0] - start[0]) ** 2 + (pts[k][2] - start[2]) ** 2)

    if not closed:
        frac = i / max(1, n - 1)                       # 0 = line starts at the grid, 1 = ends there
        return (1.0 - 2.0 * frac, f"grid at {frac * 100:.0f}% along the stage")

    tl, tr = dummies.get("AC_TIME_0_L"), dummies.get("AC_TIME_0_R")
    if not (tl and tr):
        return None
    mx, mz = (tl[0] + tr[0]) / 2, (tl[2] + tr[2]) / 2
    gx, gz = mx - start[0], mz - start[2]
    gn = math.hypot(gx, gz)
    if gn < 1e-6 or gn > 250.0:                        # on top of the grid, or too far to be a heading
        return None
    a, b = pts[i], pts[(i + 1) % n]
    tx, tz = b[0] - a[0], b[2] - a[2]
    tn = math.hypot(tx, tz)
    if tn < 1e-6:
        return None
    return ((gx / gn) * (tx / tn) + (gz / gn) * (tz / tn), f"grid→timing chord over {gn:.0f} m")


def detect_frame(fin_pts, local_pts, mirror_x: bool = False) -> tuple[str, float, float]:
    """Which frame is the finished line in — 'engine' (as centerline.local.json, x mirrored per
    mirror_x) or 'kn5' (z negated)? Returns (frame, median_dist_engine, median_dist_kn5).

    Decided by the median nearest distance of ~60 sampled local vertices under each hypothesis.
    A tie (a z-symmetric loop) or a line that matches neither keeps today's assumption: engine."""
    sx = -1.0 if mirror_x else 1.0
    n = len(local_pts)
    if n == 0 or not fin_pts:
        return "engine", 0.0, 0.0
    step = max(1, n // 60)
    sample = [local_pts[i] for i in range(0, n, step)]
    fx = [p[0] for p in fin_pts]
    fz = [p[2] for p in fin_pts]
    cell = 25.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i in range(len(fin_pts)):
        grid.setdefault((int(fx[i] // cell), int(fz[i] // cell)), []).append(i)

    def nearest(x, z):
        best = float("inf")
        cx, cz = int(x // cell), int(z // cell)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in grid.get((cx + dx, cz + dz), ()):
                    d = (fx[i] - x) ** 2 + (fz[i] - z) ** 2
                    if d < best:
                        best = d
        return math.sqrt(best) if best < float("inf") else cell * 2

    def median(vals):
        s = sorted(vals)
        return s[len(s) // 2]

    d_eng = median([nearest(sx * p[0], p[2]) for p in sample])
    d_kn5 = median([nearest(sx * p[0], -p[2]) for p in sample])
    frame = "kn5" if (d_kn5 < d_eng and d_eng > 5.0 and d_kn5 < d_eng / 4.0) else "engine"
    return frame, d_eng, d_kn5


def _to_engine_frame(pts, project: Path | None, mirror_x: bool) -> tuple[list[list[float]], str]:
    """Normalise the finished line to the ENGINE frame by measuring it against
    centerline.local.json (always written in that frame). No local file → assume engine."""
    lc = (project / "data" / "centerline.local.json") if project else None
    if lc is None or not lc.exists():
        return [list(p) for p in pts], "engine (unverified: no centerline.local.json)"
    local = json.loads(lc.read_text(encoding="utf-8"))["points_xyz_m"]
    frame, d_eng, d_kn5 = detect_frame(pts, local, mirror_x)
    how = f"{frame} frame (median dist to centerline.local: engine {d_eng:.1f} m / kn5 {d_kn5:.1f} m)"
    if frame == "kn5":
        return [[p[0], p[1], -p[2]] for p in pts], how
    return [list(p) for p in pts], how


def check_lane_clearance(line_pts, cl_pts, widths, dh, inset, island_w, *, closed: bool,
                         expect_right: bool, clear_m: float = CHECK_CLEAR_M) -> dict:
    """Judge the finished line (engine frame) against the PER-VERTEX declaration, not the resampled
    channels: nearest declared vertex, lateral offset about its tangent (positive = right of the
    declared forward order), then: on an island? inside a divider face + clear_m? past the
    kerb-line barrier face − clear_m? on the expected side wherever a divider stands?"""
    n = len(cl_pts)
    cell = 16.0
    grid: dict[tuple[int, int], list[int]] = {}
    for i, p in enumerate(cl_pts):
        grid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(i)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))
    res = {"points": len(line_pts), "unmatched": 0, "divider_stations": 0, "right_side": 0,
           "island_hits": 0, "divider_too_close": 0, "edge_too_close": 0,
           "min_divider_clear_m": None, "min_edge_clear_m": None, "max_lat_m": 0.0}
    for q in line_pts:
        cx, cz = int(q[0] // cell), int(q[2] // cell)
        best, bi = float("inf"), -1
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in grid.get((cx + dx, cz + dz), ()):
                    d = (cl_pts[i][0] - q[0]) ** 2 + (cl_pts[i][2] - q[2]) ** 2
                    if d < best:
                        best, bi = d, i
        if bi < 0:
            res["unmatched"] += 1
            continue
        a, b = cl_pts[idx(bi - 1)], cl_pts[idx(bi + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        tx, tz = tx / L, tz / L
        vx, vz = q[0] - cl_pts[bi][0], q[2] - cl_pts[bi][2]
        lat = vx * tz - vz * tx                      # right of forward order = positive
        res["max_lat_m"] = max(res["max_lat_m"], abs(lat))
        w, d, s, iw = widths[bi], dh[bi], inset[bi], island_w[bi]
        if iw > 0.0 and abs(lat) <= iw / 2.0:
            res["island_hits"] += 1
        if d > 0.0:
            res["divider_stations"] += 1
            on_right = lat > 0.0
            if on_right == expect_right:
                res["right_side"] += 1
            c = abs(lat) - d
            res["min_divider_clear_m"] = c if res["min_divider_clear_m"] is None else min(res["min_divider_clear_m"], c)
            if c < clear_m:
                res["divider_too_close"] += 1
        e = (w / 2.0 - s) - abs(lat)
        res["min_edge_clear_m"] = e if res["min_edge_clear_m"] is None else min(res["min_edge_clear_m"], e)
        if s > 0.0 and e < clear_m:
            res["edge_too_close"] += 1
    res["right_side_frac"] = (res["right_side"] / res["divider_stations"]) if res["divider_stations"] else None
    res["ok"] = (res["island_hits"] == 0 and res["divider_too_close"] == 0
                 and res["edge_too_close"] == 0 and res["unmatched"] == 0
                 and (res["right_side_frac"] in (None, 1.0)))
    return res


def verify(path: Path) -> str:
    d = path.read_bytes()
    ver, count, lap, _ = struct.unpack_from("<4i", d, 0)
    first = struct.unpack_from("<f", d, 16 + 12)[0]
    last = struct.unpack_from("<f", d, 16 + (count - 1) * 20 + 12)[0]
    sp = (last - first) / (count - 1) if count > 1 else 0
    return (f"{path.name}: v{ver}, {count:,} pts, {sp:.2f} m spacing over {last - first:,.0f} m, "
            f"lap {lap / 1000:.1f} s, extras={'yes' if len(d) > 16 + count * 20 + 4 else 'NO'}")


# --- per-vertex channels ---------------------------------------------------------------

def _channel(path: Path, key: str, n: int, label: str) -> list[float] | None:
    """A per-vertex float channel from a bands file, or None (missing file/key/length mismatch —
    printed loud, never silently zero)."""
    if not path.exists():
        print(f"  [{label}] {path.name} absent — {key} = 0 everywhere")
        return None
    vals = json.loads(path.read_text(encoding="utf-8")).get(key)
    if vals is None:
        print(f"  [{label}] {path.name} has no {key} — treated as 0 everywhere")
        return None
    if len(vals) not in (n, n + 1):
        print(f"  [{label}] {path.name} {key}: {len(vals)} values vs {n} vertices — DISABLED")
        return None
    return [float(v) for v in vals[:n]]


def load_layout(project: Path, layout_id: str) -> dict | None:
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    return next((lo for lo in (cfg.get("layouts") or []) if lo.get("id") == layout_id), None)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate fast_lane.ai (v7) from the racing line.")
    ap.add_argument("src", type=Path, help="project dir (reads data/finished_centerline.json) or a json path")
    ap.add_argument("--out", type=Path, help="output dir (default <project>/ai or <project>/ai/<layout>)")
    ap.add_argument("--install", type=Path, help="AC track dir to copy ai/ into")
    ap.add_argument("--spacing", type=float, default=1.5, help="point spacing m (measured ref floor)")
    ap.add_argument("--lat-g", type=float, default=1.6)
    ap.add_argument("--decel-g", type=float, default=1.0)
    ap.add_argument("--accel-g", type=float, default=0.4)
    ap.add_argument("--vmax-kmh", type=float, default=250.0)
    ap.add_argument("--margin-m", type=float, default=1.2, help="kept clear of each road edge")
    ap.add_argument("--no-pit-copy", action="store_true", help="skip pit_lane.ai = fast_lane.ai")
    ap.add_argument("--reverse", action="store_true",
                    help="force the line opposite the centerline order (same as --direction reverse)")
    ap.add_argument("--direction", choices=("auto", "forward", "reverse"), default="auto",
                    help="auto (default): with --layout the layout's declared direction, else the "
                         "grid heading measured in data/dummies.json (ledger 0026); forward/reverse "
                         "override it (with --layout an override that contradicts the config fails)")
    ap.add_argument("--layout", help="layout id from track.config.json layouts[] (ledger 0047): "
                                     "direction + race_furniture from the config, output ai/<id>/, "
                                     "grid check against data/dummies_<id>.json")
    ap.add_argument("--lane-offset", choices=("auto", "none"), default="auto",
                    help="auto (default): right-hand carriageway wherever a divider is declared "
                         "(median island; centre chain + kerb-line inset for race layouts); none: "
                         "the centreline, as before")
    ap.add_argument("--race-furniture", choices=("auto", "on", "off"), default="auto",
                    help="consult data/barrier_bands.json: auto = layouts[].race_furniture")
    ap.add_argument("--bands", type=Path, help="barrier bands file (default data/barrier_bands.json)")
    args = ap.parse_args(argv)

    project = args.src if args.src.is_dir() else None
    src = args.src / "data" / "finished_centerline.json" if args.src.is_dir() else args.src
    data_dir = src.parent
    j = json.loads(src.read_text(encoding="utf-8"))
    pts, widths = j["points_xyz_m"], j["widths_m"]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    if closed:
        pts, widths = pts[:-1], widths[:-1]            # L13: drop the duplicate, wrap everything
    n = len(pts)

    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8")) if project else {}
    pts, how_frame = _to_engine_frame(pts, project, bool(cfg.get("mirror_x", False)))
    print(f"frame: finished_centerline read as {how_frame}")

    # Layout (0047): direction + furniture from the config; an undeclared id needs explicit flags.
    layout = load_layout(project, args.layout) if (project and args.layout) else None
    if args.layout and layout is None:
        if args.direction == "auto" and not args.reverse:
            raise SystemExit(f"--layout {args.layout}: not declared in track.config.json layouts[] "
                             f"— pass --direction forward|reverse explicitly for an undeclared id")
        print(f"layout {args.layout}: NOT declared in track.config.json — direction/furniture from flags")
    mode = "reverse" if args.reverse else args.direction
    if layout is not None:
        declared = str(layout.get("direction", "forward"))
        if declared not in ("forward", "reverse"):
            raise SystemExit(f"layout {args.layout}: direction {declared!r} must be forward|reverse")
        if mode == "auto":
            mode = declared
            print(f"direction: {mode.upper()} (layouts[{args.layout}].direction)")
        elif mode != declared:
            raise SystemExit(f"--direction {mode} contradicts layouts[{args.layout}].direction={declared}")
    elif mode == "auto":
        # Direction, measured rather than assumed (0026). The grid is the contract; the spline obeys.
        dpath = data_dir / "dummies.json"
        dums = {}
        if dpath.exists():
            dums = {k: v for k, v in json.loads(dpath.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")}
        m = grid_alignment(pts, dums, closed) if dums else None
        if m is None:
            mode = "forward"
            print("direction: nothing measurable in dummies.json — running FORWARD unverified")
        else:
            dot, how = m
            mode = "reverse" if dot < 0 else "forward"
            flag = "" if abs(dot) >= 0.5 else "  ** WEAK — verify in game **"
            print(f"direction: {dot:+.2f} ({how}) -> {mode.upper()}{flag}")
    # With a layout the declared direction is re-measured against ITS grid when the dummies exist
    # (the chord is 27-30 m on Alvarado): a contradiction is a build error, not a warning.
    if args.layout:
        dpath = data_dir / f"dummies_{args.layout}.json"
        if dpath.exists():
            dums = {k: v for k, v in json.loads(dpath.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")}
            m = grid_alignment(pts, dums, closed)
            if m is None:
                print(f"  grid check: dummies_{args.layout}.json carries nothing measurable")
            else:
                dot, how = m
                measured = "reverse" if dot < 0 else "forward"
                print(f"  grid check: {dot:+.2f} ({how}) -> {measured.upper()}")
                if measured != mode:
                    raise SystemExit(f"layout {args.layout}: grid faces {measured.upper()} but the "
                                     f"line is declared {mode.upper()} — the grid is the contract")
        else:
            print(f"  grid check: no dummies_{args.layout}.json — declared direction unverified against the grid")

    race = {"auto": bool(layout.get("race_furniture", False)) if layout else False,
            "on": True, "off": False}[args.race_furniture]

    # Per-vertex divider channels, ENGINE frame, index-aligned with the forward vertex order.
    zeros = [0.0] * n
    island = _channel(data_dir / "median_bands.json", "island_w_by_vertex", n, "island") or zeros
    bands_path = args.bands or (data_dir / "barrier_bands.json")
    centre_w = inset = zeros
    if race:
        centre_w = _channel(bands_path, "centre_w_by_vertex", n, "barrier") or zeros
        inset = _channel(bands_path, "edge_inset_by_vertex", n, "barrier") or zeros
    else:
        print("  race furniture OFF for this line: centre chain / kerb-line inset not applied")
    dh = [max(iw / 2.0, cw / 2.0) for iw, cw in zip(island, centre_w)]
    use_offset = args.lane_offset == "auto"
    fwd_order = {"pts": [list(p) for p in pts], "widths": list(widths), "dh": dh, "inset": inset,
                 "island": island}
    if mode == "reverse":
        pts, widths = list(reversed(pts)), list(reversed(widths))
        dh, inset = list(reversed(dh)), list(reversed(inset))
    line = build_line(pts, widths, closed=closed, spacing=args.spacing, lat_g=args.lat_g,
                      decel_g=args.decel_g, accel_g=args.accel_g, vmax_kmh=args.vmax_kmh,
                      margin_m=args.margin_m, dh=dh, inset=inset, lane_offset=use_offset)

    # Write-time self-check against the DECLARATION (per-vertex, forward order, engine frame).
    chk = check_lane_clearance(line["pts"], fwd_order["pts"], fwd_order["widths"], fwd_order["dh"],
                               fwd_order["inset"], fwd_order["island"], closed=closed,
                               expect_right=(mode == "forward"))
    n_off = sum(1 for o in line["off"] if o != 0.0)
    print(f"lane: {n_off:,}/{len(line['off']):,} pts offset into the right-hand carriageway "
          f"(max {max(line['off']) if line['off'] else 0:.2f} m); divider stations {chk['divider_stations']:,}, "
          f"on the correct side {chk['right_side_frac'] if chk['right_side_frac'] is not None else 'n/a'}; "
          f"island hits {chk['island_hits']}, within {CHECK_CLEAR_M} m of a divider face "
          f"{chk['divider_too_close']}, of a kerb-line barrier face {chk['edge_too_close']}"
          + (f"; min clear divider {chk['min_divider_clear_m']:.2f} m" if chk['min_divider_clear_m'] is not None else "")
          + (f", edge {chk['min_edge_clear_m']:.2f} m" if chk['min_edge_clear_m'] is not None else ""))
    if not chk["ok"]:
        raise SystemExit("REFUSED: the line crosses a declared island/barrier band — see the lane line above")

    # The kn5/AC world is z-MIRRORED relative to the engine local frame (verified against the
    # installed dummies: kn5 z = -engine z). An unflipped line sends the AI down a ghost mirror
    # route through the terrain — they launch and never come back (ledger 0023). Flip once, here.
    for p in line["pts"]:
        p[2] = -p[2]
    for f in line["fwd"]:
        f[2] = -f[2]

    if args.out:
        out = args.out
    else:
        base_dir = (args.src if args.src.is_dir() else src.parent.parent) / "ai"
        out = base_dir / args.layout if args.layout else base_dir
    out.mkdir(parents=True, exist_ok=True)
    write_ai(line, out / "fast_lane.ai")
    if not args.no_pit_copy:
        shutil.copyfile(out / "fast_lane.ai", out / "pit_lane.ai")
    write_sides(line, out)
    lap_m = line["length"][-1] + (line["ds"] if closed else 0.0)
    kind = "closed loop" if closed else "point-to-point"
    report = {
        "status": "GENERATED DRAFT from the built centreline — not an in-game recording (docs/HANDOFF.md "
                  ":284, ledger 0023). Replace file-for-file with CSP's fast_lane.ai.candidate recorded "
                  "in this layout.",
        "layout": args.layout, "direction": mode, "race_furniture": race, "lane_offset": use_offset,
        "frame": how_frame, "points": len(line["pts"]), "spacing_m": round(line["ds"], 3),
        "lap_m": round(lap_m, 1), "lap_s_est": round(line["lap_s"], 1),
        "offset_points": n_off, "offset_max_m": round(max(line["off"]) if line["off"] else 0.0, 3),
        "clearance": chk,
    }
    (out / "ai_draft.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"{kind}, {len(line['pts']):,} pts at {line['ds']:.2f} m over {lap_m:,.1f} m; "
          f"est lap {line['lap_s']:.1f} s ({max(line['v']) * 3.6:.0f} km/h peak) -> {out}")
    print("  " + verify(out / "fast_lane.ai"))
    if args.install:
        dst = args.install / "ai"
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("fast_lane.ai", "pit_lane.ai", "side_l.csv", "side_r.csv"):
            if (out / f).exists():
                shutil.copyfile(out / f, dst / f)
        print(f"  -> installed to {dst}")


if __name__ == "__main__":
    main()
