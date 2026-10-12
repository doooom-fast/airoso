"""The shared state of one aerial measurement run: the track's inputs and the window cache.

Inputs, all read-only:
- ``<project>/data/aerial/aerial_spec.json``: the measurement plan and the authored observations (which
  windows, where; each corner's traced stretch from the P0 fitter run; manual seeds; the text an aerial
  cannot compute: what a shadow, a pull-off or a barrier line looks like, written by eye);
- the lap: ``spec.lap_centerline`` (the OSM centreline the windows were laid along, lon/lat);
- the Overpass snapshot ``spec.osm_snapshot`` (the raw OSM ways, for registration and the overlays);
- ``<project>/track.config.json`` (corner names);
- the NAIP window cache (``--cache``), filled over TLS-verified HTTPS when fetching is allowed.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import lap as lapmod
from . import naip


class Ctx:
    def __init__(self, project_dir, cache=None, fetch: bool = True, spec_path=None):
        self.project = Path(project_dir).resolve()
        self.data = self.project / "data"
        self.spec_path = Path(spec_path) if spec_path else self.data / "aerial" / "aerial_spec.json"
        self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.cache = Path(cache) if cache else naip.default_cache()
        self.fetch = fetch
        self.cfg = json.loads((self.project / "track.config.json").read_text(encoding="utf-8"))
        self.lap_path = self.project / self.spec["lap_centerline"]
        self.L = lapmod.Lap(self.lap_path)
        self.snapshot = self.project / self.spec["osm_snapshot"]
        self.ways = lapmod.osm_ways(self.snapshot)
        self.ways_highway = [w for w in self.ways if w["tags"].get("highway")]
        self.plan = {c["id"]: c for c in self.spec["corner_plan"]["corners"]}
        self.names = {c["id"]: c.get("name") for c in (self.cfg.get("hairpin_fit") or {}).get("corners") or []}
        self.V = (0.0, 0.0)  # OSM minus imagery, metres E, N: set by the registration step
        self._win = {}
        self.models = {}
        self.polar = {}

    # ---------------------------------------------------------------- windows
    def window_spec(self, wid: str) -> dict:
        for w in self.spec["windows"]:
            if w["id"] == wid:
                return w
        raise KeyError(wid)

    def window_meta(self, wid: str) -> dict:
        w = self.window_spec(wid)
        if "centre_utm13n" in w:
            E0, N0 = w["centre_utm13n"]
        elif "corner_apex_v" in w:
            E0, N0 = self.L.utm[w["corner_apex_v"]]
        else:
            p, _ = self.L.at(w["station_m"])
            E0, N0 = p
        return naip.window(self.cache, wid, E0, N0, w["half_m"], px=self.spec["imagery"]["px_m"], fetch=self.fetch)

    def win(self, wid: str) -> naip.Win:
        if wid not in self._win:
            self._win[wid] = naip.Win(self.window_meta(wid))
        return self._win[wid]
