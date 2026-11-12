"""Name the vertices behind Lake Murray's standing red gates, off the BUILT gate OBJ (ledger 0065, the keep-roads candidate).

The K, I and F checks of scripts/geometry/audit_mesh.py and drive_test's ground-on-top, run the same way, but writing out WHERE:
    K  a kerb vertex more than 0.10 m above the carriageway under it, outside a declared island
    I  a sidewalk vertex more than 0.08 m above pavement with pavement at like height on both sides of it
    F  a curb vertex at the road's edge with neither road nor ground within 0.5 m of its height
    S  a ground vertex over a road surface, at or above it, within the stations drive_test names

    python tools/red_repairs.py <project-dir>       -> data/red_repairs.plan.json (+ a summary by cluster)

tools/red_repairs_blend.py applies the plan to the prepped scene.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))
from scripts.geometry.audit_mesh import _hash, _obj_groups, _obj_tris, _surf_at, _tri_hash  # noqa: E402
from scripts.geometry.median_zone import MedianZone  # noqa: E402

KERB_STAND_M = 0.10
SW_RISE_M = 0.08
TOP_BAND = 0.20
CURB_REACH, EDGE_REACH = 3.5, 2.0


def nearest_y(h, x, z, reach, cell):
    out = []
    r = int(reach // cell) + 1
    c = (int(x // cell), int(z // cell))
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            for q in h.get((c[0] + dx, c[1] + dz), ()):
                if math.hypot(q[0] - x, q[2] - z) <= reach:
                    out.append(q[1])
    return out


def clusters(rows, reach=25.0):
    out = []
    for r in rows:
        for c in out:
            if math.hypot(c["x"] - r[0], c["z"] - r[2]) <= reach:
                c["n"] += 1
                c["worst"] = max(c["worst"], r[3])
                break
        else:
            out.append({"x": round(r[0], 1), "z": round(r[2], 1), "y": round(r[1], 2), "n": 1, "worst": r[3]})
    return out


def main(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    objp = data / "track.obj"
    g = _obj_groups(objp, ("1ROAD", "1GRASS", "1KERB"))
    zone = MedianZone.load(proj, layout=None)
    in_island = zone.contains if zone else (lambda x, z: False)
    carriage = _tri_hash(list(_obj_tris(objp, ("1ROAD",), exclude=("1ROAD_SHOULDER",))), 8.0)
    road4, grass4, curb4 = _hash(g["1ROAD"], 4.0), _hash(g["1GRASS"], 4.0), _hash(g["1KERB"], 4.0)

    k_rows, f_rows = [], []
    for x, y, z in g["1KERB"]:
        if not in_island(x, z):
            ry = _surf_at(carriage, 8.0, x, z, y, dy_max=1.2)
            if ry is not None and y - ry > KERB_STAND_M:
                k_rows.append((x, y, z, round(y - ry, 3)))
        col = nearest_y(curb4, x, z, 1.0, 4.0)
        if col and max(col) - y > TOP_BAND:
            continue
        at_edge = nearest_y(road4, x, z, EDGE_REACH, 4.0)
        if not at_edge:
            continue
        near_g = any(abs(y - ry) < 0.5 for ry in nearest_y(grass4, x, z, CURB_REACH, 4.0))
        if not (any(abs(y - ry) < 0.5 for ry in at_edge) or near_g):
            f_rows.append((x, y, z, round(min(abs(y - ry) for ry in at_edge), 3)))

    i_rows = []
    all_road = _tri_hash(list(_obj_tris(objp, ("1ROAD",))), 4.0)
    for x, y, z in _obj_groups(objp, ("1KERB_SIDEWALK",))["1KERB_SIDEWALK"]:
        if in_island(x, z):
            continue
        ry = _surf_at(all_road, 4.0, x, z, y, dy_max=3.0)
        if ry is None or y - ry <= SW_RISE_M:
            continue
        for adeg in range(0, 180, 30):
            dx, dz = 3.5 * math.cos(math.radians(adeg)), 3.5 * math.sin(math.radians(adeg))
            a = _surf_at(all_road, 4.0, x + dx, z + dz, y, dy_max=3.0)
            b = _surf_at(all_road, 4.0, x - dx, z - dz, y, dy_max=3.0)
            if a is not None and b is not None and abs(a - b) < 0.5:
                i_rows.append((x, y, z, round(y - ry, 3)))
                break

    # S: the ground on top, at the places drive_test names on every layout
    gc = json.loads((data / "gate_centerline.json").read_text(encoding="utf-8"))
    P = gc["points_xyz_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.dist(a, b))
    lap = st[-1]
    spots = []
    for f, rev in (("drive_test.street.json", False), ("drive_test.race_cw.json", False), ("drive_test.race_acw.json", None)):
        p = data / f
        if not p.exists():
            continue
        rep = json.loads(p.read_text(encoding="utf-8"))
        if rev is None:
            rev = rep.get("direction") == "reverse"
        for s, _off, _owner in rep["worst"]["soft_top"]:
            s = lap - s if rev else s
            i = min(range(len(st)), key=lambda k: abs(st[k] - s))
            spots.append((P[i][0], P[i][1], P[i][2], round(s, 1)))
    s_rows = clusters(spots, 40.0)

    plan = {"_doc": "tools/red_repairs.py: the vertices behind the K / I / F audit counts and the ground-on-top stations, off the built gate OBJ",
            "K": k_rows, "I": i_rows, "F": f_rows, "S_spots": s_rows}
    (data / "red_repairs.plan.json").write_text(json.dumps(plan), encoding="utf-8")
    for tag, rows in (("K kerb in carriageway", k_rows), ("I sidewalk isolating", i_rows), ("F curb not flush", f_rows)):
        print(f"{tag}: {len(rows)}")
        for c in clusters(rows):
            print(f"   ({c['x']}, {c['z']}) y {c['y']}: {c['n']} verts, worst {c['worst']} m")
    print("S ground on top:")
    for c in s_rows:
        print(f"   ({c['x']}, {c['z']}) y {c['y']}: {c['n']} stations")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/red_repairs.py <project-dir>")
    main(sys.argv[1])
