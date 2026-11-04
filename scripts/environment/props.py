"""Instance real 3D prop modules (Kevin's model pack) along the track — starting with the 4 m
concrete barrier replacing the procedural swept jersey at warning-barrier runs.

The module OBJ is loaded once (pure stdlib) and stamped along each run: position at the verge
offset, yawed to the local tangent, base seated just under the deck edge. Output is a normal
mesh dict (verts/uvs/tris) that build_mesh ships as physical ``1WALL_*`` (collidable — AC treats
1-prefixed meshes as physics surfaces/walls) and splits under the kn5 vertex cap like everything
else. The module's mesh ships in the kn5 as GEOMETRY we instanced ourselves (renders baked from
licensed models are imagery; these OBJs are Kevin-provided assets for his own track).
"""

from __future__ import annotations

import math
from pathlib import Path

Vertex = tuple[float, float, float]


def triangulate(pts: list[Vertex]) -> list[tuple[int, int, int]]:
    """Triangles (indices into ``pts``) for one planar polygon, wound like the polygon.

    A fan from the first vertex when that is valid (every fan triangle faces the polygon's own
    Newell normal), so convex faces load exactly as they always have. Otherwise ear clipping: a fan
    over a CONCAVE polygon folds triangles back over it, reversed and outside the outline. The 4 m
    barrier's end faces are concave 8- to 16-gons (the jersey profile); fanned, 41 of its 493
    triangles faced into the module (ledger 0071)."""
    n = len(pts)
    if n < 3:
        return []
    nx = ny = nz = 0.0                                   # Newell normal
    for i in range(n):
        (x0, y0, z0), (x1, y1, z1) = pts[i], pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    fan = [(0, k, k + 1) for k in range(1, n - 1)]
    if n == 3:
        return fan
    eps = 1e-12 * (nx * nx + ny * ny + nz * nz) ** 0.5

    def facing(a, b, c):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts[a], pts[b], pts[c]
        ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
        return (uy * vz - uz * vy) * nx + (uz * vx - ux * vz) * ny + (ux * vy - uy * vx) * nz

    if all(facing(*t) >= -eps for t in fan):
        return fan
    # ear clipping in the polygon's plane: drop the normal's largest axis, keep the winding CCW
    ax_ = max(range(3), key=lambda k: abs((nx, ny, nz)[k]))
    keep = [(1, 2), (2, 0), (0, 1)][ax_]
    sgn = 1.0 if (nx, ny, nz)[ax_] > 0 else -1.0
    p2 = [(p[keep[0]], p[keep[1]] * sgn) for p in pts]

    def cross(o, a, b):
        return (p2[a][0] - p2[o][0]) * (p2[b][1] - p2[o][1]) - (p2[a][1] - p2[o][1]) * (p2[b][0] - p2[o][0])

    rest = list(range(n))
    out: list[tuple[int, int, int]] = []
    while len(rest) > 3:
        m = len(rest)
        for k in range(m):
            a, b, c = rest[k - 1], rest[k], rest[(k + 1) % m]
            if cross(a, b, c) <= 0.0:
                continue                                  # reflex (or flat): not an ear
            if any(cross(a, b, q) >= 0.0 and cross(b, c, q) >= 0.0 and cross(c, a, q) >= 0.0
                   for q in rest if q not in (a, b, c) and p2[q] not in (p2[a], p2[b], p2[c])):
                continue                                  # another vertex inside: not an ear
            out.append((a, b, c))
            rest.pop(k)
            break
        else:                                             # numerically stuck: clip the most convex corner
            k = max(range(m), key=lambda j: cross(rest[j - 1], rest[j], rest[(j + 1) % m]))
            out.append((rest[k - 1], rest[k], rest[(k + 1) % m]))
            rest.pop(k)
    out.append(tuple(rest))
    return out


