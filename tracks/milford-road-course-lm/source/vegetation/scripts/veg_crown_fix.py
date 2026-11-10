"""Ledger 0082 vegetation Owed 3a / Milford 0.1.5: the split and merged crowns re-segmented from the lidar canopy model.

    python veg_crown_fix.py <veg.npz> <crowns dir> <built track.obj> <track dir> [--dry]

<crowns dir> is veg_crowns.py's output for 0.1.3 (crowns.npz, crowns.json); <built track.obj> the same 0.1.2 gate OBJ
veg_plan.py read (the built ground's extent). Rewrites <track dir>/source/vegetation/trees.lm.json and trunks.json, adds
crown_fix.json (every case, before and after) and a "crown_fix" section to inventory.json. --dry prints the counts only.

WHY (0.1.3's crown_check.json, measured): 2,525 of the 10,419 planted crowns needed a TreeFX width multiplier under 0.25
(2,249: the model squeezed to a pole) or over 2 (276: stretched to a fan, up to 86.5 m). Two mechanisms, both in
veg_crowns.py's segmentation, not in the woods:
  1. THE SMOOTHING STEPS AT ONE COVERAGE. veg_crowns smooths the 2 m canopy model sigma 0.5 cell where the read holds
     >= 0.6 returns / m2 and sigma 1.5 cells below. Just above the step (0.6-0.7 / m2: 2.5 returns per 2 m cell) the
     model keeps every return's noise and every bump is a top: 43 % of those crowns are fragments; just below it
     (0.3-0.6) 16 % are blobs. Above 1.0 / m2 the crowns settle at crown / height p50 0.50-0.56.
  2. THE FLOOD. scipy's watershed_ift on the inverted, uint16-quantised model resolves its many equal-cost paths by queue
     order, not by height: one top floods across the tops beside it (0.1.3's widest crown, id 6911, holds 921 tops of
     the same seed rule) and a top beside it keeps one cell, or none (974 of 14,015 tops ended with no cell at all).

THE FIX, local: only the extreme crowns and, for a fragment, the crowns it touches (the crown it is a piece of) are
re-segmented; every other crown keeps 0.1.3's numbers exactly.
  - Better smoothing: sigma from the coverage, continuously: the Gaussian holds K_RETURNS returns in its effective area
    (2 pi sigma^2 = K / cover), floored at veg_crowns' dense sigma (0.5 cell, where the read resolves crowns) and capped
    at its sparse sigma (1.5 cells). K_RETURNS = 6.3: the dense sigma (1 m) at 1.0 return / m2, the coverage above which
    0.1.3's crowns stop fragmenting (measured, above).
  - Better seeds: the same Popescu & Wynne (2004) height-dependent window, on that model.
  - A marker-controlled watershed that floods by HEIGHT (Meyer's priority flood, highest first): a crown descends from its
    own top until it meets another; the merges split at their own local maxima.
  - A crown that ends under SPARSE_MIN_AREA_M2 on the sparse returns gives its cells to its neighbours (veg_crowns' rule).
  - Every re-segmented crown is judged by veg_plan's planting rules again (a tree of 5 m, on covered, built ground, still
    standing in NAIP 2022, clear of the paved corridor and the buildings); a collider within veg_plan.COLLIDER_REACH_M.
  - Where a crown still cannot be resolved (its width multiplier still under 0.25 or over 2): its height stands as
    measured and its crown is DRAWN as height x its stand's measured crown-to-height ratio (the median over the stand's
    resolved crowns, >= STAND_MIN_TREES of them; else the whole planting's), the measured crown kept in crown_fix.json.
  - Identity: a tree whose measured top falls inside its new crown keeps its position and its KEY (trees.lm.json's 6th
    element: tools/make_treefx.py hashes the model and angle by it), so no other tree changes model or angle; a top that
    lost its crown to a merge is removed; a new top gets a new key after the last.
The bands (0.25, 2) sort the report and name "unresolved"; nothing is clamped to them.
"""
import heapq, json, math, sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from veg_common import Frame, obj_surfaces  # noqa: E402
import veg_crowns as VC  # noqa: E402  (its thresholds: one source)
import veg_plan as VP  # noqa: E402

