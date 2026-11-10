"""The downloads the SD freeway port's next steps need, worked out from CACHED indexes only (ledger 0080 2b round 1).

Kevin has approved no new data download. This tool fetches NOTHING: it reads the network draft, the port's config, the
NAIP crop cache, the 2014 EPT cache (its ``ept.json``, its cached ``ept-hierarchy-*.json`` pages and node files) and
the cached TNM product listings, and lists what is NOT cached:

  NAIP   the Planetary Computer crops tools/naip_carriageways.py would read (TILE_M squares of the local frame touched
         by its scan, +-REACH_M either side of every STEP_M station of a carriageway): the 2b mainlines. The I 8
         corridor's crops are all cached (carriageway_edges.naip.json: tiles_missing_offline []).
  EPT    the CA_SanDiegoQL2_2014 nodes whose cube meets a corridor disc (tools/network_deck_lidar.py's own walk):
         2b: every STEP_M station of each mainline carriageway, radius half its draft width + OUT_M (the barrier
         reader's window, tools/barrier_lidar.py), and the median between a pair (midpoint, radius half the gap +
         ALONG_M) where the pair is within PAIR_M (naip_carriageways'); I 8: the median's UNREAD stations
         (median_ground.lidar.json, the PC's run with both D24 tiles), midpoint, radius half the gap + ALONG_M.
         A node is cached when its .laz is in the cache. A hierarchy page the walk needs but the cache lacks is
         listed as a page (its nodes are then unknown: not counted, not guessed).
  D24    the 2024 county LAZ tiles over the 2014 EPT's holes named by runbook 0080-4, with the TNM listing's
         sizeInBytes where the cached listing has the tile; else "unknown without a request".

Sizes: a NAIP crop is stored as (4, 1000, 1000) uint8 .npy (exact: the cached crops' size); the API's response also
carries titiler's mask band (not verified without a request). An EPT node's size is NOT in the hierarchy (only its
point count): the MB given is the point count times the cached nodes' own bytes per point, labelled an estimate.

    <lidarvenv python> tools/fwlm_downloads.py <draft-dir> <track.config.json> <out.json>
        --naip-cache DIR --ept-cache DIR [--tnm FILE ...]

numpy + scipy + pyproj (the lidar venv). Reads only.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry import network_reference  # noqa: E402
from tools import naip_carriageways as naip  # noqa: E402

EPT_URL = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanDiegoQL2_2014/ept.json"
NAIP_API = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/ (collection naip)"
D24_BASE = ("https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_SanDiegoCo_D24/"
            "CA_SanDiegoCo_2_D24/LAZ/USGS_LPC_CA_SanDiegoCo_D24_{t}.laz")
# runbook 0080-4: the D24 tiles over the 2014 EPT's holes the deck reader found (E km / N km, NAD83(2011) UTM 11N)
D24_HOLES = {"11SMS480624": "I 8 west Morena (111 hole stations; read on the PC, not on the Mac)",
             "11SMS873633": "Kearny Mesa / I 5 - SR 52 holes", "11SMS833634": "Kearny Mesa / I 5 - SR 52 holes",
             "11SMS823622": "Kearny Mesa / I 5 - SR 52 holes", "11SMS813623": "Kearny Mesa / I 5 - SR 52 holes",
             "11SMS883633": "Kearny Mesa / I 5 - SR 52 holes", "11SMS873625": "Kearny Mesa / I 5 - SR 52 holes"}
STEP_M = 5.0            # naip_carriageways.STEP_M / network_deck_lidar.STEP_M
OUT_M = 3.0             # tools/barrier_lidar.py's window: 3 m out past the pavement edge
ALONG_M = 2.0           # median_lidar.ALONG_M
PAIR_M = naip.PAIR_M    # 45 m


def _frames(nloc):
    lon0, lat0 = float(nloc["origin"]["lon"]), float(nloc["origin"]["lat"])
    mx, my = naip.mpd(lat0)
    return lon0, lat0, mx, my


def _resample(pts, widths, step):
    P = np.asarray([(p[0], p[2]) for p in pts], float)
    W = np.asarray(widths, float)
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    S = np.arange(0.0, s[-1] + 1e-9, step)
    return np.c_[np.interp(S, s, P[:, 0]), np.interp(S, s, P[:, 1])], np.interp(S, s, W), S


def carriageways_2b(draft: Path, cfg: dict):
    fc = json.loads((draft / "network.geojson").read_text(encoding="utf-8"))
    er = json.loads((draft / "network.edges.local.json").read_text(encoding="utf-8"))
    out = {}
    for sp in (cfg.get("lm_intake") or {}).get("network_connectors") or []:
        if sp.get("phase") != "2b":
            continue
        decl = {"ref": sp["ref"], "direction": sp["direction"], "bridge_max_edges": int(sp.get("bridge_max_edges", 2))}
        if sp.get("edge_ids"):
            decl["edge_ids"] = list(sp["edge_ids"])
        r = network_reference.resolve(decl, fc, er)
        out[sp["name"]] = {"pts": r["grade"], "widths": r["widths"], "partner": sp.get("partner"),
                           "length_m": r["stations"][-1]}
    return out


def naip_needs(cw: dict, cache: Path):
    """per carriageway: the crops its scan touches, cached or not, and the metres of line whose scan is wholly cached"""
    cached = {p.name for p in cache.glob("naip_*.npy")}
    tile_b = sorted({p.stat().st_size for p in cache.glob("naip_*.npy")})
    offs = np.arange(-naip.REACH_M, naip.REACH_M + 1e-6, 5.0)
    per, need = {}, {}
    for name, c in cw.items():
        Q, _W, S = _resample(c["pts"], c["widths"], STEP_M)
        P, _s, _t, N = naip.frames(c["pts"])
        _S2, Q2, Nn = naip.resample(P, _s, N, STEP_M)
        ok = np.ones(len(Q2), bool)
        touched = set()
        for k in range(len(Q2)):
            xs = Q2[k, 0] + offs * Nn[k, 0]
            zs = Q2[k, 1] + offs * Nn[k, 1]
            keys = set(zip(np.floor(xs / naip.TILE_M).astype(int).tolist(), np.floor(zs / naip.TILE_M).astype(int).tolist()))
            touched |= keys
            if any(f"naip_{i}_{j}.npy" not in cached for i, j in keys):
                ok[k] = False
        miss = sorted(t for t in touched if f"naip_{t[0]}_{t[1]}.npy" not in cached)
        # the cached-coverage runs (stations whose whole scan is cached), in metres along
        runs, a = [], None
        for k, v in enumerate(ok.tolist() + [False]):
            if v and a is None:
                a = k
            elif not v and a is not None:
                runs.append([round(a * STEP_M, 1), round((k - 1) * STEP_M, 1)])
                a = None
        per[name] = {"length_m": round(float(c["length_m"]), 1), "tiles_touched": len(touched),
                     "tiles_cached": len(touched) - len(miss), "tiles_missing": len(miss),
                     "stations": int(len(ok)), "stations_scan_cached": int(ok.sum()),
                     "scan_cached_runs_m": [r for r in runs if r[1] - r[0] >= 50.0]}
        for t in miss:
            need.setdefault(t, set()).add(name)
    return per, need, tile_b


def naip_item(mos, t):
    x0, z0 = t[0] * naip.TILE_M, t[1] * naip.TILE_M
    W, S = mos._ll(x0, z0)
    E, N = mos._ll(x0 + naip.TILE_M, z0 + naip.TILE_M)
    return mos._item((W + E) / 2, (S + N) / 2), [round(W, 6), round(S, 6), round(E, 6), round(N, 6)]


def ept_needs(stations, cache: Path):
    """stations: [(lon, lat, radius_m, tag)]. The walk of network_deck_lidar.fetch, offline: returns
    (nodes {key: [points, cached, tags]}, missing hierarchy pages {key: tags})"""
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    ept = json.loads((cache / "CA_SanDiegoQL2_2014-ept.json").read_text())
    b = ept["bounds"]
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    lon = np.array([s[0] for s in stations]); lat = np.array([s[1] for s in stations])
    sx, sy = to_merc.transform(lon, lat)
    scale = 1.0 / math.cos(math.radians(float(np.mean(lat))))
    pad = np.array([s[2] for s in stations]) * scale
    tags = [s[3] for s in stations]
    pmax = float(pad.max())
    tree = cKDTree(np.c_[sx, sy])
    pages = {}

    def page(key):
        if key not in pages:
            p = cache / f"ept-hierarchy-{key}.json"
            pages[key] = json.loads(p.read_text()) if p.exists() else None
        return pages[key]
    nodes, missing_pages = {}, {}

    def hit(x0, y0, sz):
        idx = tree.query_ball_point([x0 + sz / 2, y0 + sz / 2], sz * 0.7072 + pmax)
        if not idx:
            return []
        idx = np.asarray(idx)
        dx = np.maximum(np.maximum(x0 - sx[idx], 0.0), sx[idx] - (x0 + sz))
        dy = np.maximum(np.maximum(y0 - sy[idx], 0.0), sy[idx] - (y0 + sz))
        return idx[np.hypot(dx, dy) <= pad[idx]].tolist()

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        idx = hit(x0, y0, sz)
        if not idx:
            return
        if h[k] == -1:
            hp = page(k)
            if hp is None:
                missing_pages.setdefault(k, set()).update(tags[i] for i in idx)
                return
            h = hp
        if h[k] > 0:
            nodes[k] = [int(h[k]), (cache / f"{k}.laz").exists(), {tags[i] for i in idx}]
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, page("0-0-0-0"))
    return nodes, missing_pages


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    draft, cfg_p, out_p = Path(argv[0]), Path(argv[1]), Path(argv[2])
    naip_cache = Path(argv[argv.index("--naip-cache") + 1])
    ept_cache = Path(argv[argv.index("--ept-cache") + 1])
    tnm = [Path(argv[i + 1]) for i, a in enumerate(argv) if a == "--tnm"]
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    nloc = json.loads((draft / "network.local.json").read_text(encoding="utf-8"))
    lon0, lat0, mx, my = _frames(nloc)
    mos = naip.Mosaic(nloc["origin"], naip_cache)

    def ll(x, z):
        return lon0 + x / mx, lat0 + z / my

    cw = carriageways_2b(draft, cfg)
    # ---- NAIP ----
    per, need, tile_b = naip_needs(cw, naip_cache)
    tile_bytes = tile_b[-1] if tile_b else None
    items = {}
    for t, users in sorted(need.items()):
        it, bb = naip_item(mos, t)
        items.setdefault(it or "unknown", []).append({"tile": f"naip_{t[0]}_{t[1]}", "bbox_wsen": bb,
                                                      "carriageways": sorted(users)})
    # ---- EPT stations ----
    st = []
    for name, c in cw.items():
        Q, W, _S = _resample(c["pts"], c["widths"], STEP_M)
        for (x, z), w in zip(Q, W):
            lo, la = ll(x, z)
            st.append((lo, la, w / 2.0 + OUT_M, name))
    pairs = {}
    for name, c in cw.items():
        p = c.get("partner")
        if not p or p not in cw or (p, name) in pairs:
            continue
        A, WA, _ = _resample(c["pts"], c["widths"], STEP_M)
        B = np.asarray([(q[0], q[2]) for q in cw[p]["pts"]], float)
        from scipy.spatial import cKDTree
        d, j = cKDTree(B).query(A)
        n = 0
        for k in range(len(A)):
            if d[k] < PAIR_M:
                mxz = (A[k] + B[j[k]]) / 2.0
                lo, la = ll(*mxz)
                st.append((lo, la, d[k] / 2.0 + ALONG_M, f"{name}/{p} median"))
                n += 1
        pairs[(name, p)] = n
    mg = json.loads((draft / "median_ground.lidar.json").read_text(encoding="utf-8"))
    n_i8 = 0
    for pr, rec in mg["pairs"].items():
        for r in rec["rows"]:
            if r["kind"] != "unread":
                continue
            e0, e1 = r["edges"]
            x = r["x"] + r["n"][0] * (e0 + e1) / 2.0
            z = r["z"] + r["n"][1] * (e0 + e1) / 2.0
            lo, la = ll(x, z)
            st.append((lo, la, abs(e1 - e0) / 2.0 + ALONG_M, "i8 median (unread)"))
            n_i8 += 1
    nodes, mpages = ept_needs(st, ept_cache)
    cached_pts = sum(v[0] for k, v in nodes.items() if v[1])
    cached_b = sum((ept_cache / f"{k}.laz").stat().st_size for k, v in nodes.items() if v[1])
    # bytes per point over EVERY cached node the hierarchy counts (not only the ones these corridors meet)
    allc = {}
    for p in sorted(ept_cache.glob("ept-hierarchy-*.json")):
        allc.update(json.loads(p.read_text()))
    bp_n = bp_b = 0
    for f in ept_cache.glob("*.laz"):
        k = f.stem
        if allc.get(k, 0) > 0:
            bp_n += allc[k]
            bp_b += f.stat().st_size
    bpp = bp_b / bp_n if bp_n else None
    groups = {}
    for k, (npt, cached, tg) in nodes.items():
        g = sorted({t if "median" not in t else t for t in tg})
        for t in g:
            G = groups.setdefault(t, {"nodes": 0, "points": 0, "cached_nodes": 0, "cached_points": 0})
            if cached:
                G["cached_nodes"] += 1
                G["cached_points"] += npt
            else:
                G["nodes"] += 1
                G["points"] += npt
    miss = {k: v for k, v in nodes.items() if not v[1]}
    miss_pts = sum(v[0] for v in miss.values())
    # ---- D24 ----
    tnm_size = {}
    for p in tnm:
        for it in json.loads(p.read_text())["items"]:
            if "CA_SanDiegoCo_D24" in it.get("title", ""):
                tnm_size[it["title"].split()[-1]] = int(it["sizeInBytes"])
    d24_have = {f.name for f in Path(argv[argv.index("--d24") + 1]).glob("*.laz")} if "--d24" in argv else set()
    d24 = []
    for t, why in D24_HOLES.items():
        fn = f"USGS_LPC_CA_SanDiegoCo_D24_{t}.laz"
        if fn in d24_have:
            continue
        d24.append({"tile": t, "why": why, "url": D24_BASE.format(t=t),
                    "bytes": tnm_size.get(t), "size": "TNM listing (cached)" if t in tnm_size else "unknown without a request"})
    rep = {
        "tool": "tools/fwlm_downloads.py", "ledger": "0080 2b round 1", "fetched": "nothing (cached indexes only)",
        "params": {"STEP_M": STEP_M, "OUT_M": OUT_M, "ALONG_M": ALONG_M, "PAIR_M": PAIR_M, "NAIP_REACH_M": naip.REACH_M,
                   "NAIP_TILE_M": naip.TILE_M},
        "_params_doc": "STEP_M / PAIR_M / REACH_M / TILE_M are the readers' own; OUT_M = barrier_lidar's 3 m window, "
                       "ALONG_M = median_lidar's: no new number",
        "naip": {"source": NAIP_API, "year": 2022, "gsd_m": naip.MPP,
                 "tiles_missing": sum(len(v) for v in items.values()),
                 "bytes_per_tile_stored": tile_bytes,
                 "mb_stored": round(sum(len(v) for v in items.values()) * (tile_bytes or 0) / 1e6, 1),
                 "_size_doc": "stored size exact (the cached crops: (4, 1000, 1000) uint8 .npy); the response also carries "
                              "titiler's mask band (~1 MB more per tile), not verified without a request",
                 "items": {k: len(v) for k, v in items.items()},
                 "_items_doc": "a crop inside one of naip_carriageways.ITEMS is named; 'unknown' = outside the three 2022 "
                               "items the tool knows (the I 8 corridor): its item id needs a STAC search (a request)",
                 "per_carriageway": per, "tiles": items},
        "ept": {"source": EPT_URL, "nodes_missing": len(miss), "points_missing": miss_pts,
                "bytes_per_point_cached": round(bpp, 3) if bpp else None,
                "mb_estimated": round(miss_pts * bpp / 1e6, 1) if bpp else None,
                "_size_doc": "EPT's hierarchy holds point counts, not bytes: the MB is points x the cached nodes' own "
                             "bytes per point (an estimate). Exact sizes need a HEAD request per node.",
                "hierarchy_pages_missing": sorted(mpages),
                "hierarchy_pages_missing_tags": {k: sorted(v) for k, v in sorted(mpages.items())},
                "_pages_doc": "a hierarchy page the walk needs and the cache lacks: the nodes under it are unknown (not "
                              "counted); each page is one small JSON request",
                "corridor_cached": {"nodes": len(nodes) - len(miss), "points": cached_pts,
                                    "mb": round(cached_b / 1e6, 1)},
                "per_corridor": groups, "stations": len(st), "i8_median_unread_stations": n_i8,
                "pair_median_stations": {f"{a}/{b_}": n for (a, b_), n in pairs.items()},
                "nodes": sorted(f"{k} {v[0]}" for k, v in miss.items())},
        "d24": {"source": "rockyweb.usgs.gov (USGS CA_SanDiegoCo_D24, 2024; HTTP 429 to this Mac)", "tiles": d24,
                "known_bytes": sum(x["bytes"] for x in d24 if x["bytes"]),
                "unknown": [x["tile"] for x in d24 if not x["bytes"]]},
    }
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[fwlm_downloads] NAIP {rep['naip']['tiles_missing']} crops ({rep['naip']['mb_stored']} MB stored), items "
          f"{rep['naip']['items']}; EPT {len(miss)} nodes, {miss_pts:,} points (~{rep['ept']['mb_estimated']} MB at "
          f"{rep['ept']['bytes_per_point_cached']} B/pt), {len(mpages)} hierarchy page(s) missing; D24 {len(d24)} tile(s), "
          f"{rep['d24']['known_bytes'] / 1e6:.1f} MB known, unknown {rep['d24']['unknown']}")
    for name, p in per.items():
        print(f"  {name}: {p['length_m']} m, NAIP tiles {p['tiles_cached']}/{p['tiles_touched']} cached, "
              f"stations scan-cached {p['stations_scan_cached']}/{p['stations']}, runs {p['scan_cached_runs_m']}")
    for t, g in sorted(groups.items()):
        print(f"  EPT {t}: missing {g['nodes']} nodes / {g['points']:,} pts; cached {g['cached_nodes']} / {g['cached_points']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
