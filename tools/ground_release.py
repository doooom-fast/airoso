"""Release the near-road ground to the real earth where the real earth is not a flat verge (ledger 0046, v0.18.0
integration fix round: the truth lens's criterion 4, the seven rims within 20 m of a pavement).

WHY. Since 0046 the ground within 20 m of a pavement has been the v0.17.1 graded surface, by design: the conform
corridor, the seat and the kn5 prep's contact band + feather shape it into a road-height verge, and every drive gate
was tuned on it. That is right on a street whose verge IS flat. It is wrong at four places on the loop, measured on
fresh 3DEP 1 m (2026-10-13), and criterion 4 fails at each:
  * Alvarado Road's south side, s ~1620-1995: the Alvarado Creek channel and its bank drop 2-8 m within 2-20 m of the
    kerb (a rising bank at s 1625-1705); the build had a flat shelf at road height to ~20 m;
  * College Ave's south approach to I-8, s ~2545-2600: the real road rides an earth embankment to its abutment (s 2586);
    the declared bridge span starts ~30 m early, so the ground under the approach was left 6 m under the road (sky
    under the road from the side);
  * Lake Murray Blvd over Alvarado Creek, s ~13420-13470: a bridge over a channel 8 m under the road; the build had solid
    road-height fill.
A zone in track.config.json terrain.ground_release names each one (loop stations, the side(s), how far out). Inside it
the ground is the bare-earth 3DEP surface: beside the road everywhere, and under the deck too on a "span" zone (never
above the deck: min(3DEP, deck - 0.02)). The zone reaches past the kept cells' refinement band (20 + 16 m) so the
prep's kept-cell refinement, which it then leaves alone, meets it on the same data.

THIS STEP (python, draft stage, after the mouths are welded): resolves the zones on data/centerline.local.json,
plans a CELL_M lattice over them, reads 3DEP at every node (cached in data/ground_release.samples.json.gz with
provenance; missing nodes fetched, TLS verified, no gap filling) and writes data/ground_release.json — the lattice
heights and the resolved zones. tools/ground_release_blend.py applies it to loop.blend's TERRAIN (and guards every
new drop within reach of a car with a rail); the kn5 prep (build_kn5_loop) reads the same file so its contact
feather and its kept-cell refinement leave the released ground alone.

AUTO CUTS (ledger 0054 P3 repair round 1, the truth lens; Kevin 2026-10-13: "Why are we changing ridges?"). The six cut
zones P2 found (50 m or more of a 3 m wall planed) were too few and too short: the real walls beside the four north
roads run past their ends and stand at ten more places 20-50 m long (97 of 249 stations with a 3 m+ wall kept less
than half of it), and the 45 deg batter held a rock face that rises ~1.5 m per metre to half its height. With
terrain.ground_release.auto_cuts declared, this step probes 3DEP beside every north piece (every probe_step_m, each
side, from the curb out — on this lattice's own nodes, so the probes are the lattice's first samples) and declares a
cut zone over every stretch where the real ground stands min_rise_m or more over the road (padded, merged): a bank
zone on the piece's line, rails false (a cut makes no drop), RAISE-ONLY (the ground beside the road rises to the real
earth where the real earth stands over the built ground, and is never lowered: no fill side changes, so no new drop),
its batter the steepest the real face itself climbs there (the p90 of its probe-to-probe rise), held to
docs/ROAD-CONSTRUCTION.md's range (common earth 1:1 .. fractured rock 0.5:1, i.e. 1-2 m per metre). Each zone records
what it measured; data/ground_release.auto_cuts.json lists every probe station read.

    python tools/ground_release.py <project-dir> [--offline]
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

CELL_M = 2.0        # [invented] lattice spacing of the released ground (the creek channel is ~7-16 m wide)
RAMP_M = 4.0        # [invented] blend from the released ground back to the built ground at a zone's ends and outer edge
INNER_M = 0.5       # a zone starts this far inside the nominal pavement edge (vertices under the pavement are skipped
#                     or capped by the deck anyway; this only closes the seam at the kerb)
LOCATE_M = 80.0     # a point farther than this from every centreline vertex is in no zone


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# --- v0.18.0 integration fix round 4 (the gates + view lenses), pure so the tests run them --------------------------
STRAIGHT_BANK_MIN_M = 1.0   # [invented] two pavements this much apart in height, too close for both batters, get the
#                             straight bank between their edges (below it the cut wins, as before)
RAIL_HOLD_M = 1.0           # [invented] a rail stands full height at least this far past its last station over a drop
RAIL_TAPER_MIN_M = 0.5      # [invented] a sloped end shorter than this is not built: the end stays square (full height)
ROUND_MAX_M = 5.0           # a zone's round_m (the cut top's rounding) is at most this: docs/ROAD-CONSTRUCTION.md's 2-5 m


def round_k(round_m: float, cut_slope: float) -> float:
    """the smooth-minimum width (a HEIGHT) that rounds a cut top over ``round_m`` metres of plan: against level ground
    the rounding spans |cut - ground| < k, i.e. k / cut_slope metres either side of the crease"""
    return max(0.0, 0.5 * float(round_m) * float(cut_slope))


def smin(a: float, b: float, k: float) -> float:
    """polynomial smooth minimum: min(a, b) away from the crease, rounded where |a - b| < k (at most k / 4 under it)"""
    if k <= 0.0:
        return min(a, b)
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def batter_z(z: float, cut: tuple | None, fill: tuple | None, round_k: float = 0.0) -> float:
    """The released height of a vertex beside the pavement (ground_release_blend step 2b). cut = (limit, h_c, d_c): the
    lowest 'no higher than' bound (an earth cut rising from a pavement face at h_c, d_c away); fill = (limit, h_f, d_f):
    the highest 'no lower than' bound (a fill falling from a grounded pavement face at h_f). Normally the fill lifts and
    the cut wins. Where they conflict (fill limit over cut limit) between two pavements more than STRAIGHT_BANK_MIN_M
    apart in height — College Ave's south approach 5-6 m over Alvarado Rd with 2-3 m of ground between their sidewalks
    (v0.18.0, the view lens's stepped curtain) — neither bank fits: the ground is the straight bank between the two
    edges, so no cliff stands on either side.
    round_k (ledger 0055, a zone's round_m): the cut's TOP EDGE — where the cut plane meets the real ground — is rounded
    into it (docs/ROAD-CONSTRUCTION.md: "Round the cut top into natural ground over 2-5 m") by a smooth minimum of the
    ground and the cut limit, never above either; where the fill lifts or the straight bank holds, nothing changes."""
    nz = z
    if fill is not None and nz < fill[0]:
        nz = fill[0]
    if cut is not None and nz > cut[0] - round_k:
        if fill is not None and fill[0] > cut[0] and fill[1] - cut[1] > STRAIGHT_BANK_MIN_M:
            if nz > cut[0]:
                lim_c, h_c, d_c = cut
                lim_f, h_f, d_f = fill
                t = d_c / max(1e-9, d_c + d_f)
                return h_c + (h_f - h_c) * t
            return nz
        if round_k > 0.0 and (fill is None or nz > fill[0]):
            nz = max(smin(nz, cut[0], round_k), fill[0] if fill is not None else -1e9)
        else:
            nz = min(nz, cut[0])
    return nz


def rail_heights(ss: list, need: list, taper: float, hold: float = RAIL_HOLD_M,
                 min_taper: float = RAIL_TAPER_MIN_M) -> list:
    """Per rail row, the fraction of the full barrier height (1 = full). A rail stands full height over every station
    that needs it and for `hold` past the first / last one; a sloped end (to 0, scaled by the caller to its end height)
    is built only over the padding beyond that, at most `taper` long, and not at all when less than `min_taper` is left
    (v0.18.0, the gates lens: ends sloped to 5 cm over live drops where a run's padding was clipped by a zone or a
    block end — College Ave's approach foot, s 2500-2502, 4.9 m down). A piece with no station that needs it (a split
    piece of padding) slopes at both ends over at most half its length."""
    n = len(ss)
    if n == 0:
        return []
    idx = [k for k in range(n) if need[k]]
    if idx:
        t0 = min(taper, ss[idx[0]] - ss[0] - hold)
        t1 = min(taper, ss[-1] - ss[idx[-1]] - hold)
    else:
        t0 = t1 = min(taper, 0.5 * (ss[-1] - ss[0]))
    t0 = t0 if t0 >= min_taper else 0.0
    t1 = t1 if t1 >= min_taper else 0.0
    out = []
    for k in range(n):
        h = 1.0
        if t0 > 0.0:
            h = min(h, (ss[k] - ss[0]) / t0)
        if t1 > 0.0:
            h = min(h, (ss[-1] - ss[k]) / t1)
        out.append(max(0.0, min(1.0, h)))
    return out


class Zones:
    """Pure (no bpy): which points lie in a declared release zone, and how strongly. Local frame (x = E, z = N); the
    loop's centreline vertices ``pts`` (x, y, z) with ``widths``; a zone = {name, kind: bank|span, s_m: [a, b],
    sides: [+1 (left of travel) / -1 (right)], reach_m}. Left of travel = (-tz, tx)."""

    def __init__(self, pts, widths, zones, cell=20.0):
        # ledger 0054 P3: a zone resolved on a CONNECTOR line (its record carries line / line_xz / line_w, see
        # resolve_line_zones) is judged on that line by its own Zones; self.zones stays index-aligned with `zones`
        groups, main_idx = {}, []
        for i, z in enumerate(zones):
            if z.get("line_xz"):
                groups.setdefault(z["line"], []).append(i)
            else:
                main_idx.append(i)
        self._subs = []
        aligned = [None] * len(zones)
        for _line, idx in groups.items():
            z0 = zones[idx[0]]
            sub = Zones([(x, 0.0, zz) for x, zz in z0["line_xz"]], z0["line_w"],
                        [{k: v for k, v in zones[i].items() if k not in ("line_xz", "line_w")} for i in idx], cell)
            self._subs.append(sub)
            for i, zz in zip(idx, sub.zones):
                aligned[i] = zz
        zones = [zones[i] for i in main_idx]
        n = len(pts)
        self.closed = n > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][2] - pts[-1][2]) < 1e-6
        self.P = [(p[0], p[2]) for p in pts]
        self.W = list(widths)
        self.s = [0.0]
        for a, b in zip(self.P, self.P[1:]):
            self.s.append(self.s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.T = []
        for i in range(n):
            a = self.P[max(0, i - 1)]
            b = self.P[min(n - 1, i + 1)]
            if self.closed and i == 0:
                a = self.P[n - 2]
            if self.closed and i == n - 1:
                b = self.P[1]
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            self.T.append(((b[0] - a[0]) / L, (b[1] - a[1]) / L))
        self.zones = [dict(z, a=float(z["s_m"][0]), b=float(z["s_m"][1]),
                           sides=[int(s) for s in z["sides"]], reach=float(z["reach_m"])) for z in zones]
        # an end that lies inside another zone on the same side does not ramp there (v0.18.0, the view lens: two zones
        # that overlap or abut — Lake Murray Blvd's I-8 span and creek at s 13428, College's approach foot / south
        # approach / I-8 span — each ramped to nothing at the shared station, a dip back to the built ground between
        # two released pieces)
        for zz in self.zones:
            zz["open_a"] = {sd for sd in zz["sides"] if any(o is not zz and sd in o["sides"] and o["a"] < zz["a"] <= o["b"] + 1e-6
                                                         for o in self.zones)}
            zz["open_b"] = {sd for sd in zz["sides"] if any(o is not zz and sd in o["sides"] and o["a"] - 1e-6 <= zz["b"] < o["b"]
                                                         for o in self.zones)}
        # only vertices that can be in a zone are indexed
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = {}
        self.boxes = []
        for zz in self.zones:
            idx = [i for i in range(n) if zz["a"] <= self.s[i] <= zz["b"]]
            if idx:
                m = max(self.W[i] for i in idx) / 2.0 + zz["reach"] + RAMP_M
                self.boxes.append((min(self.P[i][0] for i in idx) - m, max(self.P[i][0] for i in idx) + m,
                                   min(self.P[i][1] for i in idx) - m, max(self.P[i][1] for i in idx) + m))
        for i, (x, z) in enumerate(self.P):
            if any(zz["a"] - LOCATE_M <= self.s[i] <= zz["b"] + LOCATE_M for zz in self.zones):
                self.grid.setdefault((int(x // cell), int(z // cell)), []).append(i)
        self.main_zones = self.zones
        for i, zz in zip(main_idx, self.main_zones):
            aligned[i] = zz
        self.zones = aligned

    def locate(self, x, z):
        """(i, s, lat): the nearest indexed centreline vertex, the station of the point projected on its tangent, and
        the signed lateral offset (+ = left of travel); None beyond LOCATE_M"""
        ci, cj = int(x // self.cell), int(z // self.cell)
        r = int(math.ceil(LOCATE_M / self.cell))
        best = None
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                for i in self.grid.get((ci + di, cj + dj), ()):
                    d2 = (self.P[i][0] - x) ** 2 + (self.P[i][1] - z) ** 2
                    if best is None or d2 < best[0]:
                        best = (d2, i)
        if best is None or best[0] > LOCATE_M * LOCATE_M:
            return None
        i = best[1]
        tx, tz = self.T[i]
        dx, dz = x - self.P[i][0], z - self.P[i][1]
        return i, self.s[i] + dx * tx + dz * tz, -dx * tz + dz * tx

    def weight(self, x, z):
        """(w, zone) — w in [0, 1] (1 inside, smoothstep to 0 over RAMP_M at the zone's ends and outer edge; no ramp at
        an end lying inside another zone on that side), the zone with the largest weight; (0.0, None) outside every zone"""
        rm = RAMP_M
        best_sub = (0.0, None)
        for sub in self._subs:
            w_ = sub.weight(x, z)
            if w_[0] > best_sub[0]:
                best_sub = w_
        if not any(b[0] <= x <= b[1] and b[2] <= z <= b[3] for b in self.boxes):
            return best_sub
        loc = self.locate(x, z)
        if loc is None:
            return best_sub
        i, s, lat = loc
        hw = self.W[i] / 2.0
        best = best_sub
        for zz in self.main_zones:
            if not (zz["a"] <= s <= zz["b"]):
                continue
            # a bank zone starts at the kerb seam; a span zone takes the ground under the whole deck as well
            inner = -1e-9 if zz["kind"] == "span" else hw - INNER_M
            for side in zz["sides"]:
                o = side * lat
                if inner <= o <= hw + zz["reach"]:
                    da = 1e9 if side in zz.get("open_a", ()) else s - zz["a"]
                    db = 1e9 if side in zz.get("open_b", ()) else zz["b"] - s
                    w = smoothstep(min(da, db) / rm) * smoothstep((hw + zz["reach"] - o) / rm)
                    if w > best[0]:
                        best = (w, zz)
        return best

    def contains(self, x, z):
        return self.weight(x, z)[0] > 0.0


class Lattice:
    """Pure: the released ground's CELL_M lattice (local y per node); bilinear inside a cell whose four corners exist"""

    def __init__(self, cell, I, J, h):
        self.cell = float(cell)
        self.h = {(i, j): v for i, j, v in zip(I, J, h)}

    def at(self, x, z):
        fi, fj = x / self.cell, z / self.cell
        i, j = math.floor(fi), math.floor(fj)
        u, v = fi - i, fj - j
        try:
            a, b = self.h[(i, j)], self.h[(i + 1, j)]
            c, d = self.h[(i, j + 1)], self.h[(i + 1, j + 1)]
        except KeyError:
            return None
        return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def station_at_vertex(pts, v: float) -> float:
    """the station (plan metres from vertex 0) of a fractional centreline vertex v on the polyline pts"""
    n = len(pts)
    if not 0.0 <= v <= n - 1:
        raise SystemExit(f"[release] vertex {v} outside the centreline (0..{n - 1})")
    i = min(int(math.floor(v)), n - 2)
    s = 0.0
    for a, b in zip(pts[:i], pts[1:i + 1]):
        s += math.hypot(b[0] - a[0], b[2] - a[2])
    return s + (v - i) * math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][2] - pts[i][2])


