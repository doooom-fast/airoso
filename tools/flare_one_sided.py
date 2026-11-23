"""ONE-SIDED MEASURED JUNCTION FLARES: the lap's far kerb where no street joins, measured off the source lidar
(ledger 0098; ledger 0087 section 7 Q2; Kevin 2026-11-22, asked "One-sided junction flares, measured?": "Build it with the
disconnected-roads fix").

The cause (ledger 0087): scripts/gps/widths_from_osm.flare_widths widens the lap's WIDTH at every junction, so the flare is
swept on both sides at once: at a junction where a street joins one side only, the far kerb bulges out where there is no
street (Sand Creek: 5 such junctions, a median 6.5 m). The v021 assembler sweeps a ribbon of one width about the line, so a
one-sided flare is a width and a line moved together: the near side (the street's) keeps the source's flared half width,
the far side takes the MEASURED kerb, and the line moves half the difference toward the street.

THE MEASUREMENT, per lap vertex of a declared flare (route.flare_one_sided: the vertex range and the street that joins;
the street side is read off that street's points, which end at the lap there):
  * a cross-section on the FAR side, from the line out to the source's flared half width + FAR_PAST_M, every BIN_M; each
    bin the median class-2 return within ALONG_M along the line and BIN_M / 2 across (MIN_RETURNS or more);
  * the step map D(l) = the mean ground over (l, l + STEP_WIN_M] less over [l - STEP_WIN_M, l) (tools/lidar_curb_trace's);
  * the EDGE: the innermost l, from SEARCH_IN_M inside the street's own half width (the running minimum of the source's
    widths over +-BASE_REACH_M, the flare's base) out to the flared half width + SEARCH_OUT_M, where D >= STEP_M (a curb
    rises outward: tools/naip_edge.STEP_M) or D <= -STEP_M (the paved platform's edge falls away: an embankment, a ditch;
    Sand Creek's streets have no curb, route.edge); its kind is recorded;
  * along the flare: the readings' running median over MEDIAN_ROWS rows (a driveway cut, a car), unread rows left out.
The lap and the tiles share one frame (scripts.geometry.projection), so no frame change is needed here (tools/grid_reach.py
documents the grid's). A missing tile is no reading; nothing is fetched.

Applied by tools/lm_engine_intake.apply_flare_one_sided (lm_intake.flare_one_sided), per row as recorded here: far = the
measured edge, held between the street's own half width and the flared half width (a one-sided flare never widens the far
side past the source's flare, nor narrows it under the street's own width), interpolated between two read rows; where no
row was read the source's half stands (nothing moves on no reading); width = near + far; the vertex moves (near - far) / 2
toward the street. Numbers marked [invented] are sampling choices (fleet/GATES-CHANGELOG.md,
2026-11-22, 0098); STEP_M is round J's.

    python tools/flare_one_sided.py <port-project-dir> --tiles <dir of tile_i_j.npz> [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
for _p in (str(AIROSO), str(AIROSO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BIN_M = 0.25          # = tools/lidar_curb_trace.BIN_M
ALONG_M = 0.75        # = tools/lidar_curb_trace.ALONG_M
STEP_WIN_M = 1.0      # = tools/naip_edge.STEP_WIN_M
STEP_M = 0.08         # = tools/naip_edge.STEP_M (round J): a curb face
MIN_RETURNS = 3       # = tools/lidar_connector_profile.MIN_RETURNS
BASE_REACH_M = 25.0   # = ledger 0087's flare census (the street's own width: the running minimum over +-25 m)
SEARCH_IN_M = 1.5     # [invented] the kerb is searched from this far inside the street's own half width ...
SEARCH_OUT_M = 1.5    # [invented] ... to this far past the flared half width
FAR_PAST_M = 3.0      # [invented] the cross-section runs this far past the flared half width
MEDIAN_ROWS = 5       # [invented] the readings' running median along the flare (rows ~3 m apart)
TILE_M = 100.0        # = tools/lidar_connector_profile.TILE_M


def _tiles(tdir: Path):
    import numpy as np
    cache, missing = {}, set()

    def get(i, j):
        if (i, j) not in cache:
            p = tdir / f"tile_{i}_{j}.npz"
            if p.exists():
                d = np.load(p)
                cache[(i, j)] = (d["E"], d["N"], d["Z"], d["C"])
            else:
                missing.add((i, j))
                z = np.zeros(0)
                cache[(i, j)] = (z, z, z, np.zeros(0, np.uint8))
        return cache[(i, j)]
    return get, missing


def base_halves(pts, widths, closed=True):
    """the street's own half width at each vertex: half the running minimum of the widths over +-BASE_REACH_M"""
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    L = st[-1]
    out = []
    for i in range(len(pts)):
        lo = [widths[j] for j in range(len(pts)) if min(abs(st[j] - st[i]), L - abs(st[j] - st[i]) if closed else 1e9)
              <= BASE_REACH_M]
        out.append(min(lo) / 2.0)
    return out


