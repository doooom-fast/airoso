"""Jackson Dr north (piece D): its painted median where the lidar and the photo put it (ledger 0099 round 3, item 4;
Lake Murray 0.20.8).

    python -I fix_jackson_median.py            # what it would do
    python -I fix_jackson_median.py --write    # data/expansion.north.json, data/connectors.local.json, the record

THE FAULT. Over connector rows 496-579 and 234-239 of north_J5_jackson_north#0, the forward carriageway had no lane: the
room between its paint lines was 0.84-1.90 m (the lanes tool, the Mac's first scratch run). Piece D's median columns
there were an automatic aerial read that had caught one edge of a hatched painted median, not its middle: median_off
2.4-4.1 m, width 0-2.9 m, against a band about 5-7 m wide whose left edge they sat on (s 225-505); and, under the trees
at s 1240-1300, a painted median 4.6-6.2 m wide where the lidar reads one centre line.

THE MEASUREMENT (this folder; piece frame, + = left of J4 -> J5 travel):
  * jackson_intensity_D_full.lidar.g10.json (the G10, D24 2024 last returns, every 2.5 m over s 225-505 and 1240-1300):
    each painted line's u and along_share (about 1 solid, 0.25-0.5 dashed);
  * jackson_right_edge.lidar.g10.json (the G10's second look, a +-6 m window, s 300-450): the band's right edge only
    to s 312.5 (contrast 1.13-1.56); past it nothing but the forward edge line;
  * jackson_right_edge.photo.json (photo_line.py): the photo's line in u -5.0..-2.5, and its offset from the lidar where
    both read the edge (23 stations: median -0.61 m, spread -1.64..+0.31, so about +-1 m).

THE RULE (the Mac, 2026-11-23):
  s 225-492.5, a hatched band (the photo's diagonal stripes; decorate's own hatching where it is 1 m or wider); past
  s 487.5 the lidar reads no band line, the J4 turn pocket opening, and the rows past s 492.5 had their lanes:
    LEFT edge   the lidar's solid line (along_share >= 0.5) in u +0.8..+3.95, the strongest; a station without one takes
                it straight between its nearest neighbours that have one, within 15 m (marked "interpolated"), or at an
                end of the stretch the nearest one within 15 m (marked "nearest");
    RIGHT edge  the lidar's: its full read in u -4.2..-2.8 below s 300, its second look at s 300-312.5; past that the
                photo's line less the measured median offset (marked "photo line aligned to lidar, +-1 m"); where
                neither reads it, the left edge less the band width at the nearest stations that read both (median of up
                to 4, within 25 m; marked "[inferred]");
    the lines are paint, the band's face 0.06 m outside each (decorate puts its outer yellow 0.06 m inside the face);
    every line is carried into the BUILT road's frame by the road's shift (jackson_curbs_D.lidar.g10.json: the real road
    is 2.3-3.6 m left of the built one over s 225-472.5, about 1.5 m at s 1250; road_shift below, item 2's bin rule);
    one lane each way (lanes_fwd / lanes_rev 1): a row whose room on a side between the band and its lane edge
    (decorate's: the buffer line, BIKE_LINE_M + BUFFER_M inside the curb) is under LANE_MIN_M is REPORTED and nothing is
    written (the Mac: report it rather than narrow the band).
  s 1240-1300, a centre line (type "line", width 0) at the lidar's line in u -1.0..+1.0; a station without one,
  interpolated as above.
Every other row of the piece is as it was. The record holds every changed row before and after, and the connector's
whole paint before (lines and strokes): tools/author_median_rebuild_blend.py's paint-only mode finds the old strips in
the scene by it.
"""
from __future__ import annotations

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

LINE, PIECE = "north_J5_jackson_north", "D"
RECORD = HERE / "jackson_median_correction.json"
BAND = (270.0, 492.5)          # to connector row 496; past s 487.5 the lidar reads no band (the J4 turn pocket opens).
                                # s 225-267.5 are held as they were (the Mac): see HELD below
