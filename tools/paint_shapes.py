"""route.paint's measured shapes -> plain painted lines (pure, no bpy; ledger 0093). tools/author_paint_blend.py drapes them.

A route.paint item's "lines" were local (x, z) polylines only (ledger 0079 round N: Sand Creek's medians). A line may now
also be declared where it was MEASURED, in lon/lat about data/centerline.local.json's origin (the draft's own conversion,
scripts/geometry/projection._meters_per_degree), and two shapes expand to plain lines here:

  {"pts": [[x, z], ...], "w", "double_gap_m"?}          as before (unchanged: Sand Creek's items expand to themselves)
  {"pts_lonlat": [[lon, lat], ...], "w", ...}           the same line, measured in lon/lat
  {"dots_lonlat": [[lon, lat], ...], "size_m": d}       one d x d square per point, its sides along the lap's tangent at
                                                        the nearest centreline segment (a grid mark)
  {"hatch": {"polygon_lonlat": [...], "spacing_m": p,   a gore: stripes every p m at angle_deg to the lap's tangent at the
             "angle_deg": a, "outline": true}, "w"}     polygon's centroid, clipped to the polygon, and its outline

Every expanded line keeps the source line's "color" and "w". A hatch piece shorter than its own width is not drawn.
"""
from __future__ import annotations

import math

HATCH_MIN_M = 1e-6


def meters_per_degree(lat0: float) -> tuple[float, float]:
    """scripts/geometry/projection._meters_per_degree, restated (Blender's python loads this module bare)"""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def to_xz(origin: dict, q) -> tuple[float, float]:
    m_lon, m_lat = meters_per_degree(float(origin["lat"]))
    return (float(q[0]) - float(origin["lon"])) * m_lon, (float(q[1]) - float(origin["lat"])) * m_lat


def needs_line(item: dict) -> bool:
    """does any line of this item need data/centerline.local.json (lon/lat, dots, hatch)?"""
    return any(k in ln for ln in item.get("lines") or [] for k in ("pts_lonlat", "dots_lonlat", "hatch"))


def tangent_at(line_pts, x: float, z: float) -> tuple[float, float]:
    """the unit tangent (x, z) of the centreline segment (engine (x, y, z) points) nearest (x, z)"""
    best = None
    for a, b in zip(line_pts, line_pts[1:]):
        ex, ez = b[0] - a[0], b[2] - a[2]
        L2 = ex * ex + ez * ez
        if L2 <= 0:
            continue
        t = max(0.0, min(1.0, ((x - a[0]) * ex + (z - a[2]) * ez) / L2))
        d2 = (x - a[0] - ex * t) ** 2 + (z - a[2] - ez * t) ** 2
        if best is None or d2 < best[0]:
            best = (d2, ex, ez)
    if best is None:
        raise ValueError("no centreline segment")
    L = math.hypot(best[1], best[2])
    return best[1] / L, best[2] / L


def clip_line_to_polygon(poly, p, u) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """the pieces of the infinite line p + t u inside a simple polygon (even-odd), as (start, end) pairs"""
    ts = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ez = b[0] - a[0], b[1] - a[1]
        den = u[0] * ez - u[1] * ex
        if abs(den) < 1e-12:
            continue
        wx, wz = a[0] - p[0], a[1] - p[1]
        t = (wx * ez - wz * ex) / den
        s = (wx * u[1] - wz * u[0]) / den
        if 0.0 <= s < 1.0:
            ts.append(t)
    ts.sort()
    out = []
    for k in range(0, len(ts) - 1, 2):
        t0, t1 = ts[k], ts[k + 1]
        if t1 - t0 > HATCH_MIN_M:
            out.append(((p[0] + u[0] * t0, p[1] + u[1] * t0), (p[0] + u[0] * t1, p[1] + u[1] * t1)))
    return out


def hatch_lines(poly, spacing: float, ux: float, uz: float) -> list[list[tuple[float, float]]]:
    """stripes along (ux, uz) every ``spacing`` m across the polygon, clipped to it"""
    nx, nz = -uz, ux
    cx = sum(x for x, _ in poly) / len(poly)
    cz = sum(z for _, z in poly) / len(poly)
    offs = [(x - cx) * nx + (z - cz) * nz for x, z in poly]
    out = []
    for k in range(math.ceil(min(offs) / spacing), math.floor(max(offs) / spacing) + 1):
        p = (cx + nx * k * spacing, cz + nz * k * spacing)
        for a, b in clip_line_to_polygon(poly, p, (ux, uz)):
            out.append([a, b])
    return out


def expand_line(line: dict, origin: dict | None, line_pts) -> list[dict]:
    """one declared line -> the plain lines it paints ({"pts": [(x, z), ...], "w", "color", "double_gap_m"?})"""
    keep = {k: line[k] for k in ("color", "w", "double_gap_m") if k in line}
    w = float(line.get("w", 0.12))
    if "pts" in line:
        return [dict(keep, pts=[(float(p[0]), float(p[1])) for p in line["pts"]])]
    if origin is None:
        raise ValueError("a lon/lat paint line needs data/centerline.local.json's origin")
    if "pts_lonlat" in line:
        return [dict(keep, pts=[to_xz(origin, q) for q in line["pts_lonlat"]])]
    if "dots_lonlat" in line:
        d = float(line.get("size_m", w))
        out = []
        for q in line["dots_lonlat"]:
            x, z = to_xz(origin, q)
            tx, tz = tangent_at(line_pts, x, z)
            out.append(dict(keep, w=d, pts=[(x - tx * d / 2.0, z - tz * d / 2.0), (x + tx * d / 2.0, z + tz * d / 2.0)]))
        return out
    if "hatch" in line:
        h = line["hatch"]
        poly = [to_xz(origin, q) for q in h["polygon_lonlat"]]
        if len(poly) < 3:
            raise ValueError("a hatch polygon needs 3 or more points")
        cx = sum(x for x, _ in poly) / len(poly)
        cz = sum(z for _, z in poly) / len(poly)
        tx, tz = tangent_at(line_pts, cx, cz)
        a = math.radians(float(h.get("angle_deg", 45.0)))
        ux, uz = tx * math.cos(a) - tz * math.sin(a), tx * math.sin(a) + tz * math.cos(a)
        out = [dict(keep, pts=seg) for seg in hatch_lines(poly, float(h["spacing_m"]), ux, uz)
               if math.dist(seg[0], seg[1]) >= w]
        if h.get("outline", True):
            out.append(dict(keep, pts=poly + [poly[0]]))
        return out
    raise ValueError(f"a paint line needs pts, pts_lonlat, dots_lonlat or hatch (got {sorted(line)})")


def expand(item: dict, origin: dict | None = None, line_pts=None) -> list[dict]:
    out = []
    for ln in item.get("lines") or []:
        out += expand_line(ln, origin, line_pts)
    return out
