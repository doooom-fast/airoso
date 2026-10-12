"""The route a built-artifact gate walks, and the built OBJ it walks over — shared by the Lariat's Drive-1 gates
(tools/verify_road_inventory.py, tools/verify_stacked_legs.py; V3-PLAN P5, ledger 0048).

The line comes in drive_test's own order, so every gate reads the same line in the same frame as the OBJ:
``data/gate_centerline.json`` (written by scripts.modkit.kn5_to_gate_obj beside a kn5-derived OBJ, engine frame)
> ``data/finished_centerline.json`` (the line the ribbon was swept along) > ``data/centerline.local.json``
(x mirrored when the config says ``mirror_x``). The OBJ is read with drive_test's streaming reader. The route
only places the questions (where to look, which deck height window); every answer is read off the built
triangles (L5).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.geometry.drive_test import _load_obj  # noqa: E402,F401  (re-exported for the gates)
from scripts.geometry.projection import _meters_per_degree  # noqa: E402


def load_route(project: Path, cfg: dict) -> tuple[list[tuple[float, float, float]], list[float], str]:
    """(points xyz, widths, the file it came from) in the gate OBJ's frame."""
    data = Path(project) / "data"
    for name in ("gate_centerline.json", "finished_centerline.json"):
        p = data / name
        if p.exists():
            lc = json.loads(p.read_text(encoding="utf-8"))
            return [tuple(map(float, q)) for q in lc["points_xyz_m"]], [float(w) for w in lc["widths_m"]], name
    p = data / "centerline.local.json"
    if not p.exists():
        raise FileNotFoundError(f"{project}: no data/gate_centerline.json, finished_centerline.json or "
                                f"centerline.local.json — nothing to walk")
    lc = json.loads(p.read_text(encoding="utf-8"))
    m = -1.0 if cfg.get("mirror_x", False) else 1.0
    return ([(m * float(q[0]), float(q[1]), float(q[2])) for q in lc["points_xyz_m"]],
            [float(w) for w in lc["widths_m"]], "centerline.local.json")


def lonlat_to_frame(project: Path, cfg: dict):
    """A function (lon, lat) -> (x, z) in the gate OBJ's frame, from centerline.local.json's origin (projection's
    ENU: x east, z north; x mirrored under mirror_x); None when the project has no projected line yet."""
    p = Path(project) / "data" / "centerline.local.json"
    if not p.exists():
        return None
    o = json.loads(p.read_text(encoding="utf-8")).get("origin") or {}
    if "lon" not in o or "lat" not in o:
        return None
    lon0, lat0 = float(o["lon"]), float(o["lat"])
    mlon, mlat = _meters_per_degree(lat0)
    m = -1.0 if cfg.get("mirror_x", False) else 1.0
    return lambda lon, lat: (m * (lon - lon0) * mlon, (lat - lat0) * mlat)


def is_closed(pts) -> bool:
    return len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6


def stations(pts) -> list[float]:
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return st


def resample(pts, widths, step: float = 1.0):
    """(points, widths, stations) every ``step`` metres along the line (plan length), lerped; the last point kept."""
    st = stations(pts)
    lap = st[-1]
    out_p, out_w, out_s = [], [], []
    i = 1
    s = 0.0
    while s < lap - 1e-9:
        while i < len(pts) - 1 and st[i] < s:
            i += 1
        seg = max(st[i] - st[i - 1], 1e-12)
        t = min(1.0, max(0.0, (s - st[i - 1]) / seg))
        a, b = pts[i - 1], pts[i]
        out_p.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))
        out_w.append(widths[i - 1] + (widths[i] - widths[i - 1]) * t)
        out_s.append(s)
        s += step
    out_p.append(tuple(pts[-1]))
    out_w.append(widths[-1])
    out_s.append(lap)
    return out_p, out_w, out_s


def point_in_polygon(x: float, z: float, poly) -> bool:
    """Even-odd ray test in plan; ``poly`` = [(x, z), ...] (closing point optional)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i][0], poly[i][1]
        xj, zj = poly[j][0], poly[j][1]
        if (zi > z) != (zj > z):
            xc = xi + (z - zi) * (xj - xi) / (zj - zi)
            if x < xc:
                inside = not inside
        j = i
    return inside
