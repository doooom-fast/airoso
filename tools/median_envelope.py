"""Measure a divided road's real median from the OSM dual-carriageway geometry and re-center
the road ribbon over it.

The C1 fix deleted the broken split-carriageway ribbons (ledger 0029/0032/0035) but left the
mainline riding ONE carriageway's alignment at combined width — Kevin's seat: "it loses realism,
that road doesn't look like that there" (0037). The pro pattern (docs/JUNCTIONS.md, rt_macau):
ONE continuous pavement slab, with the median standing ON it as a raised island.

This tool does the data half:
  1. finds the opposing carriageway chain for each route.median_islands road (median-lateral
     chain classification with the ridden chain explicitly excluded — mean-based selection once
     picked the mainline's own chain as "opposing");
  2. decomposes each mainline vertex's offset to the opposing POLYLINE (segment distance — OSM
     nodes are 20-60 m apart on straights) into lateral + along components, and trusts a vertex
     only when the offset is genuinely LATERAL (|along| <= 0.5*|lat|), at least 11 m, and the two
     carriageways (opposing way - ridden way) are at most 24 m apart — near corners the nearest
     "opposing" geometry is the CROSS street and the raw vector drags the road along its own axis
     (the Navajo jank, 2026-08-20: an 11.24 m sideways step at vert 1501). The upper bound was the
     raw line's offset until ledger 0055 (College Ave's split section, see `trusted`);
  3. shifts the RAW centerline by the smoothed signed lateral/2 toward the true middle and widens
     the ribbon to span both carriageways, tapered over ~36 m at run ends — never a step;
  4. trims runs of DIFFERENT roads that meet at a shared corner back to a neutral buffer (real
     medians end before the intersection; overlapping runs were the other half of the jank);
  5. writes data/median_bands.json (per-vertex island widths, gapped at every connector mouth);
  6. SELF-GATE: re-measures its own output — any displacement step > 1.2 m between consecutive
     verts restores the pristine backup and exits 1. This tool must never ship a step.

Edits data/centerline.raw.local.json IN PLACE (backup: .pre-median, written once; every run
re-derives from the backup, so the tool is idempotent).
The Blender half is tools/author_median_blend.py — run AFTER build_loop_blend.

    python tools/median_envelope.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MIN_SEP = 11.0        # carriageways this far apart = real median between them
SEP_TRUST = 24.0      # carriageways (opposing way - ridden way) further apart than this: a junction flare /
#                       wrong-chain match — untrusted (ledger 0055: the separation, not the raw line's offset)
RIDDEN_MAX_M = 8.0    # the ridden carriageway's way lies within this of the raw line (chain pick + trust test)
MIN_RUN_M = 120.0
GAP_BRIDGE = 8        # out-of-band verts (~24 m) tolerated INSIDE a run (turn-pocket flares)
TAPER_VERTS = 16      # ~48 m blend of shift+width at run ends (cosine ramp — see _ramp)
MIN_RADIUS_MARGIN = 1.0   # self-gate: turn radius must exceed the (widened) half-width + this
CORNER_BUFFER = 10    # neutral verts kept between two different roads' runs at a shared corner
ISLAND_MIN_W, ISLAND_MAX_W = 1.5, 7.0
ISLAND_PULLBACK = 5
GAP_HALF = 6          # island gap half-length (verts, ~18 m) around each connector mouth
CLIP_REACH = 45.0
MAX_STEP_M = 1.2      # self-gate: max allowed displacement change between consecutive verts


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


def _nearest_on_polyline(px, pz, line):
    best, bp = float("inf"), (line[0][0], line[0][1])
    for a, b in zip(line, line[1:]):
        ax, az = a
        bx, bz = b
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
        qx, qz = ax + t * dx, az + t * dz
        d = math.hypot(px - qx, pz - qz)
        if d < best:
            best, bp = d, (qx, qz)
    return best, bp


def _ridden_lat(mx, mz, lxn, lzn, ridden):
    """(signed lateral of the RIDDEN carriageway's way from the raw vertex along the same normal, its plan distance)"""
    d, (rx, rz) = _nearest_on_polyline(mx, mz, ridden)
    return (rx - mx) * lxn + (rz - mz) * lzn, d


def trusted(vlat, valong, rlat, rdist):
    """Is this vertex's offset to the OPPOSING carriageway a real median (ledger 0055)?

    The lower bound and the lateral test read the raw centreline's offset to the opposing way (as before): a
    vertex less than MIN_SEP from it rides no median, and an offset that is mostly ALONG the road is a cross
    street near a corner. The UPPER bound reads what it means — the two CARRIAGEWAYS' separation (opposing
    lateral minus ridden lateral), not the raw line's distance to the far one. On College Ave the raw line sits on
    the aerial's southbound carriageway while OSM draws both ways ~3.5 m east of their pavement, so the raw-line
    offset read 24.1-24.7 m over v1282-1350 where the carriageways are 20.5-21.2 m apart: the run split in two,
    each end tapered, and the road swerved off the northbound carriageway onto the southbound one and back
    (Kevin: "one of the lanes swerves into where the other lane should be"). The ridden way must be within
    RIDDEN_MAX_M of the vertex (the bound that picked it as the ridden chain), else the separation is unknown."""
    s = abs(vlat)
    return (MIN_SEP <= s and abs(vlat - rlat) <= SEP_TRUST and abs(valong) <= 0.5 * s
            and rdist <= RIDDEN_MAX_M)


def _median_filter(v, half=2):
    n = len(v)
    return [sorted(v[max(0, k - half):min(n, k + half + 1)])[
            len(v[max(0, k - half):min(n, k + half + 1)]) // 2] for k in range(n)]


def _mean_smooth(v, half=4):
    n = len(v)
    return [sum(v[max(0, k - half):min(n, k + half + 1)]) /
            len(v[max(0, k - half):min(n, k + half + 1)]) for k in range(n)]


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

    def _tangent(k):
        a, b = pts[max(0, k - 1)], pts[min(n - 1, k + 1)]
        dx, dz = b[0] - a[0], b[2] - a[2]
        d = math.hypot(dx, dz) or 1.0
        return dx / d, dz / d

    per_road_lat = {}
    road_runs = []

    for road in roads:
        chs = [c for c in _chains(byname.get(road, [])) if len(c) >= 10]
        cands = []
        for c in chs:
            xz = [((lo - lon0) * m_lon, (la - lat0) * m_lat) for lo, la in c]
            near = [p for p in xz if min(math.hypot(p[0] - mx, p[1] - mz)
                                         for mx, mz in main_xz[::4]) <= CLIP_REACH]
            if len(near) < 20:
                continue
            lats = sorted(min(math.hypot(x - mx, z - mz) for mx, mz in main_xz[::4])
                          for x, z in near)
            cands.append((lats[len(lats) // 2], xz))
        cands.sort(key=lambda t: t[0])
        if not cands or cands[0][0] > RIDDEN_MAX_M:
            print(f"[median] '{road}': could not identify the ridden carriageway — skipped")
            continue
        ridden = cands[0][1]
        opp = next((p for lat, p in cands[1:] if 8.0 <= lat <= 30.0), None)
        if opp is None:
            print(f"[median] '{road}': no opposing carriageway found "
                  f"(chain med-lats: {[f'{lat:.1f}' for lat, _ in cands]}) — skipped")
            continue

        lat_signed = [0.0] * n
        ok = [False] * n
        self_blocked = 0
        for k, (mx, mz) in enumerate(main_xz):
            d, (qx, qz) = _nearest_on_polyline(mx, mz, opp)
            if d > SEP_TRUST * 1.5:
                continue
            tx, tz = _tangent(k)
            lxn, lzn = -tz, tx
            vlat = (qx - mx) * lxn + (qz - mz) * lzn
            valong = (qx - mx) * tx + (qz - mz) * tz
            s = abs(vlat)
            lat_signed[k] = vlat
            ok[k] = trusted(vlat, valong, *_ridden_lat(mx, mz, lxn, lzn, ridden))
            # SELF-PROXIMITY GUARD. Where the loop runs beside ITSELF (College's south end: the
            # outbound leg hairpins at verts 760-770 and comes back 22.8 m away), re-centring and
            # widening the ribbon walked it onto its own other leg — the shifted deck sat 1.2 m over
            # the approach, grass over road, an 18 m "hole" at verts 721-726 (2026-10-08). A vertex
            # whose widened ribbon would come within 1 m of any other part of the loop is not a
            # median candidate; the run simply starts past the self-adjacent stretch.
            if ok[k]:
                half_new = (s + widths[k] / 2.0) / 2.0
                # judge the SHIFTED centre (the ribbon moves s/2 toward the opposing side) — the
                # unshifted test cleared 22.8 m at verts 722/809 while the shifted ribbon collided
                sx = mx + lxn * (vlat / 2.0)
                sz = mz + lzn * (vlat / 2.0)
                cx0, cz0 = int(sx // 25.0), int(sz // 25.0)
                for q in range(max(0, k - 400), min(n, k + 400)):
                    if abs(q - k) < 40:
                        continue
                    qx2, qz2 = main_xz[q]
                    if abs(int(qx2 // 25.0) - cx0) > 2 or abs(int(qz2 // 25.0) - cz0) > 2:
                        continue
                    if math.hypot(qx2 - sx, qz2 - sz) < half_new + widths[q] / 2.0 + 1.0:
                        ok[k] = False
                        self_blocked += 1
                        break
        if self_blocked:
            print(f"[median] '{road}': {self_blocked} vert(s) excluded — widened ribbon would touch "
                  f"another part of the loop (self-adjacent stretch)")
        per_road_lat[road] = lat_signed

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
            run_len = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
                          for k in range(i + 1, j))
            if run_len >= MIN_RUN_M:
                road_runs.append([road, i, j])
            i = j

    # neutral corner buffer between runs of DIFFERENT roads (their shared intersection):
    # overlapping/abutting runs were half the Navajo jank — an 11 m step where one road's
    # full shift met the other road's zero.
    road_runs.sort(key=lambda r: r[1])
    for a, b in zip(road_runs, road_runs[1:]):
        if a[0] != b[0] and b[1] < a[2] + 2 * TAPER_VERTS + CORNER_BUFFER:
            mid = (min(a[2], b[1]) + max(a[2], b[1])) // 2
            a[2] = min(a[2], mid - CORNER_BUFFER // 2)
            b[1] = max(b[1], mid + CORNER_BUFFER // 2)
    road_runs = [r for r in road_runs if r[2] - r[1] > 2 * TAPER_VERTS]

    shift = [(0.0, 0.0)] * n
    new_w = list(widths)
    island_w = [0.0] * n

    for road, i, j in road_runs:
        lat = per_road_lat[road][i:j]
        # majority sign, spike/flip-proof: median filter then mean smooth on the signed lateral
        sgn = 1.0 if sum(1 for v in lat if v > 0) >= len(lat) / 2 else -1.0
        mag = _mean_smooth(_median_filter([abs(v) for v in lat]))
        run_len = sum(math.hypot(pts[k][0] - pts[k - 1][0], pts[k][2] - pts[k - 1][2])
                      for k in range(i + 1, j))
        for idx, k in enumerate(range(i, j)):
            # COSINE RAMP, not linear. A linear 12 m shift over 36 m puts an 18-degree kink at each
            # end of the taper (1 m lateral per 3 m vertex); on a ribbon widened to 15 m half-width
            # that is R≈9 m < half-width — the inside edge folds over itself (found 2026-10-08 as
            # fold verts 768-772 / 1512-1516 on Lake Murray r2). The cosine ramp's minimum radius is
            # 2L²/(Sπ²): 48 m for 12 m ≈ 39 m, comfortably above any half-width here.
            t_lin = max(0.0, min(1.0, idx / TAPER_VERTS, (j - 1 - k) / TAPER_VERTS))
            t = 0.5 - 0.5 * math.cos(math.pi * t_lin)
            s = max(MIN_SEP, min(SEP_TRUST, mag[idx]))
            tx, tz = _tangent(k)
            lxn, lzn = -tz, tx
            shift[k] = (t * (s / 2.0) * sgn * lxn, t * (s / 2.0) * sgn * lzn)
            w_single = widths[k] / 2.0
            new_w[k] = widths[k] + t * (s + w_single - widths[k])
            if t >= 1.0 and idx >= TAPER_VERTS + ISLAND_PULLBACK and \
                    (j - 1 - k) >= TAPER_VERTS + ISLAND_PULLBACK:
                island_w[k] = max(ISLAND_MIN_W, min(ISLAND_MAX_W, s - w_single))
        svals = sorted(max(MIN_SEP, min(SEP_TRUST, m)) for m in mag)
        print(f"[median] '{road}': divided run verts {i}-{j} ({run_len:.0f} m), "
              f"lat min/med/max {svals[0]:.1f}/{svals[len(svals) // 2]:.1f}/{svals[-1]:.1f} m, "
              f"side {'+' if sgn > 0 else '-'}")

    # island gaps at every connector mouth (connectors meet the mainline MID-polyline)
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
            lo, hi = max(0, i - GAP_HALF), min(n, j + GAP_HALF)
            if any(island_w[m] > 0 for m in range(lo, hi)):
                mouths += 1
                print(f"[median] island gap at {c['name']} mouth (mainline verts {lo}-{hi})")
            for m in range(lo, hi):
                island_w[m] = 0.0
            i = j

    for k in range(n):
        pts[k][0] += shift[k][0]
        pts[k][2] += shift[k][1]

    # SELF-GATE 1: the output must be step-free before it is allowed to exist on disk
    disp = [math.hypot(shift[k][0], shift[k][1]) for k in range(n)]
    worst = max((abs(disp[k] - disp[k - 1]), k) for k in range(1, n))
    if worst[0] > MAX_STEP_M:
        raw_path.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[median] FAIL: displacement step {worst[0]:.2f} m at vert {worst[1]} "
              f"(limit {MAX_STEP_M}) — raw restored from backup, nothing shipped")
        sys.exit(1)
    # SELF-GATE 2: no shifted vertex may turn tighter than its own half-width — a ribbon whose
    # turn radius is below half-width folds its inside edge over itself (faces invert, the kn5
    # drops them, the sidewalk lands in the lane). Only shifted verts are judged: the ring's own
    # sharp corners are a separate, pre-existing class (0034 / C3).
    worst_r = (float("inf"), -1)
    for k in range(1, n - 1):
        if shift[k] == (0.0, 0.0):
            continue
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        t1 = math.atan2(b[2] - a[2], b[0] - a[0])
        t2 = math.atan2(c[2] - b[2], c[0] - b[0])
        d = (t2 - t1 + math.pi) % (2 * math.pi) - math.pi
        seg = (math.hypot(b[0] - a[0], b[2] - a[2]) + math.hypot(c[0] - b[0], c[2] - b[2])) / 2
        r = seg / abs(d) if abs(d) > 1e-9 else float("inf")
        need = new_w[k] / 2.0 + MIN_RADIUS_MARGIN
        if r - need < worst_r[0] - (new_w[worst_r[1]] / 2.0 + MIN_RADIUS_MARGIN if worst_r[1] >= 0 else 0):
            worst_r = (r, k)
        if r < need:
            raw_path.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[median] FAIL: turn radius {r:.1f} m at shifted vert {k} < half-width+margin "
                  f"{need:.1f} m (inside edge would fold) — raw restored, nothing shipped")
            sys.exit(1)

    raw["points_xyz_m"] = [[round(v, 4) for v in p] for p in pts]
    raw["widths_m"] = [round(w, 2) for w in new_w]
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    n_isl = sum(1 for w in island_w if w > 0)
    (data / "median_bands.json").write_text(json.dumps({
        "island_w_by_vertex": [round(w, 2) for w in island_w],
        "runs": [{"road": r, "i": i, "j": j} for r, i, j in road_runs],
    }), encoding="utf-8")
    print(f"[median] shifted {sum(1 for s in shift if s != (0.0, 0.0))} verts; island on {n_isl} "
          f"verts; {mouths} mouth gaps; worst step {worst[0]:.2f} m at vert {worst[1]} — OK")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/median_envelope.py <project-dir>")
    build(sys.argv[1])
