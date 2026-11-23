"""Correct Mission Gorge Rd's raised median MD13 where it crosses Margerum Avenue / Mission Vista Drive, at the source,
from measurement (ledger 0099 round 3, item 1b; 2026-11-23). The MD7 precedent: source/expansion/phase2/fix_pv_median.py.

The plan's median width on piece C is linear between eye readings 250 m apart (st 1000: 4.5 m, st 1250: 5.5 m), so MD13
is declared as one unbroken island 4.5-5.4 m wide through a real crossing. NAIP 2022 (faces_md.py, md13_faces_*.json;
README.md) shows, in the piece frame (+ = left of J3 -> J4 travel = north-west):

  s 1087.5-1117.5   no median at all (marked crosswalks on all four legs; both side streets are built stubs there);
  s 1010-1085       a strip 1.96 m wide, its middle 0.43 m left of the line the full island's middle follows;
  s 1120-1192.5     a strip 1.84 m wide, its middle 1.50 m right of that line (the turn pocket is on its left);
  s 982.5-1010 and s 1192.5-1212.5   the island narrowing from / widening to its declared band.

THE FIT (below) is those numbers. They are medians over 24 and 26 stations of the photo's equivalent width and centroid,
set against the same measure on the stretches where the island fills its band (so the width carries +0.30 m and the
middle +0.49 m: what the measure reads short / right of the declared band there). One station scatters about +-1.3 m in
width and +-0.55 m in the middle on those stretches, so each strip's width holds to about +-0.15 m and its middle to
about +-0.12 m by count alone; what the method does on a strip narrower than the photo resolves beyond that is not
measured. The taper s 1192.5-1212.5 lies under tree shadow on the photo: its two ends are measured, its line between
them is [inferred].

This sets, in the three files that carry the median:
  data/expansion.north.json     pieces[C] rows median_w_m / median_off_m / median_type over s 982.5-1212.5; MD13 ends at
                                s 1085 (its ring re-cut, the generator's own nose rule); a new MD13b runs s 1120-2245
                                (the rest of the old ring, a new nose at its start), so no other median's id moves
  data/median_bands.json        connector_islands north_mission_gorge
  data/connectors.local.json    north_mission_gorge's paint
the last two by tools/expansion_pieces.decorate itself, run on a copy of the project, its piece-C output alone carried
over (the other pieces' records are not touched). Then ONE thing is taken out that decorate's rule puts in: where a
road has no median its rule paints a double yellow on the centre, which here would run through the crossing. Nothing is
drawn inside the crossing (no centre line, no crosswalk, no stop line: none of it is measured), so the two centre
lines' offsets are cleared at the points between the two noses. Lane and bike lines run on as they do past every other
stub mouth.

    python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py [--write]

Idempotent: the declared values are kept in the record (mg_median_correction.json) and every run starts from them.
Without --write it prints the table and touches nothing."""
from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402

