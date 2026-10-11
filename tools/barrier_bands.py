"""Declare the race-furniture bands — data/barrier_bands.json — from the data, before anything is authored.

Ledger 0047 (Kevin, 2026-10-10): "two layouts, with Barriers making tracks out of north/south kind
lanes … With Barriers between directions, leading up to medians but not on them" / "The barriers
are for wide roads, Alvarado should be the entire street" / "the two tracks … will get additional
race curbs and barriers along the inside of the sidewalks".

This file is the one place the three consumers agree on WHERE the furniture stands:

  * tools/author_race_blend.py (Blender) sweeps the strips and kerbs along these bands;
  * scripts/geometry/median_zone.py reads them as the second divider kind, so audit D / drive_test
    exempt a wall that stands ON its declared band — and only there — for the layouts that load it;
  * drive_test's ``barrier_missing`` fails a declared station with no 1WALL on it.

So the declaration IS the authored line (the 2026-10-08 median_zone precedent) and L5 still holds:
every gate measures the BUILT OBJ against the band, never the band against itself.

Inputs (read-only; loop.blend is never opened):
  track.config.json            race.* (the declared centre runs, threshold, inset, kerb params) +
                               layouts[] (grid/pit no-gap zones) + route.roads (street names)
  data/centerline.local.json   points_xyz_m (engine frame x=E, y=up, z=N) + widths_m
  data/median_bands.json       island_w_by_vertex (tools/median_envelope.py)
  data/mouths.json             the mainline mouths (sealed by the kerb-line strip — Q1 default)
  data/bridge.spans.auto.json  [[a_m, b_m], …] station spans whose rails ARE the barrier

The centre chain is DECLARED (race.centre_runs, closed vertex intervals) and VALIDATED here, never
derived silently: Kevin's answers to Q2 (the 13.5-17 m stretches) and Q7 (interior corners) are
edits to that list. Validation (exit 1 on any miss):
  * every run vertex is >= race.wide_threshold_m wide;
  * no run vertex lies on a median island, except a run END that lands exactly on the island's nose
    vertex (butt joint, JUNCTIONS seam rule); a run end one vertex short of a nose fails — a 3 m
    wedge between a 0.67 m strip end and a 0.25 m nose is a doorway for a 1.9 m car;
  * no run vertex on a street whose median width is below the threshold (Alvarado: 13.0 m);
  * no run vertex inside a hairpin's arc (|D| >= 135 deg, PC..PT — the Alvarado/College box must
    stay open for the turn);
  * no run vertex inside, or within BRIDGE_CLEAR_M of, a declared bridge span.
Everything the data would ALLOW but the config leaves open is printed ("declared open") so a
forgotten stretch is visible, not silent.

Kerb-line (edge) strips: both curb faces of EVERY street, race layouts only, gapped only inside the
declared bridge spans (the authored rails are the barrier there; drive_test's `guarded` drop probe
still gates a span with no rail). Mouths are sealed (the strip runs straight across the mouth line
on the connector's 1ROAD, the Macau rule) and the grid/pit zones are declared no-gap zones.

Race kerbs: at every corner the sign detector finds (tools/place_signs.py, imported read-only —
the signs workflow owns that file), |D| >= race.kerbs.min_turn_deg: an OUTSIDE kerb on the lip
outside the turn, symmetric about the apex (one layout's exit is the other's entry), extended by
E = clamp(2 R_apex, outer_extension_m) past PC/PT; an INSIDE kerb on the detector's own arc only
where no centre chain occupies the inside (the geometric inside of a chained corner is the chain).

Run:  python tools/barrier_bands.py <project-dir> [--out data/barrier_bands.json] [--config <track.config.json>]
      (--config: read another config against this project's data — dry runs against the workshop
      copy before ship_sd.sh syncs airoso's track.config.json down)
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIROSO = HERE.parent

BRIDGE_CLEAR_M = 9.0         # no centre chain this close to a declared span (the rail takes over; v4440 on
#                              SD ends 10.0 m before the I-8 span, v4441 7 m — invented, see GATES-CHANGELOG)
HAIRPIN_DEG = 135.0          # a corner this sharp keeps its whole box open (place_signs.HAIRPIN_DEG)
CAR_HALF_W_M = 0.95          # a 1.9 m car, for the grid clearance check
GRID_STAGGER_M = 1.4         # tools/layout_dummies.py: two columns at lane centre +/- 1.4 m
GRID_PITCH_M = 5.5
GRID_SLOTS_DEFAULT = 8
PIT_SETBACK_M = 45.0
PIT_PITCH_M = 7.0
PIT_SLOTS_DEFAULT = 8
MOUTH_CORNER_M = 3.0         # gap_mouths_blend's CORNER_M: the mouth line spans half-width + 3 m
BARRIER_HALF_DEFAULT = 0.335 # concrete_barrier_4m.obj x extent / 2 (re-measured from the asset when present)
EDGE_CENTRE_FROM_LIP = {"road": -0.485, "walk": +0.445}   # strip centre relative to the pavement lip (Q6)
KERB_OUTER_FROM_LIP = {"road": -0.87, "walk": -0.05}      # kerb's outer edge: 0.05 m clear of the strip face


def _load_place_signs():
    """tools/place_signs.py's corner detector, read-only (that file belongs to the signs workflow)."""
    spec = importlib.util.spec_from_file_location("_place_signs_ro", HERE / "place_signs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def _in_span(st_v, spans, clear=0.0):
    return any(a - clear <= st_v <= b + clear for a, b in spans)


def build(project_dir, out_name: str | None = None, config_path=None) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads(Path(config_path or (proj / "track.config.json")).read_text(encoding="utf-8"))
    race = cfg.get("race") or {}
    if not race.get("centre_runs"):
        raise SystemExit("[bands] track.config.json has no race.centre_runs — nothing to declare (ledger 0047)")
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    n = len(pts)
    if math.dist((pts[0][0], pts[0][2]), (pts[-1][0], pts[-1][2])) > 1e-6:
        raise SystemExit("[bands] centreline is not a closed lap (v[-1] != v[0]) — the loop tool only")
    ring = n - 1                                   # L13: the closure vertex repeats v0
    st = _stations(pts)
    lap = st[-1]
    mb = data / "median_bands.json"
    island_w = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else [0.0] * n
    if len(island_w) != n:
        raise SystemExit(f"[bands] median_bands.json ({len(island_w)}) vs centreline ({n}) length mismatch")
    bsp = data / "bridge.spans.auto.json"
    spans = [tuple(map(float, s)) for s in json.loads(bsp.read_text(encoding="utf-8"))] if bsp.exists() else []
    mp = data / "mouths.json"
    mouths = [m for m in (json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else [])
              if m.get("host") == "MAINLINE"]

    wide = float(race.get("wide_threshold_m", 17.0))
    edge_mode = str(race.get("edge_mode", "road"))
    if edge_mode not in EDGE_CENTRE_FROM_LIP:
        raise SystemExit(f"[bands] race.edge_mode must be road|walk, got {edge_mode!r}")
    edge_inset = float(race.get("edge_inset_m", 0.82)) if edge_mode == "road" else 0.0
    kerb_cfg = race.get("kerbs") or {}
    min_turn = float(kerb_cfg.get("min_turn_deg", 45.0))
    kerb_w = float(kerb_cfg.get("width_m", 1.0))
    kerb_h = float(kerb_cfg.get("height_m", 0.05))
    ext_lo, ext_hi = (kerb_cfg.get("outer_extension_m") or [10, 30])
    asset = AIROSO / str(race.get("barrier_profile_asset", "assets/models/concrete_barrier_4m.obj"))
    bhalf = _asset_half_width(asset)
    pitch = float(race.get("module_pitch_m", 4.04))

    fails: list[str] = []
    ps = _load_place_signs()
    corners = _corners(ps, pts, widths, min_turn)
    if not corners:
        fails.append("no corner with |D| >= %.0f deg found — a loop with no corners is a data error" % min_turn)
    streets, street_at = _streets(corners, (cfg.get("route") or {}).get("roads", []), ring)
    street_median_w = {}
    for row in streets:
        ws = sorted(widths[row["vertex_from"]:row["vertex_to"] + 1])
        street_median_w[row["street"]] = ws[len(ws) // 2] if ws else 0.0
    narrow_streets = sorted(s for s, w in street_median_w.items() if w < wide)
    isl_runs = _island_runs(island_w)
    nose = set()
    for a, b in isl_runs:
        nose.add(a); nose.add(b)
    hairpins = [c for c in corners if abs(c["D_deg"]) >= HAIRPIN_DEG]

    def in_hairpin(v):
        for c in hairpins:
            pc, pt = c["PC"], c["PT"]
            if pc <= pt:
                if pc <= v <= pt:
                    return True
            elif v >= pc or v <= pt:              # wraps the seam
                return True
        return False

    # ---- centre chain: declared runs, validated ---------------------------------------------
    centre_w = [0.0] * n
    runs_out = []
    declared = [(int(a), int(b)) for a, b in race["centre_runs"]]
    for a, b in declared:
        if not (0 <= a < b <= ring):
            fails.append(f"centre run [{a},{b}] is not a closed interval inside 0..{ring}")
            continue
        for v in range(a, b + 1):
            if widths[v] < wide:
                fails.append(f"centre run [{a},{b}]: v{v} is {widths[v]:.1f} m < {wide} m wide")
                break
        bad_island = [v for v in range(a + 1, b) if island_w[v] > 0]
        if bad_island:
            fails.append(f"centre run [{a},{b}]: {len(bad_island)} interior vertices on a median island "
                         f"(v{bad_island[0]}..v{bad_island[-1]}) — barriers lead up to medians, never on them")
        for end, prev_v, next_v, what in ((a, a - 1, a + 1, "start"), (b, b + 1, b - 1, "end")):
            if island_w[end] > 0 and end not in nose:
                fails.append(f"centre run [{a},{b}]: {what} v{end} is inside an island, not on its nose")
            if island_w[end] <= 0 and 0 <= prev_v <= ring and island_w[prev_v] > 0:
                fails.append(f"centre run [{a},{b}]: {what} v{end} stops one vertex short of the island nose "
                             f"v{prev_v} — the run must END ON the nose vertex (no 3 m wedge)")
        if any(_in_span(st[v], spans, BRIDGE_CLEAR_M) for v in range(a, b + 1)):
            fails.append(f"centre run [{a},{b}] enters a declared bridge span (+/- {BRIDGE_CLEAR_M:.0f} m)")
        on_narrow = [v for v in range(a, b + 1) if street_at[v] in narrow_streets]
        if on_narrow:
            fails.append(f"centre run [{a},{b}]: {len(on_narrow)} vertices on a narrow street "
                         f"({street_at[on_narrow[0]]}, median {street_median_w.get(street_at[on_narrow[0]], 0):.1f} m)")
        in_hp = [v for v in range(a, b + 1) if in_hairpin(v)]
        if in_hp:
            fails.append(f"centre run [{a},{b}]: {len(in_hp)} vertices inside a hairpin arc (v{in_hp[0]}..)")
        for v in range(a, b + 1):
            centre_w[v] = round(2 * bhalf, 3)
        runs_out.append({"kind": "centre", "i": a, "j": b, "street": street_at[a],
                         "street_end": street_at[b], "length_m": round(st[b] - st[a], 1),
                         "start_on_nose": a in nose, "end_on_nose": b in nose})
    # overlaps between declared runs
    for k in range(1, len(declared)):
        if declared[k][0] <= declared[k - 1][1]:
            fails.append(f"centre runs {declared[k-1]} and {declared[k]} overlap/touch — merge them")
    chain_len = sum(r["length_m"] for r in runs_out)
    # what the data would allow but the config leaves open (informational, never a failure)
    allowed = [v for v in range(ring + 1) if widths[v] >= wide and island_w[v] <= 0
               and street_at[v] not in narrow_streets and not in_hairpin(v)
               and not _in_span(st[v], spans, BRIDGE_CLEAR_M) and centre_w[v] <= 0]
    open_groups = []
    for v in allowed:
        if open_groups and v == open_groups[-1][1] + 1:
            open_groups[-1][1] = v
        else:
            open_groups.append([v, v])

    # ---- kerb-line (edge) strips: both sides, whole loop, gapped only in bridge spans ---------
    edge_strip = [0] * n
    edge_inset_v = [0.0] * n
    for v in range(n):
        if _in_span(st[v], spans):
            continue
        edge_strip[v] = 1
        edge_inset_v[v] = edge_inset
    gaps = []
    v = 0
    while v < n:
        if edge_strip[v]:
            v += 1
            continue
        g0 = v
        while v < n and not edge_strip[v]:
            v += 1
        gaps.append({"i": g0, "j": v - 1, "station_from_m": round(st[g0], 1), "station_to_m": round(st[v - 1], 1)})
    if len(gaps) != len(spans):
        fails.append(f"edge gaps ({len(gaps)}) != declared bridge spans ({len(spans)}) — a span with no vertex "
                     f"inside it, or a gap outside any span")
    for side in ("L", "R"):
        v = 0
        while v < n:
            if not edge_strip[v]:
                v += 1
                continue
            a = v
            s0 = street_at[a]
            while v + 1 < n and edge_strip[v + 1] and street_at[v + 1] == s0:
                v += 1
            runs_out.append({"kind": f"edge_{side}", "i": a, "j": v, "street": s0,
                             "length_m": round(st[v] - st[a], 1)})
            v += 1

    # ---- sealed mouths: the edge strip runs straight across each mainline mouth ----------------
    closed = []
    for m in mouths:
        h = int(m["host_vertex"])
        half = float(m.get("connector_width_m", 10.0)) / 2.0 + MOUTH_CORNER_M
        side = "L" if int(m.get("side", 1)) > 0 else "R"
        lo = h
        while lo > 0 and st[h] - st[lo - 1] <= half:
            lo -= 1
        hi = h
        while hi < ring and st[hi + 1] - st[h] <= half:
            hi += 1
        sgn = -1.0 if side == "R" else 1.0          # left of forward travel = +n = (-tz, tx)
        poly = []
        for v in range(lo, hi + 1):
            a, b = pts[max(0, v - 1)], pts[min(ring, v + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / L, tx / L
            off = sgn * (widths[v] / 2.0 + EDGE_CENTRE_FROM_LIP[edge_mode])
            poly.append([round(pts[v][0] + nx * off, 3), round(pts[v][1], 3), round(pts[v][2] + nz * off, 3)])
        if not all(edge_strip[v] for v in range(lo, hi + 1)):
            fails.append(f"mouth {m['connector']} at v{h}: the edge strip is gapped across the mouth line")
        closed.append({"connector": m["connector"], "host_vertex": h, "side": side,
                       "connector_width_m": m.get("connector_width_m"), "vertex_from": lo, "vertex_to": hi,
                       "policy": "sealed: strip continuous across the mouth line on the connector's 1ROAD (Q1)",
                       "polyline_xyz_m": poly})

    # ---- race kerbs at the detected corners -------------------------------------------------
    kerbs = []
    for c in corners:
        apex, pc, pt = c["apex"], c["PC"], c["PT"]
        inside = "R" if c["sign"] < 0 else "L"      # heading decreasing = right-hander
        outside = "L" if inside == "R" else "R"
        E = max(float(ext_lo), min(float(ext_hi), 2.0 * c["R_apex_m"]))
        wraps = pc > pt

        def _back(v0, dist):
            v1 = v0
            walked = 0.0
            while walked < dist:
                nv = v1 - 1 if v1 > 0 else ring - 1
                walked += st[v1] - st[nv] if v1 > 0 else st[ring] - st[ring - 1]
                v1 = nv
            return v1

        def _fwd(v0, dist):
            v1 = v0
            walked = 0.0
            while walked < dist:
                nv = v1 + 1 if v1 < ring else 1
                walked += st[nv] - st[v1] if v1 < ring else st[1] - st[0]
                v1 = nv
            return v1

        oi, oj = _back(pc, E), _fwd(pt, E)
        kerbs.append({"apex": apex, "side": outside, "kind": "outside", "i": oi, "j": oj,
                      "wraps": oi > oj, "R_apex_m": c["R_apex_m"], "D_deg": c["D_deg"], "extension_m": round(E, 1)})
        if centre_w[apex] <= 0:
            kerbs.append({"apex": apex, "side": inside, "kind": "inside", "i": pc, "j": pt, "wraps": wraps,
                          "R_apex_m": c["R_apex_m"], "D_deg": c["D_deg"], "extension_m": 0.0})
    for k in kerbs:
        # a kerb exists only where the kerb-line barrier does: clip a run that reaches onto a bridge
        # deck (the seam corner's outside kerb starts on the I-8 overcrossing) to the strip's vertices
        rng = list(range(k["i"], k["j"] + 1)) if not k["wraps"] else list(range(k["i"], ring)) + list(range(0, k["j"] + 1))
        kept = [v for v in rng if edge_strip[v]]
        if len(kept) != len(rng):
            if not kept:
                fails.append(f"kerb at apex v{k['apex']} ({k['kind']}) lies entirely inside a bridge gap")
                continue
            k["clipped_from"] = [k["i"], k["j"]]
            k["i"], k["j"] = kept[0], kept[-1]
            k["wraps"] = kept[0] > kept[-1]

    # ---- grid / pit no-gap zones + clearance ------------------------------------------------
    no_gap = []
    grid_slots = int(race.get("grid_slots", GRID_SLOTS_DEFAULT))
    pit_slots = int(race.get("pit_slots", PIT_SLOTS_DEFAULT))
    for lo_ in cfg.get("layouts", []):
        start = lo_.get("start") or {}
        if not start:
            continue
        gv = int(start.get("grid_vertex", start.get("vertex", 0)))
        off = abs(float(start.get("offset_right_m", 0.0)))
        reverse = str(lo_.get("direction", "forward")) == "reverse"
        behind = PIT_SETBACK_M + PIT_PITCH_M * pit_slots
        s_pole = st[gv]
        if reverse:
            s0, s1 = s_pole, min(lap, s_pole + behind)
        else:
            s0, s1 = max(0.0, s_pole - behind), s_pole
        vs = [v for v in range(n) if s0 - 1e-6 <= st[v] <= s1 + 1e-6]
        if not vs:
            continue
        need = off + GRID_STAGGER_M + CAR_HALF_W_M
        clear = min(widths[v] / 2.0 - edge_inset - need for v in vs)
        if any(not edge_strip[v] for v in vs):
            fails.append(f"layout {lo_.get('id')}: grid/pit zone v{vs[0]}..v{vs[-1]} crosses a bridge gap")
        if clear < 0:
            fails.append(f"layout {lo_.get('id')}: grid column edge {need:.2f} m vs barrier face "
                         f"{min(widths[v] for v in vs)/2 - edge_inset:.2f} m — {clear:+.2f} m")
        no_gap.append({"layout": lo_.get("id"), "i": vs[0], "j": vs[-1], "station_from_m": round(s0, 1),
                       "station_to_m": round(s1, 1), "grid_clearance_m": round(clear, 2),
                       "grid_slots": grid_slots, "pit_slots": pit_slots})

    out = {
        "version": 1,
        "_doc": "Declared race-furniture bands (ledger 0047). Index = vertex of data/centerline.local.json "
                "(engine frame x=E, y=up, z=N; same count as gate_centerline.json). centre_w_by_vertex: the "
                "centre chain's base width where it stands (0 elsewhere, incl. every island vertex except the "
                "shared nose). edge_strip_by_vertex: 1 where the kerb-line barrier runs on both curb faces "
                "(0 inside declared bridge spans). edge_inset_by_vertex: the LANE inset the strip takes from "
                "the lip (road mode) — 0 in walk mode. Band centres for the gates: centre = the centreline; "
                "edge = half_w + params.edge_centre_from_lip_m (signed outward). Written by "
                "tools/barrier_bands.py; consumed by tools/author_race_blend.py and scripts/geometry/median_zone.py.",
        "n": n,
        "lap_m": round(lap, 1),
        "params": {
            "wide_threshold_m": wide, "barrier_half_m": bhalf, "barrier_w_m": round(2 * bhalf, 3),
            "barrier_height_m": float(race.get("barrier_height_m", 1.2)), "module_pitch_m": pitch,
            "barrier_profile_asset": str(race.get("barrier_profile_asset", "")),
            "edge_mode": edge_mode, "edge_inset_m": edge_inset,
            "edge_centre_from_lip_m": EDGE_CENTRE_FROM_LIP[edge_mode],
            "kerb_width_m": kerb_w, "kerb_height_m": kerb_h,
            "kerb_outer_from_lip_m": KERB_OUTER_FROM_LIP[edge_mode],
            "kerb_min_turn_deg": min_turn, "kerb_outer_extension_m": [float(ext_lo), float(ext_hi)],
            "bridge_clear_m": BRIDGE_CLEAR_M, "hairpin_deg": HAIRPIN_DEG,
            "mouths": str(race.get("mouths", "sealed")), "interior_corners": str(race.get("interior_corners", "continuous")),
            "narrow_streets": narrow_streets, "street_median_w_m": street_median_w,
        },
        "centre_w_by_vertex": centre_w,
        "edge_strip_by_vertex": edge_strip,
        "edge_inset_by_vertex": edge_inset_v,
        "runs": runs_out,
        "closed_mouths": closed,
        "kerbs": kerbs,
        "no_gap_zones": no_gap,
        "streets": streets,
        "corners": corners,
        "bridge_spans_m": [list(s) for s in spans],
        "edge_gaps": gaps,
        "declared_open": [{"i": a, "j": b, "length_m": round(st[b] - st[a], 1), "street": street_at[a]} for a, b in open_groups],
        "summary": {
            "centre_runs": len([r for r in runs_out if r["kind"] == "centre"]),
            "chain_length_m": round(chain_len, 1),
            "centre_verts": sum(1 for w in centre_w if w > 0),
            "edge_verts": sum(edge_strip),
            "edge_gaps": len(gaps),
            "kerbs": len(kerbs),
            "corners": len(corners),
            "island_runs": [list(r) for r in isl_runs],
            "nose_vertices": sorted(nose),
        },
        "fails": fails,
    }
    out_path = data / (out_name or "barrier_bands.json")
    out_path.write_text(json.dumps(out), encoding="utf-8")
    s = out["summary"]
    print(f"[bands] {proj.name}: chain {s['centre_runs']} runs / {s['chain_length_m']:.0f} m on {s['centre_verts']} verts; "
          f"edge strips on {s['edge_verts']}/{n} verts ({s['edge_gaps']} bridge gaps); {s['kerbs']} kerbs at "
          f"{s['corners']} corners; {len(closed)} sealed mouths; mode {edge_mode} inset {edge_inset} m; half {bhalf} m")
    for r in runs_out:
        if r["kind"] == "centre":
            print(f"[bands]   centre v{r['i']}-v{r['j']} {r['length_m']:7.1f} m  {r['street']}"
                  f"{' -> ' + r['street_end'] if r['street_end'] != r['street'] else ''}"
                  f"  nose:{'S' if r['start_on_nose'] else '-'}{'E' if r['end_on_nose'] else '-'}")
    for g in out["declared_open"]:
        print(f"[bands]   declared open (data would allow): v{g['i']}-v{g['j']} {g['length_m']:.0f} m {g['street']}")
    for k in kerbs:
        print(f"[bands]   kerb apex v{k['apex']} {k['kind']:7} side {k['side']} v{k['i']}-v{k['j']}"
              f"{' (wraps)' if k['wraps'] else ''} R {k['R_apex_m']} D {k['D_deg']}")
    for z in no_gap:
        print(f"[bands]   no-gap zone {z['layout']}: v{z['i']}-v{z['j']} grid clearance {z['grid_clearance_m']:+.2f} m")
    print(f"[bands] wrote {out_path}")
    if fails:
        print("[bands] FAIL:")
        for f in fails:
            print("   -", f)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python tools/barrier_bands.py <project-dir> [--out <name.json>]")
    out_name = None
    config_path = None
    if "--out" in argv:
        k = argv.index("--out")
        out_name = Path(argv[k + 1]).name
        del argv[k:k + 2]
    if "--config" in argv:
        k = argv.index("--config")
        config_path = argv[k + 1]
        del argv[k:k + 2]
    out = build(argv[0], out_name, config_path)
    return 1 if out["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
