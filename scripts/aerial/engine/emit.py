"""Write a measured layout in the formats the engine already reads.

  <id>.centerline.geojson  data/centerline.geojson's shape (scripts/aerial/build_aerial.py's feature, closed ring in
                           lon/lat every RESAMPLE_M, widths_m per vertex, provenance): drop it in as
                           <project>/data/centerline.geojson and the elevation -> projection -> LM intake chain runs as
                           for any aerial track;
  <id>.source.json         a drop-in ``source`` block for track.config.json (type aerial, the image, its two corner
                           control points, trace_px + trace_width_m), so ship_track.sh's draft_aerial step
                           (build_aerial) regenerates the same line from the config alone; written only for an image whose
                           lon/lat is linear in pixels (a corners crop or two control points), where that block is exact;
  <id>.layout.json         every number: the centre in ENU every 1 m, widths, pieces in order, joins, corners, the S/F.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import geom

RESAMPLE_M = 3.0


def _lonlat_ring(ortho, C):
    lon, lat = ortho.en_to_lonlat(C[:, 0], C[:, 1])
    return np.c_[lon, lat]


def centerline_geojson(ortho, C, W, path: Path, name: str, extra: dict):
    Q = geom.resample(C, RESAMPLE_M, closed=True)
    s_c = geom.cumlen(np.vstack([C, C[:1]]))
    s_q = geom.cumlen(np.vstack([Q, Q[:1]]))
    Wc = np.r_[W, W[:1]]
    Wq = np.interp(s_q, s_c, Wc)
    ring = _lonlat_ring(ortho, np.vstack([Q, Q[:1]]))
    feat = {"type": "Feature",
            "properties": {"name": "centerline", "kind": "full", "closed": True,
                           "default_width_m": round(float(np.median(W)), 2),
                           "widths_m": [round(float(w), 2) for w in Wq],
                           "length_m": round(float(s_q[-1]), 1), "point_count": int(len(ring)),
                           "source": "aerial", "trace_mode": "aerial_engine", "track_name": name, **extra},
            "geometry": {"type": "LineString", "coordinates": [[round(float(a), 8), round(float(b), 8)] for a, b in ring]}}
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}), encoding="utf-8")


def source_block(ortho, C, W, image_rel: str, path: Path):
    kind = ortho.desc.get("kind")
    if kind not in ("corners", "control_points"):     # a projected image (UTM, tiles) is not exactly a lon/lat affine
        return False
    Q = geom.resample(C, 1.0, closed=True)
    s_c = geom.cumlen(np.vstack([C, C[:1]]))
    s_q = geom.cumlen(np.vstack([Q, Q[:1]]))[:-1]
    Wq = np.interp(s_q, s_c, np.r_[W, W[:1]])
    # control points: the image's own corners in TRUE lon/lat (px_to_lonlat removes the registration shift), so the
    # corners' affine takes any image pixel to the true lon/lat of what it shows; trace_px is where each true point
    # appears in the image (en_to_px adds the shift back). Continuous coordinates: pixel centre + 0.5.
    cx = np.array([-0.5, ortho.W - 0.5])
    cy = np.array([-0.5, ortho.H - 0.5])
    lon, lat = ortho.px_to_lonlat(cx, cy)
    px, py = ortho.en_to_px(Q[:, 0], Q[:, 1])
    blk = {"type": "aerial", "screenshot": image_rel, "trace_mode_note": "measured by scripts.aerial.engine (ledger 0088)",
           "control_points": [{"px": [0, 0], "lonlat": [round(float(lon[0]), 9), round(float(lat[0]), 9)], "_corner": "NW"},
                              {"px": [ortho.W, ortho.H], "lonlat": [round(float(lon[1]), 9), round(float(lat[1]), 9)],
                               "_corner": "SE"}],
           "trace_px": [[round(float(a) + 0.5, 2), round(float(b) + 0.5, 2)] for a, b in zip(px, py)],
           "trace_width_m": [round(float(w), 2) for w in Wq]}
    path.write_text(json.dumps(blk), encoding="utf-8")
    return True
