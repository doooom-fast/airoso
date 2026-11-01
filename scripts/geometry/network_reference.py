"""The reference line of a road NETWORK: one real mainline, chosen from the draft's own edges, for the ship phase.

WHY. The ship phase was written for one-line tracks: the prep (scripts/ac/build_kn5_loop.py), write_ai_line, make_map,
verify_kn5 and drive_test read ``data/centerline.local.json`` and the prep's ``data/finished_centerline.json``; a
network draft (scripts.gps.network -> classify -> scripts.elevation.network_elev -> scripts.geometry.build_network_mesh)
writes ``network.geojson`` and a track.obj of every edge instead, so a network's chain stopped at the prep
(tracks/san-diego-freeway/README.md "What the Windows run owes"). The honest shape is the one that README names: the
config DECLARES a reference line on the real road, never an invented one (fleet/LAWS.md L1).

THE DECLARATION (track.config.json ``network.reference_line``)::

    "reference_line": {
      "ref": "I 8",                 # the OSM ref classify recorded as the edge name (motorway / trunk: tags.ref)
      "direction": "eastbound",     # eastbound | westbound | northbound | southbound: the carriageway driven
      "edge_ids": null,             # OR an explicit ordered list of network.geojson edge ids, in driving order
      "bridge_max_edges": 0,        # how many non-ramp freeway edges of ANOTHER name may join two pieces (named)
      "max_joint_turn_deg": 45.0,   # a joint turning more than this is not a continuation (no U-turn chains)
      "join_tol_m": null            # endpoints this close are one network node (default network.snap_grid_m)
    }

RESOLUTION (no point is ever made up). Every edge's direction of travel comes from the OSM ways' own order
(scripts.gps.classify ``travel_dir``, opt-in on this block: a motorway way is drawn the way it is driven). The
candidates are the freeway-class, non-ramp edges named ``ref`` whose travel is not undecided and whose own chord does
not run against ``direction``; two edges continue each other when the first's head node is the second's tail node
(endpoints within ``join_tol_m`` — the same snapped OSM node) and the joint turns under ``max_joint_turn_deg``. The
line is the LONGEST such directed chain ("end to end"), which must start and end on a candidate; up to
``bridge_max_edges`` non-ramp freeway edges of another name may sit inside it (each named in the report: a mainline
piece the nearest-way vote gave a crossing freeway's ref). ``edge_ids`` replaces the search with a list that is checked
the same way. Then: the chain's overall heading must be within 60 deg of ``direction``; where the opposite carriageway
runs beside it (same ref, travel the other way, within 80 m) it must lie on the LEFT (right-hand traffic) at most
samples — a cross-check of travel_dir against geometry. Any failure is a refusal (exit 1) that says what to declare.

THE LINE. Every point is a vertex of a real built edge: the swept line build_network_mesh recorded
(``data/network.edges.local.json``), edge after edge in driving order. At a joint the shared vertex is written once; two
vertices of the same snapped node that differ (< join_tol_m) are both kept, never a point between them.

WRITES (data/):
  * ``centerline.local.json`` — the at-grade line (3DEP z_smooth - elev0), UNMIRRORED local ENU (the frame
    scripts.geometry.projection writes), the network's own origin, ``loop: false``, widths = the classified edge
    widths, ``source_by_vertex`` = [edge id, network.geojson vertex].
  * ``finished_centerline.json`` — the swept surface line, frame "mesh …" (the OBJ frame): the prep converts it to the
    KN5 frame and keeps the spans below, exactly as it does build_mesh's.
  * ``bridge.spans.auto.json`` — stations where the line rides a deck the mesh raised over 1 m (OSM bridge layers).
  * ``dummies.json`` — a single layout's grid: AC_START / PIT / HOTLAP at the START of the line, AC_TIME_0 at its
    FINISH, splits numbered up from 1 in driving order (L11: a free-roam network driven along one carriageway is a
    point-to-point road), scripts.geometry.dummies.place_dummies(loop=False), lifted SPAWN_CLEAR_M off the pavement.
  * ``network.reference.json`` — the record: the chain, its evidence, and EVERY built edge NOT on it, by id, name,
    class and length. Those edges are built (they are in track.obj) but no line-walking gate drives them: drive_test
    prints the list, ship.json ``_owed`` names the hole.

    python -m scripts.geometry.network_reference <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FREEWAY_CLS = ("motorway", "trunk")
HEADINGS = {"eastbound": (1.0, 0.0), "westbound": (-1.0, 0.0), "northbound": (0.0, 1.0), "southbound": (0.0, -1.0)}
MAX_JOINT_TURN_DEG = 45.0     # [invented] a carriageway continuing through a junction node turns far less
HEADING_TOL_DEG = 60.0        # [invented] the chain's overall heading vs the declared compass direction
OPPOSITE_SEARCH_M = 80.0      # [invented] a divided freeway's other carriageway runs within this of the line
SIDE_SAMPLE_M = 50.0
DECK_SPAN_LIFT_M = 1.0        # build_network_mesh raises an edge onto a deck when its lift exceeds 1.0 m
SPAWN_CLEAR_M = 0.6           # build_network_mesh._freeroam_dummies: the car origin this far above the pavement
FRAME_MESH = "mesh (network reference line) local metres — same frame as track.obj"
OUTPUTS = ("centerline.local.json", "finished_centerline.json", "bridge.spans.auto.json", "network.reference.json",
           "gate_centerline.json")


class RefusedError(SystemExit):
    """The declaration cannot be honoured from the draft's own edges (exit 1, with the reason)."""

    def __init__(self, msg: str):
        super().__init__(f"[network_reference] REFUSED: {msg}")
        self.reason = msg


