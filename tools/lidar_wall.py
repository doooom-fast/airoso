"""Measure a wall beside a track's lane edge from USGS 3DEP source lidar: where its face stands and how tall it is (ledger 0078).

Kevin, 2026-11-03: "I just want real". Pikes Peak's outer retaining wall stood on the port at an invented 1.4 m past the
edge and 0.81 m tall (the engine's K-rail module). The 2018 lidar (CO_Eastern_ElPaso_2018) holds the wall's own returns.

Method, per station every STEP_M along the line (data/centerline.local.json, ENU, with its widths), on the chosen side:
  - every return within ALONG_M along and from EDGE_IN_M inside the lane edge to SEARCH_M outside it, noise classes
    (7, 18) dropped;
  - the road at the edge: a least-squares plane z = a + b * lateral through the GROUND (class 2) returns on PLANE_W_M of
    lane ending 0.5 m short of FACE_IN_M inside the edge, trimmed of points more than TRIM_M off it;
  - each return's height over that plane extended outwards; the WALL is the returns standing WALL_LO_M .. WALL_HI_M over
    it from FACE_IN_M inside the edge outwards: its FACE is their FACE_PCT percentile lateral (the inner face, the one a car meets), its TOP the
    TOP_PCT percentile height of those within TOP_BAND_M of the face. Returns over WALL_HI_M are counted apart (a catch
    fence's wires and posts, too sparse to place);
  - a station with fewer than MIN_PTS wall returns has no wall reading.
Then the readings along the lap: the median face offset and top height, their spread, and the stations with a wall.
Nothing is built here; the port's config takes the numbers (ledger 0078 records them).

Writes <out>.json (per station and the summary). Fetching needs numpy, scipy, laspy[lazrs], pyproj (run it on the G10).

    python tools/lidar_wall.py <project-dir> --side right|left [--ept URL] [--out <path>]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402
from scripts.tls import https_context  # noqa: E402

EPT_DEFAULT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_Eastern_ElPaso_2018/ept.json"
STEP_M = 3.0
ALONG_M = 3.0        # [invented] a station and its neighbours either side: a 2018 QL2 wall top holds few returns per metre
EDGE_IN_M = 8.0      # [invented] how far inside the lane edge returns are read (the road plane is fitted there)
PLANE_W_M = 2.5
SEARCH_M = 8.0       # [invented] how far past the edge a wall is looked for
TRIM_M = 0.05        # [invented] ground returns further than this off the plane are not road
WALL_LO_M, WALL_HI_M = 0.3, 2.5   # [invented] a return this high over the road plane, past the edge, is wall
FACE_PCT = 10        # [invented] the inner face: the 10th percentile lateral of the wall returns
TOP_BAND_M = 0.8     # [invented] the wall's top: returns within this of the face
TOP_PCT = 90         # [invented]
MIN_PTS = 5          # [invented]
FACE_IN_M = 5.0      # [invented] a face may stand this far INSIDE the line's lane edge (the line's width is the trace's: at Pikes Peak it runs up to ~3 m past the wall)
NOISE = (7, 18)


def stations(pts, widths, step=STEP_M):
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    out, s, j = [], 0.0, 0
    while s < st[-1] - 1e-6:
        while j < len(st) - 2 and st[j + 1] < s:
            j += 1
        t = (s - st[j]) / ((st[j + 1] - st[j]) or 1e-9)
        a, b = pts[j], pts[j + 1]
        x, y = a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t
        h = math.atan2(b[2] - a[2], b[0] - a[0])
        hw = (widths[j] + (widths[j + 1] - widths[j]) * t) / 2.0
        out.append((round(s, 1), x, y, -math.sin(h), math.cos(h), hw))
        s += step
    return out


def measure(project: Path, side: str, ept_url: str, log=print) -> dict:
    import numpy as np
    import laspy
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    loc = json.loads((project / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    origin = loc["origin"]
    sts = stations(loc["points_xyz_m"], loc["widths_m"])
    sg = -1.0 if side == "right" else 1.0

    def get(url):
        with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
            return r.read()
    ept = json.loads(get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    if ept["srs"].get("horizontal") != "3857":
        raise SystemExit(f"lidar_wall: {ept_url} is not in EPSG:3857")
    m_lon, m_lat = _meters_per_degree(origin["lat"])
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    E = np.array([s[1] for s in sts]); N = np.array([s[2] for s in sts])
    sx, sy = to_merc.transform(origin["lon"] + E / m_lon, origin["lat"] + N / m_lat)
    reach = max(s[5] for s in sts) + SEARCH_M + 2.0
    pad = reach / math.cos(math.radians(origin["lat"]))
    b = ept["bounds"]
    hier_files = {}

    def hier(key):
        if key not in hier_files:
            hier_files[key] = json.loads(get(f"{base}/ept-hierarchy/{key}.json"))
        return hier_files[key]
    keys = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = hier(k)
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        if not np.any((sx >= x0 - pad) & (sx <= x0 + sz + pad) & (sy >= y0 - pad) & (sy <= y0 + sz + pad)):
            return
        if h[k] > 0:
            keys.append(k)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, hier("0-0-0-0"))
    log(f"lidar_wall: {len(keys)} EPT nodes along the corridor")
    tree = cKDTree(np.c_[E, N])
    LE = np.array([s[3] for s in sts]); LN = np.array([s[4] for s in sts]); HW = np.array([s[5] for s in sts])
    per = [[[], [], []] for _ in sts]          # station -> (lateral past the edge, z, class)
    for q, k in enumerate(keys):
        las = laspy.read(io.BytesIO(get(f"{base}/ept-data/{k}.laz")))
        cls = np.asarray(las.classification)
        m = ~np.isin(cls, NOISE)
        if not m.any():
            continue
        lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
        pe = (lon - origin["lon"]) * m_lon; pn = (lat - origin["lat"]) * m_lat
        pz = np.asarray(las.z)[m]; pc = cls[m]
        dist, i = tree.query(np.c_[pe, pn], distance_upper_bound=reach)
        ok = np.isfinite(dist)
        i, pe, pn, pz, pc = i[ok], pe[ok], pn[ok], pz[ok], pc[ok]
        de, dn = pe - E[i], pn - N[i]
        lat_ = sg * (de * LE[i] + dn * LN[i]) - HW[i]           # metres past THIS side's lane edge (- = inside)
        along = de * LN[i] - dn * LE[i]
        ok = (np.abs(along) <= ALONG_M) & (lat_ >= -EDGE_IN_M) & (lat_ <= SEARCH_M)
        for ii, la, zz, cc in zip(i[ok].tolist(), lat_[ok].tolist(), pz[ok].tolist(), pc[ok].tolist()):
            per[ii][0].append(la); per[ii][1].append(zz); per[ii][2].append(cc)
        if q % 25 == 0:
            log(f"  node {q + 1}/{len(keys)}")
    rows = []
    for (s, *_), (la, zz, cc) in zip(sts, per):
        la, zz, cc = np.array(la), np.array(zz), np.array(cc)
        g = (cc == 2) & (la <= -FACE_IN_M + 0.5) & (la >= -FACE_IN_M - PLANE_W_M)
        row = {"s": s, "wall": None}
        if g.sum() < 6:
            rows.append(row); continue
        A = np.c_[np.ones(g.sum()), la[g]]
        coef = np.linalg.lstsq(A, zz[g], rcond=None)[0]
        for _ in range(3):
            res = zz[g] - A @ coef
            keep = np.abs(res) <= max(TRIM_M, 2.5 * res.std())
            if keep.sum() < 6:
                break
            coef = np.linalg.lstsq(A[keep], zz[g][keep], rcond=None)[0]
        h = zz - (coef[0] + coef[1] * la)
        w = (la > -FACE_IN_M) & (h >= WALL_LO_M) & (h <= WALL_HI_M)
        row["fence_returns"] = int(((la > -FACE_IN_M) & (h > WALL_HI_M) & (h < 8.0)).sum())
        row["road_slope_pct"] = round(100 * coef[1] * (-1 if side == "right" else 1), 2)
        if w.sum() >= MIN_PTS:
            face = float(np.percentile(la[w], FACE_PCT))
            band = w & (la <= face + TOP_BAND_M)
            top = float(np.percentile(h[band], TOP_PCT)) if band.sum() >= 3 else None
            row["wall"] = {"face_past_edge_m": round(face, 2), "top_over_road_m": None if top is None else round(top, 2),
                           "returns": int(w.sum()), "classes": sorted(set(int(c) for c in cc[w]))}
        rows.append(row)
    walls = [r["wall"] for r in rows if r["wall"] and r["wall"]["top_over_road_m"] is not None]
    summ = {"stations": len(rows), "with_wall": len(walls)}
    if walls:
        f = np.array([w["face_past_edge_m"] for w in walls]); t = np.array([w["top_over_road_m"] for w in walls])
        summ.update({"face_past_edge_m": {"p10": round(float(np.percentile(f, 10)), 2), "median": round(float(np.median(f)), 2),
                                          "p90": round(float(np.percentile(f, 90)), 2)},
                     "top_over_road_m": {"p10": round(float(np.percentile(t, 10)), 2), "median": round(float(np.median(t)), 2),
                                         "p90": round(float(np.percentile(t, 90)), 2)},
                     "classes": sorted({c for w in walls for c in w["classes"]})})
    return {"ept": ept_url, "side": side, "line": "data/centerline.local.json (ENU) with its widths_m",
            "params": {"STEP_M": STEP_M, "ALONG_M": ALONG_M, "EDGE_IN_M": EDGE_IN_M, "PLANE_W_M": PLANE_W_M,
                       "SEARCH_M": SEARCH_M, "TRIM_M": TRIM_M, "WALL_LO_M": WALL_LO_M, "WALL_HI_M": WALL_HI_M,
                       "FACE_PCT": FACE_PCT, "FACE_IN_M": FACE_IN_M, "TOP_BAND_M": TOP_BAND_M, "TOP_PCT": TOP_PCT, "MIN_PTS": MIN_PTS},
            "summary": summ, "stations": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--side", choices=("right", "left"), required=True)
    ap.add_argument("--ept", default=EPT_DEFAULT)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    rep = measure(a.project, a.side, a.ept)
    out = a.out or (a.project / "source" / "lidar" / "wall-survey" / f"wall_{a.side}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"lidar_wall: {rep['summary']} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
