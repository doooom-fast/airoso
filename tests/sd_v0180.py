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

import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "tracks" / "san-diego-lake-murray"
DATA = Path(__file__).resolve().parent / "fixtures" / "lake_murray_v0180" / "data"
FILES = ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json",
         "finished_centerline.json", "barrier_bands.json")


def project() -> Path:
    """a scratch track dir: the current track.config.json + start_positions.json and the pinned v0.18.0 data"""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    shutil.copyfile(SD / "track.config.json", d / "track.config.json")
    shutil.copyfile(SD / "start_positions.json", d / "start_positions.json")
    for f in FILES:
        shutil.copyfile(DATA / f, d / "data" / f)
    return d


def loop_config(cfg: dict) -> dict:
    """the current config as the loop-only race tests read it (2026-10-18, ledger 0054 P3): the north network's
    route.aprons (J1's R 30 return, authored by tools/author_aprons_blend.py into data/aprons.json — a build artefact
    the pinned v0.18.0 data has none of) taken out; barrier_bands refuses a declared apron without its record. A test
    that judges the apron declares it itself (tests/tools/test_barrier_bands_swept.py)."""
    cfg.get("route", {}).pop("aprons", None)
    # ... and A7's two outside-kerb drops at the north mouths (J1 apex 1514, J5 apex 2319): the loop's own kerb census
    # (8 kerbs, 2 dropped) is what these tests pin; the swept tests judge A7's drops with the mouths they belong to
    kerbs = cfg.get("race", {}).get("kerbs") or {}
    if "trims" in kerbs:
        kerbs["trims"] = [t for t in kerbs["trims"] if not (t.get("kind") == "outside" and t.get("apex") in (1514, 2319)
                                                             and "Ledger 0054 A7" in str(t.get("why", "")))]
    return cfg

