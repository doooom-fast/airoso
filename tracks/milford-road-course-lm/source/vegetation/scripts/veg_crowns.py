"""Ledger 0082 vegetation pass, step 1: every tree crown and shrub the 2017 lidar measures, checked against NAIP 2022.

    python veg_crowns.py <veg.npz> <veg_canopy.npz> <built track.obj> <OUT dir>

Inputs: veg_read.py's grids and canopy returns (the 2017-05-03 flight), the 0.1.2 build's gate OBJ (what is paved, walled,
built), NAIP 2022-08-16 (source/naip_2022_mrc.jpg of tracks/milford-road-course). Writes OUT/crowns.npz (the 2 m grids and
the segment labels) and OUT/crowns.json (one row per crown). Every threshold is named below with its source.

THE METHOD
1. The canopy height model on a 2 m grid: the highest return over the ground per cell. A return more than SPIKE_M over
   every neighbour's height, in a cell holding at most 2 returns, is a bird or noise and is dropped; an empty cell with at
   least 5 of 8 canopy neighbours (the sparse coarse nodes far from the lap) takes their mean. Smoothed sigma 1 cell.
2. Solid, not leafy: a crown lets a pulse through to a second return, a roof / trailer / wall top does not. Over each 10 m
   square, the share of first returns over 2 m with returns after them; under SOLID_SHARE (and with enough first
   returns to judge) it is a solid object, never a crown.
3. Tree tops: the local maxima of the smoothed model, each the highest cell within half the crown width a deciduous tree of
   its height has (Popescu & Wynne 2004, Photogramm. Eng. Remote Sens. 70(5): CW = 3.09632 + 0.00895 h^2, deciduous).
   Crowns: the watershed of the model from those tops, inside the canopy (>= WOODY_MIN_M).
4. Per crown: height = its highest cell (after 1), crown width = the diameter of a circle of its area, the returns and the
   leafy share it rests on. A crown under TREE_MIN_M (FAO's tree: 5 m at maturity) is a shrub.
5. NAIP 2022: the canopy mask is calibrated on the lidar itself (cells the lidar calls deep canopy against open ground far
   from any canopy), then each crown's footprint (grown by 2 m for registration) is read: a crown NAIP shows no canopy in
   is GONE by 2022; NAIP canopy blobs the lidar has nothing under are NEW since 2017. Both flagged, neither planted.
"""
import json, math, sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from veg_common import CELL, Frame, naip_features, obj_surfaces, raster_tris  # noqa: E402

SPIKE_M = 5.0             # [rule] a single return this far over every neighbour is not canopy
HAG_MAX_M = 45.0          # [rule] sanity: no tree in Oakland County stands 45 m (the state's tallest are ~40-50 m)
SOLID_SHARE = 0.15        # [measured] roofs read 0.00-0.02 (mpg_plant_a 0.02, the pad shed and tent 0.00); woods p50 1.0
SOLID_MIN_FIRST = 6       # first returns over 2 m a 10 m square needs before it is judged solid
WOODY_MIN_M = 2.0         # [rule] the canopy model's floor: a shrub's top
TREE_MIN_M = 5.0          # [FAO 2020 FRA: a tree reaches 5 m in situ]
GROW_M = 2.0              # NAIP registration / growth allowance around a crown
GONE_SHARE = 0.2          # a crown whose (grown) footprint NAIP calls canopy under this share is gone by 2022
DENSE_SIGMA = float(__import__("os").environ.get("VEG_DENSE_SIGMA", "0.5"))   # cells (1 m): crown p50 7-12 m, as NAIP shows them
SPARSE_SIGMA = 1.5        # cells: on the sparse returns
DENSE_PER_M2 = 0.6       # [measured] the coverage above which crowns resolve (single-cell crowns 1-4 % above it, 14-57 % below)
COVER_MIN_PER_M2 = 0.1    # [measured] below this (under 1 return per 10 m2) no crown is resolvable: not inventoried
SPARSE_MIN_AREA_M2 = 12.0 # a crown on the sparse returns smaller than 3 cells is one return's noise, merged to its neighbour
SOLID_MIN_AREA_M2 = 32.0  # a solid patch smaller than this inside canopy (a dense conifer, a stand) is not a building


