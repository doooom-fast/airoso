"""Ledger 0054 P2: after the one change (grown heightfield + pin 37 / 26 + re-keyed cache).

usage: python plan_check.py <airoso> <workshop project> <workdir> <out.json>

C  the P2 config with D2's two boxes put back and planned_pavement removed, offline, on the GROWN heightfield and the
   RE-KEYED cache: the v0.18.0 plan exactly, every key shifted by (+416, -592) base units (fine keys x5), every h, keep,
   tri, phys, refine and break value identical, the frame the pinned one -> the growth moved nothing
D  the P2 config (D2 far box, Cowles to 32.828, planned pavement): the topology (no sampling) — vertex counts,
   physical / far, how many 3DEP samples the cache lacks
"""
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AIR, WS, WD, OUT = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(AIR))
from scripts.elevation import terrain_sample as ts  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402

T = AIR / "tracks" / "san-diego-lake-murray"
ref = json.loads(gzip.decompress((WS / "data" / "terrain.tiers.json.gz").read_bytes()))
cfg = json.loads((T / "track.config.json").read_text(encoding="utf-8"))
v018 = json.loads(subprocess.run(["git", "-C", str(AIR), "show", "4a9e66f:tracks/san-diego-lake-murray/track.config.json"],
                                 capture_output=True, text=True, encoding="utf-8").stdout)
KX, KZ, F = 416, 592, tt.BREAK_FINE
res = {}


def stage(name, c):
    p = WD / name
    if p.exists():
        shutil.rmtree(p)
    (p / "data").mkdir(parents=True)
    for f in ("centerline.raw.local.json", "centerline.local.json", "connectors.local.json", "corridor.i8.json",
              "i8.local.json", "i8.legacy.local.json"):
        shutil.copy2(WS / "data" / f, p / "data" / f)
    for f in ("heightfield.meta.json", "heightfield.npy", "terrain.samples.json.gz", "expansion.north.json"):
        shutil.copy2(T / "data" / f, p / "data" / f)
    (p / "track.config.json").write_text(json.dumps(c, indent=1), encoding="utf-8")
    return p


# --- C ---
c = json.loads(json.dumps(cfg))
c["terrain"]["far_extent"]["bbox_swne"] = v018["terrain"]["far_extent"]["bbox_swne"]
for a, b in zip(c["terrain"]["include"], v018["terrain"]["include"]):
    a["bbox_swne"] = b["bbox_swne"]
c["terrain"]["tier_options"].pop("planned_pavement")
p = stage("C_grown_without_D2_or_plan", c)
r = subprocess.run([sys.executable, "-m", "scripts.elevation.terrain_sample", str(p), "--offline"], cwd=str(AIR),
                   capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"})
out = {"rc": r.returncode, "log": (r.stdout + r.stderr).strip().splitlines()[-5:]}
if r.returncode == 0:
    t = json.loads(gzip.decompress((p / "data" / "terrain.tiers.json.gz").read_bytes()))
    chk = {"I_shifted": t["I"] == [i + KX for i in ref["I"]], "J_shifted": t["J"] == [j - KZ for j in ref["J"]]}
    for k in ("h", "keep", "tris", "phys", "stats"):
        chk[k] = t[k] == ref[k]
    rf, rr = t.get("refine"), ref.get("refine")
    chk["refine"] = (rf["I"] == [i + KX for i in rr["I"]] and rf["J"] == [j - KZ for j in rr["J"]] and rf["h"] == rr["h"]
                     and rf["cells"] == [[i + KX // rr["cell_r"], j - KZ // rr["cell_r"]] for i, j in rr["cells"]]
                     and rf["kept_cells"] == [[i + KX // rr["keep_r"], j - KZ // rr["keep_r"]] for i, j in rr["kept_cells"]])
    bf, br = t.get("break"), ref.get("break")
    chk["break"] = (bf["I5"] == [i + KX * F for i in br["I5"]] and bf["J5"] == [j - KZ * F for j in br["J5"]]
                    and bf["h"] == br["h"])
    chk["frame_is_pinned"] = t["frame"] != ref["frame"]
    out["identical_up_to_the_key_shift"] = chk
    out["all"] = all(chk.values())
    out["frame"] = t["frame"]
    out["frame_v018"] = ref["frame"]
    # same positions: x0' + I' ux == x0 + I ux
    fx = max(abs((t["frame"][0] + (i + KX) * t["frame"][2]) - (ref["frame"][0] + i * ref["frame"][2])) for i in ref["I"][:: 997])
    fz = max(abs((t["frame"][1] + (j - KZ) * t["frame"][3]) - (ref["frame"][1] + j * ref["frame"][3])) for j in ref["J"][:: 997])
    out["max_position_change_m"] = [fx, fz]
res["C"] = out
print("C", json.dumps(out)[:1500], flush=True)

# --- D: the P2 config's topology, without sampling ---
p = stage("D_p2_config", cfg)
spec = tt.TierSpec(cfg["terrain"], json.loads((p / "data" / "centerline.local.json").read_text())["origin"])
lines, origin, files = ts.road_inputs(p)
plan, pfiles = ts.planned_inputs(p, spec)
frame = spec.frame(tt.load_heightfield_meta(p))
# the corridor line over the D2 box needs the online corridor rebuild; use the cached corridor's line (v0.18.0 far box)
cor = json.loads((p / "data" / "corridor.i8.json").read_text(encoding="utf-8"))
cl = [[(x, 0.0, z) for x, z in cor["centreline_local"]]]
out = {}
for label, pl in (("without_planned", []), ("with_planned", plan)):
    topo = tt.Topology(spec, lines, cl, closed_first=True, frame=frame, plan_lines=pl)
    st = topo.stats()
    cache = ts.SampleCache(p / "data" / ts.SAMPLES, spec, frame)
    need = set(topo.vkeys) | set(topo.refine_keys()) | set(tt.aa_taps(topo.aa_keys()))
    out[label] = {"stats": st, "missing_samples": len(cache.missing(sorted(need))), "plan_lines": len(pl)}
    print("D", label, json.dumps(out[label])[:900], flush=True)
res["D"] = out
OUT.write_text(json.dumps(res, indent=1))
