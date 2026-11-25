"""Denver Grand Prix 0.1.0: each side street's mouth on the lap, as short connectors (data/connectors.local.json), for
the free roam's "the lap's own roads plus each side street's mouth" (ledger 0096 0.1.0; the full D4 grid comes later).

Real roads only (L1): every stub is an OSM way out of source/osm.json (OSM as of 2026-11-23T01:12:49Z) that meets the
lap at one of the lap's own OSM nodes (data/lap_line.plan.json), followed away from the lap along OSM's own line for
draft_line.mouths.reach_m [invented] (joined across a way split where the next way carries the same name), so its mouth
reaches the lap's pavement and tools/trim_connectors.py cuts it at the measured edge. Nothing is routed and no road is
drawn that OSM does not draw. A stub that meets the lap again within its reach is kept whole (the real road between two
parts of the lap, e.g. Colfax between Kalamath and Santa Fe).

Dropped, each with its count in the report: the lap's own ways; service roads, footways and the rest outside
draft_line.mouths.classes; a stub whose far end stays within parallel_m [invented] of the lap's line (the lap's other
carriageway, not a side street); a stub shorter than min_m [invented] once it leaves the lap's pavement.

Heights: USGS 3DEP 1/3 arc-second tiles (about 10 m cells) sampled bilinearly every 3 m along the stub, a 9 m running
mean, anchored to the lap: inside the lap's pavement the lap's own height; beyond its edge the 1/3 arc-second surface's
rise from the edge added to the lap's height there (3DEP 1 m along OSM's line), then a 15 m running mean; trim_connectors blends each mouth onto the lap's height at the cut. A piece that meets the lap again within
its reach (a road between two parts of the lap) is not built unless keep_both_on_lap, and every stub stops where it comes
within another part of the lap's half width + other_lap_clear_m [invented]. Widths: draft_line.mouths.widths by OSM
class [invented] (Sand Creek's grid table: the side streets' kerbs are not measured).

    python tracks/denver-grand-prix/source/draft/mouth_stubs.py --dem-dir DIR   (or DGP_DEM_DIR=DIR)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parents[1]
AIROSO = TRACK.parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

from scripts.geometry.projection import _meters_per_degree  # noqa: E402

DEM_DIR_ENV = "DGP_DEM_DIR"   # the folder holding the USGS_13_*.tif tiles (source/survey/DATA.md); never in git
STEP_M = 3.0


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def build(dem_dir: Path) -> dict:
    import numpy as np
    import rasterio
    cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
    mc = cfg["draft_line"]["mouths"]
    classes = {k: float(v) for k, v in mc["widths"].items() if not k.startswith("_")}
    reach_m, parallel_m, min_m = float(mc["reach_m"]), float(mc["parallel_m"]), float(mc["min_m"])
    exclude = {str(x["name"]) for x in mc.get("exclude") or []}
    osm = json.loads((TRACK / "source" / "osm.json").read_text(encoding="utf-8"))
    nodes = {int(k): v for k, v in osm["nodes"].items()}
    ways = {w["id"]: w for w in osm["ways"]}
    lap_ways = {x for leg in json.loads((TRACK / "data" / "lap_ways.plan.json").read_text())["legs"] for x in leg["ways"]}
    lap_nodes = [n["node"] for n in json.loads((TRACK / "data" / "lap_line.plan.json").read_text())["nodes"]]
    lap_set = set(lap_nodes)
    local = json.loads((TRACK / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    org = local["origin"]
    lon0, lat0, elev0 = float(org["lon"]), float(org["lat"]), float(org["elev_m"])
    ml, mt = _meters_per_degree(lat0)
    LP = np.array([[p[0], p[2]] for p in local["points_xyz_m"]])
    LW = np.array(local["widths_m"], dtype=float)
    LST = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(LP, axis=0).T))]); LAP = float(LST[-1])
    other_clear = float(mc.get("other_lap_clear_m", 6.0))

    def lap_near(q):
        d = np.hypot(*(LP - np.asarray(q)).T)
        k = int(np.argmin(d))
        return k, float(d[k])

    def xy(nid):
        lo, la = nodes[nid]
        return ((lo - lon0) * ml, (la - lat0) * mt)

    def lap_dist(q):
        d = np.hypot(*(LP - np.asarray(q)).T)
        k = int(np.argmin(d))
        return float(d[k]), float(LW[k])

    by_node = {}
    for w in osm["ways"]:
        for nid in w["nodes"]:
            by_node.setdefault(nid, []).append(w["id"])

    def cls(w):
        return (w.get("tags") or {}).get("highway", "")

    rep = {"dropped": {"class": 0, "parallel": 0, "short": 0, "excluded": 0, "duplicate": 0, "both_on_lap": 0}, "stubs": []}
    seen_paths = set()
    stubs = []
    for nid in lap_nodes:
        for wid in by_node.get(nid, []):
            if wid in lap_ways:
                continue
            w = ways[wid]
            c = cls(w)
            if c not in classes:
                rep["dropped"]["class"] += 1
                continue
            idx = [i for i, x in enumerate(w["nodes"]) if x == nid]
            for i0 in idx:
                for step in (+1, -1):
                    # walk away from the lap node along this way (and on along same-named ways at a split)
                    path = [nid]; length = 0.0; cur_w = w; i = i0; hit_lap = False
                    name = (w.get("tags") or {}).get("name")
                    while length < reach_m:
                        j = i + step
                        if j < 0 or j >= len(cur_w["nodes"]):
                            end = cur_w["nodes"][i]
                            nxt = [ways[x] for x in by_node.get(end, []) if x != cur_w["id"] and x not in lap_ways
                                   and cls(ways[x]) in classes and (ways[x].get("tags") or {}).get("name") == name and name]
                            if len(nxt) != 1:
                                break
                            cur_w = nxt[0]
                            pos = cur_w["nodes"].index(end)
                            step = 1 if pos == 0 else (-1 if pos == len(cur_w["nodes"]) - 1 else 0)
                            if step == 0:
                                break
                            i = pos
                            continue
                        a, b = xy(cur_w["nodes"][i]), xy(cur_w["nodes"][j])
                        length += math.dist(a, b)
                        path.append(cur_w["nodes"][j])
                        i = j
                        if cur_w["nodes"][j] in lap_set:
                            hit_lap = True
                            break
                    if len(path) < 2:
                        continue
                    key = tuple(sorted((path[0], path[-1]))) + (len(path),)
                    if key in seen_paths:
                        rep["dropped"]["duplicate"] += 1
                        continue
                    seen_paths.add(key)
                    pts = [xy(x) for x in path]
                    # resample every STEP_M along OSM's own line, cut at reach_m (a stub that meets the lap again: whole)
                    cum = [0.0]
                    for a_, b_ in zip(pts, pts[1:]):
                        cum.append(cum[-1] + math.dist(a_, b_))
                    total = cum[-1] if hit_lap else min(cum[-1], reach_m)
                    nst = max(1, int(round(total / STEP_M)))
                    out = []
                    for q in range(nst + 1):
                        t_ = total * q / nst
                        k_ = max(0, min(len(cum) - 2, next((r for r in range(1, len(cum)) if cum[r] >= t_), len(cum) - 1) - 1))
                        f_ = 0.0 if cum[k_ + 1] == cum[k_] else (t_ - cum[k_]) / (cum[k_ + 1] - cum[k_])
                        out.append((pts[k_][0] + (pts[k_ + 1][0] - pts[k_][0]) * f_, pts[k_][1] + (pts[k_ + 1][1] - pts[k_][1]) * f_))
                    # never reach another part of the lap: cut the stub where it comes within that part's half width +
                    # other_lap_clear_m (a road between two parts of the lap is not a mouth: Colfax between Speer's legs)
                    k0, _ = lap_near(out[0])
                    cut_at = None
                    for qi, q in enumerate(out[1:], 1):
                        d_ = np.hypot(*(LP - np.asarray(q)).T)
                        sep = np.abs((LST - LST[k0] + LAP / 2) % LAP - LAP / 2)
                        far = sep > 60.0
                        if far.any():
                            j_ = int(np.argmin(np.where(far, d_, np.inf)))
                            if d_[j_] < LW[j_] / 2 + other_clear:
                                cut_at = qi
                                break
                    if cut_at is not None:
                        rep["dropped"]["cut_short_of_lap"] = rep["dropped"].get("cut_short_of_lap", 0) + 1
                        out = out[:cut_at]
                        hit_lap = False
                        if len(out) < 2:
                            rep["dropped"]["short"] += 1
                            continue
                    # off the lap's pavement: how far does it run?
                    off = [p for p in out if (lambda dw: dw[0] > dw[1] / 2 + 0.5)(lap_dist(p))]
                    run = len(off) * STEP_M
                    if hit_lap and not mc.get("keep_both_on_lap", False):
                        rep["dropped"]["both_on_lap"] = rep["dropped"].get("both_on_lap", 0) + 1
                        continue
                    if not hit_lap:
                        d_far, _ = lap_dist(out[-1])
                        if d_far < parallel_m:
                            rep["dropped"]["parallel"] += 1
                            continue
                    if run < min_m:
                        rep["dropped"]["short"] += 1
                        continue
                    stubs.append({"class": c, "osm_way": wid, "name": name, "nodes": path, "xy": out, "both_on_lap": hit_lap})
    # heights: 3DEP 1/3 arc-second, bilinear
    tiles = sorted(Path(dem_dir).glob("USGS_13_*.tif"))
    dss = [rasterio.open(t) for t in tiles]

    def z_at(lo, la):
        for ds in dss:
            b = ds.bounds
            if b.left <= lo < b.right and b.bottom < la <= b.top:
                fr, fc = ds.index(lo, la, op=float)
                fr -= 0.5; fc -= 0.5
                r0, c0 = int(math.floor(fr)), int(math.floor(fc))
                tr, tc = fr - r0, fc - c0
                if r0 < 0 or c0 < 0 or r0 + 2 > ds.height or c0 + 2 > ds.width:
                    continue                      # the tiles overlap: the neighbour holds the whole 2 x 2
                v = ds.read(1, window=((r0, r0 + 2), (c0, c0 + 2)))
                return float(v[0, 0] * (1 - tc) * (1 - tr) + v[0, 1] * tc * (1 - tr) + v[1, 0] * (1 - tc) * tr + v[1, 1] * tc * tr)
        raise SystemExit("[mouth_stubs] no DEM tile under %.6f, %.6f" % (lo, la))

    counts = {}
    conns = []
    for s in sorted(stubs, key=lambda s: (s["class"], s["nodes"][0], s["nodes"][-1])):
        k = counts.get(s["class"], 0); counts[s["class"]] = k + 1
        name = f"mouth_{s['class']}_{k}"
        if name in exclude:
            rep["dropped"]["excluded"] += 1
            continue
        zs = [z_at(lon0 + x / ml, lat0 + y / mt) for x, y in s["xy"]]
        h = 1
        zs = [sum(zs[max(0, i - h):i + h + 1]) / len(zs[max(0, i - h):i + h + 1]) for i in range(len(zs))]
        # anchored to the lap: the stub's heights are the 3DEP surface's rise from the junction, added to the lap's own
        # height there (the lap is 3DEP 1 m along OSM's line; the 1/3 arc-second surface sits up to tens of cm off it)
        ie = next((i for i, q in enumerate(s["xy"]) if (lambda kd: kd[1] > LW[kd[0]] / 2)(lap_near(q))), 0)
        ke, _ = lap_near(s["xy"][ie])
        z_edge = float(local["points_xyz_m"][ke][1]) + elev0
        zz = []
        for i, (q, z) in enumerate(zip(s["xy"], zs)):
            if i < ie:
                zz.append(float(local["points_xyz_m"][lap_near(q)[0]][1]) + elev0)
            else:
                zz.append(z_edge + (z - zs[ie]))
        h2 = 2
        zs = [sum(zz[max(0, i - h2):i + h2 + 1]) / len(zz[max(0, i - h2):i + h2 + 1]) for i in range(len(zz))]
        w = classes[s["class"]]
        conns.append({"name": name, "kind": "connector",
                      "points_xyz_m": [[round(x, 3), round(z - elev0, 3), round(y, 3)] for (x, y), z in zip(s["xy"], zs)],
                      "widths_m": [w] * len(s["xy"])})
        rep["stubs"].append({"name": name, "osm_way": s["osm_way"], "street": s["name"], "class": s["class"],
                             "length_m": round(sum(math.dist(p_, q_) for p_, q_ in zip(s["xy"], s["xy"][1:])), 1), "both_on_lap": s["both_on_lap"],
                             "lap_node": s["nodes"][0]})
    for ds in dss:
        ds.close()
    data = TRACK / "data"
    (data / "connectors.local.json").write_text(json.dumps({"connectors": conns, "_doc": "tracks/denver-grand-prix/source/draft/mouth_stubs.py: each side street's mouth (OSM ways meeting the lap's own nodes), widths [invented] by class"}), encoding="utf-8")
    rep["count"] = len(conns)
    rep["md5"] = _md5(data / "connectors.local.json")
    rep["params"] = {"reach_m": reach_m, "parallel_m": parallel_m, "min_m": min_m, "widths": classes}
    (data / "mouth_stubs.report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-dir", default=__import__("os").environ.get(DEM_DIR_ENV), help="the 3DEP 1/3 arc-second tiles (or $DGP_DEM_DIR)")
    a = ap.parse_args()
    if not a.dem_dir:
        ap.error("--dem-dir (or $DGP_DEM_DIR): the folder of USGS_13_n40w105.tif / USGS_13_n40w106.tif")
    rep = build(Path(a.dem_dir))
    print(json.dumps({k: rep[k] for k in ("count", "dropped", "params")}, indent=1))
    for s in rep["stubs"]:
        print(f"  {s['name']:24s} {str(s['street'])[:28]:28s} {s['length_m']:6.1f} m  way {s['osm_way']}{'  (both ends on the lap)' if s['both_on_lap'] else ''}")


if __name__ == "__main__":
    main()