def line_resolver(proj: Path):
    """ledger 0054 P3: resolve a zone declared on a north PIECE (zone keys line = the piece's connector name, piece,
    piece_s_m = [a, b] in the intermediate's station frame, sides relative to the piece's own J-order travel) onto the
    connector as data/connectors.local.json has it after trim: (line_xz, line_w, s_m on the connector's own arc, sides
    relative to the connector's direction). Returns a function zone -> that tuple."""
    data = proj / "data"
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    src = (((cfg.get("route") or {}).get("route_connectors") or {}).get("authored_routes") or {}).get("north")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import expansion_pieces as ep
    _doc, pieces = ep.load(proj / src)

    def resolve(z):
        pc = pieces[z["piece"]]
        cands = [c for c in conns if c["name"] == z["line"] or c["name"].startswith(z["line"] + "#")]
        a_, b_ = (float(v) for v in z["piece_s_m"])
        pa, pb = pc.point(a_), pc.point(b_)
        best = None
        for c in cands:
            P = [(q[0], q[2]) for q in c["points_xyz_m"]]
            arc = [0.0]
            for u, v in zip(P, P[1:]):
                arc.append(arc[-1] + math.hypot(v[0] - u[0], v[1] - u[1]))

            def proj_(pt):
                bb = None
                for i in range(len(P) - 1):
                    dx, dz = P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]
                    L2 = dx * dx + dz * dz
                    if L2 < 1e-12:
                        continue
                    t = max(0.0, min(1.0, ((pt[0] - P[i][0]) * dx + (pt[1] - P[i][1]) * dz) / L2))
                    d = math.hypot(pt[0] - P[i][0] - t * dx, pt[1] - P[i][1] - t * dz)
                    if bb is None or d < bb[0]:
                        bb = (d, arc[i] + t * (arc[i + 1] - arc[i]), (dx, dz))
                return bb
            ja, jb = proj_(pa), proj_(pb)
            if ja is None or jb is None:
                continue
            if best is None or ja[0] + jb[0] < best[0]:
                best = (ja[0] + jb[0], c, ja, jb, P)
        if best is None or best[0] > 20.0:
            raise SystemExit(f"[release] zone {z['name']}: no {z['line']} piece runs past piece {z['piece']} "
                             f"s {a_}-{b_}")
        _d, c, ja, jb, P = best
        t = pc.tangent((a_ + b_) / 2.0)
        dx, dz = ja[2]
        same = (t[0] * dx + t[1] * dz) >= 0
        sides = [s_ if same else -s_ for s_ in z["_sides_piece"]]
        s_m = sorted([round(ja[1], 3), round(jb[1], 3)])
        return [[round(x, 3), round(zz, 3)] for x, zz in P], [float(w) for w in c["widths_m"]], s_m, sides, c["name"]
    return resolve


