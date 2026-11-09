"""Feed a track's line into Lake Murray v4's loop assembler (ledger 0078: every track is built from LM v4's engine).

The assembler (tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py) reads, from <project>/data:
  centerline.local.json   {origin {lon, lat, elev_m}, points_xyz_m [[x=E, y=elev-elev0, z=N]], widths_m} — a CLOSED loop
                          repeats point 0 last (L13); the assembler snapshots it as centerline.raw.local.json on its first
                          run and smooths from that snapshot on every rebuild
  heightfield.npy / .meta.json  the 3DEP grid (bbox_swne, nx, ny, spacing_m, row 0 = north)
  connectors.local.json   optional side streets (their own 3DEP), swept and merged into ROAD / CURB / MARKINGS
and from track.config.json route.smooth_* / route.divided_double, terrain.terrain_band_m, scenery.*.

Every track already has those inputs from airoso's data stages (scripts.gps.centerline -> scripts.elevation.heightfield ->
scripts.geometry.projection -> scripts.gps.widths_from_osm): data/centerline.local.json is the projected line with its 3DEP
profile and its per-vertex widths, in the frame the assembler reads (ENU metres about the config's origin, unmirrored).
This tool copies them from the SOURCE track (track.config.json lm_intake.source_track, a folder under tracks/) into the
project and applies one piece of elevation evidence to the line before smoothing, Y only:
  - capture.bridges: each declared deck held level over the bare-earth dip (scripts.capture.evidence.level_bridge_decks,
    keyed to this draft line's stations, as build_mesh keys it) — a DATA fact (the bare-earth DEM has no deck in it).
NO GRADE CAP (Kevin 2026-11-03: "I just want real"): the profile is the measured ground. airoso's build_mesh clamps every
track to road_profile.max_grade_pct (6 % by default) and the v021 modules carry 12 % / 11 % caps; none of them runs here.
An artefact in the data (a dip under a tree, an underpass) is fixed at its source (lidar class 2, a measured deck), never
clamped. lm_intake.max_grade_pct exists only as an explicit, reported opt-in; absent = no cap.
X/Z, the widths and the point count are the source's. Nothing here smooths, rounds a corner or touches a width: that is
the assembler's job (scripts-v021/geometry/smooth.py), which is the point of the port.

    python tools/lm_engine_intake.py <project-dir> [--connectors]

<project-dir>/track.config.json must carry lm_intake.source_track. --connectors (or lm_intake.connectors true) also
copies the source's data/connectors.local.json; without it the draft is the lap alone (no side street).
Writes data/lm_intake.json (what was taken, from where, md5s) beside the inputs. Exit 2 on any input it cannot use.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
SWITCHBACK_RMS_M = 1.0   # [invented] round 9: a measured switchback is fitted only where both edge circles fit within this
SWITCHBACK_TURN_DEG = 100.0  # round 10: the turns drive_test's corner rule judges (>100 deg); a measured platform round a gentler bend is not refitted
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

from scripts.capture import evidence  # noqa: E402


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _read_npy(path: Path) -> list[list[float]]:
    """a 2-D little-endian float64 .npy (the heightfield; stdlib only, as the assembler's own reader)"""
    import ast
    import struct
    with open(path, "rb") as f:
        if f.read(6) != b"\x93NUMPY":
            raise SystemExit(f"[lm_intake] {path} is not a .npy")
        major = f.read(2)[0]
        hlen = struct.unpack("<H" if major == 1 else "<I", f.read(2 if major == 1 else 4))[0]
        header = ast.literal_eval(f.read(hlen).decode("latin1"))
        if header.get("descr") != "<f8" or header.get("fortran_order") or len(header["shape"]) != 2:
            raise SystemExit(f"[lm_intake] {path}: expected a C-order <f8 2-D array, got {header}")
        ny, nx = header["shape"]
        data = struct.unpack(f"<{ny * nx}d", f.read(8 * ny * nx))
    return [list(data[j * nx:(j + 1) * nx]) for j in range(ny)]


def _write_npy(path: Path, grid: list[list[float]]) -> None:
    import struct
    ny, nx = len(grid), len(grid[0])
    header = "{'descr': '<f8', 'fortran_order': False, 'shape': (%d, %d), }" % (ny, nx)
    pad = 64 - (10 + len(header) + 1) % 64
    header = header + " " * pad + "\n"
    with open(path, "wb") as f:
        f.write(b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header.encode("latin1"))
        f.write(struct.pack(f"<{ny * nx}d", *[v for row in grid for v in row]))


def _upsample(grid, meta, factor):
    """bilinear, corners kept (the assembler's scripts-v021 ribbon.upsample_grid, the same rule)"""
    ny, nx = len(grid), len(grid[0])
    by, bx = (ny - 1) * factor + 1, (nx - 1) * factor + 1
    out = []
    for jj in range(by):
        fy = jj / factor
        j0 = min(ny - 1, int(fy)); j1 = min(ny - 1, j0 + 1); ty = fy - j0
        row = []
        for ii in range(bx):
            fx = ii / factor
            i0 = min(nx - 1, int(fx)); i1 = min(nx - 1, i0 + 1); tx = fx - i0
            a = grid[j0][i0] * (1 - tx) + grid[j0][i1] * tx
            b = grid[j1][i0] * (1 - tx) + grid[j1][i1] * tx
            row.append(a * (1 - ty) + b * ty)
        out.append(row)
    m2 = dict(meta)
    m2["nx"], m2["ny"], m2["spacing_m"] = bx, by, meta["spacing_m"] / factor
    return out, m2


def _max_grade(pts, over_m: float) -> float:
    """the steepest grade of a line over a horizontal run of ``over_m`` (the same reading for the intake and the build)"""
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    best, j = 0.0, 0
    for i in range(len(pts)):
        while j < len(pts) - 1 and st[j] - st[i] < over_m:
            j += 1
        if st[j] - st[i] >= over_m * 0.5:
            best = max(best, abs(pts[j][1] - pts[i][1]) / (st[j] - st[i]))
    return best



def apply_connector_profiles(proj: Path, prof_p: str) -> list:
    """ledger 0079 round H (opt-in lm_intake.connector_profiles): the named streets' heights measured off the lidar
    (tools/lidar_connector_profile.py: the road surface, ground + bridge deck returns, at each source point) replace the
    3DEP grid's in <proj>/data/connectors.local.json, which cannot hold a bridge or an embankment. Each point's plan
    position must be the profile's own (the profile was measured on these points), else the run stops."""
    data = proj / "data"
    prof = json.loads((proj / prof_p).read_text(encoding="utf-8"))["connectors"]
    cj = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))
    done = []
    for c in cj["connectors"]:
        pr = prof.get(c["name"])
        if pr is None:
            continue
        pts = c["points_xyz_m"]
        if len(pr["y"]) != len(pts) or any(abs(p[0] - q[0]) > 0.01 or abs(p[2] - q[1]) > 0.01
                                           for p, q in zip(pts, pr["xz"])):
            raise SystemExit(f"[lm_intake] {prof_p}: {c['name']} was measured on other points; re-run "
                             "tools/lidar_connector_profile.py")
        dy = [y - p[1] for y, p in zip(pr["y"], pts)]
        for p, y in zip(pts, pr["y"]):
            p[1] = float(y)
        done.append(f"{c['name']} ({min(dy):+.2f}..{max(dy):+.2f} m)")
    missing = sorted(set(prof) - {c["name"] for c in cj["connectors"]})
    if missing:
        raise SystemExit(f"[lm_intake] {prof_p}: no such connector(s) {missing}")
    (data / "connectors.local.json").write_text(json.dumps(cj), encoding="utf-8")
    print(f"[lm_intake] connector heights off the lidar ({prof_p}): {', '.join(done)}")
    return done

