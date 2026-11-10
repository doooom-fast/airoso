"""scripts-v021 geometry/ribbon.curb_sidewalk's opt-in apron (ledger 0085, Pikes Peak) and the assembler's
edge_apron reader. Without an apron the strip is exactly the one before the change (the pre-change function, kept
here verbatim as the reference); with one, only the declared side's points 2 and 3 move, to the measured apron's
width and fall and the measured lip, and the strip keeps four points a row (tools/mouth_weld.curb_index). Loaded
by path: the module is pure Python."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location(
    "_v021_ribbon_apron", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "ribbon.py")
rb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(rb)


def _reference(centerline_m, widths_m, *, lift=0.1, curb_h=0.15, curb_face_w=0.08, sidewalk_w=1.5,
               grade_w=1.0, grass_clearance=0.25, tile_m=2.0, bank_at=None):
    """ribbon.curb_sidewalk as it stood before the apron (34521fa), verbatim but for the name."""
    pts = centerline_m
    n = len(pts)
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
    m = n - 1 if closed else n
    profile = [(0.0, lift), (curb_face_w, lift + curb_h),
               (curb_face_w + sidewalk_w, lift + curb_h),
               (curb_face_w + sidewalk_w + grade_w, -grass_clearance)]
    total_w = profile[-1][0] or 1e-9
    P = len(profile)
    verts, uvs, tris = [], [], []
    for side in (1.0, -1.0):
        rows = []
        arc = 0.0
        for i in range(m):
            if i > 0:
                arc += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
            x, y, z = pts[i]
            tx, tz = rb._horiz_tangent(pts, i, closed)
            nx, nz = -tz * side, tx * side
            half = widths_m[i] / 2.0
            edge_bank = side * half * (math.tan(bank_at(arc)) if bank_at else 0.0)
            r = len(verts)
            for off, h in profile:
                o = half + off
                verts.append((x + nx * o, y + edge_bank + h, z + nz * o))
                uvs.append((off / total_w, arc / tile_m))
            rows.append(r)
        last = m if closed else m - 1
        for k in range(last):
            a = rows[k]
            b = rows[(k + 1) % m]
            for p in range(P - 1):
                tris.append((a + p, a + p + 1, b + p + 1))
                tris.append((a + p, b + p + 1, b + p))
    return {"vertices": verts, "uvs": uvs, "tris": tris}


def _ring(n=40, r=60.0):
    pts = [(r * math.cos(2 * math.pi * k / n), 1.0 + 0.1 * math.sin(3 * k / n), r * math.sin(2 * math.pi * k / n))
           for k in range(n)]
    return pts + [pts[0]]


def test_no_apron_is_the_strip_before_the_change():
    pts = _ring()
    w = [15.0 + 0.1 * (k % 7) for k in range(len(pts))]
    w[-1] = w[0]
    for kw in ({}, {"curb_h": 0.0, "curb_face_w": 0.1, "sidewalk_w": 0.2, "grade_w": 1.0, "grass_clearance": 0.05},
               {"bank_at": lambda a: -0.17}):
        assert rb.curb_sidewalk(pts, w, **kw) == _reference(pts, w, **kw)
        assert rb.curb_sidewalk(pts, w, apron=None, **kw) == _reference(pts, w, **kw)


def test_the_apron_side_takes_the_measured_width_fall_and_lip():
    pts = _ring()
    n = len(pts) - 1
    w = [19.0] * len(pts)
    bank = -0.17
    kw = {"curb_h": 0.0, "curb_face_w": 0.1, "sidewalk_w": 0.2, "grade_w": 1.0, "grass_clearance": 0.05,
          "bank_at": lambda a: bank}
    ap = {"side": 1.0, "w": [6.0] * n, "slope": [-0.066] * n, "lip": [0.02] * n}
    got = rb.curb_sidewalk(pts, w, apron=ap, **kw)
    ref = _reference(pts, w, **kw)
    assert len(got["vertices"]) == len(ref["vertices"]) == 2 * n * 4        # four points a row, both sides
    assert got["tris"] == ref["tris"]
    for i in range(n):
        lv = got["vertices"][4 * i:4 * i + 4]                                # side +1 (left) block first
        x, y, z = pts[i]
        edge_y = y + 1.0 * (w[i] / 2) * math.tan(bank)                       # the unlifted banked left edge
        assert abs(lv[0][1] - (edge_y + 0.1)) < 1e-9                          # lane edge, lifted as the deck
        assert abs(lv[2][1] - (edge_y + 0.1 - 0.066 * 6.0)) < 1e-9            # apron back: 6 m at -6.6 %
        assert abs(lv[3][1] - (edge_y - 0.066 * 6.0 + 0.02)) < 1e-9           # lip on the measured ground
        d2 = math.hypot(lv[2][0] - x, lv[2][2] - z)
        assert abs(d2 - (w[i] / 2 + 0.1 + 6.0)) < 1e-6                       # the apron's back stands 6.1 m out
    assert got["vertices"][4 * n:] == ref["vertices"][4 * n:]                # the other side untouched


def test_the_apron_without_a_lip_grades_to_the_clearance():
    pts = _ring()
    n = len(pts) - 1
    w = [19.0] * len(pts)
    ap = {"side": -1.0, "w": [5.0] * n, "slope": [-0.05] * n}
    got = rb.curb_sidewalk(pts, w, apron=ap, curb_h=0.0, grass_clearance=0.05)
    rv = got["vertices"][4 * n:]
    for i in range(n):
        y = pts[i][1]
        assert abs(rv[4 * i + 3][1] - (y - 0.05 * 5.0 - 0.05)) < 1e-9


def test_a_rounded_knee_meets_the_sharp_one_past_its_transition():
    """round_m (ledger 0085): point 1 ends a round_m transition at the mean of the bank's fall and the apron's; from it on
    the apron is the sharp knee's own surface (the knee sat round_m / 2 further out), its back at the same width"""
    pts = _ring()
    n = len(pts) - 1
    w = [19.0] * len(pts)
    bank, sa, rm, wa = -0.17, -0.04, 2.0, 7.0
    kw = {"curb_h": 0.0, "curb_face_w": 0.1, "grade_w": 1.0, "grass_clearance": 0.05, "bank_at": lambda a: math.atan(bank)}
    got = rb.curb_sidewalk(pts, w, apron={"side": 1.0, "w": [wa - 0.1] * n, "slope": [sa] * n, "lip": [0.0] * n,
                                          "round_m": rm}, **kw)
    for i in range(n):
        lv = got["vertices"][4 * i:4 * i + 4]
        edge_y = pts[i][1] + (w[i] / 2) * bank
        m = 0.5 * (bank + sa)
        assert abs(lv[1][1] - (edge_y + 0.1 + m * rm)) < 1e-9
        sharp_back = edge_y + 0.1 + bank * (rm / 2) + sa * (wa - rm / 2)          # knee at rm / 2, then the apron
        assert abs(lv[2][1] - sharp_back) < 1e-9
        assert abs(math.hypot(lv[2][0] - pts[i][0], lv[2][2] - pts[i][2]) - (w[i] / 2 + wa)) < 1e-6
