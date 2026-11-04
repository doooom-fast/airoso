"""Top-down plots of the HELD Mission Gorge Speedway plan (ledger 0054 Phase 2): the north loop, its five joins, the
declared boxes and whole street, the junction pads (2 m ground cells, stub pavement, the stub end line), each layout's planned closure line, the curb-strip line, and all 34 exit probes
(side streets, pad arms, abandoned mainline branches). Reads plan_north.py's out dir; Pillow only.

    .venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/plot_north.py [<plan out dir>] [<png dir>]

Writes north_overview.png and north_junctions.png (J1..J5 at 1 px = 0.15 m). Frame: engine x = E, z = N (north up).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]

BG, ROAD, LAP, JOIN = (250, 250, 247), (205, 205, 200), (40, 40, 40), (230, 120, 0)
BOX, WHOLE, CW, ACW, STRIP = (255, 214, 140), (170, 210, 255), (200, 30, 30), (30, 90, 200), (120, 120, 120)
KIND = {"side_street": (0, 140, 70), "pad_arm": (150, 0, 170), "branch": (0, 0, 0)}


def _font(sz):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def _normals(P):
    m = len(P) - 1
    out = []
    for k in range(m + 1):
        a, b = P[(k - 1) % m], P[(k + 1) % m]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        out.append((-tz / L, tx / L))           # forward-LEFT of increasing v (barrier_bands' y)
    return out


class View:
    def __init__(self, x0, z0, x1, z1, px):
        self.x0, self.z1 = x0, z1
        self.s = px / max(x1 - x0, z1 - z0)
        self.w, self.h = int((x1 - x0) * self.s) + 1, int((z1 - z0) * self.s) + 1

    def __call__(self, x, z):
        return ((x - self.x0) * self.s, (self.z1 - z) * self.s)


def draw(view, plan, lap, bands, lines, title, label_exits=False, pads=()):
    im = Image.new("RGB", (view.w, view.h + 70), BG)
    d = ImageDraw.Draw(im)
    f, fs = _font(26), _font(15)
    for name, ln in lines.items():               # every source road, faint, at its width
        pts = [view(p[0], p[2]) for p in ln["points_xyz_m"]]
        wid = max(1, int(sum(ln["widths_m"]) / len(ln["widths_m"]) * view.s))
        d.line(pts, fill=ROAD, width=wid, joint="curve")
    for pad in pads:                             # the junction pads: their 2 m ground cells and each stub's pavement
        for x, z in (pad.get("ground") or {}).get("xz") or []:
            a0, b0 = view(x - 1.0, z + 1.0), view(x + 1.0, z - 1.0)
            d.rectangle([a0, b0], fill=ROAD)
        for stb in (pad.get("stubs") or {}).values():
            poly = [view(x, z) for x, z in stb.get("pavement_xz") or []]
            if len(poly) > 2:
                d.polygon(poly, fill=ROAD)
            far = [view(x, z) for x, z in stb.get("far_xz") or []]
            if len(far) > 1:
                d.line(far, fill=(90, 90, 90), width=3)
    P = lap["points_xyz_m"]
    m = len(P) - 1
    nrm = _normals(P)
    zones = bands["corridors"]["north_cw"]["zone_by_vertex"]
    for k in range(m):                           # boxes and the whole street, as wide bands
        z = zones[k]
        if z in ("box", "whole"):
            w = lap["widths_m"][k] * view.s
            d.line([view(P[k][0], P[k][2]), view(P[k + 1][0], P[k + 1][2])], fill=BOX if z == "box" else WHOLE, width=max(2, int(w)))
    for side in (1, -1):                         # the curb-strip line both sides
        pts = []
        for k in range(m + 1):
            off = side * (lap["widths_m"][k] / 2.0 - 0.485)
            pts.append(view(P[k][0] + nrm[k][0] * off, P[k][2] + nrm[k][1] * off))
        d.line(pts, fill=STRIP, width=1)
    d.line([view(p[0], p[2]) for p in P], fill=LAP, width=2)
    k0 = 0
    for j in lap["joins"]:                       # the joins, highlighted
        ks = [k for k, s in enumerate(lap["source_by_vertex"]) if s[0] == "join" and s[1] == lap["joins"].index(j)]
        if ks:
            seg = [P[ks[0] - 1]] + [P[k] for k in ks] + [P[(ks[-1] + 1) % m]]
            d.line([view(p[0], p[2]) for p in seg], fill=JOIN, width=5)
    for lid, col in (("north_cw", CW), ("north_acw", ACW)):
        ys = bands["corridors"][lid]["closure_y_by_vertex"]
        run = []
        for k in range(m + 1):
            y = ys[k % m]
            if y is None:
                if len(run) > 1:
                    d.line(run, fill=col, width=3)
                run = []
                continue
            run.append(view(P[k][0] + nrm[k][0] * y, P[k][2] + nrm[k][1] * y))
        if len(run) > 1:
            d.line(run, fill=col, width=3)
        for w in bands["corridors"][lid].get("nose_walls") or []:     # the K-rails across the far carriageway (noses)
            d.line([view(p[0], p[2]) for p in w["polyline_xyz_m"]], fill=col, width=4)
    for mo in plan["exits"]:                     # the 34 exit probes
        if mo.get("probe_xz"):
            x, z = mo["probe_xz"]
        else:
            k = mo["lap_vertex"]
            pr = next((p for p in bands["corridors"]["north_cw"]["no_route"]["forbidden_probes"]
                       if p.get("why", "").endswith(mo["exit"])), None)
            y = pr["y"] if pr else 0.0
            x, z = P[k][0] + nrm[k][0] * y, P[k][2] + nrm[k][1] * y
        cx, cz = view(x, z)
        r = 7 if not label_exits else 9
        sealed = all(mo[l]["planned"] == "sealed" for l in ("north_cw", "north_acw"))
        d.ellipse([cx - r, cz - r, cx + r, cz + r], fill=KIND[mo["kind"]] if sealed else (255, 0, 0), outline=(255, 255, 255))
        if label_exits and 0 <= cx < view.w and 0 <= cz < view.h:
            d.text((cx + 10, cz - 8), mo["exit"][:38], fill=KIND[mo["kind"]], font=fs)
    d.rectangle([0, view.h, view.w, view.h + 70], fill=(255, 255, 255))
    d.text((12, view.h + 6), title, fill=(0, 0, 0), font=f)
    legend = [("lap", LAP), ("join", JOIN), ("box", BOX), ("whole", WHOLE), ("closure cw", CW), ("closure acw", ACW),
              ("side street", KIND["side_street"]), ("pad arm", KIND["pad_arm"]), ("branch", KIND["branch"])]
    x = 12
    for name, col in legend:
        d.rectangle([x, view.h + 44, x + 18, view.h + 60], fill=col)
        d.text((x + 24, view.h + 42), name, fill=(0, 0, 0), font=fs)
        x += 30 + int(d.textlength(name, font=fs)) + 14
    return im


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]) if argv else ROOT / "build" / "phase2" / "north-plan"
    png = Path(argv[1]) if len(argv) > 1 else HERE
    plan = json.loads((out / "plan_north.json").read_text(encoding="utf-8"))
    lap = json.loads((out / "data" / "lap.north.json").read_text(encoding="utf-8"))
    bands = json.loads((out / "data" / "barrier_bands.north.json").read_text(encoding="utf-8"))
    cl = json.loads((out / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    conns = json.loads((out / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    lines = {"MAINLINE": cl, **{c["name"]: c for c in conns}}
    pads = json.loads((out / "data" / "pads.plan.json").read_text(encoding="utf-8")).get("pads") or []
    P = lap["points_xyz_m"]
    xs, zs = [p[0] for p in P], [p[2] for p in P]
    pad = 150
    v = View(min(xs) - pad, min(zs) - pad, max(xs) + pad, max(zs) + pad, 2400)
    st = plan["status"]
    t = (f"Mission Gorge Speedway (HELD, planned only) - {plan['lap_m']} m, {plan['unique_vertices']} vertices; exits "
         f"{plan['exit_counts']}; planned no_route cw/acw "
         f"{'PASS' if not any(plan['planned_no_route'][l].get('fail') for l in plan['planned_no_route']) else 'FAIL'}; plan {st}")
    draw(v, plan, lap, bands, lines, t, pads=pads).save(png / "north_overview.png", optimize=True)
    corners = {c["apex"]: c for c in bands["corners"]}
    names = {320: "J2 Waring / Princess View", 707: "J3 Princess View / Mission Gorge", 1458: "J4 Mission Gorge / Jackson",
             2130: "J5 Jackson / Navajo", 2932: "J1 Navajo / College / Waring"}
    tiles = []
    for apex in (2932, 320, 707, 1458, 2130):
        c = P[apex]
        half = 110.0
        vv = View(c[0] - half, c[2] - half, c[0] + half, c[2] + half, 900)
        tiles.append(draw(vv, plan, lap, bands, lines, f"{names[apex]} (apex v{apex}, R {corners[apex]['R_apex_m']} m)", label_exits=True, pads=pads))
    W_, H_ = tiles[0].size
    sheet = Image.new("RGB", (W_ * 3, H_ * 2), BG)
    for i, t_ in enumerate(tiles):
        sheet.paste(t_, ((i % 3) * W_, (i // 3) * H_))
    sheet.save(png / "north_junctions.png", optimize=True)
    print("wrote", png / "north_overview.png", png / "north_junctions.png")


if __name__ == "__main__":
    main()
