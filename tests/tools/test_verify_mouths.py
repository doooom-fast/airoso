"""tools/verify_mouths.py — the side-street mouth gate, on a synthetic BUILT road (2026-10-11).

One mouth: a straight host 20 m wide on a -5 % grade (curb + sidewalk both sides, gapped across the mouth by
mouth_weld.gap_window), a 16 m connector meeting it at 76 deg from the left, a grass sheet well under it all. Built
as the assembler builds it (end row LEVEL and SQUARE at the cut) the gate fails exactly where the Del Cerro W mouth
did — the mouth line off the deck, the connector's corner over the host lane, the notch; welded by
tools/mouth_weld.weld_end it passes. Then one defect at a time on the welded road: a mouths.json side that disagrees
with the approach, a step in the approach, grass through the host lane, grass through the approach, the host's
sidewalk left standing across the mouth.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mouth_weld as mw  # noqa: E402
import verify_mouths as vm  # noqa: E402

GRADE = -0.05
HALF_H, HALF_C, ANG = 10.0, 8.0, 76.0
CURB_C = ((0.0, 0.0), (0.08, 0.14), (1.58, 0.14), (2.78, -0.20))
CURB_H = ((0.0, 0.0), (0.08, 0.14), (1.88, 0.14), (3.08, -0.20))
HX = [-60.0 + 3.0 * i for i in range(41)]


def hy(x):
    return 10.0 + GRADE * x


def host_rows():
    return [((x, hy(x), HALF_H), (x, hy(x), 0.0), (x, hy(x), -HALF_H)) for x in HX]


def conn_lines(step_at=None):
    a = math.radians(ANG)
    d = (math.cos(a), math.sin(a))
    n = (-d[1], d[0])
    cut = (0.0, HALF_H - mw.OVERLAP_M)
    lines = {("road", k): [] for k in range(3)}
    for s in (1, -1):
        for p in range(4):
            lines[("curb", s, p)] = []
    centre = []
    for j in range(24):
        u = 3.0 * j
        cx, cz = cut[0] + d[0] * u, cut[1] + d[1] * u
        y = hy(0.0) + 0.04 * max(0.0, u - 30.0) + (0.3 if step_at is not None and u >= step_at else 0.0)
        centre.append((cx, y, cz))
        for lane, o in ((0, HALF_C), (1, 0.0), (2, -HALF_C)):
            lines[("road", lane)].append((cx + n[0] * o, y, cz + n[1] * o))
        for s in (1, -1):
            for p, (off, h) in enumerate(CURB_C):
                o = s * (HALF_C + off)
                lines[("curb", s, p)].append((cx + n[0] * o, y + h, cz + n[1] * o))
    return lines, centre


def weld(lines):
    rows = host_rows()
    deck = mw.HostDeck(rows, mw.host_window(rows, False, 0.0, HALF_H))
    inset = {k: (mw.OVERLAP_M if k[0] == "road" else mw.CURB_INSET_M) for k in lines}
    h = {k: (0.0 if k[0] == "road" else CURB_C[k[2]][1]) for k in lines}
    return mw.weld_end(lines, deck, 1, inset, h)["new"]


class Obj:
    def __init__(self):
        self.groups = {}

    def quad(self, g, a, b, c, d):
        self.groups.setdefault(g, []).extend([(a, b, c), (a, c, d)])

    def write(self, path):
        lines, k = [], 0
        for g, tris in self.groups.items():
            lines.append(f"o {g}")
            for t in tris:
                for v in t:
                    lines.append("v %.4f %.4f %.4f" % v)
                lines.append(f"f {k + 1} {k + 2} {k + 3}")
                k += 3
        Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")


def build(tmp, lines, centre, side=1, gap=True, extra=None, extra_gap=(), skip_curb=None):
    proj = Path(tmp)
    (proj / "data").mkdir(parents=True, exist_ok=True)
    o = Obj()
    hr = host_rows()
    for j in range(len(hr) - 1):
        for a, b in ((0, 1), (1, 2)):
            o.quad("1ROAD_road", hr[j][a], hr[j][b], hr[j + 1][b], hr[j + 1][a])
    hpts = [r[1] for r in hr]
    cut_station = 0.0
    seg = next(i for i in range(len(HX) - 1) if HX[i] <= cut_station <= HX[i + 1])
    window = mw.gap_window(hpts, len(hpts), False, seg, (cut_station - HX[seg]) / 3.0, 2 * HALF_C, ANG) if gap else set()
    window = set(window) | set(extra_gap)
    for s in (1, -1):
        for j in range(len(hr) - 1):
            if s == 1 and j in window and j + 1 in window:
                continue
            for p in range(3):
                def pt(jj, pp):
                    x = HX[jj]
                    off, h = CURB_H[pp]
                    return (x, hy(x) + h, s * (HALF_H + off))
                o.quad("1KERB_sidewalk", pt(j, p), pt(j, p + 1), pt(j + 1, p + 1), pt(j + 1, p))
    rows = [tuple(lines[("road", k)][j] for k in range(3)) for j in range(len(lines[("road", 0)]))]
    for j in range(len(rows) - 1):
        for a, b in ((0, 1), (1, 2)):
            o.quad("1ROAD_road", rows[j][a], rows[j][b], rows[j + 1][b], rows[j + 1][a])
    for s in (1, -1):
        for p in range(3):
            A, B = lines[("curb", s, p)], lines[("curb", s, p + 1)]
            for j in range(len(A) - 1):
                if skip_curb is not None and s == skip_curb[0] and j + 1 <= skip_curb[1]:
                    continue
                o.quad("1KERB_sidewalk", A[j], B[j], B[j + 1], A[j + 1])
    for x in range(-80, 80, 10):
        for z in range(-60, 100, 10):
            o.quad("1GRASS_0", (x, hy(x) - 1.5, z), (x + 10, hy(x + 10) - 1.5, z), (x + 10, hy(x + 10) - 1.5, z + 10),
                   (x, hy(x) - 1.5, z + 10))
    for tri in (extra or []):
        o.groups.setdefault(tri[0], []).append(tri[1])
    o.write(proj / "data" / "track.obj")
    (proj / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in hpts],
                                                                      "widths_m": [2 * HALF_H] * len(hpts)}))
    (proj / "data" / "connectors.local.json").write_text(json.dumps({"connectors": [
        {"name": "c#0", "points_xyz_m": [list(p) for p in centre], "widths_m": [2 * HALF_C] * len(centre)}]}))
    (proj / "data" / "mouths.json").write_text(json.dumps({"mouths": [{
        "connector": "c", "host": "MAINLINE", "host_vertex": seg, "side": side, "connector_width_m": 2 * HALF_C,
        "cut_xyz": list(centre[0]), "host_seg": seg, "host_t": 0.0, "angle_deg": ANG, "host_grade": GRADE,
        "piece": "c#0", "end": "start"}]}))
    return proj


def _run(proj):
    r = vm.verify(proj)
    return r, r["mouths"][0]


def _fails(m, key):
    return [f for f in m["fails"] if f.startswith(key)]


def test_the_assembler_s_square_level_end_fails_where_del_cerro_did():
    lines, centre = conn_lines()
    with tempfile.TemporaryDirectory() as tmp:
        r, m = _run(build(tmp, lines, centre))
    assert r["fail"]
    assert _fails(m, "MOUTH LINE") and m["mouth_line"]["max_dev_m"] > 0.3
    assert _fails(m, "HOST LANE") and m["host_lane"]["max_above_m"] > 0.3
    assert _fails(m, "NOTCH")


def test_the_welded_mouth_passes():
    lines, centre = conn_lines()
    with tempfile.TemporaryDirectory() as tmp:
        r, m = _run(build(tmp, weld(lines), centre))
    assert not r["fail"], m["fails"]
    assert m["mouth_line"]["max_dev_m"] <= 0.01 and m["host_lane"]["max_above_m"] == 0.0
    assert m["notch"]["samples"] > 20 and m["approach"]["max_dg_per_m"] < vm.APPROACH_DG_PER_M
    assert abs(m["angle_deg"] - ANG) < 1.0


def test_a_side_that_disagrees_with_the_approach_fails():
    lines, centre = conn_lines()
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(build(tmp, weld(lines), centre, side=-1))
    assert _fails(m, "SIDE")


def test_a_step_in_the_approach_fails():
    lines, centre = conn_lines(step_at=10.0)
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(build(tmp, weld(lines), centre))
    assert [f for f in m["fails"] if "grade" in f], m["fails"]


def test_grass_through_the_host_lane_fails():
    lines, centre = conn_lines()
    poke = ("1GRASS_1", ((-6.0, hy(-6.0) + 0.05, 5.0), (-2.0, hy(-2.0) + 0.05, 5.0), (-4.0, hy(-4.0) + 0.05, 8.0)))
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(build(tmp, weld(lines), centre, extra=[poke]))
    assert _fails(m, "HOST LANE") and m["host_lane"]["grass_at_or_above"] > 0


def test_grass_through_the_approach_fails():
    lines, centre = conn_lines()
    new = weld(lines)
    c = new[("road", 1)]
    p, q = c[5], c[6]
    poke = ("1GRASS_1", ((p[0] - 3, p[1] + 0.03, p[2]), (p[0] + 3, p[1] + 0.03, p[2]), (q[0], q[1] + 0.03, q[2])))
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(build(tmp, new, centre, extra=[poke]))
    assert [f for f in m["fails"] if "grass at/above the connector" in f], m["fails"]


def test_the_host_sidewalk_left_across_the_mouth_fails():
    lines, centre = conn_lines()
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(build(tmp, weld(lines), centre, gap=False))
    assert _fails(m, "NOTCH")


# --- ledger 0054 P1: route.weld_exact_deck — HOST LANE read against the host's own sheet at each sample -----------

def _exact(proj, on=True):
    (proj / "track.config.json").write_text(json.dumps({"route": {"weld_exact_deck": ["c"] if on else []}}))
    return proj


def _raise_host_mouth_half(proj, dy=0.03):
    """lift the host's own road on the mouth half (z > 0) by dy at its edge, linearly from the centre — the shape the
    level-across HD(s) misreads on a corner's fanned outer half"""
    p = proj / "data" / "track.obj"
    out = []
    for ln in p.read_text(encoding="ascii").splitlines():
        if ln.startswith("v "):
            x, y, z = (float(t) for t in ln.split()[1:4])
            if 0.0 < z <= HALF_H + 1e-9 and -60.0 <= x <= 60.0 and abs(y - hy(x)) < 1e-6:
                y += dy * z / HALF_H
            ln = f"v {x} {y} {z}"
        out.append(ln)
    p.write_text("\n".join(out) + "\n", encoding="ascii")


