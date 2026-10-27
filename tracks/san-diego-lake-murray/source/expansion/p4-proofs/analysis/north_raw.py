import json, math, sys
from collections import Counter
PROJ = sys.argv[1]
cl = json.load(open(PROJ + "/data/centerline.local.json", encoding="utf-8"))
o = cl["origin"]; lon0, lat0 = o["lon"], o["lat"]
m_lon = 111320.0 * math.cos(math.radians(lat0)); m_lat = 110574.0
conns = json.load(open(PROJ + "/data/connectors.local.json", encoding="utf-8"))["connectors"]
new = json.load(open(PROJ + "/data/buildings.expansion.cache.json", encoding="utf-8"))
north = {c["name"]: [(p[0], p[2]) for p in c["points_xyz_m"]][::2] for c in conns if c["name"].startswith("north_")}
def dist(pts, x, z):
    return min(math.hypot(x - a, z - b) for a, b in pts)
by_piece = Counter(); by_type = Counter(); small = 0; areas = []
for b in new:
    if b.get("building") == "roof":
        continue
    foot = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in b["geom"]]
    if foot and foot[0] == foot[-1]:
        foot = foot[:-1]
    if len(foot) < 3:
        continue
    cx = sum(p[0] for p in foot) / len(foot); cz = sum(p[1] for p in foot) / len(foot)
    area = abs(sum(foot[i][0] * foot[(i + 1) % len(foot)][1] - foot[(i + 1) % len(foot)][0] * foot[i][1] for i in range(len(foot)))) / 2
    best = None
    for n, pts in north.items():
        d = dist(pts, cx, cz)
        if d <= 120 and (best is None or d < best[0]):
            best = (d, n)
    if best:
        by_piece[best[1]] += 1; by_type[b.get("building")] += 1; areas.append(area)
        if area < 25:
            small += 1
print("raw footprints within 120 m of a north piece:", sum(by_piece.values()), dict(by_piece))
print("by type:", by_type.most_common(10), "under 25 m2:", small, "largest m2:", sorted(areas)[-5:])
