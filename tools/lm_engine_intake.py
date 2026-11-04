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
project and applies the only elevation evidence airoso's mesh stage applies to the line before smoothing, Y only:
  - capture.bridges: each declared deck held level over the bare-earth dip (scripts.capture.evidence.level_bridge_decks,
    keyed to this draft line's stations, as build_mesh keys it);
  - road_profile.max_grade_pct (default 6 %, build_mesh's): the launch net (scripts.capture.evidence.cap_grade).
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
if str(AIROSO) not in sys.path:
    sys.path.insert(0, str(AIROSO))

from scripts.capture import evidence  # noqa: E402


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def intake(proj: Path, *, connectors: bool | None = None) -> dict:
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    li = cfg.get("lm_intake") or {}
    src_track = li.get("source_track")
    if not src_track or "/" in src_track or "\\" in src_track or src_track.startswith("."):
        raise SystemExit("[lm_intake] track.config.json lm_intake.source_track must name a folder under tracks/")
    src = AIROSO / "tracks" / src_track
    sdata = src / "data"
    need = [sdata / "centerline.local.json", sdata / "heightfield.npy", sdata / "heightfield.meta.json"]
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
    # Y-only evidence, as build_mesh applies it to this same draft line (bridges, then the grade net)
    y0 = [p[1] for p in pts]
    bridges = [(float(b["center_m"]), float(b["len_m"])) for b in ((scfg.get("capture") or {}).get("bridges") or [])]
    if bridges:
        pts = evidence.level_bridge_decks(pts, bridges)
    max_grade = float((scfg.get("road_profile") or {}).get("max_grade_pct", 6.0)) / 100.0
    pts = evidence.cap_grade(pts, max_grade=max_grade)
    if closed:
        pts[-1] = pts[0]
    dy = [p[1] - a for p, a in zip(pts, y0)]
    data = proj / "data"
    data.mkdir(parents=True, exist_ok=True)
    out = {"frame": "ENU local meters (X=east, Y=up, Z=north)", "origin": local["origin"],
           "true_north_rotation_deg": local.get("true_north_rotation_deg", 0.0),
           "point_count": len(pts), "points_xyz_m": [[round(c, 4) for c in p] for p in pts], "widths_m": widths,
           "source": f"tracks/{src_track}/data/centerline.local.json (tools/lm_engine_intake.py, ledger 0078)"}
    (data / "centerline.local.json").write_text(json.dumps(out), encoding="utf-8")
    # the assembler smooths from its first-run snapshot: a stale one would smooth the OLD line
    (data / "centerline.raw.local.json").unlink(missing_ok=True)
    for f in ("heightfield.npy", "heightfield.meta.json"):
        shutil.copyfile(sdata / f, data / f)
    want_conn = li.get("connectors", False) if connectors is None else connectors
    conn = sdata / "connectors.local.json"
    if want_conn and conn.exists():
        shutil.copyfile(conn, data / "connectors.local.json")
    else:
        (data / "connectors.local.json").unlink(missing_ok=True)
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
           "bridges_levelled": bridges, "max_grade_pct": max_grade * 100.0,
           "y_changed_points": sum(1 for d in dy if abs(d) > 1e-6),
           "y_change_max_m": round(max((abs(d) for d in dy), default=0.0), 3),
           "connectors": bool(want_conn and conn.exists()),
           "md5": {"source_centerline": _md5(need[0]), "heightfield.npy": _md5(need[1]),
                   "centerline.local.json": _md5(data / "centerline.local.json")}}
    (data / "lm_intake.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[lm_intake] {src_track}: {len(pts)} pts, lap {lap:.0f} m, widths {rep['widths_m']} m, "
          f"{len(bridges)} deck(s) levelled, grade net {max_grade*100:.1f} % — {rep['y_changed_points']} heights moved "
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
