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
        if not any(b[0] <= x <= b[1] and b[2] <= z <= b[3] for b in self.boxes):
            return 0.0, None
        loc = self.locate(x, z)
        if loc is None:
            return 0.0, None
        i, s, lat = loc
        hw = self.W[i] / 2.0
        best = (0.0, None)
        for zz in self.zones:
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


def resolve_zones(cfg: dict, pts=None) -> list[dict]:
    """The declared zones with their stations on THIS centreline (pts = data/centerline.local.json points). A zone
    names its extent either by station (s_m) or by centreline VERTEX (v: [from, to], fractional) — ledger 0055 round 2:
    a station is a place only while every metre of road before it keeps its length; College's realignment shortened
    the lap 6.6 m and slid Lake Murray Blvd's I-8 span zone 6.6 m off its abutment (a 4.9 m unguarded drop at the deck
    edge, street drive_test). Vertices past a change stay where they are; a v zone resolves to s_m here."""
    gr = ((cfg.get("terrain") or {}).get("ground_release") or {})
    out = []
    for z in gr.get("zones") or []:
        sides = []
        for s in z["sides"]:
            sides.append(1 if str(s) in ("left", "1", "+1") else -1 if str(s) in ("right", "-1") else None)
        if None in sides or z.get("kind") not in ("bank", "span"):
            raise SystemExit(f"[release] zone {z.get('name')}: kind must be bank|span, sides left|right")
        if ("v" in z) == ("s_m" in z):
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
        rec = {"name": z["name"], "kind": z["kind"], "s_m": s_m, "sides": sides,
               "reach_m": float(z["reach_m"]), "why": z.get("why", "")}
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
        out.append(rec)
    return out


def plan_nodes(Z: Zones, cell=CELL_M):
    """every lattice node within one cell of a point in a zone (scan of the zones' bounding boxes)"""
    nodes = set()
    for zz in Z.zones:
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


def run(proj: Path, offline: bool = False) -> dict | None:
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(p) for p in cl["points_xyz_m"]]
    zones = resolve_zones(cfg, pts)
    out_p = data / "ground_release.json"
    if not zones:
        if out_p.exists():
            out_p.unlink()
        print("[release] no terrain.ground_release.zones declared — nothing to do")
        return None
    o = cl["origin"]
    elev0 = float(o["elev_m"])
    Z = Zones(pts, cl["widths_m"], zones)
    nodes = plan_nodes(Z)
    from scripts.geometry import terrain_tiers as tt
    m_lon, m_lat = tt.meters_per_degree(o["lat"])
    sx = -1.0 if cfg.get("mirror_x") else 1.0
    cache_p = data / "ground_release.samples.json.gz"
    prov = {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
            "units": "metres above NAVD88", "cell_m": CELL_M, "origin": {"lon": o["lon"], "lat": o["lat"]},
            "projection": "key (I, J) -> local x = I*cell_m, z = J*cell_m; lon = lon0 + x / m_lon (x mirrored when "
                          "mirror_x), lat = lat0 + z / m_lat (terrain_tiers.meters_per_degree(lat0))",
            "mirror_x": sx < 0, "fetches": []}
    cache: dict[tuple[int, int], float] = {}
    if cache_p.exists():
        d = json.loads(gzip.decompress(cache_p.read_bytes()).decode("utf-8"))
        p = d["_provenance"]
        if (abs(p["origin"]["lon"] - o["lon"]) > 1e-12 or abs(p["origin"]["lat"] - o["lat"]) > 1e-12
                or float(p["cell_m"]) != CELL_M or bool(p.get("mirror_x")) != (sx < 0)):
            raise SystemExit(f"[release] {cache_p.name}: origin / cell changed since it was cached — move it aside on "
                             f"purpose to re-sample")
        prov = p
        cache = {(i, j): c / 100.0 for i, j, c in zip(d["I"], d["J"], d["h_cm"])}
    need = [k for k in nodes if k not in cache]
    if need:
        if offline:
            raise SystemExit(f"[release] {len(need)} 3DEP nodes not cached and --offline")
        from scripts.elevation import terrain_sample as ts_mod
        ll = [(o["lon"] + sx * i * CELL_M / m_lon, o["lat"] + j * CELL_M / m_lat) for i, j in need]
        vals = ts_mod.sample_lonlat(ll, "ground release")
        for k, v in zip(need, vals):
            cache[k] = v
        prov["fetches"].append({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "points": len(need),
                                "what": "ground release zones: " + ", ".join(z["name"] for z in zones)})
        ks = sorted(cache)
        cache_p.write_bytes(gzip.compress(json.dumps(
            {"_provenance": prov, "I": [k[0] for k in ks], "J": [k[1] for k in ks],
             "h_cm": [int(round(cache[k] * 100)) for k in ks]}, separators=(",", ":")).encode("utf-8"), 9, mtime=0))
    rep = {"_doc": "tools/ground_release.py — the near-road ground released to 3DEP inside the declared zones (ledger "
                   "0046 v0.18.0 integration fix round). h = local y (3DEP - origin elev) at lattice nodes (I*cell, "
                   "J*cell); zones resolved on data/centerline.local.json (sides: +1 left of travel, -1 right)",
           "cell_m": CELL_M, "ramp_m": RAMP_M, "inner_m": INNER_M, "elev0": elev0, "zones": zones,
           "I": [k[0] for k in nodes], "J": [k[1] for k in nodes],
           "h": [round(cache[k] - elev0, 3) for k in nodes]}
    out_p.write_text(json.dumps(rep, separators=(",", ":")), encoding="utf-8")
    print(f"[release] {len(zones)} zone(s) ({', '.join(z['name'] for z in zones)}): {len(nodes)} lattice nodes at "
          f"{CELL_M} m ({len(need)} fetched) -> data/ground_release.json")
    return rep


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python tools/ground_release.py <project-dir> [--offline]")
    run(Path(args[0]), offline="--offline" in sys.argv)


if __name__ == "__main__":
    main()
