"""Re-derive every vertex index and station the config declares onto a new centreline.

Lookout Lariat V3 (ledger 0048, P2). When ``data/centerline.geojson`` changes (here: the OSM line became the
paint centreline, ``tools/paint_centreline.py``), every vertex index and station in ``track.config.json`` that
points into the old line is stale: the climb is now 1 m points, so a vertex past it moves by thousands of
indices, and stations shift by the change in length. This tool maps each one by **station matching** through
the one key both lines share: the station on the OSM line (``osm_station_m``, carried by the paint
centreline for every vertex; the old line's own stations, when the old line IS the OSM line).

Frames (L13-aware; each key is mapped within its own frame):
- **local** (``layouts[].start`` vertices, ``race.corridor.boxes[].apex/i/j``, and every ``st_m`` /
  ``station_m`` / ``crosses_st_m`` outside ``hairpin_fit``): ``centerline.local.json``'s index space and
  stations, i.e. the ring rotated by scripts/geometry/projection.py's ``route.start_at`` pick (its own
  metric: the vertex nearest start_at, the closing duplicate dropped and re-added). Emulated here on the
  plan only (no elevation needed), exactly as projection.build rotates.
- **geojson** (``hairpin_fit.corners[].st_m``, ``span_st_m``): stations from v0 of data/centerline.geojson,
  as tools/fit_hairpins.py reads them.
- ``hairpin_fit.climb_st_m`` is **not** remapped: it is defined on the OSM source line
  (``data/centerline.osm.geojson``), which is how tools/paint_centreline.py and tools/verify_centreline_paint.py
  read it.

A vertex maps to the new vertex whose OSM station is nearest (local v0 stays 0: on either line it is
projection's start_at pick, the timing line); a station maps by linear interpolation along the new line (0
stays 0 and the lap's end stays its end). Numbers keep their precision (an integer stays an integer). The named ``_doc`` strings that
quote vertex numbers or stations (the layouts' ``_start_doc``, the race boxes' ``_boxes_doc``) have those
numbers rewritten too. Then the layouts are validated with tools/layout_dummies.py on a plan-only projection
of the new line (the line 0 < d <= 35 m ahead of the grid, sectors increasing and on straights).

Which line the config's numbers refer to is recorded in the config itself, ``centerline_frame.md5``. The old
line is found by that md5 among ``--old``, ``data/centerline.previous.geojson`` (the paint centreline
tools/paint_centreline.py replaced) and ``data/centerline.osm.geojson``; with no record the config is taken
to be on the OSM line (P0). A config already on the new line is left alone (nothing to do), and a record that
matches no candidate is refused (exit 2), so a value is never shifted twice.

Writes ``data/centerline_remap.json`` (every change with its frame, both lines' md5, the rotation each
frame uses) and, with ``--write``, the config (its values, the quoted docs and ``centerline_frame``). No
thresholds here.

    python tools/remap_centreline_config.py <project-dir> [--old F] [--new F] [--write] [--out F]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)
from scripts.geometry.projection import _meters_per_degree, centroid  # noqa: E402

STATION_KEYS = {"st_m", "station_m", "crosses_st_m"}
FRAME_KEY = "centerline_frame"


def text_md5(path) -> str:
    """md5 of a text file's content with LF line ends (as git stores it)."""
    return hashlib.md5(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_line(path):
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    f = next((x for x in gj["features"] if (x.get("properties") or {}).get("kind") == "full"), None)
    if f is None:
        f = next(x for x in gj["features"] if (x.get("geometry") or {}).get("type") == "LineString")
    return [(float(c[0]), float(c[1])) for c in f["geometry"]["coordinates"]], f.get("properties") or {}


def plan_stations(lonlat):
    lon0, lat0 = centroid(lonlat)
    mlon, mlat = _meters_per_degree(lat0)
    P = [((a - lon0) * mlon, (b - lat0) * mlat) for a, b in lonlat]
    st = [0.0]
    for i in range(1, len(P)):
        st.append(st[-1] + math.dist(P[i - 1], P[i]))
    return P, st


def projection_rotation(lonlat, start_at, loop=True):
    """projection.build's ring rotation: (k, closed, n_unique). Local index i <-> geojson index
    (i + k) mod n_unique; the closing vertex is dropped before the pick and re-added after."""
    closed = len(lonlat) > 2 and lonlat[0] == lonlat[-1]
    coords = lonlat[:-1] if closed else list(lonlat)
    k = 0
    if start_at and loop and len(coords) > 2:
        m_lon, m_lat = _meters_per_degree(float(start_at[0]))
        k = min(range(len(coords)), key=lambda i: ((coords[i][0] - float(start_at[1])) * m_lon) ** 2
                + ((coords[i][1] - float(start_at[0])) * m_lat) ** 2)
    return k, closed, len(coords)


class LineFrames:
    """One centreline: geojson and local frames, OSM stations per vertex."""

    def __init__(self, path, start_at, loop=True, osm_stations=None):
        self.path = Path(path)
        self.lonlat, self.props = load_line(path)
        self.P, self.st = plan_stations(self.lonlat)
        self.k, self.closed, self.m = projection_rotation(self.lonlat, start_at, loop)
        rot = self.lonlat[:-1] if self.closed else list(self.lonlat)
        rot = rot[self.k:] + rot[:self.k]
        if self.closed:
            rot = rot + [rot[0]]
        self.local_lonlat = rot
        _, self.local_st = plan_stations(rot)
        self.lap = self.st[-1]
        self.local_lap = self.local_st[-1]
        src = osm_stations if osm_stations is not None else self.props.get("osm_station_m")
        self.osm = list(src) if src else list(self.st)
        self.md5 = text_md5(self.path)

    def local_to_geo(self, v):
        return (v + self.k) % self.m

    def geo_to_local(self, g):
        return (g - self.k) % self.m

    def local_station_offset(self):
        """Local station of geojson v0."""
        return (self.local_lap - self.st[self.k]) % self.local_lap if self.k else 0.0


def _interp(xs, ys, x):
    lo, hi = 0, len(xs) - 1
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    t = 0.0 if xs[hi] == xs[lo] else (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + t * (ys[hi] - ys[lo])


class Mapper:
    def __init__(self, old: LineFrames, new: LineFrames):
        self.old, self.new = old, new
        if len(new.osm) != len(new.lonlat):
            raise SystemExit("[remap] the new line carries no osm_station_m per vertex")
        self.osm_lap = old.osm[-1] if old.closed else old.osm[-1]

    # stations: old geojson -> OSM -> new geojson
    def geo_station(self, s_old):
        o = _interp(self.old.st, self.old.osm, s_old)
        return _interp(self.new.osm, self.new.st, o)

    def local_station(self, s_old_local):
        """A local-frame station on the old line -> the same place's local station on the new line. The two
        ends of a lap stay ends: 0 (the start line) stays 0, and a value at or past the old lap's end keeps
        its distance past the new lap's end (the config writes the lap end as 24906)."""
        old, new = self.old, self.new
        if s_old_local <= 1e-9:
            return 0.0
        if old.closed and s_old_local >= old.local_lap - 1e-6:
            return new.local_lap + (s_old_local - old.local_lap)
        s_geo = s_old_local - old.local_station_offset()
        if old.closed and s_geo < 0:
            s_geo += old.lap
        s_new = self.geo_station(s_geo) + new.local_station_offset()
        if new.closed and s_new >= new.local_lap:
            s_new -= new.local_lap
        return s_new

    def local_index(self, v_old):
        """A local vertex on the old line -> the new line's vertex at the same OSM station. Local v0 is
        projection's start_at pick on either line (the timing line), so it stays 0."""
        old, new = self.old, self.new
        if int(v_old) == 0:
            return 0
        o = old.osm[old.local_to_geo(int(v_old))]
        # the new vertex with the nearest OSM station (they increase along the line)
        xs = new.osm[:new.m] if new.closed else new.osm
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= o:
                lo = mid
            else:
                hi = mid
        g = lo if abs(xs[lo] - o) <= abs(xs[hi] - o) else hi
        if new.closed and abs(o - old.osm[-1]) < abs(o - xs[g]):
            g = 0
        return new.geo_to_local(g)

    def position_shift_m(self, v_old, v_new):
        """Plan distance between the old local vertex and the new one (a sanity number)."""
        a = self.old.local_lonlat[int(v_old)]
        b = self.new.local_lonlat[int(v_new)]
        lat0 = 0.5 * (a[1] + b[1])
        ml, mt = _meters_per_degree(lat0)
        return math.hypot((a[0] - b[0]) * ml, (a[1] - b[1]) * mt)


def _decimals(x):
    if isinstance(x, int) and not isinstance(x, bool):
        return None
    r = repr(float(x))
    return len(r.split(".")[1]) if "." in r and "e" not in r else 6


def _round_like(new, old):
    d = _decimals(old)
    return int(round(new)) if d is None else round(new, d)


def remap(cfg, mapper):
    """(new config, changes). Pure: the input is not modified."""
    out = copy.deepcopy(cfg)
    changes = []
    _walk(out, [], mapper, changes)
    return out, changes


def _walk(node, path, mapper, changes):
    if isinstance(node, dict):
        for key in list(node.keys()):
            val = node[key]
            names = [p for p in path if isinstance(p, str)]
            in_hairpin = "hairpin_fit" in names
            parent = names[-1] if names else ""
            if (key.startswith("_") and key != "_history") or key == FRAME_KEY:
                continue
            if in_hairpin and key == "climb_st_m":
                continue
            if (parent == "start" and key in ("line_vertex", "grid_vertex", "sector_vertices")) or \
                    (parent == "boxes" and key in ("apex", "i", "j")):
                node[key] = _map_vals(val, mapper.local_index, path + [key], "local index", changes, mapper)
                continue
            if key in STATION_KEYS or (in_hairpin and key == "span_st_m"):
                frame = "geojson station" if in_hairpin else "local station"
                fn = mapper.geo_station if in_hairpin else mapper.local_station
                node[key] = _map_vals(val, fn, path + [key], frame, changes, mapper)
                continue
            _walk(val, path + [key], mapper, changes)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            _walk(x, path + [i], mapper, changes)


def _map_vals(val, fn, path, frame, changes, mapper):
    if isinstance(val, list):
        return [_map_vals(x, fn, path + [i], frame, changes, mapper) for i, x in enumerate(val)]
    if not isinstance(val, (int, float)) or isinstance(val, bool) or val is None:
        return val
    new = fn(val)
    new = _round_like(new, val)
    rec = {"path": _path_str(path), "frame": frame, "old": val, "new": new}
    if frame == "local index":
        rec["moved_m"] = round(mapper.position_shift_m(val, new), 2)
    changes.append(rec)
    return new


def _path_str(path):
    out = ""
    for p in path:
        out += f"[{p}]" if isinstance(p, int) else (("." if out else "") + p)
    return out


# --------------------------------------------------------------------------------------------------
# the prose that quotes vertex numbers and stations
# --------------------------------------------------------------------------------------------------
def remap_docs(cfg_new, cfg_old, changes, mapper):
    """Rewrite the vertex numbers (v1234) and '(st 1234.5)' stations quoted in the layouts' _start_doc and
    the race boxes' _boxes_doc, and the grid's 'N m behind the line' distances; return the doc changes."""
    vmap = {}
    for c in changes:
        if c["frame"] == "local index":
            vmap[int(c["old"])] = int(c["new"])
    smap = {}
    for c in changes:
        if c["frame"] == "local station":
            smap[float(c["old"])] = c["new"]
    docs = []
    targets = []
    for i, lo in enumerate(cfg_new.get("layouts") or []):
        if "_start_doc" in lo:
            targets.append((lo, "_start_doc", f"layouts[{i}]._start_doc"))
    corr = (cfg_new.get("race") or {}).get("corridor") or {}
    if "_boxes_doc" in corr:
        targets.append((corr, "_boxes_doc", "race.corridor._boxes_doc"))
    new_line = mapper.new
    for node, key, where in targets:
        old = node[key]

        def vsub(m):
            v = int(m.group(1))
            if v == 0:
                return m.group(0)
            nv = vmap.get(v)
            if nv is None:
                nv = mapper.local_index(v)
            return f"v{nv}"
        txt = re.sub(r"(?<![\w.])v(\d+)(?![\w.]|\.\d)", vsub, old)

        def ssub(m):
            s = float(m.group(1))
            ns = mapper.local_station(s)
            return f"(st {ns:.1f})"
        txt = re.sub(r"\(st (\d+(?:\.\d+)?)\)", ssub, txt)

        def dsub(m):  # "grid v14417 = 26.9 m behind the line": the new grid's own distance
            v = int(m.group(1))
            lay = next((lo for lo in cfg_new.get("layouts") or [] if int((lo.get("start") or {}).get("grid_vertex", -1)) == v), None)
            if lay is None:
                return m.group(0)
            return f"v{v} = {grid_distances({'layouts': [lay]}, new_line)[lay['id']]:.1f} m behind"
        txt = re.sub(r"v(\d+) = (\d+(?:\.\d+)?) m behind", dsub, txt)

        def rsub(m):  # "grid v26 = 26.1 m behind it" (the reverse grid quoted in the same sentence)
            v = int(m.group(1))
            lay = next((lo for lo in cfg_new.get("layouts") or [] if int((lo.get("start") or {}).get("grid_vertex", -1)) == v), None)
            if lay is None:
                return m.group(0)
            return f"grid v{v} = {grid_distances({'layouts': [lay]}, new_line)[lay['id']]:.1f} m behind it"
        txt = re.sub(r"grid v(\d+) = (\d+(?:\.\d+)?) m behind it", rsub, txt)
        if txt != old:
            node[key] = txt
            docs.append({"path": where, "old": old, "new": txt})
    return docs


def grid_distances(cfg, line: LineFrames):
    """Distance along the line from each layout's grid vertex to its line vertex, in its driving direction."""
    out = {}
    st = line.local_st
    lap = line.local_lap
    for lo in cfg.get("layouts") or []:
        s = lo.get("start") or {}
        g, ln = int(s.get("grid_vertex", 0)), int(s.get("line_vertex", 0))
        d = (st[ln] - st[g]) % lap if lo.get("direction", "forward") == "forward" else (st[g] - st[ln]) % lap
        out[lo["id"]] = round(d, 1)
    return out


def validate_layouts(cfg, line: LineFrames):
    """tools/layout_dummies.py's per-layout checks on a plan-only projection of the line (y = 0)."""
    import layout_dummies as ld
    lon0, lat0 = centroid(line.local_lonlat)
    ml, mt = _meters_per_degree(lat0)
    pts = [((a - lon0) * ml, 0.0, (b - lat0) * mt) for a, b in line.local_lonlat]
    widths = [cfg.get("default_width_m", 6.7)] * len(pts)
    L = ld.Line(pts, widths)
    fails = list(ld.validate_layouts(cfg.get("layouts") or []))
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for lo in cfg.get("layouts") or []:
            _, f = ld.layout_dummies(L, lo, cfg.get("race") or {})
            fails += f
    return fails


def _find_old(old, rec, data):
    """The line the config's numbers refer to: by the recorded md5, else (no record) the OSM source line."""
    cands = [Path(old)] if old else [data / "centerline.previous.geojson", data / "centerline.osm.geojson"]
    if not rec.get("md5"):
        return cands[0] if old else data / "centerline.osm.geojson"
    for c in cands:
        if c.exists() and text_md5(c) == rec["md5"]:
            return c
    raise SystemExit(f"[remap] the config's numbers refer to a centreline with md5 {rec['md5']}, and none of "
                     f"{[str(c) for c in cands]} is that line: refusing to guess (a value would shift twice)")


def _with_frame(cfg, frame):
    """cfg with centerline_frame placed after 'source' (or last)."""
    out = {}
    for k, v in cfg.items():
        if k == FRAME_KEY:
            continue
        out[k] = v
        if k == "source":
            out[FRAME_KEY] = frame
    if FRAME_KEY not in out:
        out[FRAME_KEY] = frame
    return out


def _rel(path, base):
    try:
        return str(Path(path).resolve().relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run(project_dir, old=None, new=None, write=False, out=None, log=print):
    project_dir = Path(project_dir).resolve()
    data = project_dir / "data"
    cfg_path = project_dir / "track.config.json"
    raw = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(raw)
    start_at = (cfg.get("route") or {}).get("start_at")
    loop = bool(cfg.get("loop", True))
    new_path = Path(new) if new else data / "centerline.geojson"
    new_md5 = text_md5(new_path)
    rec = cfg.get(FRAME_KEY) or {}
    if rec.get("md5") == new_md5:
        log(f"[remap] the config is already on {new_path.name} (md5 {new_md5}): nothing to do")
        return {"tool": "tools/remap_centreline_config.py", "already_on": new_md5, "changes": [], "doc_changes": [],
                "layout_dummies_fails": {"old": [], "new": []}}, cfg
    old_path = _find_old(old, rec, data)
    oldf = LineFrames(old_path, start_at, loop)
    newf = LineFrames(new_path, start_at, loop)
    if "osm_station_m" not in oldf.props:
        oldf.osm = list(oldf.st)  # the old line IS the OSM line
    mapper = Mapper(oldf, newf)
    cfg_new, changes = remap(cfg, mapper)
    docs = remap_docs(cfg_new, cfg, changes, mapper)
    fails_old = validate_layouts(cfg, oldf)
    fails_new = validate_layouts(cfg_new, newf)
    rep = {
        "tool": "tools/remap_centreline_config.py",
        "old_line": {"path": _rel(oldf.path, project_dir), "md5": oldf.md5, "points": len(oldf.lonlat),
                     "length_m": round(oldf.lap, 2), "projection_start_pick_geojson_v": oldf.k,
                     "local_index_is_geojson_index_plus": (oldf.m - oldf.k) % oldf.m,
                     "local_station_of_geojson_v0_m": round(oldf.local_station_offset(), 3)},
        "new_line": {"path": _rel(newf.path, project_dir), "md5": newf.md5, "points": len(newf.lonlat),
                     "length_m": round(newf.lap, 2), "projection_start_pick_geojson_v": newf.k,
                     "local_index_is_geojson_index_plus": (newf.m - newf.k) % newf.m,
                     "local_station_of_geojson_v0_m": round(newf.local_station_offset(), 3)},
        "frames": {
            "local": "centerline.local.json's index space and plan stations: the ring rotated by projection.py's route.start_at pick (emulated, plan only)",
            "geojson": "data/centerline.geojson's own index space and plan stations from its v0 (tools/fit_hairpins.py)",
            "osm": "stations on data/centerline.osm.geojson, the key both lines share (osm_station_m on the paint centreline)",
            "not_remapped": "hairpin_fit.climb_st_m: defined on the OSM source line",
        },
        "method": "vertex -> the new vertex with the nearest OSM station; station -> linear interpolation along the new line; precision kept",
        "start_line_moved_m": round(mapper.position_shift_m(0, 0), 3),
        "grid_distance_behind_line_m": {"old": grid_distances(cfg, oldf), "new": grid_distances(cfg_new, newf)},
        "layout_dummies_fails": {"old": fails_old, "new": fails_new},
        "changes": changes,
        "doc_changes": docs,
    }
    outp = Path(out) if out else data / "centerline_remap.json"
    outp.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    if write:
        cfg_new = _with_frame(cfg_new, {
            "file": _rel(newf.path, project_dir), "md5": newf.md5,
            "osm_source": "data/centerline.osm.geojson",
            "osm_source_md5": text_md5(data / "centerline.osm.geojson")
            if (data / "centerline.osm.geojson").exists() else None,
            "remapped_from_md5": oldf.md5, "remapped_by": "tools/remap_centreline_config.py (data/centerline_remap.json)",
            "_doc": ("The centreline every vertex index and station in this config refers to (its md5). "
                     "tools/remap_centreline_config.py re-derives them by station matching whenever data/centerline.geojson "
                     "changes, and refuses a line it cannot match to this record."),
        })
        cfg_path.write_text(json.dumps(cfg_new, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    log(f"[remap] {len(changes)} values ({sum(1 for c in changes if c['frame'] == 'local index')} vertex indices), "
        f"{len(docs)} docs; layout_dummies fails old {len(fails_old)}, new {len(fails_new)}; wrote {outp}"
        + (" and the config" if write else " (config untouched: --write)"))
    return rep, cfg_new


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        rep, _ = run(a.project_dir, a.old, a.new, a.write, a.out)
    except (SystemExit, FileNotFoundError) as e:
        print(f"[remap] {e}", file=sys.stderr)
        return 2
    return 1 if rep["layout_dummies_fails"]["new"] else 0


if __name__ == "__main__":
    sys.exit(main())
