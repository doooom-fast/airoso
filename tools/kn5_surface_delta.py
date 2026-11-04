"""Did the GROUND move between two built kn5s? The surface, not the vertices (ledger 0054 Phase 2 step 2e).

kn5_equiv --list names every mesh whose vertices differ. On a terrain that is re-tiled or re-thinned that list says
little: the prep tiles 1GRASS by MEDIAN bisection of its face centres (build_kn5_loop.balanced_face_tiles), so one face
more anywhere moves every later cut and triangles change tile far from the cause, and the thinning runs per tile with
the tile seams locked, so a re-cut tile thins to a different triangulation of (nearly) the same surface. A vertex can
"move 4.9 m" while the ground under the car does not move at all. This samples the SURFACE instead:

  * every triangle of every mesh whose name starts with the prefix (default 1GRASS: the ground tiles and the rock
    faces split out of them, 1GRASS_ROCK_*) is rasterised onto one plan grid (kn5 frame, x / z) per kn5, keeping the
    HIGHEST surface over each grid point and the mesh it belongs to;
  * the two grids are differenced point by point (b - a): overall, per tile of a (the mesh on top at that point in a),
    and for the rock (points where a ROCK mesh is on top in a or in b);
  * with --line (a json with points_xyz_m in the ENGINE frame, e.g. data/lap.north.json; the kn5 frame is z-mirrored,
    scripts/modkit/kn5_to_gate_obj), the differences are also binned by plan distance to that line.

Reports n, max |d|, p99 |d|, mean |d| and the counts past 1 mm / 1 cm / 5 cm / 10 cm, the plan box of the points past
1 cm, the worst points, and the points only one kn5 covers (a hole, or ground added). Pure Python.

    python tools/kn5_surface_delta.py <a.kn5> <b.kn5> [--prefix 1GRASS] [--step 2.0] [--line data/lap.north.json]
                                      [--box x0,z0,x1,z1] [--exclude x0,z0,x1,z1] [--json out.json]
--exclude (kn5 frame) also reports the points outside that box on their own ("surface-equal outside the island").
--box (kn5 frame) samples only that plan box (a finer --step on the island, say). Lake Murray's ground spans ~34 km2:
at the default 2 m that is ~8.5 M points per kn5: about 10-15 minutes and ~0.3 GB in pure Python.
Exit 0 always (a measurement, not a gate); 2 on an input error.
"""
from __future__ import annotations

import json
import math
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.modkit.extract_kn5 import _xform, parse  # noqa: E402

STEP_M = 2.0
BINS_M = (0.001, 0.01, 0.05, 0.10)
DIST_BINS_M = (20.0, 60.0, 200.0, 1000.0)
NEG = -1e30


def meshes(path, prefix: str) -> list[tuple[str, list, list]]:
    """[(name, world verts (kn5 frame), indices)] of every mesh whose upper-case name starts with ``prefix``"""
    pu = prefix.upper()
    parsed = parse(Path(path), keep=lambda n: str(n).upper().startswith(pu), textures=False)
    out = []
    for m in parsed["meshes"]:
        if not str(m["name"]).upper().startswith(pu):
            continue
        xf = m["xf"]
        out.append((m["name"], [_xform(xf, x, y, z) for (x, y, z, _u, _v) in m["verts"]], list(m["idx"])))
    return out


class Grid:
    def __init__(self, x0, z0, nx, nz, step):
        self.x0, self.z0, self.nx, self.nz, self.step = x0, z0, nx, nz, step
        self.h = array("d", [NEG]) * (nx * nz)
        self.t = array("i", [-1]) * (nx * nz)

    def raster(self, ms):
        x0, z0, s, nx, nz, H, T = self.x0, self.z0, self.step, self.nx, self.nz, self.h, self.t
        for mi, (_name, V, I) in enumerate(ms):
            for q in range(0, len(I) - 2, 3):
                (xa, ya, za), (xb, yb, zb), (xc, yc, zc) = V[I[q]], V[I[q + 1]], V[I[q + 2]]
                den = (zb - zc) * (xa - xc) + (xc - xb) * (za - zc)
                if abs(den) < 1e-12:
                    continue                    # vertical in plan: no surface over any point
                i0 = max(0, int(math.ceil((min(xa, xb, xc) - x0) / s)))
                i1 = min(nx - 1, int(math.floor((max(xa, xb, xc) - x0) / s)))
                j0 = max(0, int(math.ceil((min(za, zb, zc) - z0) / s)))
                j1 = min(nz - 1, int(math.floor((max(za, zb, zc) - z0) / s)))
                for j in range(j0, j1 + 1):
                    z = z0 + j * s
                    row = j * nx
                    for i in range(i0, i1 + 1):
                        x = x0 + i * s
                        wa = ((zb - zc) * (x - xc) + (xc - xb) * (z - zc)) / den
                        wb = ((zc - za) * (x - xc) + (xa - xc) * (z - zc)) / den
                        wc = 1.0 - wa - wb
                        if wa < -1e-9 or wb < -1e-9 or wc < -1e-9:
                            continue
                        h = wa * ya + wb * yb + wc * yc
                        c = row + i
                        if h > H[c]:
                            H[c] = h
                            T[c] = mi


