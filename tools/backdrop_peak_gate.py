#!/usr/bin/env python3
"""The peak gate on a baked backdrop (PLAN 3b of tracks/denver-grand-prix: "bearing and height within 0.1 degrees
from the start line"; ledger 0096). It reads the BUILT mesh (the OBJ tools/backdrop_bake.py wrote), never the DEM that
placed it (LAWS L5), and compares what a driver's eye at the start line would see in that mesh with the horizon
study's numbers (horizon.3dep13.json: a separate program, rays over the DEM).

    python tools/backdrop_peak_gate.py <slug>_backdrop.obj tracks/_reference/front-range/bake.config.json <track> \
        [--report out.json]

For every named peak of the study's site:
  - the study's summit is the highest DEM cell in a box around the peak's nominal coordinate; the mesh's summit is the
    vertex of highest real elevation (mesh height plus the curvature drop at its distance from the origin) in the SAME
    box (the study file carries the box: summit_box_half_deg, nominal_lon_lat);
  - its bearing and its altitude above the horizontal from the eye (the start line, EYE_M over the ground) are
    measured in the mesh's own coordinates;
  - a peak the study calls VISIBLE must be in the mesh; its altitude must be within TOL_DEG of the study's, and the
    study's bearing must be within TOL_DEG of the mesh's top. The top is every vertex in the box standing within
    FLAT_DEG of the summit as seen from the eye: one point on a sharp peak, a span of bearings on a mesa, which has no
    single summit;
  - a peak the study calls hidden is reported and never fails: the bake is allowed to have dropped it.
Also fails: any object whose name starts with a digit (the backdrop is visual only).
Reported, not gated: the mesh's skyline against the study's, bearing by bearing.

Exit 0 = every visible peak within tolerance; 1 = not.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backdrop_bake import DEFAULTS, curvature_drop, geod_direct, to_local  # noqa: E402  (the frame's definition, nothing of the mesh)

TOL_DEG = 0.1        # PLAN 3b, the plan's own number
FLAT_DEG = 0.01      # vertices this close under the summit, as seen, are "the top" (a tenth of the tolerance; ours)
EYE_M = 1.2          # the study's eye height


def read_obj(path):
    """(vertices N x 3, triangles M x 3, object names) of an OBJ."""
    v, f, names = [], [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            c = ln[:2]
            if c == "v ":
                q = ln.split(); v.append((float(q[1]), float(q[2]), float(q[3])))
            elif c == "f ":
                idx = [int(tok.split("/")[0]) - 1 for tok in ln.split()[1:]]
                f.extend((idx[0], idx[i], idx[i + 1]) for i in range(1, len(idx) - 1))
            elif c in ("o ", "g "):
                names.append(ln[2:].strip())
    return np.array(v, float).reshape(-1, 3), np.array(f, np.int64).reshape(-1, 3), names


def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def skyline(V, T, eye, bearings, mid_deg):
    """The mesh's highest altitude (deg) on each bearing from the eye: the highest triangle edge crossing it."""
    dx = V[:, 0] - eye[0]; dz = V[:, 2] - eye[2]
    brg = (np.degrees(np.arctan2(dx, dz)) - mid_deg + 180.0) % 360.0 - 180.0          # about the arc's middle: no wrap
    alt = np.degrees(np.arctan2(V[:, 1] - eye[1], np.hypot(dx, dz)))
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); e.sort(axis=1)
    e = np.unique(e, axis=0)
    b0 = brg[e[:, 0]]; b1 = brg[e[:, 1]]; a0 = alt[e[:, 0]]; a1 = alt[e[:, 1]]
    lo = np.minimum(b0, b1); hi = np.maximum(b0, b1)
    order = np.argsort(lo); lo, hi, b0, b1, a0, a1 = lo[order], hi[order], b0[order], b1[order], a0[order], a1[order]
    span = float((hi - lo).max()) if len(lo) else 0.0
    out = []
    for b in bearings:
        t = (b - mid_deg + 180.0) % 360.0 - 180.0
        i0 = np.searchsorted(lo, t - span, "left"); i1 = np.searchsorted(lo, t, "right")
        s = slice(i0, i1); m = hi[s] >= t
        if not m.any():
            out.append(None); continue
        d = (b1[s] - b0[s])[m]
        w = np.where(np.abs(d) < 1e-12, 0.0, (t - b0[s][m]) / np.where(np.abs(d) < 1e-12, 1.0, d))
        out.append(float((a0[s][m] + w * (a1[s][m] - a0[s][m])).max()))
    return out


