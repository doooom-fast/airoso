"""Generate traffic-signal furniture (ledger 0096, Denver Grand Prix PLAN §4b / DOSSIER §8) — deterministic,
self-made (CC0). The asset library held no signal furniture at all; this is the first.

Kevin's decision E2 (2026-11-23): signals are modelled, LIT STEADY at night, no cycle. So every lens is its own
named mesh with its own material class; which lens is lit is the placer's and the CSP config's business, and
nothing here animates.

WHAT IS MADE (assets/models/, parts — a junction is assembled from them by the recipes in signals.json):
  signal_mast_arm_25 / _35 / _45.obj   pole + mast arm, arm 25 / 35 / 45 ft
  signal_pedestal.obj                  10 ft pedestal pole on a square base
  signal_pushbutton_post.obj           pushbutton post with the button and an R10-3 plate
  signal_head_3.obj                    3-section vehicle head (R, Y, G), tunnel visors, backplate
  signal_head_3_arrow_l.obj            3-section left-arrow head (red, yellow, green arrows)
  signal_head_4_fya_l.obj              4-section flashing-yellow-arrow left-turn head
  signal_head_5_dog_l / _dog_r.obj     5-section cluster ("doghouse") head, left- or right-turn arrows
  signal_head_lrt_2.obj                2-section light-rail (bar) signal head — the rail-crossing set's signal
  signal_ped_head.obj                  pedestrian head (hand / walking person face)
  signals.json                         every dimension, each lens centre, the mounting recipes, proposed bindings
and assets/textures/signal_lens_<aspect>[_off].png, ped_signal_<hand|walk|off>.png (128 px, lit and unlit).

DIMENSIONS. "MUTCD" is the 2009 edition with revisions 1-3 (section numbers moved in the 11th edition, 2023).
The section numbers and values were written from knowledge of that edition and were NOT re-read against the
document in the session that wrote this maker: check a number against the MUTCD before leaning on it. [typical] marks a number no standard fixes: it is a common manufacturer or agency value
and must give way to Denver's own standard details or a measurement when the survey has one.
  lens                 12 in (0.305 m) nominal             MUTCD 4D.07 (8 in and 12 in are the two sizes; 12 in governs
                                                            arrows and most urban approaches)
  section housing      13.5 in wide x 14 in high x 8 in    [typical] 12 in polycarbonate / aluminium section, ITE VTCSH
                                                            class; ITE fixes the lens and the optics, not the box
  visor                tunnel, 10 in long, open below      [typical]; MUTCD 4D.12 asks for visors, not a length
  backplate            5 in border, dull black             border width [typical]; MUTCD 4D.12 (backplates, dull black
                                                            front). The optional 1-3 in yellow retroreflective edge
                                                            of 4D.12 is NOT drawn: unknown for Denver, the survey says
  head over the road   bottom >= 15 ft, top <= 25.6 ft     MUTCD 4D.15 (15 ft minimum clearance; the 25.6 ft maximum
                                                            to the top of a housing 40-53 ft beyond the stop line)
  head on a pedestal   bottom 8 ft to 19 ft over the walk  MUTCD 4D.15; here 10 ft (the pedestal's own height)
  faces apart          >= 8 ft between through faces       MUTCD 4D.13; signals.json's default head spacing is 12 ft
  mast arm             25 / 35 / 45 ft                     [typical] three lengths chosen to span 2, 3 and 4 lanes from
                                                            the kerb; Denver's standard arm lengths are NOT checked
  arm at the pole      19 ft (5.79 m), rising 1.5 deg      [typical], set so every head here clears 15 ft and none
                                                            tops 25.6 ft (the test proves both for all three arms)
  mast pole            22 ft, 13 in OD at the base         [typical]; taper 0.14 in/ft as Caltrans ES-6A / ES-7 steel
  pedestal             4 in pipe (4.5 in OD), 10 ft        pipe OD is ASME B36.10 NPS 4; height and the 13.5 in square
                                                            base [typical]
  pedestrian head      18 in wide x 16 in high             the ITE 16 x 18 in pedestrian-indication class; which way
                                                            round Denver's units sit is [typical]
  pedestrian symbols   9 in high                           MUTCD 4E.04 (at least 6 in; 9 in beyond 100 ft)
  pedestrian head      bottom 7 ft to 10 ft over the walk  MUTCD 4E.05; signals.json's recipe uses 8 ft
  pushbutton           3.5 ft over the walk                MUTCD 4E.08 (about 3.5 ft, at most 4 ft); 2 in button
                                                            [typical]; R10-3 plate 9 x 12 in, MUTCD Table 2B-1
  colours              housings and backplates black, poles galvanised grey — [typical]; Denver's finish is unverified

FRAMES (L6: metres, +y up, never pre-mirrored).
  mast, pedestal, post: origin = the pole axis at the walk (ground datum, y = 0); +x is road-ward (the arm reaches
      over the road along +x); z runs along the kerb. Poles run on below the datum so a low verge shows no gap.
  heads: origin = the middle of the housing stack on its BACK face; the lenses face +z (toward the approaching
      driver); +y up. Seen from the driver, +x is on the RIGHT, so a left-turn arrow sits at -x and points to -x.

    python tools/make_signals.py            # writes the models, the spec and the lens textures
    python tools/make_signals.py --check    # exit 1 if the committed files differ
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from street_furniture_mesh import FT, IN, Model, write_or_check          # noqa: E402

AIROSO = Path(__file__).resolve().parents[1]
OUT = AIROSO / "assets" / "models"
TEX = AIROSO / "assets" / "textures"
MAKER = "tools/make_signals.py"

# ---- vehicle heads -----------------------------------------------------------------------------------------------
LENS_D = 12 * IN                      # MUTCD 4D.07
SEC_W, SEC_H, SEC_D = 13.5 * IN, 14 * IN, 8 * IN      # [typical]
VISOR_L, VISOR_R = 10 * IN, 6.6 * IN                  # [typical] tunnel visor, a little wider than the lens
VISOR_OPEN_DEG = 60.0                                 # the slot left open underneath
BACKPLATE = 5 * IN                                    # [typical] border beyond the housing
BACKPLATE_Z = 0.5 * SEC_D
BRACKET_L, BRACKET_R = 0.22, 0.03                     # [typical] rigid arm bracket: the head stands 0.22 m off the arm
LENS_SIDES, VISOR_SIDES = 12, 8
LENS_PROUD = 0.003                                    # the lens stands 3 mm off the door: no z-fight

# cells: (aspect, column, row) with column 0 = the stack's centre line (in section widths), row 0 = top
HEADS = {
    "signal_head_3": ("3-section vehicle head: red, yellow, green", [("R", 0, 0), ("Y", 0, 1), ("G", 0, 2)]),
    "signal_head_3_arrow_l": ("3-section left-turn arrow head: red, yellow, green arrows (MUTCD 4D.19)",
                              [("RA_L", 0, 0), ("YA_L", 0, 1), ("GA_L", 0, 2)]),
    "signal_head_4_fya_l": ("4-section flashing-yellow-arrow left-turn head (MUTCD 4D.20)",
                            [("RA_L", 0, 0), ("YA_L", 0, 1), ("YA_L", 0, 2), ("GA_L", 0, 3)]),
    "signal_head_5_dog_l": ("5-section cluster head, left-turn arrows on the driver's left (MUTCD 4D.20)",
                            [("R", 0, 0), ("YA_L", -0.5, 1), ("Y", 0.5, 1), ("GA_L", -0.5, 2), ("G", 0.5, 2)]),
    "signal_head_5_dog_r": ("5-section cluster head, right-turn arrows on the driver's right (MUTCD 4D.24)",
                            [("R", 0, 0), ("Y", -0.5, 1), ("YA_R", 0.5, 1), ("G", -0.5, 2), ("GA_R", 0.5, 2)]),
    "signal_head_lrt_2": ("2-section light-rail signal head: horizontal bar (stop) over vertical bar (go), white "
                          "(MUTCD 8C.11, Figure 8C-3)", [("BAR_H", 0, 0), ("BAR_V", 0, 1)]),
}
LENS_RGB = {"R": (232, 32, 28), "Y": (255, 190, 0), "G": (0, 214, 140), "BAR": (245, 245, 235)}

# ---- supports ----------------------------------------------------------------------------------------------------
TAPER = 0.14 * IN / FT / 2            # radius per metre (0.14 in/ft on the diameter)
MAST_H = 22 * FT                      # [typical]
MAST_R = 13 * IN / 2                  # [typical]
MAST_BURY = 1.0
ARM_Y0 = 19 * FT                      # [typical] arm centre line at the pole
ARM_RISE = math.tan(math.radians(1.5))                # [typical]
ARM_LENGTHS_FT = (25, 35, 45)         # [typical]
ARM_R_TIP = 0.05
HEAD_SPACING = 12 * FT                # [typical] one lane; MUTCD 4D.13 needs >= 8 ft between through faces
HEAD_FROM_TIP = 0.6
PED_PIPE_R = 4.5 * IN / 2             # NPS 4 pipe
PEDESTAL_H = 10 * FT                  # [typical]
PEDESTAL_BASE = (13.5 * IN, 15 * IN)  # [typical] square cast base: side, height
PED_W, PED_H, PED_D = 18 * IN, 16 * IN, 7 * IN        # ITE 16 x 18 class; depth [typical]
PED_HOOD = 7 * IN                     # [typical]
PED_MOUNT_BOTTOM = 8 * FT             # MUTCD 4E.05: 7 ft to 10 ft
BUTTON_Y = 3.5 * FT                   # MUTCD 4E.08
BUTTON_POST_H = 5 * FT                # [typical]
BUTTON_PIPE_R = 2.875 * IN / 2        # NPS 2-1/2 pipe [typical]
R10_3 = (9 * IN, 12 * IN)             # MUTCD Table 2B-1


def _cells(cells):
    """cell centres (x, y) with the stack centred on the origin"""
    rows = max(r for _, _, r in cells) + 1
    return [(a, c * SEC_W, ((rows - 1) / 2 - r) * SEC_H) for a, c, r in cells]


def _blocks(cells):
    """the housing as boxes: one per row group sharing a width (x0, x1, y0, y1)"""
    by_row = {}
    for a, x, y in _cells(cells):
        by_row.setdefault(round(y, 6), []).append(x)
    out = []
    for y, xs in sorted(by_row.items(), reverse=True):
        box = [min(xs) - SEC_W / 2, max(xs) + SEC_W / 2, y - SEC_H / 2, y + SEC_H / 2]
        if out and abs(out[-1][0] - box[0]) < 1e-9 and abs(out[-1][1] - box[1]) < 1e-9:
            out[-1][2] = box[2]
        else:
            out.append(box)
    return out


def head(name: str) -> Model:
    note, cells = HEADS[name]
    m = Model(name, note, "metres, +y up, origin = middle of the stack on its back face, lenses face +z, driver's right = +x", MAKER)
    hs = m.obj("HOUSING", "SIGNALHEAD")
    for x0, x1, y0, y1 in _blocks(cells):
        hs.box((x0, y0, 0.0), (x1, y1, SEC_D))
    lo, hi = VISOR_OPEN_DEG / 2, 360.0 - VISOR_OPEN_DEG / 2
    for a, x, y in _cells(cells):
        hs.tube([(x, y, SEC_D), (x, y, SEC_D + VISOR_L)], [VISOR_R, VISOR_R], VISOR_SIDES, arc=(lo, hi), two_sided=True)
    bp = m.obj("BACKPLATE", "SIGNALBACKPLATE")
    blocks = _blocks(cells)
    for i, (x0, x1, y0, y1) in enumerate(blocks):                   # top to bottom; a wider block's plate starts one
        yb = y1 + BACKPLATE                                         # border above the join, the narrow one's ends there
        ya = y0 - BACKPLATE if i == len(blocks) - 1 else y0 + BACKPLATE
        q = [(x0 - BACKPLATE, ya, BACKPLATE_Z), (x1 + BACKPLATE, ya, BACKPLATE_Z), (x1 + BACKPLATE, yb, BACKPLATE_Z), (x0 - BACKPLATE, yb, BACKPLATE_Z)]
        uv = tuple((p[0], p[1]) for p in q)
        bp.polygon(q, uv, (0.0, 0.0, 1.0))
        bp.polygon(q, uv, (0.0, 0.0, -1.0))
    br = m.obj("BRACKET", "SIGNALPOST")
    br.tube([(0.0, 0.0, 0.0), (0.0, 0.0, -BRACKET_L)], [BRACKET_R, BRACKET_R], 6, cap_end=False)
    for k, (a, x, y) in enumerate(_cells(cells), 1):
        ln = m.obj(f"LENS_{k}_{a}", f"SIGNALLENS_{a}")
        z = SEC_D + LENS_PROUD
        ring = [(x + LENS_D / 2 * math.cos(2 * math.pi * j / LENS_SIDES), y + LENS_D / 2 * math.sin(2 * math.pi * j / LENS_SIDES), z) for j in range(LENS_SIDES)]
        ln.polygon(ring, tuple((0.5 + (p[0] - x) / LENS_D, 0.5 + (p[1] - y) / LENS_D) for p in ring), (0.0, 0.0, 1.0))
    return m


def head_extent(name: str):
    """(half width, half height) of the head WITH its backplate — what MUTCD 4D.15's clearances are measured to"""
    b = _blocks(HEADS[name][1])
    return max(x1 for _, x1, _, _ in b) + BACKPLATE, max(y1 for _, _, _, y1 in b) + BACKPLATE