CENTRE = (1240.0, 1300.0)
LEFT_WIN = (0.8, 3.95)
RIGHT_WIN = (-4.2, -2.8)
CENTRE_WIN = (-1.0, 1.0)
SECOND_LOOK_TO = 312.5          # the Mac: the second look's right edge is usable to here
POCKET_FROM, POCKET_WIN = 475.0, (-1.0, 0.0)    # the J4 turn pocket narrows the band: its right edge the lidar's line at
                                # about -0.36 (along_share 0.75-0.92), outside the band's usual window
EDGE_WIN_FWD = (-7.8, -4.6)     # the forward side's lines (the lidar's edge and bike lines)
REV_FROM_BAND_M = 2.5           # [invented] a reverse-side line nearer the band's left edge than this is not a lane edge
SOLID_MIN = 0.75                # [invented] the reverse lane's edge is the innermost line this continuous (along_share);
                                # a weaker line inside it is recorded as unexplained, not taken (the Mac, s 292.5: a solid
                                # +8.01 at 0.92 against a weak +3.71 at 0.58: "a 2.44 m lane inside a 7 m side would be the
                                # made-up thing")
EDGE_COLUMNS = ("edge_fwd_m", "outer_fwd_m", "edge_rev_m", "outer_rev_m")   # tools/expansion_pieces.py EDGE_COLS
HELD = {"from": 225.0, "to": 267.5, "why": (
    "the J4 approach: the lidar's right-hand line at u -3.3..-3.9 is continuous (along_share 0.5-0.92 at 14 of 16 "
    "stations: solid, the band's edge or a turn lane's); the line at -5.7..-6.3 shows at 6 of 16 (along 0.42-0.67: "
    "broken, dashed). Either reading leaves about 2.2 m, under LANE_MIN_M: a turn pocket beginning or a bike lane going "
    "dashed before the junction. Held as the data has it, owed with J4 (the aerial or a closer look at J4's approach "
    "settles it)")}
OUTER_MAX_M = 1.5               # [invented] a second line at most this far outside the edge line is the bike lane's
ALONG_MIN = 0.5
INTERP_M = 15.0                 # [invented] a missing edge is drawn between neighbours at most this far
WIDTH_NEAR_M = 25.0             # [invented] the band width an inferred right edge takes, from stations this near
FACE_M = 0.06                   # tools/expansion_pieces.py layout: the outer yellow 0.06 m inside the face
SRC = "0099 r3 item 4: "
BIN_M = 25.0                    # the shift's bins (the G10's report, as item 2's road bins)
BIN_MIN_N = 5                   # [invented] a bin is called with at least this many stations reading both faces, ...
UNCALLED = [(325.0, 372.5), (400.0, 422.5), (475.0, 492.5), (1265.0, 1300.0)]   # ... and not on the G10's can't-call list
                                # (too few stations, stations that disagree, canopy: its report of 2026-11-23)
STRETCH_BINS_FROM = (225.0, 1240.0)   # the G10's bins start at each stretch's first station


def key(s):
    return round(float(s), 2)


def lidar_lines():
    d = json.loads((HERE / "jackson_intensity_D_full.lidar.g10.json").read_text(encoding="utf-8"))
    return {key(r["s"]): r["lines"] for r in d["stations"]}


def best(lines, lo, hi):
    c = [l for l in lines if lo <= l["u"] <= hi and l.get("along_share", 0) >= ALONG_MIN]
    return max(c, key=lambda l: l["peak_over_median"])["u"] if c else None


