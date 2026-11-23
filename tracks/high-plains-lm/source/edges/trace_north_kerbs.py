"""The Full layout's north-loop kerbs, measured (ledger 0097 round 4, item 1): ledger 0081's method on the north loop's line.

    python -I trace_north_kerbs.py <repo>      (numpy + Pillow; rewrites kerbs.lm.json's north-loop runs beside itself)

  find     a colour scan of each lane-edge band (tools/kerb_spans.paint_class: blue present) over road wear's mosaic
           (source/road_wear/naip_2023_hp_mosaic.png: the 0.3 m crop, and the z18 photos (0.46 m) above it) and the eye on
           straightened strips of the whole loop: SPANS below, each checked by eye on zooms at 30 px/m with 1 m ticks
  measure  tools/kerb_offsets.py, the block reader (ledger 0081 round 3: light / dark blocks along the edge, colour not used;
           calibrated against High Plains' 20 colour-measured runs, raised blue / white kerbs inside its 0.4 m bar at 0.3 m
           and at 0.6 m), --follow 1 (the north loop's line is OSM's measured centre, not the kerb: the band's middle drifts
           0.3-0.6 m along a run), on the north loop's own line (source/full/connectors.full.json, its widths); in_m / out_m
           across that line's lane edge, as every kerbs.lm.json run. tools/kerb_spans.py's colour read of the same span is
           kept beside each run ("colour_read"): on the z18 photos the kerbs' blue is faded, so colour is the weaker read
  ends     the reader's, except where they lie more than 1 m off the blocks on the end zooms (the reader runs 0.5-1.5 m past
           a visible end: ledger 0081 round 3): those are the eye's (":eye")
  built    each run names its line, "line": "full_north#0#0" (the north loop as the chain's trim leaves it; opt-in in
           tools/author_kerbs_blend.py), and is laid as the lap's 20 are (kerb.placement "measured", the config's
           kerb.height_m 0.08 [invented] and end_ramp_m 4.0 [invented])
NOT measured, so not built: the two blue / yellow edge stripes the strips show (L s 372-401, L s 648-682): flat stripes fail
the block reader's bar (ledger 0081 round 3), and on the z18 photo their blue does not read as blue (kerb_spans: no paint in
L s 372-401, 4 of 35 stations in L s 648-682).
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINE = "full_north#0#0"
# side:s0-s1:colour[:eye] on the north loop's own s (connectors.full.json, from the fork's OSM node), checked by eye
SPANS = ("R:58-97:blue_white",                 # Bobsled's first kerb (0.3 m crop)
         "L:169.8-216.3:blue_white:eye",       # the reader ran 2.7 m past the last block (an edge line goes on)
         "R:307.5-334.8:blue_white:eye",       # the reader began 1.3 m before the first block
         "R:545.7-637.8:blue_white:eye",       # the north hairpin's apex kerb; the reader began 2.3 m late
         "L:733-759:blue_white",
         "L:982.8-{t13}:blue_white:eye")       # T13's kerb on Ladder's edge (0.3 m crop); the reader began 1.2 m late. It ends
#                                               where the West's T13 run (L s 2,843, re-traced onto the corner's paint in round
#                                               3) begins: the north loop's s nearest that run's first edge point (t13_end), so
#                                               the two pieces of one kerb meet and do not overlap
MOSAIC = "source/road_wear/naip_2023_hp_mosaic"


def t13_end(conn, K, origin):
    """the north loop's s (its own line, connectors.full.json) whose LEFT lane edge lies nearest the first edge point of the
    West lap's T13 run (kerbs.lm.json L s 2,843): where the West's piece of that kerb begins"""
    import numpy as np
    w = next(k for k in K["kerbs"] if not k.get("line") and k["side"] == "left" and k["s0"] == 2843.0)
    lon0, lat0 = origin["lon"], origin["lat"]
    m_lon, m_lat = ko.mpd(lat0)
    v0 = ((w["edge_lonlat"][0][0] - lon0) * m_lon, (w["edge_lonlat"][0][1] - lat0) * m_lat)
    P_ = np.array(conn["points_xyz_m"])
    Wd = np.array(conn["widths_m"])
    st = np.r_[0, np.cumsum(np.hypot(np.diff(P_[:, 0]), np.diff(P_[:, 2])))]
    s = np.arange(st[-1] - 40.0, st[-1], 0.1)
    x, n, hw = np.interp(s, st, P_[:, 0]), np.interp(s, st, P_[:, 2]), np.interp(s, st, Wd) / 2
    tx, tz = np.gradient(x), np.gradient(n)
    L_ = np.hypot(tx, tz)
    ex, en = x - tz / L_ * hw, n + tx / L_ * hw
    return round(float(s[int(np.argmin(np.hypot(ex - v0[0], en - v0[1])))]), 1)


def main(repo: Path):
    P = repo / "tracks" / "high-plains-lm"
    sys.path.insert(0, str(repo / "tools"))
    global ko
    import kerb_offsets as ko    # noqa: E402
    import kerb_spans as ksp     # noqa: E402
    rec = json.loads((P / (MOSAIC + ".json")).read_text(encoding="utf-8"))
    corners = ",".join(str(v) for v in rec["corners"])
    conn = json.loads((P / "source" / "full" / "connectors.full.json").read_text(encoding="utf-8"))["connectors"][0]
    K = json.loads((HERE / "kerbs.lm.json").read_text(encoding="utf-8"))
    origin = json.loads((P / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
    end = t13_end(conn, K, origin)
    spans = tuple(sp.format(t13=end) for sp in SPANS)
    print(f"[north kerbs] T13 on Ladder's edge ends at north-loop s {end} (the West T13 run's first edge point)")
    with tempfile.TemporaryDirectory() as td:
        T = Path(td)
        (T / "data").mkdir()
        shutil.copy(P / "data" / "centerline.local.json", T / "data" / "centerline.local.json")
        (T / "data" / "gate_centerline.json").write_text(json.dumps(
            {"points_xyz_m": conn["points_xyz_m"], "widths_m": conn["widths_m"]}), encoding="utf-8")
        out = T / "north.json"
        ko.main([str(T), "--image", str(P / (MOSAIC + ".png")), "--corners", corners, "--spans", ",".join(spans),
                 "--follow", "1", "--out", str(out), "--strips", str(HERE / "kerbs_north_blocks_strips.jpg"),
                 "--imagery", "road wear's mosaic (source/road_wear/naip_2023_hp_mosaic.png): USDA NAIP 2023-09-28, the 0.3 m "
                 "crop and its z18 tiles (0.46 m) above it"])
        runs = json.loads(out.read_text(encoding="utf-8"))["kerbs"]
        colour = {}
        for spec in spans:
            sd, rng, col = spec.split(":")[:3]
            cout = T / "colour.json"
            ksp.main([str(T), "--image", str(P / (MOSAIC + ".png")), "--corners", corners, "--spans", f"{sd}:{rng}:{col}",
                      "--imagery", "mosaic", "--out", str(cout)])
            c = json.loads(cout.read_text(encoding="utf-8"))["kerbs"][0]
            colour[(sd, rng)] = {"in_m": c["in_m"], "out_m": c["out_m"], "stations": c["stations_measured"]}
    K["kerbs"] = [r for r in K["kerbs"] if r.get("line") != LINE]
    for spec, r in zip(spans, runs):
        sd, rng = spec.split(":")[:2]
        lo = float(r["s0"])
        photo = "naip_030" if (lo < 120 or lo > 930) else "naip_z18"
        r = {"line": LINE, **r, "colour_read": colour[(sd, rng)], "photo": photo,
             "_source": ("ledger 0097 round 4: the north loop's own s (source/full/connectors.full.json), measured by "
                         "trace_north_kerbs.py (tools/kerb_offsets.py --follow 1 on road wear's mosaic)")}
        K["kerbs"].append(r)
    K["_doc_north"] = ("ledger 0097 round 4: runs with \"line\": \"full_north#0#0\" are the Full layout's north loop's kerbs "
                       "(trace_north_kerbs.py), keyed to that connector's rows by tools/author_kerbs_blend.py (opt-in)")
    (HERE / "kerbs.lm.json").write_text(json.dumps(K, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[north kerbs] {len(runs)} runs, {sum(r['s1'] - r['s0'] for r in runs):.0f} m -> kerbs.lm.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
