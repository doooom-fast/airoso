"""Phase 3 Step 0.6: the tier planner's 3DEP need, counted and (with --fetch) fetched, through the plan's own code.

Runs scripts.elevation.terrain_sample's own planning steps (road_inputs, TierSpec, the I-8 corridor centreline,
Frame, planned_inputs, Topology, refine_keys, aa_keys, aa_taps, SampleCache.missing) on a project copy, exactly as
terrain_sample.run() does up to its first fetch, and never writes the project's derived files. The fetch is that
first one (``tier vertices + anti-alias taps``), sent through p3_net (one request at a time, 450 points each, the
usgs_3dep request shape) and stored as SampleCache.fetch stores it (round(v, 2), a provenance fetch record).
Not fetched (counted only): the corridor rebuild run() would do when its key goes stale, and the break-line edge
profiles (they are planned from the fetched samples, so they can only be counted after).

    python -I p3_plan.py <airoso> <proj> <report.json> [--fetch <cap-bytes> <log.jsonl> <new-samples.json.gz>]
"""
import gzip
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD_FAR_W = -117.108


def main():
    airoso, proj, rep_p = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
    fetch = "--fetch" in sys.argv
    sys.path.insert(0, str(airoso))
    sys.path.insert(0, str(HERE))
    from scripts.elevation import terrain_sample as ts
    from scripts.geometry import terrain_tiers as tt
    t0 = time.time()
    cfg = json.loads((proj / "track.config.json").read_text())
    lines, origin, files = ts.road_inputs(proj)
    spec = tt.TierSpec(cfg.get("terrain"), origin, bool(cfg.get("mirror_x", False)))
    rep = {"project": str(proj), "far_bbox_swne": spec.far_bbox_swne, "frame_pin": spec.frame_cfg.get("pin"),
           "planned_files": spec.planned_files, "corridors": []}
    corridor_lines = []
    for c in spec.corridors:
        out = proj / "data" / f"corridor.{c['name']}.json"
        osm_p = (airoso / c["osm_cache"]) if not Path(c["osm_cache"]).is_absolute() else Path(c["osm_cache"])
        data_keys = ("name", "ref", "highway", "osm_cache", "floor_step_m", "section_step_m", "section_res_m",
                     "section_half_m", "half_width_m")
        key = {"osm_cache_md5": ts._md5_file(osm_p), "params": {k: c.get(k) for k in data_keys},
               "far_bbox_swne": spec.far_bbox_swne, "origin": {k: spec.origin[k] for k in ("lon", "lat")}}
        old = json.loads(out.read_text()) if out.exists() else None
        fresh = bool(old) and old.get("_key") == key
        line, _prov = ts.corridor_centreline(json.loads(osm_p.read_text()), spec, c)
        cl = [[round(x, 2), round(z, 2)] for x, z in line]
        same_line = bool(old) and old.get("centreline_local") == cl
        st = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(line, line[1:]))
        half = float(c.get("section_half_m", c["half_width_m"]))
        n_floor = int(st // float(c["floor_step_m"])) + 1
        n_sec = (int(st // float(c["section_step_m"])) + 1) * (int(round(2 * half / float(c["section_res_m"]))) + 1)
        use = old["centreline_local"] if fresh else cl
        corridor_lines.append([(x, 0.0, z) for x, z in use])
        rep["corridors"].append({"name": c["name"], "key_fresh": fresh, "rebuilt_line_identical": same_line,
                                 "line_m": round(st, 1), "rebuild_samples": n_floor + n_sec,
                                 "rebuild_requests": -(-n_floor // ts.CHUNK) - (-n_sec // ts.CHUNK),
                                 "old_line_m": round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in
                                                         zip(old["centreline_local"], old["centreline_local"][1:])), 1)
                                 if old else None})
    frame = spec.frame(tt.load_heightfield_meta(proj))
    plan_lines, plan_files = ts.planned_inputs(proj, spec)
    topo = tt.Topology(spec, lines, corridor_lines, closed_first=bool(cfg.get("loop", True)), frame=frame,
                       plan_lines=plan_lines)
    st = topo.stats()
    rep["frame"] = frame.to_json()
    rep["plan_lines"] = len(plan_lines)
    rep["topology"] = st
    print("[p3_plan] topology", json.dumps(st), round(time.time() - t0, 1), "s", flush=True)
    cache = ts.SampleCache(proj / "data" / ts.SAMPLES, spec, frame)
    rkeys = topo.refine_keys()
    aakeys = topo.aa_keys()
    need = set(topo.vkeys) | set(rkeys) | set(tt.aa_taps(aakeys))
    miss = cache.missing(sorted(need)) if (rkeys or aakeys) else cache.missing(topo.vkeys)
    lon = [spec.to_lonlat(frame.x0 + i * frame.ux, frame.z0 + j * frame.uz) for i, j in miss]
    west = sum(1 for lo, _la in lon if lo < OLD_FAR_W)
    rep["need"] = {"vertices": len(topo.vkeys), "refine_keys": len(rkeys), "aa_keys": len(aakeys),
                   "need_total": len(need), "cached": len(cache.h), "missing": len(miss),
                   "missing_requests": -(-len(miss) // ts.CHUNK),
                   "missing_west_of_-117.108": west, "missing_east_of_-117.108": len(miss) - west,
                   "missing_lon_range": [min(l[0] for l in lon), max(l[0] for l in lon)] if lon else None,
                   "missing_lat_range": [min(l[1] for l in lon), max(l[1] for l in lon)] if lon else None}
    print("[p3_plan] need", json.dumps(rep["need"]), round(time.time() - t0, 1), "s", flush=True)
    if fetch:
        import p3_net
        k = sys.argv.index("--fetch")
        cap, log, new_p = int(sys.argv[k + 1]), sys.argv[k + 2], Path(sys.argv[k + 3])
        budget = p3_net.Budget(cap, log)
        tf = time.time()
        # resumable: every answered request is appended to <new>.part.jsonl (chunk index, its points, values)
        part = Path(str(new_p) + ".part.jsonl")
        done = {}
        if part.exists():
            for line in part.read_text().splitlines():
                rec = json.loads(line)
                done[rec["a"]] = rec
        nreq = -(-len(miss) // ts.CHUNK)
        vals = []
        for a in range(nreq):
            pts = lon[a * ts.CHUNK:(a + 1) * ts.CHUNK]
            rec = done.get(a)
            if rec is None or rec["n"] != len(pts) or rec["first"] != list(miss[a * ts.CHUNK]):
                v = p3_net.sample_batch(pts, budget)
                rec = {"a": a, "n": len(pts), "first": list(miss[a * ts.CHUNK]), "vals": v}
                with open(part, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                if (a + 1) % 25 == 0 or a + 1 == nreq:
                    print(f"  [p3_plan] {a + 1}/{nreq} requests, {budget.used} B, {budget.backoffs} back-offs, "
                          f"{time.time() - tf:.0f} s", flush=True)
            vals += rec["vals"]
        none = [kk for kk, v in zip(miss, vals) if v is None]
        rep["fetch"] = {"points": len(miss), "requests": budget.requests, "bytes": budget.used,
                        "backoffs": budget.backoffs, "no_value": len(none), "no_value_first": none[:10],
                        "seconds": round(time.time() - tf, 1), "user_agent": p3_net.UA}
        new = {"I": [], "J": [], "lon": [], "lat": [], "h_cm": []}
        for (i, j), (lo, la), v in zip(miss, lon, vals):
            if v is None:
                continue
            cache.h[(i, j)] = round(float(v), 2)
            new["I"].append(i); new["J"].append(j); new["lon"].append(round(lo, 9)); new["lat"].append(round(la, 9))
            new["h_cm"].append(int(round(round(float(v), 2) * 100)))
        cache.prov["fetches"].append({"utc": ts._now(), "points": len(miss), "requests": -(-len(miss) // ts.CHUNK),
                                      "what": "tier vertices + anti-alias taps"})
        cache.save()
        doc = {"_provenance": {"what": "EXPANSION-PHASE3-PLAN Step 0.6: the 3DEP samples the tier planner was missing "
                                       "(tier vertices + anti-alias taps), keyed on the 88-column frame",
                               "source": cache.prov["source"], "endpoint": p3_net.GET_SAMPLES,
                               "units": "metres above NAVD88 (h_cm = round(v, 2) * 100, as SampleCache)",
                               "lattice_frame": frame.to_json(), "origin": origin, "frame_pin": spec.frame_cfg.get("pin"),
                               "far_bbox_swne": spec.far_bbox_swne, "planned_files": spec.planned_files,
                               "fetched_utc": ts._now(), "user_agent": p3_net.UA},
               **new}
        new_p.write_bytes(gzip.compress(json.dumps(doc, separators=(",", ":")).encode(), 9, mtime=0))
        print("[p3_plan] fetched", json.dumps(rep["fetch"]), flush=True)
        if none:
            rep["fetch"]["note"] = "3DEP returned no value at some points: terrain_sample would stop (no silent fill)"
        # the break lines, counted on the now complete point samples (not fetched)
        if spec.breaks is not None:
            cells, bedges = ts.plan_breaks(topo, spec, frame, lines, bool(cfg.get("loop", True)), cache.h)
            fneed = sorted({kk for a, b in bedges for kk in tt.edge_fine_keys(a, b)})
            fmiss = [kk for kk in fneed if kk not in cache.fine]
            rep["breaks_not_fetched"] = {"cells": len(cells), "edges": len(bedges), "fine_needed": len(fneed),
                                         "fine_missing": len(fmiss), "requests": -(-len(fmiss) // ts.CHUNK)}
            print("[p3_plan] breaks", json.dumps(rep["breaks_not_fetched"]), flush=True)
    rep["seconds"] = round(time.time() - t0, 1)
    rep_p.write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
