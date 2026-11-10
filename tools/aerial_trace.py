"""THE ROAD THE AERIAL SHOWS, WHERE THE LINE IS LEVEL BUT OFF IT: a NAIP road-edge trace for the stage ports (ledger 0078
round 13).

tools/road_seek.py moves a mapped line onto the graded road only where the line's own DEM profile is not a road (a grade
over 20 % over 10 m). A line that sits level beside its road (across scrub, cutting a bend's inside) reads as a road in the
DEM and is left where it is; round 10's DEM-only trigger for that case either missed it or fired over kilometres of correct
road (a graded road's crown and ditches read rougher than a strip of level scrub beside it). The evidence for that case is
in the aerial: a graded gravel road is an EVEN band of road width in NAIP (one tone across, distinct from the ground on
both sides of it), and scrub is not (shrubs, soil, shadow).

At every station of the source line, on road_seek's line (its offset_m), NAIP is read across the line (road_seek's cached
tiles) and the most even band of road width within SEEK_HALF_M is found: every centre u every STEP_M and every width w in
BAND_W_M, scored
    score(u, w) = min(|band mean - left shoulder mean|, |band mean - right shoulder mean|) / (band sd + NOISE_GREY)
(the shoulders SHOULDER_M wide either side). A station is a candidate where all of these hold:
    * the best band is a road: score >= ROAD_E;
    * the line is OFF that band entirely: |u - line| >= w / 2 + OFF_MIN_M;
    * the line's own band (road_seek's half width either side) is uneven in NAIP: its sd >= LINE_SD_GREY;
    * the line crosses uneven ground: the 1 m DEM's departure from a straight cross-section over the line's band is
      ROUGH_M or more AND more than over the road band.
A run of candidates (carried over GAP_STATIONS misses at most) whose road centre moves no more than MAX_SHIFT_M a station,
RUN_MIN_M long or more, is a place the trace would act. Every run is reported (the short ones too) with the road's centre and
the DEM's straight-fit height there. Nothing is applied by this tool, and nothing reads its record yet: a run is moved onto
its road only after it is drawn on the aerial and judged clear (round 13 drew every one on both stages and kept none: each
is the line riding the edge of a road wider than its lane, a 30-65 m piece of a longer offset, not a line off its road;
ledger 0078 round 13).

    python tools/aerial_trace.py <port-track-dir> --cache <road_seek tile dir> [--out data/aerial_trace.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

SEEK_HALF_M = 15.0       # the coordinator's (round 13): the road sought within 15 m of the line
STEP_M = 0.5
SHOULDER_M = 4.0         # road_seek's
BAND_W_M = (5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0)   # [invented] the band widths tried (the stages' 6.5 m road to a platform)
NOISE_GREY = 5.0         # [invented] grey levels: the band sd's floor (NAIP's own noise on an even surface)
ROAD_E = 3.0             # [invented] an even band: its contrast with EACH shoulder 3x its own spread
OFF_MIN_M = 1.0          # [invented] the line off the road band entirely, by this much past its edge
LINE_SD_GREY = 15.0      # [invented] the line's own band is uneven in NAIP (scrub, soil, shadow): its sd this or more
ROUGH_M = 0.05           # road_seek's: a graded road's departure from a straight DEM cross-section
RUN_MIN_M = 30.0         # [invented] a run of candidates this long
MAX_SHIFT_M = 1.5        # road_seek's: the most the centre moves between neighbouring stations
GAP_STATIONS = 2         # [invented] a run carries on over this many stations in a row that miss one test (a shrub's
                         # shadow on the road, a level patch of scrub)


def _cs(v):
    import numpy as np
    return np.concatenate([[0.0], np.cumsum(v)])


def best_band(t, g, c, widths):
    """the most even band of road width within SEEK_HALF_M of c: (score, u, w)"""
    import numpy as np
    G, G2 = _cs(g), _cs(g * g)

    def mean_sd(lo, hi):
        n = np.maximum(hi - lo, 1)
        m = (G[hi] - G[lo]) / n
        return m, np.sqrt(np.maximum((G2[hi] - G2[lo]) / n - m * m, 0.0))
    us = np.arange(c - SEEK_HALF_M, c + SEEK_HALF_M + 1e-9, STEP_M)
    best = (0.0, c, widths[0])
    sh = int(round(SHOULDER_M / STEP_M))
    for w in widths:
        h = w / 2.0
        lo = np.searchsorted(t, us - h - 1e-9)
        hi = np.searchsorted(t, us + h + 1e-9)
        ok = (lo - sh >= 0) & (hi + sh <= len(t))
        lo, hi = np.clip(lo, sh, len(t) - sh), np.clip(hi, sh, len(t) - sh)
        bm, bsd = mean_sd(lo, hi)
        lm, _ = mean_sd(lo - sh, lo)
        rm, _ = mean_sd(hi, hi + sh)
        sc = np.where(ok, np.minimum(np.abs(bm - lm), np.abs(bm - rm)) / (bsd + NOISE_GREY), 0.0)
        k = int(np.argmax(sc))
        if sc[k] > best[0]:
            best = (float(sc[k]), float(us[k]), float(w))
    return best


def dem_fit(t, d, u, half):
    import numpy as np
    import road_seek as rs
    m = (t >= u - half) & (t <= u + half) & np.isfinite(d)
    if m.sum() < 3:
        return None
    return rs._fit(list(t[m]), list(d[m]))


def trace(P, W, stations, R):
    import numpy as np
    n = len(P)
    reach = SEEK_HALF_M + max(BAND_W_M) / 2.0 + SHOULDER_M + 1.0
    rows = []
    for i in range(n):
        a, b = P[max(i - 1, 0)], P[min(i + 1, n - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        c = float(stations[i]["offset_m"])
        t = np.arange(c - reach, c + reach + 1e-9, STEP_M)
        sec = [R.at(P[i][0] + nx * q, P[i][2] + nz * q) for q in t]
        d = np.array([np.nan if v[0] is None else v[0] for v in sec])
        g = np.array([np.nan if v[1] is None else v[1] for v in sec])
        if not np.isfinite(g).all():
            rows.append(None)
            continue
        half = max(W[i] / 2.0 - 0.25, 1.5)
        score, u, w = best_band(t, g, c, BAND_W_M)
        m = (t >= c - half) & (t <= c + half)
        fl = dem_fit(t, d, c, half)
        fu = dem_fit(t, d, u, w / 2.0)
        rows.append({"i": i, "c": c, "u": u, "w": w, "score": score, "line_sd": float(g[m].std()),
                     "rms_line": None if fl is None else fl[2], "rms_u": None if fu is None else fu[2],
                     "z_u": None if fu is None else fu[0] + fu[1] * u})
    return rows


def candidates(rows):
    out = []
    for r in rows:
        if r is None:
            out.append(False)
            continue
        out.append(r["score"] >= ROAD_E and abs(r["u"] - r["c"]) >= r["w"] / 2.0 + OFF_MIN_M
                   and r["line_sd"] >= LINE_SD_GREY
                   and r["rms_line"] is not None and r["rms_u"] is not None
                   and r["rms_line"] >= ROUGH_M and r["rms_line"] > r["rms_u"])
    return out


def runs(P, rows, cand):
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    out = []
    i, n = 0, len(rows)
    while i < n:
        if not cand[i]:
            i += 1
            continue
        j = i
        while True:                      # the next candidate within GAP_STATIONS + 1, its road continuing this one's
            nxt = next((q for q in range(j + 1, min(n, j + GAP_STATIONS + 2)) if cand[q]), None)
            if nxt is None or abs(rows[nxt]["u"] - rows[j]["u"]) > MAX_SHIFT_M * (nxt - j):
                break
            j = nxt
        k_ = [k for k in range(i, j + 1) if cand[k]]
        m_ = len(k_) // 2
        out.append({"i": [i, j], "s_m": [round(st[i], 1), round(st[j], 1)], "length_m": round(st[j] - st[i], 1),
                    "stations": k_,
                    "off_m": round(max((rows[k]["u"] - rows[k]["c"] for k in k_), key=abs), 2),
                    "road_w_m": sorted(rows[k]["w"] for k in k_)[m_],
                    "score_median": round(sorted(rows[k]["score"] for k in k_)[m_], 2),
                    "line_sd_median": round(sorted(rows[k]["line_sd"] for k in k_)[m_], 1),
                    "acts": st[j] - st[i] >= RUN_MIN_M})
        i = j + 1
    return out, st


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", default="data/aerial_trace.json")
    a = ap.parse_args(argv)
    import numpy as np
    import road_seek as rs
    port = Path(a.port)
    cfg = json.loads((port / "track.config.json").read_text(encoding="utf-8"))
    src = AIROSO / "tracks" / cfg["lm_intake"]["source_track"]
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    P = [tuple(p) for p in local["points_xyz_m"]]
    W = local.get("widths_m") or [6.5] * len(P)
    stations = json.loads((port / "data" / "road_seek.json").read_text(encoding="utf-8"))["stations"]
    keys = rs.tiles_for(P, SEEK_HALF_M + max(BAND_W_M) / 2.0 + SHOULDER_M + 2.0
                        + max(abs(s["offset_m"]) for s in stations))
    cache = Path(a.cache)
    tiles = {}
    for k in keys:
        f = cache / f"t_{k[0]}_{k[1]}.npz"
        if f.exists():
            d = np.load(f)
            tiles[k] = (d["dem"], d["img"])
    print(f"[aerial_trace] {len(tiles)} of {len(keys)} tiles cached in {cache}", flush=True)
    rows = trace(P, W, stations, rs.Raster(tiles))
    cand = candidates(rows)
    rr, st = runs(P, rows, cand)
    rec = {
        "_doc": "tools/aerial_trace.py (ledger 0078 round 13): every place on the source line where NAIP shows an even band "
                "of road width within 15 m and road_seek's line is off it, on a band that is uneven in NAIP and over uneven "
                "ground in the DEM. runs[].acts = long enough to act on; nothing reads this record (round 13 drew every "
                "acting run and kept none: ledger 0078)",
        "source_track": cfg["lm_intake"]["source_track"],
        "params": {k: globals()[k] for k in ("SEEK_HALF_M", "STEP_M", "SHOULDER_M", "BAND_W_M", "NOISE_GREY", "ROAD_E",
                                             "OFF_MIN_M", "LINE_SD_GREY", "ROUGH_M", "RUN_MIN_M", "MAX_SHIFT_M",
                                             "GAP_STATIONS")},
        "stations": len(rows), "candidate_stations": int(sum(cand)),
        "runs": [dict(id=f"A{k + 1}", **r) for k, r in enumerate(rr)],
        "acted": [],
    }
    for r in rec["runs"]:
        if not r["acts"]:
            continue
        i0, i1 = r["i"]
        rec["acted"].append({"id": r["id"], "stations": {str(k): {"offset_m": round(rows[k]["u"], 2),
                                                                   "z_m": round(rows[k]["z_u"], 3)}
                                                          for k in r["stations"]}})
    out = port / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"[aerial_trace] {len(rows)} stations, {rec['candidate_stations']} candidate stations in {len(rr)} run(s); "
          f"{sum(1 for r in rr if r['acts'])} long enough to act (>= {RUN_MIN_M:.0f} m) -> {out}")
    for r in rec["runs"]:
        print(f"[aerial_trace]   {r['id']}: source s {r['s_m'][0]:,.0f}-{r['s_m'][1]:,.0f} ({r['length_m']} m), road "
              f"{r['off_m']:+.1f} m off the line ({r['road_w_m']:.0f} m band, score {r['score_median']}; the line's NAIP "
              f"sd {r['line_sd_median']})" + ("  ACTS" if r["acts"] else ""))


if __name__ == "__main__":
    main()
