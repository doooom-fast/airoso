"""tools/patch_median_measured.py: Lake Murray's installed trees.txt, the median bushes at their lidar heights (Kevin
2026-11-18: "B: lidar height each"). The patched file is what make_treefx writes under scenery.treefx.median_measured,
every other line byte for byte; it refuses a block it can't match."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests" / "tools"))
import make_treefx as mt  # noqa: E402
import patch_median_measured as pm  # noqa: E402
import test_make_treefx_plan as tp  # noqa: E402

INI = {"Bush.bin": "[BASIC]\nHEIGHT=20.660005569458\nWIDTH=34.3843803405762 ; from Algarve\n",
       "Sage.bin": "; sage\n[BASIC]\nNAME=Sage\nHEIGHT = 3.0\nWIDTH = 2.5\n[LOD_0]\nHEIGHT=99\n"}


def _models(d):
    m = d / "models"
    m.mkdir()
    for name, ini in INI.items():
        with zipfile.ZipFile(m / name, "w") as z:
            z.writestr(f"{name[:-4]}/tree.ini", ini)
            z.writestr(f"{name[:-4]}/lod0.mesh", b"\x00" * 16)
    return m


def _run(d, txt, extra=()):
    (d / "trees.txt").write_text(txt, encoding="utf-8")
    return pm.main(["--trees-txt", str(d / "trees.txt"), "--models", str(_models(d)),
                    "--scatter", str(d / "data" / "scatter_positions.json"),
                    "--heights", str(d / "source" / "vegetation" / "m.json"),
                    "--out", str(d / "out.txt"), "--report", str(d / "rep.json"), *extra])


def test_patched_installed_file_equals_what_make_treefx_writes():
    hs, cs = [5.13, 0.07, 12.4, 2.2, None, 0.31], [3.2, None, None, 1.4, None, 0.9]
    before = mt.plan(tp._median_project(hs, cs, config=False))["lines"]
    after = mt.plan(tp._median_project(hs, cs))["lines"]
    d = tp._median_project(hs, cs)
    txt = "configure: seed = 1\ntree: PalmV1.bin; pos=1.00, 0.00, -2.00; angle = 5; size = 0.90\n" + "\n".join(before) + "\n"
    assert _run(d, txt) == 0
    out = (d / "out.txt").read_text(encoding="utf-8").split("\n")
    assert out[:2] == txt.split("\n")[:2]                                   # another zone's block: untouched
    assert out[2:-1] == after and out[-1] == ""
    rep = json.loads((d / "rep.json").read_text())
    assert rep["measured"] == 4 and rep["kept"] == 2 and rep["lines_changed"] == 4
    assert rep["per_model"]["Bush.bin"]["HEIGHT"] == pytest.approx(20.660005569458)
    assert rep["per_model"]["Sage.bin"]["WIDTH"] == 2.5                       # [BASIC] only, not [LOD_0]


def test_refuses_a_line_it_cannot_place_and_writes_nothing():
    d = tp._median_project([5.0, 1.0], [None, None])
    lines = mt.plan(tp._median_project([5.0, 1.0], [None, None], config=False))["lines"]
    lines.append("tree: Bush.bin; pos=999.00, 0.10, -1.00; angle = 3; size = 0.030")
    with pytest.raises(SystemExit, match="matches 0 spots"):
        _run(d, "\n".join(lines) + "\n")
    assert not (d / "out.txt").exists()
    with pytest.raises(SystemExit, match="median_planting block"):
        _run(tp._median_project([5.0], [None]), "configure: seed = 1\n")
