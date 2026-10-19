"""Ledger 0054 P3: EXPANSION-PLAN V1 / V2 / V7-cut-walls on the BUILT road (data/track.obj, the road kn5's triangles),
against data that did not place it (L5): the OSM midline / the aerial eye widths (V1), 3DEP 1 m (V2, the walls).

  V1 plan     the built pavement's centre (the midpoint of its two edges, found by a lateral march on 1ROAD at every
              10 m of each piece) vs the piece's OSM midline: p95 <= 1.5 m; curb to curb at the 38 aerial stations within
              +-1.5 m of the eye reading
  V2 profile  the built deck (1ROAD top - 0.10 m) on each piece's midline every 2.5 m vs its 3DEP (y_3dep, stations):
              p95 <= 0.5 m; Princess View's steepest 20 m grade (10.2 % down, +-0.5); the Mission Gorge crest (114.3 +-1 m
              at s 1460 +-20 m)
  walls       P2 step 3's transects (Mission Gorge s 1115 -> J4, all of Jackson north; 12-20 m off the midline each
              side, the 3DEP cached in ../p2-proofs/cut_walls.samples.json.gz) read on the BUILT ground: per station the
              real wall (max 3DEP - road) and the built one (max ground - road); a stretch of >= 50 m where a real wall
              >= 3 m keeps under half of it is LOST (P2's own rule)
  walls_all   (repair round 1, the truth lens's own reading) every 5 m of ALL FOUR pieces, BOTH sides, fresh 3DEP at
              12-35 m off the centre line (walls_sweep.samples.json.gz, cached with provenance): per station-side the real
              wall (max 3DEP - the 3DEP road) and the built one (max ground - the built road), at 12-20 m and at 12-35 m,
              skipping points over pavement; counted: stations with a 3 m+ real wall, those more than 1 m short, those
              keeping under half, and runs of 20 m+ of short stations

    python measure_p3.py <airoso> <project> <out.json>
"""
import gzip
import json
import math
import sys
from pathlib import Path

AIR, PROJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(AIR / "tools"))
import verify_pads as vp  # noqa: E402

TRACK = AIR / "tracks" / "san-diego-lake-murray"
X = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
local = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))
elev0 = local["origin"]["elev_m"]
pieces = {p["id"]: p for p in X["pieces"]}


def rows_of(p):
    col = {c: k for k, c in enumerate(p["columns"])}
    st = p["stations"]
    out = []
    for k, r in enumerate(st):
        a, b = st[max(0, k - 1)], st[min(len(st) - 1, k + 1)]
        tx, tz = b[col["x"]] - a[col["x"]], b[col["z"]] - a[col["z"]]
        L = math.hypot(tx, tz) or 1.0
        out.append({"s": r[col["s"]], "x": r[col["x"]], "z": r[col["z"]], "y3": r[col["y_3dep"]], "l": r[col["left_m"]],
                    "r": r[col["right_m"]], "nx": -tz / L, "nz": tx / L})
    return out


R = {pid: rows_of(p) for pid, p in pieces.items()}
centres = [(q["x"], q["z"]) for rows in R.values() for q in rows[::8]]
centres.append(tuple(json.loads((PROJ / "data" / "lights.local.json").read_text(encoding="utf-8"))["lampheads"][77][::2]))
_V, T = vp.load(PROJ / "data" / "track.obj", centres)
F = vp.Field(T)


def road_at(x, z, near=None):
    hs = [h for h, n in F.at(x, z) if n.startswith("1ROAD")]
    if not hs:
        return None
    if near is None:
        return max(hs)
    return min(hs, key=lambda h: abs(h - near))


def ground_at(x, z):
    hs = [h for h, n in F.at(x, z) if not n.startswith(("MARKINGS", "YLINE", "1WALL", "LIGHT", "SIGN"))]
    return max(hs) if hs else None


