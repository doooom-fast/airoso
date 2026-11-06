"""The median between I 8's two carriageways as the lidar measures it (ledger 0080 2a round 4; Kevin 2026-11-05: "I just
want real"): class-2 (ground) returns of the USGS lidar, read across the gap between the line and each network
connector beside it, at every vertex of the line.

Source: the same lidar the deck reader uses (tools/network_deck_lidar.py): the 2014 QL2 EPT's node files in its cache
(--ept-cache, EPSG:3857) and any LAZ tiles (--laz, each tile's own CRS), NAVD88 metres; the draft's heights are NAVD88
less network.local.json's origin elev_m, so every lidar height here has that subtracted. Nothing is fetched: what the
cache holds is what is read, and a station whose median the cache does not cover is written UNREAD, not guessed.

At each line vertex paired with a connector (its nearest point within PAIR_M), along the line's normal toward it:
  - class-2 returns within ALONG_M of the section, binned every BIN_M across (median height per bin, BIN_MIN returns);
  - each carriageway's lidar pavement height = the bin just inside its inner edge (the measured edges, the built ones);
  - the median = the bins between the two inner edges; it is READ when at least READ_SHARE of them hold returns;
  - a STEP where two neighbouring read bins differ by more than STEP_MIN_M at a grade steeper than STEP_GRADE (earth
    does not stand steeper: a wall, with no return over it, not a slope); else, if read, a SLOPE (the ground as the lidar shows it), with the profile written relative to the two built pavements:
    each bin's height plus the correction that puts the lidar's pavement edges on the built ones (linear across the gap),
    so a 0.1 m datum or model difference never makes a ledge at a pavement's edge.
Every UPPER CASE number is [invented] (fleet/GATES-CHANGELOG.md 2026-11-05, round 4).

    python tools/median_lidar.py <draft-dir> --ept-cache DIR [--laz DIR] [--walls OUT.json]
Writes <draft-dir>/median_ground.lidar.json (with --walls, only the wall file walls() reads: round 5). Needs numpy, scipy, laspy[lazrs], pyproj (the lidar venv).
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAIR_M = 45.0          # naip_carriageways.PAIR_M: two carriageways within this are one section
CORRIDOR_M = 40.0      # [invented] returns further than this from either line are not read
ALONG_M = 2.0          # [invented] half the section's thickness along the line
BIN_M = 0.5            # [invented] across-section bin
BIN_MIN = 2            # [invented] returns a bin needs to hold a height
READ_SHARE = 0.6       # [invented] share of the median's bins that must hold heights for it to be READ
STEP_MIN_M = 0.5       # [invented] a jump this tall ...
PAST_M = 3.0           # [invented] the step is also sought this far past the partner's BUILT inner edge (NAIP vs lidar
#                        put the wall 0.5-2 m apart at WB s 6,750-6,950)
STEP_GRADE = 1.0       # [invented] ... at steeper than 1:1 between neighbouring read bins (ground does not stand steeper)


def _frames(P):
    import numpy as np
    xz = P[:, [0, 2]]
    t = np.zeros_like(xz)
    t[1:-1] = xz[2:] - xz[:-2]
    t[0], t[-1] = xz[1] - xz[0], xz[-1] - xz[-2]
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xz, axis=0).T))])
    return xz, t, np.stack([-t[:, 1], t[:, 0]], axis=1), s


def read_ground(draft: Path, ept_cache: Path | None, laz: Path | None, corridor_xz):
    """(N, 3) local x, z, height (elev0 subtracted) of every class-2 return within CORRIDOR_M of ``corridor_xz``."""
    import numpy as np
    import laspy
    from pyproj import Transformer
    from scipy.spatial import cKDTree
    from scripts.geometry.projection import _meters_per_degree
    org = json.loads((draft / "network.local.json").read_text(encoding="utf-8"))["origin"]
    lon0, lat0, e0 = float(org["lon"]), float(org["lat"]), float(org["elev_m"])
    mx, my = _meters_per_degree(lat0)
    tree = cKDTree(corridor_xz)
    out, files = [], []

    def keep(lo, la, z):
        x = (lo - lon0) * mx
        zz = (la - lat0) * my
        d, _ = tree.query(np.c_[x, zz], distance_upper_bound=CORRIDOR_M)
        k = np.isfinite(d)
        if k.any():
            out.append(np.c_[x[k], zz[k], z[k] - e0])
    if ept_cache is not None:
        inv = Transformer.from_crs(3857, 4326, always_xy=True)
        for f in sorted(glob.glob(str(ept_cache / "*-*-*-*.laz"))):
            las = laspy.read(f)
            m = np.asarray(las.classification) == 2
            if m.any():
                lo, la = inv.transform(np.asarray(las.x)[m], np.asarray(las.y)[m])
                keep(lo, la, np.asarray(las.z)[m])
            files.append(Path(f).name)
    if laz is not None:
        for f in sorted(Path(laz).glob("*.laz")):
            with laspy.open(f) as fh:
                crs = fh.header.parse_crs()
                h = crs.sub_crs_list[0] if crs.is_compound else crs
                tr = Transformer.from_crs(h, 4326, always_xy=True)
                for ch in fh.chunk_iterator(2_000_000):
                    m = np.asarray(ch.classification) == 2
                    if m.any():
                        lo, la = tr.transform(np.asarray(ch.x)[m], np.asarray(ch.y)[m])
                        keep(lo, la, np.asarray(ch.z)[m])
            files.append(f.name)
    G = np.concatenate(out) if out else np.zeros((0, 3))
    return G, files


def sections(line, partner, G):
    """Per line vertex paired with ``partner``: the measured median (see the module doc)."""
    import numpy as np
    from scipy.spatial import cKDTree
    P = np.asarray(line["points_xyz_m"], float); W = np.asarray(line["widths_m"], float)
    Q = np.asarray(partner["points_xyz_m"], float); QW = np.asarray(partner["widths_m"], float)
    xz, t, n, s = _frames(P)
    qt = cKDTree(Q[:, [0, 2]])
    gt = cKDTree(G[:, :2]) if len(G) else None
    rows = []
    for i in range(len(P)):
        d, j = qt.query(xz[i])
        if d > PAIR_M:
            continue
        v = Q[j, [0, 2]] - xz[i]
        side = 1.0 if float(v @ n[i]) > 0 else -1.0
        dist = abs(float(v @ n[i]))
        e_line, e_part = W[i] / 2.0, dist - QW[j] / 2.0         # inner edges, offsets from the line's centre
        rec = {"s": round(float(s[i]), 1), "i": i, "x": round(float(xz[i][0]), 2), "z": round(float(xz[i][1]), 2),
               "n": [round(float(side * n[i][0]), 5), round(float(side * n[i][1]), 5)], "partner_vertex": int(j),
               "edges": [round(e_line, 2), round(e_part, 2)], "gap_m": round(e_part - e_line, 2),
               "built_y": [round(float(P[i, 1]), 2), round(float(Q[j, 1]), 2)], "kind": "unread"}
        if gt is None or e_part - e_line < BIN_M:
            rows.append(rec); continue
        idx = gt.query_ball_point(xz[i], dist + 2.0)
        if not idx:
            rows.append(rec); continue
        pts = G[idx]
        w = pts[:, :2] - xz[i]
        al = w @ t[i]
        lat = (w @ n[i]) * side
        m = np.abs(al) <= ALONG_M
        lat, hz = lat[m], pts[m, 2]
        bins = {}
        for o in np.arange(e_line - 1.0, e_part + PAST_M + 1e-6, BIN_M):
            k = (lat >= o - BIN_M / 2) & (lat < o + BIN_M / 2)
            if int(k.sum()) >= BIN_MIN:
                bins[round(float(o), 2)] = float(np.median(hz[k]))
        inner = [o for o in np.arange(e_line - 1.0, e_part + 1.0 + 1e-6, BIN_M)]
        med = [round(float(o), 2) for o in inner if e_line < o < e_part]
        got = [o for o in med if o in bins]
        pl = [bins[o] for o in sorted(bins) if o <= e_line]
        pp = [bins[o] for o in sorted(bins) if o >= e_part]
        rec["read_share"] = round(len(got) / len(med), 2) if med else 0.0
        if not pl or not pp:
            rows.append(rec); continue
        zl, zp = pl[-1], pp[0]                                   # the lidar's pavement at each inner edge
        rec["lidar_edge_y"] = [round(zl, 2), round(zp, 2)]
        keys = sorted(bins)
        step = None
        for a, b in zip(keys, keys[1:]):
            if abs(bins[b] - bins[a]) > STEP_MIN_M and abs(bins[b] - bins[a]) > STEP_GRADE * (b - a):
                if step is None or abs(bins[b] - bins[a]) > abs(step[2]):
                    step = (a, b, bins[b] - bins[a])
        if step is not None:
            rec["kind"] = "step"
            rec["step"] = [step[0], step[1], round(step[2], 2)]
            if step[0] >= e_part - BIN_M / 2:
                rec["step_past_built_edge"] = True         # the lidar's wall stands beyond the built inner edge
        elif med and rec["read_share"] >= READ_SHARE:
            rec["kind"] = "slope"
        else:
            rows.append(rec); continue
        # the profile on the built pavements: plus the correction, linear across the gap
        cl, cp = float(P[i, 1]) - zl, float(Q[j, 1]) - zp
        prof = []
        for o in [e_line] + got + [e_part]:
            u = (o - e_line) / max(e_part - e_line, 1e-6)
            z = (zl if o == e_line else zp if o == e_part else bins[o]) + cl + (cp - cl) * u
            prof.append([round(float(o), 2), round(z, 3)])
        rec["profile"] = prof
        rows.append(rec)
    return rows


# ledger 0080 2a round 5: the WALL between the carriageways where it stands, for naip_carriageways to put the median
# barrier on (owed item 1: at line s 3,425-3,611 the lidar's wall stood 0.5-2.8 m past WB's built inner edge, which NAIP
# had put at the midline between the two centres: "barrier at the midline", nothing seen). sections() looks for a step
# only out to PAST_M past the partner's built edge, so it misses a wall further in; walls() reads the whole width from
# the line's inner edge to the partner's CENTRE, and keeps a step only where the lidar says it is THE wall between these
# two pavements: its low bin reads the low carriageway's built height and its high bin the high one's, each within
# EDGE_TOL_M (median_ground_blend's own tolerance for "this pavement's edge"). A step that does not (a deck: the lidar's
# ground under it, not its pavement) is not a wall here. The wall's line is the middle of the no-return gap between the
# two bins (the barrier stands in it: Type 60's 0.61 m base and the wall's face return no class 2).
EDGE_TOL_M = 0.5       # reused: tools/median_ground_blend.py, a pavement's edge is where the surface is within 0.5 m of it


def walls(line, partner, G):
    """Per line vertex paired with ``partner``: the wall the lidar reads between the two pavements, if any."""
    import numpy as np
    from scipy.spatial import cKDTree
    P = np.asarray(line["points_xyz_m"], float); W = np.asarray(line["widths_m"], float)
    Q = np.asarray(partner["points_xyz_m"], float)
    xz, t, n, s = _frames(P)
    qt = cKDTree(Q[:, [0, 2]])
    gt = cKDTree(G[:, :2])
    rows = []
    for i in range(len(P)):
        d, j = qt.query(xz[i])
        if d > PAIR_M:
            continue
        v = Q[j, [0, 2]] - xz[i]
        side = 1.0 if float(v @ n[i]) > 0 else -1.0
        dist = abs(float(v @ n[i]))
        idx = gt.query_ball_point(xz[i], dist + 2.0)
        if not idx:
            continue
        pts = G[idx]
        w = pts[:, :2] - xz[i]
        m = np.abs(w @ t[i]) <= ALONG_M
        lat, hz = ((w @ n[i]) * side)[m], pts[m, 2]
        bins = {}
        for o in np.arange(W[i] / 2.0 - 1.0, dist + 1e-6, BIN_M):
            k = (lat >= o - BIN_M / 2) & (lat < o + BIN_M / 2)
            if int(k.sum()) >= BIN_MIN:
                bins[round(float(o), 2)] = float(np.median(hz[k]))
        keys = sorted(bins)
        yl, yp = float(P[i, 1]), float(Q[j, 1])
        best = None
        for a, b in zip(keys, keys[1:]):
            dz = bins[b] - bins[a]
            if abs(dz) > STEP_MIN_M and abs(dz) > STEP_GRADE * (b - a):
                if abs(bins[a] - yl) <= EDGE_TOL_M and abs(bins[b] - yp) <= EDGE_TOL_M:
                    if best is None or abs(dz) > abs(best[2]):
                        best = (a, b, dz)
        if best is None:
            continue
        a, b, dz = best
        mid = (a + b) / 2.0
        nn = side * n[i]
        rows.append({"s": round(float(s[i]), 1), "i": i, "partner_vertex": int(j),
                     "bins": [a, b], "mid": round(mid, 2), "dz": round(dz, 2),
                     "y": [round(bins[a], 2), round(bins[b], 2)], "built_y": [round(yl, 2), round(yp, 2)],
                     "edges_built": [round(float(W[i] / 2.0), 2)],
                     "xz": [round(float(xz[i][0] + nn[0] * mid), 3), round(float(xz[i][1] + nn[1] * mid), 3)]})
    return rows


def main(argv=None):
    import numpy as np
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    draft = Path(argv[0])
    ept = Path(argv[argv.index("--ept-cache") + 1]) if "--ept-cache" in argv else None
    laz = Path(argv[argv.index("--laz") + 1]) if "--laz" in argv else None
    line = json.loads((draft / "centerline.measured.local.json").read_text(encoding="utf-8"))
    conns = [c for c in json.loads((draft / "connectors.measured.local.json").read_text(encoding="utf-8"))["connectors"]
             if c.get("network")]
    cor = []
    for arr in [line["points_xyz_m"]] + [c["points_xyz_m"] for c in conns]:
        a = np.asarray(arr, float)[:, [0, 2]]
        for p, q in zip(a, a[1:]):
            k = max(1, int(np.hypot(*(q - p)) / 2.0))
            cor += [p + (q - p) * u for u in np.linspace(0, 1, k, endpoint=False)]
    G, files = read_ground(draft, ept, laz, np.asarray(cor))
    if "--walls" in argv:
        out = Path(argv[argv.index("--walls") + 1])
        doc = {"tool": "tools/median_lidar.py --walls", "ledger": "0080 2a round 5",
               "lidar": {"ept_cache_nodes": sum(1 for f in files if f.count("-") == 3),
                         "laz_tiles": [f for f in files if f.count("-") != 3], "class2_returns_in_corridor": int(len(G))},
               "params": {k: globals()[k] for k in ("PAIR_M", "ALONG_M", "BIN_M", "BIN_MIN", "STEP_MIN_M", "STEP_GRADE",
                                                       "EDGE_TOL_M")},
               "_doc": "the wall between two carriageways where the lidar reads it (walls()): xz = the line of the "
                       "no-return gap's middle, in the draft's local frame; an input of tools/naip_carriageways.py --walls",
               "inputs": {f: hashlib.md5((draft / f).read_bytes()).hexdigest()
                          for f in ("centerline.measured.local.json", "connectors.measured.local.json", "network.local.json")},
               "pairs": {}}
        for c in conns:
            rows = walls(line, c, G)
            doc["pairs"][c["name"]] = {"walls": len(rows), "rows": rows}
            print(f"[median_lidar] walls line | {c['name']}: {len(rows)} stations read a wall")
        out.write_text(json.dumps(doc), encoding="utf-8")
        return
    doc = {"tool": "tools/median_lidar.py", "ledger": "0080 2a round 4",
           "lidar": {"ept_cache_nodes": sum(1 for f in files if f.count("-") == 3), "laz_tiles": [f for f in files if f.count("-") != 3],
                     "class2_returns_in_corridor": int(len(G))},
           "params": {k: globals()[k] for k in ("PAIR_M", "CORRIDOR_M", "ALONG_M", "BIN_M", "BIN_MIN", "READ_SHARE",
                                                   "STEP_MIN_M", "STEP_GRADE", "PAST_M")},
           "_invented": "every params value except PAIR_M (naip_carriageways'): fleet/GATES-CHANGELOG.md 2026-11-05 round 4",
           "inputs": {f: hashlib.md5((draft / f).read_bytes()).hexdigest()
                      for f in ("centerline.measured.local.json", "connectors.measured.local.json", "network.local.json")},
           "pairs": {}}
    for c in conns:
        rows = sections(line, c, G)
        kinds = {}
        for r in rows:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        doc["pairs"][c["name"]] = {"stations": len(rows), "kinds": kinds, "rows": rows}
        print(f"[median_lidar] line | {c['name']}: {len(rows)} paired stations: {kinds}")
    (draft / "median_ground.lidar.json").write_text(json.dumps(doc), encoding="utf-8")
    print(f"[median_lidar] {len(G):,} class-2 returns in the corridor from {len(files)} files: "
          f"{draft / 'median_ground.lidar.json'}")


if __name__ == "__main__":
    main()
