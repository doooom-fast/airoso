"""The Full layout's extra pieces measured (ledger 0097 round 2, item 2, the data half; Kevin 2026-11-22: "Yes, add the Full
layout"): To Hell On A Bobsled + Ladder To Heaven as one piece, from the fork to the merge, in the engine's connector shape.

    python -I measure_north.py <repo>      (numpy + Pillow; writes north_loop.json beside itself)

  line     OSM (osm_full_course.json, the 2026-10-28 snapshot): Bobsled (132189631) from node 1454637759 (the fork, where the
           West lap turns onto Prarie Corkscrew) to 1454637958, then Ladder (289314483) to node 1454637805 (Corkscrew's
           vertex 7, where it rejoins the West lap), resampled every STEP_M in the port's frame (the line's origin)
  widths   NAIP 2023 off the committed photos, as measure_widths.py reads the lap (the same ground-ness step, the same
           thresholds; the first outward step from 2 to 10 m, an outlier more than TOL_M off its neighbours' median dropped)
           (round 3: a row read on one side or none takes each edge interpolated between its nearest rows read on both, and
           both edges run through an EDGE_SMOOTH_M mean; summary carried_width_m stays the measured median, for reference):
           the 0.3 m crop where it reaches (south of lat 39.73681), else the z18 web-tile photo (0.46 m,
           tracks/high-plains/source/naip_2023_hp_z18.png, to lat 39.73887) and, since round 3, the z18 tiles above it
           (naip_2023_hp_north_z18.png beside this file, the same NAIP item, to lat 39.74099), read as one mosaic. Each
           side's readings run through a MED_M running median; the width is left + right and the centre moves by
           (left - right) / 2. Where no photo reads both sides the width is CARRIED, the median of the measured widths,
           and the centre is OSM's (marked per point)
  plan     round 3: the measured centre line run through a PLAN_SMOOTH_M Gaussian along (OSM's polygon of the real arcs)
  heights  3DEP beside the line (corridor_3dep_north.json: native samples every 6 m x 5 m, +-60 m): inverse distance over
           the 4 nearest, then a SMOOTH_M running mean along; y = elevation - the line's origin elevation
Every UPPER-CASE number is [invented] tuning (ledger 0097 round 2); the photos and 3DEP are the measurement. Read by
make_connectors.py (round 3) into connectors.full.json, the Full layout's connector.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "edges"))
import measure_widths as mw  # noqa: E402  (the lap's reader: groundness, first_rise, its thresholds)

STEP_M = 2.0
READ_STEP_M = 1.0
TOL_M = 0.4
MED_M = 15.0
SMOOTH_M = 9.0
EDGE_SMOOTH_M = 10.0
PLAN_SMOOTH_M = 4.0
FORK, TURN, MERGE = 1454637759, 1454637958, 1454637805
Z18_SOUTH_N = 39.73887     # the committed z18 photo's north edge: a reading north of it is the round-3 tiles' (labelled _north)
BOBSLED, LADDER = 132189631, 289314483


NORTH_Z18 = "naip_2023_hp_north_z18"     # round 3: the tiles above the committed z18 photo (beside this file)

# round 4 (ledger 0097 round 4, item 5): the SECOND READ of the rows round 3 carried. Each stretch below is a run of rows where
# the step reader left one side unread after its running median (the verge there greys into the prairie over metres, so no
# 1 m step reaches C_MIN / OUT_MIN). What edges the pavement there was checked BY EYE on straightened strips of the photos
# (ledger 0081's method: eye-checked spans, then a reader measures within them), and is read station by station:
#   "line"  the painted white edge line: the FIRST luminance ridge (a local maximum over +-0.3 m of the 0.3 m running mean of
#           (R + G + B) / 3) standing LINE_MIN over the darkest asphalt in the 1 m inside it, within the band; the edge is
#           that ridge + the photo's own measured line-to-edge offset (the median of the step reader's edge less the ridge
#           LINE_TO_EDGE_SEARCH_M inside it, over the rows both read on that photo)
#   "kerb"  a raised kerb's paint (the north loop's kerbs, kerbs.lm.json): the outer end of the first paint run within the
#           band (measure_widths.kerb_edge, the lap's own kerb rule: the kerb is the paved surface's edge)
# A second-read row joins the first read's rows through the same outlier filter and running median; a row the first read
# already holds keeps its value. The bands [lo, hi] (metres off OSM's line) are read by eye on those strips.
# (side, s0, s1, kind, lo, hi, what the strips show)
SECOND_READ = (
    ("left", 216.0, 240.0, "line", 4.8, 6.6, "the white edge line, clear, after the T10 kerb's end (L s 216); a grey-green verge 1-3 m wide beyond it"),
    ("left", 240.0, 300.0, "line", 3.8, 5.6, "the white edge line, faint, the verge beyond it greying into the prairie"),
    ("right", 301.0, 306.5, "line", 5.8, 7.2, "the white edge line before the kerb R s 307"),
    ("right", 306.5, 335.0, "kerb", 6.2, 9.4, "the kerb R s 307-335 (blue / white blocks): its paint's outer end"),
    ("right", 335.0, 354.0, "line", 6.6, 8.2, "the white edge line past the kerb"),
    ("left", 714.0, 733.0, "line", 4.8, 6.4, "the white edge line before the kerb L s 733 (a dark band just outside it)"),
    ("left", 733.0, 739.0, "kerb", 5.0, 8.6, "the kerb L s 733-761: its paint's outer end"),
    ("right", 933.0, 941.0, "line", 3.8, 5.0, "the white edge line where the read passes from the z18 photo to the 0.3 m crop"),
)
NOT_READ = (
    ("right", 0.0, 20.0, "the fork's mouth: the West lap's pavement runs on (inside the FORK pad's measured outline; the cut drops these rows)"),
    ("right", 986.0, 1001.0, "the merge's mouth: the West lap's pavement runs on (the bellmouth; the weld meets the West lap there)"),
    ("left", 996.0, 1001.0, "the merge's mouth: the T13 kerb turns onto the West lap's edge"),
)
LINE_MIN = 10.0                 # [invented] the edge line's prominence over the asphalt inside it (8-bit)
LINE_TO_EDGE_SEARCH_M = 1.0     # [invented] ... and the ridge sought this far inside a first-read edge to measure the offset


def ridges(lum, offs):
    """the luminance ridges of one cross profile: [(offset, prominence)], innermost first (round 4's edge-line reader)"""
    sm = np.convolve(lum, np.ones(3) / 3.0, mode="same")
    w, k = int(round(0.3 / mw.STEP)), int(round(1.0 / mw.STEP))
    out = []
    for j in range(k, len(sm) - w):
        if sm[j] >= sm[j - w:j + w + 1].max():
            p = float(sm[j] - sm[j - k:j].min())
            if p >= LINE_MIN:
                out.append((float(offs[j]), p))
    return out


def z18_reader(repo):
    """the committed z18 photo and, when present, the north tiles above it, as ONE z18 mosaic (both are whole web-mercator
    tiles of the same NAIP item; nan where neither holds a pixel). Returns (rgb_ll, the mosaic's north edge latitude)"""
    T = repo / "tracks" / "high-plains" / "source"
    parts = [(json.loads((T / "naip_2023_hp_z18.georef.json").read_text(encoding="utf-8")), T / "naip_2023_hp_z18.png")]
    nj = HERE / (NORTH_Z18 + ".georef.json")
    if nj.exists():
        parts.append((json.loads(nj.read_text(encoding="utf-8")), HERE / (NORTH_Z18 + ".png")))
    z = parts[0][0]["z"]
    if any(g["z"] != z for g, _p in parts):
        raise SystemExit("[north] the z18 pieces are not one zoom")
    x0 = min(g["x0"] for g, _p in parts); y0 = min(g["y0"] for g, _p in parts)
    x1 = max(g["x0"] + g["w"] // 256 for g, _p in parts); y1 = max(g["y0"] + g["h"] // 256 for g, _p in parts)
    A = np.full(((y1 - y0) * 256, (x1 - x0) * 256, 3), np.nan, dtype=np.float32)
    for g, png in parts:
        im = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
        r, c = (g["y0"] - y0) * 256, (g["x0"] - x0) * 256
        A[r:r + im.shape[0], c:c + im.shape[1]] = im
    n = 2 ** z * 256
    north_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y0 * 256 / n))))

    def rgb_ll(lon, lat):
        X = (lon + 180.0) / 360.0 * n - x0 * 256 - 0.5
        Y = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n - y0 * 256 - 0.5
        h, w, _ = A.shape
        xa = np.floor(X).astype(int); ya = np.floor(Y).astype(int)
        ok = (xa >= 0) & (ya >= 0) & (xa < w - 1) & (ya < h - 1)
        xa = np.clip(xa, 0, w - 2); ya = np.clip(ya, 0, h - 2)
        tx = (X - xa)[..., None]; ty = (Y - ya)[..., None]
        v = (A[ya, xa] * (1 - tx) + A[ya, xa + 1] * tx) * (1 - ty) + (A[ya + 1, xa] * (1 - tx) + A[ya + 1, xa + 1] * tx) * ty
        v[~ok] = np.nan
        return v
    return rgb_ll, north_lat


