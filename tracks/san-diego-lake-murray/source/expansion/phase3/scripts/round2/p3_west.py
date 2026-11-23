"""Phase 3 (EXPANSION-PHASE3-PLAN.md) Step 0 helper: the three western roads as PLANNED PAVEMENT for the tier planner.

Step 1's data/expansion.west.json (tools/author_expansion.py, adapted) does not exist yet, so the planner's input is
built here the way the plan describes it, from the plan's own facts only:
  - legs: shortest path over each road's own OSM ways (osm.expansion.json, osm_base 2026-10-14T10:13:39Z), one-way
    tags respected, between the plan's junction nodes, clockwise J2 -> J6 -> J7 -> J3 (Waring SW, Zion W,
    Mission Gorge NE) and the anticlockwise carriageways back;
  - centreline: on the divided roads (Waring, Mission Gorge) the midline between the two carriageways (Step 1.1),
    on Zion the clockwise way;
  - width: A4's curb-to-curb eye readings by station (s = metres from the leg's start node along the clockwise
    leg), linear between stations, held flat before the first and after the last; half-width = width / 2.
Pads (J6, J7) and the 35 stubs are not drawn (they do not exist before Step 1); the J2 / J3 ends are Phase 1's,
already planned through data/expansion.north.json.

    python3 p3_west.py <osm.expansion.json> <centerline.local.json> <out.json>
Writes the planned-pavement file in the shape scripts.elevation.terrain_sample.planned_inputs reads ("pieces" with
columns s, x, z, left_m, right_m) plus the legs it came from.
"""
import heapq
import json
import math
import sys

