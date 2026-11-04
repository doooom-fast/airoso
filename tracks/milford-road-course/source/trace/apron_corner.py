"""The trace read the concrete run-off apron outside the left-hander at about s 1,000 as road; this takes it back off. One run,
2026-11-03 (ledger 0069).

The perpendicular scans (finalize.py) measured paved width, and the apron outside this corner (the pale triangle south of the
apex in naip_2022_mrc.jpg, a joint line between it and the asphalt) is paved. So from fix 395 to fix 409 the scan spanned
asphalt + apron: up to 21.4 m against an 11-12 m road, and because the centre is the scan's middle, the line sat on the
asphalt's outer edge at the apex, about 5 m outside the road's centre. The inner edge (centre + w/2) is right at the apex: it
lands on the inner edge line in the image. On that line the draft's ribbon was 21 m wide round an 11.4 m radius on a 15 %
descent; the inside edge folded to within 1.1 m of the turning centre and every 3 m row dropped half its 0.44 m fall in a
sliver triangle: a staircase of 6-22 cm steps across the wheel paths (drive_test: all 26 severe steps and 141 of 152 slope
kinks on the lap).

The fix keeps the inner edge where the trace put it and gives the corner the road's own width. W_ROAD is the median traced
width of the 25 fixes either side of WINDOW (11.28 m). Each fix in WINDOW wider than that takes W_ROAD, and its centre moves
(w - W_ROAD) / 2 towards the inside of the corner. Two things keep the line from jogging: the correction eases in and out
over the window's first and last RAMP fixes (smoothstep), and the move is averaged over SMOOTH fixes either side, because
the stored width (a +-12-fix running median in to_fixes.py) jumps 4 m between fixes 394 and 395 where the scan's centre did
not. Checked against the image: at the apex the new centre is within 0.5 m of the middle of the asphalt band (low-chroma grey
160-199 between the inner edge line and the apron joint).

    python tracks/milford-road-course/source/trace/apron_corner.py     (from the airoso root; refuses a second run)
"""
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXES = HERE.parent / "mrc_fixes.json"
WINDOW = range(383, 425)       # the apron corner and the stations the running median smeared it into
RAMP = 8
SMOOTH = 4
APEX = 401
REF = list(range(WINDOW.start - 25, WINDOW.start)) + list(range(WINDOW.stop, WINDOW.stop + 25))
M_LAT = 111132.92 - 559.82 * math.cos(2 * math.radians(42.57))
M_LON = 111412.84 * math.cos(math.radians(42.57))

d = json.loads(FIXES.read_text(encoding="utf-8"))
assert d[APEX]["w"] > 18.0, "already applied (the apex is no longer apron-wide)"
w_road = round(statistics.median(d[i]["w"] for i in REF), 2)


def left_normal(i):
    a, b = d[i - 2], d[i + 2]
    tx, tz = (b["lon"] - a["lon"]) * M_LON, (b["lat"] - a["lat"]) * M_LAT
    ln = math.hypot(tx, tz)
    return -tz / ln, tx / ln


def ease(i):
    t = min(1.0, (min(i - WINDOW.start, WINDOW.stop - 1 - i) + 1) / (RAMP + 1))
    return t * t * (3.0 - 2.0 * t)


# the inside of the corner: the turn from fix APEX-8 to APEX+8 (left = counter-clockwise = +)
(ax, az), (bx, bz) = left_normal(APEX - 8), left_normal(APEX + 8)
side = 1.0 if (ax * bz - az * bx) > 0 else -1.0
raw = {i: ease(i) * max(0.0, d[i]["w"] - w_road) / 2.0 for i in WINDOW}
out = [dict(p) for p in d]
moved = []
for i in WINDOW:
    near = [raw.get(j, 0.0) for j in range(i - SMOOTH, i + SMOOTH + 1)]
    shift = side * sum(near) / len(near)
    nx, nz = left_normal(i)
    out[i]["lon"] = round(d[i]["lon"] + nx * shift / M_LON, 7)
    out[i]["lat"] = round(d[i]["lat"] + nz * shift / M_LAT, 7)
    out[i]["w"] = round(d[i]["w"] - ease(i) * max(0.0, d[i]["w"] - w_road), 2)
    moved.append((i, round(abs(shift), 2)))
FIXES.write_text(json.dumps(out), encoding="utf-8", newline="\n")
print(f"road width {w_road} m; corner turns {'left' if side > 0 else 'right'}; {len(moved)} fixes re-centred, "
      f"largest move {max(m for _, m in moved)} m at fix {max(moved, key=lambda r: r[1])[0]}")
