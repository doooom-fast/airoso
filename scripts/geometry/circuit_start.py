"""A circuit's DECLARED start, line, grid, pits and sectors: pure geometry, no bpy (ledger 0093).

Kevin, 2026-11-18: "for milford and high plains, we need more race track focused furniture like starting line,
gridlines". engine-july's prep (Lake Murray v4's engine, frozen) places a single-layout lap's AC dummies by rule (its
scripts/geometry/dummies.py place_dummies): the grid on the straightest 260 m of the lap, AC_TIME_0 30 m ahead of it,
eight pits every 10 m on the racing surface, ONE AC_START, and every facing node yawed from the first two centreline
points with atan2(tx, tz). At High Plains that put the grid on the south straight (s 1080) while the painted line is on
the front straight (s 12), its nodes facing 102 deg (and that yaw's kn5 +Z reflected) on a road running 271 deg.

A track that declares `race_start` in track.config.json gets its nodes from that declaration instead, placed by
tools/circuit_dummies_blend.py on the PREPPED scene (the prep's own set removed first; opt-in, no key = nothing runs):

  "race_start": {
    "line":    {"lonlat": [lon, lat]} | {"station_m": s},          AC_TIME_0 (start / finish), L / R at +-w/2
    "grid":    {"slots_lonlat": [[lon, lat], ...]}                  AC_START_0..n-1 in grid order (pole first): each
             | {"pattern": {...}},                                  car's centre where it was measured, or a pattern
    "pits":    {"slots_lonlat": [...]} | {"pattern": {...}},        AC_PIT_0..m-1 (the same two forms)
    "sectors": {"stations_m": [s1, s2]},                            optional: AC_TIME_1 / AC_TIME_2; absent = the lap in
                                                                    equal thirds from the line (engine-july's rule)
    "road_prefixes": ["1ROAD"]                                      optional: the prepped meshes a car must stand on
  }
  pattern = {"first_m": d0, "step_m": d, "lateral_m": [l0, l1, ...], "slots": n}: slot k at the line's station + d0 +
            k * d (signed, + = ahead of the line in driving order), lateral l[k % len(l)] (+ = left of travel)

AC_HOTLAP_START_0 stands on the pole (engine-july's convention). Every facing node (AC_START / AC_PIT / AC_HOTLAP) is
yawed from the line's tangent at ITS OWN station (a TANGENT_CHORD_M chord), as Blender rotation_euler.z = atan2(ux, -uz)
(tools/layout_dummies.yaw_deg, the measured convention of ledger 0047: the exporter's (x, z, -y) puts north at kn5 -Z).
AC_TIME_* are never rotated.

Checks (`problems`, every one fatal in the Blender step): the line within the road; every START / PIT car (CAR_HALF_W_M
x CAR_HALF_L_M) inside the road's width LANE_MARGIN_M clear of each edge (the ROAD itself is read in Blender); no two cars
overlapping; the grid running back from the line in order, AC_TIME_0 0 < d <= LINE_AHEAD_MAX_M ahead of AC_START_0
(scripts/ac/verify_kn5 (e)); the sectors in driving order.

Frames: engine local (x = E, y = up, z = N), the frame data/centerline.local.json and data/dummies.json share; lon/lat
about that file's origin with scripts/geometry/projection._meters_per_degree (the draft's own conversion).
"""
from __future__ import annotations

import math

CAR_HALF_W_M = 0.95          # scripts/ac/verify_kn5.CAR_HALF_W_M: a 1.9 m car on a slot
CAR_HALF_L_M = 2.3           # [invented] a 4.6 m car
LANE_MARGIN_M = 0.30         # scripts/ac/verify_kn5.LANE_MARGIN_M: the car's edge this far inside the road's edge
LINE_AHEAD_MAX_M = 35.0      # scripts/ac/verify_kn5.LINE_AHEAD_MAX_M
LINE_OFF_ROAD_M = 1.0        # [invented] a declared line point this far past the road's half-width is not on the road
TANGENT_CHORD_M = 5.0        # [invented] a node's travel = the chord over +-2.5 m of its own station
DROP_IN_M = 0.30             # tools/set_start_blend.py / tools/layout_dummies.py: a spawn this far above the road
TIME_LIFT_M = 0.10           # tools/layout_dummies.py TIME_LIFT
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")


