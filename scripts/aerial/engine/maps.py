"""A published (schematic) track map read against the measured aerial: ink, registration, course line, labels.

Generalised from tracks/pikes-peak/source/road-course/schematic.py + maps_route.py (ledger 0085). Kevin, 2026-11-07:
"Why aren't you using actual track maps?" / "Stop guessing". A map is a selection aid (fleet/LAWS.md L1): its ink says
WHICH pavement the lap uses, in which order and direction; its pixels never become coordinates. The course line it
yields only guides the measurement (route.py) and is reported against the measured result.

Per map, from the engine config (data only: file, ink colours, rows to drop, the S/F and label pixels, the published
direction, pixels on ink that is NOT the course such as a pit lane drawn in the course colour):

  ink           colour rules -> the course band and the facility's other drawn pavement;
  registration  the map's outer outline (course | other ink, holes filled) onto a measured reference polyline (a lidar
                edge, else the aerial's pavement outline) by similarity ICP (rotation + uniform scale + translation,
                Umeyama) from every STEP_DEG start, BOTH handednesses; near-equal outline fits (a near-symmetric
                facility fits its mirror almost as well) are decided by where the map's course line lands: the fit that
                puts most of it on measured pavement, then the S/F; every solution tried is reported;
  course line   the band thinned (Zhang-Suen), spurs pruned, the skeleton graph's edges chained into one closed loop
                after dropping edges through ``exclude_px``; oriented to the published direction; started at the S/F;
  local refit   where a schematic draws a corner fatter than the road (Pikes Peak SCCA's top hairpin, a loop out over
                the N road), the line is off measured pavement: there the line within R_IN m is refit by a PROPER
                similarity ICP onto the pavement's medial points within R_REF m (no road preferred), blended out by
                R_OUT m;
  labels        corner labels -> the course line's nearest point (a station is good to a corner's length, not an apex).
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

from . import geom

STEP_DEG = 10
R_IN, R_OUT, R_REF = 50.0, 80.0, 110.0
REFIT_OFF_FRAC = 0.5      # a stretch counts as off pavement when this share of it is off the (1 m dilated) mask
REFIT_MIN_M = 15.0
REFIT_SCALE = (0.85, 1.15)   # [invented] a schematic's local drawing error is a few per cent of scale, not more
REFIT_ROT_DEG = 20.0


# --- ink -----------------------------------------------------------------------------------------------------------

def _atom(im, a):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    m = np.ones(r.shape, bool)
    if "rgb_min" in a:
        lo = a["rgb_min"]
        m &= (r >= lo[0]) & (g >= lo[1]) & (b >= lo[2])
    if "rgb_max" in a:
        hi = a["rgb_max"]
        m &= (r <= hi[0]) & (g <= hi[1]) & (b <= hi[2])
    if "max_spread" in a:
        k = a["max_spread"]
        m &= (np.abs(g - r) < k) & (np.abs(b - r) < k)
    if "min_of_rgb" in a:
        mn = np.minimum(r, np.minimum(g, b))
        m &= (mn >= a["min_of_rgb"][0]) & (mn <= a["min_of_rgb"][1])
    if a.get("open"):
        m = ndimage.binary_opening(m, structure=np.ones((a["open"], a["open"])))
    return m


def ink(im, rule):
    m = np.zeros(im.shape[:2], bool)
    for a in rule.get("any", [rule]):
        m |= _atom(im, a)
    if rule.get("fill_holes_below"):
        holes = ndimage.binary_fill_holes(m) & ~m
        lab, n = ndimage.label(holes)
        if n:
            sz = ndimage.sum(holes, lab, range(1, n + 1))
            m |= np.isin(lab, 1 + np.flatnonzero(sz < rule["fill_holes_below"]))
    if rule.get("close"):
        m = ndimage.binary_closing(m, iterations=rule["close"])
    if rule.get("open"):
        m = ndimage.binary_opening(m, structure=np.ones((rule["open"], rule["open"])))
    return m


def load(spec: dict, path) -> dict:
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
    course = ink(im, spec["ink"]["course"])
    other = ink(im, spec["ink"]["other"]) if spec["ink"].get("other") else np.zeros_like(course)
    k = int(spec.get("drop_rows_above", 0))
    if k:
        course[:k] = False
        other[:k] = False
    sf = spec.get("sf_px")
    if sf:   # a start / finish flag drawn ON the band: close the band through it
        rad = int(spec.get("sf_close_px", 8))
        yy, xx = np.mgrid[0:course.shape[0], 0:course.shape[1]]
        course |= (np.hypot(xx - sf[0], yy - sf[1]) < rad) & ndimage.binary_dilation(course, iterations=rad)
    return {"im": im.astype(np.uint8), "course": course, "other": other}


# --- registration ----------------------------------------------------------------------------------------------------

def outer_contour(mask, close=3):
    m = ndimage.binary_closing(mask, iterations=close) if close else mask
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    big = lab == (1 + int(np.argmax(sizes)))
    f = ndimage.binary_fill_holes(big)
    edge = f & ~ndimage.binary_erosion(f)
    y, x = np.nonzero(edge)
    return np.c_[x, y].astype(float)


def umeyama(A, B, det_sign=-1):
    ma, mb = A.mean(0), B.mean(0)
    A0, B0 = A - ma, B - mb
    C = B0.T @ A0 / len(A)
    U, S, Vt = np.linalg.svd(C)
    D = np.eye(2)
    if np.sign(np.linalg.det(U @ Vt)) != det_sign:
        D[1, 1] = -1
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (A0 ** 2).sum(1).mean()
    return s, R, mb - s * R @ ma


def apply(T, P):
    s, R, t = T
    return s * np.asarray(P, float) @ R.T + t


def icp(A, ref, init, det_sign, iters=80, trim=2.0):
    T = init
    tree = cKDTree(ref)
    for _ in range(iters):
        d, j = tree.query(apply(T, A))
        keep = d < max(np.percentile(d, 90) * trim, 3.0)
        T = umeyama(A[keep], ref[j[keep]], det_sign)
    d, _ = tree.query(apply(T, A))
    return T, d


def _initial(A, ref, rot_deg, det_sign):
    th = np.radians(rot_deg)
    Rr = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    R = Rr @ np.diag([1.0, -1.0]) if det_sign < 0 else Rr
    s = np.sqrt(((ref - ref.mean(0)) ** 2).sum(1).mean()) / np.sqrt(((A - A.mean(0)) ** 2).sum(1).mean())
    return s, R, ref.mean(0) - s * R @ A.mean(0)


def fit_similarity(A, ref, step_deg=STEP_DEG):
    """Every start rotation, both handednesses -> distinct local optima, best outline fit first.
    det -1 = the map laid north-up-like without a flip (image y down, ENU N up); det +1 = the map mirrored."""
    sols = []
    for det in (-1, 1):
        for rot in range(-180, 180, step_deg):
            T, d = icp(A, ref, _initial(A, ref, rot, det), det)
            s, R, _ = T
            if s <= 0 or not np.isfinite(s):
                continue
            ang = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
            rms = float(np.sqrt((d ** 2).mean()))
            dup = [z for z in sols if z["det"] == det and abs((z["angle_deg"] - ang + 180) % 360 - 180) < 3]
            if dup:
                if rms < dup[0]["rms"]:
                    sols = [q for q in sols if q is not dup[0]]
                else:
                    continue
            sols.append(dict(T=T, det=det, rms=rms, p50=float(np.median(d)), p95=float(np.percentile(d, 95)),
                             max=float(d.max()), angle_deg=ang, scale_m_per_px=float(s)))
    return sorted(sols, key=lambda z: z["rms"])


def affine_residual(A, ref, T):
    """The outline fitted by a full affine from the chosen solution: how much of the residual is the map's own
    stretch (a schematic drawn fatter one way) rather than noise; axis ratio reported."""
    tree = cKDTree(ref)
    M = np.c_[A, np.ones(len(A))]
    B = apply(T, A)
    X = None
    for _ in range(40):
        _, j = tree.query(B)
        X, *_ = np.linalg.lstsq(M, ref[j], rcond=None)
        B = M @ X
    d, _ = tree.query(B)
    S = np.linalg.svd(X[:2].T, compute_uv=False)
    return {"rms": round(float(np.sqrt((d ** 2).mean())), 2), "p95": round(float(np.percentile(d, 95)), 2),
            "axis_ratio": round(float(S[0] / S[1]), 3)}


# --- course line -------------------------------------------------------------------------------------------------------

def thin(mask):
    m = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(m, -dy, 0), -dx, 1) for dy, dx in
                 ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            B = sum(P)
            seq = P + [P[0]]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c = (P[0] * P[2] * P[4] == 0) & (P[2] * P[4] * P[6] == 0)
            else:
                c = (P[0] * P[2] * P[6] == 0) & (P[0] * P[4] * P[6] == 0)
            rm = (m == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                m[rm] = 0
                changed = True
        if not changed:
            break
    return m[1:-1, 1:-1].astype(bool)


_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def degree(sk):
    p = np.pad(sk.astype(np.uint8), 1)
    ring = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    P = [np.roll(np.roll(p, -dy, 0), -dx, 1)[1:-1, 1:-1] for dy, dx in ring]
    cross = sum(((P[i] == 0) & (P[(i + 1) % 8] == 1)).astype(np.uint8) for i in range(8))
    n = sum(P)
    d = np.where(cross >= 3, cross, 2)
    d = np.where((n == 1) | ((n >= 2) & (cross == 1)), 1, d)
    d = np.where(n == 0, 0, d)
    return np.where(sk, d, 0)


def prune(sk, length):
    sk = sk.copy()
    for _ in range(4):
        deg = degree(sk)
        removed = False
        for e in zip(*np.nonzero(deg == 1)):
            run = [e]
            prev, cur = None, e
            while len(run) <= length:
                nb = [(cur[0] + dy, cur[1] + dx) for dy, dx in _N8
                      if 0 <= cur[0] + dy < sk.shape[0] and 0 <= cur[1] + dx < sk.shape[1] and sk[cur[0] + dy, cur[1] + dx]
                      and (cur[0] + dy, cur[1] + dx) != prev and (cur[0] + dy, cur[1] + dx) not in run]
                if len(nb) != 1:
                    break
                prev, cur = cur, nb[0]
                if deg[cur] >= 3:
                    break
                run.append(cur)
            if len(run) <= length and deg[cur] >= 3:
                for q in run:
                    sk[q] = False
                removed = True
        if not removed:
            break
    return sk


def trace(sk, start):
    out = [start]
    seen = {start}
    cur = start
    while True:
        nb = [(cur[0] + dy, cur[1] + dx) for dy, dx in _N8
              if 0 <= cur[0] + dy < sk.shape[0] and 0 <= cur[1] + dx < sk.shape[1] and sk[cur[0] + dy, cur[1] + dx]
              and (cur[0] + dy, cur[1] + dx) not in seen]
        if not nb:
            break
        nb.sort(key=lambda q: abs(q[0] - cur[0]) + abs(q[1] - cur[1]))
        cur = nb[0]
        seen.add(cur)
        out.append(cur)
    return np.array([(x, y) for y, x in out], float)


def skeleton_graph(course, spur_px):
    sk = prune(thin(course), spur_px)
    deg = degree(sk)
    br = ndimage.binary_dilation(deg >= 3, iterations=1) & sk
    blab, nb = ndimage.label(br, structure=np.ones((3, 3)))
    seg = sk & ~br
    slab, ns = ndimage.label(seg, structure=np.ones((3, 3)))
    edges = []
    for i in range(1, ns + 1):
        m = slab == i
        d = degree(m)
        ends = list(zip(*np.nonzero(m & (d <= 1))))
        if not ends:
            ends = [tuple(np.argwhere(m)[0])]
        P = trace(m, ends[0])

        def touch(p):
            x, y = int(p[0]), int(p[1])
            win = blab[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
            v = win[win > 0]
            return int(v[0]) if len(v) else None
        edges.append(dict(px=P, a=touch(P[0]), b=touch(P[-1]), n=len(P)))
    return edges


def course_loop(m: dict, spec: dict):
    """The map's course band -> one closed pixel loop (unoriented), after dropping edges through ``exclude_px``."""
    edges = skeleton_graph(m["course"], int(spec.get("spur_px", 12)))
    edges = [e for e in edges if e["n"] >= 10]
    excl = [np.asarray(p, float) for p in spec.get("exclude_px", [])]
    dropped = []
    keep = []
    for e in edges:
        if any(np.min(np.hypot(*(e["px"] - p).T)) < float(spec.get("exclude_tol_px", 8)) for p in excl):
            dropped.append(int(e["n"]))
        else:
            keep.append(e)
    closed = [e for e in keep if e["a"] is None and e["b"] is None]
    if len(keep) == 1 and closed:
        return keep[0]["px"], {"edges": 1, "dropped_px": dropped}
    keep = [e for e in keep if e["a"] is not None and e["b"] is not None]
    if not keep:
        raise SystemExit("[aerial-engine] the map's course band has no chainable edges")
    pts = [keep[0]["px"]]
    used = {0}
    start, cur = keep[0]["a"], keep[0]["b"]
    while cur != start:
        nxt = [i for i, e in enumerate(keep) if i not in used and cur in (e["a"], e["b"])]
        if len(nxt) != 1:
            raise SystemExit(f"[aerial-engine] the course band is not one loop at junction {cur}: {len(nxt)} ways on "
                             f"(mark the ink that is not the course, e.g. a pit lane, with exclude_px)")
        e = keep[nxt[0]]
        used.add(nxt[0])
        pts.append(e["px"] if e["a"] == cur else e["px"][::-1])
        cur = e["b"] if e["a"] == cur else e["a"]
    if len(used) != len(keep):
        raise SystemExit(f"[aerial-engine] {len(keep) - len(used)} course edges are left over after closing the loop")
    return np.vstack(pts), {"edges": len(keep), "dropped_px": dropped}


