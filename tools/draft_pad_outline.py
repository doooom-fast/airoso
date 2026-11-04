"""ENGINE-DRAFT PADS, the measurement half: one pad's OUTLINE and DECK from a measured source, written as the pad's authored
intermediate (``source/pads/<id>.json``) that ``tools/author_draft_pads_blend.py`` builds from. docs/JUNCTIONS.md §2.0
topology B on an engine draft (ledger 0048 P3b, the Lariat's junction mouths; ledger 0070 Dressing, Sand Creek's corners;
ledger 0065, Lake Murray v5's I-8 seam): the lap is BOTH main arms, cut twice; nothing here is a radius or a width chosen
by hand.

THE DECLARATION (track.config.json ``route.draft_pads``, a list; each entry):
  id            the pad's name (objects ``1ROAD_pad_<id>``, files ``source/pads/<id>.*``)
  node          the lap vertex the lap turns at (centerline.local.json / finished_centerline.json index; the two are the
                same vertices on an engine draft)
  cuts          [in vertex, out vertex]: the lap's two box rows; the pad replaces every lap sheet between them. Rule 4:
                straight transverse cuts 5-30 m from the junction centre, past the crossing pavement edge
  sealed        [[[E, N], [E, N]], ...] (local metres, centerline.local's frame): a straight cut across a leg the lap does
                not drive; the pad's pavement stops on it
  box           [[E, N], ...] (optional): the junction box as a polygon; the pad is the asphalt inside it. Its edges are
                the straight cuts across every leg the lap does not drive (where branches rejoin beyond a single cut, a
                box is the robust way to say where the junction ends)
  arms          [{"object": <built road object>, "cut": [[E, N], [E, N]]}, ...]: a BUILT road ending at the pad (Sand
                Creek's 1ROAD_grid_* pieces), cut on that line and welded to the deck (the author's business)
  source        {"kind": "lidar_ept", "ept": <EPT json URL>}  the 2020-era USGS source lidar: the pavement edge from
                ground-point INTENSITY (asphalt reads dark, concrete and verge bright), the deck from class-2 heights;
                {"kind": "aerial", "image": <path>, "georef": <path>}  a georeferenced aerial (NAIP): the edge from
                brightness; the deck from the draft's own 3DEP ground (data/ground.local.json) -- no aerial height
  half_m        the measurement window round the node (default 45)
  edge          "shoulder" (the default: the deck meets the ground at its outline) -- no curb, no sidewalk

WHAT IT MEASURES:
  * the asphalt mask: intensity / brightness interpolated on a 0.25 m grid (the mean within 0.6 m), thresholded midway
    between the median of the lap's own points (within 2 m of the line near the node) and the verge's (18-30 m off it),
    closed over 1.25 m (lane lines, stop bars and crosswalk zebras read bright inside the asphalt), opened over 0.75 m;
  * plus the lap's own ribbon between the cuts (line +- widths_m / 2): the deck never leaves the lap's lane unpaved
    where the engine's line sits off the measured asphalt or paint notches the edge (recorded: ribbon_union_m2);
  * the pad region: the mask's component holding the node, inside the box, bounded by the lap cuts and sealed cuts;
  * the OUTLINE: that region's boundary traced cell by cell, smoothed along itself (Gaussian, SMOOTH_M) and resampled every
    STEP_M; vertices on a cut line stay exactly on it. Its uncertainty is the edge's own: ~0.4 m on 2-4 pts/m2 lidar (two
    point spacings), wider where paint crosses the edge -- those stretches are FLAGGED (outline points whose 1 m
    neighbourhood holds paint-bright cells), never silently trusted;
  * the DECK (lidar only): local planes fitted to the class-2 ground POINTS ON ASPHALT (intensity under the threshold)
    within DECK_R_M of every 0.5 m grid node in the outline's box, one trim of points over 0.10 m off (a node with too
    few road points carries none: the author reads the nearest one that does, so a strip of the lap's ribbon beside the
    real asphalt takes the road's height, not the verge's or an embankment's), heights in the track's local frame (z - origin.elev_m, the frame
    centerline.local.json's y is in: checked equal to the lidar ground at C14 / C18 and within 0.22 m at C15).

    python tools/draft_pad_outline.py <project> <pad id>        (numpy, scipy, laspy[lazrs], pyproj, Pillow)

Writes ``<project>/source/pads/<id>.json`` (the intermediate) and ``<id>.png`` (the edge, the cuts, the flags, for a
look). Pure helpers live in tools/draft_pads.py; this file is the only one that needs the lidar stack.
"""
from __future__ import annotations

