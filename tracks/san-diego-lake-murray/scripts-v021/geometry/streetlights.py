"""Streetlights on the north network's authored pieces (ledger 0054 P4 step 2; EXPANSION-PLAN D4).

The loop's draft (blender/build_loop_blend.build_streetlights) walks the MAINLINE every SPACING_M, alternating sides,
and stands a post hw + 2.8 m off the centreline (the graded back edge of the loop's 1.8 m walk), 8.8 m under its head.
This module is the same walk for the four authored pieces (data/expansion.north.json: A Waring, B Princess View,
C Mission Gorge, D Jackson north, as data/connectors.local.json carries them), with the rules the pieces need:

  * the post stands ON the piece's walk, mid-way across it (WALK_OFFSET_M behind the pavement edge: the curb face
    0.08 + half the 1.5 m walk; tools/author_lamps_blend.py LAMP_BEHIND_CURB_M, the rule lamp 77 stands by on J1's
    return), never on the graded verge behind it — the cut faces of Jackson and Mission Gorge rise right there;
  * it stays clear of EVERY other pavement: the mainline, every other connector (the side-street STUBS included, with
    their curb returns), the junction pads J2-J4 (outline + their stub arms), and every curb cut (a lowered curb at a
    driveway) on its own host and side;
  * no two posts within MIN_GAP_M (the loop's rule), the loop's own posts counted;
  * D4: a declared UNLIT stretch of a piece (Jackson north's open canyon, stations 250-1500) gets no post;
  * where OpenStreetMap has real `highway=street_lamp` nodes beside a piece, the posts stand AT those nodes (on the
    walk, on the node's side) and the loop's spacing is not used over that stretch: each lamp records its source,
    "osm:<node id>" or "authored" (the loop's spacing), and the per-piece stretches say which rule lit them;
  * a blocked station slides along the walk (SLIDE_M in SLIDE_STEP_M steps), then tries the other side, then is
    skipped with its reasons recorded (never silently).

Heads are recorded the way the loop's are (lights.local.json lampheads: the arm tip ARM_M road-ward of the post,
HEAD_OVER_GROUND_M over the draft ground under the post) PLUS the base and the road-ward unit per lamp, because the
author's "road-ward = head -> nearest MAINLINE point" rule has no meaning 500 m from the mainline.

Pure python (no bpy): tests/tools/test_expansion_lamps.py. Every [invented] number is in fleet/GATES-CHANGELOG.md
("P4 lamps").
"""
from __future__ import annotations

import math

SPACING_M = 55.0            # the loop's draft spacing (build_streetlights spacing=55.0)
MIN_GAP_M = 25.0            # the loop's draft rule: no two posts closer than this
WALK_OFFSET_M = 0.83        # curb face 0.08 + half the pieces' 1.5 m walk (author_lamps_blend LAMP_BEHIND_CURB_M)
PAVEMENT_CLEAR_M = 1.5      # [invented] a base closer than this to ANOTHER pavement's edge is in its way
PAD_CLEAR_M = 3.0           # [invented] from a junction pad's outline (its curb returns and walk stand on it)
STUB_CLEAR_M = 10.0         # [invented] past a side-street stub's pavement edge along the host: its curb returns + walk
SLIDE_M = 12.0              # [invented] how far a blocked station may slide along the walk before the other side
SLIDE_STEP_M = 2.0          # [invented]
OSM_MATCH_M = 15.0          # [invented] an OSM street_lamp node this close to a piece's pavement edge stands on it
OSM_STRETCH_PAD_M = 27.5    # half the loop spacing: the OSM-grounded stretch reaches this far past its end nodes
ARM_M = 1.8                 # the draft's arm (build_streetlights arm=1.8)
HEAD_OVER_GROUND_M = 8.8    # the draft's head rule: post_h 9.0 - 0.2 over the ground under the post
START_M = SPACING_M         # the first station along each piece (the loop starts its walk at one spacing too)


# ----------------------------------------------------------------------------------------------- geometry helpers
def _cum(pts):
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]))
    return cum