def resolve_zones(cfg: dict, pts=None, lines=None, extra=None) -> list[dict]:
    """The declared zones with their stations on THIS centreline (pts = data/centerline.local.json points). A zone
    names its extent either by station (s_m) or by centreline VERTEX (v: [from, to], fractional) — ledger 0055 round 2:
    a station is a place only while every metre of road before it keeps its length; College's realignment shortened
    the lap 6.6 m and slid Lake Murray Blvd's I-8 span zone 6.6 m off its abutment (a 4.9 m unguarded drop at the deck
    edge, street drive_test). Vertices past a change stay where they are; a v zone resolves to s_m here."""
    gr = ((cfg.get("terrain") or {}).get("ground_release") or {})
    out = []
    for z in list(gr.get("zones") or []) + list(extra or []):
        sides = []
        for s in z["sides"]:
            sides.append(1 if str(s) in ("left", "1", "+1") else -1 if str(s) in ("right", "-1") else None)
        if None in sides or z.get("kind") not in ("bank", "span"):
            raise SystemExit(f"[release] zone {z.get('name')}: kind must be bank|span, sides left|right")
        line_rec = None
        if z.get("line"):
            # ledger 0054 P3: a zone on a north piece (the cut walls beside Jackson north and Mission Gorge)
            if lines is None:
                continue        # resolvable only against a project's connectors (run() passes line_resolver)
            if z.get("rails", True) or z.get("cut_reach_m") is None:
                raise SystemExit(f"[release] zone {z['name']}: a line zone must be a declared cut (cut_reach_m, rails "
                                 f"false) — the rail pass walks the mainline only")
            line_xz, line_w, s_m, lsides, cname = lines(dict(z, _sides_piece=sides))
            line_rec = {"line": z["line"], "line_xz": line_xz, "line_w": line_w, "connector": cname,
                        "piece": z["piece"], "piece_s_m": [float(v) for v in z["piece_s_m"]]}
            sides = lsides
            z = dict(z, s_m=s_m)
        elif ("v" in z) == ("s_m" in z):
            raise SystemExit(f"[release] zone {z.get('name')}: declare its extent by s_m OR by v (centreline vertices)")
        if "v" in z:
            if pts is None:
                raise SystemExit(f"[release] zone {z['name']}: a v zone needs the centreline to resolve its stations")
            va, vb = float(z["v"][0]), float(z["v"][1])
            if not va < vb:
                raise SystemExit(f"[release] zone {z['name']}: v {z['v']} must increase")
            s_m = [round(station_at_vertex(pts, va), 3), round(station_at_vertex(pts, vb), 3)]
        else:
            s_m = [float(v) for v in z["s_m"]]
        if line_rec is not None:
            s_m = [float(v) for v in z["s_m"]]
        rec = {"name": z["name"], "kind": z["kind"], "s_m": s_m, "sides": sides,
               "reach_m": float(z["reach_m"]), "why": z.get("why", ""), **(line_rec or {})}
        if "v" in z:
            rec["v"] = [float(z["v"][0]), float(z["v"][1])]
        # ledger 0055 (College Ave's cut face): a zone may carry its own cut reach (the batter's plan reach from the
        # pavement edge, ground_release_blend.BATTER_REACH_M otherwise) and a rounded cut top (round_m, the plan width
        # of the rounding where the cut plane meets the real ground). Neither may reach past the zone itself.
        if z.get("cut_reach_m") is not None:
            cr = float(z["cut_reach_m"])
            if not 0.0 < cr <= rec["reach_m"]:
                raise SystemExit(f"[release] zone {z['name']}: cut_reach_m {cr} must be in (0, reach_m {rec['reach_m']}]")
            rec["cut_reach_m"] = cr
        if z.get("round_m") is not None:
            rm = float(z["round_m"])
            if not 0.0 <= rm <= ROUND_MAX_M:
                raise SystemExit(f"[release] zone {z['name']}: round_m {rm} must be in [0, {ROUND_MAX_M}] "
                                 f"(docs/ROAD-CONSTRUCTION.md: round the cut top over 2-5 m)")
            rec["round_m"] = rm
        # a CUT zone (the ground beside the road rises: College's hillside, 0055) declares rails false — the release
        # makes no drop there to guard (drive_test's excursion rule then reads only the sidewalk's own outer apron,
        # the same on every street of the loop, and a rail station would stand a jersey barrier along the whole cut)
        if z.get("rails") is not None:
            if not isinstance(z["rails"], bool):
                raise SystemExit(f"[release] zone {z['name']}: rails must be true / false")
            if not z["rails"] and not rec.get("cut_reach_m"):
                raise SystemExit(f"[release] zone {z['name']}: rails false only on a declared cut zone (cut_reach_m)")
            rec["rails"] = bool(z["rails"])
        # repair round 1 (the auto cuts): a raise-only zone never lowers the ground; a zone's own batter (m per metre)
        if z.get("raise_only"):
            if not rec.get("cut_reach_m") or rec.get("rails", True):
                raise SystemExit(f"[release] zone {z['name']}: raise_only only on a declared cut (cut_reach_m, rails false)")
            rec["raise_only"] = True
        if z.get("cut_slope") is not None:
            cs = float(z["cut_slope"])
            if not 0.5 <= cs <= 2.0:
                raise SystemExit(f"[release] zone {z['name']}: cut_slope {cs} outside 0.5-2 m per metre "
                                 f"(docs/ROAD-CONSTRUCTION.md: loose soil 2:1 .. fractured rock 0.5:1)")
            rec["cut_slope"] = cs
        for k in ("auto", "measured"):
            if k in z:
                rec[k] = z[k]
        out.append(rec)
    return out


