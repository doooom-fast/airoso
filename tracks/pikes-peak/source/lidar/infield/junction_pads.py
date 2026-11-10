"""THE TWO OVAL JUNCTIONS AS MEASURED PADS (ledger 0085, Pikes Peak 0.2.0): each pad's OUTLINE and DECK, the record
tools/lm_pads_blend.py builds from (source/pads/<id>.json, tools/draft_pad_outline.py's shape).

Why: the infield road leaves the oval at the NE junction and rejoins it at the NW one, across the bank's knee and its
apron. Welded as a three-line connector ribbon onto that (tools/weld_mouths_blend.py) it could not follow the bank, the
knee and the apron at once (NW approach 3.08 %/m, an 8.9 cm step; ground over the lane where the race lap's join crosses
the unpaved corner wedges). NAIP 2023 shows the real junctions as one continuous pavement: the lap's lane, the apron, the
diverge's wedge and gore, the infield road, the corners round (NE: a grass island's tip; NW: a kerbed bend and the NE
branch road). So each junction is built the way the Lariat's mouths and Sand Creek's junctions are: one deck out to its
measured outline, on its measured ground, the lap cut at two of its own rows, the infield road welded in as an arm
(lm_pads.arms "streets"), the branch the build does not complete closed by the box.

THE OUTLINE, on a GRID_M grid round the pad's node (draft_pad_outline.py's numbers): a cell is PAVEMENT when
  * NAIP 2023 0.3 m (the crop tracks/pikes-peak/source/road-course/naip_2023_030.json describes, shifted by that
    folder's registration.json as every NAIP read there is) reads grey there: saturation (max - min) / max under SAT_MAX,
    max between MX_MIN and MX_MAX; and
  * the lidar's ground points within MEAN_R_M read asphalt-dark: their mean intensity under the threshold midway between
    the lap's own lane (class-2 points within 2 m of the line between the cuts) and the vegetation (points where NAIP
    saturation is over VEG_SAT), or there is no lidar point within MEAN_R_M (NAIP alone then).
  Measured at these junctions (2026-11-09): asphalt sat 0.02-0.06, intensity 1,700-2,300; the brownish sealed patches
  (NE north of the island, NW between the road and the branch) sat 0.135, intensity 1,140-1,230 (pavement); grass sat
  0.27-0.33, intensity 3,660-4,200; the infield's pale dirt sat 0.11 (grey enough) but intensity 3,360 (not pavement).
  or NAIP reads a red / white kerb there (road-course/pave_mask.py's rule: the rumble strips are paved and driven;
  their paint reads lidar-bright).
  Then closed over 1.25 m and opened over 0.75 m (draft_pad_outline's), holes under HOLE_MAX_M2 filled (paint, a car; a
  grass island is kept), the lap's lane between the cuts united in, clipped to the declared box and the lap's two cuts,
  the node's component traced, smoothed and resampled (draft_pads helpers, draft_pad_outline's numbers).
THE DECK: draft_pad_outline's: a DECK_CELL_M grid over the outline, each node the plane through the class-2 ground
  points within DECK_R_M whose intensity is under the threshold (never the verge's), in the track's local frame
  (lidar z - origin elev_m, the frame infield_dem.npz and the line's y are in).

    python tracks/pikes-peak/source/lidar/infield/junction_pads.py <workshop project> --naip <crop png> \
        --lidar D:/k10-scratch/pp_lidar/infield.npz --out tracks/pikes-peak-lm/source/pads [--id NE]

<workshop project> is a workshop the port was drafted into: its track.config.json lm_pads.pads are the declarations and
its data/centerline.local.json (after build_loop_blend: the line lm_pads cuts) the lap. Writes <out>/<id>.json and
<id>.png. Numbers marked [invented] are sampling choices (fleet/GATES-CHANGELOG.md, 0085).
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
from scipy.spatial import cKDTree

AIROSO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(AIROSO))
from tools import draft_pads as dp  # noqa: E402
from tools import draft_pad_outline as dpo  # noqa: E402

RC = AIROSO / "tracks" / "pikes-peak" / "source" / "road-course"
SAT_MAX = 0.16       # [invented] grey: asphalt 0.02-0.06 and the sealed patches 0.135 under it, grass 0.27+ and dirt 0.17+ over
MX_MIN, MX_MAX = 40.0, 225.0   # [invented] grey's brightness: a shadow under 40, lane paint and the wall's caps over 225
VEG_SAT = 0.22       # [invented] the vegetation the intensity threshold is set against: NAIP saturation over this
HOLE_MAX_M2 = 6.0    # [invented] a non-pavement hole inside the pavement smaller than this is paint or a car, filled
HALF_DEFAULT_M = 60.0


class Crop:
    """the NAIP crop as saturation / max arrays, read at true ENU (the registration shift applied)"""

    def __init__(self, png: Path, origin):
        meta = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
        ref = json.loads((RC / "naip_2023_030.json").read_text(encoding="utf-8"))
        if meta["corners"] != ref["corners"] or meta["w"] != ref["w"] or meta["h"] != ref["h"] or meta["item"] != ref["item"]:
            raise SystemExit(f"junction_pads: {png} is not the crop {RC / 'naip_2023_030.json'} describes")
        reg = json.loads((RC / "registration.json").read_text(encoding="utf-8"))
        self.shift = np.array(reg["shift_en_m"], float) if reg.get("apply") else np.zeros(2)
        Image.MAX_IMAGE_PIXELS = None
        im = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
        self.rgb = im
        self.mx = im.max(-1)
        self.sat = (self.mx - im.min(-1)) / np.maximum(self.mx, 1.0)
        self.W, self.N, self.E, self.S = meta["corners"]
        self.wpx, self.hpx = meta["w"], meta["h"]
        self.item = meta["item"]
        self.lon0, self.lat0 = float(origin["lon"]), float(origin["lat"])
        phi = math.radians(self.lat0)
        self.m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
        self.m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)

    def ij(self, e, n):
        e = np.asarray(e, float) + self.shift[0]
        n = np.asarray(n, float) + self.shift[1]
        u = ((self.lon0 + e / self.m_lon) - self.W) / (self.E - self.W) * self.wpx - 0.5
        v = (self.N - (self.lat0 + n / self.m_lat)) / (self.N - self.S) * self.hpx - 0.5
        return (np.clip(np.round(v).astype(int), 0, self.hpx - 1), np.clip(np.round(u).astype(int), 0, self.wpx - 1))

    def grey(self, e, n):
        j, i = self.ij(e, n)
        return (self.sat[j, i] < SAT_MAX) & (self.mx[j, i] > MX_MIN) & (self.mx[j, i] < MX_MAX)

    def kerb(self, e, n):
        """the red / white kerbs (and paint): road-course/pave_mask.py's rule, which counts them as pavement"""
        j, i = self.ij(e, n)
        r, g, b = self.rgb[j, i, 0], self.rgb[j, i, 1], self.rgb[j, i, 2]
        return ((r > 150) & (r - g > 50) & (r - b > 50)) | (np.minimum(np.minimum(r, g), b) > 200)


