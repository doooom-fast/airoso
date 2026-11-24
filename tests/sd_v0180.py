"""The Lake Murray data the real-data race / corridor / spawn tests pin: v0.18.0's built centreline and its race
declaration, frozen in tests/fixtures/lake_murray_v0180/data/ (git 8f25c48, the v0.18.1 merge before its install).

Why a frozen copy (2026-10-18): those tests pin numbers measured on v0.18.0's road (the noses, the pins, the kerb
census, the study solution, the stations the vertex-declared zones resolve to — their own docs say "the data pinned
here is the installed v0.18.0 build's"), but they read tracks/san-diego-lake-murray/data/ live. The v0.18.1 install
(704f1d0) synced the rebuilt road into it — College on its real alignment, the lap 6.6 m shorter — and ten of them
failed on main with nothing wrong in any tool. With the data pinned the way the docs already said, the tools are judged
on the road the numbers came from; the current config (tracks/san-diego-lake-murray/track.config.json) still rides along
as it did at 8f25c48. Not a test module (tests/run_tests.py collects test_*.py)."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "tracks" / "san-diego-lake-murray"
DATA = Path(__file__).resolve().parent / "fixtures" / "lake_murray_v0180" / "data"
FILES = ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json",
         "finished_centerline.json", "barrier_bands.json")
# 2026-11-23 (ledger 0055 round 2): the same thing a second time. The spawn and swept-mouth tests read
# tracks/san-diego-lake-murray/data/ live and pin numbers measured on the one-road College; round 2 puts College's two
# roads into that data (the mainline on the southbound road, no island on rows v1117-1475). The five files they read,
# frozen as Lake Murray 0.20.4 has them (main 04e0a9b4); the config rides along through one_road_college below.
DATA_0204 = Path(__file__).resolve().parent / "fixtures" / "lake_murray_v0204" / "data"


ONE_ROAD = Path(__file__).resolve().parent / "fixtures" / "lake_murray_v0180" / "college_one_road.json"


def one_road_college(cfg: dict) -> dict:
    """the current config with College declared as the pinned v0.18.0 road has it: ONE slab, its island and the
    crossover chicane (2026-11-23, ledger 0055 round 2). Today's config declares College's two roads
    (tracks/san-diego-lake-murray/source/college_r2/college_race_config.py): the Speedway on its own lap `college`,
    whose northbound piece the pinned data has none of; no chicane; the corridor's whole street in two stretches and
    the College closure run cut at the forks; the released zone over the whole split; two plant lists the pinned data
    has no files for. Each is put back as main 04e0a9b4 declared it (fixtures/lake_murray_v0180/college_one_road.json),
    so the tests that pin numbers measured on the one-road College still judge the tools on that road. Every other
    key rides along from today's config, as before. A config that never had the split comes back unchanged."""
    if not (cfg.get("route") or {}).get("college_split"):
        return cfg
    old = json.loads(ONE_ROAD.read_text(encoding="utf-8"))
    cfg["route"].pop("college_split")
    race = cfg["race"]
    for lo in cfg.get("layouts") or []:
        if lo.get("lap") == "college":
            lo.pop("lap")
    (race.get("laps") or {}).pop("college", None)
    if old["race.chicanes"]:
        race["chicanes"] = json.loads(json.dumps(old["race.chicanes"]))
    race["corridor"]["whole"] = list(old["race.corridor.whole"])
    race["corridor"]["closure_runs"] = [list(r) for r in old["race.corridor.closure_runs"]]
    zones = ((cfg.get("terrain") or {}).get("ground_release") or {}).get("zones") or []
    for i, z in enumerate(zones):
        if z.get("name") == "college_split_cut":
            zones[i] = dict(old["terrain.ground_release.zones.college_split_cut"])
    tfx = (cfg.get("scenery") or {}).get("treefx") or {}
    tfx.pop("median_spots", None)
    tfx.pop("lidar_plants", None)
    return cfg


def project() -> Path:
    """a scratch track dir: the current track.config.json (College as one road: one_road_college) + start_positions.json
    and the pinned v0.18.0 data"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    cfg = one_road_college(json.loads((SD / "track.config.json").read_text(encoding="utf-8")))
    (d / "track.config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in FILES:
        shutil.copyfile(DATA / f, d / "data" / f)
    return d


def loop_config(cfg: dict) -> dict:
    """the current config as the loop-only race tests read it (2026-10-18, ledger 0054 P3): the north network's
    route.aprons (J1's R 30 return, authored by tools/author_aprons_blend.py into data/aprons.json — a build artefact
    the pinned v0.18.0 data has none of) taken out; barrier_bands refuses a declared apron without its record. A test
    that judges the apron declares it itself (tests/tools/test_barrier_bands_swept.py). College is the pinned road's
    one slab (one_road_college)."""
    one_road_college(cfg)
    cfg.get("route", {}).pop("aprons", None)
    # ... and A7's two outside-kerb drops at the north mouths (J1 apex 1514, J5 apex 2319): the loop's own kerb census
    # (8 kerbs, 2 dropped) is what these tests pin; the swept tests judge A7's drops with the mouths they belong to
    kerbs = cfg.get("race", {}).get("kerbs") or {}
    if "trims" in kerbs:
        kerbs["trims"] = [t for t in kerbs["trims"] if not (t.get("kind") == "outside" and t.get("apex") in (1514, 2319)
                                                             and "Ledger 0054 A7" in str(t.get("why", "")))]
    return cfg

