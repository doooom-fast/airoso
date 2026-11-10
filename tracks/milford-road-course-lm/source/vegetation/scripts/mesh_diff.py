"""Which meshes of two built kn5s are the same, mesh by mesh (ledger 0082 vegetation pass: "the road and ground byte-identical
to 0.1.2, or explain each difference"). A mesh is EQUAL when its header, every vertex's position / normal / UV, its indices and
its tail are byte-identical and its tangents within tools/kn5_equiv.TANGENT_TOL (Blender's tangent pass is not bit-stable), and
its material is the same BY NAME: the tail's material id is an index into the file's material list, so dropping one material
(0.1.2's TREECARD deciduous) renumbers every mesh whose material came after it without changing what it wears.

    python mesh_diff.py <a.kn5> <b.kn5> [--json out.json]
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
import kn5_equiv as ke  # noqa: E402


def material_names(d, s):
    """the materials region's names in file order (a mesh's tail carries its material by this index); the walk is
    tools/kn5_equiv.regions' own"""
    o = [s]

    def U():
        v = struct.unpack_from("<I", d, o[0])[0]
        o[0] += 4
        return v

    def S():
        n = U()
        v = d[o[0]:o[0] + n].decode("utf-8", "replace")
        o[0] += n
        return v
    names = []
    for _ in range(U()):
        names.append(S())
        S()
        o[0] += 2
        U()
        for _ in range(U()):
            S()
            o[0] += 40
        for _ in range(U()):
            S()
            U()
            S()
    return names


def meshes(path):
    d = Path(path).read_bytes()
    regs = ke.regions(d)
    mats = material_names(d, next(s for kind, _n, s, _e, _x in regs if kind == "materials"))
    out, cur = {}, {}
    for kind, name, s, e, _x in regs:
        if kind in ("mesh_head", "vertices", "mesh_tail"):
            blob = d[s:e]
            if kind == "mesh_tail":       # [index count][indices][material id] ...: the id becomes its material's name
                ic = struct.unpack_from("<I", blob, 0)[0]
                at = 4 + ic * 2
                cur[name]["material"] = mats[struct.unpack_from("<I", blob, at)[0]]
                blob = blob[:at] + blob[at + 4:]
            cur.setdefault(name, {})[kind] = blob
            if kind == "mesh_tail":
                out.setdefault(name, []).append(cur.pop(name))
    tex = {name: d[s:e] for kind, name, s, e, _x in regs if kind == "texture"}
    return out, tex


def same(a, b):
    if a["material"] != b["material"]:
        return False, f"material {a['material']} -> {b['material']}"
    if a["mesh_head"] != b["mesh_head"] or a["mesh_tail"] != b["mesh_tail"] or len(a["vertices"]) != len(b["vertices"]):
        return False, "header / indices / vertex count"
    res = {"tangent_values": 0, "tangent_max": 0.0}
    why = ke._vertices_equiv(a["vertices"], b["vertices"], "", ke.TANGENT_TOL, res)
    return why is None, (why or f"tangents {res['tangent_values']} within {res['tangent_max']:.2g}")


def main():
    A, ta = meshes(sys.argv[1])
    B, tb = meshes(sys.argv[2])
    names = sorted(set(A) | set(B))
    rows = []
    for n in names:
        if n not in A or n not in B:
            rows.append({"mesh": n, "verdict": "only in " + ("b" if n not in A else "a"),
                         "verts": sum(len(m["vertices"]) // ke.VERTEX_B for m in (B.get(n) or A.get(n)))})
            continue
        if len(A[n]) != len(B[n]):
            rows.append({"mesh": n, "verdict": f"{len(A[n])} vs {len(B[n])} meshes of this name"})
            continue
        oks = [same(x, y) for x, y in zip(A[n], B[n])]
        rows.append({"mesh": n, "verdict": "equal" if all(o for o, _ in oks) else "DIFFERS",
                     "why": [w for o, w in oks if not o][:1], "verts": sum(len(m["vertices"]) // ke.VERTEX_B for m in A[n])})
    tex = {"only_a": sorted(set(ta) - set(tb)), "only_b": sorted(set(tb) - set(ta)),
           "changed": sorted(k for k in set(ta) & set(tb) if ta[k] != tb[k])}
    groups = {}
    for r in rows:
        g = r["mesh"].split("_")[0]
        groups.setdefault(g, {}).setdefault(r["verdict"], 0)
        groups[g][r["verdict"]] += 1
    rep = {"a": sys.argv[1], "b": sys.argv[2], "by_prefix": groups, "textures": tex, "meshes": rows}
    for g, v in sorted(groups.items()):
        print(f"{g:24s} {v}")
    print("textures:", tex)
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
