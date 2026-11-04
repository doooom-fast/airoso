"""Are two built kn5s the same build? Byte for byte, except the vertex TANGENTS within TANGENT_TOL.

Blender's tangent pass is not bit-stable run to run: the same workshop rebuilt from the prep (ledger 0065 repro,
2026-11-03) gave Lake Murray v4's road / race / street / closure kn5s with different md5s, and every differing byte was
a tangent float (tx / ty / tz) off by at most 5.7e-7. Positions, normals, UVs, indices, materials, textures and the
node tree matched exactly. So the md5 is not the test of "the same build"; this is:

  * the texture blocks, the materials and every node / mesh header byte-identical;
  * every vertex's position, normal and UV bit-identical, every index identical;
  * every tangent component within TANGENT_TOL.

The exporter merges vertices whose every attribute is equal, so tangent noise can also move a mesh's vertex count
(0.20.1, 2026-11-03: ROOFTOP_SHINGLE_0 27,728 -> 27,729 vertices, one corner left unmerged by a 6e-8 tangent). Such a
mesh is compared corner by corner instead: the same triangles in the same order, every corner's position / normal / UV
bit-identical, its tangent within TANGENT_TOL.

When the texture sets differ (a build that adds or drops an embedded image), the materials and geometry are still
compared region by region, and the verdict names exactly which textures were added / removed / changed and whether
everything else is equivalent ("textures only: ...").

    python tools/kn5_equiv.py <a.kn5> <b.kn5> [--tol 1e-6]     exit 0 = equivalent, 1 = not (the first difference named)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

TANGENT_TOL = 1e-6
VERTEX_B = 44                 # 3 position + 3 normal + 2 uv + 3 tangent float32
FIELDS = ("px", "py", "pz", "nx", "ny", "nz", "u", "v", "tx", "ty", "tz")


def regions(d: bytes):
    """[(kind, name, start, end, extra)] covering the file: textures, materials, then the node tree; a mesh's
    extra = (vertex block start, end)"""
    o = [6]

    def U():
        v = struct.unpack_from("<I", d, o[0])[0]
        o[0] += 4
        return v

    def I():
        v = struct.unpack_from("<i", d, o[0])[0]
        o[0] += 4
        return v

    def S():
        n = U()
        v = d[o[0]:o[0] + n].decode("utf-8", "replace")
        o[0] += n
        return v
    out = [("header", "", 0, 6, None)]
    s0 = o[0]
    if I() > 5:
        I()
    out.append(("version", "", s0, o[0], None))
    s0 = o[0]
    nt = I()
    out.append(("texture_count", "", s0, o[0], None))
    for _ in range(nt):
        s0 = o[0]
        I()
        name = S()
        n = U()
        o[0] += n
        out.append(("texture", name, s0, o[0], None))
    s0 = o[0]
    nm = U()
    for _ in range(nm):
        S(); S(); o[0] += 2; I()
        for _ in range(U()):
            S(); o[0] += 40
        for _ in range(U()):
            S(); I(); S()
    out.append(("materials", "", s0, o[0], None))

    def rd():
        s0 = o[0]
        ncls = U(); name = S(); cc = U(); o[0] += 1
        if ncls == 1:
            o[0] += 64
            out.append(("node", name, s0, o[0], None))
            for _ in range(cc):
                rd()
        elif ncls == 2:
            o[0] += 3
            vc = U()
            v0 = o[0]
            o[0] += vc * VERTEX_B
            out.append(("mesh_head", name, s0, v0, None))
            out.append(("vertices", name, v0, o[0], None))
            s1 = o[0]
            ic = U()
            o[0] += ic * 2 + 4 + 4 + 4 + 4 + 16 + 1
            out.append(("mesh_tail", name, s1, o[0], None))
            for _ in range(cc):
                rd()
        else:
            raise SystemExit(f"unknown node class {ncls} at {s0}")
    rd()
    if o[0] != len(d):
        out.append(("trailing", "", o[0], len(d), None))
    return out


def _vertices_equiv(a: bytes, b: bytes, n: str, tol: float, res: dict) -> str | None:
    """None when the two vertex blocks agree but for tangents within tol (res collects the tangent drift)"""
    for i in range(0, len(a), VERTEX_B):
        va, vb = a[i:i + VERTEX_B], b[i:i + VERTEX_B]
        if va == vb:
            continue
        if va[:32] != vb[:32]:
            fa, fb = struct.unpack("<8f", va[:32]), struct.unpack("<8f", vb[:32])
            f = next(j for j in range(8) if fa[j] != fb[j])
            return f"{n} vertex {i // VERTEX_B} {FIELDS[f]} {fa[f]} != {fb[f]}"
        for x, y in zip(struct.unpack("<3f", va[32:]), struct.unpack("<3f", vb[32:])):
            if x != y:
                res["tangent_values"] += 1
                res["tangent_max"] = max(res["tangent_max"], abs(x - y))
        if res["tangent_max"] > tol:
            return f"{n} vertex {i // VERTEX_B} tangent off by {res['tangent_max']:.3g} > {tol}"
    return None


def _corners_equiv(va: bytes, ia: bytes, vb: bytes, ib: bytes, n: str, tol: float, res: dict) -> str | None:
    """a mesh whose vertex count moved by the exporter's merge alone (two corners equal in position, normal and UV
    but a tangent apart by float noise stay two vertices): every triangle corner, in order, must carry the same
    position / normal / UV bit for bit and a tangent within tol"""
    (ca,), (cb,) = struct.unpack_from("<I", ia, 0), struct.unpack_from("<I", ib, 0)
    if ca != cb:
        return f"{n}: {ca // 3} vs {cb // 3} triangles"
    xa, xb = struct.unpack_from(f"<{ca}H", ia, 4), struct.unpack_from(f"<{cb}H", ib, 4)
    for c, (i, j) in enumerate(zip(xa, xb)):
        pa, pb = va[i * VERTEX_B:i * VERTEX_B + 32], vb[j * VERTEX_B:j * VERTEX_B + 32]
        if pa != pb:
            fa, fb = struct.unpack("<8f", pa), struct.unpack("<8f", pb)
            f = next(k for k in range(8) if fa[k] != fb[k])
            return f"{n} corner {c} {FIELDS[f]} {fa[f]} != {fb[f]}"
        for x, y in zip(struct.unpack_from("<3f", va, i * VERTEX_B + 32), struct.unpack_from("<3f", vb, j * VERTEX_B + 32)):
            if x != y:
                res["tangent_values"] += 1
                res["tangent_max"] = max(res["tangent_max"], abs(x - y))
    res["merge_differs"] = res.get("merge_differs", []) + [f"{n} {len(va) // VERTEX_B} -> {len(vb) // VERTEX_B} vertices"]
    if res["tangent_max"] > tol:
        return f"{n}: a tangent off by {res['tangent_max']:.3g} > {tol}"
    return None


def compare(a: bytes, b: bytes, tol: float = TANGENT_TOL) -> dict:
    """the texture sets compared by name (added / removed / changed bytes), then everything else region by region"""
    ra, rb = regions(a), regions(b)
    ta = {n: a[s:e] for k, n, s, e, _ in ra if k == "texture"}
    tb = {n: b[s:e] for k, n, s, e, _ in rb if k == "texture"}
    res = {"equivalent": True, "tangent_max": 0.0, "tangent_values": 0, "first": None,
           "textures_added": sorted(set(tb) - set(ta)), "textures_removed": sorted(set(ta) - set(tb)),
           "textures_changed": sorted(n for n in set(ta) & set(tb) if ta[n] != tb[n]),
           "texture_order_same": [n for n in ta if n in tb] == [n for n in tb if n in ta]}
    rest_a = [r for r in ra if r[0] not in ("texture", "texture_count")]
    rest_b = [r for r in rb if r[0] not in ("texture", "texture_count")]
    if [(k, n) for k, n, *_ in rest_a] != [(k, n) for k, n, *_ in rest_b]:
        res.update(equivalent=False, first="the materials or the node tree differ in layout (mesh names or order)")
        return res
    k_ = 0
    while k_ < len(rest_a):
        k, n, sa, ea, _ = rest_a[k_]
        _, _, sb, eb, _ = rest_b[k_]
        if k == "mesh_head":
            # a mesh: head + vertices + tail, compared as a unit
            (_, _, va0, va1, _), (_, _, ta0, ta1, _) = rest_a[k_ + 1], rest_a[k_ + 2]
            (_, _, vb0, vb1, _), (_, _, tb0, tb1, _) = rest_b[k_ + 1], rest_b[k_ + 2]
            if a[sa:ta1] != b[sb:tb1]:
                if a[sa:ea - 4] != b[sb:eb - 4] or a[ta1 - 33:ta1] != b[tb1 - 33:tb1]:
                    res.update(equivalent=False, first=f"mesh_head {n}")
                    return res
                if (va1 - va0) == (vb1 - vb0) and a[ta0:ta1] == b[tb0:tb1]:
                    first = _vertices_equiv(a[va0:va1], b[vb0:vb1], n, tol, res)
                else:
                    first = _corners_equiv(a[va0:va1], a[ta0:ta1 - 33], b[vb0:vb1], b[tb0:tb1 - 33], n, tol, res)
                if first:
                    res.update(equivalent=False, first=first)
                    return res
            k_ += 3
            continue
        if (ea - sa) != (eb - sb) or a[sa:ea] != b[sb:eb]:
            res.update(equivalent=False, first=f"{k} {n}".strip())
            return res
        k_ += 1
    if res["textures_added"] or res["textures_removed"] or res["textures_changed"] or not res["texture_order_same"]:
        res.update(equivalent=False, first="textures only: added " + str(res["textures_added"]) + ", removed "
                   + str(res["textures_removed"]) + ", changed " + str(res["textures_changed"])
                   + ("" if res["texture_order_same"] else ", order changed") + "; materials and geometry equivalent")
    return res


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    tol = TANGENT_TOL
    if "--tol" in argv:
        tol = float(argv[argv.index("--tol") + 1])
        del argv[argv.index("--tol"):argv.index("--tol") + 2]
    if len(argv) != 2:
        print(__doc__)
        return 2
    a, b = Path(argv[0]).read_bytes(), Path(argv[1]).read_bytes()
    if a == b:
        print(f"[kn5_equiv] {Path(argv[1]).name}: byte-identical")
        return 0
    r = compare(a, b, tol)
    if r["equivalent"]:
        print(f"[kn5_equiv] {Path(argv[1]).name}: EQUIVALENT (tangents only: {r['tangent_values']} values, max "
              f"{r['tangent_max']:.3g} <= {tol}; every other byte identical"
              + (f"; vertex merge moved by the tangent noise: {r['merge_differs']}" if r.get("merge_differs") else "") + ")")
        return 0
    print(f"[kn5_equiv] {Path(argv[1]).name}: DIFFERENT -- first: {r['first']}"
          + (f" (tangent drift elsewhere: {r['tangent_values']} values, max {r['tangent_max']:.3g})" if r["tangent_values"] else "")
          + (f" (vertex merge moved by the tangent noise: {r['merge_differs']})" if r.get("merge_differs") else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
