"""Phase 5c: assert an exported .kn5 is DRIVABLE before it ships — fail the build if not.

Every hard-won drivability lesson, encoded as a check that runs on the actual exported binary so a
regression can never ship silently again (all three of these have bitten us and cost a release):

  1. No duplicate physical mesh names. AC keys physical meshes BY NAME and drops duplicates from
     collision → car falls through. (Caused by a mesh exceeding the 65,535 vertex cap and auto-splitting
     into same-named halves.)  → see kn5-duplicate-name-fallthrough.
  2. Every drivable surface (1ROAD/1GRASS/1KERB/1RUNOFF/1LAWN) is wound FACE-UP. A face-down surface
     renders as ground but gives AC's one-sided physics no top to stand on → fall-through. Never recalc
     normals; build_mesh authors them up.  → see ac-fallthrough-real-cause.
  3. Every physical mesh is under the 65,535 vertex cap (would otherwise trip #1 on the next build).
  4. AC_START and the AC_PIT_* boxes sit ON a road surface at the same height as AC_HOTLAP_START — so
     you don't drop when spawning from the pits.

MULTI-LAYOUT (ledger 0047; fleet/LAWS.md L8 as amended). A track with more than one ``layouts[]``
entry ships a spawn-free road kn5 plus one nodes-only spawn kn5 per layout (``build/<slug>__<id>.kn5``)
and, for layouts with ``race_furniture: true``, one race-furniture kn5 (``build/<slug>_race.kn5``) —
the shape every reverse-capable reference measured ships (deepforest, Oregon Raceway Park,
rt_california_highway, Pacific Coast Hwy). On such a track check 4/5 become:

  (a) the road kn5 and the race kn5 carry NO AC_START/AC_PIT/AC_HOTLAP/AC_TIME node; exactly one
      ``<slug>__<id>.kn5`` per declared id and no other ``__*.kn5``;
  (b) each spawn kn5 is nodes-only and holds exactly the set ``data/dummies_<id>.json`` declares
      (else at least AC_START_0, AC_HOTLAP_START_0, AC_PIT_0, AC_TIME_0/1/2_L/R); every START/PIT/
      HOTLAP sits on the ROAD kn5's 1ROAD (today's 13.5 m / 1.0 m test);
  (c) HEADING: every facing node's LOCAL +Z (the node matrix's third row, kn5 frame) points along the
      layout's travel — the kn5-frame tangent of data/finished_centerline.json at the node's nearest
      vertex, negated for ``direction: reverse`` — within HEADING_MIN_DEG. Calibrated on the references:
      deepforest AC_START_0 local +Z · fast_lane travel = +1.00 (six more at +0.98..+1.00); the installed
      San Diego V3 build read −0.91 (the atan2(tx, tz) reflection, fixed in tools/layout_dummies.py) and
      must FAIL here. The dot is printed so a sign error is one constant away;
  (d) SIDE: every START/PIT stands RIGHT of the layout's travel (kn5 frame: right = (−t.z, t.x), see
      ``_right_of``), and at least barrier_half + CHAIN_CLEAR_M off the centreline where
      data/barrier_bands.json declares the centre chain (a grid slot straddling the chain);
  (e) LINE: the AC_TIME_0 pair's midpoint lies within LINE_TOL_M of ``layouts[].start.line_vertex``,
      AC_TIME_0 is 0 < d ≤ LINE_AHEAD_MAX_M ahead of AC_START_0 in driving order, and AC_TIME_1 / AC_TIME_2
      sit at increasing driving-order stations from the line (L11 — sectors renumbered per direction);
  (f) RACE kn5 (when any layout declares race_furniture): present, every mesh name 1WALL_RACE*/1KERB_RACE*
      (≥ 1 of each), every material RACE-named (an un-purged material table or a swapped .ini ships the
      whole road's materials), no mesh over the cap, no duplicate 1-prefixed name across road + race
      (AC loads both), no spawn node, file under RACE_KN5_MAX_B.

Pure-stdlib kn5 parse (no deps), reproducible on the Mac. Exit 0 = drivable, 1 = a check failed (with a
report of exactly which mesh/dummy and why).

    python -m scripts.ac.verify_kn5 projects/<slug>
"""