def load_module(path: str | Path, *, keep_seams: bool = False) -> dict:
    """Minimal OBJ loader: v/vt/f, polygons triangulated by ``triangulate``. Returns {vertices,
    uvs, tris} with uvs parallel to vertices.

    keep_seams=False: one vertex per OBJ ``v``, carrying the LAST ``vt`` any face gave it, so every
    UV seam collapses (the trees, lamps and fence panels build_env stamps still load this way).
    keep_seams=True: one vertex per distinct (v, vt) pair, which is how Blender and the kn5 store a
    mesh, so the module's own unwrap survives. Kevin's 4 m concrete barrier has 439 UVs on 249
    positions: 159 positions carry more than one, and 141 of its 183 faces touch a seam (ledgers 0070
    C3, 0071)."""
    vs: list[Vertex] = []
    vts: list[tuple[float, float]] = []
    uvs_per_v: dict[int, tuple[float, float]] = {}
    split: dict[tuple[int, int | None], int] = {}     # keep_seams: (v, vt) -> output vertex
    out_v: list[Vertex] = []
    out_uv: list[tuple[float, float]] = []
    tris: list[tuple[int, int, int]] = []
    for ln in open(path, errors="replace"):
        if ln.startswith("v "):
            p = ln.split()
            vs.append((float(p[1]), float(p[2]), float(p[3])))
        elif ln.startswith("vt "):
            p = ln.split()
            vts.append((float(p[1]), float(p[2])))
        elif ln.startswith("f "):
            idx = []
            for tok in ln.split()[1:]:
                parts = tok.split("/")
                vi = int(parts[0]) - 1
                ti = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else None
                if keep_seams:
                    key = (vi, ti)
                    if key not in split:
                        split[key] = len(out_v)
                        out_v.append(vs[vi])
                        out_uv.append(vts[ti] if ti is not None else (0.0, 0.0))
                    idx.append(split[key])
                    continue
                if ti is not None:
                    uvs_per_v[vi] = vts[ti]
                idx.append(vi)
            pos = out_v if keep_seams else vs
            tris.extend((idx[a], idx[b], idx[c]) for a, b, c in triangulate([pos[i] for i in idx]))
    if keep_seams:
        return {"vertices": out_v, "uvs": out_uv, "tris": tris}
    uvs = [uvs_per_v.get(i, (0.0, 0.0)) for i in range(len(vs))]
    return {"vertices": vs, "uvs": uvs, "tris": tris}


def module_tris(module: dict, base: int, x_axis: tuple[float, float],
                z_axis: tuple[float, float]) -> list[tuple[int, int, int]]:
    """The module's faces for ONE placement, re-indexed from ``base``, each written ONCE.

    The placement maps module +X to the horizontal unit vector ``x_axis`` = (x, z), module +Y to up
    and module +Z to ``z_axis``. When that basis is a reflection (det < 0: the outward side vector
    of a run on the +1 side, ``(-tz, tx)``, with the tangent as +Z), the image of every face turns
    inside out, so its winding is reversed here and the stamped normals stay the rigid image of the
    module's authored ones (all 183 of the barrier's agree with its winding, and its signed volume
    is positive, so authored = outward).

    This replaced writing every face twice, once per winding, on the SAME vertices (ledger 0071).
    A face and its reverse share a vertex set, Blender's Mesh.validate() in the underlay deletes one
    of each such pair, and which one survives is arbitrary: about half of every module came out
    inside out (639 and 837 of 1,479 faces on a 3-module run per side, ledger 0070 C1)."""
    ax, az = x_axis
    bx, bz = z_axis
    if ax * bz - az * bx >= 0.0:            # det[x_axis, up, z_axis]: +1 rotation, -1 reflection
        return [(a + base, b + base, c + base) for a, b, c in module["tris"]]
    return [(a + base, c + base, b + base) for a, b, c in module["tris"]]


def place_module(out: dict, module: dict, origin: Vertex, x_axis: tuple[float, float],
                 z_axis: tuple[float, float]) -> int:
    """Append one copy of ``module`` to the mesh dict ``out``: module (mx, my, mz) lands at
    origin + z_axis*mz + x_axis*mx (horizontal) and origin.y + my, wound by ``module_tris``.
    Returns the copy's first vertex index (the copy is one contiguous block, len(module verts))."""
    ox, oy, oz = origin
    ax, az = x_axis
    bx, bz = z_axis
    base = len(out["vertices"])
    for mx, my, mz in module["vertices"]:
        out["vertices"].append((ox + bx * mz + ax * mx, oy + my, oz + bz * mz + az * mx))
    out["uvs"].extend(module["uvs"])
    out["tris"].extend(module_tris(module, base, x_axis, z_axis))
    return base


def append_sheet(out: dict, verts: list[Vertex], uvs: list[tuple[float, float]],
                 tris: list[tuple[int, int, int]]) -> None:
    """A thin sheet seen from both sides (a chain-link fence panel): the front faces on ``verts``,
    the back faces, reversed, on a SECOND copy of them. Sharing one set of vertices made every back
    face a duplicate of its front (same vertex set), and the underlay's Mesh.validate() deletes one
    of each pair, which left the fences single-sided (Exotics 172 verts / 86 faces, ledger 0071)."""
    for copy in (0, 1):
        base = len(out["vertices"])
        out["vertices"].extend(verts)
        out["uvs"].extend(uvs)
        if copy == 0:
            out["tris"].extend((a + base, b + base, c + base) for a, b, c in tris)
        else:
            out["tris"].extend((a + base, c + base, b + base) for a, b, c in tris)


