"""The 2026-10-28 trace read a frame whose georeference was wrong; this puts its fixes where the road is. One run, 2026-10-31.

The USGS ImageServer answered the export (bbox -83.6700,42.5630,-83.6570,42.5770 at 2130 x 3112, EPSG:4326) with SQUARE-DEGREE
pixels, widening the extent to fit: 0.013 deg over 2130 px is 6.103e-6 deg/px, so the raster's 3112 rows span 0.018994 deg of
latitude about the same centre, not the 0.014 the request named. to_fixes.py took the requested corners as the raster's, so every
latitude was squashed about 42.5700 by 0.014 / 0.018994 = 0.7371 (1 / 1.3567; cos 42.57 = 0.7365, the look of it), and any
width read across a road was scaled by its heading. Laid over Planetary Computer NAIP (the same 2022-08-16 scene in Web Mercator,
correctly georeferenced) the unsquashed line sits on the pavement end to end; the squashed one misses by up to about 190 m, which
is what route-notes.md put down to OSM. OSM was right. Lap as traced 4,076 m; unsquashed 4,913 m (GM publishes 2.9 mi = 4,667 m).

    python tracks/milford-road-course/source/trace/unsquash_frame.py     (from the airoso root; refuses a second run)

Each width, read in the frame along the scan square to the road, becomes w * F / sqrt(tx^2 + (F ty)^2) on the frame's unit tangent
(an east-west road's width was all latitude: w * F; a north-south road's none: w), then the trace's own upper clamp, scaled.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXES = HERE.parent / "mrc_fixes.json"
LAT_C = (42.5630 + 42.5770) / 2
F = (3112 * 0.013 / 2130) / 0.014
K = math.cos(math.radians(LAT_C))
SPAN = 5                  # fixes either side for the tangent
W_MAX = 16.0 * F

d = json.loads(FIXES.read_text(encoding="utf-8"))
assert max(p["lat"] for p in d) < 42.5735, "already unsquashed"
n = len(d)
out = []
for i, p in enumerate(d):
    a, b = d[(i - SPAN) % n], d[(i + SPAN) % n]
    tx, ty = (b["lon"] - a["lon"]) * K, (b["lat"] - a["lat"])
    ln = math.hypot(tx, ty) or 1.0
    tx, ty = tx / ln, ty / ln
    w = p["w"] * F / math.hypot(tx, F * ty)
    out.append({**p, "lat": round(LAT_C + (p["lat"] - LAT_C) * F, 7), "w": round(min(w, W_MAX), 2)})
FIXES.write_text(json.dumps(out), encoding="utf-8", newline="\n")
ws = sorted(p["w"] for p in out)
print(f"{n} fixes, lat {min(p['lat'] for p in out):.5f}..{max(p['lat'] for p in out):.5f}, widths {ws[0]}..{ws[-1]} median {ws[n // 2]} m")