class Line:
    """a polyline of (x, y, z) points with per-point widths: interpolation by arc length u, nearest-point projection"""

    def __init__(self, pts, widths=None):
        self.pts = [tuple(p) for p in pts]
        self.w = list(widths) if widths is not None else [0.0] * len(self.pts)
        self.cum = _cum(self.pts)
        self.length = self.cum[-1]

    def _seg(self, u):
        import bisect
        u = max(0.0, min(self.length, u))
        i = max(0, min(len(self.pts) - 2, bisect.bisect_right(self.cum, u) - 1))
        L = self.cum[i + 1] - self.cum[i]
        t = 0.0 if L <= 1e-9 else (u - self.cum[i]) / L
        return i, t

    def at(self, u):
        """(x, y, z), (tx, tz) unit tangent, width at arc length u"""
        i, t = self._seg(u)
        a, b = self.pts[i], self.pts[i + 1]
        x, y, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        w = self.w[i] + (self.w[i + 1] - self.w[i]) * t
        return (x, y, z), (tx / L, tz / L), w

    def project(self, x, z):
        """(distance, u, lateral) of (x, z) to the line: lateral + = left of the direction of travel"""
        best = (float("inf"), 0.0, 0.0)
        for i in range(len(self.pts) - 1):
            ax, az = self.pts[i][0], self.pts[i][2]
            bx, bz = self.pts[i + 1][0], self.pts[i + 1][2]
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 <= 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
            px, pz = ax + dx * t, az + dz * t
            d = math.hypot(x - px, z - pz)
            if d < best[0]:
                L = math.sqrt(L2) or 1.0
                lat = (-dz / L) * (x - px) + (dx / L) * (z - pz)
                best = (d, self.cum[i] + L * t, lat)
        return best

    def edge_distance(self, x, z):
        """distance from (x, z) to the pavement edge (negative inside the pavement)"""
        d, u, _lat = self.project(x, z)
        _p, _t, w = self.at(u)
        return d - w / 2.0


def point_in_polygon(poly, x, z):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xi = x1 + (z - z1) * (x2 - x1) / (z2 - z1)
            if x < xi:
                inside = not inside
    return inside


def dist_to_outline(poly, x, z):
    best = float("inf")
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 <= 1e-12 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        best = min(best, math.hypot(x - (ax + dx * t), z - (az + dz * t)))
    return best


def station_of(stations, x, z):
    """the intermediate's station s nearest (x, z) (pieces[].stations rows [s, x, z, ...]); None without a table"""
    if not stations:
        return None
    return min(stations, key=lambda r: (r[1] - x) ** 2 + (r[2] - z) ** 2)[0]


# ----------------------------------------------------------------------------------------------- the plan
def unlit_stretches(cfg_expansion, piece_id):
    out = []
    for e in (cfg_expansion or {}).get("unlit") or []:
        if str(e.get("piece")) == str(piece_id):
            out.append((float(e["s_from"]), float(e["s_to"]), str(e.get("why", ""))))
    return out


def osm_lamps_on_piece(line, nodes, match_m=OSM_MATCH_M):
    """the OSM street_lamp nodes standing beside this piece: [(u, side, node id)], sorted by u"""
    out = []
    for nd in nodes or []:
        d, u, lat = line.project(nd["x"], nd["z"])
        _p, _t, w = line.at(u)
        if u <= 0.0 or u >= line.length:
            continue
        if abs(lat) - w / 2.0 <= match_m and abs(lat) >= 0.0:
            out.append((u, 1 if lat >= 0 else -1, nd["id"]))
    return sorted(out)


def osm_stretches(osm_u, spacing=SPACING_M, pad=OSM_STRETCH_PAD_M):
    """[u_from, u_to] per cluster of OSM nodes closer than 2 x spacing: inside, the loop's spacing is not used"""
    out = []
    for u, _side, _id in osm_u:
        if out and u - out[-1][1] <= 2 * spacing:
            out[-1][1] = u
        else:
            out.append([u, u])
    return [[max(0.0, a - pad), b + pad] for a, b in out]


