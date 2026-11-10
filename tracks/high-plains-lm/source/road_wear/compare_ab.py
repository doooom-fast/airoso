"""Ledger 0084 'High Plains 0.1.7': is the 0.1.7 road kn5 the installed 0.1.6's but for the road-wear surfaces' UVs,
materials and textures? Read off the two BUILT road kn5s (L5). Milford 0.1.7's compare_ab.py (claude/milford-0111) plus
the VARs (road_wear_check.materials_with_props): a mesh not under a prefix must keep its shader, textures AND VARs.

    python compare_ab.py <a.kn5> <b.kn5> <prefix> [<prefix> ...] [--moved <prefix> ...]
        prefixes: the road-wear surfaces and the kerbs, here 1ROAD 1KERB_SIDEWALK 1KERB_CIRCUIT_
        --moved: meshes another pass of the same build is declared to move (runbook 0084-2: the PC's K-rail re-seat,
                 1WALL_KRAIL): their positions are reported, not required equal; their UVs and materials still must be

Per mesh (by name, both files): the triangle corners' positions bit-identical (every mesh) and the node transform equal;
the UVs bit-identical and the material identical (every mesh not under a prefix). For the race kerbs (1KERB_CIRCUIT_)
the VARs and shader must also stay 0.1.6's (only txDiffuse may change), and their v must stay bit-identical (only u
moves). Then the texture table: added / dropped / changed names. Exit 0 when only that differs.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
from scripts.modkit.extract_kn5 import parse  # noqa: E402
from road_wear_check import materials_with_props  # noqa: E402

fa, fb = Path(sys.argv[1]), Path(sys.argv[2])
a, b = parse(fa), parse(fb)
va = {m["name"]: m for m in materials_with_props(fa)}; vb = {m["name"]: m for m in materials_with_props(fb)}
args = sys.argv[3:]
mv = args.index("--moved") if "--moved" in args else len(args)
pref = tuple(s.upper() for s in args[:mv])
moved = tuple(s.upper() for s in args[mv + 1:])
A = {m["name"]: m for m in a["meshes"]}; B = {m["name"]: m for m in b["meshes"]}
bad, rep = [], {"meshes": len(A), "positions_equal": 0, "positions_moved_declared": [], "uvs_changed": [],
                "materials_changed": []}


def corners(me, k):
    sl = {"pos": slice(0, 3), "uv": slice(3, 5), "v": slice(4, 5)}[k]
    return [tuple(me["verts"][i][sl]) for i in me["idx"]]


if set(A) != set(B):
    bad.append(f"mesh names differ: only A {sorted(set(A) - set(B))}, only B {sorted(set(B) - set(A))}")
for n in sorted(set(A) & set(B)):
    x, y = A[n], B[n]
    if corners(x, "pos") != corners(y, "pos") or x["xf"] != y["xf"]:
        if moved and n.upper().startswith(moved) and len(x["idx"]) == len(y["idx"]):
            rep["positions_moved_declared"].append(n)
        else:
            bad.append(f"{n}: positions differ"); continue
    else:
        rep["positions_equal"] += 1
    rw = n.upper().startswith(pref)
    kerb = n.upper().startswith("1KERB_CIRCUIT_")
    if corners(x, "uv") != corners(y, "uv"):
        (rep["uvs_changed"].append(n) if rw else bad.append(f"{n}: UVs differ"))
    if kerb and corners(x, "v") != corners(y, "v"):
        bad.append(f"{n}: a kerb's v moved (only u may)")
    mx, my = a["materials"][x["matid"]], b["materials"][y["matid"]]
    px, py = va.get(mx["name"], {}).get("props"), vb.get(my["name"], {}).get("props")
    if (mx["shader"], mx["textures"], px) != (my["shader"], my["textures"], py):
        if not rw:
            bad.append(f"{n}: material differs")
        else:
            rep["materials_changed"].append(f"{n}: {mx['shader']} -> {my['shader']}")
            if kerb and (mx["shader"] != my["shader"] or px != py):
                bad.append(f"{n}: a kerb's shader or VARs changed ({mx['shader']} {px} -> {my['shader']} {py})")
ta, tb = a["textures"], b["textures"]
rep["textures_added"] = sorted(set(tb) - set(ta)); rep["textures_dropped"] = sorted(set(ta) - set(tb))
rep["textures_changed"] = sorted(k for k in set(ta) & set(tb) if hashlib.md5(ta[k]).digest() != hashlib.md5(tb[k]).digest())
rep["texture_bytes"] = {k: len(tb[k]) for k in rep["textures_added"]}
rep["kn5_bytes"] = [fa.stat().st_size, fb.stat().st_size]
rep["pass"] = not bad and not rep["textures_changed"]
rep["problems"] = bad
print(json.dumps(rep, indent=1))
sys.exit(0 if rep["pass"] else 1)
