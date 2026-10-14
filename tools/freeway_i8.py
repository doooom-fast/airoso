"""Plan the I-8 freeway's own pavement in its cut — the carriageways, their lane lines and the median barrier, from
the same OSM ways the I-8 corridor was cut from (ledger 0046, v0.18.0 integration fix round: the view lens).

WHY. 0046 cut the I-8 corridor into the ground from 3DEP (Kevin, 2026-10-10: "the I-8 trench and adjacent causeway cut
out"), but left the freeway itself out ("Kevin's call: a visual-only I-8 pavement ribbon"). From the College Ave and
Lake Murray Blvd decks the cut then read as what it was built as: a grassy valley — the view lens refuted it twice
("lawn rolling down about 5 m and back up into hills, with no freeway"). The real view from those decks, per 3DEP, is a
broad shallow valley with gentle sides (ledger 0046 fix round 2): what makes it the I-8 is the eight to twelve lanes of
concrete in it. This is that pavement — visual only, no physics, nothing a gate drives on.

WHAT (pure python, no bpy; the Blender half is tools/author_freeway_blend.py, run on the PREPPED scene so the pavement
drapes on the final ground). From data/corridor.i8.json's provenance (the OSM cache and the two carriageway chains'
way ids, in chain order): each carriageway resampled every step_m, its lanes from the way's OSM lanes tag, its outer
edge lanes x lane_m / 2 + outer_shoulder_m from the way centreline, its inner (median) edge lanes x lane_m / 2 +
inner_shoulder_m but never past the median line less half the barrier; OSM bridge ways are left out (a deck over a
valley is not draped on the valley floor). A concrete median barrier runs midway between the two carriageways wherever
they are within barrier_gap_max_m. Writes data/freeway_i8.json (also read by tools/make_treefx.py: no tree on a lane).

HEIGHTS (fix round 2, 2026-10-13, the view lens: under College Ave the north carriageway climbed a 5-6 m hump to within
2 m of the deck, and at Lake Murray Blvd the outer lanes ran up the abutment slopes): the pavement is no longer draped on
the built ground. Each station's height across its carriageway is the bare-earth 3DEP (fresh, cached in
data/freeway_i8.samples.json.gz with provenance; missing points fetched, TLS verified, no gap filling) read at its right
edge, centre and left edge; an edge more than XSLOPE_MAX x its offset off the centre (a cut wall or a fill's shoulder
inside the 3 m shoulder) is held to that cross slope, and each series is 1-2-1 smoothed along the chain (SMOOTH_PASSES)
— a real freeway is a near-flat slab, 1.5-2 % across. tools/author_freeway_blend.py then makes the GROUND meet the slab
(it cuts the pavement's edges into the terrain and sets the ground inside them under it), not the slab meet the ground.
Measured on the v0.18.0 integration build: the built ground at the carriageway edges was 2-8 m off 3DEP for 1.1 km east
of College and under both decks (the 5 m corridor cells straddle the real cut walls); the station's own 3DEP across
each carriageway varies 0.1-0.5 m.

    python tools/freeway_i8.py <project-dir> [--offline]
"""
from __future__ import annotations

import gzip
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

BARRIER_HALF_M = 0.30   # the Jersey barrier's foot half-width (tools/ground_release_blend.RAIL_BASE_M / 2)
XSLOPE_MAX = 0.08       # [invented] steepest cross slope of a carriageway (interstate crown 1.5-2 %, superelevation <= 8 %)
XSLOPE_TOL_M = 0.15      # [invented] 3DEP's read noise on a slab, on top of the cross slope
MIN_PAVED_M = 3.66       # one lane: a station with less real pavement than that is not laid
SMOOTH_PASSES = 2       # [invented] 1-2-1 passes along a chain over the 4 m stations (3DEP 1 m reads +-5 cm on a slab)
SAMPLES = "freeway_i8.samples.json.gz"


def edge_heights(hr, hc, hl, wr, wl, xmax=XSLOPE_MAX):
    """the 3DEP heights at a station's right edge / centre / left edge, each edge held within xmax x its offset of the
    centre (a cut wall or a fill's shoulder caught at the edge). Pure."""
    def hold(h, w):
        return max(hc - xmax * w, min(hc + xmax * w, h))
    return hold(hr, wr), hc, hold(hl, wl)


def smooth_series(vals, passes=SMOOTH_PASSES):
    """1-2-1 along a run of stations (ends kept). Pure."""
    v = list(vals)
    for _ in range(passes):
        if len(v) < 3:
            break
        v = [v[0]] + [(v[k - 1] + 2 * v[k] + v[k + 1]) / 4.0 for k in range(1, len(v) - 1)] + [v[-1]]
    return v


