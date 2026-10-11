"""tools/barrier_bands.py on the real Lake Murray declaration (ledger 0047).

Pins the self-gates the band writer enforces and the measured shape of the declaration: six centre
runs on the four wide arterials whose island-side ends land exactly on the ten island noses, no chain
vertex on an island interior or on Alvarado (13.0 m), the kerb-line strips gapped only inside the
three declared bridge spans, seven race kerbs at the five corners the sign detector finds, and the
chain length. A run drawn one vertex short of a nose, across an island, or onto Alvarado must fail.
Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import barrier_bands as bb  # noqa: E402

SD = ROOT / "tracks" / "san-diego-lake-murray"
NOSES = [846, 1073, 1096, 1258, 1374, 1487, 1540, 1739, 2183, 2297]
ALVARADO_LAST = 779


def _project() -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    shutil.copyfile(SD / "track.config.json", d / "track.config.json")
    for f in ("centerline.local.json", "median_bands.json", "mouths.json", "bridge.spans.auto.json"):
        shutil.copyfile(SD / "data" / f, d / "data" / f)
    return d


def _island_w(d: Path):
    return json.loads((d / "data" / "median_bands.json").read_text())["island_w_by_vertex"]


def test_lake_murray_declaration_passes_its_self_gates():
    d = _project()
    out = bb.build(d)
    assert out["fails"] == [], out["fails"]
    s = out["summary"]
    assert s["centre_runs"] == 6 and s["corners"] == 5 and s["kerbs"] == 7 and s["edge_gaps"] == 3
    assert abs(s["chain_length_m"] - 8525.0) <= 40.0, s["chain_length_m"]
    assert s["nose_vertices"] == NOSES
    assert out["params"]["narrow_streets"] == ["Alvarado Road"]
    assert (d / "data" / "barrier_bands.json").exists()


def test_chain_never_on_an_island_interior_or_on_alvarado_and_ends_on_noses():
    d = _project()
    out = bb.build(d)
    cw = out["centre_w_by_vertex"]
    iw = _island_w(d)
    assert len(cw) == len(iw) == 4499
    on_island = [v for v, w in enumerate(cw) if w > 0 and iw[v] > 0 and v not in NOSES]
    assert on_island == [], on_island[:10]
    assert all(cw[v] == 0 for v in range(0, ALVARADO_LAST + 1))
    assert all(cw[v] > 0 for v in NOSES)                    # butt joint: the chain reaches every nose
    ends = sorted(set(r["i"] for r in out["runs"] if r["kind"] == "centre")
                  | set(r["j"] for r in out["runs"] if r["kind"] == "centre"))
    assert all(n in ends for n in NOSES), ends
    assert set(ends) - set(NOSES) == {780, 4440}           # the two free ends


def test_edge_strips_gap_only_inside_the_declared_bridge_spans():
    d = _project()
    out = bb.build(d)
    spans = out["bridge_spans_m"]
    assert len(spans) == 3
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    pts = cl["points_xyz_m"]
    st = [0.0]
    import math
    for i in range(1, len(pts)):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    es = out["edge_strip_by_vertex"]
    for v, flag in enumerate(es):
        inside = any(a <= st[v] <= b for a, b in spans)
        assert bool(flag) == (not inside), (v, st[v], flag)
    assert out["edge_inset_by_vertex"][300] == 0.82 and out["edge_inset_by_vertex"][612] == 0.0
    assert [m["connector"] for m in out["closed_mouths"]] == ["del_cerro_blvd", "del_cerro_blvd", "medium#2+0"]
    assert all(len(m["polyline_xyz_m"]) >= 3 for m in out["closed_mouths"])


def test_the_five_inside_lip_folds_are_declared_as_trimmed_corners():
    """2026-10-11: where the inside lip is tighter than the strip's offset the strip is trimmed to the curb's own
    corner — the declaration carries each corner (race_furniture.edge_fold_corners, the author's own trim), so
    every gate stands on what is built: SD's five right-handers, all side R, three crossing loops (the hairpin,
    College/Navajo, Navajo/Jackson) and two extended Z-folds (Jackson/Lake Murray's flare, the seam's 27.5 ->
    17 m width step)"""
    import race_furniture as rf
    d = _project()
    out = bb.build(d)
    ec = out["edge_corners"]
    assert out["summary"]["edge_corners"] == 5 and out["fails"] == []
    assert [(c["side"], c["kind"], c["in_vertex"], c["out_vertex"]) for c in ec] == [
        ("R", "loop", 763, 774), ("R", "loop", 1508, 1517), ("R", "loop", 2314, 2324),
        ("R", "extend", 3292, 3300), ("R", "extend", 4495, 5)], ec
    assert out["edge_fold_vertices"]["L"] == [] and len(out["edge_fold_vertices"]["R"]) == 41
    assert all(c["removed"] and 60.0 < abs(c["turn_deg"]) < 95.0 and 1.0 < c["mitre"] < 1.5 for c in ec)
    # the declaration IS the author's computation: the sweep matches it exactly (and refuses a drifted one)
    cl = json.loads((d / "data" / "centerline.local.json").read_text())
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    plans = rf.edge_plans(pts, widths, out)
    built = [c for p in plans for c in p.get("fold_corners", [])]
    assert len(built) == 5
    drift = dict(out, edge_corners=[dict(c, xz=[c["xz"][0] + 0.2, c["xz"][1]]) if i == 0 else c for i, c in enumerate(ec)])
    try:
        rf.edge_plans(pts, widths, drift)
    except SystemExit as e:
        assert "edge_corners" in str(e)
    else:
        raise AssertionError("a drifted declaration was authored")


def test_kerbs_outside_only_at_chained_corners_both_lips_elsewhere():
    d = _project()
    out = bb.build(d)
    by_apex = {}
    for k in out["kerbs"]:
        by_apex.setdefault(k["apex"], set()).add(k["kind"])
    assert by_apex == {0: {"outside", "inside"}, 770: {"outside", "inside"},
                       1514: {"outside"}, 2319: {"outside"}, 3297: {"outside"}}, by_apex
    assert all(k["side"] == "L" for k in out["kerbs"] if k["kind"] == "outside")   # right-handers: outside = left lip


def _with_runs(d: Path, runs):
    cfg = json.loads((d / "track.config.json").read_text(encoding="utf-8"))
    cfg["race"]["centre_runs"] = runs
    p = d / "edited.config.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def test_a_run_one_vertex_short_of_a_nose_fails():
    d = _project()
    out = bb.build(d, "x.json", _with_runs(d, [[780, 845]]))
    assert any("one vertex short of the island nose" in f for f in out["fails"]), out["fails"]


def test_a_run_across_an_island_or_on_alvarado_fails():
    d = _project()
    out = bb.build(d, "x.json", _with_runs(d, [[780, 900]]))
    assert any("on a median island" in f for f in out["fails"]), out["fails"]
    out = bb.build(d, "x.json", _with_runs(d, [[300, 400]]))
    assert any("< 17.0 m wide" in f or "narrow street" in f for f in out["fails"]), out["fails"]
