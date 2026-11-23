"""Phase 3 aerial lens: road-aligned NAIP 2022-04-25 crops at the width stations, for reading curb to curb by eye
(the method of source/expansion/aerial__widths_eye.csv), plus the automatic pavement read beside each one.

NAIP: last night's Mosaic tiles (tools/naip_carriageways.py's cache format, ca_m_3211716_sw_11_060_20220425, 0.6 m,
R G B NIR), read through tools/naip_carriageways.Mosaic with NAIP_OFFLINE=1 (never fetches).

Stations: every 150 m of each clockwise leg (EXPANSION-PHASE3-PLAN A4's stations) on the midline skeleton, its own
left normal (+ = left of the clockwise direction); plus each junction arm at ARM_AT_M out along its OSM way, and the
same-station re-reads of Phase 1's S2 / S3 readings (aerial__widths_eye.csv 'J2 arm Waring Road brg 228',
'J3 arm Mission Gorge Road brg 252').

Panel: ALONG_M along x ACROSS_M across at PX_M a pixel (nearest NAIP pixel), the road running left to right in the
reading's direction, its left at the top; ticks every 1 m on both margins, labels every 5 m; the automatic pavement
edges (naip_carriageways.classify, median over the panel's middle AUTO_ALONG_M) marked with red triangles.

    python -I p3x_crops.py <airoso> <naip-cache> <osm.expansion.json> <legs-dir> <out-dir>
"""
import json
import math
import os
import sys
from pathlib import Path

os.environ["NAIP_OFFLINE"] = "1"
ALONG_M = 60.0
ACROSS_M = 76.0     # the automatic read's span
HALF_VIEW = {"E": 24.0, "F": 16.0, "G": 26.0, "arm": 22.0}   # the panel's half width across, by piece
PX_M = 0.2
UPSCALE = 2         # the panel is drawn at PX_M / UPSCALE a pixel (bicubic), contrast stretched 2-98 %
AUTO_ALONG_M = 20.0
ARM_AT_M = 30.0
STEP_ST = 150.0
LABEL_H = 18
MARGIN = 34
NAMES = {"E": "P3-WAR", "F": "P3-ZION", "G": "P3-MG"}
P1_ARMS = [("J2 arm Waring Road brg 228 (S2 re-read)", 32.796914, -117.07642, "E"),
           ("J3 arm Mission Gorge Road brg 252 (S3 re-read)", 32.806516, -117.079583, "G")]