LINE, PIECE, ISLAND, NEW_ISLAND = "north_mission_gorge", "C", "MD13", "MD13b"
RECORD = HERE / "mg_median_correction.json"
# THE FIT. (d centre, width): the strip's middle off the line the declared middle follows (+ = left), and its width
STRIP_A = (0.43, 1.96)
STRIP_B = (-1.50, 1.84)
JOIN_A, STRIP_A_FROM, NOSE_A = 982.5, 1010.0, 1085.0     # the declared band to s 982.5; strip A from 1010; its nose 1085
NOSE_B, STRIP_B_TO, JOIN_B = 1120.0, 1192.5, 1212.5      # strip B's nose at 1120; strip B to 1192.5; declared from 1212.5
NOSE_M, NOSE_W_M = 6.0, 0.6                              # tools/author_expansion.py: a median's ring tapers to its nose
PROVENANCE = {
    "what": "Mission Gorge Rd's raised median MD13 over piece C s 982.5-1212.5: the Margerum Avenue / Mission Vista Drive "
            "crossing (no median s 1085-1120) and the narrow strips beside its two turn pockets",
    "why": "the plan's median width is linear between eye readings 250 m apart and holds no crossing there: MD13 was declared, "
           "and built, as one unbroken island 4.5-5.4 m wide across a real crossing whose two side streets are built stubs",
    "measured": "the PC, 2026-11-23: NAIP 2022 z18 full mosaic (source/naip_2022_lm_full_z18.jpg, sha256 1764a80b...) with "
                "source/expansion/mg_median/faces_md.py: per station the equivalent width (excess R - G summed across the island "
                "over a full island's plateau, +24.0 over the asphalt's -1.0) and the excess's centroid; medians over 24 "
                "stations (s 1012.5-1077.5: 1.66 m, +0.18 m) and 26 stations (s 1127.5-1192.5: 1.54 m, -2.24 m), against the "
                "same measure where the island fills its band (37 stations: width 0.30 m short, middle 0.49 m right of the "
                "declared band; one station p10..p90 -1.41..+1.23 m in width, -0.94..+0.18 m in the middle)",
    "method": "piece C rows inside s 982.5-1212.5 set to the fit (linear tapers from / to the declared band; type none and "
              "width 0 between the noses); MD13 re-cut to end at s 1085 and MD13b added from s 1120 with the generator's nose "
              "rule; the island and the paint re-derived by tools/expansion_pieces.decorate (piece C's output only); the two "
              "centre lines cleared between the noses",
    "inferred": "the taper s 1192.5-1212.5 lies under tree shadow on the photo: its two ends are measured, the line between is "
                "[inferred]",
    "centre_paint_between_the_noses": {
        "what": "no centre line: the two lines decorate's rule draws where a road has no median are cleared at the points "
                "between the noses",
        "source": "photo",
        "measured": "the PC, 2026-11-23, the same mosaic: within 3 m of the declared centre over s 1090-1112.5 (ten stations) "
                    "the yellowest pixel reads (R + G) / 2 - B = +3.5 to +7.5, the asphalt 5-8 m either side +1.5 to +5.5: no more "
                    "than 5.5 levels over it. What a double yellow reads at this resolution was not measured on this photo, so "
                    "the reading is 'no yellower than the asphalt', not a threshold passed"},
    "ledger": "0099 round 3, item 1b",
}


def fit(s, w0, o0):
    """(type, width, offset) at station s, from the DECLARED width w0 and offset o0"""
    if s < JOIN_A - 1e-9 or s > JOIN_B + 1e-9:
        return "terracotta", w0, o0
    if s <= STRIP_A_FROM:
        t = (s - JOIN_A) / (STRIP_A_FROM - JOIN_A)
        return "terracotta", w0 + (STRIP_A[1] - w0) * t, o0 + STRIP_A[0] * t
    if s <= NOSE_A + 1e-9:
        return "terracotta", STRIP_A[1], o0 + STRIP_A[0]
    if s < NOSE_B - 1e-9:
        return "none", 0.0, o0
    if s <= STRIP_B_TO:
        return "terracotta", STRIP_B[1], o0 + STRIP_B[0]
    t = (JOIN_B - s) / (JOIN_B - STRIP_B_TO)
    return "terracotta", w0 + (STRIP_B[1] - w0) * t, o0 + STRIP_B[0] * t