def gate(obj_path, horizon, site, origin, origin_elev_m, start_lon_lat, k=DEFAULTS["refraction_k"], arc=DEFAULTS["arc_deg"]):
    """The verdict as a dict; 'ok' is the gate."""
    V, T, names = read_obj(obj_path)
    digit = [n for n in names if n[:1].isdigit()]
    sx, sz = to_local(origin[0], origin[1], start_lon_lat[0], start_lon_lat[1])
    sx, sz = float(sx[0]), float(sz[0])
    eye = (sx, horizon["site_ground_m"][site] - origin_elev_m - float(curvature_drop(math.hypot(sx, sz), k)) + EYE_M, sz)
    d_origin = np.hypot(V[:, 0], V[:, 2])
    real = V[:, 1] + curvature_drop(d_origin, k) + origin_elev_m
    box = horizon.get("summit_box_half_deg")
    if not box:
        raise SystemExit("backdrop_peak_gate: the study file has no summit_box_half_deg; use one written by horizon_3dep.py --wgs84")
    rows = []
    for name, pk in horizon["peaks"][site].items():
        if pk is None:
            continue
        nlon, nlat = pk["nominal_lon_lat"]
        px, pz = to_local(origin[0], origin[1], nlon, nlat)
        cand = np.flatnonzero(np.hypot(V[:, 0] - px[0], V[:, 2] - pz[0]) <= 2500.0)
        if len(cand):                                                # the study's box, in the mesh's own positions
            vlon, vlat = geod_direct(origin[0], origin[1], np.degrees(np.arctan2(V[cand, 0], V[cand, 2])), d_origin[cand])
            cand = cand[(np.abs(vlon - nlon) <= box[0]) & (np.abs(vlat - nlat) <= box[1])]
        near = cand
        row = {"peak": name, "study_visible": bool(pk["visible"]), "study_bearing_deg": pk["bearing_deg"],
               "study_altitude_deg": pk["altitude_deg"], "study_clearance_deg": pk["clearance_deg"],
               "study_distance_km": pk["distance_km"], "study_summit_m": pk["summit_dem_m"]}
        if len(near) == 0:
            row.update({"in_mesh": False, "ok": not pk["visible"],
                        "why": "hidden in the study; dropped by the bake" if not pk["visible"] else "VISIBLE in the study but not in the mesh"})
        else:
            dx = V[near, 0] - eye[0]; dz = V[near, 2] - eye[2]; hd = np.hypot(dx, dz)
            brg_all = np.degrees(np.arctan2(dx, dz)) % 360.0
            alt_all = np.degrees(np.arctan2(V[near, 1] - eye[1], hd))
            j = int(np.argmax(real[near]))
            brg = float(brg_all[j]); alt = float(alt_all[j])
            top = angdiff(brg_all[alt_all >= alt - FLAT_DEG], pk["bearing_deg"])          # the top's bearings, about the study's
            lo, hi = float(top.min()), float(top.max())
            db = 0.0 if lo <= 0.0 <= hi else (lo if lo > 0 else hi)
            da = alt - pk["altitude_deg"]
            within = abs(db) <= TOL_DEG and abs(da) <= TOL_DEG
            row.update({"in_mesh": True, "mesh_bearing_deg": round(brg, 3), "mesh_altitude_deg": round(alt, 3),
                        "mesh_top_bearing_span_deg": [round(pk["bearing_deg"] + lo, 3), round(pk["bearing_deg"] + hi, 3)],
                        "mesh_distance_km": round(float(hd[j]) / 1000, 2), "mesh_summit_m": round(float(real[near][j]), 1),
                        "d_summit_bearing_deg": round(float(angdiff(brg, pk["bearing_deg"])), 3),
                        "d_bearing_deg": round(db, 3), "d_altitude_deg": round(da, 3), "within": within,
                        "ok": within or not pk["visible"]})
            if not pk["visible"]:
                row["why"] = "hidden in the study: reported, not gated"
        rows.append(row)
    rows.sort(key=lambda r: r["study_bearing_deg"])

    sky = None
    ref = horizon.get("sites", {}).get(site)
    if ref and len(T):
        near_m = float(np.hypot(V[:, 0] - eye[0], V[:, 2] - eye[2]).min())
        mine = skyline(V, T, eye, [r[0] for r in ref], (arc[0] + arc[1]) / 2)
        diffs = [(r[0], m - r[1], r[2]) for r, m in zip(ref, mine) if m is not None and r[2] >= near_m]
        if diffs:
            worst = max(diffs, key=lambda q: abs(q[1]))
            sky = {"bearings_compared": len(diffs),
                   "bearings_skipped": len(ref) - len(diffs),
                   "skipped_because": f"the study's skyline there is formed nearer than the mesh's near edge ({near_m:.0f} m), or the mesh has nothing on that bearing",
                   "over_tolerance": sum(1 for q in diffs if abs(q[1]) > TOL_DEG),
                   "mean_diff_deg": round(sum(q[1] for q in diffs) / len(diffs), 4),
                   "worst": {"bearing_deg": worst[0], "diff_deg": round(worst[1], 3), "study_distance_m": worst[2]}}
    failed = [r["peak"] for r in rows if not r["ok"]]
    return {"gate": "backdrop_peak_gate", "tolerance_deg": TOL_DEG, "flat_top_deg": FLAT_DEG, "summit_box_half_deg": box, "eye_m": EYE_M, "site": site,
            "eye_local_xyz": [round(c, 3) for c in eye], "obj": Path(obj_path).name, "vertices": int(len(V)),
            "triangles": int(len(T)), "objects": len(names), "digit_prefixed_objects": digit,
            "peaks": rows, "failed": failed, "skyline_reported_not_gated": sky,
            "ok": not failed and not digit and len(V) > 0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("obj"); ap.add_argument("config"); ap.add_argument("track")
    ap.add_argument("--report", help="write the verdict here as JSON")
    a = ap.parse_args(argv)
    cfg_path = Path(a.config).resolve(); cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    t = cfg["tracks"][a.track]; root = cfg_path.parents[3]
    params = dict(DEFAULTS); params.update(cfg.get("params", {})); params.update(t.get("params", {}))
    g = t["gate"]
    horizon = json.loads((root / g["horizon"]).read_text(encoding="utf-8"))
    if t.get("origin_elev_m") is None:
        raise SystemExit("backdrop_peak_gate: the track's origin_elev_m must be written in the config (the gate reads no DEM)")
    res = gate(a.obj, horizon, g["site"], tuple(t["origin_lon_lat"]), float(t["origin_elev_m"]), tuple(g["start_line_lon_lat"]),
               params["refraction_k"], params["arc_deg"])
    res["horizon"] = g["horizon"]; res["track"] = a.track
    if a.report:
        Path(a.report).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"backdrop_peak_gate: {a.track}, from {g['site']}, {res['triangles']:,} triangles")
    print(f"{'peak':24s} {'study brg':>9s} {'mesh brg':>9s} {'d':>7s} {'d top':>7s}   {'study alt':>9s} {'mesh alt':>9s} {'d':>7s}   verdict")
    for r in res["peaks"]:
        if r["in_mesh"]:
            v = "ok" if r.get("within") else ("FAIL" if r["study_visible"] else "off (hidden: not gated)")
            if r.get("within") and not r["study_visible"]:
                v = "ok (hidden in the study)"
            print(f"{r['peak']:24s} {r['study_bearing_deg']:9.2f} {r['mesh_bearing_deg']:9.2f} {r['d_summit_bearing_deg']:+7.3f} {r['d_bearing_deg']:+7.3f}   "
                  f"{r['study_altitude_deg']:9.3f} {r['mesh_altitude_deg']:9.3f} {r['d_altitude_deg']:+7.3f}   {v}")
        else:
            print(f"{r['peak']:24s} {r['study_bearing_deg']:9.2f} {'-':>9s} {'':7s} {'':7s}   {r['study_altitude_deg']:9.3f} {'-':>9s} {'':7s}   "
                  f"{'ok: ' if r['ok'] else 'FAIL: '}{r['why']}")
    s = res["skyline_reported_not_gated"]
    if s:
        print(f"skyline (reported, not gated): {s['bearings_compared']} bearings, {s['over_tolerance']} over {TOL_DEG} deg, "
              f"mean {s['mean_diff_deg']:+.3f}, worst {s['worst']['diff_deg']:+.3f} at {s['worst']['bearing_deg']}")
    if res["digit_prefixed_objects"]:
        print("FAIL: digit-prefixed objects:", ", ".join(res["digit_prefixed_objects"][:5]))
    print("PASS" if res["ok"] else f"FAIL: {', '.join(res['failed']) or 'see above'}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
