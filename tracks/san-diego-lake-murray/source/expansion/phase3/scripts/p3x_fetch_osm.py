"""Phase 3 (EXPANSION-PHASE3-PLAN.md rev 2) Step 0.2 / 0.7 and the lamps-and-signals research, refetched through the
repo's own guarded Overpass client (scripts.gps.widths_from_osm._overpass: TLS verified, 7-day freshness guard):

  roads      tools/fetch_osm.py --service, the exact box and query of data/osm.expansion.json (2026-10-14)
  buildings  tools/fetch_buildings_cache.py, the box of data/buildings.expansion.cache.json (it already reaches
             -117.115, west of the grown box's -117.101), --compare against that cache
  lamps      node[highway=street_lamp] and node[highway=traffic_signals] in a box around the Phase 3 roads (the
             shape of source/expansion/pipeline__osm_lamps_signals.json)

One query at a time, PAUSE_S between them, a generic User-Agent (p3x_ua).

    python -I p3x_fetch_osm.py <airoso> <out-dir> <old-data-dir> [roads|buildings|lamps ...]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p3x_ua  # noqa: E402,F401  (generic User-Agent)

BOX = (32.755, -117.115, 32.85, -116.985)          # S W N E: data/osm.expansion.json + buildings.expansion.cache
LAMP_BOX = (32.783, -117.106, 32.812, -117.068)    # the Phase 3 roads' extent + ~300 m [invented margin]
PAUSE_S = 30


def main():
    airoso, out, old = sys.argv[1], sys.argv[2], sys.argv[3]
    what = sys.argv[4:] or ["roads", "buildings", "lamps"]
    sys.path.insert(0, airoso)
    sys.path.insert(0, os.path.join(airoso, "tools"))
    os.makedirs(out, exist_ok=True)
    first = True
    for w in what:
        if not first:
            time.sleep(PAUSE_S)
        first = False
        t0 = time.time()
        if w == "roads":
            import fetch_osm
            d = os.path.join(out, "osm")
            os.makedirs(d, exist_ok=True)
            fetch_osm.main(["--service", "--bbox", *map(str, BOX), "--out", os.path.join(d, "osm.expansion.json")])
        elif w == "buildings":
            import fetch_buildings_cache as fbc
            d = os.path.join(out, "buildings")
            os.makedirs(d, exist_ok=True)
            fbc.main(["--bbox", *map(str, BOX), "--out", os.path.join(d, "buildings.expansion.cache.json"),
                      "--compare", os.path.join(old, "buildings.expansion.cache.json")])
        elif w == "lamps":
            from scripts.gps import widths_from_osm as wfo
            s, wl, n, e = LAMP_BOX
            q = (f'[out:json][timeout:120];(node["highway"="street_lamp"]({s},{wl},{n},{e});'
                 f'node["highway"="traffic_signals"]({s},{wl},{n},{e}););out body;')
            payload, mirror = wfo._overpass(q, timeout=180, max_age_days=wfo.OSM_MAX_AGE_DAYS)
            age = wfo.osm_age_days(payload)
            if wfo._too_old(age, wfo.OSM_MAX_AGE_DAYS):
                raise SystemExit(f"lamps: stale answer from {mirror} ({age} days)")
            els = payload.get("elements", [])
            doc = {"source": mirror, "osm_base": wfo.osm_base(payload), "osm_age_days": age,
                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "bbox": list(LAMP_BOX),
                   "query": q, "tls": "verified (scripts.tls.https_context via scripts.gps.widths_from_osm._overpass)",
                   "street_lamps": [x for x in els if (x.get("tags") or {}).get("highway") == "street_lamp"],
                   "traffic_signals": [x for x in els if (x.get("tags") or {}).get("highway") == "traffic_signals"]}
            d = os.path.join(out, "lamps")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "osm_lamps_signals.json"), "w") as f:
                json.dump(doc, f, indent=1)
            print(f"lamps: {len(doc['street_lamps'])} street lamps, {len(doc['traffic_signals'])} signals from "
                  f"{mirror} (OSM {doc['osm_base']})", flush=True)
        print(f"[p3x_fetch_osm] {w} done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