def normals(pts):
    """the unit left normal (x, z) of the line at each vertex (+ = left of the direction of travel)"""
    n = len(pts)
    out = []
    for k in range(n):
        a, b = pts[max(k - 1, 0)], pts[min(k + 1, n - 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        out.append((-tz / L, tx / L))
    return out


def street_side(pts, nl, v0, v1, street_pts, mouths=()):
    """+1 (left) / -1 (right): the side of the line the named street meets it on within the flare: its mouth's cut
    (data/mouths.json, the built record) when there is one, else the street's nearest end"""
    for mo in mouths:
        k = int(mo["host_vertex"])
        if mo.get("host") == "MAINLINE" and v0 <= k <= v1:
            c = mo["cut_xyz"]
            s = (c[0] - pts[k][0]) * nl[k][0] + (c[2] - pts[k][2]) * nl[k][1]
            return (1 if s > 0 else -1), round(math.hypot(c[0] - pts[k][0], c[2] - pts[k][2]), 1), k
    best = None
    for e in (street_pts[0], street_pts[-1]):
        for k in range(v0, v1 + 1):
            d = math.hypot(e[0] - pts[k][0], e[2] - pts[k][2])
            if best is None or d < best[0]:
                best = (d, k, e)
    d, k, e = best
    s = (e[0] - pts[k][0]) * nl[k][0] + (e[2] - pts[k][2]) * nl[k][1]
    return (1 if s > 0 else -1), round(d, 1), k


def kerb_at(tile, p, t, nf, lo, hi, reach):
    """(l, returns, kind): the innermost l in [lo, hi] (m out along nf from p) where the class-2 ground steps up
    (curb) or falls away (drop) by STEP_M or more; l None if neither"""
    import numpy as np
    xs = [p[0] + nf[0] * l for l in (0.0, reach)]
    zs = [p[2] + nf[1] * l for l in (0.0, reach)]
    E, N, Z, C = [], [], [], []
    for i in {int(math.floor(x / TILE_M)) for x in xs}:
        for j in {int(math.floor(z / TILE_M)) for z in zs}:
            e, n_, z, c = tile(i, j)
            E.append(e); N.append(n_); Z.append(z); C.append(c)
    E, N, Z, C = (np.concatenate(a) for a in (E, N, Z, C))
    if not len(E):
        return None, 0, None
    dx, dz = E - p[0], N - p[2]
    al = dx * t[0] + dz * t[1]
    ac = dx * nf[0] + dz * nf[1]
    m = (C == 2) & (np.abs(al) <= ALONG_M) & (ac >= -STEP_WIN_M) & (ac <= reach + STEP_WIN_M)
    if m.sum() < MIN_RETURNS:
        return None, int(m.sum()), None
    ac, Zm = ac[m], Z[m]
    edges = np.arange(-STEP_WIN_M, reach + STEP_WIN_M + 1e-9, BIN_M)
    cen = (edges[:-1] + edges[1:]) / 2.0
    zb = np.full(len(cen), np.nan)
    idx = np.digitize(ac, edges) - 1
    for b in range(len(cen)):
        q = Zm[idx == b]
        if len(q) >= MIN_RETURNS:
            zb[b] = np.median(q)
    w = int(round(STEP_WIN_M / BIN_M))
    for b in range(len(cen)):
        l = cen[b]
        if l < lo or l > hi or b - w < 0 or b + w >= len(cen):
            continue
        inner, outer = zb[b - w:b], zb[b + 1:b + 1 + w]
        if np.isnan(inner).all() or np.isnan(outer).all():
            continue
        d = np.nanmean(outer) - np.nanmean(inner)
        if d >= STEP_M or d <= -STEP_M:
            return round(float(l), 2), int(m.sum()), ("curb" if d > 0 else "drop")
    return None, int(m.sum()), None


def measure(proj: Path, tiles_dir: Path):
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    spec = (cfg.get("route") or {}).get("flare_one_sided") or []
    if not spec:
        raise SystemExit("[flare_one_sided] track.config.json route.flare_one_sided declares no flare")
    src = AIROSO / "tracks" / str((cfg.get("lm_intake") or {})["source_track"])
    local = json.loads((src / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    pts, widths = local["points_xyz_m"], local["widths_m"]
    conns = {c["name"]: c for c in json.loads((src / "data" / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]}
    nl = normals(pts)
    base = base_halves(pts, widths)
    mp = proj / "data" / "mouths.json"
    mouths = json.loads(mp.read_text(encoding="utf-8"))["mouths"] if mp.exists() else []
    tile, missing = _tiles(tiles_dir)
    out = []
    for r in spec:
        v0, v1 = int(r["v"][0]), int(r["v"][1])
        if r["street"] not in conns:
            raise SystemExit(f"[flare_one_sided] {r['id']}: no street {r['street']!r} in the source's connectors")
        mos = [mo for mo in mouths if str(mo.get("connector", "")).split("#")[0] == r["street"]]
        side, dist, k_near = street_side(pts, nl, v0, v1, conns[r["street"]]["points_xyz_m"], mos)
        rows = []
        for k in range(v0, v1 + 1):
            p = pts[k]
            nf = (-side * nl[k][0], -side * nl[k][1])
            t = (nl[k][1], -nl[k][0])
            hw = widths[k] / 2.0
            lo, hi = base[k] - SEARCH_IN_M, hw + SEARCH_OUT_M
            l, n, kind = kerb_at(tile, p, t, nf, lo, hi, hw + FAR_PAST_M)
            rows.append({"k": k, "source_half_m": round(hw, 3), "base_half_m": round(base[k], 3), "kerb_raw_m": l,
                         "kind": kind, "returns": n})
        raw = [q["kerb_raw_m"] for q in rows]
        h = MEDIAN_ROWS // 2
        for i, q in enumerate(rows):
            win = sorted(v for v in raw[max(0, i - h):i + h + 1] if v is not None)
            q["far_kerb_m"] = None if raw[i] is None or not win else round(win[len(win) // 2], 2)
        meas = [q for q in rows if q["far_kerb_m"] is not None]
        bulge = [q["source_half_m"] - q["base_half_m"] for q in rows]
        # THE FAR HALF APPLIED: the measured edge, held between the street's own half width and the source's flared half;
        # between two read rows the edge is interpolated, outside the outermost read rows (and in a flare with none) the
        # source's half stands: no edge moves where nothing was read
        ix = [i for i, q in enumerate(rows) if q["far_kerb_m"] is not None]
        edge = [None] * len(rows)
        for a_, b_ in zip(ix, ix[1:]):
            for i in range(a_, b_ + 1):
                t_ = (i - a_) / ((b_ - a_) or 1)
                edge[i] = rows[a_]["far_kerb_m"] + (rows[b_]["far_kerb_m"] - rows[a_]["far_kerb_m"]) * t_
        if len(ix) == 1:
            edge[ix[0]] = rows[ix[0]]["far_kerb_m"]
        far_applied = []
        for q, e_ in zip(rows, edge):
            f = q["source_half_m"] if e_ is None else max(q["base_half_m"], min(e_, q["source_half_m"]))
            far_applied.append(f)
            q["far_half_m"] = round(f, 3)
            q["width_m"] = round(q["source_half_m"] + f, 3)
            q["move_m"] = round((q["source_half_m"] - f) / 2.0, 3)       # toward the street's side
            q["line_xz"] = [round(pts[q["k"]][0], 3), round(pts[q["k"]][2], 3)]
        narrowed = [round(q["source_half_m"] - f, 3) for q, f in zip(rows, far_applied)]
        rec = {"id": r["id"], "v": [v0, v1], "street": r["street"], "street_side": side,
               "far_narrowed_m_max": max(narrowed), "far_narrowed_rows": sum(1 for x in narrowed if x > 1e-3),
               "kinds": {k_: sum(1 for q in rows if q["kind"] == k_) for k_ in ("curb", "drop")},
               "street_end_from_line_m": dist, "street_end_vertex": k_near, "rows": rows,
               "measured_rows": len(meas), "rows_total": len(rows),
               "source_far_bulge_max_m": round(max(bulge), 2),
               "far_kerb_minus_base_m": ([round(min(q["far_kerb_m"] - q["base_half_m"] for q in meas), 2),
                                          round(max(q["far_kerb_m"] - q["base_half_m"] for q in meas), 2)] if meas else None),
               "why": r.get("why", "")}
        out.append(rec)
        print(f"[flare_one_sided] {r['id']} v{v0}..v{v1}: street {r['street']} on side {side:+d} ({dist} m from the line "
              f"at v{k_near}); far kerb read at {len(meas)} of {len(rows)} rows; source's far bulge up to "
              f"{rec['source_far_bulge_max_m']} m ({rec['kinds']}); measured edge - street's own half width "
              f"{rec['far_kerb_minus_base_m']}; the far side narrowed at {rec['far_narrowed_rows']} rows, up to "
              f"{rec['far_narrowed_m_max']} m")
    return {"_doc": "tools/flare_one_sided.py (ledger 0098): per declared flare, per lap vertex, the far side's kerb off the "
                    "source lidar (class 2, the step map's first rise >= 0.08 m); applied by tools/lm_engine_intake.py "
                    "(lm_intake.flare_one_sided)",
            "line": f"tracks/{(cfg.get('lm_intake') or {})['source_track']}/data/centerline.local.json",
            "line_xz_check": [[round(pts[k][0], 3), round(pts[k][2], 3)] for k in (0, len(pts) // 2)],
            "tiles_missing": sorted([list(t) for t in missing]), "flares": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    proj = Path(a.project).resolve()
    rec = measure(proj, Path(a.tiles))
    out = Path(a.out) if a.out else proj / "source" / "flares_one_sided.lidar.json"
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"[flare_one_sided] {len(rec['flares'])} flare(s) -> {out}; tiles not in the cache: {len(rec['tiles_missing'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
