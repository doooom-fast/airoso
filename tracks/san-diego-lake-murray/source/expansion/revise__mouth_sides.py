"""Distance from the loop's outer (L) edge to the straight-through road's continuing curb line at J1 and J5."""
import json, math, runpy, sys
S = r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/expansion"
D = r"C:/Users/Owner/Documents/GitHub/k10-sd-v021/project/data"
O = {"lon": -117.04666413020487, "lat": 32.78835571285328}
p = math.radians(O["lat"]); ML = 111132.92 - 559.82 * math.cos(2 * p); MO = 111412.84 * math.cos(p) - 93.5 * math.cos(3 * p)
loc = lambda lon, lat: ((lon - O["lon"]) * MO, (lat - O["lat"]) * ML)
cl = json.load(open(D + "/centerline.local.json")); P = cl["points_xyz_m"]; W = cl["widths_m"]
def edge(v):
    a, b = P[v - 1], P[v + 1]; dx, dz = b[0] - a[0], b[2] - a[2]; L = math.hypot(dx, dz)
    return (P[v][0] - dz / L * W[v] / 2, P[v][2] + dx / L * W[v] / 2)
g = json.load(open(S + "/routes/legs.geojson"))
F = {(f["properties"]["leg"], f["properties"]["sense"]): [loc(*c) for c in f["geometry"]["coordinates"]] for f in g["features"]}
def line_from(pts, d0, d1):
    # point at arc d0 and d1
    cum = [0];
    for a, b in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a, b))
    def at(s):
        for i in range(len(cum) - 1):
            if cum[i + 1] >= s:
                t = (s - cum[i]) / ((cum[i + 1] - cum[i]) or 1); a, b = pts[i], pts[i + 1]
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return at(d0), at(d1)
def signed_dist(pt, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz)
    return ((pt[0] - a[0]) * dz - (pt[1] - a[1]) * dx) / L  # >0 = right of a->b
# J1: Waring midline from fwd/rev, SW curb = 13.25 m left of outbound direction
wf = F[("W", "fwd")]; wr = F[("W", "rev")]
a1, b1 = line_from(wf, 15, 60); a2, b2 = line_from(wr[::-1], 15, 60)
a = ((a1[0] + a2[0]) / 2, (a1[1] + a2[1]) / 2); b = ((b1[0] + b2[0]) / 2, (b1[1] + b2[1]) / 2)
print("J1: loop L edge vs Waring SW curb line (13.25 m left of the Waring midline); + = edge is right of the curb line (inside Waring)")
for v in range(1500, 1522):
    print(f"  v{v}: {signed_dist(edge(v), a, b) + 13.25:+6.1f} m")
# J5: Jackson north from rev sense (starts at J5), NE curb 12 m right of the outbound (NW) direction
jr = F[("J", "rev")]
a, b = line_from(jr, 10, 50)
print("J5: loop L edge vs Jackson-north NE curb line (12 m right of its centre); 0 = on the line")
for v in range(2310, 2340):
    print(f"  v{v}: {signed_dist(edge(v), a, b) - 12.0:+6.1f} m   edge {tuple(round(c,1) for c in edge(v))}")
print("Jackson-north SW curb line (12 m left):")
for v in range(2306, 2320):
    print(f"  v{v}: {signed_dist(edge(v), a, b) + 12.0:+6.1f} m")
