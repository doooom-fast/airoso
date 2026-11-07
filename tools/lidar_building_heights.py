"""Building heights MEASURED from USGS 3DEP lidar (ledger 0083, buildings pass 2): every planned footprint of a track's
buildings.json, its roof read off the point cloud, its ground off the lidar's own ground around it.

    python -I tools/lidar_building_heights.py <track-dir> <buildings.json> <out.json> <tile.laz> [<tile.laz> ...]
            [--stepped <key> ...] [--osm <osm_buildings.json>] [--origin <centerline.local.json>]

Needs laspy + lazrs + pyproj + numpy (not the repo's .venv: the lidar venv). Run it with python -I: it reads downloaded data.
The LAZ never enters the repo; the output (a few hundred kB) is the derived product the planner reads
(tools/plan_buildings.py, the plan's opt-in "lidar" key).

PER FOOTPRINT (all in the tile's own CRS, metres; the footprint is OSM's lon/lat through pyproj):
  roof    the points of building class 6 at least INSET_M inside the footprint's walls; when the cloud's class 6 covers less
          than CLASS6_MIN_SHARE of the footprint's first returns (CA_SanDiegoCo_D24 classifies no buildings: 1 / 2 / 7 / 9 / 17 /
          18 / 20 only), the SINGLE returns that are not ground, noise or water: a roof is a hard surface and returns once, a
          tree returns several times. A footprint whose first returns are mostly ground (GROUND_MAX_SHARE) has no roof in the
          lidar ("no_roof"); one whose non-ground first returns are mostly multiple returns (VEG_MAX_SHARE), or with vegetation
          classes 3-5, is a tree ("vegetation"). Neither is measured.
  ground  the median of the class-2 (ground) points GROUND_RING_M outside the walls, outside every other footprint, widened
          ring by ring until GROUND_MIN points are found.
  heights roof z - ground: p05 .. p98, the median the robust roof height of a flat roof (the deck: a parapet, rooftop units and
          a stray wall return are the top few per cent); a pitched roof's eave p10 and ridge p95 (the planner).
  levels  the roof heights' histogram in LEVEL_BIN_M bins: every mode holding LEVEL_MIN_SHARE of the roof points and LEVEL_SEP_M
          from a bigger one is a roof level (a stepped stand, a tower over a hall).
  cover   the share of the footprint's 1 m cells holding any lidar point: under COVER_MIN the footprint is off the tiles
          (status "uncovered", the class default stays).
--stepped <key>: that building's real stepped form: the roof's medians in SLICE_M slices across the footprint's oriented box
(short axis), runs of slices within TIER_JOIN_M of their running median merged into tiers, each tier the footprint clipped to
its band (rows "parts", flat roofs). Every number is a statistic of points, the constants below are [invented] thresholds.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

INSET_M = 0.75            # [invented] roof points this far inside the walls: a wall's own returns and the eave's edge stay out
GROUND_RING_M = [(1.0, 8.0), (1.0, 15.0), (1.0, 30.0)]    # [invented] the ground ring, widened until GROUND_MIN points
GROUND_MIN = 20           # [invented]
ROOF_MIN = 20             # [invented] fewer roof points than this is no measurement
CLASS6_MIN_SHARE = 0.25   # [invented] class 6 must hold this share of the inset first returns, else the first returns are read
VEG_MAX_SHARE = 0.5       # [invented] first returns more than this share vegetation (3, 4, 5) or multiple: a tree over it
GROUND_MAX_SHARE = 0.5    # [invented] first returns more than this share ground (class 2): no roof stands there in the lidar
NOT_ROOF = (2, 7, 9, 18, 20)   # ground, low noise, water, high noise, ignored ground: never a roof point
COVER_MIN = 0.5           # [invented] the share of the footprint's 1 m cells holding a point (a barn row cut by the tiles' edge: its 59 % holds both eaves and the ridge)
NO_ROOF_M = 1.5           # [invented] a median roof lower than this over the ground: no building stands there in the lidar
LEVEL_BIN_M = 0.5
LEVEL_MIN_SHARE = 0.15    # [invented]
LEVEL_SEP_M = 2.0         # [invented]
SLICE_M = 2.0             # [invented] the stepped form's slice across the short axis
TIER_JOIN_M = 1.0         # [invented] a slice within this of its tier's running median joins it
TIER_MIN_M = 4.0          # [invented] a tier narrower than this joins its neighbour nearer in height
PCTS = (5, 10, 25, 50, 75, 90, 95, 98)
CHUNK_POINTS = 2_000_000     # laspy chunk_iterator: a tile is read in chunks and only the kept points held
KEEP_CELL_M = 5.0           # the keep mask's cell (a superset of every footprint's query box)
KEEP_MARGIN_M = 5.0         # [invented] slack round the query box
READ_ONLY = frozenset({"CHUNK_POINTS", "KEEP_CELL_M", "KEEP_MARGIN_M"})   # how the tiles are read, not how a roof is measured: not in params


def point_in_ring(ring, x, y):
    """vectorised even-odd test: ring [(x, y)], x / y arrays -> bool array"""
    inside = np.zeros(x.shape, dtype=bool)
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if y1 == y2:
            continue
        cond = (y1 > y) != (y2 > y)
        xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= cond & (x < xint)
    return inside


def dist_to_ring(ring, x, y):
    """the distance of every point to the ring's edges"""
    d = np.full(x.shape, np.inf)
    n = len(ring)
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey
        t = np.zeros(x.shape) if L2 == 0 else np.clip(((x - ax) * ex + (y - ay) * ey) / L2, 0.0, 1.0)
        d = np.minimum(d, np.hypot(x - (ax + t * ex), y - (ay + t * ey)))
    return d