def measure(repo: Path):
    P = repo / "tracks" / "high-plains-lm"
    origin = json.loads((P / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    mlon, mlat = mw.mpd(origin["lat"])
    osm = json.loads((HERE / "osm_full_course.json").read_text(encoding="utf-8"))
    ways = {e["id"]: e for e in osm["elements"]}

    def piece(wid, a, b):
        e = ways[wid]
        i, j = e["nodes"].index(a), e["nodes"].index(b)
        return [(g["lon"], g["lat"]) for g in e["geometry"][i:j + 1]]
    ll = piece(BOBSLED, FORK, TURN) + piece(LADDER, TURN, MERGE)[1:]
    xy = np.array([((lo - origin["lon"]) * mlon, (la - origin["lat"]) * mlat) for lo, la in ll])
    st = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    s = np.arange(0, st[-1] + 1e-9, READ_STEP_M)
    x = np.interp(s, st, xy[:, 0]); z = np.interp(s, st, xy[:, 1])
    k = int(round(5.0 / READ_STEP_M))                  # tangents over +-5 m (OSM's corners are vertices)
    tx = np.array([x[min(i + k, len(s) - 1)] - x[max(i - k, 0)] for i in range(len(s))])
    tz = np.array([z[min(i + k, len(s) - 1)] - z[max(i - k, 0)] for i in range(len(s))])
    L = np.hypot(tx, tz); tx /= L; tz /= L
    meta = json.loads((P / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    crop = mw.Naip(P / "source" / "road_wear" / "naip_2023_030_hp.png", meta, origin)
    z18, z18_north = z18_reader(repo)
    lat_s = origin["lat"] + z / mlat
    offs = np.arange(mw.START_M, mw.MAX_M + 1e-9, mw.STEP)
    side_e, second_e = {}, {}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        X = x[:, None] + nx[:, None] * offs[None, :]; Z = z[:, None] + nz[:, None] * offs[None, :]
        Vc = crop.rgb(X, Z)
        Vz = z18(origin["lon"] + X / mlon, origin["lat"] + Z / mlat)
        E = np.full(len(s), np.nan); src = [""] * len(s)
        prof = [None] * len(s); pname = [""] * len(s)
        for i in range(len(s)):
            for V, name, lim in ((Vc, "naip_030", meta["corners"][1]), (Vz, "naip_z18", z18_north)):
                if lat_s[i] > lim - 10.0 / mlat or not np.isfinite(V[i]).all():
                    continue
                prof[i], pname[i] = V[i], name                 # the photo this row is read on (round 4: the second read's)
                e, _c = mw.first_rise(mw.groundness(V[i]), offs)
                if e is not None:
                    E[i] = e; src[i] = name + ("_north" if name == "naip_z18" and lat_s[i] > Z18_SOUTH_N else "")
                break
        n = len(E)
        keep = np.zeros(n, bool)
        for i in range(n):
            if np.isfinite(E[i]):
                v = E[max(0, i - 6):i + 7]; v = v[np.isfinite(v)]
                keep[i] = len(v) >= mw.MIN_NEAR and abs(E[i] - np.median(v)) <= TOL_M
        E[~keep] = np.nan
        h = int(round(MED_M / 2 / READ_STEP_M))
        Em = np.array([np.nanmedian(E[max(0, i - h):i + h + 1]) if np.isfinite(E[max(0, i - h):i + h + 1]).sum() >= 5
                       else np.nan for i in range(n)])
        # round 4: the second read (SECOND_READ above) of the rows the first read left unread after its median
        off_e = {}
        for nm in ("naip_030", "naip_z18"):
            d = []
            for i in range(n):
                if np.isfinite(E[i]) and pname[i] == nm:
                    rr = [o for o, _p in ridges(prof[i].mean(axis=1), offs) if E[i] - LINE_TO_EDGE_SEARCH_M <= o <= E[i]]
                    if rr:
                        d.append(E[i] - rr[-1])
            off_e[nm] = (float(np.median(d)) if d else None, len(d))
        E2 = np.full(n, np.nan); how2 = [""] * n
        for sd, a, b, kind, lo, hi, _why in SECOND_READ:
            if sd != side:
                continue
            for i in range(n):
                if not (a <= s[i] <= b) or np.isfinite(Em[i]) or prof[i] is None:
                    continue
                if kind == "kerb":
                    e = mw.kerb_edge(mw.paint_mask(prof[i], False), offs, lo, hi)
                else:
                    rr = [o for o, _p in ridges(prof[i].mean(axis=1), offs) if lo <= o <= hi]
                    e = rr[0] + off_e[pname[i]][0] if rr and off_e[pname[i]][0] is not None else None
                if e is not None:
                    E2[i] = e; how2[i] = kind
        Ec = np.where(np.isfinite(E), E, E2)
        keep2 = np.zeros(n, bool)
        for i in range(n):
            if np.isfinite(Ec[i]):
                v = Ec[max(0, i - 6):i + 7]; v = v[np.isfinite(v)]
                keep2[i] = len(v) >= mw.MIN_NEAR and abs(Ec[i] - np.median(v)) <= TOL_M
        Ec[~keep2] = np.nan
        Em2 = np.array([np.nanmedian(Ec[max(0, i - h):i + h + 1]) if np.isfinite(Ec[max(0, i - h):i + h + 1]).sum() >= 5
                        else np.nan for i in range(n)])
        second = ~np.isfinite(Em) & np.isfinite(Em2)
        Em = np.where(np.isfinite(Em), Em, Em2)                 # a first-read row keeps its value
        for i in np.nonzero(second)[0]:
            src[i] = (src[i] or pname[i]) + "_second_read"
        side_e[side] = (E, Em, src)
        second_e[side] = {"rows": int(second.sum()), "readings": int(np.isfinite(E2).sum()),
                          "kept": int((np.isfinite(E2) & keep2 & ~np.isfinite(E)).sum()),
                          "line_to_edge_m": {k_: (None if v_[0] is None else round(v_[0], 2), v_[1]) for k_, v_ in off_e.items()},
                          "second": second}
    EL, ER = side_e["left"][1], side_e["right"][1]
    both = np.isfinite(EL) & np.isfinite(ER)
    carried_w = float(np.median((EL + ER)[both]))
    # round 3: a row not read on both sides takes each edge interpolated between the nearest rows that are (held past the
    # last one), not round 2's median width about OSM's centre: that jumped 1-2 m sideways at every measured / carried
    # boundary, and the built ribbon jogged with it (round 3's first Full build: 36 severe steps there); both edges then run
    # through an EDGE_SMOOTH_M running mean
    rb = np.nonzero(both)[0]
    he = int(round(EDGE_SMOOTH_M / 2 / READ_STEP_M))

    def run_mean(v):
        return np.array([v[max(0, i - he):i + he + 1].mean() for i in range(len(v))])
    Lb = run_mean(np.interp(s, s[rb], EL[rb]))
    Rb = run_mean(np.interp(s, s[rb], ER[rb]))
    W = Lb + Rb
    SH = (Lb - Rb) / 2.0
    corr = json.loads((HERE / "corridor_3dep_north.json").read_text(encoding="utf-8"))
    pts3 = []
    for (slon, slat), zrow, j in zip(corr["stations_lonlat"], corr["z"], range(len(corr["z"]))):
        a = corr["stations_lonlat"][max(j - 1, 0)]; b = corr["stations_lonlat"][min(j + 1, len(corr["z"]) - 1)]
        ux, uz = (b[0] - a[0]) * mlon, (b[1] - a[1]) * mlat
        Lu = math.hypot(ux, uz) or 1.0
        nx_, nz_ = -uz / Lu, ux / Lu
        cx, cz = (slon - origin["lon"]) * mlon, (slat - origin["lat"]) * mlat
        for off, zz in zip(corr["offsets"], zrow):
            pts3.append((cx + nx_ * off, cz + nz_ * off, zz))
    pts3 = np.array(pts3)
    cx = x + (-tz) * SH; cz = z + tx * SH
    # round 3: the centre line smoothed along (a PLAN_SMOOTH_M Gaussian; each end padded straight on its own last 5 m, so the
    # ends stay where they are): OSM's nodes stand 20-25 m apart and turn up to 23 deg at a node on the hairpin, a polygon of
    # the real arcs; the race lap walks these very points
    kr = int(3 * PLAN_SMOOTH_M / READ_STEP_M)
    gw = np.exp(-0.5 * ((np.arange(-kr, kr + 1) * READ_STEP_M) / PLAN_SMOOTH_M) ** 2)
    gw /= gw.sum()
    k5 = int(round(5.0 / READ_STEP_M))
    sm = []
    for v in (cx, cz):
        head = v[0] + (v[0] - v[k5]) / k5 * np.arange(kr, 0, -1)
        tail = v[-1] + (v[-1] - v[-1 - k5]) / k5 * np.arange(1, kr + 1)
        sm.append(np.convolve(np.r_[head, v, tail], gw, mode="valid"))
    cx, cz = sm
    Y = []
    for qx, qz in zip(cx, cz):
        d2 = (pts3[:, 0] - qx) ** 2 + (pts3[:, 1] - qz) ** 2
        idx = np.argsort(d2)[:4]
        wgt = 1.0 / np.maximum(d2[idx], 1e-6)
        Y.append(float((wgt * pts3[idx, 2]).sum() / wgt.sum()))
    Y = np.array(Y)
    hs = int(round(SMOOTH_M / 2 / READ_STEP_M))
    Ys = np.array([Y[max(0, i - hs):i + hs + 1].mean() for i in range(len(Y))]) - float(origin["elev_m"])
    out_i = np.arange(0, len(s), int(round(STEP_M / READ_STEP_M)))
    if out_i[-1] != len(s) - 1:
        out_i = np.r_[out_i, len(s) - 1]
    sec2 = both & (second_e["left"]["second"] | second_e["right"]["second"])
    rows = [{"s": round(float(s[i]), 1), "left_m": None if not np.isfinite(EL[i]) else round(float(EL[i]), 2),
             "right_m": None if not np.isfinite(ER[i]) else round(float(ER[i]), 2), "width_m": round(float(W[i]), 2),
             "width": ("measured_second_read" if sec2[i] else "measured") if both[i] else "carried",
             "photo": side_e["left"][2][i] or side_e["right"][2][i] or None} for i in out_i]
    conn = {"name": "full_north", "kind": "connector",
            "points_xyz_m": [[round(float(cx[i]), 3), round(float(Ys[i]), 3), round(float(cz[i]), 3)] for i in out_i],
            "widths_m": [round(float(W[i]), 3) for i in out_i], "joined": [],
            "source": ("OSM To Hell On A Bobsled (132189631) node 1454637759 -> 1454637958 + Ladder To Heaven (289314483) -> "
                       "1454637805 (osm_full_course.json); edges NAIP 2023 (0.3 m crop / z18 0.46 m) where read on both sides, "
                       "else carried between the nearest rows that are, both run through a "
                       f"{EDGE_SMOOTH_M:.0f} m mean; heights 3DEP (corridor_3dep_north.json), {SMOOTH_M:.0f} m mean (measure_north.py)")}
    meas = (EL + ER)[both]
    summ = {"length_m": round(float(s[-1]), 1), "points": len(out_i), "carried_width_m": round(carried_w, 2),
            "measured_m": int(both.sum() * READ_STEP_M), "carried_m": int((~both).sum() * READ_STEP_M),
            "width_measured_m": [round(float(v), 2) for v in np.percentile(meas, [5, 25, 50, 75, 95])],
            "centre_shift_m": [round(float(SH.min()), 2), round(float(SH.max()), 2)],
            "width_built_m": [round(float(v), 2) for v in np.percentile(W, [5, 25, 50, 75, 95])],
            "height_m": [round(float(Ys.min() + origin["elev_m"]), 1), round(float(Ys.max() + origin["elev_m"]), 1)],
            "second_read": {"_doc": "ledger 0097 round 4 (SECOND_READ): rows the first read left unread on one side, read again "
                                    "(the edge line or a kerb's paint, in eye-checked bands); measured_m counts them",
                            "measured_m": int(sec2.sum() * READ_STEP_M),
                            "per_side": {sd: {k_: v_ for k_, v_ in second_e[sd].items() if k_ != "second"} for sd in second_e},
                            "not_read": [{"side": a, "s": [b, c], "why": d} for a, b, c, d in NOT_READ]}}
    return conn, rows, summ


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    conn, rows, summ = measure(repo)
    out = {"_doc": "ledger 0097 rounds 2-3: the Full layout's extra pieces in the engine's connector shape (measure_north.py); "
                   "make_connectors.py makes the built connector of it", "summary": summ, "connectors": [conn], "rows": rows}
    (HERE / "north_loop.json").write_text(json.dumps(out, indent=0), encoding="utf-8")
    print(f"[north] {summ}")
