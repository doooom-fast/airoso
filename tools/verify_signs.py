"""The self-checks that make a W1-6 placement right-or-wrong mechanically (Kevin, 2026-10-10:
"very easy to see when it's right or wrong" — this is the same test as numbers). A ship gate:
tools/ship_sd.sh runs it after the authoring pass; exit 1 on any FAIL.

Reads data/signs.local.json (tools/place_signs.py / tools/author_signs_blend.py) and MEASURES —
nothing a check needs is taken from a number the placement wrote about itself. Every input a
check uses is one of: the centreline / connector json (the ribbon's own geometry, resampled HERE),
the ray origin A (the construction's input, not its output), the recorded SIGN* VERTICES (the
geometry that gets built), or — with --blend — the mesh itself. Round 1 compared mesh_clear_m with
the constant it was computed from; round 2 still computed (b)'s tangent as -face_dir, took (d)'s
side from the record and tested (e)/(f) against the formula that wrote them (fleet/GATES-CHANGELOG.md).

Per sign (a paired post is checked once per plate where a plate matters):
  (a) the approach tangent t is RE-DERIVED here: PC = the station of the plate's ribbon nearest the
      ray origin A, t = unit(P[PC-2] - P[PC-12]) over a 1 m resample made in this file; the ray
      from A along t passes within +-0.61 m (half the 48 in plate) of the UN-SLID post point,
      base - slid_m * u, AHEAD of A (a paired post adds half its pair split)
  (b) the plate faces straight back down that approach: |angle(n, -t)| <= 1 deg where n is the
      REAL plate normal — with --blend the Mesh.polygons[].normal of the SIGNPLATE faces standing
      at the post (what AC renders), else unit(front face centroid - back face centroid) of the
      plate corner vertices the authoring pass recorded; the count of distinct measured normals
      must equal the plate count. The arrow glyph's tip (its vertices) must lie on the side of
      the plate the record's arrow names, as seen from the approach.
  (c) built-edge clearance, measured two ways and both must pass: the minimum horizontal distance
      from the post base to the BUILT outside pavement edge polyline the authoring pass recorded
      (built.outside_edge_xz, perpendicular probes of the ROAD top surface per station), and —
      with --blend — an independent BVH top-surface scan inside Blender (ROAD vs
      CURB/SIDEWALK/TERRAIN, 5-degree polar scan at 0.25 m steps from the base, tools/signs_mesh.py).
      Mainline 1.3-3.0 m; connectors >= 1.0 m (gate minimum; the 1.33 m walk target is a WARN
      when missed). An analytic run (no built edge, no --blend) falls back to the polyline field
      distance and says so.
  (d) the turn direction is RE-DERIVED from the centreline: the max-curvature station after PC
      (12 m heading window), chords either side of it; the base must stand on the OUTSIDE of that
      turn relative to the local travel direction at the station nearest the base (cross product);
      the placed arrow must match the derived turn unless signs.json forced it (arrow=)
  (e) plate bottom = ground + 2.13 (+-0.05)  } --blend: ground = a ray-cast made HERE at the base
  (f) post base = ground - 0.30 (+-0.05)      } onto CURB/SIDEWALK/TERRAIN (SIGN* excluded), the
      vertices from the mesh; without --blend: the recorded vertices against the centreline height
      + 0.24 analytic, +-0.50 (terrain behind a walk sits lower), labelled polyline-only
  (g) obstacle disc, min(lane_half, 6) + 0.3 m, recomputed here over the plate footprint (base
      +- 0.61 m along every plate's right vector): a MAINLINE post must clear every centreline's
      disc; a CONNECTOR post must clear the MAINLINE disc (drive_test sweeps the mainline only)
      and a negative own-street margin is a WARN; the base is off pavement (measured clearance
      > 0, and not ROAD with --blend)
  (h) exactly one record per id, none at a skipped id, no -fwd/-rev twin of a paired post, every
      plate a known geometry (W1-6)
  (i) base spacing: no two posts closer than 2.0 m
  (j) signs.json expect_arrow, where given, equals the placed arrow (never relocate silently) — read
      from signs.json HERE (not from the record), for the plate's own approach: an entry speaks for
      the forward approach, so on a -rev plate its expect_arrow is mirrored (right <-> left) unless the
      entry's "rev" sub-object names one; a record whose own expect_arrow disagrees fails too
  (k) direction coverage (ledger 0051), MAINLINE: the driven directions are read from
      <project>/track.config.json layouts[].direction (forward -> fwd, reverse -> rev; no layouts =
      forward only). Every mainline corner with a plate in one driven direction has a plate in every
      other, or a skip record in that direction EVERY one of whose reasons is either the rule finding no
      arrow corner on that approach (RULE_SKIP_RES: R_apex / |D| / mouth flare / the ray never leaving
      pavement, leaving it out of range, ending at a T, or landing outside [PC, PT] — the corner's own
      geometry, as place_signs words it) or a signs.json skip with a non-empty reason that signs.json
      itself (when read) still makes for that approach. Never coverage: a skip caused by expect_arrow,
      a placement that failed (OUTSIDE ASSERTION, base ON pavement, obstacle disc, lamp clearance — the
      rule wanted an arrow there), a reasonless signs.json skip, a hairpin's second arrow, and a
      direction with no record at all (v0.17.1: race_acw drove the lap anticlockwise past six plates
      that all faced the clockwise approach, and every check passed).
  (l) named corners stay signed (v0.18.0 integration; the 0051 verifier's gap): (k) only judges a corner
      that still has a plate somewhere, so a corner that lost EVERY plate (both M4 plates failing mesh
      placement after 0050 reshaped the Navajo/Jackson curb, or both records gone) passed. Every corner
      signs.json names and does not skip outright must keep at least one plate; a MAINLINE one a plate in
      every driven direction unless signs.json skips that approach with a reason (a rule reason does not
      cover a named corner); a side-street one a plate in each approach or a skip there that (k) would
      count as coverage.
  (m) layout coverage (ledger 0054 P4): per LAYOUT of track.config.json, in the direction it drives, every
      MAINLINE corner with a plate anywhere has a plate THAT layout loads — a shared plate (the road kn5) or
      its own LAYOUT PLATE (id <corner>-<dir>@<layout>, built into its closure kn5) — or a skip record for
      that direction that applies to it (a shared skip, or one carrying its layout id) whose reasons (k)
      counts as coverage. A plate for another layout is never this one's (v0.19.0: M3 / M4 skipped in every
      layout; the Speedways turn at J1 / J5 and had no arrow).
  LAYOUT PLATES (ledger 0054 P4): a record with "layout" is measured against the walls that layout loads
      (the scan: tools/signs_mesh.load_wall_bvhs[token], the common curb strips + its closure): (c) is its
      clearance to that wall, 1.3-3.0 m (the wall's far face stands in for the curb face; polyline-only: the
      MAINLINE lip distance minus the declared strip offset, from the record's own wall params), (e)/(f) use
      the deck under it (the highest of ROAD / ground: it stands on the sealed opening's road), (g) demands
      the MAINLINE disc only and allows ROAD under it, and it must stand on no wall. (i) spacing is judged
      only between posts a layout can load together.
  NORTH RIBBON (ledger 0054 P4): a record on ribbon "north" is re-derived on the same stitched line the
      rule scanned (tools/expansion_lines.centre_ribbon, rebuilt HERE from the connectors), as a CONNECTOR
      post; its gated discs are the MAINLINE's and the two north drive lines' (expansion_lines.compute_lines,
      rebuilt here too).
  plus blender.normal_mismatches == 0, every post >= 0.5 m from every 1WALL* face (the scan), and no race
  furniture (1KERB_RACE / 1WALL_RACE) among the authoring pass's or the scan's ground / road objects (ledger
  0051: the signs ship in the road kn5 the street layout loads, the race kerbs do not; measuring a post
  against one moved approved posts up to 0.319 m with this gate still green).

    python tools/verify_signs.py <project-dir> [--blend PATH] [--blender EXE] [--signs PATH]

--signs PATH names the signs.json (j) reads; default tracks/<slug>/signs.json beside this file (the
place_signs convention). An explicit path that does not exist is a FAIL.

--blend PATH runs the independent scan on that blend (READ ONLY: never saved) by launching Blender
(--blender, else $BLENDER, else the BL= line of tools/ship_sd.sh) on this very file with
--measure-out; the measurement lands in data/signs_measured.json. Without --blend the scan column
reads "-", (b)/(e)/(f) rest on the recorded vertices and a PASS is printed as
"PASS polyline-only (not authoritative)".
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import expansion_lines as el  # noqa: E402  (the stitched north ribbon + the drive lines, rebuilt here)

HALF_PLATE = 0.61
FACE_TOL_DEG = 1.0
CLEAR_RANGE = {"MAINLINE": (1.3, 3.0), "CONNECTOR": (1.0, None), "LAYOUT": (1.3, 3.0)}
WALL_CLEAR_M = 0.5              # every post this far from every 1WALL* face (tools/place_signs.WALL_CLEAR_M, measured here)
LAYOUT_SEP = "@"                # a layout plate's id: <corner>-<dir>@<layout id>
LINE_PREFIX = "expansion_"      # the north drive lines in the field (disc only)
CONNECTOR_TARGET_M = 1.33       # the walk clearance a connector post aims for (WARN when missed)
SCAN_TOL = 0.02
HEIGHT_TOL = 0.05               # --blend: against the ground ray-cast made here
ANALYTIC_TOL = 0.50             # no --blend: against the centreline height + 0.24 (polyline-only)
WALK_ABOVE_ROAD = 0.24
PLATE_HEIGHT = 2.13
POST_SINK = 0.30
SPACING_MIN = 2.0
MEASURED = "signs_measured.json"
GATED = ("MAINLINE",)           # the centrelines drive_test sweeps (scripts/geometry/drive_test.py)
KNOWN_PLATES = ("W1-6",)
STRAIGHT_RAD_PER_M = 1.0 / 60.0
HALF_WIN = 6                    # the rule's 12 m curvature window
NORMAL_CLUSTER_DEG = 2.0
LAYOUT_DIRECTION = {"forward": "fwd", "reverse": "rev"}
ID_RE = re.compile(r"^(?P<base>.+?)(?:-(?P<dir>fwd|rev))?(?P<second>-2)?$")
DIR_RE = re.compile(r"^(?P<base>.+?)(?:-(?P<dir>fwd|rev))?$")


# --- geometry, own code (never place_signs') ------------------------------------------------------
def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def unit(v):
    L = math.hypot(v[0], v[1]) or 1e-12
    return (v[0] / L, v[1] / L)


def seg_dist(q, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
    return math.hypot(q[0] - (a[0] + t * dx), q[1] - (a[1] + t * dz)), t


def poly_dist(q, pts):
    """min distance to a polyline (None when it has < 2 points)"""
    if not pts or len(pts) < 2:
        return None
    return min(seg_dist(q, pts[i], pts[i + 1])[0] for i in range(len(pts) - 1))


class Line:
    """one ribbon's centreline resampled to 1 m stations in the plate's travel order — (x, z, y)"""

    def __init__(self, pts3, closed, reverse=False):
        P = [(p[0], p[2], p[1]) for p in pts3]
        if closed and math.hypot(P[0][0] - P[-1][0], P[0][1] - P[-1][1]) < 1e-6:
            P = P[:-1]
        if reverse:
            P = P[::-1]
        idx = list(range(len(P))) + ([0] if closed else [])
        cum = [0.0]
        for a, b in zip(idx[:-1], idx[1:]):
            cum.append(cum[-1] + math.hypot(P[b][0] - P[a][0], P[b][1] - P[a][1]))
        self.closed, self.L = closed, cum[-1]
        self.n = int(self.L) if closed else int(self.L) + 1
        self.S = []
        j = 0
        for s in range(self.n):
            while j < len(cum) - 2 and cum[j + 1] <= s:
                j += 1
            a, b = P[idx[j]], P[idx[j + 1]]
            f = min(max((s - cum[j]) / max(1e-9, cum[j + 1] - cum[j]), 0.0), 1.0)
            self.S.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f))

    def st(self, i):
        return i % self.n if self.closed else min(max(i, 0), self.n - 1)

    def xz(self, i):
        s = self.S[self.st(i)]
        return (s[0], s[1])

    def y(self, i):
        return self.S[self.st(i)][2]

    def heading(self, i):
        a, b = self.xz(i - 2), self.xz(i + 2)
        return math.atan2(b[1] - a[1], b[0] - a[0])

    def tangent(self, i):
        h = self.heading(i)
        return (math.cos(h), math.sin(h))

    def dheading(self, i, half=HALF_WIN):
        return wrap(self.heading(i + half) - self.heading(i - half))

    def nearest(self, q, lo=None, hi=None):
        """(distance, fractional station) over the stations [lo, hi] (whole line when None)"""
        rng = range(self.n if self.closed else self.n - 1) if lo is None else range(lo, hi + 1)
        best = (float("inf"), 0.0)
        for i in rng:
            if not self.closed and self.st(i + 1) == self.st(i):
                continue
            d, t = seg_dist(q, self.xz(i), self.xz(i + 1))
            if d < best[0]:
                best = (d, i + t)
        return best


class Field:
    """every centreline's segments with widths: the pavement edge and drive_test's obstacle disc,
    min(max(w/2 - 0.4, 0.8), 6) + 0.3 (scripts/geometry/drive_test.py:390/482). Since ledger 0054 P4 also the
    stitched north ribbon (a line to re-derive on, never pavement: its pieces are) and the two north drive lines
    (disc only, never pavement) — both rebuilt here from the connectors, never read from the record."""

    def __init__(self, proj):
        data = Path(proj) / "data"
        self.segs = []
        self.lines = {}
        self.disc_only = set()
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        self._add("MAINLINE", cl["points_xyz_m"], cl["widths_m"], True)
        self.src = {"MAINLINE": (cl["points_xyz_m"], True)}
        cp = data / "connectors.local.json"
        if cp.exists():
            for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
                P = c["points_xyz_m"]
                closed = math.dist(P[0][::2], P[-1][::2]) < 1e-6
                self._add(c["name"], P, c["widths_m"], closed)
                self.src[c["name"]] = (P, closed)
        self.gated = ("MAINLINE",)
        self.polys = []          # the junction pads' BUILT decks (pavement polygons, stub arms included)
        nr = el.centre_ribbon(proj)
        if nr:
            self.src[nr["name"]] = (nr["points_xyz_m"], False)
            lines = el.compute_lines(proj) or {}
            for lname, ln in sorted(lines.items()):
                self._add(LINE_PREFIX + lname, ln["points_xyz_m"], ln["widths_m"], False)
                self.disc_only.add(LINE_PREFIX + lname)
            self.gated = ("MAINLINE",) + tuple(LINE_PREFIX + k for k in sorted(lines))
            for pid, poly, _k in el.pad_polygons(proj):
                xs, zs = [p[0] for p in poly], [p[1] for p in poly]
                self.polys.append(("pad " + pid, [tuple(p) for p in poly], (min(xs), min(zs), max(xs), max(zs))))
        self.cells = {}
        for k, (_, a, b, _, _) in enumerate(self.segs):
            for p in (a, b):
                self.cells.setdefault((int(p[0] // 60), int(p[1] // 60)), set()).add(k)

    def _add(self, name, P, W, closed):
        idx = list(range(len(P))) + ([0] if closed else [])
        for a, b in zip(idx[:-1], idx[1:]):
            self.segs.append((name, (P[a][0], P[a][2]), (P[b][0], P[b][2]), W[a], W[b]))

    def line(self, name, reverse):
        key = (name, reverse)
        if key not in self.lines:
            P, closed = self.src[name]
            self.lines[key] = Line(P, closed, reverse)
        return self.lines[key]

    def _near(self, x, z, names=None, pavement=False):
        cx, cz = int(x // 60), int(z // 60)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    name, a, b, wa, wb = self.segs[k]
                    if names is not None and name not in names:
                        continue
                    if pavement and name in self.disc_only:
                        continue
                    d, t = seg_dist((x, z), a, b)
                    yield d, wa * (1 - t) + wb * t

    def edge(self, x, z, names=None):
        """signed distance to the nearest pavement edge (> 0 = off pavement); names = these ribbons alone (the pad
        decks count as pavement unless names is given)"""
        best = min((d - w / 2 for d, w in self._near(x, z, names, pavement=True)), default=float("inf"))
        if names is None:
            for _name, poly, (x0, z0, x1, z1) in self.polys:
                if x < x0 - best or x > x1 + best or z < z0 - best or z > z1 + best:
                    continue
                dmin = min(seg_dist((x, z), poly[i], poly[(i + 1) % len(poly)])[0] for i in range(len(poly)))
                inside = False
                for i in range(len(poly)):
                    ax, az = poly[i]
                    bx, bz = poly[(i + 1) % len(poly)]
                    if (az > z) != (bz > z) and ax + (z - az) * (bx - ax) / (bz - az) > x:
                        inside = not inside
                best = min(best, -dmin if inside else dmin)
        return best

    def grazing(self, A, t, d_target, cap=6.0, step=0.25, s_max=90.0):
        """does the ray from A along t, once off pavement, stay within d_target of a pavement edge for the whole cap
        past its exit? (the precondition of the mesh stage's square side step) -> (True/False/None, exit s)"""
        s = 0.0
        s_c = None
        while s <= s_max:
            e = self.edge(A[0] + t[0] * s, A[1] + t[1] * s)
            if s_c is None:
                if e > 0:
                    s_c = s
            elif e >= d_target:
                return False, s_c
            elif s - s_c >= cap:
                return True, s_c
            s += step
        return (None, s_c)

    def disc(self, x, z, names=None):
        return min((d - (min(max(w / 2 - 0.4, 0.8), 6.0) + 0.3) for d, w in self._near(x, z, names)), default=float("inf"))

    def footprint(self, base, rights, names=None):
        pts = [tuple(base)]
        for r in rights:
            pts.append((base[0] + r[0] * HALF_PLATE, base[1] + r[1] * HALF_PLATE))
            pts.append((base[0] - r[0] * HALF_PLATE, base[1] - r[1] * HALF_PLATE))
        return min(self.disc(p[0], p[1], names) for p in pts)


# --- the derivations -----------------------------------------------------------------------------------
def chord(line, pc):
    """the 10 m approach chord PC-12..PC-2 (PC..PC+6 at an open ribbon's very start)"""
    a0, a1 = line.xz(pc - 12), line.xz(pc - 2)
    if math.hypot(a1[0] - a0[0], a1[1] - a0[1]) < 1.0:
        a0, a1 = line.xz(pc), line.xz(pc + 6)
    return unit((a1[0] - a0[0], a1[1] - a0[1]))


def approach(line, A):
    """PC = the station the ray origin A is a pure LATERAL offset from — among the stations nearest
    A, the one whose own approach chord is perpendicular to A - P[PC] (a lane-offset point on a
    curve is 0.5 m along the local tangent from its station, so nearest-and-round is ambiguous
    there); t = that chord -> (PC, t, |A - P|)"""
    dA, pcf = line.nearest(A)
    pc0 = int(round(pcf))
    best = None
    for i in range(pc0 - 2, pc0 + 3):
        if not line.closed and (i < 0 or i >= line.n):
            continue
        i = line.st(i)
        t = chord(line, i)
        P = line.xz(i)
        along = abs(t[0] * (A[0] - P[0]) + t[1] * (A[1] - P[1]))
        if best is None or along < best[0]:
            best = (along, i, t)
    _, pc, t = best
    return pc, t, dA


def turn_after(line, pc, max_walk=150):
    """the turn the road makes after PC: (sense, apex, |dheading| deg at the apex) with sense +1 =
    left/CCW, -1 = right, 0 = no turn found. The apex is the max of the 12 m heading window over
    the first curved run after PC (ended by 6 straight stations or a sign flip); the sense is the
    cross product of the 6 m chords either side of it, cross-checked against the window's sign."""
    thr = STRAIGHT_RAD_PER_M * 2 * HALF_WIN
    sense, apex, best, straight = 0, None, 0.0, 0
    for k in range(max_walk):
        i = pc + k
        if not line.closed and i >= line.n:
            break
        dh = line.dheading(i)
        if abs(dh) > thr:
            sg = 1 if dh > 0 else -1
            if sense == 0:
                sense = sg
            if sg != sense:
                break
            straight = 0
            if abs(dh) > best:
                best, apex = abs(dh), i
        elif sense:
            straight += 1
            if straight >= 6:
                break
    if apex is None:
        return 0, None, 0.0
    b0, b1 = line.xz(apex - 10), line.xz(apex - 4)
    c0, c1 = line.xz(apex + 4), line.xz(apex + 10)
    before, after = unit((b1[0] - b0[0], b1[1] - b0[1])), unit((c1[0] - c0[0], c1[1] - c0[1]))
    cr = before[0] * after[1] - before[1] * after[0]
    chord_sense = 1 if cr > 0 else -1
    if chord_sense != sense:
        return 0, apex, math.degrees(best)       # ambiguous: the chords and the window disagree
    return sense, apex, math.degrees(best)


def side_of(line, S, lo, hi):
    """cross(t_local, S - P) at the station nearest S within [lo, hi]: > 0 = S left of travel"""
    d, sf = line.nearest(S, lo, hi)
    i = line.st(int(round(sf)))
    tl, P = line.tangent(i), line.xz(i)
    return tl[0] * (S[1] - P[1]) - tl[1] * (S[0] - P[0]), i, d


def centroid_xz(verts):
    return (sum(v[0] for v in verts) / len(verts), sum(v[2] for v in verts) / len(verts))


def angle_deg(a, b):
    """unsigned angle between two xz vectors, exact for non-unit input (acos(dot) of a vector
    rounded to 4 decimals reads 0.36 deg between parallel vectors)"""
    return abs(math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])))