JN = {  # the plan's junction nodes (OSM), clockwise / anticlockwise carriageway ends
    "J2_cw": 1713352279, "J6_cw": 49397489, "J7_cw": 49317051, "J3_cw": 1484501766,
    "J3_acw": 1484501883, "J7_acw": 49317049, "J6_acw": 49333076, "J2_acw": 49333080,
}
LEGS = [  # (piece, road name, cw from, cw to, acw from, acw to)
    ("waring_sw", "Waring Road", "J2_cw", "J6_cw", "J6_acw", "J2_acw"),
    ("zion", "Zion Avenue", "J6_cw", "J7_cw", "J7_cw", "J6_cw"),
    ("mission_gorge_ne", "Mission Gorge Road", "J7_cw", "J3_cw", "J3_acw", "J7_acw"),
]
A4 = {  # EXPANSION-PHASE3-PLAN.md A4: curb to curb (m) at station s (m)
    "waring_sw": [(150, 28.0), (300, 29.5), (450, 29.7), (600, 22.0)],
    "zion": [(150 * k, w) for k, w in zip(range(1, 11), (12.0, 12.0, 13.5, 11.5, 12.0, 13.0, 11.5, 11.2, 15.1, 14.8))],
    "mission_gorge_ne": [(150 * k, w) for k, w in zip(range(1, 16), (32.1, 31.0, 27.5, 26.3, 27.3, 30.5, 27.0, 29.0,
                                                                       31.3, 27.5, 32.7, 30.1, 31.9, 33.5, 33.7))],
}
PLAN_LEN = {"waring_sw": (669.8, 668.9), "zion": (1567.3, 1594.4), "mission_gorge_ne": (2364.8, 2389.7)}
STEP_M = 2.5        # Step 1.1: "a centreline at 2-3 m spacing"
PAIR_M = 45.0       # carriageways further apart than this are not one road's two sides [invented]


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def route(ways, nodes, xy, a, b, name):
    """shortest path a -> b over the named road's ways, one-way respected; (node ids, way ids)"""
    adj = {}
    for w in ways:
        t = w.get("tags") or {}
        if t.get("name") != name:
            continue
        ow = t.get("oneway")
        ns = w["nodes"]
        for u, v in zip(ns, ns[1:]):
            if ow in ("yes", "true", "1"):
                adj.setdefault(u, []).append((v, w["id"]))
            elif ow == "-1":
                adj.setdefault(v, []).append((u, w["id"]))
            else:
                adj.setdefault(u, []).append((v, w["id"]))
                adj.setdefault(v, []).append((u, w["id"]))
    dist, prev = {a: 0.0}, {}
    pq = [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, wid in adj.get(u, ()):
            nd = d + math.dist(xy(u), xy(v))
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, (u, wid)
                heapq.heappush(pq, (nd, v))
    if b not in dist:
        raise SystemExit(f"no {name} path {a} -> {b}")
    path, wids = [b], []
    while path[-1] != a:
        u, wid = prev[path[-1]]
        path.append(u)
        if not wids or wids[-1] != wid:
            wids.append(wid)
    return path[::-1], wids[::-1], dist[b]


def resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for p, q in zip(pts, pts[1:]):
        L = math.dist(p, q)
        while acc + L >= step and L > 0:
            t = (step - acc) / L
            p = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            L = math.dist(p, q)
            out.append(p)
            acc = 0.0
        acc += L
    if math.dist(out[-1], pts[-1]) > 0.25 * step:
        out.append(pts[-1])
    return out


def nearest_on(poly, p):
    best = (1e18, None)
    for a, b in zip(poly, poly[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        q = (a[0] + dx * t, a[1] + dz * t)
        d = math.dist(p, q)
        if d < best[0]:
            best = (d, q)
    return best[1], best[0]


def width_at(table, s):
    if s <= table[0][0]:
        return table[0][1]
    for (s0, w0), (s1, w1) in zip(table, table[1:]):
        if s <= s1:
            return w0 + (w1 - w0) * (s - s0) / (s1 - s0)
    return table[-1][1]


def main():
    osm = json.load(open(sys.argv[1]))
    loc = json.load(open(sys.argv[2]))
    lon0, lat0 = loc["origin"]["lon"], loc["origin"]["lat"]
    mx, my = mpd(lat0)
    nodes = osm["nodes"]

    def xy(n):
        lo, la = nodes[str(n)][:2]
        return ((lo - lon0) * mx, (la - lat0) * my)

    pieces, legs = [], []
    for piece, name, ca, cb, aa, ab in LEGS:
        cw, cw_w, cw_len = route(osm["ways"], nodes, xy, JN[ca], JN[cb], name)
        acw, acw_w, acw_len = route(osm["ways"], nodes, xy, JN[aa], JN[ab], name)
        pc = resample([xy(n) for n in cw], STEP_M)
        pa = [xy(n) for n in acw][::-1]           # the anticlockwise carriageway, in clockwise order
        divided = piece != "zion"
        rows = []
        s = 0.0
        for k, p in enumerate(pc):
            if k:
                s += math.dist(pc[k - 1], p)
            c = p
            sep = None
            if divided:
                q, d = nearest_on(pa, p)
                sep = d
                if d <= PAIR_M:
                    c = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            w = width_at(A4[piece], s)
            rows.append([round(s, 2), round(c[0], 3), round(c[1], 3), round(w / 2, 3), round(-w / 2, 3),
                         None if sep is None else round(sep, 2)])
        pieces.append({"name": piece, "road": name, "columns": ["s", "x", "z", "left_m", "right_m", "osm_sep_m"],
                       "stations": rows})
        legs.append({"piece": piece, "road": name,
                     "cw": {"from": JN[ca], "to": JN[cb], "ways": cw_w, "nodes": len(cw), "length_m": round(cw_len, 1)},
                     "acw": {"from": JN[aa], "to": JN[ab], "ways": acw_w, "nodes": len(acw),
                             "length_m": round(acw_len, 1)},
                     "plan_length_m_cw_acw": PLAN_LEN[piece], "a4_width_table": A4[piece]})
        print(piece, "cw", round(cw_len, 1), len(cw_w), "ways; acw", round(acw_len, 1), len(acw_w), "ways; plan",
              PLAN_LEN[piece], "; first/last cw way", cw_w[0], cw_w[-1], file=sys.stderr)
    xs = [r[1] for p in pieces for r in p["stations"]]
    zs = [r[2] for p in pieces for r in p["stations"]]
    lons = [lon0 + x / mx for x in xs]
    out = {"version": 1, "what": "Phase 3 planned pavement for the tier planner (Step 0 data run, 2026-11-22); NOT "
                                 "Step 1's expansion.west.json",
           "_doc": __doc__, "frame": {"origin": loc["origin"], "what": "data/centerline.local.json's frame, x east, "
                                                                    "z north"},
           "osm": {"file": "tracks/san-diego-lake-murray/data/osm.expansion.json", "osm_base": osm.get("osm_base")},
           "legs": legs, "pieces": pieces, "pads": [], "stubs": [],
           "extent": {"x": [min(xs), max(xs)], "z": [min(zs), max(zs)], "lon": [min(lons), max(lons)]}}
    json.dump(out, open(sys.argv[3], "w"), indent=None, separators=(",", ":"))
    print("extent", out["extent"], file=sys.stderr)


if __name__ == "__main__":
    main()
