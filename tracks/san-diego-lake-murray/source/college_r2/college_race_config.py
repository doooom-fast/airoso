"""College split, step 4d: THE RACE AND ZONE DECLARATIONS in a project's track.config.json. STEP-DESIGN.md has the why.

    python college_race_config.py <project dir> [--write]

What changes (and nothing else):

  layouts            race_cw (Lake Murray Speedway, clockwise = northbound on College) runs on the lap `college`
                     (race.laps.college, written by college_split_data.py: the mainline, the northbound road, the
                     mainline). race_acw (Speedway Reverse) stays on the mainline, which IS the southbound road there.
  race.chicanes      the entry `college_split` goes (the crossover existed because both directions shared one slab).
  race.corridor      whole becomes two stretches: the one it was, and the TWO ROADS of the split, [NOSE-1, TAIL+1]: each
                     road is the whole street for its direction (both curb strips, no closure). The closure run that held
                     College, [777, 1506], becomes two: [777, NOSE-1] and [TAIL+1, 1506]. So in each FORK the closure runs
                     on from the island's end to the point where the roads part, and pins there; it is what divides the
                     fork between the two directions, as the island did. (Tried first: whole through the forks and on
                     to the box. The declaration's own gates refused it: the island that stays north of the split stood
                     in an open zone, its top reachable (2 forbidden probes), and a run ending at the fork's outer row
                     turned too tightly past the island's nose, plan radius 19.6 m under the 20 m minimum.)
  race.laps.college  .corridor = race.corridor (the lap's vertex k is the mainline's vertex k, so the same numbers
                     declare the same places) and .roads = route.roads (the same streets in the same order).
  terrain.ground_release.zones `college_split_cut`
                     v becomes the whole split (rows A0..A1): the bank's top and the east shelf are released ground.

Without --write: prints what would change. With --write: rewrites the PROJECT's track.config.json (kept once as
track.config.json.pre-race). A scratch workshop only; airoso's own config changes in the integration commit."""
import copy
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
proj = Path(sys.argv[1])
WRITE = "--write" in sys.argv[2:]
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = S["rows"]["v"][0], S["rows"]["v"][-1]
LAP = "college"
CW, CHICANE, ZONE = "race_cw", "college_split", "college_split_cut"

cfg_path = proj / "track.config.json"
_pre = cfg_path.with_name(cfg_path.name + ".pre-race")
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
if _pre.exists():                                            # a second run starts from the config as it was, less the lap
    base = json.loads(_pre.read_text(encoding="utf-8"))
    for key in ("laps",):
        base["race"][key] = cfg["race"][key]
    if "median_spots" in (cfg.get("scenery", {}).get("treefx") or {}):
        base.setdefault("scenery", {}).setdefault("treefx", {})["median_spots"] = cfg["scenery"]["treefx"]["median_spots"]
    cfg_now, cfg = cfg, base
    cfg["race"]["laps"]["college"].pop("corridor", None)
before = json.loads(_pre.read_text(encoding="utf-8")) if _pre.exists() else copy.deepcopy(cfg)
race = cfg["race"]
cor = race["corridor"]
if LAP not in (race.get("laps") or {}):
    raise SystemExit(f"race.laps.{LAP} is not declared: run college_split_data.py <project> --write first")

# the two roads are whole street; each fork is closure run, pinned where the roads part
boxes = sorted(cor["boxes"], key=lambda b: b["i"])
nxt = next(b for b in boxes if b["i"] >= A1)                 # the College / Navajo box
WHOLE_SPLIT = [NOSE - 1, TAIL + 1]
old_whole = cor["whole"] if isinstance(cor["whole"][0], list) else [cor["whole"]]
cor["whole"] = [w for w in old_whole if w != WHOLE_SPLIT] + [WHOLE_SPLIT]
runs = []
for a, b in cor["closure_runs"]:
    if a < A0 < b:                                           # the run that held College
        if b != nxt["i"]:
            raise SystemExit(f"closure run [{a}, {b}] does not end at the box at v{nxt['i']}: not the College run")
        runs += [[a, WHOLE_SPLIT[0]], [WHOLE_SPLIT[1], b]]
    else:
        runs.append([a, b])
cor["closure_runs"] = runs
ch = race.get("chicanes") or []
race["chicanes"] = [c for c in ch if c.get("name") != CHICANE]
if not race["chicanes"]:
    race.pop("chicanes")
for lo in cfg["layouts"]:
    if lo.get("id") == CW:
        lo["lap"] = LAP
lap = race["laps"][LAP]
lap["corridor"] = copy.deepcopy(cor)
lap["roads"] = list(cfg["route"]["roads"])
lap.setdefault("_doc", "ledger 0055 round 2: the Speedway's own lap, the mainline with the northbound road of College's split "
                       "(college_nb) in place of rows %d..%d. Vertex k of this lap is the mainline's vertex k." % (A0, A1))
for z in (cfg.get("terrain", {}).get("ground_release", {}) or {}).get("zones") or []:
    if z.get("name") == ZONE:
        z["v"] = [float(A0), float(A1)]
        z.pop("s_m", None)


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"+ {path}.{k} = {json.dumps(b[k])[:150]}")
            elif k not in b:
                out.append(f"- {path}.{k} (was {json.dumps(a[k])[:150]})")
            else:
                out += diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(isinstance(x, dict) for x in a + b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"~ {path}: {json.dumps(a)[:130]} -> {json.dumps(b)[:130]}")
    return out


for line in diff(before, cfg):
    print(line)
if WRITE:
    if not _pre.exists():
        shutil.copy2(cfg_path, _pre)
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"[written] {cfg_path}")