# --- AUTO CUTS (ledger 0054 P3 repair round 1) --------------------------------------------------------------------
AUTO_DEFAULTS = {
    "probe_step_m": 5.0,        # [invented] a probe station every this along each piece
    "probe_from_curb_m": 1.0,   # [invented] the first probe this far past the curb line...
    "probe_to_curb_m": 29.0,    # ...the last this far (the conform corridor's 20 m + most of its blend)
    "probe_every_m": 1.0,       # half CELL_M: every lattice node across is met (the probe IS the node, deduped)
    "min_rise_m": 1.0,          # [invented] a real face this much over the road at a station = a cut there
    "merge_gap_m": 20.0,        # [invented] cut stations this close along the road join one stretch
    "pad_m": 15.0,              # [invented] a stretch runs on this far past its first / last cut station
    "min_len_m": 10.0,          # [invented] a stretch shorter than this (before padding) is a bump, not a wall
    "reach_m": 40.0, "cut_reach_m": 20.0, "round_m": 3.0,     # the parameters of College's cut face (0055)
    "cut_slope_min": 1.0,       # docs/ROAD-CONSTRUCTION.md: common earth 1:1 ...
    "cut_slope_max": 2.0,       # ... fractured rock 0.5:1 (m per metre)
    "batter_window_m": 50.0,    # [invented] the real face's climb is read per this much of a stretch
    "batter_step": 0.25,        # [invented] ...rounded to this (m per metre): neighbouring windows alike join
    "batter": "max",            # the zone's batter: "max" = cut_slope_max everywhere (the face read for the record only),
    #                             "face" = each window's own p90 climb, held to the range. Repair round 1's first full
    #                             rehearsal ran "face": Mission Gorge's south wall then stood its full real height from
    #                             22 m out but 1.1-1.9 m short at 18-20 m — the built walk + apron (2.8 m) covers the real
    #                             wall's toe, so a batter as gentle as the face itself starts it 2-3 m late. The batter is a
    #                             bound, never a target (the ground is 3DEP wherever 3DEP stands under it): the steepest the
    #                             construction range allows (fractured rock 0.5:1) binds only where the built pavement
    #                             overlaps the real wall
}


