"""Race kerbs by RULE at a race layout's corners, written as a kerbs file for tools/author_kerbs_blend.py (ledger 0079
round K). Kevin, 2026-11-04 (ledger 0079): Sand Creek gets "race curbs". Sand Creek's public streets carry no kerb paint
(NAIP, ledger 0070 Q1), so nothing here is measured: the corners are the layout's own curvature, the rule and every
number below are AUTHORED per Kevin's request and listed in fleet/GATES-CHANGELOG.md (2026-11-05, round K).

THE RULE (engine frame x = E, y = up, z = N of data/centerline.local.json; the race layout drives increasing vertex):
  corners   tools/place_signs.py's own corner detector (the one Lake Murray's arrow signs and race kerbs stand on: 1 m
            stations, curvature over a 12 m window, PC / PT at the R = 60 m crossings, D the integrated turn), every
            corner with |D| >= MIN_TURN_DEG (Lake Murray's race.kerbs.min_turn_deg, 45 deg) and R_apex <= MAX_R_M:
            real corners, not every bend.
  apex      the INSIDE kerb (left edge for a left turn, D > 0), from PC to PT.
  exit      the OUTSIDE kerb from the apex to PT + E, E = clamp(2 R_apex, EXIT_MIN_M, EXIT_MAX_M) (Lake Murray's race
            kerb outer extension, race_furniture.KERB_EXT_MIN_M / MAX_M, 10 / 30 m): where a car tracks out.
  across    on the lane's own surface: in_m = -kerb.width_m .. out_m = 0 (the kerb's outer edge on the ribbon's lane
            edge, "edge": "ribbon" — no live edge to read an offset from); the height is kerb.height_m and the ends
            ramp over kerb.end_ramp_m (tools/author_kerbs_blend.py, kerb.placement "measured").
  merge     two runs that overlap on one edge (an S-bend: the first corner's exit and the next one's apex) are ONE kerb,
            their union, carrying both corners' rules. A run may cross the lap's seam (v m-1 -> v0).
Each run's edge_lonlat is the lane edge (centre +- width / 2 along the left normal of the central difference), one point
per vertex, in lon / lat by the same flat-earth metres-per-degree author_kerbs_blend.py reads them with.

    python tools/race_kerbs.py <project-dir> [--out data/kerbs.race.json]

Reads track.config.json kerb.race_rule (opt-in; absent = exit 0 and nothing written) and data/centerline.local.json.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
MIN_TURN_DEG = 45.0     # [authored] Lake Murray's race.kerbs.min_turn_deg (its race-kerb and arrow-sign corners)
MAX_R_M = 60.0          # [authored] the detector's own corner bound (place_signs: a corner is a run of |k| > 1/60)
EXIT_MIN_M, EXIT_MAX_M = 10.0, 30.0   # [authored] Lake Murray's outside-kerb extension E = clamp(2 R_apex, 10, 30)


def _place_signs():
    spec = importlib.util.spec_from_file_location("_place_signs_rk", AIROSO / "tools" / "place_signs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mpd(lat0):
    """metres per degree (lon, lat) — tools/author_kerbs_blend.mpd, the inverse it keys these points with"""
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def stations(pts):
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return st


def lane_edge(pts, widths, m, k, side):
    """(x, z) of the lane edge at vertex k: centre + side x w/2 along the left normal of the central difference"""
    a, b = pts[(k - 1) % m], pts[(k + 1) % m]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    nx, nz = -tz / L, tx / L            # left normal (x = E, z = N)
    h = widths[k] / 2.0 * (1.0 if side == "left" else -1.0)
    return pts[k][0] + nx * h, pts[k][2] + nz * h


def vertex_at(st, s, m):
    """the first vertex at or past station s on the closed lap"""
    lap = st[m]
    s %= lap
    for k in range(m):
        if st[k] >= s - 1e-6:
            return k
    return 0


def rule(cfg, cl):
    rr = (cfg.get("kerb") or {}).get("race_rule") or {}
    min_turn = float(rr.get("min_turn_deg", MIN_TURN_DEG))
    max_r = float(rr.get("max_r_m", MAX_R_M))
    ext_lo, ext_hi = (rr.get("exit_extension_m") or [EXIT_MIN_M, EXIT_MAX_M])
    w = float((cfg.get("kerb") or {}).get("width_m", 1.0))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(x) for x in cl["widths_m"]]
    m = len(pts) - 1
    st = stations(pts)
    ps = _place_signs()
    rb = ps.Ribbon("MAINLINE", pts, widths, True)
    corners = []
    for c in ps.detect_corners(rb):
        rec = {"apex": rb.vertex(c["apex"]), "PC": rb.vertex(c["PC"]), "PT": rb.vertex(c["PT"]),
               "apex_station_m": round(c["apex"], 1), "PT_station_m": round(c["PT"], 1),
               "D_deg": round(c["D_deg"], 2), "R_apex_m": round(c["R_apex_m"], 2)}
        if abs(rec["D_deg"]) < min_turn or rec["R_apex_m"] > max_r:
            continue
        corners.append(rec)
    corners.sort(key=lambda c: c["apex"])
    runs = []
    for c in corners:
        inside = "left" if c["D_deg"] > 0 else "right"
        outside = "right" if inside == "left" else "left"
        E = min(ext_hi, max(ext_lo, 2.0 * c["R_apex_m"]))
        exit_end = vertex_at(st, c["PT_station_m"] + E, m)
        for kind, side, i, j in (("apex", inside, c["PC"], c["PT"]), ("exit", outside, c["apex"], exit_end)):
            # a run may cross the lap's seam (v m-1 -> v0): it is the ring interval i .. j, unwrapped to i .. j + m
            runs.append({"apex": [c["apex"]], "kind": [kind], "side": side, "i": i, "j": j if j > i else j + m,
                         "D_deg": [c["D_deg"]], "R_apex_m": [c["R_apex_m"]],
                         "exit_extension_m": [round(E, 1) if kind == "exit" else None]})
    # two runs on one edge that overlap (an S: the first corner's exit and the second's apex on the same edge) are ONE
    # kerb, their union, recorded with both corners' rules — never two sheets laid over each other
    runs.sort(key=lambda r: (r["side"], r["i"]))
    kept = []
    for r in runs:
        q = kept[-1] if kept and kept[-1]["side"] == r["side"] else None
        if q is not None and r["i"] <= q["j"]:
            q["j"] = max(q["j"], r["j"])
            for key in ("apex", "kind", "D_deg", "R_apex_m", "exit_extension_m"):
                q[key] += r[key]
            continue
        kept.append(dict(r))
    if len(kept) > 1 and kept[-1]["side"] == kept[0]["side"] and kept[-1]["j"] >= kept[0]["i"] + m:
        raise SystemExit("[race-kerbs] a kerb run wraps onto another across the seam: not handled — author it by hand")
    lon0, lat0 = float(cl["origin"]["lon"]), float(cl["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    out, dropped = [], []
    for r in kept:
        ks = [k % m for k in range(r["i"], r["j"] + 1)]
        edge = [lane_edge(pts, widths, m, k, r["side"]) for k in ks]
        # a lane edge that steps BACKWARD (a junction flare wider than its own turn: the edge offset folds) has no
        # kerb line to follow — the kerb sheet would turn inside-out; the run is dropped and named, never bent
        back = [ks[q + 1] for q in range(len(ks) - 1)
                if (edge[q + 1][0] - edge[q][0]) * (pts[ks[q + 1]][0] - pts[ks[q]][0])
                + (edge[q + 1][1] - edge[q][1]) * (pts[ks[q + 1]][2] - pts[ks[q]][2]) <= 0.0]
        if back:
            dropped.append({"corner_apex_vertex": r["apex"], "kind": r["kind"], "side": r["side"],
                            "vertices": [r["i"] % m, r["j"] % m],
                            "why": f"the lane edge folds back at v{back[0]}..v{back[-1]} ({len(back)} step(s)): the "
                                   f"half-width exceeds the turn's radius there (a junction flare)"})
            continue
        arc = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(edge, edge[1:]))
        out.append({"side": r["side"], "s0": round(st[r["i"] % m], 1), "s1": round(st[r["j"] % m], 1),
                    "in_m": -w, "out_m": 0.0, "edge": "ribbon", "colour": None,
                    "rule": {"corner_apex_vertex": r["apex"], "kind": r["kind"], "vertices": [r["i"] % m, r["j"] % m],
                             "D_deg": r["D_deg"], "R_apex_m": r["R_apex_m"], "exit_extension_m": r["exit_extension_m"],
                             "edge_arc_m": round(arc, 1)},
                    "edge_lonlat": [[round(lon0 + x / m_lon, 9), round(lat0 + z / m_lat, 9)] for x, z in edge]})
    return {"_doc": "AUTHORED by rule, not measured (tools/race_kerbs.py; ledger 0079 round K; fleet/GATES-CHANGELOG.md "
                    "2026-11-05 round K): Sand Creek's race kerbs, apex + exit at each race corner, on the lane",
            "rule": {"min_turn_deg": min_turn, "max_r_m": max_r, "exit_extension_m": [ext_lo, ext_hi], "width_m": w},
            "corners": corners, "kerbs": out, "dropped": dropped}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    proj = Path(argv[0])
    out_rel = argv[argv.index("--out") + 1] if "--out" in argv else "data/kerbs.race.json"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if not (cfg.get("kerb") or {}).get("race_rule"):
        print("[race-kerbs] no kerb.race_rule: nothing to do")
        return 0
    cl = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    rec = rule(cfg, cl)
    (proj / out_rel).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"[race-kerbs] {len(rec['corners'])} corners (|D| >= {rec['rule']['min_turn_deg']} deg, R <= "
          f"{rec['rule']['max_r_m']} m) -> {len(rec['kerbs'])} kerb runs; wrote {out_rel}")
    for k in rec["kerbs"]:
        r = k["rule"]
        print(f"[race-kerbs]   {'+'.join(f'v{a} {t}' for a, t in zip(r['corner_apex_vertex'], r['kind'])):24} "
              f"{k['side']:5} v{r['vertices'][0]}-v{r['vertices'][1]} ({r['edge_arc_m']} m, s {k['s0']}-{k['s1']}, "
              f"D {r['D_deg']}, R {r['R_apex_m']} m)")
    for d in rec["dropped"]:
        print(f"[race-kerbs]   DROPPED {'+'.join(f'v{a} {t}' for a, t in zip(d['corner_apex_vertex'], d['kind']))} "
              f"{d['side']} v{d['vertices'][0]}-v{d['vertices'][1]}: {d['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
