"""Are the houses standing on the ground? — ledger 0046 fix round 3 (the visual lens's "sunken houses").

READ-ONLY on the gate OBJ (data/track.obj, kn5_to_gate_obj of the shipped road kn5 — L5: the artifact, never the
data that placed it). In plain terms: every OSM house and building is a box — a flat bottom ring, walls, a flat roof.
A box is seated when its bottom touches the LOWEST ground under its walls: not above it (a wall hanging in the air
on the downhill side), and not far below it (a house half under a hill, as the visual lens saw from the road at
(-249, 1461), (-1278, -1180) and (-1613, -693) on the 2026-10-13 build). The prep seats every building that way
(engine-july build_kn5_loop.house_seat: the floor at the mean ground less 0.4 m, the foundation down to 0.15 m under
the lowest ground), so on the built ground the bottom of a seated building sits between 0.4 m and 0.15 m under the
lowest ground its walls stand on.

    contact = bottom - lowest ground under the walls      (m; ground = the top of 1GRASS / 1ROAD / 1KERB)
    FLOATING  contact >  FLOAT_M      (a wall bottom in the air)
    SUNKEN    contact < -SUNK_M       (the box pushed down into the ground it stands on)
    BURIED    roof - highest ground under the walls < MIN_SHOW_M   (a wall swallowed on the uphill side)

The prep also raises a building whose footprint straddles more relief than half its height (a cut edge) so that
half of it stands above the highest ground under its walls (house_seat ``show``); every building in the draft is at
least 3 m tall, so a seated one shows at least 1.5 m there.

The ground is read under every bottom corner and every ~STEP_M along each wall's bottom edge (a building's faces are
re-joined by position: the exporter splits them), highest surface within LAYER_M of the bottom (L4: never another
layer). Buildings with no ground under them are counted, not judged. Also reported, not gated: the visual lens's own
measure — the share of the building's height under the mean ground — so a run can be laid beside its numbers.

    python tools/house_seat_check.py <project> [--obj <gate obj>] [--json <out>]

Exit 1 when more than MAX_FLOATING, MAX_SUNKEN or MAX_BURIED buildings fail (fleet/GATES-CHANGELOG.md 2026-10-13 fix round 3;
every number invented). Frame: local, x = E, y = up, z = N.
"""
from __future__ import annotations

import json
import math
import sys
from array import array
from pathlib import Path

GROUND = ("1GRASS", "1ROAD", "1KERB")
BUILT = ("HOUSE", "BUILDING")
FLOAT_M = 0.10        # [invented] a bottom more than this above the lowest ground under its walls is hanging in the air
SUNK_M = 1.0          # [invented] ... more than this below it is pushed into the ground (the prep's rule gives 0.15-0.40)
MIN_SHOW_M = 1.0      # [invented] a roof less than this above the highest ground under the walls is a buried wall
STEP_M = 1.5          # [invented] ground read along each wall's bottom edge at about this spacing (the prep's own step)
LAYER_M = 20.0        # L4: ground more than this from the bottom is another layer
BOTTOM_TOL = 0.05     # a vertex within this of the building's lowest is on its bottom ring
MAX_FLOATING = 0      # [invented]
MAX_SUNKEN = 0        # [invented]
MAX_BURIED = 0        # [invented]
CELL = 8.0            # ground triangle bucket (m)


def read_obj(path: Path):
    xs, ys, zs = array("d"), array("d"), array("d")
    ground, built = [], {}
    cur = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            c = line[:2]
            if c == "v ":
                p = line.split()
                xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
            elif c == "f ":
                if cur is None:
                    continue
                idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
                if cur is ground:
                    ground.extend((idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1))
                else:
                    cur.append(idx)
            elif c in ("o ", "g "):
                name = line[2:].strip()
                if name.startswith(GROUND):
                    cur = ground
                elif name.upper().startswith(BUILT):
                    cur = built.setdefault(name, [])
                else:
                    cur = None
    return (xs, ys, zs), ground, built