import io
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))
from tools import draft_pads as dp  # noqa: E402

GRID_M = 0.25            # [invented] the mask grid: 4 cells across the lidar's ~0.5 m point spacing
MEAN_R_M = 0.6           # [invented] intensity mean radius per cell
SMOOTH_M = 1.0           # [invented] the traced edge's along-edge Gaussian sigma (the cell staircase out, a curb return kept)
STEP_M = 0.75            # JUNCTIONS rule 5: outline vertices every 0.6-0.8 m
DECK_CELL_M = 0.5        # [invented] the deck grid
DECK_R_M = 2.0           # [invented] the plane-fit radius per deck node (~25-50 ground points at 2-4 pts/m2)
EDGE_UNC_M = 0.4         # two point spacings at 2-4 pts/m2: the edge's own uncertainty
PAINT_K = 1.6            # [invented] a cell brighter than the verge's median x this inside the asphalt is paint
BARRIER_W_M = 0.3        # a cut is the cells within this of its segment (just over one cell either side)


def _get(url):
    from scripts.tls import https_context
    with urllib.request.urlopen(url, timeout=180, context=https_context()) as r:
        return r.read()


def fetch_lidar(ept_url, origin, cE, cN, half, cache: Path):
    """class-2 ground (E, N, z, intensity) in the window, local metres; cached as <cache>.npz"""
    import numpy as np
    if cache.exists():
        d = np.load(cache)
        if "half" in d.files and float(d["half"]) == float(half) and abs(float(d["cE"]) - cE) < 1e-3                 and abs(float(d["cN"]) - cN) < 1e-3:
            return d["E"], d["N"], d["Z"], d["I"]
        if "half" not in d.files and float(half) == 45.0:     # the first caches (45 m windows) carry no window record
            return d["E"], d["N"], d["Z"], d["I"]
    import laspy
    from pyproj import Transformer
    m_lon, m_lat = dp.meters_per_degree(origin["lat"])
    ept = json.loads(_get(ept_url))
    base = ept_url.rsplit("/", 1)[0]
    if ept["srs"].get("horizontal") != "3857":
        raise SystemExit(f"draft_pad_outline: {ept_url} is not EPSG:3857")
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True)
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    x0, y0 = to_merc.transform(origin["lon"] + (cE - half) / m_lon, origin["lat"] + (cN - half) / m_lat)
    x1, y1 = to_merc.transform(origin["lon"] + (cE + half) / m_lon, origin["lat"] + (cN + half) / m_lat)
    b = ept["bounds"]
    if not (b[0] <= x0 and x1 <= b[3] and b[1] <= y0 and y1 <= b[4]):
        raise SystemExit(f"draft_pad_outline: the window is not inside {ept_url}'s bounds")
    hier = {}

    def h_of(key):
        if key not in hier:
            hier[key] = json.loads(_get(f"{base}/ept-hierarchy/{key}.json"))
        return hier[key]
    keys = []

    def walk(d, x, y, z, h):
        k = f"{d}-{x}-{y}-{z}"
        if k not in h:
            return
        if h[k] == -1:
            h = h_of(k)
        sz = (b[3] - b[0]) / 2 ** d
        bx, by = b[0] + x * sz, b[1] + y * sz
        if bx > x1 or bx + sz < x0 or by > y1 or by + sz < y0:
            return
        if h[k] > 0:
            keys.append(k)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    walk(d + 1, 2 * x + dx, 2 * y + dy, 2 * z + dz, h)
    walk(0, 0, 0, 0, h_of("0-0-0-0"))
    acc = [[], [], [], []]
    for k in keys:
        las = laspy.read(io.BytesIO(_get(f"{base}/ept-data/{k}.laz")))
        m = (np.asarray(las.classification) == 2) & (las.x >= x0) & (las.x <= x1) & (las.y >= y0) & (las.y <= y1)
        if not m.any():
            continue
        lon, lat = to_ll.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
        acc[0].append((lon - origin["lon"]) * m_lon)
        acc[1].append((lat - origin["lat"]) * m_lat)
        acc[2].append(np.asarray(las.z)[m])
        acc[3].append(np.asarray(las.intensity)[m].astype(float))
    E, N, Z, I = (np.concatenate(a) for a in acc)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, E=E, N=N, Z=Z, I=I, half=half, cE=cE, cN=cN)
    return E, N, Z, I