def levels_of(h):
    """the roof levels: histogram modes holding LEVEL_MIN_SHARE, LEVEL_SEP_M from any bigger mode"""
    if len(h) < ROOF_MIN:
        return []
    lo, hi = float(np.floor(h.min())), float(np.ceil(h.max())) + LEVEL_BIN_M
    counts, edges = np.histogram(h, bins=np.arange(lo, hi + LEVEL_BIN_M, LEVEL_BIN_M))
    sm = np.convolve(np.pad(counts, 1), [1, 1, 1], mode="valid")   # a level is three bins wide (1.5 m) at most
    order = np.argsort(-sm)
    picked = []
    for i in order:
        c = (edges[i] + edges[i + 1]) / 2
        if any(abs(c - p) < LEVEL_SEP_M for p in picked):
            continue
        sel = np.abs(h - c) < LEVEL_SEP_M / 2
        share = float(sel.mean())
        if share < LEVEL_MIN_SHARE:
            continue
        picked.append(float(np.median(h[sel])))
    out = []
    for p in sorted(picked):
        sel = np.abs(h - p) < LEVEL_SEP_M / 2
        out.append({"h_m": round(p, 2), "share": round(float(sel.mean()), 3)})
    return out


def oriented_box(ring):
    """(centre, u long axis, v short axis, half long, half short) of the min-area box with an edge direction"""
    best = None
    pts = np.asarray(ring)
    for i in range(len(ring)):
        a, b = pts[i], pts[(i + 1) % len(ring)]
        e = b - a
        ln = float(np.hypot(*e))
        if ln < 1e-6:
            continue
        u = e / ln
        v = np.array([-u[1], u[0]])
        us, vs = pts @ u, pts @ v
        w, h = us.max() - us.min(), vs.max() - vs.min()
        if best is None or w * h < best[0]:
            c = u * (us.max() + us.min()) / 2 + v * (vs.max() + vs.min()) / 2
            best = (w * h, c, u, v, w / 2, h / 2)
    _, c, u, v, hw, hh = best
    if hw < hh:
        u, v, hw, hh = v, -u, hh, hw
    return c, u, v, hw, hh


def clip_halfplane(poly, n, d):
    """Sutherland-Hodgman: keep the part of poly where p . n >= d"""
    out = []
    m = len(poly)
    for i in range(m):
        p, q = poly[i], poly[(i + 1) % m]
        fp, fq = p[0] * n[0] + p[1] * n[1] - d, q[0] * n[0] + q[1] * n[1] - d
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def ring_area(r):
    return abs(sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))) / 2


