"""Declare the race corridors — data/barrier_bands.json VERSION 2 — from the data, before anything is authored.

Ledger 0049 (Kevin, 2026-10-11): "racetrack versions of these, we need full intersections available for
turning. And the entire other lane blocked off from access." / "We want more or less an Alvarado's width for
the entire track with deviances in various areas." / open boxes at the "Corners the race turns at", side
streets sealed. It replaces ledger 0047's shared centre K-rail chain (retired: a v1 config with
`race.centre_runs` FAILS here).

This file is the one place every consumer agrees on WHERE the race furniture stands:

  * tools/race_furniture.py + tools/author_race_furniture_blend.py sweep the strips, the closures and the
    kerbs along these bands (the declaration IS the authored line: the trimmed corners and the kerb clips are
    race_furniture's own computation, read here);
  * scripts/geometry/median_zone.py reads them per layout (MedianZone.load(project, layout=<id>)), so audit D
    / drive_test exempt a wall that stands ON a declared band of THAT layout — and only there;
  * drive_test's ``barrier_missing`` fails a declared station with no 1WALL on it (both curb strips the whole
    lap, the layout's closure at its lateral);
  * tools/no_route.py floods each layout's BUILT gate OBJ and fails any cell reached outside the corridor
    declared here;
  * scripts/ac/write_ai_line.py drafts each layout's line inside `lane_by_vertex`.

What it declares (spec: the 2026-10-11 judged corridor spec, ledger 0049):

  curb strips   both curb faces, EVERY vertex, one closed loop per side — no bridge gaps (C1: the three
                spans had no rail on most of their length; a strip end is a door), trimmed to the curb's own
                corner at the five inside-lip folds (`edge_corners`).
  zones         WHOLE street (race.corridor.whole, a vertex interval that may wrap the seam: the I-8 deck,
                the seam box, Alvarado, the hairpin box), open BOXES at the corners the race turns at
                (race.corridor.boxes, PC-2..PT+2), CLOSURE runs between them (race.corridor.closure_runs,
                PINNED: the writer fails if the zones derive anything else — "declared, validated, never
                derived silently").
  closures      per race layout (layouts[].closure_token): the jersey strip standing so the lane is
                race.corridor.clear_width_m (11.36 m, Alvarado as raced, re-measured here) face to face
                from the race-side strip face, along each island's race-side curb (pavement mode, 0.15 m
                off it), both ends PINNED on the far curb strip at the box edges (tools/race_corridor.py).
  lanes         corridors.<id>.lane_by_vertex = [y_lo, y_hi], the corridor FACES in the forward frame
                (+ = left of increasing vertex); full width at box / whole / pin vertices.
  kerbs         outside + inside at every corner (the chain no longer holds the insides), each cut to the
                longest run containing its apex that stands >= 0.05 m off every closure — EXCEPT where
                track.config.json race.kerbs.trims (hand-authored, measured: an inside kerb on a ribbon fold sits
                under the other road sheet) pulls a run back or drops the kerb (`kerbs_dropped`, with its why).
                Lake Murray since the 0049 fix round: 8 declared (1514 / 2319 inside dropped, 770 inside
                pulled back to v751-763).
  no-route      corridors.<id>.no_route.forbidden_probes (pocket centres every 25 m, island tops every 25 m,
                10 m into each mainline mouth) + the PLANNED fill itself (tools/no_route.py --planned, run
                here on the declared polylines: 0 leaks and the lap complete, or exit 1).

Self-gates (exit 1 on any): zones cover every vertex once, boxes hold their corner arcs, runs == pinned;
pins on the far strip line (+-0.01 m) on a real strip ring; rates (toward the race side <= 1:12, away
<= 1:6, pin zones at the forced rate, nothing steeper than 1:3); clear width >= 6.5 m everywhere and >= the
floor except listed island / pin-zone / convergence vertices, pocket >= 2 m behind every running closure;
closure >= 0.15 m off the AUTHORED island at every vertex (race side of every nose); 0 backward steps,
plan radius >= 20 m; mouths per policy; spawns >= 0.30 m off every face; every detected kerb declared or
dropped (2 per corner), each declared one clear of every closure; strips on every vertex; the Alvarado
re-measure; the planned no-route.

LAPS (ledger 0054, phase 2 groundwork; scripts/geometry/race_lap.py): a race layout may name its own lap
(layouts[].lap = <lap id>, declared in race.laps.<lap id>: pieces of the mainline and of connectors, its own
corridor / kerbs / roads keyed on the LAP's vertices). The writer then declares one GROUP per line: the mainline's
race layouts -> data/barrier_bands.json (exactly as before; with no lap declared nothing else changes), and each lap's
-> data/barrier_bands.<lap>.json, every vertex number in it the lap's own, from the stitched line it writes to
data/lap.<lap>.json. A lap's mouths are its pieces' side streets plus the BRANCH it abandons at every junction (sealed
by the curb strips like any side street, probed by an `xz` point ON the branch, BRANCH_PROBE_M past the curb).

Inputs (read-only; loop.blend is never opened):
  track.config.json            race.* (+ race.corridor) and layouts[] (closure_token, direction, start)
  data/centerline.local.json   points_xyz_m (engine frame x=E, y=up, z=N) + widths_m
  data/median_bands.json       island_w_by_vertex (tools/median_envelope.py)
  data/mouths.json             the mainline mouths (sealed by the curb strips — Q1)
  data/bridge.spans.auto.json  informational only (no strip gaps since ledger 0049)

Run:  python tools/barrier_bands.py <project-dir> [--out data/barrier_bands.json] [--config <track.config.json>]
                                   [--no-planned-route]
      (--config: read another config against this project's data — dry runs against the workshop copy before
      ship_sd.sh syncs airoso's track.config.json down; --no-planned-route skips self-gate 12, for quick
      looks only: the declaration then records planned_no_route "skipped" and ship_sd never uses that flag)
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIROSO = HERE.parent

CAR_HALF_W_M = 0.95          # a 1.9 m car, for the grid clearance check (race_furniture.CAR_HALF_W)


def _load_tool(stem, alias):
    """a sibling tool module by file, read-only (no sys.path side effects on the caller)"""
    spec = importlib.util.spec_from_file_location(alias, HERE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# the grid geometry is tools/layout_dummies.py's (the producer of record) — read, never restated
_LD = _load_tool("layout_dummies", "_layout_dummies_ro")
# the kerb-line strips' trimmed inside corners and the kerbs' closure clips are race_furniture's own
# computation (the same plan + trim/clip the author sweeps), read-only: the declaration IS the authored line
_RF = _load_tool("race_furniture", "_race_furniture_ro")
_RC = _load_tool("race_corridor", "_race_corridor_ro")
_MW = _load_tool("mouth_weld", "_mouth_weld_ro")   # gap_window: where gap_mouths_blend opens the host's sidewalk


def _load_lap_module():
    """scripts/geometry/race_lap.py by file (pure; no sys.path side effects)"""
    spec = importlib.util.spec_from_file_location("_race_lap_ro", AIROSO / "scripts" / "geometry" / "race_lap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_LAP = _load_lap_module()


def _load_chicane_module():
    """scripts/geometry/race_chicane.py by file (pure; no sys.path side effects) — ledger 0055"""
    spec = importlib.util.spec_from_file_location("_race_chicane_ro", AIROSO / "scripts" / "geometry" / "race_chicane.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CH = _load_chicane_module()
FOLD_APEX_MAX_VERTICES = 15  # a trimmed fold farther than this from every inside corner apex is a data defect
GRID_STAGGER_M = _LD.GRID_STAGGER_M
GRID_PITCH_M = _LD.GRID_PITCH_M
GRID_SLOTS_DEFAULT = 8
PIT_SETBACK_M = _LD.PIT_SETBACK_M
PIT_PITCH_M = _LD.PIT_PITCH_M
PIT_SLOTS_DEFAULT = 8
GRID_CLEAR_MIN_M = 0.30      # a car on a grid / pit slot stands >= this off every corridor face (verify_race F)
MOUTH_CORNER_M = 3.0         # gap_mouths_blend's CORNER_M: the mouth line spans half-width + 3 m
BARRIER_HALF_DEFAULT = 0.335 # concrete_barrier_4m.obj x extent / 2 (re-measured from the asset when present)
EDGE_CENTRE_FROM_LIP = {"road": -0.485, "walk": +0.445}   # strip centre relative to the pavement lip (Q6)
KERB_OUTER_FROM_LIP = {"road": -0.87, "walk": -0.05}      # kerb's outer edge: 0.05 m clear of the strip face
KERB_FOOTPRINT_W = 1.10      # race_furniture KERB_W 1.0 + KERB_RAMP_W 0.10: the kerb's footprint across the road
KERB_CLOSURE_CLEAR_M = 0.05  # spec §6 clip rule
PIN_TOL_M = 0.01             # a pin's y equals the far strip centre within this
ISLAND_CLEAR_M = 0.15        # the closure footprint stays this far off the AUTHORED island outline
RATE_TOL = 0.02              # 2 % over a rate limit is the solver's own 1.02 margin, not a breach
RADIUS_MIN_M = 20.0          # INVENTED floor for the closure centre's plan radius
CLEAR_WIDTH_TOL_M = 0.02     # the Alvarado re-measure must agree with clear_width_m within this
CONVERGENCE_REACH_M = 150.0  # INVENTED: a below-floor vertex this close (along) to an island is its convergence
PROBE_STEP_M = 25.0          # forbidden probes every 25 m (pockets, island tops)
MOUTH_PROBE_M = 10.0         # ... and 10 m into each mainline mouth
ISLAND_PROBE_MIN_HALF_M = 0.5
MIRROR_TRANSITION_M = 100.0  # the mirror statistic skips this far either side of an island / opening end (report only)
SWEPT_EXTEND_MAX_M = 25.0    # tools/mouth_weld.py EXTEND_MAX_M: a swept edge short of the host edge is run on this far
SWEPT_PROBE_EVERY_M = 6.0    # INVENTED (ledger 0054 P1): a swept mouth gets probes this often along its opening (and
                             # at both ends of its declared window) ...
SWEPT_PROBE_DEPTHS_M = (3.0, MOUTH_PROBE_M)   # ... each 3 m (surely on the new road) and 10 m past the host edge
MIN_CROSSING_M = 15.0        # INVENTED (ledger 0055): a declared chicane moves the lane's centre at least this far across
#                              the road (v0.18.0's College crossing, the one Kevin liked: 18.4 m in race_cw)


def _stations(pts):
    st = [0.0]
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return st


def _island_runs(island_w):
    runs, i, n = [], 0, len(island_w)
    while i < n:
        if island_w[i] <= 0:
            i += 1
            continue
        j = i
        while j < n and island_w[j] > 0:
            j += 1
        runs.append((i, j - 1))
        i = j
    return runs


def _asset_half_width(asset_path: Path) -> float:
    """Half the lateral (x) extent of the barrier module OBJ — Kevin's asset is the profile."""
    if not asset_path.exists():
        return BARRIER_HALF_DEFAULT
    xs = []
    with asset_path.open(encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("v "):
                xs.append(float(ln.split()[1]))
    if not xs:
        return BARRIER_HALF_DEFAULT
    return round((max(xs) - min(xs)) / 2.0, 3)


def _corners(ps, pts, widths, min_turn_deg):
    rb = ps.Ribbon("MAINLINE", pts, widths, True)
    out = []
    for c in ps.detect_corners(rb):
        if abs(c["D_deg"]) < min_turn_deg:
            continue
        out.append({
            "apex": rb.vertex(c["apex"]), "PC": rb.vertex(c["PC"]), "PT": rb.vertex(c["PT"]),
            "apex_station_m": round(c["apex"], 1), "PC_station_m": round(c["PC"], 1), "PT_station_m": round(c["PT"], 1),
            "sign": c["sign"], "R_apex_m": round(c["R_apex_m"], 2), "D_deg": round(c["D_deg"], 2),
            "arc_m": c["arc_m"],
        })
    out.sort(key=lambda c: c["apex"])
    return out


def _streets(corners, roads, n_ring):
    """Street per vertex: route.roads in driving order from the seam corner (apex 0), each street
    running from one corner apex to the next. Falls back to numbered streets when the counts differ."""
    apexes = sorted(c["apex"] for c in corners)
    if not apexes or apexes[0] != 0:
        apexes = [0] + [a for a in apexes if a != 0]
    names = list(roads) if len(roads) == len(apexes) else [f"street{k}" for k in range(len(apexes))]
    table = []
    for k, a in enumerate(apexes):
        b = apexes[k + 1] - 1 if k + 1 < len(apexes) else n_ring   # last street runs to the closure vertex
        table.append({"street": names[k], "vertex_from": a, "vertex_to": b})
    by_vertex = [None] * (n_ring + 1)
    for row in table:
        for v in range(row["vertex_from"], row["vertex_to"] + 1):
            by_vertex[v] = row["street"]
    return table, by_vertex


def _load_place_signs():
    """tools/place_signs.py's corner detector, read-only (that file belongs to the signs workflow)."""
    return _load_tool("place_signs", "_place_signs_ro")


def _normals(pts, m):
    out = []
    for k in range(m):
        a, b = pts[(k - 1) % m], pts[(k + 1) % m]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        out.append((-tz / L, tx / L))
    return out


def _ring_interval(a, b, m):
    return _RC.walk(a % m, b % m, m)


def _median(vals):
    s = sorted(vals)
    return s[len(s) // 2] if s else 0.0


# ---------------------------------------------------------------------------------------------
def build(project_dir, out_name: str | None = None, config_path=None, *, planned_no_route: bool = True,
          no_route_cell: float | None = None, write: bool = True, lap: str | None = None) -> dict:
    """The declaration of ONE lap group: lap None = the mainline (data/centerline.local.json, the race layouts that
    name no lap -> data/barrier_bands.json, byte-identical to before when no layout names a lap); lap <id> = the
    stitched line of race.laps.<id> (scripts/geometry/race_lap.py, written to data/lap.<id>.json) and the race
    layouts on it -> data/barrier_bands.<id>.json, every vertex number in it the LAP's own."""
    proj = Path(project_dir)
    data = proj / "data"
    lap_id = lap                    # (`lap` below is the lap LENGTH, as it always was)
    cfg_all = json.loads(Path(config_path or (proj / "track.config.json")).read_text(encoding="utf-8"))
    lap_probs = _LAP.validate(cfg_all)
    if lap_probs:
        raise SystemExit("[bands] race.laps / layouts[].lap: " + " | ".join(lap_probs))
    cfg = _LAP.config_view(cfg_all, lap_id)
    lap_rec = _LAP.stitch(proj, cfg_all, lap_id) if lap_id else None
    if lap_rec is not None and write:
        _LAP.write(proj, lap_rec)
    race = cfg.get("race") or {}
    fails: list[str] = []
    if race.get("centre_runs"):
        fails.append("track.config.json race.centre_runs is present — the ledger-0047 centre chain is retired "
                     "(ledger 0049: one closure per direction); remove centre_runs / wide_threshold_m / "
                     "interior_corners and declare race.corridor")
    cor_cfg = race.get("corridor")
    if not isinstance(cor_cfg, dict):
        raise SystemExit("[bands] track.config.json has no race.corridor — nothing to declare (ledger 0049; the "
                         "v1 centre-chain declaration is retired)")
    cl = lap_rec if lap_rec is not None else json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    n = len(pts)
    if math.dist((pts[0][0], pts[0][2]), (pts[-1][0], pts[-1][2])) > 1e-6:
        raise SystemExit("[bands] centreline is not a closed lap (v[-1] != v[0]) — the loop tool only")
    m = n - 1                                      # L13: the closure vertex repeats v0
    W = widths[:m]                                 # ring widths (the duplicate carries the last street's width)
    st = _stations(pts)
    lap = st[-1]
    if lap_rec is not None:
        # the lap's own channels: island widths, bridge spans (lap stations) and mouths (its pieces' side streets +
        # the abandoned branch at every junction) mapped through its source map by race_lap.stitch
        island_w = [float(w) for w in lap_rec["island_w_by_vertex"]]
        spans = [tuple(map(float, s)) for s in lap_rec.get("bridge_spans_m") or []]
        mouths = [dict(mo) for mo in lap_rec.get("mouths") or []]
    else:
        mb = data / "median_bands.json"
        island_w = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else [0.0] * n
        if len(island_w) != n:
            raise SystemExit(f"[bands] median_bands.json ({len(island_w)}) vs centreline ({n}) length mismatch")
        bsp = data / "bridge.spans.auto.json"
        spans = [tuple(map(float, s)) for s in json.loads(bsp.read_text(encoding="utf-8"))] if bsp.exists() else []
        mp = data / "mouths.json"
        mouths = [mo for mo in (json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else [])
                  if mo.get("host") == "MAINLINE"]
    # ledger 0055: race.chicanes (the mainline's own vertices; a lap declares none) — the island between each street-only
    # chicane's outer leg ends stands in the street layout only, so every race solve / gate here reads the RACE island
    chicanes, ch_probs = _CH.declared(cfg) if lap_rec is None else ([], [])
    fails += [f"chicanes: {p_}" for p_ in ch_probs]
    island_w_all = list(island_w)
    if lap_rec is None:
        island_w = _CH.race_island_w(island_w, cfg)

    edge_mode = str(race.get("edge_mode", "road"))
    if edge_mode != "road":
        fails.append(f"race.edge_mode {edge_mode!r}: the corridor geometry is declared for road mode only "
                     f"(the strip on the pavement, its face 0.82 m in)")
        edge_mode = "road"
    edge_inset = float(race.get("edge_inset_m", 0.82))
    if str(race.get("edge_gaps", "")).lower() != "none":
        fails.append(f"race.edge_gaps must be \"none\" (ledger 0049 C1: the curb strips run over every bridge span), "
                     f"got {race.get('edge_gaps')!r}")
    kerb_cfg = race.get("kerbs") or {}
    min_turn = float(kerb_cfg.get("min_turn_deg", 45.0))
    kerb_w = float(kerb_cfg.get("width_m", 1.0))
    kerb_h = float(kerb_cfg.get("height_m", 0.05))
    ext_lo, ext_hi = (kerb_cfg.get("outer_extension_m") or [10, 30])
    asset = AIROSO / str(race.get("barrier_profile_asset", "assets/models/concrete_barrier_4m.obj"))
    bhalf = _asset_half_width(asset)
    pitch = float(race.get("module_pitch_m", 4.04))
    height = float(race.get("barrier_height_m", 1.2))
    strip_c = edge_inset - bhalf                   # 0.485: the strip centre from the curb line
    P = _RC.params_from(cor_cfg)
    island_mode = str(cor_cfg.get("island_mode", "pavement"))
    if island_mode != "pavement":
        fails.append(f"race.corridor.island_mode {island_mode!r}: only \"pavement\" is part of this ship "
                     f"(island_top is the post-drive option, spec §5)")

    ps = _load_place_signs()
    corners = _corners(ps, pts, widths, min_turn)
    if not corners:
        fails.append("no corner with |D| >= %.0f deg found — a loop with no corners is a data error" % min_turn)
    streets, street_at = _streets(corners, (cfg.get("route") or {}).get("roads", []), m)
    corner_by_apex = {c["apex"]: c for c in corners}

    # ---- curb strips: both sides, every vertex, one closed loop per side --------------------------
    edge_strip = [1] * n
    edge_inset_v = [edge_inset] * n
    edge_corners = _RF.edge_fold_corners(pts, widths, edge_inset_v, edge_mode)
    for c in edge_corners:
        inside = [x for x in corners if ("R" if x["sign"] < 0 else "L") == c["side"]]
        near = min((min((v_ - x["apex"]) % m, (x["apex"] - v_) % m) for x in inside for v_ in c["removed"]),
                   default=m)
        if near > FOLD_APEX_MAX_VERTICES:
            fails.append(f"edge {c['side']} fold v{c['in_vertex']}..v{c['out_vertex']} is {near} vertices from every "
                         f"inside corner apex — a fold where no corner is detected is a data defect")
    edge_fold_vertices = {s_: sorted({v_ for c in edge_corners if c["side"] == s_ for v_ in c["removed"]}) for s_ in ("L", "R")}
    removed = {s_: set(edge_fold_vertices[s_]) for s_ in ("L", "R")}

    # ---- zones (declared) ----------------------------------------------------------------------------
    try:
        whole = (int(cor_cfg["whole"][0]) % m, int(cor_cfg["whole"][1]) % m)
        boxes = [{"apex": int(b["apex"]), "i": int(b["i"]) % m, "j": int(b["j"]) % m} for b in cor_cfg.get("boxes", [])]
        pinned = [(int(a) % m, int(b) % m) for a, b in cor_cfg["closure_runs"]]
    except (KeyError, TypeError, ValueError, IndexError) as e:
        raise SystemExit(f"[bands] race.corridor needs whole [i, j], boxes [{{apex, i, j}}] and closure_runs [[i, j]]: {e}")

    def free(v):
        return _RC.in_rng(v, whole[0], whole[1], m) or any(_RC.in_rng(v, b["i"], b["j"], m) for b in boxes)

    # ---- the Alvarado re-measure (clear width = what the driver gets on Alvarado as raced) ---------------
    src = str(cor_cfg.get("clear_width_source", "")).strip().lower()
    measured_clear = None
    if src:
        rows = [r for r in streets if _RF.street_slug(r["street"]).startswith(_RF.street_slug(src))]
        if not rows:
            fails.append(f"race.corridor.clear_width_source {src!r}: no street of that name in route.roads")
        else:
            r0 = rows[0]
            measured_clear = round(_median([widths[v] - 2 * edge_inset for v in range(r0["vertex_from"], r0["vertex_to"] + 1)]), 3)
            if abs(measured_clear - float(P["clear_width_m"])) > CLEAR_WIDTH_TOL_M:
                fails.append(f"clear width: {r0['street']} as raced is {measured_clear:.2f} m face to face (median of "
                             f"w - 2 x {edge_inset}) but race.corridor.clear_width_m is {P['clear_width_m']} "
                             f"(> {CLEAR_WIDTH_TOL_M} m off) — re-declare it")

    # ---- the race layouts and their closures ---------------------------------------------------------
    race_layouts = [lo for lo in cfg.get("layouts", []) if lo.get("race_furniture")]
    if not race_layouts:
        fails.append("no layouts[].race_furniture — no corridor to declare")
    ctx = _RC.prepare(pts, widths, island_w, P)
    half_auth = ctx["half_auth"]
    # ledger 0054 Phase 2 (opt-in, race.corridor.noses; absent = nothing below changes): closure-run ends declared at a
    # median nose — the closure ends at the island's race face beside the nose, a K-rail across the far carriageway
    noses, nose_fails = _noses(cor_cfg.get("noses"), pinned, island_w, m, st, bhalf)
    fails += nose_fails
    solve_free = free
    if noses:
        nose_open = {v for nz in noses for v in nz["open"]}

        def solve_free(v):
            return free(v) or v in nose_open
    corridors = {}
    tokens = {}
    for lo in race_layouts:
        lid = str(lo.get("id"))
        tok = str(lo.get("closure_token") or "")
        if not tok or not tok.isalnum() or tok != tok.lower():
            fails.append(f"layout {lid}: layouts[].closure_token must be a lower-case [a-z0-9]+ token (\"cw\" / "
                         f"\"acw\"), got {tok!r} — declared, never derived")
        elif tok in tokens:
            fails.append(f"layout {lid}: closure_token {tok!r} is also {tokens[tok]}'s — each layout owns its closure")
        tokens[tok] = lid
        direction = str(lo.get("direction", "forward"))
        if direction not in ("forward", "reverse"):
            fails.append(f"layout {lid}: direction must be forward|reverse, got {direction!r}")
            continue
        d = "cw" if direction == "forward" else "acw"
        nkw = {"nose_pins": {nz["pin"]: nz["median"] for nz in noses}} if noses else {}
        sol = _RC.solve(pts, widths, island_w, solve_free, d, P, inset=edge_inset, half=bhalf, context=ctx, **nkw)
        mine = [c_ for c_ in chicanes if lid in c_["layouts"]]
        walls, ch_lane, ch_fails = _apply_chicanes(sol, mine, direction, pts, widths, m, st, edge_inset, bhalf, P)
        fails += [f"chicanes {lid}: {f_}" for f_ in ch_fails]
        corridors[lid] = _corridor_record(lid, tok, direction, sol, ctx, P, pts, widths, n, m, st, street_at,
                                          edge_inset, bhalf, strip_c, whole, chicane_lane=ch_lane,
                                          **({"noses": noses} if noses else {}))
        _chicane_record(corridors[lid], walls, mine, direction, pts, widths, n, m, st, edge_inset, bhalf, P)

    # ---- kerbs: outside + inside at every corner, clipped against EVERY layout's closure --------------
    kerbs = _kerbs(corners, st, m, ext_lo, ext_hi)
    # the authored pull-backs / drops (race.kerbs.trims) come BEFORE the closure clip: the clip then works on
    # what will actually be swept, and a dropped kerb never reaches the author (race_furniture.apply_declared_kerbs)
    kerbs, kerbs_dropped, trim_fails = _apply_kerb_trims(kerbs, kerb_cfg.get("trims"), m)
    fails += trim_fails
    partial = {"version": 2, "edge_strip_by_vertex": edge_strip, "edge_inset_by_vertex": edge_inset_v,
               "centre_w_by_vertex": [0.0] * n, "edge_corners": edge_corners, "corridors": corridors,
               "kerbs": [dict(k) for k in kerbs], "kerbs_dropped": kerbs_dropped, "streets": streets, "corners": corners,
               "params": {"edge_mode": edge_mode, "edge_inset_m": edge_inset, "barrier_half_m": bhalf,
                          "edge_centre_from_lip_m": EDGE_CENTRE_FROM_LIP[edge_mode], "barrier_height_m": height}}
    kerbs, clip_method = _clip_kerbs(kerbs, partial, pts, widths, m, corridors, edge_inset, bhalf, edge_mode)

    # ---- sealed mouths (top-level, the 0047 shape; the per-layout policy is corridors.<id>.mouths) ----
    closed = []
    nrm = _normals(pts, m)
    # race.swept_mouths name MAINLINE weld mouths (data/mouths.json host_seg / piece / end); a lap's stitched mouths
    # (race_lap.stitch) carry none of that, so a lap keeps the symmetric window
    swept_prefixes = [str(x) for x in (race.get("swept_mouths") or [])] if lap_rec is None else []
    swept_conns = None
    # ledger 0054 P1 fix round (opt-in, track.config.json route.aprons): a corner apron (tools/author_aprons_blend.py ->
    # data/aprons.json, the apron as built) widens its weld mouth's opening on the loop edge to where its return curb
    # meets it (E) and the host's walk resumes (E_row)
    aprons = []
    if (cfg.get("route") or {}).get("aprons"):
        ap_path = data / "aprons.json"
        if not ap_path.exists():
            fails.append("route.aprons is declared but data/aprons.json is missing (run tools/author_aprons_blend.py)")
        else:
            aprons = json.loads(ap_path.read_text(encoding="utf-8")).get("aprons", [])
    for mo in mouths:
        h = int(mo["host_vertex"]) % m
        half_m = float(mo.get("connector_width_m", 10.0)) / 2.0 + MOUTH_CORNER_M
        side = "L" if int(mo.get("side", 1)) > 0 else "R"
        swept = None
        if any(str(mo.get("connector", "")).startswith(px) for px in swept_prefixes):
            # ledger 0054 P1 (race.swept_mouths, opt-in): a wide FLARED weld mouth (the J1 / J5 openings, 35-38 m at
            # the loop edge, the curb returns built into the connector) is declared where its two swept road edges
            # really cross the loop edge (+ MOUTH_CORNER_M of arc each way), not as connector width / 2 + 3 m about
            # host_vertex: at J5 that symmetric window ran out of a box the opening lies wholly inside
            if swept_conns is None:
                cp = data / "connectors.local.json"
                swept_conns = json.loads(cp.read_text(encoding="utf-8")).get("connectors", []) if cp.exists() else []
            swept = _swept_opening(mo, swept_conns, pts, widths, m, nrm, st, aprons)
            if swept is None:
                fails.append(f"mouths: {mo.get('connector')} is a swept mouth (race.swept_mouths) but its piece's "
                             f"swept edges do not reach the host edge within {SWEPT_EXTEND_MAX_M} m")
        if swept is not None:
            lo_, hi_ = swept["vertex_from"], swept["vertex_to"]
        else:
            lo_ = h
            while lo_ > 0 and st[h] - st[lo_ - 1] <= half_m:
                lo_ -= 1
            hi_ = h
            while hi_ < m - 1 and st[hi_ + 1] - st[h] <= half_m:
                hi_ += 1
        sgn = 1.0 if side == "L" else -1.0
        poly = []
        for v in range(lo_, hi_ + 1):
            nx, nz = nrm[v]
            off = sgn * (widths[v] / 2.0 + EDGE_CENTRE_FROM_LIP[edge_mode])
            poly.append([round(pts[v][0] + nx * off, 3), round(pts[v][1], 3), round(pts[v][2] + nz * off, 3)])
        rec = {"connector": mo["connector"], "host_vertex": h, "side": side,
               "connector_width_m": mo.get("connector_width_m"), "vertex_from": lo_, "vertex_to": hi_,
               "policy": "sealed: both curb strips run straight across the mouth line (Q1); per layout see "
                         "corridors.<id>.mouths",
               "polyline_xyz_m": poly}
        if swept is not None:
            rec["swept"] = swept
        if lap_rec is not None:
            # a lap's mouth (race_lap.stitch): a side street of one of its pieces, or the BRANCH it abandons at a
            # junction — probed at the point BRANCH_PROBE_M past the lap's curb ALONG the abandoned line
            rec["kind"] = mo.get("kind", "side_street")
            if mo.get("probe_xz") is not None:
                rec["probe_xz"] = [float(mo["probe_xz"][0]), float(mo["probe_xz"][1])]
        closed.append(rec)
    for lid, c in corridors.items():
        c["mouths"] = _mouth_policies(closed, c, m, widths, nrm, pts)
        c["no_route"]["forbidden_probes"] += _mouth_probes(closed, widths, m, pts, nrm)
        c["no_route"]["forbidden_probes"] += _swept_probes(closed, widths, m, st)

    # ---- grid / pit zones ----------------------------------------------------------------------------
    no_gap = []
    grid_slots = int(race.get("grid_slots", GRID_SLOTS_DEFAULT))
    pit_slots = int(race.get("pit_slots", PIT_SLOTS_DEFAULT))
    for lo in cfg.get("layouts", []):
        start = lo.get("start") or {}
        if not start:
            continue
        gv = int(start.get("grid_vertex", start.get("vertex", 0)))
        off = abs(float(start.get("offset_right_m", 0.0)))
        reverse = str(lo.get("direction", "forward")) == "reverse"
        behind = PIT_SETBACK_M + PIT_PITCH_M * pit_slots
        s_pole = st[gv]
        s0, s1 = (s_pole, min(lap, s_pole + behind)) if reverse else (max(0.0, s_pole - behind), s_pole)
        vs = [v for v in range(m) if s0 - 1e-6 <= st[v] <= s1 + 1e-6]
        if not vs:
            continue
        no_gap.append({"layout": lo.get("id"), "i": vs[0], "j": vs[-1], "station_from_m": round(s0, 1),
                       "station_to_m": round(s1, 1), "offset_right_m": off, "reverse": reverse,
                       "grid_slots": grid_slots, "pit_slots": pit_slots})

    out = {
        "version": 2,
        "_doc": "Declared race corridors (ledger 0049; replaces the 0047 centre chain). Index = vertex of "
                "data/centerline.local.json (engine frame x=E, y=up, z=N; same count as gate_centerline.json; the "
                "last entry repeats vertex 0). y = metres LEFT of the increasing-vertex tangent (left normal (-tz, "
                "tx) of the central difference). edge_strip_by_vertex: 1 everywhere — both curb strips are closed "
                "loops (no bridge gaps); band centre at +-(half_w + params.edge_centre_from_lip_m) EXCEPT at "
                "edge_corners (the strip trimmed to the curb's corner: in_vertex band point -> xz -> out_vertex, the "
                "`removed` vertices carry none). centre_w_by_vertex: all 0 (the chain is retired; removed in v3). "
                "kerbs: the race kerbs as swept (i/j after race.kerbs.trims and the closure clip; trimmed_from / "
                "clipped_from record the detector's run); kerbs_dropped: detected kerbs race.kerbs.trims drops, each "
                "with its why (nothing is authored there). "
                "corridors.<layout id>: that layout's closure (closure_y_by_vertex = the strip CENTRE lateral, null "
                "where none stands; pins included), its lane faces (lane_by_vertex [y_lo, y_hi], forward frame), "
                "zones (whole | box | pin | closure | island), runs, mouth policies and the no_route probes. Written "
                "by tools/barrier_bands.py; consumed by tools/race_furniture.py, scripts/geometry/median_zone.py, "
                "scripts/geometry/drive_test.py, scripts/geometry/audit_mesh.py, tools/no_route.py, "
                "scripts/ac/write_ai_line.py.",
        "n": n,
        "lap_m": round(lap, 1),
        "params": {
            "barrier_half_m": bhalf, "barrier_w_m": round(2 * bhalf, 3), "barrier_height_m": height,
            "module_pitch_m": pitch, "barrier_profile_asset": str(race.get("barrier_profile_asset", "")),
            "edge_mode": edge_mode, "edge_inset_m": edge_inset, "edge_centre_from_lip_m": EDGE_CENTRE_FROM_LIP[edge_mode],
            "edge_gaps": "none", "kerb_width_m": kerb_w, "kerb_height_m": kerb_h,
            "kerb_outer_from_lip_m": KERB_OUTER_FROM_LIP[edge_mode], "kerb_min_turn_deg": min_turn,
            "kerb_outer_extension_m": [float(ext_lo), float(ext_hi)], "kerb_clip": clip_method,
            "kerb_trims": [dict(t) for t in (kerb_cfg.get("trims") or []) if isinstance(t, dict)],
            "mouths": str(race.get("mouths", "sealed")),
            "edge_loop_start_vertex": (_RF.loop_start(pts, m) if hasattr(_RF, "loop_start") else None),
            "corridor": _corridor_params_echo(cor_cfg, P, measured_clear, island_mode),
        },
        "zones": {"whole": [whole[0], whole[1]], "boxes": boxes, "closure_runs": [list(r) for r in pinned],
                  "island_zones": [list(z) for z in ctx["island_zones"]], "openings": [list(z) for z in ctx["openings"]]},
        "centre_w_by_vertex": [0.0] * n,
        "edge_strip_by_vertex": edge_strip,
        "edge_inset_by_vertex": edge_inset_v,
        "runs": [],
        "corridors": corridors,
        "closed_mouths": closed,
        "edge_corners": edge_corners,
        "edge_fold_vertices": edge_fold_vertices,
        "kerbs": kerbs,
        "kerbs_dropped": kerbs_dropped,
        "no_gap_zones": no_gap,
        "streets": streets,
        "corners": corners,
        "bridge_spans_m": [list(s) for s in spans],
        "edge_gaps": [],
        "summary": {},
        "fails": [],
    }
    if lap_rec is not None:
        out["lap"] = {"id": lap_id, "line": f"data/{_LAP.lap_file(lap_id)}", "pieces": lap_rec["pieces"],
                      "joins": lap_rec["joins"], "mouths_skipped": lap_rec.get("mouths_skipped", []),
                      "_doc": "every vertex number in this file is the LAP's own (data/lap.<id>.json, "
                              "source_by_vertex maps it back to its source line); the race layouts on it: "
                              + ", ".join(str(lo.get("id")) for lo in race_layouts)}
    vctx = {"pts": pts, "widths": widths, "island_w": island_w, "half_auth": half_auth, "m": m, "n": n, "st": st,
            "params": P, "free": free, "whole": whole, "boxes": boxes, "pinned": pinned, "corners": corners,
            "corner_by_apex": corner_by_apex, "removed": removed, "layouts": race_layouts, "cfg": cfg,
            "edge_inset": edge_inset, "bhalf": bhalf, "strip_c": strip_c}
    if noses:
        # ledger 0054 Phase 2: the declared nose ends (the self-gates read them; nothing is added when none is declared)
        out["zones"]["noses"] = [{k: nz[k] for k in ("end", "median", "pin", "run")} for nz in noses]
        out["params"]["corridor"]["noses"] = cor_cfg.get("noses")
        vctx.update(noses=noses, solve_free=solve_free, ctx=ctx)
    fails += validate(out, vctx)
    # ---- 12. the PLANNED no-route: the declaration checking its own topology (not an L5 gate) ----------
    planned = {}
    if planned_no_route and corridors and not any(f.startswith("zones") for f in fails):
        nr = _load_tool("no_route", "_no_route_ro")
        for lid in corridors:
            kw = {"cell": no_route_cell} if no_route_cell else {}
            if lap_rec is not None:
                kw["line"] = (pts, widths, island_w)          # the lap, in memory (its file may not be written)
            r = nr.run(proj, lid, planned=True, bands=out, cfg=cfg, write=write, verbose=False, **kw)
            planned[lid] = {k: r[k] for k in ("fail", "leak_m2", "reached_m2", "door_clusters", "blocked",
                                              "forbidden_reached", "seconds")}
            planned[lid]["file"] = f"no_route.{lid}.planned.json"
            corridors[lid]["no_route"]["planned"] = planned[lid]
            if r["fail"]:
                fails += [f"planned no_route {lid}: {f}" for f in r["fails"]]
    elif not planned_no_route:
        for lid in corridors:
            corridors[lid]["no_route"]["planned"] = "skipped"
    out["_st"] = st
    out["summary"] = _summary(out, corridors, kerbs, edge_corners, corners, island_w, planned)
    out.pop("_st", None)
    out["fails"] = fails
    if write:
        out_path = data / (out_name or _LAP.bands_file(lap_id))
        out_path.write_text(json.dumps(out), encoding="utf-8")
        out["_path"] = str(out_path)
    _report(proj, out, fails)
    out["_ctx"] = vctx            # in memory only (after the write): validate(out, out["_ctx"]) re-runs the self-gates
    return out


def _corridor_params_echo(cor_cfg, P, measured_clear, island_mode):
    echo = {k: (dict((str(a), b) for a, b in v.items()) if isinstance(v, dict) else v) for k, v in P.items()}
    echo.update({"island_mode": island_mode, "clear_width_source": cor_cfg.get("clear_width_source"),
                 "clear_width_measured_m": measured_clear, "whole": cor_cfg.get("whole"),
                 "boxes": cor_cfg.get("boxes"), "closure_runs": cor_cfg.get("closure_runs")})
    return echo


def _corridor_record(lid, tok, direction, sol, ctx, P, pts, widths, n, m, st, street_at, inset, bhalf, strip_c,
                     whole, chicane_lane=None, noses=None):
    """corridors.<lid>: the solved closure as a declaration (forward-frame laterals per vertex). chicane_lane
    {vertex: (y_lo, y_hi)}: the declared chicanes' lane (ledger 0055) — zone 'chicane' there, the lane between the
    closure and the chicane's race-side wall (or a curb strip). noses (ledger 0054 Phase 2, opt-in): the declared
    nose ends (_noses) — their pins keep the closure's lane (the far carriageway beyond is behind the K-rail), their
    run ends join the K-rail, and `nose_walls` declares each K-rail (absent when none is declared)"""
    e = sol["e"]
    reverse = direction == "reverse"
    race_side = "L" if reverse else "R"
    closure_side = "R" if reverse else "L"
    y = [None] * m
    pins = set()
    for R in sol["runs"]:
        for v, g in zip(R["vs"], R["g"]):
            y[v] = e * g
        pins.add(R["vs"][0])
        pins.add(R["vs"][-1])
    half_auth = ctx["half_auth"]
    zone = []
    for v in range(m):
        if v in pins:
            zone.append("pin")
        elif y[v] is not None:
            zone.append("island" if half_auth[v] > 0 else "closure")
        else:
            zone.append("whole" if _RC.in_rng(v, whole[0], whole[1], m) else "box")
    nose_pin = {nz["pin"]: nz for nz in (noses or []) if nz["pin"] in pins}
    lane = _RC.lane_by_vertex(y, widths, m, "acw" if reverse else "cw", inset=inset, half=bhalf,
                              pins=pins - set(nose_pin) if nose_pin else pins)
    for k, nz in nose_pin.items():
        # the lane narrows to the closure's ONE vertex before its K-rail (the box-side neighbour of the pin): the lane
        # is lerped between vertices (drive_test, write_ai_line), and a lane still the whole street there would sweep
        # its far-side wheel paths through the K-rail in the last metres before it. The far carriageway up to the
        # K-rail stays reachable (no_route allows the open walk at full width: Corridor.nose_walls)
        nb = (k - 1) % m if (nz["median"] - k) % m == 1 else (k + 1) % m
        lane[nb] = list(lane[k])
    for v, lh in (chicane_lane or {}).items():
        lane[v] = [float(lh[0]), float(lh[1])]
        zone[v] = "chicane"
    runs = []
    for R in sol["runs"]:
        vs, rr, g = R["vs"], R["rr"], R["g"]
        fwd = sorted([vs[0], vs[-1]]) if not reverse else [vs[-1], vs[0]]
        i, j = (vs[0], vs[-1]) if not reverse else (vs[-1], vs[0])
        toward = away = 0.0
        pin_steps = [0.0, 0.0]
        for q in range(1, len(vs)):
            ds = rr[q] - rr[q - 1]
            if ds <= 1e-9:
                continue
            rate = (g[q] - g[q - 1]) / ds
            if R["zone0"][q] or R["zone0"][q - 1]:
                pin_steps[0] = max(pin_steps[0], abs(rate))
            elif R["zone1"][q] or R["zone1"][q - 1]:
                pin_steps[1] = max(pin_steps[1], abs(rate))
            elif rate > 0:
                toward = max(toward, rate)
            else:
                away = max(away, -rate)
        clears = [lane[v][1] - lane[v][0] for v in vs[1:-1]] or [0.0]
        below = []
        floor = float(P["clear_floor_m"])
        cur = None
        for q in range(1, len(vs) - 1):
            v = vs[q]
            c = lane[v][1] - lane[v][0]
            if c >= floor - 1e-6:
                cur = None
                continue
            if half_auth[v] > 0 or (R["face"][q] is not None):
                why = "island"
            elif R["zone0"][q] or R["zone1"][q]:
                why = "pin_zone"
            elif R["L"][q] > R["Lraw"][q] + 1e-6:
                why = "convergence"
            else:
                why = "unexplained"
            if cur is not None and cur[2] == why and cur[1] == vs[q - 1]:
                cur[1] = v
            else:
                cur = [v, v, why]
                below.append(cur)
        isl_spans = []
        for a, b in ctx["island_zones"]:
            if any(a <= v <= b for v in vs):
                isl_spans.append([a, b, "island"])
        for a, b in ctx["openings"]:
            if any(a <= v <= b for v in vs):
                isl_spans.append([a, b, "opening"])
        rad, rad_v, back = _RC.plan_radius(pts, m, vs, y)
        runs.append({
            "i": i, "j": j, "travel_from": vs[0], "travel_to": vs[-1], "travel": "decreasing" if reverse else "increasing",
            "street": street_at[min(fwd)], "street_end": street_at[max(fwd)], "length_m": round(rr[-1], 1),
            "ends": [_run_end(vs[0], y, closure_side, "in", nose_pin), _run_end(vs[-1], y, closure_side, "out", nose_pin)],
            "island_spans": isl_spans,
            "max_rate": {"toward": _ratio(toward), "away": _ratio(away),
                         "pin_in": _ratio(R["k_pin"][0]), "pin_out": _ratio(R["k_pin"][1]),
                         "pin_in_built": _ratio(pin_steps[0]), "pin_out_built": _ratio(pin_steps[1])},
            "pin_zone_m": float(P["pin_zone_m"]),
            "clear_min_m": round(min(clears), 3), "clear_median_m": round(_median(clears), 3),
            "below_floor": [list(b) for b in below],
            "min_radius_m": round(rad, 1) if rad < float("inf") else None, "min_radius_vertex": rad_v,
            "backward_steps": back, "infeasible": R["infeas"], "sor_sweeps": R["iters"],
        })
    # forbidden probes: pockets behind the closure + island tops (+ the mouths, added by the caller)
    probes = []
    for R in sol["runs"]:
        vs, rr = R["vs"], R["rr"]
        next_s = 0.0
        for q, v in enumerate(vs[1:-1], start=1):
            if rr[q] < next_s:
                continue
            face = widths[v] / 2.0 - inset
            if closure_side == "L":
                lo_, hi_ = y[v] + bhalf, face
            else:
                lo_, hi_ = -face, y[v] - bhalf
            if hi_ - lo_ >= float(P["pocket_min_m"]) and half_auth[v] <= 0:
                probes.append({"vertex": v, "y": round(0.5 * (lo_ + hi_), 3), "why": "pocket"})
                next_s = rr[q] + PROBE_STEP_M
    for a, b in ctx["island_zones"]:
        next_s = -1.0
        for v in range(a, b + 1):
            if half_auth[v] >= ISLAND_PROBE_MIN_HALF_M and st[v] >= next_s:
                probes.append({"vertex": v, "y": 0.0, "why": "island"})
                next_s = st[v] + PROBE_STEP_M
    yr = [None if v is None else round(v, 4) for v in y]
    zr = zone
    rec = {
        "token": tok, "direction": direction, "travel": "decreasing" if reverse else "increasing",
        "race_side": race_side, "closure_side": closure_side,
        "zone_by_vertex": zr + [zr[0]],
        "closure_y_by_vertex": yr + [yr[0]],
        "lane_by_vertex": [[round(a, 4), round(b, 4)] for a, b in lane] + [[round(lane[0][0], 4), round(lane[0][1], 4)]],
        "pins": sorted(pins),
        "runs": runs,
        "mouths": [],
        "no_route": {"seed": "AC_START_0", "probe_r_m": 0.5, "tol_m": 0.75, "forbidden_probes": probes},
    }
    if nose_pin:
        rec["nose_walls"] = [_nose_wall(nz, y, e, closure_side, pts, widths, m, strip_c, bhalf)
                             for _p, nz in sorted(nose_pin.items())]
    return rec


def _run_end(v, y, closure_side, role, nose_pin):
    """a closure run end as declared: pinned in the far curb strip, or (ledger 0054 Phase 2) ending at a median nose
    against its K-rail (joins "nose"; only then the `nose` key)"""
    if v in nose_pin:
        nz = nose_pin[v]
        return {"vertex": v, "y": round(y[v], 4), "joins": "nose", "role": role,
                "nose": {"median": nz["median"], "end": nz["end"]}}
    return {"vertex": v, "y": round(y[v], 4), "joins": "edge_" + closure_side, "role": role}


def _nose_wall(nz, y, e, closure_side, pts, widths, m, strip_c, bhalf):
    """the K-rail across the far carriageway at a nose pin P (ledger 0054 Phase 2): along P's normal, from the
    closure's RACE face (y + e x half: the closure's end cap stands inside the K-rail's footprint, a flush L) to the
    far curb strip's centre (its far cap buried in that strip, as a closure pin is). y = forward-frame laterals."""
    k = nz["pin"]
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    nx, nzn = -tz / L, tx / L
    y_from = y[k] + e * bhalf
    y_to = -e * (widths[k] / 2.0 - strip_c)
    poly = [[round(pts[k][0] + nx * yy, 3), round(pts[k][1], 3), round(pts[k][2] + nzn * yy, 3)] for yy in (y_from, y_to)]
    return {"vertex": k, "median": nz["median"], "end": nz["end"], "y_from": round(y_from, 4), "y_to": round(y_to, 4),
            "joins": ["closure", "edge_" + closure_side], "length_m": round(abs(y_to - y_from), 3),
            "polyline_xyz_m": poly}


def _noses(spec, pinned, island_w, m, st, bhalf):
    """race.corridor.noses (ledger 0054 Phase 2, opt-in): [{end, median, why}] -> ([{end, median, pin, run, open,
    why}], fails). `end` is a declared closure-run end (a box edge); `median` the first (run start) or last (run end)
    vertex of an AUTHORED island run (tools/author_median_blend.py's >= 6 vertices) inside that run, with no authored
    island between the two; the pin P is the vertex beside the nose toward the box, and its K-rail stands
    >= ISLAND_CLEAR_M off the nose along the road. Every refusal is a fail; a refused nose is not applied."""
    if not spec:
        return [], []
    if not isinstance(spec, list):
        return [], [f"noses: race.corridor.noses must be a list of {{end, median}}, got {type(spec).__name__}"]
    iw = [float(x) for x in island_w[:m]] + [0.0] * max(0, m - len(island_w))
    runs = _RC.island_runs(iw, m)
    half = _RC.authored_half(iw, m)
    fails, out, seen = [], [], set()
    for nz in spec:
        try:
            E, M = int(nz["end"]) % m, int(nz["median"]) % m
        except (KeyError, TypeError, ValueError) as e_:
            fails.append(f"noses: an entry needs integer end and median ({e_!r}): {nz!r}")
            continue
        run = next((r for r in pinned if E in (r[0], r[1])), None)
        if run is None:
            fails.append(f"noses: end v{E} is not an end of any race.corridor.closure_runs {sorted(pinned)}")
            continue
        if E in seen:
            fails.append(f"noses: end v{E} is declared twice")
            continue
        seen.add(E)
        geo = _RC.nose_open(E, M, run, m)
        if geo is None:
            fails.append(f"noses: median v{M} is not strictly inside closure run v{run[0]}-v{run[1]}")
            continue
        pin, opn = geo
        at_start = E == run[0]
        if not any((r[0] if at_start else r[1]) == M for r in runs):
            fails.append(f"noses: v{M} is not the {'first' if at_start else 'last'} vertex of an authored island run "
                         f"(>= {_RC.ISLAND_MIN_VERTS} vertices) — not a nose")
            continue
        if pin == E:
            fails.append(f"noses: the nose v{M} stands beside the box edge v{E} — nothing to end the closure at")
            continue
        if any(half[v] > 0 for v in opn):
            fails.append(f"noses: an authored island stands between the box edge v{E} and the nose v{M}")
            continue
        gap = abs(st[M] - st[pin]) - bhalf
        if gap < ISLAND_CLEAR_M - 1e-6:
            fails.append(f"noses: the K-rail at v{pin} stands {gap:.2f} m off the nose v{M} along the road "
                         f"(< {ISLAND_CLEAR_M} m)")
            continue
        out.append({"end": E, "median": M, "pin": pin, "run": [run[0], run[1]], "open": opn,
                    "why": str(nz.get("why") or "")})
    return out, fails


def _travel_walk(a, b, m, direction):
    """vertices from a to b in the layout's travel order (forward: increasing, reverse: decreasing), both included"""
    if direction == "reverse":
        return list(reversed(_RC.walk(b % m, a % m, m)))
    return _RC.walk(a % m, b % m, m)


def _apply_chicanes(sol, chicanes, direction, pts, widths, m, st, inset, bhalf, P):
    """Ledger 0055 (Kevin: "for the racetrack versions, I do like the chicane that kind of goes from one side of the
    road across to the other and back"): carry this layout's lane across the road and back at each declared chicane.

    Works in g (metres toward THIS layout's race side, the solver's frame; race strip centre g = +(w/2 - strip_c),
    far strip centre g = -(w/2 - strip_c)). The lane enters with its solved faces [g_A + half, F] (F = w/2 - inset, the
    race-side strip face) and width W. Over the out leg (in travel order) both faces move toward the far side by the
    S of race_chicane.slope_shape: hi = F (1 - 2 f) + W f, lo = hi - W — so at the leg's end the lane is [-F, -F + W],
    against the far curb strip. Two walls carry it: the CLOSURE (g_A = lo - half), which ends pinned in the far curb
    strip at the out leg's end (the run that held the chicane is split there), and the RACE-SIDE wall (g_C = hi +
    half), which starts pinned in the race-side curb strip at the out leg's start. Between the legs the closure is gone
    (the lane runs to the far curb strip) and the race-side wall holds the line; the back leg mirrors the out leg, the
    width easing from W to the solved width where it ends, the closure restarting pinned in the far strip.

    MUTATES sol: the closure run holding the chicane is split into the part before the out leg's end and the part
    from the back leg's start, its g overridden over both legs (zone flags, pin rates and bound rows sliced and
    re-derived). Returns (walls [{name, vs (travel order), g}], lane {vertex: (y_lo, y_hi) forward frame}, fails)."""
    fails = []
    e = sol["e"]
    zone_m = float(P["pin_zone_m"])
    lane = {}
    walls = []
    for ch in chicanes:
        out_leg, back_leg = _CH.legs_in_travel(ch, direction)
        span = _travel_walk(out_leg[0], back_leg[1], m, direction)
        R = next((R_ for R_ in sol["runs"] if out_leg[0] in R_["vs"] and back_leg[1] in R_["vs"]), None)
        if R is None:
            fails.append(f"{ch['name']}: v{out_leg[0]}..v{back_leg[1]} is not inside ONE closure run of this layout "
                         f"(a chicane crosses a carriageway the closure divides off)")
            continue
        vs = R["vs"]
        q_in, q_out_end = vs.index(out_leg[0]), vs.index(out_leg[1])
        q_back0, q_out = vs.index(back_leg[0]), vs.index(back_leg[1])
        if not (0 < q_in < q_out_end <= q_back0 < q_out < len(vs) - 1):
            fails.append(f"{ch['name']}: the legs are not strictly inside the closure run v{vs[0]}..v{vs[-1]} in travel "
                         f"order ({q_in}, {q_out_end}, {q_back0}, {q_out} of {len(vs)})")
            continue

        def F(v):
            return widths[v] / 2.0 - inset

        def arc(qa, qb):
            return [R["rr"][q] - R["rr"][qa] for q in range(qa, qb + 1)]
        g = list(R["g"])
        W0 = F(vs[q_in]) - (g[q_in] + bhalf)
        W1 = F(vs[q_out]) - (g[q_out] + bhalf)
        hi_by, gA, gC = {}, {}, {}
        a_out = arc(q_in, q_out_end)
        for k, q in enumerate(range(q_in, q_out_end + 1)):
            v = vs[q]
            f = _CH.slope_shape(a_out[k] / a_out[-1])
            hi = F(v) * (1.0 - 2.0 * f) + W0 * f
            hi_by[v], gA[v], gC[v] = (hi - W0, hi), hi - W0 - bhalf, hi + bhalf
        for q in range(q_out_end + 1, q_back0):
            v = vs[q]
            hi = -F(v) + W0
            hi_by[v], gC[v] = (-F(v), hi), hi + bhalf
        a_back = arc(q_back0, q_out)
        for k, q in enumerate(range(q_back0, q_out + 1)):
            v = vs[q]
            t = a_back[k] / a_back[-1]
            f = _CH.slope_shape(1.0 - t)
            W = W0 + (W1 - W0) * t
            hi = F(v) * (1.0 - 2.0 * f) + W * f
            hi_by[v], gA[v], gC[v] = (hi - W, hi), hi - W - bhalf, hi + bhalf
        # the closure's two pins land EXACTLY on the far strip centre, the wall's on the race strip centre
        for v in (vs[q_out_end], vs[q_back0]):
            gA[v] = -(widths[v] / 2.0 - (inset - bhalf))
        for v in (vs[q_in], vs[q_out]):
            gC[v] = widths[v] / 2.0 - (inset - bhalf)
        for q in range(q_in, q_out + 1):
            if vs[q] in gA:
                g[q] = gA[vs[q]]

        def part(qa, qb, k_new0=None, k_new1=None):
            """a slice of the run (R1 = start .. out leg end, pinned in the far strip; R2 = back leg start .. end)"""
            sub = {"vs": vs[qa:qb + 1], "g": g[qa:qb + 1], "iters": R["iters"],
                   "infeas": [v for v in R["infeas"] if v in vs[qa:qb + 1]]}
            for key in ("t", "L", "Lraw", "U", "isl", "face", "g_far", "kc", "kd"):
                sub[key] = R[key][qa:qb + 1]
            rr0 = R["rr"][qa]
            sub["rr"] = [x - rr0 for x in R["rr"][qa:qb + 1]]
            L_ = sub["rr"][-1]
            sub["zone0"] = [x <= zone_m for x in sub["rr"]]
            sub["zone1"] = [L_ - x <= zone_m for x in sub["rr"]]
            k0, k1 = R["k_pin"]
            sub["k_pin"] = (k0 if k_new0 is None else k_new0, k1 if k_new1 is None else k_new1)
            return sub

        def leg_rate(gx, qa, qb):
            best = 0.0
            for q in range(qa + 1, qb + 1):
                ds = R["rr"][q] - R["rr"][q - 1]
                if ds > 1e-9:
                    best = max(best, abs(gx[vs[q]] - gx[vs[q - 1]]) / ds)
            return best
        kA_out = leg_rate(gA, q_in, q_out_end)
        kA_back = leg_rate(gA, q_back0, q_out)
        R1 = part(0, q_out_end, k_new1=kA_out * 1.02)
        R2 = part(q_back0, len(vs) - 1, k_new0=kA_back * 1.02)
        i = sol["runs"].index(R)
        sol["runs"][i:i + 1] = [R1, R2]
        for v in span:
            sol["g"][v] = gA.get(v)
        for v, (lo_g, hi_g) in hi_by.items():
            # forward frame: y = e * g; the lane's two faces swap order when e = -1
            a_, b_ = e * lo_g, e * hi_g
            lane[v] = (min(a_, b_), max(a_, b_))
        wall_vs = vs[q_in:q_out + 1]
        walls.append({"name": ch["name"], "vs": wall_vs, "g": [gC[v] for v in wall_vs],
                      "out_leg": out_leg, "back_leg": back_leg, "lane_w_m": [round(W0, 3), round(W1, 3)],
                      "rate_closure": [kA_out, kA_back],
                      "rate_wall": [leg_rate(gC, q_in, q_out_end), leg_rate(gC, q_back0, q_out)]})
    return walls, lane, fails


def _chicane_record(c, walls, chicanes, direction, pts, widths, n, m, st, inset, bhalf, P):
    """corridors.<lid> gains, per declared chicane of THIS layout (ledger 0055): chicane_walls[] (the race-side wall:
    i / j forward, travel_from / travel_to, its pins on the race-side curb strip, rates, radius), the full-length
    race_wall_y_by_vertex (the wall's CENTRE lateral, forward frame, null elsewhere — the consumers' one row) and
    chicanes[] (what the driver gets: the lane's crossing, its legs and width); plus a forbidden probe every
    PROBE_STEP_M in the pocket the race-side wall closes off (between it and the race-side curb strip)"""
    e = -1.0 if c["race_side"] == "R" else 1.0
    yw = [None] * n
    recs, summ = [], []
    probes = c["no_route"]["forbidden_probes"]
    pocket_min = float(P["pocket_min_m"])
    for w in walls:
        vs, g = w["vs"], w["g"]
        for v, gv in zip(vs, g):
            yw[v] = round(e * gv, 4)
        fwd = sorted([vs[0], vs[-1]])
        rad, rad_v, back = _RC.plan_radius(pts, m, vs, yw)
        recs.append({
            "name": w["name"], "i": fwd[0], "j": fwd[1], "travel_from": vs[0], "travel_to": vs[-1],
            "side": c["race_side"], "joins": "edge_" + c["race_side"],
            "ends": [{"vertex": vs[0], "y": yw[vs[0]], "joins": "edge_" + c["race_side"], "role": "in"},
                     {"vertex": vs[-1], "y": yw[vs[-1]], "joins": "edge_" + c["race_side"], "role": "out"}],
            "length_m": round(sum(math.hypot(pts[b][0] - pts[a][0], pts[b][2] - pts[a][2]) for a, b in zip(vs, vs[1:])), 1),
            "max_rate": {"out_leg": _ratio(w["rate_wall"][0]), "back_leg": _ratio(w["rate_wall"][1])},
            "min_radius_m": round(rad, 1) if rad < float("inf") else None, "min_radius_vertex": rad_v,
            "backward_steps": back})
        lane = c["lane_by_vertex"]
        mids = [0.5 * (lane[v][0] + lane[v][1]) for v in vs]
        summ.append({"name": w["name"], "out_leg": w["out_leg"], "back_leg": w["back_leg"],
                     "lane_w_m": w["lane_w_m"], "crossing_m": round(max(mids) - min(mids), 2),
                     "closure_rate": [_ratio(k) for k in w["rate_closure"]],
                     "wall_rate": [_ratio(k) for k in w["rate_wall"]],
                     "hold_m": round(abs(st[w["back_leg"][0]] - st[w["out_leg"][1]]), 1)})
        # the pocket behind the race-side wall (toward the race-side curb strip): a probe every PROBE_STEP_M of
        # TRAVEL — |st - st at the last probe|, since vs runs backward along the stations on a reverse layout (the
        # gates lens, 0055 round 2: race_acw got 1 pocket probe where race_cw got 12)
        last_s = None
        for v, gv in zip(vs[1:-1], g[1:-1]):
            face = widths[v] / 2.0 - inset
            lo_g, hi_g = gv + bhalf, face
            if hi_g - lo_g >= pocket_min and (last_s is None or abs(st[v] - last_s) >= PROBE_STEP_M):
                probes.append({"vertex": v, "y": round(e * 0.5 * (lo_g + hi_g), 3), "why": "chicane_pocket"})
                last_s = st[v]
    c["race_wall_y_by_vertex"] = yw
    c["chicane_walls"] = recs
    c["chicanes"] = summ


def _ratio(k):
    """lateral per metre -> the x of 1:x (None for a flat run)"""
    return round(1.0 / k, 2) if k > 1e-9 else None


def _kerbs(corners, st, m, ext_lo, ext_hi):
    """outside kerb on the lip outside the turn (symmetric about the apex, extended E = clamp(2 R, 10, 30) past
    PC/PT) + inside kerb on the detector's own arc, at every corner (the chain no longer holds the insides)"""
    kerbs = []
    for c in corners:
        apex, pc, pt = c["apex"], c["PC"], c["PT"]
        inside = "R" if c["sign"] < 0 else "L"
        outside = "L" if inside == "R" else "R"
        E = max(float(ext_lo), min(float(ext_hi), 2.0 * c["R_apex_m"]))

        def _back(v0, dist):
            v1, walked = v0, 0.0
            while walked < dist:
                nv = v1 - 1 if v1 > 0 else m - 1
                walked += st[v1] - st[nv] if v1 > 0 else st[m] - st[m - 1]
                v1 = nv
            return v1

        def _fwd(v0, dist):
            v1, walked = v0, 0.0
            while walked < dist:
                nv = v1 + 1 if v1 < m else 1
                walked += st[nv] - st[v1] if v1 < m else st[1] - st[0]
                v1 = nv
            return v1 % m
        oi, oj = _back(pc, E), _fwd(pt, E)
        kerbs.append({"apex": apex, "side": outside, "kind": "outside", "i": oi, "j": oj, "wraps": oi > oj,
                      "R_apex_m": c["R_apex_m"], "D_deg": c["D_deg"], "extension_m": round(E, 1)})
        kerbs.append({"apex": apex, "side": inside, "kind": "inside", "i": pc, "j": pt, "wraps": pc > pt,
                      "R_apex_m": c["R_apex_m"], "D_deg": c["D_deg"], "extension_m": 0.0})
    return kerbs


KERB_KIND = {"inside": "inside", "in": "inside", "outside": "outside", "out": "outside"}


def _apply_kerb_trims(kerbs, trims, m):
    """track.config.json race.kerbs.trims — HAND-AUTHORED, measured pull-backs of the detector's kerb runs (ledger
    0049 fix round: an inside kerb laid over a ribbon fold sits under the other road sheet — invisible from the
    seat, and audit K counts it against the lower sheet). Each entry is {apex, kind: inside | outside, why} plus
    either drop: true (the kerb leaves the declaration and is listed in kerbs_dropped — nothing is swept there)
    or i and / or j (a PULL-BACK: both inside the detected run, in its walk order, i before j). The kept kerb
    records trimmed_from [i, j] and trim {why}. Returns (kerbs, dropped, fails); an entry that matches no kerb,
    names one twice, lengthens a run or carries no `why` FAILS — the declaration never guesses."""
    fails, dropped = [], []
    if not trims:
        return kerbs, dropped, fails
    if not isinstance(trims, list):
        return kerbs, dropped, [f"race.kerbs.trims must be a list of {{apex, kind, why, drop | i / j}}, got {trims!r}"]
    by = {(int(k["apex"]), k["kind"]): k for k in kerbs}
    seen = set()
    for t in trims:
        try:
            key = (int(t["apex"]), KERB_KIND[str(t["kind"]).lower()])
        except (KeyError, TypeError, ValueError):
            fails.append(f"race.kerbs.trims: {t!r} needs apex (vertex) and kind (inside | outside)")
            continue
        what = f"race.kerbs.trims apex v{key[0]} {key[1]}"
        k = by.get(key)
        if k is None:
            fails.append(f"{what}: no such kerb (detected: {sorted(by)})")
            continue
        if key in seen:
            fails.append(f"{what}: named twice")
            continue
        seen.add(key)
        why = str(t.get("why") or "").strip()
        if not why:
            fails.append(f"{what}: no `why` — a trim is an authored decision; record the measurement behind it")
            continue
        if t.get("drop"):
            if "i" in t or "j" in t:
                fails.append(f"{what}: drop and i / j together — a dropped kerb has no run")
                continue
            dropped.append({"apex": k["apex"], "side": k["side"], "kind": k["kind"], "i": k["i"], "j": k["j"],
                            "why": why})
            continue
        ks = _RC.walk(int(k["i"]) % m, int(k["j"]) % m, m)
        try:
            ni = int(t.get("i", k["i"])) % m
            nj = int(t.get("j", k["j"])) % m
        except (TypeError, ValueError):
            fails.append(f"{what}: i / j must be vertex numbers, got {t.get('i')!r} / {t.get('j')!r}")
            continue
        if ni not in ks or nj not in ks or ks.index(ni) >= ks.index(nj):
            fails.append(f"{what}: v{ni}-v{nj} is not a pull-back inside the detected run v{k['i']}-v{k['j']}")
            continue
        if (ni, nj) != (k["i"], k["j"]):
            k["trimmed_from"] = [k["i"], k["j"]]
            k["trim"] = {"why": why}
            k["i"], k["j"] = ni, nj
            k["wraps"] = ni > nj
    gone = {(d["apex"], d["kind"]) for d in dropped}
    return [k for k in kerbs if (int(k["apex"]), k["kind"]) not in gone], dropped, fails


def _kerb_band(widths, k, side, inset):
    """forward-frame lateral interval [lo, hi] of a kerb's footprint at vertex k on `side`"""
    outer = widths[k] / 2.0 - inset - KERB_CLOSURE_CLEAR_M
    inner = outer - KERB_FOOTPRINT_W
    return (inner, outer) if side == "L" else (-outer, -inner)


def _gap(a, b):
    """signed gap between intervals a and b (negative = overlap)"""
    return max(b[0] - a[1], a[0] - b[1])


def _kerb_clear(widths, k, side, corridors, inset, bhalf):
    best, by = float("inf"), []
    kb = _kerb_band(widths, k, side, inset)
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"][k]
        if y is None:
            continue
        g = _gap(kb, (y - bhalf, y + bhalf))
        if g < best:
            best = g
        if g < KERB_CLOSURE_CLEAR_M:
            by.append(lid)
    return best, by


def _clip_kerbs(kerbs, partial, pts, widths, m, corridors, inset, bhalf, mode):
    """the spec §6 clip: race_furniture.kerb_closure_clips (the author's own station-level clip) when present,
    else a vertex-level clip with the same rule. Every kerb records clipped_from / clip."""
    method = "vertex"
    rf_rows = None
    if hasattr(_RF, "kerb_closure_clips") and corridors:
        try:
            rf_rows = _RF.kerb_closure_clips(pts, widths, partial, mode)
            method = "race_furniture.kerb_closure_clips"
        except Exception as e:  # noqa: BLE001 — the author's clip is in flux; the gate below still holds
            print(f"[bands] race_furniture.kerb_closure_clips raised {e!r} — vertex-level clip used")
            rf_rows = None
    out = []
    for k in kerbs:
        k = dict(k)
        ks = _RC.walk(k["i"], k["j"], m)
        if rf_rows is not None:
            row = next((r for r in rf_rows if int(r["apex"]) == k["apex"] and str(r["side"]).upper() == k["side"]), None)
            if row is not None:
                ni, nj = int(row["i"]) % m, int(row["j"]) % m
                if (ni, nj) != (k["i"], k["j"]):
                    k["clipped_from"] = [k["i"], k["j"]]
                    k["clip"] = {"by": row.get("by", []), "stations_removed": row.get("stations_removed")}
                k["i"], k["j"] = ni, nj
                k["wraps"] = ni > nj
                out.append(k)
                continue
        apex_q = ks.index(k["apex"]) if k["apex"] in ks else len(ks) // 2
        ok = [_kerb_clear(widths, v, k["side"], corridors, inset, bhalf)[0] >= KERB_CLOSURE_CLEAR_M for v in ks]
        lo_ = apex_q
        while lo_ > 0 and ok[lo_ - 1]:
            lo_ -= 1
        hi_ = apex_q
        while hi_ < len(ks) - 1 and ok[hi_ + 1]:
            hi_ += 1
        if (lo_, hi_) != (0, len(ks) - 1):
            by = sorted({lid for v in ks[:lo_] + ks[hi_ + 1:] for lid in _kerb_clear(widths, v, k["side"], corridors, inset, bhalf)[1]})
            k["clipped_from"] = [k["i"], k["j"]]
            k["clip"] = {"by": by, "vertices_removed": [lo_, len(ks) - 1 - hi_]}
            k["i"], k["j"] = ks[lo_], ks[hi_]
            k["wraps"] = k["i"] > k["j"]
        out.append(k)
    return out, method


def _vertex_policy(side, cor, v):
    """the policy one host vertex of a mouth needs: the race-side strip seals the race side; on the far side a
    closure standing there (closure / island zone) puts the mouth behind it, else (whole / box / pin) the far curb
    strip seals it - at a PIN the closure is pinned ON the far strip, so the far strip is the seal"""
    if side == cor["race_side"]:
        return "sealed_race_strip"
    if cor["closure_y_by_vertex"][v] is not None and cor["zone_by_vertex"][v] in ("closure", "island"):
        return "behind_closure"
    return "sealed_far_strip"


def _mouth_policies(closed, cor, m, widths, nrm, pts):
    rows = []
    for mo in closed:
        h = int(mo["host_vertex"]) % m
        if mo.get("swept"):
            # ledger 0054 A7: a swept mouth gets its policy per host vertex, split into runs where it changes (the
            # J1 opening runs past race_cw's box-end pin v1521 into the exit funnel: the box part stays
            # sealed_far_strip, the funnel part is behind the closure)
            vs = _RC.walk(mo["vertex_from"], mo["vertex_to"], m)
            runs = []
            for v in vs:
                pol = _vertex_policy(mo["side"], cor, v)
                if runs and runs[-1][0] == pol:
                    runs[-1][2] = v
                else:
                    runs.append([pol, v, v])
            for k, (pol, a, b) in enumerate(runs):
                row = {"connector": mo["connector"], "host_vertex": h, "side": mo["side"], "policy": pol,
                       "vertex_from": a, "vertex_to": b}
                if len(runs) > 1:
                    row["split"] = {"part": k + 1, "of": len(runs), "why": "ledger 0054 A7: the opening crosses a zone "
                                    "boundary of this corridor; the policy is per vertex"}
                else:
                    row["split"] = {"part": 1, "of": 1, "why": "swept mouth: judged on every vertex"}
                rows.append(row)
            continue
        if mo["side"] == cor["race_side"]:
            pol = "sealed_race_strip"
        elif cor["closure_y_by_vertex"][h] is not None:
            pol = "behind_closure"
        else:
            pol = "sealed_far_strip"
        rows.append({"connector": mo["connector"], "host_vertex": h, "side": mo["side"], "policy": pol,
                     "vertex_from": mo["vertex_from"], "vertex_to": mo["vertex_to"]})
    return rows


def _swept_probes(closed, widths, m, st):
    """ledger 0054 P1: a swept mouth is probed ACROSS its opening (every SWEPT_PROBE_EVERY_M of host arc, 1.5 m in from
    each end, at 3 m and 10 m past the host edge) - the J1 opening's funnel part past v1521 included - besides the one
    probe at host_vertex every mouth gets"""
    out = []
    for mo in closed:
        sw = mo.get("swept")
        if not sw:
            continue
        sgn = 1.0 if mo["side"] == "L" else -1.0
        a_, b_ = float(sw["edge_vertex_from"]), float(sw["edge_vertex_to"])

        def arc_of(vf):
            v = int(math.floor(vf))
            return st[v] + (st[min(v + 1, len(st) - 1)] - st[v]) * (vf - v)
        s0, s1 = arc_of(a_) + 1.5, arc_of(b_) - 1.5
        vs = []
        k = 0
        while s0 + k * SWEPT_PROBE_EVERY_M <= s1 + 1e-9:
            s = s0 + k * SWEPT_PROBE_EVERY_M
            vs.append(min(range(m), key=lambda q: abs(st[q] - s)))
            k += 1
        for v in [mo["vertex_from"]] + vs + [mo["vertex_to"]]:     # the declared window's two ends too
            if any(p_["vertex"] == v and p_["why"].startswith(f"swept mouth {mo['connector']}") for p_ in out):
                continue
            for dpt in SWEPT_PROBE_DEPTHS_M:
                out.append({"vertex": v, "y": round(sgn * (widths[v] / 2.0 + dpt), 3),
                            "why": f"swept mouth {mo['connector']} (v{v}, {dpt:.0f} m in)"})
    return out


def _swept_opening(mo, conns, pts, widths, m, nrm, st, aprons=()):
    """where the mouth's piece really opens the host edge: its centre smoothed as the assembler sweeps it, each road
    edge (+- width / 2, centred tangent) walked from the outer end toward the cut, its first crossing of the host edge
    line on the mouth's side (an edge short of it run on along its last direction up to SWEPT_EXTEND_MAX_M, as the
    weld does); returns fractional edge vertices and the declared whole-vertex window (+ MOUTH_CORNER_M of arc)"""
    piece = next((c for c in conns if c["name"] == mo.get("piece")), None)
    if piece is None:
        return None
    P = [(float(p[0]), float(p[2])) for p in piece["points_xyz_m"]]
    Wd = [float(w) for w in piece["widths_m"]]
    if mo.get("end") == "start":
        P, Wd = P[::-1], Wd[::-1]                  # walk from the outer end to the cut
    sm = _assembler_smooth(P)
    sgn = 1.0 if int(mo.get("side", 1)) > 0 else -1.0       # mouths.json: +1 = L (left of increasing vertex)
    h = int(mo["host_vertex"]) % m
    edge = []
    for v in range(h - 40, h + 41):
        q = v % m
        nx, nz = nrm[q]
        edge.append((pts[q][0] + nx * sgn * widths[q] / 2.0, pts[q][2] + nz * sgn * widths[q] / 2.0, v))
    hits = []
    for e_sgn in (1.0, -1.0):
        line = []
        for i in range(len(sm)):
            a, b = sm[max(0, i - 1)], sm[min(len(sm) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, tz) or 1.0
            line.append((sm[i][0] - tz / L * e_sgn * Wd[i] / 2.0, sm[i][1] + tx / L * e_sgn * Wd[i] / 2.0))
        a, b = line[-2], line[-1]
        d = (b[0] - a[0], b[1] - a[1])
        L = math.hypot(*d) or 1.0
        line.append((b[0] + d[0] / L * SWEPT_EXTEND_MAX_M, b[1] + d[1] / L * SWEPT_EXTEND_MAX_M))
        hit = None
        for i in range(len(line) - 1):
            for k in range(len(edge) - 1):
                x = _seg_x(line[i], line[i + 1], edge[k][:2], edge[k + 1][:2])
                if x is not None:
                    hit = edge[k][2] + x
                    break
            if hit is not None:
                break
        if hit is None:
            return None
        hits.append(hit)
    a_, b_ = min(hits), max(hits)
    # a corner apron on this piece (data/aprons.json): the opening runs on to where its return meets the loop edge
    apr = next((a for a in aprons if a.get("piece") == mo.get("piece") and a.get("host") == "MAINLINE"), None)
    if apr is not None:
        a_, b_ = min(a_, float(apr["E_vertex"])), max(b_, float(apr["E_vertex"]))

    def arc_of(vf):
        v = int(math.floor(vf))
        return st[v] + (st[min(v + 1, len(st) - 1)] - st[v]) * (vf - v)
    lo_ = int(math.floor(a_))
    while lo_ > 0 and arc_of(a_) - st[lo_ - 1] <= MOUTH_CORNER_M:
        lo_ -= 1
    hi_ = int(math.ceil(b_))
    while hi_ < m - 1 and st[hi_ + 1] - arc_of(b_) <= MOUTH_CORNER_M:
        hi_ += 1
    # ... and wherever gap_mouths_blend takes the host's curb + sidewalk away (no curb there either)
    gap = sorted(_MW.gap_window(pts, m, True, int(mo["host_seg"]), float(mo["host_t"]),
                                float(mo.get("connector_width_m", 10.0)), float(mo.get("angle_deg") or 90.0))) \
        if "host_seg" in mo else []
    if apr is not None:
        gap = sorted(set(gap) | set(range(int(apr["host_rows_opened"][0]), int(apr["host_rows_opened"][1]) + 1)))
    if gap and gap[-1] - gap[0] < m // 2:
        lo_, hi_ = min(lo_, gap[0]), max(hi_, gap[-1])
    return {"edge_vertex_from": round(a_, 2), "edge_vertex_to": round(b_, 2), "vertex_from": lo_, "vertex_to": hi_,
            "sidewalk_gap": [gap[0], gap[-1]] if gap else None,
            **({"apron": apr["id"], "apron_end_vertex": round(float(apr["E_vertex"]), 2)} if apr is not None else {}),
            "how": "the piece's swept road edges (assembler smoothing) crossing the host edge, + MOUTH_CORNER_M of arc, "
                   "and the host sidewalk gap (mouth_weld.gap_window) (race.swept_mouths, ledger 0054 P1)"}


def _assembler_smooth(P, sigma=1.5):
    """scripts-v021/geometry/smooth.py smooth_centerline(sigma_pts=1.5, passes=1) in plan (endpoints pinned)"""
    n = len(P)
    if n < 5:
        return list(P)
    r = max(1, int(round(3.0 * sigma)))
    ker = [math.exp(-(k * k) / (2.0 * sigma * sigma)) for k in range(-r, r + 1)]
    sk = sum(ker)
    ker = [k / sk for k in ker]
    out = [P[0]]
    for i in range(1, n - 1):
        x = z = 0.0
        for k in range(-r, r + 1):
            j = min(n - 1, max(0, i + k))
            x += ker[k + r] * P[j][0]
            z += ker[k + r] * P[j][1]
        out.append((x, z))
    out.append(P[-1])
    return out


def _seg_x(a, b, c, d):
    """fraction u along c->d where segments a->b and c->d cross, else None"""
    r = (b[0] - a[0], b[1] - a[1])
    q = (d[0] - c[0], d[1] - c[1])
    den = r[0] * q[1] - r[1] * q[0]
    if abs(den) < 1e-12:
        return None
    t = ((c[0] - a[0]) * q[1] - (c[1] - a[1]) * q[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return u if (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0) else None


def _mouth_probes(closed, widths, m, pts=None, nrm=None):
    out = []
    for mo in closed:
        h = int(mo["host_vertex"]) % m
        if mo.get("probe_xz") is not None and pts is not None and nrm is not None:
            # a lap's abandoned branch: the probe stands ON the branch (xz), y is its lateral at the junction
            # vertex for the report; tools/no_route.py reads the xz
            px, pz = mo["probe_xz"]
            y = (px - pts[h][0]) * nrm[h][0] + (pz - pts[h][2]) * nrm[h][1]
            out.append({"vertex": h, "y": round(y, 3), "xz": [round(px, 3), round(pz, 3)],
                        "why": f"{mo.get('kind', 'branch')} {mo['connector']}"})
            continue
        sgn = 1.0 if mo["side"] == "L" else -1.0
        out.append({"vertex": h, "y": round(sgn * (widths[h] / 2.0 + MOUTH_PROBE_M), 3),
                    "why": f"side_street {mo['connector']}"})
    return out


def _chicane_vertices(c, m):
    """every vertex of a corridor's declared chicanes (travel_from .. travel_to of each race-side wall)"""
    out = set()
    for w in c.get("chicane_walls") or []:
        out.update(_RC.walk(int(w["i"]) % m, int(w["j"]) % m, m))
    return out


def _validate_chicanes(out: dict, ctx: dict) -> list[str]:
    """13. the declared chicanes (ledger 0055), per race layout that drives one:
      * declared == driven: every race.chicanes entry naming the layout has its wall, and nothing else does;
      * zone 'chicane' on every vertex of the span, a lane on every one (y_lo < y_hi), never wider than the road
        between the curb-strip faces, never narrower than min(the clear floor, the corridor's own width at the
        chicane's two ends) nor the hard minimum;
      * the race-side wall: declared at every span vertex, both ends ON the race-side curb strip's centre (PIN_TOL_M),
        no step steeper than race.corridor.steepest_pin_rate, plan radius >= RADIUS_MIN_M, no backward step; the lane's
        race-side face IS the wall's face (half a barrier off its centre) or the race-side strip face;
      * the closure: declared on the out leg up to its far-strip pin and on the back leg from it, NONE between the
        legs (the lane runs to the far curb strip there), its two chicane pins ON the far strip centre (PIN_TOL_M);
        the lane's far-side face IS the closure's face where one stands, else the far strip face;
      * the island: the race island is zero over the whole span (the street-only island never stands in a race lane);
      * the crossing: the lane's centre moves at least MIN_CROSSING_M across the road (what Kevin asked to keep)."""
    fails = []
    m, n = ctx["m"], ctx["n"]
    P = ctx["params"]
    widths, pts, half_auth = ctx["widths"], ctx["pts"], ctx["half_auth"]
    inset, bhalf, strip_c = ctx["edge_inset"], ctx["bhalf"], ctx["strip_c"]
    k_hard = 1.0 / float(P["steepest_pin_rate"])
    floor_ = float(P["clear_floor_m"])
    chicanes, _p = _CH.declared(ctx["cfg"])
    for lid, c in (out.get("corridors") or {}).items():
        mine = {ch["name"]: ch for ch in chicanes if lid in ch["layouts"]}
        walls = {w["name"]: w for w in c.get("chicane_walls") or []}
        if sorted(mine) != sorted(walls):
            fails.append(f"chicanes {lid}: declared {sorted(mine)} but the corridor carries walls for {sorted(walls)}")
        yw = c.get("race_wall_y_by_vertex") or [None] * n
        y = c["closure_y_by_vertex"]
        lane = c["lane_by_vertex"]
        zn = c["zone_by_vertex"]
        rs = 1.0 if c["race_side"] == "L" else -1.0           # forward-frame sign of the race side
        for name, w in walls.items():
            ch = mine.get(name)
            if ch is None:
                continue
            vs = _RC.walk(int(w["i"]) % m, int(w["j"]) % m, m)
            if c["travel"] != "increasing":
                vs = list(reversed(vs))
            if (vs[0], vs[-1]) != (w["travel_from"], w["travel_to"]):
                fails.append(f"chicanes {lid} {name}: travel_from / travel_to {w['travel_from']} / {w['travel_to']} != "
                             f"the walk's ends {vs[0]} / {vs[-1]}")
                continue
            a, b = _CH.span_of(ch)
            if sorted([vs[0], vs[-1]]) != [a, b]:
                fails.append(f"chicanes {lid} {name}: the wall runs v{w['i']}-v{w['j']}, the declaration v{a}-v{b}")
            out_leg, back_leg = _CH.legs_in_travel(ch, "reverse" if c["travel"] != "increasing" else "forward")
            q1, q2 = vs.index(out_leg[1]), vs.index(back_leg[0])
            # the lane may not be narrower than the corridor gives it where the chicane starts and ends (an island
            # convergence there is already below the floor, listed on its run) — nor below the hard minimum
            w_ends = min(lane[vs[0]][1] - lane[vs[0]][0], lane[vs[-1]][1] - lane[vs[-1]][0])
            hard_min = float(P["clear_hard_min_m"])
            if any(yw[k] is None for k in vs):
                fails.append(f"chicanes {lid} {name}: the race-side wall is not declared on every span vertex — a door")
                continue
            for k in (vs[0], vs[-1]):
                race_c = rs * (widths[k] / 2.0 - strip_c)
                if abs(yw[k] - race_c) > PIN_TOL_M:
                    fails.append(f"chicanes {lid} {name}: the wall's end at v{k} is {abs(yw[k] - race_c):.3f} m off the "
                                 f"race-side strip centre (> {PIN_TOL_M}) — an unburied end is a door")
            for k in (out_leg[1], back_leg[0]):
                far_c = -rs * (widths[k] / 2.0 - strip_c)
                if y[k] is None or abs(y[k] - far_c) > PIN_TOL_M:
                    fails.append(f"chicanes {lid} {name}: the closure's chicane pin at v{k} is "
                                 f"{'missing' if y[k] is None else f'{abs(y[k] - far_c):.3f} m off'} the far strip centre")
            for q, k in enumerate(vs):
                if zn[k] != "chicane":
                    fails.append(f"chicanes {lid} {name}: v{k} zone {zn[k]!r}, expected 'chicane'")
                    break
                if half_auth[k] > 0 and _CH.ISLAND_NOSE_VERTS < q < len(vs) - 1 - _CH.ISLAND_NOSE_VERTS:
                    # (the modelled nose past each cap is gate 5's, on the closure run that holds it)
                    fails.append(f"chicanes {lid} {name}: the race island stands at v{k} ({2 * half_auth[k]:.2f} m) — a "
                                 f"chicane span's island must be street-only")
                    break
                held = q1 < q < q2
                if held and y[k] is not None:
                    fails.append(f"chicanes {lid} {name}: a closure stands at v{k} between the legs")
                    break
                if not held and y[k] is None:
                    fails.append(f"chicanes {lid} {name}: no closure at v{k} on a leg — a door")
                    break
                lo_, hi_ = lane[k]
                face = widths[k] / 2.0 - inset
                if not (-face - 1e-6 <= lo_ < hi_ <= face + 1e-6):
                    fails.append(f"chicanes {lid} {name}: v{k} lane [{lo_:.2f}, {hi_:.2f}] leaves the strip faces +-{face:.2f}")
                    break
                if hi_ - lo_ < min(floor_, w_ends) - 1e-3 or hi_ - lo_ < hard_min:
                    fails.append(f"chicanes {lid} {name}: v{k} lane {hi_ - lo_:.2f} m < min(the clear floor {floor_} m, "
                                 f"the corridor's own width at the chicane's ends {w_ends:.2f} m)")
                    break
                race_face = hi_ if rs > 0 else lo_
                far_face = lo_ if rs > 0 else hi_
                want_r = yw[k] - rs * bhalf
                if q not in (0, len(vs) - 1) and abs(race_face - want_r) > 1e-3:
                    fails.append(f"chicanes {lid} {name}: v{k} the lane's race-side face {race_face:+.3f} is not the "
                                 f"wall's face {want_r:+.3f}")
                    break
                want_f = (y[k] + rs * bhalf) if (y[k] is not None and k not in (out_leg[1], back_leg[0])) else -rs * face
                if abs(far_face - want_f) > 1e-3:
                    fails.append(f"chicanes {lid} {name}: v{k} the lane's far face {far_face:+.3f} is not "
                                 f"{'the closure face' if y[k] is not None else 'the far strip face'} {want_f:+.3f}")
                    break
            rr = [0.0]
            for q in range(1, len(vs)):
                rr.append(rr[-1] + math.hypot(pts[vs[q]][0] - pts[vs[q - 1]][0], pts[vs[q]][2] - pts[vs[q - 1]][2]))
            for q in range(1, len(vs)):
                ds = rr[q] - rr[q - 1]
                if ds > 1e-9 and abs(yw[vs[q]] - yw[vs[q - 1]]) / ds > k_hard * (1 + RATE_TOL):
                    fails.append(f"chicanes {lid} {name}: the wall moves 1:{ds / abs(yw[vs[q]] - yw[vs[q - 1]]):.2f} at "
                                 f"v{vs[q - 1]}->v{vs[q]} — steeper than 1:{P['steepest_pin_rate']}")
                    break
            rad, rad_v, back = _RC.plan_radius(pts, m, vs, yw)
            if back:
                fails.append(f"chicanes {lid} {name}: the wall has {back} backward steps (a fold)")
            if rad < RADIUS_MIN_M:
                fails.append(f"chicanes {lid} {name}: the wall's plan radius {rad:.1f} m at v{rad_v} < {RADIUS_MIN_M} m")
            mids = [0.5 * (lane[k][0] + lane[k][1]) for k in vs]
            if max(mids) - min(mids) < MIN_CROSSING_M:
                fails.append(f"chicanes {lid} {name}: the lane crosses only {max(mids) - min(mids):.1f} m "
                             f"(< {MIN_CROSSING_M} m) — not a chicane across the road")
    return fails


# ---------------------------------------------------------------------------------------------
# the self-gates — pure on (declaration, context): tests perturb a declaration and call this
def _validate_nose(lid, c, nz, ctx) -> list[str]:
    """14. noses (ledger 0054 Phase 2, opt-in): at a nose pin P the closure stands ON the island's race face
    (race_corridor.nose_pin_g, PIN_TOL_M), its run end joins the K-rail, and the K-rail is declared across the far
    carriageway from the closure's race face to the far curb strip's centre (both PIN_TOL_M) on a real strip ring,
    inside the declared closure run (never in a box), the lane at P no narrower than the hard minimum"""
    fails = []
    k, widths, m = nz["pin"], ctx["widths"], ctx["m"]
    e = -1.0 if c["race_side"] == "R" else 1.0
    y = c["closure_y_by_vertex"][k]
    want = e * _RC.nose_pin_g(ctx["ctx"], nz["median"], inset=ctx["edge_inset"], half=ctx["bhalf"])
    if abs(y - want) > PIN_TOL_M:
        fails.append(f"noses {lid}: v{k} closure y {y:+.3f} is {abs(y - want):.3f} m off the island's race face "
                     f"{want:+.3f} at the nose v{nz['median']} (> {PIN_TOL_M})")
    if ctx["free"](k):
        fails.append(f"noses {lid}: the nose pin v{k} lies in a declared box / whole-street zone")
    ends = [en for r in c.get("runs", []) for en in r.get("ends", []) if en.get("vertex") == k]
    if not ends or any(en.get("joins") != "nose" for en in ends):
        fails.append(f"noses {lid}: the closure end at v{k} does not join its K-rail ({[en.get('joins') for en in ends]})")
    walls = [w for w in c.get("nose_walls") or [] if w.get("vertex") == k]
    if len(walls) != 1:
        fails.append(f"noses {lid}: {len(walls)} K-rails declared at the nose pin v{k} (one expected)")
        return fails
    w = walls[0]
    far = -e * (widths[k] / 2.0 - ctx["strip_c"])
    if abs(float(w["y_to"]) - far) > PIN_TOL_M:
        fails.append(f"noses {lid}: the K-rail at v{k} ends {abs(float(w['y_to']) - far):.3f} m off the far strip "
                     f"centre {far:+.3f} — an unburied end is a door")
    if abs(float(w["y_from"]) - (y + e * ctx["bhalf"])) > PIN_TOL_M:
        fails.append(f"noses {lid}: the K-rail at v{k} starts {float(w['y_from']):+.3f}, not at the closure's race face "
                     f"{y + e * ctx['bhalf']:+.3f}")
    if k in ctx["removed"].get(c["closure_side"], ()):
        fails.append(f"noses {lid}: v{k} is a trimmed fold vertex of edge_{c['closure_side']} — no strip ring to bury "
                     f"the K-rail in")
    lo_, hi_ = c["lane_by_vertex"][k]
    if hi_ - lo_ < float(ctx["params"]["clear_hard_min_m"]):
        fails.append(f"noses {lid}: the lane at the nose pin v{k} is {hi_ - lo_:.2f} m (< the hard minimum "
                     f"{ctx['params']['clear_hard_min_m']} m)")
    return fails


def validate(out: dict, ctx: dict) -> list[str]:
    fails: list[str] = []
    m, n = ctx["m"], ctx["n"]
    P = ctx["params"]
    widths, st, half_auth = ctx["widths"], ctx["st"], ctx["half_auth"]
    inset, bhalf, strip_c = ctx["edge_inset"], ctx["bhalf"], ctx["strip_c"]
    pts = ctx["pts"]
    whole, boxes, pinned, free = ctx["whole"], ctx["boxes"], ctx["pinned"], ctx["free"]
    corridors = out.get("corridors") or {}
    removed = ctx["removed"]

    # 10. strips on every vertex; the retired chain stays retired
    es = out.get("edge_strip_by_vertex") or []
    if len(es) != n or not all(int(v) == 1 for v in es):
        fails.append(f"strips: edge_strip_by_vertex must be 1 on all {n} vertices (no bridge gaps, ledger 0049 C1) — "
                     f"{sum(1 for v in es if not v)} gapped")
    if any(float(w) > 0 for w in out.get("centre_w_by_vertex") or []):
        fails.append("strips: centre_w_by_vertex declares the retired centre chain")

    # 1. zones
    for b in boxes:
        c = ctx["corner_by_apex"].get(b["apex"])
        if c is None:
            fails.append(f"zones: box apex v{b['apex']} is not a detected corner apex "
                         f"({sorted(ctx['corner_by_apex'])})")
            continue
        if not (_RC.in_rng(c["PC"], b["i"], b["j"], m) and _RC.in_rng(c["PT"], b["i"], b["j"], m)
                and _RC.in_rng(c["apex"], b["i"], b["j"], m)):
            fails.append(f"zones: box v{b['i']}-v{b['j']} does not hold its corner's arc PC v{c['PC']} .. PT v{c['PT']}")
        if _RC.in_rng(b["i"], whole[0], whole[1], m) or _RC.in_rng(b["j"], whole[0], whole[1], m):
            fails.append(f"zones: box v{b['i']}-v{b['j']} overlaps the whole-street zone")
    for c in ctx["corners"]:
        if _RC.in_rng(c["apex"], whole[0], whole[1], m) and not (
                _RC.in_rng(c["PC"], whole[0], whole[1], m) and _RC.in_rng(c["PT"], whole[0], whole[1], m)):
            fails.append(f"zones: the whole-street zone holds corner v{c['apex']} but not its arc PC v{c['PC']} .. PT v{c['PT']}")
    derived = []
    v = 0
    # closure intervals = maximal non-free runs extended by their two pins (forward order)
    start = next((q for q in range(m) if free(q)), None)
    if start is None:
        fails.append("zones: no whole-street or box vertex at all — nothing to pin a closure to")
    else:
        q = 0
        while q < m:
            k = (start + q) % m
            if free(k):
                q += 1
                continue
            q1 = q
            while q1 + 1 < m and not free((start + q1 + 1) % m):
                q1 += 1
            derived.append(((start + q - 1) % m, (start + q1 + 1) % m))
            q = q1 + 1
    if sorted(derived) != sorted(pinned):
        fails.append(f"zones: the declared zones give closure runs {sorted(derived)} but race.corridor.closure_runs pins "
                     f"{sorted(pinned)} — re-declare one or the other (never derived silently)")
    pin_set = {a for a, _ in pinned} | {b for _, b in pinned}
    # ledger 0054 Phase 2 (opt-in): a nose end moves its run's pin from the box edge to the vertex beside the nose, and
    # the walk between stands open like the box (ctx "solve_free"); with no nose declared both are the declared ones
    noses = ctx.get("noses") or []
    nose_by_pin = {nz["pin"]: nz for nz in noses}
    if noses:
        pin_set = (pin_set - {nz["end"] for nz in noses}) | set(nose_by_pin)
        free = ctx["solve_free"]
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"]
        zn = c["zone_by_vertex"]
        lane = c["lane_by_vertex"]
        if len(y) != n or len(zn) != n or len(lane) != n:
            fails.append(f"zones {lid}: closure_y / zone / lane rows {len(y)} / {len(zn)} / {len(lane)} != {n}")
            continue
        chic = _chicane_vertices(c, m)
        for k in range(m):
            if k in chic:
                continue                                 # a declared chicane: gate 13
            fr = free(k)
            if k in pin_set:
                if zn[k] != "pin" or y[k] is None:
                    fails.append(f"zones {lid}: v{k} is a declared pin but carries zone {zn[k]!r} / closure {y[k]}")
            elif fr:
                if y[k] is not None:
                    fails.append(f"zones {lid}: a closure stands at v{k} inside the "
                                 f"{'whole-street zone' if _RC.in_rng(k, whole[0], whole[1], m) else 'open box'}")
                    break
                want = "whole" if _RC.in_rng(k, whole[0], whole[1], m) else "box"
                if zn[k] != want:
                    fails.append(f"zones {lid}: v{k} zone {zn[k]!r}, expected {want!r}")
                    break
            else:
                if y[k] is None:
                    fails.append(f"zones {lid}: v{k} is inside closure run but declares no closure — a hole in the "
                                 f"closure is a door")
                    break
                if zn[k] not in ("closure", "island"):
                    fails.append(f"zones {lid}: v{k} zone {zn[k]!r} inside a closure run")
                    break

    # 2. pins
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"]
        side = c["closure_side"]
        sgn = 1.0 if side == "L" else -1.0
        for k in sorted(pin_set):
            if y[k] is None:
                continue
            if k in nose_by_pin:
                fails += _validate_nose(lid, c, nose_by_pin[k], ctx)
                continue
            far = sgn * (widths[k] / 2.0 - strip_c)
            if abs(y[k] - far) > PIN_TOL_M:
                fails.append(f"pins {lid}: v{k} closure y {y[k]:+.3f} is {abs(y[k] - far):.3f} m off the far strip "
                             f"centre {far:+.3f} (> {PIN_TOL_M}) — an unburied end is a door")
            if k in removed.get(side, ()):
                fails.append(f"pins {lid}: v{k} is a trimmed fold vertex of edge_{side} — no strip ring to bury the pin in")

    # 3. rates, 6. shape, 4. clear width + pocket, 5. islands
    k_conv, k_div = 1.0 / float(P["rate_toward_race_side"]), 1.0 / float(P["rate_away"])
    k_hard = 1.0 / float(P["steepest_pin_rate"])
    zone_m = float(P["pin_zone_m"])
    floor_ = float(P["clear_floor_m"])
    hard_min = float(P["clear_hard_min_m"])
    pocket_min = float(P["pocket_min_m"])
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"]
        lane = c["lane_by_vertex"]
        e = -1.0 if c["race_side"] == "R" else 1.0       # g = e * y: lateral toward the race side
        listed = {}
        for r in c.get("runs", []):
            for a, b, why in r.get("below_floor", []):
                for k in _RC.walk(int(a), int(b), m) if c["travel"] == "increasing" else _RC.walk(int(b), int(a), m):
                    listed[k] = why
        for r in c.get("runs", []):
            vs = _RC.walk(r["travel_from"], r["travel_to"], m) if c["travel"] == "increasing" else \
                list(reversed(_RC.walk(r["travel_to"], r["travel_from"], m)))
            if any(y[k] is None for k in vs):
                continue                                 # reported by the zone gate
            rr = [0.0]
            for q in range(1, len(vs)):
                a, b = pts[vs[q - 1]], pts[vs[q]]
                rr.append(rr[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
            L_ = rr[-1]
            k_in = 1.0 / float(r["max_rate"]["pin_in"]) if r["max_rate"].get("pin_in") else k_div
            k_out = 1.0 / float(r["max_rate"]["pin_out"]) if r["max_rate"].get("pin_out") else k_div
            for kk in (k_in, k_out):
                if kk > k_hard * (1 + 1e-9):
                    fails.append(f"rates {lid}: run v{r['i']}-v{r['j']} pin rate 1:{1 / kk:.2f} is steeper than "
                                 f"1:{P['steepest_pin_rate']}")
            for q in range(1, len(vs)):
                ds = rr[q] - rr[q - 1]
                if ds <= 1e-9:
                    continue
                g0, g1 = e * y[vs[q - 1]], e * y[vs[q]]
                rate = (g1 - g0) / ds
                if abs(rate) > k_hard * (1 + RATE_TOL):
                    fails.append(f"rates {lid}: v{vs[q - 1]}->v{vs[q]} moves 1:{1 / abs(rate):.2f} — steeper than "
                                 f"1:{P['steepest_pin_rate']}")
                    break
                in_zone = min(rr[q - 1], L_ - rr[q]) <= zone_m
                if in_zone:
                    lim = max(max(k_conv, k_div), k_in if rr[q - 1] <= zone_m else 0.0, k_out if L_ - rr[q] <= zone_m else 0.0)
                    if abs(rate) > lim * (1 + RATE_TOL) + 1e-4:
                        fails.append(f"rates {lid}: v{vs[q - 1]}->v{vs[q]} 1:{1 / abs(rate):.2f} in a pin zone "
                                     f"(limit 1:{1 / lim:.2f})")
                        break
                elif rate > k_conv * (1 + RATE_TOL) + 1e-4:
                    fails.append(f"rates {lid}: v{vs[q - 1]}->v{vs[q]} closes toward the race side at 1:{1 / rate:.2f} "
                                 f"(limit 1:{P['rate_toward_race_side']})")
                    break
                elif -rate > k_div * (1 + RATE_TOL) + 1e-4:
                    fails.append(f"rates {lid}: v{vs[q - 1]}->v{vs[q]} opens away at 1:{1 / -rate:.2f} "
                                 f"(limit 1:{P['rate_away']})")
                    break
            # 6. shape
            rad, rad_v, back = _RC.plan_radius(pts, m, vs, y)
            if back:
                fails.append(f"shape {lid}: run v{r['i']}-v{r['j']} has {back} backward steps (a fold)")
            if rad < RADIUS_MIN_M:
                fails.append(f"shape {lid}: run v{r['i']}-v{r['j']} plan radius {rad:.1f} m at v{rad_v} < {RADIUS_MIN_M} m")
            # 4. clear width / pocket ; 5. islands
            for q in range(1, len(vs) - 1):
                k = vs[q]
                lo_, hi_ = lane[k]
                clear = hi_ - lo_
                if clear < hard_min:
                    fails.append(f"clear {lid}: v{k} lane {clear:.2f} m < the hard minimum {hard_min} m")
                    break
                if clear < floor_ - 1e-6:
                    why = listed.get(k)
                    if why not in ("island", "pin_zone", "convergence"):
                        fails.append(f"clear {lid}: v{k} lane {clear:.2f} m < the floor {floor_} m and not listed as an "
                                     f"island / pin-zone / convergence vertex")
                        break
                    if why == "convergence":
                        near = min((abs(st[k] - st[a]) for a in range(m) if half_auth[a] > 0), default=1e9)
                        if near > CONVERGENCE_REACH_M:
                            fails.append(f"clear {lid}: v{k} listed as convergence but {near:.0f} m from every island")
                            break
                in_zone = min(rr[q], L_ - rr[q]) <= zone_m
                w2 = widths[k] / 2.0
                if half_auth[k] <= 0 and not in_zone and listed.get(k) != "island":
                    pocket = (w2 - inset) - (y[k] + bhalf) if c["closure_side"] == "L" else (y[k] - bhalf) - (-(w2 - inset))
                    if pocket < pocket_min - 1e-6:
                        fails.append(f"clear {lid}: v{k} the closed-off pocket behind the closure is {pocket:.2f} m "
                                     f"(< {pocket_min} m) — declare that stretch whole street")
                        break
                if half_auth[k] > 0:
                    if c["closure_side"] == "L":     # cw: closure on the island's right (race-side) face
                        clear_isl = -half_auth[k] - (y[k] + bhalf)
                    else:
                        clear_isl = (y[k] - bhalf) - half_auth[k]
                    if clear_isl < ISLAND_CLEAR_M - 1e-3:
                        fails.append(f"islands {lid}: v{k} the closure footprint is {clear_isl:+.3f} m off the AUTHORED "
                                     f"island (< {ISLAND_CLEAR_M} m, or on the wrong side of a nose)")
                        break

    # 7. mouths
    for lid, c in corridors.items():
        for mo in c.get("mouths", []):
            h = mo["host_vertex"]
            if mo.get("split"):
                # ledger 0054 A7: a swept (split) row is judged on EVERY vertex of its run (its host_vertex may lie in
                # another part); every other row keeps the host_vertex judgement below
                rng = _RC.walk(mo["vertex_from"], mo["vertex_to"], m)
                bad = [k for k in rng if _vertex_policy(mo["side"], c, k) != mo["policy"]]
                if bad:
                    fails.append(f"mouths {lid}: {mo['connector']} part {mo['split']['part']} declared {mo['policy']} "
                                 f"but v{bad[0]} needs {_vertex_policy(mo['side'], c, bad[0])}")
                if mo["policy"] == "sealed_race_strip" and any(not es[k] for k in rng if k < len(es)):
                    fails.append(f"mouths {lid}: {mo['connector']} v{h}: the race-side strip is gapped across the mouth")
                continue
            if mo["policy"] == "sealed_race_strip":
                if mo["side"] != c["race_side"]:
                    fails.append(f"mouths {lid}: {mo['connector']} v{h} is on the far side but declared sealed by the race strip")
                rng = _RC.walk(mo["vertex_from"], mo["vertex_to"], m)
                if any(not es[k] for k in rng if k < len(es)):
                    fails.append(f"mouths {lid}: {mo['connector']} v{h}: the race-side strip is gapped across the mouth")
            elif mo["policy"] == "behind_closure":
                if c["closure_y_by_vertex"][h] is None or c["zone_by_vertex"][h] not in ("closure", "island"):
                    fails.append(f"mouths {lid}: {mo['connector']} v{h} is declared behind the closure but no closure "
                                 f"stands there")
            elif mo["policy"] == "sealed_far_strip":
                if mo["side"] == c["race_side"] or c["zone_by_vertex"][h] not in ("whole", "box", "pin"):
                    fails.append(f"mouths {lid}: {mo['connector']} v{h} far-strip policy outside a whole/box zone")
            else:
                fails.append(f"mouths {lid}: {mo['connector']} v{h} unknown policy {mo['policy']!r}")

    # 8. spawns: every grid and pit slot clear of both lane faces
    for z in out.get("no_gap_zones") or []:
        lid = str(z["layout"])
        c = corridors.get(lid)
        off = float(z.get("offset_right_m", 0.0))
        reverse = bool(z.get("reverse"))
        for k in _RC.walk(int(z["i"]), int(z["j"]), m):
            if c is not None:
                lo_, hi_ = c["lane_by_vertex"][k]
            else:
                face = widths[k] / 2.0 - inset
                lo_, hi_ = -face, face
            r_lo, r_hi = (lo_, hi_) if reverse else (-hi_, -lo_)
            outer = off + GRID_STAGGER_M + CAR_HALF_W_M
            inner = off - GRID_STAGGER_M - CAR_HALF_W_M
            cl_out, cl_in = r_hi - outer, inner - r_lo
            z.setdefault("grid_clearance_m", round(min(cl_out, cl_in), 2))
            z["grid_clearance_m"] = round(min(z["grid_clearance_m"], cl_out, cl_in), 2)
            if min(cl_out, cl_in) < GRID_CLEAR_MIN_M:
                fails.append(f"spawns {lid}: at v{k} a grid / pit car stands {min(cl_out, cl_in):+.2f} m off a corridor "
                             f"face (< {GRID_CLEAR_MIN_M})")
                break

    # 13. chicanes (ledger 0055)
    fails += _validate_chicanes(out, ctx)

    # 9. kerbs
    kerbs = out.get("kerbs") or []
    dropped = out.get("kerbs_dropped") or []
    if len(kerbs) + len(dropped) != 2 * len(ctx["corners"]):
        fails.append(f"kerbs: {len(kerbs)} declared + {len(dropped)} dropped — expected outside + inside at each of "
                     f"the {len(ctx['corners'])} corners ({2 * len(ctx['corners'])})")
    both = {(int(k["apex"]), k["kind"]) for k in kerbs} & {(int(d["apex"]), d["kind"]) for d in dropped}
    if both:
        fails.append(f"kerbs: {sorted(both)} both declared and dropped")
    for d in dropped:
        if not str(d.get("why") or "").strip():
            fails.append(f"kerbs: the dropped {d.get('kind')} kerb at v{d.get('apex')} carries no why")
    for kb in kerbs:
        for k in _RC.walk(int(kb["i"]), int(kb["j"]), m):
            g, by = _kerb_clear(widths, k, kb["side"], corridors, inset, bhalf)
            if g < KERB_CLOSURE_CLEAR_M - 1e-3:
                fails.append(f"kerbs: the {kb['kind']} kerb at v{kb['apex']} stands {g:+.3f} m off {by}'s closure at v{k} "
                             f"(< {KERB_CLOSURE_CLEAR_M} m)")
                break
    return fails


def _summary(out, corridors, kerbs, edge_corners, corners, island_w, planned):
    lays = {}
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"]
        isl_len = clos_len = 0.0
        clears = []
        below_m = 0.0
        for r in c["runs"]:
            clos_len += r["length_m"]
        m = len(y) - 1
        for r in c["runs"]:
            clears.append(r["clear_min_m"])
        lane = c["lane_by_vertex"]
        zn = c["zone_by_vertex"]
        pts_isl = sum(1 for z in zn[:m] if z == "island")
        st_ = out.get("_st") or []
        isl_m = sum(st_[k + 1] - st_[k] for k in range(m) if zn[k] == "island" and zn[(k + 1) % m] == "island") if st_ else None
        lays[lid] = {
            "token": c["token"], "closure_runs": len(c["runs"]), "closure_m": round(clos_len, 1),
            "island_vertices": pts_isl, "island_m": round(isl_m, 1) if isl_m is not None else None,
            "clear_min_m": round(min(clears), 3) if clears else None,
            "clear_median_m": round(_median([lane[k][1] - lane[k][0] for k in range(m) if zn[k] in ("closure", "island")]), 3)
            if any(z in ("closure", "island") for z in zn) else None,
            "pin_rates": [[r["travel_from"], r["max_rate"]["pin_in"]] for r in c["runs"]] +
                         [[r["travel_to"], r["max_rate"]["pin_out"]] for r in c["runs"]],
            "below_floor_vertices": sum(abs(b - a) + 1 for r in c["runs"] for a, b, _w in r["below_floor"]),
            "min_radius_m": min((r["min_radius_m"] for r in c["runs"] if r["min_radius_m"]), default=None),
            "probes": len(c["no_route"]["forbidden_probes"]),
            "planned_no_route": planned.get(lid, c["no_route"].get("planned")),
        }
    mirror = mirror_run = None
    ids = sorted(corridors)
    if len(ids) == 2:
        a, b = corridors[ids[0]], corridors[ids[1]]
        if a["closure_side"] != b["closure_side"]:
            # running vertices: off the pin zones and >= MIRROR_TRANSITION_M from every island / opening end — the
            # 1:12 convergences come BEFORE each island in each layout's own travel, so they differ by design there
            st_ = out.get("_st") or []
            ends = [e_ for z_ in (out["zones"]["island_zones"] + out["zones"]["openings"]) for e_ in z_]
            ds, dr = [], []
            for v, (ya, yb, za, zb) in enumerate(zip(a["closure_y_by_vertex"], b["closure_y_by_vertex"],
                                                     a["zone_by_vertex"], b["zone_by_vertex"])):
                if ya is None or yb is None or za not in ("closure", "island") or zb not in ("closure", "island"):
                    continue
                ds.append(abs(ya + yb))
                near_end = st_ and any(abs(st_[v] - st_[e_]) < MIRROR_TRANSITION_M for e_ in ends)
                near_pin = st_ and any(abs(st_[v] - st_[p_]) <= float(out["params"]["corridor"]["pin_zone_m"])
                                       for p_ in a.get("pins", []))
                if not near_end and not near_pin:
                    dr.append(abs(ya + yb))
            mirror = round(max(ds), 3) if ds else None
            mirror_run = round(max(dr), 3) if dr else None
    return {
        "layouts": lays,
        "mirror_max_m": mirror,
        "mirror_running_max_m": mirror_run,
        "edge_verts": sum(out["edge_strip_by_vertex"]),
        "edge_gaps": 0,
        "edge_corners": len(edge_corners),
        "kerbs": len(kerbs),
        "kerbs_dropped": [[d["apex"], d["kind"]] for d in (out.get("kerbs_dropped") or [])],
        "kerb_trims": [{"apex": k["apex"], "kind": k["kind"], "from": k["trimmed_from"], "to": [k["i"], k["j"]]}
                       for k in kerbs if k.get("trimmed_from")],
        "kerb_clips": [{"apex": k["apex"], "side": k["side"], "kind": k["kind"], "from": k.get("clipped_from"),
                        "to": [k["i"], k["j"]], "by": (k.get("clip") or {}).get("by")} for k in kerbs if k.get("clipped_from")],
        "corners": len(corners),
        "island_runs": [list(r) for r in _island_runs(island_w)],
        "nose_vertices": sorted({v for a, b in _island_runs(island_w) for v in (a, b)}),
    }


def _report(proj, out, fails):
    s = out["summary"]
    print(f"[bands] {proj.name}{(' lap ' + out['lap']['id']) if out.get('lap') else ''}: v2 corridors for "
          f"{sorted(out['corridors'])}; strips on {s['edge_verts']}/{out['n']} "
          f"verts (closed loops, {s['edge_corners']} trimmed corners); {s['kerbs']} kerbs at {s['corners']} corners; "
          f"{len(out['closed_mouths'])} sealed mouths; clear width {out['params']['corridor']['clear_width_m']} m "
          f"(measured {out['params']['corridor']['clear_width_measured_m']})")
    z = out["zones"]
    print(f"[bands]   whole v{z['whole'][0]}->v{z['whole'][1]}; boxes {[(b['i'], b['j']) for b in z['boxes']]}; "
          f"closure runs {z['closure_runs']}; openings {z['openings']}")
    for lid, c in out["corridors"].items():
        L = s["layouts"][lid]
        print(f"[bands]   {lid} (token {c['token']}, race side {c['race_side']}): {L['closure_runs']} runs, "
              f"{L['closure_m']:.0f} m of closure, clear min {L['clear_min_m']} / median {L['clear_median_m']} m, "
              f"min radius {L['min_radius_m']} m, {L['probes']} forbidden probes")
        for r in c["runs"]:
            mr = r["max_rate"]
            print(f"[bands]     v{r['travel_from']}->v{r['travel_to']} {r['street']:<22} {r['length_m']:7.1f} m  "
                  f"pins 1:{mr['pin_in']} / 1:{mr['pin_out']}  toward 1:{mr['toward']} away 1:{mr['away']}  "
                  f"clear {r['clear_min_m']:.2f} / {r['clear_median_m']:.2f}  below floor "
                  f"{[(a, b, w) for a, b, w in r['below_floor']][:4]}")
        for ch, w in zip(c.get("chicanes") or [], c.get("chicane_walls") or []):
            print(f"[bands]     chicane {ch['name']}: out leg v{ch['out_leg'][0]}->v{ch['out_leg'][1]}, back leg "
                  f"v{ch['back_leg'][0]}->v{ch['back_leg'][1]} (travel order), hold {ch['hold_m']} m; the lane crosses "
                  f"{ch['crossing_m']} m at width {ch['lane_w_m']} m; closure 1:{ch['closure_rate']} / race-side wall "
                  f"1:{ch['wall_rate']}, its radius {w['min_radius_m']} m (v{w['min_radius_vertex']})")
        pl = c["no_route"].get("planned")
        if isinstance(pl, dict):
            print(f"[bands]     planned no_route: {'FAIL' if pl['fail'] else 'PASS'} — leak {pl['leak_m2']} m2, "
                  f"{pl['door_clusters']} doors, reached {pl['reached_m2']} m2 ({pl['seconds']} s)")
    if s.get("mirror_max_m") is not None:
        print(f"[bands]   mirror: max |y_cw + y_acw| {s['mirror_running_max_m']} m on the running vertices "
              f"({s['mirror_max_m']} m incl. the convergences, which lead each island in each layout's own travel)")
    for k in out["kerbs"]:
        print(f"[bands]   kerb apex v{k['apex']} {k['kind']:7} side {k['side']} v{k['i']}-v{k['j']}"
              f"{' (wraps)' if k['wraps'] else ''}{' clipped from ' + str(k['clipped_from']) if k.get('clipped_from') else ''}"
              f"{' pulled back from ' + str(k['trimmed_from']) + ' (race.kerbs.trims)' if k.get('trimmed_from') else ''}")
    for d in out.get("kerbs_dropped") or []:
        print(f"[bands]   kerb apex v{d['apex']} {d['kind']:7} side {d['side']} DROPPED (race.kerbs.trims; detected "
              f"v{d['i']}-v{d['j']}): {d['why'][:110]}")
    for c in out["edge_corners"]:
        print(f"[bands]   edge corner {c['side']} {c['kind']:6} v{c['in_vertex']}->v{c['out_vertex']} "
              f"{len(c['removed'])} vertices trimmed")
    if out.get("_path"):
        print(f"[bands] wrote {out['_path']}")
    if fails:
        print("[bands] FAIL:")
        for f in fails:
            print("   -", f)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python tools/barrier_bands.py <project-dir> [--out <name.json>] [--config <cfg>] "
                         "[--no-planned-route]")
    out_name = None
    config_path = None
    planned = True
    if "--out" in argv:
        k = argv.index("--out")
        out_name = Path(argv[k + 1]).name
        del argv[k:k + 2]
    if "--config" in argv:
        k = argv.index("--config")
        config_path = argv[k + 1]
        del argv[k:k + 2]
    if "--no-planned-route" in argv:
        argv.remove("--no-planned-route")
        planned = False
    # one declaration per lap group (scripts/geometry/race_lap.groups): the mainline's race layouts ->
    # data/barrier_bands.json (exactly as before when no layout names a lap), each race.laps.<id> -> its own file
    cfg = json.loads(Path(config_path or (Path(argv[0]) / "track.config.json")).read_text(encoding="utf-8"))
    bad = 0
    for lap in _LAP.groups(cfg):
        out = build(argv[0], out_name if lap is None else None, config_path, planned_no_route=planned, lap=lap)
        bad += 1 if out["fails"] else 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
