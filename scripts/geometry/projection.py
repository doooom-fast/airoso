"""Project lat/lon/elev -> local meters about an origin, in AC's Y-up frame.

We build in a local ENU tangent plane centered on the centerline centroid:
  X = east (m),  Y = up (m, height above the track's lowest point),  Z = north (m).
This frame is true-north-aligned by construction, so ``true_north_rotation_deg = 0`` (the kn5 export
handles any AC axis flip later). The origin (lon0, lat0, elev0) is written to data/ so every later
phase projects identically. Metres-per-degree use the standard WGS84 series (sub-metre over a few km).

Run:  python -m scripts.geometry.projection projects/sand-creek-raceway
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from scripts.config import load_config

Vertex = tuple[float, float]



def slew_limit_widths(widths_m: list[float], points_xyz_m: list, rate: float = 0.25) -> list[float]:
    """Cap how fast road width may change: ``rate`` metres of width per metre travelled.

    OSM lane-derived widths step instantly at junction pads — Lake Murray's College Avenue went
    13 -> 30 m across a single 3 m vertex, and swept into a ribbon that reads as a sawtooth edge on
    a road that should simply stay wide (Kevin, driving v0.21.0). Real pavement opens out over a
    transition, so limit the rate rather than the value: the envelope is untouched (9-30 m stays
    9-30 m), only the approach to it is smoothed. Applied forward and backward until stable so a
    step is ramped from whichever side is lower.

    Measured on the Lake Murray loop: 105 vertex-to-vertex jumps over 1 m -> 0, worst step 21.0 m
    -> 0.75 m.
    """
    n = len(widths_m)
    if n < 2 or len(points_xyz_m) != n:
        return list(widths_m)
    import math as _m
    w = list(widths_m)
    seg = [_m.hypot(points_xyz_m[i + 1][0] - points_xyz_m[i][0],
                    points_xyz_m[i + 1][2] - points_xyz_m[i][2]) for i in range(n - 1)]
    for _ in range(3):
        for i in range(n - 1):
            lim = w[i] + rate * seg[i]
            if w[i + 1] > lim:
                w[i + 1] = lim
        for i in range(n - 2, -1, -1):
            lim = w[i + 1] + rate * seg[i]
            if w[i] > lim:
                w[i] = lim
    return [round(v, 2) for v in w]

def centroid(points: list[Vertex]) -> Vertex:
    """Mean lon/lat of the centerline — the default projection origin."""
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def in_local_order(local: dict, per_point: list) -> list:
    """Re-order a per-point array written in centerline.geojson order (centerline.elevation.json's
    ``z_raw_m`` / ``z_smooth_m`` / ``distance_m`` — the elevation stage runs BEFORE this one) into
    centerline.local.json's order.

    ``route.reverse`` and ``route.start_at`` are applied here, in projection, after the elevation file is
    written, so a reader that pairs the two files by index is wrong by the whole rotation. High Plains
    2026-10-29 (ledger 0060): the ring was rotated by 815 of 1,074 points to the real start line, and
    build_mesh's bridge detector read the bare earth 2.4 km along the lap under every road point —
    an invented 549 m valley, a 'deck + piers, no fill' bridge over real ground, kn5_ground_check
    road-over-ground p95 0.60 m; drive_test's replication read 14.6 m against the same misaligned
    profile (Exotics' 1.79 m and every earlier High Plains run were the same artefact). ``build`` records
    the permutation as ``source_index`` (local point i came from geojson/elevation point
    ``source_index[i]``); without one (no re-ordering, or an older file) this is the identity. A
    length mismatch is left to the caller's own guard."""
    idx = local.get("source_index") if isinstance(local, dict) else None
    if not idx or len(idx) != len(per_point) or min(idx) < 0 or max(idx) >= len(per_point):
        return list(per_point)
    return [per_point[j] for j in idx]


def _meters_per_degree(lat0: float) -> tuple[float, float]:
    """(m_per_deg_lon, m_per_deg_lat) at latitude lat0 — WGS84 series, accurate to <1 m."""
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


def project_to_local(
    lonlat: list[Vertex],
    z: list[float],
    origin: Vertex,
    elev0: float,
) -> list[tuple[float, float, float]]:
    """Project (lon, lat) + elevation to local ENU meters about ``origin`` (X-east, Y-up, Z-north)."""
    lon0, lat0 = origin
    m_lon, m_lat = _meters_per_degree(lat0)
    return [((lon - lon0) * m_lon, elev - elev0, (lat - lat0) * m_lat)
            for (lon, lat), elev in zip(lonlat, z)]


def build(project_dir: str | Path) -> dict:
    """Phase 3: project centerline (xy from Phase 1 + z from Phase 2) to local meters; set origin/north."""
    project_dir = Path(project_dir)
    data = project_dir / "data"
    cfg = load_config(project_dir)

    gj = json.loads((data / "centerline.geojson").read_text(encoding="utf-8"))
    full = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
    coords = [(lon, lat) for lon, lat in full["geometry"]["coordinates"]]
    widths = full["properties"].get("widths_m") or [cfg.default_width_m] * len(coords)

    elev = json.loads((data / "centerline.elevation.json").read_text(encoding="utf-8"))
    z = elev["z_smooth_m"]

    # ROUTE ORIENTATION — applied here (not just in the OSM gps stage) so EVERY source type
    # (aerial trace, KML, GPS drive) gets it, and the parallel widths/elevation arrays stay aligned.
    #   route.reverse  = true       -> run the lap in the opposite direction (the REAL race direction;
    #                                  practicing a circuit backwards is worthless).
    #   route.start_at = [lat, lon] -> rotate the ring so station 0 (start/finish, pits, hotlap spawn)
    #                                  sits at the real start line.
    route = cfg.raw.get("route", {}) or {}
    # source_index: which centerline.geojson / centerline.elevation.json point each local point came from.
    # The elevation file stays in geojson order; anything pairing it with the local line goes through
    # in_local_order (build_mesh's bridge detector, drive_test's replication — ledger 0060, High Plains).
    idx = list(range(len(coords)))
    reversed_, rotated_by = False, 0
    if route.get("reverse") or route.get("start_at"):
        was_closed = len(coords) > 2 and coords[0] == coords[-1]
        if was_closed:
            coords, widths, z, idx = coords[:-1], widths[:-1], z[:-1], idx[:-1]
        if route.get("reverse"):
            coords, widths, z, idx = coords[::-1], widths[::-1], z[::-1], idx[::-1]
            reversed_ = True
            print("  [projection] route.reverse: lap direction flipped")
        sa = route.get("start_at")
        if sa and cfg.loop and len(coords) > 2:
            m_lon, m_lat = _meters_per_degree(float(sa[0]))
            k = min(range(len(coords)),
                    key=lambda i: ((coords[i][0] - float(sa[1])) * m_lon) ** 2
                                + ((coords[i][1] - float(sa[0])) * m_lat) ** 2)
            if k:
                coords, widths, z, idx = (coords[k:] + coords[:k], widths[k:] + widths[:k], z[k:] + z[:k],
                                          idx[k:] + idx[:k])
                rotated_by = k
                print(f"  [projection] route.start_at: ring rotated by {k} points to the real start line")
        if was_closed:
            coords, widths, z, idx = coords + [coords[0]], widths + [widths[0]], z + [z[0]], idx + [idx[0]]

    # origin: default = centroid of THIS centerline; but config.origin may pin a SHARED origin (a
    # {lon,lat,elev_m} dict) so a detailed track builds in another map's frame (K10 merge) — its mesh
    # then lands directly in that frame, ready to import into one shared kn5 with no post-translation.
    origin_cfg = cfg.raw.get("origin", "centroid")
    if isinstance(origin_cfg, dict) and "lon" in origin_cfg and "lat" in origin_cfg:
        origin = (float(origin_cfg["lon"]), float(origin_cfg["lat"]))
        elev0 = float(origin_cfg.get("elev_m", min(z)))
    else:
        origin = centroid(coords)
        elev0 = min(z)
    local = project_to_local(coords, z, origin, elev0)

    xs = [p[0] for p in local]
    ys = [p[1] for p in local]
    zs = [p[2] for p in local]
    out = {
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "origin": {"lon": origin[0], "lat": origin[1], "elev_m": round(elev0, 2)},
        "true_north_rotation_deg": 0.0,
        "extent_x_m": round(max(xs) - min(xs), 1),
        "extent_z_m": round(max(zs) - min(zs), 1),
        "height_m": round(max(ys) - min(ys), 1),
        "point_count": len(local),
        "points_xyz_m": [[round(x, 2), round(y, 2), round(zz, 2)] for x, y, zz in local],
        "widths_m": widths,
    }
    if reversed_ or rotated_by:
        out["route_orientation"] = {
            "reversed": reversed_, "rotated_by_points": rotated_by,
            "_doc": ("route.reverse / route.start_at were applied here, AFTER centerline.elevation.json was written in "
                     "centerline.geojson order: local point i is geojson/elevation point source_index[i] "
                     "(scripts.geometry.projection.in_local_order)")}
        out["source_index"] = idx
    (data / "centerline.local.json").write_text(json.dumps(out), encoding="utf-8")

    # Persist the resolved true north back to the source of truth — but only when it has never been
    # resolved. The lighting stage (csp_config.resolve_true_north) owns the real value (180 on
    # mirror_x tracks); a re-run of projection must not clobber it back to 0 or the exported sun
    # sets in the east.
    if cfg.raw.get("true_north_rotation_deg") is None:
        cfg.write_back(true_north_rotation_deg=0.0)

    write_plan_svg(local, ys, data / "plan_view.svg")
    return {k: out[k] for k in ("extent_x_m", "extent_z_m", "height_m", "point_count")} | {
        "origin_lonlat": [round(origin[0], 6), round(origin[1], 6)], "true_north_deg": 0.0}


def _elev_color(t: float) -> str:
    """t in [0,1] -> blue(low) → green → red(high)."""
    if t < 0.5:
        u = t / 0.5
        r, g, b = int(40 + u * 20), int(120 + u * 135), int(220 - u * 120)
    else:
        u = (t - 0.5) / 0.5
        r, g, b = int(60 + u * 195), int(255 - u * 165), int(100 - u * 60)
    return f"#{r:02x}{g:02x}{b:02x}"


def write_plan_svg(local: list[tuple[float, float, float]], ys: list[float], path: Path, size: int = 900) -> None:
    """Top-down plan (X east →, Z north ↑) with each segment colored by elevation."""
    xs = [p[0] for p in local]
    zs = [p[2] for p in local]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    miny, maxy = min(ys), max(ys)
    yr = (maxy - miny) or 1.0
    pad = 30
    scale = (size - 2 * pad) / max(maxx - minx, maxz - minz)
    W = (maxx - minx) * scale + 2 * pad
    H = (maxz - minz) * scale + 2 * pad

    def proj(p: tuple[float, float, float]) -> tuple[float, float]:
        x = pad + (p[0] - minx) * scale
        y = H - pad - (p[2] - minz) * scale  # north up
        return round(x, 1), round(y, 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
             f'viewBox="0 0 {W:.0f} {H:.0f}"><rect width="100%" height="100%" fill="#10151b"/>']
    pts = [proj(p) for p in local]
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        col = _elev_color((ys[i] - miny) / yr)
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="3"/>')
    sx, sy = pts[0]
    parts.append(f'<circle cx="{sx}" cy="{sy}" r="5" fill="#ffffff"/>')
    # 500 m scale bar
    bar = 500 * scale
    parts.append(f'<line x1="{pad}" y1="{H - 12}" x2="{pad + bar}" y2="{H - 12}" stroke="#cdd6e0" stroke-width="2"/>')
    parts.append(f'<text x="{pad}" y="{H - 16}" fill="#cdd6e0" font-size="11" font-family="monospace">500 m</text>')
    parts.append("</svg>")
    path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m scripts.geometry.projection <project-dir>")
    stats = build(sys.argv[1])
    print("wrote data/centerline.local.json, plan_view.svg; set true_north_rotation_deg in config")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
