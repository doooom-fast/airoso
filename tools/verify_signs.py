"""The self-checks that make a W1-6 placement right-or-wrong mechanically (Kevin, 2026-10-10:
"very easy to see when it's right or wrong" — this is the same test as numbers). A ship gate:
tools/ship_sd.sh runs it after the authoring pass; exit 1 on any FAIL.

Reads data/signs.local.json (tools/place_signs.py / tools/author_signs_blend.py) and MEASURES —
nothing a check needs is taken from a number the placement wrote about itself (the first dry run's
check (c) compared mesh_clear_m with the constant it was computed from; fleet/GATES-CHANGELOG.md).
Per sign (a paired post is checked once per plate where a plate matters):
  (a) the failed-to-turn ray from A along t passes within +-0.61 m (half the 48 in plate) of the
      UN-SLID post point, base - slid_m * u — the lamp/plant slide along the curb is the only
      lateral deviation the rule allows, so it is subtracted before the test (a paired post adds
      half its pair split: each plate was moved that far to the shared post)
  (b) the plate faces straight back down the approach: |angle(f, -t)| <= 1 deg
  (c) built-edge clearance, measured two ways and both must pass: the minimum horizontal distance
      from the post base to the BUILT outside pavement edge polyline the authoring pass recorded
      (built.outside_edge_xz, perpendicular probes of the ROAD top surface per station), and —
      with --blend — an independent BVH top-surface scan inside Blender (ROAD vs
      CURB/SIDEWALK/TERRAIN, 5-degree polar scan at 0.25 m steps from the base, tools/signs_mesh.py).
      Mainline 1.3-3.0 m; connectors >= 1.0 m. An analytic run (no built edge, no --blend) falls
      back to the polyline field distance and says so.
  (d) the geometric outside assertion held (cross > 0)
  (e) plate bottom = y_base + height (+-0.05)      } from the Blender section when present,
  (f) post base = y_base - 0.30 (+-0.05)            } "n/a" on a pure-Python (analytic) run
  (g) no SIGN* vertex inside drive_test's obstacle disc, min(lane_half, 6) + 0.3 m of ANY
      centreline — the sign's own street included (4.9 m on a 10 m street) — recomputed here from
      centerline.local.json + connectors.local.json over the plate footprint (base +- 0.61 m along
      every plate's right vector); and the base is off pavement (measured clearance > 0)
  (h) exactly one record per id, none at a skipped id, no -fwd/-rev twin of a paired post
  (i) base spacing: no two posts closer than 2.0 m
  (j) signs.json expect_arrow, where given, equals the placed arrow (never relocate silently)
  plus blender.normal_mismatches == 0.

    python tools/verify_signs.py <project-dir> [--blend PATH] [--blender EXE]

--blend PATH runs the independent scan on that blend (READ ONLY: never saved) by launching Blender
(--blender, else $BLENDER, else the BL= line of tools/ship_sd.sh) on this very file with
--measure-out; the measurement lands in data/signs_measured.json. Without --blend the scan column
reads "-" and check (c) rests on the recorded built edge alone.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
HALF_PLATE = 0.61
FACE_TOL_DEG = 1.0
CLEAR_RANGE = {"MAINLINE": (1.3, 3.0), "CONNECTOR": (1.0, None)}
HEIGHT_TOL = 0.05
POST_SINK = 0.30
SPACING_MIN = 2.0
MEASURED = "signs_measured.json"


# --- geometry, own code (never place_signs') ------------------------------------------------------
def seg_dist(q, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / L2))
    return math.hypot(q[0] - (a[0] + t * dx), q[1] - (a[1] + t * dz))


def poly_dist(q, pts):
    """min distance to a polyline (None when it has < 2 points)"""
    if not pts or len(pts) < 2:
        return None
    return min(seg_dist(q, pts[i], pts[i + 1]) for i in range(len(pts) - 1))


class Discs:
    """drive_test's obstacle disc, min(max(w/2 - 0.4, 0.8), 6) + 0.3, around every centreline
    (scripts/geometry/drive_test.py:390/482) — margin = distance - radius, worst over all ribbons"""

    def __init__(self, proj):
        data = Path(proj) / "data"
        self.segs = []
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        self._add(cl["points_xyz_m"], cl["widths_m"], True)
        cp = data / "connectors.local.json"
        if cp.exists():
            for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
                P = c["points_xyz_m"]
                self._add(P, c["widths_m"], math.dist(P[0][::2], P[-1][::2]) < 1e-6)
        self.cells = {}
        for k, (a, b, _, _) in enumerate(self.segs):
            for p in (a, b):
                self.cells.setdefault((int(p[0] // 60), int(p[1] // 60)), set()).add(k)

    def _add(self, P, W, closed):
        idx = list(range(len(P))) + ([0] if closed else [])
        for a, b in zip(idx[:-1], idx[1:]):
            self.segs.append(((P[a][0], P[a][2]), (P[b][0], P[b][2]), W[a], W[b]))

    def margin(self, x, z):
        worst = float("inf")
        cx, cz = int(x // 60), int(z // 60)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in self.cells.get((cx + dx, cz + dz), ()):
                    a, b, wa, wb = self.segs[k]
                    ddx, ddz = b[0] - a[0], b[1] - a[1]
                    L2 = ddx * ddx + ddz * ddz
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - a[0]) * ddx + (z - a[1]) * ddz) / L2))
                    d = math.hypot(x - (a[0] + t * ddx), z - (a[1] + t * ddz))
                    w = wa * (1 - t) + wb * t
                    worst = min(worst, d - (min(max(w / 2 - 0.4, 0.8), 6.0) + 0.3))
        return worst

    def footprint(self, base, rights):
        pts = [tuple(base)]
        for r in rights:
            pts.append((base[0] + r[0] * HALF_PLATE, base[1] + r[1] * HALF_PLATE))
            pts.append((base[0] - r[0] * HALF_PLATE, base[1] - r[1] * HALF_PLATE))
        return min(self.margin(p[0], p[1]) for p in pts)


# --- the independent scan (runs inside Blender) ----------------------------------------------------
def measure_in_blender(proj, blend, out_path):
    import bpy
    sys.path.insert(0, str(AIROSO / "tools"))
    import signs_mesh as sm
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    road, ground, road_names, ground_names = sm.load_bvhs(skip_prefixes=("SIGN",))
    d = json.loads((Path(proj) / "data" / "signs.local.json").read_text(encoding="utf-8"))
    res = {"blend": str(blend), "road_objects": road_names, "ground_objects": ground_names,
           "scan": "5-degree polar, 0.25 m steps, bisected; ROAD top vs CURB/SIDEWALK/TERRAIN top", "signs": {}}
    for s in d["signs"]:
        x, z = s["base_xz"]
        clear, bearing = sm.polar_clearance(road, ground, x, z)
        res["signs"][s["id"]] = {"clear_m": round(clear, 3), "bearing_deg": bearing, "on_road": sm.on_road(road, ground, x, z)}
    Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("[verify-signs] measured %d bases in Blender -> %s" % (len(res["signs"]), out_path))


def blender_exe(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    ship = AIROSO / "tools" / "ship_sd.sh"
    if ship.exists():
        m = re.search(r'^BL="([^"]+)"', ship.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return "blender"


def run_blender_measure(proj, blend, exe):
    out_path = Path(proj) / "data" / MEASURED
    out_path.unlink(missing_ok=True)
    cmd = [exe, "--background", "--python-exit-code", "1", "--python", str(Path(__file__).resolve()), "--",
           str(proj), "--blend", str(blend), "--measure-out", str(out_path)]
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("[verify-signs]") or "Error" in ln or "Traceback" in ln]
    if r.returncode != 0 or not out_path.exists():
        return None, "blender exit %d, %s: %s" % (r.returncode, "no " + MEASURED if not out_path.exists() else "output", " | ".join(tail[-4:]))
    return json.loads(out_path.read_text(encoding="utf-8")), " | ".join(tail[-1:])


# --- the gate ------------------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if not argv:
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    blend = argv[argv.index("--blend") + 1] if "--blend" in argv else None
    if "--measure-out" in argv:
        measure_in_blender(proj, blend, argv[argv.index("--measure-out") + 1])
        return
    d = json.loads((proj / "data" / "signs.local.json").read_text(encoding="utf-8"))
    measured, note = None, ""
    if blend:
        measured, note = run_blender_measure(proj, blend, blender_exe(argv[argv.index("--blender") + 1] if "--blender" in argv else None))
    discs = Discs(proj)
    fails, rows = [], []
    signs = d["signs"]
    ids = [s["id"] for s in signs]
    skipped_ids = {s["id"] for s in d["skipped"]}
    if blend and measured is None:
        fails.append("blender measurement did not run (%s)" % note)
    for s in signs:
        plates = s.get("plates") or [s]
        S = s["base_xz"]
        c = s["checks"]
        slid = c.get("slid_m", 0.0)
        u = s.get("curb_dir_xz", [0.0, 0.0])
        S0 = (S[0] - u[0] * slid, S[1] - u[1] * slid)
        tol_a = HALF_PLATE + (s.get("pair_split_m", 0.0) / 2 if s.get("pair") else 0.0)
        kind = "MAINLINE" if s["ribbon"] == "MAINLINE" else "CONNECTOR"
        lo, hi = CLEAR_RANGE[kind]
        # (a) (b) (d) (j) per plate
        lat_max, ang_max, outside_min, expect_ok = 0.0, 0.0, float("inf"), True
        for p in plates:
            t = (-p["face_dir_xz"][0], -p["face_dir_xz"][1])
            f = p["face_dir_xz"]
            A = p["ray"]["A_xz"]
            lat_max = max(lat_max, abs(t[0] * (S0[1] - A[1]) - t[1] * (S0[0] - A[0])))
            ang_max = max(ang_max, math.degrees(math.acos(max(-1.0, min(1.0, -(f[0] * t[0] + f[1] * t[1]))))))
            outside_min = min(outside_min, p.get("checks", c).get("outside_cross", c["outside_cross"]))
            if p.get("expect_arrow") in ("left", "right") and p["expect_arrow"] != p["arrow"]:
                expect_ok = False
        # (c) measured two ways
        edge = (s.get("built") or {}).get("outside_edge_xz")
        clear_poly = poly_dist(S, edge) if edge else None
        clear_bvh = measured["signs"][s["id"]]["clear_m"] if measured and s["id"] in measured.get("signs", {}) else None
        clears = [v for v in (clear_poly, clear_bvh) if v is not None]
        analytic_only = not clears
        if analytic_only:
            clears = [c["edge_clear_m"]]
        c_ok = all(v >= lo and (hi is None or v <= hi) for v in clears)
        if measured and s["id"] not in measured.get("signs", {}):
            c_ok = False
        clear_min = min(clears)
        yb = s["y_base"].get("value", s["y_base"]["analytic"])
        bl = s.get("blender")
        disc = discs.footprint(S, [p["right_xz"] for p in plates])
        twins = [i for i in ids if s.get("pair") and i in (s["id"] + "-fwd", s["id"] + "-rev")]
        checks = {
            "a_ray_hits_plate": lat_max <= tol_a,
            "b_faces_approach": ang_max <= FACE_TOL_DEG,
            "c_built_edge_clearance": c_ok,
            "d_outside": outside_min > 0,
            "e_plate_height": None if not bl else abs(bl["plate_bottom_y"] - (yb + s["height_m"])) <= HEIGHT_TOL,
            "f_post_sunk": None if not bl else abs(bl["post_base_y"] - (yb - POST_SINK)) <= HEIGHT_TOL,
            "g_gate_disc": disc >= 0 and clear_min > 0 and not (measured and measured["signs"].get(s["id"], {}).get("on_road")),
            "h_unique_id": ids.count(s["id"]) == 1 and s["id"] not in skipped_ids and not twins,
            "j_expect_arrow": expect_ok,
        }
        bad = [k for k, v in checks.items() if v is False]
        fails += ["%s: %s" % (s["id"], ", ".join(bad))] if bad else []
        rows.append("[verify-signs] %-11s %-12s ray-lat %.2f m (slid %+.2f)  face-err %.2f deg  edge: poly %s / scan %s m%s  outside %+.1f  disc %+.2f  %s"
                    % (s["id"], s["kind"], lat_max, slid, ang_max,
                       "-" if clear_poly is None else "%.2f" % clear_poly, "-" if clear_bvh is None else "%.2f" % clear_bvh,
                       " (analytic %.2f)" % c["edge_clear_m"] if analytic_only else "", outside_min, disc,
                       "FAIL " + ", ".join(bad) if bad else "ok" + ("" if bl else " (e/f n/a: analytic run)")))
    # (i) spacing across every pair of posts
    for i in range(len(signs)):
        for j in range(i + 1, len(signs)):
            dd = math.dist(signs[i]["base_xz"], signs[j]["base_xz"])
            if dd < SPACING_MIN:
                fails.append("%s / %s: i_spacing %.2f m < %.1f" % (signs[i]["id"], signs[j]["id"], dd, SPACING_MIN))
    if "blender" in d and d["blender"].get("normal_mismatches"):
        fails.append("blender: %d polygon normals do not face as intended" % d["blender"]["normal_mismatches"])
    for r in rows:
        print(r)
    if measured:
        print("[verify-signs] independent scan: %s (%s)" % (measured["scan"], note or "ok"))
    for fl in fails:
        print("[verify-signs] FAIL", fl)
    print("[verify-signs] %d posts (%d plates), %d skipped, %s%s" % (
        len(signs), sum(len(s.get("plates") or [s]) for s in signs), len(d["skipped"]), "FAIL" if fails else "PASS",
        "" if blend else " (no --blend: check (c) on the recorded built edge only)"))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
