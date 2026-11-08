"""Reading a published (schematic) track map against a measured aerial (ledger 0085, "Route from the published maps").

General helpers, nothing PPIR-specific: the map is a selection aid (fleet/LAWS.md L1). Its ink says WHICH measured
pavement the lap uses and in which order; its pixels are never coordinates for geometry.

  ink masks       colour classes of a flat-colour map (course / unused pavement / labels)
  outer_contour   the outline of the map's drawing of a closed facility (an oval's outer wall)
  fit_similarity  map px -> ENU metres: rotation + uniform scale + translation (Umeyama), by ICP of the outline onto a
                  measured reference polyline; both handednesses are tried and reported (a map can be mirrored)
  thin, paths     a course band -> its centre line (Zhang-Suen thinning) -> ordered pixel paths between ends/branches
  warp            the map laid onto the aerial with a fitted transform (for the eye, never for measurement)

Pixel convention: (x right, y down). An image laid north-up on the ground maps (x, y) -> (E, N) with det -1; that is the
UNMIRRORED placement ("proper"). det +1 means the map would have to be flipped to fit.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


def outer_contour(mask, close=3):
    """Pixels on the outer boundary of the largest blob of `mask` (holes filled), as (x, y) float, and the filled blob."""
    m = ndimage.binary_closing(mask, iterations=close) if close else mask
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    big = lab == (1 + int(np.argmax(sizes)))
    f = ndimage.binary_fill_holes(big)
    edge = f & ~ndimage.binary_erosion(f)
    y, x = np.nonzero(edge)
    return np.c_[x, y].astype(float), f


def umeyama(A, B, det_sign=-1):
    """s, R, t with B ~ s R A + t (least squares), R constrained to det(R) = det_sign."""
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


def invert(T, Q):
    s, R, t = T
    return (np.asarray(Q, float) - t) @ np.linalg.inv(s * R).T


def icp(A, ref, init, det_sign, iters=80, trim=2.0):
    """Similarity ICP of points A onto the dense reference polyline points `ref`; returns (s, R, t), residuals (m)."""
    T = init
    tree = cKDTree(ref)
    for _ in range(iters):
        d, j = tree.query(apply(T, A))
        keep = d < max(np.percentile(d, 90) * trim, 3.0)
        T = umeyama(A[keep], ref[j[keep]], det_sign)
    d, _ = tree.query(apply(T, A))
    return T, d


def initial(A, ref, rot_deg, det_sign):
    """A start: centroids matched, RMS radii matched, rotated by rot_deg, with the requested handedness."""
    th = np.radians(rot_deg)
    Rr = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    R = Rr @ np.diag([1.0, -1.0]) if det_sign < 0 else Rr
    s = np.sqrt(((ref - ref.mean(0)) ** 2).sum(1).mean()) / np.sqrt(((A - A.mean(0)) ** 2).sum(1).mean())
    return s, R, ref.mean(0) - s * R @ A.mean(0)


def fit_similarity(A, ref, checks=None, step_deg=10):
    """Every start rotation, both handednesses. Returns a list of distinct local optima, best first:
    dict(T, det, rms, p50, p95, max, angle_deg, scale_m_per_px, checks={name: ENU}).
    `checks`: {name: (x, y) map px}, transformed for the caller to judge (e.g. the start/finish line)."""
    sols = []
    for det in (-1, 1):
        for rot in range(-180, 180, step_deg):
            T, d = icp(A, ref, initial(A, ref, rot, det), det)
            s, R, t = T
            if s <= 0 or not np.isfinite(s):
                continue
            ang = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
            rms = float(np.sqrt((d ** 2).mean()))
            dup = [z for z in sols if z["det"] == det and abs((z["angle_deg"] - ang + 180) % 360 - 180) < 3]
            if dup:
                if rms < dup[0]["rms"]:
                    sols.remove(dup[0])
                else:
                    continue
            sols.append(dict(T=T, det=det, rms=rms, p50=float(np.median(d)), p95=float(np.percentile(d, 95)),
                             max=float(d.max()), angle_deg=ang, scale_m_per_px=float(s),
                             checks={k: apply(T, np.array(v, float)).tolist() for k, v in (checks or {}).items()}))
    return sorted(sols, key=lambda z: z["rms"])


def thin(mask):
    """Zhang-Suen thinning (one-pixel 8-connected centre line of a band)."""
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
    """Per skeleton pixel: 1 at an end, 2 along a path, >= 3 at a branch. Counted as the 0->1 transitions round the
    8-neighbourhood (the crossing number), so a thinned diagonal staircase is not taken for a branch."""
    p = np.pad(sk.astype(np.uint8), 1)
    ring = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    P = [np.roll(np.roll(p, -dy, 0), -dx, 1)[1:-1, 1:-1] for dy, dx in ring]
    cross = sum(((P[i] == 0) & (P[(i + 1) % 8] == 1)).astype(np.uint8) for i in range(8))
    n = sum(P)
    d = np.where(cross >= 3, cross, 2)
    d = np.where((n == 1) | ((n >= 2) & (cross == 1)), 1, d)   # an end, or the tip of a 2-pixel-thick end
    d = np.where(n == 0, 0, d)
    return np.where(sk, d, 0)


def prune(sk, length):
    """Remove spurs (end -> branch runs) shorter than `length` px, repeatedly."""
    sk = sk.copy()
    for _ in range(4):
        deg = degree(sk)
        ends = list(zip(*np.nonzero((deg == 1))))
        removed = False
        for e in ends:
            run = [e]; prev = None; cur = e
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
    """Walk an 8-connected skeleton from `start` (y, x) until an end or a branch; returns [(x, y), ...]."""
    out = [start]; seen = {start}; cur = start
    while True:
        nb = [(cur[0] + dy, cur[1] + dx) for dy, dx in _N8
              if 0 <= cur[0] + dy < sk.shape[0] and 0 <= cur[1] + dx < sk.shape[1] and sk[cur[0] + dy, cur[1] + dx]
              and (cur[0] + dy, cur[1] + dx) not in seen]
        if not nb:
            break
        # prefer 4-neighbours (Zhang-Suen leaves diagonal staircases)
        nb.sort(key=lambda q: abs(q[0] - cur[0]) + abs(q[1] - cur[1]))
        cur = nb[0]; seen.add(cur); out.append(cur)
    return np.array([(x, y) for y, x in out], float)


def warp(aerial_rgb, px_to_en, T, mapimg, alpha=0.55, step=1, ink_below=235, dim=0.8):
    """The map laid over the aerial: for each aerial pixel, its ENU -> map px (inverse of T); map ink (any channel under
    `ink_below`) blended at `alpha`, the aerial dimmed by `dim` elsewhere. Nearest-neighbour sampling."""
    H, W = aerial_rgb.shape[:2]
    ys, xs = np.mgrid[0:H:step, 0:W:step]
    e, n = px_to_en(xs.ravel(), ys.ravel())
    m = invert(T, np.c_[e, n])
    mx = m[:, 0].reshape(xs.shape); my = m[:, 1].reshape(xs.shape)
    ok = (mx >= 0) & (my >= 0) & (mx <= mapimg.shape[1] - 1) & (my <= mapimg.shape[0] - 1)
    xi = np.clip(np.rint(mx), 0, mapimg.shape[1] - 1).astype(int)
    yi = np.clip(np.rint(my), 0, mapimg.shape[0] - 1).astype(int)
    samp = mapimg[yi, xi].astype(np.float32)
    base = aerial_rgb[::step, ::step].astype(np.float32)
    ink = ok & (samp.min(-1) < ink_below)
    o = base * dim
    o[ink] = base[ink] * (1 - alpha) + samp[ink] * alpha
    return o.clip(0, 255).astype(np.uint8)