def buildings(V, faces):
    """[(vertex ids of one building, its faces)]: faces re-joined through shared POSITIONS (1 cm), since the exporter
    splits a box's vertices per face"""
    xs, ys, zs = V
    key = lambda i: (round(xs[i], 2), round(ys[i], 2), round(zs[i], 2))
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for fc in faces:
        k0 = find(key(fc[0]))
        for v in fc[1:]:
            k = find(key(v))
            if k != k0:
                parent[k] = k0
    out = {}
    for fc in faces:
        out.setdefault(find(key(fc[0])), []).append(fc)
    return list(out.values())


class Ground:
    """highest ground surface at (x, z) near a height — pure python triangle buckets"""

    def __init__(self, V, tris, keep):
        self.V = V
        self.b = {}
        xs, ys, zs = V
        for t in tris:
            a, b, c = t
            x0, x1 = min(xs[a], xs[b], xs[c]), max(xs[a], xs[b], xs[c])
            z0, z1 = min(zs[a], zs[b], zs[c]), max(zs[a], zs[b], zs[c])
            for i in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
                for j in range(int(math.floor(z0 / CELL)), int(math.floor(z1 / CELL)) + 1):
                    if (i, j) in keep:
                        self.b.setdefault((i, j), []).append(t)

    def at(self, x, z, near):
        xs, ys, zs = self.V
        best = None
        for a, b, c in self.b.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
            ax, az, bx, bz, cx, cz = xs[a], zs[a], xs[b], zs[b], xs[c], zs[c]
            det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(det) < 1e-12:
                continue
            l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
            l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
            l3 = 1.0 - l1 - l2
            if l1 < -1e-9 or l2 < -1e-9 or l3 < -1e-9:
                continue
            y = l1 * ys[a] + l2 * ys[b] + l3 * ys[c]
            if abs(y - near) <= LAYER_M and (best is None or y > best):
                best = y
        return best