def auto_params(ac: dict) -> dict:
    out = dict(AUTO_DEFAULTS)
    out.update({k: v for k, v in (ac or {}).items() if not k.startswith("_") and k != "pieces"})
    return out


def probe_points(pieces: dict, ac: dict, cell=CELL_M):
    """[(piece, s, side +1 left / -1 right of the piece's own travel, out_m past the curb, lattice key)] for every probe
    of every auto-cut piece, inside the piece's two cuts"""
    prm = auto_params(ac)
    out = []
    for pid in ac.get("pieces") or []:
        pc = pieces[pid]
        s0 = float((pc.cuts.get("start") or {}).get("s", 0.0))
        s1 = float((pc.cuts.get("end") or {}).get("s", pc.length))
        s = s0
        while s <= s1 + 1e-9:
            (x0, z0), _t, (nx, nz) = pc.frame(s)
            L, R = pc.curbs(s)
            for side, curb in ((1, L), (-1, R)):
                o = prm["probe_from_curb_m"]
                seen = set()
                while o <= prm["probe_to_curb_m"] + 1e-9:
                    lat = curb + side * o
                    x, z = x0 + nx * lat, z0 + nz * lat
                    key = (int(round(x / cell)), int(round(z / cell)))
                    if key not in seen:
                        seen.add(key)
                        # the probe IS the lattice node: its own distance past the curb (the face's climb is read on it)
                        ok = side * ((key[0] * cell - x0) * nx + (key[1] * cell - z0) * nz - curb)
                        out.append((pid, round(s, 3), side, round(ok, 3), key))
                    o += prm["probe_every_m"]
            s += prm["probe_step_m"]
    return out