def meters_per_degree(lat0: float) -> tuple[float, float]:
    """scripts/geometry/projection._meters_per_degree, restated so this module imports nothing (Blender's python and
    the stdlib-only verify_kn5 both load it)"""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def lonlat_to_xz(origin: dict, lon: float, lat: float) -> tuple[float, float]:
    m_lon, m_lat = meters_per_degree(float(origin["lat"]))
    return (float(lon) - float(origin["lon"])) * m_lon, (float(lat) - float(origin["lat"])) * m_lat


def yaw_deg(ux: float, uz: float) -> float:
    """Blender rotation_euler.z (degrees) that points the exported node's kn5 local +Z along the engine-frame travel
    (ux, uz) — tools/layout_dummies.yaw_deg restated"""
    return math.degrees(math.atan2(ux, -uz))


def kn5_heading_dot(yaw_rad: float, ux: float, uz: float) -> float:
    """the kn5 local +Z of a node yawed by ``yaw_rad`` about Blender Z, dotted with the engine travel (ux, uz): the
    exporter maps a Blender Z rotation to one about kn5 +Y, so local +Z = (sin, 0, cos) in kn5 = (sin, -cos) in the engine
    (x, z) frame (kn5 z = -engine z). +1 = facing the travel; engine-july's atan2(tx, tz) reads -1 on a north-south road"""
    return math.sin(yaw_rad) * ux - math.cos(yaw_rad) * uz


class Line:
    """the closed lap of data/centerline.local.json: stations, interpolation, tangents, projection"""

    def __init__(self, pts, widths):
        self.pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
        self.widths = [float(w) for w in widths]
        n = len(self.pts)
        if n < 4 or len(self.widths) != n:
            raise ValueError("centreline too short, or widths do not match its points")
        self.closed = math.dist((self.pts[0][0], self.pts[0][2]), (self.pts[-1][0], self.pts[-1][2])) < 1e-6
        st = [0.0]
        for i in range(1, n):
            st.append(st[-1] + math.hypot(self.pts[i][0] - self.pts[i - 1][0], self.pts[i][2] - self.pts[i - 1][2]))
        self.st = st
        self.lap = st[-1]

    def wrap(self, s: float) -> float:
        return s % self.lap if self.closed else min(max(s, 0.0), self.lap)

    def _seg(self, s: float) -> tuple[int, float]:
        s = self.wrap(s)
        lo, hi = 0, len(self.st) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.st[mid] <= s:
                lo = mid
            else:
                hi = mid
        L = self.st[hi] - self.st[lo]
        return lo, (0.0 if L <= 0 else (s - self.st[lo]) / L)

    def point(self, s: float) -> tuple[float, float, float]:
        i, f = self._seg(s)
        a, b = self.pts[i], self.pts[i + 1]
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)

    def width(self, s: float) -> float:
        i, f = self._seg(s)
        return self.widths[i] + (self.widths[i + 1] - self.widths[i]) * f

    def tangent(self, s: float, chord: float = TANGENT_CHORD_M) -> tuple[float, float]:
        a, b = self.point(s - chord / 2.0), self.point(s + chord / 2.0)
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        return dx / L, dz / L

    def at(self, s: float, lateral: float = 0.0) -> tuple[float, float, float]:
        """(x, y, z) at station s, ``lateral`` m left of travel (+) — y the centreline's"""
        x, y, z = self.point(s)
        tx, tz = self.tangent(s)
        return x - tz * lateral, y, z + tx * lateral

    def project(self, x: float, z: float) -> tuple[float, float]:
        """(station, lateral + left of travel) of the nearest point on the lap"""
        best = None
        for i in range(len(self.pts) - 1):
            a, b = self.pts[i], self.pts[i + 1]
            ex, ez = b[0] - a[0], b[2] - a[2]
            L2 = ex * ex + ez * ez
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ex + (z - a[2]) * ez) / L2))
            px, pz = a[0] + ex * t, a[2] + ez * t
            d2 = (x - px) ** 2 + (z - pz) ** 2
            if best is None or d2 < best[0]:
                best = (d2, i, t)
        _d2, i, t = best
        s = self.st[i] + t * (self.st[i + 1] - self.st[i])
        tx, tz = self.tangent(s)
        cx, _cy, cz = self.point(s)
        return self.wrap(s), tx * (z - cz) - tz * (x - cx)

    def ahead(self, s_from: float, s_to: float) -> float:
        """distance from s_from to s_to in driving order (0..lap on a loop)"""
        d = s_to - s_from
        return d % self.lap if self.closed else d


