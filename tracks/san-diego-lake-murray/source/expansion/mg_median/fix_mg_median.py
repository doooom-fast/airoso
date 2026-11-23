"""Correct Mission Gorge Rd's raised median at the source, from measurement, in the two places the plan has it wrong
(ledger 0099 round 3, items 1b and 2; 2026-11-23). The MD7 precedent: source/expansion/phase2/fix_pv_median.py.

The plan's median on piece C is linear between eye readings 250 m apart, with two openings placed by hand near J3.
NAIP 2022 (faces_md.py, md13_faces_*.json; faces_piece.py, pieceC_faces_*.json; README.md) shows, in the piece frame (+ = left of
J3 -> J4 travel = north-west):

THE CROSSING (item 1b), Margerum Avenue / Mission Vista Drive, where MD13 was declared and built unbroken:
  s 1087.5-1117.5   no median at all (marked crosswalks on all four legs; both side streets are built stubs there);
  s 1010-1085       a strip 1.96 m wide, its middle 0.43 m left of the line the full island's middle follows;
  s 1120-1192.5     a strip 1.84 m wide, its middle 1.50 m right of that line (the turn pocket is on its left);
  s 982.5-1010 and s 1192.5-1212.5   the island narrowing from / widening to its declared band.
  Medians over 24 and 26 stations of the photo's equivalent width and centroid, set against the same measure where the
  island fills its band (the width carries +0.30 m and the middle +0.49 m). Each strip's width holds to about +-0.15 m
  and its middle to about +-0.12 m by count; the method's error on a strip narrower than the photo resolves is not
  measured beyond that. The taper s 1192.5-1212.5 lies under tree shadow: its line between its ends is [inferred].

THE J3 END (item 2), where the plan's two openings stand about 13 m from the real ones:
  s 100-136         MD11 leaves its declared line to the LEFT, by 3.6 m at s 136 (measured +1.1 at s 110, +2.0 at 120,
                    +3.2 at 130, +3.4 to +3.8 from s 140 to its end);
  s 136-177.5       MD11 3.6 m left of its declared line; it ends at s 177.5 (declared: 167.5). Its width is as
                    declared (the photo reads 1.1-1.5 m with the +0.30, inside that measure's error);
  s 180-192.5       no median (six stations): the first real opening. The plan's stood at s 167.5-182.5;
  s 195-207.5       the real MD12: 3.40 m wide (the middle five stations read 2.60-3.79, median 3.10, + 0.30), its
                    middle 1.0 m left of the declared centre at s 195 and 2.3 m left at s 207.5. The plan's MD12 stood
                    at s 182.5-195, on the opening's asphalt;
  s 210-222.5       no median (six stations): the second real opening, where MD13 was declared and built to start;
  s 225 on          MD13, as declared (the photo's strip there is within the lateral error of its declared line).
  No full-width island stands near enough to take a registration correction from, so the J3 end's lateral figures
  hold to about +-0.75 m (the Mac's registration range for this mosaic), and the widths to the single-window scatter.

MD12 IS NOT BUILT (the Mac's rule, 2026-11-23: only on measured rows, never lengthened, no denser rows). The real island
is 12.5 to 17.5 m long; the connector has four points inside its measured run (five within its outer bound) and the
median tool, like the lap's corridor, builds an island on six or more. It is owed. What this sets is its PLACE: the
plan's painted outline (the edge lines round a run too short to be an island) lies where the real island stands.

This sets, in the three files that carry the median:
  data/expansion.north.json     pieces[C] rows median_w_m / median_off_m / median_type inside the STRETCHES; the four
                                medians of ISLANDS (MD11, MD12, MD13 and the new MD13b, so no other median's id moves),
                                each ring re-cut inside the stretches by the generator's own nose rule and kept point
                                for point outside them
  data/median_bands.json        connector_islands north_mission_gorge
  data/connectors.local.json    north_mission_gorge's paint
the last two by tools/expansion_pieces.decorate itself, run on a copy of the project, its piece-C output alone carried
over (the other pieces' records are not touched). Then ONE thing is taken out that decorate's rule puts in: where a
road has no median its rule paints a double yellow on the centre. The photo shows none through the crossing nor in the
two openings (README.md), so those two lines' offsets are cleared at the points of NO_MEDIAN. Lane and bike lines run
on as they do past every other stub mouth; nothing else is drawn there (no crosswalk, no stop line: not measured).

    python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py [--write]

Idempotent: the declared values are kept in the record (mg_median_correction.json) and every run starts from them.
Without --write it prints the table and touches nothing."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402

LINE, PIECE = "north_mission_gorge", "C"
RECORD = HERE / "mg_median_correction.json"
# THE FIT, the crossing (item 1b). (d centre, width): the strip's middle off the line the declared middle follows
STRIP_A = (0.43, 1.96)
STRIP_B = (-1.50, 1.84)
JOIN_A, STRIP_A_FROM, NOSE_A = 982.5, 1010.0, 1085.0     # the declared band to s 982.5; strip A from 1010; its nose 1085
NOSE_B, STRIP_B_TO, JOIN_B = 1120.0, 1192.5, 1212.5      # strip B's nose at 1120; strip B to 1192.5; declared from 1212.5
# THE FIT, the J3 end (item 2)
VEER_FROM, VEER_TO, VEER_M = 100.0, 136.0, 3.6           # MD11 leaves its declared line from s 100, 3.6 m left by s 136
MD11_TO = 177.5                                          # MD11's last station with a median
MD12_FROM, MD12_TO, MD12_W = 195.0, 207.5, 3.40          # the real MD12: its stations, its width
MD12_MID = (1.0, 2.3)                                    # its middle off the declared centre at its first / last station
MD13_FROM = 225.0                                        # MD13's first station with a median
# the stations whose rows take the fit and whose ring points are re-cut (inclusive); 231 = MD13's new nose's 6 m taper
STRETCHES = [(100.0, 231.0), (JOIN_A, JOIN_B)]
ISLANDS = [("MD11", 45.0, MD11_TO), ("MD12", MD12_FROM, MD12_TO), ("MD13", MD13_FROM, NOSE_A), ("MD13b", NOSE_B, 2245.0)]
NO_MEDIAN = [(MD11_TO, MD12_FROM), (MD12_TO, MD13_FROM), (NOSE_A, NOSE_B)]     # open intervals of s with no median
DECLARED = {"MD11": (45.0, 167.5), "MD12": (182.5, 195.0), "MD13": (210.0, 2245.0)}   # the plan's runs before any of this
NOSE_M, NOSE_W_M = 6.0, 0.6                              # tools/author_expansion.py: a median's ring tapers to its nose
PROVENANCE = {
    "what": "Mission Gorge Rd's raised median on piece C, in two places: the Margerum Avenue / Mission Vista Drive crossing "
            "(s 982.5-1212.5: no median s 1085-1120, a narrow strip beside each turn pocket) and the J3 end (s 100-231: MD11 "
            "on its real line and to its real end, the two openings where they are, MD12 where it stands, MD13 from its real "
            "start)",
    "why": "the plan's median is linear between eye readings 250 m apart: MD13 was declared, and built, unbroken across a real "
           "crossing whose two side streets are built stubs; and its two openings near J3 stand about 13 m from the real ones "
           "(tools/author_expansion.py GAPS 174 / 202; the dossier's station labels run about 14.6 m ahead of s on this piece, "
           "and 202 - 14.6 is the middle of the first real opening: my reading of two numbers, not traced in the dossier)",
    "measured": "the PC, 2026-11-23: NAIP 2022 z18 full mosaic (source/naip_2022_lm_full_z18.jpg, sha256 1764a80b...). Per "
                "station the equivalent width (excess R - G summed across the island over a full island's plateau, +24.0 over "
                "the asphalt) and the excess's centroid. THE CROSSING (faces_md.py): medians over 24 stations (s 1012.5-1077.5: "
                "1.66 m, +0.18 m) and 26 stations (s 1127.5-1192.5: 1.54 m, -2.24 m), against the same measure where the island "
                "fills its band (37 stations: width 0.30 m short, middle 0.49 m right of the declared band; one station "
                "p10..p90 -1.41..+1.23 m in width, -0.94..+0.18 m in the middle). THE J3 END (faces_piece.py, 10 m windows off "
                "the declared centre, no registration correction): MD11's middle +1.12 at s 110, +1.98 at 120, +3.17 at 130, "
                "+3.76 at 140 and 150, +3.39 at 160, +3.40 at 170, its last station with terracotta s 177.5; none at the six "
                "stations s 180-192.5 nor at the six s 210-222.5; MD12 at s 195-207.5 reads 1.02 / 2.73 / 3.79 / 3.45 / 3.10 / "
                "2.60 m wide with its middle +0.90 / +1.18 / +1.73 / +1.34 / +2.20 / +2.36; MD13's first station with "
                "terracotta s 225",
    "method": "piece C rows inside the stretches set to the fit; the four medians' rings re-cut inside the stretches with the "
              "generator's nose rule and kept outside them; the island and the paint re-derived by "
              "tools/expansion_pieces.decorate (piece C's output only); the two centre lines cleared where there is no median",
    "inferred": "the taper s 1192.5-1212.5 lies under tree shadow on the photo: its two ends are measured, the line between is "
                "[inferred]. MD11's veer is drawn as one straight line from s 100 to s 136 through four measured windows",
    "not_built": "MD12: 12.5 to 17.5 m long on the photo, four connector points inside its measured run; the median tool and "
                 "the lap's corridor build an island on six or more. Its place is set (the plan's painted outline lies where "
                 "the real island stands); the island itself is owed",
    "centre_paint_where_there_is_no_median": {
        "what": "no centre line: the two lines decorate's rule draws where a road has no median are cleared at the points "
                "between the crossing's noses and in the two openings near J3",
        "source": "photo",
        "measured": "the PC, 2026-11-23, the same mosaic. The crossing: within 3 m of the declared centre over s 1090-1112.5 (ten "
                    "stations) the yellowest pixel reads (R + G) / 2 - B = +3.5 to +7.5, the asphalt 5-8 m either side +1.5 to "
                    "+5.5. The openings: within 4 m of where the islands either side stand, s 187.5-192.5 and s 212.5-217.5 read "
                    "+4.0 to +5.5 against the asphalt's +2.0 to +4.5; the stations beside the noses read +8 to +14 on light grey "
                    "pixels (red, green and blue within 16 of each other: not yellow). What a double yellow reads at this "
                    "resolution was not measured on this photo, so the reading is 'no yellower than the asphalt', not a "
                    "threshold passed"},
    "ledger": "0099 round 3, items 1b and 2",
}


def in_stretch(s):
    return any(a - 1e-9 <= s <= b + 1e-9 for a, b in STRETCHES)


def fit(s, t0, w0, o0):
    """(type, width, offset) at station s, from the DECLARED type, width and offset"""
    # the J3 end
    if VEER_FROM < s <= VEER_TO + 1e-9:
        return t0, w0, o0 + VEER_M * (s - VEER_FROM) / (VEER_TO - VEER_FROM)
    if VEER_TO < s <= MD11_TO + 1e-9:
        return t0, w0, o0 + VEER_M
    if MD11_TO < s < MD12_FROM - 1e-9 or MD12_TO < s < MD13_FROM - 1e-9:
        return "none", 0.0, o0
    if MD12_FROM - 1e-9 <= s <= MD12_TO + 1e-9:
        return "terracotta", MD12_W, o0 + MD12_MID[0] + (MD12_MID[1] - MD12_MID[0]) * (s - MD12_FROM) / (MD12_TO - MD12_FROM)
    # the crossing
    if s < JOIN_A - 1e-9 or s > JOIN_B + 1e-9:
        return t0, w0, o0
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


def ring_point(pc, s, s0, s1):
    """(left point, right point) of a raised median's ring at station s of its run s0..s1: tools/author_expansion.py's
    rule (the width tapers over NOSE_M to NOSE_W_M at the run's two ends; the middle on median_off_m)"""
    w = pc.num(s, "median_w_m")
    taper = min(1.0, (s - s0) / NOSE_M, (s1 - s) / NOSE_M)
    w = max(NOSE_W_M, w * max(0.0, taper))
    (px, pz), _t, nl = pc.frame(s)
    o = pc.num(s, "median_off_m")
    return ([round(px + nl[0] * (o + w / 2.0), 3), round(pz + nl[1] * (o + w / 2.0), 3)],
            [round(px + nl[0] * (o - w / 2.0), 3), round(pz + nl[1] * (o - w / 2.0), 3)])


def stations_of(m):
    n = len(m["polygon_xz"]) // 2
    return [round(float(m["s_from"]) + 2.5 * k, 4) for k in range(n)]


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
        if not in_stretch(s):
            continue
        d = declared.get(s)
        t0, w0, o0 = (d["median_type"][0], d["median_w_m"][0], d["median_off_m"][0]) if d else (row[it_c], float(row[iw_c]), float(row[io_c]))
        ty, w, o = fit(s, t0, w0, o0)
        w, o = round(w, 2), round(o, 2)
        if d and (row[it_c], float(row[iw_c]), float(row[io_c])) not in ((t0, w0, o0), (ty, w, o), tuple(d[k][1] for k in ("median_type", "median_w_m", "median_off_m"))):
            raise SystemExit(f"[mg-median] piece C row s {s} holds {row[iw_c]} / {row[io_c]} / {row[it_c]}: neither the declared "
                             f"values of the record nor the fit's; refused")
        changed.append({"s": s, "median_type": [t0, ty], "median_w_m": [w0, w], "median_off_m": [o0, o]})
        table.append((s, w0, o0, ty, w, o))
    print("  s       declared: width  left / right     ->  fit: type        width  left / right   (piece frame, m; + = left)")
    marks = (MD11_TO, MD12_FROM, MD12_TO, MD13_FROM, NOSE_A, NOSE_B)
    for s, w0, o0, ty, w, o in table:
        if abs(s / 12.5 - round(s / 12.5)) < 1e-9 or any(abs(s - q) < 1.3 for q in marks):
            print(f"  {s:7.1f}   {w0:5.2f}  {o0 + w0 / 2:+5.2f} / {o0 - w0 / 2:+5.2f}   ->  {ty:11s}  {w:5.2f}  "
                  + (f"{o + w / 2:+5.2f} / {o - w / 2:+5.2f}" if w > 0 else "   (no median)"))
    n_real = sum(1 for c in changed if (c["median_type"][0], c["median_w_m"][0], c["median_off_m"][0]) != (c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]))
    print(f"[mg-median] {len(changed)} piece-C rows inside {STRETCHES}; {n_real} change; no median over "
          f"{sum(1 for c in changed if c['median_w_m'][1] == 0)} of them")
    if not write:
        return 0

    by_s = {c["s"]: c for c in changed}
    for row in pc.rec["stations"]:
        c = by_s.get(float(row[0]))
        if c:
            row[it_c], row[iw_c], row[io_c] = c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]
    pc = ep.Piece(next(p for p in doc["pieces"] if p["id"] == PIECE))        # the rows as they now stand
    # the four medians: a ring point inside a stretch by the generator's rule, outside it the point the file holds
    meds = doc["medians"]
    have = {m["id"]: m for m in meds if m["piece"] == PIECE and m.get("raised")}
    rings_before = dict((rec0 or {}).get("rings_before") or {})
    if rec0 and rec0.get("ring_before") and "MD13" not in rings_before:
        rings_before["MD13"] = rec0["ring_before"]                           # item 1b's record
    for mid, (a0, b0) in DECLARED.items():
        if mid not in rings_before:
            m = have[mid]
            if (float(m["s_from"]), float(m["s_to"])) != (a0, b0):
                raise SystemExit(f"[mg-median] {mid} runs s {m['s_from']}-{m['s_to']} and the record holds no ring of it as declared "
                                 f"(s {a0}-{b0}); refused")
            rings_before[mid] = {"s_from": a0, "s_to": b0, "points": len(m["polygon_xz"])}
    old_pt = {}
    for m in have.values():
        ring, st = m["polygon_xz"], stations_of(m)
        n = len(st)
        for k, s in enumerate(st):
            old_pt[s] = (ring[k], ring[2 * n - 1 - k])
    corr = dict(PROVENANCE, fit={
        "crossing": {"strip_a": {"d_centre_m": STRIP_A[0], "width_m": STRIP_A[1], "s": [STRIP_A_FROM, NOSE_A]},
                     "strip_b": {"d_centre_m": STRIP_B[0], "width_m": STRIP_B[1], "s": [NOSE_B, STRIP_B_TO]},
                     "tapers_s": [[JOIN_A, STRIP_A_FROM], [STRIP_B_TO, JOIN_B]]},
        "j3_end": {"md11_veer": {"s": [VEER_FROM, VEER_TO], "d_centre_m": VEER_M}, "md11_to_s": MD11_TO,
                   "md12": {"s": [MD12_FROM, MD12_TO], "width_m": MD12_W, "d_centre_m": list(MD12_MID)}, "md13_from_s": MD13_FROM},
        "no_median_s": [list(x) for x in NO_MEDIAN], "stretches_s": [list(x) for x in STRETCHES]})
    for mid, a, b in ISLANDS:
        st = [round(a + 2.5 * k, 4) for k in range(int(round((b - a) / 2.5)) + 1)]
        L, R = [], []
        for s in st:
            if in_stretch(s):
                lp, rp = ring_point(pc, s, a, b)
            elif s in old_pt:
                lp, rp = old_pt[s]
            else:
                raise SystemExit(f"[mg-median] {mid}: station {s} is outside the corrected stretches and no ring holds it; refused")
            L.append(lp)
            R.append(rp)
        ws = [pc.num(s, "median_w_m") for s in st]
        new = {"s_from": round(a, 2), "s_to": round(b, 2), "width_m": [round(min(ws), 2), round(max(ws), 2)],
               "polygon_xz": L + R[::-1], "correction": dict(corr, this_median={"s": [a, b], "declared_s": list(DECLARED.get(mid, ("split off MD13",)))})}
        if mid in have:
            have[mid].update(new)
        else:
            src = have["MD13"]
            meds.insert(meds.index(src) + 1, {"id": mid, "piece": PIECE, "type": src["type"], "raised": True, **new})
    ep_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")   # the file's own format

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
    n_p = len(P)
    stn = [pc.project(p[0], p[2])[1] for p in P]
    # the centre's double yellow where there is no median: decorate's own two offsets at each such point
    # (expansion_pieces.layout: moff +- DOUBLE_HALF_M), found by value and cleared
    gap_pts = [i for i, s in enumerate(stn) if any(a < s < b for a, b in NO_MEDIAN) and pc.near(s, "median_type") == "none"]
    cleared = 0
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
    moved = [i for i in range(n_p) if isl["island_w_by_point"][i] != isl_t["island_w_by_point"][i]
             or isl["points_xyz_m"][i] != isl_t["points_xyz_m"][i]]
    before_pts = dict(((rec0 or {}).get("island") or {}).get("before") or {})
    for i in moved:                                               # the first value a point is seen with is its declared one
        before_pts.setdefault(str(i), {"w": isl["island_w_by_point"][i], "p": isl["points_xyz_m"][i]})
    # the paint as it stood, kept as differences (line -> point -> the old offset): the scene step finds the old strips by it
    old_lines, new_lines = conn["paint"]["lines"], conn_t["paint"]["lines"]
    if [(ln["color"], ln["dash"]) for ln in old_lines] != [(ln["color"], ln["dash"]) for ln in new_lines]:
        raise SystemExit("[mg-median] decorate's lines for the piece are not the lines the file holds, in order; refused")
    touched = set(moved) | set(gap_pts) | {int(k) for k in before_pts}
    far = [i for i in range(n_p) if all(abs(i - q) > 3 for q in touched)]
    for li, (a, b) in enumerate(zip(old_lines, new_lines)):       # each line is the same line: equal wherever nothing changed
        if any(a["off"][i] != b["off"][i] for i in far):
            raise SystemExit(f"[mg-median] paint line {li} differs at a point the correction does not reach: the lines are not "
                             f"in the order the file holds them; refused")
    paint_before = {k: dict(v) for k, v in (((rec0 or {}).get("paint") or {}).get("before") or {}).items()}
    for li, (a, b) in enumerate(zip(old_lines, new_lines)):
        for i in range(n_p):
            if a["off"][i] != b["off"][i]:
                paint_before.setdefault(str(li), {}).setdefault(str(i), a["off"][i])
    conn["paint"] = conn_t["paint"]
    mb["connector_islands"][mb["connector_islands"].index(isl)] = isl_t
    mbp.write_text(json.dumps(mb), encoding="utf-8")
    cp.write_text(json.dumps(cdoc), encoding="utf-8")

    def runs_of(flags):
        out, i = [], 0
        while i < len(flags):
            if flags[i]:
                j = i
                while j + 1 < len(flags) and flags[j + 1]:
                    j += 1
                out.append([i, j])
                i = j + 1
            else:
                i += 1
        return out

    w = isl_t["island_w_by_point"]
    ch = {int(k) for k in before_pts}
    out = dict(PROVENANCE, fit=corr["fit"], rows=changed, rings_before=rings_before,
               island={"line": LINE, "runs_of_points_with_an_island": runs_of([x > 0 for x in w]),
                       "points_changed_runs": runs_of([i in ch for i in range(n_p)]), "points_changed": len(ch),
                       "points_with_no_median_runs": runs_of([i in set(gap_pts) for i in range(n_p)]),
                       "before": {k: before_pts[k] for k in sorted(before_pts, key=int)}},
               paint={"centre_line_offsets_cleared_where_there_is_no_median": cleared, "lines": len(new_lines),
                      "_before_doc": "line index -> point index -> the offset the line had there before any of this (null = no "
                                     "line); every other offset of the piece's paint is as it was",
                      "before": {k: {i: paint_before[k][i] for i in sorted(paint_before[k], key=int)} for k in sorted(paint_before, key=int)}})
    RECORD.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[mg-median] wrote expansion.north.json ({len(changed)} rows; " + ", ".join(f"{m} s {a}-{b}" for m, a, b in ISLANDS)
          + f"), median_bands.json + connectors.local.json ({LINE}: islands on points {out['island']['runs_of_points_with_an_island']}, "
          f"{len(moved)} points changed this run, {cleared} centre-line offsets cleared), {RECORD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
