"""Phase 3 routes lens, re-run on fresh OSM (EXPANSION-PHASE3-PLAN.md rev 2, Step 0.2-0.3 data; the shape of
source/expansion/routes__routes_analysis.json, routes__legs.geojson and routes__mouths.json, whose research scripts
are not in the repo).

Legs: shortest path over each road's own named OSM ways, one-way tags respected, between the dossier's junction
nodes (DOSSIER-EXPANSION-WEST 2a), clockwise E Waring J2->J6, F Zion J6->J7, G Mission Gorge J7->J3, and back
anticlockwise; Princess View J3->J2 / J2->J3 only for the turns at J2 and J3. Stations s = metres from the junction
node at the start of each clockwise leg, along the clockwise OSM leg (the plan's "Stations").

Mouths: every branch of a way that is not one of the leg's own carriageway ways, at every node of either carriageway.
A branch that reaches the other carriageway within CROSS_M is a median crossing (not a mouth). A branch at a leg's
end node is a junction arm. Side L / R is of the clockwise direction.

The midline skeleton (stations every 2.5 m): tools/author_expansion.build_midline (1 m on the clockwise leg; the
anticlockwise carriageway's nearest point; midpoint where they are more than DIVIDED_SEP_M apart), smoothed with
author_expansion.gauss_smooth at SMOOTH_SIGMA_M, as author_expansion builds a piece's line.

    python -I p3x_legs.py <airoso> <fresh osm.expansion.json> <old osm.expansion.json> <out-dir>
"""
import hashlib
import heapq
import json
import math
import sys
from pathlib import Path

JN = {"J2": (1713352279, 49333080), "J6": (49397489, 49333076), "J7": (49317051, 49317049),
      "J3": (1484501766, 1484501883)}                       # (cw node, acw node): DOSSIER-EXPANSION-WEST 2a
LEGS = [  # id, plan id, road, from, to, cw (a, b), acw (a, b)
    ("E", "P3-WAR", "Waring Road", "J2", "J6", (1713352279, 49397489), (49333076, 49333080)),
    ("F", "P3-ZION", "Zion Avenue", "J6", "J7", (49397489, 49317051), (49317049, 49333076)),
    ("G", "P3-MG", "Mission Gorge Road", "J7", "J3", (49317051, 1484501766), (1484501883, 49317049)),
]
PV = ("Princess View Drive", (1484501766, 1713352279), (49333080, 1484501883))   # J3->J2 cw, J2->J3 acw
PLAN_LEN = {"E": (669.8, 668.9), "F": (1567.3, 1594.4), "G": (2364.8, 2389.7)}
CROSS_M = 80.0       # [invented] a branch that meets the other carriageway within this is a median crossing
BRANCH_M = 15.0      # [invented] a branch's heading is read over its first 15 m (the plan's stub length)
CHORD_M = 20.0       # [invented] junction bearings over the 20 m chord before / after the node
SIGNAL_NEAR_M = 40.0
CTL_KEYS = ("highway", "crossing", "traffic_signals", "traffic_signals:direction", "traffic_calming", "railway",
            "stop", "direction", "crossing:markings")
WAY_KEYS = ("name", "highway", "oneway", "lanes", "lanes:forward", "lanes:backward", "maxspeed", "surface",
            "turn:lanes", "turn:lanes:forward", "turn:lanes:backward", "cycleway", "cycleway:right",
            "cycleway:left", "cycleway:both", "sidewalk", "sidewalk:both", "width", "bridge", "layer", "ref")
PUBLIC = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
          "road", "busway"}