from __future__ import annotations

import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

DRIVABLE = ("1ROAD", "1GRASS", "1KERB", "1RUNOFF", "1LAWN")
VERT_CAP = 65535
FACE_UP_MIN = 0.90          # ≥90% of a drivable mesh's faces must point up (rest = holes_fill scraps)
PIT_ROAD_MAX_M = 13.5       # a pit/start box must be within this of a 1ROAD vertex — the nearest road vert
#                            is an EDGE vert, so a centreline spawn sits ~half-width away; real widths +
#                            junction flares reach ~25 m wide, so allow ~half of that (was 8 m for ~16 m roads)
PIT_DY_MAX_M = 1.0          # ...and within this height of it
POKE_ABOVE_M = 0.15         # a 1GRASS vert this far above a nearby drivable (road/kerb) vert = a poke
POKE_R = 5.0                # horizontal reach (matches geometry/audit_mesh.py check B)
POKE_MAX = 20               # tolerate a handful of holes_fill scraps; more = the seam regressed

# --- multi-layout (ledger 0047) ------------------------------------------------------------------
SPAWN_PREFIXES = ("AC_START", "AC_PIT", "AC_HOTLAP", "AC_TIME")
FACING = ("AC_START", "AC_PIT", "AC_HOTLAP")
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")
HEADING_MIN_DEG = 30.0      # ⚠ invented pending a measured envelope: a facing node more than this off the
#                            layout's travel fails (references read +0.98..+1.00, today's SD −0.91)
CHAIN_CLEAR_M = 1.0         # ⚠ invented: |lateral| ≥ barrier_half + this beside a declared centre chain
LINE_TOL_M = 2.0            # AC_TIME_0 midpoint vs the declared line vertex
LINE_AHEAD_MAX_M = 35.0     # AC_TIME_0 at most this far ahead of AC_START_0 (ac-track-modding: ~30 m)
RACE_KN5_MAX_B = 20_000_000
MIN_SPAWN_SET = ("AC_START_0", "AC_HOTLAP_START_0", "AC_PIT_0", "AC_TIME_0_L", "AC_TIME_0_R",
                 "AC_TIME_1_L", "AC_TIME_1_R", "AC_TIME_2_L", "AC_TIME_2_R")


def _parse_full(path: Path) -> tuple[list, list, list]:
    """Return (nodes, meshes, materials). node = (name, world_xyz, local_z_xyz) — the third row of
    the node's world matrix is its local +Z axis (row-vector convention: translation is row 3, so
    (0,0,1,0)·M = row 2); mesh = dict(name, up, dn, nverts, P, T); materials = [name, ...]."""
    d = path.read_bytes()
    if d[:6] != b"sc6969":
        raise SystemExit(f"not a kn5: {path}")
    o = [6]
    U = lambda: (struct.unpack_from("<I", d, o[0])[0], o.__setitem__(0, o[0] + 4))[0]
    I = lambda: (struct.unpack_from("<i", d, o[0])[0], o.__setitem__(0, o[0] + 4))[0]
    H = lambda: (struct.unpack_from("<H", d, o[0])[0], o.__setitem__(0, o[0] + 2))[0]
    F = lambda: (struct.unpack_from("<f", d, o[0])[0], o.__setitem__(0, o[0] + 4))[0]
    B = lambda: (d[o[0]] != 0, o.__setitem__(0, o[0] + 1))[0]

    def BL(n):
        v = d[o[0]:o[0] + n]; o[0] += n; return v

    def S():
        n = U(); v = d[o[0]:o[0] + n]; o[0] += n; return v.decode("utf-8", "replace")

    ver = I()
    if ver > 5:
        I()
    for _ in range(I()):
        I(); S(); BL(U())
    materials: list = []
    for _ in range(U()):
        materials.append(S()); S(); BL(2); I()
        for _ in range(U()):
            S(); BL(40)
        for _ in range(U()):
            S(); I(); S()

    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def mm(a, b):
        return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]

    nodes: list = []
    meshes: list = []

    def rd(par):
        ncls = U(); name = S(); cc = U(); B()
        if ncls == 1:
            w = mm([F() for _ in range(16)], par)
            nodes.append((name, (w[12], w[13], w[14]), (w[8], w[9], w[10])))
            for _ in range(cc):
                rd(w)
        elif ncls == 2:
            B(); B(); B()
            vc = U(); P = []
            for _ in range(vc):
                px, py, pz = F(), F(), F(); F(); F(); F(); F(); F(); F(); F(); F()
                P.append((px, py, pz))
            ic = U(); idx = [H() for _ in range(ic)]
            U(); U(); F(); F(); BL(16); B()
            up = dn = 0
            for t in range(0, len(idx) - 2, 3):
                a, b, c = P[idx[t]], P[idx[t + 1]], P[idx[t + 2]]
                ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
                if ny > 0:
                    up += 1
                elif ny < 0:
                    dn += 1
            meshes.append({"name": name, "up": up, "dn": dn, "nverts": vc, "P": P, "T": idx})
            for _ in range(cc):
                rd(par)
        else:
            raise SystemExit(f"unknown node class {ncls}")

    rd(ident)
    return nodes, meshes, materials