def main(argv=None):
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage
    from scipy.spatial import cKDTree
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit("usage: python tools/draft_pad_outline.py <project> <pad id>")
    proj, pid = Path(args[0]), args[1]
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    decl = dp.declaration(cfg, pid)
    loc = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    origin = loc["origin"]
    P = [(p[0], p[2]) for p in loc["points_xyz_m"]]
    node = decl["node"]
    cE, cN = P[node]
    half = float(decl.get("half_m", 45.0))
    src = decl["source"]
    if src.get("kind") != "lidar_ept":
        raise SystemExit(f"draft_pad_outline: source kind {src.get('kind')!r} is not built yet (lidar_ept)")
    out_dir = proj / "source" / "pads"
    E, N, Z, I = fetch_lidar(src["ept"], origin, cE, cN, half, out_dir / f"{pid}.lidar.npz")
    # the intensity raster
    n = int(round(2 * half / GRID_M))
    xs = cE - half + (np.arange(n) + 0.5) * GRID_M
    ys = cN + half - (np.arange(n) + 0.5) * GRID_M
    gx, gy = np.meshgrid(xs, ys)
    tree = cKDTree(np.c_[E, N])
    idx = tree.query_ball_point(np.c_[gx.ravel(), gy.ravel()], MEAN_R_M)
    val = np.array([I[i].mean() if len(i) else np.nan for i in idx]).reshape(n, n)
    road = cKDTree(np.array(P[max(0, node - 25):node + 26]))
    dd, _ = road.query(np.c_[E, N])
    on, off = float(np.median(I[dd < 2.0])), float(np.median(I[(dd > 18.0) & (dd < 30.0)]))
    thr = (on + off) / 2.0
    mask = np.nan_to_num(val, nan=1e9) < thr
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
    mask = ndimage.binary_fill_holes(mask)
    measured_cells = int(mask.sum())
    # THE LAP'S OWN ROAD between the cuts joins the mask: the engine's line can sit off the measured asphalt (C18's ramp:
    # the line runs along the real ramp's west edge) and paint can notch it (C15's west crosswalk); a deck that leaves
    # the lap's lane unpaved is a hole the car falls through. The engine ribbon's footprint (line +- widths_m / 2) is
    # always paved; how much of the deck is that and not measured asphalt is recorded.
    W = loc.get("widths_m") or []
    ribbon = np.zeros_like(mask)
    k0, k1 = sorted(decl["cuts"])
    for k in range(k0, k1):
        (ax, ay), (bx, by) = P[k], P[k + 1]
        hw = (W[k] / 2.0) if k < len(W) else 3.0
        ribbon |= dp.segment_band((ax, ay), (bx, by), gx, gy, hw)
    ribbon_only = int((ribbon & ~mask).sum())
    # the region: the node's component of the asphalt once every cut is a BARRIER along its segment -- a lap cut CUT_HALF_M
    # either side of the lap (across its own arm and anything merging there: C14's ramp joins Paradise above the island),
    # a sealed cut along its declared segment. A barrier, not a half-plane: an infinite line would clip the other arm
    # (C18's third-band seal crossed 19th St west).
    cuts = [dp.lap_cut(loc["points_xyz_m"], k, node) for k in decl["cuts"]]
    sealed = [dp.sealed_cut(s, (cE, cN)) for s in decl.get("sealed") or []]
    keep = mask.copy()
    box = decl.get("box")
    if box:
        keep &= dp.in_ring_grid(box, gx, gy)
        sealed += [dp.sealed_cut((box[i - 1], box[i]), (cE, cN)) for i in range(len(box))]
    keep |= ribbon                                   # the lap's lane: never clipped by a box or a seal, only by its cuts
    for c in cuts:
        keep &= ~dp.segment_band(c["a"], c["b"], gx, gy, BARRIER_W_M)
    for c in sealed:
        keep &= ~(dp.segment_band(c["a"], c["b"], gx, gy, BARRIER_W_M) & ~ribbon)
    lab, _ = ndimage.label(keep)
    ci, cj = int(half / GRID_M), int(half / GRID_M)
    if not lab[ci, cj]:
        raise SystemExit(f"draft_pad_outline {pid}: the node is not on asphalt in the mask (threshold {thr:.0f})")
    region = lab == lab[ci, cj]
    # trace, smooth, resample
    ring = dp.trace_boundary(region.tolist(), xs.tolist(), ys.tolist())
    ring = dp.smooth_ring(ring, SMOOTH_M, keep_on=[c for c in cuts + sealed], pin=cuts)
    ring = dp.resample_ring(ring, STEP_M)
    # paint flags: outline points with paint-bright cells (> off x PAINT_K) inside the asphalt within 1 m
    paint = (np.nan_to_num(val, nan=0) > off * PAINT_K) & ndimage.binary_dilation(region, iterations=4)
    pt = cKDTree(np.c_[gx[paint], gy[paint]]) if paint.any() else None
    flags = [i for i, (x, y) in enumerate(ring) if pt is not None and pt.query_ball_point((x, y), 1.0)]
    # the deck: local planes in the track's local frame
    zl = Z - float(origin["elev_m"])
    bx0, bx1 = min(p[0] for p in ring) - 2.0, max(p[0] for p in ring) + 2.0
    by0, by1 = min(p[1] for p in ring) - 2.0, max(p[1] for p in ring) + 2.0
    nx, ny = int(math.ceil((bx1 - bx0) / DECK_CELL_M)) + 1, int(math.ceil((by1 - by0) / DECK_CELL_M)) + 1
    deck = []
    for j in range(ny):
        row = []
        for i in range(nx):
            x, y = bx0 + i * DECK_CELL_M, by0 + j * DECK_CELL_M
            ids = [k for k in tree.query_ball_point((x, y), DECK_R_M) if I[k] < thr]   # the ROAD's points only:
            row.append(dp.plane_height([(E[k] - x, N[k] - y, zl[k]) for k in ids]))      # never the verge's fall
        deck.append(row)
    rec = {
        "id": pid, "node": node, "cuts": decl["cuts"], "sealed": decl.get("sealed") or [],
        "outline_en": [[round(x, 3), round(y, 3)] for x, y in ring],
        "outline_flags_paint": flags,
        "deck": {"e0": round(bx0, 3), "n0": round(by0, 3), "cell_m": DECK_CELL_M, "nx": nx, "ny": ny,
                 "y": [[None if v is None else round(v, 3) for v in r] for r in deck]},
        "ribbon_union_m2": round(ribbon_only * GRID_M * GRID_M, 1),
        "source": {"kind": "lidar_ept", "ept": src["ept"], "ground_points": int(len(E)),
                   "density_per_m2": round(len(E) / (2 * half) ** 2, 2), "intensity_road_median": round(on),
                   "intensity_verge_median": round(off), "threshold": round(thr), "window_half_m": half,
                   "method": "tools/draft_pad_outline.py (intensity edge, class-2 deck)"},
        "uncertainty_m": {"outline": EDGE_UNC_M, "outline_at_flags": "paint across the edge: the closing bridged it, "
                          "the edge there is the paint's outer side +- 1 m"},
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # the picture
    lo, hi = np.nanpercentile(val, 2), np.nanpercentile(val, 98)
    g = np.nan_to_num(np.clip((val - lo) / max(hi - lo, 1e-6), 0, 1)) * 255
    S = 3
    img = Image.fromarray(np.stack([g, g, g], -1).astype(np.uint8)).resize((n * S, n * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)

    def px(x, y):
        return ((x - (cE - half)) / GRID_M * S, ((cN + half) - y) / GRID_M * S)
    dr.line([px(*p) for p in ring + ring[:1]], fill=(0, 230, 255), width=2)
    for i in flags:
        x, y = px(*ring[i]); dr.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 140, 0))
    for c in cuts + sealed:
        (ax, ay), (bx, by) = c["a"], c["b"]
        dr.line([px(ax, ay), px(bx, by)], fill=(255, 60, 60), width=2)
    dr.line([px(*P[k]) for k in range(max(0, node - 40), min(len(P), node + 41))], fill=(40, 220, 60), width=2)
    for k in range(max(0, node - 40), min(len(P), node + 41), 10):
        x, y = px(*P[k]); dr.text((x + 4, y - 4), f"v{k}", fill=(60, 255, 80))
    img.save(out_dir / f"{pid}.png")
    print(f"[draft_pad_outline] {pid}: {len(ring)} outline points every {STEP_M} m, {len(flags)} flagged (paint); "
          f"area {dp.ring_area(ring):.0f} m2; deck {nx} x {ny} @ {DECK_CELL_M} m ({sum(v is None for r in deck for v in r)} "
          f"empty); the lap's ribbon added {rec['ribbon_union_m2']} m2 outside the measured asphalt; ground {len(E):,} pts "
          f"({rec['source']['density_per_m2']} /m2), intensity road {on:.0f} / verge {off:.0f} "
          f"-> {out_dir / (pid + '.json')}")


if __name__ == "__main__":
    main()