def main():
    airoso, cache, osm_p, legs_d, out = (Path(a) for a in sys.argv[1:6])
    sys.path.insert(0, str(airoso / "tools"))
    sys.path.insert(0, str(airoso))
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import author_expansion as ae
    import naip_carriageways as nc
    out.mkdir(parents=True, exist_ok=True)
    sk = json.loads((legs_d / "skeleton.west.json").read_text())
    mo = json.loads((legs_d / "mouths.west.raw.json").read_text())
    osm = json.loads(osm_p.read_text())
    nodes = {int(k): v for k, v in osm["nodes"].items()}
    ways = {w["id"]: w for w in osm["ways"]}
    origin = sk["frame"]["origin"]
    fr = ae.Frame(origin)
    mos = nc.Mosaic(origin, cache)
    xy = lambda n: fr.xz(*nodes[n][:2])
    try:
        font = ImageFont.load_default(size=13)
    except Exception:
        font = ImageFont.load_default()

    stations = []   # (label, key, x, z, tx, tz, ref line note)
    for lid, pc in sk["pieces"].items():
        rows = pc["stations"]
        P = [(r[1], r[2]) for r in rows]
        S = [r[0] for r in rows]
        k = 1
        while k * STEP_ST < S[-1] - 20:
            s = k * STEP_ST
            i = min(range(len(S)), key=lambda q: abs(S[q] - s))
            t = ae.tangent(P, i)
            stations.append((f"{NAMES[lid]} st {int(s)}", f"{lid}_st{int(s)}", P[i][0], P[i][1], t[0], t[1],
                             lid, S[i], "midline"))
            k += 1
    for lab, lat, lon, lid in P1_ARMS:
        p = fr.xz(lon, lat)
        rows = sk["pieces"][lid]["stations"]
        P = [(r[1], r[2]) for r in rows]
        d, s, latoff, seg = ae.project(p, P)
        i = min(range(len(rows)), key=lambda q: abs(rows[q][0] - s))
        t = ae.tangent(P, i)
        stations.append((lab, f"{lid}_p1arm", p[0], p[1], t[0], t[1], lid, round(s, 1), "Phase 1 reading point"))
    seen = set()
    for lid, recs in mo["mouths"].items():
        for r in recs:
            if r["kind"] not in ("junction_arm",) or r["junction"] not in ("J6", "J7"):
                continue
            key = (r["junction"], r["name"], round(r["bearing_deg"] / 30))
            if key in seen:
                continue
            seen.add(key)
            w = ways[r["way"]]["nodes"]
            i, j = w.index(r["node"]), w.index(r["next_node"])
            seq = w[i::1] if j > i else w[i::-1]
            P = [xy(n) for n in seq]
            sl = ae.arc(P)
            u = min(ARM_AT_M, sl[-1])
            q = ae.at_arc(P, sl, u)
            q2 = ae.at_arc(P, sl, min(sl[-1], u + 5.0))
            q0 = ae.at_arc(P, sl, max(0.0, u - 5.0))
            L = math.dist(q0, q2) or 1.0
            tx, tz = (q2[0] - q0[0]) / L, (q2[1] - q0[1]) / L
            brg = (math.degrees(math.atan2(tx, tz)) + 360) % 360
            stations.append((f"{r['junction']} arm {r['name']} brg {int(round(brg)):03d}",
                             f"{r['junction']}_arm_{int(round(brg)):03d}", q[0], q[1], tx, tz, lid, u,
                             f"OSM way {r['way']} at {u:.0f} m from node {r['node']}, outward"))

    if len(sys.argv) > 6:
        # extra-stations mode: [{label, key, lat, lon, heading_deg, half}] only (calibration / zooms)
        stations = []
        for e in json.loads(Path(sys.argv[6]).read_text()):
            x, z = fr.xz(e["lon"], e["lat"])
            h = math.radians(e["heading_deg"])
            HALF_VIEW[e["key"]] = float(e.get("half", 20.0))
            NAMES[e["key"]] = e.get("piece", "x")
            stations.append((e["label"], e["key"], x, z, math.sin(h), math.cos(h), e["key"], e.get("s", 0.0),
                             e.get("ref", "extra")))
    na, nx = int(ALONG_M / PX_M), int(ACROSS_M / PX_M)
    recs = []
    for lab, key, x, z, tx, tz, lid, s, ref in stations:
        nxv, nzv = -tz, tx                      # left normal
        us = (np.arange(na) + 0.5) * PX_M - ALONG_M / 2
        vs = ACROSS_M / 2 - (np.arange(nx) + 0.5) * PX_M          # top = left (+)
        U, V = np.meshgrid(us, vs)
        X = x + U * tx + V * nxv
        Z = z + U * tz + V * nzv
        px = mos.sample(X.ravel(), Z.ravel()).reshape(nx, na, 4)
        rgb = np.nan_to_num(px[:, :, :3], nan=0).clip(0, 255).astype(np.uint8)
        # automatic pavement read: classify the middle AUTO_ALONG_M, per offset the share of pavement
        mid = np.abs(us) <= AUTO_ALONG_M / 2
        cls, _mean = nc.classify(px[:, mid, :].reshape(-1, 4))
        cls = cls.reshape(nx, int(mid.sum()))
        share = (cls == 1).mean(axis=1)
        veg = (cls == 2).mean(axis=1)
        c0 = int(np.argmin(np.abs(vs)))
        pav = share >= 0.5
        # from the line outward, the pavement stops at the first BREAK of non-pavement rows
        brk = max(1, int(round(nc.BREAK_M / PX_M)))

        # divided pieces: read each side outward from its own OSM carriageway line (the midline sits in the median)
        sep = 0.0
        if lid in sk["pieces"] and ref == "midline":
            rr = min(sk["pieces"][lid]["stations"], key=lambda q: abs(q[0] - s))
            sep = rr[3] if rr[3] > 3.0 else 0.0
        start = {-1: int(np.argmin(np.abs(vs - sep / 2))), 1: int(np.argmin(np.abs(vs + sep / 2)))}

        def edge(direction):
            k = start[direction]
            run, last = 0, k
            while 0 <= k < nx:
                if pav[k]:
                    run, last = 0, k
                else:
                    run += 1
                    if run >= brk:
                        break
                k += direction
            return float(vs[last])
        hi_p, lo_p = edge(-1), edge(1)            # up the image = left (+)
        hv = HALF_VIEW[lid] if lid in HALF_VIEW and lid not in ("E", "F", "G") else (HALF_VIEW["arm"] if " arm " in lab else HALF_VIEW[lid])
        rows_v = np.abs(vs) <= hv
        sub = px[rows_v, :, :3]
        lo_c, hi_c = np.nanpercentile(sub, 0.5), np.nanpercentile(sub, 99.8)
        sub = np.nan_to_num((sub - lo_c) / max(1.0, hi_c - lo_c) * 255.0, nan=0).clip(0, 255).astype(np.uint8)
        im = Image.fromarray(sub, "RGB")
        im = im.resize((im.width * UPSCALE, im.height * UPSCALE), Image.BICUBIC)
        q = PX_M / UPSCALE
        W, H = im.width + 2 * MARGIN, im.height + LABEL_H
        canvas = Image.new("RGB", (W, H), (255, 255, 255))
        canvas.paste(im, (MARGIN, LABEL_H))
        d = ImageDraw.Draw(canvas)
        d.text((4, 2), f"{lab}  s {s:.0f}  (+ left of travel, up; 1 m ticks)", fill=(0, 0, 0), font=font)
        top = float(vs[rows_v][0]) + PX_M / 2
        for m in range(-int(hv), int(hv) + 1):
            yy = LABEL_H + (top - m) / q
            L = 12 if m % 5 == 0 else 6
            for x0 in (MARGIN - L, W - MARGIN):
                d.line([(x0, yy), (x0 + L, yy)], fill=(0, 0, 0), width=1)
            # the ruler strip in the middle of the panel: ticks pointing right from the panel's middle column
            xm = MARGIN + im.width // 2
            d.line([(xm, yy), (xm + (10 if m % 5 == 0 else 5), yy)], fill=(255, 255, 0) if m % 5 == 0 else
                   (255, 140, 0), width=1)
            if m % 5 == 0:
                d.text((1, yy - 6), f"{m:+d}", fill=(0, 0, 160), font=font)
                d.text((W - MARGIN + 13, yy - 6), f"{m:+d}", fill=(0, 0, 160), font=font)
                d.text((xm + 12, yy - 7), f"{m:+d}", fill=(255, 255, 0), font=font)
        d.line([(MARGIN + 8, LABEL_H + 8), (MARGIN + 48, LABEL_H + 8)], fill=(255, 255, 0), width=2)
        d.polygon([(MARGIN + 54, LABEL_H + 8), (MARGIN + 46, LABEL_H + 4), (MARGIN + 46, LABEL_H + 12)],
                  fill=(255, 255, 0))
        f = out / f"{key}.png"
        canvas.save(f)
        lon, lat = fr.lonlat(x, z)
        recs.append({"label": lab, "key": key, "piece": NAMES[lid], "s": round(s, 1), "lat": round(lat, 6),
                     "lon": round(lon, 6), "x": round(x, 2), "z": round(z, 2), "heading_deg":
                     round((math.degrees(math.atan2(tx, tz)) + 360) % 360, 1), "ref": ref,
                     "auto_left_m": round(hi_p, 1), "auto_right_m": round(lo_p, 1),
                     "auto_total_m": round(hi_p - lo_p, 1), "auto_from_sep_m": round(sep, 2), "file": f.name,
                     "veg_share_by_offset": None, "no_image": bool(np.isnan(px[:, :, 0]).all())})
        print(lab, "auto", round(hi_p, 1), round(lo_p, 1), round(hi_p - lo_p, 1), flush=True)
    (out / "crops.json").write_text(json.dumps({"what": "the eye-reading crops (p3x_crops.py)",
                                                "params": {"ALONG_M": ALONG_M, "ACROSS_M": ACROSS_M, "PX_M": PX_M,
                                                           "AUTO_ALONG_M": AUTO_ALONG_M, "ARM_AT_M": ARM_AT_M,
                                                           "classify": {"VEG_NDVI": nc.VEG_NDVI,
                                                                        "PAVE_NDVI": nc.PAVE_NDVI,
                                                                        "PAVE_SAT": nc.PAVE_SAT, "PAVE_MIN": nc.PAVE_MIN,
                                                                        "BREAK_M": nc.BREAK_M}},
                                                "missing_tiles": mos.missing, "stations": recs}, indent=1))


if __name__ == "__main__":
    main()
