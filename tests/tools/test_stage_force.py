"""tools/stage_force.py: Kevin's force by place and row. A red drive_test may be force-installed only where every red
reason is a declared one, for the declared build versions. A window may name its layout (ledger 0085, Pikes Peak's
three laps): it then covers that layout's stations only; without one it covers every report, as before."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import stage_force as sf  # noqa: E402


def _rep(und=(), soft=0, lap=750.0):
    return {"lap_m": lap, "soft_top_in_lane": soft, "undrivable_corners": len(und),
            "worst": {"undrivable_all": [list(u) for u in und]}}


def _cfg(windows, version="0.2.0"):
    return {"version": version, "gates": {"drive1": {"force_exemptions": {"stage": {
        "versions": ["0.2.0"], "undrivable_corners": windows}}}}}


HAIRPIN = [(665.0, 112.0, 8.0), (669.0, 121.0, 8.4), (681.0, 118.0, 8.4)]


def test_a_layout_window_covers_its_own_layout():
    v = sf.verdict(_cfg([{"id": "hairpin", "layout": "infield", "s_m": [650, 695]}]),
                   {"oval": _rep(), "infield": _rep(HAIRPIN)})
    assert v["force_install_ok"] is True and len(v["covered"]) == 3


def test_a_layout_window_never_covers_another_layout():
    v = sf.verdict(_cfg([{"id": "hairpin", "layout": "infield", "s_m": [650, 695]}]),
                   {"roadcourse": _rep([(670.0, 115.0, 8.0)]), "infield": _rep(HAIRPIN)})
    assert v["force_install_ok"] is False
    assert any(w.startswith("roadcourse: undrivable corner at s 670") for w in v["why_not"])


def test_a_window_without_a_layout_covers_every_report_as_before():
    v = sf.verdict(_cfg([{"id": "hairpin", "s_m": [650, 695]}]),
                   {"roadcourse": _rep([(670.0, 115.0, 8.0)]), "infield": _rep(HAIRPIN)})
    assert v["force_install_ok"] is True


def test_another_red_row_or_another_version_refuses():
    w = [{"id": "hairpin", "layout": "infield", "s_m": [650, 695]}]
    assert sf.verdict(_cfg(w), {"infield": _rep(HAIRPIN, soft=1)})["force_install_ok"] is False
    assert sf.verdict(_cfg(w, version="0.2.1"), {"infield": _rep(HAIRPIN)})["force_install_ok"] is False
