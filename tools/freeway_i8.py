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

    python tools/freeway_i8.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

BARRIER_HALF_M = 0.30   # the Jersey barrier's foot half-width (tools/ground_release_blend.RAIL_BASE_M / 2)


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


def build(proj: Path) -> dict | None:
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
    barrier = barrier_lines(chains[0], plain[1], float(P.get("barrier_gap_max_m", 40.0)))
    med = [st["median_side"] for ch in chains for st in ch if st is not None]
    rep = {"_doc": "tools/freeway_i8.py — the I-8 carriageways, lane lines and median barrier (ledger 0046 v0.18.0 "
                   "integration fix round). Local frame; per station: centre (x, z), unit tangent, lanes, half-widths "
                   "left (wl) / right (wr) of travel, edge-line and dashed lane-line offsets (+ = left); null = an OSM "
                   "bridge way (not draped)",
           "_provenance": {"source": prov["source"], "osm_cache": prov["osm_cache"],
                           "chain_a_way_ids": prov["chain_a_way_ids"], "chain_b_way_ids": prov["chain_b_way_ids"]},
           "params": {k: P[k] for k in P if not k.startswith("_")},
           "chains": chains, "barrier": barrier,
           "median_on_left": round(sum(1 for m in med if m > 0) / max(1, len(med)), 4)}
    out_p.write_text(json.dumps(rep, separators=(",", ":")), encoding="utf-8")
    n = [sum(1 for s in ch if s is not None) for ch in chains]
    print(f"[freeway] I-8: carriageways {n[0]} + {n[1]} stations every {step} m "
          f"({sum(1 for ch in chains for s in ch if s is None)} on OSM bridge ways, left out), "
          f"median barrier {len(barrier)} run(s) / {sum(len(b) for b in barrier)} points; median on the left of travel "
          f"at {100 * rep['median_on_left']:.1f} % of stations -> data/freeway_i8.json")
    return rep


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python tools/freeway_i8.py <project-dir>")
    build(Path(args[0]))


if __name__ == "__main__":
    main()