def detect_cuts(pieces: dict, ac: dict, probes, height):
    """the auto-cut zones (declarations in the config's own form) and the per-station record. height(key) = 3DEP
    local y at a lattice node. The road's height at a station is the piece's own 3DEP profile (Piece.y_fit, the line
    the built deck follows within centimetres); a station is a CUT on a side where the real ground at any of its probes
    stands min_rise_m or more over it"""
    prm = auto_params(ac)
    rows = {}
    for pid, s, side, o, key in probes:
        rows.setdefault((pid, side, s), []).append((o, height(key)))
    stations = []
    by = {}
    for (pid, side, s), L in sorted(rows.items()):
        road = pieces[pid].y_fit(s)
        L.sort()
        rises = [h - road for _o, h in L]
        top = max(rises)
        # the face's own steepness: the steepest rise between neighbouring probes (only where it climbs)
        steep = max([(b - a) / (ob - oa) for (oa, a), (ob, b) in zip(L, L[1:]) if ob - oa >= 0.5 * CELL_M] + [0.0])
        cut = top >= prm["min_rise_m"]
        stations.append({"piece": pid, "side": side, "s": s, "max_rise_m": round(top, 2),
                         "steepest_m_per_m": round(steep, 2), "cut": cut})
        by.setdefault((pid, side), []).append(stations[-1])
    zones = []
    for (pid, side), st in sorted(by.items()):
        pc = pieces[pid]
        s_lo = float((pc.cuts.get("start") or {}).get("s", 0.0))
        s_hi = float((pc.cuts.get("end") or {}).get("s", pc.length))
        runs = []
        for r in st:
            if not r["cut"]:
                continue
            if runs and r["s"] - runs[-1][-1]["s"] <= prm["merge_gap_m"] + 1e-9:
                runs[-1].append(r)
            else:
                runs.append([r])
        for run in runs:
            a, b = run[0]["s"], run[-1]["s"]
            if b - a < prm["min_len_m"]:
                continue
            a2, b2 = max(s_lo, a - prm["pad_m"]), min(s_hi, b + prm["pad_m"])
            top = max(r["max_rise_m"] for r in run)
            # the batter follows the face along the stretch: per BATTER_WINDOW_M window the p90 of its stations' climb,
            # held to the construction range and rounded to BATTER_STEP; equal neighbours join. The pieces abut (no
            # ramp between them: ground_release.Zones open ends); only the stretch's own two ends are padded and ramped
            wins = []
            for r in run:
                k = int((r["s"] - a) // prm["batter_window_m"])
                if not wins or wins[-1][0] != k:
                    wins.append([k, []])
                wins[-1][1].append(r)
            parts = []
            for k, rs in wins:
                st_ = sorted(r["steepest_m_per_m"] for r in rs)
                p90 = st_[min(len(st_) - 1, int(0.9 * len(st_)))]
                sl = max(prm["cut_slope_min"], min(prm["cut_slope_max"], p90))
                sl = round(round(sl / prm["batter_step"]) * prm["batter_step"], 2)
                if prm["batter"] == "max":
                    sl = float(prm["cut_slope_max"])
                if parts and parts[-1]["slope"] == sl:
                    parts[-1]["rs"] += rs
                    parts[-1]["p90"] = max(parts[-1]["p90"], p90)
                else:
                    parts.append({"slope": sl, "rs": list(rs), "p90": p90})
            for j, pt in enumerate(parts):
                pa = a2 if j == 0 else (parts[j - 1]["rs"][-1]["s"] + pt["rs"][0]["s"]) / 2.0
                pb = b2 if j == len(parts) - 1 else (pt["rs"][-1]["s"] + parts[j + 1]["rs"][0]["s"]) / 2.0
                ptop = max(r["max_rise_m"] for r in pt["rs"])
                sd = "left" if side > 0 else "right"
                zones.append({
                    "name": f"auto_cut_{pid}_{sd}_{int(round(pa))}_{int(round(pb))}",
                    "kind": "bank", "line": PIECE_LINES[pid], "piece": pid, "piece_s_m": [round(pa, 1), round(pb, 1)],
                    "sides": [sd], "reach_m": prm["reach_m"], "cut_reach_m": prm["cut_reach_m"], "round_m": prm["round_m"],
                    "rails": False, "raise_only": True, "cut_slope": pt["slope"], "auto": True,
                    "measured": {"stretch_cut_s_m": [a, b], "stretch_max_rise_m": top, "cut_s_m": [pt["rs"][0]["s"],
                                 pt["rs"][-1]["s"]], "stations": len(pt["rs"]), "max_rise_m": ptop,
                                 "face_p90_m_per_m": round(pt["p90"], 2)},
                    "why": f"ledger 0054 P3 repair round 1 (auto cut): fresh 3DEP stands up to {ptop:.1f} m over the road "
                           f"{prm['probe_from_curb_m']:.0f}-{prm['probe_to_curb_m']:.0f} m past the {sd} curb, piece s "
                           f"{pt['rs'][0]['s']:.0f}-{pt['rs'][-1]['s']:.0f} (a stretch of s {a:.0f}-{b:.0f}, up to "
                           f"{top:.1f} m); the real face climbs {pt['p90']:.2f} m per metre (p90); batter "
                           f"{pt['slope']} ({'the construction maximum, a bound only' if prm['batter'] == 'max' else 'the face own'}"
                           f", docs/ROAD-CONSTRUCTION.md 1-2)"})
    return zones, stations


PIECE_LINES = {"A": "north_J1_waring", "B": "north_princess_view", "C": "north_mission_gorge",
               "D": "north_J5_jackson_north"}    # tools/expansion_pieces.PIECE_CONN (no import: this module stays pure)


def plan_nodes(Z: Zones, cell=CELL_M):
    """every lattice node within one cell of a point in a zone (scan of the zones' bounding boxes); a zone on a
    connector line is scanned on its line's own Zones (ledger 0054 P3)"""
    nodes = set()
    for sub in Z._subs:
        nodes.update(plan_nodes(sub, cell))
    for zz in Z.main_zones:
        idx = [i for i in range(len(Z.P)) if zz["a"] - RAMP_M <= Z.s[i] <= zz["b"] + RAMP_M]
        if not idx:
            continue
        span = max(Z.W[i] for i in idx) / 2.0 + zz["reach"] + 2 * cell
        xs = [Z.P[i][0] for i in idx]
        zs = [Z.P[i][1] for i in idx]
        i0, i1 = math.floor((min(xs) - span) / cell), math.ceil((max(xs) + span) / cell)
        j0, j1 = math.floor((min(zs) - span) / cell), math.ceil((max(zs) + span) / cell)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                if Z.weight(i * cell, j * cell)[1] is zz:
                    # the node and its 8 neighbours: every cell touching the zone has all four corners
                    for di in (-1, 0, 1):
                        for dj in (-1, 0, 1):
                            nodes.add((i + di, j + dj))
    return sorted(nodes)


def _load_cache(cache_p: Path, o: dict, sx: float):
    cache: dict[tuple[int, int], float] = {}
    prov = {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
            "units": "metres above NAVD88", "cell_m": CELL_M, "origin": {"lon": o["lon"], "lat": o["lat"]},
            "projection": "key (I, J) -> local x = I*cell_m, z = J*cell_m; lon = lon0 + x / m_lon (x mirrored when "
                          "mirror_x), lat = lat0 + z / m_lat (terrain_tiers.meters_per_degree(lat0))",
            "mirror_x": sx < 0, "fetches": []}
    if cache_p.exists():
        d = json.loads(gzip.decompress(cache_p.read_bytes()).decode("utf-8"))
        p = d["_provenance"]
        if (abs(p["origin"]["lon"] - o["lon"]) > 1e-12 or abs(p["origin"]["lat"] - o["lat"]) > 1e-12
                or float(p["cell_m"]) != CELL_M or bool(p.get("mirror_x")) != (sx < 0)):
            raise SystemExit(f"[release] {cache_p.name}: origin / cell changed since it was cached — move it aside on "
                             f"purpose to re-sample")
        prov = p
        cache = {(i, j): c / 100.0 for i, j, c in zip(d["I"], d["J"], d["h_cm"])}
    return cache, prov


def _fetch(cache, prov, need, o, sx, what, offline):
    if not need:
        return 0
    if offline:
        raise SystemExit(f"[release] {len(need)} 3DEP nodes not cached and --offline ({what})")
    from scripts.geometry import terrain_tiers as tt
    from scripts.elevation import terrain_sample as ts_mod
    m_lon, m_lat = tt.meters_per_degree(o["lat"])
    ll = [(o["lon"] + sx * i * CELL_M / m_lon, o["lat"] + j * CELL_M / m_lat) for i, j in need]
    vals = ts_mod.sample_lonlat(ll, "ground release")
    for k, v in zip(need, vals):
        cache[k] = v
    prov["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "points": len(need),
                            "what": what})
    return len(need)


