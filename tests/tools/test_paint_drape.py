"""Ledger 0093 round 2: tools/paint_shapes.drape (the drape tools/author_paint_blend.py paint() runs on the built surface)
and its opt-in "clip_to_surface", which High Plains' pit-out gore needs (its traced tip lies past the paddock sheet: the
PC's first 0.1.8 rehearsal stopped on "[paint] FATAL: pit_out_gore line 0: no PADAPRON under (435.20, -9.11)").

Pure: no bpy. The surface is a stand-in: a flat sheet over a polygon.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import paint_shapes as ps  # noqa: E402


def _old_drape(lines, top, ds, lift):
    """the loop author_paint_blend.paint() ran before round 2, verbatim but for bpy: the reference for 'unchanged'"""
    verts, faces, made = [], [], []
    for li, line in enumerate(lines):
        pts = [(float(p[0]), float(p[1])) for p in line["pts"]]
        P = ps.resample(pts, ds)
        for lo, hi in ps.stripes(line):
            base = len(verts)
            for k, (x, z) in enumerate(P):
                a, b = P[max(0, k - 1)], P[min(len(P) - 1, k + 1)]
                tx, tz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(tx, tz) or 1e-9
                nx, nz = -tz / L, tx / L
                for o in (lo, hi):
                    px, pz = x + nx * o, z + nz * o
                    y = top(px, pz)
                    if y is None:
                        raise LookupError((li, round(px, 2), round(pz, 2)))
                    verts.append((px, pz, y + lift))
            for k in range(len(P) - 1):
                i0 = base + 2 * k
                faces.append((i0, i0 + 1, i0 + 3, i0 + 2))
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        made.append((line.get("color", "yellow"), L, len(ps.stripes(line))))
    return verts, faces, made


def _sheet(poly, y=1.25):
    def inside(x, z):
        c, j = False, len(poly) - 1
        for i in range(len(poly)):
            (xi, zi), (xj, zj) = poly[i], poly[j]
            if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
                c = not c
            j = i
        return c
    return lambda x, z: (y + 0.01 * x) if inside(x, z) else None


LINES = [{"pts": [(0, 0), (7.3, 1.0), (9.0, 6.0)], "w": 0.4, "color": "yellow"},
         {"pts": [(1, 2), (5, 2)], "w": 0.12, "double_gap_m": 0.06, "color": "yellow"}]
BIG = [(-50, -50), (50, -50), (50, 50), (-50, 50)]


def test_unclipped_is_the_old_loop_vertex_for_vertex():
    top = _sheet(BIG)
    v0, f0, m0 = _old_drape(LINES, top, 0.5, 0.015)
    v1, f1, m1, clipped = ps.drape(LINES, top, 0.5, 0.015)
    assert v1 == v0 and f1 == f0 and m1 == m0 and clipped == 0.0
    v2, f2, m2, c2 = ps.drape(LINES, top, 0.5, 0.015, clip=True)     # all on the surface: clip draws the same faces
    assert len(f2) == len(f0) and c2 == 0.0
    assert [round(m[1], 9) for m in m2] == [round(m[1], 9) for m in m0]


def test_unclipped_stops_on_the_first_point_with_no_surface():
    half = _sheet([(-50, -50), (4, -50), (4, 50), (-50, 50)])
    with pytest.raises(LookupError) as old:
        _old_drape(LINES, half, 0.5, 0.015)
    with pytest.raises(ps.NoSurface) as new:
        ps.drape(LINES, half, 0.5, 0.015)
    assert (new.value.li, round(new.value.x, 2), round(new.value.z, 2)) == old.value.args[0]
    with pytest.raises(ps.ShortLine):
        ps.drape([{"pts": [(0, 0)]}], half, 0.5, 0.015)


def test_clip_draws_only_over_the_surface_and_counts_the_rest():
    half = _sheet([(-50, -50), (4, -50), (4, 50), (-50, 50)])
    verts, faces, made, clipped = ps.drape(LINES, half, 0.5, 0.015, clip=True)
    total = sum(m[1] for m in made) + clipped
    declared = sum(sum(math.dist(a, b) for a, b in zip(ln["pts"], ln["pts"][1:])) for ln in LINES)
    assert abs(total - declared) < 1e-9 and 0 < clipped < declared
    assert all(half(x, z) is not None and abs(y - half(x, z) - 0.015) < 1e-12 for x, z, y in verts)
    used = {i for f in faces for i in f}
    assert used == set(range(len(verts)))                               # no lone vertex
    assert all(len(set(f)) == 4 for f in faces)
    nothing = ps.drape(LINES, _sheet([(100, 100), (101, 100), (101, 101)]), 0.5, 0.015, clip=True)
    assert nothing[1] == [] and abs(nothing[3] - declared) < 1e-9       # paint() stops the step on this


def _hp():
    t = ROOT / "tracks" / "high-plains-lm"
    cfg = json.loads((t / "track.config.json").read_text(encoding="utf-8"))
    local = json.loads((t / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    quad = [ps.to_xz(local["origin"], q) for q in cfg["scenery"]["bespoke"]["pads"][0]["quad_lonlat"]]
    return cfg, local, quad


def test_high_plains_pit_out_gore_reproduces_the_pc_stop_and_clips_past_the_paddock_sheet():
    """measured 2026-11-20 (Mac, this config): the paddock sheet is pad 0's quad; the gore's last outline corner lies 4.2 m
    outside it. Unclipped, the drape stops where the PC's rehearsal did; clipped, it paints 129.8 of the gore's 144.3 m of
    line and leaves out 14.5 m at its tip: hatch stripes 0 and 1 (1.2, 2.5 m), 1.0 m of stripe 2 and 9.7 m of the outline. 2026-11-23: 0.1.12's
    install synced back the line the build drives (the measured edge re-fit, median 0.53 m off the Nov 3 intake line airoso
    held): on it the drape stops at (435.15, -9.10) and paints 129.74 m, leaving 14.52 m"""
    cfg, local, quad = _hp()
    item = next(i for i in cfg["route"]["paint"] if i["id"] == "pit_out_gore")
    assert item["surface"] == ["PADAPRON"] and item["clip_to_surface"] is True
    lines = ps.expand(item, local["origin"], local["points_xyz_m"])
    sheet = _sheet(quad, 0.0)
    with pytest.raises(ps.NoSurface) as e:
        ps.drape(lines, sheet, 0.5, 0.015)
    assert (e.value.li, f"{e.value.x:.2f}", f"{e.value.z:.2f}") == (0, "435.15", "-9.10")
    verts, faces, made, clipped = ps.drape(lines, sheet, 0.5, 0.015, clip=True)
    drawn = sum(m[1] for m in made)
    assert faces and abs(clipped - 14.52) < 0.05 and abs(drawn - 129.74) < 0.05, (clipped, drawn)


def test_only_the_pit_out_gore_clips():
    seen = []
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        for it in (cfg.get("route") or {}).get("paint") or []:
            if it.get("clip_to_surface"):
                seen.append((cfgp.parent.name, it["id"]))
    assert seen == [("high-plains-lm", "pit_out_gore")]