def compass(b):
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(((b % 360) + 22.5) // 45) % 8]


def main():
    airoso, fresh_p, old_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    sys.path.insert(0, str(airoso / "tools"))
    import author_expansion as ae
    out.mkdir(parents=True, exist_ok=True)
    osm = json.loads(fresh_p.read_text())
    old = json.loads(old_p.read_text())
    cl = json.loads((airoso / "tracks/san-diego-lake-murray/data/centerline.local.json").read_text())
    fr = ae.Frame(cl["origin"])
    nodes = {int(k): v for k, v in osm["nodes"].items()}
    ntags = {int(k): v for k, v in osm.get("node_tags", {}).items()}
    ways = {w["id"]: w for w in osm["ways"]}
    byn = {}
    for w in osm["ways"]:
        for n in w["nodes"]:
            byn.setdefault(n, set()).add(w["id"])
    xy = lambda n: fr.xz(*nodes[n][:2])

    def route(name, a, b, extra=()):
        adj = {}
        for w in osm["ways"]:
            t = w.get("tags") or {}
            if t.get("name") != name and w["id"] not in extra:
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
        path, seg_w = [b], []
        while path[-1] != a:
            u, wid = prev[path[-1]]
            path.append(u)
            seg_w.append(wid)
        return path[::-1], seg_w[::-1]

    def arcs(path):
        s = [0.0]
        for u, v in zip(path, path[1:]):
            s.append(s[-1] + math.dist(xy(u), xy(v)))
        return s

    def way_rec(wid, path, seg_w):
        t = ways[wid].get("tags") or {}
        L = sum(math.dist(xy(u), xy(v)) for (u, v), w in zip(zip(path, path[1:]), seg_w) if w == wid)
        r = {"id": wid, "len_m": round(L, 1)}
        r.update({k: t[k] for k in WAY_KEYS if k in t})
        return r

    def leg_rec(lid, road, sense, path, seg_w):
        s = arcs(path)
        wl = []
        for w in seg_w:
            if not wl or wl[-1] != w:
                wl.append(w)
        ctl = []
        for n, sn in zip(path, s):
            t = ntags.get(n)
            if t and any(k in t for k in ("highway", "crossing", "traffic_signals", "traffic_calming", "railway")):
                c = {"arc_m": round(sn, 1), "node": n}
                c.update({k: t[k] for k in CTL_KEYS if k in t})
                ctl.append(c)
        br = [way_rec(w, path, seg_w) for w in wl if (ways[w].get("tags") or {}).get("bridge")]
        return {"leg": lid, "road": road, "sense": sense, "length_m": round(s[-1], 1), "start_node": path[0],
                "end_node": path[-1], "start": nodes[path[0]][:2], "end": nodes[path[-1]][:2],
                "ways": [way_rec(w, path, seg_w) for w in wl], "controls_on_path": ctl, "bridges": br,
                "path_nodes": path, "geom": [nodes[n][:2] for n in path], "_s": s, "_seg_w": seg_w}

    legs = {}
    for lid, pid, road, ja, jb, (ca, cb), (aa, ab) in LEGS:
        cw = leg_rec(lid, road, "cw", *route(road, ca, cb))
        acw = leg_rec(lid, road, "acw", *route(road, aa, ab))
        legs[lid] = {"cw": cw, "acw": acw, "plan_id": pid, "from": ja, "to": jb}
    pv_cw = leg_rec("P", PV[0], "cw", *route(PV[0], *PV[1]))
    try:
        pv_acw = leg_rec("P", PV[0], "acw", *route(PV[0], *PV[2]))
    except SystemExit:
        # J2's anticlockwise node sits on Waring's NE carriageway: Princess View leaves from the cw node
        pv_acw = leg_rec("P", PV[0], "acw", *route(PV[0], PV[1][1], PV[2][1]))

    # ---------------------------------------------------------------- the midline skeleton (author_expansion's way)
    skel = {}
    for lid, L in legs.items():
        fwd = [xy(n) for n in L["cw"]["path_nodes"]]
        rev = [xy(n) for n in L["acw"]["path_nodes"]][::-1]
        f1, raw, sep = ae.build_midline({"fwd": fwd, "rev": rev})
        sm = ae.gauss_smooth(raw, ae.SMOOTH_SIGMA_M / 1.0)
        # every 2.5 m: index i is the cw station in metres (1 m samples); take i = 0, 2.5, 5 ... by interpolation
        st = []
        n = len(sm)
        s2 = 0.0
        while s2 <= n - 1 + 1e-9:
            i0 = int(math.floor(s2))
            i1 = min(i0 + 1, n - 1)
            f = s2 - i0
            x = sm[i0][0] + (sm[i1][0] - sm[i0][0]) * f
            z = sm[i0][1] + (sm[i1][1] - sm[i0][1]) * f
            rx = raw[i0][0] + (raw[i1][0] - raw[i0][0]) * f
            rz = raw[i0][1] + (raw[i1][1] - raw[i0][1]) * f
            sp = sep[i0] + (sep[i1] - sep[i0]) * f
            st.append([round(s2, 2), round(x, 3), round(z, 3), round(sp, 2), round(math.hypot(x - rx, z - rz), 3)])
            s2 += 2.5
        skel[lid] = {"columns": ["s", "x", "z", "osm_sep_m", "smooth_vs_raw_m"], "stations": st,
                     "length_m": round(n - 1, 1), "midline_p95_m": sorted(r[4] for r in st)[int(0.95 * (len(st) - 1))]}

    # ---------------------------------------------------------------- mouths
    def walk(n, wid, k_next, limit):
        """from node n along way wid toward its neighbour index k_next: [(node, metres)] up to limit metres"""
        ns = ways[wid]["nodes"]
        i = ns.index(n)
        step = 1 if k_next > i else -1
        out, acc, prev = [], 0.0, n
        j = i + step
        while 0 <= j < len(ns):
            acc += math.dist(xy(prev), xy(ns[j]))
            out.append((ns[j], acc))
            if acc >= limit:
                break
            prev = ns[j]
            j += step
        return out

    def cw_station(lid, p):
        cwp = [xy(n) for n in legs[lid]["cw"]["path_nodes"]]
        d, s, lat, i = ae.project(p, cwp)
        return s, d, lat, i, cwp

    mouths, crossings, seen = {}, {}, set()
    for lid, L in legs.items():
        own = set(L["cw"]["_seg_w"]) | set(L["acw"]["_seg_w"])
        cwset, acwset = set(L["cw"]["path_nodes"]), set(L["acw"]["path_nodes"])
        ends = {L["cw"]["path_nodes"][0]: L["from"], L["acw"]["path_nodes"][-1]: L["from"],
                L["cw"]["path_nodes"][-1]: L["to"], L["acw"]["path_nodes"][0]: L["to"]}
        recs, xr = [], []
        for sense, other in (("cw", acwset), ("acw", cwset)):
            for n in L[sense]["path_nodes"]:
                for wid in sorted(byn.get(n, ())):
                    if wid in own:
                        continue
                    ns = ways[wid]["nodes"]
                    i = ns.index(n)
                    for k in (i - 1, i + 1):
                        if not (0 <= k < len(ns)):
                            continue
                        key = (n, wid, ns[k])
                        if key in seen:
                            continue
                        seen.add(key)
                        wk = walk(n, wid, k, CROSS_M)
                        hit = next(((m, d) for m, d in wk if m in other and m != n), None)
                        t = ways[wid].get("tags") or {}
                        p = xy(n)
                        s, d, lat, seg, cwp = cw_station(lid, p)
                        if hit and n not in ends and hit[0] not in ends:
                            xr.append({"station_cw_m": round(s, 1), "way": wid, "name": t.get("name"),
                                       "highway": t.get("highway"), "service": t.get("service"),
                                       "from_node": n, "to_node": hit[0], "length_m": round(hit[1], 1),
                                       "at": nodes[n][:2]})
                            continue
                        if hit:
                            continue          # a crossing at a junction end: the pad's business
                        # heading over the first BRANCH_M
                        far = next(((m, dd) for m, dd in wk if dd >= BRANCH_M), wk[-1] if wk else None)
                        q = xy(far[0])
                        b = (math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) + 360) % 360
                        a0, a1 = cwp[max(0, min(seg, len(cwp) - 2))], cwp[max(0, min(seg, len(cwp) - 2)) + 1]
                        tx, tz = a1[0] - a0[0], a1[1] - a0[1]
                        cr = tx * (q[1] - p[1]) - tz * (q[0] - p[0])
                        hb = (math.degrees(math.atan2(tx, tz)) + 360) % 360
                        ang = ((b - hb + 180) % 360) - 180
                        ow = t.get("oneway")
                        flow = None
                        if ow in ("yes", "true", "1"):
                            flow = "out" if k > i else "in"
                        elif ow == "-1":
                            flow = "in" if k > i else "out"
                        rec = {"station_cw_m": round(s, 1), "way": wid, "name": t.get("name"),
                               "highway": t.get("highway"), "service": t.get("service"), "access": t.get("access"),
                               "surface": t.get("surface"), "oneway": ow, "flow": flow, "lanes": t.get("lanes"),
                               "width": t.get("width"), "maxspeed": t.get("maxspeed"),
                               "leaves_toward": compass(b), "bearing_deg": round(b, 1),
                               "angle_vs_cw_deg": round(ang, 1), "side": "L" if cr > 0 else "R",
                               "on": sense, "node": n, "next_node": ns[k], "at": nodes[n][:2],
                               "through": 0 < i < len(ns) - 1,
                               "node_ctl": {kk: vv for kk, vv in (ntags.get(n) or {}).items() if kk in CTL_KEYS},
                               "kind": None, "junction": ends.get(n)}
                        hw = t.get("highway")
                        if n in ends:
                            rec["kind"] = "junction_arm"
                        elif hw == "service":
                            rec["kind"] = "service"
                        elif hw and hw.endswith("_link"):
                            rec["kind"] = "link"
                        elif hw in PUBLIC:
                            rec["kind"] = "public"
                        else:
                            rec["kind"] = "other"
                        rec["control"] = ("signal" if (ntags.get(n) or {}).get("highway") == "traffic_signals" else
                                          (ntags.get(n) or {}).get("highway") or "-")
                        recs.append(rec)
        recs.sort(key=lambda r: (r["station_cw_m"], r["side"], r["way"]))
        xr.sort(key=lambda r: r["station_cw_m"])
        mouths[lid] = recs
        crossings[lid] = xr

    # ---------------------------------------------------------------- junctions: turns over the 20 m chords
    def chord_bearing(leg, at_end):
        path, s = leg["path_nodes"], leg["_s"]
        P = [xy(n) for n in path]
        sl = ae.arc(P)
        if at_end:
            q = ae.at_arc(P, sl, sl[-1] - CHORD_M)
            a, b = q, P[-1]
        else:
            q = ae.at_arc(P, sl, CHORD_M)
            a, b = P[0], q
        return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360

    def last_seg_bearing(leg, at_end):
        P = [xy(n) for n in leg["path_nodes"]]
        a, b = (P[-2], P[-1]) if at_end else (P[0], P[1])
        return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360

    sig = [n for n, t in ntags.items() if t.get("highway") == "traffic_signals"]
    order_cw = [("J6", legs["E"]["cw"], legs["F"]["cw"]), ("J7", legs["F"]["cw"], legs["G"]["cw"]),
                ("J3", legs["G"]["cw"], pv_cw), ("J2", pv_cw, legs["E"]["cw"])]
    order_acw = [("J2", legs["E"]["acw"], pv_acw), ("J3", pv_acw, legs["G"]["acw"]),
                 ("J7", legs["G"]["acw"], legs["F"]["acw"]), ("J6", legs["F"]["acw"], legs["E"]["acw"])]
    junctions = []
    for sense, order in (("cw", order_cw), ("acw", order_acw)):
        for j, a, b in order:
            bi, bo = chord_bearing(a, True), chord_bearing(b, False)
            n_in, n_out = a["path_nodes"][-1], b["path_nodes"][0]
            at = nodes[n_in][:2]
            pj = xy(n_in)
            junctions.append({"junction": j, "sense": sense, "from": a["road"], "to": b["road"], "node_in": n_in,
                              "node_out": n_out, "at": at, "bearing_in": round(bi, 1), "bearing_out": round(bo, 1),
                              "turn_deg(+R/-L)": round(((bo - bi + 180) % 360) - 180, 1),
                              "turn_last_segment_deg": round(((last_seg_bearing(b, False) - last_seg_bearing(a, True)
                                                               + 180) % 360) - 180, 1),
                              "gap_in_out_m": round(math.dist(xy(n_in), xy(n_out)), 1),
                              "signals_near": sorted(n for n in sig if math.dist(xy(n), pj) <= SIGNAL_NEAR_M)})

    # ---------------------------------------------------------------- the old OSM (2026-10-14) against the fresh one
    onodes = {int(k): v for k, v in old["nodes"].items()}
    oways = {w["id"]: w for w in old["ways"]}
    diff = {"old": {"osm_base": old.get("osm_base"), "fetched_utc": old.get("fetched_utc"),
                    "query_fingerprint": old.get("query_fingerprint")},
            "new": {"osm_base": osm.get("osm_base"), "fetched_utc": osm.get("fetched_utc"),
                    "query_fingerprint": osm.get("query_fingerprint")}, "legs": {}}
    for lid, L in legs.items():
        for sense in ("cw", "acw"):
            lg = L[sense]
            wl = [w["id"] for w in lg["ways"]]
            moved = [n for n in lg["path_nodes"] if n not in onodes or onodes[n][:2] != nodes[n][:2]]
            tag_changed = [w for w in wl if w not in oways or (oways[w].get("tags") != ways[w].get("tags"))]
            node_list_changed = [w for w in wl if w not in oways or oways[w]["nodes"] != ways[w]["nodes"]]
            diff["legs"][f"{lid}.{sense}"] = {"ways": len(wl), "path_nodes": len(lg["path_nodes"]),
                                              "nodes_new_or_moved": moved, "ways_tags_changed": tag_changed,
                                              "ways_nodes_changed": node_list_changed}
    # every way within the Phase 3 corridor (any node within 60 m of a leg): added / removed / changed
    corridor = []
    for L in legs.values():
        for sense in ("cw", "acw"):
            corridor += [xy(n) for n in L[sense]["path_nodes"]]

    def near(lonlat, R=60.0):
        p = fr.xz(*lonlat[:2])
        return any(abs(p[0] - c[0]) < R and abs(p[1] - c[1]) < R and math.dist(p, c) < R for c in corridor[::2])
    cand_new = {w["id"] for w in osm["ways"] if any(near(nodes[n]) for n in w["nodes"][::3] + [w["nodes"][-1]])}
    cand_old = {w["id"] for w in old["ways"] if any(near(onodes[n]) for n in w["nodes"][::3] + [w["nodes"][-1]]
                                                    if n in onodes)}
    diff["corridor_60m"] = {
        "ways_new": len(cand_new), "ways_old": len(cand_old),
        "added": sorted(cand_new - set(oways)), "removed": sorted(w for w in cand_old if w not in ways),
        "tags_changed": sorted(w for w in cand_new & set(oways) if oways[w].get("tags") != ways[w].get("tags")),
        "nodes_changed": sorted(w for w in cand_new & set(oways) if oways[w]["nodes"] != ways[w]["nodes"] or
                                any(onodes.get(n, [None])[:2] != nodes[n][:2] for n in ways[w]["nodes"]))}

    # ---------------------------------------------------------------- outputs
    def strip(lg):
        return {k: v for k, v in lg.items() if not k.startswith("_")}
    summ = {f"{lid}_{sense}_m": legs[lid][sense]["length_m"] for lid in legs for sense in ("cw", "acw")}
    summ["new_road_cw_m"] = round(sum(legs[l]["cw"]["length_m"] for l in legs), 1)
    summ["new_road_acw_m"] = round(sum(legs[l]["acw"]["length_m"] for l in legs), 1)
    summ["princess_view_cw_J3_J2_m"] = pv_cw["length_m"]
    summ["princess_view_acw_J2_J3_m"] = pv_acw["length_m"]
    summ["western_loop_cw_m"] = round(summ["new_road_cw_m"] + pv_cw["length_m"], 1)
    summ["western_loop_acw_m"] = round(summ["new_road_acw_m"] + pv_acw["length_m"], 1)
    summ["plan_rev2_cw_acw_m"] = PLAN_LEN
    meta = {"osm_file": "osm.expansion.json (this folder)", "osm_base": osm.get("osm_base"),
            "fetched_utc": osm.get("fetched_utc"), "mirror": osm.get("source"), "bbox_swne": osm.get("bbox"),
            "query": osm.get("query"), "query_fingerprint": osm.get("query_fingerprint"),
            "osm_sha256": hashlib.sha256(fresh_p.read_bytes()).hexdigest(),
            "frame": {"origin": cl["origin"], "what": "data/centerline.local.json's local frame (x east, z north), "
                                                      "tools/author_expansion.Frame"},
            "legs": {l: {"plan_id": L["plan_id"], "from": L["from"], "to": L["to"]} for l, L in legs.items()},
            "junction_nodes_cw_acw": JN,
            "parameters": {"CROSS_M": CROSS_M, "BRANCH_M": BRANCH_M, "CHORD_M": CHORD_M,
                           "SIGNAL_NEAR_M": SIGNAL_NEAR_M, "DIVIDED_SEP_M": ae.DIVIDED_SEP_M,
                           "SMOOTH_SIGMA_M": ae.SMOOTH_SIGMA_M}}
    analysis = {"meta": meta, "cw": [strip(legs[l]["cw"]) for l in legs], "acw": [strip(legs[l]["acw"]) for l in legs],
                "princess_view_cw": strip(pv_cw), "princess_view_acw": strip(pv_acw), "junctions": junctions,
                "median_crossings": crossings, "summary": summ}
    (out / "routes_analysis.west.json").write_text(json.dumps(analysis, indent=1))
    feats = []
    for lid, L in legs.items():
        for sense in ("cw", "acw"):
            lg = L[sense]
            feats.append({"type": "Feature", "properties": {"leg": lid, "plan_id": L["plan_id"], "road": lg["road"],
                                                            "sense": sense, "length_m": lg["length_m"],
                                                            "from": L["from"] if sense == "cw" else L["to"],
                                                            "to": L["to"] if sense == "cw" else L["from"]},
                          "geometry": {"type": "LineString", "coordinates": lg["geom"]}})
    (out / "legs.west.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    (out / "mouths.west.raw.json").write_text(json.dumps({"mouths": mouths, "median_crossings": crossings,
                                                          "lengths": summ}, indent=1))
    (out / "skeleton.west.json").write_text(json.dumps({"frame": meta["frame"], "pieces": skel}, indent=0))
    (out / "osm_diff.west.json").write_text(json.dumps(diff, indent=1))
    for lid in legs:
        c = {}
        for m in mouths[lid]:
            c[m["kind"]] = c.get(m["kind"], 0) + 1
        print(lid, "cw", legs[lid]["cw"]["length_m"], "acw", legs[lid]["acw"]["length_m"], "plan", PLAN_LEN[lid],
              "mouths", c, "crossings", len(crossings[lid]), "midline p95", skel[lid]["midline_p95_m"])
    for j in junctions:
        print(j["junction"], j["sense"], j["from"], "->", j["to"], j["turn_deg(+R/-L)"], "gap", j["gap_in_out_m"])
    print("diff", json.dumps({k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()}
                              for k, v in diff["legs"].items()}))
    print("corridor", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in diff["corridor_60m"].items()}))


if __name__ == "__main__":
    main()