def label_points(m: dict, spec: dict) -> dict:
    """Label centres: as given in the config, moved to the centroid of the nearest ``label_ink`` component within
    LABEL_SNAP_PX when a rule is given (a disc or digit's own centre)."""
    labels = {k: np.asarray(v, float) for k, v in spec.get("labels", {}).items()}
    rule = spec.get("label_ink")
    if not rule:
        return labels
    msk = ink(m["im"].astype(np.int32), rule)
    lab, n = ndimage.label(msk)
    if not n:
        return labels
    cents = np.array(ndimage.center_of_mass(msk, lab, range(1, n + 1)))[:, ::-1]
    sizes = ndimage.sum(msk, lab, range(1, n + 1))
    cents = cents[(sizes >= rule.get("min_px", 15)) & (sizes <= rule.get("max_px", 1e12))]
    out = {}
    for k, p in labels.items():
        if len(cents):
            j = int(np.argmin(np.hypot(*(cents - p).T)))
            out[k] = cents[j] if np.hypot(*(cents[j] - p)) < spec.get("label_snap_px", 25) else p
        else:
            out[k] = p
    return out


def choose(sols, on_pave_frac, sf_miss=None):
    """Near-equal outline fits (rms within 1.5x + 2 m of the best) are decided by the share of the course line on
    measured pavement, then the S/F miss."""
    best = sols[0]["rms"]
    near = [z for z in sols if z["rms"] <= 1.5 * best + 2.0]
    for z in near:
        z["on_pavement"] = on_pave_frac(z)
        z["sf_miss_m"] = sf_miss(z) if sf_miss else None
    return max(near, key=lambda z: (round(z["on_pavement"], 2), -(z["sf_miss_m"] or 0), -z["rms"])), near


