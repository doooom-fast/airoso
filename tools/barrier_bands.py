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
          no_route_cell: float | None = None, write: bool = True) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads(Path(config_path or (proj / "track.config.json")).read_text(encoding="utf-8"))
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
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    n = len(pts)
    if math.dist((pts[0][0], pts[0][2]), (pts[-1][0], pts[-1][2])) > 1e-6:
        raise SystemExit("[bands] centreline is not a closed lap (v[-1] != v[0]) — the loop tool only")
    m = n - 1                                      # L13: the closure vertex repeats v0
    W = widths[:m]                                 # ring widths (the duplicate carries the last street's width)
    st = _stations(pts)
    lap = st[-1]
    mb = data / "median_bands.json"
    island_w = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else [0.0] * n
    if len(island_w) != n:
        raise SystemExit(f"[bands] median_bands.json ({len(island_w)}) vs centreline ({n}) length mismatch")
    bsp = data / "bridge.spans.auto.json"
    spans = [tuple(map(float, s)) for s in json.loads(bsp.read_text(encoding="utf-8"))] if bsp.exists() else []
    mp = data / "mouths.json"
    mouths = [mo for mo in (json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else [])
              if mo.get("host") == "MAINLINE"]

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
        sol = _RC.solve(pts, widths, island_w, free, d, P, inset=edge_inset, half=bhalf, context=ctx)
        corridors[lid] = _corridor_record(lid, tok, direction, sol, ctx, P, pts, widths, n, m, st, street_at,
                                          edge_inset, bhalf, strip_c, whole)

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
    swept_prefixes = [str(x) for x in (race.get("swept_mouths") or [])]
    swept_conns = None
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
            swept = _swept_opening(mo, swept_conns, pts, widths, m, nrm, st)
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
        row = {"connector": mo["connector"], "host_vertex": h, "side": side,
               "connector_width_m": mo.get("connector_width_m"), "vertex_from": lo_, "vertex_to": hi_,
               "policy": "sealed: both curb strips run straight across the mouth line (Q1); per layout see "
                         "corridors.<id>.mouths",
               "polyline_xyz_m": poly}
        if swept is not None:
            row["swept"] = swept
        closed.append(row)
    for lid, c in corridors.items():
        c["mouths"] = _mouth_policies(closed, c, m, widths, nrm, pts)
        c["no_route"]["forbidden_probes"] += _mouth_probes(closed, widths, m)
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
    vctx = {"pts": pts, "widths": widths, "island_w": island_w, "half_auth": half_auth, "m": m, "n": n, "st": st,
            "params": P, "free": free, "whole": whole, "boxes": boxes, "pinned": pinned, "corners": corners,
            "corner_by_apex": corner_by_apex, "removed": removed, "layouts": race_layouts, "cfg": cfg,
            "edge_inset": edge_inset, "bhalf": bhalf, "strip_c": strip_c}
    fails += validate(out, vctx)
    # ---- 12. the PLANNED no-route: the declaration checking its own topology (not an L5 gate) ----------
    planned = {}
    if planned_no_route and corridors and not any(f.startswith("zones") for f in fails):
        nr = _load_tool("no_route", "_no_route_ro")
        for lid in corridors:
            kw = {"cell": no_route_cell} if no_route_cell else {}
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
        out_path = data / (out_name or "barrier_bands.json")
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
                     whole):
    """corridors.<lid>: the solved closure as a declaration (forward-frame laterals per vertex)"""
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
    lane = _RC.lane_by_vertex(y, widths, m, "acw" if reverse else "cw", inset=inset, half=bhalf, pins=pins)
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
            "ends": [{"vertex": vs[0], "y": round(y[vs[0]], 4), "joins": "edge_" + closure_side, "role": "in"},
                     {"vertex": vs[-1], "y": round(y[vs[-1]], 4), "joins": "edge_" + closure_side, "role": "out"}],
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
    return {
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


def _swept_opening(mo, conns, pts, widths, m, nrm, st):
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
    if gap and gap[-1] - gap[0] < m // 2:
        lo_, hi_ = min(lo_, gap[0]), max(hi_, gap[-1])
    return {"edge_vertex_from": round(a_, 2), "edge_vertex_to": round(b_, 2), "vertex_from": lo_, "vertex_to": hi_,
            "sidewalk_gap": [gap[0], gap[-1]] if gap else None,
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


def _mouth_probes(closed, widths, m):
    out = []
    for mo in closed:
        h = int(mo["host_vertex"]) % m
        sgn = 1.0 if mo["side"] == "L" else -1.0
        out.append({"vertex": h, "y": round(sgn * (widths[h] / 2.0 + MOUTH_PROBE_M), 3),
                    "why": f"side_street {mo['connector']}"})
    return out


# ---------------------------------------------------------------------------------------------
# the self-gates — pure on (declaration, context): tests perturb a declaration and call this
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
    for lid, c in corridors.items():
        y = c["closure_y_by_vertex"]
        zn = c["zone_by_vertex"]
        lane = c["lane_by_vertex"]
        if len(y) != n or len(zn) != n or len(lane) != n:
            fails.append(f"zones {lid}: closure_y / zone / lane rows {len(y)} / {len(zn)} / {len(lane)} != {n}")
            continue
        for k in range(m):
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
    print(f"[bands] {proj.name}: v2 corridors for {sorted(out['corridors'])}; strips on {s['edge_verts']}/{out['n']} "
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
    out = build(argv[0], out_name, config_path, planned_no_route=planned)
    return 1 if out["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
