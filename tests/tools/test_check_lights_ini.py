"""Ledger 0054 P4 step 2 — tools/check_lights_ini.py: one CSP [LIGHT_N] per lamp at its lens on the WRITTEN
ext_config.ini (the 0043 / 0056 duplicate-light class), the approved look on every block."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_lights_ini", ROOT / "tools" / "check_lights_ini.py")
CL = importlib.util.module_from_spec(_spec)
sys.modules["check_lights_ini"] = CL
_spec.loader.exec_module(CL)

CFG = {"intensity": 0.015, "range_m": 25.0, "color": [1.0, 0.647, 0.118], "spot_deg": 150, "spot_sharpness": 0.2,
       "range_gradient_offset": 0.5, "specular_mult": 0.1}
LENSES = [[10.0, 11.8, 100.0], [60.0, 12.1, 100.0], [110.0, 11.9, 100.0]]


def _lights(n=3):
    return {"lampheads": [[l[0] - 1.0, l[1] - 2.0, l[2]] for l in LENSES[:n]], "provenance": {"lens_xyz": LENSES[:n]}}


def _block(n, x, y, z, color="255, 165, 30, 0.015"):
    return (f"[LIGHT_{n}]\nACTIVE = 1\nPOSITION = {x:.2f}, {y:.2f}, {z:.2f}\nDIRECTION = 0, -1, 0\nCOLOR = {color}\n"
            "COLOR_OFF = 0, 0, 0, 0\nSPOT = 150\nSPOT_SHARPNESS = 0.2\nRANGE = 25.0\nRANGE_GRADIENT_OFFSET = 0.5\n"
            "SPECULAR_MULT = 0.1\nFADE_AT = 800\nFADE_SMOOTH = 200\nCONDITION = NIGHT_SMOOTH\n\n")


def _ini(lenses, **kw):
    # the writer: POSITION = (x, y - 0.15, -z) in the kn5 frame, numbered 0..n-1
    return "[INCLUDE]\nINCLUDE = common/conditions.ini\n\n" + "".join(
        _block(i, l[0], l[1] - CL.LIGHT_DROP_M, -l[2], **kw) for i, l in enumerate(lenses))


def test_one_light_per_lamp_at_its_lens_passes():
    r = CL.check(_lights(), CL.parse_lights(_ini(LENSES)), CFG)
    assert r["ok"], r["problems"]
    assert (r["n_lamps"], r["n_lights"], r["matched"]) == (3, 3, 3)


def test_a_duplicate_light_at_one_lens_fails():
    txt = _ini(LENSES) + _block(3, LENSES[1][0], LENSES[1][1] - CL.LIGHT_DROP_M, -LENSES[1][2])
    r = CL.check(_lights(), CL.parse_lights(txt), CFG)
    assert not r["ok"]
    assert any("4 [LIGHT_N] blocks for 3 lamps" in p for p in r["problems"])
    assert any("duplicate light" in p for p in r["problems"]), r["problems"]


def test_a_missing_light_and_a_light_off_every_lens_fail():
    r = CL.check(_lights(), CL.parse_lights(_ini(LENSES[:2])), CFG)
    assert not r["ok"] and any("have no light at their lens" in p for p in r["problems"]), r["problems"]
    off = LENSES[:2] + [[110.0, 11.9, 104.0]]            # the third light 4 m off its lens
    r = CL.check(_lights(), CL.parse_lights(_ini(off)), CFG)
    assert not r["ok"] and any("stands at no recorded lens" in p for p in r["problems"]), r["problems"]


def test_the_look_must_match_the_config_on_every_block():
    r = CL.check(_lights(), CL.parse_lights(_ini(LENSES, color="255, 165, 30, 0.03")), CFG)
    assert not r["ok"] and any(p.startswith("COLOR = ") for p in r["problems"]), r["problems"]
    mixed = _ini(LENSES[:2]) + _block(2, LENSES[2][0], LENSES[2][1] - CL.LIGHT_DROP_M, -LENSES[2][2], color="255, 165, 30, 0.02")
    r = CL.check(_lights(), CL.parse_lights(mixed), CFG)
    assert not r["ok"] and any("COLOR differs between lights" in p for p in r["problems"]), r["problems"]


def test_parse_reads_only_light_blocks_and_crlf():
    txt = "[LIGHT_POLLUTION]\nX = 1\n\n" + _ini(LENSES).replace("\n", "\r\n") + "[LIGHT_DANGER_0]\nPOSITION = 1, 2, 3\n"
    blocks = CL.parse_lights(txt)
    assert [b["n"] for b in blocks] == [0, 1, 2]
    assert blocks[0]["pos"] == (10.0, round(11.8 - CL.LIGHT_DROP_M, 2), -100.0)
    assert blocks[0]["keys"]["COLOR"] == "255, 165, 30, 0.015"
