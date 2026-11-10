"""Milford furniture inventory (ledger 0082): NAIP 2022 pixel reads -> lon/lat polylines, lengths, offsets from the traced
pavement edge, lap stations. The pixel vertices are read by eye off zoomed crops with a labelled source-pixel grid
(grid.py); the frame is source/naip_2022_mrc.jpg on its TRUE extent (ledger 0062).

inventory.py <repo> <out.json>
"""
import json, math, sys
REPO, OUT = sys.argv[1:3]
LON0, LAT0, LON1, LAT1 = -83.67, 42.56050328638498, -83.657, 42.57949671361502
W, H = 2130, 3112
def ll(px, py):   # pixel centre -> lon/lat
    return (LON0 + (px + 0.5) / W * (LON1 - LON0), LAT1 - (py + 0.5) / H * (LAT1 - LAT0))
lat_c = 42.5700
MLON = 111320.0 * math.cos(math.radians(lat_c)); MLAT = 110540.0
def m(p): return (p[0] * MLON, p[1] * MLAT)

g = json.load(open(f"{REPO}/tracks/milford-road-course/data/centerline.geojson"))["features"][0]
co = [m(c) for c in g["geometry"]["coordinates"]]; wd = g["properties"]["widths_m"]
S = [0.0]
for a, b in zip(co, co[1:]):
    S.append(S[-1] + math.dist(a, b))

def nearest(q):
    best = None
    for i in range(len(co) - 1):
        a, b = co[i], co[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2))
        px, py = a[0] + dx * t, a[1] + dy * t
        d = math.hypot(q[0] - px, q[1] - py)
        if best is None or d < best[0]:
            side = "L" if dx * (q[1] - a[1]) - dy * (q[0] - a[0]) > 0 else "R"
            w = wd[i] + (wd[i + 1] - wd[i]) * t if i + 1 < len(wd) else wd[i]
            best = (d, S[i] + math.sqrt(L2) * t, side, w)
    return best

ITEMS = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
rows = []
for it in ITEMS:
    out = dict(it)
    if "px" in it:
        pl = [ll(*p) for p in it["px"]]
        out["polyline_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in pl]
        mm = [m(p) for p in pl]
        out["length_m"] = round(sum(math.dist(a, b) for a, b in zip(mm, mm[1:])), 1)
        near = [nearest(q) for q in mm]
        offs = [n[0] - n[3] / 2 for n in near]
        out["edge_offset_m"] = [round(min(offs), 1), round(max(offs), 1)]
        out["lap_s_m"] = [round(min(n[1] for n in near)), round(max(n[1] for n in near))]
        out["side"] = "".join(sorted({n[2] for n in near}))
    if "px_ring" in it:
        pl = [ll(*p) for p in it["px_ring"]]
        out["footprint_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in pl]
        mm = [m(p) for p in pl]
        out["sides_m"] = [round(math.dist(mm[i], mm[(i + 1) % len(mm)]), 1) for i in range(len(mm))]
        n = nearest(((mm[0][0] + mm[2][0]) / 2, (mm[0][1] + mm[2][1]) / 2))
        out["edge_offset_m"] = round(n[0] - n[3] / 2, 1)
        out["lap_s_m"] = round(n[1])
    rows.append(out)
json.dump({"frame": "NAIP 2022-08-16 tile m_4208327_ne_17_060_20220816 as source/naip_2022_mrc.jpg, true extent "
                     "lon -83.6700..-83.6570, lat 42.56050..42.57950, 2130 x 3112 px (0.53 m E-W x 0.68 m N-S)",
           "items": rows}, open(OUT, "w"), indent=1)
for r in rows:
    print(r["id"], r["kind"], r.get("length_m", r.get("sides_m")), "edge", r.get("edge_offset_m"), "s", r.get("lap_s_m"), r.get("side", ""))