K_RETURNS = 6.3            # [measured] returns in the smoothing's effective area: sigma 1 m at 1.0 return / m2 (above)
SIG_MIN, SIG_MAX = 0.5, 1.5   # cells: veg_crowns' DENSE_SIGMA and SPARSE_SIGMA, the two it already used
W_LO, W_HI = 0.25, 2.0     # the report's bands (0.1.3 crown_check.py), the line between resolved and not
STAND_MIN_TREES = 30       # [invented] a stand's own ratio needs this many resolved crowns, else the planting's
CELL = 2.0


def width_mult(h, c, nh, nw):
    size = round(h / nh, 2)
    return round(c / (nw * size), 2)     # as trees.txt writes it (make_treefx: "width = %.2f"), so the bands judge the file


def meyer(hgt, seeds, mask):
    """marker-controlled watershed, highest first; seeds: int labels (> 0) inside mask; 4-connected"""
    lab = np.where(mask, seeds, 0).astype(np.int64)
    ny, nx = hgt.shape
    heap, n = [], 0
    for j, i in zip(*np.nonzero(lab)):
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q, p = j + dj, i + di
            if 0 <= q < ny and 0 <= p < nx and mask[q, p] and lab[q, p] == 0:
                heapq.heappush(heap, (-float(hgt[q, p]), n, q, p, int(lab[j, i]))); n += 1
    while heap:
        _, _, j, i, k = heapq.heappop(heap)
        if lab[j, i]:
            continue
        lab[j, i] = k
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q, p = j + dj, i + di
            if 0 <= q < ny and 0 <= p < nx and mask[q, p] and lab[q, p] == 0:
                heapq.heappush(heap, (-float(hgt[q, p]), n, q, p, k)); n += 1
    return lab