def wall_points(V, faces, bottom):
    """the bottom-edge points of every wall: each face's edges with both ends on the bottom ring, walked at STEP_M"""
    xs, ys, zs = V
    seen, pts = set(), []
    for fc in faces:
        n = len(fc)
        for k in range(n):
            a, b = fc[k], fc[(k + 1) % n]
            if ys[a] > bottom + BOTTOM_TOL or ys[b] > bottom + BOTTOM_TOL:
                continue
            e = tuple(sorted(((round(xs[a], 2), round(zs[a], 2)), (round(xs[b], 2), round(zs[b], 2)))))
            if e in seen or e[0] == e[1]:
                continue
            seen.add(e)
            (ax, az), (bx, bz) = e
            m = int(math.hypot(bx - ax, bz - az) // STEP_M)
            pts += [(ax, az), (bx, bz)] + [(ax + (bx - ax) * j / (m + 1), az + (bz - az) * j / (m + 1))
                                          for j in range(1, m + 1)]
    return sorted(set(pts))


def run(proj: Path, obj: Path | None = None):
    obj = obj or proj / "data" / "track.obj"
    V, gtris, groups = read_obj(obj)
    xs, ys, zs = V
    blds = []
    for g, faces in groups.items():
        for fs in buildings(V, faces):
            ids = {i for fc in fs for i in fc}
            blds.append((g, fs, ids))
    keep = set()
    for _g, _fs, ids in blds:
        x0, x1 = min(xs[i] for i in ids), max(xs[i] for i in ids)
        z0, z1 = min(zs[i] for i in ids), max(zs[i] for i in ids)
        for i in range(int(math.floor(x0 / CELL)) - 1, int(math.floor(x1 / CELL)) + 2):
            for j in range(int(math.floor(z0 / CELL)) - 1, int(math.floor(z1 / CELL)) + 2):
                keep.add((i, j))
    G = Ground(V, gtris, keep)
    rows, no_ground = [], 0
    for g, fs, ids in blds:
        bottom = min(ys[i] for i in ids)
        top = max(ys[i] for i in ids)
        pts = wall_points(V, fs, bottom)
        hs = [h for h in (G.at(x, z, bottom) for x, z in pts) if h is not None]
        if len(pts) < 3 or len(hs) < max(3, len(pts) // 2):
            no_ground += 1
            continue
        corners = sorted({(round(xs[i], 2), round(zs[i], 2)) for i in ids if ys[i] <= bottom + BOTTOM_TOL})
        hc = [h for h in (G.at(x, z, bottom) for x, z in corners) if h is not None]
        gmean = sum(hc) / len(hc) if hc else sum(hs) / len(hs)
        cx = sum(x for x, _ in corners) / len(corners)
        cz = sum(z for _, z in corners) / len(corners)
        rows.append({"group": g, "x": round(cx, 1), "z": round(cz, 1), "bottom": round(bottom, 3), "top": round(top, 3),
                     "ground_low": round(min(hs), 3), "ground_high": round(max(hs), 3), "ground_mean": round(gmean, 3),
                     "contact_m": round(bottom - min(hs), 3), "show_m": round(top - max(hs), 3),
                     "lens_buried_share": round((gmean - bottom) / max(top - bottom, 0.1), 3)})
    floating = [r for r in rows if r["contact_m"] > FLOAT_M]
    sunken = [r for r in rows if r["contact_m"] < -SUNK_M]
    buried = [r for r in rows if r["show_m"] < MIN_SHOW_M]
    share = sorted(r["lens_buried_share"] for r in rows)
    rep = {"obj": str(obj), "buildings": len(rows), "no_ground": no_ground,
           "floating": len(floating), "sunken": len(sunken), "buried": len(buried),
           "limits": {"FLOAT_M": FLOAT_M, "SUNK_M": SUNK_M, "MIN_SHOW_M": MIN_SHOW_M, "STEP_M": STEP_M,
                      "MAX_FLOATING": MAX_FLOATING, "MAX_SUNKEN": MAX_SUNKEN, "MAX_BURIED": MAX_BURIED},
           "contact_m": {"min": min((r["contact_m"] for r in rows), default=None),
                         "max": max((r["contact_m"] for r in rows), default=None)},
           "show_m_min": min((r["show_m"] for r in rows), default=None),
           "lens_buried_share": {"over_30pct": sum(s > 0.3 for s in share), "over_50pct": sum(s > 0.5 for s in share),
                                 "p95": share[int(0.95 * (len(share) - 1))] if share else None},
           "worst_floating": sorted(floating, key=lambda r: -r["contact_m"])[:15],
           "worst_sunken": sorted(sunken, key=lambda r: r["contact_m"])[:15],
           "worst_buried": sorted(buried, key=lambda r: r["show_m"])[:15]}
    rep["verdict"] = "PASS" if (len(floating) <= MAX_FLOATING and len(sunken) <= MAX_SUNKEN
                                and len(buried) <= MAX_BURIED) else "FAIL"
    return rep, rows


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("--"):
        raise SystemExit(__doc__)
    proj = Path(argv[0])
    obj = Path(argv[argv.index("--obj") + 1]) if "--obj" in argv else None
    out = Path(argv[argv.index("--json") + 1]) if "--json" in argv else None
    rep, rows = run(proj, obj)
    print(f"[houses] {rep['obj']}: {rep['buildings']} buildings judged, {rep['no_ground']} with no ground under them")
    print(f"[houses] contact (bottom - lowest ground under the walls): min {rep['contact_m']['min']} m, "
          f"max {rep['contact_m']['max']} m")
    print(f"[houses] floating (> {FLOAT_M:g} m above): {rep['floating']} (limit {MAX_FLOATING}); "
          f"sunken (> {SUNK_M:g} m below): {rep['sunken']} (limit {MAX_SUNKEN}); buried (roof < {MIN_SHOW_M:g} m over "
          f"the highest ground under the walls): {rep['buried']} (limit {MAX_BURIED}); lowest roof over that ground "
          f"{rep['show_m_min']} m")
    for r in rep["worst_floating"][:5] + rep["worst_sunken"][:5] + rep["worst_buried"][:5]:
        print(f"[houses]   {r['group']} ({r['x']}, {r['z']}): contact {r['contact_m']:+.2f} m, roof over the highest "
              f"ground {r['show_m']:+.2f} m, ground {r['ground_low']}..{r['ground_high']}, bottom {r['bottom']}")
    print(f"[houses] the visual lens's buried share (mean ground over the height, foundation included; not gated): "
          f"{rep['lens_buried_share']}")
    print(f"[houses] {rep['verdict']}")
    if out:
        out.write_text(json.dumps({**rep, "rows": rows}, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
