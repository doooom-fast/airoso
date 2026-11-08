"""The written trees against the BUILT track (L5; ledger 0082 vegetation pass). Not a chain gate (Milford has no race layout,
so tools/verify_race.py --scenery-only does not run); run after the ship, on the workshop:

    python veg_verify.py <project> [--json out.json]

Reads build/<slug>/extension/trees/trees.txt (kn5 frame: x, y, -z) and data/track.obj (the gate OBJ, engine frame). Checks:
  - no trunk on, or within corridor_margin_m (track.config.json) of, a paved face (1ROAD*, 1KERB*, PADAPRON*);
  - no trunk within 1.0 m (tools/make_treefx.py BUILT_BUILDING_CLEAR_M) of a wall or building (1WALL*, BUILDING*, ROOFTOP*,
    FARBLOCK*, GUARDRAIL*), its ghost trunk colliders excepted;
  - every 1WALL_GHOST_TRUNK collider stands on a written tree (within 0.5 m), and every written tree nearer the built paved
    surface than the collider reach (veg_plan.COLLIDER_REACH_M) less the plan grid's own error (veg_plan.HALF_DIAG_M: the
    plan measured on 2 m cells) has one; the trees in that last 1.41 m band without one are listed, not failed.
Exit 1 on any failure.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from veg_common import obj_surfaces  # noqa: E402
from veg_plan import COLLIDER_REACH_M, HALF_DIAG_M  # noqa: E402

TREE_RE = re.compile(r"^\s*tree:\s*([^;]+);\s*pos\s*=\s*([-0-9.eE+]+)\s*,\s*([-0-9.eE+]+)\s*,\s*([-0-9.eE+]+)")


def seg_dist(P, tris):
    """the plan distance from each point to the nearest triangle (inside = 0), brute force in 200 m tiles"""
    out = np.full(len(P), np.inf)
    if not len(tris):
        return out
    A, B, C = tris[:, 0], tris[:, 1], tris[:, 2]
    lo, hi = tris.min(axis=1), tris.max(axis=1)
    for k, p in enumerate(P):
        near = np.all((lo - 40 <= p) & (p <= hi + 40), axis=1)
        if not near.any():
            continue
        a, b, c = A[near], B[near], C[near]
        best = np.inf
        for u, v in ((a, b), (b, c), (c, a)):
            d = v - u
            L2 = (d * d).sum(1)
            t = np.clip(((p - u) * d).sum(1) / np.where(L2 > 0, L2, 1), 0, 1)
            q = u + t[:, None] * d
            best = min(best, float(np.sqrt(((p - q) ** 2).sum(1)).min()))
        d1 = (b[:, 0] - a[:, 0]) * (p[1] - a[:, 1]) - (p[0] - a[:, 0]) * (b[:, 1] - a[:, 1])
        d2 = (c[:, 0] - b[:, 0]) * (p[1] - b[:, 1]) - (p[0] - b[:, 0]) * (c[:, 1] - b[:, 1])
        d3 = (a[:, 0] - c[:, 0]) * (p[1] - c[:, 1]) - (p[0] - c[:, 0]) * (a[:, 1] - c[:, 1])
        inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        out[k] = 0.0 if inside.any() else best
    return out


def main():
    proj = Path(sys.argv[1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    slug = cfg["slug"]
    margin = float(cfg["scenery"]["corridor_margin_m"])
    txt = (proj / "build" / slug / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8")
    trees = np.array([(float(m.group(2)), -float(m.group(4))) for m in map(TREE_RE.match, txt.splitlines()) if m])
    srf = obj_surfaces(proj / "data" / "track.obj", ("1ROAD", "1KERB", "PADAPRON", "1WALL_GHOST_TRUNK", "1WALL", "BUILDING",
                                                     "ROOFTOP", "FARBLOCK", "GUARDRAIL"))
    paved = np.concatenate([srf[k] for k in ("1ROAD", "1KERB", "PADAPRON") if len(srf[k])])
    walls = np.concatenate([srf[k] for k in ("1WALL", "BUILDING", "ROOFTOP", "FARBLOCK", "GUARDRAIL") if len(srf[k])])
    dp = seg_dist(trees, paved)
    dw = seg_dist(trees, walls)
    trunk_v = srf["1WALL_GHOST_TRUNK"].reshape(-1, 2) if len(srf["1WALL_GHOST_TRUNK"]) else np.zeros((0, 2))
    # one collider = 8 sides; its centre = the mean of its vertices, clustered by 1 m
    centres = []
    for v in trunk_v:
        for c in centres:
            if math.dist(c[0], v) < 1.0:
                c[1].append(v)
                break
        else:
            centres.append([tuple(v), [v]])
    centres = np.array([np.mean(c[1], axis=0) for c in centres]) if centres else np.zeros((0, 2))
    orphan = 0
    for c in centres:
        if not len(trees) or np.sqrt(((trees - c) ** 2).sum(1)).min() > 0.5:
            orphan += 1
    has = np.array([bool(len(trunk_v)) and float(np.sqrt(((trunk_v - t) ** 2).sum(1)).min()) < 0.5 for t in trees], dtype=bool)
    reach = (dp <= COLLIDER_REACH_M) & ~has
    missing = int((reach & (dp < COLLIDER_REACH_M - HALF_DIAG_M)).sum())
    band = sorted(round(float(x), 2) for x in dp[reach & (dp >= COLLIDER_REACH_M - HALF_DIAG_M)])
    bad_p = int((dp < margin).sum())
    bad_w = int((dw < 1.0).sum())
    rep = {"trees": int(len(trees)), "trunk_colliders": int(len(centres)), "orphan_colliders": orphan,
           "nearest_paved_m": round(float(dp.min()), 2) if len(dp) else None, "within_margin_of_paved": bad_p,
           "nearest_wall_m": round(float(dw.min()), 2) if len(dw) else None, "within_1m_of_wall": bad_w,
           "trees_within_reach_of_paved": int((dp <= COLLIDER_REACH_M).sum()), "collider_reach_m": COLLIDER_REACH_M,
           "within_reach_no_collider": missing, "reach_band_no_collider_m": band, "corridor_margin_m": margin,
           "verdict": "PASS" if not (bad_p or bad_w or orphan or missing) else "FAIL"}
    print(json.dumps(rep))
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rep, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
