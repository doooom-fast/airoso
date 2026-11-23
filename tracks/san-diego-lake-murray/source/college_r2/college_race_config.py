"""College split: EVERY edit to track.config.json, in one place. STEP-DESIGN.md has the why.

    python college_race_config.py <project dir> [--write]     a workshop's own config (a scratch workshop)
    python college_race_config.py --repo [--write]            airoso's own tracks/san-diego-lake-murray/track.config.json

What changes (and nothing else); every edit is idempotent, a second run changes nothing:

  route.college_split   the opt-in key of the chain's author step `college_split` (tools/ship_track.sh): absent = no-op.
  race.laps.college     the Speedway's own lap, from the committed college_split.data.json (`lap`: the mainline, the
                        northbound road, the mainline); .corridor = race.corridor (the lap's vertex k is the mainline's
                        vertex k, so the same numbers declare the same places) and .roads = route.roads.
  layouts               race_cw (Lake Murray Speedway, clockwise = northbound on College) runs on the lap `college`.
                        race_acw (Speedway Reverse) stays on the mainline, which IS the southbound road there.
  race.chicanes         the entry `college_split` goes (the crossover existed because both directions shared one slab).
  race.corridor         whole becomes two stretches: the one it was, and the TWO ROADS of the split, [NOSE-1, TAIL+1]: each
                        road is the whole street for its direction (both curb strips, no closure). The closure run that held
                        College, [777, 1506], becomes two: [777, NOSE-1] and [TAIL+1, 1506]. So in each FORK the closure runs
                        on from the island's end to the point where the roads part, and pins there; it is what divides the
                        fork between the two directions, as the island did. (Tried first: whole through the forks and on
                        to the box. The declaration's own gates refused it: the island that stays north of the split stood
                        in an open zone, its top reachable (2 forbidden probes), and a run ending at the fork's outer row
                        turned too tightly past the island's nose, plan radius 19.6 m under the 20 m minimum.)
  terrain.ground_release.zones `college_split_cut`
                        v becomes the whole split (rows A0..A1): the bank's top and the east shelf are released ground.
  scenery.treefx.median_spots   the exclusion list and the new foot heights of the median spots, by file
                        (source/college_r2/college_plants.median_spots.json, written by college_plants_data.py).
  scenery.treefx.lidar_plants   the bank's own plants off the lidar (college_bank_plants.lidar_plants.json, the entry
                        college_plants_data.py writes; its list is source/college_r2/college_bank_plants.json).

  route.median_tops, lawn_as_grass   (--medians; the medians, ledger 0055 "Known defect", option (a)) every island's grass
                        top in its own object, 1LAWN_median (tools/author_median_tops_blend.py, the chain's author step
                        median_tops), and the LAWN surface key written with GRASS's own values.

Without --write: prints what would change. With --write: rewrites the config. A workshop's config is dumped plain and
the two plant files are copied to <project>/source/college_r2/ (in the chain ship.json's sync_in brings them); airoso's
own keeps its hand-compacted lines (the dump is put back into the file's own layout, or the write is refused)."""
import copy
import difflib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
args = sys.argv[1:]
WRITE = "--write" in args
REPO = "--repo" in args
paths = [a for a in args if not a.startswith("--")]
if REPO == bool(paths):
    raise SystemExit("usage: college_race_config.py <project dir> [--write]  |  college_race_config.py --repo [--write]")
proj = HERE.parents[1] if REPO else Path(paths[0])
S = json.loads((HERE / "college_split.data.json").read_text(encoding="utf-8"))
A0, A1 = S["mainline"]["from_v"], S["mainline"]["to_v"]
NOSE, TAIL = S["rows"]["v"][0], S["rows"]["v"][-1]
LAP = "college"
CW, CHICANE, ZONE = "race_cw", "college_split", "college_split_cut"
SPOTS_FILE = "source/college_r2/college_plants.median_spots.json"
ENTRY = json.loads((HERE / "college_bank_plants.lidar_plants.json").read_text(encoding="utf-8"))
PLANTS_FILE = ENTRY["file"]

cfg_path = proj / "track.config.json"
text0 = cfg_path.read_text(encoding="utf-8")
before = json.loads(text0)
cfg = copy.deepcopy(before)
race = cfg["race"]
cor = race["corridor"]

cfg["route"]["college_split"] = {
    "_doc": "ledger 0055 round 2 (Kevin: 'realism+'): College Avenue between rows v%d and v%d is two roads, the mainline on the "
            "southbound one and the northbound one a connector (college_nb), with a planted bank between them. Opt-in key of the "
            "chain's author step college_split (tools/ship_track.sh, first in the author phase): "
            "tracks/san-diego-lake-murray/source/college_r2/college_split_data.py --chain writes the project's data, then "
            "college_split_blend.py, college_middle_blend.py and college_ground_blend.py edit loop.blend, each self-checked and "
            "a no-op on a scene that already carries it. Absent = the step does nothing." % (A0, A1),
    "rows": [A0, A1],
}

# the lap, from the committed data (college_split_data.py --chain holds the project's data to it)
lap = dict(race.setdefault("laps", {}).get(LAP) or {})
lap.update(S["lap"])
lap["_doc"] = ("ledger 0055 round 2: the Speedway's own lap, the mainline with the northbound road of College's split "
               "(college_nb) in place of rows %d..%d. Vertex k of this lap is the mainline's vertex k." % (A0, A1))
race["laps"][LAP] = lap