def plate_normal_from_verts(front, back):
    """the horizontal normal of a recorded plate: perpendicular to its 1.219 m horizontal edge
    (vertices rounded to 0.1 mm give 0.005 deg there), signed toward the front face"""
    r = unit((front[1][0] - front[0][0], front[1][2] - front[0][2]))
    n = (r[1], -r[0])
    fc, bc = centroid_xz(front), centroid_xz(back)
    if n[0] * (fc[0] - bc[0]) + n[1] * (fc[1] - bc[1]) < 0:
        n = (-n[0], -n[1])
    return n


# --- the independent scan (runs inside Blender) ----------------------------------------------------
def cluster_normals(normals, tol_deg=NORMAL_CLUSTER_DEG):
    out = []
    for n in normals:
        for c in out:
            if angle_deg(n, unit(c["sum"])) <= tol_deg:
                c["sum"] = (c["sum"][0] + n[0], c["sum"][1] + n[1])
                c["count"] += 1
                break
        else:
            out.append({"sum": tuple(n), "count": 1})
    return [[round(v, 5) for v in unit(c["sum"])] for c in out]


def walk_behind_scan(sm, ground, x, z, clear, bearing_deg, step=0.05, reach=4.0):
    """how far the base stands behind the back edge of the raised walk between it and the
    nearest built pavement (bearing_deg, from the polar scan): > 0 = on the terrain that far
    behind the walk, < 0 = on the walk, that far inside its back edge; None = no walk level found.
    The walk level is the highest top hit within the 2 m before the pavement edge; a sample is
    'walk' at >= that - 0.04 (the curb-top test tools/author_signs_blend.py uses)."""
    if bearing_deg is None or clear is None or clear <= 0:
        return None
    th = math.radians(bearing_deg)
    ux, uz = math.cos(th), math.sin(th)
    prof = []
    d = 0.0
    while d <= clear:
        prof.append((d, sm.top_hit(ground, x + ux * d, z + uz * d)))
        d += step
    vals = [v for dd, v in prof if v is not None and dd >= clear - 2.0]
    if not vals:
        return None
    h_walk = max(vals)
    g0 = sm.top_hit(ground, x, z)
    if g0 is not None and g0 >= h_walk - 0.04:          # on the walk: outward until the top drops
        d = step
        while d <= reach:
            g = sm.top_hit(ground, x - ux * d, z - uz * d)
            if g is None or g < h_walk - 0.04:
                return round(-d, 2)
            d += step
        return round(-reach, 2)
    for dd, v in prof:                                    # on terrain: inward until the walk starts
        if v is not None and v >= h_walk - 0.04:
            return round(dd, 2)
    return None