class Cloud:
    """the tiles' points (x, y, z, class, return number, number of returns) with a 2 m cell index"""
    CELL = 2.0

    def __init__(self, x, y, z, cls, rn, nr=None):
        self.x0, self.y0 = float(x.min()), float(y.min())
        ix = ((x - self.x0) / self.CELL).astype(np.int64)
        iy = ((y - self.y0) / self.CELL).astype(np.int64)
        self.nx = int(ix.max()) + 1
        key = iy * self.nx + ix
        o = np.argsort(key, kind="stable")
        self.key = key[o]
        self.x, self.y, self.z, self.cls, self.rn = x[o], y[o], z[o], cls[o], rn[o]
        self.nr = (np.ones_like(rn) if nr is None else nr)[o]
        self.ny = int(iy.max()) + 1

    def box(self, xmin, ymin, xmax, ymax):
        """indices of the points in the cells overlapping the box"""
        i0, i1 = max(0, int((xmin - self.x0) // self.CELL)), min(self.nx - 1, int((xmax - self.x0) // self.CELL))
        j0, j1 = max(0, int((ymin - self.y0) // self.CELL)), min(self.ny - 1, int((ymax - self.y0) // self.CELL))
        if i1 < i0 or j1 < j0:
            return np.zeros(0, dtype=np.int64)
        parts = []
        for j in range(j0, j1 + 1):
            a = np.searchsorted(self.key, j * self.nx + i0, side="left")
            b = np.searchsorted(self.key, j * self.nx + i1, side="right")
            if b > a:
                parts.append(np.arange(a, b))
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.int64)


def measure(cloud, ring, others):
    """one footprint -> the record (see the header)"""
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    pad = GROUND_RING_M[-1][1] + 1
    idx = cloud.box(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    rec = {"area_m2": round(ring_area(ring), 1)}
    if len(idx) == 0:
        rec.update(status="uncovered", cover=0.0)
        return rec, None
    x, y, z, c, rn, nr = cloud.x[idx], cloud.y[idx], cloud.z[idx], cloud.cls[idx], cloud.rn[idx], cloud.nr[idx]
    inside = point_in_ring(ring, x, y)
    d = dist_to_ring(ring, x, y)
    # cover: the footprint's 1 m cells holding any point
    gx = np.arange(math.floor(min(xs)) + 0.5, max(xs), 1.0)
    gy = np.arange(math.floor(min(ys)) + 0.5, max(ys), 1.0)
    GX, GY = np.meshgrid(gx, gy)
    GX, GY = GX.ravel(), GY.ravel()
    cin = point_in_ring(ring, GX, GY)
    held = set(zip(np.floor(x[inside]).astype(int).tolist(), np.floor(y[inside]).astype(int).tolist()))
    cells = list(zip(np.floor(GX[cin]).astype(int).tolist(), np.floor(GY[cin]).astype(int).tolist()))
    cover = (sum(1 for q in cells if q in held) / len(cells)) if cells else 0.0
    rec["cover"] = round(cover, 3)
    if cover < COVER_MIN:
        rec["status"] = "uncovered"
        return rec, None
    # ground: class 2 outside the walls and outside every other footprint
    out_other = np.ones(x.shape, dtype=bool)
    for o in others:
        ox, oy = [p[0] for p in o], [p[1] for p in o]
        near = (x >= min(ox)) & (x <= max(ox)) & (y >= min(oy)) & (y <= max(oy))
        if near.any():
            out_other[near] &= ~point_in_ring(o, x[near], y[near])
    ground = None
    for a, b in GROUND_RING_M:
        sel = (c == 2) & ~inside & (d >= a) & (d <= b) & out_other
        if sel.sum() >= GROUND_MIN:
            ground = float(np.median(z[sel]))
            rec.update(ground_m=round(ground, 2), ground_n=int(sel.sum()), ground_ring_m=[a, b],
                       ground_p10_p90=[round(float(np.percentile(z[sel], 10)), 2), round(float(np.percentile(z[sel], 90)), 2)])
            break
    if ground is None:
        rec["status"] = "no_ground"
        return rec, None
    core = inside & (d >= INSET_M)
    first = core & (rn == 1)
    n_first = int(first.sum())
    six = core & (c == 6)
    above = first & ~np.isin(c, NOT_ROOF)
    veg = above & (np.isin(c, (3, 4, 5)) | (nr > 1))
    rec["n_first"], rec["n_class6"] = n_first, int(six.sum())
    rec["ground_share"] = round(float((first & (c == 2)).sum() / max(1, n_first)), 3)
    rec["veg_share"] = round(float(veg.sum() / max(1, above.sum())), 3)
    single = above & (nr == 1) & ~np.isin(c, (3, 4, 5))
    if six.sum() >= ROOF_MIN and six.sum() >= CLASS6_MIN_SHARE * n_first:
        roof, rec["roof_src"] = six, "class 6"
    elif n_first < ROOF_MIN:
        rec["status"] = "too_few_points"
        return rec, None
    elif rec["ground_share"] > GROUND_MAX_SHARE:
        rec["status"] = "no_roof"
        return rec, None
    elif rec["veg_share"] > VEG_MAX_SHARE or single.sum() < ROOF_MIN:
        rec["status"] = "vegetation"
        return rec, None
    else:
        roof, rec["roof_src"] = single, "single returns, not ground"
    h = z[roof] - ground
    rec["n_roof"] = int(roof.sum())
    rec["h_pct"] = {f"p{p:02d}": round(float(np.percentile(h, p)), 2) for p in PCTS}
    rec["levels"] = levels_of(h)
    rec["status"] = "no_roof" if rec["h_pct"]["p50"] < NO_ROOF_M else "measured"
    return rec, (x[roof], y[roof], h)


def stepped(ring, rx, ry, h):
    """the stepped form: tiers across the short axis, each the footprint clipped to its band"""
    c, u, v, hw, hh = oriented_box(ring)
    pts = np.c_[rx, ry] - c
    t = pts @ v                                         # across the short axis, -hh .. hh
    edges = np.arange(-hh, hh + SLICE_M, SLICE_M)
    slices = []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (t >= a) & (t < b)
        if sel.sum() >= 5:
            slices.append([float(a), float(b), float(np.median(h[sel])), int(sel.sum())])
    tiers = []
    for s in slices:
        if tiers and abs(s[2] - tiers[-1]["med"]) <= TIER_JOIN_M:
            T = tiers[-1]
            T["b"], T["hs"] = s[1], T["hs"] + [s[2]]
            T["med"] = float(np.median(T["hs"]))
        else:
            tiers.append({"a": s[0], "b": s[1], "hs": [s[2]], "med": s[2]})
    merged = True
    while merged and len(tiers) > 1:
        merged = False
        for i, T in enumerate(tiers):
            if T["b"] - T["a"] < TIER_MIN_M:
                nb = [j for j in (i - 1, i + 1) if 0 <= j < len(tiers)]
                j = min(nb, key=lambda k: abs(tiers[k]["med"] - T["med"]))
                lo, hi = min(i, j), max(i, j)
                A, B = tiers[lo], tiers[hi]
                tiers[lo:hi + 1] = [{"a": A["a"], "b": B["b"], "hs": A["hs"] + B["hs"], "med": float(np.median(A["hs"] + B["hs"]))}]
                merged = True
                break
    tiers[0]["a"], tiers[-1]["b"] = -hh - 1.0, hh + 1.0   # the outermost bands reach past the box
    out = []
    for T in tiers:
        sel = (t >= T["a"]) & (t < T["b"])
        poly = [tuple(p) for p in ring]
        n = (v[0], v[1])
        poly = clip_halfplane(poly, n, float(c @ v) + T["a"])
        poly = clip_halfplane(poly, (-n[0], -n[1]), -(float(c @ v) + T["b"]))
        if len(poly) < 3 or ring_area(poly) < 1.0:
            continue
        hsel = h[sel]
        out.append({"band_m": [round(max(T["a"], -hh), 1), round(min(T["b"], hh), 1)], "ring": poly,
                    "n_roof": int(sel.sum()), "h_p50": round(float(np.median(hsel)), 2),
                    "h_p10": round(float(np.percentile(hsel, 10)), 2), "h_p90": round(float(np.percentile(hsel, 90)), 2)})
    profile = [{"band_m": [round(s[0], 1), round(s[1], 1)], "h_p50": round(s[2], 2), "n": s[3]} for s in slices]
    return out, profile, {"long_m": round(2 * hw, 1), "short_m": round(2 * hh, 1),
                          "short_axis_bearing_deg": round(math.degrees(math.atan2(v[0], v[1])) % 360, 1)}


def main() -> int:
    import laspy
    from pyproj import CRS, Transformer
    argv = sys.argv[1:]
    track, bfile, outp = Path(argv[0]), Path(argv[1]), Path(argv[2])
    tiles, stepped_keys, osm_file, origin_file = [], [], None, None
    i = 3
    while i < len(argv):
        if argv[i] == "--stepped":
            stepped_keys.append(argv[i + 1]); i += 2
        elif argv[i] == "--osm":
            osm_file = Path(argv[i + 1]); i += 2
        elif argv[i] == "--origin":
            origin_file = Path(argv[i + 1]); i += 2
        else:
            tiles.append(Path(argv[i])); i += 1
    rows = json.loads(bfile.read_text(encoding="utf-8"))
    extra = []
    if osm_file:                                   # the footprints the planner left out (canopies, pavilions): measured, listed
        planned = {r["key"] for r in rows}
        for e in json.loads(osm_file.read_text(encoding="utf-8")):
            k = f"osm{e['id']}"
            t = e.get("tags", {})
            if k not in planned and t.get("building") in ("pavilion", "roof") and e.get("geometry"):
                extra.append({"key": k, "footprint_lonlat": [[p["lon"], p["lat"]] for p in e["geometry"]],
                              "class": "canopy", "_tag": t.get("building"), "_name": t.get("name")})
    with laspy.open(tiles[0]) as f:                   # the first tile's CRS frames the footprints before any point is read
        crs = f.header.parse_crs()
    hcrs = crs.sub_crs_list[0] if crs.is_compound else crs
    to_m = Transformer.from_crs(CRS.from_epsg(4326), hcrs, always_xy=True)
    to_ll = Transformer.from_crs(hcrs, CRS.from_epsg(4326), always_xy=True)
    unit = hcrs.axis_info[0].unit_conversion_factor
    if abs(unit - 1.0) > 1e-9:
        raise SystemExit(f"tile CRS unit {unit} m: this tool reads metres only")
    rings = {}
    for r in rows + extra:
        xy = [to_m.transform(p[0], p[1]) for p in r["footprint_lonlat"]]
        if xy[0] == xy[-1]:
            xy = xy[:-1]
        rings[r["key"]] = xy
    # KEEP ONLY what a footprint can read (the G10's 4 GB cap, ledger 0083 pass 3): the points in KEEP_CELL_M cells that a
    # footprint's box, padded by the widest ground ring + 1 m (measure()'s own query) + KEEP_MARGIN_M, overlaps. measure()
    # reads exact predicates inside that query, so the output is the whole-tile run's, byte for byte (proved on pass 2's tiles)
    pad = GROUND_RING_M[-1][1] + 1.0 + KEEP_MARGIN_M
    boxes = [(min(p[0] for p in v) - pad, min(p[1] for p in v) - pad, max(p[0] for p in v) + pad, max(p[1] for p in v) + pad)
             for v in rings.values()]
    heads = []
    for tp in tiles:
        with laspy.open(tp) as f:
            heads.append((float(f.header.mins[0]), float(f.header.mins[1]), float(f.header.maxs[0]), float(f.header.maxs[1])))
    gx0, gy0 = min(h[0] for h in heads), min(h[1] for h in heads)
    gnx = int((max(h[2] for h in heads) - gx0) // KEEP_CELL_M) + 1
    gny = int((max(h[3] for h in heads) - gy0) // KEEP_CELL_M) + 1
    mask = np.zeros((gny, gnx), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        i0, i1 = max(0, int((x0 - gx0) // KEEP_CELL_M)), min(gnx - 1, int((x1 - gx0) // KEEP_CELL_M))
        j0, j1 = max(0, int((y0 - gy0) // KEEP_CELL_M)), min(gny - 1, int((y1 - gy0) // KEEP_CELL_M))
        if i1 >= i0 and j1 >= j0:
            mask[j0:j1 + 1, i0:i1 + 1] = True
    import datetime
    t0 = datetime.datetime(1980, 1, 6) + datetime.timedelta(seconds=1e9)   # adjusted standard GPS time (LAS 1.4)
    xs_, ys_, zs_, cs_, rns_, nrs_, tinfo = [], [], [], [], [], [], []
    for tp in tiles:
        counts, gmin, gmax = {}, None, None
        with laspy.open(tp) as f:
            hd = f.header
            for ch in f.chunk_iterator(CHUNK_POINTS):
                cls = np.asarray(ch.classification, dtype=np.uint8)
                u, n = np.unique(cls, return_counts=True)
                for a, b in zip(u, n):
                    counts[int(a)] = counts.get(int(a), 0) + int(b)
                gps = np.asarray(ch.gps_time)
                gmin = float(gps.min()) if gmin is None else min(gmin, float(gps.min()))
                gmax = float(gps.max()) if gmax is None else max(gmax, float(gps.max()))
                x, y = np.asarray(ch.x), np.asarray(ch.y)
                ci = np.clip(((x - gx0) // KEEP_CELL_M).astype(np.int64), 0, gnx - 1)
                cj = np.clip(((y - gy0) // KEEP_CELL_M).astype(np.int64), 0, gny - 1)
                keep = mask[cj, ci] & (cls != 7) & (cls != 18)       # low / high noise dropped, as before
                xs_.append(x[keep]); ys_.append(y[keep]); zs_.append(np.asarray(ch.z)[keep])
                cs_.append(cls[keep]); rns_.append(np.asarray(ch.return_number, dtype=np.uint8)[keep])
                nrs_.append(np.asarray(ch.number_of_returns, dtype=np.uint8)[keep])
        flown = [str((t0 + datetime.timedelta(seconds=v)).date()) for v in (gmin, gmax)]
        tinfo.append({"file": tp.name, "bytes": tp.stat().st_size, "points": int(hd.point_count),
                      "bbox": [round(float(v), 2) for v in (hd.mins[0], hd.mins[1], hd.maxs[0], hd.maxs[1])],
                      "z_range": [round(float(hd.mins[2]), 2), round(float(hd.maxs[2]), 2)],
                      "classes": dict(sorted(counts.items())), "file_created": str(hd.creation_date),
                      "flown": flown,
                      "point_format": int(hd.point_format.id), "version": str(hd.version)})
    cloud = Cloud(np.concatenate(xs_), np.concatenate(ys_), np.concatenate(zs_), np.concatenate(cs_), np.concatenate(rns_),
                  np.concatenate(nrs_))
    del xs_, ys_, zs_, cs_, rns_, nrs_
    origin = None
    if origin_file:
        origin = json.loads(origin_file.read_text(encoding="utf-8"))["origin"]
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from scripts.geometry.projection import _meters_per_degree
        mlon, mlat = _meters_per_degree(origin["lat"])
        for t in tinfo:
            x0, y0, x1, y1 = t["bbox"]
            corners = [to_ll.transform(a, b) for a, b in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            t["corners_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in corners]
            t["corners_track_xy"] = [[round((a - origin["lon"]) * mlon, 1), round((b - origin["lat"]) * mlat, 1)] for a, b in corners]
    # neighbours for the ground ring: every footprint near this one
    cent = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in rings.items()}
    out = {}
    parts = {}
    for r in rows + extra:
        k = r["key"]
        ring = rings[k]
        rad = max(math.dist(cent[k], p) for p in ring) + GROUND_RING_M[-1][1] + 60
        others = [rings[o] for o in rings if o != k and math.dist(cent[k], cent[o]) < rad]
        rec, roof = measure(cloud, ring, others)
        rec["class"] = r["class"]
        if r.get("_tag"):
            rec["osm_building"], rec["name"] = r["_tag"], r.get("_name")
        out[k] = rec
        if k in stepped_keys and roof is not None:
            tiers, profile, box = stepped(ring, *roof)
            for T in tiers:
                T["footprint_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in (to_ll.transform(p[0], p[1]) for p in T.pop("ring"))]
            parts[k] = {"box": box, "profile": profile, "tiers": tiers}
    tally = {}
    for v in out.values():
        tally[v["status"]] = tally.get(v["status"], 0) + 1
    doc = {"_doc": "ledger 0083 buildings pass 2: every planned footprint's roof and ground measured off USGS 3DEP lidar "
                   "(tools/lidar_building_heights.py; the header says how). Heights in metres over the lidar ground around the "
                   "footprint; h_pct the roof points' percentiles; levels the roof's height modes; status measured / uncovered "
                   "(under COVER_MIN of it on the tiles: the class default stays) / vegetation / no_roof / no_ground / too_few_points.",
           "crs": hcrs.name, "crs_epsg": hcrs.to_epsg(), "vertical": crs.sub_crs_list[1].name if crs.is_compound else None,
           "origin": origin, "tiles": tinfo,
           "params": {k: v for k, v in globals().items() if k.isupper() and k not in READ_ONLY and isinstance(v, (int, float, list, tuple))},
           "status": tally, "buildings": out, "stepped": parts}
    outp.write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
    print(f"[lidar] {len(cloud.x):,} points from {len(tiles)} tiles ({hcrs.name}); {len(out)} footprints: {tally}; stepped {list(parts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
