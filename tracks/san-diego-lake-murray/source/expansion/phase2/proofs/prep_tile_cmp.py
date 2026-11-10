"""python tile_cmp.py <a tiles.json> <b tiles.json>: the prepped terrain tiles of two scenes compared — tile names and
counts, and every face present in one and not the other, with whether it lies inside the island box (Blender frame)"""
import json
import sys

ISL = (-3001.7, 1537.9, -2968.3, 1592.1)        # Princess View's island box: x, y(north) — the kn5 box with z mirrored
PAD = 0.0
a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))


def inside(c):
    return ISL[0] - PAD <= c[0] <= ISL[2] + PAD and ISL[1] - PAD <= c[1] <= ISL[3] + PAD


rep = {"tiles_a": len(a), "tiles_b": len(b), "same_tile_names": sorted(a) == sorted(b),
       "faces_a": sum(r["f"] for r in a.values()), "faces_b": sum(r["f"] for r in b.values()), "tiles": {}}
out_total = in_total = 0
box = None
for n in sorted(set(a) | set(b)):
    fa = (a.get(n) or {}).get("faces", {})
    fb = (b.get(n) or {}).get("faces", {})
    only_a = [fa[h] for h in fa.keys() - fb.keys()]
    only_b = [fb[h] for h in fb.keys() - fa.keys()]
    if not only_a and not only_b and (a.get(n) or {}).get("v") == (b.get(n) or {}).get("v"):
        continue
    outside = [c for c in only_a + only_b if not inside(c)]
    out_total += len(outside)
    in_total += len(only_a) + len(only_b) - len(outside)
    for c in outside:
        box = c + c if box is None else (min(box[0], c[0]), min(box[1], c[1]), max(box[2], c[0]), max(box[3], c[1]))
    rep["tiles"][n] = {"v": [(a.get(n) or {}).get("v"), (b.get(n) or {}).get("v")],
                       "f": [(a.get(n) or {}).get("f"), (b.get(n) or {}).get("f")],
                       "only_a": len(only_a), "only_b": len(only_b), "outside_island_box": len(outside),
                       "outside_first": outside[:5]}
rep["faces_differing_inside_island_box"] = in_total
rep["faces_differing_outside_island_box"] = out_total
rep["outside_box_xy"] = box
print(json.dumps(rep, indent=1))