res = {"V1": {}, "V2": {}, "walls": {}}
# ---- V1 / V2 per piece
for pid, rows in R.items():
    cuts = pieces[pid]["cuts"]
    s_lo, s_hi = cuts["start"]["s"] + 3.0, cuts["end"]["s"] - 3.0
    dev, prof, widths = [], [], []
    for q in rows:
        if not (s_lo <= q["s"] <= s_hi):
            continue
        h = road_at(q["x"], q["z"], q["y3"] + 0.1)
        if h is not None:
            prof.append((q["s"], h - 0.10, q["y3"]))
        if abs(q["s"] / 10.0 - round(q["s"] / 10.0)) > 1e-6:
            continue
        edges = []
        for sg in (1.0, -1.0):
            last = None
            o = 0.0
            while o < 25.0:
                x, z = q["x"] + q["nx"] * sg * o, q["z"] + q["nz"] * sg * o
                if road_at(x, z, q["y3"]) is not None:
                    last = o
                elif last is not None and o > last + 0.6:
                    break
                o += 0.1
            edges.append(None if last is None else sg * last)
        if None not in edges:
            mid = (edges[0] + edges[1]) / 2.0
            design_mid = (q["l"] + q["r"]) / 2.0
            dev.append(abs(mid - design_mid))
            widths.append((q["s"], edges[0] - edges[1], q["l"] - q["r"]))
    d2 = sorted(abs(b - c) for _s, b, c in prof)
    dv = sorted(dev)
    g = []
    for i in range(len(prof)):
        j = next((k for k in range(i, len(prof)) if prof[k][0] - prof[i][0] >= 20.0), None)
        if j is not None:
            g.append(((prof[j][1] - prof[i][1]) / (prof[j][0] - prof[i][0]), (prof[i][0] + prof[j][0]) / 2))
    gmin = min(g, key=lambda t: t[0]) if g else None
    gmax = max(g, key=lambda t: t[0]) if g else None
    res["V2"][pid] = {"stations": len(prof), "p95_m": round(d2[int(0.95 * (len(d2) - 1))], 3) if d2 else None,
                      "max_m": round(d2[-1], 3) if d2 else None, "steepest_down_pct_20m": [round(100 * gmin[0], 2), gmin[1]],
                      "steepest_up_pct_20m": [round(100 * gmax[0], 2), gmax[1]], "pass_p95": bool(d2) and d2[int(0.95 * (len(d2) - 1))] <= 0.5}
    if pid == "C":
        near = [(s, h) for s, h, _y in prof if abs(s - 1460) <= 60]
        top = max(near, key=lambda t: t[1])
        res["V2"][pid]["crest"] = {"s": top[0], "z_m": round(top[1] + elev0, 2),
                                   "pass": abs(top[1] + elev0 - 114.3) <= 1.0 and abs(top[0] - 1460) <= 20}
    res["V1"][pid] = {"centre_vs_design_p95_m": round(dv[int(0.95 * (len(dv) - 1))], 3) if dv else None,
                      "sections": len(dv),
                      "width_built_vs_design_max_m": round(max(abs(a - b) for _s, a, b in widths), 3) if widths else None}
# the 38 aerial stations
ws = []
for w in X["width_stations"]:
    pid = w["piece"]
    rows = R[pid]
    q = min(rows, key=lambda r: abs(r["s"] - w["s"]))
    cuts = pieces[pid]["cuts"]
    if not (cuts["start"]["s"] + 1 <= q["s"] <= cuts["end"]["s"] - 1):
        ws.append({"n": w["n"], "label": w["label"], "note": "inside a pad / weld (the pad's or the loop's own pavement)"})
        continue
    edges = []
    for sg in (1.0, -1.0):
        last, o = None, 0.0
        while o < 25.0:
            x, z = q["x"] + q["nx"] * sg * o, q["z"] + q["nz"] * sg * o
            if road_at(x, z, q["y3"]) is not None:
                last = o
            elif last is not None and o > last + 0.6:
                break
            o += 0.1
        edges.append(last)
    built = None if None in edges else round(edges[0] + edges[1], 2)
    ws.append({"n": w["n"], "label": w["label"], "eye_m": w["eye_width_m"], "built_m": built,
               "pass": built is not None and abs(built - w["eye_width_m"]) <= 1.5})
res["V1"]["aerial_stations"] = ws
res["V1"]["aerial_pass"] = sum(1 for w in ws if w.get("pass")), sum(1 for w in ws if "pass" in w)
# ---- walls
cache = json.loads(gzip.decompress((TRACK / "source" / "expansion" / "p2-proofs" / "cut_walls.samples.json.gz").read_bytes()))
OFFS = [12.0 + k for k in range(9)]
SPANS = {"C": (1115.0, None), "D": (0.0, None)}
idx = []
for pid, (s0, s1) in SPANS.items():
    rows = []
    col = {c: k for k, c in enumerate(pieces[pid]["columns"])}
    st = pieces[pid]["stations"]
    for k, r in enumerate(st):
        a, b = st[max(0, k - 1)], st[min(len(st) - 1, k + 1)]
        tx, tz = b[col["x"]] - a[col["x"]], b[col["z"]] - a[col["z"]]
        L = math.hypot(tx, tz) or 1.0
        rows.append({"s": r[col["s"]], "x": r[col["x"]], "z": r[col["z"]], "y": r[col["y_smooth"]], "nx": -tz / L, "nz": tx / L})
    s_end = rows[-1]["s"] if s1 is None else s1
    for q in rows:
        if q["s"] < s0 - 1e-6 or q["s"] > s_end + 1e-6 or abs((q["s"] - s0) / 5.0 - round((q["s"] - s0) / 5.0)) > 1e-6:
            continue
        for side, sg in (("left", 1.0), ("right", -1.0)):
            for off in OFFS:
                idx.append((pid, q, side, sg * off))