def main():
    veg = np.load(sys.argv[1])
    can = np.load(sys.argv[2])
    obj, out = Path(sys.argv[3]), Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    frame = Frame(json.loads(str(veg["origin"])))
    E0, N0 = float(veg["E0"]), float(veg["N0"])
    ny1, nx1 = veg["chm"].shape
    nx, ny = nx1 // 2, ny1 // 2
    e_c = E0 + (np.arange(nx) + 0.5) * CELL
    n_c = N0 + (np.arange(ny) + 0.5) * CELL

    # 1. the 2 m model from the canopy returns themselves
    e, n, h, rn, nr = can["e"], can["n"], can["hag"], can["rn"], can["nr"]
    keep = h < HAG_MAX_M
    e, n, h, rn, nr = e[keep], n[keep], h[keep], rn[keep], nr[keep]
    ii = np.clip(((e - E0) / CELL).astype(int), 0, nx - 1)
    jj = np.clip(((n - N0) / CELL).astype(int), 0, ny - 1)
    flat = jj * nx + ii
    chm = np.zeros(nx * ny, np.float32)
    np.maximum.at(chm, flat, h)
    chm = chm.reshape(ny, nx)
    cnt = np.bincount(flat, minlength=nx * ny).reshape(ny, nx)
    first = rn == 1
    n_first = np.bincount(flat[first], minlength=nx * ny).reshape(ny, nx)
    n_first_multi = np.bincount(flat[first & (nr > 1)], minlength=nx * ny).reshape(ny, nx)
    # density of ALL returns per 2 m cell (from the 1 m grid)
    dens = veg["n_all"][:ny * 2, :nx * 2].reshape(ny, 2, nx, 2).sum((1, 3)) / (CELL * CELL)
    # spikes: higher than every neighbour by SPIKE_M, resting on <= 2 returns
    fp = np.ones((3, 3), bool); fp[1, 1] = False
    nb_max = ndi.maximum_filter(np.where(np.isfinite(chm), chm, 0), footprint=fp, mode="constant")
    seen = ndi.convolve((dens > 0).astype(np.int32), np.ones((3, 3), np.int32), mode="constant") - (dens > 0)
    spike = (chm > nb_max + SPIKE_M) & (cnt <= 2) & (seen >= 6)      # its neighbours were seen, and stood lower
    chm[spike] = nb_max[spike]
    # fill the sparse holes inside canopy
    is_c = chm >= WOODY_MIN_M
    k8 = ndi.convolve(is_c.astype(np.int32), np.ones((3, 3), np.int32), mode="constant") - is_c
    s8 = ndi.convolve(np.where(is_c, chm, 0), np.ones((3, 3)), mode="constant") - np.where(is_c, chm, 0)
    fill = (cnt == 0) & (k8 >= 5)
    chm[fill] = s8[fill] / np.maximum(k8[fill], 1)
    # coverage: all returns per m2 over 10 m. Where the read is dense (>= DENSE_PER_M2) one crown is resolved by a 2 m
    # smoothing; on the coarse nodes' sparse returns a crown needs twice that, or every lone return is a "top"
    cov = ndi.uniform_filter(dens, 5)
    sm = np.where(cov >= DENSE_PER_M2, ndi.gaussian_filter(chm, DENSE_SIGMA), ndi.gaussian_filter(chm, SPARSE_SIGMA))
    sm = np.maximum(sm, 0)

    # 2. solid squares (5 x 5 cells = 10 m)
    k5 = np.ones((5, 5))
    f5 = ndi.convolve(n_first.astype(float), k5, mode="constant")
    m5 = ndi.convolve(n_first_multi.astype(float), k5, mode="constant")
    share = np.where(f5 > 0, m5 / np.maximum(f5, 1), np.nan)
    solid = (f5 >= SOLID_MIN_FIRST) & (share < SOLID_SHARE) & (chm >= WOODY_MIN_M)
    sl_, n_sl = ndi.label(solid)
    s_area = ndi.sum(np.ones_like(sl_), sl_, range(1, n_sl + 1)) * CELL * CELL
    solid = np.isin(sl_, np.flatnonzero(s_area >= SOLID_MIN_AREA_M2) + 1)
    covered = cov >= COVER_MIN_PER_M2
    woody = (sm >= WOODY_MIN_M) & ~solid & (chm >= WOODY_MIN_M * 0.75) & covered

    # 3. tops with a height-dependent window
    cw = 3.09632 + 0.00895 * sm ** 2                      # Popescu & Wynne 2004, deciduous
    rad_cells = np.clip(np.round(cw / 2 / CELL), 1, 5).astype(int)
    tops = np.zeros_like(woody)
    for r in range(1, 6):
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        mx = ndi.maximum_filter(sm, footprint=(xx ** 2 + yy ** 2) <= r * r, mode="constant")
        tops |= (rad_cells == r) & (sm >= mx - 1e-6) & woody
    tl, ntop = ndi.label(tops)                           # plateaus: one top each
    centres = ndi.center_of_mass(tops, tl, range(1, ntop + 1))
    markers = np.zeros(sm.shape, np.int32)
    for k, (cj, ci) in enumerate(centres, start=1):
        markers[int(round(cj)), int(round(ci))] = k
    # the flood: canopy costs its depth under 60 m, everything outside the canopy is a wall (65535), no background marker
    # (a background marker floods the crowns' low rims first and leaves them unlabelled); a canopy patch with no top of its
    # own is left out
    inv = np.where(woody, np.clip(60 - sm, 0, 60) * 1000, 65535).astype(np.uint16)
    comp, _ = ndi.label(woody)
    has_top = np.zeros(comp.max() + 1, bool)
    has_top[np.unique(comp[markers > 0])] = True
    has_top[0] = False

    def flood(mk):
        lb = ndi.watershed_ift(inv, mk)
        lb[~woody | ~has_top[comp]] = 0
        return np.maximum(lb, 0)
    lab = flood(markers)
    # the sparse returns' one-return crowns: drop their tops and let the neighbours take the cells
    a0 = ndi.sum(np.ones_like(lab), lab, range(1, ntop + 1)) * CELL * CELL
    small = [k for k in range(ntop) if a0[k] < SPARSE_MIN_AREA_M2
             and cov[int(round(centres[k][0])), int(round(centres[k][1]))] < DENSE_PER_M2]
    if small:
        drop = np.zeros(ntop + 1, bool)
        drop[np.array(small) + 1] = True
        markers[(markers > 0) & drop[np.clip(markers, 0, ntop)]] = 0
        lab = flood(markers)
    print(f"[crowns] {len(small)} one-return tops on the sparse nodes merged into their neighbours")

    # 4. per crown
    idx = np.arange(1, ntop + 1)
    area = ndi.sum(np.ones_like(lab), lab, idx) * CELL * CELL
    hmax = ndi.maximum(chm, lab, idx)
    nret = ndi.sum(cnt, lab, idx)
    nf, nfm = ndi.sum(n_first, lab, idx), ndi.sum(n_first_multi, lab, idx)
    dmean = ndi.mean(dens, lab, idx)

    # the built surfaces (0.1.2's gate OBJ): paved, walls, buildings
    srf = obj_surfaces(obj, ("1ROAD", "1KERB", "PADAPRON", "1WALL", "GUARDRAIL", "BUILDING", "ROOFTOP", "FARBLOCK", "MARKINGS"))
    paved = np.zeros(sm.shape, bool)
    for k in ("1ROAD", "1KERB", "PADAPRON", "MARKINGS"):
        paved |= raster_tris(srf[k], E0, N0, nx, ny, CELL)
    built = np.zeros(sm.shape, bool)
    for k in ("1WALL", "GUARDRAIL", "BUILDING", "ROOFTOP", "FARBLOCK"):
        built |= raster_tris(srf[k], E0, N0, nx, ny, CELL, wall_w=0.5)
    d_paved = ndi.distance_transform_edt(~paved) * CELL
    d_built = ndi.distance_transform_edt(~built) * CELL

    # 5. NAIP 2022, calibrated on the lidar
    rgb, sdv = naip_features(frame, E0, N0, nx, ny, CELL)
    have = np.isfinite(rgb[..., 0]) & np.isfinite(sdv)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mean = (r + g + b) / 3
    gr = g / np.maximum(r, 1)
    dense = cov >= DENSE_PER_M2                      # calibrate only where the read resolves crowns
    deep = ndi.binary_erosion(sm >= 8, iterations=2) & ~solid & have & dense
    open_ = (ndi.distance_transform_edt(sm < 1.0) * CELL >= 15) & have & ~paved & ~built & dense
    rng = np.random.default_rng(20170503)
    pd_ = rng.choice(np.flatnonzero(deep), min(40000, int(deep.sum())), replace=False)
    po_ = rng.choice(np.flatnonzero(open_), min(40000, int(open_.sum())), replace=False)
    D = np.c_[mean.flat[pd_], gr.flat[pd_], sdv.flat[pd_]]
    O = np.c_[mean.flat[po_], gr.flat[po_], sdv.flat[po_]]
    best = None
    for mt in np.arange(90, 152, 4):
        dm, om = D[:, 0] <= mt, O[:, 0] <= mt
        for gt in np.arange(1.0, 1.21, 0.01):
            dg, og = dm & (D[:, 1] >= gt), om & (O[:, 1] >= gt)
            for st in np.arange(0, 13, 1.0):
                tpr = (dg & (D[:, 2] >= st)).mean()
                tnr = 1 - (og & (O[:, 2] >= st)).mean()
                ba = (tpr + tnr) / 2
                if best is None or ba > best[0]:
                    best = (ba, mt, gt, st, tpr, tnr)
    ba, mt, gt, st, tpr, tnr = best
    naip_can = have & (mean <= mt) & (gr >= gt) & (sdv >= st)
    naip_can = ndi.binary_opening(naip_can, iterations=1)
    xt = None
    print(f"[crowns] NAIP canopy rule calibrated on the lidar: mean <= {mt}, g/r >= {gt:.2f}, 2 m spread >= {st}: deep canopy "
          f"{100 * tpr:.1f} % canopy, open ground {100 * tnr:.1f} % open (balanced {100 * ba:.1f} %; {deep.sum()} / {open_.sum()} cells)")
    grown = ndi.grey_dilation(lab, size=(int(2 * GROW_M / CELL) + 1,) * 2)
    in_naip = ndi.sum(have.astype(float), grown, idx)
    naip_share = np.where(in_naip > 0, ndi.sum(naip_can.astype(float), grown, idx) / np.maximum(in_naip, 1), np.nan)
    # NEW: NAIP canopy with no lidar canopy within 3 m
    near_lidar = ndi.binary_dilation(sm >= WOODY_MIN_M, iterations=2)
    new_c = naip_can & ~near_lidar & ~paved & ~built & (cov >= DENSE_PER_M2)     # only where the read could have seen it
    unread = naip_can & (cov < COVER_MIN_PER_M2)                                   # NAIP canopy the read never reached
    new_lab, n_new = ndi.label(new_c)
    new_area = ndi.sum(np.ones_like(new_lab), new_lab, range(1, n_new + 1)) * CELL * CELL
    new_com = ndi.center_of_mass(new_c, new_lab, range(1, n_new + 1))
    new_rows = [{"e": round(float(E0 + (ci + 0.5) * CELL), 1), "n": round(float(N0 + (cj + 0.5) * CELL), 1), "area_m2": float(a)}
                for (cj, ci), a in zip(new_com, new_area) if a >= 20.0]

    rows = []
    for k in range(ntop):
        cj, ci = centres[k]
        j, i = int(round(cj)), int(round(ci))
        te, tn = E0 + (ci + 0.5) * CELL, N0 + (cj + 0.5) * CELL
        if area[k] <= 0:
            continue
        lon, lat = frame.to_lonlat(te, tn)
        rows.append({"id": k + 1, "e": round(float(te), 2), "n": round(float(tn), 2), "lon": round(float(lon), 7), "lat": round(float(lat), 7),
                     "h_m": round(float(hmax[k]), 2), "crown_m": round(2 * math.sqrt(area[k] / math.pi), 2), "area_m2": float(area[k]),
                     "returns": int(nret[k]), "leafy_share": round(float(nfm[k] / nf[k]), 3) if nf[k] else None,
                     "density_per_m2": round(float(dmean[k]), 2), "cover_per_m2": round(float(cov[j, i]), 2),
                     "kind": "tree" if hmax[k] >= TREE_MIN_M else "shrub",
                     "naip_share": None if not np.isfinite(naip_share[k]) else round(float(naip_share[k]), 3),
                     "d_paved_m": round(float(d_paved[j, i]), 1), "d_built_m": round(float(d_built[j, i]), 1)})
    np.savez_compressed(out / "crowns.npz", chm=chm, sm=sm, lab=lab, solid=solid, woody=woody, paved=paved, built=built,
                        naip_can=naip_can, have_naip=have, dens=dens, E0=E0, N0=N0, cell=CELL, new_c=new_c, unread=unread,
                        cov=cov.astype(np.float32))
    rep = {"_doc": "veg_crowns.py: every crown the 2017 lidar measures (2 m grid), NAIP 2022's word on each, the 0.1.2 build's paved / "
                   "built distance", "naip_rule": {"mean_max": float(mt), "g_over_r_min": round(float(gt), 2), "spread_min": float(st), "tpr": round(float(tpr), 3),
                                                   "tnr": round(float(tnr), 3)},
           "solid_cells": int(solid.sum()), "spikes_dropped": int(spike.sum()), "holes_filled": int(fill.sum()),
           "naip_canopy_unread_m2": float(unread.sum() * CELL * CELL),
           "crowns": rows, "naip_new": new_rows}
    (out / "crowns.json").write_text(json.dumps(rep), encoding="utf-8")
    nt = sum(1 for r_ in rows if r_["kind"] == "tree")
    print(f"[crowns] {len(rows)} crowns ({nt} trees >= {TREE_MIN_M} m, {len(rows) - nt} shrubs); solid cells {int(solid.sum())}; "
          f"spikes {int(spike.sum())}; filled {int(fill.sum())}; NAIP-new blobs >= 20 m2: {len(new_rows)}")


if __name__ == "__main__":
    main()