def station_offsets(st):
    """the lateral offsets 3DEP is read at: the centre, every lane line and edge line, both pavement edges"""
    return sorted({0.0, round(-st["wr"], 3), round(st["wl"], 3), *(round(o, 3) for o in st["edge"]),
                   *(round(o, 3) for o in st["dash"])})


def paved_widths(prof, wr, wl, xmax=XSLOPE_MAX, tol=XSLOPE_TOL_M):
    """(right, left) paved width of a station: from the centre outward, the farthest read offset up to which every
    3DEP read stays within xmax x offset + tol of the centre — where the real ground leaves the slab (a cut wall, a
    fill's shoulder, an adjacent ramp) the pavement stops at the last read on the slab. Pure."""
    p = dict(prof)
    hc = p[0.0]
    out = []
    for sign, w in ((-1, wr), (1, wl)):
        keep = 0.0
        for o in sorted((o for o in p if o * sign > 0 and abs(o) <= w + 1e-6), key=abs):
            if abs(p[o] - hc) <= xmax * abs(o) + tol:
                keep = abs(o)
            else:
                break
        out.append(keep)
    return out[0], out[1]


def interp_prof(p, o):
    ks = sorted(p)
    if o <= ks[0]:
        return p[ks[0]]
    if o >= ks[-1]:
        return p[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= o <= b:
            return p[a] + (p[b] - p[a]) * ((o - a) / (b - a) if b > a else 0.0)
    return p[ks[-1]]


def median_filter(vals, k=2):
    out = []
    for i in range(len(vals)):
        w = sorted(vals[max(0, i - k):i + k + 1])
        out.append(w[len(w) // 2])
    return out


def height_at(st, o):
    """the planned pavement height at lateral offset o (+ = left of travel) of a station with h = [right, centre, left]:
    linear between the right edge, the centre and the left edge. Pure."""
    hr, hc, hl = st["h"]
    if o >= 0:
        return hc + (hl - hc) * (o / st["wl"] if st["wl"] > 0 else 0.0)
    return hc + (hr - hc) * (-o / st["wr"] if st["wr"] > 0 else 0.0)


def resample(poly, step):
    """[(x, z, attr)] polyline -> stations every ``step`` m: (x, z, tx, tz, attr of the segment it lies on)"""
    out = []
    acc = 0.0
    for (ax, az, at), (bx, bz, _bt) in zip(poly, poly[1:]):
        L = math.hypot(bx - ax, bz - az)
        if L <= 0:
            continue
        tx, tz = (bx - ax) / L, (bz - az) / L
        t = acc
        while t < L:
            out.append((ax + tx * t, az + tz * t, tx, tz, at))
            t += step
        acc = t - L
    return out


def nearest_on(poly, p):
    best = (1e18, None)
    for a, b in zip(poly, poly[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        q = (a[0] + dx * t, a[1] + dz * t)
        d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
        if d < best[0]:
            best = (d, q)
    return best[1], math.sqrt(best[0])


def plan_chain(stations, other_poly, P):
    """per station: centre, tangent, lanes, half-widths left / right (left = (-tz, tx), the median side of a one-way
    carriageway in a right-hand-traffic country), the lane line offsets; None where the station is on a bridge way"""
    out = []
    lane = float(P["lane_m"])
    for x, z, tx, tz, at in stations:
        if at["bridge"]:
            out.append(None)
            continue
        lanes = int(at["lanes"])
        half = lanes * lane / 2.0
        q, d = nearest_on(other_poly, (x, z))
        nx, nz = -tz, tx
        side = 1.0 if (q[0] - x) * nx + (q[1] - z) * nz >= 0 else -1.0      # +1: the other carriageway is on the left
        inner = half + float(P["inner_shoulder_m"])
        if d < 2.0 * inner + 2.0 * BARRIER_HALF_M:
            inner = max(half, d / 2.0 - BARRIER_HALF_M)
        outer = half + float(P["outer_shoulder_m"])
        wl, wr = (inner, outer) if side > 0 else (outer, inner)
        dashes = [-half + k * lane for k in range(1, lanes)]
        out.append({"x": round(x, 3), "z": round(z, 3), "tx": round(tx, 5), "tz": round(tz, 5), "lanes": lanes,
                    "wl": round(wl, 3), "wr": round(wr, 3), "edge": [round(-half, 3), round(half, 3)],
                    "dash": [round(o, 3) for o in dashes], "median_side": int(side), "gap_m": round(d, 2)})
    return out


def barrier_lines(sa, pb, gap_max):
    """polylines midway between carriageway A's stations and carriageway B wherever they are within ``gap_max``"""
    lines, cur = [], []
    for st in sa:
        if st is None:
            if len(cur) >= 2:
                lines.append(cur)
            cur = []
            continue
        q, d = nearest_on(pb, (st["x"], st["z"]))
        if d <= gap_max:
            cur.append([round((st["x"] + q[0]) / 2.0, 3), round((st["z"] + q[1]) / 2.0, 3)])
        else:
            if len(cur) >= 2:
                lines.append(cur)
            cur = []
    if len(cur) >= 2:
        lines.append(cur)
    return lines


def build(proj: Path, offline: bool = False) -> dict | None:
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    P = (cfg.get("scenery") or {}).get("freeway")
    out_p = data / "freeway_i8.json"
    if not P or not P.get("enabled"):
        if out_p.exists():
            out_p.unlink()
        print("[freeway] scenery.freeway not enabled — nothing to do")
        return None
    cor = json.loads((data / f"corridor.{P.get('corridor', 'i8')}.json").read_text(encoding="utf-8"))
    prov = cor["_provenance"]
    osm_p = AIROSO / prov["osm_cache"]
    osm = json.loads(osm_p.read_text(encoding="utf-8"))
    ways = {w["id"]: w for w in osm["ways"]}
    nodes = osm["nodes"]
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    o = cl["origin"]
    from scripts.geometry import terrain_tiers as tt
    m_lon, m_lat = tt.meters_per_degree(o["lat"])
    sx = -1.0 if cfg.get("mirror_x") else 1.0

    def to_local(lon, lat):
        return sx * (lon - o["lon"]) * m_lon, (lat - o["lat"]) * m_lat

    polys = []
    for key in ("chain_a_way_ids", "chain_b_way_ids"):
        poly = []
        for wid in prov[key]:
            w = ways[wid]
            t = w.get("tags") or {}
            try:
                lanes = int(str(t.get("lanes", P.get("default_lanes", 4))).split(";")[0])
            except ValueError:
                lanes = int(P.get("default_lanes", 4))
            at = {"lanes": lanes, "bridge": str(t.get("bridge", "no")) not in ("no", ""), "way": wid}
            pts = [to_local(*nodes[str(n)]) for n in w["nodes"] if str(n) in nodes]
            for k, p in enumerate(pts):
                if poly and k == 0:
                    poly[-1] = (poly[-1][0], poly[-1][1], at)        # the joint node starts this way's segment
                    continue
                poly.append((p[0], p[1], at))
        polys.append(poly)
    step = float(P.get("step_m", 4.0))
    sta = [resample(p, step) for p in polys]
    plain = [[(x, z) for x, z, _a in p] for p in polys]
    chains = [plan_chain(sta[0], plain[1], P), plan_chain(sta[1], plain[0], P)]
    # the slab's heights: 3DEP at each station's right edge, centre and left edge (cached, fetched when missing)
    elev0 = float(o["elev_m"])
    pts = []
    for ch in chains:
        for st in ch:
            if st is None:
                continue
            nx, nz = -st["tz"], st["tx"]
            for off in station_offsets(st):
                pts.append((round(st["x"] + nx * off, 2), round(st["z"] + nz * off, 2)))
    cache_p = data / SAMPLES
    sprov = {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
            "units": "metres above NAVD88", "origin": {"lon": o["lon"], "lat": o["lat"]}, "mirror_x": sx < 0,
            "key": "local x, z (m, 2 decimals) -> lon = lon0 + x / m_lon (x mirrored when mirror_x), lat = lat0 + "
                   "z / m_lat (terrain_tiers.meters_per_degree(lat0))", "fetches": []}
    cache = {}
    if cache_p.exists():
        d = json.loads(gzip.decompress(cache_p.read_bytes()).decode("utf-8"))
        p0 = d["_provenance"]
        if (abs(p0["origin"]["lon"] - o["lon"]) > 1e-12 or abs(p0["origin"]["lat"] - o["lat"]) > 1e-12
                or bool(p0.get("mirror_x")) != (sx < 0)):
            raise SystemExit(f"[freeway] {SAMPLES}: origin changed since it was cached — move it aside on purpose")
        sprov = p0
        cache = {(x, z): c / 100.0 for x, z, c in zip(d["X"], d["Z"], d["h_cm"])}
    need = sorted({p for p in pts if p not in cache})
    if need:
        if offline:
            raise SystemExit(f"[freeway] {len(need)} 3DEP points not cached and --offline")
        from scripts.elevation import terrain_sample as ts_mod
        vals = ts_mod.sample_lonlat([(o["lon"] + sx * x / m_lon, o["lat"] + z / m_lat) for x, z in need], "freeway")
        for k, v in zip(need, vals):
            cache[k] = v
        sprov["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "points": len(need), "what": "I-8 carriageway edges and centres"})
        ks = sorted(cache)
        cache_p.write_bytes(gzip.compress(json.dumps(
            {"_provenance": sprov, "X": [k[0] for k in ks], "Z": [k[1] for k in ks],
             "h_cm": [int(round(cache[k] * 100)) for k in ks]}, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    n_held = n_shrunk = n_dropped = 0
    for ci, ch in enumerate(chains):
        runs, cur = [], []
        for k, st in enumerate(ch + [None]):
            if st is None:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            nx, nz = -st["tz"], st["tx"]
            prof = [(off, cache[(round(st["x"] + nx * off, 2), round(st["z"] + nz * off, 2))] - elev0)
                    for off in station_offsets(st)]
            st["_prof"] = prof
            st["_w"] = paved_widths(prof, st["wr"], st["wl"])
            cur.append((k, st))
        for run in runs:
            # each side's paved width: the median of its neighbours' (one noisy 3DEP read never notches the slab)
            wr = median_filter([s["_w"][0] for _k, s in run])
            wl = median_filter([s["_w"][1] for _k, s in run])
            hs = []
            for (k, st), a, b in zip(run, wr, wl):
                n_shrunk += (a < st["wr"] - 1e-6) + (b < st["wl"] - 1e-6)
                st["wr"], st["wl"] = round(a, 3), round(b, 3)
                prof = dict(st.pop("_prof"))
                st.pop("_w")
                hr, hc, hl = interp_prof(prof, -a), prof[0.0], interp_prof(prof, b)
                held = edge_heights(hr, hc, hl, a, b)
                n_held += sum(1 for u, v in zip((hr, hc, hl), held) if abs(u - v) > 1e-9)
                hs.append(list(held))
            cols = [smooth_series([h[j] for h in hs]) for j in range(3)]
            for i, (k, st) in enumerate(run):
                st["h"] = [round(cols[0][i], 3), round(cols[1][i], 3), round(cols[2][i], 3)]
                if st["wr"] + st["wl"] < MIN_PAVED_M:
                    ch[k] = None                  # less than a lane's width of real pavement: not laid
                    n_dropped += 1
    barrier = barrier_lines(chains[0], plain[1], float(P.get("barrier_gap_max_m", 40.0)))
    med = [st["median_side"] for ch in chains for st in ch if st is not None]
    rep = {"_doc": "tools/freeway_i8.py — the I-8 carriageways, lane lines and median barrier (ledger 0046 v0.18.0 "
                   "integration fix round). Local frame; per station: centre (x, z), unit tangent, lanes, half-widths "
                   "left (wl) / right (wr) of travel, edge-line and dashed lane-line offsets (+ = left), h = the slab's "
                   "local height at the right edge / centre / left edge (3DEP, cross slope held, smoothed); null = an "
                   "OSM bridge way (not draped)",
           "_provenance": {"source": prov["source"], "osm_cache": prov["osm_cache"],
                           "chain_a_way_ids": prov["chain_a_way_ids"], "chain_b_way_ids": prov["chain_b_way_ids"]},
           "params": {k: P[k] for k in P if not k.startswith("_")},
           "chains": chains, "barrier": barrier,
           "median_on_left": round(sum(1 for m in med if m > 0) / max(1, len(med)), 4),
           "heights": {"source": SAMPLES, "points": len(pts), "fetched": len(need), "edges_held_to_xslope": n_held,
                       "xslope_max": XSLOPE_MAX, "xslope_tol_m": XSLOPE_TOL_M, "smooth_passes": SMOOTH_PASSES,
                       "sides_narrowed_to_the_real_pavement": n_shrunk, "stations_too_narrow_dropped": n_dropped}}
    out_p.write_text(json.dumps(rep, separators=(",", ":")), encoding="utf-8")
    n = [sum(1 for s in ch if s is not None) for ch in chains]
    print(f"[freeway] I-8: carriageways {n[0]} + {n[1]} stations every {step} m "
          f"({sum(1 for ch in chains for s in ch if s is None)} on OSM bridge ways, left out), "
          f"median barrier {len(barrier)} run(s) / {sum(len(b) for b in barrier)} points; median on the left of travel "
          f"at {100 * rep['median_on_left']:.1f} % of stations; heights from 3DEP at {len(pts)} points ({len(need)} "
          f"fetched, {n_shrunk} sides narrowed to where 3DEP leaves the slab, {n_dropped} stations dropped, {n_held} "
          f"edges held to {XSLOPE_MAX:.0%} cross slope) -> data/freeway_i8.json")
    return rep


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python tools/freeway_i8.py <project-dir>")
    build(Path(args[0]), offline="--offline" in sys.argv)


if __name__ == "__main__":
    main()