if len(idx) != len(cache["h"]):
    raise SystemExit(f"transects {len(idx)} != cached {len(cache['h'])}")
by = {}
for (pid, q, side, off), h in zip(idx, cache["h"]):
    x, z = q["x"] + q["nx"] * off, q["z"] + q["nz"] * off
    rd = road_at(q["x"], q["z"], q["y"] + 0.1)
    rec = by.setdefault((pid, q["s"], side), {"road": None if rd is None else rd - 0.10 + elev0, "real": [], "built": []})
    rec["real"].append(h)
    gb = ground_at(x, z)
    rec["built"].append(None if gb is None else gb + elev0)
rows_out = []
for (pid, s, side), r in sorted(by.items()):
    if r["road"] is None:
        continue
    real_cut = max(v - r["road"] for v in r["real"])
    bb = [v for v in r["built"] if v is not None]
    built_cut = max(v - r["road"] for v in bb) if bb else None
    lost = real_cut >= 3.0 and (built_cut is None or built_cut < 0.5 * real_cut)
    rows_out.append({"piece": pid, "s": s, "side": side, "real_cut_m": round(real_cut, 2),
                     "built_cut_m": None if built_cut is None else round(built_cut, 2), "lost": lost})


def stretches(flag):
    out = []
    for pid in SPANS:
        for side in ("left", "right"):
            cur = None
            for q in [q for q in rows_out if q["piece"] == pid and q["side"] == side]:
                if flag(q):
                    if cur is None:
                        cur = {"piece": pid, "side": side, "s_from": q["s"], "s_to": q["s"], "max_real_m": q["real_cut_m"],
                               "min_kept_frac": None}
                    cur["s_to"] = q["s"]
                    cur["max_real_m"] = max(cur["max_real_m"], q["real_cut_m"])
                elif cur is not None:
                    out.append(cur)
                    cur = None
            if cur is not None:
                out.append(cur)
    for c in out:
        c["length_m"] = round(c["s_to"] - c["s_from"] + 5.0, 1)
    return out


