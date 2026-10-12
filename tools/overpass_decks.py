"""The C-470 bridges over the Lariat lap (V3-PLAN P3a ``overpass_decks``, D5: "Build the bridges"), the data half.

Lookout Lariat V3 (ledger 0048). The lap passes UNDER C-470 twice: on West Colfax (aerial window X19340: one 35.7 m
concrete surface carrying both C-470 carriageways and both links, OSM ways 84720931 / 84720904 / 84721006 /
1459465701) and on US-6 (X21138: the 13.2 m north-bound deck, way 84720905). The integrated Drive-1 build had no deck
at all, so the lap ran under open sky between two embankments (the verifiers' drive lens, 2026-10-12), against the
plan's "-> Drive 1" box ("The C-470 decks are in").

The decks are SCENERY: no digit prefix (no physics, no gate reads them as road), named ``AUTH_overpass_*``, never
``HIGHWAY*``; no pavement continues along the lap. This tool computes them; tools/author_overpass_blend.py writes them
into loop.blend (collection ``AUTH_overpass``).

FROM WHAT (no invented geometry where a measurement exists):
- alignment: each OSM bridge way's own geometry (``data/osm.widths.cache.json``, the widths stage's Overpass payload);
- width: the aerial pass (``data/aerial/aerial_measurements.json`` c470.crossings deck_width_m.median [measured]),
  shared among a structure's ways by their OSM lane counts;
- height: USGS 3DEP along each way (bare earth: under a bridge it reads the ground, on the approach fills the fill's
  top). The deck runs between the two PLATEAUS either side of the lap crossing (scanning outward, the first 3DEP point
  at least ``ABUTMENT_RISE_M`` above the ground at the crossing [invented]) as a straight line between their heights;
  a way whose structure continues past its own end (no plateau on that side) takes the structure's height at the lap
  (the mean over its ways that have both plateaus) and runs level to that end;
- depth: ``DECK_DEPTH_M`` [invented]; piers every ``PIER_EVERY_M`` [invented] where the deck stands more than
  ``PIER_MIN_H_M`` over the ground, never within ``PIER_CLEAR_M`` [invented] of the lap's pavement edge.

Reported per deck: the clearance under it over the lap road (deck underside minus the lap centreline height at the
crossing), against 4.9 m [std: AASHTO / FHWA 16 ft minimum vertical clearance] — reported, not adjusted.

Writes ``data/overpass_decks.json`` (local frame: x = E, y = up, z = N about centerline.local.json's origin) and
caches the 3DEP samples in ``data/overpass.elev.json``. Exit 0, 1 when a crossing cannot be built (a way missing from
the payload, no plateau on either side), 2 on a usage error.

    python tools/overpass_decks.py <project-dir>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

SAMPLE_M = 2.5               # 3DEP sampling along each way (measurement resolution, not a threshold)
ABUTMENT_RISE_M = 5.5        # [invented] a plateau = 3DEP this far above the ground at the crossing
PLATEAU_INTO_M = 4.0         # [invented] the deck runs this far onto each fill (its seat)
DECK_DEPTH_M = 1.5           # [invented] slab + girders
PIER_EVERY_M = 30.0          # [invented]
PIER_MIN_H_M = 3.0           # [invented]
PIER_CLEAR_M = 4.0           # [invented] from the lap's pavement edge
PIER_SIZE_M = 1.2            # [invented]
CLEARANCE_STD_M = 4.9        # [std] AASHTO / FHWA 16 ft
PARAMS = {k: globals()[k] for k in ("SAMPLE_M", "ABUTMENT_RISE_M", "PLATEAU_INTO_M", "DECK_DEPTH_M", "PIER_EVERY_M",
                                    "PIER_MIN_H_M", "PIER_CLEAR_M", "PIER_SIZE_M", "CLEARANCE_STD_M")}


def _resample(g, mlon, mlat, step):
    pts = []
    for a, b in zip(g, g[1:]):
        L = math.hypot((b[0] - a[0]) * mlon, (b[1] - a[1]) * mlat)
        n = max(1, int(math.ceil(L / step)))
        for k in range(n):
            t = k / n
            pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    pts.append(tuple(g[-1]))
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot((b[0] - a[0]) * mlon, (b[1] - a[1]) * mlat))
    return pts, s


def _sample(proj: Path, pts, sampler=None):
    """3DEP at every point, cached by the points' fingerprint (data/overpass.elev.json)."""
    key = hashlib.sha1(json.dumps([[round(a, 7), round(b, 7)] for a, b in pts]).encode()).hexdigest()[:16]
    cp = proj / "data" / "overpass.elev.json"
    cache = json.loads(cp.read_text(encoding="utf-8")) if cp.is_file() else {}
    if key in cache:
        return cache[key]
    if sampler is None:
        from scripts.elevation import usgs_3dep
        sampler = usgs_3dep.sample_points
    z = [float(v) for v in sampler(list(pts))]
    cache[key] = z
    cp.write_text(json.dumps(cache), encoding="utf-8")
    return z


