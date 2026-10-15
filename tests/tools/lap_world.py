"""A synthetic world with a SECOND LAP (ledger 0054 phase 2 groundwork) — the fixture tests/tools/test_race_lap.py
drives every race tool on.

    MAINLINE   a rounded rectangle (800 x 440 m, corner radius 40 m, 20 m wide, 3 m vertices — a 2.4 km lap, the
               scale the per-km gates are set for), run counter-clockwise from v0 on the bottom edge (x = +240,
               heading east)
    cross#0    a connector straight up x = 0 from the bottom edge's inner curb (z = -210) to the top edge's (z = +210),
               20 m wide — trimmed at the mainline edge like tools/trim_connectors.py leaves every side street
    lap "w"    the WEST half: MAINLINE from the top junction (x = 0, z = +110) counter-clockwise round the two west
               corners to the bottom junction (x = 0, z = -110), then north up cross#0 — partly on the mainline,
               partly on the connector (a 1.6 km lap); two sharp junction corners (the abandoned east halves of the
               top and bottom edges are its branches) and two 40 m arcs

Layouts: street (the mainline, no furniture), race_cw (the mainline, token cw), lap_f / lap_r (lap w forward /
reverse, tokens lf / lr). Each corridor is declared the way Lake Murray's is (track.config.json race.corridor:
boxes PC-2 .. PT+2 at the corners the race turns at, a whole-street zone, closure runs pinned between) — on its OWN
line's vertex numbers, from the corners tools/barrier_bands.py itself detects.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import barrier_bands as bb  # noqa: E402
from scripts.geometry import race_lap  # noqa: E402

XH, ZH, R, W = 400.0, 220.0, 40.0, 20.0
LAP = "w"


def _edge(a, b, n):
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]


def _arc(cx, cz, a0, a1, n):
    return [(cx + R * math.cos(a0 + (a1 - a0) * k / n), cz + R * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n)]


def mainline_xz():
    """CCW from the bottom-left end of the bottom edge; returns (ring points, index of x=0 bottom, x=0 top)"""
    pts = []
    pts += _edge((-XH + R, -ZH), (XH - R, -ZH), 240)                     # bottom, east: x = -360 + 3 k
    pts += _arc(XH - R, -ZH + R, -math.pi / 2, 0.0, 21)                    # BR
    pts += _edge((XH, -ZH + R), (XH, ZH - R), 120)                         # right, north
    pts += _arc(XH - R, ZH - R, 0.0, math.pi / 2, 21)                      # TR
    pts += _edge((XH - R, ZH), (-XH + R, ZH), 240)                         # top, west
    pts += _arc(-XH + R, ZH - R, math.pi / 2, math.pi, 21)                 # TL
    pts += _edge((-XH, ZH - R), (-XH, -ZH + R), 120)                       # left, south
    pts += _arc(-XH + R, -ZH + R, math.pi, 1.5 * math.pi, 21)              # BL
    # rotate so v0 sits on the bottom edge at k = 200 (x = +240), away from both junctions
    k0 = 200
    pts = pts[k0:] + pts[:k0]
    bot = min(range(len(pts)), key=lambda i: math.hypot(pts[i][0], pts[i][1] + ZH))
    top = min(range(len(pts)), key=lambda i: math.hypot(pts[i][0], pts[i][1] - ZH))
    assert abs(pts[bot][0]) < 1e-6 and abs(pts[top][0]) < 1e-6
    return pts, bot, top


def connector_xz():
    return [(0.0, -ZH + W / 2 + 3.0 * k) for k in range(int(round((2 * ZH - W) / 3.0)) + 1)]


def corridor_for(pts, widths, *, whole_over=None):
    """a race.corridor declaration on THIS line, Lake Murray's way: a box PC-2 .. PT+2 at every detected corner,
    except the corners named in `whole_over` (apex predicate), which a whole-street zone spans together with
    everything between them; closure runs pinned between. Returns (corridor dict, corners)."""
    ps = bb._load_place_signs()
    corners = bb._corners(ps, pts, widths, 45.0)
    m = len(pts) - 1
    boxes, wcs = [], []
    for c in corners:
        if whole_over and whole_over(c):
            wcs.append(c)
        else:
            boxes.append({"apex": c["apex"], "i": (c["PC"] - 2) % m, "j": (c["PT"] + 2) % m})
    if wcs:
        # the whole zone runs from 3 vertices before the first named corner's PC to 3 after the last one's PT
        # (in increasing order, wrapping the seam when it must)
        first = min(wcs, key=lambda c: c["PC"] if c["PC"] > m // 2 else c["PC"] + m)
        last = max(wcs, key=lambda c: c["PT"] if c["PT"] > m // 2 else c["PT"] + m)
        whole = [(first["PC"] - 3) % m, (last["PT"] + 3) % m]
    else:
        # the whole street over the seam (v0), from the box before it to the box after it — Lake Murray's shape
        # (its whole zone holds v0 too: race_corridor.solve starts its walk at the first free vertex)
        before = max(boxes, key=lambda b: b["j"])
        after = min(boxes, key=lambda b: b["i"])
        whole = [(before["j"] + 1) % m, (after["i"] - 1) % m]
    free = lambda v: (bb._RC.in_rng(v, whole[0], whole[1], m)
                      or any(bb._RC.in_rng(v, b["i"], b["j"], m) for b in boxes))
    start = next(q for q in range(m) if free(q))
    runs, q = [], 0
    while q < m:
        k = (start + q) % m
        if free(k):
            q += 1
            continue
        q1 = q
        while q1 + 1 < m and not free((start + q1 + 1) % m):
            q1 += 1
        runs.append([(start + q - 1) % m, (start + q1 + 1) % m])
        q = q1 + 1
    cor = {"clear_width_m": 11.36, "island_mode": "pavement", "whole": whole, "boxes": boxes, "closure_runs": runs,
           "rate_toward_race_side": 12, "rate_away": 6, "pin_zone_m": 120, "pin_rate_min": 6, "pin_rate": {},
           "steepest_pin_rate": 3, "base_open_m": 60, "base_sigma_m": 20, "island_env_m": 30, "attract_m": 40,
           "smooth_sigma_m": 4, "clear_floor_m": 10.86, "clear_hard_min_m": 6.5, "pocket_min_m": 2.0}
    return cor, corners


def _start(line_v, grid_v, sectors):
    return {"line_vertex": line_v, "grid_vertex": grid_v, "offset_right_m": 3.25, "sector_vertices": sectors}


def build(*, with_lap=True, mainline_race=True) -> tuple[Path, dict]:
    """the project dir and a facts dict (mainline / lap vertex numbers the tests pin against)"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    ring, bot, top = mainline_xz()
    main = [[x, 0.0, z] for x, z in ring] + [[ring[0][0], 0.0, ring[0][1]]]
    m = len(ring)
    mw = [W] * (m + 1)
    conn = connector_xz()
    (d / "data" / "centerline.local.json").write_text(json.dumps(
        {"points_xyz_m": main, "widths_m": mw, "origin": {"lon": 0.0, "lat": 0.0, "elev_m": 0.0}}), encoding="utf-8")
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": [0.0] * (m + 1), "runs": []}),
                                                  encoding="utf-8")
    (d / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [
        {"name": "cross#0", "kind": "connector", "points_xyz_m": [[x, 0.0, z] for x, z in conn],
         "widths_m": [W] * len(conn)}]}), encoding="utf-8")
    (d / "data" / "mouths.json").write_text(json.dumps({"mouths": [
        {"connector": "cross", "host": "MAINLINE", "host_vertex": bot, "side": 1, "connector_width_m": W,
         "piece": "cross#0", "end": "start"},
        {"connector": "cross", "host": "MAINLINE", "host_vertex": top, "side": 1, "connector_width_m": W,
         "piece": "cross#0", "end": "end"}]}), encoding="utf-8")
    (d / "data" / "bridge.spans.auto.json").write_text("[]", encoding="utf-8")
    # the mainline's own corridor: a box at each of its four 40 m corners, the whole street over v0's stretch
    mpts = [tuple(p) for p in main]
    mcor, mcorners = corridor_for(mpts, mw)
    # the timing sectors on straights, in driving order from the line (v10, the bottom edge): the right edge, the top
    sec = [min(range(m), key=lambda k: math.hypot(mpts[k][0] - XH, mpts[k][2])),
           min(range(m), key=lambda k: math.hypot(mpts[k][0] + 100.0, mpts[k][2] - ZH))]
    layouts = [{"id": "street", "name": "Free Roam", "kind": "street", "direction": "forward", "race_furniture": False,
                "start": _start(10, 5, sec)}]
    if mainline_race:
        layouts.append({"id": "race_cw", "name": "Speedway", "kind": "race", "direction": "forward",
                        "race_furniture": True, "closure_token": "cw", "start": _start(10, 5, sec)})
    cfg = {"slug": "t", "name": "T", "mirror_x": False, "loop": True, "layouts": layouts,
           "route": {"roads": []},
           "race": {"barrier_height_m": 1.2, "module_pitch_m": 4.04, "edge_mode": "road", "edge_inset_m": 0.82,
                    "edge_gaps": "none", "mouths": "sealed", "corridor": mcor,
                    "kerbs": {"min_turn_deg": 45, "width_m": 1.0, "height_m": 0.05, "outer_extension_m": [10, 30]}}}
    facts = {"mainline_n": m, "bot": bot, "top": top, "mainline_corners": [c["apex"] for c in mcorners]}
    if with_lap:
        cfg["race"]["laps"] = {LAP: {"pieces": [{"line": "MAINLINE", "from": top, "to": bot},
                                                {"line": "cross#0", "from": 0, "to": len(conn) - 1}],
                                     "roads": []}}
        rec = race_lap.stitch(d, cfg, LAP)
        lpts = [tuple(p) for p in rec["points_xyz_m"]]
        lw = rec["widths_m"]
        lm = len(lpts) - 1
        # the connector (and both junction corners) is the whole street; the two west arcs are open boxes
        on_conn = lambda c: abs(lpts[c["apex"]][0]) < 15.0
        lcor, lcorners = corridor_for(lpts, lw, whole_over=on_conn)
        cfg["race"]["laps"][LAP]["corridor"] = lcor
        # a stitched junction is a zero-radius corner: its inside offset never crosses itself, so the inside kerb has
        # no corner to be trimmed to — DECLARED dropped (race.laps.<lap>.kerbs.trims, never derived)
        cfg["race"]["laps"][LAP]["kerbs"] = {"trims": [
            {"apex": c["apex"], "kind": "inside", "drop": True,
             "why": "stitched junction (zero radius): no inside kerb on the lap's own corner"}
            for c in lcorners if on_conn(c)]}
        k_conn = [k for k, sv in enumerate(rec["source_by_vertex"][:lm]) if sv[0] == "cross#0"]
        mid = k_conn[len(k_conn) // 2]
        top_mid = next(k for k in range(lm) if lpts[k][2] > ZH - 1 and lpts[k][0] < -79 and lpts[k][0] > -82)
        left_mid = next(k for k in range(lm) if lpts[k][0] < -XH + 1 and abs(lpts[k][2]) < 2)
        bot_mid = next(k for k in range(lm) if lpts[k][2] < -ZH + 1 and lpts[k][0] < -79 and lpts[k][0] > -82)
        cfg["layouts"] += [
            {"id": "lap_f", "name": "West Speedway", "kind": "race", "direction": "forward", "race_furniture": True,
             "closure_token": "lf", "lap": LAP, "start": _start(mid + 3, mid - 3, [top_mid, left_mid])},
            {"id": "lap_r", "name": "West Speedway Reverse", "kind": "race", "direction": "reverse",
             "race_furniture": True, "closure_token": "lr", "lap": LAP, "start": _start(mid - 3, mid + 3,
                                                                                         [bot_mid, left_mid])}]
        facts.update({"lap_n": lm, "lap_conn": (k_conn[0], k_conn[-1]), "lap_mid": mid,
                      "lap_corners": [c["apex"] for c in lcorners], "lap_whole": lcor["whole"],
                      "lap_boxes": lcor["boxes"], "lap_runs": lcor["closure_runs"]})
    (d / "track.config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    return d, facts


# ---------------------------------------------------------------------------------------------
# a BUILT gate OBJ for one layout (road ribbons + grass + the authored furniture as K-rail prisms) — what
# scripts.modkit.kn5_to_gate_obj extracts from the kn5 set the layout loads
def _ribbon(pts, widths, y=0.0):
    n = len(pts)
    verts, tris = [], []
    for k in range(n):
        a, b = pts[max(0, k - 1)], pts[min(n - 1, k + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        h = widths[k] / 2.0
        verts += [(pts[k][0] + nx * h, y, pts[k][2] + nz * h), (pts[k][0] - nx * h, y, pts[k][2] - nz * h)]
    for k in range(n - 1):
        a = 2 * k
        tris += [(a, a + 2, a + 1), (a + 1, a + 2, a + 3)]
    for t in range(len(tris)):           # face up (+y): AC's one-sided physics, drive_test reads the top
        a_, b_, c_ = tris[t]
        A, B, C = verts[a_], verts[b_], verts[c_]
        ny = (B[2] - A[2]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[2] - A[2])
        if ny < 0:
            tris[t] = (a_, c_, b_)
    return {"vertices": verts, "tris": tris}


def _prism(centres, half=0.335, y0=0.0, y1=1.2):
    """a closed box strip along the polyline of (x, z) centres"""
    verts, tris = [], []
    n = len(centres)
    for k, (x, z) in enumerate(centres):
        a, b = centres[max(0, k - 1)], centres[min(n - 1, k + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L * half, tx / L * half
        verts += [(x + nx, y0, z + nz), (x - nx, y0, z - nz), (x - nx, y1, z - nz), (x + nx, y1, z + nz)]
    for r in range(n - 1):
        a = 4 * r
        tris += [(a + 3, a + 2, a + 6), (a + 3, a + 6, a + 7), (a + 1, a + 2, a + 6), (a + 1, a + 6, a + 5),
                 (a + 0, a + 3, a + 7), (a + 0, a + 7, a + 4)]
    last = 4 * (n - 1)
    tris += [(0, 1, 2), (0, 2, 3), (last, last + 1, last + 2), (last, last + 2, last + 3)]
    return {"vertices": verts, "tris": tris}


def write_obj(path: Path, groups) -> None:
    lines, base = [], 1
    for name, mesh in groups:
        lines.append(f"o {name}")
        for x, y, z in mesh["vertices"]:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        for a, b, c in mesh["tris"]:
            lines.append(f"f {base + a} {base + b} {base + c}")
        base += len(mesh["vertices"])
    path.write_text("# gate OBJ (synthetic lap world)\n" + "\n".join(lines) + "\n", encoding="utf-8")


def gate_obj(d: Path, layout_id: str, plans, *, drop=()) -> Path:
    """data/track.<layout_id>.obj: both road ribbons + a grass plane + every plan of this layout's kn5 set (the common
    set of its group + ITS closure) as a prism along the planned strip centres; `drop` = object names left out"""
    import race_furniture as rf
    cl = json.loads((d / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    cn = json.loads((d / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"][0]
    groups = [("1ROAD_main", _ribbon(cl["points_xyz_m"], cl["widths_m"])),
              ("1ROAD_cross", _ribbon(cn["points_xyz_m"], cn["widths_m"], y=0.0))]
    gx = [(x, -0.05, z) for z in range(-280, 281, 20) for x in range(-460, 461, 20)]
    nxg = len(range(-460, 461, 20))
    gt = []
    for j in range(len(range(-280, 281, 20)) - 1):
        for i in range(nxg - 1):
            a = j * nxg + i
            gt += [(a, a + nxg + 1, a + 1), (a, a + nxg, a + nxg + 1)]
    groups.append(("1GRASS_plane", {"vertices": gx, "tris": gt}))
    for p in plans:
        name = rf.object_name(p)
        if name in drop:
            continue
        if p["kind"] in ("edge", "close"):
            groups.append((name, _prism([rf._strip_xz(r) for r in p["rings"]])))
    out = d / "data" / f"track.{layout_id}.obj"
    write_obj(out, groups)
    return out
