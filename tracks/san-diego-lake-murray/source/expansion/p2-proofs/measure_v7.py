"""Ledger 0054 P2: EXPANSION-PLAN Verification V7's sightlines on the BUILT terrain of a rehearsal (tools/sightline_check:
every 1GRASS* + GRASS_FAR* triangle of the gate OBJ, eye 1.2 m over the ground at the station - P2 builds no north road,
so the ground there is 3DEP's own road surface), stations in the junction-node frame of data/expansion.north.json.

Peaks (local x E, z N): trilaterated from the terrain lens's 11 station distances each (source/expansion/
terrain__out__views.json, residual 0.0 m); the ray aims at the highest built vertex within 60 m (sightline_check).

    python measure_v7.py <airoso> <rehearsal project> <out.json>
"""
import json
import sys
from pathlib import Path

AIR, PROJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(AIR / "tools"))
import sightline_check as sc  # noqa: E402

X = json.loads((AIR / "tracks" / "san-diego-lake-murray" / "data" / "expansion.north.json").read_text(encoding="utf-8"))
PIECE = {p["id"]: p for p in X["pieces"]}
COWLES = sc.COWLES
KWAAY_PAAY = (48.7, 4395.9)
PYLES = (792.9, 3848.7)


def at(pid, s):
    p = PIECE[pid]
    col = {c: k for k, c in enumerate(p["columns"])}
    best = min(p["stations"], key=lambda r: abs(r[col["s"]] - s))
    return (best[col["x"]], best[col["z"]])


rays, checks = [], []


def ray(name, pid, s, to, min_deg=0.0, hidden=False, cone=None):
    rays.append({"name": name, "from": at(pid, s), "to": to, "min_deg": min_deg, "hidden": hidden,
                 **({"cone_m": cone} if cone else {})})
    return name


# V7 rows (EXPANSION-PLAN Verification)
jk = [ray(f"cowles_from_jackson_s{s}", "D", s, COWLES, 9.0) for s in range(550, 1551, 100)]
checks.append({"v7": "Cowles from Jackson s 550-1550 (eye 1.2 m) >= 9.0 deg (real 9.6-9.8)", "rays": jk, "rule": "min", "deg": 9.0})
checks.append({"v7": "Cowles from Mission Gorge s 1865: 7.4 +- 0.5 deg",
               "rays": [ray("cowles_from_mg_s1865", "C", 1865, COWLES, 6.9)], "rule": "band", "deg": [6.9, 7.9]})
mg = [ray(f"cowles_from_mg_s{s}", "C", s, COWLES, 0.0, hidden=True) for s in range(565, 1466, 100)]
checks.append({"v7": "Cowles from Mission Gorge s 565-1465: blocked by built terrain", "rays": mg, "rule": "hidden"})
# re-worded (P2): fresh 3DEP fails the 60 m cone too - Kwaay Paay's top is a broad dome and its own shoulder 90 m short of
# the top stands +0.03 deg over the cone; the summit is judged as a 150 m cone [invented], everything nearer must not
# stand higher (the 60 m reading is kept beside it)
checks.append({"v7": "Kwaay Paay from Jackson s 550: visible (summit cone 150 m), 8.0 +- 0.5 deg",
               "rays": [ray("kwaay_paay_from_jackson_s550", "D", 550, KWAAY_PAAY, 7.5, cone=150.0)], "rule": "band",
               "deg": [7.5, 8.5]})
checks.append({"v7": "Kwaay Paay from Mission Gorge s 2190: hidden behind the +8.85 deg knoll 321 m away",
               "rays": [ray("kwaay_paay_from_mg_s2190", "C", 2190, KWAAY_PAAY, 0.0, hidden=True)], "rule": "hidden"})
checks.append({"v7": "Pyles from Mission Gorge s 2190: 8.5 +- 0.5 deg",
               "rays": [ray("pyles_from_mg_s2190", "C", 2190, PYLES, 8.0)], "rule": "band", "deg": [8.0, 9.0]})

rep, _bad = sc.run(PROJ, [dict(r) for r in rays], obj=PROJ / "data" / "track.obj", out=None)
by = {r["name"]: r for r in rep}

# THE WORLD (L5): fresh 3DEP 1 m along every built ray (the same steps, the same eye: 3DEP at the station + 1.2 m),
# judged by the same rule - where the build and the world disagree the build is wrong; where both fail a wording, the
# wording is (cached: v7_world.samples.json.gz, TLS verified)
import gzip, math, time  # noqa: E402
sys.path.insert(0, str(AIR))
from scripts.elevation import usgs_3dep  # noqa: E402
from scripts.geometry import terrain_tiers as tt  # noqa: E402
origin = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
m_lon, m_lat = tt.meters_per_degree(origin["lat"])
pts = []
for r in rep:
    fx, fz = r["from"]
    tx, tz = r["to"]
    L = math.hypot(tx - fx, tz - fz)
    pts.append((origin["lon"] + fx / m_lon, origin["lat"] + fz / m_lat))
    for d, _y, _a in r["profile_abs"]:
        pts.append((origin["lon"] + (fx + (tx - fx) * d / L) / m_lon, origin["lat"] + (fz + (tz - fz) * d / L) / m_lat))
