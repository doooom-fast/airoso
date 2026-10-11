"""Per-layout AC dummies, ENGINE frame, pure Python — data/dummies_<id>.json for every layouts[] entry.

Ledger 0047: three versions of the Lake Murray loop (street, race clockwise, race anticlockwise)
share one road kn5 and each loads its own nodes-only spawn kn5 (L8 as amended). This tool writes
the FULL set per layout — AC_START_0..n-1, AC_HOTLAP_START_0, AC_PIT_0..p-1, AC_TIME_0/1/2_L/R —
from the declared start in track.config.json `layouts[].start`:

    line_vertex      AC_TIME_0 (start/finish) at this centreline vertex, L/R at +/- w/2
    grid_vertex      pole (AC_START_0 = AC_HOTLAP_START_0), BEHIND the line in that layout's travel
    offset_right_m   lateral, RIGHT OF THAT LAYOUT'S OWN TRAVEL (the lane the layout drives)
    sector_vertices  [TIME_1, TIME_2] in driving order from the line (validated, never re-derived)

Grid: AC_START_g (g = 1..slots-1) at pole - 5.5 g m, two staggered columns INSIDE the lane at the
lane centre +/- 1.4 m (never dummies.py's +/-30 % of the half-width about the CENTRE, which would put
slots in the oncoming lane). Pits: AC_PIT_p single file at the lane centre, pole - 45 - 7 (p+1) m.
Heights: START/PIT/HOTLAP at centreline y + LIFT 0.10 + DROP_IN 0.30 (tools/set_start_blend.py),
TIME at y + 0.10. "Behind" = lower station for `direction: forward`, higher for `reverse`.

FACING (a measured correction, scratchpad/layouts/judge_facing.py, 2026-10-10): on every reference
the AC_START node's LOCAL +Z (kn5 frame) points along the AI travel (deepforest dot +1.00); the
installed San Diego V3 reads -0.91. The prep and set_start set Blender rotation_euler.z =
atan2(tx, tz) from the engine (E, N) tangent; the exporter's (x, z, -y) conversion maps that to kn5
local +Z = (tx, 0, tz) while the kn5-frame travel is (tx, 0, -tz) (kn5 z = -engine z). Correct yaw:
    psi = atan2(u_x, -u_z)   with u = THIS layout's travel tangent (forward tangent, negated for reverse)
= forward + pi for the reverse layout. `_yaw_deg[name]` carries it per facing dummy; AC_TIME_* are
never rotated. Tangent from pts[k-1] -> pts[k+1] at the dummy's OWN nearest vertex (ledger 0016).

Schema = the dict track_folder counts pits from ({name: [x, y, z]}, engine frame x=E, y=up, z=N —
the frame dummies.json / finished_centerline.json / write_ai_line.grid_alignment share) plus
UNDERSCORE keys every consumer must skip: `_layout`, `_direction`, `_frame`, `_yaw_deg`,
`_vertex`, `_station_m`, `_right_of_travel_m`, `_line`, `_issue_spawn`.

Per-issue spawns (Kevin 2026-08-20) survive for the STREET layout only:
    python tools/layout_dummies.py <project> --issue-spawn <key>
moves that layout's START/HOTLAP/PIT to start_positions.json positions[key] (vertex + forward-frame
offset_right_m), never AC_TIME, never a race layout, never by default.

Run:  python tools/layout_dummies.py <project-dir> [--config <track.config.json>] [--layout <id>]...
                                     [--issue-spawn <key>]
Exit 1 on any validation miss (ids, directions, kinds, vertices, sector order, line distance).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

LIFT = 0.10                 # build_loop_blend's road lift
DROP_IN = 0.30              # set_start_blend: spawn 30 cm above the deck
TIME_LIFT = 0.10
GRID_PITCH_M = 5.5
GRID_STAGGER_M = 1.4        # two columns at lane centre +/- 1.4 m (car 1.9 m wide: 0.9 m between columns)
PIT_SETBACK_M = 45.0
PIT_PITCH_M = 7.0
LINE_AHEAD_MAX_M = 35.0     # AC_TIME_0 must be this close ahead of the pole (ac-track-modding: ~30 m)
SECTOR_KINK_MAX_DEG = 1.0   # a timing plane on a straight (invented, see GATES-CHANGELOG)
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
DIRECTIONS = ("forward", "reverse")
KINDS = ("street", "race")
UNDERSCORE_DOC = ("underscore keys are metadata — consumers (build_spawn_kn5, track_folder, write_ai_line, "
                  "verify_kn5) must skip every key starting with '_'")


def yaw_deg(ux: float, uz: float) -> float:
    """Blender rotation_euler.z (degrees) that makes the exported node's kn5 local +Z point along
    the engine-frame travel (ux, uz): atan2(ux, -uz)."""
    return math.degrees(math.atan2(ux, -uz))


class Line:
    """The closed centreline: stations, interpolation, tangents (L13: the closure vertex repeats v0)."""

    def __init__(self, pts, widths):
        self.pts = [tuple(p) for p in pts]
        self.widths = [float(w) for w in widths]
        n = len(self.pts)
        if n < 4:
            raise SystemExit("[dummies] centreline too short")
        self.closed = math.dist((self.pts[0][0], self.pts[0][2]), (self.pts[-1][0], self.pts[-1][2])) < 1e-6
        self.ring = n - 1 if self.closed else n     # vertices that are distinct places
        st = [0.0]
        for i in range(1, n):
            st.append(st[-1] + math.hypot(self.pts[i][0] - self.pts[i - 1][0], self.pts[i][2] - self.pts[i - 1][2]))
        self.st = st
        self.lap = st[-1]

    def forward_tangent(self, k: int) -> tuple[float, float]:
        n = len(self.pts)
        if self.closed:
            a, b = self.pts[(k - 1) % self.ring], self.pts[(k + 1) % self.ring]
        else:
            a, b = self.pts[max(0, k - 1)], self.pts[min(n - 1, k + 1)]
        dx, dz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        return dx / L, dz / L

    def travel(self, k: int, direction: str) -> tuple[float, float]:
        tx, tz = self.forward_tangent(k)
        return (-tx, -tz) if direction == "reverse" else (tx, tz)

    def kink_deg(self, k: int) -> float:
        a, b, c = self.pts[(k - 1) % self.ring], self.pts[k % self.ring], self.pts[(k + 1) % self.ring]
        h0 = math.atan2(b[2] - a[2], b[0] - a[0])
        h1 = math.atan2(c[2] - b[2], c[0] - b[0])
        return abs(math.degrees((h1 - h0 + math.pi) % (2 * math.pi) - math.pi))

    def at_station(self, s: float):
        """(x, y, z) on the polyline at station s (mod lap on a loop) + the nearest vertex index."""
        if self.closed:
            s = s % self.lap
        s = min(max(s, 0.0), self.lap)
        st = self.st
        lo, hi = 0, len(st) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if st[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = self.pts[lo], self.pts[lo + 1]
        t = (s - st[lo]) / max(1e-9, st[lo + 1] - st[lo])
        p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)
        k = lo if t < 0.5 else lo + 1
        return p, k % self.ring if self.closed else k

    def ahead_m(self, s_from: float, s_to: float, direction: str) -> float:
        """distance from s_from to s_to in the driving direction (0..lap on a loop)"""
        d = (s_to - s_from) if direction == "forward" else (s_from - s_to)
        return d % self.lap if self.closed else d


def place(line: Line, station: float, direction: str, right_m: float, lift: float):
    (x, y, z), k = line.at_station(station)
    ux, uz = line.travel(k, direction)
    rx, rz = uz, -ux                     # right-hand side of travel (set_start_blend.py:55)
    return ([round(x + rx * right_m, 3), round(y + lift, 3), round(z + rz * right_m, 3)], k, (ux, uz))


def derive_sectors(line: Line, line_vertex: int, direction: str, island_w=None, window: int = 6):
    """1/3 and 2/3 of the lap from the line in driving order, nudged to the nearest vertex whose
    +/- `window` neighbourhood is straight (kink < 1 deg/vertex) and off any island. Used only when a
    layout declares no sector_vertices; the declared ones are validated, never replaced."""
    out = []
    for frac in (1.0 / 3.0, 2.0 / 3.0):
        target = (line.st[line_vertex] + frac * line.lap) if direction == "forward" else (line.st[line_vertex] - frac * line.lap)
        target %= line.lap
        _, k0 = line.at_station(target)
        best = None
        for d in range(0, 200):
            for k in ((k0 + d) % line.ring, (k0 - d) % line.ring):
                if island_w is not None and island_w[k] > 0:
                    continue
                if max(line.kink_deg((k + j) % line.ring) for j in range(-window, window + 1)) < SECTOR_KINK_MAX_DEG:
                    best = k
                    break
            if best is not None:
                break
        out.append(best if best is not None else k0)
    return out


def layout_dummies(line: Line, layout: dict, race: dict, island_w=None, override=None) -> tuple[dict, list[str]]:
    fails: list[str] = []
    lid = layout.get("id", "?")
    direction = str(layout.get("direction", "forward"))
    start = layout.get("start") or {}
    line_v = int(start.get("line_vertex", -1))
    grid_v = int(start.get("grid_vertex", start.get("vertex", -1)))
    off = float(start.get("offset_right_m", 0.0))
    n_grid = int(race.get("grid_slots", 8))
    n_pits = int(race.get("pit_slots", 8))
    if direction not in DIRECTIONS:
        fails.append(f"{lid}: direction must be forward|reverse, got {direction!r}")
        direction = "forward"
    if not (0 <= line_v < line.ring):
        fails.append(f"{lid}: start.line_vertex {line_v} out of range 0..{line.ring - 1}")
        line_v = 0
    if not (0 <= grid_v < line.ring):
        fails.append(f"{lid}: start.grid_vertex {grid_v} out of range 0..{line.ring - 1}")
        grid_v = line_v
    out: dict = {}
    yaw: dict = {}
    vert: dict = {}
    stat: dict = {}
    right: dict = {}

    def put(name, pos, k, s, r, u=None):
        out[name] = pos
        vert[name] = int(k)
        stat[name] = round(s % line.lap if line.closed else s, 2)
        right[name] = round(r, 3)
        if u is not None:
            yaw[name] = round(yaw_deg(*u), 3)

    # the line: AC_TIME_0 L/R at +/- w/2 of THIS layout's travel, never rotated
    w0 = line.widths[line_v]
    s_line = line.st[line_v]
    for suffix, r in (("L", -w0 / 2.0), ("R", +w0 / 2.0)):
        pos, k, _ = place(line, s_line, direction, r, TIME_LIFT)
        put(f"AC_TIME_0_{suffix}", pos, k, s_line, r)
    # sectors: declared, validated (driving order from the line, straight, off islands)
    sectors = start.get("sector_vertices")
    if not sectors:
        sectors = derive_sectors(line, line_v, direction, island_w)
        print(f"[dummies] {lid}: no sector_vertices declared — derived {sectors}")
    if len(sectors) != 2:
        fails.append(f"{lid}: sector_vertices must hold exactly two vertices, got {sectors}")
    prev_ahead = 0.0
    for idx, sv in enumerate(sectors[:2], start=1):
        sv = int(sv)
        if not (0 <= sv < line.ring):
            fails.append(f"{lid}: sector vertex {sv} out of range")
            continue
        ahead = line.ahead_m(s_line, line.st[sv], direction)
        if ahead <= prev_ahead:
            fails.append(f"{lid}: AC_TIME_{idx} (v{sv}) is {ahead:.0f} m from the line in driving order — "
                         f"not after AC_TIME_{idx - 1} ({prev_ahead:.0f} m); sectors must increase in driving order (L11)")
        prev_ahead = ahead
        kk = line.kink_deg(sv)
        if kk >= SECTOR_KINK_MAX_DEG:
            fails.append(f"{lid}: AC_TIME_{idx} at v{sv} sits on a {kk:.1f} deg/vertex kink (a corner, not a timing straight)")
        if island_w is not None and island_w[sv] > 0:
            fails.append(f"{lid}: AC_TIME_{idx} at v{sv} is on a median island")
        wv = line.widths[sv]
        for suffix, r in (("L", -wv / 2.0), ("R", +wv / 2.0)):
            pos, k, _ = place(line, line.st[sv], direction, r, TIME_LIFT)
            put(f"AC_TIME_{idx}_{suffix}", pos, k, line.st[sv], r)
        print(f"[dummies] {lid}: AC_TIME_{idx} v{sv} at {ahead:.0f} m ({ahead / line.lap:.3f} lap) from the line")

    # the grid: pole + staggered slots behind it, inside the lane
    pole_v, pole_off = grid_v, off
    issue_key = None
    if override:
        # per-issue spawn (street layout only): registry offsets are in the FORWARD frame
        issue_key = override.get("key")
        pole_v = int(override["vertex"])
        pole_off = float(override["offset_right_m"]) * (1.0 if direction == "forward" else -1.0)
        if not (0 <= pole_v < line.ring):
            fails.append(f"{lid}: issue spawn {issue_key!r} vertex {pole_v} out of range")
            pole_v = grid_v
    s_pole = line.st[pole_v]
    behind = line.ahead_m(s_pole, s_line, direction)
    if not override and not (0.0 < behind <= LINE_AHEAD_MAX_M):
        fails.append(f"{lid}: AC_TIME_0 (v{line_v}) is {behind:.0f} m ahead of the pole v{grid_v} in {direction} travel — "
                     f"must be 0 < d <= {LINE_AHEAD_MAX_M:.0f} m (the grid sits just behind the line)")
    sgn = -1.0 if direction == "forward" else 1.0          # "behind" = lower station when forward
    pos, k, u = place(line, s_pole, direction, pole_off, LIFT + DROP_IN)
    put("AC_START_0", pos, k, s_pole, pole_off, u)
    put("AC_HOTLAP_START_0", list(pos), k, s_pole, pole_off, u)
    for g in range(1, n_grid):
        s = s_pole + sgn * GRID_PITCH_M * g
        lat = pole_off + (GRID_STAGGER_M if g % 2 == 1 else -GRID_STAGGER_M)
        pos, k, u = place(line, s, direction, lat, LIFT + DROP_IN)
        put(f"AC_START_{g}", pos, k, s, lat, u)
    for p in range(n_pits):
        s = s_pole + sgn * (PIT_SETBACK_M + PIT_PITCH_M * (p + 1))
        pos, k, u = place(line, s, direction, pole_off, LIFT + DROP_IN)
        put(f"AC_PIT_{p}", pos, k, s, pole_off, u)

    meta = {
        "_layout": lid, "_direction": direction, "_kind": layout.get("kind"),
        "_frame": "engine x=E, y=up, z=N (centerline.local.json); Blender = (x, z, y); kn5 z = -z",
        "_doc": UNDERSCORE_DOC,
        "_yaw_doc": "Blender rotation_euler.z in degrees for the FACING dummies: atan2(u_x, -u_z) of this "
                    "layout's travel at the dummy's own vertex (kn5 local +Z then points along travel; "
                    "measured calibration: deepforest +1.00). AC_TIME_* carry no yaw.",
        "_line": {"vertex": line_v, "station_m": round(s_line, 2), "width_m": w0, "pole_vertex": pole_v,
                  "pole_behind_line_m": round(behind, 2), "sector_vertices": [int(s) for s in sectors[:2]]},
        "_issue_spawn": issue_key,
        "_yaw_deg": yaw, "_vertex": vert, "_station_m": stat, "_right_of_travel_m": right,
    }
    return {**out, **meta}, fails


def validate_layouts(layouts: list[dict]) -> list[str]:
    fails: list[str] = []
    ids = [lo.get("id") for lo in layouts]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        fails.append(f"layout ids must be unique and non-empty: {ids}")
    for lo in layouts:
        lid = lo.get("id")
        if lid in ("full", "freeroam"):
            fails.append(f"layout id {lid!r} suppresses the CM name suffix (track_folder.ui_track_json) — rename")
        if str(lo.get("direction", "forward")) not in DIRECTIONS:
            fails.append(f"{lid}: direction must be forward|reverse")
        kind = lo.get("kind", "street")
        if kind not in KINDS:
            fails.append(f"{lid}: kind must be street|race, got {kind!r}")
        if lo.get("race_furniture") and kind != "race":
            fails.append(f"{lid}: race_furniture: true requires kind 'race'")
        if not isinstance(lo.get("start"), dict):
            fails.append(f"{lid}: no start block (line_vertex / grid_vertex / offset_right_m / sector_vertices)")
    return fails


def write_all(project_dir, config_path=None, only=None, issue_spawn=None) -> int:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads(Path(config_path or (proj / "track.config.json")).read_text(encoding="utf-8"))
    layouts = cfg.get("layouts") or []
    race = cfg.get("race") or {}
    fails = validate_layouts(layouts)
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    line = Line(cl["points_xyz_m"], cl["widths_m"])
    mb = data / "median_bands.json"
    island_w = None
    if mb.exists():
        iw = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", [])
        island_w = iw if len(iw) == len(line.pts) else None
    ids = {lo.get("id") for lo in layouts}
    if only:
        stale = [o for o in only if o not in ids]
        if stale:
            raise SystemExit(f"[dummies] --layout {stale} not in layouts[] {sorted(ids)} — refusing (stale id)")
    override = None
    if issue_spawn:
        reg = json.loads((proj / "start_positions.json").read_text(encoding="utf-8"))
        pos = (reg.get("positions") or {}).get(issue_spawn)
        if pos is None:
            raise SystemExit(f"[dummies] --issue-spawn {issue_spawn!r} not in start_positions.json")
        if int(pos.get("vertex", 0)) == 0 and float(pos.get("offset_right_m", 0.0)) == 0.0:
            print(f"[dummies] issue spawn {issue_spawn!r} is the default placement — declared start kept")
        else:
            override = {"key": issue_spawn, "vertex": pos["vertex"], "offset_right_m": pos["offset_right_m"]}
    written = []
    for lo in layouts:
        lid = lo.get("id")
        if only and lid not in only:
            continue
        ov = override if (override and lo.get("kind", "street") == "street") else None
        if override and ov is None and lo.get("kind") == "race":
            print(f"[dummies] {lid}: race layout — issue spawn ignored (declared grid kept)")
        d, lf = layout_dummies(line, lo, race, island_w, ov)
        fails.extend(lf)
        out = data / f"dummies_{lid}.json"
        out.write_text(json.dumps(d, indent=1), encoding="utf-8")
        written.append(out)
        s0 = d["AC_START_0"]
        print(f"[dummies] {lid:9} {d['_direction']:7} pole v{d['_vertex']['AC_START_0']} "
              f"({s0[0]:.2f}, {s0[1]:.2f}, {s0[2]:.2f}) right {d['_right_of_travel_m']['AC_START_0']:+.2f} m "
              f"yaw {d['_yaw_deg']['AC_START_0']:+.1f} deg; line v{d['_line']['vertex']} "
              f"{d['_line']['pole_behind_line_m']:.1f} m ahead; pits v{d['_vertex']['AC_PIT_0']}..v{d['_vertex'][f'AC_PIT_{int(race.get('pit_slots', 8)) - 1}']}"
              f"{'; ISSUE SPAWN ' + repr(ov['key']) if ov else ''} -> {out.name}")
    # stale per-layout files: a dummies_<x>.json whose id is no longer a layout would still become a
    # spawn kn5 through any glob-driven writer
    for old in sorted(data.glob("dummies_*.json")):
        x = old.stem[len("dummies_"):]
        if x not in ids:
            old.unlink()
            print(f"[dummies] removed stale {old.name} (no layout {x!r})")
    if fails:
        print("[dummies] FAIL:")
        for f in fails:
            print("   -", f)
        return 1
    print(f"[dummies] wrote {len(written)} layout file(s)")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python tools/layout_dummies.py <project-dir> [--config <cfg>] [--layout <id>]... [--issue-spawn <key>]")
    config_path = None
    only: list[str] = []
    issue = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--config":
            config_path = argv[i + 1]; i += 2
        elif a == "--layout":
            only.append(argv[i + 1]); i += 2
        elif a == "--issue-spawn":
            issue = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument {a!r}")
    return write_all(argv[0], config_path, only or None, issue)


if __name__ == "__main__":
    sys.exit(main())
