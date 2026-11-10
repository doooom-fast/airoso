import sys, json
from pathlib import Path
A = Path(sys.argv[1]); W = Path(sys.argv[2])
sys.path.insert(0, str(A / "tools")); sys.path.insert(0, str(A))
import road_wear_check as rwc
d = json.load(open(W / "fake.json"))
json.dump(d["line_json"], open(W / "proj" / "data" / "road_wear.line.full.json", "w"))
decl = d["decl"]; kd = decl["kerbs"]
atlas = next(iter(kd["paint"].values()))["atlas"]
blob = open(W / "proj" / "textures" / "road_wear" / atlas, "rb").read()
mats = [{"name": "1KERB_circuit_0_mat", "shader": decl["materials"]["1KERB_circuit_0_mat"]["shader"], "props": {"ksAmbient": 0.4, "ksDiffuse": 0.4},
         "textures": [(t[0], t[1]) for t in decl["materials"]["1KERB_circuit_0_mat"]["textures"]]}]
rwc._world_verts = lambda me: me["V"]
p = {"textures": {atlas: blob}, "meshes": [{"matid": 0, "V": d["V"], "idx": d["idx"], "name": "1KERB_circuit_0"}]}
w = decl["spec"]["wear"]
out = rwc.kerb_rows(W / "proj", {"loop": True}, decl, kd, mats, p, [tuple(d["line"])], w)
for k, v in out.items(): print(k, v)
# a tampered level must fail
V2 = [list(q) for q in d["V"]]
for q in V2[:3]: q[3] = (q[3] * 16 % 1 + (int(q[3] * 16) + 1) % 16) / 16
p["meshes"][0]["V"] = V2
print("tampered", rwc.kerb_rows(W / "proj", {"loop": True}, decl, kd, mats, p, [tuple(d["line"])], w)["kerb_levels"]["pass"])
