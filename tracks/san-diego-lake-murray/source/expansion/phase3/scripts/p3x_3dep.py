"""Phase 3 terrain lens, profiles only: USGS 3DEP 1 m along the three new roads (the shape of
source/expansion/routes__profile_3dep.json and revise__measure.json, whose research scripts are not in the repo).

Points (local frame of data/centerline.local.json -> lon / lat through tools/author_expansion.Frame):
  * both OSM carriageways of each leg (cw and acw), every STEP_M along the path, end nodes included;
  * the midline skeleton (p3x_legs.py), every STEP_M;
  * the junction nodes (both carriageways at J2, J6, J7, J3);
  * every public side street, junction arm and link mouth: along its own OSM way from the node out to ARM_M every
    STEP_M; every service mouth at 0, 10 and 20 m.
Fetched through the round-2 job's p3_net (scripts.elevation.usgs_3dep._sample_batch's request shape: POST multipoint
wkid 4326, returnFirstValueOnly, 450 points a request, one at a time, TLS verified) with a generic User-Agent.

    python -I p3x_3dep.py <airoso> <osm.expansion.json> <legs-dir> <dl-dir> <cap-bytes>
Writes <dl-dir>/points.json (every point, why it was asked) and <dl-dir>/samples.json (the values as 3DEP gave
them), <dl-dir>/net.jsonl (every request).
"""
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p3_net_r2 as net  # noqa: E402

net.UA = "data-fetch/1.0"
STEP_M = 5.0
ARM_M = 40.0
SERVICE_AT = (0.0, 10.0, 20.0)


def main():
    airoso, osm_p, legs_d, dl = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    cap = int(sys.argv[5])
    sys.path.insert(0, str(airoso / "tools"))
    import author_expansion as ae
    dl.mkdir(parents=True, exist_ok=True)
    osm = json.loads(osm_p.read_text())
    nodes = {int(k): v for k, v in osm["nodes"].items()}
    ways = {w["id"]: w for w in osm["ways"]}
    an = json.loads((legs_d / "routes_analysis.west.json").read_text())
    mo = json.loads((legs_d / "mouths.west.raw.json").read_text())
    sk = json.loads((legs_d / "skeleton.west.json").read_text())
    fr = ae.Frame(sk["frame"]["origin"])
    xy = lambda n: fr.xz(*nodes[n][:2])
    pts = []     # [tag, s, x, z]

    def along(P, tag):
        sl = ae.arc(P)
        k = 0
        while k * STEP_M <= sl[-1] + 1e-9:
            q = ae.at_arc(P, sl, k * STEP_M)
            pts.append([tag, round(k * STEP_M, 2), q[0], q[1]])
            k += 1
        if sl[-1] - (k - 1) * STEP_M > 0.5:
            pts.append([tag, round(sl[-1], 2), P[-1][0], P[-1][1]])

    for sense in ("cw", "acw"):
        for lg in an[sense]:
            along([xy(n) for n in lg["path_nodes"]], f"{lg['leg']}.{sense}")
    for lid, pc in sk["pieces"].items():
        P = [(r[1], r[2]) for r in pc["stations"]]
        along(P, f"{lid}.mid")
    for j, (a, b) in an["meta"]["junction_nodes_cw_acw"].items():
        for n, nm in ((a, "cw"), (b, "acw")):
            p = xy(n)
            pts.append([f"node.{j}.{nm}", 0.0, p[0], p[1]])
    for lid, recs in mo["mouths"].items():
        for k, r in enumerate(recs):
            w = ways[r["way"]]["nodes"]
            i = w.index(r["node"])
            j = w.index(r["next_node"])
            seq = w[i::1] if j > i else w[i::-1]
            P = [xy(n) for n in seq]
            sl = ae.arc(P)
            at = SERVICE_AT if r["kind"] == "service" else [m * STEP_M for m in range(int(ARM_M / STEP_M) + 1)]
            for u in at:
                if u > sl[-1] + 1e-9:
                    break
                q = ae.at_arc(P, sl, u)
                pts.append([f"mouth.{lid}.{k}", u, q[0], q[1]])
    lonlat = [fr.lonlat(p[2], p[3]) for p in pts]
    (dl / "points.json").write_text(json.dumps({"what": "the 3DEP points of the Phase 3 profiles (tag, s or u m, x, z, "
                                                        "lon, lat)", "frame": sk["frame"],
                                                "points": [p[:2] + [round(p[2], 3), round(p[3], 3), round(lo, 8),
                                                                    round(la, 8)] for p, (lo, la) in zip(pts, lonlat)]}))
    print(f"{len(pts)} points, {-(-len(pts) // 450)} requests", flush=True)
    budget = net.Budget(cap, str(dl / "net.jsonl"))
    t0 = time.time()
    q = [(round(lo, 8), round(la, 8)) for lo, la in lonlat]
    vals = net.sample_points(q, budget, chunk=450,
                             progress=lambda a, n: print(f"  {a}/{n} requests, {budget.used} B", flush=True))
    none = sum(1 for v in vals if v is None)
    (dl / "samples.json").write_text(json.dumps({
        "source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (returnFirstValueOnly)",
        "endpoint": net.GET_SAMPLES, "user_agent": net.UA, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "units": "metres above NAVD88", "requests": budget.requests, "bytes": budget.used, "backoffs": budget.backoffs,
        "no_value": none, "values": vals}))
    print(f"done: {budget.requests} requests, {budget.used} B, {budget.backoffs} back-offs, {none} no-value, "
          f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
