"""Sample the tiered terrain (ledger 0046 E1/E4): plan the multi-resolution lattice, fetch USGS 3DEP
AT every vertex it needs (cached), build each declared corridor from cached OSM ways, and write the
data files a track's assembler meshes from.

OPT-IN: a project whose ``track.config.json`` ``terrain`` block has no ``tiers`` list exits here
having touched nothing.

Writes (data/, L2 — every fetched value is cached with its provenance; a rerun fetches only what is
missing):
  terrain.samples.json.gz   the 3DEP cache: base-lattice key (I, J) -> metres, + provenance
  corridor.<name>.json      a corridor's centreline (OSM way ids, the cache it came from), its floor
                            every ``floor_step_m`` and its ``section_res_m`` cross-sections every
                            ``section_step_m`` (3DEP), and which stations 3DEP says are cut / fill
  <polyline_out>            the corridor floor as the legacy [x, y, z] polyline (e.g. data/i8.local.json),
                            re-fetched over the far box; the file it replaces is kept once as
                            <legacy_copy> (the near-road surface was graded on it)
  terrain.tiers.json.gz     the topology (vertices, triangles, physical/far split) + each vertex's 3DEP
                            height — derived, regenerable, never synced

    python -m scripts.elevation.terrain_sample <ABSOLUTE-project-dir> [--offline]

``--offline`` refuses to fetch (exit 1 listing what is missing). TLS verification is always on
(scripts.tls.https_context through usgs_3dep).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from scripts.elevation import usgs_3dep
from scripts.geometry import terrain_tiers as tt

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = "terrain.samples.json.gz"
TIERS = "terrain.tiers.json.gz"
CHUNK = 450
WORKERS = 4


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _md5_file(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --- project inputs -------------------------------------------------------------------------------


def road_inputs(proj: Path):
    """(lines, origin, input files) exactly as the loop assembler reads them: the raw mainline
    (centerline.raw.local.json, else centerline.local.json) + every connector line (+ the heightfield
    meta the lattice frame may be anchored on — the plan is stale when any of them changes)."""
    data = proj / "data"
    raw = data / "centerline.raw.local.json"
    src = raw if raw.exists() else data / "centerline.local.json"
    local = json.loads(src.read_text(encoding="utf-8"))
    lines = [([tuple(p) for p in local["points_xyz_m"]], list(local["widths_m"]))]
    files = [src]
    cp = data / "connectors.local.json"
    if cp.exists():
        files.append(cp)
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            if len(c["points_xyz_m"]) >= 2:
                lines.append(([tuple(p) for p in c["points_xyz_m"]], list(c["widths_m"])))
    if (data / "heightfield.meta.json").exists():
        files.append(data / "heightfield.meta.json")      # a heightfield frame anchors the lattice on it
    return lines, local["origin"], files


def inputs_md5(files) -> dict:
    return {Path(f).name: _md5_file(Path(f)) for f in files}


# --- 3DEP with a cache ----------------------------------------------------------------------------


class SampleCache:
    def __init__(self, path: Path, spec: tt.TierSpec, frame: tt.Frame):
        self.path = path
        self.spec = spec
        self.frame = frame
        self.h: dict[tuple[int, int], float] = {}
        self.prov = {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
                     "endpoint": usgs_3dep.GET_SAMPLES, "units": "metres above NAVD88",
                     "lattice_frame": frame.to_json(), "origin": {k: spec.origin[k] for k in ("lon", "lat")},
                     "projection": "key (I, J) -> local x = x0 + I*ux, z = z0 + J*uz (lattice_frame); "
                                   "lon = lon0 + x / m_lon, lat = lat0 + z / m_lat (meters_per_degree(lat0))",
                     "mirror_x": spec.sx < 0, "fetches": []}
        if path.exists():
            d = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
            p = d.get("_provenance", {})
            fr = p.get("lattice_frame") or []
            same = (len(fr) == 4 and all(abs(a - b) < 1e-9 for a, b in zip(fr, frame.to_json()))
                    and abs(p.get("origin", {}).get("lon", 0) - spec.origin["lon"]) < 1e-12
                    and abs(p.get("origin", {}).get("lat", 0) - spec.origin["lat"]) < 1e-12
                    and bool(p.get("mirror_x", False)) == (spec.sx < 0))
            if not same:
                raise SystemExit(f"[terrain] {path.name}: lattice/origin changed since it was cached — move it aside "
                                 f"on purpose to re-sample (cached frame {fr} @ {p.get('origin')})")
            self.prov = p
            for i, j, c in zip(d["I"], d["J"], d["h_cm"]):
                self.h[(i, j)] = c / 100.0

    def missing(self, keys):
        return [k for k in keys if k not in self.h]

    def fetch(self, keys, label: str):
        if not keys:
            return 0
        f = self.frame
        lonlat = [self.spec.to_lonlat(f.x0 + i * f.ux, f.z0 + j * f.uz) for i, j in keys]
        chunks = [list(range(a, min(a + CHUNK, len(keys)))) for a in range(0, len(keys), CHUNK)]
        t0 = time.time()

        def one(idx):
            return idx, usgs_3dep._sample_batch([lonlat[k] for k in idx], retries=4)

        none = []
        done = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for idx, vals in ex.map(one, chunks):
                for k, v in zip(idx, vals):
                    if v is None:
                        none.append(keys[k])
                    else:
                        self.h[keys[k]] = round(float(v), 2)
                done += 1
                if done % 50 == 0:
                    print(f"  [terrain] {label}: {done}/{len(chunks)} requests ({time.time() - t0:.0f} s)", flush=True)
        if none:
            raise SystemExit(f"[terrain] 3DEP returned no value for {len(none)} of {len(keys)} points ({label}); "
                             f"first {none[:5]} — no silent fill (L2)")
        self.prov["fetches"].append({"utc": _now(), "points": len(keys), "requests": len(chunks), "what": label})
        return len(keys)

    def save(self):
        ks = sorted(self.h)
        d = {"_provenance": self.prov, "I": [k[0] for k in ks], "J": [k[1] for k in ks],
             "h_cm": [int(round(self.h[k] * 100)) for k in ks]}
        self.path.write_bytes(gzip.compress(json.dumps(d, separators=(",", ":")).encode("utf-8"), 9, mtime=0))


def sample_lonlat(points, label: str):
    """3DEP at arbitrary (lon, lat) points (corridor floor + sections), no cache, fail on no-data"""
    out = []
    chunks = [points[a:a + CHUNK] for a in range(0, len(points), CHUNK)]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for vals in ex.map(lambda c: usgs_3dep._sample_batch(c, retries=4), chunks):
            out += vals
    bad = sum(1 for v in out if v is None)
    if bad:
        raise SystemExit(f"[terrain] 3DEP no-data at {bad} of {len(points)} points ({label}) — no silent fill (L2)")
    return [round(float(v), 2) for v in out]


# --- corridors from cached OSM ways ---------------------------------------------------------------


def _chains(ways, nodes):
    """directed chains of ways joined end node -> start node; [[node ids...], ...] longest first"""
    by_start = {}
    for w in ways:
        by_start.setdefault(w["nodes"][0], []).append(w)
    ends = {w["nodes"][-1] for w in ways}
    used = set()
    out = []
    for w in sorted(ways, key=lambda w: w["id"]):
        if w["id"] in used or w["nodes"][0] in ends:
            continue
        chain, ids, cur = list(w["nodes"]), [w["id"]], w
        used.add(w["id"])
        while True:
            nxt = [x for x in by_start.get(cur["nodes"][-1], []) if x["id"] not in used]
            if not nxt:
                break
            cur = sorted(nxt, key=lambda x: x["id"])[0]
            used.add(cur["id"])
            ids.append(cur["id"])
            chain += cur["nodes"][1:]
        out.append((chain, ids))
    out.sort(key=lambda c: -len(c[0]))
    return out


def _resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        while acc + L >= step and L > 0:
            t = (step - acc) / L
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            out.append(a)
            acc = 0.0
        acc += L
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > step * 0.25:
        out.append(pts[-1])
    return out


def _nearest_on(poly, p):
    best = (1e18, None)
    for a, b in zip(poly, poly[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        q = (a[0] + dx * t, a[1] + dz * t)
        d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
        if d < best[0]:
            best = (d, q)
    return best[1], math.sqrt(best[0])


def corridor_centreline(osm: dict, spec: tt.TierSpec, c: dict):
    """The corridor centreline in the local frame: the median between the two longest directed
    chains of the matching ways (a divided freeway's two carriageways), resampled at 10 m and
    clipped to the far box + 50 m. Returns (pts_local, provenance)."""
    nodes = osm["nodes"]
    hw = c.get("highway", "motorway")
    ways = [w for w in osm["ways"] if (w.get("tags") or {}).get("highway") == hw
            and (w.get("tags") or {}).get("ref") == c["ref"]
            and all(str(n) in nodes for n in w["nodes"])]
    if not ways:
        raise SystemExit(f"[terrain] corridor {c['name']}: no highway={hw} ref={c['ref']!r} ways in the OSM cache")
    chains = _chains(ways, nodes)
    if len(chains) < 2:
        raise SystemExit(f"[terrain] corridor {c['name']}: expected two carriageway chains, found {len(chains)}")
    (ca, ida), (cb, idb) = chains[0], chains[1]
    pa = [spec.to_local(*nodes[str(n)]) for n in ca]
    pb = [spec.to_local(*nodes[str(n)]) for n in cb]
    ra = _resample(pa, 10.0)
    mid = []
    for p in ra:
        q, d = _nearest_on(pb, p)
        if d < 150.0:                       # the two carriageways run abreast: their median
            mid.append(((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0))
    # where one carriageway runs on past the other's end (the cache clips ways at different nodes),
    # carry the line on along whichever chain reaches further: a single carriageway is ~15 m off the
    # median, well inside the corridor's half-width
    for end in (0, -1):
        tip = mid[end]
        tan = (mid[end][0] - mid[1 if end == 0 else -2][0], mid[end][1] - mid[1 if end == 0 else -2][1])
        L = math.hypot(*tan) or 1.0
        tan = (tan[0] / L, tan[1] / L)
        best = []
        for chain in (ra, _resample(pb, 10.0)):
            ext = [p for p in chain if (p[0] - tip[0]) * tan[0] + (p[1] - tip[1]) * tan[1] > 5.0]
            if len(ext) > len(best):
                best = ext
        best.sort(key=lambda p: (p[0] - tip[0]) * tan[0] + (p[1] - tip[1]) * tan[1])
        if end == 0:
            mid = best[::-1] + mid
        else:
            mid = mid + best
    mid = _resample(mid, 10.0)
    # light smoothing (a median of two polylines kinks where one has a node and the other not)
    sm = [mid[0]] + [((mid[k - 1][0] + 2 * mid[k][0] + mid[k + 1][0]) / 4.0,
                      (mid[k - 1][1] + 2 * mid[k][1] + mid[k + 1][1]) / 4.0) for k in range(1, len(mid) - 1)] + [mid[-1]]
    x0, z0, x1, z1 = spec.far_box_local()
    keep = [p for p in sm if x0 - 50 <= p[0] <= x1 + 50 and z0 - 50 <= p[1] <= z1 + 50]
    prov = {"source": "OpenStreetMap ways, highway=%s ref=%r, from the cached fetch" % (hw, c["ref"]),
            "osm_cache": c.get("osm_cache"), "chain_a_way_ids": ida, "chain_b_way_ids": idb,
            "ways_matched": len(ways), "method": "median of the two longest directed carriageway chains, "
            "resampled 10 m, 1-2-1 smoothed, clipped to the far box + 50 m"}
    return keep, prov


def build_corridor(proj: Path, spec: tt.TierSpec, c: dict, offline: bool, elev0: float):
    data = proj / "data"
    out = data / f"corridor.{c['name']}.json"
    osm_p = (ROOT / c["osm_cache"]) if not Path(c["osm_cache"]).is_absolute() else Path(c["osm_cache"])
    data_keys = ("name", "ref", "highway", "osm_cache", "floor_step_m", "section_step_m", "section_res_m",
                 "section_half_m", "half_width_m")
    key = {"osm_cache_md5": _md5_file(osm_p), "params": {k: c.get(k) for k in data_keys},
           "far_bbox_swne": spec.far_bbox_swne, "origin": {k: spec.origin[k] for k in ("lon", "lat")}}
    if out.exists():
        d = json.loads(out.read_text(encoding="utf-8"))
        if d.get("_key") == key:
            return d
    if offline:
        raise SystemExit(f"[terrain] --offline: {out.name} missing or stale (inputs changed)")
    osm = json.loads(osm_p.read_text(encoding="utf-8"))
    line, prov = corridor_centreline(osm, spec, c)
    # stations along the centreline
    st = [0.0]
    for a, b in zip(line, line[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

    def at(s):
        k = max(0, min(len(line) - 2, next((i for i in range(len(st) - 1) if st[i + 1] >= s), len(st) - 2)))
        L = st[k + 1] - st[k] or 1.0
        t = (s - st[k]) / L
        a, b = line[k], line[k + 1]
        tx, tz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), (tx, tz)

    fstep, sstep = float(c["floor_step_m"]), float(c["section_step_m"])
    res, half = float(c["section_res_m"]), float(c.get("section_half_m", c["half_width_m"]))
    floor_s = [k * fstep for k in range(int(st[-1] // fstep) + 1)]
    floor_xz = [at(s)[0] for s in floor_s]
    sec_s = [k * sstep for k in range(int(st[-1] // sstep) + 1)]
    offs = [-half + k * res for k in range(int(round(2 * half / res)) + 1)]
    sec_pts = []
    for s in sec_s:
        (px, pz), (tx, tz) = at(s)
        nx, nz = -tz, tx                                    # left of travel
        sec_pts += [(px + nx * o, pz + nz * o) for o in offs]
    print(f"  [terrain] corridor {c['name']}: {st[-1]:.0f} m centreline, {len(floor_s)} floor + "
          f"{len(sec_s)} x {len(offs)} section samples from 3DEP", flush=True)
    fh = sample_lonlat([spec.to_lonlat(x, z) for x, z in floor_xz], f"{c['name']} floor")
    sh = sample_lonlat([spec.to_lonlat(x, z) for x, z in sec_pts], f"{c['name']} sections")
    sections = []
    n = len(offs)
    for k, s in enumerate(sec_s):
        prof = sh[k * n:(k + 1) * n]
        mid = prof[n // 2]
        rim = [v for o, v in zip(offs, prof) if abs(o) >= half - 20.0]      # the outer 20 m each side
        lo = [v for o, v in zip(offs, prof) if abs(o) <= 15.0]
        kind = "fill" if min(lo) > max(rim) + 1.0 else ("cut" if max(lo) < min(rim) - 1.0 else "grade")
        sections.append({"s": round(s, 1), "xz": [round(c_, 2) for c_ in sec_pts[k * n + n // 2]],
                         "floor": mid, "kind": kind, "h": prof})
    d = {"_key": key, "_provenance": {**prov, "elevation": "USGS 3DEP getSamples, fetched " + _now(),
                                      "floor_step_m": fstep, "section_step_m": sstep, "section_res_m": res,
                                      "section_half_m": half},
         "centreline_local": [[round(x, 2), round(z, 2)] for x, z in line],
         "floor": [{"s": round(s, 1), "x": round(x, 2), "z": round(z, 2), "h": h}
                   for s, (x, z), h in zip(floor_s, floor_xz, fh)],
         "section_offsets_m": offs, "sections": sections,
         "summary": {kk: sum(1 for x in sections if x["kind"] == kk) for kk in ("cut", "fill", "grade")}}
    out.write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
    print(f"  [terrain] corridor {c['name']}: 3DEP sections {d['summary']} -> {out.name}")
    return d


def write_polyline(proj: Path, c: dict, cor: dict, elev0: float):
    """the corridor floor as the [x, y, z] polyline older consumers read (e.g. data/i8.local.json),
    keeping the replaced file once as ``legacy_copy``"""
    po = c.get("polyline_out")
    if not po:
        return
    p = proj / po
    if c.get("legacy_copy") and p.exists():
        lp = proj / c["legacy_copy"]
        old = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(old, list) and not lp.exists():
            lp.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  [terrain] kept the replaced {p.name} as {lp.name} (the near-road surface was graded on it)")
    pts = [[f["x"], round(f["h"] - elev0, 3), f["z"]] for f in cor["floor"]]
    p.write_text(json.dumps({"_provenance": {**cor["_provenance"], "what": "corridor floor polyline, local "
                                             "[x, y = 3DEP floor - elev0, z]", "elev0": elev0},
                             "points_xyz_m": pts}, separators=(",", ":")), encoding="utf-8")


# --- main -----------------------------------------------------------------------------------------


def run(proj: Path, offline: bool = False) -> dict | None:
    proj = Path(proj).resolve()
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    lines, origin, files = road_inputs(proj)
    spec = tt.TierSpec(cfg.get("terrain"), origin, bool(cfg.get("mirror_x", False)))
    if not spec.enabled:
        print("[terrain] terrain.tiers not declared — nothing to do (opt-in)")
        return None
    data = proj / "data"
    elev0 = float(origin["elev_m"])
    t0 = time.time()
    corridor_lines, cors = [], []
    for c in spec.corridors:
        cor = build_corridor(proj, spec, c, offline, elev0)
        write_polyline(proj, c, cor, elev0)
        cors.append(cor)
        corridor_lines.append([(x, 0.0, z) for x, z in cor["centreline_local"]])
    frame = spec.frame(tt.load_heightfield_meta(proj))
    topo = tt.Topology(spec, lines, corridor_lines, closed_first=bool(cfg.get("loop", True)), frame=frame)
    st = topo.stats()
    print(f"[terrain] topology: {st['vertices']} vertices, {st['triangles']} triangles "
          f"(physical {st['physical_vertices']} v / far {st['far_vertices']} v), leaves {st['leaves_by_cell_m']} "
          f"({time.time() - t0:.0f} s)", flush=True)
    cache = SampleCache(data / SAMPLES, spec, frame)
    miss = cache.missing(topo.vkeys)
    if miss and offline:
        raise SystemExit(f"[terrain] --offline: {len(miss)} vertices have no cached 3DEP sample")
    if miss:
        print(f"[terrain] fetching {len(miss)} missing 3DEP samples ({math.ceil(len(miss) / CHUNK)} requests)", flush=True)
        cache.fetch(miss, "tier vertices")
        cache.save()
    hs = [cache.h[k] for k in topo.vkeys]
    out = {"_provenance": {"what": "tiered terrain topology + 3DEP height at every vertex (ledger 0046)",
                           "samples": SAMPLES, "written_utc": _now()},
           "inputs_md5": inputs_md5(files),
           "frame": frame.to_json(),
           "spec": {"levels_m": spec.levels, "base_m": spec.base_m, "far_bbox_swne": spec.far_bbox_swne,
                    "tiers": spec.tiers, "tier_options": cfg["terrain"].get("tier_options"),
                    "corridors": [c["name"] for c in spec.corridors]},
           "stats": st,
           "I": [k[0] for k in topo.vkeys], "J": [k[1] for k in topo.vkeys], "h": hs,
           "keep": [1 if k else 0 for k in topo.vkeep],
           "tris": [v for t in topo.tris for v in t], "phys": [1 if p else 0 for p in topo.tri_phys]}
    (data / TIERS).write_bytes(gzip.compress(json.dumps(out, separators=(",", ":")).encode("utf-8"), 6, mtime=0))
    print(f"[terrain] wrote {TIERS}: {len(hs)} vertices, 3DEP {min(hs):.1f}..{max(hs):.1f} m "
          f"({time.time() - t0:.0f} s total)")
    return st


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python -m scripts.elevation.terrain_sample <ABSOLUTE-project-dir> [--offline]")
    run(Path(args[0]), offline="--offline" in sys.argv)


if __name__ == "__main__":
    main()
