"""Thin low fence lines: non-ground returns BAND over ground with nothing over CANOPY_M within 2 m (not under trees),
chained along a line with a long link (a chain-link's top rail returns are sparse) but only where the chain stays
straight: a RANSAC line per seed neighbourhood. Prints the chains >= MIN_LEN_M with their top, length, returns.
Draws west.png: the candidates over the ground-intensity grid.
python -I fence.py pts.npz hag.npz mf_grid.npz centerline.local.json out.json"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

pts = np.load(sys.argv[1]); hag = np.load(sys.argv[2])["hag"]; G = np.load(sys.argv[3]); loc = json.load(open(sys.argv[4]))
LO, HI, CANOPY_M, LINK_M, TOL_M, MIN_LEN_M = 1.4, 2.8, 3.0, 30.0, 0.6, 40.0
e, n, cls = pts["e"].astype(float), pts["n"].astype(float), pts["cls"]
ok = ~np.isin(cls, (7, 18)) & np.isfinite(hag)
tall = ok & (cls != 2) & (hag > CANOPY_M)
Tt = cKDTree(np.c_[e[tall], n[tall]])
ci = np.where(ok & (cls != 2) & (hag >= LO) & (hag < HI))[0]
clear = np.array([len(x) == 0 for x in Tt.query_ball_point(np.c_[e[ci], n[ci]], r=2.0)])
ci = ci[clear]
P = np.c_[e[ci], n[ci]]
T = cKDTree(P)
used = np.zeros(len(ci), bool)
chains = []
rng = np.random.default_rng(0)
for s in rng.permutation(len(ci)):
    if used[s]:
        continue
    nb = np.array(T.query_ball_point(P[s], r=LINK_M))
    if len(nb) < 4:
        continue
    best = None
    for _ in range(60):
        j = nb[rng.integers(len(nb))]
        if j == s:
            continue
        d = P[j] - P[s]; L = np.hypot(*d)
        if L < 3:
            continue
        u = d / L; nrm = np.array([-u[1], u[0]])
        inl = nb[np.abs((P[nb] - P[s]) @ nrm) <= TOL_M]
        if best is None or len(inl) > len(best[0]):
            best = (inl, u, nrm)
    if best is None or len(best[0]) < 4:
        continue
    # grow along the line both ways, link by link
    u, nrm = best[1], best[2]
    mem = set(best[0].tolist()); frontier = list(mem)
    while frontier:
        q = frontier.pop()
        for k in T.query_ball_point(P[q], r=LINK_M):
            if k in mem or used[k]:
                continue
            if abs((P[k] - P[s]) @ nrm) <= TOL_M + 0.02 * abs((P[k] - P[s]) @ u):   # lets the line bend gently
                mem.add(k); frontier.append(k)
    mem = np.array(sorted(mem))
    a = (P[mem] - P[s]) @ u
    length = float(np.ptp(a))
    if length < MIN_LEN_M:
        continue
    srt = mem[np.argsort(a)]
    gaps = np.diff(np.sort(a))
    used[mem] = True
    hh = hag[ci[mem]]
    chains.append({"returns": int(len(mem)), "len_m": round(length, 1), "max_gap_m": round(float(gaps.max()), 1),
                   "top_p50": round(float(np.median(hh)), 2), "top_p90": round(float(np.percentile(hh, 90)), 2),
                   "ends_en": [P[srt[0]].round(1).tolist(), P[srt[-1]].round(1).tolist()],
                   "points_en": P[srt].round(2).tolist(), "h": hh[np.argsort(a)].round(2).tolist()})
chains.sort(key=lambda c: -c["len_m"])
for c in chains:
    print({k: v for k, v in c.items() if k not in ("points_en", "h")})
json.dump(chains, open(sys.argv[5], "w"))
# picture
cell = float(G["cell"]); e0, n0 = float(G["e0"]), float(G["n0"]); ny, nx = G["ground_int"].shape
gi = G["ground_int"]; v = gi[G["ground_n"] > 0]; lo, hi = np.percentile(v, 2), np.percentile(v, 98)
img = (np.clip((gi - lo) / (hi - lo), 0, 1) * 180).astype(np.uint8)
im = Image.fromarray(np.stack([img] * 3, -1)[::-1].copy()); d = ImageDraw.Draw(im)
X = lambda x: (x - e0) / cell; Y = lambda y: ny - 1 - (y - n0) / cell
for x, y in P:
    d.point((X(x), Y(y)), fill=(255, 140, 0))
for c in chains:
    pe = c["points_en"]
    d.line([(X(p[0]), Y(p[1])) for p in pe], fill=(255, 0, 255), width=1)
im.save(sys.argv[5].replace(".json", ".png"))
