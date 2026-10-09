"""Collapse a divided side street that OSM stores as an out-and-back loop into ONE trunk ribbon with a
median island — the C1/0037 lesson applied to connectors.

Kevin (2026-10-08, seat): "the side streets, something's wrong with them where they're not
connecting correctly." Measured on del_cerro_blvd: the 3.3 km connector polyline runs parallel to
ITSELF at 11.9–15 m for points 0–475 and 625–1100 (its two carriageways, chained by merge_ways
into one loop), with a real loop road at the far end (points ~475–625 diverge to 440 m). The draft
swept both carriageways as separate 10 m ribbons with sidewalks on all four edges, meeting College
as two skinny mouths 12 m apart with sidewalks back-to-back between them — the phantom-carriageway
mistake in miniature.

This tool, for each route.divided_connectors name:
  1. pairs every point with its counterpart on the other carriageway (nearest point > 150 indices
     away); a point is "divided" when the pair is 8–18 m apart;
  2. the leading divided run (leg A) and the trailing one (leg B) become ONE trunk: centreline =
     pair midpoints, width = separation + W_CARRIAGEWAY, island width = separation − W_CARRIAGEWAY;
  3. the far loop between the legs stays a plain ribbon ("<name>_loop"), closed onto the trunk end;
  4. island widths go to 0 within MOUTH_SETBACK_M of the mainline (the left-turn pocket) and taper
     at both trunk ends; written to data/median_bands.json["connector_islands"] for
     tools/author_median_blend.py (geometry) and scripts/geometry/median_zone.py (gate exemption).

Idempotent from data/connectors.local.json.pre-divide (written once). Writes the divided set as
BOTH connectors.local.json and connectors.local.json.pre-trim so trim_connectors picks it up.
Run after median_envelope (it appends to median_bands.json) and before trim_connectors.

    python tools/divide_connectors.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

W_CARRIAGEWAY = 8.0
SEP_MIN, SEP_MAX = 8.0, 18.0
PAIR_GAP = 150
ISLAND_MIN_W, ISLAND_MAX_W = 1.5, 6.0
MOUTH_SETBACK_M = 18.0
END_PULLBACK = 5
TAPER = 8


def _nearest_seg_dist(px, pz, line):
    best = float("inf")
    for a, b in zip(line, line[1:]):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        best = min(best, math.hypot(px - (ax + t * dx), pz - (az + t * dz)))
    return best


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    names = cfg.get("route", {}).get("divided_connectors", [])
    src = data / "connectors.local.json"
    bak = data / "connectors.local.json.pre-divide"
    if not names:
        print("[divide] no route.divided_connectors configured — nothing to do")
        return
    if bak.exists():
        conns = json.loads(bak.read_text(encoding="utf-8"))
    else:
        pre_trim = data / "connectors.local.json.pre-trim"
        conns = json.loads((pre_trim if pre_trim.exists() else src).read_text(encoding="utf-8"))
        bak.write_text(json.dumps(conns), encoding="utf-8")
    main = [tuple(p) for p in json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
    main_w = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["widths_m"]

    out = []
    islands = []
    for c in conns.get("connectors", []):
        if c["name"] not in names:
            out.append(c)
            continue
        pts = [tuple(p) for p in c["points_xyz_m"]]
        n = len(pts)
        partner = [None] * n
        sep = [None] * n
        for i in range(n):
            best, bj = float("inf"), None
            for j in range(n):
                if abs(j - i) <= PAIR_GAP:
                    continue
                d = math.hypot(pts[i][0] - pts[j][0], pts[i][2] - pts[j][2])
                if d < best:
                    best, bj = d, j
            if bj is not None and SEP_MIN <= best <= SEP_MAX:
                partner[i], sep[i] = bj, best
        a_end = 0
        while a_end + 1 < n and partner[a_end + 1] is not None:
            a_end += 1
        b_start = n - 1
        while b_start - 1 > a_end and partner[b_start - 1] is not None:
            b_start -= 1
        if a_end < 20 or (n - b_start) < 20:
            print(f"[divide] {c['name']}: no divided legs found (A {a_end} pts, B {n - b_start} pts) — left as is")
            out.append(c)
            continue
        # trunk from leg A paired with leg B
        mids, widths, iw = [], [], []
        for i in range(0, a_end + 1):
            j = partner[i]
            if j is None:
                continue
            p, q = pts[i], pts[j]
            mids.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2))
            widths.append(round(sep[i] + W_CARRIAGEWAY, 2))
            iw.append(max(ISLAND_MIN_W, min(ISLAND_MAX_W, sep[i] - W_CARRIAGEWAY)))
        m = len(mids)
        # island gaps: mouth setback from the mainline, pullback + taper at trunk ends
        for k in range(m):
            d = _nearest_seg_dist(mids[k][0], mids[k][2], main)
            if d < MOUTH_SETBACK_M + max(main_w) / 2.0:
                iw[k] = 0.0
        for k in range(m):
            if k < END_PULLBACK or (m - 1 - k) < END_PULLBACK:
                iw[k] = 0.0
        out.append({"name": c["name"], "kind": "connector",
                    "points_xyz_m": [[round(v, 3) for v in p] for p in mids],
                    "widths_m": widths})
        islands.append({"name": c["name"], "points_xyz_m": [[round(v, 3) for v in p] for p in mids],
                        "island_w_by_point": [round(w, 2) for w in iw]})
        # the far loop: points between the legs, closed onto the trunk end
        loop = [mids[-1]] + list(pts[a_end + 1:b_start]) + [mids[-1]]
        if len(loop) >= 4:
            out.append({"name": f"{c['name']}_loop", "kind": "connector",
                        "points_xyz_m": [[round(v, 3) for v in p] for p in loop],
                        "widths_m": [float(c["widths_m"][0])] * len(loop)})
        print(f"[divide] {c['name']}: trunk {m} pts, width {min(widths):.1f}-{max(widths):.1f} m, island on "
              f"{sum(1 for w in iw if w > 0)} pts; loop {len(loop)} pts; legs A 0-{a_end}, B {b_start}-{n - 1}")

    payload = dict(conns)
    payload["connectors"] = out
    src.write_text(json.dumps(payload), encoding="utf-8")
    (data / "connectors.local.json.pre-trim").write_text(json.dumps(payload), encoding="utf-8")
    bands_path = data / "median_bands.json"
    bands = json.loads(bands_path.read_text(encoding="utf-8")) if bands_path.exists() else {}
    bands["connector_islands"] = islands
    bands_path.write_text(json.dumps(bands), encoding="utf-8")
    print(f"[divide] {len(out)} connector(s) written; {len(islands)} connector island(s) -> median_bands.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/divide_connectors.py <project-dir>")
    build(sys.argv[1])
