"""The road course's route read off the two published maps, registered to the aerial, assembled from the measured pieces
(ledger 0085, "Route from the published maps").

    python tracks/pikes-peak/source/road-course/maps_route.py      (after routes.py; needs the NAIP crop and the maps)

Kevin, 2026-11-07: "Why aren't you using actual track maps?" / "Stop guessing". The two maps (downloaded on his word,
not committed; PPIR_MAPS, default /Volumes/Drive/codex/pp_work/maps_dl):
  scca  scca_trackmap_ppir.png              SCCA Track Night: 9 corners, start/finish + arrow, pit entry / exit
  rc    racingcircuits_ppir_road_2017.png   racingcircuits.info 2017 road course: T1-T9, arrows, unused pavement grey

What is read from a map (L1: a selection aid, never coordinates):
  1. its oval outline, fitted to the 2018 lidar wall face by a similarity (schematic.fit_similarity), both handednesses;
     the start/finish and the infield's side decide between the near-symmetric solutions;
  2. its course line (thinned), carried into ENU by that fit; where a schematic draws a corner fatter than the road
     (SCCA's top hairpin: a loop out over the N road, median 12 m off every measured centre line) the line within 50 m
     of that junction is refit by a proper similarity ICP onto EVERY measured infield centre line near it at once (no
     piece preferred), blended out by 80 m (local_refit);
  3. per 2 m of the map's line: the nearest measured piece, its station on that piece -> the pieces in order and their
     direction (the station's trend);
  4. corner labels (T1-T9 / 1-9): the course line's nearest point, then that point's station on the assembled lap.
Direction: as published (both maps' arrows: counter-clockwise). Kevin's strokes (pp_work/sketch/routes) give SHAPE only
(Kevin 2026-11-07: "Do them as published, i just drew shape"); the infield-only layout, which no map publishes, runs the
way the road course runs on the pieces they share.
The route's GEOMETRY is the measured pieces (infield_pieces.naip.json) and, inside the skid pad lot where the map's line
runs over open pavement, the centre of the driven dark band measured here (lot_band()).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import naip  # noqa: E402
import routes  # noqa: E402
import schematic as sc  # noqa: E402

MAPS = Path(os.environ.get("PPIR_MAPS", "/Volumes/Drive/codex/pp_work/maps_dl"))
OUT = Path(os.environ.get("PPIR_MAPS_OUT", "/Volumes/Drive/codex/pp_work/maps_route"))

# --- the maps' ink (flat colours, sampled off each file) and their labels, read by eye off the images: the label's
# centre in map px. Positions are where the label is printed; the corner it names is the course line's nearest point.
MAP = {
    "scca": dict(
        file="scca_trackmap_ppir.png",
        title="SCCA Track Night in America (scca.com, 2026)",
        drop_rows_above=122,          # the title block, "Start/Finish" and its arrow (the oval's top edge is at y 127)
        sf_px=(317, 134),             # the chequered square on the front stretch
        labels={"1": (132, 186), "2": (421, 418), "3": (534, 357), "4": (315, 357), "5": (381, 313), "6": (418, 276),
                "7": (477, 270), "8": (538, 246), "9": (512, 196)},
        pit={"Pit Entry": (486, 184), "Pit Exit": (160, 415)},
        direction="the front stretch arrow under 'Start/Finish' points left (map -x)",
    ),
    "rc": dict(
        file="racingcircuits_ppir_road_2017.png",
        title="racingcircuits.info, Pikes Peak International Raceway road course 2017 to date",
        drop_rows_above=0,
        sf_px=(937, 135),
        labels={"T1": (273, 243), "T2": (253, 890), "T3": (1108, 1008), "T4": (1443, 733), "T5": (784, 752),
                "T6": (1055, 484), "T7": (1155, 497), "T8": (1226, 397), "T9": (1497, 430)},
        pit={},
        direction="white arrows: front stretch left, back stretch right, T4->T5 straight left-down, T8->T9 right-down",
    ),
}


def load_map(key):
    im = np.asarray(Image.open(MAPS / MAP[key]["file"]).convert("RGB")).astype(np.int32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mn = np.minimum(r, np.minimum(g, b))
    if key == "rc":
        course = (r > 200) & (g < 90) & (b < 90)
        unused = (abs(r - 152) < 22) & (abs(g - r) < 8) & (abs(b - r) < 8)
        # the white arrows and the chequered flag punch holes in the red band: fill small holes only
        holes = ndimage.binary_fill_holes(course) & ~course
        lab, n = ndimage.label(holes)
        sz = ndimage.sum(holes, lab, range(1, n + 1))
        course = course | np.isin(lab, 1 + np.flatnonzero(sz < 3000))
        course = ndimage.binary_closing(course, iterations=2)
    else:
        yel = (r > 190) & (g > 190) & (b < 120)
        dark = (r < 90) & (g < 90) & (b < 90)
        unused = (mn >= 205) & (mn <= 243) & ~((r > 243) & (g > 243) & (b > 243))
        # the black band is ~10 px wide; text strokes ~3 px: an opening of radius 2 keeps the band, drops the text
        band = ndimage.binary_opening(dark, structure=np.ones((5, 5)))
        course = ndimage.binary_closing(yel | band, iterations=2)
        course = ndimage.binary_opening(course, structure=np.ones((3, 3)))
    k = MAP[key]["drop_rows_above"]
    if k:
        course[:k] = False; unused[:k] = False
    # the start/finish flag is drawn ON the band (chequers, not course colour): close the band through it
    yy, xx = np.mgrid[0:course.shape[0], 0:course.shape[1]]
    x0, y0 = MAP[key]["sf_px"]
    rad = 24 if key == "rc" else 8
    course = course | ((np.hypot(xx - x0, yy - y0) < rad) & ndimage.binary_dilation(course, iterations=rad))
    return dict(im=im.astype(np.uint8), course=course, unused=unused)


def skeleton_graph(course, spur_px):
    """The course band's centre line as a graph: nodes = branch clusters / ends, edges = ordered pixel paths."""
    sk = sc.prune(sc.thin(course), spur_px)
    deg = sc.degree(sk)
    br = ndimage.binary_dilation(deg >= 3, iterations=1) & sk
    blab, nb = ndimage.label(br, structure=np.ones((3, 3)))
    seg = sk & ~br
    slab, ns = ndimage.label(seg, structure=np.ones((3, 3)))
    nodes = {i: np.array(ndimage.center_of_mass(br, blab, i))[::-1] for i in range(1, nb + 1)}
    edges = []
    for i in range(1, ns + 1):
        m = slab == i
        d = sc.degree(m)
        ends = list(zip(*np.nonzero(m & (d <= 1))))
        if not ends:                       # a closed loop with no branch
            ends = [tuple(np.argwhere(m)[0])]
        P = sc.trace(m, ends[0])
        # which branch cluster touches each end
        def touch(p):
            x, y = int(p[0]), int(p[1])
            win = blab[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
            v = win[win > 0]
            return int(v[0]) if len(v) else None
        edges.append(dict(px=P, a=touch(P[0]), b=touch(P[-1]), n=len(P)))
    return sk, nodes, edges


def aerial_reference():
    om = np.load(naip.CACHE / "oval_mid.npy")
    return dict(mid=om[:, 0:2], face=om[:, 2:4], edge=om[:, 4:6])


def sf_aerial():
    """The start/finish line painted across the front stretch by the grandstand, read on NAIP (a white bar across the
    lane; centre picked at the bar's middle, px (394, 1442))."""
    return np.array(naip.px_to_en(394.0, 1442.0), float)


INFIELD_LABELS = {"scca": ["3", "4", "5", "6", "7", "8"], "rc": ["T4", "T5", "T6", "T7", "T8"]}


def infield_centroid():
    d = json.loads((HERE / "infield_pieces.naip.json").read_text())
    return np.vstack([np.array(v["centre_en_m"]) for v in d["pieces"].values()]).mean(0)


def register(key, m, ref):
    A, _ = sc.outer_contour(m["course"] | m["unused"], close=2)
    face = naip.resample(ref["face"], 0.25, closed=True)
    inf = np.mean([MAP[key]["labels"][k] for k in INFIELD_LABELS[key]], axis=0)
    sols = sc.fit_similarity(A, face, checks={"sf": MAP[key]["sf_px"], "infield": inf})
    SF = sf_aerial(); IC = infield_centroid()
    for z in sols:
        z["sf_miss_m"] = float(np.hypot(*(np.array(z["checks"]["sf"]) - SF)))
        z["infield_miss_m"] = float(np.hypot(*(np.array(z["checks"]["infield"]) - IC)))
    # the same outline, an affine fit (6 parameters) on the chosen solution's correspondences: how much of the residual
    # is the map's own stretch (a schematic drawn fatter or longer than the oval) rather than noise
    return A, sols


def affine_residual(A, ref, T):
    face = naip.resample(ref["face"], 0.25, closed=True)
    tree = cKDTree(face)
    M = np.c_[A, np.ones(len(A))]
    B = sc.apply(T, A)
    for _ in range(40):
        d, j = tree.query(B)
        X, *_ = np.linalg.lstsq(M, face[j], rcond=None)
        B = M @ X
    d, _ = tree.query(B)
    U, S, Vt = np.linalg.svd(X[:2].T)
    return dict(rms=float(np.sqrt((d ** 2).mean())), p95=float(np.percentile(d, 95)), max=float(d.max()),
                scale_ratio=float(S[0] / S[1]))


def choose(sols):
    """The oval is nearly symmetric about its long axis, so a mirrored fit matches its outline almost as well, and so
    does the unmirrored one turned end for end. The start/finish (painted by the grandstand) and the infield's side
    decide: keep solutions whose S/F lands within 60 m of the painted line and whose infield labels land within 80 m
    of the measured infield's centroid; of those, the lowest outline residual."""
    ok = [z for z in sols if z["sf_miss_m"] < 60 and z["infield_miss_m"] < 80]
    assert ok, "no registration puts the start/finish and the infield where the aerial has them"
    return min(ok, key=lambda z: z["rms"])


# ----------------------------------------------------------------------------------------------------------------------
# the measured network: every infield centre line + the oval's mid-surface line, densified, with (name, station)

def load_pieces():
    d = json.loads((HERE / "infield_pieces.naip.json").read_text())
    P = {k: np.array(v["centre_en_m"], float) for k, v in d["pieces"].items()}
    return d, P


def lot_polygon(d):
    """The skid pad lot's outer boundary: the three ring pieces' measured outer (left) edges, joined."""
    E = np.vstack([np.array(d["pieces"][k]["left"]["edge_en_m"]) for k in ("ring_nw", "ring_ne", "ring_s")])
    return E


def inside_poly(P, poly):
    x, y = P[:, 0], P[:, 1]
    inside = np.zeros(len(P), bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / np.where(yj - yi == 0, 1e-9, yj - yi) + xi)
        inside ^= c
        j = i
    return inside


class Network:
    def __init__(self, ref):
        d, P = load_pieces()
        self.d, self.P = d, P
        pts, nm, st, half = [], [], [], []
        for k, Q in P.items():
            Q2 = naip.resample(Q, 0.5)
            pts.append(Q2); nm += [k] * len(Q2); st.append(naip.cumlen(Q2))
            w = d["pieces"][k]["width_m"]["p50"]
            half.append(np.full(len(Q2), w / 2))
        mid = ref["mid"]
        self.mid = mid
        self.smid = naip.cumlen(mid)
        self.lap_mid = float(naip.cumlen(np.vstack([mid, mid[:1]]))[-1])
        pts.append(mid); nm += ["oval"] * len(mid); st.append(self.smid)
        half.append(np.hypot(*(ref["face"] - ref["edge"]).T) / 2)
        self.pts = np.vstack(pts); self.nm = np.array(nm); self.st = np.concatenate(st); self.half = np.concatenate(half)
        self.tree = cKDTree(self.pts)
        self.lot = lot_polygon(d)

    def on_pavement(self, Q, d, j, tol):
        """road pieces: within half the measured width (+tol) of the centre; the oval: between wall face and inside
        edge (+tol); the lot ring: anywhere inside the lot's measured outer edge (its interior is paved) or within tol
        of a ring centre line."""
        ok = d <= self.half[j] + tol
        ring = np.char.startswith(self.nm[j].astype(str), "ring")
        ok = ok | (ring & inside_poly(Q, self.lot))
        return ok

    def read(self, path, tol, mode_win=11, min_run=8.0, closed=False):
        """A drawn line (ENU) -> the measured pieces it runs over, in order and direction."""
        Q = naip.resample(np.asarray(path, float), 1.0, closed=closed)
        d, j = self.tree.query(Q)
        name = self.nm[j].copy()
        # mode filter along the line: junction flicker between neighbouring pieces is not a route change
        h = mode_win // 2
        filt = name.copy()
        for i in range(len(name)):
            w = name[max(0, i - h):i + h + 1]
            u, c = np.unique(w, return_counts=True)
            filt[i] = u[np.argmax(c)]
        onp = self.on_pavement(Q, d, j, tol)
        runs = []
        i = 0
        while i < len(Q):
            k = i
            while k + 1 < len(Q) and filt[k + 1] == filt[i]:
                k += 1
            runs.append([i, k])
            i = k + 1
        # absorb short runs into the longer neighbour
        changed = True
        while changed and len(runs) > 1:
            changed = False
            for r in range(len(runs)):
                a, b = runs[r]
                if b - a + 1 < min_run:
                    nb = [x for x in (r - 1, r + 1) if 0 <= x < len(runs)]
                    t = max(nb, key=lambda x: runs[x][1] - runs[x][0])
                    lo, hi = min(runs[t][0], a), max(runs[t][1], b)
                    runs[t] = [lo, hi]
                    del runs[r]
                    changed = True
                    break
            # merge equal neighbours
            m = [runs[0]]
            for r in runs[1:]:
                if filt[r[0]] == filt[m[-1][0]] or (self._same(filt, m[-1], r)):
                    m[-1] = [m[-1][0], r[1]]
                else:
                    m.append(r)
            runs = m
        out = []
        for a, b in runs:
            sel = np.arange(a, b + 1)
            nmk = filt[a] if (filt[sel] == filt[a]).mean() > 0.5 else max(set(filt[sel]), key=list(filt[sel]).count)
            mine = sel[name[sel] == nmk]
            s = self.st[j[mine]] if len(mine) else np.array([np.nan])
            if nmk == "oval" and len(s) > 2:
                s = np.unwrap(s / self.lap_mid * 2 * np.pi) * self.lap_mid / (2 * np.pi)
            slope = np.polyfit(np.arange(len(s)), s, 1)[0] if len(s) > 2 else 0.0
            out.append(dict(piece=str(nmk), n_m=int(b - a + 1), dir=int(np.sign(slope)) or 1,
                            s_from=round(float(s[0]) % (self.lap_mid if nmk == "oval" else 1e9), 1),
                            s_to=round(float(s[-1]) % (self.lap_mid if nmk == "oval" else 1e9), 1),
                            dist_p50_m=round(float(np.median(d[sel])), 2), dist_max_m=round(float(d[sel].max()), 2),
                            off_pavement_m=int((~onp[sel]).sum()),
                            line_from_m=int(a), line_to_m=int(b)))
        return Q, out, d, onp

    @staticmethod
    def _same(filt, r1, r2):
        return False


def bilinear(img, x, y):
    x = np.clip(np.asarray(x, float), 0, img.shape[1] - 1.001); y = np.clip(np.asarray(y, float), 0, img.shape[0] - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy
            + img[y0 + 1, x0 + 1] * fx * fy)


# ----------------------------------------------------------------------------------------------------------------------
# the driven dark band round the skid pad lot

def lot_band(line, lot, valley=6.0, nb=(3.0, 12.0), min_depth=6.0, med_m=15):
    """The lot's perimeter carries a darker asphalt band (the ring road round the lot: kerbed outside, a dashed kerb
    inside); the lot's interior is lighter concrete with the dark skid pad circle, the paddock outside tan concrete.
    The ring pieces' outer edges are the LOT's boundary, not the band's, so the band is measured here, on
    cross-sections every 1 m along the RC map's own line through the lot (the selection: which side of the lot the
    course runs; never the coordinates):

      the band's floor: the darkest point within +-valley m of the map's line (profile smoothed 1 m sigma across, +-4 m
      along the line);
      each side's neighbouring surface: the 80th percentile of the profile nb[0]-nb[1] m beyond the floor on that side
      (each side normalised against its own surface: the paddock is brighter than the lot's interior);
      the band's limits: where the profile, going out from the floor, rises half way to that side's surface level
      (sub-sample); a section whose band is not at least min_depth grey levels below BOTH sides is [unseen], not
      filled; nor is one whose width falls outside 3-20 m, nor one whose limits jump > 1.5 m off the running median.
    Both limits: running median over med_m m of the seen sections (>= 5 of them in the window), never across a gap of
    more than med_m m; the centre is midway. Sections left without a value hold the nearest smoothed one and are
    flagged inferred. Returns the line's sections, both limits and the centre as offsets along the line's LEFT normal."""
    lum = naip.channels()["lum"]
    E = naip.resample(np.asarray(line, float), 1.0)
    # the skeleton line steps pixel by pixel: its normals are taken off a +-5 m running mean of it
    Es = np.c_[ndimage.uniform_filter1d(E[:, 0], 11, mode="nearest"), ndimage.uniform_filter1d(E[:, 1], 11, mode="nearest")]
    T, L = naip.normals(Es)
    reach = valley + nb[1] + 2.0
    offs = np.arange(-reach, reach + 0.01, 0.25)
    X = Es[:, None, :] + offs[None, :, None] * L[:, None, :]
    px, py = naip.en_to_px(X[..., 0], X[..., 1])
    raw = bilinear(lum, px, py)
    # the lot's measured outer edge (the ring pieces' outer edges) bounds the band: on a section standing in the lot,
    # samples beyond it (grass, dirt: darker than the concrete, never driven) read as the section's lot-interior level
    out = ~inside_poly(X.reshape(-1, 2), lot).reshape(X.shape[:2])
    in_lot = ~out[:, np.argmin(np.abs(offs))]
    for i in np.where(in_lot)[0]:
        raw[i, out[i]] = np.percentile(raw[i, ~out[i]], 80)
    # cracks, joint sealant and the kerbs' dark gaps are 0.3-1 m wide: a 1 m (sigma) gaussian across the line and a
    # +-4 m mean along it leave a 4-12 m band and drop them
    prof = ndimage.uniform_filter1d(ndimage.gaussian_filter1d(raw, 1.0 / 0.25, axis=1), 9, axis=0)
    n = len(Es)
    lo = np.full(n, np.nan); hi = np.full(n, np.nan); floor_off = np.full(n, np.nan)
    depth_lo = np.full(n, np.nan); depth_hi = np.full(n, np.nan); why = [""] * n
    core = np.abs(offs) <= valley
    for i in range(n):
        p = prof[i]
        k0 = np.where(core)[0][np.argmin(p[core])]
        f0 = offs[k0]; floor_off[i] = f0
        side_lo = (offs <= f0 - nb[0]) & (offs >= f0 - nb[1])
        side_hi = (offs >= f0 + nb[0]) & (offs <= f0 + nb[1])
        lv_lo = np.percentile(p[side_lo], 80); lv_hi = np.percentile(p[side_hi], 80)
        depth_lo[i] = lv_lo - p[k0]; depth_hi[i] = lv_hi - p[k0]
        if depth_lo[i] < min_depth or depth_hi[i] < min_depth:
            why[i] = "unseen: band not %g grey levels below both sides" % min_depth
            continue
        tl = p[k0] + depth_lo[i] / 2; th = p[k0] + depth_hi[i] / 2
        k = k0
        while k + 1 < len(offs) and p[k + 1] < th:
            k += 1
        if k + 1 < len(offs):
            hi[i] = offs[k] + (th - p[k]) / max(p[k + 1] - p[k], 1e-6) * (offs[k + 1] - offs[k])
        k = k0
        while k - 1 >= 0 and p[k - 1] < tl:
            k -= 1
        if k - 1 >= 0:
            lo[i] = offs[k] - (tl - p[k]) / max(p[k - 1] - p[k], 1e-6) * (offs[k] - offs[k - 1])
    width = hi - lo
    seen = np.isfinite(width) & (width > 3) & (width < 20)
    for i in np.where(~seen & np.isfinite(width))[0]:
        why[i] = "unseen: width %.1f m outside 3-20 m" % width[i]
    h = med_m // 2

    def smooth(v):
        out = np.full(n, np.nan)
        for i in range(n):
            w = v[max(0, i - h):i + h + 1]
            w = w[np.isfinite(w)]
            if len(w) >= 5:
                out[i] = np.median(w)
        return out
    vlo = np.where(seen, lo, np.nan); vhi = np.where(seen, hi, np.nan)
    slo, shi = smooth(vlo), smooth(vhi)
    # a section whose band jumps off its neighbours' (either limit > 1.5 m from the running median) has found some
    # other dark patch: [unseen], and the median taken again without it
    jump = seen & ((np.abs(vlo - slo) > 1.5) | (np.abs(vhi - shi) > 1.5) | ~np.isfinite(slo) | ~np.isfinite(shi))
    for i in np.where(jump)[0]:
        why[i] = "unseen: band jumps > 1.5 m off its neighbours'"
    seen = seen & ~jump
    vlo = np.where(seen, lo, np.nan); vhi = np.where(seen, hi, np.nan)
    slo, shi = smooth(vlo), smooth(vhi)
    have = np.isfinite(slo) & np.isfinite(shi)
    idx = np.where(have)[0]
    near = idx[np.abs(np.arange(n)[:, None] - idx[None, :]).argmin(1)]
    gap = np.abs(np.arange(n) - near)
    lo_f, hi_f = slo[near], shi[near]
    centre_off = (lo_f + hi_f) / 2
    C = Es + centre_off[:, None] * L
    res = np.r_[(vlo - slo)[seen & have], (vhi - shi)[seen & have]]
    return dict(line=Es, left=L, in_lot=in_lot, lo=lo_f, hi=hi_f, centre=C, centre_off=centre_off, seen=seen, have=have,
                held_m=gap, floor_off=floor_off, depth_lo=depth_lo, depth_hi=depth_hi, why=why,
                residual_abs=np.abs(res), width=hi_f - lo_f)


# ----------------------------------------------------------------------------------------------------------------------
# the map's course line as a lap in ENU

def course_cycle(key, m, T, net):
    """Skeleton graph -> the lap (closed, CCW in ENU, starting at the map's start/finish) and the pit lane edges.
    Where the graph has parallel edges between the same two nodes, the one lying on the oval's surface is the course
    and the other is the pit lane (both maps draw the pit road inside the front stretch)."""
    sk, nodes, edges = skeleton_graph(m["course"], 12 if key == "scca" else 40)
    edges = [e for e in edges if e["n"] >= 10 and e["a"] is not None and e["b"] is not None]
    for e in edges:
        e["en"] = sc.apply(T, e["px"])
        d, _ = cKDTree(net.mid).query(e["en"])
        e["d_mid"] = float(np.median(d)); e["d_mid_p90"] = float(np.percentile(d, 90))
    # the pit road: an edge running alongside the oval, off its surface (median 12-50 m from the mid line) but never
    # out into the infield (90 % of it within 60 m); every other edge is the course
    pit = [e for e in edges if 12 < e["d_mid"] < 50 and e["d_mid_p90"] < 60]
    course = [e for e in edges if not any(e is p for p in pit)]
    # chain the course edges into a loop
    loop = [course[0]]; used = {id(course[0])}
    cur_end = course[0]["b"]; pts = [course[0]["en"]]
    while len(used) < len(course):
        nxt = [e for e in course if id(e) not in used and cur_end in (e["a"], e["b"])]
        if not nxt:
            break
        e = nxt[0]; used.add(id(e))
        P = e["en"] if e["a"] == cur_end else e["en"][::-1]
        cur_end = e["b"] if e["a"] == cur_end else e["a"]
        pts.append(P)
    L = np.vstack(pts)
    area = 0.5 * np.sum(L[:-1, 0] * L[1:, 1] - L[1:, 0] * L[:-1, 1])
    if area < 0:
        L = L[::-1]
    L = naip.resample(L, 1.0, closed=True)
    sf = sc.apply(T, np.array(MAP[key]["sf_px"], float))
    i0 = int(np.argmin(np.hypot(*(L - sf).T)))
    L = np.roll(L, -i0, axis=0)
    node_en = {k: sc.apply(T, v) for k, v in nodes.items()}
    return dict(lap=L, pit=[e["en"] for e in pit], pit_nodes=[(e["a"], e["b"]) for e in pit], nodes=node_en,
                n_edges=len(edges))


def label_points(key, m):
    """Label centres refined on the map: RC's orange discs (component centroids), SCCA's black digits (dark component
    centroid within 9 px of the read position)."""
    im = m["im"].astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    out = {}
    if key == "rc":
        orange = (r > 200) & (g > 110) & (g < 190) & (b < 80)
        lab, n = ndimage.label(orange)
        cents = np.array(ndimage.center_of_mass(orange, lab, range(1, n + 1)))[:, ::-1]
        sizes = ndimage.sum(orange, lab, range(1, n + 1))
        cents = cents[sizes > 500]
        for k, p in MAP[key]["labels"].items():
            j = int(np.argmin(np.hypot(*(cents - p).T)))
            out[k] = cents[j].tolist() if np.hypot(*(cents[j] - p)) < 25 else list(p)
    else:
        dark = (r < 100) & (g < 100) & (b < 100)
        lab, n = ndimage.label(dark)
        for k, p in MAP[key]["labels"].items():
            x, y = p
            win = lab[y - 9:y + 10, x - 9:x + 10]
            ids = [i for i in np.unique(win) if i]
            best = None
            for i in ids:
                yy, xx = np.nonzero(lab == i)
                if 15 < len(yy) < 250:
                    c = np.array([xx.mean(), yy.mean()])
                    if best is None or np.hypot(*(c - p)) < np.hypot(*(best - p)):
                        best = c
            out[k] = (best if best is not None else np.array(p, float)).tolist()
    return out


# ----------------------------------------------------------------------------------------------------------------------
# a schematic draws a tight hairpin as a fat loop: refit the map line locally there

def local_refit(lap, net, centre, r_in=50.0, r_out=80.0, r_ref=110.0):
    """Around `centre` (a junction, ENU): the map line's points within r_in m, a proper similarity (det +1) ICP onto
    EVERY measured infield centre line within r_ref m at once (no piece preferred; the oval excluded). The correction
    is applied with weight 1 inside r_in, blended linearly to 0 at r_out, so the line stays continuous."""
    d0 = np.hypot(*(lap - centre).T)
    A = lap[d0 < r_in]
    refp = net.pts[(net.nm != "oval") & (np.hypot(*(net.pts - centre).T) < r_ref)]
    tree = cKDTree(refp)
    before = tree.query(A)[0]
    T, after = sc.icp(A, refp, (1.0, np.eye(2), np.zeros(2)), det_sign=1)
    s, R, t = T

    def fix(P):
        P = np.atleast_2d(np.asarray(P, float))
        w = np.clip((r_out - np.hypot(*(P - centre).T)) / (r_out - r_in), 0, 1)[:, None]
        return P + w * (sc.apply(T, P) - P)
    info = dict(centre_en_m=np.round(centre, 1).tolist(), r_in_m=r_in, r_out_m=r_out, scale=round(float(s), 4),
                rot_deg=round(float(np.degrees(np.arctan2(R[1, 0], R[0, 0]))), 2),
                moves_centre_m=round(float(np.hypot(*(sc.apply(T, centre) - centre))), 2),
                to_pieces_before_m=dict(p50=round(float(np.median(before)), 2), p95=round(float(np.percentile(before, 95)), 2)),
                to_pieces_after_m=dict(p50=round(float(np.median(after)), 2), p95=round(float(np.percentile(after, 95)), 2)))
    return fix(lap), fix, info


# ----------------------------------------------------------------------------------------------------------------------
# a route: the pieces in order and direction, the lot as the measured band, the oval as its mid-surface line

MIN_RUN = 20         # a reading's run shorter than this (m) is junction flicker, not a piece of the route
LOT_PIECES = ("ring_nw", "ring_ne", "ring_s")
LOT_ENDS = ("LOTN", "LOTW")      # the band, the long way round: in off diag south, out onto the bottom road


def sequence(runs):
    """A reading's runs -> [(piece, dir)]: flicker dropped, the lot's ring pieces as one 'LOT', repeats merged."""
    seq = []
    for r in runs:
        if r["n_m"] < MIN_RUN:
            continue
        p = "LOT" if r["piece"] in LOT_PIECES else r["piece"]
        if seq and seq[-1][0] == p:
            continue
        seq.append((p, r["dir"]))
    return seq


def ends_of(p, dr):
    a, b = LOT_ENDS if p == "LOT" else routes.ENDS[p]
    return (a, b) if dr > 0 else (b, a)


def complete(seq, closed):
    """Insert the connector piece where consecutive pieces do not share a junction (a 16 m piece such as c_road.b is
    shorter than MIN_RUN and falls out of a reading), and split pieces' halves for unsplit names."""
    out = []
    pairs = list(zip(seq, seq[1:] + (seq[:1] if closed else [])))
    for (a, da), (b, db) in pairs:
        out.append((a, da))
        ea = ends_of(a, da)[1]; sb = ends_of(b, db)[0]
        if ea == sb:
            continue
        hit = [(k, 1) for k, (x, y) in routes.ENDS.items() if (x, y) == (ea, sb)] + \
              [(k, -1) for k, (x, y) in routes.ENDS.items() if (y, x) == (ea, sb)]
        if len(hit) != 1:
            raise ValueError(f"no single connector {a}->{b} ({ea}->{sb}): {hit}")
        out.append(hit[0])
    if not closed:
        out.append(seq[-1])
    return out


def assemble(seq, net, band, Pp, oval_ends=None):
    """The route's centre line, in order. oval_ends: (iSF, iNE, iNW) mid-line indices for a road-course lap that
    starts at the start/finish; None for an infield-only loop. Returns the closed lap (1 m) and every join."""
    parts = []
    if oval_ends:
        iSF, iNE, iNW = oval_ends
        n = len(net.mid)
        parts.append(("oval S/F->NE", net.mid[np.arange(iSF, iNE + (n if iNE < iSF else 0) + 1) % n]))
    lot_run = band["run"]
    for p, dr in seq:
        if p == "LOT":
            parts.append(("LOT", None))
        else:
            Q = Pp[p]
            parts.append((p, Q if dr > 0 else Q[::-1]))
    if oval_ends:
        parts.append(("oval NW->S/F", net.mid[np.arange(iNW, iSF + (n if iSF < iNW else 0) + 1) % n]))
    # the lot: the band's well-seen run, cut where it passes nearest the neighbouring pieces' ends
    for k, (p, Q) in enumerate(parts):
        if p != "LOT":
            continue
        prev = parts[k - 1][1][-1]; nxt = parts[(k + 1) % len(parts)][1][0]
        C = band["centre"]
        a, b = lot_run
        h = (a + b) // 2        # the lot's two junctions stand ~50 m apart across its short side: search each half
        i0 = a + int(np.argmin(np.hypot(*(C[a:h + 1] - prev).T)))
        i1 = h + int(np.argmin(np.hypot(*(C[h:b + 1] - nxt).T)))
        parts[k] = ("LOT", C[i0:i1 + 1])
    joins = []
    for k in range(len(parts) - (0 if not oval_ends else 1)):
        (pa, A), (pb, B) = parts[k], parts[(k + 1) % len(parts)]
        joins.append(dict(after=pa, before=pb, gap_m=round(float(np.hypot(*(A[-1] - B[0]))), 1),
                          bridge=bool(pa == "LOT" or pb == "LOT")))
    lap = np.vstack([Q for _, Q in parts])
    lap = naip.resample(lap, 1.0, closed=True)
    return lap, parts, joins


def lap_len(L):
    return float(naip.cumlen(np.vstack([L, L[:1]]))[-1])


def station_on(L, p):
    s = naip.cumlen(L)
    d = np.hypot(*(L - np.asarray(p, float)).T)
    i = int(np.argmin(d))
    return float(s[i]), float(d[i]), i


def piece_at(parts, L, i):
    """Which part of the assembled route lap index i falls on."""
    p = L[i]
    best = min(((float(np.min(np.hypot(*(Q - p).T))), name) for name, Q in parts), key=lambda z: z[0])
    return best[1]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ref = aerial_reference()
    net = Network(ref)
    Pp = routes.split_pieces(net.P)
    _, nodes = routes.nodes_of(Pp)
    res = {"_doc": __doc__.strip().splitlines()[0], "maps": {}, "routes": {}}
    M = {}
    for key in ("scca", "rc"):
        m = load_map(key)
        A, sols = register(key, m, ref)
        z = choose(sols)
        aff = affine_residual(A, ref, z["T"])
        cyc = course_cycle(key, m, z["T"], net)
        Q0, runs0, _, _ = net.read(cyc["lap"], tol=3.0, closed=True)
        lap, fix, refit = local_refit(Q0, net, nodes["TOP"])
        # applied only where the map's line is off the measured roads there (median > 3 m): SCCA draws the top hairpin
        # as a loop out over the N road; the RC map's line already lies on the hairpin (median 0.6 m) and is kept
        refit["applied"] = refit["to_pieces_before_m"]["p50"] > 3.0
        if not refit["applied"]:
            lap, fix = Q0, (lambda P: np.atleast_2d(np.asarray(P, float)))
        Q, runs, d, onp = net.read(lap, tol=3.0, closed=True)
        labs = label_points(key, m)
        lab_en = {k: fix(sc.apply(z["T"], np.array(p, float)))[0] for k, p in labs.items()}
        M[key] = dict(lap=Q, raw=Q0, runs=runs, labels=lab_en, pit=[fix(P) for P in cyc["pit"]], m=m, T=z["T"])
        res["maps"][key] = dict(
            file=MAP[key]["file"], title=MAP[key]["title"], direction_as_drawn=MAP[key]["direction"],
            registration=dict(det=z["det"], scale_m_per_px=round(z["scale_m_per_px"], 4), angle_deg=round(z["angle_deg"], 2),
                              outline_to_wall_face_m=dict(rms=round(z["rms"], 2), p50=round(z["p50"], 2),
                                                          p95=round(z["p95"], 2), max=round(z["max"], 2)),
                              sf_miss_m=round(z["sf_miss_m"], 1), infield_labels_miss_m=round(z["infield_miss_m"], 1),
                              solutions_tried=len(sols),
                              runner_up=[dict(det=s_["det"], angle_deg=round(s_["angle_deg"], 1), rms=round(s_["rms"], 2),
                                              sf_miss_m=round(s_["sf_miss_m"], 1),
                                              infield_labels_miss_m=round(s_["infield_miss_m"], 1)) for s_ in sols[:4]],
                              affine=dict(rms=round(aff["rms"], 2), p95=round(aff["p95"], 2), scale_ratio=round(aff["scale_ratio"], 3))),
            map_line_m=round(lap_len(Q), 1), top_hairpin_refit=refit,
            reading_before_refit=[(r["piece"], r["n_m"], r["dir"], r["dist_p50_m"], r["off_pavement_m"]) for r in runs0],
            reading=runs, sequence=sequence(runs))
        print(key, "reg rms", round(z["rms"], 2), "sf miss", round(z["sf_miss_m"], 1), "refit", refit)
        print("  ", [(r["piece"], r["n_m"], r["dir"], r["dist_p50_m"], r["off_pavement_m"]) for r in runs])
    seqs = {k: [x for x in res["maps"][k]["sequence"] if x[0] != "oval"] for k in M}
    agree = seqs["scca"] == seqs["rc"]
    print("sequences agree:", agree, seqs)
    rc_seq = seqs["rc"]
    # the lot band, measured along the RC map's line through the lot (+-15 m of map line past its ring runs)
    rr = [r for r in M["rc"]["runs"] if r["piece"] in LOT_PIECES]
    a = max(0, rr[0]["line_from_m"] - 15); b = rr[-1]["line_to_m"] + 15
    band = lot_band(M["rc"]["lap"][a:b + 1], net.lot)
    ok = band["in_lot"] & (band["held_m"] <= 5)
    lab_, nr = ndimage.label(ok)
    sizes = ndimage.sum(ok, lab_, range(1, nr + 1))
    j = 1 + int(np.argmax(sizes))
    idx = np.where(lab_ == j)[0]
    band["run"] = (int(idx[0]), int(idx[-1]))
    run = slice(idx[0], idx[-1] + 1)
    res["lot_band"] = dict(
        sections=len(band["line"]), in_lot=int(band["in_lot"].sum()),
        seen=int(band["seen"].sum()), seen_in_used_run=int(band["seen"][run].sum()), used_run_m=int(idx[-1] - idx[0] + 1),
        unseen_reasons={w: band["why"].count(w) for w in sorted(set(band["why"])) if w},
        width_m=dict(p10=round(float(np.percentile(band["width"][run], 10)), 2), p50=round(float(np.median(band["width"][run])), 2),
                     p90=round(float(np.percentile(band["width"][run], 90)), 2)),
        limit_residual_m=dict(p50=round(float(np.median(band["residual_abs"])), 2),
                              p95=round(float(np.percentile(band["residual_abs"], 95)), 2)),
        depth_grey=dict(inner_p50=round(float(np.nanmedian(band["depth_lo"][run])), 1),
                        outer_p50=round(float(np.nanmedian(band["depth_hi"][run])), 1)),
        held_max_m=int(band["held_m"][run].max()),
        centre_en_m=np.round(band["centre"][run], 2).tolist())
    # the oval: S/F, NE diverge, NW merge on the mid-surface line
    iSF = int(np.argmin(np.hypot(*(net.mid - sf_aerial()).T)))
    iNE = int(np.argmin(np.hypot(*(net.mid - Pp["ne_lane"][0]).T)))
    iNW = int(np.argmin(np.hypot(*(net.mid - Pp["arc_nw"][0]).T)))
    seq_rc = complete(rc_seq, closed=False)
    lap, parts, joins = assemble(seq_rc, net, band, Pp, oval_ends=(iSF, iNE, iNW))
    L_rc = lap_len(lap)
    nj = len(joins)
    corners = {}
    for key in ("rc", "scca"):
        for k, p in M[key]["labels"].items():
            # the label's corner = the map line's nearest point; that point's station on the assembled lap
            mp = M[key]["lap"][int(np.argmin(np.hypot(*(M[key]["lap"] - p).T)))]
            s, dd, i = station_on(lap, mp)
            num = k.lstrip("T")
            corners.setdefault(num, {})[key] = dict(s_m=round(s, 1), label_to_line_m=round(float(np.hypot(*(mp - p))), 1),
                                                     line_to_route_m=round(dd, 1), on=piece_at(parts, lap, i),
                                                     en_m=np.round(lap[i], 1).tolist())
    for num, v in corners.items():
        if "rc" in v and "scca" in v:
            ds = abs(v["rc"]["s_m"] - v["scca"]["s_m"]); ds = min(ds, L_rc - ds)
            v["rc_minus_scca_m"] = round(ds, 1)
    res["routes"]["RC-D"] = dict(
        name="road course (both published maps): oval from S/F, turns 1-2 = T1, back stretch, NE lane, top hairpin, "
             "diag, round the skid pad lot the long way on its driven band, bottom road, west road, sweeper, NW merge",
        direction="counter-clockwise (both maps' arrows)", pieces=[[p, d_] for p, d_ in seq_rc],
        maps_agree_on_pieces=agree, lap_m=round(L_rc, 1), uncertainty_m=round(routes.J_EPS * nj, 0),
        vs_published_m=[round(L_rc - routes.PUBLISHED[0], 1), round(L_rc - routes.PUBLISHED[1], 1)],
        part_m={p: round(float(naip.cumlen(Q)[-1]), 1) for p, Q in parts}, joins=joins,
        start_finish=dict(mid_s_m=round(float(net.smid[iSF]), 1), en_m=np.round(net.mid[iSF], 1).tolist()),
        corners=dict(sorted(corners.items(), key=lambda kv: int(kv[0]))),
        centre_en_m=np.round(lap, 2).tolist())
    print("RC-D", round(L_rc, 1), joins)
    for num, v in sorted(corners.items(), key=lambda kv: int(kv[0])):
        print("  T" + num, v)
    # the infield-only layout: Kevin's stroke gives its SHAPE (which pieces); its direction is the published road
    # course's on the pieces they share (Kevin 2026-11-07: "Do them as published, i just drew shape")
    sk = json.loads(SKETCH.read_text())
    pts = np.array(sk["strokes"][0]["pts"], float).reshape(-1, 2)
    e, n_ = naip.px_to_en(pts[:, 0], pts[:, 1])
    Qs, runs_s, _, _ = net.read(np.c_[e, n_], tol=3.0, closed=True)
    seq_s = sequence(runs_s)
    if seq_s[0][0] == seq_s[-1][0]:
        seq_s = seq_s[:-1]
    rcdir = dict(rc_seq)
    shared = [(p, d_) for p, d_ in seq_s if p in rcdir and p != "LOT"]
    flip = sum(1 for p, d_ in shared if d_ != rcdir[p]) > len(shared) / 2
    if flip:
        seq_s = [(p, -d_) for p, d_ in seq_s[::-1]]
    assert dict(seq_s).get("LOT", 1) == rcdir["LOT"], "the lot band runs one way: the road course's"
    # start where the road course's order puts the first shared piece
    i0 = next(i for i, (p, _) in enumerate(seq_s) if p == rc_seq[0][0] or p == "diag_n")
    seq_s = seq_s[i0:] + seq_s[:i0]
    seq_if = complete(seq_s, closed=True)
    lap_if, parts_if, joins_if = assemble(seq_if, net, band, Pp)
    L_if = lap_len(lap_if)
    on_if = {}
    for num, v in corners.items():
        s, dd, i = station_on(lap_if, v["rc"]["en_m"] if "rc" in v else v["scca"]["en_m"])
        if dd < 3:
            on_if["T" + num] = round(s, 1)
    res["routes"]["IF-K"] = dict(
        name="infield only (Kevin's shape): diag, round the lot the long way, bottom road, S-curve, C road east",
        direction="as the published road course runs on the shared pieces (diag, lot, bottom road); "
                  "the stroke was drawn %s" % ("the other way" if flip else "the same way"),
        stroke_reading=[(r["piece"], r["n_m"], r["dir"], r["dist_p50_m"], r["off_pavement_m"]) for r in runs_s],
        pieces=[[p, d_] for p, d_ in seq_if], lap_m=round(L_if, 1), uncertainty_m=round(routes.J_EPS * len(joins_if), 0),
        part_m={p: round(float(naip.cumlen(Q)[-1]), 1) for p, Q in parts_if}, joins=joins_if,
        published_corners_on_it=on_if, centre_en_m=np.round(lap_if, 2).tolist())
    print("IF-K", round(L_if, 1), seq_if, joins_if, on_if, "flip", flip)
    (HERE / "route_from_maps.naip.json").write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    stills(res, M, net, band, lap, lap_if, corners)
    return res


SKETCH = Path(os.environ.get("PPIR_SKETCH", "/Volumes/Drive/codex/pp_work/sketch/routes/infield_only.json"))


def stills(res, M, net, band, lap, lap_if, corners):
    from PIL import ImageDraw, ImageFont
    im = naip.image()
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        font = small = ImageFont.load_default()

    def canvas(x0, y0, x1, y1, k, dim=0.75):
        o = Image.fromarray((im[y0:y1, x0:x1] * dim).astype(np.uint8))
        return o.resize((int(o.width * k), int(o.height * k)), Image.LANCZOS)

    def line(dr, P, x0, y0, k, col, w):
        px, py = naip.en_to_px(P[:, 0], P[:, 1])
        dr.line(list(zip((px - x0) * k, (py - y0) * k)), fill=col, width=w)
    # 1. the whole route
    px, py = naip.en_to_px(lap[:, 0], lap[:, 1])
    x0, y0 = int(max(0, px.min() - 60)), int(max(0, py.min() - 60))
    x1, y1 = int(min(im.shape[1], px.max() + 60)), int(min(im.shape[0], py.max() + 60))
    k = 0.75
    o = canvas(x0, y0, x1, y1, k, 0.6); dr = ImageDraw.Draw(o)
    line(dr, M["scca"]["lap"], x0, y0, k, (255, 220, 0), 1)
    line(dr, M["rc"]["lap"], x0, y0, k, (255, 140, 0), 1)
    line(dr, np.vstack([lap_if, lap_if[:1]]), x0, y0, k, (0, 229, 255), 5)
    line(dr, np.vstack([lap, lap[:1]]), x0, y0, k, (255, 40, 40), 3)
    for num, v in corners.items():
        if "rc" not in v:
            continue
        x, y = naip.en_to_px(*v["rc"]["en_m"])
        x, y = (x - x0) * k, (y - y0) * k
        dr.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(255, 140, 0), outline=(0, 0, 0))
        dr.text((x - 6, y - 12), num, fill=(0, 0, 0), font=font)
    sf = res["routes"]["RC-D"]["start_finish"]["en_m"]
    x, y = naip.en_to_px(*sf)
    dr.rectangle(((x - x0) * k - 8, (y - y0) * k - 8, (x - x0) * k + 8, (y - y0) * k + 8), fill=(255, 255, 255), outline=(0, 0, 0))
    r = res["routes"]
    txt = [f"RC-D road course (red, CCW): {r['RC-D']['lap_m']:.0f} m +-{r['RC-D']['uncertainty_m']:.0f} "
           f"(published 2,074 / 2,116)", f"infield only (cyan, same direction): {r['IF-K']['lap_m']:.0f} m",
           "thin: the SCCA (yellow) and racingcircuits.info (orange) map lines as registered; discs: T1-T9 (rc map)",
           "white square: start/finish painted on the front stretch"]
    for i, t_ in enumerate(txt):
        dr.text((20, 20 + 24 * i), t_, fill=(255, 255, 255), font=small, stroke_width=2, stroke_fill=(0, 0, 0))
    o.save(HERE / "still_route_from_maps.jpg", quality=85)
    # 2. the lot band
    x0, y0, x1, y1 = 700, 650, 1350, 1250
    k = 2
    o = canvas(x0, y0, x1, y1, k, 0.9); dr = ImageDraw.Draw(o)
    line(dr, band["line"], x0, y0, k, (255, 140, 0), 1)
    a, b = band["run"]
    for key, col in (("lo", (0, 255, 0)), ("hi", (0, 160, 255))):
        line(dr, (band["line"] + band[key][:, None] * band["left"])[a:b + 1], x0, y0, k, col, 2)
    line(dr, lap, x0, y0, k, (255, 40, 40), 2)
    dr.text((20, 20), "lot band: limits green / blue (seen run), route red, RC map line orange", fill=(255, 255, 255),
            font=small, stroke_width=2, stroke_fill=(0, 0, 0))
    o.save(OUT / "lot_band.jpg", quality=88)
    # 3. the top hairpin, before / after the local refit
    x0, y0, x1, y1 = 650, 200, 1150, 650
    k = 2
    o = canvas(x0, y0, x1, y1, k, 0.8); dr = ImageDraw.Draw(o)
    for key, c0, c1 in (("scca", (120, 100, 0), (255, 220, 0)), ("rc", (120, 60, 0), (255, 140, 0))):
        line(dr, M[key]["raw"], x0, y0, k, c0, 2)
        line(dr, M[key]["lap"], x0, y0, k, c1, 2)
    line(dr, lap, x0, y0, k, (255, 40, 40), 2)
    dr.text((20, 20), "top hairpin: map lines as registered (dark) and refit locally (bright); route red", fill=(255, 255, 255),
            font=small, stroke_width=2, stroke_fill=(0, 0, 0))
    o.save(OUT / "top_hairpin_refit.jpg", quality=88)


if __name__ == "__main__":
    main()
