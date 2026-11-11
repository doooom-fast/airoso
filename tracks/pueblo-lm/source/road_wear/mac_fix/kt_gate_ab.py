"""The gate's kerb rows on kerb_ab_blend.py's output (the code tree given), and a tampered copy that must fail."""
import sys, json, math
from pathlib import Path
T = Path(sys.argv[1]); W = Path(sys.argv[2])
sys.path.insert(0, str(T / "tools")); sys.path.insert(0, str(T))
import road_wear_check as rwc
d = json.load(open(W / "fake.json"))
decl = d["decl"]; kd = decl["kerbs"]
atlas = next(iter(kd["paint"].values()))["atlas"]
blob = open(W / "proj" / "textures" / "road_wear" / atlas, "rb").read()
names = sorted(kd["materials"])
mats = [{"name": n, "shader": decl["materials"][n]["shader"], "props": {},
         "textures": [(t[0], t[1]) for t in decl["materials"][n]["textures"]]} for n in names]
rwc._world_verts = lambda me: me["V"]
p = {"textures": {atlas: blob}, "meshes": [{"matid": 0, "V": d["V"], "idx": d["idx"], "name": "1KERB_circuit_0"}]}
w = decl["spec"]["wear"]
out = rwc.kerb_rows(W / "proj", {"loop": True}, decl, kd, mats, p, [tuple(d["line"])], w)
for k, v in out.items():
    print(k, json.dumps(v))
L = kd["levels"]
V2 = [list(q) for q in d["V"]]
for q in V2[:3]:
    q[3] = (q[3] * L % 1 + (int(q[3] * L) + 1) % L) / L
p["meshes"][0]["V"] = V2
print("tampered (one triangle a level up): kerb_levels pass =", rwc.kerb_rows(W / "proj", {"loop": True}, decl, kd, mats, p, [tuple(d["line"])], w)["kerb_levels"]["pass"])
