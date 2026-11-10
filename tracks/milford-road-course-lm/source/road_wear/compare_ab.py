"""Ledger 0084: is 0.1.7 (road_wear on) the A side's build (the same commit, the key off) but for the road-wear surfaces'
UVs, materials and textures? Read off the two BUILT road kn5s (L5).

    python compare_ab.py <a.kn5> <b.kn5> <prefix> [<prefix> ...]     (prefixes: the road_wear surfaces, e.g. 1ROAD 1KERB_SIDEWALK)

Per mesh (by name, both files): the triangle corners' positions bit-identical (every mesh), the UVs bit-identical (every
mesh not under a prefix), the material identical (shader + textures; every mesh not under a prefix). Then the texture
table: added / dropped / changed names. Exit 0 when only the road-wear surfaces' UVs / materials and the textures differ.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from scripts.modkit.extract_kn5 import parse, _world_verts  # noqa: E402

a, b = parse(Path(sys.argv[1])), parse(Path(sys.argv[2]))
pref = tuple(s.upper() for s in sys.argv[3:])
ma = {m["name"]: m for m in a["materials"]}; mb = {m["name"]: m for m in b["materials"]}
A = {m["name"]: m for m in a["meshes"]}; B = {m["name"]: m for m in b["meshes"]}
bad, rep = [], {"meshes": len(A), "positions_equal": 0, "uvs_changed": [], "materials_changed": []}


def corners(me, k):
    return [tuple(me["verts"][i][:3]) if k == "pos" else tuple(me["verts"][i][3:5]) for i in me["idx"]]


if set(A) != set(B):
    bad.append(f"mesh names differ: only A {sorted(set(A) - set(B))}, only B {sorted(set(B) - set(A))}")
for n in sorted(set(A) & set(B)):
    x, y = A[n], B[n]
    if corners(x, "pos") != corners(y, "pos") or x["xf"] != y["xf"]:
        bad.append(f"{n}: positions differ"); continue
    rep["positions_equal"] += 1
    rw = n.upper().startswith(pref)
    if corners(x, "uv") != corners(y, "uv"):
        (rep["uvs_changed"].append(n) if rw else bad.append(f"{n}: UVs differ"))
    mx, my = a["materials"][x["matid"]], b["materials"][y["matid"]]
    if (mx["shader"], mx["textures"]) != (my["shader"], my["textures"]):
        (rep["materials_changed"].append(f"{n}: {mx['shader']} -> {my['shader']}") if rw else bad.append(f"{n}: material differs"))
ta, tb = a["textures"], b["textures"]
rep["textures_added"] = sorted(set(tb) - set(ta)); rep["textures_dropped"] = sorted(set(ta) - set(tb))
rep["textures_changed"] = sorted(k for k in set(ta) & set(tb) if hashlib.md5(ta[k]).digest() != hashlib.md5(tb[k]).digest())
rep["texture_bytes"] = {k: len(tb[k]) for k in rep["textures_added"]}
rep["kn5_bytes"] = [Path(sys.argv[1]).stat().st_size, Path(sys.argv[2]).stat().st_size]
rep["pass"] = not bad and not rep["textures_changed"]
rep["problems"] = bad
print(json.dumps(rep, indent=1))
sys.exit(0 if rep["pass"] else 1)
