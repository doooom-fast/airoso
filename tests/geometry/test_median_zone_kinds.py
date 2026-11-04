"""scripts/geometry/median_zone.py — the two divider KINDS load independently (ledger 0047).

The island kind (data/median_bands.json) is what every gate read before 0047; the barrier kind
(data/barrier_bands.json: centre chain, kerb-line strips, sealed-mouth polylines) is consulted only
by callers that ask for it. These pin: default kinds = island only (byte-identical behaviour for
every existing caller), the centre / edge / mouth band maths (half-width + 0.6 m laterally, 2 m
along past a run's end, continuous between consecutive declared vertices), one kind disabling on a length mismatch while the other keeps working, and ``reversed()``
mapping vertex i -> n-1-i. Plain ``test_*`` for tests/run_tests.py.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from scripts.geometry.median_zone import MedianZone, ALL_KINDS, MARGIN_M

N = 41           # vertices, 5 m apart along +z: z = 0..200
W = 10.0


def _project(*, island=(10, 20), centre=(25, 35), edge=True, mouth=True, bad_barrier_len=False,
             with_island_file=True, with_barrier_file=True) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    pts = [[0.0, 0.0, 5.0 * i] for i in range(N)]
    (d / "data" / "gate_centerline.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": [W] * N}))
    if with_island_file:
        iw = [4.0 if island[0] <= i <= island[1] else 0.0 for i in range(N)]
        (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": iw}))
    if with_barrier_file:
        n = N - 1 if bad_barrier_len else N
        cw = [0.67 if centre[0] <= i <= centre[1] else 0.0 for i in range(n)]
        bands = {"centre_w_by_vertex": cw,
                 "edge_strip_by_vertex": [1 if edge else 0] * n,
                 "edge_inset_by_vertex": [0.82 if edge else 0.0] * n,
                 "params": {"barrier_half_m": 0.335, "edge_centre_from_lip_m": -0.485},
                 "closed_mouths": ([{"polyline_xyz_m": [[20.0, 0.0, 300.0], [20.0, 0.0, 310.0]]}] if mouth else [])}
        (d / "data" / "barrier_bands.json").write_text(json.dumps(bands))
    return d


def test_default_kinds_are_island_only_and_barrier_is_opt_in():
    z = MedianZone.load(_project())
    assert z is not None and z.n_island == 11 and z.n_barrier == 11 and z.n_edge == N
    assert z.contains(0.0, 75.0)                         # v15: island
    assert not z.contains(0.0, 150.0)                    # v30: centre chain — invisible by default
    assert z.contains(0.0, 150.0, ALL_KINDS)
    assert z.contains(0.0, 150.0, ("barrier",))
    assert not z.contains(0.0, 75.0, ("barrier",))       # the island is not a barrier band


def test_centre_band_is_half_plus_margin_laterally_and_two_metres_along():
    z = MedianZone.load(_project())
    reach = 0.335 + MARGIN_M                             # 0.935
    assert z.contains(reach - 0.05, 150.0, ALL_KINDS)
    assert not z.contains(reach + 0.1, 150.0, ALL_KINDS)
    assert z.contains(0.0, 151.5, ALL_KINDS)             # 1.5 m along from v30
    # 2.5 m from both v30 and v31 — but BETWEEN two declared vertices: the band is continuous there
    # (2026-10-11: the outside-lip edge points stand ~7 m apart and the densified strip fills the gap)
    assert z.contains(0.0, 152.5, ALL_KINDS)
    assert z.contains(reach - 0.05, 152.5, ALL_KINDS) and not z.contains(reach + 0.1, 152.5, ALL_KINDS)
    assert z.contains(0.0, 176.5, ALL_KINDS)             # 1.5 m past the run's last vertex v35
    assert not z.contains(0.0, 177.5, ALL_KINDS)         # 2.5 m past it: outside the band
    assert not z.contains(0.0, 122.5, ALL_KINDS)         # 2.5 m before its first vertex v25 (v24 undeclared)
    assert z.barrier_half_at(30) == 0.335 and z.barrier_half_at(5) == 0.0
    assert z.island_half_at(15) == 2.0 and z.divider_half_at(15) == 2.0 and z.divider_half_at(30) == 0.335


def test_edge_band_sits_at_half_width_plus_offset_on_both_sides():
    z = MedianZone.load(_project())
    ec = W / 2 - 0.485                                   # 4.515 — the strip centre in 'road' mode
    for sgn in (1.0, -1.0):
        assert z.contains(sgn * ec, 100.0, ALL_KINDS)
        assert z.contains(sgn * (ec + 0.9), 100.0, ALL_KINDS)
        assert not z.contains(sgn * (ec + 1.0), 100.0, ALL_KINDS)
        assert not z.contains(sgn * 3.0, 100.0, ALL_KINDS)
        assert z.contains(sgn * ec, 102.5, ALL_KINDS)    # mid-way between v20 and v21: continuous
        assert not z.contains(sgn * (ec + 1.0), 102.5, ALL_KINDS)
    assert z.edge_inset_at(20) == 0.82 and z.edge_strip_at(20)
    assert not z.contains(ec, 100.0)                     # default kinds: not exempt


def test_mouth_polyline_is_a_band_too():
    z = MedianZone.load(_project())
    assert z.contains(20.3, 305.0, ALL_KINDS)
    assert z.contains(20.0, 311.5, ALL_KINDS)            # 1.5 m past the polyline end (ALONG_M)
    assert not z.contains(22.0, 305.0, ALL_KINDS)
    assert not z.contains(20.3, 305.0)


def test_barrier_length_mismatch_disables_that_kind_only():
    z = MedianZone.load(_project(bad_barrier_len=True))
    assert z is not None and z.n_island == 11
    assert not z.has_barrier and z.n_barrier == 0 and z.n_edge == 0
    assert z.contains(0.0, 75.0)                         # the island still works
    assert not z.contains(0.0, 150.0, ALL_KINDS)
    assert z.edge_inset_at(20) == 0.0


def test_barrier_file_alone_loads_and_neither_file_is_none():
    z = MedianZone.load(_project(with_island_file=False))
    assert z is not None and z.n_island == 0 and z.has_barrier
    assert z.contains(0.0, 150.0, ALL_KINDS) and not z.contains(0.0, 75.0, ALL_KINDS)
    assert MedianZone.load(_project(with_island_file=False, with_barrier_file=False)) is None


def test_reversed_maps_vertex_i_to_n_minus_1_minus_i():
    z = MedianZone.load(_project())
    r = z.reversed()
    assert r.barrier_half_at(N - 1 - 30) == 0.335 and r.barrier_half_at(30) == 0.0
    assert r.island_half_at(N - 1 - 15) == 2.0 and r.island_half_at(15) == 0.0
    assert r.edge_inset_at(N - 1 - 20) == 0.82
    assert r.contains(0.0, 150.0, ALL_KINDS) and r.contains(0.0, 75.0)   # geometry unchanged
    assert r.contains(W / 2 - 0.485, 100.0, ALL_KINDS)


def test_closed_lap_seam_band_is_vertex_0s():
    """A closed lap repeats vertex 0 as its last point and that duplicate carries the LAST street's
    width (Lake Murray: 27.5 m vs Alvarado's 17.0 m) with a one-sided tangent 6.8 deg off: the barrier
    band at the seam must be vertex 0's (the ribbon and the race author wrap there). Found 2026-10-11
    when the densified outside-lip rings of the seam corner read as 28 audit-D walls on the road."""
    import math
    n_v, rad = 40, 40.0
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "track.config.json").write_text(json.dumps({"slug": "t", "mirror_x": False}))
    pts = [[rad * math.cos(2 * math.pi * k / n_v), 0.0, rad * math.sin(2 * math.pi * k / n_v)] for k in range(n_v)]
    pts.append(list(pts[0]))
    widths = [W] * n_v + [W + 10.0]                       # the closure duplicate: another street's width
    (d / "data" / "gate_centerline.json").write_text(json.dumps({"points_xyz_m": pts, "widths_m": widths}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps({
        "centre_w_by_vertex": [0.0] * (n_v + 1), "edge_strip_by_vertex": [1] * (n_v + 1),
        "edge_inset_by_vertex": [0.82] * (n_v + 1), "params": {"barrier_half_m": 0.335, "edge_centre_from_lip_m": -0.485}}))
    z = MedianZone.load(d)
    assert z.closed and z.n_edge == n_v + 1
    nx, nz = z._normal(0)
    assert abs(nx + 1.0) < 1e-9 and abs(nz) < 1e-9 and z._normal(n_v) == z._normal(0)   # wrapped: inward at angle 0
    left = rad - (W / 2 - 0.485)                          # the left (inner) band radius, 35.485 m
    assert z.contains(left, 0.0, ALL_KINDS)               # vertex 0's own band point
    a = math.radians(-4.5)                                # half-way back to vertex 39, on the declared curve
    r_mid = rad * math.cos(math.radians(4.5)) - (W / 2 - 0.485)
    assert z.contains(r_mid * math.cos(a), r_mid * math.sin(a), ALL_KINDS)
    wrong = rad - ((W + 10.0) / 2 - 0.485)                # where the duplicate's width would put it
    assert not z.contains(wrong, 0.0, ALL_KINDS)
    # an OPEN polyline keeps its one-sided end tangents
    assert not MedianZone.load(_project()).closed


def test_road_islands_zone_the_mainline_medians_for_a_lap_layout_only():
    """ledger 0054 step 2e: a layout on a LAP is zoned on its lap, but its gate OBJ carries the whole road kn5 —
    road_islands() gives the mainline's own medians (island kind) for it, and None for every other layout"""
    d = _project()
    cfg = {"slug": "t", "mirror_x": False,
           "layouts": [{"id": "street", "kind": "street"},
                       {"id": "race_cw", "kind": "race", "race_furniture": True},
                       {"id": "north_cw", "kind": "race", "race_furniture": True, "lap": "north"}]}
    (d / "track.config.json").write_text(json.dumps(cfg))
    z = MedianZone.road_islands(d, "north_cw")
    assert z is not None and z.n_island == 11 and not z.has_barrier
    assert z.contains(0.0, 75.0)                          # v15: the mainline island
    assert not z.contains(0.0, 150.0, ALL_KINDS)          # the mainline's race bands are not the lap's
    for lid in (None, "street", "race_cw"):
        assert MedianZone.road_islands(d, lid) is None


def test_a_trimmed_corner_band_runs_through_its_corner_not_the_folded_offsets():
    """2026-10-11: barrier_bands.json `edge_corners` — on that side the removed vertices have NO band point and
    the band is the polyline in_vertex band point -> X -> out_vertex band point (what the author sweeps), so
    audit D exempts the corner strip and nothing at the folded offsets; reversed() moves the corner to the
    other side of travel with its vertices walked backwards"""
    d = _project(island=(0, -1), centre=(0, -1), mouth=False)
    bj = json.loads((d / "data" / "barrier_bands.json").read_text())
    # straight road along +z: right of travel is +x here (left normal (-tz, tx) = (-1, 0)); the R band at x = +4.515
    X = [6.0, 100.0]                                       # an (artificial) corner 1.5 m outboard at v20
    bj["edge_corners"] = [{"side": "R", "in_vertex": 18, "out_vertex": 22, "removed": [19, 20, 21], "xz": X}]
    (d / "data" / "barrier_bands.json").write_text(json.dumps(bj))
    z = MedianZone.load(d)
    off = W / 2 - 0.485
    assert z._band_point("edge_R", 20) is None and z._band_point("edge_L", 20) is not None
    assert z.contains(6.0, 100.0, ALL_KINDS)               # AT X
    assert z.contains(5.25, 95.0, ALL_KINDS)               # on the leg in_vertex (x 4.515, z 90) -> X
    assert not z.contains(off, 100.0, ALL_KINDS)            # the removed vertex's own (folded) band point
    assert z.contains(-off, 100.0, ALL_KINDS)               # the other side is untouched
    spans = z.edge_corner_spans("edge_R")
    assert len(spans) == 1 and spans[0][:2] == (18, 22) and spans[0][2][1] == (6.0, 100.0)
    assert z.edge_corner_spans("edge_L") == []
    r = z.reversed()
    rs = r.edge_corner_spans("edge_L")                      # walked backwards the corner is on the LEFT
    assert len(rs) == 1 and rs[0][:2] == (N - 1 - 22, N - 1 - 18) and rs[0][2][1] == (6.0, 100.0)
    assert r._band_point("edge_L", N - 1 - 20) is None and r.contains(6.0, 100.0, ALL_KINDS)
    assert math.dist(rs[0][2][0], (off, 110.0)) < 1e-9 and math.dist(rs[0][2][2], (off, 90.0)) < 1e-9


# --- per-layout corridors (ledger 0049) ---------------------------------------------------------------------

def _corridor_project(*, other_layout=True) -> Path:
    """the straight road with a v2 declaration: race_cw closes 1 m LEFT of the centreline (left = -x here),
    race_acw 1 m right of it; both curb strips everywhere, no chain"""
    d = _project(island=(0, -1), centre=(0, -1), mouth=False)
    bj = json.loads((d / "data" / "barrier_bands.json").read_text())
    face = W / 2 - 0.82

    def cor(sgn):
        y = [sgn * 1.0 if 10 <= i <= 30 else None for i in range(N)]
        lane = [([-face, sgn - 0.335] if sgn > 0 else [sgn + 0.335, face]) if y[i] is not None else [-face, face]
                for i in range(N)]
        zone = ["closure" if y[i] is not None else "whole" for i in range(N)]
        return {"token": "cw" if sgn > 0 else "acw", "closure_y_by_vertex": y, "lane_by_vertex": lane,
                "zone_by_vertex": zone}
    bj["version"] = 2
    bj["corridors"] = {"race_cw": cor(1.0)}
    if other_layout:
        bj["corridors"]["race_acw"] = cor(-1.0)
    (d / "data" / "barrier_bands.json").write_text(json.dumps(bj))
    return d


def test_a_layout_zone_carries_its_own_closure_band_and_lane():
    d = _corridor_project()
    plain = MedianZone.load(d)
    assert not plain.has_corridor and plain.n_closure == 0 and plain.closure_at(20) is None
    assert not plain.contains(-1.0, 100.0, ALL_KINDS)          # no layout: no closure band at all
    cw = MedianZone.load(d, layout="race_cw")
    assert cw.has_corridor and cw.n_closure == 21 and cw.zone_at(20) == "closure" and cw.zone_at(5) == "whole"
    assert cw.closure_at(20) == 1.0
    # forward travel +z: left normal (-1, 0) -> the cw closure stands at x = -1.0
    assert cw.contains(-1.0, 100.0, ALL_KINDS) and cw.contains(-1.0 - 0.9, 100.0, ALL_KINDS)
    assert not cw.contains(-1.0 + 1.0, 100.0, ALL_KINDS)
    assert not cw.contains(1.0, 100.0, ALL_KINDS)              # race_acw's closure is not race_cw's band
    assert not cw.contains(-1.0, 100.0)                        # default kinds: island only
    lo, hi = cw.lane_r(20)                                     # right of travel: the closure face .. the right strip face
    assert abs(lo - (-(1.0 - 0.335))) < 1e-9 and abs(hi - (W / 2 - 0.82)) < 1e-9
    assert cw.lane_r(5) == (-(W / 2 - 0.82), W / 2 - 0.82)
    acw = MedianZone.load(d, layout="race_acw")
    assert acw.contains(1.0, 100.0, ALL_KINDS) and not acw.contains(-1.0, 100.0, ALL_KINDS)


def test_a_reversed_layout_zone_flips_the_lane_into_its_own_right():
    d = _corridor_project()
    acw = MedianZone.load(d, layout="race_acw").reversed()
    k = N - 1 - 20                                             # forward vertex 20 walked backwards
    assert acw.closure_at(k) == 1.0                            # forward y -1.0 is LEFT of the reversed travel
    lo, hi = acw.lane_r(k)                                     # right of reverse travel = forward-left = +y fwd
    assert abs(lo - (-1.0 + 0.335)) < 1e-9 and abs(hi - (W / 2 - 0.82)) < 1e-9
    assert acw.contains(1.0, 100.0, ALL_KINDS)                 # same world band
    assert acw.zone_at(k) == "closure"


def test_a_v2_file_without_the_asked_layout_is_an_error_and_v1_files_ignore_layouts():
    d = _corridor_project(other_layout=False)
    try:
        MedianZone.load(d, layout="race_acw")
    except SystemExit as e:
        assert "race_acw" in str(e)
    else:
        raise AssertionError("a race layout was zoned without its declared corridor")
    v1 = _project()
    z = MedianZone.load(v1, layout="race_cw")                  # a v1 file: today's bands, no corridor
    assert z is not None and not z.has_corridor and z.n_barrier == 11
