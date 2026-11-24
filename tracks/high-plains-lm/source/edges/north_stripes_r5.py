"""The north loop's two blue / yellow edge stripes, measured and built (ledger 0097 round 5, item 2).

    python -I north_stripes_r5.py <repo>      (numpy + Pillow; adds the two runs to kerbs.lm.json beside itself)

  inner side  the 2018 lidar's intensity (r5_lidar_g10/north_stripes.json, the G10's hp_r5_lidar.py): along each stripe the
              first bright return outward from the lane is the paint's inner side, 0.80-0.81 m further in than the white
              edge line either side. in_m is its median past the north loop's built lane edge IN THE PHOTO'S FRAME
              (in_m_photo_frame: the lidar's raw offset moved by the registration's measured shift, the 2018 lidar against
              the 2023 photo; the built edge was read off that photo): -1.37 m (372; raw -1.21) and -1.60 m (648; raw -1.78)
  outer side  NOT measured: the paint and the verge past it read alike in the lidar, and the z18 photo (0.46 m) does not
              resolve it. out_m 0.0, the road's built lane edge [invented]
  ends        the 2023 photo (NAIP 2023-09-28 z18, the newer state) where it gives a readable end, else the lidar's (2018).
              Read on the band [in_m, 0] against the lane 1.0-2.5 m inside it (PROFILE below, printed by this script) and
              by eye on 40 px/m zooms of the z18 photo:
                372 s0  372.0 lidar: on the photo the white edge line runs on into the stripe, so the band's brightness does
                        not step; the colour alone begins 370.5-371.5 on single 0.46 m pixels: not readable
                372 s1  400.0 photo: the band's brightness falls to the lane's (+28 -> +2 over 399-401, half at 400.0);
                        the lidar's core ends 396.5 (its taper 398.5)
                648 s0  648.0 photo: the band's brightness steps up (p90 +68 -> +98 over 647.5-648.0: the stripe's pale
                        blocks are brighter than the edge line before them; its first blue block 649.5); the lidar's 653.0
                        (it ramps in over 649-655)
                648 s1  681.0 photo: the band's brightness falls to the lane's (+17 -> +6 over 680.5-681.5, half at 681.0);
                        the lidar's 674.0 (it ramps out over 674-681)
  edge        edge_lonlat: the north loop's built left lane edge from s0 to s1 (source/full/connectors.full.json, the line
              the lidar's offsets are read from), every 2 m and at both ends
Built as the lap's stripes are (author_kerbs_blend.py profile "paint": laid flat, no height; kerb.placement "measured"),
keyed to the north loop's rows ("line": "full_north#0#0", round 4's opt-in).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LINE = "full_north#0#0"
ENDS = {   # stripe: ((s0, source), (s1, source))
    "stripe372": ((372.0, "lidar_2018"), (400.0, "naip_2023_z18")),
    "stripe648": ((648.0, "naip_2023_z18"), (681.0, "naip_2023_z18")),
}
OUT_M = 0.0          # [invented] the outer side: the road's built lane edge (the paint's outer side is not measured)
EDGE_STEP_M = 2.0    # edge_lonlat every this far along (as the lap's runs: one point per ~2 m)
PROFILE = {"band": "[in_m, 0] past the built lane edge", "lane": "1.0-2.5 m inside in_m", "step_m": 0.5, "mean_m": 1.0}


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def frame(conn):
    P = np.array(conn["points_xyz_m"], float)
    W = np.array(conn["widths_m"], float)
    st = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 2])))]

    def left_edge(s, off=0.0):
        s = np.asarray(s, float)
        x, z, hw = np.interp(s, st, P[:, 0]), np.interp(s, st, P[:, 2]), np.interp(s, st, W) / 2
        d = 0.5
        tx = np.interp(s + d, st, P[:, 0]) - np.interp(s - d, st, P[:, 0])
        tz = np.interp(s + d, st, P[:, 2]) - np.interp(s - d, st, P[:, 2])
        L = np.hypot(tx, tz)
        nx, nz = -tz / L, tx / L                       # left of travel
        return x + nx * (hw + off), z + nz * (hw + off)
    return left_edge


def profile(repo, left_edge, origin, in_m, a, b):
    """the band's brightness over the lane's, every PROFILE step_m from a to b, a mean_m running mean (the record)"""
    sys.path.insert(0, str(repo / "tracks" / "high-plains-lm" / "source" / "full"))
    import measure_north as mn
    z18, _n = mn.z18_reader(repo)
    m_lon, m_lat = mpd(origin["lat"])
    s = np.arange(a - 0.5, b + 0.5 + 1e-9, 0.1)

    def lum(o0, o1):
        acc = []
        for o in np.arange(o0, o1 + 1e-9, 0.1):
            x, z = left_edge(s, o)
            acc.append(z18(origin["lon"] + x / m_lon, origin["lat"] + z / m_lat).mean(axis=-1))
        return np.array(acc)
    band, lane = lum(in_m, 0.0), lum(in_m - 2.5, in_m - 1.0)
    d = band.mean(axis=0) - lane.mean(axis=0)
    p90 = np.percentile(band, 90, axis=0) - lane.mean(axis=0)
    k = 10
    dm = np.convolve(d, np.ones(k) / k, mode="same")
    out = {}
    for i in range(5, len(s) - 5, 5):
        out[f"{s[i]:.1f}"] = [round(float(dm[i]), 1), round(float(p90[i]), 1)]
    return out


def main(repo: Path):
    P = repo / "tracks" / "high-plains-lm"
    origin = json.loads((P / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    m_lon, m_lat = mpd(origin["lat"])
    conn = json.loads((P / "source" / "full" / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    left_edge = frame(conn)
    S = json.loads((HERE / "r5_lidar_g10" / "north_stripes.json").read_text(encoding="utf-8"))["stripes"]
    K = json.loads((HERE / "kerbs.lm.json").read_text(encoding="utf-8"))
    K["kerbs"] = [r for r in K["kerbs"] if not (r.get("line") == LINE and r.get("profile") == "paint")]
    runs = []
    for key, rec in S.items():
        (s0, src0), (s1, src1) = ENDS[key]
        ss = list(np.arange(s0, s1, EDGE_STEP_M)) + [s1]
        x, z = left_edge(ss)
        edge = [[round(origin["lon"] + float(a) / m_lon, 8), round(origin["lat"] + float(c) / m_lat, 8)] for a, c in zip(x, z)]
        in_m = float(rec["in_m_photo_frame"])
        prof = {f"s{j}": profile(repo, left_edge, origin, in_m, e - 3.0, e + 3.0) for j, e in ((0, s0), (1, s1))}
        runs.append({
            "line": LINE, "side": rec["side"], "s0": s0, "s1": s1, "in_m": in_m, "out_m": OUT_M,
            "colour": "blue_yellow", "profile": "paint", "s_eye": rec["round4_eye_s"],
            "edge_lonlat": edge,
            "ends": {"s0": src0, "s1": src1, "lidar_2018": rec["s0_s1"], "lidar_2018_tapered": rec["s0_s1_tapered"],
                     "round4_eye_2023": rec["round4_eye_s"], "photo_profile_2023": prof,
                     "_doc": "the band's brightness over the lane's on NAIP 2023 z18, [1 m mean, p90] every 0.5 m about each "
                             "end (north_stripes_r5.py PROFILE); an end is the photo's where it steps, else the lidar's"},
            "in_m_raw_lidar": rec["in_m"], "in_m_p10_p90_raw_lidar": rec["in_m_p10_p90"],
            "out_m_invented": "the road's built lane edge: the lidar cannot place the paint's outer side (paint and verge "
                              "read alike) and the z18 photo does not resolve it",
            "photo": "naip_z18",
            "_source": ("ledger 0097 round 5: the north loop's own s (source/full/connectors.full.json); in_m the 2018 lidar's "
                        "intensity (r5_lidar_g10/north_stripes.json, photo frame), the ends the 2023 photo's where readable "
                        "(north_stripes_r5.py)")})
    K["kerbs"] += runs
    K["_doc_north_stripes"] = ("ledger 0097 round 5: the two runs with \"line\": \"full_north#0#0\" and \"profile\": \"paint\" "
                               "are the north loop's blue / yellow stripes (north_stripes_r5.py): in_m off the 2018 lidar, "
                               "out_m the built lane edge [invented], the ends the 2023 photo's where it reads them")
    (HERE / "kerbs.lm.json").write_text(json.dumps(K, indent=1, ensure_ascii=False), encoding="utf-8")
    for r in runs:
        print(f"[north stripes] {r['side']} s {r['s0']}-{r['s1']} ({r['ends']['s0']} / {r['ends']['s1']}), in_m {r['in_m']}, "
              f"out_m {r['out_m']} [invented], {len(r['edge_lonlat'])} edge points")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
