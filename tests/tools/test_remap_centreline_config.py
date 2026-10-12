"""tools/remap_centreline_config.py: every vertex index and station the config declares, onto a new centreline.

Lookout Lariat V3 (ledger 0048, P2). A synthetic lap (a stadium at 3 m points, the timing line one vertex
before v0 as projection.py picks it on the Lariat) and a "new" line that bulges 1 m out over st 100-200 at
1 m points and re-samples the seam at 1 m (so projection's start pick moves, as it did: + 1 -> + 2). Pinned:
the rotation emulation equals scripts/geometry/projection.py's own; vertices land on the same place; stations
keep their place (before the bulge unchanged, after it longer by exactly the added length); the start line
stays 0 and the lap end stays the lap end; hairpin_fit.climb_st_m is untouched; precision is kept; the quoted
docs follow; layout_dummies still validates; the frame record makes a second run a no-op and refuses a line
it cannot match. Plus the real Lariat: the committed config is on the committed centreline.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import remap_centreline_config as rc  # noqa: E402
from scripts.geometry.projection import _meters_per_degree  # noqa: E402

LAT0, LON0 = 39.70, -105.20
MLON, MLAT = _meters_per_degree(LAT0)
R, L = 40.0, 300.0
LARIAT = ROOT / "tracks" / "lookout-lariat"


def ll(p):
    return [LON0 + p[0] / MLON, LAT0 + p[1] / MLAT]


def lap_point(s):
    """The stadium by station: east along y = 0, left semicircle, west along y = 2R, left semicircle."""
    per = 2 * L + 2 * math.pi * R
    s %= per
    if s < L:
        return (s, 0.0), (1.0, 0.0)
    s -= L
    if s < math.pi * R:
        a = -math.pi / 2 + s / R
        return (L + R * math.cos(a), R + R * math.sin(a)), (-math.sin(a), math.cos(a))
    s -= math.pi * R
    if s < L:
        return (L - s, 2 * R), (-1.0, 0.0)
    s -= L
    a = math.pi / 2 + s / R
    return (R * math.cos(a), R + R * math.sin(a)), (-math.sin(a), math.cos(a))


PER = 2 * L + 2 * math.pi * R


def old_line():
    n = int(PER / 3.0)
    return [lap_point(PER * k / n)[0] for k in range(n)], [PER * k / n for k in range(n)]


def new_line():
    """1 m points over st 100-200 bulging 1 m south (smooth), 1 m points within 9 m of the seam, else the old
    vertices; osm_station_m = the old station of each point."""
    old, sts = old_line()
    pts, osm = [], []
    for p, s in zip(old, sts):
        if 100 <= s <= 200 or s <= 9 or s >= PER - 9:
            continue
        pts.append(p)
        osm.append(s)
    extra = [s for s in range(0, 10)] + [s for s in range(100, 201)] + [PER - k for k in range(9, 0, -1)]
    for s in extra:
        q, t = lap_point(s)
        bump = 0.0
        if 100 <= s <= 200:
            u = (s - 100) / 100.0
            bump = math.sin(math.pi * u) ** 2  # 0 -> 1 -> 0, smooth
        pts.append((q[0] + t[1] * bump, q[1] - t[0] * bump))  # right of travel = south on the first straight
        osm.append(float(s))
    order = sorted(range(len(pts)), key=lambda i: osm[i])
    return [pts[i] for i in order], [osm[i] for i in order]


def geojson(pts, osm=None):
    coords = [ll(p) for p in pts] + [ll(pts[0])]
    props = {"kind": "full", "closed": True, "widths_m": [6.7] * len(coords), "point_count": len(coords)}
    if osm is not None:
        props["osm_station_m"] = list(osm) + [osm[0] + PER]
        props["paint_centreline"] = {"tool": "test"}
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": props,
                                                       "geometry": {"type": "LineString", "coordinates": coords}}]}


def config(n_old):
    # start_at 2.4 m before v0: projection picks the last 3 m vertex (local = geo + 1), and on the new line
    # (1 m points there) the vertex 2 m before v0 (local = geo + 2), as on the Lariat
    sa, _ = lap_point(PER - 2.4)
    lon, lat = ll(sa)
    return {
        "name": "t", "slug": "t", "location": {"lat": LAT0, "lon": LON0}, "source": {"type": "osm"},
        "loop": True, "default_width_m": 6.7, "origin": "centroid", "surfaces": {}, "lighting": {},
        "true_north_rotation_deg": 0.0,
        "route": {"start_at": [lat, lon]},
        "hairpin_fit": {"climb_st_m": [0, 300], "corners": [{"id": "C1", "st_m": 362, "_doc": "v40 stays prose"}]},
        "width_overrides": [{"st_m": [0, 150]}, {"st_m": [150, 851]}],
        "layouts": [
            {"id": "street_full", "kind": "street", "direction": "forward", "race_furniture": False,
             "start": {"line_vertex": 0, "grid_vertex": n_old - 9, "offset_right_m": 1.6, "sector_vertices": [20, 160]},
             "_start_doc": f"Forward grid v{n_old - 9} = 27.0 m behind the line; sectors v20 (st 60.0) and v160 (st 480.0)."},
            {"id": "street_reverse", "kind": "street", "direction": "reverse", "race_furniture": False,
             "start": {"line_vertex": 0, "grid_vertex": 9, "offset_right_m": 1.6, "sector_vertices": [160, 20]},
             "_start_doc": "As street_full's, mirrored: grid v9, sectors reversed."}],
        "race": {"grid_slots": 8, "pit_slots": 8, "corridor": {
            "boxes": [{"corner": "B1", "apex": 60, "i": 52, "j": 68, "st_m": [155.5, 203.25]}],
            "_boxes_doc": "B1 spans (v52, v68); v0.15.0 is a version, not a vertex."}},
        "_history": {"route.wide_corners": [{"station_m": 120}]},
        "scenery": {"zones": [{"st_m": [[10.5, 99.25]]}, {"st_m": [[400, 852]]}]},
    }


def project(tmp: Path):
    proj = tmp / "proj"
    (proj / "data").mkdir(parents=True)
    old, _ = old_line()
    new, osm = new_line()
    (proj / "data" / "centerline.osm.geojson").write_text(json.dumps(geojson(old)), encoding="utf-8")
    (proj / "data" / "centerline.geojson").write_text(json.dumps(geojson(new, osm)), encoding="utf-8")
    (proj / "track.config.json").write_text(json.dumps(config(len(old)), indent=2) + "\n", encoding="utf-8")
    return proj


def test_rotation_emulation_equals_projection():
    from scripts.geometry import projection
    with tempfile.TemporaryDirectory() as td:
        proj = project(Path(td))
        for name in ("centerline.osm.geojson", "centerline.geojson"):
            data = proj / "data"
            src = data / name
            work = Path(td) / ("w_" + name)
            (work / "data").mkdir(parents=True)
            (work / "track.config.json").write_text((proj / "track.config.json").read_text(encoding="utf-8"), encoding="utf-8")
            (work / "data" / "centerline.geojson").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            n = len(json.loads(src.read_text(encoding="utf-8"))["features"][0]["geometry"]["coordinates"])
            (work / "data" / "centerline.elevation.json").write_text(json.dumps({"z_smooth_m": [0.0] * n}), encoding="utf-8")
            projection.build(work)
            loc = json.loads((work / "data" / "centerline.local.json").read_text(encoding="utf-8"))
            cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
            lf = rc.LineFrames(src, cfg["route"]["start_at"])
            lon0, lat0 = loc["origin"]["lon"], loc["origin"]["lat"]
            ml, mt = _meters_per_degree(lat0)
            assert loc["point_count"] == len(lf.local_lonlat)
            for (lon, lat), (x, _, z) in zip(lf.local_lonlat, loc["points_xyz_m"]):
                assert abs((lon - lon0) * ml - x) < 0.006 and abs((lat - lat0) * mt - z) < 0.006
        old = rc.LineFrames(proj / "data" / "centerline.osm.geojson", cfg["route"]["start_at"])
        new = rc.LineFrames(proj / "data" / "centerline.geojson", cfg["route"]["start_at"])
        assert (old.m - old.k) % old.m == 1  # local = geojson + 1 on the 3 m line, as on the Lariat's OSM line
        assert (new.m - new.k) % new.m == 2  # and + 2 once the seam is at 1 m points


def test_values_land_on_the_same_place():
    with tempfile.TemporaryDirectory() as td:
        proj = project(Path(td))
        cfg0 = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
        rep, cfg = rc.run(proj, write=True, log=lambda *a: None)
        assert rep["layout_dummies_fails"] == {"old": [], "new": []}
        ch = {c["path"]: c for c in rep["changes"]}
        # every vertex lands within the bulge (1 m) of where it was
        for c in rep["changes"]:
            if c["frame"] == "local index":
                assert c["moved_m"] <= 1.1, c
        assert cfg["layouts"][0]["start"]["line_vertex"] == 0
        # sectors are on straights outside the bulge: the same place exactly
        assert ch["layouts[0].start.sector_vertices[0]"]["moved_m"] < 0.01
        # the box at st ~178 (on the bulge): within the bulge
        assert ch["race.corridor.boxes[0].apex"]["moved_m"] <= 1.0
        added = rep["new_line"]["length_m"] - rep["old_line"]["length_m"]
        assert 0.02 < added < 0.5
        # stations: the same PLACE on both lines (the new start pick sits 1 m further on, so a place's distance
        # from the start line drops by 1 m); 0 stays 0 and the lap's end stays its end; precision kept
        start = cfg0["route"]["start_at"]
        oldf = rc.LineFrames(proj / "data" / "centerline.osm.geojson", start)
        newf = rc.LineFrames(proj / "data" / "centerline.geojson", start)

        def place(lf, s):
            pts, st = lf.local_lonlat, lf.local_st
            i = max(k for k in range(len(st)) if st[k] <= min(s, st[-1]))
            j = min(i + 1, len(st) - 1)
            t = 0.0 if st[j] == st[i] else (s - st[i]) / (st[j] - st[i])
            lon = pts[i][0] + t * (pts[j][0] - pts[i][0])
            lat = pts[i][1] + t * (pts[j][1] - pts[i][1])
            return ((lon - LON0) * MLON, (lat - LAT0) * MLAT)
        n_local = 0
        for c in rep["changes"]:
            if c["frame"] != "local station" or c["old"] in (0, 852):
                continue
            n_local += 1
            rounding = 0.5 if isinstance(c["old"], int) else 0.01
            assert math.dist(place(oldf, c["old"]), place(newf, c["new"])) <= 1.0 + rounding + 0.02, c
            assert type(c["new"]) is type(c["old"])
        assert n_local >= 6
        assert cfg["width_overrides"][0]["st_m"][0] == 0  # the start line stays 0
        # a value past the old lap's end (the Lariat writes its end as 24906 > 24905.7) stays past the new end
        assert cfg["scenery"]["zones"][1]["st_m"][0][1] == round(newf.local_lap + (852 - oldf.local_lap))
        assert cfg["width_overrides"][0]["st_m"][1] == 149  # 150 m from the old start line = 149 m from the new one
        z = cfg["scenery"]["zones"][0]["st_m"][0]
        assert all(abs(a - (b - 1.0)) <= 0.02 for a, b in zip(z, (10.5, 99.25)))  # before the bulge: the start shift
        assert all(len(repr(v).split(".")[1]) <= 2 for v in z)                     # decimals kept
        b = cfg["race"]["corridor"]["boxes"][0]["st_m"]
        assert isinstance(b[1], float) and len(repr(b[1]).split(".")[1]) <= 2
        # geojson-frame corner stations follow the new line's own stations; climb_st_m is never remapped
        assert abs(cfg["hairpin_fit"]["corners"][0]["st_m"] - (362 + added)) <= 0.5
        assert cfg["hairpin_fit"]["climb_st_m"] == [0, 300]
        assert cfg["_history"]["route.wide_corners"][0]["station_m"] == 119  # history is remapped too (a local station)
        # the quoted docs: vertices, stations and the grid distance; a version string is not a vertex
        doc = cfg["layouts"][0]["_start_doc"]
        g = cfg["layouts"][0]["start"]["grid_vertex"]
        s0, s1 = cfg["layouts"][0]["start"]["sector_vertices"]
        assert f"v{g} = " in doc and f"v{s0} (st " in doc and f"v{s1} (st " in doc and "v20 " not in doc
        assert f"grid v{cfg['layouts'][1]['start']['grid_vertex']}," in cfg["layouts"][1]["_start_doc"]
        bd = cfg["race"]["corridor"]["_boxes_doc"]
        assert f"(v{cfg['race']['corridor']['boxes'][0]['i']}, v{cfg['race']['corridor']['boxes'][0]['j']})" in bd and "v0.15.0" in bd
        assert cfg["hairpin_fit"]["corners"][0]["_doc"] == "v40 stays prose"  # only the named docs change
        # the input config object was not modified by remap()
        assert cfg0["layouts"][0]["start"]["sector_vertices"] == [20, 160]
        # the record, and the file on disk is the written config
        on_disk = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
        fr = on_disk["centerline_frame"]
        assert fr["md5"] == rc.text_md5(proj / "data" / "centerline.geojson")
        assert list(on_disk.keys()).index("centerline_frame") == list(on_disk.keys()).index("source") + 1
        assert json.loads((proj / "data" / "centerline_remap.json").read_text(encoding="utf-8"))["changes"]


def test_idempotent_and_refuses_an_unknown_frame():
    with tempfile.TemporaryDirectory() as td:
        proj = project(Path(td))
        rc.run(proj, write=True, log=lambda *a: None)
        before = (proj / "track.config.json").read_bytes()
        rep, _ = rc.run(proj, write=True, log=lambda *a: None)
        assert rep["changes"] == [] and (proj / "track.config.json").read_bytes() == before
        assert rc.main([str(proj), "--write"]) == 0
        # the line changes again without the replaced line being kept: the record matches nothing -> refuse
        gj = json.loads((proj / "data" / "centerline.geojson").read_text(encoding="utf-8"))
        gj["features"][0]["geometry"]["coordinates"][5][0] += 1e-7
        (proj / "data" / "centerline.geojson").write_text(json.dumps(gj), encoding="utf-8")
        try:
            rc.run(proj, write=True, log=lambda *a: None)
            raise AssertionError("remapped from a line it cannot match")
        except SystemExit as e:
            assert "refusing to guess" in str(e)
        assert rc.main([str(proj), "--write"]) == 2
        # ... but with the replaced line kept as centerline.previous.geojson it maps from that one
        old_paint = json.dumps(json.loads(before.decode("utf-8")))  # noqa: F841  (config unchanged)
        prev = proj / "data" / "centerline.previous.geojson"
        gj["features"][0]["geometry"]["coordinates"][5][0] -= 1e-7
        prev.write_text(json.dumps(gj), encoding="utf-8")
        cfg = json.loads(before.decode("utf-8"))
        cfg["centerline_frame"]["md5"] = rc.text_md5(prev)
        (proj / "track.config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        rep, cfg2 = rc.run(proj, write=True, log=lambda *a: None)
        assert rep["old_line"]["path"] == "data/centerline.previous.geojson"
        assert all(c["old"] == c["new"] for c in rep["changes"] if c["frame"] == "local index")


def test_real_lariat_config_is_on_the_committed_centreline():
    cl = LARIAT / "data" / "centerline.geojson"
    rm = LARIAT / "data" / "centerline_remap.json"
    if not (cl.exists() and rm.exists()):
        return
    cfg = json.loads((LARIAT / "track.config.json").read_text(encoding="utf-8"))
    assert cfg["centerline_frame"]["md5"] == rc.text_md5(cl)
    rep = json.loads(rm.read_text(encoding="utf-8"))
    assert rep["new_line"]["md5"] == cfg["centerline_frame"]["md5"]
    assert rep["layout_dummies_fails"]["new"] == []
    ch = {c["path"]: c for c in rep["changes"]}
    assert cfg["layouts"][0]["start"]["grid_vertex"] == ch["layouts[0].start.grid_vertex"]["new"]
    # a junction apex (race.corridor.boxes[*].apex: C12, C14, C15, C16, C18) was the OSM junction NODE; since the
    # junction fillets (2026-10-12) the lap turns on an arc inside it, so its nearest vertex sits up to the arc's
    # offset from the node (R (sec(turn / 2) - 1), <= 5 m on these corners); every other vertex stays within 1.5 m
    assert all(c["moved_m"] < (6.0 if ".apex" in c["path"] else 1.5) for c in rep["changes"]
               if c["frame"] == "local index"), [c for c in rep["changes"] if c["frame"] == "local index" and c["moved_m"] >= 1.5]
    assert cfg["hairpin_fit"]["climb_st_m"] == [0, 7100]
    out, _ = rc.run(LARIAT, write=False, log=lambda *a: None)
    assert out["changes"] == [] and out.get("already_on") == cfg["centerline_frame"]["md5"]
