"""The Full layout's extra pieces measured (ledger 0097 round 2, item 2, the data half; Kevin 2026-11-22: "Yes, add the Full
layout"): To Hell On A Bobsled + Ladder To Heaven as one piece, from the fork to the merge, in the engine's connector shape.

    python -I measure_north.py <repo>      (numpy + Pillow; writes north_loop.json beside itself)

  line     OSM (osm_full_course.json, the 2026-10-28 snapshot): Bobsled (132189631) from node 1454637759 (the fork, where the
           West lap turns onto Prarie Corkscrew) to 1454637958, then Ladder (289314483) to node 1454637805 (Corkscrew's
           vertex 7, where it rejoins the West lap), resampled every STEP_M in the port's frame (the line's origin)
  widths   NAIP 2023 off the committed photos, as measure_widths.py reads the lap (the same ground-ness step, the same
           thresholds; the first outward step from 2 to 10 m, an outlier more than TOL_M off its neighbours' median dropped):
           the 0.3 m crop where it reaches (south of lat 39.73681), else the z18 web-tile photo (0.46 m,
           tracks/high-plains/source/naip_2023_hp_z18.png, to lat 39.73887). Each side's readings run through a
           MED_M running median; the width is left + right and the centre moves by (left - right) / 2. North of the photos
           (the top ~318 m) nothing is read: the width there is CARRIED, the median of the measured widths, and the centre
           is OSM's (marked per point)
  heights  3DEP beside the line (corridor_3dep_north.json: native samples every 6 m x 5 m, +-60 m): inverse distance over
           the 4 nearest, then a SMOOTH_M running mean along; y = elevation - the line's origin elevation
Every UPPER-CASE number is [invented] tuning (ledger 0097 round 2); the photos and 3DEP are the measurement. Nothing reads
north_loop.json yet: the Full layout is not built (ledger 0097, "Still to do (round 3)").
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
FORK, TURN, MERGE = 1454637759, 1454637958, 1454637805
BOBSLED, LADDER = 132189631, 289314483


def z18_reader(repo):
    T = repo / "tracks" / "high-plains" / "source"
    g = json.loads((T / "naip_2023_hp_z18.georef.json").read_text(encoding="utf-8"))
    A = np.asarray(Image.open(T / "naip_2023_hp_z18.png").convert("RGB")).astype(np.float32)
    n = 2 ** g["z"] * 256

    def rgb_ll(lon, lat):
        X = (lon + 180.0) / 360.0 * n - g["x0"] * 256 - 0.5
        Y = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n - g["y0"] * 256 - 0.5
        h, w, _ = A.shape
        x0 = np.floor(X).astype(int); y0 = np.floor(Y).astype(int)
        ok = (x0 >= 0) & (y0 >= 0) & (x0 < w - 1) & (y0 < h - 1)
        x0 = np.clip(x0, 0, w - 2); y0 = np.clip(y0, 0, h - 2)
        tx = (X - x0)[..., None]; ty = (Y - y0)[..., None]
        v = (A[y0, x0] * (1 - tx) + A[y0, x0 + 1] * tx) * (1 - ty) + (A[y0 + 1, x0] * (1 - tx) + A[y0 + 1, x0 + 1] * tx) * ty
        v[~ok] = np.nan
        return v
    return rgb_ll, A.shape


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
    z18, _ = z18_reader(repo)
    lat_s = origin["lat"] + z / mlat
    offs = np.arange(mw.START_M, mw.MAX_M + 1e-9, mw.STEP)
    side_e = {}
    for side, sg in (("left", 1), ("right", -1)):
        nx, nz = -tz * sg, tx * sg
        X = x[:, None] + nx[:, None] * offs[None, :]; Z = z[:, None] + nz[:, None] * offs[None, :]
        Vc = crop.rgb(X, Z)
        Vz = z18(origin["lon"] + X / mlon, origin["lat"] + Z / mlat)
        E = np.full(len(s), np.nan); src = [""] * len(s)
        for i in range(len(s)):
            for V, name, lim in ((Vc, "naip_030", meta["corners"][1]), (Vz, "naip_z18", 39.73887)):
                if lat_s[i] > lim - 10.0 / mlat or not np.isfinite(V[i]).all():
                    continue
                e, _c = mw.first_rise(mw.groundness(V[i]), offs)
                if e is not None:
                    E[i] = e; src[i] = name
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
        side_e[side] = (E, Em, src)
    EL, ER = side_e["left"][1], side_e["right"][1]
    both = np.isfinite(EL) & np.isfinite(ER)
    carried_w = float(np.median((EL + ER)[both]))
    # the photo's last read row, then carried to the merge's end (the top of the loop is in no photo)
    W = np.where(both, EL + ER, carried_w)
    SH = np.where(both, (EL - ER) / 2.0, 0.0)
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
    rows = [{"s": round(float(s[i]), 1), "left_m": None if not np.isfinite(EL[i]) else round(float(EL[i]), 2),
             "right_m": None if not np.isfinite(ER[i]) else round(float(ER[i]), 2), "width_m": round(float(W[i]), 2),
             "width": "measured" if both[i] else "carried",
             "photo": side_e["left"][2][i] or side_e["right"][2][i] or None} for i in out_i]
    conn = {"name": "full_north", "kind": "connector",
            "points_xyz_m": [[round(float(cx[i]), 3), round(float(Ys[i]), 3), round(float(cz[i]), 3)] for i in out_i],
            "widths_m": [round(float(W[i]), 3) for i in out_i], "joined": [],
            "source": ("OSM To Hell On A Bobsled (132189631) node 1454637759 -> 1454637958 + Ladder To Heaven (289314483) -> "
                       "1454637805 (osm_full_course.json); widths NAIP 2023 (0.3 m crop / z18 0.46 m) where read, else carried "
                       f"{carried_w:.2f} m; heights 3DEP (corridor_3dep_north.json), {SMOOTH_M:.0f} m mean (measure_north.py)")}
    meas = (EL + ER)[both]
    summ = {"length_m": round(float(s[-1]), 1), "points": len(out_i), "carried_width_m": round(carried_w, 2),
            "measured_m": int(both.sum() * READ_STEP_M), "carried_m": int((~both).sum() * READ_STEP_M),
            "width_measured_m": [round(float(v), 2) for v in np.percentile(meas, [5, 25, 50, 75, 95])],
            "centre_shift_m": [round(float(SH[both].min()), 2), round(float(SH[both].max()), 2)],
            "height_m": [round(float(Ys.min() + origin["elev_m"]), 1), round(float(Ys.max() + origin["elev_m"]), 1)]}
    return conn, rows, summ


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    conn, rows, summ = measure(repo)
    out = {"_doc": "ledger 0097 round 2: the Full layout's extra pieces in the engine's connector shape (measure_north.py); "
                   "nothing reads it yet (the Full layout is not built)", "summary": summ, "connectors": [conn], "rows": rows}
    (HERE / "north_loop.json").write_text(json.dumps(out, indent=0), encoding="utf-8")
    print(f"[north] {summ}")