def corner_flares_off(pts, widths, origin, entries):
    """THE DECLARED CORNERS' FLARES OFF (lm_intake.corner_flare_off; ledger 0079 round Q, Sand Creek). The source's widths
    stage (scripts.gps.widths_from_osm) sweeps a junction flare round a turn corner unless route.corner_flare_off declares
    it, and that list is the source track's: the port copies the widths and never re-runs the stage. route.corner_flare_off's
    doc is the rule: a corner joins the list when its authored pad exists, because the pad's measured deck paves the
    crossroads the flare stood in for. Each entry of the PORT's list (at [lat, lon], radius_m, default
    widths_from_osm.FLARE_OFF_RADIUS_M) takes its flare off the copied widths: the crest of widths within radius_m (by
    station) of the nearest lap vertex, out on both sides to where the width stops falling (each leg's own width), is
    re-laid by station between those two widths. A crest that does not fall to a level leg on both sides is no flare (a
    slip's ramp to the wider road it joins: its crest runs on past the radius) and is left as it is. No new number; a width
    is only ever narrowed (refused otherwise). Returns (widths, report)."""
    from scripts.geometry.projection import _meters_per_degree
    from scripts.gps.widths_from_osm import FLARE_OFF_RADIUS_M
    widths = list(widths)
    rep = []
    m_lon, m_lat = _meters_per_degree(float(origin["lat"]))
    st_f = [0.0]
    for a_, b_ in zip(pts, pts[1:]):
        st_f.append(st_f[-1] + math.hypot(b_[0] - a_[0], b_[2] - a_[2]))
    for cfo in entries:
        ax = (float(cfo["at"][1]) - float(origin["lon"])) * m_lon
        az = (float(cfo["at"][0]) - float(origin["lat"])) * m_lat
        r_ = float(cfo.get("radius_m", FLARE_OFF_RADIUS_M))
        kn = min(range(len(pts)), key=lambda k: (pts[k][0] - ax) ** 2 + (pts[k][2] - az) ** 2)
        dn = math.hypot(pts[kn][0] - ax, pts[kn][2] - az)
        if dn > r_:
            raise SystemExit(f"[lm_intake] corner_flare_off {cfo.get('name')!r}: no lap vertex within {r_} m ({dn:.1f})")
        near = [k for k in range(len(pts)) if abs(st_f[k] - st_f[kn]) <= r_]
        kp = max(near, key=lambda k: widths[k])     # the flare's crest near the node

        def _walk(k, step):
            """out from the crest while the width falls (or holds on the crest), to where it levels at the leg. The crest
            (the widths held before the fall) must lie within radius_m of the node; the fall may run past it.
            (vertex, fell, levelled)"""
            i, fell = k, False
            while 0 <= i + step < len(pts):
                w_a, w_b = widths[i], widths[i + step]
                if w_b < w_a - 1e-9:
                    fell = True
                elif abs(w_b - w_a) <= 1e-9 and not fell:
                    if not near[0] <= i + step <= near[-1]:
                        return i, fell, False
                else:
                    return i, fell, True
                i += step
            return i, fell, False
        (i0, f0, l0), (i1, f1, l1) = _walk(kp, -1), _walk(kp, +1)
        w0, w1 = widths[i0], widths[i1]
        if not (f0 and f1 and l0 and l1) or widths[kp] <= max(w0, w1) + 1e-6:
            rep.append({"name": cfo.get("name"), "vertex": kn, "flare": None})
            print(f"[lm_intake] corner_flare_off {cfo.get('name')!r}: no flare at v{kn} (as the source has it)")
            continue
        was = widths[i0:i1 + 1]
        for k in range(i0, i1 + 1):
            t = (st_f[k] - st_f[i0]) / max(st_f[i1] - st_f[i0], 1e-9)
            w_new = round(w0 + (w1 - w0) * t, 3)
            if w_new > widths[k] + 1e-6:
                raise SystemExit(f"[lm_intake] corner_flare_off {cfo.get('name')!r}: v{k} would widen "
                                 f"({widths[k]} -> {w_new})")
            widths[k] = w_new
        rep.append({"name": cfo.get("name"), "vertex": kn, "flare": [i0, i1], "legs_m": [w0, w1],
                    "was_m": [round(min(was), 2), round(max(was), 2)]})
        print(f"[lm_intake] corner_flare_off {cfo.get('name')!r}: the flare v{i0}..v{i1} ({min(was):.2f}..{max(was):.2f} "
              f"m) re-laid between its legs' {w0:.2f} and {w1:.2f} m")
    return widths, rep


