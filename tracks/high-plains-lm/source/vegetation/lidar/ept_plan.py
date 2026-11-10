"""EPT read plan for a lon/lat box (ledger 0089): every node of every depth whose cube meets the box, its point count and
its LAZ byte size (HTTP HEAD). Hierarchy JSONs are saved under <dl>/hier/. Usage: ept_plan.py <dl-dir> <ept-url-base> w s e n"""
import json, math, sys, ssl, urllib.request
from pathlib import Path
dl, base = Path(sys.argv[1]), sys.argv[2].rstrip("/")
w, s, e, n = map(float, sys.argv[3:7])
R = 6378137.0
mx = lambda lon: math.radians(lon) * R
my = lambda lat: R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
bx0, by0, bx1, by1 = mx(w), my(s), mx(e), my(n)
ept = json.loads((dl / "ept.json").read_text())
B = ept["bounds"]
(dl / "hier").mkdir(exist_ok=True)
def get(url, head=False):
    req = urllib.request.Request(url, method="HEAD" if head else "GET")
    with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as r:
        return int(r.headers["Content-Length"]) if head else r.read()
def hier(key):
    p = dl / "hier" / f"{key}.json"
    if not p.exists():
        p.write_bytes(get(f"{base}/ept-hierarchy/{key}.json"))
    return json.loads(p.read_text())
def cube(d, x, y, z):
    sx = (B[3] - B[0]) / 2 ** d; sy = (B[4] - B[1]) / 2 ** d
    return B[0] + x * sx, B[1] + y * sy, B[0] + (x + 1) * sx, B[1] + (y + 1) * sy
nodes = {}
H = {}
def walk(d, x, y, z):
    x0, y0, x1, y1 = cube(d, x, y, z)
    if x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1:
        return
    key = f"{d}-{x}-{y}-{z}"
    if key not in H:
        return
    c = H[key]
    if c == -1:
        H.update(hier(key)); c = H[key]
    if c > 0:
        nodes[key] = c
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz)
H.update(hier("0-0-0-0"))
walk(0, 0, 0, 0)
tot = 0
plan = []
for k in sorted(nodes, key=lambda k: [int(v) for v in k.split("-")]):
    b = get(f"{base}/ept-data/{k}.laz", head=True); tot += b
    plan.append({"key": k, "points": nodes[k], "bytes": b})
(dl / "plan.json").write_text(json.dumps({"box_lonlat": [w, s, e, n], "nodes": plan, "bytes": tot}, indent=0))
print(f"{len(plan)} nodes, {sum(p['points'] for p in plan):,} points (whole nodes), {tot/1e6:.1f} MB; deepest {max(int(p['key'].split('-')[0]) for p in plan)}")
