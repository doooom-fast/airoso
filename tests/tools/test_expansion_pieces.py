"""tools/expansion_pieces.py + tools/junction_pad.py (ledger 0054 P3 steps 1, 2, 5): the north pieces as connectors and
the redesigned junction pads, on the committed intermediate (data/expansion.north.json)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402
import junction_pad as jp  # noqa: E402

SRC = ROOT / "tracks" / "san-diego-lake-murray" / "data" / "expansion.north.json"
DOC, PCS = ep.load(SRC)
DESIGN = jp.design_pads(DOC, PCS)


def _cut_of(pid, end):
    for pad in DESIGN.values():
        for a in pad["arms"]:
            if a["kind"] == "route" and a["piece"] == pid and a["piece_end"] == end:
                return a
    return None


def test_every_piece_is_one_connector_curb_to_curb_on_its_pavement_midline():
    for pid in "ABCD":
        c = ep.piece_connector(DOC, PCS, pid)
        assert c["name"] == ep.PIECE_CONN[pid]
        pc = PCS[pid]
        for p, w in list(zip(c["points_xyz_m"], c["widths_m"]))[c["expansion"]["weld_points"]:][::25]:
            _d, s, lat = pc.project(p[0], p[2])
            L, R = pc.curbs(s)
            assert abs(w - (L - R)) < 0.05, (pid, s, w, L - R)
            assert abs(lat - (L + R) / 2.0) < 0.25, (pid, s, lat, (L + R) / 2.0)
        g, _at = ep.grade_report(c)
        assert g <= ep.MAX_GRADE + 1e-9, (pid, g)          # A6: the 11 % cap binds nowhere


def test_a_pad_end_stops_exactly_on_the_redesigned_cut_line():
    for pid in "ABCD":
        c = ep.piece_connector(DOC, PCS, pid)
        end = "end" if pid != "D" else "start"            # D runs J5 -> J4: its far end is the J4 (start) cut
        a = _cut_of(pid, end)
        (lx, lz), (rx, rz) = a["cut_line_xz"]
        q = c["points_xyz_m"][-1]
        assert math.hypot(q[0] - (lx + rx) / 2, q[2] - (lz + rz) / 2) < 0.02, pid
        assert abs(c["widths_m"][-1] - math.hypot(rx - lx, rz - lz)) < 0.05, pid
    for pid in "BC":                                       # both ends on a pad
        c = ep.piece_connector(DOC, PCS, pid)
        (lx, lz), (rx, rz) = _cut_of(pid, "start")["cut_line_xz"]
        q = c["points_xyz_m"][0]
        assert math.hypot(q[0] - (lx + rx) / 2, q[2] - (lz + rz) / 2) < 0.02, pid


def test_welded_pieces_start_with_their_p1_weld_stub_and_d_runs_j5_to_j4():
    for pid, wid in (("A", "W1"), ("D", "W5")):
        c = ep.piece_connector(DOC, PCS, pid)
        w = next(x for x in DOC["welds"] if x["id"] == wid)["connector"]
        n = c["expansion"]["weld_points"]
        assert n == len(w["points_xyz_m"])
        for a, b in zip(c["points_xyz_m"][:n], w["points_xyz_m"]):
            assert abs(a[0] - b[0]) < 1e-3 and abs(a[2] - b[2]) < 1e-3
    assert ep.piece_connector(DOC, PCS, "D")["expansion"]["reverse"] is True


def test_the_profile_fit_follows_3dep_and_is_smooth():
    for pid in "ABCD":
        pc = PCS[pid]
        dev = sorted(abs(pc.y_fit(s) - float(r["y_3dep"])) for s, r in zip(pc.s, pc.rows))
        assert dev[int(0.95 * (len(dev) - 1))] < 0.15, pid
        ys = [pc.y_fit(k * 3.0) for k in range(int(pc.length / 3))]
        g = [(b - a) / 3.0 for a, b in zip(ys, ys[1:])]
        assert max(abs(b - a) for a, b in zip(g, g[1:])) < 0.012, pid    # < 0.4 %-pt per metre


def test_paint_layout_per_road():
    B = PCS["B"]
    keys = {k for k, *_ in ep.layout(B, 300.0, [])}
    assert {"dy_L", "dy_R", "park_L", "park_R"} <= keys                   # Princess View: double yellow, parking
    D = PCS["D"]
    s_painted = next(s for s, r in zip(D.s, D.rows) if r["median_type"] == "painted" and float(r["median_w_m"]) > 2.0)
    keys = {k for k, *_ in ep.layout(D, s_painted, [])}
    assert {"pm_L1", "pm_L2", "pm_R1", "pm_R2", "bike_L", "buf_L"} <= keys  # double-double yellow, buffered bike lanes
    A = PCS["A"]
    runs = [(float(m["s_from"]), float(m["s_to"])) for m in DOC["medians"] if m["piece"] == "A" and m["raised"]]
    lay = ep.layout(A, 400.0, runs)
    assert any(k == "med_edge_L" for k, *_ in lay) and any(k.startswith("lane_") for k, *_ in lay)
    for pid, pc in PCS.items():                                            # no lane narrower than LANE_MIN_M
        for s in pc.s[::40]:
            offs = sorted(o for k, o, c_, _d in ep.layout(pc, s, []) if c_ == "white")
            L, R = pc.curbs(s)
            assert all(R - 0.01 <= o <= L + 0.01 for o in offs), (pid, s)


def test_design_pads_cut_where_the_piece_is():
    for J, pad in DESIGN.items():
        assert len(pad["arms"]) == 4 and len(pad["corners"]) == 4
        for a in pad["arms"]:
            if a["kind"] != "route":
                continue
            pc = PCS[a["piece"]]
            p, _t, n = pc.frame(a["cut_s"])
            L, R = pc.curbs(a["cut_s"])
            cl = [(p[0] + n[0] * L, p[1] + n[1] * L), (p[0] + n[0] * R, p[1] + n[1] * R)]
            for q in a["cut_line_xz"]:
                assert min(math.dist(q, c) for c in cl) < 0.05, (J, a["name"])
        for c in pad["corners"]:
            assert 5.0 <= c["R_m"] <= 12.0


def test_outline_as_built_welds_the_rows_and_runs_curbs_between_cuts():
    for J, pad in DESIGN.items():
        rows = {}
        for a in pad["arms"]:
            if a["kind"] == "route":
                (lx, lz), (rx, rz) = a["cut_line_xz"]
                rows[a["name"]] = {"L": (lx, 1.0, lz), "C": ((lx + rx) / 2, 1.0, (lz + rz) / 2), "R": (rx, 1.0, rz)}
        sh = {sid: [1.2, 1.2, 1.2] for sid in pad["stubs"]}
        ob = jp.outline_as_built(pad, pad["stubs"], rows, sh)
        assert jp._area(ob["outline"]) > 1000.0
        assert len(ob["runs"]) == 4 and len(ob["barriers"]) == 2
        for t0, t1 in ob["run_ends"]:
            for t in (t0, t1):
                assert t[0] in ("arm", "stub") and t[2] in ("L", "R", 0, 2)
        for name, r in rows.items():                        # the three row vertices ARE outline vertices
            for k in ("L", "C", "R"):
                assert any(math.hypot(q[0] - r[k][0], q[1] - r[k][2]) < 1e-9 for q in ob["outline"]), (J, name, k)
        steps = [math.dist(ob["outline"][i], ob["outline"][(i + 1) % len(ob["outline"])]) for i in range(len(ob["outline"]))]
        assert max(steps) <= jp.BOUNDARY_STEP_M + 1e-6
