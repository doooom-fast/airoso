"""NAIP in the track's own frame, and the per-station EDGE TRACER (ledger 0079 round J, Sand Creek; opt-in).

Kevin, 2026-11-03: "I just want real"; "Real junctions". Round I measured Quebec (grid_primary_6 / 7) and
sandcreek_quebec and found the missing piece: a lidar tile with no intensity (so tools/draft_pad_outline.py's asphalt
mask reads nothing) and a NAIP brightness rule that picks lane paint, turn-bay paint, the median's concrete and
driveway aprons as readily as the real pavement edge. This module is that piece.

  * ``Naip``: the 2023 NAIP mosaic (tracks/sand-creek/source/naip_2023_sc_z18.jpg + .georef.json, web-mercator z18
    tiles) read at local (E, N) metres through the TRACK frame (scripts.geometry.projection._meters_per_degree, the WGS84
    series; round H found the 111,320 x cos(lat) / 110,540 shortcut 0.44 % / 0.14 % off). Bilinear, vectorised.
  * ``trace_section``: one cross-section's carriageway edges. From a seed lateral (on the carriageway) it walks out on
    each side and returns the first lateral that is BOTH
      - a NAIP edge: the gray leaves the road's own band (the road median +- half the road-verge gap) and stays out for
        RUN_M (paint is a bright run narrower than that: a lane line is 0.1-0.15 m, a stop bar 0.3-0.6 m), and
      - a lidar CURB STEP: the class-2 ground across the edge rises or falls by STEP_M or more within STEP_WIN_M
        (a curb face is 0.10-0.20 m), or the lidar has no reading there;
    an edge with no step (a driveway apron, a slip lane's painted gore, a flush concrete gutter run on) is returned
    flagged ``"no_step"`` and a NAIP run that is concrete-bright on a stepless, road-level surface is classified
    ``"flush"``. The caller decides; nothing here smooths along the road.

Numbers marked [invented] are in fleet/GATES-CHANGELOG.md (round J).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
NAIP_IMAGE = AIROSO / "tracks/sand-creek/source/naip_2023_sc_z18.jpg"
NAIP_GEOREF = AIROSO / "tracks/sand-creek/source/naip_2023_sc_z18.georef.json"

RUN_M = 1.0          # [invented] a NAIP edge holds off the road band this far (paint is narrower)
STEP_M = 0.08        # [invented] a curb step: the class-2 ground changes this much ...
STEP_WIN_M = 1.0     # [invented] ... within this across the edge (a curb face 0.10-0.20 m, a gutter pan 0.6 m)
STEP_SEARCH_M = 1.0  # [invented] the step may sit this far either side of the NAIP edge (NAIP 0.46 m px, lidar 0.5 m)


def _mpd(lat):
    import sys
    sys.path.insert(0, str(AIROSO))
    from scripts.geometry.projection import _meters_per_degree
    return _meters_per_degree(lat)


class Naip:
    """NAIP gray at local (E, N) metres in the track frame (origin {"lat", "lon"})."""

    def __init__(self, origin, image=NAIP_IMAGE, georef=NAIP_GEOREF):
        import numpy as np
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        g = json.loads(Path(georef).read_text(encoding="utf-8"))
        with open(image, "rb") as fh:
            if fh.read(40).startswith(b"version https://git-lfs"):
                raise SystemExit(f"naip_edge: {image} is a Git LFS pointer (pull it, or pass the image's path)")
        self.z, self.x0, self.y0 = int(g["z"]), int(g["x0"]), int(g["y0"])
        self.a = np.asarray(Image.open(image).convert("L"), dtype=np.float32)
        self.lat0, self.lon0 = float(origin["lat"]), float(origin["lon"])
        self.m_lon, self.m_lat = _mpd(self.lat0)

    def px(self, E, N):
        import numpy as np
        lon = self.lon0 + np.asarray(E, dtype=float) / self.m_lon
        lat = np.radians(self.lat0 + np.asarray(N, dtype=float) / self.m_lat)
        tx = (lon + 180.0) / 360.0 * 2 ** self.z
        ty = (1.0 - np.log(np.tan(lat) + 1.0 / np.cos(lat)) / math.pi) / 2.0 * 2 ** self.z
        return (tx - self.x0) * 256.0, (ty - self.y0) * 256.0

    def gray(self, E, N):
        import numpy as np
        u, v = self.px(E, N)
        h, w = self.a.shape
        u = np.clip(u - 0.5, 0, w - 2.001)
        v = np.clip(v - 0.5, 0, h - 2.001)
        i, j = np.floor(u).astype(int), np.floor(v).astype(int)
        fu, fv = u - i, v - j
        a = self.a
        return (a[j, i] * (1 - fu) * (1 - fv) + a[j, i + 1] * fu * (1 - fv) + a[j + 1, i] * (1 - fu) * fv
                + a[j + 1, i + 1] * fu * fv)


def _step_near(lat, h, at, side):
    """the largest class-2 change across `at` +- STEP_SEARCH_M: (lateral, outer - inner) of the best window, or None
    when the lidar has no reading on both sides. `side` +1 walks to + lateral."""
    best = None
    for k in range(len(lat)):
        if abs(lat[k] - at) > STEP_SEARCH_M or h[k] is None:
            continue
        for q in range(len(lat)):
            d = (lat[q] - lat[k]) * side
            if 0 < d <= STEP_WIN_M and h[q] is not None:
                dh = h[q] - h[k]
                if best is None or abs(dh) > abs(best[1]):
                    best = ((lat[k] + lat[q]) / 2.0, dh)
    return best



ROAD_BAND = (150.0, 195.0)  # [invented] NAIP 2023 gray of Quebec's asphalt: the corridor histogram's peak (160-190)
MIN_RUN_M = 3.0             # [invented] a carriageway is a road run at least this wide (under one lane)


def road_runs(lat, gray, band=ROAD_BAND):
    """the road runs of one section: samples inside the gray band, closed over RUN_M (paint brighter, a car or a
    shadow darker, both narrower than RUN_M), kept when MIN_RUN_M or wider. [(lo, hi)] lateral, ascending."""
    dl = abs(lat[1] - lat[0]) if len(lat) > 1 else 0.5
    on = [band[0] <= g <= band[1] for g in gray]
    gap = max(1, int(round(RUN_M / dl)))
    k = 0
    while k < len(on):                      # close: an off gap shorter than RUN_M between two on samples
        if not on[k]:
            j = k
            while j < len(on) and not on[j]:
                j += 1
            if 0 < k and j < len(on) and j - k < gap:
                for q in range(k, j):
                    on[q] = True
            k = j
        else:
            k += 1
    runs, k = [], 0
    while k < len(on):
        if on[k]:
            j = k
            while j < len(on) and on[j]:
                j += 1
            lo, hi = lat[k] - dl / 2.0, lat[j - 1] + dl / 2.0
            if hi - lo >= MIN_RUN_M:
                runs.append((lo, hi))
            k = j
        else:
            k += 1
    return runs


def trace_section(lat, gray, h, seed, band=ROAD_BAND):
    """the carriageway at `seed`: the road run holding the seed, else the nearest one; each of its two NAIP edges checked
    against the lidar (samples: lat ascending, gray, h = class-2 median or None). Returns {"run": [lo, hi], "left":
    {"edge", "naip_edge", "kind": "curb" | "flush" | "no_step", "step_m"}, "right": {...}} (left = + lateral) or None."""
    runs = road_runs(lat, gray, band)
    if not runs:
        return None
    lo, hi = min(runs, key=lambda r: 0.0 if r[0] <= seed <= r[1] else min(abs(r[0] - seed), abs(r[1] - seed)))
    out = {"run": [round(lo, 2), round(hi, 2)]}
    for key, edge, side in (("left", hi, 1), ("right", lo, -1)):
        st = _step_near(lat, h, edge, side)
        past = [g for l, g in zip(lat, gray) if 0 < (l - edge) * side <= RUN_M]
        bright = bool(past) and min(past) > band[1]
        if st is not None and abs(st[1]) >= STEP_M:
            out[key] = {"edge": round(st[0], 2), "naip_edge": round(edge, 2), "kind": "curb", "step_m": round(st[1], 3)}
        else:
            out[key] = {"edge": round(edge, 2), "naip_edge": round(edge, 2), "kind": "flush" if bright else "no_step",
                        "step_m": None if st is None else round(st[1], 3)}
    return out
