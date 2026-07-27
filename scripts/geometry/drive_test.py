"""Virtual drive test — simulate what a CAR experiences over the BUILT track, before any kn5.

The mesh audit checks geometry classes (vertices, surfaces, props). This drives the lap: six wheel
paths swept along the built triangles at 1 m steps, asking at every step the only three questions a
driver cares about:

  1. WHAT SURFACE IS UNDER THE TIRE?  The car rides the HIGHEST physical surface at (x,z). If that
     top surface is 1GRASS inside the lane, the ground pokes through the road — a launch. If the
     top surface steps more than a tire absorbs, it's a jolt. This is triangle-accurate: it samples
     the interpolated faces the physics engine collides with, not the vertices (which pass audits
     while the faces between them knife through — learned on the Lariat's switchbacks).
  2. IS ANYTHING STANDING IN THE CORRIDOR?  Walls, parapets, highway decks, posts, tree trunks —
     any triangle that rises above the deck inside the swept lane (+ margin) is an obstruction,
     reported by mesh name so the offender is identifiable (BARRIER_warning vs HWYSTRUCT vs TREES).
  3. IS THE SURFACE SMOOTH AT SPEED?  Wheel-path vertical kinks (slope change per metre) beyond
     what real roads allow. Real geometric design keeps cross-slope breaks under ~4-8% and rounds
     every grade change through vertical curves; a healthy build shows the same statistics.

Thresholds (physical rationale, tune at the top):
  STEP_BUMP_M    0.025  a 2.5 cm sharp step ~ hitting a lane reflector curb at speed — feel it
  STEP_SEVERE_M  0.060  6 cm ~ a full curb face — suspension crash, possible airborne moment
  KINK_PCT       3.0    slope change %-pts across 1 m ~ a driveway lip; real roads use vertical
                        curves precisely so this never happens on the carriageway
  OBST_CLEAR_M   0.25   anything rising this far above deck inside the corridor is a hit hazard

Run:  python -m scripts.geometry.drive_test tracks/<slug>
Writes data/drive_test.json, prints a per-problem report, exits 1 on FAIL (gate builds on it).
Pure stdlib; ~1-3 min for a 25 km lap.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

STEP_BUMP_M = 0.025
STEP_SEVERE_M = 0.060
KINK_PCT = 3.0
# SPEED. The thresholds above are fixed heights, and their own rationale is written in terms of
# speed ("~ hitting a lane reflector curb AT SPEED") — but nothing here ever knew how fast the car
# was going, so a 30 km/h hairpin and a 200 km/h straight were judged identically. A wheel crossing
# a step of height h at speed v is thrown with vertical velocity ~ v*h/L, so equal severity means a
# threshold that scales as 1/v. Measured consequence on Grand Junction: 40 of its 43 severe steps
# sit above 100 km/h (worst 0.187 m at ~145 km/h) and only 3 in tight corners — the unweighted
# count was flattering the places that matter most.
SPEED_REF_KMH = 100.0        # the speed the fixed thresholds above were hand-calibrated for
SPEED_MIN_KMH = 30.0         # below this the scaling stops helping: a curb is still a curb
SPEED_MAX_KMH = 260.0
GRIP_LAT = 1.3               # lateral g a GT car carries — sets the cornering speed from radius
ACCEL_MS2 = 4.5              # tractive
BRAKE_MS2 = 12.0             # braking dominates: the fast-approach-to-slow-corner case
OBST_CLEAR_M = 0.25
OBST_HEIGHT_M = 1.8          # car-strike ceiling: AC cars are ~1.3 m tall; walls/trunks rise from deck
#                              level and still trip this, while legit overhead furniture (cobra-head
#                              lamps arching the lane at 2.5 m+) clears it
STEP_M = 1.0                 # sampling step along the lap
WHEEL_HALF_TRACK = 0.75      # wheel offset around each driving line
CELL = 3.0                   # spatial hash cell (m)

DRIVABLE = ("1ROAD", "1KERB", "1RUNOFF", "1LAWN", "1GRASS")   # car can roll on these
SOFT = ("1GRASS", "1LAWN")   # ...but these mid-lane on TOP = ground through road
PAINT = ("MARKINGS", "ROADTEXT", "YLINE")   # flat paint decals ~1.5 cm over deck — never obstructions


def speed_profile(pts, st, closed: bool) -> list[float]:
    """Speed (m/s) the car can carry at each centerline point: cornering grip capped by how fast it
    can actually get there and stop again. Three passes — radius, then forward acceleration, then
    backward braking — which is what makes the approach to a slow corner read fast (the wheel meets
    the bumps before the apex at entry speed, not apex speed)."""
    n = len(pts)
    if n < 3:
        return [SPEED_MAX_KMH / 3.6] * n
    vmax = SPEED_MAX_KMH / 3.6
    v = []
    for i in range(n):
        # Wrap only on a closed lap. On a point-to-point stage the two ends are different places
        # (Dragon Tail's finish is 17 km and 145 m from its start), and sampling across them
        # invents a hairpin at each end — which then drags the whole opening straight down through
        # the forward acceleration pass. Same trap the elevation profile documents for its filters.
        ia = (i - 3) % n if closed else max(0, i - 3)
        ic = (i + 3) % n if closed else min(n - 1, i + 3)
        a, b, c = pts[ia], pts[i], pts[ic]
        A = math.dist((a[0], a[2]), (b[0], b[2]))
        B = math.dist((b[0], b[2]), (c[0], c[2]))
        C = math.dist((a[0], a[2]), (c[0], c[2]))
        sp = (A + B + C) / 2.0
        ar2 = sp * (sp - A) * (sp - B) * (sp - C)
        R = (A * B * C) / (4.0 * math.sqrt(ar2)) if ar2 > 1e-9 else 1e6
        v.append(min(vmax, math.sqrt(max(1.0, R) * 9.81 * GRIP_LAT)))
    # FROM A STANDING START AT THE LINE (Kevin). Station 0 is the start/pit line, and the car is
    # stationary there — not arriving at flying-lap speed. Seeding v[0]=0 and refusing to wrap the
    # passes past it gives the speeds the car ACTUALLY carries over this lap: the opening stretch is
    # acceleration-limited, everything after is grip- and braking-limited as normal. Wrapping
    # instead converges a flying lap, which reads faster over the first few hundred metres than any
    # real first lap does.
    v[0] = 0.0
    for i in range(1, n):                         # forward: how fast can it GET here from the line
        d = max(1e-6, st[i] - st[i - 1])
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * ACCEL_MS2 * d))
    for i in range(n - 2, -1, -1):                # backward: and still make the next corner
        d = max(1e-6, st[i + 1] - st[i])
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * BRAKE_MS2 * d))
    return v


def _load_obj(path: Path):
    """[(group, verts, tris)] — tris as vertex index triples into the group's own vert list."""
    groups = []
    cur = None
    base = 0
    verts_all: list[tuple[float, float, float]] = []
    # Stream the file. read_text().splitlines() materialises the whole OBJ twice over, and a 25 km
    # stage ships a ~170 MB track.obj beside a ~300 MB environment.obj.
    _va = verts_all.append
    with path.open() as fh:
        for ln in fh:
            k = ln[:2]
            if k == "v ":
                p = ln.split()
                _va((float(p[1]), float(p[2]), float(p[3])))
            elif k == "f ":
                if cur is not None:
                    p = ln.split()
                    cur["tris"].append((int(p[1].partition("/")[0]) - 1,
                                        int(p[2].partition("/")[0]) - 1,
                                        int(p[3].partition("/")[0]) - 1))
            elif k == "o ":
                cur = {"name": ln[2:].strip(), "v0": len(verts_all), "tris": []}
                groups.append(cur)
    return verts_all, groups