# the two roads are whole street; each fork is closure run, pinned where the roads part
boxes = sorted(cor["boxes"], key=lambda b: b["i"])
nxt = next(b for b in boxes if b["i"] >= A1)                 # the College / Navajo box
WHOLE_SPLIT = [NOSE - 1, TAIL + 1]
old_whole = cor["whole"] if isinstance(cor["whole"][0], list) else [cor["whole"]]
cor["whole"] = [w for w in old_whole if w != WHOLE_SPLIT] + [WHOLE_SPLIT]
runs = []
for a, b in cor["closure_runs"]:
    if a < WHOLE_SPLIT[0] and b > WHOLE_SPLIT[1]:            # the run that held College, both forks and the split
        if b != nxt["i"]:
            raise SystemExit(f"closure run [{a}, {b}] does not end at the box at v{nxt['i']}: not the College run")
        runs += [[a, WHOLE_SPLIT[0]], [WHOLE_SPLIT[1], b]]
    else:
        runs.append([a, b])
if [WHOLE_SPLIT[0]] != [b for a, b in runs if b == WHOLE_SPLIT[0]] or [WHOLE_SPLIT[1]] != [a for a, b in runs if a == WHOLE_SPLIT[1]]:
    raise SystemExit(f"race.corridor.closure_runs {runs}: no run ends at v{WHOLE_SPLIT[0]} and none starts at v{WHOLE_SPLIT[1]}")
cor["closure_runs"] = runs
race["chicanes"] = [c for c in race.get("chicanes") or [] if c.get("name") != CHICANE]
if not race["chicanes"]:
    race.pop("chicanes")
if not any(lo.get("id") == CW for lo in cfg["layouts"]):
    raise SystemExit(f"no layout {CW}")
for lo in cfg["layouts"]:
    if lo.get("id") == CW:
        lo["lap"] = LAP
lap["corridor"] = copy.deepcopy(cor)
lap["roads"] = list(cfg["route"]["roads"])
for z in (cfg.get("terrain", {}).get("ground_release", {}) or {}).get("zones") or []:
    if z.get("name") == ZONE:
        z["v"] = [float(A0), float(A1)]
        z.pop("s_m", None)
tfx = cfg.setdefault("scenery", {}).setdefault("treefx", {})
tfx["median_spots"] = {
    "_doc": "ledger 0055 round 2 (the College split), tools/make_treefx.py: median_planting spots of data/scatter_positions.json "
            "by index, in a file. drop = not planted (on pavement since the split, or a bare spot on the bank, which is planted "
            "from the lidar's measured tops, or a measured spot on the bank's curb ring whose own top is planted in its place); "
            "foot_y = planted where it is, its foot on the bank's top. Written by source/college_r2/college_plants_data.py.",
    "file": SPOTS_FILE,
}
tfx["lidar_plants"] = ENTRY
if "--medians" in args:
    cfg["route"]["median_tops"] = {
        "_doc": "ledger 0055, 'Known defect of the current build' (the Mac 2026-11-23, option (a)): every raised median showed the "
                "road's asphalt between its curbs, because its grass top was part of TERRAIN and the prep sets every 1GRASS vertex "
                "with pavement under it to the deck less 0.02 m (2,486 of 2,486 island rows on 0.20.3). Opt-in key of the chain's "
                "author step median_tops (tools/author_median_tops_blend.py): every island's top is moved, face for face, out of "
                "TERRAIN into this object, which the prep does not pin. The name is the surface and the material: 1LAWN is the "
                "engine table's other physical turf row (the same grass textures this track's ground wears); lawn_as_grass gives "
                "its surface key GRASS's own values. tools/make_treefx.py seats the median plants on it. Absent = no-op.",
        "object": "1LAWN_median",
    }
    cfg["lawn_as_grass"] = True
    cfg["_lawn_as_grass_doc"] = ("ledger 0055 (the medians): scripts/ac/track_folder.py writes the LAWN surface block with the GRASS "
                                 "block's own values, so a car on a median's grass top (1LAWN_median, this track's only LAWN mesh) "
                                 "is on grass, exactly. Absent = LAWN as every other track has it.")


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


changes = diff(before, cfg)
for line in changes:
    print(line)
if not changes:
    print("nothing to change: the config already carries every College edit")


def in_the_files_own_layout(new):
    """airoso's config is a plain indent-2 dump but for a few lines compacted by hand. The new dump with those lines
    put back as the file has them: every block of dump lines the file replaces by its own lines is replaced the same
    way wherever it stands unchanged in the new dump. None when the file's layout cannot be reproduced exactly."""
    for ascii_ in (False, True):
        d0 = json.dumps(before, indent=2, ensure_ascii=ascii_).split("\n")
        t0 = text0.rstrip("\n").split("\n")
        ops = [(d0[i1:i2], t0[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, d0, t0, autojunk=False).get_opcodes()
               if tag != "equal"]

        def put_back(lines):
            for old, mine in ops:
                if not old:
                    return None                                  # the file has lines the dump lacks: not a compaction
                hits = [k for k in range(len(lines) - len(old) + 1) if lines[k:k + len(old)] == old]
                if len(hits) != 1:
                    return None
                lines = lines[:hits[0]] + mine + lines[hits[0] + len(old):]
            return lines

        if put_back(list(d0)) != t0:
            continue
        out = put_back(json.dumps(new, indent=2, ensure_ascii=ascii_).split("\n"))
        if out is not None:
            return "\n".join(out) + ("\n" if text0.endswith("\n") else "")
    return None


if WRITE and changes:
    if REPO:
        text1 = in_the_files_own_layout(cfg)
        if text1 is None or json.loads(text1) != cfg:
            raise SystemExit("NOT WRITTEN: the config's own layout could not be reproduced around the edits; edit it by hand")
        cfg_path.write_text(text1, encoding="utf-8", newline="\n")
    else:
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        for rel in (SPOTS_FILE, PLANTS_FILE):
            dst = proj / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / Path(rel).name, dst)
    print(f"[written] {cfg_path}")
