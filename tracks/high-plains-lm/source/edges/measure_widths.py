"""The real pavement edge beside High Plains' lap, measured off NAIP 2023 at 0.3 m (ledger 0097 round 2).

Kevin, 2026-11-22: "Rebuild at the measured widths" (the 12.0 m was INHERITED FROM THE FABRICATED CONFIG; ledger 0059 read
10.5 +/- 0.6 m between the edge lines' centres on NAIP 2019 at 0.6 m, 11.7-12.0 m on the front straight).

    python -I measure_widths.py <repo>      (numpy + Pillow; writes beside itself)

Every 1 m along the built line (data/gate_centerline.json: the assembler's smoothed line, its frame = the line's origin,
data/centerline.raw.local.json) and on both sides, the 0.3 m crop (source/road_wear/naip_2023_030_hp.png, corners in its
.json, EPSG:4326, bilinear) is read every 0.1 m from START_M to MAX_M off the line:
  ground-ness  g = max((R + G) / 2 - B, (2G - R - B) - 5): the dry prairie and graded dirt are yellow (B well under R and
               G: 35-55), the green draws are green (excess green 35+); the asphalt, the white edge lines and the kerbs' blue
               are neither (asphalt 15-21 here, measured: p50 8 / p95 15 of the lap's centre +-2 m, warmer at the edges)
  the edge     the FIRST outward offset where the mean g over the next 0.2-1.0 m exceeds the mean over the last 1.0-0.2 m by
               C_MIN and the outer mean is ground (>= OUT_MIN), moved to the strongest such step within 0.6 m past it: the
               outer side of the white edge line (it lowers g just inside the step) or the asphalt's end
  kerb runs    inside one of ledger 0081's 20 measured runs (the port's kerbs.lm.json = tracks/high-plains/source/edges/
               kerbs.json with R s 2,673 re-traced onto its paint, retrace_stripe_2673.py: its live edge and in_m / out_m), the outer side of the run's PAINT instead: the outermost white (mean >= 150, B >= 0.8 R), blue
               (B - (R + G) / 2 >= 12) or, on a blue / yellow stripe, yellow (R >= 175, (R + G) / 2 - B >= 50, mean >= 150:
               the stripe's yellow is (205, 194, 137), the bright dirt beside it (178-183, 166-170, 131-141)) run's outer end:
               the FIRST paint run within the run's band (live edge + in_m - 0.5 .. + out_m + 1.0), joints up to 0.2 m
               bridged. The kerb is the paved surface's edge
  mouths       MOUTHS below: where another road's paving runs on past the lap's edge (the north course's fork and merge,
               the short-course link, the pit-in lane), no reading is kept; the intake interpolates across. EYE_REJECT:
               the same for a stretch the strips show misread (each with its reason). A step found in the search's last
               window (offset >= MAX_M - 1.05 m) is the search's end, not an edge: not kept
  outliers     per side, a reading more than TOL_M off the median of the readings within +-HALF_M (at least MIN_NEAR of
               them) is dropped
Written as WORLD points (E, N in the line's frame) so the intake reads them against whatever line it builds
(tools/edge_retrace.py, lm_intake.edge_retrace mode "measured"): edge_evidence.json. Beside it, widths_measured.json (every
station: the two readings, their kind, the width where both read) and widths_strips_2023_030.jpg (the road straightened,
400 m a column, the readings drawn over it: check it by eye). Every UPPER-CASE number is [invented] tuning of a colour
reader (ledger 0097 round 2; no gate reads them); what the photo shows is the measurement.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

STEP = 0.1
START_M = 2.0           # [invented] the nearest edge on the lap is 3.4 m off the line
MAX_M = 10.0            # [invented] the farthest 9.9 m (the corner flares)
C_MIN = 12.0            # [invented] g step (p10 of the kept steps 18, median 26; 15 left the warm-asphalt edges at
#                         s 1,330-1,440 unread: their step is 13-16)
PAINT_GAP = 2           # [invented] a kerb's paint run bridges gaps of up to 0.2 m (the blocks' joints)
OUT_MIN = 30.0          # [invented] the outer window must look like ground (asphalt <= ~21 at its warmest)
WIN_IN = (-1.0, -0.2)
WIN_OUT = (0.2, 1.0)
HALF_M = 6.0            # [invented] the outlier window, +-6 m along
TOL_M = 0.4             # [invented] a reading this far off its neighbours' median is dropped
MIN_NEAR = 5
# where another road's paving runs on past the lap's edge: (side, s0, s1, what), stations on data/gate_centerline.json
MOUTHS = (
    ("right", 1335.0, 1395.0, "the short-course link's paving (ledger 0081: 'branches at s 1,348')"),
    ("right", 2595.0, 2672.0, "the link road leaving the hairpin's outside (light grey paving to the south-east)"),
    ("left", 2690.0, 2752.0, "the Full course's fork: To Hell On A Bobsled leaves (OSM node 1454637759, s 2,709)"),
    ("left", 2812.0, 2852.0, "the Full course's merge: Ladder To Heaven joins (OSM node 1454637805, s 2,831)"),
    ("left", 2992.0, 3082.0, "the pit-in lane beside the lap (its white line; ledger 0081: 'the pit lane (s 3,040-3,082)')"),
)
# rejected by eye on widths_strips_2023_030.jpg (the readings drawn over the photo): (side, s0, s1, why)
EYE_REJECT = (
    ("left", 1715.0, 1772.0, "dull green-grey grass the step reader takes for asphalt (its readings ramp 6.9 -> 9.0 m); the "
     "photo's edge runs from +4.95 m at s 1,710 to +4.9 m at s 1,775"),
)


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


class Naip:
    def __init__(self, png, meta, origin):
        self.A = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
        self.W, self.N, self.E, self.S = meta["corners"]
        self.o = origin
        self.mlon, self.mlat = mpd(origin["lat"])

    def rgb(self, x, z):
        h, w, _ = self.A.shape
        lon = self.o["lon"] + x / self.mlon
        lat = self.o["lat"] + z / self.mlat
        px = (lon - self.W) / (self.E - self.W) * w - 0.5
        py = (self.N - lat) / (self.N - self.S) * h - 0.5
        x0 = np.floor(px).astype(int); y0 = np.floor(py).astype(int)
        ok = (x0 >= 0) & (y0 >= 0) & (x0 < w - 1) & (y0 < h - 1)
        x0 = np.clip(x0, 0, w - 2); y0 = np.clip(y0, 0, h - 2)
        tx = (px - x0)[..., None]; ty = (py - y0)[..., None]
        A = self.A
        v = (A[y0, x0] * (1 - tx) + A[y0, x0 + 1] * tx) * (1 - ty) + (A[y0 + 1, x0] * (1 - tx) + A[y0 + 1, x0 + 1] * tx) * ty
        v[~ok] = np.nan
        return v


def groundness(V):
    R, G, B = V[..., 0], V[..., 1], V[..., 2]
    return np.maximum((R + G) / 2 - B, (2 * G - R - B) - 5.0)


def paint_mask(V, yellow_ok):
    R, G, B = V[..., 0], V[..., 1], V[..., 2]
    mean = (R + G + B) / 3
    white = (mean >= 150) & (B >= 0.8 * R)
    yel = (R >= 175) & ((R + G) / 2 - B >= 50) & (mean >= 150) & yellow_ok
    return white | (B - (R + G) / 2 >= 12) | yel


def first_rise(g, offs):
    n = len(offs)
    a0, a1 = int(round(WIN_IN[0] / STEP)), int(round(WIN_IN[1] / STEP))
    b0, b1 = int(round(WIN_OUT[0] / STEP)), int(round(WIN_OUT[1] / STEP))
    C = np.full(n, np.nan)
    OUT = np.full(n, np.nan)
    for j in range(-a0, n - b1):
        C[j] = np.nanmean(g[j + b0:j + b1 + 1]) - np.nanmean(g[j + a0:j + a1 + 1])
        OUT[j] = np.nanmean(g[j + b0:j + b1 + 1])
    ok = np.nonzero((C >= C_MIN) & (OUT >= OUT_MIN))[0]
    if len(ok) == 0:
        return None, None
    j = int(ok[0])
    k = j + int(np.nanargmax(C[j:j + 7]))
    if offs[k] >= MAX_M - WIN_OUT[1] - 0.05:        # the search's last window: its end, not an edge
        return None, None
    return float(offs[k]), float(C[k])


def kerb_edge(paint, offs, lo, hi):
    """the outer end of the FIRST paint run inside [lo, hi] (gaps of up to PAINT_GAP samples bridged): the kerb or stripe
    itself, never bright dirt or a block beyond it"""
    idx = np.nonzero(paint & (offs >= lo) & (offs <= hi))[0]
    if len(idx) < 2:
        return None
    end = idx[0]
    for j in idx[1:]:
        if j - end - 1 > PAINT_GAP:
            break
        end = j
    if end == idx[0]:
        return None
    return float(offs[end] + STEP / 2)


def measure(repo: Path):
    T = repo / "tracks" / "high-plains-lm"
    gc = json.loads((T / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
    origin = json.loads((T / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    meta = json.loads((T / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    naip = Naip(T / "source" / "road_wear" / "naip_2023_030_hp.png", meta, origin)
    kerbs = json.loads((T / "source" / "edges" / "kerbs.lm.json").read_text(encoding="utf-8"))   # the port's copy (R s 2,673)
    P = np.array([[p[0], p[2]] for p in gc["points_xyz_m"]])
    st = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = np.arange(0, st[-1], 1.0)
    x = np.interp(s, st, P[:, 0]); z = np.interp(s, st, P[:, 1])
    tx = np.gradient(x); tz = np.gradient(z); L = np.hypot(tx, tz); tx /= L; tz /= L
    offs = np.arange(START_M, MAX_M + 1e-9, STEP)
    runs = []
    for r in kerbs["kerbs"]:
        sg = 1 if r["side"] == "left" else -1
        ss, le = [], []
        for lon, lat in r["edge_lonlat"]:
            ex, ez = (lon - origin["lon"]) * naip.mlon, (lat - origin["lat"]) * naip.mlat
            i = int(np.argmin(np.hypot(x - ex, z - ez)))
            ss.append(s[i]); le.append(sg * ((ex - x[i]) * (-tz[i]) + (ez - z[i]) * tx[i]))
        runs.append({"side": r["side"], "colour": r["colour"], "s0": min(ss), "s1": max(ss), "ss": np.array(ss),
                     "le": np.array(le), "in_m": r["in_m"], "out_m": r["out_m"]})
    sides = {}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        V = naip.rgb(x[:, None] + nx[:, None] * offs[None, :], z[:, None] + nz[:, None] * offs[None, :])
        E = np.full(len(s), np.nan); C = np.full(len(s), np.nan); kind = [""] * len(s)
        for i in range(len(s)):
            if any(sd == side and a <= s[i] <= b for sd, a, b, _ in MOUTHS):
                kind[i] = "mouth"
                continue
            if any(sd == side and a <= s[i] <= b for sd, a, b, _ in EYE_REJECT):
                kind[i] = "eye-rejected"
                continue
            rr = [r for r in runs if r["side"] == side and r["s0"] - 2 <= s[i] <= r["s1"] + 2]
            if rr:
                r = rr[0]
                le = r["le"][int(np.argmin(np.abs(r["ss"] - s[i])))]
                e = kerb_edge(paint_mask(V[i], r["colour"] == "blue_yellow"), offs, le + r["in_m"] - 0.5, le + r["out_m"] + 1.0)
                if e is not None:
                    E[i] = e; kind[i] = "kerb"
                    continue
            e, c = first_rise(groundness(V[i]), offs)
            if e is not None:
                E[i] = e; C[i] = c; kind[i] = "edge"
        n = len(E)
        keep = np.zeros(n, bool)
        for i in range(n):
            if not np.isfinite(E[i]):
                continue
            v = E[np.arange(i - int(HALF_M), i + int(HALF_M) + 1) % n]
            v = v[np.isfinite(v)]
            keep[i] = len(v) >= MIN_NEAR and abs(E[i] - np.median(v)) <= TOL_M
        for i in range(n):
            if np.isfinite(E[i]) and not keep[i]:
                kind[i] = kind[i] + "-dropped"
        sides[side] = {"E": E, "C": C, "kind": kind, "keep": keep, "nx": nx, "nz": nz}
    return s, x, z, sides, naip, P


def write(repo: Path, out_dir: Path):
    s, x, z, sides, naip, P = measure(repo)
    T = repo / "tracks" / "high-plains-lm"
    origin = naip.o
    pts = []
    for side, d in sides.items():
        for i in np.nonzero(d["keep"])[0]:
            e = d["E"][i]
            pts.append([round(float(x[i] + d["nx"][i] * e), 3), round(float(z[i] + d["nz"][i] * e), 3), "naip",
                        round(float(d["C"][i]), 1) if np.isfinite(d["C"][i]) else None])
    EL, ER = sides["left"]["E"].copy(), sides["right"]["E"].copy()
    EL[~sides["left"]["keep"]] = np.nan; ER[~sides["right"]["keep"]] = np.nan
    W = EL + ER
    q = lambda a: [round(float(v), 2) for v in np.nanpercentile(a, [5, 25, 50, 75, 95])]
    counts = {side: {k: int(sum(1 for kk in d["kind"] if kk == k)) for k in sorted(set(d["kind"]))} for side, d in sides.items()}
    ev = {"_doc": "ledger 0097 round 2: measured pavement-edge points beside High Plains' lap (source/edges/measure_widths.py); "
                  "world E/N in the port's local frame (the line's origin), NAIP 2023's frame. The intake reads them through "
                  "tools/edge_retrace.py mode \"measured\" (lm_intake.edge_retrace).",
          "origin": origin, "imagery": "USDA NAIP co_m_3910317_ne_13_030_20230928 (2023-09-28), 0.3 m, the crop "
                                       "source/road_wear/naip_2023_030_hp.png (public domain)",
          "line": "data/gate_centerline.json (0.1.9's built line)", "counts": {"naip": len(pts)},
          "params": {"STEP": STEP, "START_M": START_M, "MAX_M": MAX_M, "C_MIN": C_MIN, "OUT_MIN": OUT_MIN,
                     "HALF_M": HALF_M, "TOL_M": TOL_M, "MIN_NEAR": MIN_NEAR},
          "mouths": [{"side": a, "s": [b, c], "what": d} for a, b, c, d in MOUTHS],
          "eye_rejected": [{"side": a, "s": [b, c], "why": d} for a, b, c, d in EYE_REJECT],
          "points": pts}
    (out_dir / "edge_evidence.json").write_text(json.dumps(ev), encoding="utf-8")
    rows = [{"s": float(s[i]), "left_m": None if not np.isfinite(EL[i]) else round(float(EL[i]), 2),
             "right_m": None if not np.isfinite(ER[i]) else round(float(ER[i]), 2),
             "width_m": None if not np.isfinite(W[i]) else round(float(W[i]), 2),
             "kind": [sides["left"]["kind"][i], sides["right"]["kind"][i]]} for i in range(len(s))]
    summ = {"_doc": "ledger 0097 round 2: every station's readings off the line (left / right, + outward), the kind of each "
                    "(edge, kerb, mouth, -dropped = an outlier) and the width where both sides read (measure_widths.py)",
            "stations": len(s), "both_read": int(np.isfinite(W).sum()), "counts": counts,
            "width_m": q(W), "left_m": q(EL), "right_m": q(ER), "rows": rows}
    (out_dir / "widths_measured.json").write_text(json.dumps(summ), encoding="utf-8")
    # the straightened strips (400 m a column, +-10 m across, 0.1 m a pixel), the kept readings drawn over them
    s2 = np.arange(0, s[-1], 0.5)
    x2 = np.interp(s2, s, x); z2 = np.interp(s2, s, z)
    t2x = np.gradient(x2); t2z = np.gradient(z2); L2 = np.hypot(t2x, t2z); t2x /= L2; t2z /= L2
    o2 = np.arange(-10, 10.001, 0.1)
    V = naip.rgb(x2[:, None] + (-t2z)[:, None] * o2[None, :], z2[:, None] + t2x[:, None] * o2[None, :])
    cols = []
    for k in range(int(s2[-1] // 400) + 1):
        a, b = k * 800, min(len(s2), k * 800 + 800)
        I = Image.fromarray(np.nan_to_num(V[a:b]).clip(0, 255).astype(np.uint8)).resize((402, b - a), Image.NEAREST)
        D = ImageDraw.Draw(I)
        for i in range(len(s)):
            r = int(round(s[i] / 0.5)) - a
            if 0 <= r < b - a:
                for E, sg, col in ((EL, 1, (255, 0, 0)), (ER, -1, (255, 0, 255))):
                    if np.isfinite(E[i]):
                        xx = (sg * E[i] + 10) / 0.1 * 2
                        D.rectangle([xx - 1, r - 1, xx + 1, r + 1], fill=col)
        for sv in range(int(s2[a] // 50 * 50), int(s2[b - 1]) + 1, 50):
            r = int(round(sv / 0.5)) - a
            if 0 <= r < b - a:
                D.text((2, r), str(sv), fill=(255, 255, 0))
        cols.append(I)
    sheet = Image.new("RGB", (sum(c.width + 6 for c in cols), 800), (255, 255, 255))
    xo = 0
    for c in cols:
        sheet.paste(c, (xo, 0)); xo += c.width + 6
    sheet.save(out_dir / "widths_strips_2023_030.jpg", quality=88)
    print(f"[measure_widths] {len(pts)} edge points kept ({counts}); widths where both read (p5/25/50/75/95) {summ['width_m']} m")
    return summ


if __name__ == "__main__":
    write(Path(sys.argv[1]).resolve(), Path(__file__).resolve().parent)
