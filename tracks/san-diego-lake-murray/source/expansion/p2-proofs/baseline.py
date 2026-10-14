"""Ledger 0054 P2 step 1: the terrain planner, offline, on the UNGROWN config must reproduce the v0.18.0 plan (the
installed workshop's data/terrain.tiers.json.gz) exactly, before anything grows.

usage: python baseline.py <airoso> <workshop project> <config.v0180.json> <config.branch.json> <workdir> <out.json>

A  v0.18.0's own config (4a9e66f)                      -> I, J, h, keep, tris, phys, refine, break all identical
B  the branch config (db3f7e8) with D2's two boxes put back to v0.18.0's (pin offsets 0, grid_grow held, the north
   route held)                                         -> identical
Read-only on the workshop: a minimal planning copy of its data/ is made in <workdir>.
"""
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AIR, WS, CA, CB, WD, OUT = (Path(a) for a in sys.argv[1:7])
FILES = ["centerline.raw.local.json", "centerline.local.json", "connectors.local.json", "heightfield.meta.json",
         "terrain.samples.json.gz", "corridor.i8.json", "i8.local.json", "i8.legacy.local.json"]
ref = json.loads(gzip.decompress((WS / "data" / "terrain.tiers.json.gz").read_bytes()))
KEYS = ("I", "J", "h", "keep", "tris", "phys", "refine", "break", "frame", "inputs_md5")
res = {"workshop_v018_plan": {"stats": ref["stats"], "vertices": len(ref["I"]),
                              "break_vertices": len((ref.get("break") or {}).get("h", [])),
                              "frame": ref["frame"]}}


def stage(name, cfg_bytes):
    p = WD / name
    if p.exists():
        shutil.rmtree(p)
    (p / "data").mkdir(parents=True)
    for f in FILES:
        if (WS / "data" / f).exists():
            shutil.copy2(WS / "data" / f, p / "data" / f)
    (p / "track.config.json").write_bytes(cfg_bytes)
    return p


def run(name, cfg_bytes):
    p = stage(name, cfg_bytes)
    before = (p / "data" / "terrain.samples.json.gz").read_bytes()
    r = subprocess.run([sys.executable, "-m", "scripts.elevation.terrain_sample", str(p), "--offline"], cwd=str(AIR),
                       capture_output=True, text=True, env={**os.environ, "PYTHONUTF8": "1"})
    out = {"rc": r.returncode, "log": (r.stdout + r.stderr).strip().splitlines()[-6:]}
    if r.returncode == 0:
        t = json.loads(gzip.decompress((p / "data" / "terrain.tiers.json.gz").read_bytes()))
        out["identical_to_v018"] = {k: t.get(k) == ref.get(k) for k in KEYS}
        out["all_identical"] = all(out["identical_to_v018"].values())
        out["stats"] = t["stats"]
        out["vertices"] = len(t["I"])
        out["break_vertices"] = len((t.get("break") or {}).get("h", []))
    out["samples_cache_untouched"] = (p / "data" / "terrain.samples.json.gz").read_bytes() == before
    res[name] = out
    print(name, json.dumps(out)[:900], flush=True)


ca = CA.read_bytes()
run("A_v0180_config", ca)
b = json.loads(CB.read_text(encoding="utf-8"))
a = json.loads(ca.decode("utf-8"))
b["terrain"]["far_extent"]["bbox_swne"] = a["terrain"]["far_extent"]["bbox_swne"]
for ib, ia in zip(b["terrain"]["include"], a["terrain"]["include"]):
    ib["bbox_swne"] = ia["bbox_swne"]
run("B_branch_config_without_D2", json.dumps(b, indent=1).encode("utf-8"))
OUT.write_text(json.dumps(res, indent=1))
print("baseline:", "PASS" if all(res[k].get("all_identical") for k in ("A_v0180_config", "B_branch_config_without_D2"))
      else "FAIL")