def local_refit(lap, ref_pts, centre, r_in=R_IN, r_out=R_OUT, r_ref=R_REF):
    d0 = np.hypot(*(lap - centre).T)
    A = lap[d0 < r_in]
    refp = ref_pts[np.hypot(*(ref_pts - centre).T) < r_ref]
    if len(A) < 10 or len(refp) < 10:
        return lap, None
    tree = cKDTree(refp)
    before = tree.query(A)[0]
    T, after = icp(A, refp, (1.0, np.eye(2), np.zeros(2)), det_sign=1)
    s, R, _ = T
    rot = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
    if not (REFIT_SCALE[0] <= s <= REFIT_SCALE[1]) or abs(rot) > REFIT_ROT_DEG:
        # a refit that shrinks, swells or spins the drawn corner is fitting the wrong pavement: refused, reported
        return lap, {"centre_en_m": np.round(centre, 1).tolist(), "refused": True, "scale": round(float(s), 4),
                     "rot_deg": round(rot, 2)}
    w = np.clip((r_out - np.hypot(*(lap - centre).T)) / (r_out - r_in), 0, 1)[:, None]
    out = lap + w * (apply(T, lap) - lap)
    info = dict(centre_en_m=np.round(centre, 1).tolist(), scale=round(float(s), 4),
                rot_deg=round(float(np.degrees(np.arctan2(R[1, 0], R[0, 0]))), 2),
                moves_centre_m=round(float(np.hypot(*(apply(T, centre) - centre))), 2),
                to_pavement_medial_before_m={"p50": round(float(np.median(before)), 2), "p95": round(float(np.percentile(before, 95)), 2)},
                to_pavement_medial_after_m={"p50": round(float(np.median(after)), 2), "p95": round(float(np.percentile(after, 95)), 2)})
    return out, info


def off_pavement_stretches(lap, on_mask_fn, step=1.0):
    """Runs of the (1 m spaced, closed) line whose share off pavement exceeds REFIT_OFF_FRAC over >= REFIT_MIN_M."""
    off = ~on_mask_fn(lap)
    k = int(REFIT_MIN_M / step)
    frac = ndimage.uniform_filter1d(off.astype(float), k, mode="wrap")
    return [(a, b) for a, b in geom.runs(frac > REFIT_OFF_FRAC) if (b - a + 1) * step >= REFIT_MIN_M * 0.5]
