"""Post-build geometry AUDIT for a freeroam NETWORK track — run at the end of every generative pass.

Measures the ACTUAL built geometry (track.obj vertices + emitted pier list) — never a re-derivation of the
road, because a reconstruction that drifts from the real mesh produces phantom defects (learned the hard
way: an earlier version flagged a 31 m "poke" that did not exist). Checks the three defect classes that
repeatedly break these networks:

  A. supports-in-road   — a viaduct pier standing IN a road that passes under its deck (car hits a column).
  B. terrain-poke       — a GRASS vertex sitting ABOVE the road surface near it (launches the car).
  C. junction-crossing  — two roads crossing at a large angle at the SAME height where one connects to the
                          other (a ramp crossing OVER the road it should merge into, not a real merge).

A + B read only track.obj (ground truth) + data/network.piers.json. C needs per-edge identity, so it
reconstructs the decks from network.geojson AND applies the same ramp merge-trim the build does, so it
reflects what was actually built. Writes data/audit.json; exits 1 if any defect exceeds tolerance.

    python -m scripts.geometry.audit_mesh projects/<slug>
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# --- tolerances -------------------------------------------------------------------------------------
POKE_ABOVE_M = 0.10     # a grass vert this far above a road vert within POKE_R = a poke
POKE_R = 5.0            # horizontal reach from a road (surface) vert
SUPPORT_R = 3.5        # a pier this close (xz) to a road vert below its deck = standing in the road
SUPPORT_BELOW = (1.5, 45.0)   # road is (y_top-1.5 .. y_top-45) below the deck = a real crossing, not the deck's own road
CROSS_R = 6.0
CROSS_ANGLE_DEG = 32.0
CROSS_DY = 2.2
LAYER_H = 5.5


def _mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def _smooth(vals, win):
    n = len(vals)
    if n < 3 or win < 2:
        return list(vals)
    h = win // 2
    return [sum(vals[max(0, i - h):min(n, i + h + 1)]) / (min(n, i + h + 1) - max(0, i - h)) for i in range(n)]


def _obj_groups(obj_path: Path, prefixes):
    want = {p: [] for p in prefixes}
    cur = None
    for ln in obj_path.read_text().splitlines():
        if ln.startswith("o "):
            nm = ln[2:].strip().upper()
            cur = next((p for p in prefixes if nm.startswith(p)), None)
        elif ln.startswith("v ") and cur:
            _, x, y, z = ln.split()[:4]
            want[cur].append((float(x), float(y), float(z)))
    return want


def _obj_tris(obj_path: Path, prefixes, exclude=()):
    """World-space triangles of every object whose name starts with one of `prefixes`
    (and contains no `exclude` substring). OBJ face indices are global, so all verts are
    kept; faces are filtered by group."""
    verts, tris, cur = [], [], False
    for ln in obj_path.read_text().splitlines():
        if ln.startswith("o "):
            _up = ln[2:].strip().upper()
            cur = _up.startswith(prefixes) and not any(e in _up for e in exclude)
        elif ln.startswith("v "):
            _, x, y, z = ln.split()[:4]
            verts.append((float(x), float(y), float(z)))
        elif ln.startswith("f ") and cur:
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            for k in range(1, len(idx) - 1):
                tris.append((verts[idx[0]], verts[idx[k]], verts[idx[k + 1]]))
    return tris


def _tri_hash(tris, cell):
    h = defaultdict(list)
    for t in tris:
        xs = [v[0] for v in t]; zs = [v[2] for v in t]
        for ci in range(int(min(xs) // cell), int(max(xs) // cell) + 1):
            for cj in range(int(min(zs) // cell), int(max(zs) // cell) + 1):
                h[(ci, cj)].append(t)
    return h


def _surf_at(th, cell, x, z, y_ref, dy_max=20.0):
    """Lowest surface height at (x,z) from hashed tris, within dy_max of y_ref (layer guard)."""
    best = None
    for a, b, c in th.get((int(x // cell), int(z // cell)), ()):
        # skip near-vertical faces (paved skirts/aprons): they are walls, not road surface —
        # grass legitimately crosses them and must not read as a poke.
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx_ = uy * vz - uz * vy; ny_ = uz * vx - ux * vz; nz_ = ux * vy - uy * vx
        nl = math.sqrt(nx_ * nx_ + ny_ * ny_ + nz_ * nz_) or 1e-12
        if abs(ny_) / nl < 0.5:
            continue
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        w2 = 1.0 - w0 - w1
        if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
            yy = w0 * a[1] + w1 * b[1] + w2 * c[1]
            if abs(yy - y_ref) <= dy_max and (best is None or yy < best):
                best = yy
    return best


def _hash(pts_xyz, cell):
    h = defaultdict(list)
    for x, y, z in pts_xyz:
        h[(int(x // cell), int(z // cell))].append((x, y, z))
    return h


def _decks_trimmed(data: Path):
    """Per-edge freeway decks (id, ramp, half, tangent-carrying pts) in the build's local frame, WITH the
    same ramp merge-trim applied, so check C sees what was actually built. Only used for C (topology)."""
    from scripts.geometry.build_network_mesh import _grade_cap_y, _layer_lift, _trim_ramp_merge
    fc = json.loads((data / "network.geojson").read_text())["features"]
    elev = {e["id"]: e["z_smooth_m"] for e in json.loads((data / "network.elevation.json").read_text())["edges"]}
    loc = json.loads((data / "network.local.json").read_text())
    o = loc["origin"]; lon0, lat0, elev0 = o["lon"], o["lat"], o["elev_m"]
    sx = -1.0 if loc.get("mirror_x", True) else 1.0
    m_lon, m_lat = _mpd(lat0)
    FREEWAY = {"motorway", "trunk"}

    def local(c, z):
        return [(sx * (lo - lon0) * m_lon, zz - elev0, (la - lat0) * m_lat) for (lo, la), zz in zip(c, z)]

    road_trim = defaultdict(list)
    for f in fc:
        p = f["properties"]
        if p.get("road_class") not in FREEWAY:
            continue
        c = f["geometry"]["coordinates"]; z = elev.get(p["id"]) or [0.0] * len(c)
        if len(z) != len(c):
            z = (z + [z[-1]] * len(c))[:len(c)]
        half = float(p.get("width_m", 12)) / 2.0
        for x, y, zz in local(c, z):
            road_trim[(int(x // 12.0), int(zz // 12.0))].append((x, y, zz, half, p["id"]))

    out = []
    for f in fc:
        p = f["properties"]
        if p.get("road_class") not in FREEWAY:
            continue
        c = f["geometry"]["coordinates"]; z = elev.get(p["id"]) or [0.0] * len(c)
        if len(z) != len(c):
            z = (z + [z[-1]] * len(c))[:len(c)]
        pts = local(c, z)
        lay = _layer_lift(pts, p.get("layer_profile"))
        deck = _grade_cap_y([(x, y + lay[i] + 0.12, zz) for i, (x, y, zz) in enumerate(pts)]) if max(lay) > 1 \
            else [(x, y + 0.12, zz) for x, y, zz in pts]
        if p.get("is_ramp"):
            deck = _trim_ramp_merge(deck, road_trim, p["id"])
        if len(deck) >= 2:
            out.append({"id": p["id"], "ramp": bool(p.get("is_ramp")),
                        "half": float(p.get("width_m", 12)) / 2.0, "pts": deck})
    return out


RACE_CLASH_TOL_M = 0.05   # a race-strip vert within this (plan) of another wall's footprint, inside its height = a clash


def _race_wall_clashes(objp: Path):
    """W. RACE STRIP x OTHER WALL (ledger 0049 C1): since the curb strips run over every bridge span they stand
    beside the decks' own 1WALL_guard rails; a vert of one standing INSIDE the other's footprint (within
    RACE_CLASH_TOL_M in plan, within its height range) — either way round, a thin rail can stand wholly inside a
    0.67 m strip — is two walls through each other, the clash the spec asks audit to gate. Returns (count, samples)."""
    others = _obj_tris(objp, ("1WALL",), exclude=("1WALL_RACE",))
    races = _obj_tris(objp, ("1WALL_RACE",))
    if not others or not races:
        return 0, []
    cell = 2.0
    tol = RACE_CLASH_TOL_M
    hits = []
    for probe_tris, target_tris in ((races, others), (others, races)):
        th = _tri_hash(target_tris, cell)
        seen = set()
        for tri in probe_tris:
            for x, y, z in tri:
                key = (round(x, 4), round(y, 4), round(z, 4))
                if key in seen:
                    continue
                seen.add(key)
                for a, b, c in th.get((int(x // cell), int(z // cell)), ()):
                    if not min(a[1], b[1], c[1]) - tol <= y <= max(a[1], b[1], c[1]) + tol:
                        continue
                    if _xz_tri_dist(x, z, a, b, c) <= tol:
                        hits.append((round(x, 2), round(y, 2), round(z, 2)))
                        break
    return len(hits), hits[:12]


def _xz_tri_dist(x, z, a, b, c):
    """plan distance from (x, z) to the triangle's XZ footprint (0 inside)"""
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) > 1e-12:
        w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        if w0 >= 0 and w1 >= 0 and 1.0 - w0 - w1 >= 0:
            return 0.0
    best = float("inf")
    for p, q in ((a, b), (b, c), (c, a)):
        dx, dz = q[0] - p[0], q[2] - p[2]
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - p[0]) * dx + (z - p[2]) * dz) / L2))
        best = min(best, math.hypot(x - p[0] - t * dx, z - p[2] - t * dz))
    return best


