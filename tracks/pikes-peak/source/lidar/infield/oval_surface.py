"""The oval's measured racing surface for the intake (lm_intake.edge_on_bank): where the bank plane really ends on the
inside, the plane's own height, and the apron beyond it — per 3 m station of the 0.1.0 built line.

    python oval_surface.py <inside_slope.json> <out oval_surface.json>

From inside_slope.py's rows (its knee fit: the bank plane over -6.5 m .. the knee, the apron beyond, 1-3 cm residual):
  - bank_edge_m: the knee's lateral offset from the BUILT centre (built half-width + knee past the built edge), median
    over SMOOTH_K stations then a mean over SMOOTH_K (the wall survey's own smoothing, lm_intake.edge_on_wall): one
    station's knee off by a few m (s 900: -1.75) is dropped, a 15 m roll of the edge kept;
  - plane: z = a + b * lateral (build-y metres, lateral + = left / inside, from the station's built centre), the lane
    fit over +-6.5 m; a mean over 3 stations (the fit's own noise ~2 mm);
  - apron: its slope (the knee fit's outer segment), its width to the measured inside edge (inside_edge.naip.json) and
    lip_step_m, the ground 1 m past that edge above the apron there (a swale: the infield stands 5-20 cm over the
    apron's low edge), the same smoothing; the intake hands them to the assembler's edge strip (edge_on_bank.apron).
Positions are the built line's (ENU, x = E, z = N), so the intake keys each of its own vertices to the nearest station.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SMOOTH_K = 5        # stations (15 m), lm_intake.edge_on_wall's SMOOTH_WALL
WEAK_KNEE_PCT = 1.75  # [invented] a knee whose two slopes differ by less is no reading (the back stretch s 885-906:
                      # -5.4 vs -4.0 %, its knee wandering -1.75..+2.25 m; carrying the plane 3 m on is 4 cm at that change)
PLANE_K = 3         # [invented] stations for the plane's own mean


def cyc_filter(v, k, f):
    n = len(v); h = k // 2
    return np.array([f(np.take(v, range(i - h, i + h + 1), mode="wrap")) for i in range(n)])


def fill(v):
    """Gaps filled linearly between the readings either side (cyclic: the lap is closed)."""
    v = np.array(v, float); n = len(v)
    ok = np.isfinite(v)
    if not ok.any():
        raise SystemExit("[oval_surface] no reading at any station")
    idx = np.arange(n); good = idx[ok]
    xp = np.r_[good - n, good, good + n]; fp = np.r_[v[good], v[good], v[good]]
    v[~ok] = np.interp(idx[~ok], xp, fp)
    return v


def main(src, out):
    d = json.loads(Path(src).read_text(encoding="utf-8"))
    R = d["rows"]
    hw = np.array([r["half_w_m"] for r in R])
    strong = ["knee" in r and abs(r["knee"]["slope_in_pct"] - r["knee"]["slope_out_pct"]) >= WEAK_KNEE_PCT for r in R]
    knee = fill([r["knee"]["from_built_edge_m"] if ok else np.nan for r, ok in zip(R, strong)])
    sout = fill([r["knee"]["slope_out_pct"] if "knee" in r else np.nan for r in R])
    edge = fill([r["edge_m"] if r.get("edge_m") is not None else np.nan for r in R])
    lip = fill([r["beyond"]["lip_step_m"] if "lip_step_m" in r.get("beyond", {}) else np.nan for r in R])
    Ls = cyc_filter(cyc_filter(lip, SMOOTH_K, np.median), SMOOTH_K, np.mean)
    a = fill([r["lane"]["a"] if "lane" in r else np.nan for r in R])
    b = fill([r["lane"]["b"] if "lane" in r else np.nan for r in R])
    K = hw + knee
    Ks = cyc_filter(cyc_filter(K, SMOOTH_K, np.median), SMOOTH_K, np.mean)
    So = cyc_filter(cyc_filter(sout, SMOOTH_K, np.median), SMOOTH_K, np.mean)
    As = cyc_filter(a, PLANE_K, np.mean); Bs = cyc_filter(b, PLANE_K, np.mean)
    st = []
    for i, r in enumerate(R):
        st.append({"s": r["s"], "xz": r["xz"], "left": r["left"], "built_half_w_m": r["half_w_m"],
                   "bank_edge_m": round(float(Ks[i]), 3), "bank_edge_raw_m": round(float(K[i]), 3),
                   "knee_read": bool(strong[i]),
                   "plane": {"a": round(float(As[i]), 4), "b": round(float(Bs[i]), 5)},
                   "apron": {"slope_pct": round(float(So[i]), 2), "width_m": round(float(edge[i] - Ks[i]), 2),
                             "lip_step_m": round(float(Ls[i]), 3),
                             "edge_label": r.get("edge_label")}})
    past = Ks - hw
    res = {"_doc": __doc__.strip().splitlines()[0], "source": str(src).replace("\\", "/"),
           "line": d.get("workshop"), "lap_m": d.get("lap_m"), "stations": st,
           "summary": {"bank_edge_past_built_edge_m": {"min": round(float(past.min()), 2), "p50": round(float(np.median(past)), 2),
                                                       "max": round(float(past.max()), 2)},
                       "surface_width_m_from_built_right_edge": {"min": round(float((hw + Ks).min()), 2),
                                                                 "p50": round(float(np.median(hw + Ks)), 2),
                                                                 "max": round(float((hw + Ks).max()), 2)},
                       "raw_minus_smoothed_m": {"p95_abs": round(float(np.percentile(np.abs(K - Ks), 95)), 2),
                                                "max_abs": round(float(np.abs(K - Ks).max()), 2)},
                       "apron_slope_pct_p50": round(float(np.median(So)), 2),
                       "lip_step_m": {"p10": round(float(np.percentile(Ls, 10)), 3), "p50": round(float(np.median(Ls)), 3),
                                      "p90": round(float(np.percentile(Ls, 90)), 3)},
                       "apron_width_m": {"p10": round(float(np.percentile(edge - Ks, 10)), 2),
                                         "p50": round(float(np.median(edge - Ks)), 2)}},
           "params": {"SMOOTH_K": SMOOTH_K, "PLANE_K": PLANE_K, "WEAK_KNEE_PCT": WEAK_KNEE_PCT},
           "weak_knees_filled": int(len(R) - sum(strong))}
    Path(out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
