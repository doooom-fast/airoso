"""Byte-identity proof (ledger 0054 Phase 2 nose end): run ONE airoso tree's race tools on a scratch copy of Lake Murray
v4's project (no nose declared anywhere) and print md5s of everything they declare / plan / judge.

    python prove_nose_off.py <airoso tree> <scratch project> <out.json>

Run it twice — once with the tree BEFORE the nose end (git archive 2ce9495 tools scripts | tar -x -C <base>, plus a
link to airoso's assets/) and once with this branch — each on its own fresh copy of tracks/san-diego-lake-murray's
data/ + track.config.json, and diff the two out files. 2026-11-04 on the Mac: identical, every key
(nose_off_md5.json beside this file). barrier_bands.json is compared byte for byte with the planned fill's
"seconds" timings blanked (they differ run to run).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
PROJ = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import barrier_bands as bands  # noqa: E402
import no_route as nr  # noqa: E402
import race_corridor as rc  # noqa: E402
import race_furniture as rf  # noqa: E402
import verify_race as vr  # noqa: E402


def md5(o):
    return hashlib.md5(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in ("seconds", "_path", "_ctx", "elapsed_s", "generated")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


res = {}
# 1. the declaration (+ its planned no_route per layout), written as the chain writes it
out = bands.build(PROJ)
data = PROJ / "data"
res["barrier_bands.json (every byte but the planned fill's seconds)"] = hashlib.md5(__import__("re").sub(r'"seconds": [0-9.eE+-]+', '"seconds": X', (data / "barrier_bands.json").read_text()).encode()).hexdigest()
res["seconds keys"] = (data / "barrier_bands.json").read_text().count('"seconds"')
res["barrier_bands fails"] = out["fails"]
for lid in ("race_cw", "race_acw"):
    p = data / f"no_route.{lid}.planned.json"
    res[f"no_route.{lid}.planned (minus seconds)"] = md5(strip(json.loads(p.read_text())))
b = json.loads((data / "barrier_bands.json").read_text())
res["edge_corners"] = md5(b["edge_corners"])
res["kerbs (declared, clipped)"] = md5(b["kerbs"])
for lid, c in b["corridors"].items():
    res[f"corridor {lid}: closure_y / lane / zone / runs"] = md5([c["closure_y_by_vertex"], c["lane_by_vertex"],
                                                                  c["zone_by_vertex"], c["runs"]])
    res[f"corridor {lid}: keys"] = sorted(c)
# 2. the race furniture plans (what the Blender author sweeps)
pts, widths, island_w, plans, corners = rf.plan_all(PROJ, b, b["params"]["edge_mode"])
for kind in ("edge", "kerb", "close"):
    ps = [p for p in plans if p["kind"] == kind]
    res[f"race_furniture plans {kind} ({len(ps)})"] = md5(ps)
res["race_furniture object names"] = md5(sorted(rf.object_name(p) for p in plans))
res["kerb_closure_clips"] = md5(rf.kerb_closure_clips(pts, widths, b, b["params"]["edge_mode"]))
# 3. the corridor solve itself, both directions
cfg = json.loads((PROJ / "track.config.json").read_text())
cor = cfg["race"]["corridor"]
P = rc.params_from(cor)
m = rc.ring_count(pts)
whole = (int(cor["whole"][0]) % m, int(cor["whole"][1]) % m)
boxes = [(int(x["i"]) % m, int(x["j"]) % m) for x in cor["boxes"]]


def free(v):
    return rc.in_rng(v, *whole, m) or any(rc.in_rng(v, i, j, m) for i, j in boxes)


iw = json.loads((data / "median_bands.json").read_text())["island_w_by_vertex"]
for d in ("cw", "acw"):
    s = rc.solve(pts, widths, iw, free, d, P)
    res[f"race_corridor.solve {d}"] = md5([[r["vs"], r["g"], r["L"], r["U"]] for r in s["runs"]])
# 4. the planned no_route on the declaration in memory
for lid in ("race_cw", "race_acw"):
    r = nr.run(PROJ, lid, planned=True, bands=b, write=False, verbose=False)
    res[f"no_route.run planned {lid}"] = md5(strip({k: v for k, v in r.items()}))
# 5. verify_race on v4's committed authored file
authored = json.loads((data / "race_authored.json").read_text())
fails, warns, counts = [], [], {}
rep = vr.verify(authored, b, pts, island_w, widths=widths)
res["verify_race.verify (committed race_authored.json)"] = md5(strip(rep))
res["verify_race fails"] = rep.get("fails") if isinstance(rep, dict) else None
# 6. the per-layout zone drive_test / audit_mesh exempt walls on (scripts/geometry/median_zone.py)
from scripts.geometry.median_zone import MedianZone  # noqa: E402
for lid in ("race_cw", "race_acw"):
    z = MedianZone.load(PROJ, layout=lid)
    res[f"median_zone {lid}: mouths / lane / closure / bands"] = md5([z.mouths, z.lane, z.closure_y,
                                                                      sorted(map(str, z.bcells.items()))])
OUT.write_text(json.dumps(res, indent=1, sort_keys=True))
print(json.dumps(res, indent=1, sort_keys=True))