walls = stretches(lambda q: q["real_cut_m"] >= 3.0)
lost = [c for c in stretches(lambda q: q["lost"]) if c["length_m"] >= 50.0]
for w in walls:
    ins = [q for q in rows_out if q["piece"] == w["piece"] and q["side"] == w["side"] and w["s_from"] <= q["s"] <= w["s_to"]]
    fr = [q["built_cut_m"] / q["real_cut_m"] for q in ins if q["built_cut_m"] is not None and q["real_cut_m"] > 0]
    w["kept_frac_median"] = round(sorted(fr)[len(fr) // 2], 2) if fr else None
    w["built_max_m"] = max((q["built_cut_m"] or 0) for q in ins)
res["walls"] = {"real_walls_ge_3m": walls, "lost_stretches_ge_50m": lost,
                "stations_with_real_wall": sum(1 for q in rows_out if q["real_cut_m"] >= 3.0),
                "of_them_lost": sum(1 for q in rows_out if q["lost"])}
# ---- walls_all (repair round 1): the truth lens's sweep on all four pieces, both sides
SW = json.loads(gzip.decompress((Path(__file__).resolve().parent / "walls_sweep.samples.json.gz").read_bytes()))
y3 = {pid: {q["s"]: q["y3"] for q in rows} for pid, rows in R.items()}
cuts_s = {pid: (p["cuts"]["start"]["s"], p["cuts"]["end"]["s"]) for pid, p in pieces.items()}
st_all = {}
for pid, s_, off, x, z, h in zip(SW["piece"], SW["s"], SW["off"], SW["x"], SW["z"], SW["h"]):
    q = next((q for q in R[pid] if abs(q["s"] - s_) < 1e-6), None)
    if q is None or h is None or s_ not in y3[pid]:
        continue
    key = (pid, s_, 1 if off > 0 else -1)
    if key not in st_all:
        rd = road_at(q["x"], q["z"])
        st_all[key] = {"road_built": rd, "road_3dep": y3[pid][s_] + elev0, "pts": []}
    on_road = road_at(x, z) is not None
    st_all[key]["pts"].append((abs(off), h, ground_at(x, z), on_road))
wall_rows = []
for (pid, s_, side), r in sorted(st_all.items()):
    if r["road_built"] is None or not (cuts_s[pid][0] <= s_ <= cuts_s[pid][1]):
        continue
    for lo, hi, tag in ((12, 20, "12-20"), (12, 35, "12-35")):
        win = [t for t in r["pts"] if lo <= t[0] <= hi and t[2] is not None and not t[3]]
        if not win:
            continue
        real = max(t[1] - r["road_3dep"] for t in win)
        built = max(t[2] + elev0 - r["road_built"] for t in win)
        wall_rows.append({"piece": pid, "s": s_, "side": "left" if side > 0 else "right", "band": tag,
                          "real_m": round(real, 2), "built_m": round(built, 2)})
wa = {}
for tag in ("12-20", "12-35"):
    w3 = [q for q in wall_rows if q["band"] == tag and q["real_m"] >= 3.0]
    short = sorted([q for q in w3 if q["real_m"] - q["built_m"] > 1.0], key=lambda q: (q["piece"], q["side"], q["s"]))
    runs, cur = [], None
    for q in short:
        k = (q["piece"], q["side"])
        if cur and cur["k"] == k and q["s"] - cur["s_to"] <= 5.01:
            cur["s_to"] = q["s"]
            cur["n"] += 1
        else:
            if cur:
                runs.append(cur)
            cur = {"k": k, "s_from": q["s"], "s_to": q["s"], "n": 1}
    if cur:
        runs.append(cur)
    shortfall = sorted(q["real_m"] - q["built_m"] for q in w3)
    wa[tag] = {"stations_real_ge_3m": len(w3), "short_gt_1m": len(short),
               "kept_under_half": sum(1 for q in w3 if q["built_m"] < 0.5 * q["real_m"]),
               "shortfall_median_m": round(shortfall[len(shortfall) // 2], 2) if shortfall else None,
               "runs_ge_20m": [{"piece": c["k"][0], "side": c["k"][1], "s_from": c["s_from"], "s_to": c["s_to"],
                                "length_m": round(c["s_to"] - c["s_from"] + 5.0, 1)}
                               for c in runs if c["s_to"] - c["s_from"] + 5.0 >= 20.0],
               "short_stations": [[q["piece"], q["side"], q["s"], q["real_m"], q["built_m"]] for q in short][:60]}
res["walls_all"] = wa
# ---- lamp 77 (ledger 0054 prep: v0.18.1 stood it behind J1's R 30 return; is its foot on the apron's ground?)
lights = json.loads((PROJ / "data" / "lights.local.json").read_text(encoding="utf-8"))["lampheads"]
hx, hy, hz = lights[77]
post = []
cur = None
with open(PROJ / "data" / "track.obj", encoding="ascii", errors="replace") as f:
    Vall = []
    for ln in f:
        c2 = ln[:2]
        if c2 == "v ":
            q = ln.split()
            Vall.append((float(q[1]), float(q[2]), float(q[3])))
        elif c2 in ("o ", "g "):
            cur = ln[2:].strip().upper()
        elif c2 == "f " and cur and cur.startswith("LIGHTPOST"):
            for t in ln.split()[1:]:
                v = Vall[int(t.split("/")[0]) - 1]
                if math.hypot(v[0] - hx, v[2] - hz) < 6.0:
                    post.append(v)
if post:
    base = min(post, key=lambda v: v[1])
    gnd = [h for h, n in F.at(base[0], base[2]) if not n.startswith(("MARKINGS", "YLINE", "1WALL", "LIGHT", "SIGN"))]
    top = max(gnd) if gnd else None
    res["lamp77"] = {"head": [hx, hy, hz], "base": [round(c, 3) for c in base],
                     "surface_under_base": None if top is None else round(top, 3),
                     "base_minus_surface_m": None if top is None else round(base[1] - top, 3),
                     "head_over_surface_m": None if top is None else round(hy - top, 3),
                     "head_over_surface_rule_m": 8.8,
                     "surfaces": sorted({n for _h, n in F.at(base[0], base[2])})}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({"V1": {k: v for k, v in res["V1"].items() if k != "aerial_stations"}, "V2": res["V2"],
                  "walls": {"lost_stretches_ge_50m": lost, "stations_with_real_wall": res["walls"]["stations_with_real_wall"],
                            "of_them_lost": res["walls"]["of_them_lost"]},
                  "walls_all": {k: {kk: vv for kk, vv in v.items() if kk != "short_stations"} for k, v in wa.items()},
                  "lamp77": res.get("lamp77")}, indent=1))
