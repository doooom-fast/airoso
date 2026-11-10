"""A lap junction's pad DECLARATION from where it is (ledger 0079 round B, Sand Creek's six authored junctions): node, the
lap's two cut rows and the junction box, for tools/draft_pad_outline.py (the measurement, lidar) and tools/lm_pads_blend.py
(the author). Nothing here is measured; it says WHERE to measure, by rule:

    node   the lap vertex nearest the plan's node_xz (local E, N on the project's data/centerline.local.json)
    cuts   the lap vertices CUT_M of arc either side of the node (rule 4: a straight transverse cut 5-30 m from the junction
           centre, past the crossing pavement edge) [CUT_M invented within that rule]
    box    a star polygon round the node: each lap cut's two ends (the lane's half width + BOX_PAD_M out) and, for every grid
           street with a point within ARM_NEAR_M of the node, the two points BOX_PAD_M past its edges where it crosses
           the circle of radius reach_m round the node (reach_m = the lap's half width at the node + the corner's curb
           return + ARM_PAST_M) [the pads invented]; ordered by angle round the node
    arms   those streets, with the circle crossing as the arm's cut (the author's business; recorded for it)

The plan is track.config.json lm_pads.plan: [{"id", "node_xz": [E, N], "curb_return_m", "cut_m"?, "half_m"?}]. --write puts
the declarations into lm_pads.pads (keeping lm_pads.source), each with its provenance; without it, prints them.

    python tools/pad_boxes.py <project-or-track> [--write]

Reads data/centerline.local.json and data/connectors.local.json (.pre-trim when present: the streets as drawn).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

CUT_M = 30.0        # [invented, within rule 4's 5-30 m] arc from the node to each lap cut
BOX_PAD_M = 3.0     # [invented] the box this far past a lane's edge
ARM_NEAR_M = 30.0   # [invented] a street with a point this close to the node is one of its arms
ARM_PAST_M = 6.0    # [invented] the arm cut this far past the curb return


def build(proj: Path):
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    plan = ((cfg.get("lm_pads") or {}).get("plan")) or []
    data = proj / "data"
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    P = [(p[0], p[2]) for p in loc["points_xyz_m"]]
    W = loc["widths_m"]
    cs = data / "connectors.local.json.pre-trim"
    if not cs.exists():
        cs = data / "connectors.local.json"
    conns = json.loads(cs.read_text(encoding="utf-8")).get("connectors", []) if cs.exists() else []
    arc = [0.0]
    for a, b in zip(P, P[1:]):
        arc.append(arc[-1] + math.dist(a, b))
    out = []
    for p in plan:
        nx, nz = p["node_xz"]
        node = min(range(len(P)), key=lambda i: math.hypot(P[i][0] - nx, P[i][1] - nz))
        cut = float(p.get("cut_m", CUT_M))
        k0 = max(i for i in range(node + 1) if arc[node] - arc[i] >= cut) if arc[node] >= cut else 0
        # the lap seam (L13): a cut never wraps past the last unique vertex; a pad over the seam is cut short there and says so
        k1 = min((i for i in range(node, len(P) - 1) if arc[i] - arc[node] >= cut), default=len(P) - 2)
        if arc[k1] - arc[node] < cut:
            print(f"[pad-boxes] {p['id']}: the out cut stops at the lap seam, {arc[k1] - arc[node]:.0f} m past the node (not {cut:.0f})")
        c0, c1 = P[node]
        hw = W[node] / 2.0
        reach = hw + float(p.get("curb_return_m", 0.0)) + ARM_PAST_M
        box = []
        for k in (k0, k1):
            a, b = P[max(k - 1, 0)], P[min(k + 1, len(P) - 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, tz) or 1.0
            ox, oz = -tz / L, tx / L
            d = W[k] / 2.0 + BOX_PAD_M
            box += [(P[k][0] + ox * d, P[k][1] + oz * d), (P[k][0] - ox * d, P[k][1] - oz * d)]
        arms = []
        for c in conns:
            pts = [(q[0], q[2]) for q in c["points_xyz_m"]]
            dn = [math.hypot(x - c0, z - c1) for x, z in pts]
            if min(dn) > ARM_NEAR_M:
                continue
            j = dn.index(min(dn))
            outside = dn[j] >= reach                  # the street stops short of the circle: its nearest point is the cut
            for step in (1, -1):                      # walk away from the node both ways along the street
                i = j
                if outside:
                    if not 0 <= j + step < len(pts):
                        continue
                    ax, az = pts[j]
                    bx, bz = pts[j + step]
                else:
                    while 0 <= i + step < len(pts) and dn[i] < reach:
                        i += step
                    if dn[i] < reach or i == j:
                        continue
                    ax, az = pts[i]
                    bx, bz = pts[i - step]
                tx, tz = ax - bx, az - bz
                L = math.hypot(tx, tz) or 1.0
                ox, oz = -tz / L, tx / L
                w = c["widths_m"][i] / 2.0 + BOX_PAD_M
                box += [(ax + ox * w, az + oz * w), (ax - ox * w, az - oz * w)]
                arms.append({"connector": c["name"], "cut": [[round(ax + ox * w, 2), round(az + oz * w, 2)],
                                                             [round(ax - ox * w, 2), round(az - oz * w, 2)]]})
                if outside:
                    break                             # one cut for a street that only reaches the circle
        box.sort(key=lambda q: math.atan2(q[1] - c1, q[0] - c0))
        out.append({"id": p["id"], "node": node, "cuts": [k0, k1], "box": [[round(x, 2), round(z, 2)] for x, z in box],
                    "arms": arms, "half_m": float(p.get("half_m", max(45.0, reach + 15.0, cut + 15.0))),
                    "source": {"kind": "lidar_ept", "ept": "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept.json"},
                    "edge": "shoulder",
                    "_by": f"tools/pad_boxes.py from lm_pads.plan {p['id']}: node v{node} nearest {p['node_xz']}, cuts {cut:.0f} m of "
                           f"arc either side, box reach {reach:.1f} m (half width {hw:.1f} + curb return {p.get('curb_return_m', 0)} + "
                           f"{ARM_PAST_M}) [rule, invented pads], {len(arms)} street arm(s)"})
    return cfg, out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    proj = Path(argv[0])
    cfg, pads = build(proj)
    for d in pads:
        print(f"[pad-boxes] {d['id']}: node v{d['node']}, cuts {d['cuts']}, {len(d['box'])} box points, arms "
              f"{[a['connector'] for a in d['arms']]}, window {d['half_m']} m")
    if write:
        cfg.setdefault("lm_pads", {})["pads"] = pads
        (proj / "track.config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[pad-boxes] wrote {len(pads)} declaration(s) into lm_pads.pads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