def main():
    dry = "--dry" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--dry"]
    veg = np.load(args[0])
    cdir, obj, track = Path(args[1]), Path(args[2]), Path(args[3])
    vdir = track / "source" / "vegetation"
    cfg = json.loads((track / "track.config.json").read_text(encoding="utf-8"))
    corridor = float(cfg["scenery"]["corridor_margin_m"])
    pl = cfg["scenery"]["treefx"]["planted"]
    NH = {k: float(v) for k, v in pl["native_h_m"].items() if not k.startswith("_")}
    NW = {k: float(v) for k, v in pl["native_w_m"].items() if not k.startswith("_")}
    sys.path.insert(0, str(track.parents[1] / "tools"))
    import make_treefx as MT
    species = MT.ZONES[pl["zones"]["1"]]
    model_of = lambda key: MT._pick(species, key)[0]

    c = np.load(cdir / "crowns.npz")
    rep = json.loads((cdir / "crowns.json").read_text(encoding="utf-8"))
    frame = Frame(json.loads(str(veg["origin"])))
    E0, N0 = float(c["E0"]), float(c["N0"])
    chm, sm, lab, woody, cov = c["chm"], c["sm"], c["lab"], c["woody"], c["cov"].astype(np.float64)
    paved, built, naip_can, have = c["paved"], c["built"], c["naip_can"], c["have_naip"]
    ny, nx = sm.shape
    d_paved = ndi.distance_transform_edt(~paved) * CELL
    d_built = ndi.distance_transform_edt(~built) * CELL
    grass = obj_surfaces(obj, ("1GRASS",))["1GRASS"]
    gx0, gx1 = grass[..., 0].min() + 5, grass[..., 0].max() - 5
    gz0, gz1 = grass[..., 1].min() + 5, grass[..., 1].max() - 5

    rows = {r["id"]: r for r in rep["crowns"]}
    old_pts = json.loads((vdir / "trees.lm.json").read_text(encoding="utf-8"))
    old_tr = json.loads((vdir / "trunks.json").read_text(encoding="utf-8"))
    by_ll = {(r["lon"], r["lat"]): r["id"] for r in rep["crowns"]}
    planted = []                        # [(key, crown id)] in the file's order
    for k, p in enumerate(old_pts["points"]):
        assert len(p) == 5 or p[5] == k, "trees.lm.json already carries keys: run this on 0.1.3's file"
        planted.append((k, by_ll[(p[0], p[1])]))
    key_of = {cid: k for k, cid in planted}
    top_cell = lambda r: (int(round((r["n"] - N0) / CELL - 0.5)), int(round((r["e"] - E0) / CELL - 0.5)))

    def extreme(key, h, cm):
        m = model_of(key)
        w = width_mult(h, cm, NH[m], NW[m])
        return w, (w < W_LO or w > W_HI)

    ext = {}
    for k, cid in planted:
        r = rows[cid]
        w, bad = extreme(k, r["h_m"], r["crown_m"])
        if bad:
            ext[cid] = ("fragment" if w < W_LO else "blob", w)
    print(f"[crown_fix] before: {len(planted)} planted, {sum(v[0] == 'fragment' for v in ext.values())} under {W_LO}, "
          f"{sum(v[0] == 'blob' for v in ext.values())} over {W_HI}")

    # the better model and its seeds
    sig = np.clip(np.sqrt(K_RETURNS / (2 * math.pi * np.maximum(cov, 1e-3))) / CELL, SIG_MIN, SIG_MAX)
    levels = np.round(np.arange(SIG_MIN, SIG_MAX + 1e-9, 0.125), 3)
    pick = np.abs(sig[..., None] - levels[None, None, :]).argmin(-1)
    sm2 = np.zeros_like(sm, dtype=np.float64)
    for q, s in enumerate(levels):
        g = ndi.gaussian_filter(chm.astype(np.float64), s)
        sm2[pick == q] = g[pick == q]
    sm2 = np.maximum(sm2, 0)
    cw = 3.09632 + 0.00895 * sm2 ** 2
    rad = np.clip(np.round(cw / 2 / CELL), 1, 5).astype(int)
    tops = np.zeros(sm.shape, bool)
    for r_ in range(1, 6):
        yy, xx = np.mgrid[-r_:r_ + 1, -r_:r_ + 1]
        mx = ndi.maximum_filter(sm2, footprint=(xx ** 2 + yy ** 2) <= r_ * r_, mode="constant")
        tops |= (rad == r_) & (sm2 >= mx - 1e-9) & woody

    # the units: each extreme crown (a fragment with every crown it touches), overlapping units joined
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    objs = ndi.find_objects(lab)
    for cid, (kind, _) in ext.items():
        sl = objs[cid - 1]
        j0, j1 = max(sl[0].start - 1, 0), min(sl[0].stop + 1, ny)
        i0, i1 = max(sl[1].start - 1, 0), min(sl[1].stop + 1, nx)
        sub = lab[j0:j1, i0:i1]
        m = sub == cid
        find(cid)
        if kind == "fragment":
            ring = ndi.binary_dilation(m) & ~m
            for q in set(np.unique(sub[ring]).tolist()) - {0, cid}:
                parent[find(q)] = find(cid)
    units = {}
    for a in list(parent):
        units.setdefault(find(a), []).append(a)
    print(f"[crown_fix] {len(units)} units, {sum(len(v) for v in units.values())} crowns re-segmented")

    new_rows, removed, unreached_m2 = [], [], 0.0
    case = {}
    next_key = len(planted)
    for root, cids in sorted(units.items()):
        bb = [objs[q - 1] for q in cids]
        j0, j1 = min(s[0].start for s in bb), max(s[0].stop for s in bb)
        i0, i1 = min(s[1].start for s in bb), max(s[1].stop for s in bb)
        sub = lab[j0:j1, i0:i1]
        M = np.isin(sub, cids)
        hs = sm2[j0:j1, i0:i1]
        tl, nt = ndi.label(tops[j0:j1, i0:i1] & M)
        seeds = np.zeros(M.shape, np.int64)
        com = ndi.center_of_mass(np.ones_like(tl), tl, range(1, nt + 1)) if nt else []
        for k_, (cj, ci) in enumerate(com, start=1):
            seeds[int(round(cj)), int(round(ci))] = k_
        L = meyer(hs, seeds, M)
        cv = cov[j0:j1, i0:i1]
        for _ in range(3):              # veg_crowns' rule: a crown under 12 m2 on the sparse returns is one return's noise
            a = ndi.sum(np.ones_like(L), L, range(1, nt + 1)) * CELL * CELL
            drop = [k_ for k_ in range(1, nt + 1) if 0 < a[k_ - 1] < VC.SPARSE_MIN_AREA_M2
                    and cv[tuple(np.argwhere(seeds == k_)[0])] < VC.DENSE_PER_M2]
            if not drop:
                break
            seeds[np.isin(seeds, drop)] = 0
            L = meyer(hs, seeds, M)
        unreached_m2 += float((M & (L == 0)).sum()) * CELL * CELL
        old_in = {}                     # new label -> [old crown ids whose measured top it holds]
        for q in cids:
            tj, ti = top_cell(rows[q])
            jj, ii = tj - j0, ti - i0
            k_ = int(L[jj, ii]) if 0 <= jj < L.shape[0] and 0 <= ii < L.shape[1] else 0
            old_in.setdefault(k_, []).append(q)
        for q in old_in.get(0, []):
            removed.append((q, "its top lies in no crown after the flood"))
        for k_ in range(1, nt + 1):
            mk = L == k_
            if not mk.any():
                continue
            sj, si = np.argwhere(seeds == k_)[0]
            heirs = old_in.get(k_, [])
            if heirs:
                # the old top at the seed cell, else the tallest old top, keeps its id (position, key)
                at_seed = [q for q in heirs if top_cell(rows[q]) == (sj + j0, si + i0)]
                heir = at_seed[0] if at_seed else max(heirs, key=lambda q: rows[q]["h_m"])
                for q in heirs:
                    if q != heir:
                        removed.append((q, f"merged into crown {heir}"))
                base = dict(rows[heir])
            else:
                heir = None
                te, tn = E0 + (si + i0 + 0.5) * CELL, N0 + (sj + j0 + 0.5) * CELL
                lon, lat = frame.to_lonlat(te, tn)
                base = {"id": None, "e": round(float(te), 2), "n": round(float(tn), 2), "lon": round(float(lon), 7),
                        "lat": round(float(lat), 7)}
            gj, gi = top_cell(base)
            area = float(mk.sum()) * CELL * CELL
            hmax = float(chm[j0:j1, i0:i1][mk].max())
            grown = ndi.binary_dilation(mk, iterations=int(VC.GROW_M / CELL))
            hv = have[j0:j1, i0:i1] & grown
            nshare = float((naip_can[j0:j1, i0:i1] & grown).sum() / hv.sum()) if hv.sum() else None
            base.update({"h_m": round(hmax, 2), "crown_m": round(2 * math.sqrt(area / math.pi), 2), "area_m2": area,
                         "cover_per_m2": round(float(cov[gj, gi]), 2), "kind": "tree" if hmax >= VC.TREE_MIN_M else "shrub",
                         "naip_share": None if nshare is None else round(nshare, 3),
                         "d_paved_m": round(float(d_paved[gj, gi]), 1), "d_built_m": round(float(d_built[gj, gi]), 1),
                         "_unit": int(root), "_heir_of": heir})
            new_rows.append(base)

    def why_not(r):
        if r["kind"] != "tree":
            return "shrub"
        if not (gx0 <= r["e"] <= gx1 and gz0 <= r["n"] <= gz1):
            return "off_ground"
        if r["cover_per_m2"] < VC.COVER_MIN_PER_M2:
            return "uncovered"
        if r["naip_share"] is not None and r["naip_share"] < VC.GONE_SHARE:
            return "gone_by_2022"
        if r["d_paved_m"] < corridor + VP.HALF_DIAG_M:
            return "too_near_paved"
        if r["d_built_m"] < VP.CLEAR_BUILT_M + VP.HALF_DIAG_M:
            return "too_near_built"
        return None

    touched = {q for v in units.values() for q in v}
    out = {}                            # key -> row (planted after the fix)
    for k, cid in planted:
        if cid not in touched:
            out[k] = dict(rows[cid], _kept=True)
    new_trees, not_planted = [], []
    for r in sorted(new_rows, key=lambda r: (r["n"], r["e"])):
        w = why_not(r)
        if w:
            not_planted.append((r, w))
            continue
        if r["_heir_of"] is not None and r["_heir_of"] in key_of:
            k = key_of[r["_heir_of"]]
        else:
            k = next_key; next_key += 1
            new_trees.append(k)
        out[k] = r

    # resolved or not, and the stand ratio for the rest
    st_lab, _ = ndi.label(ndi.binary_dilation(sm >= 2.0, iterations=1) & (cov >= 0.1))
    stand_of = lambda r: int(st_lab[top_cell(r)])
    ratio_pool = {}
    for k, r in out.items():
        w, bad = extreme(k, r["h_m"], r["crown_m"])
        r["_w"] = w
        if not bad:
            ratio_pool.setdefault(stand_of(r), []).append(r["crown_m"] / r["h_m"])
    allr = [x for v in ratio_pool.values() for x in v]
    global_ratio = float(np.median(allr))
    stand_ratio = {s: float(np.median(v)) for s, v in ratio_pool.items() if len(v) >= STAND_MIN_TREES}
    drawn = []
    for k, r in out.items():
        if r.get("_kept") or not (r["_w"] < W_LO or r["_w"] > W_HI):
            continue
        s = stand_of(r)
        rt = stand_ratio.get(s, global_ratio)
        r["_measured_crown_m"] = r["crown_m"]
        r["crown_m"] = round(r["h_m"] * rt, 2)
        r["_drawn"] = {"stand": s, "ratio": round(rt, 3), "from": "stand" if s in stand_ratio else "planting"}
        r["_w_after"], _ = extreme(k, r["h_m"], r["crown_m"])
        drawn.append(k)

    # every case
    old_keys = {k for k, _ in planted}
    gone_keys = sorted(old_keys - set(out))
    cid_now = {r["_heir_of"]: k for k, r in out.items() if not r.get("_kept") and r.get("_heir_of") is not None}
    removed_by = dict(removed)
    np_by = {r["_heir_of"]: w for r, w in not_planted if r["_heir_of"] is not None}
    cases = []
    for cid, (kind, w) in sorted(ext.items(), key=lambda t: key_of[t[0]]):
        k = key_of[cid]
        r0 = rows[cid]
        d = {"key": k, "crown_id": cid, "was": kind, "lon": r0["lon"], "lat": r0["lat"], "h_m": r0["h_m"],
             "crown_m": r0["crown_m"], "width": round(w, 3), "model": model_of(k)}
        if k in out:
            r = out[k]
            d["after"] = {"h_m": r["h_m"], "crown_m": r["crown_m"], "width": round(r.get("_w_after", r["_w"]), 3)}
            if "_drawn" in r:
                d["outcome"] = "unresolved: crown drawn from the stand's crown / height ratio"
                d["after"]["measured_crown_m"] = r["_measured_crown_m"]
                d["after"]["drawn"] = r["_drawn"]
            else:
                d["outcome"] = "re-segmented: resolved"
            sibs = [kk for kk in new_trees if out[kk]["_unit"] == r["_unit"]]
            if sibs:
                d["unit_new_keys"] = sibs
        elif cid in removed_by:
            d["outcome"] = f"removed: {removed_by[cid]}"
            heir = removed_by[cid].split()[-1]
            if heir.isdigit() and int(heir) in cid_now:
                d["into_key"] = cid_now[int(heir)]
        elif cid in np_by:
            d["outcome"] = f"not planted after re-segmentation: {np_by[cid]}"
        else:
            d["outcome"] = "removed"
        cases.append(d)
    neighbours = []
    for k, cid in planted:
        if cid in touched and cid not in ext:
            r0 = rows[cid]
            d = {"key": k, "crown_id": cid, "before": {"h_m": r0["h_m"], "crown_m": r0["crown_m"]}}
            if k in out:
                d["after"] = {"h_m": out[k]["h_m"], "crown_m": out[k]["crown_m"]}
                if "_drawn" in out[k]:
                    d["after"]["drawn"] = out[k]["_drawn"]
            else:
                d["after"] = removed_by.get(cid) or np_by.get(cid) or "removed"
            neighbours.append(d)

    final = sorted(out)
    lo = sum(1 for k in final if out[k].get("_w_after", out[k]["_w"]) < W_LO)
    hi = sum(1 for k in final if out[k].get("_w_after", out[k]["_w"]) > W_HI)
    still = [k for k in final if out[k]["_w"] < W_LO or out[k]["_w"] > W_HI]
    summary = {
        "before": {"planted": len(planted), "width_under_0.25": sum(v[0] == "fragment" for v in ext.values()),
                   "width_over_2": sum(v[0] == "blob" for v in ext.values())},
        "re_segmented": {"units": len(units), "crowns": len(touched), "extreme": len(ext),
                         "neighbours_touched": sum(1 for q in touched if q not in ext and q in key_of)},
        "after_resegmentation": {"planted": len(final),
                                 "width_under_0.25": sum(1 for k in still if out[k]["_w"] < W_LO),
                                 "width_over_2": sum(1 for k in still if out[k]["_w"] > W_HI)},
        "drawn_from_stand_ratio": len(drawn),
        "after": {"planted": len(final), "width_under_0.25": lo, "width_over_2": hi},
        "removed_trees": len(gone_keys), "new_trees": len(new_trees),
        "global_ratio": round(global_ratio, 3), "stand_ratios": {str(s): round(v, 3) for s, v in sorted(stand_ratio.items())},
        "unreached_m2": unreached_m2,
        "not_planted_after": {w: sum(1 for _, ww in not_planted if ww == w) for w in sorted({w for _, w in not_planted})},
        "untouched_trees": sum(1 for k in final if out[k].get("_kept")),
        "rules": {"K_RETURNS": K_RETURNS, "sigma_cells": [SIG_MIN, SIG_MAX], "bands": [W_LO, W_HI],
                  "STAND_MIN_TREES": STAND_MIN_TREES},
    }
    print("[crown_fix] " + json.dumps({k: v for k, v in summary.items() if k != "stand_ratios"}))
    if dry:
        return

    def ll(k):
        r = out[k]
        return [r["lon"], r["lat"], 1, r["h_m"], r["crown_m"], k]
    order = [k for k, _ in planted if k in out] + new_trees
    (vdir / "trees.lm.json").write_text(json.dumps(dict(old_pts, points=[ll(k) for k in order],
        _source=old_pts["_source"] + ". Milford 0.1.5 (veg_crown_fix.py): the split and merged crowns re-segmented; the 6th "
        "element is the tree's KEY (tools/make_treefx.py hashes its model and angle by it); crown_fix.json lists every case"),
        separators=(",", ":")), encoding="utf-8")
    old_tr_by = {(p[0], p[1]): p for p in old_tr["points"]}
    trunks = []
    for k in order:
        r = out[k]
        if r.get("_kept"):
            p = old_tr_by.get((r["lon"], r["lat"]))
            if p:
                trunks.append(p)
        elif r["d_paved_m"] <= VP.COLLIDER_REACH_M:
            trunks.append([r["lon"], r["lat"], r["h_m"], r["d_paved_m"]])
    (vdir / "trunks.json").write_text(json.dumps(dict(old_tr, points=trunks), separators=(",", ":")), encoding="utf-8")
    summary["trunk_colliders"] = {"before": len(old_tr["points"]), "after": len(trunks)}
    (vdir / "crown_fix.json").write_text(json.dumps({
        "_doc": "Milford 0.1.5 crown fix (veg_crown_fix.py, ledger 0082 Owed 3a): every crown 0.1.3 planted with a width "
                "multiplier under 0.25 or over 2 (cases), every crown re-segmented beside them (neighbours), every new tree "
                "and every removed key", "summary": summary, "cases": cases, "neighbours": neighbours,
        "new": [{"key": k, "lon": out[k]["lon"], "lat": out[k]["lat"], "h_m": out[k]["h_m"], "crown_m": out[k]["crown_m"],
                 **({"drawn": out[k]["_drawn"], "measured_crown_m": out[k]["_measured_crown_m"]} if "_drawn" in out[k] else {})}
                for k in new_trees],
        "removed_keys": gone_keys}, indent=1), encoding="utf-8")
    inv = json.loads((vdir / "inventory.json").read_text(encoding="utf-8"))
    h = np.array([out[k]["h_m"] for k in order]); w = np.array([out[k]["crown_m"] for k in order])
    inv["planted"].update({"trees": len(order), "trunk_colliders": len(trunks),
                           "h_p10_p50_p90_max_m": [round(float(x), 1) for x in np.percentile(h, [10, 50, 90, 100])],
                           "crown_p10_p50_p90_m": [round(float(x), 1) for x in np.percentile(w, [10, 50, 90])]})
    inv["crown_fix"] = {"_doc": "Milford 0.1.5: veg_crown_fix.py (crown_fix.json holds every case)", **summary}
    (vdir / "inventory.json").write_text(json.dumps(inv, indent=1), encoding="utf-8")
    print(f"[crown_fix] wrote {len(order)} trees ({len(new_trees)} new, {len(gone_keys)} removed), {len(trunks)} colliders")


if __name__ == "__main__":
    main()