def fill_small_holes(mask, cell_m, max_m2):
    lab, k = ndimage.label(~mask)
    if not k:
        return mask
    sizes = ndimage.sum(np.ones_like(mask), lab, index=np.arange(1, k + 1))
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    small = [q + 1 for q, s in enumerate(sizes) if s * cell_m * cell_m < max_m2 and (q + 1) not in edge]
    return mask | np.isin(lab, small)


def measure(d, loc, crop, pts, out_dir: Path):
    pid, node = d["id"], d["node"]
    P = [(p[0], p[2]) for p in loc["points_xyz_m"]]
    W = loc["widths_m"]
    cE, cN = P[node]
    half = float(d.get("half_m", HALF_DEFAULT_M))
    E, N, Z, I = pts
    G = dpo.GRID_M
    n = int(round(2 * half / G))
    xs = cE - half + (np.arange(n) + 0.5) * G
    ys = cN + half - (np.arange(n) + 0.5) * G
    gx, gy = np.meshgrid(xs, ys)
    win = (np.abs(E - cE) < half + 3) & (np.abs(N - cN) < half + 3)
    E, N, Z, I = E[win], N[win], Z[win], I[win]
    tree = cKDTree(np.c_[E, N])
    # the intensity threshold: the lap's own lane between the cuts against the vegetation NAIP shows in the window
    k0, k1 = sorted(d["cuts"])
    lane = cKDTree(np.array(P[k0:k1 + 1]))
    dd, _ = lane.query(np.c_[E, N])
    veg = crop.sat[crop.ij(E, N)] > VEG_SAT
    on, off = float(np.median(I[dd < 2.0])), float(np.median(I[veg]))
    thr = (on + off) / 2.0
    idx = tree.query_ball_point(np.c_[gx.ravel(), gy.ravel()], dpo.MEAN_R_M)
    val = np.array([I[q].mean() if len(q) else np.nan for q in idx]).reshape(n, n)
    grey = crop.grey(gx, gy)
    # the kerbs are paved and driven (the road course's red / white rumble strips), and their paint reads lidar-bright:
    # NAIP's kerb rule alone decides them (pave_mask.py's)
    mask = (grey & (np.isnan(val) | (val < thr))) | crop.kerb(gx, gy)
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    mask = fill_small_holes(mask, G, HOLE_MAX_M2)
    measured_cells = int(mask.sum())
    ribbon = np.zeros_like(mask)
    for k in range(k0, k1):
        ribbon |= dp.segment_band(P[k], P[k + 1], gx, gy, W[k] / 2.0)
    # THE WALL'S FOOT (the pad's "ribbon_right_m"): the outer wall stands on the lap's right edge (its inner face 0.05 m
    # past it, its 0.6 m foot beyond); where the lap's edge strip went, the deck runs under the whole foot so the wall
    # seats on it (tools/author_bespoke_blend.py rails stand_on; lm_pads.deck.hold_beyond_lane holds its height)
    rr = float(d.get("ribbon_right_m") or 0.0)
    if rr > 0.0:
        def right_of(k_, off):
            a_, b_ = P[max(k_ - 1, 0)], P[min(k_ + 1, len(P) - 1)]
            tx, ty = b_[0] - a_[0], b_[1] - a_[1]
            tl = math.hypot(tx, ty) or 1.0
            return (P[k_][0] + ty / tl * off, P[k_][1] - tx / tl * off)     # right of travel
        for k in range(k0, k1):
            ribbon |= dp.segment_band(right_of(k, W[k] / 2.0 + rr / 2.0), right_of(k + 1, W[k + 1] / 2.0 + rr / 2.0),
                                      gx, gy, rr / 2.0 + 0.05)
    ribbon_only = int((ribbon & ~mask).sum())
    cuts = [dp.lap_cut(loc["points_xyz_m"], k, node) for k in d["cuts"]]
    sealed = [dp.sealed_cut(s, (cE, cN)) for s in d.get("sealed") or []]
    keep = mask.copy()
    box = d.get("box")
    if box:
        keep &= dp.in_ring_grid(box, gx, gy)
        sealed += [dp.sealed_cut((box[i - 1], box[i]), (cE, cN)) for i in range(len(box))]
    keep |= ribbon
    for c in cuts:
        keep &= ~dp.segment_band(c["a"], c["b"], gx, gy, dpo.BARRIER_W_M)
    for c in sealed:
        keep &= ~(dp.segment_band(c["a"], c["b"], gx, gy, dpo.BARRIER_W_M) & ~ribbon)
    lab, _ = ndimage.label(keep)
    ci = cj = int(half / G)
    if not lab[ci, cj]:
        raise SystemExit(f"junction_pads {pid}: the node is not on pavement in the mask")
    region = lab == lab[ci, cj]
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    ring = dp.smooth_ring(ring, dpo.SMOOTH_M, keep_on=list(cuts + sealed), pin=cuts)
    ring = dp.resample_ring(ring, dpo.STEP_M)
    # the deck: draft_pad_outline's local planes through the asphalt's class-2 points
    zl = Z - float(loc["origin"]["elev_m"])
    bx0, bx1 = min(p[0] for p in ring) - 2.0, max(p[0] for p in ring) + 2.0
    by0, by1 = min(p[1] for p in ring) - 2.0, max(p[1] for p in ring) + 2.0
    C = dpo.DECK_CELL_M
    nx, ny = int(math.ceil((bx1 - bx0) / C)) + 1, int(math.ceil((by1 - by0) / C)) + 1
    deck = []
    for j in range(ny):
        row = []
        for i in range(nx):
            x, y = bx0 + i * C, by0 + j * C
            ids = [k for k in tree.query_ball_point((x, y), dpo.DECK_R_M) if I[k] < thr]
            v = dp.plane_height([(E[k] - x, N[k] - y, zl[k]) for k in ids])
            row.append(None if v is None else round(v, 3))
        deck.append(row)
    rec = {
        "id": pid, "node": node, "cuts": d["cuts"], "sealed": d.get("sealed") or [],
        "outline_en": [[round(x, 3), round(y, 3)] for x, y in ring],
        "outline_flags_paint": [],
        "deck": {"e0": round(bx0, 3), "n0": round(by0, 3), "cell_m": C, "nx": nx, "ny": ny, "y": deck},
        "ribbon_union_m2": round(ribbon_only * G * G, 1),
        "source": {"kind": "naip+lidar", "naip": {"item": crop.item, "shift_en_m": [round(float(v), 3) for v in crop.shift],
                                                  "sat_max": SAT_MAX, "mx": [MX_MIN, MX_MAX]},
                   "lidar": "CO_Eastern_ElPaso_2018 class-2 ground (D:/k10-scratch/pp_lidar/infield.npz)",
                   "ground_points": int(len(E)), "intensity_lane_median": round(on), "intensity_vegetation_median": round(off),
                   "threshold": round(thr), "measured_cells": measured_cells, "window_half_m": half,
                   "method": "tracks/pikes-peak/source/lidar/infield/junction_pads.py (NAIP grey x lidar intensity edge, "
                             "class-2 deck)"},
        "uncertainty_m": {"outline": 0.4},
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # the picture: NAIP dimmed, the kept pavement lit, the outline yellow, the cuts green, the box red
    j_, i_ = crop.ij(gx, gy)
    rgb = crop.rgb[j_, i_] * 0.5
    rgb[region] = rgb[region] * 0.5 + 110.0
    S = 2
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((n * S, n * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)

    def px(x, y):
        return ((x - (cE - half)) / G * S, ((cN + half) - y) / G * S)
    if box:
        b = [px(*q) for q in box]
        dr.line(b + [b[0]], fill=(255, 40, 40), width=2)
    for c in cuts:
        dr.line([px(*c["a"]), px(*c["b"])], fill=(0, 255, 0), width=2)
    r_ = [px(*q) for q in ring]
    dr.line(r_ + [r_[0]], fill=(255, 230, 0), width=2)
    dr.text((6, 6), f"{pid}: {len(ring)} outline points, threshold {thr:.0f}", fill=(255, 255, 255))
    img.save(out_dir / f"{pid}.png")
    area = abs(sum(ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1] for i in range(len(ring)))) / 2.0
    print(f"[junction_pads] {pid}: {len(ring)} outline points, {area:.0f} m2, intensity lane {on:.0f} / vegetation {off:.0f}"
          f" -> threshold {thr:.0f}; ribbon united {rec['ribbon_union_m2']} m2; deck {nx} x {ny} -> {out_dir / (pid + '.json')}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--naip", required=True)
    ap.add_argument("--lidar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", action="append", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decls = (cfg.get("lm_pads") or {}).get("pads") or []
    if not decls:
        raise SystemExit("junction_pads: the workshop's track.config.json declares no lm_pads.pads")
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    crop = Crop(Path(a.naip), loc["origin"])
    lid = np.load(a.lidar)
    g = lid["cls"] == 2
    pts = (lid["e"][g], lid["n"][g], lid["z"][g], lid["inten"][g].astype(float))
    for d in decls:
        if a.id and d["id"] not in a.id:
            continue
        measure(d, loc, crop, pts, Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
