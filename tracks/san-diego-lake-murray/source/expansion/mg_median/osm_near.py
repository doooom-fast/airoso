"""The OSM ways at a station of a declared median, read off the track's own extract (pure Python; reads only).

    python -I osm_near.py <airoso> <island id> <s> [--radius 70] [--out <json>]

The extract is tracks/san-diego-lake-murray/data/osm.expansion.json ({"nodes": {id: [lon, lat]}, "ways": [{id, nodes,
tags}], "node_tags": {id: tags}}). The station is the middle of the island's declared band there (data/expansion.north.json
medians[].polygon_xz: side A's stations, then side B's reversed, 2.5 m apart), taken to lon / lat with the WGS84
metres-per-degree series of scripts/geometry/projection.py about the plan's frame.origin. For every highway way with a
segment within the radius: its distance, its nearer end's distance, its length, and the bearing it leaves on (over its
first 40 m from the end nearer the point). Tagged nodes within the radius are listed too (a signal, a crossing)."""
import json
import math
import sys
from pathlib import Path

air, mid, s = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])
rad = float(sys.argv[sys.argv.index("--radius") + 1]) if "--radius" in sys.argv else 70.0
outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
LM = air / "tracks" / "san-diego-lake-murray"
e = json.loads((LM / "data" / "expansion.north.json").read_text(encoding="utf-8"))
m = next(x for x in e["medians"] if x["id"] == mid)
ring = m["polygon_xz"]
n = len(ring) // 2
k = int(round((s - m["s_from"]) / ((m["s_to"] - m["s_from"]) / (n - 1))))
a, b = ring[k], ring[2 * n - 1 - k]
cx, cz = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
o = e["frame"]["origin"]
lat0, lon0 = float(o["lat"]), float(o["lon"])
phi = math.radians(lat0)
m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
osm = json.loads((LM / "data" / "osm.expansion.json").read_text(encoding="utf-8"))
nodes = osm["nodes"]


def loc(nid):
    lon, lat = nodes[str(nid)]
    return (lon - lon0) * m_lon - cx, (lat - lat0) * m_lat - cz      # metres east / north of the point


ways = []
for w in osm["ways"]:
    tags = w.get("tags") or {}
    if "highway" not in tags:
        continue
    ids = [i for i in w.get("nodes", []) if str(i) in nodes]
    pts = [loc(i) for i in ids]
    best = None
    for i in range(len(pts) - 1):
        (x1, z1), (x2, z2) = pts[i], pts[i + 1]
        dx, dz = x2 - x1, z2 - z1
        t = max(0.0, min(1.0, (-x1 * dx - z1 * dz) / (dx * dx + dz * dz or 1e-9)))
        dd = math.hypot(x1 + t * dx, z1 + t * dz)
        best = dd if best is None or dd < best else best
    if best is None or best > rad:
        continue
    if math.hypot(*pts[-1]) < math.hypot(*pts[0]):
        pts, ids = pts[::-1], ids[::-1]
    length = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
    acc, j = 0.0, 0
    while j + 1 < len(pts) and acc < 40.0:
        acc += math.hypot(pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1])
        j += 1
    brg = (math.degrees(math.atan2(pts[j][0] - pts[0][0], pts[j][1] - pts[0][1])) + 360.0) % 360.0
    ways.append({"way": w["id"], "distance_m": round(best, 1), "nearer_end_m": round(math.hypot(*pts[0]), 1),
                 "nearer_end_node": ids[0], "length_m": round(length), "leaves_on_bearing_deg": round(brg),
                 "tags": {t: tags[t] for t in ("highway", "name", "lanes", "oneway", "access", "service", "surface", "maxspeed") if t in tags}})
ways.sort(key=lambda r: (r["distance_m"], r["way"]))
tagged = sorted(({"node": int(nid), "distance_m": round(math.hypot(*loc(nid)), 1), "tags": t}
                 for nid, t in (osm.get("node_tags") or {}).items() if str(nid) in nodes and math.hypot(*loc(nid)) <= rad),
                key=lambda r: r["distance_m"])
rep = {"_doc": "osm_near.py: the OSM highway ways within %g m of the middle of %s's declared band at s %g" % (rad, mid, s),
       "extract": {"file": "data/osm.expansion.json", "osm_base": osm.get("osm_base"), "source": osm.get("source")},
       "point": {"island": mid, "s": s, "local_x_m": round(cx, 1), "local_z_m": round(cz, 1),
                 "lat": round(lat0 + cz / m_lat, 6), "lon": round(lon0 + cx / m_lon, 6)},
       "ways": ways, "tagged_nodes": tagged}
print(json.dumps(rep["point"]))
for r in ways:
    print("  %6.1f m  way %-10s end %5.1f m  %5d m long  leaves %3d deg  %s" % (
        r["distance_m"], r["way"], r["nearer_end_m"], r["length_m"], r["leaves_on_bearing_deg"], json.dumps(r["tags"])))
print("  tagged nodes within %g m: %d" % (rad, len(tagged)), [t["tags"] for t in tagged][:6])
if outp:
    Path(outp).write_text(json.dumps(rep, indent=1), encoding="utf-8")
