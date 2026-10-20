"""P0 rehearsal (python-only, offline): what the P0 config does to the next ship's terrain plan.
A  HEAD config                      -> the plan reproduces the workshop's v0.18.0 terrain.tiers.json.gz (I/J/h/tris/phys/keep)
B  new config, far_extent + cowles reverted to HEAD's (pin 0, grid_grow, bbox, route changes only) -> identical to A
C  new config (D2 far box + Cowles to 32.828), --offline -> the topology and how many 3DEP samples P2 must fetch
usage: rehearse_terrain.py <airoso> <proj> <config.head.json> <config.new.json> <out.json>
"""
import contextlib, gzip, io, json, shutil, subprocess, sys
from pathlib import Path
AIR, PROJ, HEADC, NEWC, OUT = (Path(a) for a in sys.argv[1:6])
base_tiers = gzip.decompress((PROJ / "data" / "terrain.tiers.json.gz").read_bytes())
base = json.loads(base_tiers)
KEYS = ("I", "J", "h", "keep", "tris", "phys")
res = {}


def run(cfg_bytes, label):
    (PROJ / "track.config.json").write_bytes(cfg_bytes)
    r = subprocess.run([sys.executable, "-m", "scripts.elevation.terrain_sample", str(PROJ), "--offline"],
                       cwd=str(AIR), capture_output=True, text=True, env={**__import__("os").environ, "PYTHONUTF8": "1"})
    log = (r.stdout + r.stderr)
    out = {"rc": r.returncode, "log_tail": log.strip().splitlines()[-6:]}
    if r.returncode == 0:
        t = json.loads(gzip.decompress((PROJ / "data" / "terrain.tiers.json.gz").read_bytes()))
        out["same_as_workshop_v018"] = {k: t.get(k) == base.get(k) for k in KEYS}
        out["refine_same"] = t.get("refine") == base.get("refine")
        out["break_same"] = t.get("break") == base.get("break")
        out["frame"] = t["frame"]
        out["stats"] = t["stats"]
    res[label] = out
    print(label, json.dumps(out)[:1500], flush=True)


head = HEADC.read_bytes()
new = NEWC.read_bytes()
nb = json.loads(new.decode("utf-8"))
hb = json.loads(head.decode("utf-8"))
mid = json.loads(new.decode("utf-8"))
mid["terrain"]["far_extent"]["bbox_swne"] = hb["terrain"]["far_extent"]["bbox_swne"]
for inc_m, inc_h in zip(mid["terrain"]["include"], hb["terrain"]["include"]):
    inc_m["bbox_swne"] = inc_h["bbox_swne"]
samples_before = (PROJ / "data" / "terrain.samples.json.gz").read_bytes()
run(head, "A_head_config")
run(json.dumps(mid).encode("utf-8"), "B_new_config_without_D2")
run(new, "C_new_config_offline")
res["samples_cache_untouched"] = (PROJ / "data" / "terrain.samples.json.gz").read_bytes() == samples_before
(PROJ / "data" / "terrain.tiers.json.gz").write_bytes(gzip.compress(base_tiers, 6, mtime=0))
OUT.write_text(json.dumps(res, indent=1))
