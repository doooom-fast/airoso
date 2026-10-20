"""Append ONE named route to airoso data/routes.json without touching the routes already in it.

Ledger 0054 P0 step 4 (2026-10-14). ``tools/route_tracks.py`` regenerates every route from ``data/osm.json`` in one
go; re-running it would re-route ``full`` / ``medium`` / ``short`` (whatever OSM has done to those nodes since
2026-08-10) and every tool that counts along them would move. This tool APPENDS instead: the existing entries are
re-serialised and proven byte-identical to the file on disk before anything is written, and the new route is
added after them.

The new route is built from a route SPEC (a readable JSON, kept with the track's data) that names, per direction,
the legs in drive order: each leg's road, its start / end junction node and the OSM way ids it may use. Each leg is
routed on a fresh OSM snapshot (``tools/fetch_osm.py``, 7-day guard) by shortest path over THOSE ways only, with
one-way tags respected (``oneway=yes|true|1`` along the node order, ``-1`` against it, ``junction=roundabout``
implied); the path must equal the spec's ``path_nodes`` when the spec carries them (the research lens's routing,
on its own fetch) — a difference stops the tool and names the leg. The finished path is re-checked edge by edge
against the one-way tags (an edge that runs against a one-way way is a FAIL even if a router produced it).

The entry has the shape every consumer of routes.json already reads — ``nodes`` / ``coords`` ([lon, lat]) / ``km``
for the route's first direction (its drive order) — plus the other direction under ``rev`` (same three keys), the
legs of both, the junction nodes and the provenance (spec, OSM snapshot, its server and data timestamp).

    python tools/route_append.py <spec.json> --osm <snapshot.json> [--routes data/routes.json] [--check]

``--check`` builds and verifies everything and writes nothing. Exit 1 on any FAIL, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
ONEWAY_FWD = {"yes", "true", "1"}
ONEWAY_REV = {"-1", "reverse"}
EARTH_R = 6371008.8          # tools/network.py's metres(): the km routes.json already carries


def metres(a, b):
    (lon1, lat1), (lon2, lat2) = a, b
    mlat = math.radians((lat1 + lat2) * 0.5)
    return math.hypot(math.radians(lon2 - lon1) * math.cos(mlat) * EARTH_R, math.radians(lat2 - lat1) * EARTH_R)


def oneway(tags: dict) -> int:
    """+1 along the node order only, -1 against it only, 0 both ways"""
    o = str(tags.get("oneway", "")).lower()
    if o in ONEWAY_FWD:
        return 1
    if o in ONEWAY_REV:
        return -1
    if tags.get("junction") in ("roundabout", "circular") and o != "no":
        return 1
    return 0


class Snapshot:
    def __init__(self, osm: dict):
        self.node = {int(k): tuple(v) for k, v in osm["nodes"].items()}
        self.ways = {int(w["id"]): w for w in osm["ways"]}

    def edges(self, way_ids):
        """directed adjacency over the given ways, one-way aware: u -> [(v, way_id, metres)]"""
        adj = {}
        for wid in way_ids:
            w = self.ways.get(int(wid))
            if w is None:
                raise LookupError(f"way {wid} is not in the OSM snapshot")
            ow, ns = oneway(w.get("tags", {})), w["nodes"]
            for a, b in zip(ns, ns[1:]):
                L = metres(self.node[a], self.node[b])
                if ow >= 0:
                    adj.setdefault(a, []).append((b, int(wid), L))
                if ow <= 0:
                    adj.setdefault(b, []).append((a, int(wid), L))
        return adj

    def route(self, start: int, goal: int, way_ids):
        adj = self.edges(way_ids)
        best, prev, pq = {start: 0.0}, {}, [(0.0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > best.get(u, float("inf")):
                continue
            if u == goal:
                break
            for v, wid, L in adj.get(u, ()):
                nd = d + L
                if nd < best.get(v, float("inf")):
                    best[v], prev[v] = nd, (u, wid)
                    heapq.heappush(pq, (nd, v))
        if goal not in best:
            raise LookupError(f"no one-way-respecting path {start} -> {goal} over ways {sorted(way_ids)}")
        path, wids = [goal], []
        while path[-1] != start:
            u, wid = prev[path[-1]]
            wids.append(wid)
            path.append(u)
        return path[::-1], wids[::-1]

    def against_oneway(self, path):
        """every consecutive pair of the path that no way allows in that direction: [(a, b, why)]"""
        if not hasattr(self, "_pairs"):
            self._pairs = {}                       # frozenset({a, b}) -> [(way_id, a_first)]
            for wid, w in self.ways.items():
                ns = w["nodes"]
                for i in range(len(ns) - 1):
                    self._pairs.setdefault(frozenset((ns[i], ns[i + 1])), []).append((wid, ns[i]))
        bad = []
        for a, b in zip(path, path[1:]):
            ok, seen = False, []
            for wid, first in self._pairs.get(frozenset((a, b)), ()):
                ow = oneway(self.ways[wid].get("tags", {}))
                along = first == a
                seen.append(wid)
                if ow == 0 or (ow == 1 and along) or (ow == -1 and not along):
                    ok = True
            if not ok:
                bad.append((a, b, f"ways {seen} are one-way the other way" if seen else "no way joins them"))
        return bad

    def length(self, path):
        return sum(metres(self.node[a], self.node[b]) for a, b in zip(path, path[1:]))


def build_direction(snap: Snapshot, legs: list[dict], label: str):
    """route each leg on its own ways; returns (nodes, legs_out, failures)"""
    nodes, out, fails = [], [], []
    for k, leg in enumerate(legs):
        start, end = int(leg["start_node"]), int(leg["end_node"])
        if nodes and nodes[-1] != start:
            fails.append(f"{label} leg {k} ({leg.get('road')}): starts at {start}, the previous leg ended at {nodes[-1]}")
        try:
            path, wids = snap.route(start, end, leg["ways"])
        except LookupError as e:
            fails.append(f"{label} leg {k} ({leg.get('road')}): {e}")
            continue
        want = leg.get("path_nodes")
        if want is not None and [int(n) for n in want] != path:
            fails.append(f"{label} leg {k} ({leg.get('road')}): the routed path ({len(path)} nodes) differs from the "
                         f"spec's path_nodes ({len(want)} nodes); first difference at index "
                         f"{next((i for i, (x, y) in enumerate(zip(path, want)) if x != int(y)), min(len(path), len(want)))}")
        unused = sorted(set(int(w) for w in leg["ways"]) - set(wids))
        if unused:
            fails.append(f"{label} leg {k} ({leg.get('road')}): spec ways never used by the path: {unused}")
        nodes.extend(path if not nodes else path[1:])
        out.append({"leg": leg.get("leg"), "road": leg.get("road"), "start_node": start, "end_node": end,
                    "ways": [int(w) for w in leg["ways"]], "length_m": round(snap.length(path), 1),
                    "nodes": len(path)})
    for a, b, why in snap.against_oneway(nodes):
        fails.append(f"{label}: edge {a} -> {b} runs against a one-way ({why})")
    return nodes, out, fails


def entry(snap: Snapshot, nodes):
    return {"nodes": nodes, "coords": [list(snap.node[n]) for n in nodes], "km": round(snap.length(nodes) / 1000, 2)}


def append(routes_path: Path, spec: dict, osm_path: Path, osm: dict, check: bool = False) -> dict:
    name = spec["name"]
    raw = routes_path.read_bytes()
    routes = json.loads(raw)
    # the existing file must be exactly what json.dumps writes for it, or the append cannot prove it left it alone
    if json.dumps(routes).encode("utf-8") != raw:
        raise SystemExit(f"[route-append] {routes_path} does not re-serialise byte-identically; refusing to rewrite it")
    if name in routes:
        raise SystemExit(f"[route-append] {routes_path} already has a route {name!r}: append only (never regenerate "
                         f"or replace a route here — every race tool counts along these node paths)")
    snap = Snapshot(osm)
    dirs = spec["directions"]
    first, second = list(dirs)[:2] if len(dirs) > 1 else (list(dirs)[0], None)
    report = {"name": name, "fails": []}
    built = {}
    for d in [first] + ([second] if second else []):
        nodes, legs_out, fails = build_direction(snap, dirs[d]["legs"], d)
        built[d] = (nodes, legs_out)
        report["fails"] += fails
        report[d] = {"km": round(snap.length(nodes) / 1000, 3), "nodes": len(nodes), "legs": legs_out}
    if report["fails"]:
        return report
    new = entry(snap, built[first][0])
    if second:
        new[second] = entry(snap, built[second][0])
    new["legs"] = {d: built[d][1] for d in built}
    new["junctions"] = spec.get("junctions", {})
    new["provenance"] = {
        "tool": "tools/route_append.py (ledger 0054 P0 step 4)",
        "spec": spec.get("_spec_path", ""), "spec_provenance": spec.get("provenance", {}),
        "osm_snapshot": osm_path.as_posix() if not osm_path.is_absolute() else osm_path.name,
        "osm_source": osm.get("source"), "osm_base": osm.get("osm_base"), "osm_fetched_utc": osm.get("fetched_utc"),
        "drive_order": first, "oneway": "every edge checked against its way's oneway tag (none against)",
    }
    out = dict(routes)
    out[name] = new
    text = json.dumps(out).encode("utf-8")
    # proof: every existing route re-serialises to the same bytes inside the new file, and the old file minus its
    # closing brace is a prefix of the new one (the append only adds after it)
    for k in routes:
        assert json.dumps(json.loads(text)[k]) == json.dumps(routes[k]), k
    assert text[:len(raw) - 1] == raw[:-1], "the append changed bytes of the existing routes"
    report["existing_byte_identical"] = sorted(routes)
    report["bytes"] = {"before": len(raw), "after": len(text)}
    if not check:
        routes_path.write_bytes(text)
        report["written"] = routes_path.as_posix()
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="append one route to data/routes.json (append only)")
    ap.add_argument("spec")
    ap.add_argument("--osm", required=True, help="OSM snapshot (tools/fetch_osm.py schema)")
    ap.add_argument("--routes", default=str(AIROSO / "data" / "routes.json"))
    ap.add_argument("--check", action="store_true", help="verify only; write nothing")
    a = ap.parse_args(argv)
    spec_p, osm_p = Path(a.spec), Path(a.osm)
    try:
        spec = json.loads(spec_p.read_text(encoding="utf-8"))
        osm = json.loads(osm_p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[route-append] cannot read inputs: {e}")
        return 2
    try:
        spec["_spec_path"] = spec_p.resolve().relative_to(AIROSO).as_posix()
    except ValueError:
        spec["_spec_path"] = spec_p.name
    try:
        rel = osm_p.resolve().relative_to(AIROSO)
    except ValueError:
        rel = osm_p
    rep = append(Path(a.routes), spec, rel if not rel.is_absolute() else osm_p, osm, check=a.check)
    for d in spec["directions"]:
        if d in rep:
            print(f"[route-append] {rep['name']}.{d}: {rep[d]['km']} km, {rep[d]['nodes']} nodes, "
                  + ", ".join(f"{L['road']} {L['length_m']} m" for L in rep[d]["legs"]))
    if rep["fails"]:
        for f in rep["fails"]:
            print(f"[route-append] FAIL {f}")
        return 1
    print(f"[route-append] existing routes byte-identical: {rep['existing_byte_identical']}; "
          f"{rep['bytes']['before']} -> {rep['bytes']['after']} bytes"
          + (f"; wrote {rep['written']}" if rep.get("written") else " (--check: nothing written)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
