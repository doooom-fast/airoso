"""Furniture pass 1's blocks (ledger 0085, 0.2.1) from buildings_lidar.py's read: one block per measured roof, the
grandstand as its measured tiers, in tools/author_bespoke_blend.py's blocks shape (a planned file, "auto": a footprint the
checks refuse is dropped and counted).

Per roof row of <read>.json (kind "roof", and the rows named in TAKE_TREES, a grey-roofed building whose mixed heights
read as a canopy):
  footprint_lonlat  the read's footprint (its minimum rectangle, or its outline) in lon / lat, the track's origin;
  wall_h_m          its points' median height over the lidar ground [measured: CO_Eastern_ElPaso_2018];
  roof_z_m          its median roof elevation in the scene frame [measured]: read by the author only for a block past the
                    built ground (an off-terrain far block), where it seats the roof;
  roof              NAIP 2023's colour over it, by class: WHITE when its median grey is over WHITE_MIN and its saturation
                    under 0.10, TAN when it is warm (red over blue by TAN_WARM or more), else DARK [measured class];
  skin              METAL for a building under TALL_M, TILTUP over it [invented: the fleet's two skins, CC0, for the steel
                    sheds and the concrete stands NAIP shows; no photo of the walls on disk].
The grandstand (GRANDSTAND_ID, the largest roof) is cut along its depth, from the track side back, into TIERS: each
band a block at the band's own median height (the seating rises 5.1 -> 19.5 m over 36 m, the suites block behind it stands
33.0 m).

    python tracks/pikes-peak/source/lidar/infield/plan_furniture.py <read.json> <workshop project> --out <plan.json>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GRANDSTAND_ID = 0
TAKE_TREES = {3: "the striped building by the pit road (grey roof, sat 0.07; its 3.7-12.6 m spread read it as a canopy)"}
TALL_M = 6.0           # [invented] a block over this is a concrete stand / tower, under it a steel shed
WHITE_MIN, TAN_WARM = 170.0, 12.0   # [invented] the roof class cuts on NAIP's 8-bit median RGB
TIERS = [(0, 6), (6, 12), (12, 18), (18, 24), (24, 30), (30, 36), (36, 57)]   # [invented] 6 m bands; the suites block whole
NAMES = {0: "grandstand", 1: "pit_building_south", 2: "pit_building_north", 3: "striped_building", 4: "sw_shed_a",
         5: "s_shed_a", 6: "sw_shed_b", 7: "infield_shed_a", 8: "infield_se_shed", 9: "sw_shed_c", 11: "s_shed_b",
         12: "infield_shed_b", 13: "sw_shed_d", 15: "pit_canopy", 17: "s_container_a", 18: "s_container_b",
         20: "kart_shed_a", 22: "kart_shed_b", 25: "se_container_a", 26: "se_container_b", 28: "far_se_shed",
         31: "far_ne_shed"}


def roof_class(rgb, sat):
    r, g, b = rgb
    if (r + g + b) / 3.0 > WHITE_MIN and sat < 0.10:
        return "white"
    if r - b >= TAN_WARM:
        return "tan"
    return "dark"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("read")
    ap.add_argument("project")
    ap.add_argument("--lidar", default="D:/k10-scratch/pp_lidar/infield.npz")
    ap.add_argument("--dem", default="D:/k10-scratch/pp_lidar/infield_dem.npz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rd = json.loads(Path(a.read).read_text(encoding="utf-8"))
    loc = json.loads((Path(a.project) / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0, elev0 = float(loc["origin"]["lon"]), float(loc["origin"]["lat"]), float(loc["origin"]["elev_m"])
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)

    def ll(p):
        return [round(lon0 + p[0] / m_lon, 8), round(lat0 + p[1] / m_lat, 8)]
    flight = "CO_Eastern_ElPaso_2018 (lidar 2018) against NAIP 2023-09-20"
    out = []
    for r in rd["rows"]:
        if r["kind"] == "pole" or (r["kind"] != "roof" and r["id"] not in TAKE_TREES):
            continue
        if r["id"] not in NAMES:
            continue
        name = NAMES[r["id"]]
        roof = roof_class(r["naip_rgb"], r["naip_sat"])
        if r["id"] == GRANDSTAND_ID:
            L = np.load(a.lidar)
            D = np.load(a.dem)
            dem, e0, n0 = D["dem"], float(D["e0"]), float(D["n0"])
            m = L["cls"] == 1
            E, N, Z = L["e"][m], L["n"][m], L["z"][m] - elev0
            i = np.clip((E - e0).astype(int), 0, dem.shape[1] - 1)
            j = np.clip((N - n0).astype(int), 0, dem.shape[0] - 1)
            H = Z - dem[j, i]
            R = np.array(r["footprint_en"])
            a0, b0, c0 = R[0], R[1], R[2]
            if np.hypot(*(b0 - a0)) < np.hypot(*(c0 - b0)):
                a0, b0, c0 = R[1], R[2], R[3]
            u = (b0 - a0) / np.hypot(*(b0 - a0))
            v = (c0 - b0) / np.hypot(*(c0 - b0))
            Lu = float(np.hypot(*(b0 - a0)))
            lap = np.array([[p[0], p[2]] for p in loc["points_xyz_m"]])
            if np.min(np.hypot(*(lap - (a0 + u * Lu / 2)).T)) > np.min(np.hypot(*(lap - (a0 + u * Lu / 2 + v * 50)).T)):
                raise SystemExit("plan_furniture: the grandstand's v = 0 edge is not its track side")
            P = np.c_[E, N] - a0
            pu, pv = P @ u, P @ v
            for k, (v0, v1) in enumerate(TIERS):
                s = (pu >= 0) & (pu <= Lu) & (pv >= v0) & (pv < v1)
                h = float(np.median(H[s]))
                rz = float(np.median(Z[s]))
                ring = [a0 + v * v0, a0 + u * Lu + v * v0, a0 + u * Lu + v * v1, a0 + v * v1]
                tier = "the suites block" if k == len(TIERS) - 1 else f"seating tier {k + 1} of {len(TIERS) - 1}"
                out.append({"key": f"{name}_{k}", "footprint_lonlat": [ll(q) for q in ring], "wall_h_m": round(h, 2),
                            "roof_z_m": round(rz, 2), "skin": "tiltup", "roof": "dark" if k < len(TIERS) - 1 else roof,
                            "_source": (f"the west grandstand, {tier}: v {v0}-{v1} m back from its track-side edge, "
                                        f"{Lu:.1f} m long (buildings_lidar.py row {r['id']}, its minimum rectangle); "
                                        f"wall_h {h:.2f} m = the band's median height over the lidar ground of {int(s.sum())} "
                                        f"points [measured, {flight}]; skin tilt-up [invented: the fleet's concrete]; "
                                        + ("roof dark: the seating's own top [invented]" if k < len(TIERS) - 1
                                           else f"roof {roof} [measured class, NAIP median RGB {r['naip_rgb']}]"))})
            continue
        h = float(r["hag_m"][1])
        out.append({"key": name, "footprint_lonlat": [ll(q) for q in r["footprint_en"]], "wall_h_m": round(h, 2),
                    "roof_z_m": r["roof_z_m"], "skin": "tiltup" if h > TALL_M else "metal", "roof": roof,
                    "_source": (f"buildings_lidar.py row {r['id']} ({r['shape']}, {r['rect_m'][0]} x {r['rect_m'][1]} m, "
                                f"{r['area_m2']} m2" + (f"; {TAKE_TREES[r['id']]}" if r["id"] in TAKE_TREES else "")
                                + f"); wall_h {h:.2f} m = its median height over the lidar ground (p10 {r['hag_m'][0]}, "
                                f"p95 {r['hag_m'][2]}) [measured, {flight}]; skin {'tilt-up' if h > TALL_M else 'metal'} "
                                f"[invented: the fleet's skins]; roof {roof} [measured class, NAIP median RGB {r['naip_rgb']}]")})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[plan] {len(out)} blocks -> {a.out}")
    for b in out:
        print(f"  {b['key']:24s} {b['wall_h_m']:6.2f} m  {b['skin']:7s} {b['roof']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