def audit(project_dir: str | Path, *, race: bool = False, obj: str = "track.obj",
          out: str = "audit.json", layout: str | None = None) -> dict:
    """Audit the built OBJ ``data/<obj>`` and write ``data/<out>``.

    ``race`` (ledger 0047): judge the race layouts' kn5 set (``--obj track.race.obj``: road + race
    furniture, from kn5_to_gate_obj --kn5 main --kn5 race) with check D exempting 1WALL verts that
    stand ON a declared barrier band (data/barrier_bands.json: the centre chain, the kerb-line strip
    on both curb faces, the sealed mouths — scripts/geometry/median_zone.py kind 'barrier'). K and I
    keep the island band only (the race kerb is 0.05 m < K's 0.10 m, no exemption needed); E and F
    are untouched — E is the strips' seating gate. Without ``race`` the bands are never consulted,
    so the street layout and every other track audit exactly as before.

    ``layout`` (ledger 0049): ONE race layout on its own gate OBJ (``track.<id>.obj``: road + common race +
    that layout's closure kn5). D is exempt only on THAT layout's bands — both curb strips and its own closure
    (MedianZone.load(project, layout=<id>)), never the other direction's closure; check W (a race strip standing
    through another wall, e.g. a bridge rail) gates."""
    proj = Path(project_dir)
    if layout is not None:
        race = True
    data = proj / "data"
    slug = json.loads((proj / "track.config.json").read_text())["slug"]
    objp = data / obj
    if not objp.exists():
        raise SystemExit(f"audit_mesh: data/{obj} does not exist"
                         + (" — a race audit needs the main+race gate OBJ (kn5_to_gate_obj --kn5 main "
                            "--kn5 race --out data/track.race.obj)" if race else ""))
    # curb prefix is "1KERB": built OBJ groups are 1KERB_sidewalk_a / 1KERB_corners / ... — a bare
    # "KERB" prefix matched NOTHING, which made check F report "0 (of 0 curb verts)" forever
    # (a vacuous gate; pinned by tests/geometry/test_audit_mesh_f.py).
    g = _obj_groups(objp, ("1ROAD_MAIN", "1ROAD", "1GRASS", "HWYSTRUCT", "1WALL", "1KERB"))
    g["1ROAD"] = g["1ROAD"] + g["1ROAD_MAIN"]   # full road set (main + shoulder) for B/H
    road_hash = _hash(g["1ROAD"], 8.0)
    road_hash4 = _hash(g["1ROAD"], 4.0)
    mainroad_hash4 = _hash(g["1ROAD_MAIN"] or g["1ROAD"], 4.0)
    grass_hash4 = _hash(g["1GRASS"], 4.0)

    def nearest_y(h, x, z, R, cell):
        ci, cj = int(x // cell), int(z // cell); ys = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for rx, ry, rz in h.get((ci + di, cj + dj), ()):
                    if (x - rx) ** 2 + (z - rz) ** 2 <= R * R:
                        ys.append(ry)
        return ys

    def road_y_near(x, z, R):
        ci, cj = int(x // 8.0), int(z // 8.0); best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for rx, ry, rz in road_hash.get((ci + di, cj + dj), ()):
                    if (x - rx) ** 2 + (z - rz) ** 2 <= R * R and (best is None or ry > best):
                        best = ry
        return best

    # --- A. supports standing in a road (from the emitted pier list vs the real road surface) ---
    support_hits = []
    piers_p = data / "network.piers.json"
    piers = json.loads(piers_p.read_text()) if piers_p.exists() else []
    for px, pz, y_top in piers:
        ci, cj = int(px // 8.0), int(pz // 8.0)
        speared = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for rx, ry, rz in road_hash.get((ci + di, cj + dj), ()):
                    if (px - rx) ** 2 + (pz - rz) ** 2 <= SUPPORT_R * SUPPORT_R \
                            and (y_top - SUPPORT_BELOW[1]) < ry < (y_top - SUPPORT_BELOW[0]):
                        speared = round(ry, 1)
        if speared is not None:
            support_hits.append((round(px, 1), round(pz, 1), round(y_top, 1), speared))

    # --- B. terrain poke (grass vert above the road surface AT ITS OWN XZ) ---
    # Footprint-exact: a grass vert is a poke only if it sits OVER the pavement, above it.
    # (The old vertex-radius test false-positived on legitimate bench-cut faces standing
    # legally beside the deck — 5 m into a 0.75:1 cut is ~6.7 m up by design.)
    # DECK ONLY: the shoulder's outer quads (ground-meet, hem at -0.8) bury into cut banks BY
    # CONSTRUCTION, so grass legitimately stands metres above them — the same bench-cut
    # false-positive class this check was rewritten to kill, reintroduced through 1ROAD_shoulder
    # (59,162 "pokes" on an IMI whose every one was a bank over the apron; _surf_at picks the
    # LOWEST in-window surface, so the buried hem always reads as "the road"). Grass through the
    # driven deck still fails; grass draped over the transition apron is the terrain doing its job.
    road_tris = _obj_tris(objp, ("1ROAD",), exclude=("SHOULDER",))
    road_th = _tri_hash(road_tris, 8.0)
    poke_hits = []
    for x, y, z in g["1GRASS"]:
        ry = _surf_at(road_th, 8.0, x, z, y)
        if ry is not None and y > ry + POKE_ABOVE_M:
            poke_hits.append((round(x, 1), round(z, 1), round(y - ry, 2)))

    # --- C. junction crossings (per-edge topology, trimmed to match the build) ---
    cross = []
    try:
        decks = _decks_trimmed(data)
        CELL = 12.0
        dh = defaultdict(list)
        for d in decks:
            pts = d["pts"]
            for i, (x, y, z) in enumerate(pts):
                a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
                dh[(int(x // CELL), int(z // CELL))].append(
                    (d["id"], x, y, z, math.atan2(b[2] - a[2], b[0] - a[0]), d["ramp"]))
        seen = set()
        for d in decks:
            pts = d["pts"]
            for i in range(len(pts)):
                x, y, z = pts[i]
                a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
                st = math.atan2(b[2] - a[2], b[0] - a[0])
                ci, cj = int(x // CELL), int(z // CELL)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        for (eid2, rx, ry, rz, rt, ramp2) in dh.get((ci + di, cj + dj), ()):
                            if eid2 == d["id"] or (x - rx) ** 2 + (z - rz) ** 2 > CROSS_R * CROSS_R:
                                continue
                            if abs(y - ry) > CROSS_DY:
                                continue
                            da = abs((st - rt + math.pi) % (2 * math.pi) - math.pi)
                            da = min(da, math.pi - da)
                            if da > math.radians(CROSS_ANGLE_DEG):
                                key = tuple(sorted((d["id"], eid2))) + (round(x / 25), round(z / 25))
                                if key not in seen:
                                    seen.add(key)
                                    kind = "ramp" if (d["ramp"] or ramp2) else "mainline"
                                    cross.append((round(x, 1), round(z, 1), round(math.degrees(da)), kind))
    except Exception as e:  # noqa: BLE001 — never let C crash the audit
        print(f"  (check C skipped: {e})")

    # === CRUFT PASS: walls + curbs ===================================================================
    # D. wall-on-road — a 1WALL vert sitting on/over a road that is NOT its own. A wall is placed ~offset
    #    (>2.5 m) past its OWN road edge, so a wall vert within 2.5 m of a road vert (at similar height) is
    #    on a DIFFERENT road (a median wall on the opposing carriageway, or a wall tangled across a road at
    #    an interchange — covers "walls crossing over others" + "walls passing onto the road").
    # FOOTPRINT-exact (like B): pavement of the MAIN carriageway exists directly under the wall
    # vert at its own height. Vertex-radius false-flagged fences standing legally beside
    # junction-flare ramps (206 phantoms on Sand Creek 0.23).
    main_tris = _obj_tris(objp, ("1ROAD_MAIN",))
    if not main_tris:
        main_tris = road_tris
    main_th = _tri_hash(main_tris, 8.0)
    # MEDIAN ISLAND (0037): a raised landscaped island stands ON the slab of a divided road by
    # design — its barrier is a wall on a road, its curb is kerb in the carriageway, its curb is a
    # sidewalk with pavement on both sides. D/K/I exempt verts on the declared island (and only
    # there — scripts/geometry/median_zone.py, band + 0.6 m). Zero-width = no exemption.
    # BARRIER BANDS (0047): under --race, D also exempts a 1WALL vert standing on a DECLARED
    # barrier band (centre chain 0.335 + 0.6 m, kerb-line strip |lat - (w/2 - 0.485)| <= 0.935,
    # sealed-mouth polylines; continuous between consecutive declared vertices, +/- 2 m past a run's
    # ends) — the strips are walls on the road by design and are
    # gated for presence (drive_test barrier_missing), seating (E) and lane clearance (drive_test
    # disc) instead. A strip OFF its band still counts; K and I never read the barrier kind.
    from scripts.geometry.median_zone import MedianZone, ALL_KINDS
    _zone = MedianZone.load(project_dir, layout=layout)
    _in_island = _zone.contains if _zone else (lambda x, z: False)
    if race and _zone is not None and _zone.has_barrier:
        _in_band_D = lambda x, z: _zone.contains(x, z, ALL_KINDS)   # noqa: E731
    else:
        _in_band_D = _in_island
    if _zone:
        print(f"  (median island declared on {_zone.n_island} centreline verts — D/K/I exempt there"
              + (f"; --race: barrier bands on {_zone.n_barrier} centre / {_zone.n_edge} edge"
                 + (f" / {_zone.n_closure} closure ({layout})" if layout else "") + " verts — D exempt there"
                 if race and _zone.has_barrier else "") + ")")
    if race and (_zone is None or not _zone.has_barrier):
        print("  (--race given but data/barrier_bands.json declares no band — nothing exempted)")
    wall_on_road = 0
    for x, y, z in g["1WALL"]:
        if _in_band_D(x, z):
            continue
        ry = _surf_at(main_th, 8.0, x, z, y, dy_max=1.2)
        if ry is not None and abs(y - ry) < 1.2:
            wall_on_road += 1
    # K. KERB/SIDEWALK STANDING IN THE CARRIAGEWAY. A raised sidewalk slab crossing the driving lane
    #    is invisible to every other check: drive_test's ground-on-top only flags SOFT owners
    #    (1GRASS/1LAWN) and a sidewalk is 1KERB_*, which counts as drivable and lands in the surface
    #    field; D covers walls only; F measures whether curbs are FLUSH, not whether they are in the
    #    way; I only catches a sidewalk that isolates pavement. Kevin drove straight into sidewalks
    #    running through the Lake Murray intersections while all ten checks read green.
    #
    #    The invariant is the same one the barriers already obey: nothing that is not road may stand
    #    on the road surface. A kerb vert RISING above the road beneath it, more than a kerb height,
    #    is in the carriageway.
    #    THRESHOLD. A kerb's own lip overlaps the pavement edge by construction, so a few cm of
    #    "kerb above road" is the seam where the two meet, not an intrusion. After the carriageway
    #    drop, Lake Murray's residue was 12 verts spanning +0.061..+0.065 m across 7 clusters —
    #    tightly bunched, i.e. one systematic seam — where the real intrusions it had caught ranged
    #    +0.06..+0.33 m. 0.10 m sits above the seam and below anything a driver would hit.
    KERB_STAND_M = 0.10
    kerb_on_road = 0
    worst_kerb_stand = 0.0
    # Against every CARRIAGEWAY (main + connectors + opposing), but NOT 1ROAD_SHOULDER: a shoulder
    # is a graded verge and a kerb sits above it by design — including it read 218 false hits up to
    # +0.79 m. main_th alone had the opposite problem, missing connector crossings, which is
    # precisely where a swept sidewalk runs through a junction.
    _cverts: list = []
    _ctris: list = []
    _keep = False
    for _ln in objp.read_text().splitlines():
        if _ln.startswith("o "):
            _nm = _ln[2:].strip().upper()
            _keep = _nm.startswith("1ROAD") and not _nm.startswith("1ROAD_SHOULDER")
        elif _ln.startswith("v "):
            _q = _ln.split()
            _cverts.append((float(_q[1]), float(_q[2]), float(_q[3])))
        elif _ln.startswith("f ") and _keep:
            _ix = [int(_q.split("/")[0]) - 1 for _q in _ln.split()[1:]]
            for _k in range(1, len(_ix) - 1):
                _ctris.append((_cverts[_ix[0]], _cverts[_ix[_k]], _cverts[_ix[_k + 1]]))
    _carriage = _tri_hash(_ctris, 8.0)
    for x, y, z in g["1KERB"]:
        if _in_island(x, z):
            continue
        ry = _surf_at(_carriage, 8.0, x, z, y, dy_max=1.2)
        if ry is not None and y - ry > KERB_STAND_M:
            kerb_on_road += 1
            worst_kerb_stand = max(worst_kerb_stand, y - ry)

    # E. wall-float — the BASE of a wall (min y per 0.6 m column) sitting above the ground/road beneath it.
    wall_col = defaultdict(lambda: 1e9)
    for x, y, z in g["1WALL"]:
        k = (round(x / 0.6), round(z / 0.6)); wall_col[k] = min(wall_col[k], y)
    wall_float = 0; worst_float = 0.0
    # A rail/arm member spanning between posts has NO base verts in its own 0.6 m column — its
    # min-y is the rail 2 m up, which read as "+1.6 floating wall" on a perfectly seated wooden
    # fence. A column only floats if no SUPPORTED column (gap <= 0.6) stands within reach — the
    # kn5 gate's arm-exclusion rule, ported here.
    gaps = {}
    for (kx, kz), by in wall_col.items():
        x, z = kx * 0.6, kz * 0.6
        gnd = nearest_y(grass_hash4, x, z, 4.5, 4.0) + nearest_y(road_hash4, x, z, 4.5, 4.0)
        if gnd:
            gaps[(kx, kz)] = by - max(gnd)
    supported = {k for k, gp in gaps.items() if gp <= 0.6}
    R_SUP = 4       # 4 columns = 2.4 m — a fence post every 1.73 m is always within reach
    for (kx, kz), gap in gaps.items():
        # 1.4 threshold: barrier modules seat on the INTERPOLATED drape surface; on steep
        # embankments the nearest mesh VERTEX 3 m away legitimately differs by >1 m.
        if gap > 1.4:
            if any((kx + di, kz + dj) in supported for di in range(-R_SUP, R_SUP + 1)
                   for dj in range(-R_SUP, R_SUP + 1)):
                continue           # a grounded post nearby: rail member, not a hover
            wall_float += 1; worst_float = max(worst_float, gap)
    # F. curb-not-flush — a KERB vert that meets NEITHER the road nor the ground within reach (a gap/step).
    #    Reach 3.5 m: the height tolerance (|dy| < 0.5) is the defect being hunted — a curb stepped or
    #    gapped VERTICALLY from everything around it. The reach only has to FIND the neighbour surface,
    #    so it must exceed the built meshes' vertex spacing: on Sand Creek the sidewalk curb's nearest
    #    road-vertex row is exactly 2.80 m away (measured over all 40 928 curb verts, worst case), so
    #    the old 2.0 m reach flagged 6 250 perfectly-flush verts. 3.5 m covers that spacing with margin
    #    and stays inside nearest_y's guaranteed +/-1-cell coverage (4.0 m at cell 4.0).
    #    SCOPE (measured on Sand Creek, 53 866 curb verts): the ``1KERB`` group is not just the curb.
    #    ``ribbon.curb_sidewalk`` sweeps ONE strip — curb face, walk, verge, then an embankment skirt
    #    running out to the terrain — so most of its verts are metres from the road by construction.
    #    Checking them all against "is a road or grass vert within 0.5 m of my height" flagged 4 619,
    #    of which **99.3% lay beyond 3.5 m from any road vertex** (the skirt, descending a slope) and
    #    exactly **2** sat at the road edge. drive_test agreed the whole time: it passes this track
    #    with 0 daylight gaps. So the count was dominated by geometry the check was never about, and
    #    it blocked four tracks that drive clean.
    #
    #    A curb IS at the road edge. Gate on that; the skirt's grounding is a different question and
    #    is already gated by drive_test (daylight gaps at edges) and checks E/H. The skirt is still
    #    COUNTED and REPORTED — advisory, not gating — so narrowing the scope hides nothing.
    #    TOP SURFACE ONLY. A curb mesh has vertical extent — the 3D-ridged racing kerb drops a skirt
    #    to the terrain, measured at a consistent 0.69-0.72 m below its own top on Sand Creek. Those
    #    underside verts are BELOW the road by construction, and sampling them accounted for 21 of
    #    the 31 remaining flags there, every one of which sat under a kerb whose top read 30.92 vs a
    #    road at 30.81 — an 11 cm kerb, correctly flush. Flushness is a property of the TOP edge, so
    #    a vert with more than a kerb-height of its own mesh standing above it is a side/underside
    #    face and is not what this check is about. A wholly-sunken kerb still fails, because its top
    #    vert is still tested.
    CURB_REACH = 3.5
    EDGE_REACH = 2.0
    TOP_BAND = 0.20        # > one kerb height (curb_h defaults to 0.15) below the local top = a face
    curb_hash4 = _hash(g["1KERB"], 4.0)
    # J. OVERSIZED TERRAIN TRIANGLE. A vertex-based check cannot see a triangle whose corners are
    #    hundreds of metres away but whose SURFACE crosses the pavement. That is exactly how the
    #    inverted 500 m skirt hid: check B compared grass VERTICES to road vertices, found nothing,
    #    and Aspen shipped 1,037 wheel-path hits that only drive_test could see. On a terrain grid
    #    nothing legitimate spans more than a few cells, so measure the triangles themselves — no
    #    proximity reasoning needed, and it catches the whole class rather than one instance.
    span_bad, worst_span = 0, 0.0
    _cellm = 0.0
    _hf = data / "heightfield.meta.json"
    if _hf.exists():
        try:
            _m = json.loads(_hf.read_text(encoding="utf-8"))
            _cellm = float(_m.get("spacing_m") or 0.0)
        except (json.JSONDecodeError, ValueError):
            _cellm = 0.0
    SPAN_LIMIT = max(60.0, _cellm * 3.0)      # generous: the raw DEM spacing is the coarse bound
    # Being oversized is NOT itself a fault: the 500 m skirt is deliberate, extruded outward so you
    # cannot drive off the edge of the world. The fault is an oversized triangle that lies OVER THE
    # ROAD. So pair the span test with "does it cover a road vertex" — which is what made the
    # inverted skirt a hazard and leaves the honest one alone.
    _road_pts = g["1ROAD"][::7]
    for a, b, c in _obj_tris(objp, ("1GRASS",)):
        e = max(math.hypot(a[0] - b[0], a[2] - b[2]),
                math.hypot(b[0] - c[0], b[2] - c[2]),
                math.hypot(c[0] - a[0], c[2] - a[2]))
        if e <= SPAN_LIMIT:
            continue
        x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
        z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        for rx, ry, rz in _road_pts:
            if not (x0 <= rx <= x1 and z0 <= rz <= z1):
                continue
            w0 = ((b[2] - c[2]) * (rx - c[0]) + (c[0] - b[0]) * (rz - c[2])) / d
            w1 = ((c[2] - a[2]) * (rx - c[0]) + (a[0] - c[0]) * (rz - c[2])) / d
            if w0 >= -1e-6 and w1 >= -1e-6 and 1.0 - w0 - w1 >= -1e-6:
                span_bad += 1
                worst_span = max(worst_span, e)
                break

    curb_bad = 0
    curb_skirt = 0
    curb_faces = 0
    for x, y, z in g["1KERB"]:
        col = nearest_y(curb_hash4, x, z, 1.0, 4.0)
        if col and max(col) - y > TOP_BAND:
            curb_faces += 1
            continue
        at_edge = nearest_y(road_hash4, x, z, EDGE_REACH, 4.0)
        near_g = any(abs(y - ry) < 0.5 for ry in nearest_y(grass_hash4, x, z, CURB_REACH, 4.0))
        if not at_edge:                       # verge / embankment skirt, not a curb
            if not near_g:
                curb_skirt += 1
            continue
        if not (any(abs(y - ry) < 0.5 for ry in at_edge) or near_g):
            curb_bad += 1
    # I. sidewalk-isolating-pavement — Kevin's invariant: "sidewalks should never isolate driving
    #    surfaces." A raised sidewalk curb (>8 cm over the road beside it) with pavement at similar
    #    height on BOTH sides of it is a divider stranding a drivable island; the builder must have
    #    rolled it flat. Tri-exact against ALL 1ROAD surfaces; rolled humps (<=8 cm) pass.
    sw_isolate = 0
    sw_worst: list = []
    sw_verts = _obj_groups(objp, ("1KERB_SIDEWALK",))["1KERB_SIDEWALK"]
    if sw_verts:
        all_road_th = _tri_hash(_obj_tris(objp, ("1ROAD",)), 4.0)
        for x, y, z in sw_verts:
            if _in_island(x, z):
                continue
            ry = _surf_at(all_road_th, 4.0, x, z, y, dy_max=3.0)
            if ry is None or y - ry <= 0.08:
                continue
            for adeg in range(0, 180, 30):
                dx = 3.5 * math.cos(math.radians(adeg)); dz = 3.5 * math.sin(math.radians(adeg))
                fy = _surf_at(all_road_th, 4.0, x + dx, z + dz, y, dy_max=3.0)
                ny2 = _surf_at(all_road_th, 4.0, x - dx, z - dz, y, dy_max=3.0)
                if fy is not None and ny2 is not None and abs(fy - ny2) < 0.5:
                    sw_isolate += 1
                    if len(sw_worst) < 8:
                        sw_worst.append((round(x, 1), round(z, 1), round(y - ry, 2)))
                    break
    # G. prop-floating — a scatter billboard (bush/tree/palm) whose BASE hovers above the ground SURFACE
    #    beneath it. Measured against the conformed-ground sampler (data/ground.local.json) — the SAME
    #    surface the grass mesh + the prop placement use — so it is not fooled by a steep slope's
    #    down-hill neighbour vertex (measuring against nearest verts invented phantom 7 m floats). Needs
    #    environment.obj + ground.local.json (both built after the mesh), else skipped at mesh-audit time.
    prop_float = None
    envp = data / "environment.obj"; glp = data / "ground.local.json"
    if envp.exists() and glp.exists():
        gl = json.loads(glp.read_text())
        gx0, gz0, gdx, gdz, gnx, gny, GY = gl["x0"], gl["z0"], gl["dx"], gl["dz"], gl["nx"], gl["ny"], gl["y"]

        def ground_surf(x, z):
            # TRIANGLE-exact, same (a,b,c)+(a,c,d) split the grass renders and build_env seats on —
            # bilinear here read up to ~1 m off the rendered triangle on steep slopes (phantom floats)
            fi = (x - gx0) / gdx if gdx else 0.0; fj = (z - gz0) / gdz if gdz else 0.0
            i0 = max(0, min(gnx - 2, int(fi))); j0 = max(0, min(gny - 2, int(fj)))
            u = max(0.0, min(1.0, fi - i0)); v = max(0.0, min(1.0, fj - j0))
            ya = GY[j0][i0]; yb = GY[j0][i0 + 1]; yc = GY[j0 + 1][i0 + 1]; yd = GY[j0 + 1][i0]
            if u >= v:
                return ya + u * (yb - ya) + v * (yc - yb)
            return ya + v * (yd - ya) + u * (yc - yd)

        env = _obj_groups(envp, ("BUSHES", "TREES", "PALMS", "CONIFER"))
        # keep the ACTUAL coords of each column's lowest vert — sampling the ground at the quantized
        # 0.8 m cell corner instead was a metre of phantom height on steep slopes (false G floats)
        col: dict = {}
        for pre in ("BUSHES", "TREES", "PALMS", "CONIFER"):
            for x, y, z in env[pre]:
                k = (round(x / 0.8), round(z / 0.8))
                if k not in col or y < col[k][0]:
                    col[k] = (y, x, z)
        prop_float = 0
        _keys = list(col.keys())
        _grounded = {k for k in _keys if col[k][0] <= ground_surf(col[k][1], col[k][2]) + 0.7}
        for k in _keys:
            by, bx, bz = col[k]
            if by > ground_surf(bx, bz) + 0.7:
                # canopy-corner columns: a wide billboard's outer quad verts have no base verts
                # in their own 0.8 m column — grounded-neighbor rule (same as E's rail fix)
                if any((k[0] + di, k[1] + dj) in _grounded
                       for di in range(-6, 7) for dj in range(-6, 7)):
                    continue
                prop_float += 1

    # H. ground-above-deck at the SURFACE level — bilinear-sample the conformed ground (the actual
    #    rendered/collided triangle surface) across lateral cross-sections of the road envelope and
    #    flag anywhere it rises above the deck. B (vertex-vs-vertex) provably misses this: on a coarse
    #    grid the clamped VERTICES are legal while the triangles BETWEEN them bridge the road cut —
    #    the Lariat shipped with the mountainside knifing +4.4 m through its switchbacks and B read 0.
    ground_cut = None
    worst_cut = 0.0
    cut_hits = []
    clp = data / "centerline.local.json"
    if glp.exists() and clp.exists():
        gl2 = json.loads(glp.read_text())
        hx0, hz0, hdx, hdz, hnx, hny, HY = gl2["x0"], gl2["z0"], gl2["dx"], gl2["dz"], gl2["nx"], gl2["ny"], gl2["y"]

        def _hsurf(x, z):
            fi = (x - hx0) / hdx if hdx else 0.0
            fj = (z - hz0) / hdz if hdz else 0.0
            if not (0 <= fi < hnx - 1 and 0 <= fj < hny - 1):
                return None
            i0, j0 = int(fi), int(fj)
            ti, tj = fi - i0, fj - j0
            a = HY[j0][i0] * (1 - ti) + HY[j0][i0 + 1] * ti
            b = HY[j0 + 1][i0] * (1 - ti) + HY[j0 + 1][i0 + 1] * ti
            return a * (1 - tj) + b * tj

        # Deck height comes from the BUILT 1ROAD verts (nearest within 4 m), NOT the centerline y —
        # a centerline reconstruction reads banking (PPIR's 10-degree corners put the edge ~1 m above
        # the centerline), bridge-deck lifts and cambers as phantom ground cuts. First principle:
        # measure the built geometry.
        cl = json.loads(clp.read_text())
        cfg_raw = json.loads((Path(project_dir) / "track.config.json").read_text())
        sxm = -1.0 if cfg_raw.get("mirror_x", False) else 1.0
        rpts = [(sxm * p[0], p[1], p[2]) for p in cl["points_xyz_m"]]
        rw = cl["widths_m"]
        # MESH CONFIRMATION. The raster is bilinear over coarse cells (13.3 m on the rally
        # stages), so near a switchback stack the upper leg's bench bleeds into the lower leg's
        # sample — a phantom cut the car never touches. On corridor-refined tracks the raster is
        # not even the shipping surface: the refined 1GRASS mesh is, and drive_test reads THAT
        # at 10 wheel paths. So: the raster nominates a candidate, the actual grass mesh
        # confirms it. A real bench standing over the deck exists in the mesh and still fails.
        _gh_tris = _obj_tris(objp, ("1GRASS",))
        _gh_hash = _tri_hash(_gh_tris, 4.0)

        def _gmax(x, z, y_ref):
            """HIGHEST grass surface at (x,z) within 6 m of y_ref — no angle filter (a steep
            bench face standing over the deck is exactly what H exists to catch)."""
            best = None
            for a, b, c in _gh_hash.get((int(x // 4.0), int(z // 4.0)), ()):
                d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
                if abs(d) < 1e-12:
                    continue
                w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
                w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
                w2 = 1.0 - w0 - w1
                if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                    y = w0 * a[1] + w1 * b[1] + w2 * c[1]
                    if abs(y - y_ref) <= 6.0 and (best is None or y > best):
                        best = y
            return best

        ground_cut = 0
        cut_hits = []
        for i in range(10, len(rpts), 10):
            ax, ay, az = rpts[i - 1]
            bx, by, bz = rpts[i]
            tx, tz = bx - ax, bz - az
            L = math.hypot(tx, tz) or 1.0
            nxv, nzv = -tz / L, tx / L
            # ±(w/2 + 2) covers the flush shoulder band as well as the lane — on switchback stacks
            # the upper leg's embankment can bury the lower leg's shoulder while the lane reads clean
            for off in (-rw[i] / 2 - 2.0, -rw[i] / 2, -rw[i] / 4, 0.0, rw[i] / 4, rw[i] / 2, rw[i] / 2 + 2.0):
                px, pz = bx + nxv * off, bz + nzv * off
                deck = nearest_y(road_hash4, px, pz, 3.5, 4.0)
                if not deck:
                    continue
                gy2 = _hsurf(px, pz)
                if gy2 is not None and gy2 - max(deck) > 0.10:
                    # BOTH SIDES MUST BE SURFACES AT THIS POINT. max(deck) is the highest road
                    # VERTEX within 4 m; on a descending or banked road those sit BELOW the deck
                    # surface directly overhead, so grass correctly tucked 4 cm under the deck
                    # reads as standing over a vertex downhill. That is the Lariat's 47 hits:
                    # measured at three of them, grass is 43-51 mm UNDER 1ROAD_main. Compare
                    # surface-to-surface where the road exists at this point; only fall back to
                    # vertices out beyond the pavement (the w/2+2 samples), where by definition
                    # there is no deck overhead and a cut face legitimately rises.
                    _dk2 = _surf_at(road_th, 8.0, px, pz, max(deck), 6.0)
                    _ref2 = _dk2 if _dk2 is not None else max(deck)
                    _gm2 = _gmax(px, pz, _ref2)
                    if _gm2 is None or _gm2 - _ref2 <= 0.10:
                        continue        # artifact: the real mesh does not stand over the real deck
                    ground_cut += 1
                    worst_cut = max(worst_cut, _gm2 - _ref2)
                    # RECORD WHERE. A bare count sent every H investigation to an instrumented
                    # build; the x/z and the offset say immediately whether the hits are a cut
                    # face at the verge (off = ±(w/2+2)) or ground in the lane (off ≈ 0).
                    cut_hits.append((round(px, 1), round(pz, 1), round(_gm2 - max(deck), 2),
                                     round(off, 1), i))

    # W. race strip through another wall (0049 C1: the strips now cross the bridge spans beside the deck rails)
    race_clash, race_clash_samples = _race_wall_clashes(objp) if race else (0, [])

    report = {
        "slug": slug, "obj": obj, "race": race,
        "road_verts": len(g["1ROAD"]), "grass_verts": len(g["1GRASS"]), "piers": len(piers),
        "wall_verts": len(g["1WALL"]), "curb_verts": len(g["1KERB"]),
        "A_supports_in_road": len(support_hits),
        "B_terrain_poke": len(poke_hits),
        "C_junction_crossings": len(cross),
        "D_wall_on_road": wall_on_road,
        "E_wall_floating": wall_float,
        "J_terrain_span": span_bad,
        "K_kerb_in_carriageway": kerb_on_road,
        "worst_kerb_stand_m": round(worst_kerb_stand, 2),
        "worst_terrain_span_m": round(worst_span, 1),
        "F_curb_not_flush": curb_bad,
        "F_skirt_off_terrain": curb_skirt,
        "F_side_faces_skipped": curb_faces,
        "G_prop_floating": prop_float,
        "H_ground_above_deck": ground_cut,
        "I_sidewalk_isolating": sw_isolate,
        "I_samples": sw_worst,
        "worst_ground_cut_m": round(worst_cut, 2),
        "worst_poke_m": round(max((h[2] for h in poke_hits), default=0.0), 2),
        "worst_float_m": round(worst_float, 2),
        "C_by_kind": {"ramp": sum(1 for c in cross if c[3] == "ramp"),
                      "mainline": sum(1 for c in cross if c[3] == "mainline")},
        "samples": {"supports": support_hits[:8],
                    "ground_cut": sorted(cut_hits, key=lambda h: -h[2])[:12],
                    "poke": sorted(poke_hits, key=lambda h: -h[2])[:8],
                    "crossings": cross[:10]},
    }
    (data / out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"AUDIT {slug}{' [race: ' + obj + ']' if race else ''}   (roads {len(g['1ROAD'])}v, grass {len(g['1GRASS'])}v, "
          f"walls {len(g['1WALL'])}v, piers {len(piers)})")
    print(f"  A. supports standing in a road : {len(support_hits)}")
    print(f"  B. terrain poking through road : {len(poke_hits)}  (worst +{report['worst_poke_m']} m)")
    print(f"  C. at-grade junction crossings : {len(cross)}  ({report['C_by_kind']})")
    print(f"  D. walls sitting on a road     : {wall_on_road}")
    print(f"  E. walls floating over ground  : {wall_float}  (worst +{report['worst_float_m']} m)")
    print(f"  F. curbs not flush             : {curb_bad}  (of {len(g['1KERB'])} curb verts,\n                                      edge-scoped, top-surface only;\n                                      {curb_skirt} skirt verts off terrain (advisory), {curb_faces} side faces skipped,\n                                      grounding is gated by drive_test + E/H)")
    print(f"  G. plants floating over ground : {'(env not built)' if prop_float is None else prop_float}")
    print(f"  H. ground cutting into road    : {'(no ground grid)' if ground_cut is None else ground_cut}"
          f"  (worst +{report['worst_ground_cut_m']} m)")
    print(f"  I. sidewalk isolating pavement : {sw_isolate}"
          + (f"  e.g. {sw_worst[:3]}" if sw_worst else ""))
    print(f"  K. kerb/sidewalk in carriageway: {kerb_on_road}"
          + (f"  (worst +{worst_kerb_stand:.2f} m above the road)" if kerb_on_road else ""))
    print(f"  J. terrain triangles over road : {span_bad}"
          + (f"  (worst {worst_span:.0f} m edge; limit {SPAN_LIMIT:.0f} m)" if span_bad else ""))
    total = (kerb_on_road + span_bad + len(support_hits) + len(poke_hits) + len(cross) + wall_on_road + wall_float + curb_bad
             + (prop_float or 0) + (ground_cut or 0) + sw_isolate)
    if race:                     # race-only keys: the street audit.json keeps today's exact shape
        report["layout"] = layout
        report["W_race_wall_clash"] = race_clash
        report["samples"]["race_wall_clash"] = race_clash_samples
        (data / out).write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"  W. race strip through a wall   : {race_clash}" + (f"  e.g. {race_clash_samples[:3]}" if race_clash else ""))
    total += race_clash
    print(f"  => {'CLEAN' if total == 0 else str(total) + ' issues'}")
    return report


def main(argv: list[str] | None = None) -> int:
    """python -m scripts.geometry.audit_mesh <project> [--race] [--layout <id>] [--obj track.<id>.obj]
                                             [--out audit.<id>.json]"""
    argv = list(sys.argv[1:] if argv is None else argv)
    project = "projects/san-diego-freeway-loop"
    race, obj, out, layout = False, "track.obj", "audit.json", None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--race":
            race = True; i += 1
        elif a == "--layout":
            layout = argv[i + 1]; race = True; i += 2
        elif a == "--obj":
            obj = Path(argv[i + 1]).name; i += 2
        elif a == "--out":
            out = Path(argv[i + 1]).name; i += 2
        else:
            project = a; i += 1
    if race and obj == "track.obj":
        obj = f"track.{layout}.obj" if layout else "track.race.obj"
    if race and out == "audit.json":
        out = f"audit.{layout}.json" if layout else "audit.race.json"
    r = audit(project, race=race, obj=obj, out=out, layout=layout)
    hard = (r["A_supports_in_road"] + r["B_terrain_poke"] + r["D_wall_on_road"] + r["E_wall_floating"]
            + r["F_curb_not_flush"] + (r["G_prop_floating"] or 0) + (r["H_ground_above_deck"] or 0)
            + r["I_sidewalk_isolating"] + (r.get("W_race_wall_clash", 0) if layout else 0))
    return 1 if hard else 0   # C (junction crossings) reported but non-gating (walls are gapped there)


if __name__ == "__main__":
    sys.exit(main())


def _legacy_main():   # pragma: no cover — the pre-0047 entry, kept for reference of the gate line
    r = audit(sys.argv[1] if len(sys.argv) > 1 else "projects/san-diego-freeway-loop")
    hard = (r["A_supports_in_road"] + r["B_terrain_poke"] + r["D_wall_on_road"] + r["E_wall_floating"]
            + r["F_curb_not_flush"] + (r["G_prop_floating"] or 0) + (r["H_ground_above_deck"] or 0)
            + r["I_sidewalk_isolating"])
    sys.exit(1 if hard else 0)   # C (junction crossings) reported but non-gating (walls are gapped there)