def ped_head() -> Model:
    m = Model("signal_ped_head", "pedestrian signal head, 18 x 16 in face (hand / walking person)",
              "metres, +y up, origin = middle of the housing on its back face, the face looks along +z", MAKER)
    hs = m.obj("HOUSING", "SIGNALHEAD")
    hs.box((-PED_W / 2, -PED_H / 2, 0.0), (PED_W / 2, PED_H / 2, PED_D))
    z0, z1, t = PED_D, PED_D + PED_HOOD, 0.004
    for lo, hi in (((-PED_W / 2, PED_H / 2 - t, z0), (PED_W / 2, PED_H / 2, z1)),            # hood: top and two cheeks
                   ((-PED_W / 2, -PED_H / 2, z0), (-PED_W / 2 + t, PED_H / 2 - t, z1)),
                   ((PED_W / 2 - t, -PED_H / 2, z0), (PED_W / 2, PED_H / 2 - t, z1))):
        hs.box(lo, hi, skip=("-z",))
    br = m.obj("BRACKET", "SIGNALPOST")
    br.box((-0.05, -0.10, -0.12), (0.05, 0.10, 0.0))
    f = m.obj("LENS_PED", "PEDLENS")
    i = 0.6 * IN
    q = [(-PED_W / 2 + i, -PED_H / 2 + i, PED_D + LENS_PROUD), (PED_W / 2 - i, -PED_H / 2 + i, PED_D + LENS_PROUD),
         (PED_W / 2 - i, PED_H / 2 - i, PED_D + LENS_PROUD), (-PED_W / 2 + i, PED_H / 2 - i, PED_D + LENS_PROUD)]
    f.polygon(q, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), (0.0, 0.0, 1.0))
    return m


