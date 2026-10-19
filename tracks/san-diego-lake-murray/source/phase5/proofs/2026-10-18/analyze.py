"""analyze.py <project> <tris.json> : the phase-5 verifier's four cosmetic notes, measured on a BUILT gate OBJ extract
(extract.py) of a demo run:
  grass   per corner: 1GRASS triangles steeper than 45 deg within R + 5 m of K (and their max rise); grass standing over a
          1KERB surface (a poke through the walk / verge) within R + 5 m
  notch   per corner: 1KERB triangles whose plan winding disagrees with the majority (a folded strip) within R + 5 m;
          the lowest grass point within 0.75 R of the return's centre O vs the walk around it (a pit)
  paint   per stub: painted strips (MARKINGS / YLINE) on the stub's own road, by lateral offset (a divider at |lat| ~ 3.65
          m = the doubled edge line) and the farthest paint along the stub vs the barrier's road-side toe
  joints  per barrier: the stations across it where the barrier's top dips under 1.15 m (Kevin's module's end chamfer)
"""
import json, math, sys
from collections import Counter

proj, tj = sys.argv[1], sys.argv[2]
T = json.load(open(tj))["tris"]
plan = {s["id"]: s for s in json.load(open(proj + "/data/stubs.plan.json", encoding="utf-8"))["stubs"]}
built = json.load(open(proj + "/data/stubs.built.json", encoding="utf-8"))
out = {"stubs": {}}


def slope_rise(a, b, c):
    ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]; vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
    nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
    nl = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
    return abs(ny)/nl, max(a[1], b[1], c[1]) - min(a[1], b[1], c[1])


def h_at(x, z, a, b, c):
    d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
    if abs(d) < 1e-12: return None
    l1 = ((b[2]-c[2])*(x-c[0]) + (c[0]-b[0])*(z-c[2]))/d; l2 = ((c[2]-a[2])*(x-c[0]) + (a[0]-c[0])*(z-c[2]))/d
    l3 = 1-l1-l2
    return None if min(l1, l2, l3) < -1e-7 else l1*a[1]+l2*b[1]+l3*c[1]


CELL = 1.0
grid = {}
for i, (n, a, b, c) in enumerate(T):
    xs = [a[0], b[0], c[0]]; zs = [a[2], b[2], c[2]]
    for ix in range(int(math.floor(min(xs)/CELL)), int(math.floor(max(xs)/CELL))+1):
        for iz in range(int(math.floor(min(zs)/CELL)), int(math.floor(max(zs)/CELL))+1):
            grid.setdefault((ix, iz), []).append(i)


def surf(x, z):
    o = []
    for i in grid.get((int(math.floor(x/CELL)), int(math.floor(z/CELL))), ()):
        n, a, b, c = T[i]
        y = h_at(x, z, a, b, c)
        if y is not None: o.append((n.upper(), y))
    return o


