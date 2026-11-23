"""THE FULL LAYOUT'S FORK AND MERGE AS MEASURED PADS (ledger 0097 round 3): each junction's OUTLINE off NAIP 2023 0.3 m, the
record tools/lm_pads_blend.py builds from (source/pads/<id>.json, the shape tools/draft_pad_outline.py and Pikes Peak's
junction_pads.py write).

Why pads: the north loop leaves the West lap at a fast Y (High Plains Drifter runs straight on into To Hell On A Bobsled while
the West course bends right): the two roads' outer edges are one line there, so no lateral line of the connector crosses the
host's edge and the mitre weld cannot build it (tools/weld_mouths_blend.py, round 3's first try: "a lateral line stops > 25.0 m
short of the host edge"). NAIP shows both junctions as one continuous pavement (the fork's flare and gore; the merge's
bellmouth and its kerbed inside corner), so each is built as Pikes Peak's and Sand Creek's are: one deck out to its measured
outline, the lap cut at two of its own rows, the north loop welded in as an arm at the box edge (lm_pads.arms "streets",
route.street_junctions.pad_arms).

THE OUTLINE, on draft_pad_outline's GRID_M grid round the pad's node: a cell is PAVEMENT when the 0.3 m crop's ground-ness
(source/edges/measure_widths.py groundness: prairie, dirt and the draws read high; asphalt, its paint and the kerbs' blue /
white low) is under the threshold midway between the lap's own lane between the cuts and the verge (the cells more than
VERGE_M off both roads); then closed over 1.25 m and opened over 0.75 m (draft_pad_outline's), holes under HOLE_MAX_M2 filled,
both roads' ribbons united in (the lap's between the cuts, the connector's inside the box: the deck must carry both lanes),
clipped to the declared box, split at the lap's two cuts (drawn LANE_CUT_M past the lap's lane, not draft_pads' 30 m, so the
out-cut never crosses the other road) and the box's edges, the node's component traced, smoothed and resampled (draft_pads
helpers, draft_pad_outline's numbers).
THE DECK: none measured (no lidar over either junction on disk): every node None, and the pad is declared
lm_pads.deck.fill "membrane" (the lap's own ribbon surface and the arm row exact, the paving between them the smoothest surface
that meets both).

    python measure_pads.py <workshop project> --out <tracks/high-plains-lm/source/pads> [--id FORK]

<workshop project> is a workshop the port was drafted into (after build_loop_blend: data/centerline.local.json is the line
lm_pads cuts, data/connectors.local.json.pre-trim the connector); its track.config.json lm_pads.pads are the declarations.
Writes <out>/<id>.json and <id>.png. Numbers marked [invented] are sampling choices.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
AIROSO = HERE.parents[3]
sys.path.insert(0, str(AIROSO))
sys.path.insert(0, str(HERE.parent / "edges"))
from tools import draft_pads as dp  # noqa: E402
from tools import draft_pad_outline as dpo  # noqa: E402
import measure_widths as mw  # noqa: E402

CROP = HERE.parent / "road_wear" / "naip_2023_030_hp.png"
VERGE_M = 4.0        # [invented] a verge cell stands this far past both roads' lane edges
LANE_IN_M = 1.0      # [invented] a lane cell stands this far inside the lap's lane edge
HOLE_MAX_M2 = 6.0    # [invented] (Pikes Peak's) a non-pavement hole smaller than this is paint or a mark, filled
LANE_CUT_M = 3.0     # [invented] a lap cut is drawn this far past the lap's lane edge each side


def lap_cut_short(loc, k, node):
    c = dp.lap_cut(loc["points_xyz_m"], k, node)
    half = float(loc["widths_m"][k]) / 2.0 + LANE_CUT_M
    p, (nx, ny) = c["p"], c["n"]
    ax, ay = -ny, nx                                   # along the cut (the lap's normal)
    return dict(c, a=(p[0] - ax * half, p[1] - ay * half), b=(p[0] + ax * half, p[1] + ay * half))


def ribbon_mask(P, W, k0, k1, gx, gy, pad=0.0):
    out = np.zeros(gx.shape, bool)
    for k in range(k0, k1):
        out |= dp.segment_band(P[k], P[k + 1], gx, gy, max(W[k], W[k + 1]) / 2.0 + pad)
    return out


def measure(d, loc, conn, naip, out_dir: Path):
    pid, node = d["id"], d["node"]
    P = [(p[0], p[2]) for p in loc["points_xyz_m"]]
    W = [float(w) for w in loc["widths_m"]]
    CP = [(p[0], p[2]) for p in conn["points_xyz_m"]]
    CW = [float(w) for w in conn["widths_m"]]
    cE, cN = P[node]
    half = float(d.get("half_m", 60.0))
    G = dpo.GRID_M
    n = int(round(2 * half / G))
    xs = cE - half + (np.arange(n) + 0.5) * G
    ys = cN + half - (np.arange(n) + 0.5) * G
    gx, gy = np.meshgrid(xs, ys)
    g = mw.groundness(naip.rgb(gx, gy))
    k0, k1 = sorted(d["cuts"])
    lane = ribbon_mask(P, [w - 2 * LANE_IN_M for w in W], k0, k1, gx, gy)
    near_lap = ribbon_mask(P, W, max(0, k0 - 40), min(len(P) - 1, k1 + 40), gx, gy, VERGE_M)
    near_conn = ribbon_mask(CP, CW, 0, len(CP) - 1, gx, gy, VERGE_M)
    on, off = float(np.nanmedian(g[lane])), float(np.nanmedian(g[~near_lap & ~near_conn]))
    thr = (on + off) / 2.0
    mask = np.nan_to_num(g, nan=1e3) < thr
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    lab, k = ndimage.label(~mask)
    if k:
        sizes = ndimage.sum(np.ones_like(mask), lab, index=np.arange(1, k + 1))
        edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        small = [q + 1 for q, s in enumerate(sizes) if s * G * G < HOLE_MAX_M2 and (q + 1) not in edge]
        mask |= np.isin(lab, small)
    measured_cells = int(mask.sum())
    box = d["box"]
    inbox = dp.in_ring_grid(box, gx, gy)
    ribbon = ribbon_mask(P, W, k0, k1, gx, gy)
    cribbon = ribbon_mask(CP, CW, 0, len(CP) - 1, gx, gy) & inbox
    united_lap = int((ribbon & ~mask).sum())
    united_conn = int((cribbon & ~mask & ~ribbon).sum())
    cuts = [lap_cut_short(loc, kk, node) for kk in d["cuts"]]
    sealed = [dp.sealed_cut((box[i - 1], box[i]), (cE, cN)) for i in range(len(box))]
    keep = (mask & inbox) | ribbon | cribbon
    for c in cuts:
        keep &= ~dp.segment_band(c["a"], c["b"], gx, gy, dpo.BARRIER_W_M)
    for c in sealed:
        keep &= ~(dp.segment_band(c["a"], c["b"], gx, gy, dpo.BARRIER_W_M) & ~ribbon)
    lab, _ = ndimage.label(keep)
    ci = cj = int(half / G)
    if not lab[ci, cj]:
        raise SystemExit(f"measure_pads {pid}: the node is not on pavement in the mask")
    region = lab == lab[ci, cj]
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    ring = dp.smooth_ring(ring, dpo.SMOOTH_M, keep_on=list(cuts + sealed), pin=cuts)
    ring = dp.resample_ring(ring, dpo.STEP_M)
    bx0, bx1 = min(p[0] for p in ring) - 2.0, max(p[0] for p in ring) + 2.0
    by0, by1 = min(p[1] for p in ring) - 2.0, max(p[1] for p in ring) + 2.0
    C = dpo.DECK_CELL_M
    nx, ny = int(math.ceil((bx1 - bx0) / C)) + 1, int(math.ceil((by1 - by0) / C)) + 1
    area = abs(sum(ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1] for i in range(len(ring)))) / 2.0
    rec = {
        "id": pid, "node": node, "cuts": d["cuts"], "sealed": d.get("sealed") or [],
        "outline_en": [[round(x, 3), round(y, 3)] for x, y in ring],
        "outline_flags_paint": [],
        "deck": {"e0": round(bx0, 3), "n0": round(by0, 3), "cell_m": C, "nx": nx, "ny": ny, "y": [[None] * nx for _ in range(ny)],
                 "_doc": "none measured (no lidar over the junction on disk): lm_pads.deck.fill \"membrane\" builds the deck"},
        "ribbon_union_m2": round((united_lap + united_conn) * G * G, 1),
        "area_m2": round(area, 1),
        "source": {"kind": "naip", "naip": {"item": naip_item(), "crop": "source/road_wear/naip_2023_030_hp.png"},
                   "groundness_lane_median": round(on, 1), "groundness_verge_median": round(off, 1),
                   "threshold": round(thr, 1), "measured_cells": measured_cells, "window_half_m": half,
                   "united_m2": {"lap": round(united_lap * G * G, 1), "connector": round(united_conn * G * G, 1)},
                   "method": "tracks/high-plains-lm/source/full/measure_pads.py (NAIP 2023 0.3 m ground-ness, measure_widths' "
                             "rule; no lidar)"},
        "uncertainty_m": {"outline": 0.45},
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pid}.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    # the picture: NAIP dimmed, the kept pavement lit, the outline yellow, the cuts green, the box red, the arms cyan
    rgb = np.nan_to_num(naip.rgb(gx, gy)) * 0.5
    rgb[region] = rgb[region] * 0.5 + 110.0
    S = 2
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((n * S, n * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)

    def px(x, y):
        return ((x - (cE - half)) / G * S, ((cN + half) - y) / G * S)
    b = [px(*q) for q in box]
    dr.line(b + [b[0]], fill=(255, 40, 40), width=2)
    for a in d.get("arms") or []:
        dr.line([px(*a["cut"][0]), px(*a["cut"][1])], fill=(0, 255, 255), width=3)
    for c in cuts:
        dr.line([px(*c["a"]), px(*c["b"])], fill=(0, 255, 0), width=3)
    r_ = [px(*q) for q in ring]
    dr.line(r_ + [r_[0]], fill=(255, 230, 0), width=2)
    dr.text((6, 6), f"{pid}: {len(ring)} outline points, {area:.0f} m2, ground-ness threshold {thr:.1f}", fill=(255, 255, 255))
    img.save(out_dir / f"{pid}.png")
    print(f"[measure_pads] {pid}: {len(ring)} outline points, {area:.0f} m2, ground-ness lane {on:.1f} / verge {off:.1f} -> "
          f"{thr:.1f}; united lap {rec['source']['united_m2']['lap']} m2, connector {rec['source']['united_m2']['connector']} m2 "
          f"-> {out_dir / (pid + '.json')}")
    return rec


def naip_item():
    return json.loads((CROP.with_suffix(".json")).read_text(encoding="utf-8"))["item"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", action="append", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decls = (cfg.get("lm_pads") or {}).get("pads") or []
    if not decls:
        raise SystemExit("measure_pads: the workshop's track.config.json declares no lm_pads.pads")
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pre = proj / "data" / "connectors.local.json.pre-trim"
    src = pre if pre.exists() else proj / "data" / "connectors.local.json"
    conns = {c["name"]: c for c in json.loads(src.read_text(encoding="utf-8"))["connectors"]}
    naip = mw.Naip(CROP, json.loads(CROP.with_suffix(".json").read_text(encoding="utf-8")), loc["origin"])
    for d in decls:
        if a.id and d["id"] not in a.id:
            continue
        arm = (d.get("arms") or [{}])[0].get("connector")
        if arm not in conns:
            raise SystemExit(f"measure_pads {d['id']}: its arm {arm!r} is not a connector of {src.name}")
        measure(d, loc, conns[arm], naip, Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
