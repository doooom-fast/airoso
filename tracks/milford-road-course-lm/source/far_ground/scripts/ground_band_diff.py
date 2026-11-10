"""The near ground of two built kn5s, triangle by triangle (ledger 0082 'Far ground (0.1.11)': "the near ground band
bit-identical to 0.1.10"). The far ground replaces only the skirt past the 3DEP grid, but the prep re-tiles 1GRASS by balanced
bisection over ALL of it, so the tiles' names, vertex order and splits move and mesh_diff.py reads every tile as different.
This compares what they hold instead:

  every 1GRASS* triangle with all three corners inside the 3DEP grid's box (data/far_ground.report.json grid.bbox_xy, +-5 cm)
  is a key of its three corner POSITIONS as float32 bytes (rotated to start at the smallest, winding kept); the two builds'
  multisets of keys must be equal. Each corner's normal and UV are then compared for the matched triangles: a corner ON the
  grid's border takes its normal from the faces on both sides of it, so its normal may move with the ring (counted apart);
  every other corner must match bit for bit.

    python ground_band_diff.py <a.kn5> <b.kn5> <far_ground.report.json> [--json out.json]
"""
import json
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
import kn5_equiv as ke  # noqa: E402

VB = ke.VERTEX_B
TOL = 0.05


def grass_tris(path):
    d = Path(path).read_bytes()
    cur = {}
    out = []
    for kind, name, s, e, _x in ke.regions(d):
        if not name.upper().startswith("1GRASS"):
            continue
        if kind == "vertices":
            cur[name] = d[s:e]
        elif kind == "mesh_tail":
            v = cur.pop(name)
            ic = struct.unpack_from("<I", d, s)[0]
            idx = struct.unpack_from(f"<{ic}H", d, s + 4)
            for t in range(0, ic, 3):
                out.append(tuple(v[idx[t + k] * VB:(idx[t + k] + 1) * VB] for k in range(3)))
    return out


def key(tri):
    pos = [c[:12] for c in tri]
    k = pos.index(min(pos))
    return tuple(pos[k:] + pos[:k]), tuple(tri[k:] + tri[:k])


def main(argv):
    a, b, repp = argv[0], argv[1], argv[2]
    x0, y0, x1, y1 = json.loads(Path(repp).read_text(encoding="utf-8"))["grid"]["bbox_xy"]

    def inside(c):
        x, _y, zk = struct.unpack("<3f", c[:12])
        n = -zk                                            # the kn5 frame's z is the engine's north negated
        return x0 - TOL <= x <= x1 + TOL and y0 - TOL <= n <= y1 + TOL

    def on_border(c):
        x, _y, zk = struct.unpack("<3f", c[:12])
        n = -zk
        return min(abs(x - x0), abs(x - x1), abs(n - y0), abs(n - y1)) <= TOL

    res = {}
    band = {}
    for tag, p in (("a", a), ("b", b)):
        tris = grass_tris(p)
        sel = [key(t) for t in tris if all(inside(c) for c in t)]
        band[tag] = sel
        res[tag] = {"kn5": p, "grass_triangles": len(tris), "band_triangles": len(sel)}
    ca, cb = Counter(k for k, _ in band["a"]), Counter(k for k, _ in band["b"])
    res["only_a"] = sum((ca - cb).values())
    res["only_b"] = sum((cb - ca).values())
    attrs = {}
    for k, t in band["a"]:
        attrs.setdefault(k, []).append(t)
    border_n = inner_diff = border_diff = 0
    worst = []
    for k, t in band["b"]:
        if k not in attrs or not attrs[k]:
            continue
        ta = attrs[k].pop()
        for c1, c2 in zip(ta, t):
            if c1[12:32] == c2[12:32]:
                continue
            if on_border(c1):
                border_diff += 1
            else:
                inner_diff += 1
                if len(worst) < 10:
                    worst.append([struct.unpack("<8f", c1[:32]), struct.unpack("<8f", c2[:32])])
    for k, t in band["b"]:
        border_n += sum(on_border(c) for c in t)
    res["corners_normal_or_uv_differ"] = {"on_the_grid_border": border_diff, "inside": inner_diff,
                                          "border_corners_total": border_n}
    res["worst_inside"] = worst
    res["verdict"] = ("EQUAL" if res["only_a"] == 0 and res["only_b"] == 0 and inner_diff == 0 else "DIFFERS")
    print(f"[ground-band] grid box x {x0:.1f}..{x1:.1f} y {y0:.1f}..{y1:.1f}: a {res['a']['band_triangles']} / b "
          f"{res['b']['band_triangles']} triangles inside; only in a {res['only_a']}, only in b {res['only_b']}; corners whose "
          f"normal / UV differ: inside {inner_diff}, on the border {border_diff} (of {border_n}) -> {res['verdict']}")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0 if res["verdict"] == "EQUAL" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