def _norm_name(v) -> set[str]:
    return {s.strip() for s in str(v).split(";") if s.strip()} if v else set()


def _xz(p):
    return (float(p[0]), float(p[2]))


def _unit(dx, dz):
    L = math.hypot(dx, dz)
    return (dx / L, dz / L) if L > 1e-9 else (0.0, 0.0)


class _Edge:
    __slots__ = ("id", "name", "cls", "is_ramp", "travel", "trimmed", "length", "surf", "grade", "widths",
                 "tail", "head", "rec")

    def __init__(self, rec: dict, length_m: float):
        self.rec = rec
        self.id = rec["id"]
        self.name = rec.get("name")
        self.cls = rec.get("road_class")
        self.is_ramp = bool(rec.get("is_ramp"))
        self.travel = int(rec.get("travel_dir") or 0)
        self.trimmed = bool(rec.get("trimmed"))
        self.length = float(length_m)
        s, g, w = rec["surface_xyz_m"], rec["at_grade_xyz_m"], rec["widths_m"]
        idx = list(range(len(g)))
        if self.travel < 0:                       # driving order
            s, g, w, idx = s[::-1], g[::-1], w[::-1], idx[::-1]
        self.surf, self.grade, self.widths = s, g, w
        self.rec = {**rec, "_idx": idx}
        self.tail = self.head = None

    def first_dir(self):
        a, b = self.grade[0], self.grade[min(1, len(self.grade) - 1)]
        return _unit(b[0] - a[0], b[2] - a[2])

    def last_dir(self):
        a, b = self.grade[max(0, len(self.grade) - 2)], self.grade[-1]
        return _unit(b[0] - a[0], b[2] - a[2])

    def chord(self):
        a, b = self.grade[0], self.grade[-1]
        return (b[0] - a[0], b[2] - a[2])