def _slots(spec, what: str, line: Line, origin: dict, s_line: float, problems: list) -> list[tuple[float, float]]:
    """[(station, lateral)] of a grid / pits declaration, in its own order"""
    if not isinstance(spec, dict):
        problems.append(f"race_start.{what} must be an object (slots_lonlat or pattern)")
        return []
    if "slots_lonlat" in spec:
        return [line.project(*lonlat_to_xz(origin, q[0], q[1])) for q in spec["slots_lonlat"]]
    pat = spec.get("pattern")
    if not isinstance(pat, dict):
        problems.append(f"race_start.{what}: neither slots_lonlat nor pattern")
        return []
    lat = [float(v) for v in pat.get("lateral_m") or []]
    n = int(pat.get("slots", 0))
    if not lat or n < 1:
        problems.append(f"race_start.{what}.pattern needs lateral_m [...] and slots >= 1")
        return []
    d0, d = float(pat["first_m"]), float(pat["step_m"])
    return [(line.wrap(s_line + d0 + k * d), lat[k % len(lat)]) for k in range(n)]


def plan(race_start: dict, local: dict) -> dict:
    """Resolve a race_start declaration on data/centerline.local.json (``local``). Returns
    {"nodes": {name: {"x", "y", "z", "station_m", "lateral_m", "yaw_deg" + "travel" (facing nodes only)}},
     "line_station_m", "sectors_m", "lap_m", "problems": [...]}; y is the centreline's (the Blender step reads the built
    road instead)."""
    problems: list[str] = []
    line = Line(local["points_xyz_m"], local["widths_m"])
    origin = local["origin"]
    if not line.closed:
        problems.append("race_start is a circuit's: the centreline is not a closed lap")
    ln = race_start.get("line") or {}
    if "lonlat" in ln:
        s_line, lat_line = line.project(*lonlat_to_xz(origin, *ln["lonlat"]))
        if abs(lat_line) > line.width(s_line) / 2.0 + LINE_OFF_ROAD_M:
            problems.append(f"race_start.line lon/lat is {lat_line:+.1f} m off the centreline at s {s_line:.1f}: "
                            f"past the road's half-width {line.width(s_line) / 2.0:.1f} m")
    elif "station_m" in ln:
        s_line = line.wrap(float(ln["station_m"]))
    else:
        problems.append("race_start.line needs lonlat or station_m")
        s_line = 0.0
    grid = _slots(race_start.get("grid"), "grid", line, origin, s_line, problems)
    pits = _slots(race_start.get("pits"), "pits", line, origin, s_line, problems)
    if not grid:
        problems.append("race_start.grid places no slot")
    if not pits:
        problems.append("race_start.pits places no slot")
    nodes: dict[str, dict] = {}

    def facing(name, s, lateral):
        x, y, z = line.at(s, lateral)
        tx, tz = line.tangent(s)
        nodes[name] = {"x": x, "y": y, "z": z, "station_m": s, "lateral_m": lateral, "yaw_deg": yaw_deg(tx, tz),
                       "travel": [tx, tz]}

    for k, (s, la) in enumerate(grid):
        facing(f"AC_START_{k}", s, la)
    for k, (s, la) in enumerate(pits):
        facing(f"AC_PIT_{k}", s, la)
    if grid:
        nodes["AC_HOTLAP_START_0"] = dict(nodes["AC_START_0"])
    sec = (race_start.get("sectors") or {}).get("stations_m")
    if sec is None:
        sec = [line.wrap(s_line + line.lap / 3.0), line.wrap(s_line + 2.0 * line.lap / 3.0)]
    sec = [line.wrap(float(v)) for v in sec]
    for k, s in enumerate([s_line] + sec):
        half = line.width(s) / 2.0
        for side, sign in (("L", 1.0), ("R", -1.0)):
            x, y, z = line.at(s, sign * half)
            nodes[f"AC_TIME_{k}_{side}"] = {"x": x, "y": y, "z": z, "station_m": s, "lateral_m": sign * half}
    # --- checks ---------------------------------------------------------------------------------------------------
    cars = [(n, v) for n, v in nodes.items() if n.startswith(("AC_START", "AC_PIT"))]
    for n, v in cars:
        half = line.width(v["station_m"]) / 2.0
        clear = half - (abs(v["lateral_m"]) + CAR_HALF_W_M)
        if clear < LANE_MARGIN_M:
            problems.append(f"{n} at s {v['station_m']:.1f}, lateral {v['lateral_m']:+.2f}: the car stands {clear:.2f} m "
                            f"inside the road's {half:.2f} m half-width (< {LANE_MARGIN_M} m)")
    for i in range(len(cars)):
        for j in range(i + 1, len(cars)):
            (na, a), (nb, b) = cars[i], cars[j]
            ds = abs(line.ahead(a["station_m"], b["station_m"]))
            ds = min(ds, line.lap - ds) if line.closed else ds
            if ds < 2 * CAR_HALF_L_M and abs(a["lateral_m"] - b["lateral_m"]) < 2 * CAR_HALF_W_M:
                problems.append(f"{na} and {nb} overlap ({ds:.2f} m apart along, "
                                f"{abs(a['lateral_m'] - b['lateral_m']):.2f} m across)")
    behind = [line.ahead(s, s_line) for s, _la in grid]
    if grid and not (0.0 < behind[0] <= LINE_AHEAD_MAX_M):
        problems.append(f"AC_TIME_0 is {behind[0]:.1f} m ahead of AC_START_0: must be 0 < d <= {LINE_AHEAD_MAX_M:.0f} m "
                        f"(the pole just behind the line; verify_kn5 (e))")
    for k in range(1, len(behind)):
        if behind[k] < behind[k - 1] - 1e-6:
            problems.append(f"grid slot AC_START_{k} is {behind[k]:.1f} m behind the line, ahead of AC_START_{k - 1} "
                            f"({behind[k - 1]:.1f} m): the grid runs back from the line in order")
    prev = 0.0
    for k, s in enumerate(sec, start=1):
        a = line.ahead(s_line, s)
        if a <= prev or a >= line.lap - 1.0:
            problems.append(f"AC_TIME_{k} at s {s:.1f} is {a:.0f} m from the line in driving order: not after "
                            f"AC_TIME_{k - 1} ({prev:.0f} m)")
        prev = a
    return {"nodes": nodes, "line_station_m": s_line, "sectors_m": sec, "lap_m": line.lap, "problems": problems}


def car_corners(node: dict) -> list[tuple[float, float]]:
    """the four plan corners of a car standing on a facing node (engine x, z), for the Blender step's ROAD read"""
    tx, tz = node["travel"]
    nx, nz = -tz, tx
    out = []
    for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        out.append((node["x"] + tx * a * CAR_HALF_L_M + nx * b * CAR_HALF_W_M,
                    node["z"] + tz * a * CAR_HALF_L_M + nz * b * CAR_HALF_W_M))
    return out