def test_exact_deck_reads_the_host_s_own_raised_half_as_the_deck():
    lines, centre = conn_lines()
    with tempfile.TemporaryDirectory() as tmp:
        proj = build(tmp, weld(lines), centre)
        _raise_host_mouth_half(proj)
        _r, legacy = _run(_exact(proj, on=False))
        _r, exact = _run(_exact(proj, on=True))
    assert _fails(legacy, "HOST LANE") and legacy["host_lane"]["road_kerb_above"] > 0
    assert not _fails(exact, "HOST LANE"), exact["fails"]
    assert exact.get("host_lane_deck", "").startswith("exact") and "host_lane_deck" not in legacy


def test_exact_deck_still_fails_a_sheet_over_the_host_and_grass_through_it():
    lines, centre = conn_lines()
    over = ("1ROAD_x", ((-6.0, hy(-6.0) + 0.05, 5.0), (-2.0, hy(-2.0) + 0.05, 5.0), (-4.0, hy(-4.0) + 0.05, 8.0)))
    poke = ("1GRASS_1", ((6.0, hy(6.0) + 0.002, 5.0), (10.0, hy(10.0) + 0.002, 5.0), (8.0, hy(8.0) + 0.002, 8.0)))
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(_exact(build(tmp, weld(lines), centre, extra=[over, poke])))
    assert _fails(m, "HOST LANE") and m["host_lane"]["road_kerb_above"] > 0 and m["host_lane"]["grass_at_or_above"] > 0


