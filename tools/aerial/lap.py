"""The lap the aerial windows are laid along: a centreline's stations and its UTM positions.

Stations are metres from geojson v0 in a plan frame: equirectangular about the centreline's plain
lon/lat mean (every vertex, the closing duplicate included; that is how the aerial pass measured, and
the stations agree with tools/fit_hairpins.py's to well under 0.1 m). Positions are UTM 13N on GRS80
with NO datum shift (the OSM frame put on the imagery grid); subtract the registration offset to reach
the imagery frame.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import geo


class Lap:
    def __init__(self, path):
        g = json.loads(Path(path).read_text(encoding="utf-8"))
        f = next((x for x in g["features"] if (x.get("properties") or {}).get("kind") == "full"), None)
        if f is None:
            f = next(x for x in g["features"] if (x.get("geometry") or {}).get("type") == "LineString")
        self.ll = [(float(c[0]), float(c[1])) for c in f["geometry"]["coordinates"]]
        n = len(self.ll)
        lon0 = sum(p[0] for p in self.ll) / n
        lat0 = sum(p[1] for p in self.ll) / n
        mlon, mlat = geo.meters_per_degree(lat0)
        self.plan = [((lo - lon0) * mlon, (la - lat0) * mlat) for lo, la in self.ll]
        self.st = [0.0]
        for i in range(1, n):
            self.st.append(self.st[-1] + geo.dist(self.plan[i], self.plan[i - 1]))
        self.utm = [geo.to_utm(lo, la) for lo, la in self.ll]
        self.length = self.st[-1]

    def index_at(self, s):
        lo, hi = 0, len(self.st) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.st[mid] <= s:
                lo = mid
            else:
                hi = mid
        return lo

    def at(self, s):
        """UTM position + unit tangent at station s."""
        i = self.index_at(s)
        j = min(i + 1, len(self.st) - 1)
        t = 0 if self.st[j] == self.st[i] else (s - self.st[i]) / (self.st[j] - self.st[i])
        a, b = self.utm[i], self.utm[j]
        p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        i0 = self.index_at(max(0, s - 4))
        i1 = min(self.index_at(s + 4) + 1, len(self.utm) - 1)
        dx = self.utm[i1][0] - self.utm[i0][0]
        dy = self.utm[i1][1] - self.utm[i0][1]
        L = math.hypot(dx, dy) or 1
        return p, (dx / L, dy / L)

    def utm_between(self, s0, s1):
        i0 = self.index_at(s0)
        i1 = self.index_at(s1) + 1
        return [self.utm[k] for k in range(max(0, i0), min(len(self.utm), i1 + 1))]


def osm_ways(snapshot_path, require_highway: bool = False):
    """Ways (id, tags, lon/lat, UTM) from an Overpass snapshot ({payload: {elements}} or {elements})."""
    d = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    payload = d.get("payload", d)
    out = []
    for e in payload["elements"]:
        if e["type"] != "way":
            continue
        if require_highway and not (e.get("tags") or {}).get("highway"):
            continue
        out.append({"id": e["id"], "tags": e.get("tags", {}),
                    "ll": [(n["lon"], n["lat"]) for n in e["geometry"]],
                    "utm": [geo.to_utm(n["lon"], n["lat"]) for n in e["geometry"]]})
    return out