def plateaus(s, z, s_cross):
    """(left index, right index) of the first 3DEP points either side of the crossing standing ABUTMENT_RISE_M over
    the ground there, or None for a side with none"""
    ic = min(range(len(s)), key=lambda i: abs(s[i] - s_cross))
    z0 = z[ic]
    left = next((i for i in range(ic, -1, -1) if z[i] >= z0 + ABUTMENT_RISE_M), None)
    right = next((i for i in range(ic, len(s)) if z[i] >= z0 + ABUTMENT_RISE_M), None)
    return left, right, ic


def _local(lon, lat, origin, mlon, mlat):
    return ((lon - origin[0]) * mlon, (lat - origin[1]) * mlat)


def build(project_dir, sampler=None) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    am = json.loads((data / "aerial" / "aerial_measurements.json").read_text(encoding="utf-8"))["c470"]
    pay = json.loads((data / "osm.widths.cache.json").read_text(encoding="utf-8"))["payload"]
    ways = {e["id"]: e for e in pay["elements"] if e.get("type") == "way"}
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    o = loc["origin"]
    origin = (float(o["lon"]), float(o["lat"]))
    elev0 = float(o["elev_m"])
    mlon, mlat = _meters_per_degree(origin[1])
    lap = [(p[0], p[1], p[2]) for p in loc["points_xyz_m"]]
    lw = loc["widths_m"]
    cells: dict = {}
    for i, p in enumerate(lap):
        cells.setdefault((int(p[0] // 20), int(p[2] // 20)), []).append(i)

    def lap_near(x, z):
        best = None
        for di in (-2, -1, 0, 1, 2):
            for dj in (-2, -1, 0, 1, 2):
                for i in cells.get((int(x // 20) + di, int(z // 20) + dj), ()):
                    d = math.hypot(lap[i][0] - x, lap[i][2] - z)
                    if best is None or d < best[0]:
                        best = (d, i)
        return best

    crossings = {c["way"]: c for c in am["osm_crossings"]}
    decks, problems = [], []
    for st in am["crossings"]:
        win = st["window"]
        wids = list(st["osm_ways_all_on_structure"])
        total_w = float(st["deck_width_m"]["median"])
        lanes = {w: max(1, int(str((ways.get(w) or {}).get("tags", {}).get("lanes", "1")).split(";")[0])) for w in wids}
        lanes_sum = sum(lanes.values())
        prof = {}
        for w in wids:
            e = ways.get(w)
            if e is None:
                problems.append(f"{win}: way {w} is not in data/osm.widths.cache.json")
                continue
            if w not in crossings:
                problems.append(f"{win}: way {w} has no lap crossing in aerial_measurements c470.osm_crossings")
                continue
            g = [(p["lon"], p["lat"]) for p in e["geometry"]]
            pts, s = _resample(g, mlon, mlat, SAMPLE_M)
            z = _sample(proj, pts, sampler)
            sc = float(crossings[w]["crossing_at_m_along_way"])
            left, right, ic = plateaus(s, z, sc)
            prof[w] = (pts, s, z, sc, left, right, ic)
        both = [w for w, p in prof.items() if p[4] is not None and p[5] is not None]
        if not both:
            problems.append(f"{win}: no way of the structure has a fill top on both sides of the lap")
            continue

        def line_at(p, i):
            pts, s, z, sc, left, right, ic = p
            zl, zr = z[left], z[right]
            return zl + (zr - zl) * (s[i] - s[left]) / max(1e-6, s[right] - s[left])
        ref = sum(line_at(prof[w], prof[w][6]) for w in both) / len(both)
        for w, p in prof.items():
            pts, s, z, sc, left, right, ic = p
            a = max(0, left - int(PLATEAU_INTO_M / SAMPLE_M)) if left is not None else 0
            b = min(len(s) - 1, right + int(PLATEAU_INTO_M / SAMPLE_M)) if right is not None else len(s) - 1
            line = []
            for i in range(a, b + 1):
                if left is not None and right is not None:
                    zt = line_at(p, i)
                elif left is not None:
                    zt = z[left] + (ref - z[left]) * min(1.0, (s[i] - s[left]) / max(1e-6, s[ic] - s[left]))
                elif right is not None:
                    zt = z[right] + (ref - z[right]) * min(1.0, (s[right] - s[i]) / max(1e-6, s[right] - s[ic]))
                else:
                    zt = ref
                x, zn = _local(pts[i][0], pts[i][1], origin, mlon, mlat)
                line.append([round(x, 3), round(zt - elev0, 3), round(zn, 3), round(z[i] - elev0, 3)])
            # the lap under it: the lap centreline point nearest the crossing
            xc, zc = _local(pts[ic][0], pts[ic][1], origin, mlon, mlat)
            near = lap_near(xc, zc)
            k = ic - a
            under = line[k][1] - DECK_DEPTH_M
            clearance = round(under - lap[near[1]][1], 2) if near else None
            piers = []
            last = -1e9
            for j, (x, y, zn, gy) in enumerate(line):
                sj = s[a + j]
                if sj - last < PIER_EVERY_M or y - DECK_DEPTH_M - gy < PIER_MIN_H_M:
                    continue
                q = lap_near(x, zn)
                if q is not None and q[0] < lw[q[1]] / 2.0 + PIER_CLEAR_M:
                    continue
                piers.append([x, round(gy - 1.0, 3), zn, round(y - DECK_DEPTH_M, 3)])
                last = sj
            decks.append({"name": f"AUTH_overpass_{win}_{w}", "window": win, "way": w,
                          "ref": (ways[w].get("tags") or {}).get("ref"),
                          "width_m": round(total_w * lanes[w] / lanes_sum, 2), "depth_m": DECK_DEPTH_M,
                          "line_xyz_ground": line, "plateaus": [left is not None, right is not None],
                          "length_m": round(s[b] - s[a], 1),
                          "lap_vertex": near[1] if near else None, "clearance_over_lap_m": clearance,
                          "clearance_ok_vs_std": (clearance is not None and clearance >= CLEARANCE_STD_M),
                          "piers": piers})
    return {"tool": "tools/overpass_decks.py", "params": PARAMS, "frame": "local ENU (x E, y up, z N), origin "
            "data/centerline.local.json", "decks": decks, "problems": problems,
            "_doc": "scenery only (no digit prefix), written into loop.blend by tools/author_overpass_blend.py"}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python tools/overpass_decks.py <project-dir>")
        return 2
    try:
        rep = build(argv[0])
    except (OSError, KeyError, ValueError) as e:
        print(f"[overpass] INPUT ERROR: {e!r}")
        return 2
    out = Path(argv[0]) / "data" / "overpass_decks.json"
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    for d in rep["decks"]:
        print(f"[overpass] {d['name']}: {d['length_m']} m long, {d['width_m']} m wide, plateaus {d['plateaus']}, "
              f"clearance over the lap {d['clearance_over_lap_m']} m (std {CLEARANCE_STD_M} m: "
              f"{'ok' if d['clearance_ok_vs_std'] else 'BELOW'}), {len(d['piers'])} piers")
    for p in rep["problems"]:
        print(f"[overpass] PROBLEM: {p}")
    print(f"[overpass] wrote {out}")
    return 1 if rep["problems"] or not rep["decks"] else 0


if __name__ == "__main__":
    sys.exit(main())