# --- ledger 0054 P1 fix round: a corner APRON on the mouth (data/aprons.json) -------------------------------------

import apron as ap  # noqa: E402


def _apron_scene(tmp, *, mesh=True, gap=True, lift_seam=0.0):
    """the welded mouth + a return of R 30 on the connector's east (lane 2) side, tangent at its row 8, meeting the
    host's edge east of the mouth: the apron deck (ear-clipped outline, the seams' own heights), the return curb, the
    host walk gapped to E_row, the connector's own east curb gone up to T; data/aprons.json as the author writes it"""
    lines, centre = conn_lines()
    new = weld(lines)
    host_edge = {j: (HX[j], hy(HX[j]), HALF_H) for j in range(len(HX))}
    stub_edge = list(new[("road", 2)])
    stub_centre = list(new[("road", 1)])
    a = ap.build(host_edge, list(range(len(HX))), stub_edge, stub_centre,
                 (stub_edge[8][0], stub_edge[8][2]), 30.0)
    outline = a["outline"]
    oh = list(a["outline_h"])
    if lift_seam:
        for i in range(1, a["n_stub"]):          # the stub-seam vertices (not P0, not T) lifted off the stub
            oh[i] += lift_seam
    tris = _earclip(outline)
    extra = []
    if mesh:
        for i, j, k in tris:
            extra.append(("1ROAD_apron_AP1", tuple((outline[q][0], oh[q], outline[q][1]) for q in (i, j, k))))
        arc_h = [a["height"](x, z) for x, z in a["arc"]]
        first = [new[("curb", -1, p)][a["T_row"]] for p in range(4)]
        last = [(HX[a["E_row"]], hy(HX[a["E_row"]]) + h, HALF_H + off) for off, h in CURB_H]
        st = ap.curb_stations(a["arc"], a["centre"], arc_h, first, last, e_normal=(0.0, 1.0))
        for k in range(len(st) - 1):
            for q in range(3):
                A, B, C, D = st[k][q], st[k][q + 1], st[k + 1][q + 1], st[k + 1][q]
                extra += [("1KERB_sidewalk_apAP1", (A, B, C)), ("1KERB_sidewalk_apAP1", (A, C, D))]
    gap_rows = range(a["P0_host"][0], a["E_row"] + 1) if gap else ()
    proj = build(tmp, new, centre, extra=extra, extra_gap=gap_rows, skip_curb=(-1, a["T_row"]))
    rec = {"id": "AP1", "piece": "c#0", "host": "MAINLINE", "side": 1, "E_vertex": a["E_vertex"], "R_m": a["R"],
           "host_rows_opened": [a["P0_host"][0], a["E_row"]],
           "arc_xyz": [[x, h, z] for (x, z), h in zip(a["arc"], [a["height"](x, z) for x, z in a["arc"]])],
           "outline_xz": [list(q) for q in outline],
           "seam_stub_xyz": [list(a["P0"])] + [list(stub_edge[j]) for j in range(a["P0_stub"][0] + 1, a["T_row"] + 1)]}
    (proj / "data" / "aprons.json").write_text(json.dumps({"aprons": [rec]}))
    return proj


