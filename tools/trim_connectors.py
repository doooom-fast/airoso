"""Cut every side street at the pavement edge of the road it joins — the RIBBON-THROUGH junction
topology (docs/JUNCTIONS.md §2: host ribbon unbroken, side street butt-welded to its edge).

Hosts: the MAINLINE, plus every divided connector trunk (route.divided_connectors — Del Cerro Blvd
after tools/divide_connectors.py), so a street joining the boulevard is cut and gapped exactly like
one joining College (Kevin, 2026-10-08: side streets "not connecting correctly ... sidewalks
blocking them"). Two passes: all connectors vs the mainline, then the non-host pieces vs the host
trunks. For each cut: an endpoint OVERLAP_M inside the host's pavement edge (a hairline gap shows
terrain; 0.4 m of overlap does not), a record in data/mouths.json {host, host_vertex, side,
connector_width_m} for tools/gap_mouths_blend.py, and — when the host carries a median island —
the island zeroed within MOUTH_ISLAND_GAP_M of the cut (left-turn pocket) in median_bands.json.

Idempotent from data/connectors.local.json.pre-trim (written once per base). Run after divide,
before build_loop_blend.

    python tools/trim_connectors.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OVERLAP_M = 0.4
MIN_PIECE_M = 15.0
MOUTH_ISLAND_GAP_M = 18.0


def _lateral(px, pz, line, widths):
    """(distance, host half-width there, nearest vertex, side) vs a polyline"""
    best = (float("inf"), 0, 0.0)
    for i in range(len(line) - 1):
        ax, az, bx, bz = line[i][0], line[i][2], line[i + 1][0], line[i + 1][2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        d = math.hypot(px - (ax + t * dx), pz - (az + t * dz))
        if d < best[0]:
            best = (d, i, t)
    d, i, t = best
    n = len(line)
    half = (widths[i] * (1 - t) + widths[min(n - 1, i + 1)] * t) / 2.0
    k = i if t < 0.5 else min(n - 1, i + 1)
    ax, az = line[i][0], line[i][2]
    bx, bz = line[min(n - 1, i + 1)][0], line[min(n - 1, i + 1)][2]
    tx, tz = bx - ax, bz - az
    s = (-(tz) * (px - ax) + tx * (pz - az))
    return d, half, k, (1 if s >= 0 else -1)


def _trim_against(conns, hosts, mouths):
    """conns: list of connector dicts to trim; hosts: list of (name, pts, widths). Returns new list."""
    out = []
    for c in conns:
        pts = [tuple(p) for p in c["points_xyz_m"]]
        w = list(c["widths_m"])
        # REACH THE HOST: a piece whose end stops short of a host's pavement (the route node sits
        # on the host's carriageway, but a divided trunk's centre is the carriageway midpoint, so
        # the end lands outside half-width) is extended to the host's centreline so the cut below
        # butts it to the edge. Only ends within REACH_M of a host are extended.
        REACH_M = 15.0
        for end in (0, -1):
            x, y, z = pts[end]
            best = None
            for hname, hpts, hw in hosts:
                d, half, k, side = _lateral(x, z, hpts, hw)
                if best is None or d - half < best[0] - best[1]:
                    best = (d, half, k, hname, hpts)
            if best and best[1] - OVERLAP_M <= best[0] <= best[1] + REACH_M:
                hx, hy, hz = best[4][best[2]]
                tgt = (hx, y, hz)
                if end == 0:
                    pts.insert(0, tgt)
                    w.insert(0, w[0])
                else:
                    pts.append(tgt)
                    w.append(w[-1])
        m = len(pts)
        info = []
        inside = []
        for (x, y, z) in pts:
            best = None
            for hname, hpts, hw in hosts:
                d, half, k, side = _lateral(x, z, hpts, hw)
                if best is None or d - half < best[0] - best[1]:
                    best = (d, half, k, side, hname)
            info.append(best)
            inside.append(best is not None and best[0] < best[1] - OVERLAP_M)
        pieces = []
        i = 0
        while i < m:
            if inside[i]:
                i += 1
                continue
            j = i
            while j < m and not inside[j]:
                j += 1
            piece = list(pts[i:j])
            pw = list(w[i:j])
            for (edge_idx, nbr) in ((i - 1, i), (j, j - 1)):
                if 0 <= edge_idx < m and inside[edge_idx]:
                    po, pi_ = pts[nbr], pts[edge_idx]
                    do, ho, _, _, _ = info[nbr]
                    di, hi, k_in, side, hname = info[edge_idx]
                    target = hi - OVERLAP_M
                    f = 0.0 if do == di else max(0.0, min(1.0, (do - target) / (do - di)))
                    cut = (po[0] + (pi_[0] - po[0]) * f, po[1] + (pi_[1] - po[1]) * f, po[2] + (pi_[2] - po[2]) * f)
                    if edge_idx < i:
                        piece.insert(0, cut)
                        pw.insert(0, w[nbr])
                    else:
                        piece.append(cut)
                        pw.append(w[nbr])
                    mouths.append({"connector": c["name"], "host": hname, "host_vertex": k_in, "side": side,
                                   "connector_width_m": float(w[nbr]), "cut_xyz": [round(v, 3) for v in cut]})
            plen = sum(math.hypot(piece[q][0] - piece[q - 1][0], piece[q][2] - piece[q - 1][2])
                       for q in range(1, len(piece)))
            if plen >= MIN_PIECE_M and len(piece) >= 2:
                pieces.append((piece, pw))
            i = j
        if len(pieces) == 1 and not any(inside):
            out.append(c)
            continue
        for q, (piece, pw) in enumerate(pieces):
            out.append({"name": f"{c['name']}#{q}", "kind": c.get("kind", "connector"),
                        "points_xyz_m": [[round(v, 3) for v in p] for p in piece], "widths_m": pw})
        if any(inside):
            print(f"[trim] {c['name']}: {len(pieces)} piece(s), {sum(inside)} pt(s) inside a host dropped")
    return out


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    divided = cfg.get("route", {}).get("divided_connectors", [])
    src = data / "connectors.local.json"
    bak = data / "connectors.local.json.pre-trim"
    if bak.exists():
        conns = json.loads(bak.read_text(encoding="utf-8"))
    else:
        conns = json.loads(src.read_text(encoding="utf-8"))
        bak.write_text(json.dumps(conns), encoding="utf-8")
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    main = [tuple(p) for p in local["points_xyz_m"]]
    mouths = []

    # pass 1: everything vs the mainline
    first = _trim_against(conns.get("connectors", []), [("MAINLINE", main, local["widths_m"])], mouths)
    # pass 2: non-host pieces vs the divided trunks (host = any piece of a divided connector, not its _loop)
    def is_host(c):
        return any(c["name"] == d or c["name"].startswith(d + "#") for d in divided)
    hosts = [(c["name"], [tuple(p) for p in c["points_xyz_m"]], c["widths_m"]) for c in first if is_host(c)]
    hosts_set = {h[0] for h in hosts}
    rest = [c for c in first if c["name"] not in hosts_set and not any(c["name"].startswith(d + "_loop") for d in divided)]
    loops = [c for c in first if any(c["name"].startswith(d + "_loop") for d in divided)]
    second = _trim_against(rest, hosts, mouths) if hosts else rest
    out = [c for c in first if c["name"] in hosts_set] + loops + second

    # island gaps on trunk hosts at every mouth
    bands_path = data / "median_bands.json"
    if bands_path.exists():
        bands = json.loads(bands_path.read_text(encoding="utf-8"))
        gapped = 0
        for ci in bands.get("connector_islands", []):
            ipts = ci["points_xyz_m"]
            for mo in mouths:
                if not mo["host"].startswith(ci["name"]):
                    continue
                cx, _, cz = mo["cut_xyz"]
                for q, p in enumerate(ipts):
                    if ci["island_w_by_point"][q] > 0 and math.hypot(p[0] - cx, p[2] - cz) <= MOUTH_ISLAND_GAP_M:
                        ci["island_w_by_point"][q] = 0.0
                        gapped += 1
        bands_path.write_text(json.dumps(bands), encoding="utf-8")
        if gapped:
            print(f"[trim] trunk island gapped on {gapped} point(s) at connector mouths")

    payload = dict(conns)
    payload["connectors"] = out
    src.write_text(json.dumps(payload), encoding="utf-8")
    (data / "mouths.json").write_text(json.dumps({"mouths": mouths}, indent=1), encoding="utf-8")
    hosts_hit = sorted({mo["host"] for mo in mouths})
    print(f"[trim] {len(out)} connector piece(s), {len(mouths)} mouth cut(s) on {hosts_hit} -> connectors.local.json + mouths.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/trim_connectors.py <project-dir>")
    build(sys.argv[1])
