"""Gate: every side-street MOUTH, measured on the BUILT road (the gate OBJ of the shipped kn5) — L5: the heights
come from the triangles that ship, never from the data that placed them; the data only says where to look.

    python tools/verify_mouths.py <project-dir> [--obj data/track.obj] [--json data/verify_mouths.json]

For every data/mouths.json record (connector piece + end, host, side, cut, angle) — the host's deck HD(s) at a
host station s is its lowest 1ROAD sheet ON the host centreline (the host ribbon is level across: a connector
never reaches the centre), extended level across the host. Then:

  MOUTH LINE   along the host edge line inset MOUTH_INSET_M (inside trim_connectors' 0.4 m overlap) across the
               connector's span (where its two road edges cross that line, less CORNER_INSET_M at each corner): every
               1ROAD sheet within MOUTH_TOL_M of HD — the connector's end lies ON the host, cross-fall and all
  HOST LANE    the host's half on the mouth side, centre to half-width − LANE_EDGE_M, over the span + LANE_PAD_M each
               way (the island, if any, excluded): no 1ROAD / 1KERB top above HD + LANE_TOL_M, no 1GRASS at or
               above HD − GRASS_AT_M — nothing of the connector stands in the host's lane
  NOTCH        just outside the host edge (half-width + NOTCH_OUT_M) across the span: the top surface is 1ROAD and
               within NOTCH_TOL_M of HD — no grass / curb notch between the host and the connector
  APPROACH     along the connector (its centreline and both wheel lines, half-width − 1 m) from APPROACH_IN_M inside
               the host to APPROACH_M out: the grade measured over a WHEELBASE_M baseline (what a car's axles feel; a
               1 m difference on a 3 m-row triangulated deck reads every row crease as a kink) changes by at most
               APPROACH_DG_PER_M per metre [INVENTED, fleet/GATES-CHANGELOG.md 2026-10-11]. The 1 m figure is
               reported beside it. Sampled every 0.25 m along the piece centreline smoothed as the assembler smooths
               it (sigma 1.5 points), so a raw polyline kink is not read as a road kink; a sample pair whose plan step
               is not its nominal length +-40 % (a wheel line folding round a tight corner) is not measured. On the
               same samples (0.5 m out to APPROACH_M, the same folded-line samples left out): no 1GRASS at or above
               the connector's road (GRASS_AT_M) — the warped approach is a twisted surface, and grass planes pinned
               under it came through a valley crease
  SIDE         the side the piece approaches from (its centreline 10 m out) is mouths.json's side — gap_mouths and
               barrier_bands act on that side
  APRON        (opt-in, ledger 0054 P1 fix round: a corner apron in data/aprons.json, tools/author_aprons_blend.py, on
               this mouth's piece) the NOTCH runs on along the host past the stub's own span to where the return curb
               comes within NOTCH_OUT_M + APRON_CURB_CLEAR_M of the host edge, and the HOST LANE window to the
               apron's end + LANE_PAD_M; the apron's seam with the stub (APRON_SEAM_OUT_M either side of the stub's
               edge, from P0 to where the return stands clear of the stub): the apron's road within NOTCH_TOL_M of the stub's; its deck (every APRON_GRID_M,
               APRON_GRID_CLEAR_M inside its outline): a road sheet there, no 1GRASS at or above it (GRASS_AT_M)

Writes data/verify_mouths.json; exit 1 on any FAIL, 2 on an input error (no mouths.json / no OBJ / a mouth whose
piece cannot be found).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

MOUTH_INSET_M = 0.2
MOUTH_TOL_M = 0.05
CORNER_INSET_M = 0.75
LANE_EDGE_M = 0.45
LANE_PAD_M = 3.0
LANE_TOL_M = 0.02
GRASS_AT_M = 0.005                # "at" the deck: within 5 mm (the prep pins grass 0.02 under it at vertices;
                                  # between them it rises to 0.009 under the host edge on the welded mouths)
NOTCH_OUT_M = 0.15
NOTCH_TOL_M = 0.05
APPROACH_IN_M = 3.0
APPROACH_M = 30.0
APPROACH_DG_PER_M = 0.03          # INVENTED (3 %-pt of grade per metre); no measured envelope yet
WHEELBASE_M = 2.5                 # the baseline the approach grade is measured over (a car's axle spacing)
SAMPLE_M = 0.25
STEP_ALONG_M = 0.25
EDGE_BACK_M = 15.0                # the connector edges are searched this far past the cut into the host...
EDGE_OUT_M = 25.0                 # ...and this far out along the connector for their host-line crossing
STEP_LANE_M = 0.5
KEEP_M = 70.0
CELL = 2.0
CLASSES = (("ROAD", "1ROAD"), ("KERB", "1KERB"), ("GRASS", "1GRASS"))
APRON_CURB_CLEAR_M = 0.18         # the return curb's face (0.08 m batter) + 0.10 m: the notch runs while the return's
                                  # pavement edge stands this far past the notch line
APRON_SEAM_OUT_M = 0.15           # the stub seam is read this far either side of the stub's edge (as NOTCH_OUT_M)
#                                   ... from CORNER_INSET_M past P0 to where the return (tangent at T, radius R) stands
#                                   APRON_SEAM_OUT_M + APRON_CURB_CLEAR_M off the stub's edge: sqrt(2 R (that)) short of T
APRON_GRID_M = 0.5
APRON_GRID_CLEAR_M = 0.3


def load_obj(path: Path, centres, keep=KEEP_M):
    """{class: [tri]} for 1ROAD / 1KERB / 1GRASS triangles with a vertex within `keep` (plan) of any centre"""
    V = []
    tris = {c: [] for c, _ in CLASSES}
    cur = None
    k2 = keep * keep

    def near(p):
        for cx, cz in centres:
            if (p[0] - cx) ** 2 + (p[2] - cz) ** 2 <= k2:
                return True
        return False

    with open(path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            c2 = line[:2]
            if c2 == "v ":
                q = line.split()
                V.append((float(q[1]), float(q[2]), float(q[3])))
            elif c2 == "o " or c2 == "g ":
                name = line[2:].strip().upper()
                cur = next((c for c, pre in CLASSES if name.startswith(pre)), None)
            elif c2 == "f " and cur is not None:
                idx = [int(t.split("/")[0]) for t in line.split()[1:]]
                pts = [V[i - 1] if i > 0 else V[i] for i in idx]
                if any(near(p) for p in pts):
                    for k in range(1, len(pts) - 1):
                        tris[cur].append((pts[0], pts[k], pts[k + 1]))
    return tris


class Field:
    """point queries on a set of triangles: every sheet height at (x, z), per class"""

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
        out = {c: [] for c, _ in CLASSES}
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


def smooth_xz(pts, sigma=1.5):
    """the assembler's plan smoothing of an open connector (scripts/geometry/smooth.py: one Gaussian pass of
    sigma points, endpoints pinned) — the ribbon is swept on this, not on the raw points"""
    n = len(pts)
    r = max(1, int(round(3.0 * sigma)))
    ker = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    out = []
    for i in range(n):
        if i == 0 or i == n - 1:
            out.append(tuple(pts[i]))
            continue
        sx = sz = sw = 0.0
        for k in range(-r, r + 1):
            j = min(n - 1, max(0, i + k))
            w = ker[k + r]
            sx += pts[j][0] * w
            sz += pts[j][2] * w
            sw += w
        out.append((sx / sw, pts[i][1], sz / sw))
    return out


class Path2:
    """a host / connector polyline by plan arc, with its widths: point(s, lateral) and the frame there"""

    def __init__(self, pts, widths):
        self.p = [tuple(q) for q in pts]
        self.w = list(widths)
        self.s = [0.0]
        for i in range(1, len(self.p)):
            self.s.append(self.s[-1] + math.hypot(self.p[i][0] - self.p[i - 1][0], self.p[i][2] - self.p[i - 1][2]))

    def _seg(self, s):
        lo, hi = 0, len(self.s) - 1
        s = max(self.s[0], min(self.s[-1], s))
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.s[mid] <= s:
                lo = mid
            else:
                hi = mid
        seg = self.s[hi] - self.s[lo]
        return lo, hi, (0.0 if seg < 1e-12 else (s - self.s[lo]) / seg)

    def frame(self, s):
        lo, hi, t = self._seg(s)
        a, b = self.p[lo], self.p[hi]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        tx, tz = dx / L, dz / L
        return (a[0] + dx * t, a[2] + dz * t), (tx, tz), (-tz, tx), self.w[lo] * (1 - t) + self.w[hi] * t

    def point(self, s, lat):
        (x, z), _t, (nx, nz), _w = self.frame(s)
        return x + nx * lat, z + nz * lat

    def project(self, x, z):
        best = None
        for i in range(len(self.p) - 1):
            a, b = self.p[i], self.p[i + 1]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[2]) * dz) / L2))
            d = math.hypot(x - (a[0] + dx * t), z - (a[2] + dz * t))
            if best is None or d < best[0]:
                lat = (-dz * (x - a[0]) + dx * (z - a[2])) / math.sqrt(L2)
                best = (d, self.s[i] + (self.s[i + 1] - self.s[i]) * t, lat)
        return best


def _island_half(mo, host_path, data, s):
    """the host's median-island half-width at host arc s (0 when none)"""
    bp = data / "median_bands.json"
    if not bp.exists():
        return 0.0
    bands = json.loads(bp.read_text(encoding="utf-8"))
    if mo["host"] == "MAINLINE":
        iw = bands.get("island_w_by_vertex") or []
        if not iw:
            return 0.0
        lo, hi, t = host_path._seg(s)
        return max(iw[min(lo, len(iw) - 1)], iw[min(hi, len(iw) - 1)]) / 2.0
    for ci in bands.get("connector_islands", []):
        if mo["host"] == ci["name"] or mo["host"].startswith(ci["name"] + "#"):
            (x, z), _t, _n, _w = host_path.frame(s)
            best = min(range(len(ci["points_xyz_m"])),
                       key=lambda k: math.hypot(ci["points_xyz_m"][k][0] - x, ci["points_xyz_m"][k][2] - z))
            k0 = max(0, best - 2)
            if ci.get("offset_aware"):
                # ledger 0054 P3: a north piece's raised median stands off the host's centre line (median_off_m) —
                # its reach on the mouth's side is its own lateral + its half-width, point by point
                side = int(mo.get("side", 1))
                (_x, _z), _t, (nx, nz), _w = host_path.frame(s)
                ext = 0.0
                for k in range(k0, min(len(ci["points_xyz_m"]), best + 3)):
                    w_ = ci["island_w_by_point"][k]
                    if w_ <= 0:
                        continue
                    q = ci["points_xyz_m"][k]
                    lat = (q[0] - x) * nx + (q[2] - z) * nz
                    ext = max(ext, side * lat + w_ / 2.0)
                return ext
            return max(ci["island_w_by_point"][k0:best + 3]) / 2.0
    return 0.0