def layout_tokens(proj):
    """{layout id: closure token} of the race layouts (track.config.json layouts[].closure_token)"""
    try:
        cfg = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(lo.get("id")): str(lo.get("closure_token") or "").lower()
            for lo in cfg.get("layouts") or [] if isinstance(lo, dict) and lo.get("race_furniture")}


def measure_in_blender(proj, blend, out_path):
    import bpy
    sys.path.insert(0, str(AIROSO / "tools"))
    import signs_mesh as sm
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    road, ground, road_names, ground_names = sm.load_bvhs(skip_prefixes=("SIGN",))
    race_names = list(getattr(sm.load_bvhs, "last_race", []))
    walls = sm.load_wall_bvhs()
    wall_names = dict(sm.load_wall_bvhs.names)
    tokens = layout_tokens(proj)
    d = json.loads((Path(proj) / "data" / "signs.local.json").read_text(encoding="utf-8"))
    # every SIGNPLATE polygon (centre, normal) and every SIGNPLATE / SIGNPOST vertex, world space,
    # in the engine frame (x, y up, z) = Blender (x, z, y)
    plate_polys, plate_verts, post_verts = [], [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        up = ob.name.upper()
        if not up.startswith(("SIGNPLATE", "SIGNPOST")):
            continue
        mw = ob.matrix_world
        vs = [mw @ v.co for v in ob.data.vertices]
        if up.startswith("SIGNPLATE"):
            plate_verts += [(v.x, v.z, v.y) for v in vs]
            rot = mw.to_3x3()
            for poly in ob.data.polygons:
                n = (rot @ poly.normal).normalized()
                c = mw @ poly.center
                plate_polys.append(((c.x, c.z, c.y), (n.x, n.z, n.y)))
        else:
            post_verts += [(v.x, v.z, v.y) for v in vs]
    res = {"blend": str(blend), "road_objects": road_names, "ground_objects": ground_names, "race_excluded": race_names,
           "walls": {k: len(v) for k, v in sorted(wall_names.items())},
           "scan": "5-degree polar, 0.25 m steps, bisected; ROAD top vs CURB/SIDEWALK/TERRAIN top; "
                   "ground = top hit at the base (SIGN* excluded); plate normals = Mesh.polygons[].normal of "
                   "the vertical SIGNPLATE faces within 1.2 m of the post; plate bottom = lowest SIGNPLATE vertex "
                   "0.5-0.75 m off the post axis; post base = lowest SIGNPOST vertex within 0.1 m of it; walk_behind_m = "
                   "the ground profile from the base toward the nearest pavement (> 0 behind the walk, < 0 on it); "
                   "wall_m = the nearest 1WALL* face 0.6 m up the post; a layout plate: layout_wall_m = the nearest face of "
                   "the walls its layout loads (RACE + RACE_CLOSE_<TOKEN>), on_wall = a wall top over the deck at the base, "
                   "ground_y = the highest of ROAD / ground under it",
           "signs": {}}
    for s in d["signs"]:
        x, z = s["base_xz"]
        clear, bearing = sm.polar_clearance(road, ground, x, z)
        g = sm.top_hit(ground, x, z)
        r_top = sm.top_hit(road, x, z)
        wb = walk_behind_scan(sm, ground, x, z, clear, bearing)
        near = [n for c, n in plate_polys if math.hypot(c[0] - x, c[2] - z) < 1.2 and abs(n[1]) < 0.2]
        pb = [v[1] for v in plate_verts if 0.5 <= math.hypot(v[0] - x, v[2] - z) <= 0.75]
        pp = [v[1] for v in post_verts if math.hypot(v[0] - x, v[2] - z) <= 0.1]
        y_ref = g if g is not None else (r_top if r_top is not None else 0.0)
        wd = sm.nearest_dist(walls.get("all"), x, y_ref + 0.6, z)
        rec = {"clear_m": round(clear, 3), "bearing_deg": bearing, "on_road": sm.on_road(road, ground, x, z),
               "ground_y": None if g is None else round(g, 4), "walk_behind_m": wb,
               "wall_m": None if wd == float("inf") else round(wd, 3),
               "plate_normals_xz": cluster_normals([unit((n[0], n[2])) for n in near]),
               "n_plate_faces": len(near),
               "plate_bottom_y": None if not pb else round(min(pb), 4),
               "post_base_y": None if not pp else round(min(pp), 4)}
        if s.get("layout"):
            tok = tokens.get(str(s["layout"]), "")
            wl = walls.get(tok)
            ys = [v for v in (g, r_top) if v is not None]
            deck = max(ys) if ys else None
            wtop = sm.top_hit(wl, x, z) if wl is not None else None
            lw = sm.nearest_dist(wl, x, (deck if deck is not None else 0.0) + 0.6, z)
            rec.update(ground_y=None if deck is None else round(deck, 4), layout_token=tok,
                       layout_walls=len(wall_names.get(tok, [])),
                       layout_wall_m=None if lw == float("inf") else round(lw, 3),
                       on_wall=bool(wtop is not None and (deck is None or wtop > deck + 0.05)))
        res["signs"][s["id"]] = rec
    Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("[verify-signs] measured %d bases in Blender -> %s" % (len(res["signs"]), out_path))


def blender_exe(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    ship = AIROSO / "tools" / "ship_sd.sh"
    if ship.exists():
        m = re.search(r'^BL="([^"]+)"', ship.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return "blender"


def run_blender_measure(proj, blend, exe):
    out_path = Path(proj) / "data" / MEASURED
    out_path.unlink(missing_ok=True)
    cmd = [exe, "--background", "--python-exit-code", "1", "--python", str(Path(__file__).resolve()), "--",
           str(proj), "--blend", str(blend), "--measure-out", str(out_path)]
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("[verify-signs]") or "Error" in ln or "Traceback" in ln]
    if r.returncode != 0 or not out_path.exists():
        return None, "blender exit %d, %s: %s" % (r.returncode, "no " + MEASURED if not out_path.exists() else "output", " | ".join(tail[-4:]))
    return json.loads(out_path.read_text(encoding="utf-8")), " | ".join(tail[-1:])


# --- (j) and (k): what signs.json and track.config.json say, read here ------------------------------------
def split_layout(cid):
    """('M3-fwd', 'race_cw') for a layout plate's id (ledger 0054 P4), (cid, None) otherwise"""
    if LAYOUT_SEP in cid:
        core, lid = cid.split(LAYOUT_SEP, 1)
        return core, lid
    return cid, None


def parse_id(cid, second=None):
    """(corner base id, direction suffix or None, second-arrow flag): M2-fwd-2 -> (M2, fwd, True);
    M2-2 -> (M2, None, True); MED-6-rev -> (MED-6, rev, False); M-c5 -> (M-c5, None, False);
    M3-fwd@race_cw -> (M3, fwd, False) (a layout plate's layout is split_layout's).
    A bare trailing "-2" is ambiguous (M2-2 = M2's hairpin second arrow, DCL-2 = a merged connector
    post): pass `second` (the record's corner.second_arrow, or for a skip whether the id minus "-2"
    was placed) and only a real second arrow loses its "-2". second=None = the id's shape alone."""
    cid, _lid = split_layout(cid)
    if second is not None:
        core = cid[:-2] if second and cid.endswith("-2") else cid
        m = DIR_RE.match(core)
        return m.group("base"), m.group("dir"), bool(second)
    m = ID_RE.match(cid)
    return m.group("base"), m.group("dir"), bool(m.group("second"))


def plate_second(p, s=None):
    """a placed plate's own second-arrow flag (None when the record predates it)"""
    v = (p.get("corner") or (s or {}).get("corner") or {}).get("second_arrow")
    return None if v is None else bool(v)


# (k): the reasons that mean the RULE found no arrow corner on this approach — the corner's own
# geometry (R / D / mouth flare / where the ray lands), not a placement that failed. Worded as
# tools/place_signs.py words them; any other reason (expect_arrow, OUTSIDE ASSERTION, ON pavement,
# obstacle disc, lamp clearance, a hairpin's second arrow) is never coverage.
RULE_SKIP_RES = tuple(re.compile(r) for r in (
    r"^R_apex [\d.]+ > [\d.]+ m$",
    r"^\|D\| [\d.]+ < [\d.]+ deg$",
    r"^apex \d+ m from .+ \(< \d+ m: mouth-flare geometry\)$",
    r"^ray never leaves pavement within \d+ m \(through leg / junction\)$",
    r"^ray exits pavement at [\d.]+ m \(want \d+-\d+\)$",
    r"^T-end: ray re-enters .+ within 3 m of the curb \(W1-7 candidate, second pass\)$",
    r"^ray foot at station PC[+-]\d+ is outside \[PC, PT\+[\d.]+\] \(a curve, not a turn\)$",
    r"^ray runs \d+ m down .+ before leaving pavement \(a through road\)$",     # ledger 0054 P4
    r"^no race declaration \(data/barrier_bands\.json params\): .*$",         # a layout plate with no walls to stand behind
))
SIGNS_JSON_SKIP_RE = re.compile(r"^signs\.json skip: (?P<reason>.*)$")


def entry_skip_reason(entry, direction):
    """the reason signs.json gives for skipping ONE approach (its sub-object over the entry), or None
    when that approach is not skipped there or the skip carries no reason"""
    if not entry:
        return None
    sub = entry.get(direction or "fwd") or {}
    skip = sub["skip"] if "skip" in sub else entry.get("skip")
    reason = sub["reason"] if "reason" in sub else entry.get("reason")
    if not skip or not isinstance(reason, str) or not reason.strip() or reason.strip() == "(no reason given)":
        return None
    return reason.strip()


def coverage_reason(r, entry, direction):
    """(counts as coverage, why not). A rule reason, or a signs.json skip that carries a real reason —
    and, when signs.json was read, one that signs.json itself still makes for this approach."""
    if any(rx.match(r) for rx in RULE_SKIP_RES):
        return True, None
    m = SIGNS_JSON_SKIP_RE.match(r)
    if m:
        why = m.group("reason").strip()
        if not why or why == "(no reason given)":
            return False, "a signs.json skip with no reason"
        if entry is not False and entry_skip_reason(entry, direction) is None:
            return False, "a signs.json skip that signs.json does not make (with a reason) for this approach"
        return True, None
    if "expect_arrow" in r:
        return False, "skipped by expect_arrow, not by the rule"
    return False, "a placement that failed, not the rule finding no corner"


def mirror(a):
    return {"left": "right", "right": "left"}.get(a, a)


def signs_json_path(proj, explicit=None):
    """the signs.json (j) reads: --signs, else tracks/<slug>/signs.json (dashed slug first) beside
    this file; None when the track has none"""
    if explicit:
        return Path(explicit)
    try:
        slug = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8")).get("slug", "")
    except Exception:
        slug = ""
    for cand in (slug.replace("_", "-"), slug):
        if cand and (AIROSO / "tracks" / cand / "signs.json").exists():
            return AIROSO / "tracks" / cand / "signs.json"
    return None


def load_entries(path):
    if path is None:
        return {}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in (d.get("corners") or {}).items() if not k.startswith("_") and isinstance(v, dict)}


def expected_arrow(entry, direction):
    """the arrow signs.json demands of ONE approach: the entry's per-approach sub-object first,
    else its expect_arrow — which names the FORWARD approach, so a -rev plate expects the mirror"""
    if not entry:
        return None
    sub = entry.get(direction or "fwd") or {}
    if sub.get("expect_arrow") in ("left", "right"):
        return sub["expect_arrow"]
    e = entry.get("expect_arrow")
    if e not in ("left", "right"):
        return None
    return mirror(e) if direction == "rev" else e


def driven_directions(proj):
    """{"fwd": [layout ids], "rev": [...]} from <proj>/track.config.json layouts[].direction; no
    layouts = forward only. An unknown direction word raises ValueError (a FAIL, never a guess)."""
    try:
        cfg = json.loads((Path(proj) / "track.config.json").read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    out = {}
    for lay in cfg.get("layouts") or []:
        if lay.get("lap") not in (None, ""):
            continue    # ledger 0054 Phase 2: a layout on its own lap drives no MAINLINE corner (place_signs.race_layouts)
        word = str(lay.get("direction") or "forward").lower()       # absent / null = forward (the older configs)
        if word not in LAYOUT_DIRECTION:
            raise ValueError("layout %s: direction %r is not forward / reverse" % (lay.get("id"), lay.get("direction")))
        out.setdefault(LAYOUT_DIRECTION[word], []).append(str(lay.get("id")))
    return out or {"fwd": ["(no layouts: forward)"]}


def direction_coverage(d, driven, ribbon="MAINLINE", entries=None):
    """check (k): -> (fails, rows). See the module doc. entries = signs.json's corners as read by
    this gate (None: not read; a "signs.json skip" then counts only on its non-empty reason)."""
    fails, rows = [], []
    dirs = sorted(driven)
    plates, skips = {}, {}
    placed = {s["id"] for s in d["signs"]} | {p["id"] for s in d["signs"] for p in (s.get("plates") or []) if "id" in p}
    for s in d["signs"]:
        if s["ribbon"] != ribbon:
            continue
        for p in s.get("plates") or [s]:
            base, _, _ = parse_id(p["id"], plate_second(p, s))
            plates.setdefault(base, {}).setdefault(p["direction"], []).append(p["id"])
    for sk in d["skipped"]:
        if sk["ribbon"].split("(")[0] != ribbon:
            continue
        # a skipped hairpin second arrow is "<placed id>-2"; any other trailing -2 is the corner's own name
        base, _, second = parse_id(sk["id"], sk["id"].endswith("-2") and sk["id"][:-2] in placed)
        if second:
            continue                        # a hairpin's second arrow is the rule's extra, never coverage
        direction = "rev" if sk["ribbon"].endswith("(rev)") else "fwd"
        skips.setdefault(base, {}).setdefault(direction, []).extend(sk["reasons"])
    who = lambda dr: "%s (%s)" % (dr, ", ".join(driven.get(dr, [])))
    if len(dirs) < 2:
        rows.append("(k) one driven direction, %s: nothing to cover" % who(dirs[0]))
        return fails, rows
    for base in sorted(plates):
        have = plates[base]
        for want in dirs:
            if want in have:
                continue
            rs = skips.get(base, {}).get(want)
            got = "/".join("%s %s" % (dr, ",".join(have[dr])) for dr in sorted(have))
            if rs is None:
                fails.append("k_direction_coverage: %s corner %s has a plate %s but no record at all for %s — that "
                             "approach was never signed" % (ribbon, base, got, who(want)))
                continue
            entry = False if entries is None else entries.get(base)
            judged = [(r,) + coverage_reason(r, entry, want) for r in rs]
            bad = ["%s (%s)" % (r, why) for r, ok, why in judged if not ok]
            if not rs or bad:
                fails.append("k_direction_coverage: %s corner %s has a plate %s but the %s approach was skipped by "
                             "reasons that are not the rule's own: %s" % (ribbon, base, got, who(want), "; ".join(bad) or "(no reasons)"))
            else:
                rows.append("(k) %s %s: no plate for %s — covered by its skip: %s" % (ribbon, base, who(want), "; ".join(rs)))
    n = {dr: sum(len(v.get(dr, [])) for v in plates.values()) for dr in dirs}
    rows.append("(k) %s plates by approach: %s; %d corners signed" % (ribbon, ", ".join("%d %s" % (n[dr], who(dr)) for dr in dirs), len(plates)))
    return fails, rows


def named_coverage(d, driven, entries):
    """check (l) (0051 verify finding, integration v0.18.0): every corner signs.json NAMES and does not skip outright
    stays signed. (k) only judges corners that still have a plate in some direction, so a geometry change that cost
    a corner EVERY plate (0050's reshaped Navajo/Jackson curb dropping M4-fwd and M4-rev as 'ON pavement', or both
    records vanishing) passed with every gate green. Here, per named corner:
      - at least one plate, always;
      - MAINLINE: a plate in every DRIVEN direction (track.config.json layouts[].direction), or a signs.json skip of
        that approach with a reason — a rule reason does not cover a corner Kevin named (the rule losing it is
        exactly the silent loss this check exists for);
      - any other ribbon (two-way side streets, both approaches signed): a plate in each approach, or a skip record
        there whose every reason is coverage as (k) words it (coverage_reason).
    -> (fails, rows). entries None (signs.json not read) -> nothing to check, said so."""
    fails, rows = [], []
    if entries is None:
        rows.append("(l) signs.json not read: named corners not checked")
        return fails, rows
    placed = {s["id"] for s in d["signs"]} | {p["id"] for s in d["signs"] for p in (s.get("plates") or []) if "id" in p}
    plates, skips = {}, {}
    for s in d["signs"]:
        for p in s.get("plates") or [s]:
            base, _, _ = parse_id(p["id"], plate_second(p, s))
            plates.setdefault(base, {}).setdefault(p.get("direction") or "fwd", []).append(p["id"])
    for sk in d["skipped"]:
        base, _, second = parse_id(sk["id"], sk["id"].endswith("-2") and sk["id"][:-2] in placed)
        if second:
            continue
        direction = "rev" if sk["ribbon"].endswith("(rev)") else "fwd"
        skips.setdefault(base, {}).setdefault(direction, []).extend(sk.get("reasons") or [])
    mainline_dirs = sorted(driven)
    checked = 0
    for base in sorted(entries):
        e = entries[base]
        if e.get("skip"):
            continue                        # skipped outright by signs.json (place_signs refuses one without a reason)
        checked += 1
        have = plates.get(base, {})
        ribbon = str(e.get("ribbon") or "")
        if not have:
            why = "; ".join("%s: %s" % (dr, ", ".join(rs) or "(no reasons)") for dr, rs in sorted(skips.get(base, {}).items()))
            fails.append("l_named_corner: signs.json names %s (%s%s) and does not skip it, but it has NO plate in any "
                         "direction — %s" % (base, ribbon, (", " + e["where"]) if e.get("where") else "",
                                              ("skipped: " + why) if why else "no record at all"))
            continue
        want = mainline_dirs if ribbon == "MAINLINE" else ["fwd", "rev"]
        for dr in want:
            if dr in have:
                continue
            if ribbon == "MAINLINE":
                if entry_skip_reason(e, dr) is not None:
                    rows.append("(l) %s: no %s plate — signs.json skips that approach: %s" % (base, dr, entry_skip_reason(e, dr)))
                else:
                    rs = skips.get(base, {}).get(dr)
                    fails.append("l_named_corner: MAINLINE corner %s (named in signs.json) has no plate for %s (%s) — %s"
                                 % (base, dr, ", ".join(driven.get(dr, [])),
                                    ("skipped: " + "; ".join(rs)) if rs else "no record at all"))
                continue
            rs = skips.get(base, {}).get(dr)
            if rs is None:
                fails.append("l_named_corner: %s corner %s (named in signs.json) has no %s plate and no record for that "
                             "approach" % (ribbon, base, dr))
                continue
            bad = ["%s (%s)" % (r, why) for r in rs for ok, why in [coverage_reason(r, e, dr)] if not ok]
            if not rs or bad:
                fails.append("l_named_corner: %s corner %s (named in signs.json): the %s approach was skipped by reasons "
                             "that are not the rule's own: %s" % (ribbon, base, dr, "; ".join(bad) or "(no reasons)"))
            else:
                rows.append("(l) %s: no %s plate — covered by its skip: %s" % (base, dr, "; ".join(rs)))
    rows.append("(l) %d named corners (signs.json, not skipped) checked: every one signed" % checked
                if not fails else "(l) %d named corners checked" % checked)
    return fails, rows


def layout_coverage(d, driven, entries):
    """check (m) (ledger 0054 P4): per layout, in the direction it drives, every MAINLINE corner with a plate anywhere
    has a plate THAT layout loads — shared (no "layout") or its own (record.layout == the id) — or a skip record for
    that direction that applies to it (shared, or carrying its id) whose reasons are coverage as (k) words them.
    -> (fails, rows). driven = {direction: [layout ids]} (driven_directions)."""
    fails, rows = [], []
    placed = {s["id"] for s in d["signs"]} | {p["id"] for s in d["signs"] for p in (s.get("plates") or []) if "id" in p}
    plates, skips = {}, {}
    for s in d["signs"]:
        if s["ribbon"] != "MAINLINE":
            continue
        for p in s.get("plates") or [s]:
            base, _, _ = parse_id(p["id"], plate_second(p, s))
            plates.setdefault(base, {}).setdefault(p["direction"], []).append((p["id"], s.get("layout")))
    for sk in d["skipped"]:
        if sk["ribbon"].split("(")[0] != "MAINLINE":
            continue
        base, _, second = parse_id(sk["id"], sk["id"].endswith("-2") and sk["id"][:-2] in placed)
        if second:
            continue
        direction = "rev" if sk["ribbon"].endswith("(rev)") else "fwd"
        skips.setdefault(base, {}).setdefault(direction, []).append((sk.get("layout"), list(sk.get("reasons") or [])))
    by_layout = {}
    for base in sorted(plates):
        for dr, lids in sorted(driven.items()):
            for lid in lids:
                mine = [pid for pid, lay in plates[base].get(dr, []) if lay is None or lay == lid]
                if mine:
                    by_layout.setdefault(lid, []).append("%s %s" % (base, "/".join(mine)))
                    continue
                entry = False if entries is None else entries.get(base)
                cov = [rs for lay, rs in skips.get(base, {}).get(dr, []) if lay is None or lay == lid]
                if not cov:
                    others = [pid for pid, lay in plates[base].get(dr, []) if lay not in (None, lid)]
                    fails.append("m_layout_coverage: layout %s (%s) loads no plate of MAINLINE corner %s and has no skip record for "
                                 "that approach%s" % (lid, dr, base, (" — only other layouts' plates %s" % ", ".join(others)) if others else ""))
                    continue
                bad = ["%s (%s)" % (r, why) for rs in cov for r in rs for ok, why in [coverage_reason(r, entry, dr)] if not ok]
                if bad:
                    fails.append("m_layout_coverage: layout %s (%s) loads no plate of MAINLINE corner %s and its skip is not the rule's own: %s"
                                 % (lid, dr, base, "; ".join(bad)))
                else:
                    by_layout.setdefault(lid, []).append("%s skipped (%s)" % (base, "; ".join(r for rs in cov for r in rs)[:90]))
    for lid in sorted(by_layout):
        rows.append("(m) layout %s: %s" % (lid, "; ".join(by_layout[lid])))
    if not plates:
        rows.append("(m) no MAINLINE plate: nothing to cover per layout")
    return fails, rows


def race_ground(d, measured):
    """names of race furniture the authoring pass or the scan measured as ground / road (must be none)"""
    sys.path.insert(0, str(AIROSO / "tools"))
    import signs_mesh as sm
    bad = []
    for src, rec in (("authoring", d.get("blender") or {}), ("scan", measured or {})):
        for key in ("ground_objects", "road_objects"):
            bad += ["%s %s: %s" % (src, key, n) for n in rec.get(key, []) if sm.is_race_furniture(n)]
    return bad


# --- the gate ------------------------------------------------------------------------------------------
def check_sign(s, field, measured, ids, skipped_ids, warns, entries=None):
    """-> (checks dict, row string, fails list)"""
    plates = s.get("plates") or [s]
    S = tuple(s["base_xz"])
    c = s["checks"]
    tol_a = HALF_PLATE + (s.get("pair_split_m", 0.0) / 2 if s.get("pair") else 0.0)
    layout = s.get("layout")
    kind = "LAYOUT" if layout else ("MAINLINE" if s["ribbon"] == "MAINLINE" else "CONNECTOR")
    lo, hi = CLEAR_RANGE[kind]
    # the discs a gate enforces: every centreline for a mainline post; the MAINLINE alone for a layout plate (its
    # race layout's drive_test sweeps the mainline and every side street is sealed); the swept lines for the rest
    gated = None if kind == "MAINLINE" else (("MAINLINE",) if kind == "LAYOUT" else field.gated)
    meas = (measured or {}).get("signs", {}).get(s["id"]) if measured else None
    bl = s.get("blender") or {}
    rec_plates = bl.get("plates") or []
    # (a) (b) (d) (j) per plate — everything from the centreline, the ray origin and the vertices
    lat_max, ang_max, outside_min, expect_ok, turn_ok, arrow_ok = 0.0, 0.0, float("inf"), True, True, True
    b_src, notes = "-", []
    for k, p in enumerate(plates):
        line = field.line(s["ribbon"], p["direction"] == "rev")
        A = tuple(p["ray"]["A_xz"])
        pc, t, dA = approach(line, A)
        nR = (t[1], -t[0])
        slid = p.get("checks", c).get("slid_m", c.get("slid_m", 0.0))
        u = p.get("curb_dir_xz", s.get("curb_dir_xz", [0.0, 0.0]))
        S0 = (S[0] - u[0] * slid, S[1] - u[1] * slid)
        along = t[0] * (S0[0] - A[0]) + t[1] * (S0[1] - A[1])
        lat = abs(t[0] * (S0[1] - A[1]) - t[1] * (S0[0] - A[0]))
        # a recorded square side step (the mesh stage's grazing-exit fallback) widens (a) only when THIS gate's own
        # ray confirms the grazing exit on its own field: off pavement, the ray stays under the clearance target for
        # the whole cap; an unconfirmed step is a plate the ray does not hit
        step_m = float(p.get("checks", c).get("lateral_step_m", c.get("lateral_step_m", 0.0)) or 0.0)
        if step_m > 0.0 and kind != "LAYOUT":
            target = 1.33 if kind == "CONNECTOR" else 1.63
            graz, _sc = field.grazing(A, t, target)
            if graz:
                tol_a += step_m + 0.1
                notes.append("square side step %.2f m (grazing exit confirmed)" % step_m)
            else:
                notes.append("square side step %.2f m NOT confirmed (the ray clears %.2f m within the cap)" % (step_m, target))
        lat_max = max(lat_max, lat if along > 0 else float("inf"))
        # (b) the real normal
        want = (-t[0], -t[1])
        if meas and meas.get("plate_normals_xz"):
            normals = meas["plate_normals_xz"]
            ang = min(angle_deg(tuple(n), want) for n in normals)
            b_src = "scan"
            if len(normals) != len(plates):
                ang = float("inf")
                notes.append("%d distinct plate normals in the mesh for %d plates" % (len(normals), len(plates)))
        elif k < len(rec_plates):
            n = plate_normal_from_verts(rec_plates[k]["front_xyz"], rec_plates[k]["back_xyz"])
            ang = angle_deg(n, want)
            b_src = "verts"
        else:
            ang = angle_deg(tuple(p["face_dir_xz"]), want)      # analytic record: the recorded facing vs OUR t
            b_src = "record"
        ang_max = max(ang_max, ang)
        # the arrow glyph: its tip (vertex 0) lies to the driver's right of the plate centre for a
        # right arrow — measured from the vertices (the glyph as seen from the approach)
        if k < len(rec_plates):
            tip = rec_plates[k]["arrow_xyz"][0]
            fc = centroid_xz(rec_plates[k]["front_xyz"])
            side = (tip[0] - fc[0]) * nR[0] + (tip[2] - fc[1]) * nR[1]
            if (side > 0) != (p["arrow"] == "right"):
                arrow_ok = False
        # (d) the turn, re-derived, and the base's side of the road at the station nearest it
        sense, apex, dh = turn_after(line, pc)
        if sense == 0:
            outside_min = min(outside_min, float("-inf"))
            notes.append("no unambiguous turn after PC %d" % pc)
        else:
            cross, s_near, _ = side_of(line, S, pc - 5, (apex if apex is not None else pc) + 80)
            outside_min = min(outside_min, -sense * cross)       # > 0 = outside of the derived turn
            derived = "right" if sense < 0 else "left"
            if derived != p["arrow"] and not any(a.startswith("arrow=") for a in p.get("overrides_applied", s.get("overrides_applied", []))):
                turn_ok = False
                notes.append("turn derived %s (apex %d, %.0f deg/12 m) but the plate carries a %s arrow" % (derived, apex, dh, p["arrow"]))
        if entries is None:                 # no signs.json read: the record's own claim (old behaviour)
            if p.get("expect_arrow") in ("left", "right") and p["expect_arrow"] != p["arrow"]:
                expect_ok = False
        else:
            base, _, _ = parse_id(p.get("id", s["id"]), plate_second(p, s))
            exp = expected_arrow(entries.get(base), p["direction"])
            if exp is not None and exp != p["arrow"]:
                expect_ok = False
                notes.append("signs.json %s expects a %s arrow on the %s approach, the plate carries %s" % (base, exp, p["direction"], p["arrow"]))
            if (p.get("expect_arrow") or None) != exp:
                expect_ok = False
                notes.append("the record's expect_arrow %s != signs.json's %s for %s" % (p.get("expect_arrow"), exp, p["direction"]))
    # (c) measured two ways
    edge = (s.get("built") or {}).get("outside_edge_xz")
    clear_poly = poly_dist(S, edge) if edge else None
    clear_bvh = meas["clear_m"] if meas else None
    if kind == "LAYOUT":
        # a layout plate's clearance is to its layout's sealing wall: the scan's nearest wall face, else the
        # analytic one from the MAINLINE lip and the record's declared strip offset (not the record's own measure)
        clear_bvh = meas.get("layout_wall_m") if meas else None
        wl = s.get("wall") or {}
        off = float(wl.get("edge_centre_from_lip_m", 0.0)) + float(wl.get("barrier_half_m", 0.0))
        clear_poly = field.edge(S[0], S[1], ("MAINLINE",)) - off
    clears = [v for v in (clear_poly, clear_bvh) if v is not None]
    analytic_only = not clears
    if analytic_only:
        clears = [c["edge_clear_m"]]
    c_ok = all(v >= lo - SCAN_TOL and (hi is None or v <= hi) for v in clears)
    if measured and not meas:
        c_ok = False
    clear_min = min(clears)
    if kind == "CONNECTOR" and clear_min < CONNECTOR_TARGET_M - SCAN_TOL:
        warns.append("%s: built-edge clearance %.2f m under the %.2f m walk target (passes the %.1f m gate minimum)" % (s["id"], clear_min, CONNECTOR_TARGET_M, lo))
    walk_behind_rec = c.get("walk_behind_m")                  # the authoring pass's ray profile
    walk_behind_scan_m = meas.get("walk_behind_m") if meas else None   # measured here, with --blend
    # (e) (f)
    e_ok = f_ok = None
    ef_src = "n/a"
    if meas and meas.get("ground_y") is not None and meas.get("plate_bottom_y") is not None and meas.get("post_base_y") is not None:
        g = meas["ground_y"]
        e_ok = abs(meas["plate_bottom_y"] - (g + PLATE_HEIGHT)) <= HEIGHT_TOL
        f_ok = abs(meas["post_base_y"] - (g - POST_SINK)) <= HEIGHT_TOL
        ef_src = "mesh vs ground ray-cast %.2f" % g
    elif rec_plates and bl.get("post"):
        line = field.line(s["ribbon"], plates[0]["direction"] == "rev")
        _, sf = line.nearest(S)
        y_an = line.y(int(round(sf))) + WALK_ABOVE_ROAD
        plate_bottom = min(v[1] for e in rec_plates for v in e["front_xyz"])
        post_base = min(v[1] for v in bl["post"]["post_base_xyz"])
        e_ok = abs(plate_bottom - (y_an + PLATE_HEIGHT)) <= ANALYTIC_TOL
        f_ok = abs(post_base - (y_an - POST_SINK)) <= ANALYTIC_TOL
        ef_src = "verts vs centreline+0.24 analytic %.2f, +-%.2f (polyline-only)" % (y_an, ANALYTIC_TOL)
    elif measured:
        e_ok = f_ok = False
        ef_src = "mesh: no SIGN* vertices found at the post"
    # (g)
    disc_all = field.footprint(S, [p["right_xz"] for p in plates])
    disc_gated = field.footprint(S, [p["right_xz"] for p in plates], gated)
    on_road = bool(meas and meas.get("on_road"))
    if kind == "CONNECTOR" and disc_all < 0:
        warns.append("%s: plate footprint %.2f m inside the obstacle disc of a connector centreline (not gated: drive_test sweeps the mainline only)" % (s["id"], -disc_all))
    # a layout plate may stand on the sealed opening's ROAD (behind the wall), never on a wall; every post clear of
    # every 1WALL* face (the scan; a record without a scan is judged on its own wall_m, labelled)
    on_wall = bool(meas and meas.get("on_wall"))
    wall_m = meas.get("wall_m") if meas else c.get("wall_m")
    wall_ok = None if wall_m is None else wall_m >= WALL_CLEAR_M - SCAN_TOL
    if measured and meas and kind == "LAYOUT" and not meas.get("layout_walls"):
        notes.append("the scan found no wall for layout %s (token %r)" % (layout, meas.get("layout_token")))
        wall_ok = False
    twins = [i for i in ids if s.get("pair") and i in (s["id"] + "-fwd", s["id"] + "-rev")]
    checks = {
        "a_ray_hits_plate": lat_max <= tol_a,
        "b_faces_approach": ang_max <= FACE_TOL_DEG and arrow_ok,
        "c_built_edge_clearance": c_ok,
        "d_outside": outside_min > 0 and turn_ok,
        "e_plate_height": e_ok,
        "f_post_sunk": f_ok,
        "g_gate_disc": disc_gated >= 0 and clear_min > 0 and (kind == "LAYOUT" or not on_road) and not on_wall,
        "h_unique_id": ids.count(s["id"]) == 1 and s["id"] not in skipped_ids and not twins
                       and all(p.get("plate", s.get("plate")) in KNOWN_PLATES for p in plates),
        "j_expect_arrow": expect_ok,
        "w_wall_clear": wall_ok,
    }
    bad = [k for k, v in checks.items() if v is False]
    row = ("[verify-signs] %-11s %-12s ray-lat %.2f m (slid %+.2f)  face-err %.2f deg (%s)  %s: poly %s / scan %s m%s  "
           "outside %+.1f  disc %+.2f (gated %+.2f)  walk-behind rec %s / scan %s  wall %s  e/f: %s  %s"
           % (s["id"], s["kind"], lat_max, c.get("slid_m", 0.0), ang_max, b_src, "wall" if kind == "LAYOUT" else "edge",
              "-" if clear_poly is None else "%.2f" % clear_poly, "-" if clear_bvh is None else "%.2f" % clear_bvh,
              " (analytic %.2f)" % c["edge_clear_m"] if analytic_only else "", outside_min, disc_all, disc_gated,
              "-" if walk_behind_rec is None else "%+.2f" % walk_behind_rec,
              "-" if walk_behind_scan_m is None else "%+.2f" % walk_behind_scan_m,
              "-" if wall_m is None else "%.2f" % wall_m, ef_src,
              "FAIL " + ", ".join(bad) + ("; " + "; ".join(notes) if notes else "") if bad else "ok" + ("; " + "; ".join(notes) if notes else "")))
    return checks, row, (["%s: %s" % (s["id"], ", ".join(bad))] if bad else []), {
        "clear_m": clear_min, "walk_behind_rec_m": walk_behind_rec, "walk_behind_scan_m": walk_behind_scan_m,
        "disc_m": disc_all, "disc_gated_m": disc_gated}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    blend = argv[argv.index("--blend") + 1] if "--blend" in argv else None
    if "--measure-out" in argv:
        measure_in_blender(proj, blend, argv[argv.index("--measure-out") + 1])
        return
    d = json.loads((proj / "data" / "signs.local.json").read_text(encoding="utf-8"))
    pre_fails = []
    sj = signs_json_path(proj, argv[argv.index("--signs") + 1] if "--signs" in argv else None)
    entries = {}
    if sj is not None and not sj.exists():
        pre_fails.append("--signs %s: no such file" % sj)
    elif sj is not None:
        entries = load_entries(sj)
    measured, note = None, ""
    if blend:
        measured, note = run_blender_measure(proj, blend, blender_exe(argv[argv.index("--blender") + 1] if "--blender" in argv else None))
    field = Field(proj)
    fails, rows, warns = list(pre_fails), [], []
    signs = d["signs"]
    ids = [s["id"] for s in signs]
    skipped_ids = {s["id"] for s in d["skipped"]}
    if blend and measured is None:
        fails.append("blender measurement did not run (%s)" % note)
    for s in signs:
        _, row, fl, _ = check_sign(s, field, measured, ids, skipped_ids, warns, entries)
        rows.append(row)
        fails += fl
    # (i) spacing across every pair of posts a layout can load together (two layouts' own plates never meet)
    for i in range(len(signs)):
        for j in range(i + 1, len(signs)):
            la, lb = signs[i].get("layout"), signs[j].get("layout")
            if la and lb and la != lb:
                continue
            dd = math.dist(signs[i]["base_xz"], signs[j]["base_xz"])
            if dd < SPACING_MIN:
                fails.append("%s / %s: i_spacing %.2f m < %.1f" % (signs[i]["id"], signs[j]["id"], dd, SPACING_MIN))
    dup_skipped = sorted({i for i in skipped_ids if sum(1 for s in d["skipped"] if s["id"] == i) > 1})
    if dup_skipped:
        fails.append("skipped ids repeat: %s" % ", ".join(dup_skipped))
    if "blender" in d and d["blender"].get("normal_mismatches"):
        fails.append("blender: %d polygon normals do not face as intended" % d["blender"]["normal_mismatches"])
    # (k) every driven direction signed; (l) named corners; (m) every layout (ledger 0054 P4)
    try:
        driven = driven_directions(proj)
        k_fails, k_rows = direction_coverage(d, driven, entries=entries if sj is not None else None)
        l_fails, l_rows = named_coverage(d, driven, entries if sj is not None else None)
        m_fails, m_rows = layout_coverage(d, driven, entries if sj is not None else None)
    except ValueError as e:
        k_fails, k_rows = ["k_direction_coverage: %s" % e], []
        l_fails, l_rows = [], []
        m_fails, m_rows = [], []
    fails += k_fails + l_fails + m_fails
    rows += ["[verify-signs] " + r for r in k_rows + l_rows + m_rows]
    # race furniture is never the signs' ground or road
    for n in race_ground(d, measured):
        fails.append("race furniture measured as the signs' surface (%s) — the street layout has no such kerb" % n)
    for r in rows:
        print(r)
    if measured:
        print("[verify-signs] independent scan: %s (%s)" % (measured["scan"], note or "ok"))
    for w in warns:
        print("[verify-signs] WARN", w)
    for fl in fails:
        print("[verify-signs] FAIL", fl)
    print("[verify-signs] signs.json for (j): %s" % (sj if sj is not None else "(none: the track has no overrides)"))
    lay = [s["id"] for s in signs if s.get("layout")]
    print("[verify-signs] %d posts (%d plates%s), %d skipped, %s%s" % (
        len(signs), sum(len(s.get("plates") or [s]) for s in signs),
        (", %d layout plate%s: %s" % (len(lay), "s" if len(lay) != 1 else "", ", ".join(lay))) if lay else "",
        len(d["skipped"]),
        "FAIL" if fails else ("PASS" if blend else "PASS polyline-only (not authoritative)"),
        "" if blend else " (no --blend: (b)/(e)/(f) from the recorded vertices, (c) on the recorded built edge only)"))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