def _nodes(edges: list[_Edge], tol: float) -> None:
    """Union every edge endpoint within ``tol`` (plan) into one node; set each edge's tail / head (driving order)."""
    ends = []
    for k, e in enumerate(edges):
        ends.append((k, 0, _xz(e.grade[0])))
        ends.append((k, 1, _xz(e.grade[-1])))
    parent = list(range(len(ends)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    cell = max(tol, 1e-3)
    grid: dict = {}
    for i, (_k, _w, (x, z)) in enumerate(ends):
        grid.setdefault((int(math.floor(x / cell)), int(math.floor(z / cell))), []).append(i)
    for i, (_k, _w, (x, z)) in enumerate(ends):
        cx, cz = int(math.floor(x / cell)), int(math.floor(z / cell))
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((cx + dx, cz + dz), ()):
                    if j > i and math.dist((x, z), ends[j][2]) <= tol:
                        ra, rb = find(i), find(j)
                        if ra != rb:
                            parent[ra] = rb
    for i, (k, w, _p) in enumerate(ends):
        if w == 0:
            edges[k].tail = find(i)
        else:
            edges[k].head = find(i)


def _turn_deg(a: tuple, b: tuple) -> float:
    c = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    return math.degrees(math.acos(c))


def _joint_ok(e: _Edge, f: _Edge, max_turn: float) -> bool:
    return e.head == f.tail and e is not f and _turn_deg(e.last_dir(), f.first_dir()) <= max_turn


def _longest_chain(cands: list[_Edge], bridges: list[_Edge], max_bridges: int, max_turn: float) -> list[_Edge]:
    """The longest directed chain that starts and ends on a candidate, with at most ``max_bridges`` bridge edges
    inside it. Memoised DFS over (edge, bridges used); a cycle is a refusal (a carriageway does not loop)."""
    pool = cands + bridges
    is_b = {id(e): (e in bridges) for e in pool}
    by_tail: dict = {}
    for e in pool:
        by_tail.setdefault(e.tail, []).append(e)
    memo: dict = {}
    onstack: set = set()

    def best(e: _Edge, k: int):
        key = (id(e), k)
        if key in memo:
            return memo[key]
        if key in onstack:
            raise RefusedError(f"the candidate edges form a directed cycle through edge {e.id} — a carriageway does "
                               f"not loop; declare network.reference_line.edge_ids")
        onstack.add(key)
        top = (e.length, [e]) if not is_b[id(e)] else (None, None)
        for f in sorted(by_tail.get(e.head, ()), key=lambda q: q.id):
            if not _joint_ok(e, f, max_turn):
                continue
            k2 = k + (1 if is_b[id(f)] else 0)
            if k2 > max_bridges:
                continue
            sub = best(f, k2)
            if sub[0] is not None and (top[0] is None or e.length + sub[0] > top[0] + 1e-9):
                top = (e.length + sub[0], [e] + sub[1])
        onstack.discard(key)
        memo[key] = top
        return top

    out, out_len = [], -1.0
    for e in sorted(cands, key=lambda q: q.id):
        L, chain = best(e, 0)
        if L is not None and L > out_len + 1e-9:
            out, out_len = chain, L
    return out


def _components(pool: list[_Edge]) -> list[list[_Edge]]:
    """Connected pieces of ``pool`` (edges sharing a node, either direction)."""
    by_node: dict = {}
    for e in pool:
        by_node.setdefault(e.tail, []).append(e)
        by_node.setdefault(e.head, []).append(e)
    seen, out = set(), []
    for e in pool:
        if id(e) in seen:
            continue
        comp, stack = [], [e]
        seen.add(id(e))
        while stack:
            q = stack.pop()
            comp.append(q)
            for n in (q.tail, q.head):
                for r in by_node.get(n, ()):
                    if id(r) not in seen:
                        seen.add(id(r))
                        stack.append(r)
        out.append(comp)
    return out


def _link_path(edges: list[_Edge], src_node, dst_node, max_turn: float, first_dir, max_len: int = 4):
    """The fewest built edges (any freeway class, decided travel, untrimmed) leading from src_node to dst_node in
    driving order, joints <= max_turn, at most ``max_len`` edges; None when there is none. Only a SUGGESTION in a
    refusal: the operator reads it and declares edge_ids."""
    pool = [e for e in edges if e.cls in FREEWAY_CLS and e.travel != 0 and not e.trimmed]
    by_tail: dict = {}
    for e in pool:
        by_tail.setdefault(e.tail, []).append(e)
    frontier = [([], src_node, first_dir)]
    for _ in range(max_len):
        nxt = []
        for path, node, d in frontier:
            for e in sorted(by_tail.get(node, ()), key=lambda q: q.id):
                if any(e is q for q in path) or (d is not None and _turn_deg(d, e.first_dir()) > max_turn):
                    continue
                if e.head == dst_node:
                    return path + [e]
                nxt.append((path + [e], e.head, e.last_dir()))
        frontier = nxt
    return None


def _refuse_if_broken(chain, cands, edges, max_turn, ref, direction) -> None:
    """The declaration says END TO END: a same-ref, same-direction piece that does not touch the chain at all means
    the road is broken in this draft (a mislabelled or missing piece between), and no line is drawn across a gap.
    Refuse, naming the pieces, their gap to the chain, and — where the draft has one — a contiguous edge_ids list."""
    on_nodes = {e.tail for e in chain} | {e.head for e in chain}
    loose = [c for c in _components([e for e in cands if e not in chain])
             if not any(e.tail in on_nodes or e.head in on_nodes for e in c)]
    if not loose:
        return
    msgs = []
    for comp in loose:
        piece = _longest_chain(comp, [], 0, max_turn) or sorted(comp, key=lambda q: q.id)
        L = sum(e.length for e in comp)
        g_after = math.dist(_xz(chain[-1].grade[-1]), _xz(piece[0].grade[0]))
        g_before = math.dist(_xz(piece[-1].grade[-1]), _xz(chain[0].grade[0]))
        sug = None
        p1 = _link_path(edges, chain[-1].head, piece[0].tail, max_turn, chain[-1].last_dir())
        if p1 is not None:
            sug = [e.id for e in chain + p1 + piece]
        else:
            p2 = _link_path(edges, piece[-1].head, chain[0].tail, max_turn, piece[-1].last_dir())
            if p2 is not None:
                sug = [e.id for e in piece + p2 + chain]
        msgs.append(f"piece {[e.id for e in piece]} ({L:.0f} m) lies {min(g_after, g_before):.0f} m from the chain "
                    f"{'after' if g_after <= g_before else 'before'} it"
                    + (f"; the draft joins them contiguously as edge_ids {sug}" if sug else
                       "; no contiguous run of built edges joins them in this draft"))
    raise RefusedError(f"{ref!r} {direction} is not contiguous in this draft: the longest chain is "
                       f"{[e.id for e in chain]} ({sum(e.length for e in chain):.0f} m) and " + "; ".join(msgs)
                       + ". Declare network.reference_line.edge_ids (every id a built edge of THIS draft, in driving "
                         "order) after reading data/network.geojson, or raise bridge_max_edges for a mislabelled "
                         "non-ramp piece.")


def _check_explicit(ids: list, by_id: dict, max_turn: float) -> list[_Edge]:
    chain = []
    for i in ids:
        if i not in by_id:
            raise RefusedError(f"edge_ids names edge {i!r}, which this draft's network.geojson does not have "
                               f"(edge ids are this draft's: re-read data/network.geojson after every net step)")
        e = by_id[i]
        if e.travel == 0:
            raise RefusedError(f"edge {i} has no decided direction of travel (classify travel_votes "
                               f"{e.rec.get('travel_votes')}) — a line is driven in a direction")
        if e.trimmed:
            raise RefusedError(f"edge {i} was trimmed by the mesh (a ramp cut back at its merge): its swept line no "
                               f"longer reaches its node")
        chain.append(e)
    for e, f in zip(chain, chain[1:]):
        if e.head != f.tail:
            gap = math.dist(_xz(e.grade[-1]), _xz(f.grade[0]))
            raise RefusedError(f"edge_ids are not contiguous in this draft: edge {e.id} ends {gap:.1f} m from where "
                               f"edge {f.id} starts (driving order) — no line is drawn across a gap")
        if not _joint_ok(e, f, max_turn):
            raise RefusedError(f"edge {e.id} -> {f.id} turns {_turn_deg(e.last_dir(), f.first_dir()):.0f} deg at their "
                               f"joint (> {max_turn:.0f}): not a continuation")
    return chain


def _side_check(chain: list[_Edge], opposite: list[_Edge]) -> dict:
    """Where the opposite carriageway runs beside the line, which side is it on? (+ = left of travel)"""
    pts = [_xz(p) for e in chain for p in e.grade]
    opp = [(_xz(a), _xz(b)) for e in opposite for a, b in zip(e.grade, e.grade[1:])]
    left = right = 0
    if not opp:
        return {"samples": 0, "left": 0, "right": 0,
                "note": f"no opposite carriageway within {OPPOSITE_SEARCH_M:.0f} m: the right-hand cross-check could not run"}
    acc, last = 0.0, None
    for i in range(1, len(pts) - 1):
        acc += math.dist(pts[i], pts[i - 1])
        if last is not None and acc - last < SIDE_SAMPLE_M:
            continue
        last = acc
        px, pz = pts[i]
        tx, tz = _unit(pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1])
        best = None
        for (ax, az), (bx, bz) in opp:
            dx, dz = bx - ax, bz - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
            qx, qz = ax + t * dx, az + t * dz
            d = math.hypot(qx - px, qz - pz)
            if d <= OPPOSITE_SEARCH_M and (best is None or d < best[0]):
                best = (d, qx - px, qz - pz)
        if best is None:
            continue
        cross = tx * best[2] - tz * best[1]       # x = east, z = north: > 0 is counter-clockwise = left of travel
        if cross > 0:
            left += 1
        elif cross < 0:
            right += 1
    return {"samples": left + right, "left": left, "right": right}


def _spans(stations: list[float], lift: list[float]) -> list[list[float]]:
    out, a = [], None
    for s, h in zip(stations, lift):
        if h > DECK_SPAN_LIFT_M:
            if a is None:
                a = s
            b = s
        elif a is not None:
            out.append([round(a, 1), round(b, 1)])
            a = None
    if a is not None:
        out.append([round(a, 1), round(b, 1)])
    return out


def resolve(decl: dict, fc: dict, edges_rec: dict, *, snap_grid_m: float = 7.0) -> dict:
    """Pure resolution (no file I/O): the chain and the line for ``decl`` on this draft. Raises RefusedError."""
    if not isinstance(decl, dict):
        raise RefusedError("network.reference_line must be an object")
    lengths = {f["properties"]["id"]: float(f["properties"].get("length_m") or 0.0) for f in fc["features"]}
    recs = edges_rec.get("edges") or []
    if not recs:
        raise RefusedError("data/network.edges.local.json has no edges — run scripts.geometry.build_network_mesh "
                           "with network.reference_line declared")
    edges = [_Edge(r, lengths.get(r["id"], 0.0)) for r in recs if len(r.get("at_grade_xyz_m") or []) >= 2]
    tol = float(decl.get("join_tol_m") or snap_grid_m)
    max_turn = float(decl.get("max_joint_turn_deg") or MAX_JOINT_TURN_DEG)
    _nodes(edges, tol)
    by_id = {e.id: e for e in edges}
    ref = decl.get("ref")
    direction = decl.get("direction")
    if direction is not None and direction not in HEADINGS:
        raise RefusedError(f"direction {direction!r} is not one of {sorted(HEADINGS)}")
    hd = HEADINGS.get(direction) if direction else None
    ids = decl.get("edge_ids")
    max_b = int(decl.get("bridge_max_edges") or 0)
    if ids:
        chain = _check_explicit(list(ids), by_id, max_turn)
        how = "edge_ids (declared)"
        bridged = []
    else:
        if not ref or not hd:
            raise RefusedError("declare ref + direction (or edge_ids)")
        want = _norm_name(ref)

        def heading_ok(e):
            cx, cz = e.chord()
            return math.hypot(cx, cz) < 20.0 or cx * hd[0] + cz * hd[1] >= 0.0

        main = [e for e in edges if e.cls in FREEWAY_CLS and not e.is_ramp and not e.trimmed]
        named = [e for e in main if _norm_name(e.name) & want]
        undecided = [e.id for e in named if e.travel == 0]
        cands = [e for e in named if e.travel != 0 and heading_ok(e)]
        if not cands:
            raise RefusedError(f"no non-ramp freeway edge named {ref!r} drives {direction} in this draft "
                               f"(named {len(named)}, undecided travel {undecided}); edge names: "
                               f"{sorted({str(e.name) for e in main})}")
        bridges = [e for e in main if e not in named and e.travel != 0 and heading_ok(e)] if max_b > 0 else []
        chain = _longest_chain(cands, bridges, max_b, max_turn)
        if not chain:
            raise RefusedError(f"no directed chain of {ref!r} {direction} edges could be formed")
        bridged = [e for e in chain if e in bridges]
        how = f"ref {ref!r} {direction}: the longest directed chain" + (f", {len(bridged)} bridging edge(s)" if bridged else "")
        _refuse_if_broken(chain, cands, edges, max_turn, ref, direction)
        # same-ref pieces TOUCHING the chain (a branch, a parallel collector, a stub): listed unjudged, not refused
        off = [e for e in cands if e not in chain]
        if off:
            how += f"; {len(off)} same-ref {direction} edge(s) branch off the chain (listed unjudged)"
    # the overall heading
    a, b = chain[0].grade[0], chain[-1].grade[-1]
    dx, dz = b[0] - a[0], b[2] - a[2]
    if hd is not None:
        L = math.hypot(dx, dz)
        ang = _turn_deg(_unit(dx, dz), hd) if L > 1e-6 else 180.0
        if ang > HEADING_TOL_DEG:
            raise RefusedError(f"the chain {[e.id for e in chain]} runs {ang:.0f} deg off {direction} overall "
                               f"(start {round(a[0])},{round(a[2])} -> end {round(b[0])},{round(b[2])})")
    # the right-hand cross-check against the opposite carriageway
    on = {e.id for e in chain}
    names = set().union(*[_norm_name(e.name) for e in chain]) if any(e.name for e in chain) else set()
    opp_pool = [e for e in edges if e.id not in on and e.cls in FREEWAY_CLS and not e.is_ramp and e.travel != 0
                and (not names or _norm_name(e.name) & names)]
    opposite = []
    for e in opp_pool:
        cx, cz = e.chord()
        if math.hypot(cx, cz) >= 20.0 and cx * dx + cz * dz < 0.0:
            opposite.append(e)
    side = _side_check(chain, opposite)
    if side["samples"] and side["right"] > side["left"]:
        raise RefusedError(f"the opposite carriageway lies on the RIGHT of the line at {side['right']} of "
                           f"{side['samples']} samples — in right-hand traffic it is on the left: the travel "
                           f"direction (classify travel_dir) contradicts the geometry")
    # the line: every point a vertex of a built edge
    surf, grade, widths, src, joints = [], [], [], [], []
    for k, e in enumerate(chain):
        s_, g_, w_, ix = e.surf, e.grade, e.widths, e.rec["_idx"]
        start = 0
        if k:
            gap = math.dist(_xz(grade[-1]), _xz(g_[0]))
            joints.append({"from": chain[k - 1].id, "to": e.id, "gap_m": round(gap, 3)})
            if gap < 1e-6:
                start = 1                                   # the shared vertex, written once
        for i in range(start, len(g_)):
            surf.append(list(s_[i]))
            grade.append(list(g_[i]))
            widths.append(float(w_[i]))
            src.append([e.id, ix[i]])
    st = [0.0]
    for i in range(1, len(grade)):
        st.append(st[-1] + math.dist(_xz(grade[i - 1]), _xz(grade[i])))
    lift_m = float(edges_rec.get("road_lift_m") or 0.0)
    lift = [s_[1] - lift_m - g_[1] for s_, g_ in zip(surf, grade)]
    unjudged = []
    for e in sorted(edges, key=lambda q: q.id):
        if e.id in on:
            continue
        if e.is_ramp:
            why = "ramp / interchange connector"
        elif e in opposite:
            why = "the other carriageway"
        elif _norm_name(e.name) & names:
            why = "same road, not on the chain (a parallel or off-direction piece)"
        else:
            why = "another mainline"
        unjudged.append({"id": e.id, "name": e.name, "road_class": e.cls, "is_ramp": e.is_ramp,
                         "length_m": round(e.length, 1), "why": why})
    return {"how": how, "chain": [e.id for e in chain],
            "bridged": [{"id": e.id, "name": e.name, "length_m": round(e.length, 1)} for e in bridged],
            "joints": joints, "side_check": side, "surface": surf, "grade": grade, "widths": widths,
            "source_by_vertex": src, "stations": st, "lift": lift, "spans": _spans(st, lift),
            "unjudged": unjudged, "built_km": round(sum(e.length for e in edges) / 1000.0, 3),
            "judged_km": round(st[-1] / 1000.0, 3), "join_tol_m": tol, "max_joint_turn_deg": max_turn}


def build(project_dir: str | Path) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    net = cfg.get("network") or {}
    decl = net.get("reference_line")
    if not decl:
        raise RefusedError("track.config.json declares no network.reference_line — this step has nothing to resolve")
    if bool(cfg.get("loop", True)):
        raise RefusedError("loop is true: a reference line along one carriageway of a network is a point-to-point "
                           "road (fleet/LAWS.md L11) — set loop false")
    if len(cfg.get("layouts") or []) > 1:
        raise RefusedError("more than one layout: a multi-layout network's spawns ride per layout "
                           "(build_network_mesh layouts[].spawn) — this step writes a single layout's grid")
    # this step's own outputs go first: a refusal must leave NO line behind (an earlier run's would be walked against
    # this draft). dummies.json stays the mesh's until replaced; the prep stops without centerline.local.json anyway.
    for stale in OUTPUTS:
        (data / stale).unlink(missing_ok=True)
    fc = json.loads((data / "network.geojson").read_text(encoding="utf-8"))
    ep = data / "network.edges.local.json"
    if not ep.exists():
        raise RefusedError("no data/network.edges.local.json — run scripts.geometry.build_network_mesh first (it "
                           "records every swept edge line when network.reference_line is declared)")
    erec = json.loads(ep.read_text(encoding="utf-8"))
    r = resolve(decl, fc, erec, snap_grid_m=float(net.get("snap_grid_m", 7.0)))

    mirror_x = bool(erec.get("mirror_x", cfg.get("mirror_x", False)))
    sx = -1.0 if mirror_x else 1.0
    origin = erec["origin"]
    grade_local = [[round(sx * p[0], 2), round(p[1], 2), round(p[2], 2)] for p in r["grade"]]
    xs = [p[0] for p in grade_local]
    ys = [p[1] for p in grade_local]
    zs = [p[2] for p in grade_local]
    label = (f"{decl.get('ref')} {decl.get('direction')}" if not decl.get("edge_ids")
             else f"edge_ids {decl.get('edge_ids')}")
    (data / "centerline.local.json").write_text(json.dumps({
        "frame": "ENU local meters (X=east, Y=up, Z=north)",
        "origin": origin, "true_north_rotation_deg": float(cfg.get("true_north_rotation_deg") or 0.0),
        "extent_x_m": round(max(xs) - min(xs), 1), "extent_z_m": round(max(zs) - min(zs), 1),
        "height_m": round(max(ys) - min(ys), 1), "point_count": len(grade_local),
        "points_xyz_m": grade_local, "widths_m": [round(w, 2) for w in r["widths"]], "loop": False,
        "source": f"network reference line ({label}): the at-grade line under the network edges {r['chain']} "
                  f"(scripts.geometry.network_reference)",
        "source_by_vertex": r["source_by_vertex"]}), encoding="utf-8")
    (data / "finished_centerline.json").write_text(json.dumps({
        "frame": FRAME_MESH,
        "source": f"build_network_mesh's swept edges {r['chain']} in driving order ({label})",
        "points_xyz_m": [[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in r["surface"]],
        "widths_m": [round(w, 2) for w in r["widths"]]}), encoding="utf-8")
    (data / "bridge.spans.auto.json").write_text(json.dumps(r["spans"]), encoding="utf-8")

    from scripts.geometry import dummies as dmod
    surf = [tuple(p) for p in r["surface"]]
    placed = dmod.place_dummies(surf, r["widths"], n_sectors=3, n_pits=4, loop=False)
    dum = {k: [v[0], round(v[1] + SPAWN_CLEAR_M, 3), v[2]] for k, v in placed.items()}
    (data / "dummies.json").write_text(json.dumps(dum, indent=1), encoding="utf-8")

    rep = {"tool": "scripts/geometry/network_reference.py", "line": {
               "label": label, "how": r["how"], "edges": r["chain"], "bridged": r["bridged"], "joints": r["joints"],
               "max_joint_gap_m": max([j["gap_m"] for j in r["joints"]] or [0.0]),
               "points": len(r["surface"]), "length_km": r["judged_km"], "spans": r["spans"],
               "side_check": r["side_check"], "join_tol_m": r["join_tol_m"],
               "max_joint_turn_deg": r["max_joint_turn_deg"], "loop": False},
           "declared": decl, "built_km": r["built_km"], "judged_km": r["judged_km"],
           "unjudged_km": round(sum(u["length_m"] for u in r["unjudged"]) / 1000.0, 3),
           "unjudged_edges": len(r["unjudged"]), "unjudged": r["unjudged"],
           "_doc": "The ship phase walks ONE line: drive_test (10 wheel paths), write_ai_line and make_map's lap follow "
                   "it, verify_kn5's spawns sit on it. Every edge listed in 'unjudged' is BUILT (in track.obj and the "
                   "kn5) but no line-walking gate drives it; audit_mesh, verify_kn5's mesh checks and kn5_ground_check "
                   "read the whole mesh. A hole, named here, never hidden."}
    (data / "network.reference.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[network_reference] {label}: {r['how']}")
    print(f"[network_reference] line: edges {r['chain']}, {len(r['surface'])} vertices, {r['judged_km']:.2f} km "
          f"(joints {[j['gap_m'] for j in r['joints']]} m), {len(r['spans'])} deck span(s); side check {r['side_check']}")
    print(f"[network_reference] grid at the start, AC_TIME_0 at the finish (L11) -> data/dummies.json "
          f"({len(dum)} placements)")
    print(f"[network_reference] UNJUDGED by the line gates: {len(r['unjudged'])} built edge(s), "
          f"{rep['unjudged_km']:.2f} of {r['built_km']:.2f} km (data/network.reference.json)")
    return rep


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: python -m scripts.geometry.network_reference <project-dir>")
    build(args[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