def _stats(ds: list, pts: list | None = None) -> dict:
    if not ds:
        return {"n": 0}
    a = sorted(abs(d) for d in ds)
    n = len(a)
    out = {"n": n, "max_abs_m": round(a[-1], 4), "p99_abs_m": round(a[min(n - 1, int(0.99 * n))], 4),
           "mean_abs_m": round(sum(a) / n, 5)}
    for b in BINS_M:
        out[f"n_gt_{int(round(b * 1000))}mm"] = sum(1 for d in ds if abs(d) > b)
    if pts:
        big = [p for p, d in zip(pts, ds) if abs(d) > 0.01]
        if big:
            out["box_gt_10mm_xz"] = [round(min(p[0] for p in big), 1), round(min(p[1] for p in big), 1),
                                     round(max(p[0] for p in big), 1), round(max(p[1] for p in big), 1)]
    return out


class _LineDist:
    def __init__(self, pts_xz, cell=25.0):
        self.cell = cell
        self.grid: dict = {}
        for x, z in pts_xz:
            self.grid.setdefault((int(x // cell), int(z // cell)), []).append((x, z))
        self.segs = pts_xz

    def dist(self, x, z, cap):
        """plan distance to the nearest line point (the lap's points stand <= 3.5 m apart), up to ``cap``"""
        r = int(cap // self.cell) + 1
        cx, cz = int(x // self.cell), int(z // self.cell)
        best = cap
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                for px, pz in self.grid.get((cx + dx, cz + dz), ()):
                    d = math.hypot(px - x, pz - z)
                    if d < best:
                        best = d
        return best


def delta(a_path, b_path, *, prefix="1GRASS", step=STEP_M, line=None, box=None, exclude=None) -> dict:
    ma, mb = meshes(a_path, prefix), meshes(b_path, prefix)
    if not ma or not mb:
        raise ValueError(f"no {prefix}* mesh in {'a' if not ma else 'b'}")
    xs = [v[0] for _n, V, _I in ma + mb for v in V]
    zs = [v[2] for _n, V, _I in ma + mb for v in V]
    lo_x, lo_z, hi_x, hi_z = min(xs), min(zs), max(xs), max(zs)
    if box is not None:
        lo_x, lo_z, hi_x, hi_z = max(lo_x, box[0]), max(lo_z, box[1]), min(hi_x, box[2]), min(hi_z, box[3])
        if hi_x < lo_x or hi_z < lo_z:
            raise ValueError(f"--box {box} holds no ground")
    x0, z0 = math.ceil(lo_x / step) * step, math.ceil(lo_z / step) * step
    nx, nz = int((hi_x - x0) / step) + 1, int((hi_z - z0) / step) + 1
    ga, gb = Grid(x0, z0, nx, nz, step), Grid(x0, z0, nx, nz, step)
    ga.raster(ma)
    gb.raster(mb)
    rock_a = {i for i, (n, _V, _I) in enumerate(ma) if "ROCK" in n.upper()}
    rock_b = {i for i, (n, _V, _I) in enumerate(mb) if "ROCK" in n.upper()}
    ld = None
    if line is not None:
        lj = json.loads(Path(line).read_text(encoding="utf-8"))
        ld = _LineDist([(p[0], -p[2]) for p in lj["points_xyz_m"]])      # engine -> kn5 frame (z mirrored)
    all_d, all_p = [], []
    by_tile: dict = {}
    rock_d, rock_p = [], []
    by_dist: dict = {}
    only_a = only_b = 0
    worst = []
    out_d, out_p = [], []
    for c in range(nx * nz):
        ha, hb = ga.h[c], gb.h[c]
        if ha == NEG and hb == NEG:
            continue
        if ha == NEG:
            only_b += 1
            continue
        if hb == NEG:
            only_a += 1
            continue
        d = hb - ha
        p = (x0 + (c % nx) * step, z0 + (c // nx) * step)
        all_d.append(d)
        all_p.append(p)
        if exclude is not None and not (exclude[0] <= p[0] <= exclude[2] and exclude[1] <= p[1] <= exclude[3]):
            out_d.append(d)
            out_p.append(p)
        ta = ma[ga.t[c]][0]
        by_tile.setdefault(ta, ([], []))
        by_tile[ta][0].append(d)
        by_tile[ta][1].append(p)
        if ga.t[c] in rock_a or gb.t[c] in rock_b:
            rock_d.append(d)
            rock_p.append(p)
        if ld is not None:
            dd = ld.dist(p[0], p[1], DIST_BINS_M[-1])
            k = next((f"<{int(b)} m" for b in DIST_BINS_M if dd < b), f">={int(DIST_BINS_M[-1])} m")
            by_dist.setdefault(k, []).append(d)
        if abs(d) > 0.01:
            worst.append((abs(d), round(d, 4), round(p[0], 1), round(p[1], 1), ta, mb[gb.t[c]][0]))
    worst.sort(reverse=True)
    out = {"a": str(a_path), "b": str(b_path), "prefix": prefix, "step_m": step, "frame": "kn5 (x, z; z = -engine z)",
           "meshes_a": len(ma), "meshes_b": len(mb), "points_compared": len(all_d),
           "points_only_in_a": only_a, "points_only_in_b": only_b,
           "overall": _stats(all_d, all_p),
           "rock": _stats(rock_d, rock_p),
           "by_tile_a": {t: _stats(v[0], v[1]) for t, v in sorted(by_tile.items())},
           "worst": [{"d_m": w[1], "x": w[2], "z": w[3], "tile_a": w[4], "tile_b": w[5]} for w in worst[:25]]}
    if exclude is not None:
        out["exclude_box_xz"] = list(exclude)
        out["outside_exclude"] = _stats(out_d, out_p)
    if ld is not None:
        out["line"] = str(line)
        out["by_distance_to_line"] = {k: _stats(v) for k, v in sorted(by_dist.items())}
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pos, opt, i = [], {}, 0
    while i < len(argv):
        if argv[i].startswith("--"):
            if i + 1 >= len(argv):
                print(__doc__)
                return 2
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    if len(pos) != 2 or set(opt) - {"prefix", "step", "line", "json", "box", "exclude"}:
        print(__doc__)
        return 2
    try:
        r = delta(pos[0], pos[1], prefix=opt.get("prefix", "1GRASS"), step=float(opt.get("step", STEP_M)),
                  line=opt.get("line"),
                  box=[float(v) for v in opt["box"].split(",")] if opt.get("box") else None,
                  exclude=[float(v) for v in opt["exclude"].split(",")] if opt.get("exclude") else None)
    except (ValueError, OSError, KeyError) as e:
        print(f"[surface-delta] INPUT ERROR: {e}")
        return 2
    if opt.get("json"):
        Path(opt["json"]).write_text(json.dumps(r, indent=1), encoding="utf-8")

    def line(lbl, s):
        if not s.get("n"):
            return f"[surface-delta] {lbl:28s} no points"
        return (f"[surface-delta] {lbl:28s} n {s['n']:>9d}  max {s['max_abs_m']:.4f}  p99 {s['p99_abs_m']:.4f}  "
                f"mean {s['mean_abs_m']:.5f}  >1mm {s['n_gt_1mm']}  >1cm {s['n_gt_10mm']}  >5cm {s['n_gt_50mm']}  "
                f">10cm {s['n_gt_100mm']}" + (f"  box>1cm {s['box_gt_10mm_xz']}" if s.get("box_gt_10mm_xz") else ""))
    print(f"[surface-delta] {r['prefix']}* on a {r['step_m']} m grid: {r['points_compared']} points compared, "
          f"{r['points_only_in_a']} only in a, {r['points_only_in_b']} only in b")
    print(line("overall", r["overall"]))
    print(line("rock (ROCK on top, a or b)", r["rock"]))
    if r.get("outside_exclude") is not None:
        print(line("outside the --exclude box", r["outside_exclude"]))
    for t, s in r["by_tile_a"].items():
        print(line(t, s))
    for k, s in (r.get("by_distance_to_line") or {}).items():
        print(line(f"line {k}", s))
    for w in r["worst"][:10]:
        print(f"[surface-delta]   worst {w['d_m']:+.4f} m at ({w['x']}, {w['z']}) {w['tile_a']} -> {w['tile_b']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
