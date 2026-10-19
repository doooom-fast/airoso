"""Ledger 0054 P3 repair round 2: the BUILT yellow centre paint (data/track.obj YLINE*) vs the yellow paint NAIP shows,
on Princess View (B) and Jackson north (D), every 10 m inside each piece's cuts — the truth lens's paint check, repeated.

Per station: the built yellow lines across the road (YLINE coverage on a 5 cm transect along the station's own normal;
lines closer than PAIR_M are one double yellow, read at their middle) and the aerial yellow faces (the station's OWN
cross profile from tools/aerial_paint_north.py — not the stacked one that placed the paint — read by its own
segments(): a stretch wider than its MERGED_W_M as two faces BLUR_M inside its edges, else one face at its centroid).
Counted: every built double yellow's distance to the nearest aerial face, and every aerial face's distance to the
nearest built double yellow (stations where the aerial reads nothing — shadow, a crosswalk — are skipped), plus the
lens's own number: where the aerial shows two faces 2.5-6 m apart (a clear painted median), the real median's centre
minus the built one's.

    python measure_paint.py <airoso> <project> <out.json>
"""
import gzip
import json
import math
import sys
from pathlib import Path

AIR, PROJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(AIR / "tools"))
import aerial_paint_north as apn  # noqa: E402

PAIR_M = 0.45
STEP_M = 10.0
X = json.loads((PROJ / "data" / "expansion.north.json").read_text(encoding="utf-8"))
pieces = {p["id"]: p for p in X["pieces"] if p["id"] in ("B", "D")}

# the aerial cross profiles (cached by the intermediate they were sampled on; re-sampled from the cached windows if absent)
TRACK = AIR / "tracks" / "san-diego-lake-murray"
cache = apn.default_cache()
key = json.loads((TRACK / "source" / "expansion" / "aerial__paint_north.json").read_text(encoding="utf-8"))["intermediate_sha256_12"]
pp = cache / f"profiles_{key}_{apn.ALONG_N}_{apn.DL_M}_ming.json.gz"
prof = json.loads(gzip.decompress(pp.read_bytes()).decode("utf-8"))
offs = prof["offs"]

# the built YLINE triangles near the two pieces
pts = [(r[1], r[2]) for p in pieces.values() for r in p["stations"][::8]]
cells = {}
CELL = 4.0
V, tris, cur = [], [], None
with open(PROJ / "data" / "track.obj", encoding="ascii", errors="replace") as f:
    for ln in f:
        c2 = ln[:2]
        if c2 == "v ":
            q = ln.split()
            V.append((float(q[1]), float(q[2]), float(q[3])))
        elif c2 in ("o ", "g "):
            cur = ln[2:].strip().upper()
        elif c2 == "f " and cur and cur.startswith("YLINE"):
            idx = [int(t.split("/")[0]) - 1 for t in ln.split()[1:]]
            P = [V[i] for i in idx]
            for k in range(1, len(P) - 1):
                tris.append((P[0], P[k], P[k + 1]))
for t, (a, b, c) in enumerate(tris):
    for ix in range(int(math.floor(min(a[0], b[0], c[0]) / CELL)), int(math.floor(max(a[0], b[0], c[0]) / CELL)) + 1):
        for iz in range(int(math.floor(min(a[2], b[2], c[2]) / CELL)), int(math.floor(max(a[2], b[2], c[2]) / CELL)) + 1):
            cells.setdefault((ix, iz), []).append(t)


def yline_at(x, z):
    for t in cells.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
        a, b, c = tris[t]
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
            return True
    return False


def pct(a, q):
    a = sorted(a)
    return round(a[min(len(a) - 1, int(q * (len(a) - 1)))], 2) if a else None


res = {"_doc": __doc__.split("\n\n")[0], "pieces": {}}
for pid, pc in pieces.items():
    rows = [dict(zip(pc["columns"], r)) for r in pc["stations"]]
    cuts = pc["cuts"]
    s0, s1 = cuts["start"]["s"] + 10.0, cuts["end"]["s"] - 10.0
    P = prof["pieces"][pid]
    b2a, a2b, med, per = [], [], [], []
    last = -1e9
    for i, r in enumerate(rows):
        if not (s0 <= r["s"] <= s1) or r["s"] - last < STEP_M - 1e-6:
            continue
        last = r["s"]
        a, b = rows[max(0, i - 1)], rows[min(len(rows) - 1, i + 1)]
        tx, tz = b["x"] - a["x"], b["z"] - a["z"]
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        lo, hi = r["right_m"] + apn.CENTRE_CLEAR_M, r["left_m"] - apn.CENTRE_CLEAR_M
        # built
        runs, cur_, o = [], None, lo
        while o <= hi + 1e-9:
            on = yline_at(r["x"] + nx * o, r["z"] + nz * o)
            if on and cur_ is None:
                cur_ = o
            if not on and cur_ is not None:
                runs.append((cur_ + o - 0.05) / 2)
                cur_ = None
            o += 0.05
        if cur_ is not None:
            runs.append((cur_ + hi) / 2)
        doubles = []
        for c in runs:
            if doubles and c - doubles[-1][-1] < PAIR_M:
                doubles[-1].append(c)
            else:
                doubles.append([c])
        built = [sum(d) / len(d) for d in doubles]
        # aerial (the station's own profile)
        y = P[i][1]
        prof_i = [(o_, v) for o_, v in zip(offs, y) if v is not None and lo <= o_ <= hi]
        segs = apn.segments(prof_i)
        faces = []
        for g in segs:
            if g[1] - g[0] >= apn.MERGED_W_M:
                faces += [g[0] + apn.BLUR_M, g[1] - apn.BLUR_M]
            else:
                faces.append(g[2])
        if not faces:
            continue
        for c in built:
            b2a.append(min(abs(c - f) for f in faces))
        for f in faces:
            if built:
                a2b.append(min(abs(c - f) for c in built))
        if len(faces) >= 2:
            fa, fb = min(faces), max(faces)
            if 2.5 <= fb - fa <= 6.0 and len(built) >= 2:
                med.append(((fa + fb) / 2) - ((min(built) + max(built)) / 2))
        per.append({"s": r["s"], "built": [round(c, 2) for c in built], "aerial_faces": [round(f, 2) for f in faces]})
    res["pieces"][pid] = {
        "stations": len(per),
        "built_to_aerial_m": {"n": len(b2a), "p50": pct(b2a, .5), "p90": pct(b2a, .9), "over_1m": sum(v > 1 for v in b2a)},
        "aerial_to_built_m": {"n": len(a2b), "p50": pct(a2b, .5), "p90": pct(a2b, .9), "over_1m": sum(v > 1 for v in a2b)},
        "clear_median_real_minus_built_m": {"n": len(med), "p50": pct(med, .5),
                                            "abs_p90": pct([abs(v) for v in med], .9)},
        "per_station": per}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_station"} for k, v in res["pieces"].items()}, indent=1))
