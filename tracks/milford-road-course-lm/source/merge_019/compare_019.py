"""Milford 0.1.9 = 0.1.7 + 0.1.8, read off the three BUILT road kn5s (L5):

    python compare_019.py <0.1.7.kn5> <0.1.8.kn5> <0.1.9.kn5> [--json out.json]

1. positions: every mesh of 0.1.9 has 0.1.8's triangle-corner positions bit for bit (and its transform), and the same mesh names.
2. road wear: on the road-wear surfaces (track.config.json road_wear.surfaces: 1ROAD, 1KERB_SIDEWALK) 0.1.9's corner UVs and
   material (shader + texture slots) are 0.1.7's bit for bit.
3. everything else: corner UVs and material are 0.1.8's (0.1.8 = 0.1.6 there but for its own furniture).
4. textures: 0.1.9's embedded set is 0.1.7's, byte for byte (0.1.8 added none to 0.1.6's).
Exit 0 when all four hold; every exception is listed.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from scripts.modkit.extract_kn5 import parse  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
if out:
    args = [a for a in args if a != out]
p7, p8, p9 = (Path(a) for a in args[:3])
k7, k8, k9 = parse(p7), parse(p8), parse(p9)
SURF = ("1ROAD", "1KERB_SIDEWALK")
M = lambda k: {m["name"]: m for m in k["meshes"]}  # noqa: E731
m7, m8, m9 = M(k7), M(k8), M(k9)


def corners(me, k):
    return [tuple(me["verts"][i][:3]) if k == "pos" else tuple(me["verts"][i][3:5]) for i in me["idx"]]


def mat(k, me):
    x = k["materials"][me["matid"]]
    return x["shader"], x["textures"]


bad, rep = [], {"kn5_bytes": {"0.1.7": p7.stat().st_size, "0.1.8": p8.stat().st_size, "0.1.9": p9.stat().st_size},
                "meshes": len(m9), "positions_equal_018": 0, "uv_mat_equal_017_on_road_wear": [], "uv_mat_equal_018_elsewhere": 0,
                "differs_from_017_elsewhere_by_018_design": []}
if set(m9) != set(m8):
    bad.append(f"mesh names vs 0.1.8: only 0.1.9 {sorted(set(m9) - set(m8))}, only 0.1.8 {sorted(set(m8) - set(m9))}")
for n in sorted(set(m9) & set(m8)):
    a, b = m9[n], m8[n]
    if corners(a, "pos") != corners(b, "pos") or a["xf"] != b["xf"]:
        bad.append(f"{n}: positions differ from 0.1.8")
    else:
        rep["positions_equal_018"] += 1
    if n.upper().startswith(SURF):
        c = m7.get(n)
        if c is None:
            bad.append(f"{n}: not in 0.1.7")
            continue
        ok = corners(a, "uv") == corners(c, "uv") and mat(k9, a) == mat(k7, c)
        (rep["uv_mat_equal_017_on_road_wear"].append(n) if ok else bad.append(f"{n}: UVs or material differ from 0.1.7"))
        if corners(a, "uv") == corners(b, "uv"):
            bad.append(f"{n}: UVs equal 0.1.8's (the bake did not run?)")
    else:
        if corners(a, "uv") == corners(b, "uv") and mat(k9, a) == mat(k8, b):
            rep["uv_mat_equal_018_elsewhere"] += 1
        else:
            bad.append(f"{n}: UVs or material differ from 0.1.8")
        c = m7.get(n)
        if c is None or corners(a, "pos") != corners(c, "pos") or a["xf"] != c["xf"]:
            rep["differs_from_017_elsewhere_by_018_design"].append(n + (" (not in 0.1.7)" if c is None else ""))
t7, t9 = k7["textures"], k9["textures"]
h = lambda b: hashlib.md5(b).hexdigest()  # noqa: E731
rep["textures"] = {"0.1.7": len(t7), "0.1.8": len(k8["textures"]), "0.1.9": len(t9),
                   "only_017": sorted(set(t7) - set(t9)), "only_019": sorted(set(t9) - set(t7)),
                   "changed_vs_017": sorted(k for k in set(t7) & set(t9) if h(t7[k]) != h(t9[k]))}
if rep["textures"]["only_017"] or rep["textures"]["only_019"] or rep["textures"]["changed_vs_017"]:
    bad.append("the embedded textures are not 0.1.7's")
rep["pass"] = not bad
rep["problems"] = bad
s = json.dumps(rep, indent=1)
print(s)
if out:
    Path(out).write_text(s + "\n", encoding="utf-8")
sys.exit(0 if rep["pass"] else 1)