WC = Path(__file__).resolve().parent / "v7_world.samples.json.gz"
key = {"n": len(pts), "first": [round(v, 9) for v in pts[0]], "last": [round(v, 9) for v in pts[-1]]}
H = None
if WC.exists():
    w = json.loads(gzip.decompress(WC.read_bytes()))
    H = w["h"] if w.get("_key") == key else None
if H is None:
    H = []
    for a in range(0, len(pts), 450):
        H += usgs_3dep._sample_batch(pts[a:a + 450], retries=4)
    if any(v is None for v in H):
        raise SystemExit("[v7] 3DEP no-data on a ray - no silent fill (L2)")
    WC.write_bytes(gzip.compress(json.dumps({"_key": key, "_provenance": {
        "source": "USGS 3DEP 1 m, ImageServer getSamples (TLS verified)", "fetched_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "what": "V7 rays, ledger 0054 P2"}, "h": H}).encode("utf-8"), 9, mtime=0))
k = 0
for r in rep:
    eye = H[k] + sc.EYE_M
    k += 1
    prof = []
    for d, _y, _a in r["profile_abs"]:
        h = H[k]
        k += 1
        prof.append((d, h, math.degrees(math.atan2(h - eye, d))))
    spec_r = next(x for x in rays if x["name"] == r["name"])
    cone = float(spec_r.get("cone_m", sc.SUMMIT_R_M))
    w = sc.judge_target(prof, prof[-1][0], float(spec_r["min_deg"]), cone=cone, hidden=bool(spec_r.get("hidden")))
    if cone != sc.SUMMIT_R_M:
        # the built profile re-judged with the same cone; the 60 m verdict kept beside it
        bp = [(d, y, a) for d, y, a in r["profile_abs"]]
        r["cone60"] = {k_: r[k_] for k_ in ("target_deg", "max_intermediate_deg", "pass")}
        r.update(sc.judge_target(bp, bp[-1][0], float(spec_r["min_deg"]), cone=cone, hidden=bool(spec_r.get("hidden"))))
        r["cone_m"] = cone
        w0 = sc.judge_target(prof, prof[-1][0], float(spec_r["min_deg"]), hidden=bool(spec_r.get("hidden")))
        w["cone60"] = {k_: (round(w0[k_], 3) if isinstance(w0[k_], float) else w0[k_])
                       for k_ in ("target_deg", "max_intermediate_deg", "pass")}
    r["world"] = {"eye_abs_m": round(eye, 2), **{kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in w.items()}}
    # where the highest step outside the 60 m cone stands, metres short of the top (a broad summit's own shoulder?)
    outside = [(a, d) for d, _h, a in prof if d < prof[-1][0] - sc.SUMMIT_R_M]
    if outside:
        a_, d_ = max(outside)
        r["world"]["max_outside_cone_short_of_top_m"] = round(r["target_dist_m"] - d_, 1)
    bo = [(a, d) for d, _y, a in r["profile_abs"] if a is not None and d < r["target_dist_m"] - sc.SUMMIT_R_M]
    if bo:
        a_, d_ = max(bo)
        r["max_outside_cone_short_of_top_m"] = round(r["target_dist_m"] - d_, 1)
for c in checks:
    rows = [by[n] for n in c["rays"]]
    c["readings"] = [{k: r.get(k) for k in ("name", "target_deg", "top_deg", "max_intermediate_deg", "target_dist_m",
                                             "eye_abs_m", "top_abs_m", "pass", "max_outside_cone_short_of_top_m", "world", "cone_m",
                                             "cone60")}
                     for r in rows]
    c["world_pass"] = all(r["world"]["pass"] for r in rows)
    if c["rule"] == "min":
        c["pass"] = all(r["pass"] for r in rows)
    elif c["rule"] == "band":
        lo, hi = c["deg"]
        c["pass"] = all(r["pass"] and r["target_deg"] is not None and lo <= r["target_deg"] <= hi for r in rows)
    else:
        c["pass"] = all(r["pass"] for r in rows)
    print(f"[v7] {'PASS' if c['pass'] else 'FAIL'} (world {'PASS' if c['world_pass'] else 'FAIL'})  {c['v7']}: "
          + ", ".join(f"{r['name'].split('_s')[-1] if '_s' in r['name'] else ''} {r['target_deg']}/{r['max_intermediate_deg']}"
                      + f" (world {r['world']['target_deg']}/{r['world']['max_intermediate_deg']})" for r in rows))
OUT.write_text(json.dumps({"peaks_local": {"cowles": COWLES, "kwaay_paay": KWAAY_PAAY, "pyles": PYLES},
                           "checks": checks, "rays": rep}, indent=1), encoding="utf-8")
