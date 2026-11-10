"""What stands beside the lane: the road edge and the near-road ground, REPORT ONLY (ledger 0078; no threshold, none gated).

Ledger 0078's comparison of Lake Murray v4 and v5-bare found the drive gates blind to what made v5 feel bad: v4 had a
curb at the lane edge and the ground held near road level; v5 had a paved embankment (1ROAD_shoulder) and the ground
draped down the hillside. drive_test walks the lane. This reads, at every ~``--every`` metres of the line and on both
sides, the top PHYSICAL surface every 0.5 m out to 30 m past the centre line, and reports:

  at_1m       the surface 1 m past the lane edge: lane (1ROAD road / pad / apron / mouth fill), shoulder (1ROAD_shoulder:
              road physics past the lane), kerb (1KERB / CURB), ground (1GRASS / TERRAIN), wall (1WALL / GUARDRAIL), none
  rise_2m     the highest point within 2 m past the lane edge over the lane edge (a curb reads its height)
  paved_m     how far past the lane edge a road-physics surface (lane or shoulder) continues
  h_3m/6m/10m the top surface 3 / 6 / 10 m past the lane edge, over the lane edge (+ = above)
and their distributions (shares, median, p5 / p95) — the four columns ledger 0078 compares. No verdict, exit 0.

Two front ends, one metric:
  python tools/edge_report.py <project-dir> [--every 10] [--json <out>]
        the BUILT road: data/track.obj (kn5_to_gate_obj / build_mesh) + data/gate_centerline.json (the gates' inputs)
  blender -b <file.blend> --python tools/edge_report.py -- <gate_centerline.json> [--every 10] [--json <out>]
        a blend (an authored loop.blend, an underlay), by ray casts; frame Blender x = E, y = N, z = up
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OFFS = [k * 0.5 for k in range(-60, 61)]
SKIP = ("SHOULDERUND", "MARKINGS", "YLINE", "GRASS_FAR", "LIGHTS", "LIGHTPOST", "SIGN", "ROOFTOP", "BUILDING", "FARBLOCK",
        "PALM", "TREE", "SCRUB", "BRIDGESTRUCT", "PROPCONE", "PADAPRON", "HOUSE")


def physical(name: str) -> bool:
    u = name.upper()
    if u.startswith(SKIP) or "RACE" in u or "STREETONLY" in u:
        return False              # visual-only meshes, race-layout furniture, the street-only median: not the base road
    return u.startswith(("1", "ROAD", "CURB", "TERRAIN", "GUARDRAIL"))


def cls(name):
    if name is None:
        return "none"
    u = name.upper()
    if u.startswith("1ROAD_SHOULDER"):
        return "shoulder"
    if u.startswith(("1ROAD", "ROAD")):
        return "lane"
    if u.startswith(("1KERB", "CURB")):
        return "kerb"
    if u.startswith(("1GRASS", "TERRAIN")):
        return "ground"
    if u.startswith(("1WALL", "GUARDRAIL")):
        return "wall"
    return "other"


def stations(line, every):
    P, W = line["points_xyz_m"], line["widths_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    nxt = 0.0
    for i in range(1, len(P) - 1):
        if st[i] < nxt:
            continue
        nxt = st[i] + every
        a, b = P[i - 1], P[i + 1]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        yield st[i], P[i], W[i], -tz / L, tx / L          # left normal (x = E, z = N)


def side_metrics(prof, hw, side):
    """prof: {offset: (class, height over the line)}; side +1 = left of travel, -1 = right"""
    e_h = None
    for k in range(12):                                  # the lane edge: the last lane sample inside the lane
        c = prof.get(round(side * (hw - 0.5 - 0.5 * k) * 2) / 2)
        if c and c[0] == "lane" and c[1] is not None:
            e_h = c[1]
            break
    if e_h is None:
        return None
    o = round(hw * 2) / 2
    paved, k = 0.0, 0.0
    while abs(o + k) <= 30:
        c = prof.get(side * (o + k))
        if c is None or c[0] not in ("lane", "shoulder"):
            break
        paved = k
        k += 0.5
    rise = 0.0
    for k in (x * 0.5 for x in range(0, 5)):
        c = prof.get(side * (o + k))
        if c and c[1] is not None:
            rise = max(rise, c[1] - e_h)
    out = {"at_1m": (prof.get(side * (o + 1.0)) or ("none", None))[0], "rise_2m": rise, "paved_m": paved}
    for d in (3, 6, 10):
        c = prof.get(side * (o + d))
        out[f"h_{d}m"] = None if c is None or c[1] is None else c[1] - e_h
    return out


def q(v, f):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(f * len(v)))], 3) if v else None


def summarise(rows):
    M = [m for r in rows for m in r["sides"] if m]
    n = len(M)
    out = {"side_stations": n,
           "at_1m": {k: round(sum(1 for m in M if m["at_1m"] == k) / n, 3) for k in
                     ("lane", "shoulder", "kerb", "ground", "wall", "none", "other")} if n else {},
           "rise_2m_m": {"median": q([m["rise_2m"] for m in M], .5), "p95": q([m["rise_2m"] for m in M], .95)},
           "paved_past_edge_m": {"median": q([m["paved_m"] for m in M], .5), "p95": q([m["paved_m"] for m in M], .95)}}
    for d in (3, 6, 10):
        v = [m[f"h_{d}m"] for m in M if m[f"h_{d}m"] is not None]
        out[f"ground_{d}m"] = {"p5": q(v, .05), "median": q(v, .5), "p95": q(v, .95),
                               "share_below_1m": round(sum(1 for x in v if x < -1.0) / len(v), 3) if v else None,
                               "share_above_1m": round(sum(1 for x in v if x > 1.0) / len(v), 3) if v else None}
    return out


def run(line, top, every):
    rows = []
    for s, (x, y, z), w, lx, lz in stations(line, every):
        prof = {}
        for o in OFFS:
            nm, h = top(x + lx * o, z + lz * o, y)
            prof[o] = (cls(nm), None if h is None else h - y)
        hw = w / 2.0
        rows.append({"s": round(s, 1), "w": w, "sides": [side_metrics(prof, hw, 1), side_metrics(prof, hw, -1)]})
    return rows


# --- the built OBJ (pure Python: a bucketed triangle set, the top physical surface under a point) -------------------
def obj_top(obj_path: Path, line, reach=40.0):
    V, cur = [], None
    B = 8.0
    buckets: dict = {}
    P = line["points_xyz_m"]
    near = set()
    for p in P:
        for dx in range(-int(reach // B) - 1, int(reach // B) + 2):
            for dz in range(-int(reach // B) - 1, int(reach // B) + 2):
                near.add((int(p[0] // B) + dx, int(p[2] // B) + dz))
    with open(obj_path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            if ln.startswith("v "):
                _, a, b, c = ln.split()[:4]
                V.append((float(a), float(b), float(c)))
            elif ln.startswith(("g ", "o ")):
                cur = ln.split()[1] if len(ln.split()) > 1 else None
            elif ln.startswith("f ") and cur is not None and physical(cur):
                ids = [int(t.split("/")[0]) for t in ln.split()[1:]]
                for k in range(1, len(ids) - 1):
                    tri = (V[ids[0] - 1], V[ids[k] - 1], V[ids[k + 1] - 1])
                    x0, x1 = min(t[0] for t in tri), max(t[0] for t in tri)
                    z0, z1 = min(t[2] for t in tri), max(t[2] for t in tri)
                    for bx in range(int(x0 // B), int(x1 // B) + 1):
                        for bz in range(int(z0 // B), int(z1 // B) + 1):
                            if (bx, bz) in near:
                                buckets.setdefault((bx, bz), []).append((tri, cur))

    def top(x, z, yref):
        best, bn = None, None
        for (a, b, c), nm in buckets.get((int(x // B), int(z // B)), ()):
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            l3 = 1.0 - l1 - l2
            if min(l1, l2, l3) < -1e-9:
                continue
            h = l1 * a[1] + l2 * b[1] + l3 * c[1]
            if abs(h - yref) > 60.0:
                continue
            if best is None or h > best:
                best, bn = h, nm
        return bn, best
    return top


def blend_top():
    import bpy
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not physical(ob.name):
            ob.hide_set(True); ob.hide_viewport = True
    dg.update()

    def top(x, z, yref):
        o = Vector((x, z, yref + 60.0))
        for _ in range(8):
            hit, loc, _n, _i, ob, _m = scene.ray_cast(dg, o, Vector((0, 0, -1)))
            if not hit:
                return None, None
            if physical(ob.name):
                return ob.name, loc.z
            o = Vector((x, z, loc.z - 0.002))
        return None, None
    return top


def main(argv=None) -> int:
    in_blender = "bpy" in sys.modules
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if in_blender and "--" in sys.argv else sys.argv[1:]
    argv = list(argv)
    every, out = 10.0, None
    if "--every" in argv:
        i = argv.index("--every"); every = float(argv[i + 1]); del argv[i:i + 2]
    if "--json" in argv:
        i = argv.index("--json"); out = Path(argv[i + 1]); del argv[i:i + 2]
    if len(argv) != 1:
        print(__doc__)
        return 2
    if in_blender:
        line = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        top, src = blend_top(), "blend"
    else:
        proj = Path(argv[0])
        line = json.loads((proj / "data" / "gate_centerline.json").read_text(encoding="utf-8"))
        top, src = obj_top(proj / "data" / "track.obj", line), "data/track.obj"
        out = out or proj / "data" / "edge_report.json"
    rows = run(line, top, every)
    rep = {"_doc": "tools/edge_report.py, ledger 0078: REPORT ONLY, no threshold", "source": src, "every_m": every,
           "summary": summarise(rows)}
    if out:
        rep["rows"] = rows
        out.write_text(json.dumps(rep), encoding="utf-8")
    print("[edge] " + json.dumps(rep["summary"]))
    return 0


if __name__ == "__main__":
    rc = main()
    if "bpy" not in sys.modules:
        raise SystemExit(rc)
