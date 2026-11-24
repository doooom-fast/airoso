"""The merge's west corner from a second source (ledger 0097 round 5, item 4): the 2018 lidar reads its asphalt edge at
R 6.75 m (r5_lidar_g10/carried_edges.json merge.west_corner); round 4 built it at NAIP's R 14.0 m (mouth_radii.naip.json).
Which outline does the pavement follow on the 2023 aerial?

    python -I check_west_corner_r5.py <repo> [--still <out.jpg>]   (numpy + Pillow; writes west_corner_r5.json beside itself)

  photo    NAIP 2023-09-28, the 0.3 m crop (source/road_wear/naip_2023_030_hp.png; road wear's mosaic, round 4's, holds these
           pixels unchanged in its bottom rows, so one read serves both)
  frame    the lidar's points moved into the photo's frame by the registration's measured shift (carried_edges.json
           registration: the 2018 lidar against the 2023 photo, -0.24 E / -0.04 N m)
  rays     from the lidar's corner point K across the wedge (23 rays between its two tangent directions): the photo's asphalt
           ends where measure_widths' groundness (0.5 m running mean) first reaches the midpoint between the West lap's lane
           (4 m south of the built K, 10 m along) and the prairie 1.5-5 m past the 14.0 m arc, the threshold rule
           measure_pads.py used for the FORK pad's outline; each ray's distance against both arcs
  regions  groundness in the lidar's fillet, between the two arcs, in the lane and on the prairie
round 4's 14.0 m return is its build's own (data/mouth_returns.json of an empty-workshop build of 0.1.12, main d31cb9a8):
R14 below. --still draws the lidar's outline, both arcs and the photo's read edge over the crop, the mosaic and the z18 photo.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure_widths as mw  # noqa: E402

R14 = {"K": [-99.126, 148.549], "A": [-116.217, 149.176], "B": [-101.89, 165.427], "O": [-115.704, 163.165], "R": 14.0,
       "_src": "0.1.12's build (main d31cb9a8, empty workshop, Mac): data/mouth_returns.json full_north#0#0|end|-1"}
RAYS = 23
SMOOTH_PX = 5                   # the 0.5 m running mean (0.1 m samples)


def in_tri(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def ray_circle(K, u, O, R):
    d = K - O
    b = 2 * float(np.dot(u, d))
    c = float(np.dot(d, d)) - R * R
    disc = b * b - 4 * c
    if disc < 0:
        return None
    t = (-b - math.sqrt(disc)) / 2
    return t if t > 0 else None


def main(repo: Path, still=None):
    P = repo / "tracks" / "high-plains-lm"
    origin = json.loads((P / "data" / "centerline.raw.local.json").read_text(encoding="utf-8"))["origin"]
    meta = json.loads((P / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    crop = mw.Naip(P / "source" / "road_wear" / "naip_2023_030_hp.png", meta, origin)
    car = json.loads((HERE / "r5_lidar_g10" / "carried_edges.json").read_text(encoding="utf-8"))
    wc = car["merge"]["west_corner"]
    sh = car["registration"]["fit"]["shift_E_N_m"]

    def ph(E, N):
        return np.array([E - sh[0], N - sh[1]])
    f = wc["fit"]
    O6 = ph(f["centre"]["E"], f["centre"]["N"])
    A6 = ph(f["tangent_on_west_lap_edge"]["E"], f["tangent_on_west_lap_edge"]["N"])
    B6 = ph(f["tangent_on_ladder_edge"]["E"], f["tangent_on_ladder_edge"]["N"])
    K6 = ph(*wc["Kreal"])
    R6 = float(wc["asphalt_edge_radius_m"])
    K14, A14, B14, O14 = (np.array(R14[k]) for k in ("K", "A", "B", "O"))
    E0, E1, N0, N1 = -125.0, -92.0, 140.0, 172.0
    EE, NN = np.meshgrid(np.arange(E0, E1, 0.15), np.arange(N0, N1, 0.15))
    V = crop.rgb(EE, NN)
    G = mw.groundness(V)
    pts = np.stack([EE, NN], axis=-1)
    tri6 = np.array([[in_tri(p, K6, A6, B6) for p in row] for row in pts])
    tri14 = np.array([[in_tri(p, K14, A14, B14) for p in row] for row in pts])
    d6 = np.hypot(EE - O6[0], NN - O6[1])
    d14 = np.hypot(EE - O14[0], NN - O14[1])
    f6 = tri6 & (d6 > R6)
    f14 = tri14 & (d14 > R14["R"])
    band = f14 & ~f6
    prairie = (d14 > R14["R"] - 5.0) & (d14 < R14["R"] - 1.5) & ~tri14
    lane = (np.abs(NN - (K14[1] - 4.0)) < 1.0) & (EE > K14[0] - 12.0) & (EE < K14[0] - 2.0)

    def st(m):
        return {"px": int(m.sum()), "groundness_p10_p50_p90": [round(float(np.nanpercentile(G[m], q)), 1) for q in (10, 50, 90)],
                "share_at_ground_level_30": round(float(np.nanmean(G[m] >= 30.0)), 2)}
    regions = {"the West lap's lane": st(lane), "the lidar's 6.75 m fillet": st(f6), "between the 6.75 and 14.0 m arcs": st(band),
               "the prairie 1.5-5 m past the 14.0 m arc": st(prairie)}
    thr = (regions["the West lap's lane"]["groundness_p10_p50_p90"][1]
           + regions["the prairie 1.5-5 m past the 14.0 m arc"]["groundness_p10_p50_p90"][1]) / 2
    a0 = math.atan2(A6[1] - K6[1], A6[0] - K6[0])
    b0 = math.atan2(B6[1] - K6[1], B6[0] - K6[0])
    db = (b0 - a0 + math.pi) % (2 * math.pi) - math.pi
    o = np.arange(0.0, 16.0, 0.1)
    rays = []
    for k in range(1, RAYS + 1):
        th = a0 + db * k / (RAYS + 1)
        u = np.array([math.cos(th), math.sin(th)])
        g = np.convolve(mw.groundness(crop.rgb(K6[0] + u[0] * o, K6[1] + u[1] * o)), np.ones(SMOOTH_PX) / SMOOTH_PX, mode="same")
        hit = next((float(o[i]) for i in range(2, len(o) - 2) if g[i] >= thr), None)
        t6, t14 = ray_circle(K6, u, O6, R6), ray_circle(K6, u, O14, R14["R"])
        rays.append({"theta_deg": round(math.degrees(th), 1), "photo_edge_m": None if hit is None else round(hit, 2),
                     "arc_6_75_m": None if t6 is None else round(t6, 2), "arc_14_0_m": None if t14 is None else round(t14, 2),
                     "E_N": None if hit is None else [round(float(K6[0] + u[0] * hit), 2), round(float(K6[1] + u[1] * hit), 2)]})
    ok = [r for r in rays if r["photo_edge_m"] is not None and r["arc_6_75_m"] and r["arc_14_0_m"]]
    q6 = np.array([r["photo_edge_m"] - r["arc_6_75_m"] for r in ok])
    q14 = np.array([r["photo_edge_m"] - r["arc_14_0_m"] for r in ok])
    out = {"_doc": __doc__.split("\n\n")[0], "threshold_groundness": round(thr, 2), "regions": regions,
           "rays": {"n": len(rays), "read": len(ok),
                    "photo_minus_6_75_p10_p50_p90_m": [round(float(np.percentile(q6, q)), 2) for q in (10, 50, 90)],
                    "photo_minus_14_0_p10_p50_p90_m": [round(float(np.percentile(q14, q)), 2) for q in (10, 50, 90)],
                    "rows": rays},
           "K_lidar_photo_frame": [round(float(v), 2) for v in K6], "R14_round4_built": R14,
           "verdict": ("the 2023 photo's asphalt follows the lidar's outline (R 6.75 m); the 14.0 m arc bounds a tan apron the "
                       "photo reads as ground: rebuild the corner at the lidar's radius")}
    (HERE / "west_corner_r5.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[west corner] threshold {thr:.1f}; {len(ok)}/{len(rays)} rays: photo - 6.75 arc p50 {np.median(q6):+.2f} m, "
          f"photo - 14.0 arc p50 {np.median(q14):+.2f} m; between the arcs groundness p50 "
          f"{regions['between the 6.75 and 14.0 m arcs']['groundness_p10_p50_p90'][1]}")
    if still:
        draw_still(repo, P, origin, wc, ph, O6, A6, B6, R6, (K14, A14, B14, O14), ok, Path(still))


def draw_still(repo, P, origin, wc, ph, O6, A6, B6, R6, r14, ok, out):
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(P / "source" / "full"))
    import measure_north as mn
    m_lon, m_lat = mw.mpd(origin["lat"])
    E0, E1, N0, N1 = -124.0, -90.0, 138.0, 172.0
    mpp = 0.05
    EE, NN = np.meshgrid(np.arange(E0, E1, mpp), np.arange(N1, N0, -mpp))
    meta = json.loads((P / "source" / "road_wear" / "naip_2023_030_hp.json").read_text(encoding="utf-8"))
    mos_meta = json.loads((P / "source" / "road_wear" / "naip_2023_hp_mosaic.json").read_text(encoding="utf-8"))
    crop = mw.Naip(P / "source" / "road_wear" / "naip_2023_030_hp.png", meta, origin)
    mos = mw.Naip(P / "source" / "road_wear" / "naip_2023_hp_mosaic.png", mos_meta, origin)
    z18, _n = mn.z18_reader(repo)
    panels = [("NAIP 2023-09-28 0.3 m (the 2023 aerial)", crop.rgb(EE, NN)),
              ("round 4's road-wear mosaic (its bottom rows = the crop)", mos.rgb(EE, NN)),
              ("NAIP 2023 z18 tiles (0.46 m)", z18(origin["lon"] + EE / m_lon, origin["lat"] + NN / m_lat))]
    K14, A14, B14, O14 = r14

    def px(p):
        return ((p[0] - E0) / mpp, (N1 - p[1]) / mpp)

    def arc(d, O, A, B, R, col):
        t0 = math.atan2(A[1] - O[1], A[0] - O[0]); t1 = math.atan2(B[1] - O[1], B[0] - O[0])
        dt = (t1 - t0 + math.pi) % (2 * math.pi) - math.pi
        d.line([px((O[0] + R * math.cos(t0 + dt * k / 80), O[1] + R * math.sin(t0 + dt * k / 80))) for k in range(81)],
               fill=col, width=3)
    ims = []
    for title, V in panels:
        im = Image.fromarray(np.nan_to_num(V).clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        arc(d, O14, A14, B14, 14.0, (0, 230, 255))
        arc(d, O6, A6, B6, R6, (255, 40, 40))
        for o in wc["outline"]:
            if o.get("kept"):
                x, y = px(ph(o["E"], o["N"]))
                d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 160, 0), width=2)
        for r in ok:
            x, y = px(r["E_N"])
            d.rectangle([x - 3, y - 3, x + 3, y + 3], outline=(60, 255, 60), width=2)
        d.rectangle([0, 0, im.width, 34], fill=(0, 0, 0))
        d.text((6, 4), title, fill=(255, 255, 255))
        d.text((6, 18), "orange: lidar asphalt edge (photo frame)  red: lidar R 6.75 m  cyan: 0.1.12's built R 14.0 m  "
               "green: the photo's asphalt end per ray", fill=(255, 255, 255))
        for e in range(int(math.ceil(E0 / 5)) * 5, int(E1) + 1, 5):
            d.line([px((e, N0))[0], im.height - 10, px((e, N0))[0], im.height], fill=(255, 255, 255))
        ims.append(im)
    W = sum(i.width for i in ims) + 20
    canvas = Image.new("RGB", (W, ims[0].height + 24), (0, 0, 0))
    xx = 0
    for i in ims:
        canvas.paste(i, (xx, 0))
        xx += i.width + 10
    ImageDraw.Draw(canvas).text((6, ims[0].height + 6), "the merge's west corner, E -124..-90 / N 138..172 m (track frame), "
                                "ticks every 5 m E; ledger 0097 round 5 item 4", fill=(255, 255, 255))
    canvas.save(out, quality=90)
    print(f"[west corner] still {out} {canvas.size}")


if __name__ == "__main__":
    a = sys.argv[1:]
    still = a[a.index("--still") + 1] if "--still" in a else None
    main(Path(a[0]).resolve(), still)