def instance_barriers(centerline_m: list[Vertex], widths_m: list[float], placements: list[dict],
                      module: dict, *, module_len: float = 4.04, off_extra: float = 1.6,
                      base_sink: float = 0.05, surface_y=None, on_pavement=None,
                      station_skip=None) -> dict:
    """Stamp the barrier module end-to-end along each warning-barrier run, on the run's OUTSIDE.
    Load the module with ``load_module(..., keep_seams=True)`` so its UVs survive.

    ``surface_y(x, z) -> y|None`` seats each module on the BUILT edge surface (road+shoulder tops).
    Seating at centerline height floats the whole run wherever the verge falls away — every fill
    and hairpin on the Lariat shipped with barriers hovering in mid-air ("everything is floating")."""
    pts = centerline_m
    n = len(pts)
    out = {"vertices": [], "uvs": [], "tris": []}
    for pl in placements:
        a0, b0, side = pl["start_idx"], pl.get("end_idx", pl["start_idx"] + 8), pl["side"]
        arc = 0.0
        next_at = 0.0
        for i in range(max(1, a0), min(b0, n - 1)):
            seg = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2])
            arc += seg
            if arc < next_at:
                continue
            next_at += module_len
            if station_skip is not None and station_skip(i):
                continue          # bridge spans carry their own railings — no barriers walked
                                  # onto the shoulder drape over the void (27 m floaters)
            x, y, z = pts[i]
            tx, tz = pts[min(i + 1, n - 1)][0] - pts[i - 1][0], pts[min(i + 1, n - 1)][2] - pts[i - 1][2]
            L = math.hypot(tx, tz) or 1e-9
            tx, tz = tx / L, tz / L
            nx, nz = -tz * side, tx * side              # outward on the run's side
            # width RAMPS through junction flares (0.15 m/m): a 4 m module placed off one
            # station's width ends up INSIDE the widened lane a few metres later. Use the max
            # width over the module's whole span.
            _wspan = max(widths_m[max(0, i - 2):min(n, i + 3)] or [widths_m[i]])
            off = _wspan / 2.0 + off_extra
            if on_pavement is not None:
                # a danger barrier must guard the corner, not stand on its flared apron: WALK
                # OUTBOARD until off the pavement — but ONLY onto real support (walking off a
                # BRIDGE DECK hung modules 27 m over the creek). No supported clear spot = skip.
                _ok_spot = False
                for _try in range(5):
                    _cx0, _cz0 = x + nx * off, z + nz * off
                    _hl0 = module_len / 2.0
                    if not any(on_pavement(_cx0 + tx * _q0, _cz0 + tz * _q0, y)
                               for _q0 in (-_hl0, 0.0, _hl0)):
                        if surface_y is None:
                            _ok_spot = True
                            break
                        _sy0 = surface_y(_cx0, _cz0, y)
                        # STANDABLE support only: probe the local slope — a 0.75:1 fill face
                        # (53 deg) passes the wall-cut but nothing stands on it (the Quebec
                        # approach floaters). Reject support steeper than ~24 deg.
                        if _sy0 is not None and abs(_sy0 - y) < 2.5:
                            _sy1 = surface_y(_cx0 + nx * 0.8, _cz0 + nz * 0.8, y)
                            if _sy1 is not None and abs(_sy1 - _sy0) <= 0.35:
                                _ok_spot = True
                                break
                    off += 1.0
                if not _ok_spot:
                    continue
            bx, bz = x + nx * off, z + nz * off
            if surface_y is not None:
                sy = surface_y(bx, bz, y)   # y_ref = the run's own station height (layer window)
                if sy is not None:
                    _syo = surface_y(bx + nx * 0.8, bz + nz * 0.8, y)
                    if _syo is not None and abs(_syo - sy) > 0.35:
                        sy = None           # steep face is not support — force the inboard retry
                if sy is None:
                    # retry INBOARD and MOVE the module there — taking the inboard height while
                    # leaving the module at the outer spot hung 50 modules over the shoulder edge
                    bx2, bz2 = x + nx * (off - 1.2), z + nz * (off - 1.2)
                    sy = surface_y(bx2, bz2, y)
                    if sy is not None:
                        bx, bz = bx2, bz2
                if sy is None:
                    continue                 # nothing built under this spot — skip, never float
                y = sy + base_sink           # seat ON the built surface (sink re-subtracted below)
            # module: length along local Z, width X, up Y, base at y=0. Each face ONCE, wound
            # outward for this placement's handedness (module_tris; ledger 0071). The old
            # double-sided stamp shared vertices, and the underlay's validate() halved it at random.
            place_module(out, module, (bx, y - base_sink, bz), (nx, nz), (tx, tz))
    return out