def _pip(poly, x, z):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return inside


def _d_outline(poly, x, z):
    best = float("inf")
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        best = min(best, math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz)))
    return best


def check_mouth(mo, field, host_path, piece_path, piece_end, data, exact_deck: bool = False, apron=None) -> dict:
    fails = []
    cx, _cy, cz = mo["cut_xyz"]
    _d, c, _lat = host_path.project(cx, cz)
    _p, (htx, htz), _n, hwid = host_path.frame(c)
    half = hwid / 2.0
    # the connector's approach: from the cut along the piece
    plen = piece_path.s[-1]
    s_dir = (lambda u: u) if piece_end == "start" else (lambda u: plen - u)
    q0 = piece_path.point(s_dir(0.0), 0.0)
    q1 = piece_path.point(s_dir(min(6.0, plen)), 0.0)
    ax, az = q1[0] - q0[0], q1[1] - q0[1]
    La = math.hypot(ax, az) or 1.0
    ang = math.degrees(math.acos(min(1.0, abs(ax * htx + az * htz) / La)))
    q10 = piece_path.point(s_dir(min(10.0, plen)), 0.0)
    side_geo = 1 if host_path.project(q10[0], q10[1])[2] >= 0 else -1
    side = int(mo["side"])
    if side_geo != side:
        fails.append(f"SIDE: the piece approaches from side {side_geo:+d}, mouths.json says {side:+d}")
    side = side_geo
    wc = (piece_path.frame(s_dir(0.0))[3])
    hw = (wc / 2.0) / max(math.sin(math.radians(max(1.0, ang))), 0.05)

    def span_at(lat_host):
        """host arcs where the connector's two road edges cross the host line at lateral side * (half + lat_host),
        nearest the cut (the edges: the smoothed centreline offset by +-half its width)"""
        out = []
        for e in (1.0, -1.0):
            prev = None
            for k in range(-int(EDGE_BACK_M / 0.05), int(EDGE_OUT_M / 0.05) + 1):
                u = 0.05 * k
                if u < 0:
                    x0, z0 = piece_path.point(s_dir(0.0), e * wc / 2.0)
                    x, z = x0 + ax / La * u, z0 + az / La * u      # u < 0: past the cut, into the host
                else:
                    uu = s_dir(min(u, plen))
                    x, z = piece_path.point(uu, e * piece_path.frame(uu)[3] / 2.0)
                _dd, sh, lat = host_path.project(x, z)
                hh = host_path.frame(sh)[3] / 2.0
                g = side * lat - (hh + lat_host)
                if prev is not None and (prev[0] <= 0.0) != (g <= 0.0):
                    t = prev[0] / (prev[0] - g)
                    out.append(prev[1] + (sh - prev[1]) * t)
                    break
                prev = (g, sh)
        if len(out) < 2:
            return c - hw, c + hw                         # an edge never crossed: the analytic span
        return min(out), max(out)
    ml_lo, ml_hi = span_at(-MOUTH_INSET_M)
    nt_lo, nt_hi = span_at(NOTCH_OUT_M)
    lo_s, hi_s = ml_lo + CORNER_INSET_M, ml_hi - CORNER_INSET_M
    lane_lo, lane_hi = c - hw - LANE_PAD_M, c + hw + LANE_PAD_M
    ap_rec = None
    if apron is not None:
        # the notch runs on over the apron while the return's pavement edge stands clear of the notch line; the host
        # lane window to the apron's far end
        run = []
        for q in apron["arc_xyz"]:
            _dd, sq, lq = host_path.project(q[0], q[2])
            off = side * lq - host_path.frame(sq)[3] / 2.0
            run.append((sq, off))
        clear = [sq for sq, off in run if off >= NOTCH_OUT_M + APRON_CURB_CLEAR_M]
        s_end = [sq for sq, _o in run][-1]
        if clear:
            if s_end >= c:
                nt_hi = max(nt_hi, max(clear) + CORNER_INSET_M)
            else:
                nt_lo = min(nt_lo, min(clear) - CORNER_INSET_M)
        lane_lo, lane_hi = min(lane_lo, s_end - LANE_PAD_M), max(lane_hi, s_end + LANE_PAD_M)
        ap_rec = {"id": apron["id"], "notch_span_m": [round(nt_lo - c, 2), round(nt_hi - c, 2)],
                  "lane_span_m": [round(lane_lo - c, 2), round(lane_hi - c, 2)]}

    def HD(s):
        x, z = host_path.point(s, 0.0)
        r = field.heights(x, z)["ROAD"]
        return min(r) if r else None

    def steps(a, b, d):
        n = max(1, int(round((b - a) / d)))
        return [a + (b - a) * k / n for k in range(n + 1)]

    # MOUTH LINE
    ml = {"samples": 0, "fail": 0, "max_dev_m": 0.0, "no_road": 0, "worst": None}
    for s in steps(lo_s, hi_s, STEP_ALONG_M):
        hd = HD(s)
        if hd is None:
            continue
        hhalf = host_path.frame(s)[3] / 2.0
        x, z = host_path.point(s, side * (hhalf - MOUTH_INSET_M))
        r = field.heights(x, z)["ROAD"]
        ml["samples"] += 1
        if not r:
            ml["no_road"] += 1
            continue
        dev = max(abs(v - hd) for v in r)
        if dev > ml["max_dev_m"]:
            ml["max_dev_m"] = round(dev, 3)
            ml["worst"] = [round(s - c, 2), round(x, 2), round(z, 2), [round(v - hd, 3) for v in r]]
        if dev > MOUTH_TOL_M:
            ml["fail"] += 1
    if ml["fail"] or ml["no_road"]:
        fails.append(f"MOUTH LINE: {ml['fail']} / {ml['samples']} samples with a ROAD sheet > {MOUTH_TOL_M} m off the host "
                     f"deck (max {ml['max_dev_m']} m), {ml['no_road']} with no road")
    # HOST LANE
    hl = {"samples": 0, "road_kerb_above": 0, "grass_at_or_above": 0, "max_above_m": 0.0, "max_grass_m": None,
          "worst": []}
    for s in steps(lane_lo, lane_hi, STEP_LANE_M):
        hd_s = HD(s)
        if hd_s is None:
            continue
        hhalf = host_path.frame(s)[3] / 2.0
        isl = _island_half(mo, host_path, data, s)
        o = isl + 0.3 if isl > 0 else 0.0
        while o <= hhalf - LANE_EDGE_M + 1e-9:
            x, z = host_path.point(s, side * o)
            h = field.heights(x, z)
            hl["samples"] += 1
            if exact_deck and h["ROAD"]:
                # ledger 0054 P1 (route.weld_exact_deck): the host deck AT the sample, its lowest road sheet — on a
                # corner's fanned outer half the level-across HD(s) reads the host's own triangles up to 2.2 cm
                # "above themselves" (the v0.18.0 J5 corner with no mouth at all: 8 such samples, 21 grass ones)
                hd = min(h["ROAD"])
            else:
                hd = hd_s
            top = max(h["ROAD"] + h["KERB"], default=None)
            if top is not None and top - hd > LANE_TOL_M:
                hl["road_kerb_above"] += 1
                hl["max_above_m"] = max(hl["max_above_m"], round(top - hd, 3))
                if len(hl["worst"]) < 8:
                    hl["worst"].append(["above", round(s - c, 2), round(o, 2), round(top - hd, 3)])
            if h["GRASS"]:
                g = max(h["GRASS"]) - hd
                hl["max_grass_m"] = round(g, 3) if hl["max_grass_m"] is None else max(hl["max_grass_m"], round(g, 3))
                if g >= -GRASS_AT_M:
                    hl["grass_at_or_above"] += 1
                    if len(hl["worst"]) < 8:
                        hl["worst"].append(["grass", round(s - c, 2), round(o, 2), round(g, 3)])
            o += STEP_LANE_M
    if hl["road_kerb_above"] or hl["grass_at_or_above"]:
        fails.append(f"HOST LANE: {hl['road_kerb_above']} samples with road/curb > {LANE_TOL_M} m over the host deck "
                     f"(max {hl['max_above_m']} m), {hl['grass_at_or_above']} with grass at/above it")
    # NOTCH
    nt = {"samples": 0, "fail": 0, "max_dev_m": 0.0, "worst": []}
    for s in steps(nt_lo + CORNER_INSET_M, nt_hi - CORNER_INSET_M, STEP_ALONG_M):
        hd = HD(s)
        if hd is None:
            continue
        hhalf = host_path.frame(s)[3] / 2.0
        x, z = host_path.point(s, side * (hhalf + NOTCH_OUT_M))
        h = field.heights(x, z)
        nt["samples"] += 1
        road = max(h["ROAD"], default=None)
        other = max(h["KERB"] + h["GRASS"], default=None)
        bad = road is None or abs(road - hd) > NOTCH_TOL_M or (other is not None and other > road - 0.005)
        if road is not None:
            nt["max_dev_m"] = max(nt["max_dev_m"], round(abs(road - hd), 3))
        if bad:
            nt["fail"] += 1
            if len(nt["worst"]) < 8:
                nt["worst"].append([round(s - c, 2), None if road is None else round(road - hd, 3),
                                    None if other is None else round(other - hd, 3)])
    if nt["fail"]:
        fails.append(f"NOTCH: {nt['fail']} / {nt['samples']} samples just outside the host edge are not the connector's "
                     f"road at the host deck (+-{NOTCH_TOL_M} m), e.g. [s, road-HD, curb/grass-HD] {nt['worst'][:3]}")
    # APRON: the seam with the stub and the deck itself
    if apron is not None:
        seam = [tuple(q) for q in apron["seam_stub_xyz"]]          # P0 .. T along the stub's apron-side edge
        Ls = [0.0]
        for i in range(1, len(seam)):
            Ls.append(Ls[-1] + math.hypot(seam[i][0] - seam[i - 1][0], seam[i][2] - seam[i - 1][2]))
        out_dir = apron["outline_xz"]
        sm = {"samples": 0, "fail": 0, "max_dev_m": 0.0, "worst": []}
        u = CORNER_INSET_M
        seam_inset = math.sqrt(2.0 * float(apron["R_m"]) * (APRON_SEAM_OUT_M + APRON_CURB_CLEAR_M))
        while u <= Ls[-1] - seam_inset + 1e-9:
            i = max(k for k in range(len(seam) - 1) if Ls[k] <= u + 1e-12) if u > 0 else 0
            i = min(i, len(seam) - 2)
            t = (u - Ls[i]) / max(Ls[i + 1] - Ls[i], 1e-9)
            x = seam[i][0] + (seam[i + 1][0] - seam[i][0]) * t
            z = seam[i][2] + (seam[i + 1][2] - seam[i][2]) * t
            tx, tz = seam[i + 1][0] - seam[i][0], seam[i + 1][2] - seam[i][2]
            Lt = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / Lt, tx / Lt
            if not _pip(out_dir, x + nx * 0.5, z + nz * 0.5):
                nx, nz = -nx, -nz                                   # +n into the apron
            hi_ = field.heights(x + nx * APRON_SEAM_OUT_M, z + nz * APRON_SEAM_OUT_M)
            lo_ = field.heights(x - nx * APRON_SEAM_OUT_M, z - nz * APRON_SEAM_OUT_M)
            sm["samples"] += 1
            ra, rs = max(hi_["ROAD"], default=None), max(lo_["ROAD"], default=None)
            other = max(hi_["KERB"] + hi_["GRASS"], default=None)
            bad = ra is None or rs is None or abs(ra - rs) > NOTCH_TOL_M or (other is not None and other > ra - 0.005)
            if ra is not None and rs is not None:
                sm["max_dev_m"] = max(sm["max_dev_m"], round(abs(ra - rs), 3))
            if bad:
                sm["fail"] += 1
                if len(sm["worst"]) < 8:
                    sm["worst"].append([round(u, 2), None if ra is None else round(ra, 3), None if rs is None else round(rs, 3),
                                        None if other is None else round(other, 3)])
            u += STEP_ALONG_M
        dk = {"samples": 0, "holes": 0, "grass_at_or_above": 0, "max_grass_m": None, "worst": []}
        xs = [q[0] for q in out_dir]
        zs = [q[1] for q in out_dir]
        x = math.floor(min(xs) / APRON_GRID_M) * APRON_GRID_M
        while x <= max(xs):
            z = math.floor(min(zs) / APRON_GRID_M) * APRON_GRID_M
            while z <= max(zs):
                if _pip(out_dir, x, z) and _d_outline(out_dir, x, z) >= APRON_GRID_CLEAR_M:
                    h = field.heights(x, z)
                    dk["samples"] += 1
                    if not h["ROAD"]:
                        dk["holes"] += 1
                        if len(dk["worst"]) < 8:
                            dk["worst"].append(["hole", round(x, 2), round(z, 2)])
                    elif h["GRASS"]:
                        g = max(h["GRASS"]) - min(h["ROAD"])
                        dk["max_grass_m"] = round(g, 3) if dk["max_grass_m"] is None else max(dk["max_grass_m"], round(g, 3))
                        if g >= -GRASS_AT_M:
                            dk["grass_at_or_above"] += 1
                            if len(dk["worst"]) < 8:
                                dk["worst"].append(["grass", round(x, 2), round(z, 2), round(g, 3)])
                z += APRON_GRID_M
            x += APRON_GRID_M
        ap_rec.update({"stub_seam": sm, "deck": dk})
        if sm["fail"]:
            fails.append(f"APRON {apron['id']}: {sm['fail']} / {sm['samples']} samples across the stub seam are not road "
                         f"on both sides within {NOTCH_TOL_M} m (or a curb / grass stands on the apron side), e.g. "
                         f"[u, apron, stub, curb/grass] {sm['worst'][:3]}")
        if dk["holes"] or dk["grass_at_or_above"] or not dk["samples"]:
            fails.append(f"APRON {apron['id']}: deck {dk['samples']} samples, {dk['holes']} without road, "
                         f"{dk['grass_at_or_above']} with grass at/above it")
    # APPROACH
    ap = {"lines": {}, "max_dg_per_m": 0.0, "max_dg_per_m_1m": 0.0, "wheelbase_m": WHEELBASE_M}
    nb = int(round(WHEELBASE_M / 2.0 / SAMPLE_M))           # half a wheelbase, in samples
    n1 = int(round(1.0 / SAMPLE_M))                         # one metre, in samples
    for lat in (-(wc / 2.0 - 1.0), 0.0, wc / 2.0 - 1.0):
        P, H, G = [], [], []
        u = -APPROACH_IN_M - WHEELBASE_M
        while u <= APPROACH_M + WHEELBASE_M + 1e-9:
            if u < 0:
                p0 = piece_path.point(s_dir(0.0), lat)
                x, z = p0[0] + ax / La * u, p0[1] + az / La * u      # u < 0: past the cut, into the host
            else:
                x, z = piece_path.point(s_dir(min(u, plen)), lat)
            hh = field.heights(x, z)
            r = hh["ROAD"]
            P.append((x, z, u))
            H.append(max(r) if r else None)
            G.append(max(hh["GRASS"]) if hh["GRASS"] else None)
            u += SAMPLE_M

        def grade(i, half):
            a, b = i - half, i + half
            if a < 0 or b >= len(P) or H[a] is None or H[b] is None:
                return None
            d = math.hypot(P[b][0] - P[a][0], P[b][1] - P[a][1])
            if abs(d - 2 * half * SAMPLE_M) > 0.4 * 2 * half * SAMPLE_M:
                return None
            return (H[b] - H[a]) / d
        worst = worst1 = 0.0
        where = where1 = None
        skipped = 0
        for i in range(len(P)):
            if not (-APPROACH_IN_M + 1.0 <= P[i][2] <= APPROACH_M):
                continue
            g0, g1 = grade(i - n1, nb), grade(i, nb)
            f0, f1 = grade(i - n1, n1 // 2), grade(i, n1 // 2)
            if g0 is None or g1 is None:
                skipped += 1
                continue
            if abs(g1 - g0) > worst:
                worst, where = abs(g1 - g0), round(P[i][2] - 0.5, 2)
            if f0 is not None and f1 is not None and abs(f1 - f0) > worst1:
                worst1, where1 = abs(f1 - f0), round(P[i][2] - 0.5, 2)
        def regular(i):
            """the sample sits on a real wheel line: both its 0.25 m steps are 0.25 m +-40 % in plan"""
            if i <= 0 or i >= len(P) - 1:
                return False
            return all(abs(math.hypot(P[j][0] - P[j - 1][0], P[j][1] - P[j - 1][1]) - SAMPLE_M) <= 0.4 * SAMPLE_M
                       for j in (i, i + 1))
        grass, folded = [], 0
        for i in range(len(P)):
            if not (0.5 <= P[i][2] <= APPROACH_M) or G[i] is None or H[i] is None:
                continue
            if not regular(i):
                folded += 1
                continue
            if G[i] >= H[i] - GRASS_AT_M:
                grass.append((round(P[i][2], 2), round(G[i] - H[i], 3)))
        ap["grass_on_road"] = ap.get("grass_on_road", 0) + len(grass)
        ap["lines"][f"{lat:+.2f}"] = {"max_dg_per_m": round(worst, 4), "at_m": where, "max_dg_per_m_1m": round(worst1, 4),
                                      "at_m_1m": where1, "unmeasured": skipped,
                                      "holes": sum(1 for v in H if v is None), "grass_on_road": grass[:8],
                                      "grass_unmeasured_folded": folded}
        ap["max_dg_per_m"] = max(ap["max_dg_per_m"], round(worst, 4))
        ap["max_dg_per_m_1m"] = max(ap["max_dg_per_m_1m"], round(worst1, 4))
    if ap.get("grass_on_road"):
        fails.append(f"APPROACH: {ap['grass_on_road']} samples with grass at/above the connector's road (within "
                     f"{GRASS_AT_M} m) within {APPROACH_M:.0f} m of the mouth")
    if ap["max_dg_per_m"] > APPROACH_DG_PER_M:
        fails.append(f"APPROACH: the grade (over a {WHEELBASE_M} m wheelbase) changes by {100 * ap['max_dg_per_m']:.1f} %/m "
                     f"(> {100 * APPROACH_DG_PER_M:.0f} %/m [invented]) within {APPROACH_M:.0f} m of the mouth")
    return {"connector": mo["connector"], "piece": mo.get("piece"), "end": piece_end, "host": mo["host"],
            "host_vertex": mo.get("host_vertex"), "side": side, "side_recorded": int(mo["side"]),
            "angle_deg": round(ang, 2), "angle_recorded_deg": mo.get("angle_deg"), "span_half_m": round(hw, 2),
            "span_mouth_line_m": [round(ml_lo - c, 2), round(ml_hi - c, 2)],
            "span_notch_m": [round(nt_lo - c, 2), round(nt_hi - c, 2)],
            "host_half_m": round(half, 2), "mouth_line": ml, "host_lane": hl, "notch": nt, "approach": ap,
            **({"host_lane_deck": "exact: the host's lowest road sheet at each sample (route.weld_exact_deck)"}
               if exact_deck else {}),
            **({"apron": ap_rec} if ap_rec is not None else {}),
            "fails": fails, "fail": bool(fails)}


def _find_piece(mo, conns):
    """the piece whose endpoint is the cut (mouths.json piece/end when recorded, else by position)"""
    cx, _cy, cz = mo["cut_xyz"]
    byname = {c["name"]: c for c in conns}
    if mo.get("piece") in byname and mo.get("end") in ("start", "end"):
        return byname[mo["piece"]], mo["end"]
    for c in conns:
        if c["name"] != mo["connector"] and not c["name"].startswith(mo["connector"] + "#"):
            continue
        p = c["points_xyz_m"]
        for end, q in (("start", p[0]), ("end", p[-1])):
            if math.hypot(q[0] - cx, q[2] - cz) < 0.05:
                return c, end
    return None, None


def verify(project: Path, obj: Path | None = None) -> dict:
    data = project / "data"
    mp = data / "mouths.json"
    if not mp.exists():
        raise FileNotFoundError("no data/mouths.json")
    mouths = json.loads(mp.read_text(encoding="utf-8")).get("mouths", [])
    obj = obj or data / "track.obj"
    if not obj.exists():
        raise FileNotFoundError(f"no {obj}")
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8")).get("connectors", [])
    ap_path = data / "aprons.json"
    aprons = json.loads(ap_path.read_text(encoding="utf-8")).get("aprons", []) if ap_path.exists() else []
    tris = load_obj(obj, [(mo["cut_xyz"][0], mo["cut_xyz"][2]) for mo in mouths])
    cfgp = project / "track.config.json"
    exact_prefixes = [str(x) for x in ((json.loads(cfgp.read_text(encoding="utf-8")).get("route", {})
                                        .get("weld_exact_deck") or []) if cfgp.exists() else [])]
    field = Field(tris)
    rows = []
    for mo in mouths:
        piece, end = _find_piece(mo, conns)
        if piece is None:
            raise LookupError(f"mouth {mo['connector']} -> {mo['host']} v{mo.get('host_vertex')}: no piece ends at its cut")
        if mo["host"] == "MAINLINE":
            hp = Path2(local["points_xyz_m"], local["widths_m"])
        else:
            hc = next((c for c in conns if c["name"] == mo["host"]), None)
            if hc is None:
                raise LookupError(f"mouth {mo['connector']}: host {mo['host']!r} not in connectors.local.json")
            hp = Path2(hc["points_xyz_m"], hc["widths_m"])
        pp = Path2(smooth_xz([tuple(q) for q in piece["points_xyz_m"]]), piece["widths_m"])
        rows.append(check_mouth(mo, field, hp, pp, end, data,
                                exact_deck=any(str(mo["connector"]).startswith(px) for px in exact_prefixes),
                                apron=next((a for a in aprons if a.get("piece") == mo.get("piece")
                                            and a.get("host") == mo["host"]), None)))
    return {"obj": obj.name, "mouths": rows, "fail": any(r["fail"] for r in rows),
            "thresholds": {"mouth_tol_m": MOUTH_TOL_M, "lane_tol_m": LANE_TOL_M, "lane_edge_m": LANE_EDGE_M,
                           "grass_at_m": GRASS_AT_M, "notch_out_m": NOTCH_OUT_M, "notch_tol_m": NOTCH_TOL_M,
                           "approach_m": APPROACH_M, "approach_dg_per_m_invented": APPROACH_DG_PER_M,
                           "wheelbase_m": WHEELBASE_M}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--obj", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    try:
        r = verify(proj, Path(a.obj) if a.obj else None)
    except (FileNotFoundError, LookupError) as e:
        print(f"[verify_mouths] INPUT ERROR: {e}")
        return 2
    out = Path(a.json) if a.json else proj / "data" / "verify_mouths.json"
    out.write_text(json.dumps(r, indent=1), encoding="utf-8")
    for m in r["mouths"]:
        print(f"[verify_mouths] {m['piece']} ({m['end']}) -> {m['host']} side {m['side']:+d} angle {m['angle_deg']} deg: "
              f"mouth line max {m['mouth_line']['max_dev_m']} m ({m['mouth_line']['samples']} samples); host lane "
              f"road/curb above max {m['host_lane']['max_above_m']} m, grass max {m['host_lane']['max_grass_m']} m "
              f"({m['host_lane']['samples']} samples); notch max {m['notch']['max_dev_m']} m; approach max "
              f"{100 * m['approach']['max_dg_per_m']:.2f} %/m over {WHEELBASE_M} m "
              f"(1 m: {100 * m['approach']['max_dg_per_m_1m']:.2f}) — {'FAIL' if m['fail'] else 'PASS'}")
        for f in m["fails"]:
            print(f"    FAIL {f}")
    print(f"[verify_mouths] {len(r['mouths'])} mouth(s) on {r['obj']}: {'FAIL' if r['fail'] else 'PASS'} -> {out.name}")
    return 1 if r["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
