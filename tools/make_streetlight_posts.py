"""Generate two more street-light classes beside `led_cobra` (ledger 0096, Denver Grand Prix PLAN §4b / DOSSIER
§8) — deterministic, self-made (CC0), parametric.

THE CLASS LIST IS PROVISIONAL. PLAN §4b wants "one owned model per class" with the class read per street from
street-level imagery, and that survey has not been made: nobody has yet said which fixtures stand on the lap. The
two families here are the likely ones for a downtown (a pedestrian-scale post and a double-arm arterial post), built
as parametric makers so the survey's answer becomes a row in CLASSES, not a new tool. Until then every dimension
below is [typical]: a common catalogue value, not Denver's or Xcel Energy's standard, and not a measurement.

ALREADY OWNED, NOT REMADE: `led_cobra` (tools/make_streetlight_led.py) is a 35 ft Caltrans Type 21 pole with one or
two 12 ft upswept arms and cobra heads. Where the survey finds that fixture, use it. `arterial_*` below is a
different fixture (a shorter pole, short straight bracket arms, a flat rectangular LED head), not a second copy.

CLASSES (assets/models/streetlight_<class>.obj + streetlight_posts.json):
  ped_acorn        12 ft post, flared base, acorn refractor      [typical] pedestrian-scale lighting is 10-16 ft;
  ped_globe        12 ft post, flared base, 18 in globe           acorn about 16 x 30 in; globe 18 in
  arterial_twin    30 ft tapered pole, two 8 ft bracket arms     [typical]; mounting height 32.5 ft; pole 8 in OD at
  arterial_single  the same pole, one road-ward arm               the base, 0.14 in/ft taper (as Caltrans ES-6A steel)

Each file holds the post as object POST (material LIGHTPOST) and each light-emitting part as its own object LENS,
or LENS_1 (road-ward) and LENS_2, with material LIGHTS: the two classes pbr.TEXTURES already binds, and the mesh
name CSP's [LIGHT_N] is keyed on (tools/author_lamps_blend.py, scripts/ac/ext_config.lamp_clusters).

FRAME (as the LED lamp): metres, +x road-ward, +y up, z along the road, origin = the pole axis at the datum. The
arterial pole runs on 2.5 m below it, the pedestrian post 0.5 m.

    python tools/make_streetlight_posts.py            # writes the models and the spec
    python tools/make_streetlight_posts.py --check    # exit 1 if the committed files differ
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
MAKER = "tools/make_streetlight_posts.py"
TAPER = 0.14 * IN / FT / 2            # radius per metre

# every value [typical] until the survey names the fixtures (see the docstring)
CLASSES = {
    "ped_acorn": {"family": "pedestrian", "height_ft": 12.0, "top": "acorn"},
    "ped_globe": {"family": "pedestrian", "height_ft": 12.0, "top": "globe"},
    "arterial_twin": {"family": "arterial", "pole_ft": 30.0, "arm_ft": 8.0, "rise_ft": 2.5, "arms": 2},
    "arterial_single": {"family": "arterial", "pole_ft": 30.0, "arm_ft": 8.0, "rise_ft": 2.5, "arms": 1},
}
PED_BURY, ART_BURY = 0.5, 2.5
PED_SIDES, ART_SIDES = 10, 10
PED_BASE = [(0.19, 0.0), (0.19, 0.10), (0.15, 0.16), (0.13, 0.55), (0.085, 0.70)]     # flared base profile (r, y)
PED_SHAFT_R = (0.065, 0.045)          # 5 in -> 3.5 in OD
ACORN = [(0.075, 0.00), (0.105, 0.05), (0.105, 0.11), (0.200, 0.24), (0.190, 0.36), (0.110, 0.60), (0.095, 0.63)]
ACORN_CAP = [(0.115, 0.63), (0.070, 0.70), (0.022, 0.74), (0.0, 0.80)]
GLOBE_R, GLOBE_LAT = 9 * IN, 6
ART_BASE_R = 8 * IN / 2
HEAD = (0.66, 0.30, 0.10)             # flat LED head: length (along the arm), width, depth
LENS = (0.46, 0.22)
LIFT = 0.004


def pedestrian(name: str, height_ft: float, top: str) -> tuple[Model, dict]:
    H = height_ft * FT
    m = Model(f"streetlight_{name}", f"pedestrian-scale post, {height_ft:g} ft, {top} luminaire [typical, provisional class]",
              "metres, +x road-ward, +y up, origin = post axis at the datum", MAKER)
    p = m.obj("POST", "LIGHTPOST")
    p.revolve([(PED_BASE[0][0], -PED_BURY)] + PED_BASE, PED_SIDES)
    p.tube([(0.0, PED_BASE[-1][1], 0.0), (0.0, H, 0.0)], list(PED_SHAFT_R), PED_SIDES, cap_end=False)
    ln = m.obj("LENS", "LIGHTS")
    if top == "acorn":
        p.revolve([(PED_SHAFT_R[1], H - 0.02)] + [(r, H + y) for r, y in ACORN[:3]], PED_SIDES)          # the fitter
        ln.revolve([(r, H + y) for r, y in ACORN[2:]], PED_SIDES)
        p.revolve([(r, H + y) for r, y in ACORN_CAP], PED_SIDES)                                      # the cap and finial
        centre, top_y = (0.0, H + 0.33, 0.0), H + ACORN_CAP[-1][1]
    elif top == "globe":
        p.revolve([(PED_SHAFT_R[1], H - 0.02), (0.085, H + 0.03), (0.085, H + 0.07)], PED_SIDES)        # the fitter
        cy = H + 0.07 + GLOBE_R * math.cos(math.asin(0.085 / GLOBE_R))
        a0 = -math.acos(0.085 / GLOBE_R)                              # the sphere starts on the fitter's rim
        prof = [(GLOBE_R * math.cos(a0 + (math.pi / 2 - a0) * i / GLOBE_LAT), cy + GLOBE_R * math.sin(a0 + (math.pi / 2 - a0) * i / GLOBE_LAT))
                for i in range(GLOBE_LAT + 1)]
        prof[-1] = (0.0, cy + GLOBE_R)
        ln.revolve(prof, PED_SIDES)
        centre, top_y = (0.0, cy, 0.0), cy + GLOBE_R
    else:
        raise ValueError(top)
    info = {"family": "pedestrian", "post_height_m": round(H, 4), "top": top, "top_of_fixture_m": round(top_y, 4),
            "lenses": [{"object": "LENS", "centre_m": [round(c, 4) for c in centre]}],
            "mast_radius_m": PED_BASE[0][0], "bury_m": PED_BURY}
    return m, info


def arterial(name: str, pole_ft: float, arm_ft: float, rise_ft: float, arms: int) -> tuple[Model, dict]:
    H, L, rise = pole_ft * FT, arm_ft * FT, rise_ft * FT
    mount = H + rise
    m = Model(f"streetlight_{name}", f"arterial post, {pole_ft:g} ft pole, {arms} x {arm_ft:g} ft bracket arm, flat LED head "
              "[typical, provisional class]", "metres, +x road-ward, +y up, origin = pole axis at the road datum", MAKER)
    p = m.obj("POST", "LIGHTPOST")
    r = lambda y: ART_BASE_R - TAPER * max(y, 0.0)
    p.tube([(0.0, -ART_BURY, 0.0), (0.0, 0.0, 0.0), (0.0, H, 0.0)], [r(0), r(0), r(H)], ART_SIDES)
    hl, hw, hd = HEAD
    lenses = []
    for j, sgn in enumerate((1, -1)[:arms], 1):
        yb = mount + LIFT                                             # the head's underside
        p.tube([(0.0, H - 0.45, 0.0), (sgn * (L - 0.35), yb + hd / 2, 0.0), (sgn * (L - hl / 2 + 0.05), yb + hd / 2, 0.0)],
               [0.042, 0.032, 0.030], 6, cap_end=False)
        p.tube([(0.0, H - 1.25, 0.0), (sgn * 0.55 * L, H - 0.45 + 0.55 * (rise + 0.45 + hd / 2) - 0.02, 0.0)], [0.022, 0.022], 5,
               cap_end=False)                                         # the brace under the bracket arm
        x0, x1 = sorted((sgn * (L - hl / 2), sgn * (L + hl / 2)))
        p.box((x0, yb, -hw / 2), (x1, yb + hd, hw / 2))
        lx0, lx1 = sorted((sgn * (L - LENS[0] / 2), sgn * (L + LENS[0] / 2)))
        ln = m.obj("LENS" if arms == 1 else f"LENS_{j}", "LIGHTS")
        ln.polygon([(lx0, mount, -LENS[1] / 2), (lx1, mount, -LENS[1] / 2), (lx1, mount, LENS[1] / 2), (lx0, mount, LENS[1] / 2)],
                   ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), (0.0, -1.0, 0.0))
        lenses.append({"object": ln.name, "centre_m": [round(sgn * L, 4), round(mount, 4), 0.0]})
    info = {"family": "arterial", "pole_height_m": round(H, 4), "arm_length_m": round(L, 4), "mounting_height_m": round(mount, 4),
            "arms": arms, "lenses": lenses, "mast_radius_m": round(r(0), 4), "bury_m": ART_BURY}
    return m, info


def build(name: str):
    c = dict(CLASSES[name])
    fam = c.pop("family")
    return pedestrian(name, **c) if fam == "pedestrian" else arterial(name, **c)


def outputs() -> dict[str, str]:
    out, classes = {}, {}
    for n in CLASSES:
        m, info = build(n)
        out[f"streetlight_{n}.obj"] = m.text()
        classes[n] = {"file": f"streetlight_{n}.obj", "params": CLASSES[n], **info, **m.summary()}
    spec = {
        "name": "streetlight_posts",
        "_doc": "ledger 0096 — street-light classes beside led_cobra, generated by tools/make_streetlight_posts.py. Frame: "
                "metres, +x road-ward, +y up, origin = pole axis at the datum. POST is the LIGHTPOST mesh, each LENS* object "
                "the LIGHTS mesh one CSP light is keyed on. Nothing here is placed on a track.",
        "provisional": "THE CLASS LIST IS PROVISIONAL: no survey has yet said which fixtures stand on Denver's lap (PLAN §4b). "
                       "Every dimension is [typical], not a Denver or Xcel Energy standard and not a measurement. A surveyed "
                       "class is a new row in the maker's CLASSES table.",
        "already_owned": "led_cobra (tools/make_streetlight_led.py): 35 ft Caltrans Type 21 pole, one or two 12 ft arms, cobra heads",
        "classes": classes,
    }
    out["streetlight_posts.json"] = json.dumps(spec, indent=1) + "\n"
    return out


if __name__ == "__main__":
    sys.exit(write_or_check(OUT, outputs(), sys.argv[1:], "streetlight-posts"))