def instance_line(centerline_m, module: dict, *, ranges: list[dict], widths_m=None,
                  ground=None, module_len: float = 1.7, default_offset: float = 8.0,
                  max_dy: float = 45.0, reject=None) -> dict:
    """Instance a module continuously along config-declared lap ranges — ranch fences at the
    right-of-way line, pylon runs across the plains. Each instance drapes to ``ground(x,z)`` so
    runs follow the terrain. ranges: [{start_m, end_m, side (+1 left/-1 right/0 both), offset_m}]."""
    pts = centerline_m
    n = len(pts)
    st = [0.0]
    for i in range(1, n):
        st.append(st[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    out = {"vertices": [], "uvs": [], "tris": []}
    _last_panel: dict = {}
    for rg in ranges:
        s0, s1 = float(rg["start_m"]), float(rg["end_m"])
        off = float(rg.get("offset_m", default_offset))
        sides = (1.0, -1.0) if rg.get("side", 0) == 0 else (float(rg["side"]),)
        for side in sides:
            next_at = s0
            for i in range(1, n):
                if st[i] < next_at:
                    continue
                if st[i] > s1:
                    break
                next_at += module_len
                x, y, z = pts[i]
                tx = pts[min(i + 1, n - 1)][0] - pts[i - 1][0]
                tz = pts[min(i + 1, n - 1)][2] - pts[i - 1][2]
                L = math.hypot(tx, tz) or 1e-9
                tx, tz = tx / L, tz / L
                nx, nz = -tz * side, tx * side
                w_half = (max(widths_m[max(0, i - 3):min(len(widths_m), i + 4)]) / 2.0 if widths_m else 0.0)
                bx, bz = x + nx * (w_half + off), z + nz * (w_half + off)
                # seat on the MIN ground over the module's footprint (center + both ends): a
                # center-point seat on a bank flies the downhill end of the panel (+1.6 m fence
                # floats). Burying the uphill end slightly is what real fence posts do.
                if ground and module_len <= 10.0:      # short modules (fences); pylons keep center-seat
                    _hl = module_len / 2.0
                    _cands = [ground(bx, bz), ground(bx + tx * _hl, bz + tz * _hl),
                              ground(bx - tx * _hl, bz - tz * _hl)]
                    _cands = [c for c in _cands if c is not None]
                    by = min(_cands) if _cands else None
                elif ground:
                    by = ground(bx, bz)
                else:
                    by = y
                # LAYER WINDOW safety net: a ground sample tens of metres off the run's own station
                # height is corrupt or another terrain layer — skip the instance, never fly/bury it.
                if by is None or abs(by - y) > max_dy:
                    continue
                # footing sink (per-range): tall towers on rough terrain bury their footings — a
                # 10 m-grid drape leaves a corner up to ~1 m proud of the true surface otherwise.
                by -= float(rg.get("sink_m", 0.0))
                if reject is not None:
                    _hl2 = module_len / 2.0
                    # probe the module's CORNERS too — a diagonal apron edge can clip a panel's
                    # side while its axis line stays clear (one panel, 14 audit verts)
                    _probe2 = [(bx + tx * _q, bz + tz * _q) for _q in (-_hl2, 0.0, _hl2)]
                    _probe2 += [(bx + tx * _q + nx * _w2, bz + tz * _q + nz * _w2)
                                for _q in (-_hl2, _hl2) for _w2 in (-0.6, 0.6)]
                    if any(reject(_px2, _pz2, by) for _px2, _pz2 in _probe2):
                        continue        # module would stand on pavement (corner mouths, aprons)
                # PILE GUARD: on tight corners consecutive stations' tangents fan — stamping a
                # panel per station piles them into a woodstack. Skip until the run has moved
                # a real module-length AND turned less than 30 deg since the last stamp.
                _yaw2 = math.atan2(tz, tx)
                _lp = _last_panel.get(id(rg))
                if _lp is not None:
                    _dyaw = abs((_yaw2 - _lp[2] + math.pi) % (2 * math.pi) - math.pi)
                    if math.hypot(bx - _lp[0], bz - _lp[1]) < module_len * 0.8 or \
                       (_dyaw > math.radians(30.0) and math.hypot(bx - _lp[0], bz - _lp[1]) < module_len * 2.0):
                        continue
                _last_panel[id(rg)] = (bx, bz, _yaw2)
                base = len(out["vertices"])
                for mx, my, mz in module["vertices"]:
                    out["vertices"].append((bx + tx * mz + nx * mx, by + my, bz + tz * mz + nz * mx))
                out["uvs"].extend(module["uvs"])
                out["tris"].extend((a + base, b + base, c + base) for a, b, c in module["tris"])
                if module_len <= 10.0:      # panels are seen from both sides; pylons are closed solids
                    out["tris"].extend((a + base, c + base, b + base) for a, b, c in module["tris"])
    return out
