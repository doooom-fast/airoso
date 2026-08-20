"""The street network as a real graph, with junctions as first-class objects.

Two OSM ways that share a node ID are a junction. That is the whole point of this
module, and the thing the previous pipeline threw away: it resampled every route
to a uniform 3 m polyline, which averages junctions out of existence. You cannot
build a wide, square intersection out of a strand that no longer knows an
intersection was ever there.

Nothing here smooths, resamples, or simplifies. Coordinates come out exactly as
OpenStreetMap has them.
"""

import json
import math
import os
from collections import defaultdict
from heapq import heappop, heappush

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

EARTH_R = 6371008.8


def metres(a, b):
    """Ground distance between two (lon, lat) points."""
    (lon1, lat1), (lon2, lat2) = a, b
    mlat = math.radians((lat1 + lat2) * 0.5)
    x = math.radians(lon2 - lon1) * math.cos(mlat) * EARTH_R
    y = math.radians(lat2 - lat1) * EARTH_R
    return math.hypot(x, y)


class Network:
    def __init__(self, path=None):
        with open(path or os.path.join(DATA, "osm.json"), encoding="utf-8") as f:
            raw = json.load(f)

        self.fetched = raw["fetched_utc"]
        self.node = {int(k): tuple(v) for k, v in raw["nodes"].items()}
        self.ways = {w["id"]: w for w in raw["ways"]}

        # node -> [(neighbour, way_id)] along the way's own node order
        self.adj = defaultdict(list)
        # node -> set of way ids passing through it
        self.at = defaultdict(set)
        for w in raw["ways"]:
            ns = w["nodes"]
            for n in ns:
                self.at[n].add(w["id"])
            for a, b in zip(ns, ns[1:]):
                self.adj[a].append((b, w["id"]))
                self.adj[b].append((a, w["id"]))

    # -- naming ------------------------------------------------------------

    def name(self, way_id):
        return self.ways[way_id]["tags"].get("name")

    def ways_named(self, *names):
        want = set(names)
        return [w for w in self.ways.values() if w["tags"].get("name") in want]

    def street_names(self):
        return {w["tags"].get("name") for w in self.ways.values()} - {None}

    # -- junctions ---------------------------------------------------------

    def junctions(self, name_a, name_b):
        """Every node where a way named A meets a way named B.

        Returns nodes, not an averaged point: a divided road crossing another
        divided road is genuinely several nodes, and that is real, not noise.
        """
        a_nodes = {n for w in self.ways_named(name_a) for n in w["nodes"]}
        b_nodes = {n for w in self.ways_named(name_b) for n in w["nodes"]}
        return sorted(a_nodes & b_nodes)

    def junction(self, name_a, name_b):
        """The single best junction node between two streets.

        Where a junction spans several nodes (divided roads, slip lanes), pick the
        one closest to the centroid of the cluster, so the chosen point sits in the
        middle of the real intersection rather than on one of its corners.
        """
        found = self.junctions(name_a, name_b)
        if not found:
            raise LookupError(f"no junction: {name_a!r} x {name_b!r}")
        if len(found) == 1:
            return found[0]
        pts = [self.node[n] for n in found]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        return min(found, key=lambda n: metres(self.node[n], (cx, cy)))

    def named_at(self, node):
        return sorted({self.name(w) for w in self.at[node]} - {None})

    # -- routing -----------------------------------------------------------

    def route(self, start, goal, allow=None):
        """Shortest path start -> goal, optionally restricted to named streets.

        `allow` is the set of street names the leg may use. Restricting it is what
        keeps "the Navajo leg" actually on Navajo instead of letting the router
        shortcut through a cul-de-sac that happens to be 40 m quicker.
        """
        if start == goal:
            return [start]
        ok = None if allow is None else set(allow)
        dist = {start: 0.0}
        prev = {}
        pq = [(0.0, start)]
        seen = set()
        while pq:
            d, n = heappop(pq)
            if n in seen:
                continue
            seen.add(n)
            if n == goal:
                break
            for m, wid in self.adj[n]:
                if ok is not None and self.name(wid) not in ok:
                    continue
                nd = d + metres(self.node[n], self.node[m])
                if nd < dist.get(m, float("inf")):
                    dist[m] = nd
                    prev[m] = n
                    heappush(pq, (nd, m))
        if goal not in dist:
            raise LookupError(
                f"no path {start} -> {goal}"
                + (f" within {sorted(ok)}" if ok else "")
            )
        path, n = [goal], goal
        while n != start:
            n = prev[n]
            path.append(n)
        return path[::-1]

    def length(self, nodes):
        return sum(
            metres(self.node[a], self.node[b]) for a, b in zip(nodes, nodes[1:])
        )

    def coords(self, nodes):
        return [self.node[n] for n in nodes]
