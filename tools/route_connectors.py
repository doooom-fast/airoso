"""Derive the side streets from Kevin's ROUTES, not from street names.

Kevin (2026-10-08, seat): "side streets ... there's a bunch of disjointed streets that don't connect
in the path that I defined for you." Measured: the per-name connectors (extra_lines: merge every
OSM way called X) left Del Cerro Ave 120 m short of Del Cerro Blvd, Pennsylvania Lane absent, and
Connecticut's north end 140 m from Pennsylvania's — because the real path runs Del Cerro Ave →
MADRA Ave → Del Cerro Blvd and Pennsylvania → DELAWARE Ave → Connecticut, streets nobody listed.
tools/route_tracks.py + data/routes.json (airoso V2) already encode the three confirmed routes as
continuous node paths on the real OSM graph. This tool turns the medium and short routes' off-loop
portions into connector polylines: every piece is a contiguous run of route points that are NOT on
the full loop (and not on Del Cerro Blvd, which stays the divided trunk), extended one point into
the road it joins at each end so trim_connectors butts it to the pavement edge.

Elevation: live USGS 3DEP per point (scripts.elevation.usgs_3dep, the same source extra_lines
used), despiked/smoothed/grade-capped like extra_lines; fallback = nearest old connector point.

Writes data/connectors.local.json AND .pre-divide (the base for divide → trim); keeps the entries
named in route.route_connectors.keep (del_cerro_blvd). Idempotent from .pre-route (written once).

    python tools/route_connectors.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AIROSO))

RESAMPLE_M = 3.0
MAIN_PAD = 1.0
DCB_REACH = 12.0
MIN_PIECE_M = 30.0
WIDTH_M = 10.0
MAX_GRADE = 0.11


def _mpd(lat):
    r = 6371000.0
    return r * math.cos(math.radians(lat)) * math.pi / 180.0, r * math.pi / 180.0


def _seg_dist(px, pz, line):
    best, bi = float("inf"), 0
    for i in range(len(line) - 1):
        ax, az, bx, bz = line[i][0], line[i][2], line[i + 1][0], line[i + 1][2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        d = math.hypot(px - (ax + t * dx), pz - (az + t * dz))
        if d < best:
            best, bi = d, i
    return best, bi


def _resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg == 0:
            continue
        while acc + step <= seg:
            acc += step
            t = acc / seg
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        acc -= seg
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def _despike_smooth_cap(z, spacing):
    n = len(z)
    if n < 3:
        return list(z)
    med = [z[0]] + [sorted(z[i - 1:i + 2])[1] for i in range(1, n - 1)] + [z[-1]]
    # two mean passes over ~75 m (was one over 45 m): Kevin 2026-10-09 "smooth out the roughness" —
    # 3DEP sample noise at 3 m spacing reads as texture under the wheels on the side streets
    k = max(3, round(75.0 / spacing)) | 1
    h = k // 2
    sm = list(med)
    for _ in range(2):
        sm = [sum(sm[max(0, i - h):min(n, i + h + 1)]) / len(sm[max(0, i - h):min(n, i + h + 1)]) for i in range(n)]
    cap = MAX_GRADE * spacing
    for i in range(1, n):
        sm[i] = max(sm[i - 1] - cap, min(sm[i - 1] + cap, sm[i]))
    for i in range(n - 2, -1, -1):
        sm[i] = max(sm[i + 1] - cap, min(sm[i + 1] + cap, sm[i]))
    return sm


def _authored_take(rname, path, ids, local):
    """the named weld stubs of an authored intermediate (tools/author_expansion.py) as connector records: the centre +
    width per point exactly as authored (the flare is the curb returns — never resampled here), the 3DEP height
    smoothed like every route piece (despike + 2 x 75 m mean + the 11 % cap). The intermediate must be in this
    project's frame (same origin), or nothing is taken"""
    doc = json.loads(path.read_text(encoding="utf-8"))
    o, lo = doc.get("frame", {}).get("origin", {}), local["origin"]
    if any(abs(float(o.get(k, 1e9)) - float(lo[k])) > 1e-9 for k in ("lon", "lat", "elev_m")):
        raise SystemExit(f"[route-conn] {rname}: {path.name} is in another frame (origin {o}) than "
                         f"centerline.local.json ({lo}) - rerun tools/author_expansion.py")
    welds = {w["id"]: w for w in doc.get("welds", [])}
    piece_ids = {pc["id"] for pc in doc.get("pieces", [])}
    out = []
    # ledger 0054 P3 (step 1): a PIECE id (A-D) takes the whole road piece (tools/expansion_pieces.py: the pavement
    # midline + curb-to-curb width per station, a welded piece starting with its P1 weld stub, a pad end exactly on the
    # pad's arm cut, the 3DEP profile through a local quadratic fit — never re-smoothed here: route_connectors' running
    # means are one-sided at a piece's end); a piece that carries a weld replaces that weld's stub
    taken_pieces = [x for x in ids if x in piece_ids]
    if taken_pieces:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import expansion_pieces as ep
        _doc, pieces = ep.load(path)
        for pid in taken_pieces:
            c = ep.piece_connector(_doc, pieces, pid)
            g, at = ep.grade_report(c)
            out.append(c)
            print(f"[route-conn] {rname}: piece {pid} taken from {path.name} -> {c['name']} ({len(c['points_xyz_m'])} "
                  f"pts, width {min(c['widths_m']):.1f}..{max(c['widths_m']):.1f} m, steepest {100 * g:.1f} %"
                  f"{' - OVER the 11 % cap' if g > MAX_GRADE + 1e-9 else ', the 11 % cap binds nowhere'}; ledger 0054 P3)")
    covered = {w["id"] for w in doc.get("welds", []) if w.get("piece") in taken_pieces}
    for wid in ids:
        if wid in piece_ids or wid in covered:
            continue
        if wid not in welds:
            raise SystemExit(f"[route-conn] {rname}: authored_take names {wid!r}; {path.name} has welds {sorted(welds)}"
                             f" and pieces {sorted(piece_ids)}")
        c = welds[wid]["connector"]
        pts = c["points_xyz_m"]
        y = _despike_smooth_cap([p[1] for p in pts], RESAMPLE_M)
        out.append({"name": c["name"], "kind": "connector",
                    "points_xyz_m": [[p[0], round(yy, 3), p[2]] for p, yy in zip(pts, y)],
                    "widths_m": list(c["widths_m"])})
        print(f"[route-conn] {rname}: {wid} taken from {path.name} -> {c['name']} (ledger 0054 P1, "
              f"route_connectors.authored_take)")
    return out


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    rc = cfg.get("route", {}).get("route_connectors")
    if not rc:
        print("[route-conn] no route.route_connectors configured — nothing to do")
        return
    routes = json.loads((AIROSO / "data" / "routes.json").read_text(encoding="utf-8"))
    src = data / "connectors.local.json"
    bak = data / "connectors.local.json.pre-route"
    if bak.exists():
        old = json.loads(bak.read_text(encoding="utf-8"))
    else:
        pre = data / "connectors.local.json.pre-divide"
        old = json.loads((pre if pre.exists() else src).read_text(encoding="utf-8"))
        bak.write_text(json.dumps(old), encoding="utf-8")
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    o = local["origin"]
    lon0, lat0, elev0 = o["lon"], o["lat"], o["elev_m"]
    m_lon, m_lat = _mpd(lat0)
    main = [tuple(p) for p in local["points_xyz_m"]]
    main_w = local["widths_m"]
    keep = set(rc.get("keep", []))
    kept = [c for c in old.get("connectors", []) if c["name"] in keep]
    old_pts = [tuple(p) for c in old.get("connectors", []) for p in c["points_xyz_m"]]
    # "on the loop" is judged against the FULL route's own raw node path (same OSM nodes as the
    # medium/short paths), NOT the built mainline — the median tool shifts the built line up to
    # 12 m off the raw line on College/Navajo, which leaked 2 km of the loop into the first run
    full = [((lo - lon0) * m_lon, 0.0, (la - lat0) * m_lat) for lo, la in routes["full"]["coords"]]
    blocked_lines = [(full, [6.0] * len(full)), (main, [w / 2.0 - 2.0 for w in main_w])]
    for c in kept:
        blocked_lines.append(([tuple(p) for p in c["points_xyz_m"]], [DCB_REACH] * len(c["points_xyz_m"])))

    def on_road(x, z):
        for line, reach in blocked_lines:
            d, i = _seg_dist(x, z, line)
            if d <= reach[min(i, len(reach) - 1)]:
                return True
        return False

    try:
        from scripts.elevation import usgs_3dep
    except Exception:
        usgs_3dep = None

    pieces = []
    # ledger 0054 (P0, 2026-10-14): a route named in route_connectors.authored_routes is NOT drawn here as constant
    # WIDTH_M pieces. Its roads are 17-33 m divided boulevards whose geometry is the readable intermediate Claude
    # authors (EXPANSION-PLAN P1, data/expansion.<name>.json) and route_connectors takes it over in P3; until then the
    # route is HELD — listed in routes so the plan of record is visible, contributing no connector. Absent key: as before.
    authored = dict(rc.get("authored_routes") or {})
    # ledger 0054 P1 (opt-in): route_connectors.authored_take {route: [weld id, ...]} takes those parts of the authored
    # intermediate over as connectors NOW — the weld stubs (data/expansion.<route>.json welds[].connector: the new road
    # flared onto the loop's outer edge with its curb returns, EXPANSION-PLAN P1 step 5's rehearsal). Absent key: the
    # authored route stays HELD, as before. P3 extends the take to the whole pieces.
    take = dict(rc.get("authored_take") or {})
    authored_conns = []
    for rname in rc.get("routes", ["medium", "short"]):
        if rname in authored:
            ap = Path(str(authored[rname]))
            ap = ap if ap.is_absolute() else proj / ap
            ids = [str(x) for x in (take.get(rname) or [])]
            if ids:
                if not ap.exists():
                    raise SystemExit(f"[route-conn] {rname}: route_connectors.authored_take names {ids} but the "
                                     f"authored intermediate {authored[rname]} is not in the project (sync it in)")
                authored_conns += _authored_take(rname, ap, ids, local)
                continue
            print(f"[route-conn] {rname}: HELD - an authored route (route_connectors.authored_routes -> "
                  f"{authored[rname]}, {'present' if ap.exists() else 'not written yet'}); no connector drawn "
                  f"from it here (ledger 0054: its pieces come from the authored intermediate, P3)")
            continue
        coords = routes[rname]["coords"]
        pts = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in coords]
        on = [on_road(x, z) for x, z in pts]
        n = len(pts)
        i = 0
        k = 0
        while i < n:
            if on[i]:
                i += 1
                continue
            j = i
            while j < n and not on[j]:
                j += 1
            run = pts[max(0, i - 1):min(n, j + 1)]      # one on-road point at each end
            L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run, run[1:]))
            if L >= MIN_PIECE_M:
                pieces.append((f"{rname}#{k}", run))
                k += 1
            i = j

    # drop SPURS: a run whose two ends sit within 40 m of each other is an out-and-back routing
    # artefact (routes.json's medium carried a 1.5 km one SW of the loop), not a street Kevin named
    kept_pieces = []
    for name, run in pieces:
        if math.hypot(run[0][0] - run[-1][0], run[0][1] - run[-1][1]) < 40.0:
            print(f"[route-conn] {name}: out-and-back spur ({len(run)} pts) — dropped")
            continue
        kept_pieces.append((name, run))
    # dedupe FIRST (medium and short share the neighbourhood chain), then chain the survivors —
    # merging before dedupe once chained the chain to its own duplicate into a 5.1 km there-and-back
    uniq = []
    for name, run in kept_pieces:
        dup = False
        for _, prev in uniq:
            prev3 = [(p[0], 0.0, p[1]) for p in prev]
            near = sum(1 for x, z in run if _seg_dist(x, z, prev3)[0] <= 3.0)
            if near >= 0.9 * len(run):
                dup = True
                break
        if not dup:
            uniq.append((name, run))
    kept_pieces = uniq
    # chain pieces whose ends coincide (< 3 m) into one polyline — a corner, not a junction
    merged = True
    while merged:
        merged = False
        for a in range(len(kept_pieces)):
            for b in range(len(kept_pieces)):
                if a == b:
                    continue
                na, ra = kept_pieces[a]
                nb, rb = kept_pieces[b]
                if math.hypot(ra[-1][0] - rb[0][0], ra[-1][1] - rb[0][1]) < 3.0:
                    kept_pieces[a] = (f"{na}+{nb.split('#')[-1]}", ra + rb[1:])
                    del kept_pieces[b]
                    merged = True
                    break
                if math.hypot(ra[-1][0] - rb[-1][0], ra[-1][1] - rb[-1][1]) < 3.0:
                    kept_pieces[a] = (f"{na}+{nb.split('#')[-1]}", ra + list(reversed(rb))[1:])
                    del kept_pieces[b]
                    merged = True
                    break
            if merged:
                break
    pieces = kept_pieces

    accepted = [(name, _resample(run, RESAMPLE_M)) for name, run in pieces]

    out = list(kept)
    for name, rs in accepted:
        lonlat = [(lon0 + x / m_lon, lat0 + z / m_lat) for x, z in rs]
        z_abs = None
        if usgs_3dep is not None:
            try:
                z_abs = usgs_3dep.sample_points(lonlat)
            except Exception as e:
                print(f"[route-conn] 3DEP failed for {name} ({e}) — falling back to nearest old points")
        if z_abs is None:
            z_abs = []
            for x, z in rs:
                q = min(old_pts + main, key=lambda p: (p[0] - x) ** 2 + (p[2] - z) ** 2)
                z_abs.append(q[1] + elev0)
        y = _despike_smooth_cap([v - elev0 for v in z_abs], RESAMPLE_M)
        out.append({"name": name, "kind": "connector",
                    "points_xyz_m": [[round(x, 3), round(yy, 3), round(z, 3)] for (x, z), yy in zip(rs, y)],
                    "widths_m": [WIDTH_M] * len(rs)})
        print(f"[route-conn] {name}: {len(rs)} pts, {RESAMPLE_M * (len(rs) - 1):.0f} m, y {min(y):.1f}..{max(y):.1f}")

    for c in authored_conns:
        out.append(c)
        ys = [p[1] for p in c["points_xyz_m"]]
        print(f"[route-conn] {c['name']}: {len(c['points_xyz_m'])} pts (authored {'piece' if c.get('expansion') else 'weld stub'}), width "
              f"{min(c['widths_m']):.1f}..{max(c['widths_m']):.1f} m, y {min(ys):.1f}..{max(ys):.1f}")
    payload = dict(old)
    payload["connectors"] = out
    payload.pop("narrow_main", None)
    src.write_text(json.dumps(payload), encoding="utf-8")
    (data / "connectors.local.json.pre-divide").write_text(json.dumps(payload), encoding="utf-8")
    pt = data / "connectors.local.json.pre-trim"
    if pt.exists():
        pt.unlink()
    print(f"[route-conn] {len(out)} connector(s): {len(kept)} kept + {len(accepted)} route piece(s) "
          f"({len(pieces) - len(accepted)} duplicate(s) dropped) -> connectors.local.json + .pre-divide")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/route_connectors.py <project-dir>")
    build(sys.argv[1])
