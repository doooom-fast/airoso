"""Measure a divided road's real median from the OSM dual-carriageway geometry and re-center
the road ribbon over it.

The C1 fix deleted the broken split-carriageway ribbons (ledger 0029/0032/0035) but left the
mainline riding ONE carriageway's alignment at combined width — Kevin's seat: "it loses realism,
that road doesn't look like that there" (0037). The pro pattern (docs/JUNCTIONS.md, rt_macau):
ONE continuous pavement slab, with the median standing ON it as a raised island.

This tool does the data half:
  1. finds the opposing carriageway chain for each route.median_islands road (same geometric
     clustering the old extra_lines used, now for good);
  2. on cleanly-divided runs (separation >= 11 m sustained >= 200 m) shifts the RAW centerline
     laterally to the true midpoint between carriageways and widens the ribbon to span both
     (new_width = separation + single_carriageway_width), tapered over ~36 m at run ends —
     never a step (the sawtooth lesson);
  3. writes data/median_bands.json: per-vertex island widths for the authored island, with
     gaps cut around every connector mouth (left turns) and pulled back from run ends.

Edits data/centerline.raw.local.json IN PLACE (backup: .pre-median, written once).
The Blender half is tools/author_median_blend.py — run AFTER build_loop_blend.

    python tools/median_envelope.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MIN_SEP = 11.0        # carriageways this far apart = real median between them (same as old machinery)
SEP_TRUST = 24.0      # above this, it's a junction flare / wrong-chain match, not a median — exclude
MAX_SEP = 40.0
MIN_RUN_M = 120.0
GAP_BRIDGE = 8        # out-of-band verts (~24 m) tolerated INSIDE a run (turn-pocket flares)
TAPER_VERTS = 12      # ~36 m blend of shift+width at run ends
ISLAND_MIN_W, ISLAND_MAX_W = 1.5, 7.0
ISLAND_PULLBACK = 5   # island starts this many verts inside the full-shift zone
GAP_HALF = 6          # island gap half-length (verts, ~18 m) around each connector mouth
CLIP_REACH = 45.0


def _chains(ways):
    segs = [list(w) for w in ways if len(w) >= 2]
    used = [False] * len(segs)
    out = []

    def key(p):
        return (round(p[0], 6), round(p[1], 6))

    for i, s in enumerate(segs):
        if used[i]:
            continue
        used[i] = True
        ch = list(s)
        ext = True
        while ext:
            ext = False
            for j, t in enumerate(segs):
                if used[j]:
                    continue
                if key(ch[-1]) == key(t[0]):
                    ch += t[1:]
                elif key(ch[-1]) == key(t[-1]):
                    ch += list(reversed(t))[1:]
                elif key(ch[0]) == key(t[-1]):
                    ch = t[:-1] + ch
                elif key(ch[0]) == key(t[0]):
                    ch = list(reversed(t))[:-1] + ch
                else:
                    continue
                used[j] = True
                ext = True
        out.append(ch)
    return sorted(out, key=len, reverse=True)


def _meters_per_degree(lat):
    r = 6371000.0
    return (r * math.cos(math.radians(lat)) * math.pi / 180.0, r * math.pi / 180.0)


def build(project_dir):
    proj = Path(project_dir)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    roads = cfg.get("route", {}).get("median_islands", [])
    if not roads:
        print("[median] no route.median_islands configured — nothing to do")
        return

    raw_path = data / "centerline.raw.local.json"
    bak = data / "centerline.raw.local.json.pre-median"
    if bak.exists():
        # idempotent: always work from the pristine pre-median snapshot
        raw = json.loads(bak.read_text(encoding="utf-8"))
    else:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        bak.write_text(json.dumps(raw), encoding="utf-8")
    pts = [list(p) for p in raw["points_xyz_m"]]
    widths = list(raw["widths_m"])
    n = len(pts)
    o = raw["origin"]
    lon0, lat0 = o["lon"], o["lat"]
    m_lon, m_lat = _meters_per_degree(lat0)

    cache = json.loads((data / "network.cache.json").read_text(encoding="utf-8"))
    byname = {}
    for w in cache:
        nm = w.get("name")
        if nm:
            byname.setdefault(nm, []).append([(x[0], x[1]) for x in w["geom"]])

    main_xz = [(p[0], p[2]) for p in pts]

    # signed per-vertex state: shift vector (dx,dz), new width, island width (0 = none)
    shift = [(0.0, 0.0)] * n
    new_w = list(widths)
    island_w = [0.0] * n
    run_ranges = []

    for road in roads:
        chs = [c for c in _chains(byname.get(road, [])) if len(c) >= 10]
        # classify chains by MEDIAN lateral distance (mean is inflated by turn-flare outliers —
        # that mis-pick selected the mainline's own chain as "opposing" on the first attempt)
        cands = []
        for c in chs:
            xz = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in c]
            near = [p for p in xz if min(math.hypot(p[0] - mx, p[1] - mz)
                                         for mx, mz in main_xz[::4]) <= CLIP_REACH]
            if len(near) < 20:
                continue
            lats = sorted(min(math.hypot(x - mx, z - mz) for mx, mz in main_xz[::4])
                          for x, z in near)
            # classify on the near points, but keep the FULL ordered chain for geometry —
            # the near-filter punches holes and a holed polyline chords across them
            cands.append((lats[len(lats) // 2], xz))
        cands.sort(key=lambda t: t[0])
        # the ridden carriageway is the chain closest to the mainline; the opposing one is the
        # NEXT chain sitting a plausible median away (8-30 m median lateral)
        if not cands or cands[0][0] > 8.0:
            print(f"[median] '{road}': could not identify the ridden carriageway — skipped")
            continue
        opp = next((p for lat, p in cands[1:] if 8.0 <= lat <= 30.0), None)
        if opp is None:
            print(f"[median] '{road}': no opposing carriageway found "
                  f"(chain med-lats: {[f'{lat:.1f}' for lat, _ in cands]}) — skipped")
            continue

        # per-mainline-vertex separation to the opposing POLYLINE (segment distance — OSM nodes
        # on straights are 20-60 m apart, so nearest-VERTEX distance balloons between nodes)
        def _seg_dist(px, pz, line):
            best = float("inf")
            for a, b in zip(line, line[1:]):
                ax, az = a
                bx, bz = b
                dx, dz = bx - ax, bz - az
                L2 = dx * dx + dz * dz
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
                best = min(best, math.hypot(px - (ax + t * dx), pz - (az + t * dz)))
            return best

        sep = [_seg_dist(mx, mz, opp) for mx, mz in main_xz]
        ok = [MIN_SEP <= s <= SEP_TRUST for s in sep]
        # runs of ok verts, bridging short out-of-band gaps (turn-pocket flares mid-median)
        i = 0
        while i < n:
            if not ok[i]:
                i += 1
                continue
            j = i
            gap = 0
            while j < n:
                if ok[j]:
                    gap = 0
                elif gap < GAP_BRIDGE:
                    gap += 1
                else:
                    j -= gap
                    break
                j += 1
            else:
                j = n
            while j > i and not ok[j - 1]:
                j -= 1
            # clamp bridged verts' sep into the trust band so shift/width stay continuous
            for k in range(i, j):
                sep[k] = max(MIN_SEP, min(SEP_TRUST, sep[k]))
            run_len = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
                          for k in range(i + 1, j))
            if run_len >= MIN_RUN_M:
                run_ranges.append((road, i, j))
                for k in range(i, j):
                    # taper factor: 0 at run edge -> 1 inside
                    t = min(1.0, (k - i) / TAPER_VERTS, (j - 1 - k) / TAPER_VERTS)
                    t = max(0.0, t)
                    s = sep[k]
                    # lateral direction: toward the nearest opp point
                    mx, mz = main_xz[k]
                    ox, oz = min(opp, key=lambda p: math.hypot(mx - p[0], mz - p[1]))
                    dx, dz = ox - mx, oz - mz
                    dl = math.hypot(dx, dz) or 1.0
                    w_single = widths[k] / 2.0
                    shift[k] = (t * (s / 2.0) * dx / dl, t * (s / 2.0) * dz / dl)
                    new_w[k] = widths[k] + t * (s + w_single - widths[k])
                    if t >= 1.0 and (k - i) >= TAPER_VERTS + ISLAND_PULLBACK and \
                            (j - 1 - k) >= TAPER_VERTS + ISLAND_PULLBACK:
                        island_w[k] = max(ISLAND_MIN_W, min(ISLAND_MAX_W, s - w_single))
                svals = sorted(sep[k] for k in range(i, j))
                print(f"[median] '{road}': divided run verts {i}-{j} ({run_len:.0f} m), "
                      f"sep min/med/max {svals[0]:.1f}/{svals[len(svals) // 2]:.1f}/{svals[-1]:.1f} m, "
                      f"max shift {max(sep[k] for k in range(i, j)) / 2:.1f} m")
            i = j

    # cut island gaps at every connector mouth (left-turn access). Connector polylines are FULL
    # street sweeps — their endpoints sit far up the hill; they meet the mainline mid-polyline.
    # A mouth = a contiguous cluster of mainline verts that any connector point approaches.
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))
    mouths = 0
    MOUTH_REACH = 16.0
    for c in conns.get("connectors", []):
        close = [False] * n
        cpts = [(p[0], p[2]) for p in c["points_xyz_m"]]
        for i, (mx, mz) in enumerate(main_xz):
            if min(math.hypot(mx - x, mz - z) for x, z in cpts[::2]) <= MOUTH_REACH:
                close[i] = True
        i = 0
        while i < n:
            if not close[i]:
                i += 1
                continue
            j = i
            while j < n and close[j]:
                j += 1
            mid = (i + j) // 2
            lo, hi = max(0, i - GAP_HALF), min(n, j + GAP_HALF)
            if any(island_w[m] > 0 for m in range(lo, hi)):
                mouths += 1
                print(f"[median] island gap at {c['name']} mouth (mainline verts {lo}-{hi})")
            for m in range(lo, hi):
                island_w[m] = 0.0
            i = j

    # apply shift + width to the raw snapshot
    for k in range(n):
        pts[k][0] += shift[k][0]
        pts[k][2] += shift[k][1]
    raw["points_xyz_m"] = [[round(v, 4) for v in p] for p in pts]
    raw["widths_m"] = [round(w, 2) for w in new_w]
    raw_path.write_text(json.dumps(raw), encoding="utf-8")

    n_isl = sum(1 for w in island_w if w > 0)
    (data / "median_bands.json").write_text(json.dumps({
        "island_w_by_vertex": [round(w, 2) for w in island_w],
        "runs": [{"road": r, "i": i, "j": j} for r, i, j in run_ranges],
    }), encoding="utf-8")
    print(f"[median] shifted {sum(1 for s in shift if s != (0.0, 0.0))} verts to true center; "
          f"island on {n_isl} verts; {mouths} connector-mouth gaps; wrote data/median_bands.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/median_envelope.py <project-dir>")
    build(sys.argv[1])