def mast_arm(arm_ft: float) -> Model:
    L = arm_ft * FT
    name = f"signal_mast_arm_{int(arm_ft)}"
    m = Model(name, f"signal pole with a {int(arm_ft)} ft mast arm",
              "metres, +y up, origin = pole axis at the walk, the arm reaches over the road along +x, z along the kerb", MAKER)
    p = m.obj("POLE", "SIGNALPOST")
    r = lambda y: MAST_R - TAPER * max(y, 0.0)
    p.tube([(0.0, -MAST_BURY, 0.0), (0.0, 0.0, 0.0), (0.0, MAST_H, 0.0)], [r(0), r(0), r(MAST_H)], 10)
    p.revolve([(MAST_R + 0.09, 0.0), (MAST_R + 0.09, 0.05), (MAST_R + 0.02, 0.09)], 10, cap_top=False)   # anchor-base flange
    r0 = 0.085 + 0.0010 * arm_ft                               # [typical] a longer arm is a heavier section
    a = m.obj("ARM", "SIGNALPOST")
    a.tube([(0.0, ARM_Y0, 0.0), (L, ARM_Y0 + L * ARM_RISE, 0.0)], [r0, ARM_R_TIP], 8)
    a.revolve([(r(ARM_Y0) + 0.03, ARM_Y0 - r0 - 0.06), (r(ARM_Y0) + 0.03, ARM_Y0 + r0 + 0.06)], 10, cap_top=True, cap_bottom=True)   # arm clamp
    return m