def _save_cache(cache_p, cache, prov):
    ks = sorted(cache)
    cache_p.write_bytes(gzip.compress(json.dumps(
        {"_provenance": prov, "I": [k[0] for k in ks], "J": [k[1] for k in ks],
         "h_cm": [int(round(cache[k] * 100)) for k in ks]}, separators=(",", ":")).encode("utf-8"), 9, mtime=0))


def run(proj: Path, offline: bool = False) -> dict | None:
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    grc = (cfg.get("terrain") or {}).get("ground_release") or {}
    ac = grc.get("auto_cuts")
    o = cl["origin"]
    elev0 = float(o["elev_m"])
    sx = -1.0 if cfg.get("mirror_x") else 1.0
    cache_p = data / "ground_release.samples.json.gz"
    cache, prov = _load_cache(cache_p, o, sx)
    n_fetched = 0
    auto, auto_st = [], []
    if ac:
        src = (((cfg.get("route") or {}).get("route_connectors") or {}).get("authored_routes") or {}).get("north")
        if not src:
            raise SystemExit("[release] auto_cuts declared but no route_connectors.authored_routes.north")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import expansion_pieces as ep
        _doc, pieces = ep.load(proj / src)
        probes = probe_points(pieces, ac)
        need = sorted({k for *_r, k in probes if k not in cache})
        n_fetched += _fetch(cache, prov, need, o, sx, "auto-cut probes beside the north pieces", offline)
        if need:
            _save_cache(cache_p, cache, prov)
        auto, auto_st = detect_cuts(pieces, ac, probes, lambda k: cache[k] - elev0)
        (data / "ground_release.auto_cuts.json").write_text(json.dumps(
            {"_doc": "tools/ground_release.py AUTO CUTS (ledger 0054 P3 repair round 1): every probe station beside the "
                     "north pieces (max rise of fresh 3DEP over the road past the curb, the steepest probe-to-probe "
                     "climb) and the cut zones declared from them",
             "params": auto_params(ac), "zones": auto, "stations": auto_st}, separators=(",", ":")), encoding="utf-8")
        print(f"[release] auto cuts: {len(probes)} probes ({len(need)} fetched), "
              f"{sum(1 for r in auto_st if r['cut'])} of {len(auto_st)} station-sides cut -> {len(auto)} zone(s): "
              + ", ".join(f"{z['piece']} {z['sides'][0]} {z['piece_s_m'][0]:.0f}-{z['piece_s_m'][1]:.0f} "
                          f"(<= {z['measured']['max_rise_m']:.1f} m, batter {z['cut_slope']})" for z in auto))
    lines = line_resolver(proj) if any(z.get("line") for z in list(grc.get("zones") or []) + auto) else None
    zones = resolve_zones(cfg, pts, lines, extra=auto)
    out_p = data / "ground_release.json"
    if not zones:
        if out_p.exists():
            out_p.unlink()
        print("[release] no terrain.ground_release.zones declared — nothing to do")
        return None
    Z = Zones(pts, cl["widths_m"], zones)
    nodes = plan_nodes(Z)
    need = [k for k in nodes if k not in cache]
    n_fetched += _fetch(cache, prov, need, o, sx, "ground release zones: " + ", ".join(z["name"] for z in zones),
                        offline)
    if need:
        _save_cache(cache_p, cache, prov)
    rep = {"_doc": "tools/ground_release.py — the near-road ground released to 3DEP inside the declared zones (ledger "
                   "0046 v0.18.0 integration fix round). h = local y (3DEP - origin elev) at lattice nodes (I*cell, "
                   "J*cell); zones resolved on data/centerline.local.json (sides: +1 left of travel, -1 right)",
           "cell_m": CELL_M, "ramp_m": RAMP_M, "inner_m": INNER_M, "elev0": elev0, "zones": zones,
           "I": [k[0] for k in nodes], "J": [k[1] for k in nodes],
           "h": [round(cache[k] - elev0, 3) for k in nodes]}
    out_p.write_text(json.dumps(rep, separators=(",", ":")), encoding="utf-8")
    print(f"[release] {len(zones)} zone(s) ({', '.join(z['name'] for z in zones)}): {len(nodes)} lattice nodes at "
          f"{CELL_M} m ({n_fetched} fetched) -> data/ground_release.json")
    return rep


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python tools/ground_release.py <project-dir> [--offline]")
    run(Path(args[0]), offline="--offline" in sys.argv)


if __name__ == "__main__":
    main()