for sb in built["stubs"]:
    sid = sb["id"]; st = plan[sid]
    rec = {"corners": []}
    for c in sb["corners"]:
        K = c["K"]; O = c["O"]; R = c["radius_m"]; rr = R + 5.0
        near = lambda t: any(math.hypot(p[0]-K[0], p[2]-K[1]) <= rr for p in t)
        steep = []; flipped = Counter(); kerb_n = 0
        for n, a, b, cc in T:
            u = n.upper()
            if not near((a, b, cc)): continue
            if u.startswith("1GRASS"):
                cy, rise = slope_rise(a, b, cc)
                if cy < math.cos(math.radians(45)): steep.append(rise)
            if u.startswith("1KERB"):
                s = (b[2]-a[2])*(cc[0]-a[0]) - (b[0]-a[0])*(cc[2]-a[2])
                if abs(s) > 1e-6: flipped[s > 0] += 1; kerb_n += 1
        # grass over curb (a poke), sampled on a 0.1 m grid within R + 5 of K
        poke, pmax = 0, 0.0
        gor = [0, -1.0]
        g = 0.1; n_ = int(rr/g)
        for i in range(-n_, n_+1):
            for j in range(-n_, n_+1):
                x, z = K[0]+i*g, K[1]+j*g
                if math.hypot(i*g, j*g) > rr: continue
                ss = surf(x, z)
                ks = [y for nm, y in ss if nm.startswith("1KERB")]
                gs = [y for nm, y in ss if nm.startswith("1GRASS")]
                rs = [y for nm, y in ss if nm.startswith("1ROAD")]
                if rs and gs:
                    r_ = max(rs); g_ = [y for y in gs if abs(y - r_) < 1.0]
                    if g_ and max(g_) >= r_ - 0.005:
                        gor[0] += 1; gor[1] = max(gor[1], max(g_) - r_)
                if ks and gs:
                    k = max(ks); gg = [y for y in gs if abs(y - k) < 1.0]
                    if gg and max(gg) > k + 0.005:
                        poke += 1; pmax = max(pmax, max(gg) - k)
        # pit: within 0.75 R of O, the lowest exposed grass vs the walk heights around
        pit = None
        for i in range(-30, 31):
            for j in range(-30, 31):
                x, z = O[0]+i*0.05, O[1]+j*0.05
                if math.hypot(i*0.05, j*0.05) > 0.75*R: continue
                ss = surf(x, z)
                if not ss: continue
                top = max(ss, key=lambda t: t[1])
                if top[0].startswith("1GRASS"):
                    ks = [y for nm, y in surf(x, z) if nm.startswith("1KERB")]
                    pit = top[1] if pit is None else min(pit, top[1])
        walk = [y for i in range(-30, 31) for j in range(-30, 31)
                for nm, y in surf(O[0]+i*0.05, O[1]+j*0.05) if nm.startswith("1KERB") and math.hypot(i*0.05, j*0.05) <= 0.75*R]
        rec["corners"].append({"edge": c["edge"], "phi": c["phi_deg"], "R": R, "compress": c["compress"],
                               "steep_grass": len(steep), "steep_max_rise": round(max(steep), 3) if steep else 0.0,
                               "grass_over_kerb_samples": poke, "grass_at_road_samples": gor[0], "grass_at_road_max": round(gor[1], 3), "grass_over_kerb_max": round(pmax, 3),
                               "kerb_tris": kerb_n, "kerb_flipped": min(flipped.values()) if len(flipped) == 2 else 0,
                               "pit_grass_min": None if pit is None else round(pit, 3),
                               "walk_top_near_O": round(max(walk), 3) if walk else None,
                               "pit_depth_below_walk": None if (pit is None or not walk) else round(max(walk) - pit, 3)})
    # paint on the stub's own road
    cx, cz = st["cut_xz"]; dx, dz = st["dir_xz"]; w = st["width_m"]
    u_bar = float(st["u_barrier_from_cut_m"]); toe = u_bar - 0.335
    lats = Counter(); umax = None
    for n, a, b, c in T:
        u_ = n.upper()
        if not (u_.startswith("MARKINGS") or u_.startswith("YLINE")): continue
        for p in (a, b, c):
            u = (p[0]-cx)*dx + (p[2]-cz)*dz
            lat = -(p[0]-cx)*dz + (p[2]-cz)*dx
            if 1.0 <= u <= u_bar + 3.0 and abs(lat) <= w/2 + 0.5:
                lats[round(abs(lat), 1)] += 1
                umax = u if umax is None else max(umax, u)
    divider = sum(v for k, v in lats.items() if abs(k - 3.65) <= 0.15 and abs(k - (w/2 - 0.55)) > 0.2)
    rec["paint"] = {"lateral_offsets_m": sorted(k for k in lats), "divider_verts": divider,
                    "farthest_paint_u_m": None if umax is None else round(umax, 3), "barrier_toe_u_m": round(toe, 3),
                    "past_toe_m": None if umax is None else round(umax - toe, 3)}
    # joints: barrier top heights along it
    name = ("1WALL_STUB_" + sid).upper()
    bv = [p for n, a, b, c in T if n.upper() == name for p in (a, b, c)]
    if bv:
        rows = {}
        for p in bv:
            lat = round(-(p[0]-cx)*dz + (p[2]-cz)*dx, 2)
            rows.setdefault(lat, []).append(p[1])
        # the top over the base at each ring: max - min of the ring's vertices
        tops = sorted((lat, max(v) - min(v)) for lat, v in rows.items())
        dips = [lat for lat, h in tops if h < 1.15]
        rec["joints"] = {"rings": len(tops), "dip_rings_lat": dips[:20], "n_dips": len(dips)}
    out["stubs"][sid] = rec
print(json.dumps(out, indent=1))