def fill(vals: dict, src: dict, tag: str):
    """vals: s -> u or None; a None takes the straight line between its nearest valued neighbours within INTERP_M."""
    S = sorted(vals)
    for s in S:
        if vals[s] is not None:
            continue
        lo = next((t for t in reversed(S) if t < s and vals[t] is not None and src.get(t) not in (tag, "nearest")), None)
        hi = next((t for t in S if t > s and vals[t] is not None and src.get(t) not in (tag, "nearest")), None)
        if lo is not None and hi is not None and s - lo <= INTERP_M and hi - s <= INTERP_M:
            vals[s] = round(vals[lo] + (vals[hi] - vals[lo]) * (s - lo) / (hi - lo), 3)
            src[s] = tag
        elif (lo is not None and s - lo <= INTERP_M) or (hi is not None and hi - s <= INTERP_M):
            t = lo if (lo is not None and s - lo <= INTERP_M and (hi is None or hi - s > INTERP_M or s - lo <= hi - s)) else hi
            vals[s] = vals[t]                                    # an end of the stretch: the nearest measured one
            src[s] = "nearest"


def face_shift(field):
    """s -> (shift, how) for one field of jackson_curbs_D.lidar.g10.json (left_minus_built_m, right_minus_built_m or
    real_minus_built_middle_m): road_shift's bins and line, on that field's own stations."""
    d = json.loads((HERE / "jackson_curbs_D.lidar.g10.json").read_text(encoding="utf-8"))
    bins = {}
    for r in d["stations"]:
        if field in r:
            s = float(r["s"])
            a = max(t for t in STRETCH_BINS_FROM if t <= s + 1e-9)
            bins.setdefault(a + BIN_M * int((s - a + 1e-9) // BIN_M), []).append(float(r[field]))
    # a face is called on its own readings (BIN_MIN_N of them in the bin); the G10's can't-call list is about stations
    # reading BOTH faces, so it holds for the middle (road_shift), not for one face
    called = {s0 + (BIN_M - 2.5) / 2.0: (median(v), len(v)) for s0, v in bins.items() if len(v) >= BIN_MIN_N}
    C = sorted(called)

    def at(s):
        stretch = [c for c in C if abs(c - s) <= 400.0]
        if not stretch:
            raise SystemExit(f"[jackson] s {s}: no called {field} bin near; refused")
        if s <= stretch[0] or s >= stretch[-1]:
            c = stretch[0] if s <= stretch[0] else stretch[-1]
            return called[c][0], ("its bin's" if abs(c - s) <= BIN_M / 2 else "[inferred] the nearest called bin's")
        lo = max(c for c in stretch if c <= s); hi = min(c for c in stretch if c >= s)
        if hi == lo:
            return called[lo][0], "its bin's"
        how = "between its bins" if hi - lo <= BIN_M + 1e-6 else "[inferred] across uncalled bins"
        return called[lo][0] + (called[hi][0] - called[lo][0]) * (s - lo) / (hi - lo), how
    return at, {round(c, 2): {"shift_m": round(v, 3), "n": n} for c, (v, n) in sorted(called.items())}


def road_shift():
    """s -> (real road middle - built road middle, how): jackson_curbs_D.lidar.g10.json's stations with both faces, the
    median per BIN_M bin held at the bin's centre and drawn straight to the next called centre (item 2's rule for its
    road bins); a bin with fewer than BIN_MIN_N such stations is not called and takes the line between its neighbours
    ([inferred]); before the first and after the last called centre of a stretch, that centre's value."""
    d = json.loads((HERE / "jackson_curbs_D.lidar.g10.json").read_text(encoding="utf-8"))
    bins = {}
    for r in d["stations"]:
        if "real_minus_built_middle_m" in r:
            s = float(r["s"])
            a = max(t for t in STRETCH_BINS_FROM if t <= s + 1e-9)
            s0 = a + BIN_M * int((s - a + 1e-9) // BIN_M)
            bins.setdefault(s0, []).append(float(r["real_minus_built_middle_m"]))
    called = {}
    for s0, v in bins.items():
        if len(v) >= BIN_MIN_N and not any(lo - 1e-6 <= s0 <= hi + 1e-6 for lo, hi in UNCALLED):
            called[s0 + (BIN_M - 2.5) / 2.0] = (median(v), len(v))       # the centre of a bin of stations s0 .. s0 + 22.5
    C = sorted(called)

    def at(s):
        stretch = [c for c in C if abs(c - s) <= 400.0]                   # the two stretches are 750 m apart
        if not stretch:
            raise SystemExit(f"[jackson] s {s}: no called road-shift bin near; refused")
        if s <= stretch[0]:
            return called[stretch[0]][0], "the nearest called bin's"
        if s >= stretch[-1]:
            return called[stretch[-1]][0], "the nearest called bin's"
        lo = max(c for c in stretch if c <= s); hi = min(c for c in stretch if c >= s)
        if hi == lo:
            return called[lo][0], "its bin's"
        t = (s - lo) / (hi - lo)
        how = "between its bins" if hi - lo <= BIN_M + 1e-6 else "[inferred] across uncalled bins"
        return called[lo][0] + (called[hi][0] - called[lo][0]) * t, how
    return at, {round(c, 2): {"shift_m": round(v, 3), "n": n} for c, (v, n) in sorted(called.items())}


def measure(rows_by_s: dict) -> dict:
    """s -> {"type", "w", "off", "src", "lanes"}: the rule above."""
    lid = lidar_lines()
    second = {key(r["s"]): r for r in json.loads((HERE / "jackson_right_edge.lidar.g10.json").read_text(encoding="utf-8"))["stations"]}
    photo = json.loads((HERE / "jackson_right_edge.photo.json").read_text(encoding="utf-8"))
    p_off = float(photo["photo_minus_lidar"]["median_m"])
    p_u = {key(r["s"]): r["photo_u"] for r in photo["rows"]}
    out = {}
    # the band
    S = [s for s in sorted(rows_by_s) if BAND[0] <= s <= BAND[1]]
    left = {s: best(lid.get(s, []), *LEFT_WIN) for s in S}
    lsrc = {s: "lidar" for s in S if left[s] is not None}
    fill(left, lsrc, "interpolated")
    right, rsrc = {}, {}
    for s in S:
        u = None
        if s < 300.0:
            u = best(lid.get(s, []), *RIGHT_WIN)
            if u is not None:
                rsrc[s] = "lidar"
        elif s <= SECOND_LOOK_TO and second.get(s, {}).get("right_edge_u") is not None:
            u = float(second[s]["right_edge_u"]); rsrc[s] = "lidar, second look"
        elif s >= POCKET_FROM:
            u = best(lid.get(s, []), *POCKET_WIN)
            if u is not None:
                rsrc[s] = "lidar, the pocket's line"
        if u is None and p_u.get(s) is not None and SECOND_LOOK_TO < s < POCKET_FROM:
            u = round(p_u[s] - p_off, 3); rsrc[s] = "photo line aligned to lidar, +-1 m"
        right[s] = u
    both = {s: left[s] - right[s] for s in S if left[s] is not None and right[s] is not None and rsrc.get(s) in ("lidar", "lidar, second look", "photo line aligned to lidar, +-1 m", "lidar, the pocket's line")}
    for s in S:
        if right[s] is None and left[s] is not None:
            near = sorted((abs(t - s), w) for t, w in both.items() if abs(t - s) <= WIDTH_NEAR_M)[:4]
            if near:
                right[s] = round(left[s] - median(w for _d, w in near), 3); rsrc[s] = "[inferred] the left edge less the nearest band width"
    lsh, _lb = face_shift("left_minus_built_m")
    rsh, _rb = face_shift("right_minus_built_m")
    curbs = {key(r["s"]): r for r in json.loads((HERE / "jackson_curbs_D.lidar.g10.json").read_text(encoding="utf-8"))["stations"]}
    # the edge lines, as distances from each REAL curb (a distance from its own curb needs no carrying)
    efw, ofw, erv, orv, weak_rev = {}, {}, {}, {}, {}
    for s in S:
        r = rows_by_s[s]; c = curbs.get(s, {})
        dl = float(c["left_minus_built_m"]) if "left_minus_built_m" in c else lsh(s)[0]
        dr = float(c["right_minus_built_m"]) if "right_minus_built_m" in c else rsh(s)[0]
        real_L, real_R = float(r["left_m"]) + dl, float(r["right_m"]) + dr
        fw = sorted((l["u"] for l in lid.get(s, []) if EDGE_WIN_FWD[0] <= l["u"] <= EDGE_WIN_FWD[1]
                     and l.get("along_share", 0) >= ALONG_MIN and l["u"] > real_R + 0.3), reverse=True)
        efw[s] = round(fw[0] - real_R, 3) if fw else None
        ofw[s] = round(fw[1] - real_R, 3) if len(fw) > 1 and fw[0] - fw[1] <= OUTER_MAX_M else None
        cand = sorted((l["u"], l.get("along_share", 0)) for l in lid.get(s, []) if left[s] is not None
                      and l["u"] >= left[s] + REV_FROM_BAND_M and l["u"] <= real_L - 0.3 and l.get("along_share", 0) >= ALONG_MIN)
        rv = [u for u, a in cand if a >= SOLID_MIN]
        weak_rev[s] = [[round(u, 2), round(a, 2)] for u, a in cand if a < SOLID_MIN and (not rv or u < rv[0])]
        rv += [u for u, a in cand if a < SOLID_MIN and rv and u > rv[0]]      # a bike line outside may be weaker
        rv = sorted(set(rv))
        erv[s] = round(real_L - rv[0], 3) if rv else None
        orv[s] = round(real_L - rv[1], 3) if len(rv) > 1 and rv[1] - rv[0] <= OUTER_MAX_M else None
    efs = {t: "lidar" for t in efw if efw[t] is not None}
    ers = {t: "lidar" for t in erv if erv[t] is not None}
    fill(efw, efs, "interpolated")
    fill(erv, ers, "interpolated")
    for t in S:                                                       # a bike line goes with a measured edge line only
        if efs.get(t) != "lidar":
            ofw[t] = None
        if ers.get(t) != "lidar":
            orv[t] = None
    short = []
    inferred_face = {"left": 0, "right": 0}
    for s in S:
        if left[s] is None or right[s] is None:
            raise SystemExit(f"[jackson] s {s}: no {'left' if left[s] is None else 'right'} edge, nor one to draw it from; refused")
        r = rows_by_s[s]
        dl, hl = lsh(s); dr, hr = rsh(s)                            # each face carried by ITS curb's shift (the Mac)
        inferred_face["left"] += hl.startswith("[inferred]"); inferred_face["right"] += hr.startswith("[inferred]")
        fL, fR = left[s] - dl + FACE_M, right[s] - dr - FACE_M      # the band's faces, outside its outer yellows
        e_f = efw[s] if efw[s] is not None else ep.BIKE_LINE_M + ep.BUFFER_M
        e_r = erv[s] if erv[s] is not None else ep.BIKE_LINE_M + ep.BUFFER_M
        edge_R = float(r["right_m"]) + e_f                          # the lane edges decorate will draw
        edge_L = float(r["left_m"]) - e_r
        room = (round(fR - edge_R, 2), round(edge_L - fL, 2))
        if min(room) < ep.LANE_MIN_M:
            short.append((s, room))
        src = (f"{SRC}left {lsrc[s]}; right {rsrc[s]}; carried by each face's curb shift (left {hl}, right {hr})")
        out[s] = {"type": "hatched", "w": round(fL - fR, 3), "off": round((fL + fR) / 2.0, 3), "src": src, "lanes": (1, 1),
                  "edges_u_lidar": [round(right[s], 3), round(left[s], 3)], "shift_lr_m": [round(dl, 3), round(dr, 3)],
                  "room_fwd_rev_m": list(room),
                  "edge_cols": {"edge_fwd_m": efw[s], "outer_fwd_m": ofw[s], "edge_rev_m": erv[s], "outer_rev_m": orv[s]},
                  "edge_src": [efs.get(s), ers.get(s)],
                  **({"unexplained_weak_lines_rev": weak_rev[s]} if weak_rev.get(s) else {})}
    out["_inferred_face_shift_rows"] = inferred_face
    if short:
        print(f"[jackson] {len(short)} band rows hold no {ep.LANE_MIN_M} m lane on a side (forward, reverse room):")
        for s, room in short:
            print(f"[jackson]   s {s}: {room}")
        out["_short"] = short
    # the centre line under the trees: carried by the road middle's shift (a line in the middle of the road)
    shift, _bins = road_shift()
    S2 = [s for s in sorted(rows_by_s) if CENTRE[0] <= s <= CENTRE[1]]
    cen = {s: best(lid.get(s, []), *CENTRE_WIN) for s in S2}
    csrc = {s: "lidar" for s in S2 if cen[s] is not None}
    fill(cen, csrc, "interpolated")
    for s in S2:
        if cen[s] is None:
            raise SystemExit(f"[jackson] s {s}: no centre line, nor one to draw it from; refused")
        dm, how = shift(s)
        out[s] = {"type": "line", "w": 0.0, "off": round(cen[s] - dm, 3), "lanes": None, "shift_m": round(dm, 3),
                  "src": f"{SRC}centre line, {csrc[s]}; carried by the road's shift {dm:+.2f} m ({how})"}
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    write = "--write" in argv
    ep_path = PROJECT / "data" / "expansion.north.json"
    doc, pieces = ep.load(ep_path)
    praw = next(p for p in doc["pieces"] if p["id"] == PIECE)
    cols = praw["columns"]
    for c in EDGE_COLUMNS:                                       # the opt-in edge columns: null wherever not measured
        if c not in cols:
            cols.append(c)
            for row in praw["stations"]:
                row.append(None)
    ix = {c: cols.index(c) for c in ("s", "median_w_m", "median_off_m", "median_type", "median_src", "lanes_fwd", "lanes_rev",
                                     "left_m", "right_m") + EDGE_COLUMNS}
    rec0 = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else None
    declared = {key(r["s"]): r["before"] for r in (rec0 or {}).get("rows", [])}
    rows_by_s = {}
    for row in praw["stations"]:
        s = key(row[ix["s"]])
        rows_by_s[s] = {c: row[ix[c]] for c in ix}
    got = measure(rows_by_s)
    changed = []
    for row in praw["stations"]:
        s = key(row[ix["s"]])
        if s not in got or not isinstance(got.get(s), dict) or "type" not in got[s]:
            continue
        before = declared.get(s) or {c: row[ix[c]] for c in ("median_type", "median_w_m", "median_off_m", "median_src", "lanes_fwd",
                                                             "lanes_rev") + EDGE_COLUMNS}
        now = {c: row[ix[c]] for c in before}
        g = got[s]
        after = {"median_type": g["type"], "median_w_m": g["w"], "median_off_m": g["off"], "median_src": g["src"],
                 "lanes_fwd": g["lanes"][0] if g["lanes"] else before["lanes_fwd"],
                 "lanes_rev": g["lanes"][1] if g["lanes"] else before["lanes_rev"],
                 **{c: (g.get("edge_cols") or {}).get(c, before.get(c)) for c in EDGE_COLUMNS}}
        if s in declared and now not in (before, after):
            raise SystemExit(f"[jackson] piece D row s {s} holds {now}: neither the record's before nor the measurement; refused")
        for c, v in after.items():
            row[ix[c]] = v
        changed.append({"s": s, "before": before, "after": after,
                        **{k: g[k] for k in ("edges_u_lidar", "shift_lr_m", "shift_m", "room_fwd_rev_m", "edge_cols", "edge_src")
                           if k in g}})
    nb = sum(1 for c in changed if c["after"]["median_type"] == "hatched")
    short = got.get("_short") or []
    srcs = {}
    import re
    for c in changed:
        for part in c["after"]["median_src"][len(SRC):].split("; "):
            part = re.sub(r"shift [+-][0-9.]+ m", "shift", part)
            srcs[part] = srcs.get(part, 0) + 1
    print(f"[jackson] {len(changed)} rows: {nb} hatched band, {len(changed) - nb} centre line; {len(short)} band rows short of a lane")
    for k, v in sorted(srcs.items(), key=lambda kv: -kv[1]):
        print(f"[jackson]   {v:3d} x {k}")
    if not write:
        return 0
    if short:
        print(f"[jackson] {len(short)} band rows under LANE_MIN_M, written as measured (the Mac: reported, no nudge): "
              f"{[(s_, r_) for s_, r_ in short]}")
    # the paint: decorate's own output for piece D, off two copies of the project, the old data and the new; nothing is
    # written until every check below has passed
    cp = PROJECT / "data" / "connectors.local.json"
    cdoc = json.loads(cp.read_text(encoding="utf-8"))
    new_text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"

    def decorated(ep_text):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "data").mkdir()
            for f in ("track.config.json", "data/connectors.local.json", "data/median_bands.json"):
                shutil.copyfile(PROJECT / f, tmp / f)
            (tmp / "data" / "expansion.north.json").write_text(ep_text, encoding="utf-8")
            ep.decorate(tmp)
            return (json.loads((tmp / "data" / "connectors.local.json").read_text(encoding="utf-8")),
                    json.loads((tmp / "data" / "median_bands.json").read_text(encoding="utf-8")))
    c_old, mb_old = decorated(ep_path.read_text(encoding="utf-8"))
    cdoc_t, mb_new = decorated(new_text)
    names = [c["name"] for c in cdoc["connectors"]]
    for c, co, ct in zip(cdoc["connectors"], c_old["connectors"], cdoc_t["connectors"]):
        if not (c["name"] == co["name"] == ct["name"]) or c["points_xyz_m"] != ct["points_xyz_m"]:
            raise SystemExit(f"[jackson] decorate moved or reordered connector {c['name']}; refused")
        if c["name"].split("#")[0] != LINE and co.get("paint") != ct.get("paint"):
            raise SystemExit(f"[jackson] the new data changes another connector's paint ({c['name']}); refused")
    if mb_old != mb_new:
        raise SystemExit("[jackson] the new data changes median_bands.json (an island); refused")
    conn = next(c for c in cdoc["connectors"] if c["name"].split("#")[0] == LINE)
    co_ = next(c for c in c_old["connectors"] if c["name"].split("#")[0] == LINE)
    conn_t = next(c for c in cdoc_t["connectors"] if c["name"].split("#")[0] == LINE)
    if rec0 is None and conn.get("paint") != co_.get("paint"):
        raise SystemExit(f"[jackson] {conn['name']}'s committed paint is not decorate's own on the committed data: a later "
                         f"correction of its own would be lost; refused")
    ep_path.write_text(new_text, encoding="utf-8")
    paint_before = (rec0 or {}).get("paint_before") or conn.get("paint")
    conn["paint"] = conn_t["paint"]
    cp.write_text(json.dumps(cdoc), encoding="utf-8")
    out = {"_doc": __doc__.split("\n\n")[0], "line": conn["name"], "piece": PIECE, "connectors": len(names), "held": HELD,
           "short_rows": [{"s": s_, "room_fwd_rev_m": list(r_)} for s_, r_ in short],
           "photo_minus_lidar": json.loads((HERE / "jackson_right_edge.photo.json").read_text(encoding="utf-8"))["photo_minus_lidar"],
           "rows": changed, "sources": srcs,
           "_paint_before_doc": "the connector's whole paint as it stood before this correction (lines and strokes): the scene "
                                "step finds every old strip by it, then lays the new paint (connectors.local.json)",
           "paint_before": paint_before,
           "paint_after_summary": {"lines": len(conn_t["paint"]["lines"]), "strokes": len(conn_t["paint"].get("strokes") or [])}}
    RECORD.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"[jackson] wrote expansion.north.json, connectors.local.json ({conn['name']}: {len(conn_t['paint']['lines'])} lines, "
          f"{len(conn_t['paint'].get('strokes') or [])} strokes; before {len(paint_before['lines'])} lines, "
          f"{len(paint_before.get('strokes') or [])} strokes), {RECORD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
