"""The pit-exit lane's paved edges, measured off NAIP 2023 at 0.3 m (ledger 0093 "Not fixed: the pit exit's merge past the
paddock sheet is built as terrain. Paving it needs its edges measured off the 0.3 m photo"; ledger 0097 round 2).

    python -I measure_pit_exit.py <repo>      (numpy + Pillow; writes pit_exit_strip.json beside itself)

The pit-exit lane leaves the paddock past the pit-out gore, runs outside T1-T2 between K-rails, then beside the lap behind a
grass strip, and merges at T2's exit (the photo: the merge at s ~452 of data/gate_centerline.json). Every STEP_M from S0 to S1
along the built line, the crop (source/road_wear/naip_2023_030_hp.png) is read on the LEFT every 0.1 m from 3 m to 40 m and
classed as in measure_widths.py: asphalt (ground-ness max((R + G) / 2 - B, 2G - R - B - 5) under ASPH_G, not paint,
mean under 150), paint (white: mean >= 150 and B >= 0.8 R; blue: B - (R + G) / 2 >= 12), ground (the rest). The lap's own
paving is the first asphalt run (ground gaps <= GAP_M bridged); the LANE is the next asphalt run at least LANE_MIN_M long
after GRASS_MIN_M of anything else; its edges are that run's ends (its paint is the K-rails' and edge lines', kept out).
Where no such gap is left the lane has merged: the strip ends there, its last pair the lap's own left edge (measure_widths'
reading) and the joined run's end.
Each edge is a 3-station median along s. The strip starts at the first pair both outside the paddock sheet
(scenery.bespoke.pads "paddock", its quad), so the two PADAPRON sheets never lie one over the other. Every UPPER-CASE number
is [invented] tuning of the colour reader (ledger 0097 round 2); the photo is the measurement.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

S0, S1, STEP_M = 180.0, 470.0, 5.0
ASPH_G = 22.0
GAP_M = 0.3
GRASS_MIN_M = 1.0
LANE_MIN_M = 2.5
OFF0, OFF1, DO = 3.0, 40.0, 0.1


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def runs_of(mask):
    out, j = [], 0
    n = len(mask)
    while j < n:
        if mask[j]:
            k = j
            while k + 1 < n and mask[k + 1]:
                k += 1
            out.append((j, k))
            j = k + 1
        else:
            j += 1
    return out


def bridge(mask, gap):
    m = mask.copy()
    r = runs_of(mask)
    for (a0, a1), (b0, b1) in zip(r, r[1:]):
        if b0 - a1 - 1 <= gap:
            m[a1 + 1:b0] = True
    return m


def in_quad(q, x, z):
    c = False
    for i in range(len(q)):
        x1, z1 = q[i]; x2, z2 = q[(i + 1) % len(q)]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            c = not c
    return c


def measure(repo: Path):
    T = repo / "tracks" / "high-plains-lm"
    cfg = json.loads((T / "track.config.json").read_text(encoding="utf-8"))
    gc = json.loads((T / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    o = json.loads((T / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    meta = json.loads((T / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    A = np.asarray(Image.open(T / "source" / "road_wear" / "naip_2023_030_hp.png").convert("RGB")).astype(np.float32)
    Wc, Nc, Ec, Sc = meta["corners"]
    h, w, _ = A.shape
    mlon, mlat = mpd(o["lat"])

    def rgb(x, z):
        lon = o["lon"] + x / mlon; lat = o["lat"] + z / mlat
        px = (lon - Wc) / (Ec - Wc) * w - 0.5; py = (Nc - lat) / (Nc - Sc) * h - 0.5
        x0 = np.clip(np.floor(px).astype(int), 0, w - 2); y0 = np.clip(np.floor(py).astype(int), 0, h - 2)
        tx = (px - x0)[..., None]; ty = (py - y0)[..., None]
        return (A[y0, x0] * (1 - tx) + A[y0, x0 + 1] * tx) * (1 - ty) + (A[y0 + 1, x0] * (1 - tx) + A[y0 + 1, x0 + 1] * tx) * ty
    P = np.array([[p[0], p[2]] for p in gc["points_xyz_m"]])
    st = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = np.arange(S0, S1 + 1e-9, STEP_M)
    x = np.interp(s, st, P[:, 0]); z = np.interp(s, st, P[:, 1])
    tx = np.gradient(x); tz = np.gradient(z); L = np.hypot(tx, tz); tx /= L; tz /= L
    offs = np.arange(OFF0, OFF1 + 1e-9, DO)
    gap = int(round(GAP_M / DO)); gmin = int(round(GRASS_MIN_M / DO)); lmin = int(round(LANE_MIN_M / DO))
    rows = []
    for i in range(len(s)):
        V = rgb(x[i] + (-tz[i]) * offs, z[i] + tx[i] * offs)
        R, G, B = V[:, 0], V[:, 1], V[:, 2]
        mean = V.mean(1)
        g = np.maximum((R + G) / 2 - B, 2 * G - R - B - 5)
        paint = ((mean >= 150) & (B >= 0.8 * R)) | (B - (R + G) / 2 >= 12)
        asph = bridge((g < ASPH_G) & ~paint & (mean < 150), gap)
        rr = runs_of(asph)
        if not rr or rr[0][0] > 5:
            rows.append(None); continue
        lap_end = rr[0][1]
        lane = None
        for a, b in rr[1:]:
            if a - lap_end - 1 >= gmin and b - a + 1 >= lmin:
                lane = (a, b); break
        if lane is None:
            rows.append({"s": float(s[i]), "merged": True, "lap_edge": float(offs[lap_end] + DO / 2)})
            continue
        rows.append({"s": float(s[i]), "merged": False, "lap_edge": float(offs[lap_end] + DO / 2),
                     "inner": float(offs[lane[0]] - DO / 2), "outer": float(offs[lane[1]] + DO / 2)})
    # the lane's rows up to the first merge after it was seen
    seen, keep = False, []
    for r in rows:
        if r is None:
            continue
        if not r["merged"]:
            seen = True; keep.append(r)
        elif seen:
            keep.append(r); break
    ks = np.array([r["s"] for r in keep])
    inn = np.array([r.get("inner", np.nan) for r in keep]); out = np.array([r.get("outer", np.nan) for r in keep])
    med = lambda a: np.array([np.nanmedian(a[max(0, k - 1):k + 2]) for k in range(len(a))])
    inn_m, out_m = med(inn), med(out)
    if keep and keep[-1]["merged"]:
        # the merge: the lane's paving now runs on from the lap's: the pair is the lap's own left edge there (measure_widths'
        # reading, widths_measured.json) and the joined run's end
        wm = json.loads((T / "source" / "edges" / "widths_measured.json").read_text(encoding="utf-8"))
        near = [r_ for r_ in wm["rows"] if abs(r_["s"] - keep[-1]["s"]) <= 3.0 and r_["left_m"] is not None]
        inn_m[-1] = float(np.median([r_["left_m"] for r_ in near])) if near else keep[-1]["lap_edge"]
        out_m[-1] = keep[-1]["lap_edge"]
    pad = next(p for p in cfg["scenery"]["bespoke"]["pads"] if p["key"] == "paddock")
    quad = [((lo - o["lon"]) * mlon, (la - o["lat"]) * mlat) for lo, la in pad["quad_lonlat"]]
    strip = {"inner": [], "outer": []}
    rec = []
    for k, sv in enumerate(ks):
        xi, zi = np.interp(sv, st, P[:, 0]), np.interp(sv, st, P[:, 1])
        j = int(np.argmin(np.abs(s - sv)))
        nx, nz = -tz[j], tx[j]
        a = (xi + nx * inn_m[k], zi + nz * inn_m[k]); b = (xi + nx * out_m[k], zi + nz * out_m[k])
        if not strip["inner"] and (in_quad(quad, *a) or in_quad(quad, *b)):
            continue
        ll = lambda q: [round(o["lon"] + q[0] / mlon, 8), round(o["lat"] + q[1] / mlat, 8)]
        strip["inner"].append(ll(a)); strip["outer"].append(ll(b))
        rec.append({"s": float(sv), "inner_m": round(float(inn_m[k]), 2), "outer_m": round(float(out_m[k]), 2),
                    "width_m": round(float(out_m[k] - inn_m[k]), 2), "merged": keep[k]["merged"]})
    return strip, rec


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    strip, rec = measure(repo)
    out = {"_doc": "ledger 0097 round 2: the pit-exit lane's paved edges off NAIP 2023 0.3 m (measure_pit_exit.py), "
                   "track.config.json scenery.bespoke.pads 'pit_exit'; offsets from data/gate_centerline.json, + = left",
           "rows": rec, "strip_lonlat": strip}
    (Path(__file__).resolve().parent / "pit_exit_strip.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    w = [r["width_m"] for r in rec if not r["merged"]]
    print(f"[pit_exit] {len(rec)} pairs, s {rec[0]['s']:.0f}-{rec[-1]['s']:.0f}; lane width p5/50/95 "
          f"{np.percentile(w, 5):.2f} / {np.median(w):.2f} / {np.percentile(w, 95):.2f} m; merged at s {rec[-1]['s']:.0f}"
          f" ({rec[-1]['merged']})")
    for r in rec:
        print(r)
