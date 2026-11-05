"""Measure every freeway deck from the public USGS lidar: class 17 (bridge deck) and class 2 (ground) along each
bridge edge of the network draft, every STEP_M (ledger 0080, runbook 0080-2; Kevin 2026-11-05: "I just want real").

The network draft lifts a deck by OSM ``layer`` x ``scenery.viaduct.layer_height_m`` 5.5 m: a modelled number. 3DEP is
bare earth and has no deck. The San Diego lidar classifies bridge-deck returns as ASPRS class 17, so the deck can be
read where it is.

For every edge of the draft's ``network.geojson`` whose ``layer_profile`` is non-zero anywhere, the stretch from
APPROACH_M before the first non-zero vertex to APPROACH_M past the last is stationed every STEP_M along the edge's
OSM centreline (lon / lat, so no projection of ours enters the reading). At each station:

  - every class-17 and class-2 return within RADIUS_M (horizontal) of the station;
  - the class-17 heights split into levels wherever two sorted heights are more than LEVEL_GAP_M apart (a stacked
    interchange puts two or three decks over one spot);
  - the level kept: within CONT_M along the same edge of the last reading, the level nearest it (if within CONT_DZ_M:
    the deck we are on, never one crossing over or under it); otherwise the one whose median is nearest the draft's
    own surface height there (``surface_xyz_m``,
    the layer x 5.5 m model): the model only CHOOSES between measured levels, it never supplies a height;
  - deck z = that level's median, with its return count; no class-17 return (or none within MAX_PICK_M of the model)
    = no deck reading at that station. Nothing is filled.
  - ground z = the class-2 median (the earth under the deck or beside the approach), as a datum check against the
    draft's ``at_grade_xyz_m`` (3DEP).

Writes ``<out>/deck_profiles.lidar.json``: provenance, the per-station table and a per-edge summary. Heights are the
lidar's own vertical datum (the EPT keeps the source's NAVD88 metres); the summary reports the ground-vs-3DEP offset so a
datum shift would show.

    python tools/network_deck_lidar.py <draft-data-dir> <out-dir> [--ept URL] [--edges 1,2,3] [--dry] [--cache DIR]

With --cache, --dry lists the node files in <cache>/nodes.txt; fetch them in parallel (e.g. ``xargs -P 8 curl -O``)
and rerun without --dry: Python's single TLS stream stalled on this Mac where curl ran at full speed.

Needs numpy, scipy, laspy[lazrs], pyproj.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.tls import https_context  # noqa: E402

EPT_DEFAULT = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanDiego_2015_C17_1/ept.json"
STEP_M = 5.0          # runbook 0080-2's spacing
APPROACH_M = 30.0     # [invented] read this far past the first / last bridged vertex, so the abutments are in the table
RADIUS_M = 2.0        # [invented] half a 3.65 m lane: a disc on the carriageway's OSM centreline
LEVEL_GAP_M = 2.0     # [invented] heights more than this apart are different decks (a deck slab is < 2 m thick)
MAX_PICK_M = 8.0      # [invented] a level further than this from the draft's model is another road's deck, not ours
CONT_M = 15.0         # [invented] a reading within this along the same edge is the deck we are on: its level is kept
CONT_DZ_M = 2.0       # [invented] ... unless the nearest level is further than this from it (another deck over / under)
GROUND, DECK = 2, 17  # ASPRS classes
M_PER_DEG_LAT = 110_946.0


def _m_per_deg(lat: float) -> tuple[float, float]:
    from scripts.geometry.projection import _meters_per_degree
    return _meters_per_degree(lat)


def bridge_stations(geojson: dict, edges: dict, only: set[int] | None = None):
    """[(edge id, s along the edge m, vertex index (float), lon, lat, draft surface z, draft at-grade z)] for every
    bridged stretch. The draft's z rows are index-aligned with the geojson unless the edge was trimmed (then skipped
    for the model: z None)."""
    by_id = {e["id"]: e for e in edges["edges"]}
    out = []
    for f in geojson["features"]:
        p = f["properties"]
        eid = int(p["id"])
        if only and eid not in only:
            continue
        lp = p.get("layer_profile") or []
        c = f["geometry"]["coordinates"]
        if len(lp) != len(c) or not any(v != 0 for v in lp):
            continue
        lat0 = c[0][1]
        m_lon, m_lat = _m_per_deg(lat0)
        cum = [0.0]
        for i in range(1, len(c)):
            cum.append(cum[-1] + math.hypot((c[i][0] - c[i - 1][0]) * m_lon, (c[i][1] - c[i - 1][1]) * m_lat))
        nz = [i for i, v in enumerate(lp) if v != 0]
        s0 = max(0.0, cum[nz[0]] - APPROACH_M)
        s1 = min(cum[-1], cum[nz[-1]] + APPROACH_M)
        e = by_id.get(eid)
        surf = e["surface_xyz_m"] if e and len(e["surface_xyz_m"]) == len(c) else None
        grade = e["at_grade_xyz_m"] if e and len(e["at_grade_xyz_m"]) == len(c) else None
        n = max(1, int(round((s1 - s0) / STEP_M)))
        j = 0
        for k in range(n + 1):
            s = s0 + (s1 - s0) * k / n
            while j < len(cum) - 2 and cum[j + 1] < s:
                j += 1
            seg = cum[j + 1] - cum[j]
            t = 0.0 if seg <= 0 else min(1.0, max(0.0, (s - cum[j]) / seg))
            lon = c[j][0] + (c[j + 1][0] - c[j][0]) * t
            lat = c[j][1] + (c[j + 1][1] - c[j][1]) * t
            zs = None if surf is None else surf[j][1] + (surf[j + 1][1] - surf[j][1]) * t
            zg = None if grade is None else grade[j][1] + (grade[j + 1][1] - grade[j][1]) * t
            lay = lp[j] if t < 0.5 else lp[j + 1]
            out.append((eid, round(s, 2), round(j + t, 3), lon, lat, zs, zg, lay))
    return out


def levels(zs: list[float]) -> list[tuple[float, int]]:
    """Split sorted heights at gaps > LEVEL_GAP_M: [(median, count)] low to high."""
    zs = sorted(zs)
    if not zs:
        return []
    groups, cur = [], [zs[0]]
    for z in zs[1:]:
        if z - cur[-1] > LEVEL_GAP_M:
            groups.append(cur)
            cur = []
        cur.append(z)
    groups.append(cur)
    return [(g[len(g) // 2] if len(g) % 2 else 0.5 * (g[len(g) // 2 - 1] + g[len(g) // 2]), len(g)) for g in groups]


def pick(lv: list[tuple[float, int]], model: float | None):
    if not lv:
        return None
    if model is None:
        return max(lv, key=lambda t: t[1]) if len(lv) == 1 else None
    best = min(lv, key=lambda t: abs(t[0] - model))
    return best if abs(best[0] - model) <= MAX_PICK_M else None


def fetch(ept_url: str, sts, *, dry: bool = False, cache: Path | None = None, log=print):
    """{station index: {class: [z...]}} for every EPT node within RADIUS_M of a station. ``cache``: a folder of node
    files already downloaded (``<key>.laz``, ``ept-hierarchy-<key>.json``); a missing one is fetched and kept there.
    With ``dry`` the node URLs are written to ``<cache>/nodes.txt`` (one per line) for a parallel download."""
    import numpy as np
    import laspy
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    def get(url, tries=4):
        if cache is not None:
            tail = url.rsplit("/", 2)
            cp = cache / (tail[-1] if tail[-2] == "ept-data" else f"{tail[-2]}-{tail[-1]}")
            if cp.exists() and cp.stat().st_size > 0:
                return cp.read_bytes()
            b = _get(url, tries)
            cache.mkdir(parents=True, exist_ok=True)
            cp.write_bytes(b)
            return b
        return _get(url, tries)

    def _get(url, tries):
        for a in range(tries):
            try:
                with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
                    return r.read()
            except Exception as ex:  # noqa: BLE001 - network: retry, then raise
                if a == tries - 1:
                    raise
                log(f"  retry {url.rsplit('/', 1)[-1]}: {ex}")
                time.sleep(3 * (a + 1))
    ept = json.loads(get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    if ept["srs"].get("horizontal") != "3857":
        raise SystemExit(f"network_deck_lidar: {ept_url} is not in EPSG:3857")
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    lon = np.array([s[3] for s in sts]); lat = np.array([s[4] for s in sts])
    sx, sy = to_merc.transform(lon, lat)
    scale = 1.0 / math.cos(math.radians(float(np.mean(lat))))       # web-mercator metres per ground metre
    pad = RADIUS_M * scale
    b = ept["bounds"]
    hier_files: dict = {}

    def hier(key):
        if key not in hier_files:
            hier_files[key] = json.loads(get(f"{base}/ept-hierarchy/{key}.json"))
        return hier_files[key]
    keys = []
    # a coarse prefilter tree of the stations, so the walk is quick over ~6,000 stations
    stree = cKDTree(np.c_[sx, sy])

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = hier(k)
        sz = (b[3] - b[0]) / 2 ** d
        x0, y0 = b[0] + x * sz, b[1] + y * sz
        cx, cy = x0 + sz / 2, y0 + sz / 2
        if not stree.query_ball_point([cx, cy], sz * 0.7072 + pad, return_length=True):
            return
        idx = stree.query_ball_point([cx, cy], sz * 0.7072 + pad)
        if not np.any((sx[idx] >= x0 - pad) & (sx[idx] <= x0 + sz + pad) & (sy[idx] >= y0 - pad) & (sy[idx] <= y0 + sz + pad)):
            return
        if h[k] > 0:
            keys.append((k, h[k]))
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, hier("0-0-0-0"))
    npts = sum(c for _, c in keys)
    log(f"network_deck_lidar: {len(keys)} EPT nodes ({npts:,} points) along {len(sts)} stations")
    if dry:
        if cache is not None:
            cache.mkdir(parents=True, exist_ok=True)
            (cache / "nodes.txt").write_text("".join(f"{base}/ept-data/{k}.laz\n" for k, _ in keys))
        return None, len(keys), npts
    got: dict = {}
    t0 = time.time()
    for q, (k, _) in enumerate(keys):
        las = laspy.read(io.BytesIO(get(f"{base}/ept-data/{k}.laz")))
        cls = np.asarray(las.classification)
        m = np.isin(cls, (GROUND, DECK))
        if not m.any():
            continue
        px = np.asarray(las.x)[m]; py = np.asarray(las.y)[m]; pz = np.asarray(las.z)[m]; pc = cls[m]
        hits = stree.query_ball_point(np.c_[px, py], RADIUS_M * scale)
        for pi, hs in enumerate(hits):
            for si in hs:
                got.setdefault(si, {GROUND: [], DECK: []})[int(pc[pi])].append(float(pz[pi]))
        if q % 50 == 0:
            log(f"  node {q + 1}/{len(keys)}  {time.time() - t0:.0f} s")
    return got, len(keys), npts


def build(draft: Path, out: Path, *, ept_url: str = EPT_DEFAULT, only=None, dry=False, cache=None, log=print) -> dict:
    geo = json.loads((draft / "network.geojson").read_text())
    edges = json.loads((draft / "network.edges.local.json").read_text())
    sts = bridge_stations(geo, edges, only)
    # the draft's heights are local (NAVD88 less the origin's elev_m); the lidar's are NAVD88 metres
    elev0 = float(json.loads((draft / "network.local.json").read_text())["origin"]["elev_m"])
    log(f"network_deck_lidar: {len({s[0] for s in sts})} bridge edges, {len(sts)} stations every {STEP_M} m")
    got, nn, npts = fetch(ept_url, sts, dry=dry, cache=cache, log=log)
    if dry:
        return {"nodes": nn, "points": npts, "stations": len(sts)}
    rows, per_edge = [], {}
    last = None                                     # (edge, s, z) of the last deck read on this edge
    for i, (eid, s, v, lon, lat, zs, zg, lay) in enumerate(sts):
        g = got.get(i, {GROUND: [], DECK: []})
        lv = levels(g[DECK])
        if last is not None and last[0] == eid and abs(s - last[1]) <= CONT_M and lv:
            # the deck we are on continues: the level nearest the last reading, if the deck can have got there
            near = min(lv, key=lambda t: abs(t[0] - last[2]))
            pk = near if abs(near[0] - last[2]) <= CONT_DZ_M else None
        else:
            pk = pick(lv, None if zs is None else zs + elev0)
        if pk is not None and not lay and (zg is None or abs(pk[0] - (zg + elev0)) > CONT_DZ_M):
            # off OSM's bridge (an approach station) a deck is ours only where it meets the approach's own grade;
            # higher is another road's deck crossing over this one (I 8 WB under the overpass at edge 295 s 145-155)
            pk = None
        if pk is not None:
            last = (eid, s, pk[0])
        gz = levels(g[GROUND])
        ground = gz[0][0] if gz else None          # the lowest ground level: the earth, not a retaining-wall top
        rows.append([eid, s, v, round(lon, 7), round(lat, 7), lay,
                     None if pk is None else round(pk[0], 3), 0 if pk is None else pk[1],
                     [[round(a, 2), n] for a, n in lv],
                     None if ground is None else round(ground, 3), len(g[GROUND]),
                     None if zs is None else round(zs, 3), None if zg is None else round(zg, 3)])
        pe = per_edge.setdefault(eid, {"stations": 0, "bridged": 0, "deck_read": 0, "dz_model": [], "dz_3dep": []})
        pe["stations"] += 1
        if lay:
            pe["bridged"] += 1
            if pk is not None:
                pe["deck_read"] += 1
                if zs is not None:
                    pe["dz_model"].append(pk[0] - elev0 - zs)
        if ground is not None and zg is not None and not lay:
            pe["dz_3dep"].append(ground - elev0 - zg)

    def med(a):
        a = sorted(a)
        return None if not a else round(a[len(a) // 2], 3)
    summary = {str(k): {"stations": v["stations"], "bridged": v["bridged"], "deck_read": v["deck_read"],
                        "deck_minus_model_median_m": med(v["dz_model"]),
                        "ground_minus_3dep_median_m": med(v["dz_3dep"])} for k, v in sorted(per_edge.items())}
    all_dm = [x for v in per_edge.values() for x in v["dz_model"]]
    all_dg = [x for v in per_edge.values() for x in v["dz_3dep"]]
    doc = {
        "_doc": __doc__.split("\n\n")[0],
        "ept": ept_url,
        "classes": {"deck": DECK, "ground": GROUND},
        "params": {"step_m": STEP_M, "approach_m": APPROACH_M, "radius_m": RADIUS_M, "level_gap_m": LEVEL_GAP_M,
                   "max_pick_m": MAX_PICK_M, "cont_m": CONT_M, "cont_dz_m": CONT_DZ_M,
                   "_invented": "approach_m, radius_m, level_gap_m, max_pick_m, cont_m, cont_dz_m"},
        "vertical": "deck_z, deck_levels, ground_z: the lidar's NAVD88 metres; draft_*: the draft's local Y (NAVD88 less origin elev_m)",
        "origin_elev_m": elev0,
        "columns": ["edge", "s_m", "vertex", "lon", "lat", "osm_layer", "deck_z", "deck_n", "deck_levels[[z,n]]",
                    "ground_z", "ground_n", "draft_surface_z", "draft_at_grade_z"],
        "totals": {"edges": len(per_edge), "stations": len(rows),
                   "bridged_stations": sum(v["bridged"] for v in per_edge.values()),
                   "deck_read": sum(v["deck_read"] for v in per_edge.values()),
                   "deck_minus_model_median_m": med(all_dm),
                   "deck_minus_model_p5_p95_m": None if not all_dm else
                   [round(sorted(all_dm)[int(0.05 * (len(all_dm) - 1))], 2), round(sorted(all_dm)[int(0.95 * (len(all_dm) - 1))], 2)],
                   "ground_minus_3dep_median_m": med(all_dg), "ept_nodes": nn, "ept_points": npts},
        "edges": summary,
        "stations": rows,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "deck_profiles.lidar.json").write_text(json.dumps(doc, separators=(",", ":")))
    log(json.dumps(doc["totals"]))
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("draft", type=Path, help="the network draft's data dir (network.geojson, network.edges.local.json)")
    ap.add_argument("out", type=Path)
    ap.add_argument("--ept", default=EPT_DEFAULT)
    ap.add_argument("--edges", default="")
    ap.add_argument("--dry", action="store_true", help="count the EPT nodes only (and list them in <cache>/nodes.txt)")
    ap.add_argument("--cache", type=Path, default=None, help="a folder of downloaded EPT node files")
    a = ap.parse_args(argv)
    only = {int(x) for x in a.edges.split(",") if x.strip()} or None
    build(a.draft, a.out, ept_url=a.ept, only=only, dry=a.dry, cache=a.cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
