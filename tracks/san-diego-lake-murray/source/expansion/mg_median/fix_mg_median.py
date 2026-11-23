"""Correct Mission Gorge Rd's raised median at the source, from measurement (ledger 0099 round 3, items 1b and 2;
2026-11-23). The MD7 precedent: source/expansion/phase2/fix_pv_median.py.

The plan's median on piece C is linear between eye readings 250 m apart, with two openings placed by hand near J3. It
was declared, and built, unbroken across the Margerum Avenue / Mission Vista Drive crossing, and its J3 end stood about
13 m from the real one. WHAT IS BUILT NOW IS THE LIDAR'S: the G10 read the island's two curb faces off the USGS 2024
lidar at every 2.5 m station (mg_median_faces_g10.py -> mg_median_faces.lidar.g10.json, its .md the method; a face's
+- is a median 0.03 m), in the piece frame (+ = left of J3 -> J4 travel = north-west). Every row of piece C that the
lidar covers takes its width from the two faces measured at its own station, and its place by the rule below.

THE PHOTO CAME FIRST AND WAS WRONG IN ITS CORRECTION (kept as a record: faces_md.py, faces_piece.py, README.md). Its
raw readings agree with the lidar (strip B's middle -2.24 against -2.32). What I added to them did not: +0.30 m of
width and +0.49 m of middle, taken from two stretches (s 930-985, 1215-1260) where I assumed the island fills the band
the plan declares. The lidar shows the island there 0.61 m narrower and 0.86 m right of that band, so the "correction"
moved good readings off. The first form of this script built strips 1.96 / 1.84 m wide from it; the lidar has them
1.24 / 1.30 m.

HOW A ROW IS SET (the lidar's station verdicts are island / none / unclear):
  island    the two faces, each the median of its own station and the two beside it in the same island (MEDIAN_OF: a
            face off by one return's spacing at one station does not kink the curb; a ramp keeps its shape). The row's
            width is left - right, its offset their middle.
  none      no median. The row's offset runs straight from the middle of the island before to the middle of the island
            after, so the lane lines do not jog across the opening [inferred: there is nothing to measure].
  unclear   55 stations (a top just under 0.10 m, a nose, a taper, vegetation on the top, one face flush with a turn
            pocket). The Mac's rule:
            "use the photo there, or the nearest clear lidar, and say which". All take THE NEAREST CLEAR LIDAR: a raised
            station if the nearest clear station on either side is an island, its faces drawn straight between the
            clear island stations either side of it (at an island's end: the one beside it). The record lists each.
Where the lidar's coverage ends inside an island the faces return to the declared ones over BLEND_M [invented]. With
both files (the J3 end and the crossing, then the whole of MD13 / MD13b, s 225-2245) no such place is left.

WHERE IN THE ROAD THE ISLAND GOES (the Mac's rule, 2026-11-23). Its WIDTH is the lidar's everywhere: a width needs no
frame. Its PLACE is not the same question, because the plan's road is not a survey: its two edges are eye readings on
NAIP every 250 m, +-1.0 to 1.5 m each. The G10 read the road's two outer curbs off the same lidar and, per 50 m, said
which is off (its `reads`, 0.30 m [invented] as the line):
  the road edges are where the plan has them     the island at the lidar's place;
  the plan's road edges are off / both off       the island's middle measured from the REAL road's middle, set from the
                                                 PLAN's road's middle: lidar middle - (real road middle - plan road
                                                 middle). The lane room either side of the island is then the real one,
                                                 inside a road that is itself misplaced (its re-fit is owed);
  too few stations with both curbs read          the shift drawn straight between the nearest called bins either side
                                                 [inferred: interpolated], the lidar's width and shape kept (TOO_FEW
                                                 "between"; "declared" = the plan's own middle, the first rule, which
                                                 swings the island off its line and back between called neighbours).
A bin's rule holds at the bin's centre and is drawn straight to the next bin's centre, inside one island, so the curb
never steps sideways at a bin's edge; nothing is drawn across a real gap. THE J3 END (s 45-222.5: MD11, MD12) STAYS AT THE
LIDAR'S PLACE: the bins there are not sound (on the north-west side the "edge" read is the side street's mouth and a
bank), the south-east curb reads clean and within 0.33 m of the plan's over s 100-200, and the plan's middle cannot
carry MD11's 3.2 m veer.

MD11'S START IS HELD AT s 45 (HOLD_BEFORE_S). The lidar has the island from s 25 (the J3 pad cuts at s 24.74); the
built island and the north lap's nose at J3 begin at s 45. Rows before it keep the plan's values; s 25-45 is owed.

MD12 IS NOT BUILT (the Mac's rule, 2026-11-23: only on measured rows, never lengthened, no denser rows). The real island
stands at s 195-207.5, up to 3.6 m wide; the connector has four points inside it and the median tool, like the lap's
corridor, builds an island on six or more. It is owed. What this sets is its PLACE: the plan's painted outline (the
edge lines round a run too short to be an island) lies where the real island stands.

This sets, in the three files that carry the median:
  data/expansion.north.json     pieces[C] rows median_w_m / median_off_m / median_type at the stations the lidar covers;
                                the medians of the islands found (MD11, MD12, MD13, then MD13b ..., so no other median's
                                id moves), each ring re-cut at those stations by the generator's own nose rule and kept
                                point for point at the others
  data/median_bands.json        connector_islands north_mission_gorge
  data/connectors.local.json    north_mission_gorge's paint
the last two by tools/expansion_pieces.decorate itself, run on a copy of the project, its piece-C output alone carried
over (the other pieces' records are not touched). Then ONE thing is taken out that decorate's rule puts in: where a
road has no median its rule paints a double yellow on the centre. The photo shows none through the crossing nor in the
two openings (README.md), so those two lines' offsets are cleared at the points with no median. Lane and bike lines run
on as they do past every other stub mouth; nothing else is drawn there (no crosswalk, no stop line: not measured).

    python -I tracks/san-diego-lake-murray/source/expansion/mg_median/fix_mg_median.py [--write]

Idempotent: the declared values are kept in the record (mg_median_correction.json) and every run starts from them.
Without --write it prints the table and touches nothing."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import expansion_pieces as ep  # noqa: E402

LINE, PIECE = "north_mission_gorge", "C"
RECORD = HERE / "mg_median_correction.json"
LIDAR_FILES = ("mg_median_faces.lidar.g10.json",         # the G10's faces: the J3 end and the crossing (s 25-300, 930-1260),
               "mg_median_faces_full.lidar.g10.json")    # then all of MD13 / MD13b (s 225-2245); a later file's station replaces an earlier one's
TOO_FEW = "between"                                      # a bin with too few curb readings: "between" (the Mac, 2026-11-23) or "declared"
STEP_M = 2.5                                             # the piece's station spacing, and the lidar's
MEDIAN_OF = 3                                            # each face: the median of this many neighbouring stations of its island
BLEND_M = 20.0                                           # [invented] back to the declared faces where coverage ends inside an island
HOLD_BEFORE_S = 45.0                                     # MD11's declared start: rows before it keep the plan's values (s 25-45 owed)
IDS = ("MD11", "MD12", "MD13")                           # the islands found, in order; further ones are MD13b, MD13c ...
DECLARED = {"MD11": (45.0, 167.5), "MD12": (182.5, 195.0), "MD13": (210.0, 2245.0)}   # the plan's runs before any of this
NOSE_M, NOSE_W_M = 6.0, 0.6                              # tools/author_expansion.py: a median's ring tapers to its nose
PROVENANCE = {
    "what": "Mission Gorge Rd's raised median on piece C, set to its two curb faces as the 2024 lidar has them at every 2.5 m "
            "station it covers: the island's real width and place, the Margerum Avenue / Mission Vista Drive crossing (no "
            "median between two noses, a narrow strip beside each turn pocket), and the J3 end (MD11 on its real line and to "
            "its real end, the two openings where they are, MD12 where it stands, MD13 from its real start)",
    "why": "the plan's median is linear between eye readings 250 m apart, centred on the middle of road edges read by eye to "
           "+-1.0-1.5 m: MD13 was declared, and built, unbroken across a real crossing whose two side streets are built stubs; "
           "its two openings near J3 stand about 13 m from the real ones (tools/author_expansion.py GAPS 174 / 202; the "
           "dossier's station labels run about 14.6 m ahead of s on this piece: my reading of two numbers, not traced in the "
           "dossier); and where it is whole it is wider than the real island and off its place",
    "measured": "the G10, 2026-11-23: USGS CA_SanDiegoCo_D24 lidar (flown 2024-11), mg_median_faces_g10.py -> "
                "mg_median_faces.lidar.g10.json (its .md is the method and its checks). Per station the island's left and "
                "right curb face in the piece frame, each placed between the two neighbouring returns where the fewest fall "
                "on the wrong side (+- half that gap, a median 0.03 m), or 'none', or 'unclear'. Not measured there: the "
                "lidar's absolute horizontal accuracy (the NAD83(2011) -> WGS84 step is the null transform, stated to 2 m)",
    "method": "piece C rows at the stations the lidar covers set to its faces (the median of three neighbouring stations "
              "per face; an unclear station from the nearest clear lidar); the island's place by the G10's 50 m bins of the "
              "road's outer curbs (edges true: the lidar's place; edges off: its middle from the real road's middle, set "
              "from the plan's road's middle; too few readings: the shift between the nearest called bins); the J3 end at "
              "the lidar's place; the medians' rings re-cut at those stations with "
              "the generator's nose rule and kept at the others; the island and the paint re-derived by "
              "tools/expansion_pieces.decorate (piece C's output only); the two centre lines cleared where there is no median",
    "the_photo_method_and_its_error": "the PC first measured this off NAIP 2022 (faces_md.py, faces_piece.py; README.md): per "
                                      "station the excess R - G summed across the island, and its centroid. Its raw readings "
                                      "agree with the lidar (strip B's middle -2.24 against -2.32; within 0.22 m on the "
                                      "reference stretches). I then added +0.30 m of width and +0.49 m of middle, taken from "
                                      "s 930-985 and 1215-1260 on the assumption that the island fills its declared band "
                                      "there. It does not: the lidar has it 0.61 m narrower and 0.86 m right of that band. "
                                      "The strips built from the corrected photo were 1.96 and 1.84 m wide with their middles "
                                      "0.70 and 0.58 m left of where the lidar has them; the lidar's are 1.24 and 1.30 m",
    "inferred": "the offset of a row with no median (it only spaces the lane lines across an opening) runs straight between "
                "the islands either side. The shift of a 50 m bin with too few curb readings is interpolated between the "
                "nearest called bins. BLEND_M, the return to the declared faces where the lidar's coverage ends inside an "
                "island, is invented (with both lidar files no such place is left)",
    "not_built": "MD12: the lidar has it at s 195-207.5, up to 3.6 m wide; four connector points lie inside it and the median "
                 "tool and the lap's corridor build an island on six or more. Its place is set (the plan's painted outline "
                 "lies where the real island stands); the island itself is owed. MD11 before s 45: the lidar has the island "
                 "from s 25; the built one, and the north lap's nose at J3, start at s 45; owed",
    "centre_paint_where_there_is_no_median": {
        "what": "no centre line: the two lines decorate's rule draws where a road has no median are cleared at the points "
                "between the crossing's noses and in the two openings near J3",
        "source": "photo",
        "measured": "the PC, 2026-11-23, NAIP 2022 z18 full mosaic. The crossing: within 3 m of the declared centre over s "
                    "1090-1112.5 (ten stations) the yellowest pixel reads (R + G) / 2 - B = +3.5 to +7.5, the asphalt 5-8 m "
                    "either side +1.5 to +5.5. The openings: within 4 m of where the islands either side stand, s 187.5-192.5 "
                    "and s 212.5-217.5 read +4.0 to +5.5 against the asphalt's +2.0 to +4.5; the stations beside the noses "
                    "read +8 to +14 on light grey pixels (red, green and blue within 16 of each other: not yellow). What a "
                    "double yellow reads at this resolution was not measured on this photo, so the reading is 'no yellower "
                    "than the asphalt', not a threshold passed"},
    "ledger": "0099 round 3, items 1b and 2",
}


def key(s):
    return round(float(s), 4)


def lidar_table():
    """({s: the lidar's station}, [the files read])"""
    tab, files = {}, []
    for name in LIDAR_FILES:
        d = json.loads((HERE / name).read_text(encoding="utf-8"))
        rows = list(d.get("check_stations") or []) + list(d["stations"])
        if d.get("columns"):                             # the full-length file holds its stations as rows of `columns`
            rows = [dict(zip(d["columns"], r)) for r in rows]
        for r in rows:
            tab[key(r["s"])] = r
        used = sorted((key(r["s"]), r["verdict"], r.get("left_m"), r.get("right_m")) for r in rows)
        files.append({"file": name, "stations": len(rows), "s": [used[0][0], used[-1][0]],
                      "faces_sha256_16": hashlib.sha256(json.dumps(used).encode("utf-8")).hexdigest()[:16]})
    return tab, files


def road_bins():
    """the G10's 50 m bins of the full-length file: [{"s": [from, to], "kind": true / off / too_few, "shift_m": what is
    taken off the lidar's middle there, ...}], in order. A too-few bin's shift (TOO_FEW "between") is drawn straight
    between the nearest called bins either side"""
    out = []
    for name in LIDAR_FILES:
        d = json.loads((HERE / name).read_text(encoding="utf-8"))
        for b in (d.get("summary") or {}).get("per_50m") or []:
            r = b.get("road") or {}
            reads = str(r.get("reads") or "")
            c = (r.get("road_middle_m") or {}).get("lidar_minus_declared")
            if reads.startswith("too few"):
                kind = "too_few"
            elif reads.startswith("the road edges are where the plan has them"):
                kind = "true"
            elif reads.startswith("the plan's road edges are off") or reads == "both off":
                kind = "off"
            else:
                raise SystemExit(f"[mg-median] {name}: bin s {b['s']} reads {reads!r}, which this script does not know; refused")
            if kind == "off" and c is None:
                raise SystemExit(f"[mg-median] {name}: bin s {b['s']} reads {reads!r} but holds no road middle; refused")
            out.append({"s": [float(b["s"][0]), float(b["s"][1])], "kind": kind, "reads": reads,
                        "stations_with_both_curbs": r.get("stations_with_both_curbs"),
                        "real_road_middle_minus_plan_m": c, "shift_m": 0.0 if kind == "true" else (float(c) if kind == "off" else None)})
    out.sort(key=lambda b: b["s"][0])
    called = [i for i, b in enumerate(out) if b["kind"] != "too_few"]
    for i, b in enumerate(out):
        if b["kind"] != "too_few":
            continue
        lo = [j for j in called if j < i]
        hi = [j for j in called if j > i]
        if lo and hi:
            a, z = out[lo[-1]], out[hi[0]]
            ca, cz, ci = (sum(x["s"]) / 2.0 for x in (a, z, b))
            b["shift_m"] = round(a["shift_m"] + (z["shift_m"] - a["shift_m"]) * (ci - ca) / (cz - ca), 3)
        elif lo or hi:
            b["shift_m"] = out[(lo or hi)[-1 if lo else 0]]["shift_m"]
        else:
            b["shift_m"] = 0.0
    return out


def island_id(k):
    return IDS[k] if k < len(IDS) else IDS[-1] + "bcdefghijklmnopqrstuvwxyz"[k - len(IDS)]


def measure(S, tab, declared_of, bins=()):
    """the piece's rows from the lidar. S: every station of the piece, in order; declared_of(s) -> (type, width, offset);
    bins: road_bins() (none = every island at the lidar's own place).
    Returns {"rows": {s: (type, width, offset)} for the covered stations, "runs": [(s_from, s_to)] of the raised
    stations of the whole piece, "covered": [s], "unclear": [...], "blended": [s], "shift": {s: what was taken off the
    lidar's middle there}}"""
    S = [key(s) for s in S]
    cov = [s for s in S if s in tab and (HOLD_BEFORE_S is None or s >= HOLD_BEFORE_S - 1e-9)]
    cset = set(cov)
    idx = {s: i for i, s in enumerate(S)}
    verdict = {s: tab[s]["verdict"] for s in cov}

    def clear_beside(s, d):
        """the nearest station on side d that is not unclear, while the lidar covers it: (s, verdict) or None"""
        i = idx[s] + d
        while 0 <= i < len(S) and S[i] in cset:
            if verdict[S[i]] != "unclear":
                return S[i], verdict[S[i]]
            i += d
        return None

    def declared_raised(s):
        return any(a - 1e-9 <= s <= b + 1e-9 for a, b in DECLARED.values())

    raised = {}
    for s in S:
        if s not in cset:
            raised[s] = declared_raised(s)
        elif verdict[s] == "unclear":
            raised[s] = any((c := clear_beside(s, d)) is not None and c[1] == "island" for d in (-1, 1))
        else:
            raised[s] = verdict[s] == "island"
    runs, i = [], 0
    while i < len(S):
        if raised[S[i]]:
            j = i
            while j + 1 < len(S) and raised[S[j + 1]]:
                j += 1
            runs.append((S[i], S[j]))
            i = j + 1
        else:
            i += 1
    run_of = {}
    for a, b in runs:
        for i in range(idx[a], idx[b] + 1):
            run_of[S[i]] = (a, b)

    # the faces of every covered raised station: the lidar's, an unclear one from the clear island stations beside it
    raw, unclear = {}, []
    for s in cov:
        if not raised[s]:
            if verdict[s] == "unclear":
                unclear.append({"s": s, "lidar": tab[s].get("reason") or tab[s].get("why") or "unclear", "taken": "no median: the "
                                "nearest clear lidar station on both sides has none"})
            continue
        if verdict[s] == "island":
            raw[s] = (float(tab[s]["left_m"]), float(tab[s]["right_m"]))
    for s in cov:
        if not raised[s] or s in raw:
            continue
        side = []
        for d in (-1, 1):
            i = idx[s] + d
            hit = None
            while 0 <= i < len(S) and S[i] in cset and run_of.get(S[i]) == run_of[s]:
                if verdict[S[i]] == "island":
                    hit = S[i]
                    break
                i += d
            side.append(hit)
        a, b = side
        if a is None and b is None:
            raise SystemExit(f"[mg-median] the lidar's station s {s} is unclear and its island holds no clear station; refused")
        if a is not None and b is not None:
            t = (s - a) / (b - a)
            raw[s] = tuple(raw[a][k] + (raw[b][k] - raw[a][k]) * t for k in (0, 1))
            took = f"the nearest clear lidar: drawn straight between s {a} and s {b}"
        else:
            q = a if a is not None else b
            raw[s] = raw[q]
            took = f"the nearest clear lidar: the island's end, the faces of s {q} beside it"
        unclear.append({"s": s, "lidar": tab[s].get("reason") or tab[s].get("why") or "unclear",
                        "lidar_faces_m": [tab[s].get("left_m"), tab[s].get("right_m")], "taken": took,
                        "faces_m": [round(raw[s][0], 3), round(raw[s][1], 3)]})

    # the median of MEDIAN_OF neighbouring stations, per face, inside each island's covered stretch
    half = MEDIAN_OF // 2
    faces = {}
    for s in raw:
        grp = [S[i] for i in range(idx[s] - half, idx[s] + half + 1) if 0 <= i < len(S)]
        if len(grp) == MEDIAN_OF and all(q in raw and run_of[q] == run_of[s] for q in grp):
            faces[s] = tuple(median(raw[q][k] for q in grp) for k in (0, 1))
        else:
            faces[s] = raw[s]

    # where coverage ends inside an island: back to the declared faces over BLEND_M
    blended = []
    edges = [s for s in raw for d in (-1, 1)
             if 0 <= idx[s] + d < len(S) and S[idx[s] + d] not in cset and raised[S[idx[s] + d]]]
    for s in sorted(faces):
        near = [abs(s - e) for e in edges if run_of[e] == run_of[s]]
        if near and min(near) < BLEND_M - 1e-9:
            _t, w0, o0 = declared_of(s)
            t = min(near) / BLEND_M
            dl, dr = o0 + w0 / 2.0, o0 - w0 / 2.0
            faces[s] = (dl + (faces[s][0] - dl) * t, dr + (faces[s][1] - dr) * t)
            blended.append(s)

    # the island's place, by each 50 m bin's verdict: the bin's rule at its centre, drawn straight to the next bin's
    # centre inside one island (nothing is drawn across a gap; a run with no bin stays where the lidar has it)
    shift = {}
    bins = list(bins)
    cen = [sum(b["s"]) / 2.0 for b in bins]

    def rule(i, s, mid):
        if bins[i]["kind"] == "too_few" and TOO_FEW == "declared":
            return declared_of(s)[2]
        return mid - bins[i]["shift_m"]

    for a, b in runs:
        mine_s = [s for s in sorted(faces) if a <= s <= b]
        mine = [i for i, bn in enumerate(bins) if any(bn["s"][0] - 1e-9 <= s <= bn["s"][1] + 1e-9 for s in mine_s)]
        if not mine:
            continue
        for s in mine_s:
            L, R = faces[s]
            w, mid = L - R, (L + R) / 2.0
            if s <= cen[mine[0]]:
                m = rule(mine[0], s, mid)
            elif s >= cen[mine[-1]]:
                m = rule(mine[-1], s, mid)
            else:
                j = max(k for k in range(len(mine)) if cen[mine[k]] <= s)
                i0, i1 = mine[j], mine[j + 1]
                t = (s - cen[i0]) / (cen[i1] - cen[i0])
                m = (1.0 - t) * rule(i0, s, mid) + t * rule(i1, s, mid)
            faces[s] = (m + w / 2.0, m - w / 2.0)
            shift[s] = round(mid - m, 3)

    rows = {}
    for s in cov:
        if raised[s]:
            L, R = faces[s]
            if L - R <= 0.05:
                raise SystemExit(f"[mg-median] s {s}: the faces {L:+.2f} / {R:+.2f} leave no island; refused")
            rows[s] = ("terracotta", round(L - R, 2), round((L + R) / 2.0, 2))
    # a row with no median: its offset straight between the islands either side
    mid = {s: rows[s][2] for s in rows}
    for s in cov:
        if raised[s]:
            continue
        before = [b for a, b in runs if b < s]
        after = [a for a, b in runs if a > s]
        ends = []
        for q in (before[-1] if before else None, after[0] if after else None):
            if q is not None:
                ends.append((q, mid[q] if q in mid else declared_of(q)[2]))
        if len(ends) == 2:
            (sa, oa), (sb, ob) = ends
            o = oa + (ob - oa) * (s - sa) / (sb - sa)
        elif ends:
            o = ends[0][1]
        else:
            o = declared_of(s)[2]
        rows[s] = ("none", 0.0, round(o, 2))
    return {"rows": rows, "runs": runs, "covered": cov, "unclear": unclear, "blended": blended, "shift": shift,
            "segments": _segments(cov, idx)}


def _segments(cov, idx):
    out = []
    for s in cov:
        if out and idx[s] == idx[out[-1][1]] + 1:
            out[-1][1] = s
        else:
            out.append([s, s])
    return out


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


def lanes(pc, s, runs):
    """per side ("L", "R"): (lanes, one lane's width) as decorate's rule paints them at s"""
    out = {}
    lay = ep.layout(pc, s, runs)
    for tag in ("L", "R"):
        n = 1 + sum(1 for k, *_ in lay if k.startswith(f"lane_{tag}"))
        inner = next(off for k, off, *_ in lay if k in (f"med_edge_{tag}", f"dy_{tag}", f"pm_{tag}1"))
        bike = next(off for k, off, *_ in lay if k == f"bike_{tag}")
        out[tag] = (n, abs(bike - inner) / n)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    write = "--write" in argv
    ep_path = PROJECT / "data" / "expansion.north.json"
    doc, pieces = ep.load(ep_path)
    pc = pieces[PIECE]
    cols = pc.rec["columns"]
    iw_c, io_c, it_c = cols.index("median_w_m"), cols.index("median_off_m"), cols.index("median_type")
    rec0 = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else None
    declared = {key(r["s"]): r for r in (rec0 or {}).get("rows", [])}
    now = {key(row[0]): (row[it_c], float(row[iw_c]), float(row[io_c])) for row in pc.rec["stations"]}

    def declared_of(s):
        d = declared.get(key(s))
        return (d["median_type"][0], float(d["median_w_m"][0]), float(d["median_off_m"][0])) if d else now[key(s)]

    tab, files = lidar_table()
    S = [key(row[0]) for row in pc.rec["stations"]]
    bins = road_bins()
    got = measure(S, tab, declared_of, bins)
    cov = set(got["covered"])
    stray = sorted(s for s in declared if s not in cov)
    if stray:
        raise SystemExit(f"[mg-median] the record holds {len(stray)} rows the lidar does not cover (s {stray[0]}-{stray[-1]}); refused")
    islands = [(island_id(k), a, b) for k, (a, b) in enumerate(got["runs"])]
    if len(islands) < len(IDS):
        raise SystemExit(f"[mg-median] {len(islands)} islands found on piece C ({got['runs']}); the plan has {len(IDS)} or more; refused")
    no_median = [(islands[k][2], islands[k + 1][1]) for k in range(len(islands) - 1)]      # open intervals of s
    changed, table = [], []
    for row in pc.rec["stations"]:
        s = key(row[0])
        if s not in cov:
            continue
        t0, w0, o0 = declared_of(s)
        ty, w, o = got["rows"][s]
        d = declared.get(s)
        if d and now[s] not in ((t0, w0, o0), (ty, w, o), tuple(d[k][1] for k in ("median_type", "median_w_m", "median_off_m"))):
            raise SystemExit(f"[mg-median] piece C row s {s} holds {now[s]}: neither the declared values of the record nor the "
                             f"lidar's; refused")
        changed.append({"s": s, "median_type": [t0, ty], "median_w_m": [w0, w], "median_off_m": [o0, o]})
        table.append((s, t0, w0, o0, ty, w, o))
    marks = [q for _m, a, b in islands for q in (a, b)]
    print("  s       declared: width  left / right     ->  lidar: type       width  left / right   (piece frame, m; + = left)")
    for s, t0, w0, o0, ty, w, o in table:
        if abs(s / 25.0 - round(s / 25.0)) < 1e-9 or any(abs(s - q) < 2.6 for q in marks):
            print(f"  {s:7.1f}   {w0:5.2f}  {o0 + w0 / 2:+5.2f} / {o0 - w0 / 2:+5.2f}   ->  {ty:11s}  {w:5.2f}  "
                  + (f"{o + w / 2:+5.2f} / {o - w / 2:+5.2f}" if w > 0 else f"   (no median; offset {o:+.2f})"))
    n_real = sum(1 for c in changed if (c["median_type"][0], c["median_w_m"][0], c["median_off_m"][0]) != (c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]))
    print(f"[mg-median] the lidar covers {len(changed)} piece-C rows (s {got['segments']}); {n_real} change; no median at "
          f"{sum(1 for c in changed if c['median_w_m'][1] == 0)}; {len(got['unclear'])} unclear stations taken from the nearest "
          f"clear lidar; {len(got['blended'])} blended back to the declared faces where coverage ends")
    print("[mg-median] islands: " + ", ".join(f"{m} s {a}-{b}" for m, a, b in islands))
    sh = sorted(got["shift"].values())
    kinds = {k: sum(1 for b in bins if b["kind"] == k) for k in ("true", "off", "too_few")}
    placement = {"too_few_rule": TOO_FEW, "bins": bins, "bins_by_kind": kinds,
                 "stations_placed_by_a_bin": len(sh), "stations_at_the_lidars_own_place": sum(1 for v in sh if v == 0.0),
                 "taken_off_the_lidars_middle_m": ({"min": sh[0], "median": sh[len(sh) // 2], "max": sh[-1]} if sh else None),
                 "shift_m_by_station": [[q, got["shift"][q]] for q in sorted(got["shift"])],
                 "_doc": "+ = the island stands that far to the right (south-east) of where the lidar has it, in the plan's "
                         "frame: the plan's road is that far north-west of the real one there"}
    if TOO_FEW == "between" and kinds["too_few"]:           # against the first rule (the plan's own middle in those bins)
        globals()["TOO_FEW"] = "declared"
        try:
            other = measure(S, tab, declared_of, bins)
        finally:
            globals()["TOO_FEW"] = "between"
        diff = sorted((abs(got["rows"][q][2] - other["rows"][q][2]), q) for q in got["rows"] if got["rows"][q][1] > 0 and other["rows"][q][1] > 0)
        placement["too_few_bins"] = {"rule": "[inferred: interpolated] the shift drawn straight between the nearest called bins",
                                     "bins_s": [b["s"] for b in bins if b["kind"] == "too_few"],
                                     "against_the_declared_middle_m": {"max": round(diff[-1][0], 2), "at_s": diff[-1][1],
                                                                       "stations_over_0.3_m": sum(1 for v, _q in diff if v > 0.3)}}
        print(f"[mg-median] too-few bins {placement['too_few_bins']['bins_s']}: against the declared-middle rule the island's "
              f"middle differs by at most {placement['too_few_bins']['against_the_declared_middle_m']}")
    print(f"[mg-median] place: {len(bins)} bins of 50 m ({kinds}); {placement['stations_at_the_lidars_own_place']} of {len(sh)} "
          f"stations stay at the lidar's place, the rest are set from the plan's road's middle; taken off the lidar's middle: "
          f"{placement['taken_off_the_lidars_middle_m']}; too-few rule: {TOO_FEW}")

    # the lanes as decorate's rule paints them, before and after (the declared rows against the lidar's)
    rec_decl = copy.deepcopy(pc.rec)
    rec_new = copy.deepcopy(pc.rec)
    by_s = {c["s"]: c for c in changed}
    for r_d, r_n in zip(rec_decl["stations"], rec_new["stations"]):
        c = by_s.get(key(r_d[0]))
        if c:
            r_d[it_c], r_d[iw_c], r_d[io_c] = c["median_type"][0], c["median_w_m"][0], c["median_off_m"][0]
            r_n[it_c], r_n[iw_c], r_n[io_c] = c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]
    pc_d, pc_n = ep.Piece(rec_decl), ep.Piece(rec_new)
    runs_d, runs_n = list(DECLARED.values()), [(a, b) for _m, a, b in islands]
    lane_rep = {"stations": 0, "lane_count_changes": [], "L": {"before": [], "after": []}, "R": {"before": [], "after": []}}
    for s in got["covered"]:
        if not (pc.cuts.get("start", {}).get("s", 0.0) <= s <= pc.cuts.get("end", {}).get("s", 1e9)):
            continue
        b, a = lanes(pc_d, s, runs_d), lanes(pc_n, s, runs_n)
        lane_rep["stations"] += 1
        for tag in ("L", "R"):
            lane_rep[tag]["before"].append(b[tag][1])
            lane_rep[tag]["after"].append(a[tag][1])
            if b[tag][0] != a[tag][0]:
                lane_rep["lane_count_changes"].append({"s": s, "side": tag, "lanes": [b[tag][0], a[tag][0]]})
    for tag in ("L", "R"):
        for k in ("before", "after"):
            v = sorted(lane_rep[tag][k])
            lane_rep[tag][k] = {"min_m": round(v[0], 2), "median_m": round(v[len(v) // 2], 2), "max_m": round(v[-1], 2)}
    print(f"[mg-median] lanes as decorate paints them over {lane_rep['stations']} covered stations: left (north-west) one lane "
          f"{lane_rep['L']['before']} -> {lane_rep['L']['after']}; right (south-east) {lane_rep['R']['before']} -> "
          f"{lane_rep['R']['after']}; the lane count changes at {len(lane_rep['lane_count_changes'])} station-sides"
          + (f" (first: {lane_rep['lane_count_changes'][:4]})" if lane_rep["lane_count_changes"] else ""))
    if not write:
        return 0

    for row in pc.rec["stations"]:
        c = by_s.get(key(row[0]))
        if c:
            row[it_c], row[iw_c], row[io_c] = c["median_type"][1], c["median_w_m"][1], c["median_off_m"][1]
    pc = ep.Piece(next(p for p in doc["pieces"] if p["id"] == PIECE))        # the rows as they now stand
    # the medians: a ring point at a covered station by the generator's rule, at any other the point the file holds
    meds = doc["medians"]
    have = {m["id"]: m for m in meds if m["piece"] == PIECE and m.get("raised")}
    rings_before = dict((rec0 or {}).get("rings_before") or {})
    if rec0 and rec0.get("ring_before") and "MD13" not in rings_before:
        rings_before["MD13"] = rec0["ring_before"]                           # item 1b's record
    for mid_, (a0, b0) in DECLARED.items():
        if mid_ not in rings_before:
            m = have[mid_]
            if (float(m["s_from"]), float(m["s_to"])) != (a0, b0):
                raise SystemExit(f"[mg-median] {mid_} runs s {m['s_from']}-{m['s_to']} and the record holds no ring of it as declared "
                                 f"(s {a0}-{b0}); refused")
            rings_before[mid_] = {"s_from": a0, "s_to": b0, "points": len(m["polygon_xz"])}
    old_pt = {}
    for m in have.values():
        ring, st = m["polygon_xz"], stations_of(m)
        n = len(st)
        for k, s in enumerate(st):
            old_pt[s] = (ring[k], ring[2 * n - 1 - k])
    lidar = {"files": files, "covered_s": got["segments"], "hold_before_s": HOLD_BEFORE_S, "median_of": MEDIAN_OF,
             "blend_m": BLEND_M, "blended_s": got["blended"], "unclear": got["unclear"],
             "islands": [{"id": m, "s": [a, b]} for m, a, b in islands], "no_median_s": [list(x) for x in no_median],
             "placement": placement, "lanes_as_painted": lane_rep}
    corr = dict(PROVENANCE, lidar={k: lidar[k] for k in ("files", "covered_s", "hold_before_s", "median_of", "blend_m", "islands", "no_median_s")})
    for k_i, (mid_, a, b) in enumerate(islands):
        st = [round(a + 2.5 * k, 4) for k in range(int(round((b - a) / 2.5)) + 1)]
        L, R = [], []
        for s in st:
            if s in cov:
                lp, rp = ring_point(pc, s, a, b)
            elif s in old_pt:
                lp, rp = old_pt[s]
            else:
                raise SystemExit(f"[mg-median] {mid_}: station {s} is outside the lidar's coverage and no ring holds it; refused")
            L.append(lp)
            R.append(rp)
        ws = [pc.num(s, "median_w_m") for s in st]
        new = {"s_from": round(a, 2), "s_to": round(b, 2), "width_m": [round(min(ws), 2), round(max(ws), 2)],
               "polygon_xz": L + R[::-1], "correction": dict(corr, this_median={"s": [a, b], "declared_s": list(DECLARED.get(mid_, ("split off MD13",)))})}
        if mid_ in have:
            have[mid_].update(new)
        else:
            src = have[islands[k_i - 1][0]]
            entry = {"id": mid_, "piece": PIECE, "type": src["type"], "raised": True, **new}
            meds.insert(meds.index(src) + 1, entry)
            have[mid_] = entry
    gone = [m for m in have if m not in {i[0] for i in islands}]
    if gone:
        raise SystemExit(f"[mg-median] the file holds medians {gone} the lidar's islands do not name; refused")
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
    gap_pts = [i for i, s in enumerate(stn) if any(a < s < b for a, b in no_median) and pc.near(s, "median_type") == "none"]
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
    before_pts = {k: v for k, v in before_pts.items()             # a point back at its declared value is not a changed one
                  if (v["w"], v["p"]) != (isl_t["island_w_by_point"][int(k)], isl_t["points_xyz_m"][int(k)])}
    # the paint as it stood, kept as differences (line -> point -> the old offset): the scene step finds the old strips by it
    old_lines, new_lines = conn["paint"]["lines"], conn_t["paint"]["lines"]
    if [(ln["color"], ln["dash"]) for ln in old_lines] != [(ln["color"], ln["dash"]) for ln in new_lines]:
        raise SystemExit("[mg-median] decorate's lines for the piece are not the lines the file holds, in order; refused")
    paint_before = {k: dict(v) for k, v in (((rec0 or {}).get("paint") or {}).get("before") or {}).items()}
    touched = set(moved) | set(gap_pts) | {int(k) for k in before_pts} | {int(i) for v in paint_before.values() for i in v}
    far = [i for i in range(n_p) if all(abs(i - q) > 3 for q in touched)]
    for li, (a, b) in enumerate(zip(old_lines, new_lines)):       # each line is the same line: equal wherever nothing changed
        if any(a["off"][i] != b["off"][i] for i in far):
            raise SystemExit(f"[mg-median] paint line {li} differs at a point the correction does not reach: the lines are not "
                             f"in the order the file holds them; refused")
    for li, (a, b) in enumerate(zip(old_lines, new_lines)):
        for i in range(n_p):
            if a["off"][i] != b["off"][i]:
                paint_before.setdefault(str(li), {}).setdefault(str(i), a["off"][i])
    paint_before = {li: {i: o for i, o in v.items() if new_lines[int(li)]["off"][int(i)] != o} for li, v in paint_before.items()}
    paint_before = {li: v for li, v in paint_before.items() if v}
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
    out = dict(PROVENANCE, lidar=lidar, rows=changed, rings_before=rings_before,
               island={"line": LINE, "runs_of_points_with_an_island": runs_of([x > 0 for x in w]),
                       "points_changed_runs": runs_of([i in ch for i in range(n_p)]), "points_changed": len(ch),
                       "points_with_no_median_runs": runs_of([i in set(gap_pts) for i in range(n_p)]),
                       "before": {k: before_pts[k] for k in sorted(before_pts, key=int)}},
               paint={"centre_line_offsets_cleared_where_there_is_no_median": cleared, "lines": len(new_lines),
                      "_before_doc": "line index -> point index -> the offset the line had there before any of this (null = no "
                                     "line); every other offset of the piece's paint is as it was",
                      "before": {k: {i: paint_before[k][i] for i in sorted(paint_before[k], key=int)} for k in sorted(paint_before, key=int)}})
    RECORD.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[mg-median] wrote expansion.north.json ({len(changed)} rows; " + ", ".join(f"{m} s {a}-{b}" for m, a, b in islands)
          + f"), median_bands.json + connectors.local.json ({LINE}: islands on points {out['island']['runs_of_points_with_an_island']}, "
          f"{len(moved)} points changed this run, {cleared} centre-line offsets cleared), {RECORD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
