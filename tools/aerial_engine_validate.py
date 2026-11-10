"""Validate the aerial reading stage (scripts/aerial/engine, ledger 0088) against tracks with measured truth.

    python tools/aerial_engine_validate.py high-plains --image <png> --truth <kerb_offsets_calibration.json> [--out <json>]
    python tools/aerial_engine_validate.py exotics     --run <stage out dir> [--out <json>]
    python tools/aerial_engine_validate.py pikes-peak  --run <stage out dir> --truth <route_from_maps.naip.json>
                                                       [--pieces <infield_pieces.naip.json>] [--out <json>]

high-plains  the stage's block reader (scripts/aerial/engine/kerbs.py) over the 20 colour-measured runs' eye spans on
             the same NAIP 2023 0.3 m crop, the gate line data/gate_centerline.json; residuals against the colour truth
             (as ledger 0081 round 3 computed them) and against tools/kerb_offsets.py's own read (the record's runs),
             plus how many truths the stage's candidate scan finds.
exotics      the stage's lap against the committed trace (data/centerline.geojson, 2026-10-28): centre-to-centre
             distance, width difference, lap length.
pikes-peak   the stage's road course and infield-only layout against f11baae3's (route_from_maps.naip.json): piece
             order, lap length, centre-to-centre distance; the infield road widths against infield_pieces.naip.json.
Nothing is built; every number is printed and written to --out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.aerial.engine import geom, kerbs  # noqa: E402
from scripts.aerial.engine.ortho import Ortho  # noqa: E402


def _opts(argv):
    o = {}
    while argv:
        k = argv.pop(0)
        o[k] = argv.pop(0) if argv and not argv[0].startswith("--") else True
    return o


def _stats(v):
    v = np.abs(np.asarray(v, float))
    return {"n": int(len(v)), "median": round(float(np.median(v)), 3), "p95": round(float(np.percentile(v, 95)), 3),
            "max": round(float(v.max()), 3)}


def high_plains(o):
    tdir = ROOT / "tracks" / "high-plains"
    local = json.loads((tdir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    origin = (float(local["origin"]["lon"]), float(local["origin"]["lat"]))
    ortho = Ortho.load(o["--image"], origin=origin)
    line = json.loads((tdir / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    P = np.array(line["points_xyz_m"], float)[:, [0, 2]]
    L = kerbs.Line(ortho, P, line["widths_m"])
    cal = json.loads(Path(o["--truth"]).read_text(encoding="utf-8"))
    rows = []
    res_t = {"in": [], "out": [], "s0": [], "s1": [], "width": []}
    res_r = {"in": [], "out": [], "s0": [], "s1": []}
    by_class = {}
    for k in cal["kerbs"]:
        t = k["reader"].get("truth")
        s0, s1 = k["s_eye"]
        side = 1 if k["side"] == "left" else -1
        m = kerbs.measure(L, side, float(s0), float(s1))
        row = {"side": k["side"], "s_eye": [s0, s1], "colour": k.get("colour"), "stage": m,
               "kerb_offsets_record": {kk: k[kk] for kk in ("in_m", "out_m", "s0", "s1")}, "truth": t}
        if m is not None:
            res_r["in"].append(m["in_m"] - k["in_m"])
            res_r["out"].append(m["out_m"] - k["out_m"])
            res_r["s0"].append(m["s0"] - k["s0"])
            res_r["s1"].append(m["s1"] - k["s1"])
            if t:
                d = {"in": m["in_m"] - t["in_m"], "out": m["out_m"] - t["out_m"], "s0": m["s0"] - t["s0"],
                     "s1": m["s1"] - t["s1"], "width": (m["out_m"] - m["in_m"]) - (t["out_m"] - t["in_m"])}
                row["residual_vs_truth"] = {kk: round(v, 3) for kk, v in d.items()}
                for kk, v in d.items():
                    res_t[kk].append(v)
                    by_class.setdefault(f"{kk}@{t.get('colour')}", []).append(v)
        rows.append(row)
        print(f"[hp] {k['side'][0].upper()} {s0:.0f}-{s1:.0f} {k.get('colour')}: stage {m and (m['in_m'], m['out_m'], m['s0'], m['s1'])}"
              f" | kerb_offsets {k['in_m']}, {k['out_m']} | truth {t and (t['in_m'], t['out_m'])}")
    # the candidate scan over both whole sides: which truths does it find (a candidate overlapping the eye span)?
    found = []
    for sgn, name in ((1, "left"), (-1, "right")):
        cands = kerbs.scan(L, sgn)
        for k in cal["kerbs"]:
            if k["side"] != name:
                continue
            s0, s1 = k["s_eye"]
            hit = [c for c in cands if c[1] >= s0 and c[0] <= s1]
            found.append({"side": name, "s_eye": [s0, s1], "candidates_overlapping": hit})
        print(f"[hp] scan {name}: {len(cands)} candidate runs, {sum(b - a for a, b in cands):.0f} m")
    out = {"track": "high-plains", "image": ortho.describe(),
           "truth": "tools/kerb_spans.py colour measure, 20 runs (kerb_offsets_calibration.json on claude/circuit-kerbs-lm)",
           "vs_truth": {k: _stats(v) for k, v in res_t.items() if v},
           "vs_truth_by_class": {k: _stats(v) for k, v in by_class.items()},
           "vs_kerb_offsets_record": {k: _stats(v) for k, v in res_r.items() if v},
           "ledger_0081_round3": {"in": {"median": 0.16, "p95": 0.34, "max": 0.48},
                                  "out": {"median": 0.17, "p95": 0.67, "max": 1.25}},
           "scan_recall": f"{sum(1 for f in found if f['candidates_overlapping'])} / {len(found)}",
           "scan": found, "runs": rows}
    for k, v in out["vs_truth"].items():
        print(f"[hp] |stage - truth| {k:6s}: median {v['median']:.2f}  p95 {v['p95']:.2f}  max {v['max']:.2f}  (n {v['n']})")
    for k, v in out["vs_kerb_offsets_record"].items():
        print(f"[hp] |stage - kerb_offsets| {k:3s}: median {v['median']:.3f}  max {v['max']:.3f}")
    print(f"[hp] scan finds {out['scan_recall']} truths")
    return out


def _lonlat_line(path):
    g = json.loads(Path(path).read_text(encoding="utf-8"))
    f = g["features"][0]
    return np.array(f["geometry"]["coordinates"], float), f["properties"]


def exotics(o):
    run = Path(o["--run"])
    rep = json.loads((run / "report.json").read_text(encoding="utf-8"))
    lay = rep["layouts"][0]["id"]
    ours, props = _lonlat_line(run / f"{lay}.centerline.geojson")
    ref, rprops = _lonlat_line(ROOT / "tracks" / "exotics-racing-lv" / "data" / "centerline.geojson")
    lat0 = float(ref[:, 1].mean())
    from scripts.aerial.engine.ortho import mpd
    mlon, mlat = mpd(lat0)
    A = np.c_[(ours[:, 0] - ref[0, 0]) * mlon, (ours[:, 1] - ref[0, 1]) * mlat]
    B = np.c_[(ref[:, 0] - ref[0, 0]) * mlon, (ref[:, 1] - ref[0, 1]) * mlat]
    Ad = geom.resample(A[:-1] if np.allclose(A[0], A[-1]) else A, 0.5, closed=True)
    Bd = geom.resample(B[:-1] if np.allclose(B[0], B[-1]) else B, 0.5, closed=True)
    d_ab = cKDTree(Bd).query(Ad)[0]
    d_ba = cKDTree(Ad).query(Bd)[0]
    wa = np.array(props["widths_m"], float)
    wb = np.array(rprops["widths_m"], float)
    # widths compared at matched positions: each of our vertices takes the nearest reference vertex's width
    _, j = cKDTree(B).query(A)
    dw = wa - wb[j]
    out = {"track": "exotics-racing-lv", "stage_run": str(run), "layout": lay,
           "reference": "tracks/exotics-racing-lv/data/centerline.geojson (2026-10-28 trace: hand seeds + refine_trace.py)",
           "lap_m": {"stage": round(geom.closed_len(Ad), 1), "trace": round(geom.closed_len(Bd), 1)},
           "centre_to_centre_m": {"stage_to_trace": geom.pct(d_ab, 2), "trace_to_stage": geom.pct(d_ba, 2)},
           "width_minus_trace_m": {"median": round(float(np.median(dw)), 2), "abs": geom.pct(dw, 2)},
           "trace_width_note": "the trace's widths are floored 11.5 m, capped 20 m and smoothed 11 stations (README)"}
    print(json.dumps(out, indent=1))
    return out


def pikes_peak(o):
    run = Path(o["--run"])
    rep = json.loads((run / "report.json").read_text(encoding="utf-8"))
    truth = json.loads(Path(o["--truth"]).read_text(encoding="utf-8"))
    out = {"track": "pikes-peak", "stage_run": str(run),
           "reference": "route_from_maps.naip.json at f11baae3 (origin/claude/pikes-peak-road-course, ledger 0085)",
           "layouts": {}}
    pairs = json.loads(o.get("--pairs", '{"rcd": "RC-D", "ifk": "IF-K"}'))
    for lid, tid in pairs.items():
        lay = next((x for x in rep["layouts"] if x["id"] == lid), None)
        if lay is None or tid not in truth["routes"]:
            continue
        T = np.array(truth["routes"][tid]["centre_en_m"], float)
        A = np.array(json.loads((run / f"{lid}.layout.json").read_text(encoding="utf-8"))["centre_en_m"], float)
        Ad, Td = geom.resample(A, 0.5, closed=True), geom.resample(T, 0.5, closed=True)
        d_at = cKDTree(Td).query(Ad)[0]
        d_ta = cKDTree(Ad).query(Td)[0]
        tr = truth["routes"][tid]
        out["layouts"][lid] = {
            "vs": tid, "lap_m": {"stage": lay["lap_m"], "f11baae3": tr["lap_m"], "difference": round(lay["lap_m"] - tr["lap_m"], 1),
                                 "f11baae3_uncertainty_m": tr.get("uncertainty_m")},
            "centre_to_centre_m": {"stage_to_f11baae3": geom.pct(d_at, 2), "f11baae3_to_stage": geom.pct(d_ta, 2)},
            "over_3m_m": round(float((d_at > 3).sum() * 0.5), 1)}
    if "--pieces" in o:
        # per f11baae3 road piece: the stage's measured widths where a stage layout runs down it (within 2 m of its
        # centre line), against f11baae3's width per metre there
        pcs = json.loads(Path(o["--pieces"]).read_text(encoding="utf-8"))["pieces"]
        Cs, Ws = [], []
        for lay in rep["layouts"]:
            body = json.loads((run / f"{lay['id']}.layout.json").read_text(encoding="utf-8"))
            Cs.append(np.array(body["centre_en_m"], float))
            Ws.append(np.array(body["width_m_per_metre"], float))
        C, Wd = np.vstack(Cs), np.concatenate(Ws)
        tree = cKDTree(C)
        rows = []
        for name, q in pcs.items():
            if not q.get("centre_en_m") or q.get("kind") == "ring":
                continue
            Q = np.array(q["centre_en_m"], float)
            qw = np.array([np.nan if w is None else w for w in q["width_m_per_metre"]], float)
            d, j = tree.query(Q)
            on = (d < 2.0) & np.isfinite(qw)
            if on.sum() < 10:
                rows.append({"f11baae3_piece": name, "on_a_stage_layout_m": int(on.sum())})
                continue
            dw = Wd[j[on]] - qw[on]
            rows.append({"f11baae3_piece": name, "on_a_stage_layout_m": int(on.sum()),
                         "f11baae3_width_p50_m": round(float(np.median(qw[on])), 2),
                         "stage_minus_f11baae3_m": {"median": round(float(np.median(dw)), 2), "abs": geom.pct(dw, 2)}})
        out["piece_widths"] = rows
    print(json.dumps(out, indent=1))
    return out


def exotics_sketch(o):
    """A stand-in for a hand sketch, made from the committed trace and degraded so it cannot carry geometry: one vertex
    every --every m (default 30), each moved by a seeded uniform +-(--jitter) m (default 3) in E and N, as strokes in
    the sketch page's format over naip_2019_exr.png's corners. Exotics has no published map on disk and no sketch from
    Kevin; this tests that the measured lap does not depend on where the guide's points were put."""
    every = float(o.get("--every", 30))
    jit = float(o.get("--jitter", 3))
    cfg = json.loads((ROOT / "tracks" / "exotics-racing-lv" / "track.config.json").read_text(encoding="utf-8"))
    cps = cfg["source"]["control_points"]
    (x0, y0), (lw, ln_) = cps[0]["px"], cps[0]["lonlat"]
    (x1, y1), (le, ls) = cps[1]["px"], cps[1]["lonlat"]
    W_, H_ = int(x1 - x0), int(y1 - y0)
    ll, _ = _lonlat_line(ROOT / "tracks" / "exotics-racing-lv" / "data" / "centerline.geojson")
    from scripts.aerial.engine.ortho import mpd
    mlon, mlat = mpd(float(ll[:, 1].mean()))
    E = np.c_[(ll[:, 0] - lw) * mlon, (ll[:, 1] - ln_) * mlat]
    if np.allclose(E[0], E[-1]):
        E = E[:-1]
    Q = geom.resample(E, every, closed=True)
    rng = np.random.default_rng(int(o.get("--seed", 88)))
    Q = Q + rng.uniform(-jit, jit, Q.shape)
    lon, lat = lw + Q[:, 0] / mlon, ln_ + Q[:, 1] / mlat
    px = (lon - lw) / (le - lw) * W_ - 0.5
    py = (ln_ - lat) / (ln_ - ls) * H_ - 0.5
    doc = {"_doc": exotics_sketch.__doc__.strip(), "coords": "aerial pixel centres, x right, y down; stroke order = "
           "the order drawn (direction is NOT read from it)", "corners_wnes": [lw, ln_, le, ls], "image_w": W_, "image_h": H_,
           "image": "naip_2019_exr.png", "every_m": every, "jitter_m": jit,
           "strokes": [{"pts": [round(float(v), 1) for xy in zip(px, py) for v in xy]}]}
    Path(o["--out"]).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"[exotics-sketch] {len(Q)} vertices every {every} m, +-{jit} m -> {o['--out']}")
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    which = argv.pop(0)
    o = _opts(argv)
    if which == "exotics-sketch":
        return exotics_sketch(o)
    res = {"high-plains": high_plains, "exotics": exotics, "pikes-peak": pikes_peak}[which](o)
    if "--out" in o:
        Path(o["--out"]).write_text(json.dumps(res, indent=1, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)),
                                    encoding="utf-8")
        print(f"-> {o['--out']}")


if __name__ == "__main__":
    main()