class TriField:
    """Spatial-hashed triangle soup answering: top surface height + owner at (x,z); tris in cell."""

    def __init__(self):
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.tris: list[tuple] = []          # (ax,ay,az,bx,by,bz,cx,cy,cz, name)

    def add(self, verts, tri, name):
        a, b, c = (verts[i] for i in tri)
        k = len(self.tris)
        self.tris.append((*a, *b, *c, name))
        x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
        z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
        for ci in range(int(x0 // CELL), int(x1 // CELL) + 1):
            for cj in range(int(z0 // CELL), int(z1 // CELL) + 1):
                self.cells[(ci, cj)].append(k)

    def top_at(self, x, z, y_ref=None, window=2.5):
        """(height, owner_name) of the highest surface at (x,z). With ``y_ref``: highest surface
        within ±``window`` of the expected deck height — REQUIRED on tracks that cross over
        themselves (the Lariat's 19th St bridge over its own US-6 ramp): the global maximum reads
        the upper deck while you drive the lower one, minting phantom multi-metre steps."""
        best, owner = None, None
        for k in self.cells.get((int(x // CELL), int(z // CELL)), ()):
            t = self.tris[k]
            ax, ay, az, bx, by, bz, cx, cy, cz, name = t
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-12:
                continue
            w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
            w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
            w2 = 1.0 - w0 - w1
            if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                continue
            y = w0 * ay + w1 * by + w2 * cy
            if y_ref is not None and abs(y - y_ref) > window:
                continue
            if best is None or y > best:
                best, owner = y, name
        return best, owner

    def rising_in(self, x, z, r, deck_at, clear, cap):
        """Names of tri owners with a vertex inside radius r of (x,z) rising ``clear``..``cap``
        above the deck DIRECTLY BENEATH that vertex (deck_at(x,z) sampler) — comparing against the
        station-centre deck instead reads ordinary up-slope geometry on any grade as a wall."""
        hits = set()
        R = int(r // CELL) + 1
        ci, cj = int(x // CELL), int(z // CELL)
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                for k in self.cells.get((ci + di, cj + dj), ()):
                    t = self.tris[k]
                    if t[9] in hits:
                        continue
                    for vx, vy, vz in ((t[0], t[1], t[2]), (t[3], t[4], t[5]), (t[6], t[7], t[8])):
                        if math.hypot(vx - x, vz - z) >= r:
                            continue
                        d = deck_at(vx, vz)
                        if d is not None and d + clear < vy < d + cap:
                            hits.add(t[9])
                            break
        return hits


def run(project_dir: str | Path) -> dict:
    import time as _tmod
    _t0 = _tmod.time()
    def _phase(_label):
        nonlocal _t0
        _now = _tmod.time()
        print(f"  [drive-time] {_label:22} {_now - _t0:7.1f}s", flush=True)
        _t0 = _now
    project = Path(project_dir)
    data = project / "data"
    cfg = json.loads((project / "track.config.json").read_text())
    fin = data / "finished_centerline.json"
    if fin.exists():
        # the line the ribbon was actually swept along (already in mesh frame) — driving the raw
        # centerline instead reads phantom obstructions where corner-rounding moved the pavement
        lc = json.loads(fin.read_text())
        pts = [tuple(p) for p in lc["points_xyz_m"]]
    else:
        mirror = -1.0 if cfg.get("mirror_x", False) else 1.0
        lc = json.loads((data / "centerline.local.json").read_text())
        pts = [(mirror * p[0], p[1], p[2]) for p in lc["points_xyz_m"]]
    widths = lc["widths_m"]

    # declared bridge spans: parapet/railing furniture INSIDE these is expected (a bridge with no
    # railing is the defect, not the railing) — obstruction hits on *bridge-named meshes there are skipped
    spans = [(b.get("center_m", 0) - b.get("len_m", 0) / 2 - 20, b.get("center_m", 0) + b.get("len_m", 0) / 2 + 20)
             for b in (cfg.get("capture", {}) or {}).get("bridges", [])]

    surface = TriField()      # everything the car can roll on
    obstacle = TriField()     # everything else that could stand in the corridor
    _wall_verts = []          # 1WALL columns for the furniture-seating gate
    # CORRIDOR CULL. Every query this gate makes happens within a corridor around the centerline —
    # wheel paths, excursion sweeps, obstruction checks. On a 25 km stage the terrain grid covers
    # roughly 90 km2 while that corridor is about 4 km2, so hashing the whole world costs ~20x more
    # than it needs to and the load/hash phase dominates the run (measured on IMI: top_at was 0.65 s
    # of 9.4 s, while loading and hashing was over 7 s).
    _CULL_M = 120.0          # generous: the widest excursion sweep is well inside this
    _ccell = 64.0
    _cnear: set = set()
    for _px, _py, _pz in pts:
        _ci0, _cj0 = int(_px // _ccell), int(_pz // _ccell)
        _r = int(_CULL_M // _ccell) + 1
        for _di in range(-_r, _r + 1):
            for _dj in range(-_r, _r + 1):
                _cnear.add((_ci0 + _di, _cj0 + _dj))

    # SKIP THE GIANTS. TriField.add registers a triangle in EVERY 3 m cell its bbox covers, so one
    # 500 m terrain-skirt triangle lands in ~27,000 cells. A 25 km stage has a long enough border
    # that every corridor cell then holds thousands of them, and each top_at scans the lot: measured
    # at >200 ms per station on Dragon Tail against ~0.6 ms on Sand Creek — the sweep that appeared
    # to take hours. The skirt is a flat apron far outside the track that no wheel path can reach,
    # and terrain spanning the road is audit check J's job, not this gate's.
    _MAX_TRI_M = 60.0

    def _near_corridor(a, b, c):
        if (max(a[0], b[0], c[0]) - min(a[0], b[0], c[0]) > _MAX_TRI_M
                or max(a[2], b[2], c[2]) - min(a[2], b[2], c[2]) > _MAX_TRI_M):
            return False
        return (((int(a[0] // _ccell), int(a[2] // _ccell)) in _cnear)
                or ((int(b[0] // _ccell), int(b[2] // _ccell)) in _cnear)
                or ((int(c[0] // _ccell), int(c[2] // _ccell)) in _cnear))

    _track_groups: list = []
    _culled = 0
    for objfile in ("track.obj", "environment.obj"):
        p = data / objfile
        if not p.exists():
            continue
        verts, groups = _load_obj(p)
        if objfile == "track.obj":
            _track_groups = groups
        for grp in groups:
            up = grp["name"].upper()
            if up.startswith(PAINT):
                continue
            if up.startswith("1WALL"):
                _seen_w = set()
                for tri in grp["tris"]:
                    for vi in tri:
                        if vi not in _seen_w:
                            _seen_w.add(vi)
                            _wall_verts.append(verts[vi])
            field = surface if up.startswith(DRIVABLE) else obstacle
            for tri in grp["tris"]:
                _a, _b, _c = verts[tri[0]], verts[tri[1]], verts[tri[2]]
                if not _near_corridor(_a, _b, _c):
                    _culled += 1
                    continue
                field.add(verts, tri, grp["name"])

    if _culled:
        print(f"  [drive] corridor cull: skipped {_culled} triangles beyond {_CULL_M:.0f} m")
    _phase("load + hash")

    # SANITY: there must BE a road. A build_mesh that dies mid-write (2.87 M grid verts ran the
    # process out of memory) leaves a TRUNCATED track.obj holding only the 1GRASS chunks written so
    # far — no 1ROAD at all. This gate then scored a world with no road in it: every wheel-path
    # sample landed on grass, so it reported 159,635 "ground above the road" and 548 bumps/km and
    # called it a surface problem. A gate that cannot tell a bad road from NO road is not a gate.
    # Reuse the groups already parsed above. This used to re-read track.obj in full just to list the
    # road groups — a third parse of a file that can be 170 MB.
    _road_groups = [g for g in _track_groups if g["name"].upper().startswith("1ROAD")]
    if not _road_groups:
        raise SystemExit(
            "drive_test: track.obj contains no 1ROAD_* geometry — the mesh build did not finish "
            "(check for a truncated OBJ / out-of-memory kill in build_mesh). Refusing to score a "
            "track with no road surface.")

    # six wheel paths: wheel pair around center line + around left/right third lines
    n = len(pts)
    st = [0.0]
    for i in range(1, n):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    lap = st[-1]

    _fzp = project / "data" / "flat_zones.json"
    _fzones = json.loads(_fzp.read_text()) if _fzp.exists() else []

    def _in_flat_zone(px, pz):
        return any((px - a) ** 2 + (pz - b) ** 2 < d * d for a, b, c, d in _fzones)

    problems = {"soft_top_in_lane": [], "steps": [], "severe_steps": [], "kinks": [], "obstructions": [],
                "daylight_gaps": []}
    def _pavement_at(x, z):
        """Is there 1ROAD directly under (x,z)? Point-precise, but scans only the ONE hash cell's
        road triangles — a road-only TriField answered the same question and took 20+ minutes on a
        25 km stage, while plain cell-membership was too coarse (a sample 3 m off the ribbon end
        still lands in a cell the first quad reaches into)."""
        for i in surface.cells.get((int(x // CELL), int(z // CELL)), ()):
            ax, ay, az, bx, by, bz, cx, cy, cz, name = surface.tris[i]
            if not name.upper().startswith("1ROAD"):
                continue
            d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(d) < 1e-12:
                continue
            w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d
            w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d
            if w0 >= -1e-6 and w1 >= -1e-6 and 1.0 - w0 - w1 >= -1e-6:
                return True
        return False
    _has_ends = not bool(cfg.get("loop", True))
    _lap_end = sum(math.dist((pts[i][0], pts[i][2]), (pts[i + 1][0], pts[i + 1][2]))
                   for i in range(len(pts) - 1))
    prev_h = [None] * 10
    prev_slope = [None] * 10
    off_pavement = 0
    obst_names = defaultdict(int)
    _phase("pre-sweep setup")
    s = 0.0
    i = 1
    _nst = 0
    _tsweep = _tmod.time()
    while s < lap:
        _nst += 1
        if _nst % 2000 == 0:
            _el = _tmod.time() - _tsweep
            print(f"  [drive-time] sweep {_nst:6} stations ({s/1000:6.2f} km)  {_el:7.1f}s  "
                  f"{1000*_el/_nst:.2f} ms/station", flush=True)
        while i < n - 1 and st[i] < s:
            i += 1
        t = (s - st[i - 1]) / max(st[i] - st[i - 1], 1e-9)
        x = pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t
        y_ref = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t
        z = pts[i - 1][2] + (pts[i][2] - pts[i - 1][2]) * t
        tx, tz = pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]
        L = math.hypot(tx, tz) or 1e-9
        nx, nz = -tz / L, tx / L
        w = widths[i]
        # TRAVEL-SWATH cap: at junction-flare boxes w balloons to 24-40 m, but a swept ribbon
        # covers a bowtie there, not the full square — wheel paths at box-width offsets ride the
        # un-swept notches and read grass 'mid-lane'. Cars travel the center swath; test THAT.
        lane_half = min(max(w / 2 - 0.4, 0.8), 6.0)
        lines = (-(w / 2 - 0.5), -w / 3, 0.0, w / 3, (w / 2 - 0.5))   # edges included
        # edge paths (|line| = w/2-0.5) DETECT holes/ground-through at the pavement lip;
        # smoothness (steps/kinks) gates only on INTERIOR paths — nobody laps on the hinge
        edge_line = {0, len(lines) - 1}
        paths = [off + d for off in lines for d in (-WHEEL_HALF_TRACK, WHEEL_HALF_TRACK)]
        # OFF THE END OF THE PAVEMENT. A point-to-point stage's finished_centerline can overhang
        # the built ribbon: on Dragon Tail its first point sits 30 m before the road starts, over
        # bare terrain. Every wheel path there reads grass as the top surface, so ONE station minted
        # 10 "ground on top mid-lane" hits and an 0.8 m "severe step" climbing back onto the road —
        # the sole blocker on all four rally stages, and pure artifact. Ask the ROAD-ONLY field
        # whether there is pavement here at all: no pavement = off the stage, not a defect. Grass
        # sitting ON a road that IS here still fails, which is the case this gate exists for.
        # Only near the ENDS, and only on a stage that has ends. This artifact is the finished
        # centerline overhanging the built ribbon at a start/finish cap, so it cannot occur mid-lap
        # — and running the point test on all 25,260 stations of a 25 km stage took 5 HOURS of CPU
        # without finishing. Bounded to ~60 stations it is free.
        if _has_ends and (s < 30.0 or s > _lap_end - 30.0) and not _pavement_at(x, z):
            off_pavement += 1
            prev_h = [None] * 10
            prev_slope = [None] * 10
            s += STEP_M          # MUST advance: `s += STEP_M` lives at the END of this body, so a
            continue             # bare `continue` here spins forever. That hung every rally build
                                 # from v0.25.1 on — the stages were never slow, they never finished.
        deck_c, _ = surface.top_at(x, z, y_ref)
        for pi, off in enumerate(paths):
            is_edge = (pi // 2) in edge_line
            if abs(off) > lane_half:
                off = math.copysign(lane_half, off)
            px, pz = x + nx * off, z + nz * off
            h, owner = surface.top_at(px, pz, y_ref)
            if h is None:
                prev_h[pi] = None
                prev_slope[pi] = None
                continue
            if owner and owner.upper().startswith(SOFT):
                problems["soft_top_in_lane"].append((round(s, 1), round(off, 2), owner))
            if prev_h[pi] is not None:
                dh = h - prev_h[pi]
                slope = dh / STEP_M
                if prev_slope[pi] is not None and not is_edge:
                    kink = abs(slope - prev_slope[pi]) * 100
                    if kink > KINK_PCT:
                        problems["kinks"].append((round(s, 1), round(off, 2), round(kink, 2)))
                    step = abs(dh - prev_slope[pi] * STEP_M)
                    if step > STEP_SEVERE_M:
                        # flared-apron texture: on widened corner pavement (w >= 11) the OUTER
                        # offsets ride taper fans with rolled crossfall breaks — real aprons
                        # have them and the driving line doesn't touch them. Report, don't gate.
                        if w >= 9.5 and abs(off) > 3.5 and not _in_flat_zone(px, pz):
                            problems.setdefault("apron_steps", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                        else:
                            # inside a junction flat zone the WHOLE pad is driving surface —
                            # no exemptions (Kevin: "how do your tests pass this")
                            problems["severe_steps"].append((round(s, 1), round(off, 2), round(step, 3)))
                    elif step > STEP_BUMP_M:
                        if w >= 9.5 and abs(off) > 3.5 and not _in_flat_zone(px, pz):
                            problems.setdefault("apron_bumps", []).append(
                                (round(s, 1), round(off, 2), round(step, 3)))
                        else:
                            problems["steps"].append((round(s, 1), round(off, 2), round(step, 3)))
                prev_slope[pi] = slope
            prev_h[pi] = h
        # daylight probe: just past each pavement edge, some surface must exist from deck level
        # down to 7 m below — a miss means a hole in the embankment skirt (sky under the road)
        if deck_c is not None:
            for side in (-1.0, 1.0):
                off = side * (w / 2 + 0.8)
                gy_probe, _own = surface.top_at(x + nx * off, z + nz * off, deck_c - 2.5, 5.0)
                if gy_probe is None:
                    problems["daylight_gaps"].append((round(s, 1), round(off, 2)))
        # corridor obstruction scan at this station (uses centre deck height)
        if deck_c is not None:
            on_bridge = any(a <= s <= b for a, b in spans)
            # corridor CAP: at junction-flare boxes lane_half balloons to 12-16 m and the box's
            # own edge furniture (barriers hugging a 33 m mouth) reads as an obstruction. The
            # car needs a clear TRAVEL SWATH — 6 m half-width is a full two-lane clearance.
            for name in obstacle.rising_in(x, z, min(lane_half, 6.0) + 0.3,
                                           lambda vx, vz: surface.top_at(vx, vz, y_ref)[0],
                                           OBST_CLEAR_M, OBST_HEIGHT_M):
                if on_bridge and "BRIDGE" in name.upper():
                    continue                       # declared-span railing = required furniture
                problems["obstructions"].append((round(s, 1), name))
                obst_names[name] += 1
        s += STEP_M

    # EXCURSION SWEEPS (Kevin: "your tests need to drive the car off the road and back onto it").
    # Every ~150 m the virtual car leaves the pavement laterally, crosses the shoulder onto the
    # grass out to +8 m, and returns — sampling the built surface continuously. Any DROP > 20 cm
    # between adjacent samples in that crossing is the hover/moat/ledge class no along-the-road
    # path can see. Declared bridge spans exempt (past the railing is a real drop, guarded).
    # UNPAVED RUN-OFF. This sweep steps laterally every 0.5 m, so a perfectly ordinary 2:1 fill
    # slope (0.25 m per step) trips the 0.12 m drop test at EVERY sample. On a paved circuit that is
    # right — run-off there is a flat apron, so any drop really is a ledge. On a graded dirt road the
    # slope IS the surface: the shoulder falls away into its borrow ditch and nothing is wrong.
    #
    # Evidence this is terrain and not a meshing artifact (Dragon Tail, 25 km of CR 116): refining
    # the terrain grid 20% (10 m -> 8 m cells) moved ground-through-lane 23 -> 5, a 78% cut, while
    # the excursion count went 1,000 -> 1,041 — 4%, and the wrong way. Every worst offender sits at
    # +/-9 to 9.5 m, six metres beyond a 6.5 m carriageway, out on the fill slope.
    #
    # So on an unpaved road two things still gate, both surface-independent:
    #   * a FACE far steeper than an embankment. A 2:1 fill slope is 0.25 m per 0.5 m sample;
    #     1.0 m in one sample is four times that — a wall, not a slope.
    #   * a total FALL from the pavement edge deeper than the parapet warrant. build_mesh builds a
    #     stone parapet at fill edges dropping > 2 m and deliberately builds nothing below that, so a
    #     gate demanding a wall below 2 m contradicts the builder. Measuring cumulative fall (not the
    #     per-sample delta) is what catches a real cliff that descends over several samples and so
    #     never shows its full height in any single one — the case a per-step threshold alone misses.
    _unpaved = str(cfg.get("road_surface", "tarmac")) != "tarmac"
    UNPAVED_FACE_M = 1.0         # one-sample face 4x steeper than a 2:1 embankment
    UNPAVED_FALL_M = 3.0         # cumulative fall across the band (a 2:1 slope falls 2 m over 4 m)
    UNPAVED_LIP_M = 1.0          # ...of the CARRIAGEWAY edge, not the shoulder's outer lip
    UNPAVED_LIP_DROP_M = 0.25    # a step that would catch a wheel as it leaves the driven surface
    excursions = []
    s2 = 0.0
    next_exc = 0.0
    for i in range(1, n):
        seg2 = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
        s2 += seg2
        if s2 < next_exc:
            continue
        next_exc += 150.0
        if any(a <= s2 <= b for a, b in spans):
            continue
        # intersection flare mouths: the widened lip has no graded edge yet (tracked task —
        # the coverage guard removes the sidewalk the flare swallows and nothing replaces it).
        # Exempt from GATING, still counted in the report as flare ledges.
        _wmed = sorted(widths)[len(widths) // 2]
        in_flare = widths[i] > _wmed + 1.5
        x0, y0, z0 = pts[i]
        _a2, _b2 = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        _dx2, _dz2 = _b2[0] - _a2[0], _b2[2] - _a2[2]
        _L2 = math.hypot(_dx2, _dz2) or 1.0
        txe, tze = _dx2 / _L2, _dz2 / _L2
        nxe, nze = -tze, txe
        we = widths[i] / 2
        for sgn in (1.0, -1.0):
            prev_y = None
            off = 0.0
            built_edge = None    # where BUILT pavement actually ends (surface-owner, not nominal width)
            miss_run = 0
            edge_y = None        # ground height where the pavement ends — the datum for total fall
            carriage_edge = None # outer edge of the DRIVEN surface (excludes the shoulder)
            while off <= we + 9.0:   # FULLY exit the tarmac, past the hem onto raw world (Kevin)
                exx, ezz = x0 + nxe * off * sgn, z0 + nze * off * sgn
                ey, own = surface.top_at(exx, ezz, y0, 8.0)
                if own is not None and str(own).upper().startswith(("1ROAD", "1KERB")):
                    built_edge = off
                    edge_y = ey        # keeps advancing while still on pavement -> the true edge
                    # CARRIAGEWAY edge = where the surface you DRIVE on ends. The shoulder is also
                    # named 1ROAD_*, so built_edge runs out to the shoulder's outer lip — which on a
                    # graded road is exactly where the fill slope starts. Using that as "the pavement
                    # edge" made an ordinary shoulder-to-slope transition look like a ledge, 719 times.
                    if "SHOULDER" not in str(own).upper():
                        carriage_edge = off
                in_band = built_edge is not None and off <= built_edge + 4.0 and not in_flare
                if ey is None:
                    # NO SURFACE mid-crossing = a hole in the world. The old sweep silently
                    # skipped None — the literal fall-through case, ignored by the tool built to
                    # find it ("your tests should show it, but they continually don't").
                    miss_run += 1
                    if in_band and miss_run >= 2:      # >= 1 m of nothing inside the band
                        excursions.append((round(s2, 1), round(off * sgn, 2), 9.99, True))
                        miss_run = -999                # one report per crossing
                else:
                    miss_run = 0
                if ey is not None and prev_y is not None and prev_y - ey > 0.12 and off > we - 0.5:
                    # 0.12 m = a tall curb, the most a real car survives at speed. A drop BEHIND a
                    # barrier/guard wall is GUARDED (the car never reaches it — that's the wall's
                    # job, per the construction research: stone parapets at every drop > 2 m on
                    # the real Lariat). Unguarded car-destroyer drops in the band fail — they mark
                    # exactly where the four-condition selector must place walls.
                    guarded = False
                    for _wo in (off - 2.0, off - 1.0, off - 0.5):
                        if _wo <= we - 0.5:
                            break
                        _wx, _wz = x0 + nxe * _wo * sgn, z0 + nze * _wo * sgn
                        _wy, _wown = surface.top_at(_wx, _wz, y0 + 0.5, 2.5)
                        if _wown is not None and str(_wown).upper().startswith("1WALL"):
                            guarded = True
                            break
                    _drop = prev_y - ey
                    if _unpaved:
                        # Gate on PHYSICAL DANGER, not on proximity to the pavement. Two reasons the
                        # paved in-band test is wrong here: the shoulder counts as built pavement, so
                        # "just past the edge" IS where a graded road's fill slope starts (that alone
                        # gated 719 ordinary transitions); and `in_flare` excludes corner flares, which
                        # is where the worst real drop on this stage lives — 3.12 m off the outside of
                        # a flared switchback, waved through while shoulder slopes failed.
                        _fall = (edge_y - ey) if edge_y is not None else 0.0
                        _lip = (carriage_edge is not None and off <= carriage_edge + UNPAVED_LIP_M
                                and _drop > UNPAVED_LIP_DROP_M)
                        _gated = (not guarded) and (_drop > UNPAVED_FACE_M
                                                    or _fall > UNPAVED_FALL_M or _lip)
                    else:
                        _gated = in_band and not guarded
                    excursions.append((round(s2, 1), round(off * sgn, 2), round(_drop, 2), _gated))
                if ey is not None:
                    prev_y = ey
                off += 0.5
    problems["excursion_drops"] = excursions

    # CORNER FEASIBILITY (Kevin: "the tests should be catching my issue"): a KINK — fold over
    # a tight ±10 m window > 85 deg (apex radius <= ~12 m; switchbacks read 55-75 deg here) —
    # cannot be driven on street-width pavement. Kinks must carry >= 10 m.
    tight_corners = []
    for i in range(2, n - 2, 2):
        j0 = i
        while j0 > 0 and st[i] - st[j0] < 15.0:
            j0 -= 1
        j1 = i
        while j1 < n - 1 and st[j1] - st[i] < 15.0:
            j1 += 1
        h0 = math.atan2(pts[min(j0 + 2, n - 1)][2] - pts[max(j0 - 2, 0)][2],
                        pts[min(j0 + 2, n - 1)][0] - pts[max(j0 - 2, 0)][0])
        h1 = math.atan2(pts[min(j1 + 2, n - 1)][2] - pts[max(j1 - 2, 0)][2],
                        pts[min(j1 + 2, n - 1)][0] - pts[max(j1 - 2, 0)][0])
        dturn = abs((math.degrees(h1 - h0) + 180.0) % 360.0 - 180.0)
        wmax_local = max(widths[max(0, i - 7):min(n, i + 8)])   # the corner CORE the line uses
        if dturn > 110.0 and wmax_local < 9.0:
            tight_corners.append((round(st[i], 0), round(dturn, 0), round(widths[i], 1)))
    problems["undrivable_corners"] = tight_corners

    # FURNITURE SEATING (Kevin: "get the drive test to fail on what I'm driving right now"):
    # every wall/fence COLUMN stands on its support — base within 0.8 m of the surface directly
    # beneath (tri-exact). Rails between posts excused by grounded neighbors. The 27 m barriers
    # hanging over the creek FAIL here, forever. No advisory mode for this check.
    floating_walls = []
    cols = {}
    for gx2, gy2, gz2 in _wall_verts:
        k2 = (round(gx2 / 0.6), round(gz2 / 0.6))
        if k2 not in cols or gy2 < cols[k2][0]:
            cols[k2] = (gy2, gx2, gz2)
    grounded = set()
    gaps2 = {}
    for k2, (wy, wx, wz) in cols.items():
        gy2, _own2 = surface.top_at(wx, wz, wy - 0.5)
        if gy2 is None:
            gy2, _own2 = surface.top_at(wx, wz, wy)
        if gy2 is not None:
            gaps2[k2] = wy - gy2
            if wy - gy2 <= 0.8:
                grounded.add(k2)
        else:
            gaps2[k2] = 99.0          # nothing under it at all: definitely floating
    for k2, gp2 in gaps2.items():
        if gp2 > 0.8:
            if any((k2[0] + di, k2[1] + dj) in grounded for di in range(-4, 5) for dj in range(-4, 5)):
                continue
            floating_walls.append((round(cols[k2][1], 1), round(cols[k2][2], 1), round(gp2, 2)))
    problems["floating_furniture"] = floating_walls

    # REPLICATION ERROR (Kevin: "i want a realistic road. this exists so we have to be able to
    # replicate it"): the lidar measured the ACTUAL road bench — the built deck must match it.
    # |built - raw measured| along the lap, declared bridges exempt. This is the number that says
    # how far the pipeline strayed from the real mountain.
    rep = []
    ep = data / "centerline.elevation.json"
    if ep.exists():
        try:
            ej = json.loads(ep.read_text())
            zr = ej.get("z_raw_m") or []
            e0 = 0.0
            _lc9 = data / "centerline.local.json"
            if _lc9.exists():
                e0 = float(json.loads(_lc9.read_text()).get("origin", {}).get("elev_m", 0.0))
            if zr and len(zr) >= 10:
                m2 = min(len(zr), len(pts))
                stq = 0.0
                for i in range(1, m2):
                    stq += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
                    if any(a <= stq <= b for a, b in spans):
                        continue
                    rep.append(abs(pts[i][1] - (zr[i] - e0)))
        except Exception:
            pass
    if rep:
        rep.sort()
        nR = len(rep)
        problems["replication"] = {"median": round(rep[nR // 2], 2), "p95": round(rep[19 * nR // 20], 2),
                                   "max": round(rep[-1], 2)}

    # collapse obstruction runs (one wall = many stations)
    per_km = lap / 1000
    _phase("post-sweep passes")
    report = {
        "lap_m": round(lap, 1),
        "soft_top_in_lane": len(problems["soft_top_in_lane"]),
        "off_pavement_stations": off_pavement,
        "severe_steps": len(problems["severe_steps"]),
        "severe_per_km": round(len(problems["severe_steps"]) / per_km, 2),
        "steps_per_km": round(len(problems["steps"]) / per_km, 2),
        "kinks_per_km": round(len(problems["kinks"]) / per_km, 2),
        "obstruction_stations": len(set(s for s, _ in problems["obstructions"])),
        "daylight_gaps": len(problems["daylight_gaps"]),
        "replication_vs_measured": problems.get("replication"),
        "undrivable_corners": len(problems["undrivable_corners"]),
        "floating_furniture": len(problems["floating_furniture"]),
        "apron_steps": len(problems.get("apron_steps", [])),
        "excursion_drops": sum(1 for r in problems["excursion_drops"] if r[3]),
        "excursion_far_ledges": sum(1 for r in problems["excursion_drops"] if not r[3]),
        "worst_excursions": sorted(problems["excursion_drops"], key=lambda r: -r[2])[:12],
        "worst_gated_excursions": sorted((r for r in problems["excursion_drops"] if r[3]),
                                         key=lambda r: -r[2])[:20],
        "obstruction_by_mesh": dict(sorted(obst_names.items(), key=lambda kv: -kv[1])[:12]),
        "worst": {
            "soft_top": problems["soft_top_in_lane"][:12],
            "severe_steps": sorted(problems["severe_steps"], key=lambda r: -r[2])[:12],
            "severe_all": sorted(problems["severe_steps"], key=lambda r: -r[2])[:2000],
            "kinks": sorted(problems["kinks"], key=lambda r: -r[2])[:12],
            "obstructions": problems["obstructions"][:16],
        },
    }
    (data / "drive_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    # Gate philosophy: ABSOLUTE ZERO for the things no driver tolerates (ground through the lane,
    # solid objects in the corridor); RATES vs the driver-approved baseline for surface texture
    # (Sand Creek v0.15.x, the reference feel, runs ~11 severe/km and ~19 bumps/km — all at
    # junction crotches where edge strips meet). Kinks are reported but don't gate: on a real
    # mountain profile 3%-pt/m events are genuine road texture, not defects.
    severe_per_km = report["severe_per_km"]
    # SURFACE-AWARE BUMP RATE. The 75/km pass line is calibrated against Sand Creek — a PAVED street
    # loop, ~19 bumps/km. A 2.5 cm step is a defect on asphalt; on a graded dirt road it is the
    # surface. Dragon Tail measures ~114/km straight off 1 m lidar of the real road while its severe
    # rate (9.8/km) and its replication (median 0.06 m) both sit comfortably inside their limits —
    # i.e. the deck is faithfully following a genuinely rougher surface, not wobbling off it.
    # Holding gravel to the tarmac line would mean smoothing a rally stage until it drove like a
    # circuit, which is the opposite of correct. Severe steps, ground-through-lane, obstructions and
    # excursions are UNCHANGED — this moves one pass line for one surface, nothing else.
    _surface = str(cfg.get("road_surface", "tarmac"))
    _bump_limit = {"tarmac": 75.0, "gravel": 150.0}.get(_surface, 75.0)
    import os as _os
    # GATE_EXCURSIONS_ADVISORY=1: report-only for a TEST build while the construction selector
    # (#17: guard walls at drops, per docs/ROAD-CONSTRUCTION.md) is pending — the failures are the
    # tracked missing-walls class. NEVER set for a full (non-rc) release.
    _exc_adv = _os.environ.get("GATE_EXCURSIONS_ADVISORY") == "1"
    if _exc_adv and report["excursion_drops"]:
        print(f"  !! EXCURSIONS ADVISORY MODE: {report['excursion_drops']} unguarded drops NOT gating "
              f"(awaiting construction selector #17)")
    fail = (report["soft_top_in_lane"] > 0
            or report["daylight_gaps"] > 0
            or (not _exc_adv and report["excursion_drops"] > int(report["lap_m"] / 1000))
            or report["obstruction_stations"] > 0
            or report["undrivable_corners"] > 0
            or report["floating_furniture"] > 0
            or severe_per_km > 12.0
            or report["steps_per_km"] > _bump_limit)
    print(f"DRIVE TEST {cfg['slug']}  lap {lap/1000:.2f} km  (10 wheel paths @ {STEP_M} m)")
    print(f"  ground on top mid-lane : {report['soft_top_in_lane']}"
          + (f"   [{off_pavement} station(s) skipped: no pavement — off the stage end]" if off_pavement else ""))
    print(f"  floating furniture (walls/fences off support): {report['floating_furniture']} "
          f"{problems['floating_furniture'][:3] if problems['floating_furniture'] else ''}")
    print(f"  undrivable corners (>100deg @ <11m): {report['undrivable_corners']} "
          f"{problems['undrivable_corners'][:4] if problems['undrivable_corners'] else ''}")
    print(f"  severe steps (>{STEP_SEVERE_M*100:.0f} cm)  : {report['severe_steps']}")
    print(f"  bumps >{STEP_BUMP_M*100:.1f} cm /km      : {report['steps_per_km']} "
          f"(limit {_bump_limit:.0f} for {_surface})")
    print(f"  slope kinks >{KINK_PCT}%% /km   : {report['kinks_per_km']}")
    print(f"  daylight gaps at edges : {report['daylight_gaps']}")
    if report.get("replication_vs_measured"):
        _rp = report["replication_vs_measured"]
        print(f"  replication vs measured road : median {_rp['median']} m  p95 {_rp['p95']} m  max {_rp['max']} m")
    print(f"  off-road excursion drops>20cm : {report['excursion_drops']}"
          f"  (far flare ledges, reported: {report['excursion_far_ledges']})"
          + ("  [unpaved: only ledges >2 m or drops at the pavement edge gate]" if _unpaved else ""))
    for r in report["worst_excursions"][:6]:
        print(f"    worst excursion drop: {r}")
    print(f"  obstructed stations    : {report['obstruction_stations']}"
          + (f"  {report['obstruction_by_mesh']}" if obst_names else ""))
    for label, rows in (("soft_top", report["worst"]["soft_top"]),
                        ("severe", report["worst"]["severe_steps"]),
                        ("obstruction", report["worst"]["obstructions"][:8])):
        for r in rows[:6]:
            print(f"    worst {label}: {r}")
    print(f"  => {'FAIL' if fail else 'PASS'}   (data/drive_test.json)")
    return {**report, "fail": fail}


if __name__ == "__main__":
    r = run(sys.argv[1] if len(sys.argv) > 1 else ".")
    sys.exit(1 if r["fail"] else 0)