def _earclip(outline):
    idx = list(range(len(outline)))
    area = ap.polygon_area(outline)
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = outline[i0], outline[i1], outline[i2]
            cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cr * area <= 1e-12:
                continue
            if any(ap.point_in_polygon([a, b, c], *outline[j]) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    tris.append(tuple(idx[:3]))
    return tris


def test_the_apron_mouth_passes_and_its_notch_runs_on_to_the_return():
    with tempfile.TemporaryDirectory() as tmp:
        r, m = _run(_apron_scene(tmp))
    assert not r["fail"], m["fails"]
    apr = m["apron"]
    # the stub alone spans +-(8 / sin 76 deg) = +-8.2 m of host; the notch ran on along the apron toward its return
    assert apr["notch_span_m"][1] > 8.2 + 5.0, apr
    assert apr["stub_seam"]["samples"] > 20 and apr["stub_seam"]["fail"] == 0
    assert apr["deck"]["samples"] > 20 and apr["deck"]["holes"] == 0


def test_an_apron_declared_but_not_built_fails():
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(_apron_scene(tmp, mesh=False))
    assert _fails(m, "NOTCH") and _fails(m, "APRON")


def test_the_host_walk_left_across_the_apron_fails_the_notch():
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(_apron_scene(tmp, gap=False))
    assert _fails(m, "NOTCH")


def test_an_apron_off_the_stub_s_deck_fails_its_seam():
    with tempfile.TemporaryDirectory() as tmp:
        _r, m = _run(_apron_scene(tmp, lift_seam=0.08))
    assert _fails(m, "APRON") and m["apron"]["stub_seam"]["fail"] > 0