def arm_point(arm_ft: float, x: float):
    """the arm's centre line at ``x`` metres from the pole axis"""
    return (x, ARM_Y0 + x * ARM_RISE, 0.0)


def default_head_xs(arm_ft: float):
    """default head stations along an arm: the first 0.6 m in from the tip, then one per 12 ft lane toward the pole,
    none closer than 3 m to the pole. A survey record overrides these; they exist so a `tagged` junction can stand."""
    xs, x = [], arm_ft * FT - HEAD_FROM_TIP
    while x >= 3.0:
        xs.append(round(x, 3))
        x -= HEAD_SPACING
    return xs


def pedestal() -> Model:
    m = Model("signal_pedestal", "10 ft signal pedestal: NPS 4 pipe on a square cast base",
              "metres, +y up, origin = pole axis at the walk; a head stands on the pipe's top", MAKER)
    p = m.obj("POLE", "SIGNALPOST")
    s, h = PEDESTAL_BASE
    p.box((-s / 2, -0.4, -s / 2), (s / 2, h, s / 2), skip=("-y",))
    p.tube([(0.0, h, 0.0), (0.0, PEDESTAL_H, 0.0)], [PED_PIPE_R, PED_PIPE_R], 8)
    return m


def pushbutton_post() -> Model:
    m = Model("signal_pushbutton_post", "pedestrian pushbutton post: button at 3.5 ft, R10-3 plate over it",
              "metres, +y up, origin = post axis at the walk; the button and the plate face +z", MAKER)
    p = m.obj("POLE", "SIGNALPOST")
    p.tube([(0.0, -0.4, 0.0), (0.0, BUTTON_POST_H, 0.0)], [BUTTON_PIPE_R, BUTTON_PIPE_R], 8)
    zf = BUTTON_PIPE_R
    hs = m.obj("BUTTON_HOUSING", "SIGNALHEAD")
    hs.box((-0.05, BUTTON_Y - 0.075, zf - 0.01), (0.05, BUTTON_Y + 0.075, zf + 0.05))
    b = m.obj("BUTTON", "SIGNALBUTTON")
    b.tube([(0.0, BUTTON_Y, zf + 0.05), (0.0, BUTTON_Y, zf + 0.062)], [IN, IN], 8)
    w, h = R10_3
    y0 = BUTTON_Y + 0.075 + 0.03
    z = zf + 0.006
    q = [(-w / 2, y0, z), (w / 2, y0, z), (w / 2, y0 + h, z), (-w / 2, y0 + h, z)]
    m.obj("SIGN_R10-3", "SIGNFACE_R10-3").polygon(q, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), (0.0, 0.0, 1.0))
    m.obj("SIGN_BACK", "SIGNBACK").polygon([(x, y, z - 0.002) for x, y, _ in q], ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), (0.0, 0.0, -1.0))
    return m


