"""Correct Princess View's raised median (MD7) over the tree-shadow run, at the source, from measurement (ledger 0054 Phase 2
step 2c, 2026-11-04).

The automatic aerial reader (expansion.north.json MD7, `median_src` aerial island, one reading every 2.5 m) swung the median's
RIGHT face 3.6 <-> 5.9 m wide at s ~622-650 (lap v533-v542). On NAIP 2022 z18 two street trees stand IN the median there
(v533-535, v537-540): their crowns and westward shadows are what it read as island. The left face holds at +1.4..+1.9 m.
The PC's read (2026-11-04, D:/k10-scratch/lm_phase2/naip/{edges.txt, pv_table.txt}): source/naip_2022_lm_z18.jpg projected
with scripts-v021 projection.py's WGS84 series (a plain-sphere equirectangular is ~9 m E / 5 m N off), calibrated to the built
faces on the clear run v543-v556 (offset -2.58 m), a line fit of the right face: -3.45 m at v535 -> -3.38 m at v556 (lap
frame, + = left of travel, metres off the connector line; sd 0.35 m).

This sets the right face of every piece-B station row inside the run to that line and keeps the left face, in the three
files that carry the median:
  data/expansion.north.json     pieces[B] rows median_w_m / median_off_m (+ MD7 polygon_xz, width_m, `correction`)
  data/median_bands.json        connector_islands north_princess_view: points + widths, the formula of
                                tools/expansion_pieces.decorate (the points keep their heights: the weld warped them)
  data/connectors.local.json    north_princess_view paint: the two median edge lines (MEDIAN_EDGE_M off each face)
and writes the record beside this file (pv_median_correction.json: before / after per lap vertex v530-v557).

    .venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/fix_pv_median.py [--write]

Idempotent: a row already on the line is left as it is. Without --write it prints the table and touches nothing.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402

LINE = "north_princess_view"
LAP_OFFSET = 331                 # lap v = connector vertex + 331 on this piece (race_lap.stitch, the north lap)
V_FROM, V_TO = 533, 542          # the tree-shadow run (lap vertices)
FIT = (535, -3.45, 556, -3.38)   # the PC's line fit of the right face (v, lateral) .. (v, lateral)
SD_M = 0.35
RECORD = HERE / "pv_median_correction.json"
PROVENANCE = {
    "what": "Princess View's raised median MD7, right face over the tree-shadow run lap v533-v542 (piece B s 622.5-647.5)",
    "why": "the automatic aerial reader read two street trees standing in the median (crowns + westward shadows, NAIP 2022 "
           "z18) as island: the right face swung 3.6 <-> 5.9 m wide; the left face held at +1.4..+1.9 m",
    "measured": "the PC, 2026-11-04: NAIP 2022 z18 (source/naip_2022_lm_z18.jpg) on scripts-v021 projection.py's WGS84 series, "
                "calibrated to the built faces on the clear run v543-v556 (offset -2.58 m), line fit of the right face "
                "-3.45 m at v535 -> -3.38 m at v556 (lap frame), sd 0.35 m; files D:/k10-scratch/lm_phase2/naip/edges.txt, "
                "pv_table.txt, step3b_read.txt",
    "method": "the right face of every piece-B row whose lap vertex lies in [533, 542] set to the line fit (extrapolated to "
              "v533-v534); the left face kept; width and offset recomputed; the islands and the median edge paint "
              "re-derived with tools/expansion_pieces.decorate's formula",
    "ledger": "0054 Phase 2 step 2c",
}


def fit_right(v):
    v0, r0, v1, r1 = FIT
    return r0 + (r1 - r0) * (v - v0) / (v1 - v0)


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for a in range(len(xs) - 1):
        if xs[a] <= x <= xs[a + 1]:
            t = (x - xs[a]) / ((xs[a + 1] - xs[a]) or 1.0)
            return ys[a] + (ys[a + 1] - ys[a]) * t
    return ys[-1]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ep_path = PROJECT / "data" / "expansion.north.json"
    doc, pieces = ep.load(ep_path)                 # pc.rec is doc's own piece B: its rows are edited in place
    pc = pieces["B"]
    cp = PROJECT / "data" / "connectors.local.json"
    cdoc = json.loads(cp.read_text(encoding="utf-8"))
    conn = next(c for c in cdoc["connectors"] if c["name"] == LINE)
    P = conn["points_xyz_m"]
    n = len(P)
    st, lat, sense = [], [], []
    for i, p in enumerate(P):
        _dd, s, la = pc.project(p[0], p[2])
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        pt = pc.tangent(s)
        st.append(s)
        lat.append(la)
        sense.append(1.0 if tx * pt[0] + tz * pt[1] >= 0 else -1.0)
    i0, i1 = V_FROM - LAP_OFFSET, V_TO - LAP_OFFSET
    if any(sense[i] < 0 for i in range(i0 - 1, i1 + 2)):
        raise SystemExit("[pv-median] the connector runs against the piece here — the lateral frame would flip; refused")
    vfrac_of_s = lambda s: _interp(st, list(range(n)), s) + LAP_OFFSET  # noqa: E731
    lat_of_s = lambda s: _interp(st, lat, s)  # noqa: E731
    s_lo, s_hi = st[i0], st[i1]

    def faces(i):
        """(left, right) of the island at connector vertex i, lap frame, from the piece rows as they now stand"""
        mw, mo = pc.num(st[i], "median_w_m"), pc.num(st[i], "median_off_m")
        return mo + mw / 2.0 - lat[i], mo - mw / 2.0 - lat[i]

    before = {V_FROM - 3 + k: faces(V_FROM - 3 + k - LAP_OFFSET) for k in range(V_TO - V_FROM + 19)}
    cols = pc.rec["columns"]
    iw_c, io_c = cols.index("median_w_m"), cols.index("median_off_m")
    changed = []
    for r, row in zip(pc.rows, pc.rec["stations"]):
        s = float(row[0])
        lo_s = s_lo - (st[i0] - st[i0 - 1])          # rows between v532 and v533 shape v533 too
        if not (lo_s < s <= s_hi + 1e-6) or row[cols.index("median_type")] not in ep.RAISED:
            continue
        v = vfrac_of_s(s)
        if v < V_FROM - 1 or v > V_TO + 1e-6:
            continue
        la = lat_of_s(s)
        mw, mo = float(row[iw_c]), float(row[io_c])
        left_p = mo + mw / 2.0
        right_p = fit_right(max(v, V_FROM)) + la
        new_w, new_o = round(left_p - right_p, 2), round((left_p + right_p) / 2.0, 2)
        if abs(new_w - mw) < 0.005 and abs(new_o - mo) < 0.005:
            continue
        changed.append({"s": s, "lap_v": round(v, 2), "median_w_m": [mw, new_w], "median_off_m": [mo, new_o]})
        row[iw_c], row[io_c] = new_w, new_o
        r["median_w_m"], r["median_off_m"] = new_w, new_o
    after = {v: faces(v - LAP_OFFSET) for v in before}
    print("lap v | before L / R / width / centre  ->  after L / R / width / centre   (lap frame, m)")
    table = []
    for v in sorted(before):
        (bl, br), (al, ar) = before[v], after[v]
        table.append({"lap_v": v, "before": {"left": round(bl, 3), "right": round(br, 3), "width": round(bl - br, 3),
                                             "centre": round((bl + br) / 2, 3)},
                      "after": {"left": round(al, 3), "right": round(ar, 3), "width": round(al - ar, 3),
                                "centre": round((al + ar) / 2, 3)}})
        mark = "  *" if abs(br - ar) > 1e-3 else ""
        print(f"v{v} | {bl:+.2f} / {br:+.2f} / {bl - br:.2f} / {(bl + br) / 2:+.2f}  ->  {al:+.2f} / {ar:+.2f} / "
              f"{al - ar:.2f} / {(al + ar) / 2:+.2f}{mark}")
    print(f"[pv-median] {len(changed)} piece-B rows on the line")
    if "--write" not in argv:
        return 0
    # MD7: polygon (the face points of the changed rows), width range, the correction record
    md7 = next(m for m in doc["medians"] if m["id"] == "MD7")
    pts = md7["polygon_xz"]
    new_doc_rows = {float(r[0]): r for r in pc.rec["stations"]}
    for ch in changed:
        s = ch["s"]
        (px, pz), t, nl = pc.frame(s)
        for old_mw, old_mo, new_mw, new_mo in ((ch["median_w_m"][0], ch["median_off_m"][0], ch["median_w_m"][1],
                                                ch["median_off_m"][1]),):
            for sg in (1.0, -1.0):
                oe, ne = old_mo + sg * old_mw / 2.0, new_mo + sg * new_mw / 2.0
                old_xz = (px + nl[0] * oe, pz + nl[1] * oe)
                q = min(range(len(pts)), key=lambda k: math.hypot(pts[k][0] - old_xz[0], pts[k][1] - old_xz[1]))
                if math.hypot(pts[q][0] - old_xz[0], pts[q][1] - old_xz[1]) < 0.05:
                    pts[q] = [round(px + nl[0] * ne, 3), round(pz + nl[1] * ne, 3)]
    ws = [float(r[iw_c]) for s_, r in new_doc_rows.items() if md7["s_from"] <= s_ <= md7["s_to"]]
    md7["width_m"] = [round(min(ws), 2), round(max(ws), 2)]
    md7["correction"] = dict(PROVENANCE, rows=changed)
    ep_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")   # the file's own format
    # the island + the edge paint, at the connector vertices the changed rows shape (decorate's formula)
    _d, pieces = ep.load(ep_path)
    pc = pieces["B"]
    mbp = PROJECT / "data" / "median_bands.json"
    mb = json.loads(mbp.read_text(encoding="utf-8"))
    isl = next(ci for ci in mb["connector_islands"] if ci["name"] == LINE)
    lines = conn.get("paint", {}).get("lines") or []
    touched = []
    for i in range(i0 - 1, i1 + 2):
        s = st[i]
        mw, mo = pc.num(s, "median_w_m"), pc.num(s, "median_off_m")
        a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        Lt = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / Lt, tx / Lt
        o = sense[i] * (mo - lat[i])
        old_w = float(isl["island_w_by_point"][i])
        old_p = isl["points_xyz_m"][i]
        new_p = [round(P[i][0] + nx * o, 3), old_p[1], round(P[i][2] + nz * o, 3)]
        if abs(round(mw, 3) - old_w) < 1e-6 and math.hypot(new_p[0] - old_p[0], new_p[2] - old_p[2]) < 1e-3:
            continue
        # the two median edge lines (their old offsets identify them)
        bl, br = before[i + LAP_OFFSET]
        for old_off, new_off in ((bl + ep.MEDIAN_EDGE_M, (mo + mw / 2.0 - lat[i]) + ep.MEDIAN_EDGE_M),
                                 (br - ep.MEDIAN_EDGE_M, (mo - mw / 2.0 - lat[i]) - ep.MEDIAN_EDGE_M)):
            for ln in lines:
                if ln["off"][i] is not None and abs(ln["off"][i] - old_off) < 0.005:
                    ln["off"][i] = round(new_off, 3)
                    break
        isl["island_w_by_point"][i] = round(mw, 3)
        isl["points_xyz_m"][i] = new_p
        touched.append(i + LAP_OFFSET)
    mbp.write_text(json.dumps(mb), encoding="utf-8")
    cp.write_text(json.dumps(cdoc), encoding="utf-8")
    RECORD.write_text(json.dumps(dict(PROVENANCE, fit={"v0": FIT[0], "right0_m": FIT[1], "v1": FIT[2], "right1_m": FIT[3],
                                                       "sd_m": SD_M},
                                      rows=changed, island_vertices=touched, table=table), indent=1) + "\n",
                      encoding="utf-8")
    print(f"[pv-median] wrote expansion.north.json ({len(changed)} rows), median_bands.json + connectors.local.json "
          f"(lap v{touched[0]}..v{touched[-1]}, {len(touched)} vertices), {RECORD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