def intake(proj: Path, *, connectors: bool | None = None) -> dict:
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    li = cfg.get("lm_intake") or {}
    src_track = li.get("source_track")
    if not src_track or "/" in src_track or "\\" in src_track or src_track.startswith("."):
        raise SystemExit("[lm_intake] track.config.json lm_intake.source_track must name a folder under tracks/")
    src = AIROSO / "tracks" / src_track
    sdata = src / "data"
    need = [sdata / "centerline.local.json", sdata / "heightfield.npy", sdata / "heightfield.meta.json"]
    # a source track whose heightfield is not committed (High Plains: the elev stage's output lives in its workshop) may
    # have it fetched into the PORT track (scripts.elevation.heightfield on a copy of the source; synced in by ship.json):
    # then the project's own copy is used, and its provenance is the port track's
    # lm_intake.heightfield "port" (ledger 0079, Sand Creek): the port track's OWN grid even where the source commits one —
    # a wider 3DEP grid on the source's lattice (the buildings and the grid streets past the source's 150 m margin), synced
    # in by ship.json. Absent = the source's grid whenever it has one (every port before 0079; Lake Murray never runs this)
    want_own = li.get("heightfield") == "port"
    if li.get("heightfield") not in (None, "port"):
        raise SystemExit(f"[lm_intake] lm_intake.heightfield {li.get('heightfield')!r}: only \"port\" (or absent)")
    hf_own = ((want_own or not need[1].exists()) and (proj / "data" / "heightfield.npy").exists()
              and (proj / "data" / "heightfield.meta.json").exists())
    if want_own and not hf_own:
        raise SystemExit("[lm_intake] lm_intake.heightfield \"port\": the project has no data/heightfield.npy + .meta.json "
                         "(ship.json sync_in.optional must carry the port track's grid)")
    if hf_own:
        need = need[:1]
    need.append(sdata / "centerline.geojson")              # the track folder reads it (written into the port below)
    missing = [str(p) for p in need if not p.exists()]
    if missing:
        raise SystemExit(f"[lm_intake] the source track lacks {missing} — run its gps / elev / project / widths stages first")
    scfg = json.loads((src / "track.config.json").read_text(encoding="utf-8"))
    if scfg.get("mirror_x"):
        # the assembler has no mirror: its frame is the projection's. A mirrored track's line is unmirrored on disk, so
        # it would build fine, but every station / index its config keys to the MIRRORED finished line would not hold.
        print("[lm_intake] note: the source track declares mirror_x; the assembler builds unmirrored (as Lake Murray)")
    local = json.loads(need[0].read_text(encoding="utf-8"))
    pts = [tuple(float(c) for c in p) for p in local["points_xyz_m"]]
    widths = [float(w) for w in local["widths_m"]]
    if len(pts) != len(widths) or len(pts) < 5:
        raise SystemExit(f"[lm_intake] {len(pts)} points vs {len(widths)} widths")
    loop = bool(scfg.get("loop", True))
    closed = math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) < 1e-6
    if loop and not closed:
        raise SystemExit("[lm_intake] the source is a loop but its line does not repeat point 0 last (L13)")
    # THE MEASURED PROFILE, UNCAPPED (lm_intake.profile "uncapped"; Kevin 2026-11-03: "I just want real"). airoso's elevation
    # stage (scripts.elevation.heightfield.build) writes centerline.local.json's Y as profile_along(z_raw): a 33 m median
    # despike, a light mean, then a GRADE CAP (road_profile.max_grade_pct, 9 % by default). The despike and the mean remove
    # DEM artefacts; the cap reshapes the hill. Here the same profile is recomputed from the stage's own raw 3DEP samples
    # (centerline.elevation.json z_raw_m) with the cap off, after first reproducing the committed profile WITH the cap to
    # prove the inputs are the ones that built it (exit 2 otherwise), and put on the line in its own order (projection's
    # source_index, scripts.geometry.projection.in_local_order).
    prof_rep = None
    decks_held = False          # the source profile already holds its declared decks straight (road_profile.py)
    if li.get("profile") == "uncapped":
        from scripts.elevation import heightfield as hf
        from scripts.geometry.projection import in_local_order
        from scripts.gps.centerline import haversine
        ej = json.loads((sdata / "centerline.elevation.json").read_text(encoding="utf-8"))
        gj = json.loads((sdata / "centerline.geojson").read_text(encoding="utf-8"))
        full = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
        coords = [(lon, lat) for lon, lat in full["geometry"]["coordinates"]]
        z_raw = ej["z_raw_m"]
        if len(z_raw) != len(coords) or len(coords) != len(pts):
            raise SystemExit(f"[lm_intake] profile uncapped: {len(z_raw)} raw samples, {len(coords)} geojson points, "
                             f"{len(pts)} line points")
        seg = [haversine(coords[i - 1], coords[i]) for i in range(1, len(coords))]
        rp = scfg.get("road_profile") or {}
        cap_was = float(rp.get("max_grade_pct", 9.0))
        med = float(rp.get("despike_window_m", hf.MEDIAN_WINDOW_M))
        closed_g = bool(full["properties"].get("closed", scfg.get("loop", True)))
        repeats = tuple(coords[0]) == tuple(coords[-1])
        kw = dict(median_m=med, closed=closed_g,
                  close_seg_m=None if (repeats or not closed_g) else haversine(coords[-1], coords[0]))
        if (ej.get("road_profile") or {}).get("tool") == "scripts/elevation/road_profile.py":
            # the source's profile is scripts/elevation/road_profile.py's (metre windows, declared decks held straight,
            # then the cap: the Lariat, ledger 0078 round 6): the same tool on a scratch copy of the source, once at its
            # own cap (it must reproduce the committed profile) and once with the cap off
            import shutil as _sh
            import tempfile as _tf
            from scripts.elevation import road_profile as rprof
            tmp = Path(_tf.mkdtemp(prefix="lm_intake_rp_"))
            try:
                (tmp / "data").mkdir()
                for f in ("centerline.geojson", "centerline.elevation.json", "osm.cache.json"):
                    if (sdata / f).exists():
                        _sh.copyfile(sdata / f, tmp / "data" / f)

                def _run(cap):
                    c2 = json.loads(json.dumps(scfg))
                    c2.setdefault("road_profile", {})["max_grade_pct"] = cap
                    (tmp / "track.config.json").write_text(json.dumps(c2), encoding="utf-8")
                    rprof.build(tmp, write=False, log=lambda *a, **k: None)
                    return [float(v) for v in json.loads((tmp / "data" / "centerline.elevation.json")
                                                         .read_text(encoding="utf-8"))["z_smooth_m"]]
                z_was = _run(cap_was)
                z_new = _run(1e9)
                decks_held = bool((ej.get("road_profile") or {}).get("decks"))
            finally:
                _sh.rmtree(tmp, ignore_errors=True)
        else:
            z_was, _ = hf.profile_along(z_raw, seg, grade_cap_pct=cap_was, **kw)
            z_new, _ = hf.profile_along(z_raw, seg, grade_cap_pct=1e9, **kw)
        dev = max(abs(a - b) for a, b in zip(z_was, ej["z_smooth_m"]))
        if dev > 0.0101:                                # z_smooth_m is written to 0.01 m
            raise SystemExit(f"[lm_intake] profile uncapped: the stage's own profile does not reproduce from its raw "
                             f"samples (max {dev:.3f} m off) — rerun the source track's elev stage")
        z_loc = in_local_order(local, z_new)
        z_old_loc = in_local_order(local, z_was)
        elev0 = float(local["origin"]["elev_m"])
        moved = [abs(a - b) for a, b in zip(z_loc, z_old_loc)]
        pts = [(p[0], z - elev0, p[2]) for p, z in zip(pts, z_loc)]
        prof_rep = {"cap_was_pct": cap_was, "reproduced_within_m": round(dev, 4),
                    "points_moved": sum(1 for d in moved if d > 0.005), "max_move_m": round(max(moved), 3)}
        print(f"[lm_intake] profile uncapped: the stage's {cap_was:.0f} % cap undone ({prof_rep['points_moved']} points, "
              f"max {prof_rep['max_move_m']} m); its despike ({med:.0f} m median) and mean kept")
        # THE ROAD WHERE THE DEM SAYS IT IS (lm_intake.road_seek, the port's data/road_seek.json from tools/road_seek.py;
        # ledger 0078 round 8). Where the mapped line sits off the graded road, 3DEP read along it reads a cut bank or a
        # fill slope; road_seek found the road's centre in 3DEP cross-sections. Each point moves onto it (along the line's
        # own normal) and takes the road's height there; the profile is then the same despike and mean, cap off.
        rs_rel = li.get("road_seek")
        if rs_rel:
            rs = json.loads((proj / rs_rel).read_text(encoding="utf-8"))
            st_ = rs["stations"]
            if len(st_) != len(pts) or rs.get("source_track") != src_track:
                raise SystemExit(f"[lm_intake] road_seek: {rs_rel} was measured for another line ({len(st_)} stations, "
                                 f"this line {len(pts)}; source {rs.get('source_track')})")
            n_ = len(pts)
            # THE GRADED BENCH'S WIDTH (lm_intake.road_seek_widths; round 8): where the DEM bounds the road's graded
            # surface on both sides (a hillside: the cut and the fill), that width and its centre are the road's, the
            # measured switchback platforms included; on level ground (unbounded) the source's width and centre stay.
            # Both smoothed along the line (a Gaussian of 2 stations) so a width never steps.
            shift = [0.0] * n_
            if li.get("road_seek_widths"):
                tw, tc = [], []
                for w_, s_ in zip(widths, st_):
                    bl, bh = (s_.get("bench_m") or [0.0, 0.0])
                    if s_.get("bench_bounded"):
                        tw.append(bh - bl); tc.append((bh + bl) / 2.0)
                    else:
                        tw.append(w_); tc.append(0.0)
                sg_ = 2.0                                  # [invented] stations (6 m): a switchback platform keeps its width
                rr = int(3 * sg_)
                kern = [math.exp(-0.5 * (q / sg_) ** 2) for q in range(-rr, rr + 1)]

                def _sm(v):
                    out_ = []
                    for i in range(n_):
                        num = den = 0.0
                        for q, kw_ in zip(range(i - rr, i + rr + 1), kern):
                            if 0 <= q < n_:
                                num += kw_ * v[q]; den += kw_
                        out_.append(num / den)
                    return out_
                w_was = list(widths)
                widths = [round(w, 3) for w in _sm(tw)]
                shift = _sm(tc)
                nb = sum(1 for s_ in st_ if s_.get("bench_bounded"))
                prof_rep["road_seek_widths"] = {"bounded_stations": nb, "width_m": [round(min(widths), 2),
                                                                                    round(max(widths), 2)],
                                                "changed_by_m_max": round(max(abs(a - b) for a, b in zip(widths, w_was)), 2)}
                print(f"[lm_intake] road_seek widths: the graded bench measured at {nb} of {n_} stations; widths now "
                      f"{min(widths):.2f}..{max(widths):.2f} m (the source's {min(w_was):.2f}..{max(w_was):.2f})")
            from tools import road_seek as _rsk
            pts0_src = list(pts)
            moved_pts, n_relaxed = _rsk.moved_line(pts, st_, shift)       # untangled where it would step backwards
            prof_rep["road_seek_relaxed_points"] = n_relaxed
            seg_l = [math.hypot(moved_pts[i][0] - moved_pts[i - 1][0], moved_pts[i][2] - moved_pts[i - 1][2])
                     for i in range(1, n_)]
            z_rs, _ = hf.profile_along([float(s_["z_m"]) for s_ in st_], seg_l, grade_cap_pct=1e9, median_m=med,
                                       closed=closed_g, close_seg_m=None)
            pts = [(q[0], z - elev0, q[2]) for q, z in zip(moved_pts, z_rs)]
            # THE SWITCHBACKS AS MEASURED (lm_intake.switchback_fit, the port's data/switchbacks.json; round 10): each
            # measured platform's centre arc taken as given and joined to the legs as they are (tools/switchback_fit.py),
            # its width the platform's; a turn whose fit fails its proofs is left as it was, and reported
            sbf = li.get("switchback_fit")
            if sbf:
                from tools import switchback_fit as _sbf
                swb = json.loads((proj / sbf).read_text(encoding="utf-8"))
                use = [c for c in swb["corners"] if c.get("measured") and c.get("turn_deg", 0) > SWITCHBACK_TURN_DEG
                       and c.get("rms_outside_m", 9) <= SWITCHBACK_RMS_M
                       and c.get("rms_inside_m", 9) <= SWITCHBACK_RMS_M]
                # on the line the platforms were measured on (road_seek's, without the bench-centre shift, which wobbles
                # a switchback's legs by up to ~2 m); outside each fitted span the shifted line stays
                base0, _n0 = _rsk.moved_line(pts0_src, st_, None)
                pts0 = [(q[0], z - elev0, q[2]) for q, z in zip(base0, z_rs)]
                fit_p, fit_w, sb_rep = _sbf.fit_all(pts0, list(widths), use)
                for r_ in sb_rep:
                    if r_["status"] == "PASS":
                        a_, b_ = r_["span_i"]
                        for k_ in range(a_ + 1, b_):
                            pts[k_] = fit_p[k_]
                            widths[k_] = fit_w[k_]
                        # the bench-centre shift eased out over BLEND stations into each join (no lateral step there)
                        BLEND = 10
                        for d_ in range(0, BLEND + 1):
                            f_ = d_ / BLEND                          # 0 at the join: the unshifted line; 1: the shifted
                            for k_ in (a_ - d_, b_ + d_):
                                if 0 <= k_ < len(pts):
                                    p1, p0 = pts[k_], pts0[k_]
                                    pts[k_] = (p0[0] + (p1[0] - p0[0]) * f_, p1[1], p0[2] + (p1[2] - p0[2]) * f_)
                prof_rep["switchbacks"] = sb_rep
                for r_ in sb_rep:
                    print(f"[lm_intake] switchback {r_['id']} s {r_['st_m']:.0f}: {r_['status']} R {r_['radius_m']} m, "
                          f"width {r_['width_m']} m, inside edge R {r_.get('inside_edge_r_m')} m, joins "
                          f"{r_.get('join_m')} m, back steps {r_.get('back_steps')}" + (f" ({r_['why']})" if r_.get("why") else ""))
            offs_ = sorted(abs(float(s_["offset_m"])) for s_ in st_)
            prof_rep["road_seek"] = {"file": rs_rel, "offset_abs_m": {"median": round(offs_[len(offs_) // 2], 2),
                                                                       "max": round(offs_[-1], 2)},
                                     "steepest_10m_pct": round(100.0 * _max_grade(pts, 10.0), 2)}
            print(f"[lm_intake] road_seek: {n_} points onto the graded road found in 3DEP cross-sections (off the mapped "
                  f"line median {prof_rep['road_seek']['offset_abs_m']['median']} m, max "
                  f"{prof_rep['road_seek']['offset_abs_m']['max']} m); steepest 10 m now "
                  f"{prof_rep['road_seek']['steepest_10m_pct']} %")
    # Y-only evidence: the declared decks (a data fact); no grade cap unless one is declared (ledger 0078: "I just want real")
    y0 = [p[1] for p in pts]
    bridges = [(float(b["center_m"]), float(b["len_m"])) for b in ((scfg.get("capture") or {}).get("bridges") or [])]
    if bridges and not decks_held:              # (decks road_profile.py held straight stay as it held them)
        pts = evidence.level_bridge_decks(pts, bridges)
    mg = li.get("max_grade_pct")
    max_grade = None if mg is None else float(mg) / 100.0
    if max_grade is not None:
        pts = evidence.cap_grade(pts, max_grade=max_grade)
    if closed:
        pts[-1] = pts[0]
    # THE DECLARED CORNERS' FLARES OFF (lm_intake.corner_flare_off true; ledger 0079 round Q, Sand Creek; absent = the
    # source's widths as traced): corner_flares_off below.
    flare_rep = []
    if li.get("corner_flare_off"):
        widths, flare_rep = corner_flares_off(pts, widths, local["origin"],
                                              (cfg.get("route") or {}).get("corner_flare_off") or [])
    # WIDTH STEPS TAPERED (lm_intake.width_taper, m of half-width per m along; absent = the widths as traced; ledger 0078
    # round 5). A traced width can jump in one station where the paved area takes in a gore or an apron (Milford s 2,604:
    # 12.2 -> 21.7 m in 3 m). The ribbon stays planar across such a row on any bank, but drive_test's wheel paths sit at
    # fractions of the width, so on Milford's 7-10 % lidar bank every jump re-seated them across the slope in one station
    # (kinks and 4 severe steps; 0.6.0 was flat and never showed it). The taper only WIDENS: each point's half-width is the
    # largest of its neighbours' less the rate times the distance, so no measured pavement is lost and every step becomes a
    # flare at the declared rate.
    wt = li.get("width_taper")
    taper_rep = None
    if wt:
        rate = float(wt)
        st_w = [0.0]
        for a, b in zip(pts, pts[1:]):
            st_w.append(st_w[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        lap_w = st_w[-1]
        n_w = len(widths)
        reach = (max(widths) - min(widths)) / 2.0 / rate
        hw = [w / 2.0 for w in widths]
        new = list(hw)
        for i in range(n_w):
            for j in range(n_w):
                if hw[j] <= new[i]:
                    continue
                d = abs(st_w[i] - st_w[j])
                if closed:
                    d = min(d, lap_w - d)
                if d <= reach:
                    new[i] = max(new[i], hw[j] - rate * d)
        moved = [2 * (b - a) for a, b in zip(hw, new)]
        widths = [round(2 * h, 3) for h in new]
        if closed:
            widths[-1] = widths[0]
        taper_rep = {"rate_m_per_m": rate, "points_widened": sum(1 for m in moved if m > 1e-3),
                     "max_widening_m": round(max(moved), 2)}
        print(f"[lm_intake] width steps tapered at {rate} m per m a side: {taper_rep['points_widened']} points widened "
              f"(max {taper_rep['max_widening_m']} m); none narrowed")
    # THE LANE ON A MEASURED PAD (lm_intake.pad_widths [pad records, tools/bench_pad.py]; ledger 0078 round 13). Between a
    # pad's two cuts the deck is the measured platform (tools/lm_pads_blend.py) and the ribbon there is deleted; the lane
    # drive_test reads (its wheel paths, its corner rule) is the widest one CENTRED ON THE LINE that both measured edges
    # allow at each vertex (2 x the nearer edge), never wider than measured, and no wider than the taper allows from its
    # neighbours and from the cut rows (width_taper a side: a lower envelope, so the lane never steps up at a cut). After
    # the taper, so the taper never flares the ribbon outside the cuts out of a platform it does not have. The line itself
    # is not moved: the record names its own vertices and is refused on any other line.
    pad_rep = []
    for rel in li.get("pad_widths") or []:
        rec_p = json.loads((proj / rel).read_text(encoding="utf-8"))
        k0, k1 = rec_p["cuts"]
        lap = {int(x["k"]): x for x in rec_p.get("lap") or []}
        if sorted(lap) != list(range(k0, k1 + 1)):
            raise SystemExit(f"[lm_intake] pad_widths {rel}: its lap does not name every vertex v{k0}..v{k1}")
        off = max(math.hypot(pts[k][0] - lap[k]["raw_xz"][0], pts[k][2] - lap[k]["raw_xz"][1]) for k in lap)
        if off > 0.01:
            raise SystemExit(f"[lm_intake] pad_widths {rel}: measured on another line (a lap vertex {off:.3f} m off) — "
                             f"measure it again (tools/bench_pad.py) on this port's own line")
        st_p = [0.0]
        for a, b in zip(pts, pts[1:]):
            st_p.append(st_p[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        rate_p = float(wt) if wt else 0.0
        anchors = [(k0, widths[k0]), (k1, widths[k1])]
        anchors += [(k, 2.0 * min(-lap[k]["edge_m"][0], lap[k]["edge_m"][1])) for k in range(k0 + 1, k1)]
        was = widths[k0 + 1:k1]
        for k in range(k0 + 1, k1):
            widths[k] = round(min(w_ + 2.0 * rate_p * abs(st_p[k] - st_p[j]) for j, w_ in anchors), 3)
        pad_rep.append({"file": rel, "id": rec_p.get("id"), "cuts": [k0, k1],
                        "width_m": [round(min(widths[k0 + 1:k1]), 2), round(max(widths[k0 + 1:k1]), 2)],
                        "was_m": [round(min(was), 2), round(max(was), 2)]})
        print(f"[lm_intake] pad {rec_p.get('id')} ({rel}): the lane between v{k0} and v{k1} on its measured platform, "
              f"{pad_rep[-1]['width_m'][0]}..{pad_rep[-1]['width_m'][1]} m (the ribbon's {pad_rep[-1]['was_m'][0]}.."
              f"{pad_rep[-1]['was_m'][1]} m)")
    dy = [p[1] - a for p, a in zip(pts, y0)]
    # THE MEASURED CORNER ARCS (lm_intake.corner_arcs true; ledger 0078 round 6, the Lariat). The source's
    # hairpin_fit.mesh_fit corners (C12 / C13: junction nodes holding most of a 76-79 deg turn, measured on the aerial at
    # R 14.9 / 16.08 m) are fitted by build_mesh on the line it sweeps; the v021 assembler does not run build_mesh, so the
    # same fit (scripts/geometry/corner_arcs.fit_corners, the same declaration) is made here on the line it is handed.
    arcs_rep = None
    if li.get("corner_arcs"):
        from scripts.geometry import corner_arcs
        if isinstance(li["corner_arcs"], str):
            # round 9: the port's own measured switchbacks (tools/switchback_measure.py: the graded platform's centre arc
            # from the 1 m DEM), the ones both of whose edges the DEM bounds and fits within SWITCHBACK_RMS_M
            swb = json.loads((proj / li["corner_arcs"]).read_text(encoding="utf-8"))
            decl = [{"id": c["id"], "st_m": c["st_m"], "radius_m": c["radius_m"]} for c in swb["corners"]
                    if c.get("measured") and c.get("rms_outside_m", 9) <= SWITCHBACK_RMS_M
                    and c.get("rms_inside_m", 9) <= SWITCHBACK_RMS_M]
        else:
            hfit = scfg.get("hairpin_fit") or {}
            mf = set(hfit.get("mesh_fit") or [])
            decl = [c for c in (hfit.get("corners") or []) if c.get("id") in mf and c.get("radius_m")]
        if not decl:
            raise SystemExit("[lm_intake] lm_intake.corner_arcs: the source declares no hairpin_fit.mesh_fit corner with a radius")
        new_line, arep = corner_arcs.fit_corners([tuple(p) for p in pts], decl)

        def _span_fails(r):
            # build_mesh fits on its already-rounded line; here the arms still carry the raw line's facets, which the
            # assembler's own smoothing takes out: a step-gate reading OUTSIDE the fitted span is reported, not fatal
            a_, b_ = (r.get("span_v") or [0, -1])[:2]
            return [f for f in ((r.get("gate") or {}).get("fails") or []) if a_ <= f.get("v", -1) <= b_]
        for r in arep:
            if r["status"] == "FAIL" and not _span_fails(r) and r.get("span_v"):
                r["status"] = "PASS (arm facets outside the span: " + ", ".join(
                    f"v{f['v']} {f.get('adjacent_diff_deg', f.get('step_deg'))} deg" for f in r["gate"]["fails"]) + ")"
        bad = [r["id"] for r in arep if not str(r["status"]).startswith("PASS")]
        if bad or len(arep) != len(decl):
            raise SystemExit(f"[lm_intake] corner arcs {[c['id'] for c in decl]}: not fitted or failing the step gate: "
                             f"{[(r['id'], r['status'], r.get('why'), (r.get('gate') or {}).get('fails', [])[:3]) for r in arep if r['id'] in bad]}")
        old_pts = pts
        pts = [tuple(p) for p in new_line]
        arcs_rep = [{k: r[k] for k in ("id", "status", "radius_m", "turn_deg", "max_move_m") if k in r} for r in arep]
        # THE ARCS' HEIGHTS FROM THE GROUND (ledger 0078 round 7, Kevin: "I just want real"). fit_corners keeps heights by
        # index, so a corner cut shorter carries the node's drop over a shorter road (the Lariat: 15.48 % over 10 m at
        # C12 / C13 against 11.82 % without the arcs). Every moved point reads 3DEP where it now stands (the source's
        # corridor.elev.json: native 3DEP every 6 m along x 5 m across, +-60 m; inverse-distance over the 4 nearest),
        # then the profile is re-smoothed on the new stations by road_profile's own windows, cap off, and taken within
        # REACH of the moved points (the windows' reach); everywhere else the profile stays as read above.
        cp_ = sdata / "corridor.elev.json"
        rp_ = (ej.get("road_profile") or {}) if li.get("profile") == "uncapped" else {}
        if cp_.exists() and rp_.get("tool") == "scripts/elevation/road_profile.py":
            from scripts.elevation import road_profile as rprof
            from scripts.geometry.projection import in_local_order as _ilo
            corr = json.loads(cp_.read_text(encoding="utf-8"))
            lat0c = corr["stations_lonlat"][0][1]
            mlon_c, mlat_c = 111_320.0 * math.cos(math.radians(lat0c)), 110_540.0     # heightfield's own corridor maths
            lon0_, lat0_ = float(local["origin"]["lon"]), float(local["origin"]["lat"])
            phi_ = math.radians(lat0_)
            mlon_l = 111412.84 * math.cos(phi_) - 93.5 * math.cos(3 * phi_) + 0.118 * math.cos(5 * phi_)
            mlat_l = 111132.954 - 559.822 * math.cos(2 * phi_) + 1.175 * math.cos(4 * phi_)
            SP = corr["stations_lonlat"]
            buck = {}
            for i2, (slon, slat) in enumerate(SP):
                a2, b2 = SP[max(i2 - 1, 0)], SP[min(i2 + 1, len(SP) - 1)]
                tx_, tz_ = (b2[0] - a2[0]) * mlon_c, (b2[1] - a2[1]) * mlat_c
                L_ = math.hypot(tx_, tz_) or 1.0
                nx_, nz_ = -tz_ / L_, tx_ / L_
                for off, zz in zip(corr["offsets"], corr["z"][i2]):
                    if zz is None:
                        continue
                    qlon, qlat = slon + nx_ * off / mlon_c, slat + nz_ * off / mlat_c
                    qx, qz = (qlon - lon0_) * mlon_l, (qlat - lat0_) * mlat_l
                    buck.setdefault((int(qx // 10), int(qz // 10)), []).append((qx, qz, float(zz)))

            def g3dep(x, z):
                near = []
                for gx in range(int(x // 10) - 1, int(x // 10) + 2):
                    for gz in range(int(z // 10) - 1, int(z // 10) + 2):
                        near += buck.get((gx, gz), ())
                near.sort(key=lambda q: (q[0] - x) ** 2 + (q[1] - z) ** 2)
                near = near[:4]
                if not near:
                    raise SystemExit(f"[lm_intake] corner arcs: no corridor 3DEP near ({x:.1f}, {z:.1f})")
                w = [1.0 / max(1e-6, (q[0] - x) ** 2 + (q[1] - z) ** 2) for q in near]
                return sum(wi * q[2] for wi, q in zip(w, near)) / sum(w)
            moved_i = [i for i, (a, b) in enumerate(zip(old_pts, pts)) if math.hypot(a[0] - b[0], a[2] - b[2]) > 0.01]
            base = list(_ilo(local, ej.get("z_held_m") or ej["z_raw_m"]))
            for i in moved_i:
                base[i] = g3dep(pts[i][0], pts[i][2])
            st_n = [0.0]
            for a, b in zip(pts, pts[1:]):
                st_n.append(st_n[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
            z_s = rprof.snap_to_ground_stations(base, st_n, grade_cap_pct=1e9,
                                                median_m=float(rp_.get("median_window_m", rprof.MEDIAN_WINDOW_M)),
                                                mean_m=float(rp_.get("mean_window_m", rprof.MEAN_WINDOW_M)), closed=closed)
            elev0_ = float(local["origin"]["elev_m"])
            reach = float(rp_.get("median_window_m", 33.0)) + float(rp_.get("mean_window_m", 9.0))
            mset = [st_n[i] for i in moved_i]
            took = 0
            new_pts = []
            for i, p in enumerate(pts):
                if mset and min(abs(st_n[i] - s_) for s_ in mset) <= reach:
                    new_pts.append((p[0], z_s[i] - elev0_, p[2])); took += 1
                else:
                    new_pts.append(p)
            if closed:
                new_pts[-1] = new_pts[0]
            pts = new_pts
            for r_ in arcs_rep:
                r_["heights"] = "3DEP along the arc (corridor.elev.json), re-smoothed, cap off"
            print(f"[lm_intake] corner arcs: {len(moved_i)} moved points read 3DEP where they stand; {took} heights re-smoothed "
                  f"within {reach:.0f} m (road_profile's windows, cap off); steepest now "
                  f"{100.0 * _max_grade(pts, 10.0):.2f} % over 10 m")
        print(f"[lm_intake] corner arcs: " + ", ".join(f"{r['id']} R {r.get('radius_m')} m, moved <= {r.get('max_move_m')} m"
                                                      for r in arcs_rep))
    # A LANE EDGE ON A MEASURED WALL (lm_intake.edge_on_wall {"side": "right"|"left", "file": <tools/lidar_wall.py output
    # inside the source track>}; ledger 0078 round 5). Where a wall bounds the pavement, its face IS the lane edge. The
    # survey gives the face's offset from the line's own edge per station (Pikes Peak: 0.1 to 2.9 m INSIDE it, the OSM
    # line plus 15 m running past the oval's outer wall). That side's edge is moved onto the face, the other edge kept:
    # the centre shifts by half the offset and the width changes by all of it. The offsets are smoothed over SMOOTH_WALL
    # stations (a median, then a mean) first; a station with no reading takes its neighbours'.
    eow = li.get("edge_on_wall")
    wall_rep = None
    if eow:
        rel_w = eow["file"]
        if rel_w.startswith(("/", "\\")) or ".." in Path(rel_w).parts:
            raise SystemExit(f"[lm_intake] lm_intake.edge_on_wall.file {rel_w!r} must be a plain path inside the source track")
        wj = json.loads((src / rel_w).read_text(encoding="utf-8"))
        side_w = eow.get("side", wj.get("side"))
        if side_w != wj.get("side"):
            raise SystemExit(f"[lm_intake] edge_on_wall side {side_w!r} but {rel_w} surveyed {wj.get('side')!r}")
        ws_ = [float(r["s"]) for r in wj["stations"]]
        wf = [None if not r.get("wall") else r["wall"]["face_past_edge_m"] for r in wj["stations"]]
        n_r = len(wf)
        known = [i for i, v in enumerate(wf) if v is not None]
        if not known:
            raise SystemExit(f"[lm_intake] {rel_w}: no wall reading at any station")
        filled = []
        for i in range(n_r):                                 # a gap takes the nearest reading (cyclic)
            if wf[i] is not None:
                filled.append(wf[i]); continue
            j = min(known, key=lambda k: min(abs(k - i), n_r - abs(k - i)))
            filled.append(wf[j])
        K = 2                                                 # SMOOTH_WALL = 5 stations (15 m)
        med = [sorted(filled[(i + d) % n_r] for d in range(-K, K + 1))[K] for i in range(n_r)]
        sm = [sum(med[(i + d) % n_r] for d in range(-K, K + 1)) / (2 * K + 1) for i in range(n_r)]
        st_e = [0.0]
        for a, b in zip(pts, pts[1:]):
            st_e.append(st_e[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        import bisect
        sgn = -1.0 if side_w == "right" else 1.0
        new_pts, new_w, moved = [], [], []
        for i, (p, w) in enumerate(zip(pts, widths)):
            s_i = st_e[i]
            k = min(max(bisect.bisect_right(ws_, s_i), 1), n_r - 1)
            t = (s_i - ws_[k - 1]) / max(1e-9, ws_[k] - ws_[k - 1])
            f = sm[k - 1] + (sm[k] - sm[k - 1]) * min(1.0, max(0.0, t))
            a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            lx, lz = -tz / L, tx / L                          # left normal
            new_pts.append((p[0] + sgn * lx * f / 2.0, p[1], p[2] + sgn * lz * f / 2.0))
            new_w.append(round(w + f, 3))
            moved.append(f)
        if closed:
            new_pts[-1], new_w[-1] = new_pts[0], new_w[0]
        pts, widths = new_pts, new_w
        wall_rep = {"side": side_w, "file": rel_w, "face_offset_m": {"min": round(min(moved), 2),
                    "median": round(sorted(moved)[len(moved) // 2], 2), "max": round(max(moved), 2)},
                    "width_m": [round(min(widths), 2), round(max(widths), 2)]}
        print(f"[lm_intake] {side_w} lane edge onto the measured wall ({rel_w}): edge moved {wall_rep['face_offset_m']} m, "
              f"widths now {wall_rep['width_m'][0]}..{wall_rep['width_m'][1]} m")
    # A LANE EDGE ON THE MEASURED BANK (lm_intake.edge_on_bank {"side": "left"|"right", "file": <a surface file inside the
    # source track>, "heights": "plane"}; ledger 0085, Pikes Peak). Where a banked surface runs on past the traced lane,
    # its real edge is where the bank's plane ends: the 2018 lidar's knee (tracks/pikes-peak/source/lidar/infield/
    # oval_surface.py: per 3 m station of the built line, the knee's lateral offset from that line's centre, smoothed, and
    # the lane plane z = a + b * lateral). That side's edge is moved onto it, the other edge kept: the centre shifts by half
    # the move and the width changes by all of it (as edge_on_wall). heights "plane": the moved centre takes the plane's
    # height where it now stands (the lidar ground; the assembler lifts the deck as everywhere), so the deck is the
    # measured plane, not the old centre's height carried sideways down a 17 % bank. Each vertex reads the two stations
    # either side of its foot on the station polyline, by position. The banking (lm_intake.crossfall, keyed by position)
    # moves with the line: each of its points takes the move of the vertex nearest it. Absent = no move.
    eob = li.get("edge_on_bank")
    bank_rep = None
    bank_move = None                                          # (pre-move points, per-vertex (dx, dz)) for the crossfall
    if eob:
        rel_b = eob["file"]
        if rel_b.startswith(("/", "\\")) or ".." in Path(rel_b).parts:
            raise SystemExit(f"[lm_intake] lm_intake.edge_on_bank.file {rel_b!r} must be a plain path inside the source track")
        side_b = eob.get("side", "left")
        if side_b not in ("left", "right"):
            raise SystemExit(f"[lm_intake] edge_on_bank side {side_b!r}: left or right")
        heights_b = eob.get("heights")
        if heights_b not in (None, "plane"):
            raise SystemExit(f"[lm_intake] edge_on_bank heights {heights_b!r}: \"plane\" or absent")
        bj = json.loads((src / rel_b).read_text(encoding="utf-8"))
        S_b = bj["stations"]
        if len(S_b) < 3:
            raise SystemExit(f"[lm_intake] {rel_b}: {len(S_b)} stations")
        sgn_b = 1.0 if side_b == "left" else -1.0
        n_s = len(S_b)

        def _station_at(px, pz):
            """The station values at the foot of (px, pz) on the closed station polyline, interpolated along it."""
            best = None
            for k in range(n_s):
                a_, b_ = S_b[k], S_b[(k + 1) % n_s]
                ax, az = a_["xz"]
                dx_, dz_ = b_["xz"][0] - ax, b_["xz"][1] - az
                L2 = dx_ * dx_ + dz_ * dz_
                t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx_ + (pz - az) * dz_) / L2))
                d2 = (px - ax - t * dx_) ** 2 + (pz - az - t * dz_) ** 2
                if best is None or d2 < best[0]:
                    best = (d2, k, t)
            d2, k, t = best
            a_, b_ = S_b[k], S_b[(k + 1) % n_s]

            def lerp(u, v):
                return u + (v - u) * t
            ox, oz = lerp(a_["xz"][0], b_["xz"][0]), lerp(a_["xz"][1], b_["xz"][1])
            lx, lz = lerp(a_["left"][0], b_["left"][0]), lerp(a_["left"][1], b_["left"][1])
            ln = math.hypot(lx, lz) or 1.0
            return {"o": (ox, oz), "l": (lx / ln, lz / ln), "edge": lerp(a_["bank_edge_m"], b_["bank_edge_m"]),
                    "a": lerp(a_["plane"]["a"], b_["plane"]["a"]), "b": lerp(a_["plane"]["b"], b_["plane"]["b"]),
                    "apron_w": lerp(a_["apron"]["width_m"], b_["apron"]["width_m"]) if "apron" in a_ else None,
                    "apron_s": lerp(a_["apron"]["slope_pct"], b_["apron"]["slope_pct"]) / 100.0 if "apron" in a_ else None,
                    "apron_lip": (lerp(a_["apron"]["lip_step_m"], b_["apron"]["lip_step_m"])
                                  if "lip_step_m" in a_.get("apron", {}) else None),
                    "off_m": math.sqrt(d2)}
        pre_b = list(pts)
        want_apron = bool(eob.get("apron"))
        new_pts, new_w, moves, offs, dys, ap_w, ap_s, ap_l = [], [], [], [], [], [], [], []
        for i, (p, w) in enumerate(zip(pts, widths)):
            sa = _station_at(p[0], p[2])
            c = (p[0] - sa["o"][0]) * sa["l"][0] + (p[2] - sa["o"][1]) * sa["l"][1]   # lateral in the station frame
            # the edge's outward move: left, the bank edge (+edge) minus the lane's left edge (c + w/2); right, mirrored
            f = (sa["edge"] - (c + w / 2.0)) if side_b == "left" else (sa["edge"] - (w / 2.0 - c))
            a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(tx, tz) or 1.0
            lx, lz = -tz / L, tx / L                                                 # the line's own left normal
            nx_, nz_ = p[0] + sgn_b * lx * f / 2.0, p[2] + sgn_b * lz * f / 2.0
            y_ = p[1]
            if heights_b == "plane":
                c_new = (nx_ - sa["o"][0]) * sa["l"][0] + (nz_ - sa["o"][1]) * sa["l"][1]
                y_ = sa["a"] + sa["b"] * c_new
            new_pts.append((nx_, y_, nz_))
            new_w.append(round(w + f, 3))
            moves.append(f)
            offs.append(sa["off_m"])
            dys.append(y_ - p[1])
            if want_apron:
                if sa["apron_w"] is None:
                    raise SystemExit(f"[lm_intake] edge_on_bank.apron: {rel_b} has no apron per station")
                ap_w.append(round(sa["apron_w"], 3))
                ap_s.append(round(sa["apron_s"], 5))
                ap_l.append(None if sa["apron_lip"] is None else round(sa["apron_lip"], 3))
        if closed:
            new_pts[-1], new_w[-1] = new_pts[0], new_w[0]
        if max(offs) > 6.0:
            raise SystemExit(f"[lm_intake] edge_on_bank {rel_b}: a vertex {max(offs):.2f} m from the stations' line — "
                             f"measured on another line")
        bank_move = (pre_b, [(q[0] - p[0], q[2] - p[2]) for p, q in zip(pre_b, new_pts)])
        pts, widths = new_pts, new_w
        srt = sorted(moves)
        bank_rep = {"side": side_b, "file": rel_b, "heights": heights_b,
                    "edge_moved_m": {"min": round(srt[0], 2), "median": round(srt[len(srt) // 2], 2), "max": round(srt[-1], 2)},
                    "width_m": [round(min(widths), 2), round(max(widths), 2)],
                    "height_change_m": {"min": round(min(dys), 3), "max": round(max(dys), 3)},
                    "line_to_stations_m_max": round(max(offs), 2)}
        # THE APRON (edge_on_bank.apron true): past the bank's edge the measured apron to the inside edge, its width and
        # fall per vertex for the assembler's edge strip (route.edge_apron_file, build_loop_blend.edge_apron)
        data_dir_b = proj / "data"
        data_dir_b.mkdir(parents=True, exist_ok=True)
        if want_apron:
            (data_dir_b / "apron.lm.json").write_text(json.dumps({
                "side": side_b, "points_xz": [[round(q[0], 3), round(q[2], 3)] for q in pts], "width_m": ap_w, "slope": ap_s,
                **({"lip": ap_l} if ap_l and all(v is not None for v in ap_l) else {}),
                "source": f"tracks/{src_track}/{rel_b}",
                "_doc": "lm_intake.edge_on_bank.apron (ledger 0085): the measured apron past the bank's edge, per line vertex; "
                        "slope = rise per m away from the lane"}), encoding="utf-8")
            bank_rep["apron"] = {"width_m": [round(min(ap_w), 2), round(max(ap_w), 2)],
                                 "slope_pct": [round(100 * min(ap_s), 2), round(100 * max(ap_s), 2)]}
        else:
            (data_dir_b / "apron.lm.json").unlink(missing_ok=True)
        print(f"[lm_intake] {side_b} lane edge onto the measured bank ({rel_b}): edge moved {bank_rep['edge_moved_m']} m, "
              f"widths now {bank_rep['width_m'][0]}..{bank_rep['width_m'][1]} m"
              + (f", heights on the measured plane ({bank_rep['height_change_m']['min']:+.3f}.."
                 f"{bank_rep['height_change_m']['max']:+.3f} m)" if heights_b else ""))
    # FINER ROWS (lm_intake.resample_m; absent = the source's own spacing; ledger 0078 round 5). The assembler sweeps one
    # ribbon row per line point, so the surface is planar between rows and every change of grade a wheel path meets lands
    # on a row boundary. On a tight corner on a steep grade (Milford's s 990 left-hander, R 15 m on -13.8 %, ledger 0069)
    # the inside paths' grade turns several % per 3 m row and drive_test reads the turns as severe steps; at half the spacing
    # each turn is half. The line is re-cut linearly at the declared spacing (plan, height and width: no new shape, the
    # same polyline), so the declaring track also doubles route.smooth_sigma_pts / smooth_sigma_y_pts to keep the
    # assembler's smoothing the same in metres.
    rs = li.get("resample_m")
    resample_rep = None
    if rs:
        step_r = float(rs)
        st_r = [0.0]
        for a, b in zip(pts, pts[1:]):
            st_r.append(st_r[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        total = st_r[-1]
        n_new = max(5, int(round(total / step_r)))
        new_pts, new_w, j = [], [], 0
        for k in range(n_new + (1 if closed else 1)):
            s_k = min(total, k * total / n_new)
            while j < len(st_r) - 2 and st_r[j + 1] < s_k:
                j += 1
            seg = (st_r[j + 1] - st_r[j]) or 1e-9
            t = (s_k - st_r[j]) / seg
            a, b = pts[j], pts[j + 1]
            new_pts.append(tuple(a[c] + (b[c] - a[c]) * t for c in range(3)))
            new_w.append(round(widths[j] + (widths[j + 1] - widths[j]) * t, 3))
        if closed:
            new_pts[-1], new_w[-1] = new_pts[0], new_w[0]
        resample_rep = {"spacing_m": step_r, "points_before": len(pts), "points_after": len(new_pts)}
        pts, widths = new_pts, new_w                  # dy (the heights the intake moved) stays the source points'
        print(f"[lm_intake] resampled every {step_r} m: {resample_rep['points_before']} -> {resample_rep['points_after']} points")
    data = proj / "data"
    data.mkdir(parents=True, exist_ok=True)
    out = {"frame": "ENU local meters (X=east, Y=up, Z=north)", "origin": local["origin"],
           "true_north_rotation_deg": local.get("true_north_rotation_deg", 0.0),
           "point_count": len(pts), "points_xyz_m": [[round(c, 4) for c in p] for p in pts], "widths_m": widths,
           "source": f"tracks/{src_track}/data/centerline.local.json (tools/lm_engine_intake.py, ledger 0078)"}
    (data / "centerline.local.json").write_text(json.dumps(out), encoding="utf-8")
    # the assembler smooths from its first-run snapshot: a stale one would smooth the OLD line
    (data / "centerline.raw.local.json").unlink(missing_ok=True)
    # THE LINE AS GEOJSON (2026-11-03, the PC's Sand Creek rehearsal: the track folder read data/centerline.geojson's
    # features[0].properties.length_m from a file only the Mac's workshop held). The port's line IS the source's line in
    # lon / lat (only its heights change, above), so the source's file is the port's; its OSM ways cache (the track
    # folder's CM preview, optional) rides along when the source has one. Nothing a later step reads may come from an old
    # workshop: tests/tools/test_lm_engine_port.py runs this into an empty dir and checks every such file (WORKSHOP_INPUTS).
    shutil.copyfile(sdata / "centerline.geojson", data / "centerline.geojson")
    if (sdata / "osm.ways.json").exists():
        shutil.copyfile(sdata / "osm.ways.json", data / "osm.ways.json")
    else:
        (data / "osm.ways.json").unlink(missing_ok=True)
    if not hf_own:
        for f in ("heightfield.npy", "heightfield.meta.json"):
            shutil.copyfile(sdata / f, data / f)
    else:
        print("[lm_intake] heightfield: the project's own (the port track's fetched 3DEP grid; the source commits none)")
    # FINER FACETS, SAME SAMPLES (lm_intake.grid_upsample, default 1 = the source grid as is). The assembler halves the
    # grid once (40 -> 20 m, build_loop_blend.py upsample_grid(.., 2)); engine-july's prep then splits terrain edges near the
    # road at most 4 times. On a 20 m grid that leaves edges up to ~10 m under a narrow road, and where the deck sags
    # (a levelled deck's raised-cosine ramp back to the road: Sand Creek s 2,524, the slip after E 56th) the straight grass
    # chord between two pinned vertices stands over the curved deck: 64 "ground on top" samples. Pre-dividing the 3DEP grid
    # here (bilinear, as the assembler's own upsample: no new heights, the same surface in finer facets) gives the prep
    # vertices to pin. Lake Murray never runs this tool.
    up = int(li.get("grid_upsample", 1))
    if up > 1:
        hgrid = _read_npy(data / "heightfield.npy")
        meta = json.loads((data / "heightfield.meta.json").read_text(encoding="utf-8"))
        if "lm_intake_upsample" in meta:
            raise SystemExit("[lm_intake] data/heightfield.npy is already an upsampled grid: re-sync the source grid first")
        hgrid, meta2 = _upsample(hgrid, meta, up)
        _write_npy(data / "heightfield.npy", hgrid)
        meta2["lm_intake_upsample"] = {"factor": up, "source_spacing_m": meta["spacing_m"],
                                       "_doc": "bilinear from the source 3DEP grid (tools/lm_engine_intake.py)"}
        (data / "heightfield.meta.json").write_text(json.dumps(meta2), encoding="utf-8")
    want_conn = li.get("connectors", False) if connectors is None else connectors
    conn = sdata / "connectors.local.json"
    # THE PORT'S OWN SIDE STREETS (lm_intake.connectors_file, a path inside the PORT project; ledger 0085, Pikes Peak's
    # infield roads off the measured pieces): the source track has none, so the port carries its own set (ship.json
    # sync_in). Taken instead of the source's; the same fresh-copy rules below. Absent = as before.
    cfile = li.get("connectors_file")
    if cfile:
        if str(cfile).startswith(("/", "\\")) or ".." in Path(str(cfile)).parts:
            raise SystemExit(f"[lm_intake] lm_intake.connectors_file {cfile!r} must be a plain path inside the project")
        conn = proj / str(cfile)
        if not conn.exists():
            raise SystemExit(f"[lm_intake] lm_intake.connectors_file {cfile}: not in the project (ship.json sync_in)")
        want_conn = True
        print(f"[lm_intake] connectors: the port's own ({cfile}, "
              f"{len(json.loads(conn.read_text(encoding='utf-8'))['connectors'])} pieces)")
    if want_conn and conn.exists():
        shutil.copyfile(conn, data / "connectors.local.json")
        (data / "mouths.json").unlink(missing_ok=True)       # tools/trim_connectors.py writes it for these connectors
        # ledger 0079 round B: trim / divide / route re-read their .pre-* snapshot when one exists, so a snapshot an earlier
        # run left would re-trim the OLD set: the fresh copy is the only source
        for suf in (".pre-trim", ".pre-divide", ".pre-route"):
            (data / ("connectors.local.json" + suf)).unlink(missing_ok=True)
        if li.get("connector_profiles"):
            apply_connector_profiles(proj, str(li["connector_profiles"]))
        if li.get("connector_widths"):
            # ledger 0079 round H (opt-in lm_intake.connector_widths {street: m}): a street's width measured off NAIP where
            # OSM's is short (the config's doc carries the cross-sections); every point of the named street
            cw = {str(k): float(v) for k, v in li["connector_widths"].items()}
            cj = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))
            seen = set()
            for c in cj["connectors"]:
                if c["name"] in cw:
                    c["widths_m"] = [cw[c["name"]]] * len(c["points_xyz_m"])
                    seen.add(c["name"])
            if set(cw) - seen:
                raise SystemExit(f"[lm_intake] lm_intake.connector_widths: no such connector(s) {sorted(set(cw) - seen)}")
            (data / "connectors.local.json").write_text(json.dumps(cj), encoding="utf-8")
            print(f"[lm_intake] connector widths measured: {cw}")
    else:
        # the lap alone: an EMPTY side-street set, so the assembler sweeps none and tools/weld_mouths_blend.py (the
        # mainline fold mend, ledger 0050) runs on the mainline alone — it reads both files
        (data / "connectors.local.json").write_text(json.dumps({"connectors": []}), encoding="utf-8")
        (data / "mouths.json").write_text(json.dumps({"mouths": []}), encoding="utf-8")
    # THE MEASURED CAMBER (lm_intake.crossfall true; ledger 0066's lidar crossfall). The source's data/crossfall.json is
    # keyed to stations of ITS finished line (build_mesh's); those stations mean nothing on the assembler's line, so each
    # banked station is written as a POSITION (the source's gate_centerline.json, engine frame = this frame) with its bank,
    # and the assembler keys it to its own smoothed line (build_loop_blend.crossfall_bank, route.crossfall_file).
    cf_rep = None
    cf_out = data / "crossfall.lm.json"
    if li.get("crossfall"):
        # true = the source's data/crossfall.json; a string = a path inside the source track (a survey's file, e.g.
        # source/lidar/camber-survey/crossfall.json on High Plains / Nevada Nights, keyed to the same finished line)
        rel_cf = li["crossfall"] if isinstance(li["crossfall"], str) else "data/crossfall.json"
        if rel_cf.startswith(("/", "\\")) or ".." in Path(rel_cf).parts:
            raise SystemExit(f"[lm_intake] lm_intake.crossfall {rel_cf!r} must be a plain path inside the source track")
        cfp, glp = src / rel_cf, sdata / "gate_centerline.json"
        if not cfp.exists() or not glp.exists():
            raise SystemExit("[lm_intake] lm_intake.crossfall: the source track has no data/crossfall.json + gate_centerline.json")
        cf = json.loads(cfp.read_text(encoding="utf-8"))
        if cf.get("status") != "measured":
            raise SystemExit(f"[lm_intake] {cfp}: status {cf.get('status')!r}, only a measured crossfall is taken")
        gl = json.loads(glp.read_text(encoding="utf-8"))["points_xyz_m"]
        gst = [0.0]
        for a, b in zip(gl, gl[1:]):
            gst.append(gst[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        cst, cbk = cf["station_m"], cf["bank_rad"]
        keep = set()
        for k, v in enumerate(cbk):
            if abs(v) > 1e-9:
                keep.update((k - 1, k, k + 1))                  # each banked run with a flat station either side
        import bisect
        pxz, pbk = [], []
        for k in sorted(i for i in keep if 0 <= i < len(cst)):
            s = cst[k]
            j = min(len(gst) - 1, max(1, bisect.bisect_left(gst, s)))
            t = (s - gst[j - 1]) / ((gst[j] - gst[j - 1]) or 1.0)
            pxz.append([round(gl[j - 1][0] + (gl[j][0] - gl[j - 1][0]) * t, 3),
                        round(gl[j - 1][2] + (gl[j][2] - gl[j - 1][2]) * t, 3)])
            pbk.append(cbk[k])
        if bank_move is not None:                     # lm_intake.edge_on_bank moved the line: its banking moves with it
            pre_b, mv_b = bank_move
            for q in pxz:
                j = min(range(len(pre_b)), key=lambda i_: (pre_b[i_][0] - q[0]) ** 2 + (pre_b[i_][2] - q[1]) ** 2)
                q[0], q[1] = round(q[0] + mv_b[j][0], 3), round(q[1] + mv_b[j][1], 3)
        cf_out.write_text(json.dumps({"points_xz": pxz, "bank_rad": pbk, "source": f"tracks/{src_track}/data/crossfall.json",
                                      "source_frame": cf.get("frame"), "source_status": cf.get("status"),
                                      "_doc": "+ = the left edge (of travel) higher; keyed by position (ledger 0078)"}),
                          encoding="utf-8")
        cf_rep = {"stations": len(pbk), "max_pct": round(100 * math.tan(max(abs(b) for b in pbk)), 2) if pbk else 0.0}
    else:
        cf_out.unlink(missing_ok=True)
    # THE BUILDINGS (Kevin 2026-11-03: "Lake Murray v4 had many more houses in it this time, don't lose those"): the
    # footprint plan the config's scenery.bespoke.blocks names (tools/plan_buildings.py's output, source/bespoke/...) comes
    # from the source track; tools/author_bespoke_blend.py stands it in place of the assembler's HOUSE / BUILDING boxes
    copied = []
    # every file the bespoke dressing names (blocks / cards / ... "file"), and every project-relative texture the config's
    # texture_overrides name (a track's own ground tile, e.g. High Plains' prairie): the source track's files, copied
    rels = []

    def _files(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "file" and isinstance(v, str):
                    rels.append(v)
                elif not k.startswith("_"):
                    _files(v)
        elif isinstance(node, list):
            for v in node:
                _files(v)
    _files(((cfg.get("scenery") or {}).get("bespoke") or {}))
    if (cfg.get("route") or {}).get("kerbs_file"):
        rels.append(cfg["route"]["kerbs_file"])           # the traced kerb runs (tools/aerial_edges.py, ledger 0078)
    for row in (cfg.get("texture_overrides") or {}).values():
        for v in (row or {}).values() if isinstance(row, dict) else ():
            if isinstance(v, str) and v.startswith("textures/"):
                rels.append(v)
    for rel in dict.fromkeys(rels):
        if rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
            raise SystemExit(f"[lm_intake] {rel!r} must be a plain path inside the track")
        sp = src / rel
        if not sp.exists():
            if (proj / rel).exists():                      # the port's own file (e.g. its kerb texture), synced in by ship.json
                continue
            raise SystemExit(f"[lm_intake] the config names {rel} but tracks/{src_track}/{rel} does not exist")
        (proj / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sp, proj / rel)
        copied.append(rel)
    # THE TREE MODELS (lm_intake.tree_models true; ledger 0079): the source track's TreeFX models (source/trees/*.bin,
    # personal-use, gitignored, present only on the machine that holds them) into the project's source/trees, where
    # tools/make_treefx.py resolves its species; none there = every species dropped, [TREES] skipped (L7). Absent = nothing
    if li.get("tree_models"):
        n_bin = 0
        for b in sorted((src / "source" / "trees").glob("*.bin")):
            (proj / "source" / "trees").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(b, proj / "source" / "trees" / b.name)
            n_bin += 1
        print(f"[lm_intake] tree models: {n_bin} TreeFX .bin from tracks/{src_track}/source/trees"
              f"{'' if n_bin else ' (none on this machine: make_treefx drops every species)'}")
    # THE LINE'S OWN RECORDS (lm_intake.carry_records [paths under the source's data/]; ledger 0078 round 6, the Lariat).
    # Gates that re-read the draft's records of the LINE (tools/drive1_gates.py: the one-way check, the paint-centreline /
    # hairpin gate; drive_test's replication against the raw 3DEP in centerline.elevation.json) find them in the workshop;
    # the port's line is the source's, so the source's records are the port's. lm_intake.roll_record "flat": a port that
    # tilts nothing writes its own roll-rate record (no crossfall: nothing rolls), not the source's.
    carried = []
    for rel in li.get("carry_records") or []:
        if rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
            raise SystemExit(f"[lm_intake] carry_records {rel!r} must be a plain path under the source's data/")
        if not (sdata / rel).exists():
            raise SystemExit(f"[lm_intake] carry_records: tracks/{src_track}/data/{rel} does not exist")
        (data / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sdata / rel, data / rel)
        carried.append(rel)
    # THE MEASURED ROAD THE GATES REPLICATE AGAINST (round 8): with lm_intake.road_seek the line stands on the road
    # road_seek found, so the carried raw record's heights become that road's (drive_test's replication reads z_raw_m;
    # against the mapped line's own DEM it would read the hillside the line was moved off). geojson order, by the
    # source's own permutation (projection.in_local_order).
    if li.get("road_seek") and (data / "centerline.elevation.json").exists():
        ejp = data / "centerline.elevation.json"
        ej2 = json.loads(ejp.read_text(encoding="utf-8"))
        st2 = json.loads((proj / li["road_seek"]).read_text(encoding="utf-8"))["stations"]
        zr2 = list(ej2["z_raw_m"])
        sidx = local.get("source_index") or list(range(len(zr2)))
        if len(sidx) == len(st2) == len(zr2):
            for i, s_ in enumerate(st2):
                zr2[sidx[i]] = float(s_["z_m"])
            ej2["z_raw_m"] = zr2
            ej2["_road_seek_doc"] = (f"z_raw_m: the road tools/road_seek.py found ({li['road_seek']}), not the mapped "
                                     "line's own DEM samples (ledger 0078 round 8)")
            ejp.write_text(json.dumps(ej2), encoding="utf-8")
            carried.append("centerline.elevation.json (z_raw_m: the road_seek road)")
    # THE SOURCE'S MEASUREMENTS (lm_intake.carry_source [paths under the source track's source/]; round 7): the lidar
    # pad outlines tools/lm_pads_blend.py builds the lap's junction pads from, copied to the same path in the project
    for rel in li.get("carry_source") or []:
        if rel.startswith(("/", "\\")) or ".." in Path(rel).parts or Path(rel).parts[0] != "source":
            raise SystemExit(f"[lm_intake] carry_source {rel!r} must be a plain path under the source track's source/")
        sp = AIROSO / "tracks" / src_track / rel
        if not sp.exists():
            raise SystemExit(f"[lm_intake] carry_source: tracks/{src_track}/{rel} does not exist")
        (proj / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sp, proj / rel)
        carried.append(rel)
    if li.get("roll_record") == "flat":
        if li.get("crossfall"):
            raise SystemExit("[lm_intake] roll_record flat on a port that takes a crossfall")
        (data / "crossfall_gate.json").write_text(json.dumps({
            "_doc": "tools/lm_engine_intake.py (ledger 0078): this port takes no crossfall, so nothing rolls",
            "status_of_file": "none: the port is flat across (lm_intake takes no crossfall)", "stations": 0,
            "halves": {"left": {"worst_change_pct": 0.0, "swings": 0}, "right": {"worst_change_pct": 0.0, "swings": 0}},
            "problems": [], "fail": False}, indent=1), encoding="utf-8")
        carried.append("crossfall_gate.json (written: flat)")
    # THE DECKS FOR THE PREP. engine-july's prep (build_kn5_loop.declare_bridge_spans) spares the ground under a bridge
    # from its conform only where data/bridges.cache.json (OSM bridge ways, Lake Murray's fetch) puts one on the line.
    # A track without that cache declares its decks in capture.bridges instead: each becomes one way along the line's
    # own points over its span (the prep matches within 14 m and pads 8 m), so the prep spares exactly the declared deck.
    bcache = data / "bridges.cache.json"
    if (sdata / "bridges.cache.json").exists():
        shutil.copyfile(sdata / "bridges.cache.json", bcache)
    elif bridges:
        st = [0.0]
        for a, b in zip(pts, pts[1:]):
            st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
        lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
        phi = math.radians(lat0)       # build_kn5_loop._mpd: the WGS84 series the prep projects the cache with
        m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
        m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
        ways = []
        for (c, ln), b in zip(bridges, (scfg.get("capture") or {}).get("bridges") or []):
            geom = [[round(lon0 + p[0] / m_lon, 8), round(lat0 + p[2] / m_lat, 8)]
                    for p, s in zip(pts, st) if c - ln / 2.0 <= s <= c + ln / 2.0]
            if len(geom) >= 2:
                ways.append({"hw": "declared", "name": b.get("name"), "geom": geom,
                             "_source": f"track.config.json capture.bridges (center_m {c}, len_m {ln}) on the draft line"})
        bcache.write_text(json.dumps(ways), encoding="utf-8")
    else:
        bcache.unlink(missing_ok=True)
    lap = sum(math.hypot(b[0] - a[0], b[2] - a[2]) for a, b in zip(pts, pts[1:]))
    rep = {"source_track": src_track, "points": len(pts), "lap_m": round(lap, 1), "closed": closed,
           "widths_m": [round(min(widths), 2), round(sum(widths) / len(widths), 2), round(max(widths), 2)],
           "bridges_levelled": bridges, "max_grade_pct": None if max_grade is None else max_grade * 100.0,
           "measured_max_grade_pct": round(100.0 * _max_grade(pts, 10.0), 2),
           "y_changed_points": sum(1 for d in dy if abs(d) > 1e-6),
           "y_change_max_m": round(max((abs(d) for d in dy), default=0.0), 3),
           "connectors": bool(want_conn and conn.exists()), "bespoke_files": copied, "crossfall": cf_rep, "profile": prof_rep,
           "width_taper": taper_rep, **({"pad_widths": pad_rep} if pad_rep else {}),
           **({"corner_flare_off": flare_rep} if flare_rep else {}), "resample": resample_rep, "edge_on_wall": wall_rep,
           **({"edge_on_bank": bank_rep} if bank_rep else {}), "corner_arcs": arcs_rep, "carried": carried,
           "grid_upsample": up,
           "md5": {"source_centerline": _md5(need[0]), "heightfield.npy": _md5(data / "heightfield.npy"),
                   "centerline.local.json": _md5(data / "centerline.local.json")}}
    (data / "lm_intake.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[lm_intake] {src_track}: {len(pts)} pts, lap {lap:.0f} m, widths {rep['widths_m']} m, "
          f"{len(bridges)} deck(s) levelled, grade cap {'none' if max_grade is None else f'{max_grade*100:.1f} %'}, steepest {rep['measured_max_grade_pct']} % over 10 m — {rep['y_changed_points']} heights moved "
          f"(max {rep['y_change_max_m']} m); connectors {'in' if rep['connectors'] else 'out'}")
    return rep


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    conn = None
    if "--connectors" in argv:
        argv.remove("--connectors"); conn = True
    if len(argv) != 1:
        print(__doc__); return 2
    intake(Path(argv[0]).resolve(), connectors=conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
