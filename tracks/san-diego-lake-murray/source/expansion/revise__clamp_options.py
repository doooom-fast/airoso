"""Re-simulate the L3 band clamp on the terrain lens's fresh-3DEP transects under per-road options."""
import json, sys
from collections import defaultdict
S = r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/expansion"
rows = json.load(open(S + "/terrain/out/clamp_transects.json"))
BAND = 22.0
SIDEHILL = ("mission_gorge", "jackson_north")


def smooth(t):
    t = min(1, max(0, t)); return t * t * (3 - 2 * t)


def cw(d, full, rel):
    if d <= full: return 1.0
    if d >= rel: return 0.0
    return 1.0 - smooth((d - full) / (rel - full))


def run(name, opt):
    out = defaultdict(lambda: [0, 0, 0.0, 0, 0.0])  # n, moved>1, worst, moved>1 beyond 40, worst beyond 40
    bind_in40 = defaultdict(int)
    for lg, s, o, x, z, h, d, road, rh, w0, mv0 in rows:
        side = road.split(".")[0] in SIDEHILL
        full, rel = opt if side else (80.0, 250.0)
        w = cw(max(0.0, d), full, rel)
        c = rh - BAND if h < rh - BAND else (rh + BAND if h > rh + BAND else h)
        mv = w * (c - h)
        r = out[lg]
        r[0] += 1
        if abs(mv) > 1: r[1] += 1
        if abs(mv) > abs(r[2]): r[2] = mv
        if d > 40 and abs(mv) > 1: r[3] += 1
        if d > 40 and abs(mv) > abs(r[4]): r[4] = mv
        if side and d <= 40 and abs(h - rh) > BAND: bind_in40[lg] += 1
    print(f"== {name}: sidehill roads full {opt[0]} m, released by {opt[1]} m; others 80/250")
    for lg, (n, m, wst, mb, wb) in out.items():
        print(f"  {lg:14} n={n:4} moved>1m={m:4} worst={wst:+6.1f}  beyond40 moved>1m={mb:4} worst={wb:+6.1f}  sidehill clamp binds within 40 m: {bind_in40[lg]}")


run("as amended", (80.0, 250.0))
run("D3 default", (40.0, 40.0))
run("soft", (40.0, 120.0))
