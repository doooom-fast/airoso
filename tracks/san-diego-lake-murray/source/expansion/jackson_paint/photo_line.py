"""Jackson Dr north (piece D): the hatched median's RIGHT edge off the aerial, aligned to the lidar (ledger 0099 round 3,
item 4). Read-only; pure python + PIL.

    python -I photo_line.py <project> [--out jackson_right_edge.photo.json]

WHY. The G10's lidar intensity (jackson_intensity_D_full.lidar.g10.json; jackson_right_edge.lidar.g10.json, a second
look with a +-6 m window) reads the band's LEFT edge all along s 225-505, but its RIGHT edge only over s 245-312: past
s 312 that line is worn or smeared and the strongest returns in its window are the forward edge line itself. The
photo (NAIP 2022, 0.5 m, under the bake's registration) shows a line there in its mean brightness across the road.

WHAT. Per lidar station (piece D's own rows, + = left of J4 -> J5 travel), the photo's luminance averaged along the
road over +- 6 m [invented, the lidar's second look's window], every 0.125 m across u -5.25..-2.25; the photo's line =
the highest local maximum of that mean in u -5.0..-2.5 [invented: between the lidar's forward edge line, -5.2..-7.0,
and its band edges, -2.1..-3.7]. Where the lidar also reads the right edge (its full read: a line with along_share >=
0.5 in u -4.2..-2.8; s 245-299), photo minus lidar is recorded; its MEDIAN is the photo's offset from the lidar here,
and its spread is the photo's error (about +-1 m, measured: the file says).

The project must carry the aerial (track.config.json road_wear.aerial, the mosaic itself, not its LFS pointer) and the
bake's registration (data/road_wear.json stats.aerial.registration; a scratch workshop after its bake).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
LIDAR = HERE / "jackson_intensity_D_full.lidar.g10.json"
WIN_M = 6.0           # [invented] the along-road half window (the lidar's second look's)
U_SCAN = (-5.25, -2.25)
U_PEAK = (-5.0, -2.5)  # [invented] where the photo's line is looked for
LIDAR_R = (-4.2, -2.8)  # the lidar's right edge, where its full read has it
ALONG_MIN = 0.5


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    proj = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else HERE / "jackson_right_edge.photo.json"
    Image.MAX_IMAGE_PIXELS = None
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    aer = cfg["road_wear"]["aerial"]
    reg = json.loads((proj / "data" / "road_wear.json").read_text(encoding="utf-8"))["stats"]["aerial"]["registration"]
    o = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    phi = math.radians(o["lat"])
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    img = Image.open(proj / aer["image"]).convert("RGB")
    aw, ah = img.size
    px = img.load()
    Wb, Sb, Eb, Nb = aer["bbox_lonlat"]
    d = json.loads((proj / "data" / "expansion.north.json").read_text(encoding="utf-8"))
    D = [p for p in d["pieces"] if p.get("id") == "D"][0]
    st = [dict(zip(D["columns"], r)) for r in D["stations"]]
    S0, dS = st[0]["s"], st[1]["s"] - st[0]["s"]

    def at(s):
        k = max(1, min(len(st) - 1, int((s - S0) / dS) + 1))
        a, b = st[k - 1], st[k]
        t = (s - a["s"]) / (b["s"] - a["s"])
        tx, tz = b["x"] - a["x"], b["z"] - a["z"]
        L = math.hypot(tx, tz) or 1.0
        return a["x"] + tx * t, a["z"] + tz * t, -tz / L, tx / L

    def lum(x, y):
        lon = o["lon"] + (x + reg["dx_m"]) / m_lon
        lat = o["lat"] + (y + reg["dy_m"]) / m_lat
        u = (lon - Wb) / (Eb - Wb) * aw - 0.5
        v = (Nb - lat) / (Nb - Sb) * ah - 0.5
        i, j = int(math.floor(u)), int(math.floor(v))
        if not (0 <= i < aw - 1 and 0 <= j < ah - 1):
            return None
        fu, fv = u - i, v - j
        c = 0.0
        for ii, jj, w in ((i, j, (1 - fu) * (1 - fv)), (i + 1, j, fu * (1 - fv)), (i, j + 1, (1 - fu) * fv), (i + 1, j + 1, fu * fv)):
            q = px[ii, jj]
            c += w * (0.2126 * q[0] + 0.7152 * q[1] + 0.0722 * q[2])
        return c / 255.0

    lid = json.loads(LIDAR.read_text(encoding="utf-8"))["stations"]
    rows = []
    for r in lid:
        s = float(r["s"])
        if s > 510.0:
            continue
        prof, u = [], U_SCAN[0]
        while u <= U_SCAN[1] + 1e-9:
            vals, t = [], -WIN_M
            while t <= WIN_M + 1e-9:
                x, z, nx, nz = at(s + t)
                v = lum(x + nx * u, z + nz * u)
                if v is not None:
                    vals.append(v)
                t += 0.5
            prof.append((round(u, 3), sum(vals) / len(vals)))
            u += 0.125
        pk = [prof[k] for k in range(1, len(prof) - 1) if prof[k][1] >= prof[k - 1][1] and prof[k][1] >= prof[k + 1][1]
              and U_PEAK[0] <= prof[k][0] <= U_PEAK[1]]
        lr = [l for l in r["lines"] if LIDAR_R[0] <= l["u"] <= LIDAR_R[1] and l.get("along_share", 0) >= ALONG_MIN]
        rows.append({"s": s, "photo_u": max(pk, key=lambda p: p[1])[0] if pk else None,
                     "lidar_u": round(max(lr, key=lambda l: l["peak_over_median"])["u"], 3) if lr else None})
    diffs = sorted(x["photo_u"] - x["lidar_u"] for x in rows if x["photo_u"] is not None and x["lidar_u"] is not None)
    med = diffs[len(diffs) // 2] if diffs else None
    doc = {"_doc": __doc__.split("\n\n")[0] + " See photo_line.py for the method; every window is [invented].",
           "aerial": aer["image"], "registration": reg, "window_m": WIN_M, "u_peak": list(U_PEAK), "lidar_right_window": list(LIDAR_R),
           "photo_minus_lidar": {"stations": len(diffs), "median_m": round(med, 3) if med is not None else None,
                                 "min_m": round(diffs[0], 3) if diffs else None, "max_m": round(diffs[-1], 3) if diffs else None},
           "rows": rows}
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"[photo-line] {len(rows)} stations, the photo's line at {sum(1 for x in rows if x['photo_u'] is not None)}; photo minus "
          f"lidar over {len(diffs)}: median {med:+.2f} m, {diffs[0]:+.2f}..{diffs[-1]:+.2f} -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
