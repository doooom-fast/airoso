"""Cut every connector street at the mainline's pavement edge — the RIBBON-THROUGH junction
topology (docs/JUNCTIONS.md §2: main ribbon unbroken, side street butt-welded to its edge).

Today the draft sweeps each connector as a full polyline straight THROUGH the mainline ribbon
(del_cerro_blvd crosses College twice; its 10 m ribbon, both raised sidewalks and double-yellow
run across College's pavement — ledger 0033, "criss-crossing sidewalks running THROUGH the
street"). Pros never do this: at all 13 junctions measured, zero road triangles overlap another
road. This tool does the data half of C2:

  1. for every connector point, lateral distance to the BUILT mainline (the smoothed centreline the
     ribbon was swept along, data/centerline.local.json) vs the mainline half-width there;
  2. splits the polyline wherever it enters the mainline footprint, inserting an endpoint
     OVERLAP_M inside the pavement edge (a hairline gap shows terrain; a 0.4 m overlap does not);
  3. drops stubs shorter than MIN_PIECE_M; names pieces <name>#<k>;
  4. writes data/mouths.json — one record per cut: mainline vertex, side, connector width — for
     tools/gap_mouths_blend.py, which gaps the mainline's own curb+sidewalk strip across each mouth.

Idempotent: works from data/connectors.local.json.pre-trim (written once). Run AFTER
median_envelope (the mainline alignment it trims against is the median-shifted one) and BEFORE
build_loop_blend.

    python tools/trim_connectors.py <project-dir>

Not yet handled (C2 v1.5): connector-to-connector mouths inside the Del Cerro sub-loop.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OVERLAP_M = 0.4
MIN_PIECE_M = 15.0


def _nearest_on_polyline(px, pz, line, cell_idx, cells, cell_m=25.0):
    best, bi, bt = float("inf"), 0, 0.0
    cx, cz = int(px // cell_m), int(pz // cell_m)
    cand = set()
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            cand.update(cells.get((cx + dx, cz + dz), ()))
    if not cand:
        return best, bi, bt
    for i in cand:
        if i + 1 >= len(line):
            continue
        ax, az = line[i][0], line[i][2]
        bx, bz = line[i + 1][0], line[i + 1][2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        d = math.hypot(px - (ax + t * dx), pz - (az + t * dz))
        if d < best:
            best, bi, bt = d, i, t
    return best, bi, bt


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    src = data / "connectors.local.json"
    bak = data / "connectors.local.json.pre-trim"
    if bak.exists():
        conns = json.loads(bak.read_text(encoding="utf-8"))
    else:
        conns = json.loads(src.read_text(encoding="utf-8"))
        bak.write_text(json.dumps(conns), encoding="utf-8")

    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    main = [tuple(p) for p in local["points_xyz_m"]]
    widths = local["widths_m"]
    n = len(main)
    cells: dict = {}
    for i in range(n - 1):
        for (x, z) in ((main[i][0], main[i][2]), (main[i + 1][0], main[i + 1][2])):
            cells.setdefault((int(x // 25.0), int(z // 25.0)), set()).add(i)

    def lateral(px, pz):
        d, i, t = _nearest_on_polyline(px, pz, main, None, cells)
        half = (widths[i] * (1 - t) + widths[min(n - 1, i + 1)] * t) / 2.0
        k = i if t < 0.5 else min(n - 1, i + 1)
        # signed side: + = left of travel (ribbon's side=+1), - = right
        ax, az = main[i][0], main[i][2]
        bx, bz = main[min(n - 1, i + 1)][0], main[min(n - 1, i + 1)][2]
        tx, tz = bx - ax, bz - az
        s = (-(tz) * (px - ax) + tx * (pz - az))
        return d, half, k, (1 if s >= 0 else -1)

    out = []
    mouths = []
    n_cuts = 0
    for c in conns.get("connectors", []):
        pts = [tuple(p) for p in c["points_xyz_m"]]
        w = list(c["widths_m"])
        inside = []
        info = []
        for (x, y, z) in pts:
            d, half, k, side = lateral(x, z)
            info.append((d, half, k, side))
            inside.append(d < half - OVERLAP_M)
        pieces = []
        i = 0
        m = len(pts)
        while i < m:
            if inside[i]:
                i += 1
                continue
            j = i
            while j < m and not inside[j]:
                j += 1
            piece = list(pts[i:j])
            pw = list(w[i:j])
            # extend the piece to the pavement edge on the inside side(s)
            for (edge_idx, nbr) in ((i - 1, i), (j, j - 1)):
                if 0 <= edge_idx < m and inside[edge_idx]:
                    po, pi_ = pts[nbr], pts[edge_idx]
                    do, ho, _, _ = info[nbr]
                    di, hi, k_in, side = info[edge_idx]
                    target = hi - OVERLAP_M
                    # linear interpolate the crossing of d == target between outside and inside pts
                    f = 0.0 if do == di else max(0.0, min(1.0, (do - target) / (do - di)))
                    cut = (po[0] + (pi_[0] - po[0]) * f, po[1] + (pi_[1] - po[1]) * f,
                           po[2] + (pi_[2] - po[2]) * f)
                    if edge_idx < i:
                        piece.insert(0, cut)
                        pw.insert(0, w[nbr])
                    else:
                        piece.append(cut)
                        pw.append(w[nbr])
                    mouths.append({"connector": c["name"], "main_vertex": k_in, "side": side,
                                   "connector_width_m": float(w[nbr]),
                                   "cut_xyz": [round(v, 3) for v in cut]})
                    n_cuts += 1
            plen = sum(math.hypot(piece[q][0] - piece[q - 1][0], piece[q][2] - piece[q - 1][2])
                       for q in range(1, len(piece)))
            if plen >= MIN_PIECE_M and len(piece) >= 2:
                pieces.append((piece, pw))
            i = j
        if len(pieces) == 1 and not any(inside):
            out.append(c)   # untouched
            continue
        for q, (piece, pw) in enumerate(pieces):
            out.append({"name": f"{c['name']}#{q}", "kind": c.get("kind", "connector"),
                        "points_xyz_m": [[round(v, 3) for v in p] for p in piece],
                        "widths_m": pw})
        print(f"[trim] {c['name']}: {len(pieces)} piece(s), {sum(inside)} pt(s) inside the mainline dropped")

    payload = dict(conns)
    payload["connectors"] = out
    src.write_text(json.dumps(payload), encoding="utf-8")
    (data / "mouths.json").write_text(json.dumps({"mouths": mouths}, indent=1), encoding="utf-8")
    print(f"[trim] {len(out)} connector piece(s), {n_cuts} mouth cut(s) -> data/connectors.local.json + data/mouths.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/trim_connectors.py <project-dir>")
    build(sys.argv[1])
