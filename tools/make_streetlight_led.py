"""Generate the modern LED street light (ledger 0056) — a deterministic, self-made (CC0) model.

Kevin, 2026-10-14: "make lighter lamp model" / "more modern", then "Taller too". The 2026-10 lamp (Kevin's
decimated Street_Lamp, assets/models/lamp_post.obj + lamp_lens.obj) costs ~4,045 kn5 render points per lamp and
is 57 % of the road kn5's vertices (ledger 0054/0056). This builds the contemporary San Diego arterial light in
its place: a galvanised tapered round steel pole with an upswept mast arm carrying a flat-bottomed LED cobra-head
luminaire (twist-lock photocell on top) and a flat LED lens — at about a tenth of the render points.

DIMENSIONS (every number sourced or recorded in fleet/GATES-CHANGELOG.md, 2026-10-14 lamp entry):
  pole height      10.67 m (35'-0")  Caltrans Standard Plan ES-6A, Type 21 lighting standard (the 35 ft pole;
                                      Type 15 is the 30 ft one) — the steel standard City of San Diego SDE-101
                                      allows for its major streets ("Type 15 shall be steel ... arm 12'")
  mast arm         3.66 m (12'-0")   ES-6A mast-arm length table; SDE-101's maximum arm for a steel standard
  mounting height  11.81 m (38'-9")  ES-6A Type 21 row for the 12 ft arm (Type 15 + 12 ft arm = 33'-9");
                                      i.e. the arm's 1.14 m rise over the pole top. The LENS (the light-emitting
                                      face) sits here, measured from the pole's road datum (y = 0)
  pole OD          219 mm (8-5/8") at the base, Caltrans' 0.14 in/ft taper -> 94 mm at the top
  luminaire        0.82 m x 0.33 m x 0.135 m flat-bottom LED cobra head, level (0 deg tilt), lens 0.52 x 0.23 m

FRAME: metres, +x road-ward (the arm reaches toward the road), +y up, z along the road; origin = the pole axis at
the ROAD datum (tools/author_lamps_blend.py places y = 0 at the road height the 2026-10 lamp was measured against).
The pole runs on 2.5 m below the datum (the 2026-10 lamp stood 2.46 m below it too), so a verge lower than the road
never shows the pole's foot in the air.

OUTPUT (assets/models/, all CC0, generated — rerun to reproduce byte-for-byte):
  streetlight_led_post_twin.obj    pole + TWO arms + two luminaires (back-to-back), the LIGHTPOST mesh — the
                                    double-arm configuration every 2026-10 lamp has (lamp_post.obj is symmetric)
  streetlight_led_post_single.obj  pole + one road-ward arm + luminaire (the one-key single-arm variant)
  streetlight_led_lens.obj         the flat LED lens under the ROAD-WARD luminaire, the emissive LIGHTS mesh CSP
                                    keys its [LIGHT_N] on (one lens = one light; the back luminaire is unlit, as the
                                    2026-10 lamp's back head was)
  streetlight_led.json             the spec author_lamps_blend.py / verify_race.py read (lens datum, mast radius, ...)

Normals: faces carry OBJ smoothing groups — `s 1..n` smooth (pole, arm, photocell walls, the cobra-head shell),
`s off` flat (caps, the luminaire's bottom, the lens); author_lamps_blend marks every edge between two groups (or
beside a flat face) sharp, so curved parts shade round and edges stay crisp. UVs: cylindrical on the tubes (seam
at u = 1), box-projected on the luminaire, 0..1 on the lens.

    PYTHONUTF8=1 python tools/make_streetlight_led.py            # writes the four files
    PYTHONUTF8=1 python tools/make_streetlight_led.py --check    # exit 1 if the committed files differ
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
OUT = AIROSO / "assets" / "models"
NAME = "streetlight_led"

FT = 0.3048
POLE_H = 35.0 * FT                    # 10.668 m — ES-6A Type 21
ARM_L = 12.0 * FT                     # 3.658 m — ES-6A / SDE-101 12 ft mast arm
MOUNT_H = (38.0 + 9.0 / 12.0) * FT    # 11.811 m — ES-6A Type 21, 12 ft arm
POLE_BURY = 2.5                       # pole runs on below the road datum (the 2026-10 lamp: 2.46 m)
R_BASE = 0.219 / 2                    # 8-5/8" OD at the base
TAPER = 0.14 * 0.0254 / FT / 2        # 0.14 in/ft on the diameter -> radius per metre
POLE_SIDES = 10
ARM_SIDES = 6
ARM_R0, ARM_R1 = 0.042, 0.030         # 3-1/2" -> 2-3/8" (the luminaire slip-fitter tenon)
# luminaire: stations along x from the arm tip (back) to the nose; widths / heights per station
LUM_X0 = ARM_L - 0.06                 # back face just behind the arm's tenon
LUM_LEN = 0.82
LUM_STATIONS = ((0.00, 0.24, 0.100), (0.08, 0.33, 0.135), (0.62, 0.33, 0.120), (0.82, 0.20, 0.070))
LIFT = 0.004                          # housing bottom 4 mm above the lens face (the lens stands proud: no z-fight)
LENS_X = (LUM_X0 + 0.18, LUM_X0 + 0.70)
LENS_HALF_W = 0.115
PC_X, PC_R, PC_H, PC_SIDES = LUM_X0 + 0.24, 0.035, 0.050, 6   # twist-lock photocell on the housing top
LENS_CENTRE = ((LENS_X[0] + LENS_X[1]) / 2, MOUNT_H, 0.0)


class Part:
    """vertices + faces (vertex indices, per-corner uv, smoothing group, an interior point for winding)"""

    def __init__(self):
        self.v: list[tuple[float, float, float]] = []
        self.f: list[tuple[tuple[int, ...], tuple[tuple[float, float], ...], int]] = []

    def add_v(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def add_f(self, idx, uv, group, inside):
        """orient so the face normal points AWAY from ``inside`` (outward CCW, the OBJ convention)"""
        idx, uv = list(idx), list(uv)
        n = _normal([self.v[i] for i in idx])
        c = [sum(self.v[i][k] for i in idx) / len(idx) for k in range(3)]
        if sum(n[k] * (c[k] - inside[k]) for k in range(3)) < 0:
            idx.reverse()
            uv.reverse()
        self.f.append((tuple(idx), tuple(uv), group))

    def add_f_dir(self, idx, uv, group, outward):
        """orient so the face normal points along ``outward``"""
        idx, uv = list(idx), list(uv)
        n = _normal([self.v[i] for i in idx])
        if sum(n[k] * outward[k] for k in range(3)) < 0:
            idx.reverse()
            uv.reverse()
        self.f.append((tuple(idx), tuple(uv), group))


def _normal(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def pole(part: Part, group: int):
    y0, y1 = -POLE_BURY, POLE_H
    r = lambda y: R_BASE - TAPER * y
    rings = []
    for y in (y0, y1):
        rings.append([part.add_v((r(y) * math.cos(2 * math.pi * k / POLE_SIDES), y,
                                  r(y) * math.sin(2 * math.pi * k / POLE_SIDES))) for k in range(POLE_SIDES)])
    for k in range(POLE_SIDES):
        k1 = (k + 1) % POLE_SIDES
        u0, u1 = k / POLE_SIDES, (k + 1) / POLE_SIDES
        part.add_f((rings[0][k], rings[0][k1], rings[1][k1], rings[1][k]),
                   ((u0, y0 / 4), (u1, y0 / 4), (u1, y1 / 4), (u0, y1 / 4)), group, (0.0, (y0 + y1) / 2, 0.0))
    top = rings[1]
    part.add_f_dir(top, tuple((0.5 + 0.5 * math.cos(2 * math.pi * k / POLE_SIDES),
                               0.5 + 0.5 * math.sin(2 * math.pi * k / POLE_SIDES)) for k in range(POLE_SIDES)),
                   0, (0.0, 1.0, 0.0))


def _arm_curve(sgn):
    """the upswept mast arm's centreline in the x-y plane: leaves the pole 0.5 m under its top, rises 1.14 m + the
    luminaire's back, and ends level (the slip-fitter tenon) inside the luminaire's back face"""
    yb = MOUNT_H + LIFT + 0.055                    # tenon height: mid-height of the luminaire's back
    pts = [(-0.02, POLE_H - 0.55), (0.45, POLE_H - 0.02), (1.30, yb - 0.38), (2.30, yb - 0.10),
           (3.05, yb - 0.01), (ARM_L + 0.10, yb)]
    return [(sgn * x, y) for x, y in pts]


def arm(part: Part, sgn: int, group: int):
    c = _arm_curve(sgn)
    n = len(c)
    seg = [0.0]
    for i in range(1, n):
        seg.append(seg[-1] + math.dist(c[i], c[i - 1]))
    rings = []
    for i, (x, y) in enumerate(c):
        a, b = c[max(0, i - 1)], c[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty)
        tx, ty = tx / L, ty / L
        nx, ny = -ty, tx                             # in-plane normal
        rr = ARM_R0 + (ARM_R1 - ARM_R0) * (seg[i] / seg[-1])
        rings.append([part.add_v((x + rr * math.cos(2 * math.pi * k / ARM_SIDES) * nx, y + rr * math.cos(2 * math.pi * k / ARM_SIDES) * ny,
                                  rr * math.sin(2 * math.pi * k / ARM_SIDES))) for k in range(ARM_SIDES)])
    for i in range(n - 1):
        mid = ((c[i][0] + c[i + 1][0]) / 2, (c[i][1] + c[i + 1][1]) / 2, 0.0)
        for k in range(ARM_SIDES):
            k1 = (k + 1) % ARM_SIDES
            u0, u1 = k / ARM_SIDES, (k + 1) / ARM_SIDES
            v0, v1 = seg[i] / 4, seg[i + 1] / 4
            part.add_f((rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k]),
                       ((u0, v0), (u1, v0), (u1, v1), (u0, v1)), group, mid)


def luminaire(part: Part, sgn: int, g_shell: int, g_wall: int, g_pc: int):
    yb = MOUNT_H + LIFT
    prof = lambda w, h: [(-w / 2, 0.0), (-w / 2, 0.35 * h), (-0.40 * w, 0.80 * h), (-0.17 * w, h),
                         (0.17 * w, h), (0.40 * w, 0.80 * h), (w / 2, 0.35 * h), (w / 2, 0.0)]
    rows = []
    for dx, w, h in LUM_STATIONS:
        x = sgn * (LUM_X0 + dx)
        rows.append([part.add_v((x, yb + py, pz)) for pz, py in prof(w, h)])
    xs = [sgn * (LUM_X0 + s[0]) for s in LUM_STATIONS]
    inside = lambda cx: (max(min(cx, max(xs) - 0.05), min(xs) + 0.05), yb + 0.05, 0.0)

    def box_uv(idx):
        nrm = _normal([part.v[i] for i in idx])
        ax = max(range(3), key=lambda k: abs(nrm[k]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        return tuple((part.v[i][a] * 2, part.v[i][b] * 2) for i in idx)

    for s in range(len(rows) - 1):
        for p in range(7):
            idx = (rows[s][p], rows[s][p + 1], rows[s + 1][p + 1], rows[s + 1][p])
            grp = g_wall if p in (0, 6) else g_shell
            cx = sum(part.v[i][0] for i in idx) / 4
            part.add_f(idx, box_uv(idx), grp, inside(cx))
        idx = (rows[s][0], rows[s][7], rows[s + 1][7], rows[s + 1][0])          # flat bottom (the lens frame)
        part.add_f_dir(idx, box_uv(idx), 0, (0.0, -1.0, 0.0))
    for r_, out in ((rows[0], -sgn), (rows[-1], sgn)):                          # back face, nose face (flat)
        part.add_f_dir(r_, box_uv(r_), 0, (float(out), 0.0, 0.0))
    # twist-lock photocell receptacle on the housing top
    top_y = yb + _height_at(PC_X - LUM_X0)
    y0, y1 = top_y - 0.012, top_y + PC_H
    cx = sgn * PC_X
    ring = [[part.add_v((cx + PC_R * math.cos(2 * math.pi * k / PC_SIDES), y, PC_R * math.sin(2 * math.pi * k / PC_SIDES)))
             for k in range(PC_SIDES)] for y in (y0, y1)]
    for k in range(PC_SIDES):
        k1 = (k + 1) % PC_SIDES
        u0, u1 = k / PC_SIDES, (k + 1) / PC_SIDES
        part.add_f((ring[0][k], ring[0][k1], ring[1][k1], ring[1][k]),
                   ((u0, 0.0), (u1, 0.0), (u1, 0.25), (u0, 0.25)), g_pc, (cx, (y0 + y1) / 2, 0.0))
    part.add_f_dir(ring[1], tuple((0.5 + 0.5 * math.cos(2 * math.pi * k / PC_SIDES), 0.5 + 0.5 * math.sin(2 * math.pi * k / PC_SIDES))
                                  for k in range(PC_SIDES)), 0, (0.0, 1.0, 0.0))


def _height_at(dx):
    """housing top height above its bottom at dx along the luminaire (linear between stations)"""
    st = LUM_STATIONS
    for (a, _, ha), (b, _, hb) in zip(st, st[1:]):
        if a <= dx <= b:
            return ha + (hb - ha) * (dx - a) / (b - a)
    return st[-1][2]


def lens(part: Part):
    x0, x1 = LENS_X
    idx = [part.add_v((x0, MOUNT_H, -LENS_HALF_W)), part.add_v((x1, MOUNT_H, -LENS_HALF_W)),
           part.add_v((x1, MOUNT_H, LENS_HALF_W)), part.add_v((x0, MOUNT_H, LENS_HALF_W))]
    part.add_f_dir(idx, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), 0, (0.0, -1.0, 0.0))


def build(arms: int) -> Part:
    p = Part()
    pole(p, 1)
    sides = (1, -1) if arms == 2 else (1,)
    for j, sgn in enumerate(sides):
        g = 2 + 4 * j
        arm(p, sgn, g)
        luminaire(p, sgn, g + 1, g + 2, g + 3)
    return p


def obj_text(part: Part, name: str, note: str) -> str:
    out = [f"# {name} — {note}", "# generated by tools/make_streetlight_led.py (ledger 0056); self-made, CC0-1.0",
           "# frame: metres, +x road-ward, +y up, origin = pole axis at the road datum", f"o {name}"]
    out += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in part.v]
    vt, vt_ix = [], {}
    for _, uv, _ in part.f:
        for u in uv:
            key = (round(u[0], 5), round(u[1], 5))
            if key not in vt_ix:
                vt_ix[key] = len(vt) + 1
                vt.append(key)
    out += [f"vt {u:.5f} {v:.5f}" for u, v in vt]
    cur = None
    for idx, uv, g in part.f:
        if g != cur:
            out.append("s off" if g == 0 else f"s {g}")
            cur = g
        out.append("f " + " ".join(f"{i + 1}/{vt_ix[(round(u[0], 5), round(u[1], 5))]}" for i, u in zip(idx, uv)))
    return "\n".join(out) + "\n"


def mast_radius_at_base() -> float:
    """circumscribed radius of the pole at its buried foot (verify_race G's lamp footprint)"""
    return R_BASE + TAPER * POLE_BURY


def spec() -> dict:
    return {
        "name": NAME,
        "_doc": "ledger 0056 — modern LED street light. Frame: metres, +x road-ward, +y up, origin = pole axis at the road "
                "datum. Read by tools/author_lamps_blend.py (placement) and tools/verify_race.py (mast footprint).",
        "files": {"post_twin": f"{NAME}_post_twin.obj", "post_single": f"{NAME}_post_single.obj", "lens": f"{NAME}_lens.obj"},
        "pole_height_m": round(POLE_H, 4),
        "arm_length_m": round(ARM_L, 4),
        "mounting_height_m": round(MOUNT_H, 4),
        "lens_centre_m": [round(c, 4) for c in LENS_CENTRE],
        "lens_size_m": [round(LENS_X[1] - LENS_X[0], 4), round(2 * LENS_HALF_W, 4)],
        "pole_bury_m": POLE_BURY,
        "mast_radius_m": round(mast_radius_at_base(), 4),
        "sources": {
            "pole_height": "Caltrans Standard Plan ES-6A (Lighting Standard, Types 15 and 21): Type 21 pole 35'-0\"",
            "arm": "ES-6A mast-arm lengths 6/8/10/12/15 ft; City of San Diego SDE-101: arm 8' max (concrete/fiberglass), 12' for Type 15 (steel)",
            "mounting_height": "ES-6A Type 21 + 12 ft arm = 38'-9\" (Type 15 + 12 ft arm = 33'-9\"); SDE-101's own table tops out at 30' for its 250 W HPS / 180 W LPS arterial lamp",
            "pole_od": "ES-6A Type 21 base OD 8-5/8\"; 0.14 in/ft taper",
        },
    }


def outputs() -> dict[str, str]:
    twin, single, ln = build(2), build(1), Part()
    lens(ln)
    return {
        f"{NAME}_post_twin.obj": obj_text(twin, f"{NAME}_post_twin", "pole + two mast arms + two LED cobra heads (LIGHTPOST)"),
        f"{NAME}_post_single.obj": obj_text(single, f"{NAME}_post_single", "pole + one mast arm + one LED cobra head (LIGHTPOST)"),
        f"{NAME}_lens.obj": obj_text(ln, f"{NAME}_lens", "flat LED lens under the road-ward head (LIGHTS, emissive)"),
        f"{NAME}.json": json.dumps(spec(), indent=1) + "\n",
    }


def main(argv: list[str]) -> int:
    outs = outputs()
    if "--check" in argv:
        bad = [n for n, t in outs.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        print("make_streetlight_led --check: " + ("differs: " + ", ".join(bad) if bad else "committed files match"))
        return 1 if bad else 0
    for n, t in outs.items():
        (OUT / n).write_text(t, encoding="utf-8", newline="\n")
        nv = sum(1 for ln in t.splitlines() if ln.startswith("v "))
        nf = sum(1 for ln in t.splitlines() if ln.startswith("f "))
        print(f"[streetlight] wrote assets/models/{n}" + (f"  ({nv} v, {nf} faces)" if n.endswith(".obj") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