def models() -> dict[str, Model]:
    out = {f"signal_mast_arm_{ft}": mast_arm(ft) for ft in ARM_LENGTHS_FT}
    out["signal_pedestal"] = pedestal()
    out["signal_pushbutton_post"] = pushbutton_post()
    out.update({n: head(n) for n in HEADS})
    out["signal_ped_head"] = ped_head()
    return out


def spec(ms: dict[str, Model]) -> dict:
    r4 = lambda v: [round(c, 4) for c in v]
    heads = {}
    for n in HEADS:
        hw, hh = head_extent(n)
        heads[n] = {"file": n + ".obj", "note": HEADS[n][0], "half_width_m": round(hw, 4), "half_height_m": round(hh, 4),
                    "lenses": [{"object": f"LENS_{k}_{a}", "aspect": a, "material": f"SIGNALLENS_{a}",
                                "centre_m": r4((x, y, SEC_D + LENS_PROUD)), "normal": [0, 0, 1]}
                               for k, (a, x, y) in enumerate(_cells(HEADS[n][1]), 1)], **ms[n].summary()}
    arms = {}
    for ft in ARM_LENGTHS_FT:
        n = f"signal_mast_arm_{ft}"
        arms[n] = {"file": n + ".obj", "arm_length_m": round(ft * FT, 4), "arm_length_ft": ft,
                   "arm_at_pole_m": r4(arm_point(ft, 0.0)), "arm_tip_m": r4(arm_point(ft, ft * FT)),
                   "default_head_stations_m": default_head_xs(ft),
                   "head_origins_m": [r4((x, arm_point(ft, x)[1], BRACKET_L)) for x in default_head_xs(ft)],
                   "mast_radius_m": round(MAST_R + 0.09, 4), **ms[n].summary()}
    aspects = sorted({a for _, c in HEADS.values() for a, _, _ in c})
    return {
        "name": "signals",
        "_doc": "ledger 0096 — traffic-signal furniture, generated by tools/make_signals.py (docstring: every dimension and "
                "its source; [typical] = no standard fixes it). Parts, not junctions: a placer assembles a junction from "
                "'recipes'. Split each OBJ into its objects with tools/street_furniture_mesh.read_obj_objects; the lenses "
                "are separate meshes so one can be lit steady at night (decision E2). Nothing here is placed on a track.",
        "provisional": "arm lengths, pole sizes, housing colours and the 8 ft pedestrian-head height are [typical], not "
                       "Denver's standard details; source/survey/signals.json decides which parts stand where",
        "frames": {"support": "origin = pole axis at the walk, +x road-ward (the arm), +y up, z along the kerb",
                   "head": "origin = middle of the stack on its back face, lenses face +z, +y up, driver's right = +x"},
        "mast_arms": arms,
        "arm_rise_per_m": round(ARM_RISE, 6),
        "pedestal": {"file": "signal_pedestal.obj", "top_m": round(PEDESTAL_H, 4), "pipe_radius_m": round(PED_PIPE_R, 4),
                     "base_side_m": round(PEDESTAL_BASE[0], 4), **ms["signal_pedestal"].summary()},
        "pushbutton_post": {"file": "signal_pushbutton_post.obj", "button_height_m": round(BUTTON_Y, 4),
                            "post_height_m": round(BUTTON_POST_H, 4), "sign": "R10-3, 9 x 12 in, texture mutcd_r10-3.png",
                            **ms["signal_pushbutton_post"].summary()},
        "heads": heads,
        "ped_head": {"file": "signal_ped_head.obj", "face_m": [round(PED_W, 4), round(PED_H, 4)],
                     "lens": {"object": "LENS_PED", "material": "PEDLENS", "centre_m": [0.0, 0.0, round(PED_D + LENS_PROUD, 4)], "normal": [0, 0, 1]},
                     "mount_bottom_m": round(PED_MOUNT_BOTTOM, 4), **ms["signal_ped_head"].summary()},
        "recipes": {
            "_doc": "part + where its origin goes in the support's frame + yaw about +y (degrees, 0 = facing +z). "
                    "'drop' lists objects to leave out. Heads on an arm face +z by default; the placer turns the whole "
                    "junction leg to the approach.",
            "mast_arm_heads": {"each head": {"at": "mast_arms[<arm>].head_origins_m[i]", "yaw_deg": 0}},
            "pedestal_head": {"part": "signal_head_3", "at": r4((0.0, PEDESTAL_H + head_extent("signal_head_3")[1] - BACKPLATE, -SEC_D / 2)),
                              "yaw_deg": 0, "drop": ["BRACKET"]},
            "ped_head_on_pole": {"part": "signal_ped_head", "at": r4((0.0, PED_MOUNT_BOTTOM + PED_H / 2, MAST_R + 0.12)),
                                 "yaw_deg": 0, "note": "z = the pole's radius at that height + the 0.12 m bracket; on the pedestal use pipe_radius_m"},
        },
        "bindings_proposed": {
            "_doc": "material class -> texture. These are pbr.TEXTURES rows the ENGINE has to add (scripts/ac/pbr.py is "
                    "not this maker's); every material has a texture (L7). Lens meshes carry real UVs (0..1 over the "
                    "lens) and need the prep's UV exemption, like the sign plates (PLAN §4b engine work 8).",
            "SIGNALPOST": "solid_metal_grey.png", "SIGNALHEAD": "solid_sign_black.png", "SIGNALBACKPLATE": "solid_sign_black.png",
            "SIGNALBUTTON": "solid_metal_grey.png", "SIGNBACK": "solid_metal_grey.png", "SIGNFACE_R10-3": "mutcd_r10-3.png",
            "PEDLENS": {"lit_hand": "ped_signal_hand.png", "lit_walk": "ped_signal_walk.png", "unlit": "ped_signal_off.png"},
            **{f"SIGNALLENS_{a}": {"lit": f"signal_lens_{a.lower()}.png", "unlit": f"signal_lens_{a.lower()}_off.png"} for a in aspects},
        },
        "sources": {
            "lens": "MUTCD 2009 4D.07: signal lenses are 8 in or 12 in nominal; 12 in used",
            "mounting": "MUTCD 2009 4D.15: over a roadway the bottom of the housing (and backplate) at least 15 ft above the "
                        "pavement, the top at most 25.6 ft; not over a roadway, the bottom 8 ft to 19 ft above the walk",
            "separation": "MUTCD 2009 4D.13: through signal faces at least 8 ft apart, centre to centre",
            "backplate": "MUTCD 2009 4D.12: backplates, dull black front; yellow retroreflective edge 1-3 in optional (not drawn)",
            "pedestrian": "MUTCD 2009 4E.04 (symbols at least 6 in high), 4E.05 (bottom of the housing 7 ft to 10 ft above the walk), "
                          "4E.08 (pushbutton about 3.5 ft, at most 4 ft)",
            "light_rail": "MUTCD 2009 8C.11 and Figure 8C-3: light-rail signals are white bars; a horizontal bar is stop, a vertical bar is go",
            "typical": "section 13.5 x 14 x 8 in, visor 10 in, backplate border 5 in, arm 25/35/45 ft at 19 ft rising 1.5 deg, pole 22 ft "
                       "x 13 in, pedestal 10 ft, pushbutton post 5 ft: common values, not from a Denver standard detail",
        },
    }