def plan(pieces, *, mainline, others, pads, stubs, curb_cuts, placed, cfg_expansion=None, osm_nodes=None, ground=None,
         spacing=None):
    """Plan the pieces' lamps. ``pieces`` = [{name, id, pts, widths, stations}]; ``mainline`` = (pts, widths);
    ``others`` = [(name, pts, widths, kind)] every OTHER connector (kind "stub" | "connector"); ``pads`` =
    [(id, outline_xz)] (pad outlines and their stub arms' pavements); ``stubs`` = [{id, host, side, cut_xz, width_m}];
    ``curb_cuts`` = [{id, host, side, station_m, half_span_m, flare_m, cut_xz}]; ``placed`` = [(x, z)] bases already
    standing (the loop's); ``osm_nodes`` = [{id, x, z}] street_lamp nodes in the local frame; ``ground(x, z)`` = the
    draft ground. Returns {"lamps": [...], "skipped": [...], "per_piece": {...}}; each lamp: head, base_xz,
    roadward_xz, piece, name, u_m, s_m, side, source."""
    spacing = float(spacing or (cfg_expansion or {}).get("spacing_m") or SPACING_M)
    min_gap = float((cfg_expansion or {}).get("min_gap_m") or MIN_GAP_M)
    walk_off = float((cfg_expansion or {}).get("walk_offset_m") or WALK_OFFSET_M)
    main = Line(*mainline) if mainline and len(mainline[0]) > 1 else None
    other_lines = [(n, Line(p, w), k) for n, p, w, k in others if len(p) > 1]
    placed = [tuple(p) for p in placed]
    lamps, skipped, per_piece = [], [], {}
    ground = ground or (lambda x, z: 0.0)

    for pc in pieces:
        line = Line(pc["pts"], pc["widths"])
        pid, name = str(pc.get("id")), pc["name"]
        stations = pc.get("stations") or []
        unlit = unlit_stretches(cfg_expansion, pid)
        my_cuts = [c for c in curb_cuts if c.get("host") == name]
        my_stubs = [s for s in stubs if s.get("host") == name]
        cut_u = {c["id"]: line.project(c["cut_xz"][0], c["cut_xz"][1])[1] for c in my_cuts if c.get("cut_xz")}
        stub_u = {s["id"]: line.project(s["cut_xz"][0], s["cut_xz"][1])[1] for s in my_stubs if s.get("cut_xz")}
        osm_u = osm_lamps_on_piece(line, osm_nodes)
        o_stretches = osm_stretches(osm_u, spacing)
        rec = {"name": name, "length_m": round(line.length, 1), "authored": 0, "osm": 0, "skipped": 0,
               "unlit": [{"s_from": a, "s_to": b, "why": w} for a, b, w in unlit],
               "osm_stretches_u": [[round(a, 1), round(b, 1)] for a, b in o_stretches],
               "osm_nodes": [{"u_m": round(u, 1), "side": sd, "id": i} for u, sd, i in osm_u]}

        def candidate(u, side):
            p, (tx, tz), w = line.at(u)
            nx, nz = -tz, tx                       # left of travel
            off = w / 2.0 + walk_off
            bx, bz = p[0] + nx * side * off, p[2] + nz * side * off
            rx, rz = -nx * side, -nz * side        # road-ward
            return bx, bz, rx, rz, w

        def why_blocked(u, side, bx, bz, w):
            why = []
            s = station_of(stations, bx, bz)
            for a, b, wtxt in unlit:
                if s is not None and a <= s <= b:
                    return ["unlit"]              # D4: never slid around, never the other side
            for a, b in o_stretches:
                if a <= u <= b:
                    return ["osm_stretch"]        # the OSM nodes light this stretch
            for px, pz in placed:
                if (px - bx) ** 2 + (pz - bz) ** 2 < min_gap * min_gap:
                    why.append("gap")
                    break
            if main is not None and main.edge_distance(bx, bz) < PAVEMENT_CLEAR_M:
                why.append("mainline")
            for n, ln, kind in other_lines:
                if n == name:
                    continue
                clear = PAVEMENT_CLEAR_M + (STUB_CLEAR_M if kind == "stub" else 0.0)
                if ln.edge_distance(bx, bz) < clear:
                    why.append(f"{kind}:{n}")
            for pid_, poly in pads:
                if point_in_polygon(poly, bx, bz) or dist_to_outline(poly, bx, bz) < PAD_CLEAR_M:
                    why.append(f"pad:{pid_}")
            for c in my_cuts:
                if c.get("side", 0) == side and c["id"] in cut_u and \
                        abs(u - cut_u[c["id"]]) < float(c.get("half_span_m", 0)) + float(c.get("flare_m", 0)) + PAVEMENT_CLEAR_M:
                    why.append(f"curb_cut:{c['id']}")
            for st in my_stubs:
                if st.get("side", 0) == side and st["id"] in stub_u and \
                        abs(u - stub_u[st["id"]]) < float(st.get("width_m", 0)) / 2.0 + STUB_CLEAR_M:
                    why.append(f"stub:{st['id']}")
            return why

        def place(u, side, source):
            bx, bz, rx, rz, w = candidate(u, side)
            gy = ground(bx, bz)
            hx, hz = bx + rx * ARM_M, bz + rz * ARM_M
            lamp = {"head": [round(hx, 3), round(gy + HEAD_OVER_GROUND_M, 3), round(hz, 3)],
                    "base_xz": [round(bx, 3), round(bz, 3)], "roadward_xz": [round(rx, 5), round(rz, 5)],
                    "piece": pid, "name": name, "u_m": round(u, 2), "s_m": station_of(stations, bx, bz),
                    "side": "L" if side > 0 else "R", "width_m": round(w, 2), "source": source,
                    "ground_y_draft": round(gy, 3)}
            lamps.append(lamp)
            placed.append((bx, bz))
            return lamp

        # the OSM-grounded posts first: at the node, on its side, on the walk
        for u, side, nid in osm_u:
            bx, bz, rx, rz, w = candidate(u, side)
            why = [r for r in why_blocked(u, side, bx, bz, w) if r != "osm_stretch"]
            if why:
                skipped.append({"piece": pid, "name": name, "u_m": round(u, 1), "side": "L" if side > 0 else "R",
                                "source": f"osm:{nid}", "why": why})
                rec["skipped"] += 1
                continue
            place(u, side, f"osm:{nid}")
            rec["osm"] += 1

        # the loop's walk: every spacing, alternating sides; slide, then the other side, then skip
        u, side = START_M, 1
        while u < line.length - min_gap:
            done, reasons = None, []
            for sd in (side, -side):
                for k in range(0, int(SLIDE_M / SLIDE_STEP_M) + 1):
                    for du in ((0.0,) if k == 0 else (k * SLIDE_STEP_M, -k * SLIDE_STEP_M)):
                        uu = u + du
                        if uu <= 0.0 or uu >= line.length:
                            continue
                        bx, bz, rx, rz, w = candidate(uu, sd)
                        why = why_blocked(uu, sd, bx, bz, w)
                        if not why:
                            done = (uu, sd)
                            break
                        reasons.append((sd, round(du, 1), why))
                        if why == ["unlit"] or why == ["osm_stretch"]:
                            break
                    if done or (reasons and reasons[-1][2] in (["unlit"], ["osm_stretch"])):
                        break
                if done or (reasons and reasons[-1][2] in (["unlit"], ["osm_stretch"])):
                    break
            if done:
                place(done[0], done[1], "authored")
                rec["authored"] += 1
                side = -done[1]
            else:
                flat = sorted({r for _sd, _du, why in reasons for r in why})
                skipped.append({"piece": pid, "name": name, "u_m": round(u, 1), "side": "L" if side > 0 else "R",
                                "source": "authored", "why": flat})
                if flat not in (["unlit"], ["osm_stretch"]):
                    rec["skipped"] += 1
                side = -side
            u += spacing
        per_piece[pid] = rec
    return {"lamps": lamps, "skipped": skipped, "per_piece": per_piece,
            "rules": {"spacing_m": spacing, "min_gap_m": min_gap, "walk_offset_m": walk_off,
                      "pavement_clear_m": PAVEMENT_CLEAR_M, "pad_clear_m": PAD_CLEAR_M, "stub_clear_m": STUB_CLEAR_M,
                      "slide_m": SLIDE_M, "osm_match_m": OSM_MATCH_M, "arm_m": ARM_M,
                      "head_over_ground_m": HEAD_OVER_GROUND_M}}


def project_osm_nodes(nodes, origin_lon, origin_lat):
    """OSM street_lamp nodes (lat / lon) -> [{id, x, z}] in the local frame (scripts-v021 projection series)"""
    phi = math.radians(origin_lat)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    out = []
    for nd in nodes or []:
        try:
            out.append({"id": int(nd["id"]), "x": (float(nd["lon"]) - origin_lon) * m_lon,
                        "z": (float(nd["lat"]) - origin_lat) * m_lat})
        except (KeyError, TypeError, ValueError):
            continue
    return out