def ring_side(pc, stations, s0, s1):
    """(left points, right points) of a raised median's ring over its stations: tools/author_expansion.py's rule (the
    width tapers over NOSE_M to NOSE_W_M at the run's two ends s0 / s1; the middle on median_off_m)"""
    left, right = [], []
    for s in stations:
        w = pc.num(s, "median_w_m")
        taper = min(1.0, (s - s0) / NOSE_M, (s1 - s) / NOSE_M)
        w = max(NOSE_W_M, w * max(0.0, taper))
        (px, pz), _t, nl = pc.frame(s)
        o = pc.num(s, "median_off_m")
        left.append([round(px + nl[0] * (o + w / 2.0), 3), round(pz + nl[1] * (o + w / 2.0), 3)])
        right.append([round(px + nl[0] * (o - w / 2.0), 3), round(pz + nl[1] * (o - w / 2.0), 3)])
    return left, right


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    write = "--write" in argv
    ep_path = PROJECT / "data" / "expansion.north.json"
    doc, pieces = ep.load(ep_path)
    pc = pieces[PIECE]
    cols = pc.rec["columns"]
    iw_c, io_c, it_c = cols.index("median_w_m"), cols.index("median_off_m"), cols.index("median_type")
    rec0 = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else None
    declared = {float(r["s"]): r for r in (rec0 or {}).get("rows", [])}
    changed, table = [], []
    for row in pc.rec["stations"]:
        s = float(row[0])
        if not (JOIN_A - 1e-9 <= s <= JOIN_B + 1e-9):
            continue
        d = declared.get(s)
        w0, o0, t0 = (d["median_w_m"][0], d["median_off_m"][0], d["median_type"][0]) if d else (float(row[iw_c]), float(row[io_c]), row[it_c])
        ty, w, o = fit(s, w0, o0)
        w, o = round(w, 2), round(o, 2)
        if d and (float(row[iw_c]), float(row[io_c]), row[it_c]) not in ((w0, o0, t0), (w, o, ty)):
            raise SystemExit(f"[mg-median] piece C row s {s} holds {row[iw_c]} / {row[io_c]} / {row[it_c]}: neither the declared "
                             f"values of the record nor the fit's; refused")
        changed.append({"s": s, "median_type": [t0, ty], "median_w_m": [w0, w], "median_off_m": [o0, o]})
        table.append((s, w0, o0, ty, w, o))
    print("  s       declared: width  left / right     ->  fit: type        width  left / right   (piece frame, m; + = left)")
    for s, w0, o0, ty, w, o in table:
        if abs(s / 12.5 - round(s / 12.5)) < 1e-9 or abs(s - NOSE_A) < 1.3 or abs(s - NOSE_B) < 1.3:
            print(f"  {s:7.1f}   {w0:5.2f}  {o0 + w0 / 2:+5.2f} / {o0 - w0 / 2:+5.2f}   ->  {ty:11s}  {w:5.2f}  "
                  + (f"{o + w / 2:+5.2f} / {o - w / 2:+5.2f}" if w > 0 else "   (no median)"))
    print(f"[mg-median] {len(changed)} piece-C rows in s {JOIN_A}-{JOIN_B}; no median over {sum(1 for c in changed if c['median_w_m'][1] == 0)} of them")
    if not write:
        return 0

    by_s = {c["s"]: c for c in changed}
    for row in pc.rec["stations"]:
        c = by_s.get(float(row[0]))
        if c:
            row[it_c], row[iw_c], row[io_c] = c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]
    doc2, pieces2 = doc, {p["id"]: ep.Piece(p) for p in doc["pieces"]}       # the rows as they now stand
    pc = pieces2[PIECE]
    # MD13 ends at NOSE_A; MD13b runs from NOSE_B. The ring's points outside the changed stretch are kept as they are
    meds = doc2["medians"]
    old = next(m for m in meds if m["id"] == ISLAND)
    have_new = next((m for m in meds if m["id"] == NEW_ISLAND), None)
    if have_new is None:
        s_from, s_to = float(old["s_from"]), float(old["s_to"])
        ring = old["polygon_xz"]
        n = len(ring) // 2
        step = (s_to - s_from) / (n - 1)
        st = [round(s_from + k * step, 4) for k in range(n)]
        L0, R0 = ring[:n], ring[n:][::-1]                          # left then right, both by station
        ring0 = {"s_from": s_from, "s_to": s_to, "points": len(ring)}
    else:
        r0 = (rec0 or {}).get("ring_before")
        if not r0:
            raise SystemExit(f"[mg-median] {NEW_ISLAND} exists and the record holds no ring_before; refused")
        s_from, s_to = float(old["s_from"]), float(have_new["s_to"])
        na, nb = len(old["polygon_xz"]) // 2, len(have_new["polygon_xz"]) // 2
        st_a = [round(s_from + k * 2.5, 4) for k in range(na)]
        st_b = [round(float(have_new["s_from"]) + k * 2.5, 4) for k in range(nb)]
        L0 = dict(zip(st_a, old["polygon_xz"][:na])) | dict(zip(st_b, have_new["polygon_xz"][:nb]))
        R0 = dict(zip(st_a, old["polygon_xz"][na:][::-1])) | dict(zip(st_b, have_new["polygon_xz"][nb:][::-1]))
        st = sorted(L0)
        L0, R0 = [L0[s] for s in st], [R0[s] for s in st]
        ring0 = r0
    if abs((st[1] - st[0]) - 2.5) > 1e-6:
        raise SystemExit(f"[mg-median] {ISLAND}'s ring is not one point per 2.5 m station; refused")

    def cut(a, b, nose_at_start, nose_at_end):
        ks = [k for k, s in enumerate(st) if a - 1e-9 <= s <= b + 1e-9]
        ss = [st[k] for k in ks]
        newL, newR = ring_side(pc, ss, a if nose_at_start else -1e9, b if nose_at_end else 1e9)
        Lp, Rp = [], []
        for j, k in enumerate(ks):
            keep = st[k] < JOIN_A - 1e-9 or st[k] > JOIN_B + 1e-9
            Lp.append(L0[k] if keep else newL[j])
            Rp.append(R0[k] if keep else newR[j])
        ws = [pc.num(s, "median_w_m") for s in ss]
        return {"s_from": round(a, 2), "s_to": round(b, 2), "width_m": [round(min(ws), 2), round(max(ws), 2)], "polygon_xz": Lp + Rp[::-1]}

    a_part = cut(s_from, NOSE_A, False, True)
    b_part = cut(NOSE_B, s_to, True, False)
    corr = dict(PROVENANCE, fit={"strip_a": {"d_centre_m": STRIP_A[0], "width_m": STRIP_A[1], "s": [STRIP_A_FROM, NOSE_A]},
                                 "strip_b": {"d_centre_m": STRIP_B[0], "width_m": STRIP_B[1], "s": [NOSE_B, STRIP_B_TO]},
                                 "tapers_s": [[JOIN_A, STRIP_A_FROM], [STRIP_B_TO, JOIN_B]], "no_median_s": [NOSE_A, NOSE_B]})
    old.update(a_part, correction=dict(corr, split="the run from s %.1f is %s" % (NOSE_B, NEW_ISLAND)))
    corr_b = dict(corr, split="split off %s, which ends at s %.1f" % (ISLAND, NOSE_A))
    if have_new is None:
        meds.insert(meds.index(old) + 1, {"id": NEW_ISLAND, "piece": PIECE, "type": old["type"], "raised": True, **b_part,
                                          "correction": corr_b})
    else:
        have_new.update(b_part, correction=corr_b)
    ep_path.write_text(json.dumps(doc2, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")   # the file's own format

    # the island and the paint: decorate's own output for piece C, off a copy of the project
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "data").mkdir()
        for f in ("track.config.json", "data/expansion.north.json", "data/connectors.local.json", "data/median_bands.json"):
            shutil.copyfile(PROJECT / f, tmp / f)
        ep.decorate(tmp)
        cdoc_t = json.loads((tmp / "data" / "connectors.local.json").read_text(encoding="utf-8"))
        mb_t = json.loads((tmp / "data" / "median_bands.json").read_text(encoding="utf-8"))
    cp, mbp = PROJECT / "data" / "connectors.local.json", PROJECT / "data" / "median_bands.json"
    cdoc = json.loads(cp.read_text(encoding="utf-8"))
    mb = json.loads(mbp.read_text(encoding="utf-8"))
    conn = next(c for c in cdoc["connectors"] if c["name"] == LINE)
    conn_t = next(c for c in cdoc_t["connectors"] if c["name"] == LINE)
    if conn["points_xyz_m"] != conn_t["points_xyz_m"]:
        raise SystemExit("[mg-median] decorate moved the connector's own points; refused")
    isl = next(ci for ci in mb["connector_islands"] if ci["name"] == LINE)
    isl_t = next(ci for ci in mb_t["connector_islands"] if ci["name"] == LINE)
    P = conn["points_xyz_m"]
    stn = [pc.project(p[0], p[2])[1] for p in P]
    # the centre's double yellow between the noses: decorate's own two offsets at each such point (expansion_pieces.layout:
    # moff +- DOUBLE_HALF_M where the road has no median), found by value and cleared
    gap_pts = [i for i, s in enumerate(stn) if NOSE_A < s < NOSE_B and pc.near(s, "median_type") == "none"]
    cleared = 0
    n_p = len(P)
    for i in gap_pts:
        a, b = P[max(0, i - 1)], P[min(n_p - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        pt = pc.tangent(stn[i])
        sense = 1.0 if tx * pt[0] + tz * pt[1] >= 0 else -1.0
        lat = pc.project(P[i][0], P[i][2])[2]
        moff = pc.num(stn[i], "median_off_m")
        want = {round(sense * (moff + sg * ep.DOUBLE_HALF_M - lat), 3) for sg in (1.0, -1.0)}
        hit = [ln for ln in conn_t["paint"]["lines"] if ln["color"] == "yellow" and not ln["dash"] and ln["off"][i] in want]
        if len(hit) != 2:
            raise SystemExit(f"[mg-median] point {i} (s {stn[i]:.1f}): {len(hit)} centre lines found where decorate's rule draws two; refused")
        for ln in hit:
            ln["off"][i] = None
            cleared += 1
    moved = [i for i in range(len(P)) if isl["island_w_by_point"][i] != isl_t["island_w_by_point"][i]
             or isl["points_xyz_m"][i] != isl_t["points_xyz_m"][i]]
    before_pts = {i: {"w": isl["island_w_by_point"][i], "p": isl["points_xyz_m"][i]} for i in moved}
    # the paint as it stood, kept as differences (line -> point -> the old offset): the scene step finds the old strips by it
    old_lines, new_lines = conn["paint"]["lines"], conn_t["paint"]["lines"]
    if [(ln["color"], ln["dash"]) for ln in old_lines] != [(ln["color"], ln["dash"]) for ln in new_lines]:
        raise SystemExit("[mg-median] decorate's lines for the piece are not the lines the file holds, in order; refused")
    paint_before = {str(li): {str(i): a["off"][i] for i in range(n_p) if a["off"][i] != b["off"][i]}
                    for li, (a, b) in enumerate(zip(old_lines, new_lines))}
    paint_before = {k: v for k, v in paint_before.items() if v}
    conn["paint"] = conn_t["paint"]
    mb["connector_islands"][mb["connector_islands"].index(isl)] = isl_t
    mbp.write_text(json.dumps(mb), encoding="utf-8")
    cp.write_text(json.dumps(cdoc), encoding="utf-8")
    runs, i = [], 0
    w = isl_t["island_w_by_point"]
    while i < len(w):
        if w[i] > 0:
            j = i
            while j + 1 < len(w) and w[j + 1] > 0:
                j += 1
            runs.append([i, j])
            i = j + 1
        else:
            i += 1
    out = dict(PROVENANCE, fit=corr["fit"], rows=changed, ring_before=ring0,
               island={"line": LINE, "runs_of_points_with_an_island": runs,
                       "points_changed": [moved[0], moved[-1], len(moved)] if moved else (rec0 or {}).get("island", {}).get("points_changed"),
                       "points_with_no_median_between_the_noses": [gap_pts[0], gap_pts[-1]] if gap_pts else None,
                       "before": before_pts if moved else (rec0 or {}).get("island", {}).get("before")},
               paint={"centre_line_offsets_cleared_between_the_noses": cleared if cleared or not rec0 else rec0.get("paint", {}).get("centre_line_offsets_cleared_between_the_noses"),
                      "lines": len(conn_t["paint"]["lines"]),
                      "_before_doc": "line index -> point index -> the offset the line had there before (null = no line); every "
                                     "other offset of the piece's paint is as it was",
                      "before": paint_before if paint_before else (rec0 or {}).get("paint", {}).get("before")})
    RECORD.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[mg-median] wrote expansion.north.json ({len(changed)} rows; {ISLAND} s {a_part['s_from']}-{a_part['s_to']}, {NEW_ISLAND} "
          f"s {b_part['s_from']}-{b_part['s_to']}), median_bands.json + connectors.local.json ({LINE}: islands on points {runs}, "
          f"{len(moved)} points changed, {cleared} centre-line offsets cleared), {RECORD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