def outputs() -> dict[str, str]:
    ms = models()
    out = {n + ".obj": m.text() for n, m in ms.items()}
    out["signals.json"] = json.dumps(spec(ms), indent=1) + "\n"
    return out


# ---- textures ----------------------------------------------------------------------------------------------------
ARROW_L = [(0.14, 0.5), (0.48, 0.84), (0.48, 0.62), (0.86, 0.62), (0.86, 0.38), (0.48, 0.38), (0.48, 0.16)]


def textures() -> dict:
    from PIL import Image, ImageDraw
    from street_furniture_draw import SS, thick_line
    px, out = 128, {}
    aspects = sorted({a for _, c in HEADS.values() for a, _, _ in c})

    def lens(aspect: str, lit: bool):
        n = px * SS
        rgb = LENS_RGB[aspect.split("_")[0][0] if not aspect.startswith("BAR") else "BAR"]
        dim = tuple(int(c * 0.20) + 8 for c in rgb)
        on = rgb if lit else dim
        im = Image.new("RGB", (n, n), (10, 10, 10))
        d = ImageDraw.Draw(im)
        plain = aspect in ("R", "Y", "G")
        d.ellipse([2 * SS, 2 * SS, n - 2 * SS, n - 2 * SS], fill=on if plain else (14, 14, 14))
        if plain and not lit:                                            # an unlit lens: a darker centre, the rim catches light
            d.ellipse([14 * SS, 14 * SS, n - 14 * SS, n - 14 * SS], fill=tuple(int(c * 0.8) for c in dim))
        if aspect.endswith(("A_L", "A_R")):
            pts = [((x if aspect.endswith("_L") else 1 - x) * n, (1 - y) * n) for x, y in ARROW_L]
            d.polygon(pts, fill=on)
        if aspect == "BAR_H":
            d.rectangle([0.16 * n, 0.42 * n, 0.84 * n, 0.58 * n], fill=on)
        if aspect == "BAR_V":
            d.rectangle([0.42 * n, 0.16 * n, 0.58 * n, 0.84 * n], fill=on)
        return im.resize((px, px), Image.LANCZOS)

    for a in aspects:
        out[f"signal_lens_{a.lower()}.png"] = lens(a, True)
        out[f"signal_lens_{a.lower()}_off.png"] = lens(a, False)

    def ped(kind: str):
        w, h = 256 * SS, 256 * SS                                        # the 18 x 16 in face on a square texture
        im = Image.new("RGB", (w, h), (12, 12, 12))
        d = ImageDraw.Draw(im)
        orange, white, ghost = (255, 106, 0), (245, 245, 238), (34, 30, 28)
        u = lambda x, y: (x * w, (1 - y) * h)                            # unit square, y up
        # the hand (left half) — a palm, four fingers, a thumb; 9 in of the 16 in face is 0.56 of the height
        c = orange if kind == "hand" else ghost
        for fx, top in ((0.115, 0.72), (0.185, 0.78), (0.255, 0.76), (0.325, 0.70)):
            thick_line(d, [u(fx, 0.44), u(fx, top)], 0.052 * w, c, round_ends=True)
        d.rounded_rectangle([*u(0.085, 0.50), *u(0.355, 0.24)], radius=0.05 * w, fill=c)
        thick_line(d, [u(0.33, 0.34), u(0.435, 0.50)], 0.055 * w, c, round_ends=True)
        # the walking person (right half)
        c = white if kind == "walk" else ghost
        d.ellipse([*u(0.685, 0.80), *u(0.775, 0.70)], fill=c)
        for pts, t in (([(0.715, 0.66), (0.690, 0.44)], 0.075), ([(0.720, 0.63), (0.800, 0.52), (0.850, 0.50)], 0.036),
                       ([(0.705, 0.63), (0.630, 0.54), (0.610, 0.46)], 0.036), ([(0.695, 0.45), (0.760, 0.33), (0.790, 0.21)], 0.044),
                       ([(0.685, 0.45), (0.640, 0.33), (0.575, 0.22)], 0.044)):
            thick_line(d, [u(*p) for p in pts], t * w, c, round_ends=True)
        return im.resize((256, 256), Image.LANCZOS)

    for k in ("hand", "walk", "off"):
        out[f"ped_signal_{k}.png"] = ped(k)
    return out


def main(argv: list[str]) -> int:
    rc = write_or_check(OUT, outputs(), argv, "signals")
    from street_furniture_draw import write_or_check_png
    return rc | write_or_check_png(TEX, textures(), argv, "signals")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
