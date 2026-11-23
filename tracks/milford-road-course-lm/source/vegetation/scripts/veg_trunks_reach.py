"""Ledger 0100 item 4 (Kevin 2026-11-22, the tree collider reach: "Narrower", no number given): the trunk colliders
re-selected with a reach DERIVED from Milford's measured barrier lines instead of 0.1.3's 30 m [invented].

    python veg_trunks_reach.py <track dir> [--write [--line-doc TEXT]]

No car's stopping distance off this road is measured (NAIP 2022 resolves no run-off traces). What IS measured is where
the facility stands its own barriers: every W-beam and tyre wall of scenery.bespoke.rails is a line off NAIP 2022 (+-1 px),
and its standoff from the lane edge is the run-off the facility leaves in front of it. A car that leaves the road where
the run-off is widest reaches at most that far before the facility expects to catch it. So:

  REACH_M = the widest median standoff of any W-beam or tyre wall (kinds wbeam / tyres; the F1 screens are site fences,
            not run-off barriers) off the built lane edge, rounded UP to the next whole metre.

The lane edge is the 0.1.13 build's swept line (data/centerline.local.json) +- half its width, as the PC's own rail-to-lane
measurements (ledger 0091 rehearsal 3) and tests/tools/test_milford_finish_0100.py reproduce. A tree's distance to the
drivable surface is the least of: its lane-edge distance less the edge strip (STRIP_M, the 1KERB's widest p99 per 250 m on
the 0.1.5 OBJ, ledger 0092: the strip is paved and drivable), and its distance to any scenery.bespoke.pads outline (the ride
pad and the 19 run-off pads, drivable 1RUNOFF since 0.1.13; 0 inside one). Every planted tree (trees.lm.json, which since
ledger 0100 item 7 also holds the NAIP-only verge trees) within REACH_M of it gets a collider (trunks.json). --write
writes trunks.json; without it the counts are printed only.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

STRIP_M = 1.84                  # ledger 0092: the 0.1.5 gate OBJ's 1KERB p99 per 250 m, 1.73-1.84 m (the widest)
BARRIER_KINDS = ("wbeam", "tyres")


def meters_per_degree(lat0):
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat


class Lane:
    """the built lane edge: data/centerline.local.json +- half its width (scripts/geometry/circuit_start's frame)"""

    def __init__(self, cl):
        P = np.array(cl["points_xyz_m"], float)[:, [0, 2]]
        self.half = np.array(cl["widths_m"], float) / 2.0
        self.ax, self.az, bx, bz = P[:-1, 0], P[:-1, 1], P[1:, 0], P[1:, 1]
        self.dx, self.dz = bx - self.ax, bz - self.az
        self.L2 = np.where(self.dx ** 2 + self.dz ** 2 == 0, 1.0, self.dx ** 2 + self.dz ** 2)

    def edge_d(self, qx, qz):
        """signed distance to the lane edge (+ outside the road), numpy, chunked"""
        qx, qz = np.asarray(qx, float), np.asarray(qz, float)
        out = np.empty(len(qx))
        h0, h1 = self.half[:-1], self.half[1:]
        for k in range(0, len(qx), 256):
            x, z = qx[k:k + 256, None], qz[k:k + 256, None]
            t = np.clip(((x - self.ax) * self.dx + (z - self.az) * self.dz) / self.L2, 0, 1)
            out[k:k + 256] = (np.hypot(x - self.ax - t * self.dx, z - self.az - t * self.dz) - (h0 * (1 - t) + h1 * t)).min(1)
        return out


def densify(poly, step=0.5):
    out = []
    for a, b in zip(poly, poly[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out + [poly[-1]]


def barrier_standoffs(cfg, cl, lane):
    """{rail key: (kind, median standoff m)} for every W-beam / tyre wall, off the lane edge"""
    o = cl["origin"]
    m_lon, m_lat = meters_per_degree(o["lat"])
    out = {}
    for r in cfg["scenery"]["bespoke"]["rails"]:
        if r["kind"] not in BARRIER_KINDS:
            continue
        poly = densify([((p[0] - o["lon"]) * m_lon, (p[1] - o["lat"]) * m_lat) for p in r["polyline_lonlat"]])
        d = lane.edge_d([p[0] for p in poly], [p[1] for p in poly])
        out[r["key"]] = (r["kind"], float(np.median(d)))
    return out


def reach_m(standoffs):
    return float(math.ceil(max(v for _k, v in standoffs.values())))


def pad_rings(cfg, o):
    m_lon, m_lat = meters_per_degree(o["lat"])
    out = []
    for p in cfg["scenery"]["bespoke"].get("pads") or []:
        if "strip_lonlat" in p:
            ll = list(p["strip_lonlat"]["inner"]) + list(p["strip_lonlat"]["outer"])[::-1]
        elif "quad_lonlat" in p:
            ll = list(p["quad_lonlat"])
        else:
            continue
        out.append((p["key"], np.array([((a - o["lon"]) * m_lon, (b - o["lat"]) * m_lat) for a, b in ll], float)))
    return out


def ring_d(ring, qx, qz):
    """distance of each point to a polygon (0 inside), numpy"""
    qx, qz = np.asarray(qx, float), np.asarray(qz, float)
    A, B = ring, np.roll(ring, -1, axis=0)
    ex, ez = B[:, 0] - A[:, 0], B[:, 1] - A[:, 1]
    L2 = np.where(ex * ex + ez * ez == 0, 1.0, ex * ex + ez * ez)
    x, z = qx[:, None], qz[:, None]
    t = np.clip(((x - A[:, 0]) * ex + (z - A[:, 1]) * ez) / L2, 0, 1)
    d = np.hypot(x - A[:, 0] - t * ex, z - A[:, 1] - t * ez).min(1)
    inside = np.zeros(len(qx), bool)
    for (x1, z1), (x2, z2) in zip(A, B):
        c = ((z1 > qz) != (z2 > qz)) & (qx < x1 + (qz - z1) * (x2 - x1) / np.where(z2 == z1, 1e-12, z2 - z1))
        inside ^= c
    return np.where(inside, 0.0, d)


def drivable_d(cfg, cl, lane, lon, lat):
    o = cl["origin"]
    m_lon, m_lat = meters_per_degree(o["lat"])
    x = (np.asarray(lon) - o["lon"]) * m_lon
    z = (np.asarray(lat) - o["lat"]) * m_lat
    d = np.maximum(lane.edge_d(x, z) - STRIP_M, 0.0)
    for _key, ring in pad_rings(cfg, o):
        near = (np.abs(x - ring[:, 0].mean()) < 600) & (np.abs(z - ring[:, 1].mean()) < 600)
        if near.any():
            d[near] = np.minimum(d[near], ring_d(ring, x[near], z[near]))
    return d


def plan(track):
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    cl = json.loads((track / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    trees = json.loads((track / "source" / "vegetation" / "trees.lm.json").read_text(encoding="utf-8"))
    lane = Lane(cl)
    st = barrier_standoffs(cfg, cl, lane)
    reach = reach_m(st)
    pts = trees["points"]
    d = drivable_d(cfg, cl, lane, [p[0] for p in pts], [p[1] for p in pts])
    keep = [[p[0], p[1], p[3], round(float(dd), 1)] for p, dd in zip(pts, d) if dd <= reach]
    return {"reach_m": reach, "standoffs": st, "trunks": keep, "d": d, "n_trees": len(pts)}


def main():
    track = Path(sys.argv[1])
    res = plan(track)
    st, reach = res["standoffs"], res["reach_m"]
    widest = max(st, key=lambda k: st[k][1])
    print("[reach] barrier standoffs off the lane edge (median, m): "
          + ", ".join(f"{k} {v:.2f}" for k, (_kind, v) in sorted(st.items(), key=lambda t: -t[1][1])))
    print(f"[reach] REACH_M = ceil({st[widest][1]:.2f}) = {reach:.0f} m ({widest}); {len(res['trunks'])} of {res['n_trees']} "
          f"planted trees within it of the drivable surface (lane + {STRIP_M} m strip, every pad)")
    old = json.loads((track / "source" / "vegetation" / "trunks.json").read_text(encoding="utf-8"))
    print(f"[reach] trunks.json had {len(old['points'])} colliders")
    if "--write" in sys.argv:
        # ledger 0102: --line-doc names the swept line the plan was made on (0.1.15: GM's loop, predicted by
        # source/round2/predict_lines_0102.py); without it, round 1's wording
        line_doc = sys.argv[sys.argv.index("--line-doc") + 1] if "--line-doc" in sys.argv else "0.1.13's swept line"
        out = {"_source": (f"ledger 0100 item 4 (source/vegetation/scripts/veg_trunks_reach.py): the planted trees within {reach:.0f} m of "
                           f"the drivable surface (the lane edge of {line_doc} + the {STRIP_M} m edge strip, and every "
                           "scenery.bespoke.pads outline): [lon, lat, h_m, d_drivable_m]. The reach is DERIVED from measured lines, "
                           f"not a measured stopping distance: the widest median standoff of any W-beam or tyre wall off the lane "
                           f"edge ({widest} {st[widest][1]:.2f} m), rounded up. 0.1.3-0.1.13: 30 m [invented]"),
               "reach_m": reach,
               "points": res["trunks"]}
        (track / "source" / "vegetation" / "trunks.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print(f"[reach] wrote trunks.json: {len(res['trunks'])} colliders")


if __name__ == "__main__":
    main()