def _parse(path: Path) -> tuple[list, list]:
    """Return (nodes, meshes). node = (name, world_xyz); mesh = dict(name, up, dn, nverts, road_pts).
    (The shape ext_config.py and kn5_ground_check.py unpack — kept; ``_parse_full`` adds the heading.)"""
    nodes, meshes, _mats = _parse_full(path)
    return [(n, p) for n, p, _z in nodes], meshes


# --- geometry helpers for the per-layout checks ------------------------------------------------
def _right_of(t):
    """Right-hand side of travel ``t`` = (x, z) in the KN5 frame. Derivation: the engine frame is x=E,
    z=N with right-of-travel (tz, −tx) (north → east); the kn5 frame mirrors z (finished_centerline =
    (x, y, −z_engine), scripts/modkit/kn5_to_gate_obj.py), so travel t' = (tx, −tz) and the same east
    vector becomes (−t'.z, t'.x). Check: kn5 travel (0, −1) (= north) → right (1, 0) = east."""
    return (-t[1], t[0])


class _Line:
    """finished_centerline.json (kn5 frame): nearest vertex, travel tangent, driving-order stations."""

    def __init__(self, pts, closed: bool | None = None):
        self.pts = [tuple(p) for p in pts]
        n = len(self.pts)
        self.closed = (closed if closed is not None else
                       n > 3 and math.dist((self.pts[0][0], self.pts[0][2]), (self.pts[-1][0], self.pts[-1][2])) < 1e-6)
        self.ring = n - 1 if self.closed else n
        st = [0.0]
        for i in range(1, n):
            st.append(st[-1] + math.hypot(self.pts[i][0] - self.pts[i - 1][0], self.pts[i][2] - self.pts[i - 1][2]))
        self.st = st
        self.lap = st[-1]

    def nearest(self, x, z) -> int:
        return min(range(self.ring), key=lambda i: (self.pts[i][0] - x) ** 2 + (self.pts[i][2] - z) ** 2)

    def travel(self, k: int, reverse: bool):
        n = len(self.pts)
        if self.closed:
            a, b = self.pts[(k - 1) % self.ring], self.pts[(k + 1) % self.ring]
        else:
            a, b = self.pts[max(0, k - 1)], self.pts[min(n - 1, k + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return (-tx / L, -tz / L) if reverse else (tx / L, tz / L)

    def ahead(self, s_from: float, s_to: float, reverse: bool) -> float:
        """distance from s_from to s_to in the driving direction (0..lap on a loop)"""
        d = (s_from - s_to) if reverse else (s_to - s_from)
        return d % self.lap if self.closed else d


def _verify_race_kn5(race_p: Path, main_meshes: list, fails: list) -> list:
    rnodes, rmeshes, rmats = _parse_full(race_p)
    tag = f"RACE kn5 '{race_p.name}'"
    bad = [m["name"] for m in rmeshes if not m["name"].upper().startswith(RACE_PREFIXES)]
    if bad:
        fails.append(f"{tag} carries {len(bad)} non-race mesh(es) e.g. {bad[:3]} — the export filter leaked "
                     f"(only 1WALL_RACE*/1KERB_RACE* belong in it)")
    if not any(m["name"].upper().startswith("1WALL_RACE") for m in rmeshes):
        fails.append(f"{tag} has no 1WALL_RACE* mesh (no centre chain / kerb-line strip)")
    if not any(m["name"].upper().startswith("1KERB_RACE") for m in rmeshes):
        fails.append(f"{tag} has no 1KERB_RACE* mesh (no race kerbs)")
    for m in rmeshes:
        if m["nverts"] > VERT_CAP:
            fails.append(f"OVER-CAP '{race_p.name}:{m['name']}' {m['nverts']} v > {VERT_CAP} — will split into dup meshes")
        tot = m["up"] + m["dn"]
        if m["name"].upper().startswith("1KERB") and tot and m["up"] / tot < FACE_UP_MIN:
            fails.append(f"FACE-DOWN drivable '{race_p.name}:{m['name']}' ({m['up']} up / {m['dn']} dn)")
    dups = {n: c for n, c in Counter(m["name"] for m in rmeshes if m["name"].startswith("1")).items() if c > 1}
    for name, c in dups.items():
        fails.append(f"DUPLICATE physical mesh '{race_p.name}:{name}' x{c}")
    main_names = {m["name"] for m in main_meshes if m["name"].startswith("1")}
    both = sorted(main_names & {m["name"] for m in rmeshes if m["name"].startswith("1")})
    if both:
        fails.append(f"DUPLICATE physical mesh name(s) across road + race kn5 {both[:4]} — AC loads both and "
                     f"drops dup-named meshes from collision")
    nonrace_mats = [mn for mn in rmats if not mn.upper().startswith(RACE_PREFIXES)]
    if nonrace_mats:
        fails.append(f"{tag} embeds {len(nonrace_mats)} non-race material(s) e.g. {nonrace_mats[:3]} — the "
                     f"material table was not purged (orphan meshes keep materials 'used') or the .ini was swapped")
    spawn = [n for n, _p, _z in rnodes if n.upper().startswith(SPAWN_PREFIXES)]
    if spawn:
        fails.append(f"{tag} carries spawn/timing node(s) {spawn[:4]} — those ride in the per-layout spawn kn5s only")
    size = race_p.stat().st_size
    if size >= RACE_KN5_MAX_B:
        fails.append(f"{tag} is {size / 1e6:.1f} MB ≥ {RACE_KN5_MAX_B / 1e6:.0f} MB — not the furniture-only kn5")
    return rmeshes


def _verify_spawn_kn5(lo: dict, spk: Path, dummies_p: Path, road: list, line: _Line, centre_w: list,
                      barrier_half: float, fails: list) -> None:
    lid = str(lo.get("id"))
    direction = str(lo.get("direction", "forward"))
    reverse = direction == "reverse"
    snodes, smeshes, _m = _parse_full(spk)
    if smeshes:
        fails.append(f"spawn kn5 '{spk.name}' carries {len(smeshes)} mesh(es) — a spawn kn5 is nodes only")
    ac = {n: (p, z) for n, p, z in snodes if n.upper().startswith("AC_")}
    # (b) the declared set
    if dummies_p.exists():
        declared = {k for k in json.loads(dummies_p.read_text(encoding="utf-8")) if not k.startswith("_")}
        src = dummies_p.name
    else:
        declared = set(MIN_SPAWN_SET)
        src = "the minimal set (no dummies file)"
    missing = sorted(declared - set(ac))
    if missing:
        fails.append(f"spawn kn5 '{spk.name}' lacks {len(missing)} node(s) of {src}: {missing[:6]}")
    if dummies_p.exists():
        extra = sorted(set(ac) - declared)
        if extra:
            fails.append(f"spawn kn5 '{spk.name}' carries {len(extra)} node(s) not in {src}: {extra[:6]}")
    # on-road (today's test) for every START/PIT/HOTLAP against the ROAD kn5
    if road:
        for nm, ((x, y, z), _zax) in ac.items():
            if not nm.upper().startswith(FACING):
                continue
            nr = min(road, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)
            d = math.hypot(nr[0] - x, nr[2] - z)
            if d > PIT_ROAD_MAX_M or abs(y - nr[1]) > PIT_DY_MAX_M:
                fails.append(f"SPAWN off-road '{spk.name}:{nm}': {d:.1f} m from road, dY {y - nr[1]:+.1f} m")
    else:
        fails.append("no 1ROAD mesh in the road kn5 to validate spawns against")
    # (c) heading + (d) side for every facing node
    cos_min = math.cos(math.radians(HEADING_MIN_DEG))
    heading_rows = []
    for nm, ((x, y, z), zax) in sorted(ac.items()):
        if not nm.upper().startswith(FACING):
            continue
        k = line.nearest(x, z)
        t = line.travel(k, reverse)
        zl = math.hypot(zax[0], zax[2])
        if zl < 1e-6:
            fails.append(f"HEADING '{lid}:{nm}' has no horizontal +Z (matrix degenerate)")
            continue
        dot = (zax[0] * t[0] + zax[2] * t[1]) / zl
        heading_rows.append((nm, dot))
        if dot < cos_min:
            off = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
            fails.append(f"HEADING '{lid}:{nm}' local +Z · {direction} travel = {dot:+.2f} < {cos_min:.2f} "
                         f"(faces {off:.0f}° off the travel at v{k}; the reflected atan2(tx, tz) yaw reads ≈ −1 on "
                         f"north-south roads — tools/layout_dummies.py writes atan2(tx, −tz))")
        rx, rz = _right_of(t)
        px, pz = line.pts[k][0], line.pts[k][2]
        lateral = (x - px) * rx + (z - pz) * rz
        if nm.upper().startswith(("AC_START", "AC_PIT")) and lateral <= 0.0:
            fails.append(f"SIDE '{lid}:{nm}' is {lateral:+.2f} m LEFT of the {direction} travel at v{k} — grid and "
                         f"pits sit right of travel (their own carriageway)")
        if centre_w and 0 <= k < len(centre_w) and centre_w[k] > 0 and abs(lateral) < barrier_half + CHAIN_CLEAR_M:
            fails.append(f"CHAIN '{lid}:{nm}' is {abs(lateral):.2f} m off the centreline at v{k} where the centre "
                         f"chain is declared — needs ≥ {barrier_half + CHAIN_CLEAR_M:.2f} m")
    if heading_rows:
        worst = min(heading_rows, key=lambda r: r[1])
        print(f"  [{lid}] heading: {len(heading_rows)} facing nodes, local +Z · travel min {worst[1]:+.2f} ({worst[0]})"
              f", AC_START_0 {dict(heading_rows).get('AC_START_0', float('nan')):+.2f}")
    # (e) the line + the sectors
    start = lo.get("start") or {}
    line_v = start.get("line_vertex")

    def _mid(idx):
        a = ac.get(f"AC_TIME_{idx}_L"); b = ac.get(f"AC_TIME_{idx}_R")
        if not a or not b:
            return None
        return ((a[0][0] + b[0][0]) / 2.0, (a[0][2] + b[0][2]) / 2.0)

    m0 = _mid(0)
    if m0 is None:
        fails.append(f"spawn kn5 '{spk.name}' has no AC_TIME_0_L/R pair")
        return
    k0 = line.nearest(*m0)
    if line_v is not None:
        if not (0 <= int(line_v) < line.ring):
            fails.append(f"layout {lid}: start.line_vertex {line_v} out of range")
        else:
            lp = line.pts[int(line_v)]
            dline = math.hypot(m0[0] - lp[0], m0[1] - lp[2])
            if dline > LINE_TOL_M:
                fails.append(f"LINE '{lid}': AC_TIME_0 midpoint is {dline:.1f} m from the declared line vertex v{line_v} "
                             f"(> {LINE_TOL_M} m; nearest vertex v{k0})")
    s_line = line.st[k0]
    st0 = ac.get("AC_START_0")
    if st0:
        ks = line.nearest(st0[0][0], st0[0][2])
        ahead = line.ahead(line.st[ks], s_line, reverse)
        if not (0.0 < ahead <= LINE_AHEAD_MAX_M):
            fails.append(f"LINE '{lid}': AC_TIME_0 is {ahead:.0f} m ahead of AC_START_0 in {direction} travel — "
                         f"must be 0 < d ≤ {LINE_AHEAD_MAX_M:.0f} m (the grid just behind the line)")
    prev = 0.0
    for idx in (1, 2):
        mi = _mid(idx)
        if mi is None:
            fails.append(f"spawn kn5 '{spk.name}' has no AC_TIME_{idx}_L/R pair")
            continue
        ki = line.nearest(*mi)
        a = line.ahead(s_line, line.st[ki], reverse)
        if a <= prev or (line.closed and a >= line.lap - 1.0):
            fails.append(f"SECTORS '{lid}': AC_TIME_{idx} at v{ki} is {a:.0f} m from the line in {direction} driving "
                         f"order — not after AC_TIME_{idx - 1} ({prev:.0f} m); sectors must increase in driving order (L11)")
        prev = a


def _verify_layouts(project: Path, cfg: dict, slug: str, layouts: list, kn5_dir: Path, main_nodes: list,
                    main_meshes: list, road: list) -> list[str]:
    fails: list[str] = []
    ids = [str(lo["id"]) for lo in layouts]
    # (a) spawn-free road kn5
    spawn_in_main = [n for n, _p, _z in main_nodes if n.upper().startswith(SPAWN_PREFIXES)]
    if spawn_in_main:
        fails.append(f"MULTI-LAYOUT road kn5 carries {len(spawn_in_main)} spawn/timing node(s) e.g. "
                     f"{spawn_in_main[:4]} — every layout's set rides in build/{slug}__<id>.kn5 (L8); the prep's "
                     f"multi-layout guard did not run")
    # (f) the race-furniture kn5
    race_p = kn5_dir / f"{slug}_race.kn5"
    need_race = [lid for lid, lo in zip(ids, layouts) if lo.get("race_furniture")]
    if need_race and not race_p.exists():
        fails.append(f"layout(s) {need_race} declare race_furniture but build/{race_p.name} does not exist")
    if race_p.exists():
        _verify_race_kn5(race_p, main_meshes, fails)
    # (a) exactly one spawn kn5 per id, no strays
    expected = {f"{slug}__{lid}.kn5" for lid in ids}
    present = {p.name for p in kn5_dir.glob(f"{slug}__*.kn5")}
    for name in sorted(expected - present):
        fails.append(f"missing spawn kn5 build/{name} (layout {name[len(slug) + 2:-4]!r} would have no grid)")
    for name in sorted(present - expected):
        fails.append(f"stray spawn kn5 build/{name} — not a declared layout (delete it; AC's layout list is the "
                     f"models_<id>.ini set, a stray __*.kn5 is a retired id or a typo)")
    fin = project / "data" / "finished_centerline.json"
    if not fin.exists():
        fails.append("no data/finished_centerline.json — cannot judge spawn heading / side / line (kn5 frame)")
        return fails
    fj = json.loads(fin.read_text(encoding="utf-8"))
    line = _Line(fj["points_xyz_m"], closed=bool(cfg.get("loop", True)) if "loop" in cfg else None)
    centre_w: list = []
    barrier_half = 0.335
    bb = project / "data" / "barrier_bands.json"
    if bb.exists():
        bj = json.loads(bb.read_text(encoding="utf-8"))
        cw = bj.get("centre_w_by_vertex", [])
        if len(cw) == len(line.pts):
            centre_w = cw
            barrier_half = float((bj.get("params") or {}).get("barrier_half_m", barrier_half))
        else:
            print(f"  (barrier_bands.json {len(cw)} vs finished_centerline {len(line.pts)} — chain clearance check skipped)")
    for lid, lo in zip(ids, layouts):
        spk = kn5_dir / f"{slug}__{lid}.kn5"
        if not spk.exists():
            continue
        _verify_spawn_kn5(lo, spk, project / "data" / f"dummies_{lid}.json", road, line, centre_w, barrier_half, fails)
    return fails


def verify(project_dir: str | Path) -> list[str]:
    project = Path(project_dir)
    cfg = json.loads((project / "track.config.json").read_text(encoding="utf-8"))
    slug = cfg["slug"]
    kn5 = project / "build" / f"{slug}.kn5"
    if not kn5.exists():
        return [f"kn5 not found: {kn5}"]
    nodes3, meshes, _mats = _parse_full(kn5)
    nodes = [(n, p) for n, p, _z in nodes3]
    fails: list[str] = []

    # 1. duplicate physical (1-prefixed) mesh names
    dups = {n: c for n, c in Counter(m["name"] for m in meshes if m["name"].startswith("1")).items() if c > 1}
    for name, c in dups.items():
        fails.append(f"DUPLICATE physical mesh '{name}' x{c} — AC drops dup-named meshes from collision")

    # 2 + 3. drivable meshes face-up + under the vertex cap
    for m in meshes:
        if not any(m["name"].upper().startswith(p) for p in DRIVABLE):
            continue
        tot = m["up"] + m["dn"]
        if tot and m["up"] / tot < FACE_UP_MIN:
            fails.append(f"FACE-DOWN drivable '{m['name']}' ({m['up']} up / {m['dn']} dn) — car falls through")
        if m["nverts"] > VERT_CAP:
            fails.append(f"OVER-CAP '{m['name']}' {m['nverts']} v > {VERT_CAP} — will split into dup meshes")

    road = [v for m in meshes if m["name"].upper().startswith("1ROAD") for v in m["P"]]
    layouts = [lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and lo.get("id")]
    if len(layouts) > 1:
        # MULTI-LAYOUT (0047): spawn-free road kn5 + one spawn kn5 per layout (+ the race kn5)
        fails += _verify_layouts(project, cfg, slug, layouts, kn5.parent, nodes3, meshes, road)
    else:
        # 4. AC_START + AC_PIT_* sit on a road surface
        spawns = [(nm, p) for nm, p in nodes if nm == "AC_START_0" or nm.startswith("AC_PIT")]
        if road:
            for nm, (x, y, z) in spawns:
                nr = min(road, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)
                d = math.hypot(nr[0] - x, nr[2] - z)
                if d > PIT_ROAD_MAX_M or abs(y - nr[1]) > PIT_DY_MAX_M:
                    fails.append(f"SPAWN off-road '{nm}': {d:.1f} m from road, dY {y - nr[1]:+.1f} m — will drop")
        elif spawns:
            fails.append("no 1ROAD mesh found to validate spawns against")

        # 5. per-layout spawn kn5s (multi-layout network): the main kn5 carries no spawns; each
        #    build/<slug>__<layout>.kn5 holds THIS layout's AC_START/AC_PIT. Verify they sit on the shared
        #    main kn5's roads (same drop check as the baked-in case).
        if road:
            for spk in sorted(kn5.parent.glob(f"{slug}__*.kn5")):
                snodes, _sm = _parse(spk)
                sspawns = [(nm, p) for nm, p in snodes if nm == "AC_START_0" or nm.startswith("AC_PIT")]
                if not sspawns:
                    fails.append(f"spawn kn5 '{spk.name}' has no AC_START/AC_PIT dummies")
                    continue
                for nm, (x, y, z) in sspawns:
                    nr = min(road, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)
                    d = math.hypot(nr[0] - x, nr[2] - z)
                    if d > PIT_ROAD_MAX_M or abs(y - nr[1]) > PIT_DY_MAX_M:
                        fails.append(f"SPAWN off-road '{spk.name}:{nm}': {d:.1f} m from road, dY {y - nr[1]:+.1f} m")

    # 6. terrain-poke ON THE SHIPPED BINARY — a 1GRASS vert sitting above the drivable surface AT
    #    ITS OWN XZ launches the car. audit_mesh checks this on track.obj (pre-export); this re-checks
    #    the kn5 AFTER the weld + holes_fill + export so a regression there can't ship silently.
    #    FOOTPRINT-EXACT like the audit: barycentric over the drivable triangles directly at the grass
    #    vert, near-vertical tris excluded (paved skirts are walls; the shoulder's buried hem verts are
    #    0.8 m into dirt by design), 20 m layer window for stacked legs. Vertex-radius here false-flagged
    #    the contact bench at +1.24 against buried hem tips. A regular clean build reads 0.
    grass = [v for m in meshes if m["name"].upper().startswith("1GRASS") for v in m["P"]]
    dtris: dict[tuple[int, int], list] = {}
    cell = 8.0
    for m in meshes:
        _up6 = m["name"].upper()
        # DECK ONLY (matches audit B, ledger 0028): the shoulder's ground-meet/hem quads bury
        # into cut banks by construction, and the lowest-surface pick below means they always
        # read as "the road" under a legitimate bank — 52,658 false pokes on an IMI whose
        # drive_test and audit both passed. Grass through the driven deck still fails.
        if not any(_up6.startswith(p) for p in ("1ROAD", "1KERB")) or "SHOULDER" in _up6:
            continue
        P, idx = m["P"], m["T"]
        for t in range(0, len(idx) - 2, 3):
            a, b, c = P[idx[t]], P[idx[t + 1]], P[idx[t + 2]]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx = uy * vz - uz * vy; ny = uz * vx - ux * vz; nz = ux * vy - uy * vx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1e-12
            if abs(ny) / nl < 0.5:
                continue                       # wall-steep (skirt/hem face), not a surface
            xs = (a[0], b[0], c[0]); zs = (a[2], b[2], c[2])
            for ci in range(int(min(xs) // cell), int(max(xs) // cell) + 1):
                for cj in range(int(min(zs) // cell), int(max(zs) // cell) + 1):
                    dtris.setdefault((ci, cj), []).append((a, b, c))
    if dtris and grass:
        pokes = worst = 0
        for gx, gy, gz in grass:
            surf = None
            for a, b, c in dtris.get((int(gx // cell), int(gz // cell)), ()):
                d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                if abs(d) < 1e-12:
                    continue
                w0 = ((b[2] - c[2]) * (gx - c[0]) + (c[0] - b[0]) * (gz - c[2])) / d
                w1 = ((c[2] - a[2]) * (gx - c[0]) + (a[0] - c[0]) * (gz - c[2])) / d
                w2 = 1.0 - w0 - w1
                if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                    y = w0 * a[1] + w1 * b[1] + w2 * c[1]
                    if abs(y - gy) <= 20.0 and (surf is None or y < surf):
                        surf = y
            if surf is not None and gy > surf + POKE_ABOVE_M:
                pokes += 1
                worst = max(worst, gy - surf)
        if pokes > POKE_MAX:
            fails.append(f"TERRAIN POKE x{pokes} (worst +{worst:.2f} m) — 1GRASS pokes through the "
                         f"drivable surface in the exported kn5 (>{POKE_MAX} tolerated)")
    return fails


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m scripts.ac.verify_kn5 <project-dir>")
    fails = verify(sys.argv[1])
    if fails:
        print("✗ kn5 verification FAILED:")
        for f in fails:
            print("   -", f)
        raise SystemExit(1)
    print("✓ kn5 verification passed (no dup meshes, drivable surfaces face-up, spawns on road"
          ", per-layout spawn kn5s facing their travel)")


if __name__ == "__main__":
    main()
