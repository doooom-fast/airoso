"""Kink calibration: drive_test's own kink metric, run on a reference mountain road someone else built.

Lookout Lariat V3-PLAN P5 (ledger 0048): "Before Drive 1 the kink metric runs on la_canyons and simtraxx
Pikes Peak (both on this machine); a ceiling re-set from those reference mountain roads becomes [std]." The
Lariat's kink ceiling was 5/km, copied from Lake Murray's own 4.97/km [invented]; this tool measures what the
same ruler reads on roads that drive well, so the ceiling can cite them.

The ruler is not re-implemented: the reference road is written as a gate project (``track.config.json`` +
``data/track.obj`` + ``data/gate_centerline.json``) in a scratch folder and ``scripts.geometry.drive_test.run``
drives it, exactly as it drives ours (1 m stations, ten wheel paths, kinks = slope change > KINK_PCT %-points
between consecutive 1 m steps on the six interior paths).

What is read (READ ONLY; nothing is written beside the reference track):
  * the layout's ``models_<layout>.ini`` (its ``[MODEL_*]`` kn5 files; dynamic objects are not road);
  * every ``surfaces.ini`` under the track: the physics KEYs;
  * the layout's AI line (``<layout>/ai/fast_lane.ai`` v7, the documented format of fleet/reference/RESEARCH.md
    B6; ``--ai`` names another, e.g. a disabled ``_fast_lane.ai``) — positions and the sideLeft / sideRight
    extras. It is read, never written, never generated (docs/HANDOFF.md's ban is on AI lines from GPS);
  * from each kn5, through ``scripts.modkit.extract_kn5.parse(keep=...)``: only the PHYSICS road meshes, the
    AC rule (a mesh named <digits><KEY>..., KEY from surfaces.ini, inspect_kn5.classify_surface) with a KEY
    matching ``--road-rx`` (default ``^ROAD``). Visible or invisible, as AC's physics reads them.

What the gate project holds:
  * ``data/track.obj``: those meshes, renamed ``1ROAD_<original name>`` (drive_test keys pavement on 1ROAD),
    in the kn5's own frame (AC's; no mirror — the AI line is in the same frame), culled to triangles with a
    vertex within ``CULL_M`` of the AI line (the reference maps are 40-90 km of road; drive_test culls to
    120 m itself, this only keeps the OBJ small);
  * ``data/gate_centerline.json``: the lane centre, NOT the racing line. A racing line cuts every apex, so it
    is moved to the middle of the valid road at each point: centre = p + s * n * (sideLeft - sideRight) / 2,
    width = sideLeft + sideRight, where n is drive_test's own normal and the sign s (AC's left in that frame)
    is decided on the built road: the s for which both declared edges, 0.4 m inside, lie on the road more
    often. The offset and width are averaged over +-SMOOTH_PTS points (~15 m at 1.5 m spacing) so the lane
    does not wobble laterally with the recorded sides (a lateral wobble across a cambered road would itself
    read as vertical kinks). Points with sideLeft + sideRight < MIN_WIDTH_M (the recorder's zero-width first
    point) are dropped.

    python tools/calibrate_kinks.py --track "D:/.../tracks/la_canyons" --layout mt_wilson_hillclimb \\
        --work <scratch dir> --out fleet/reference/raw/kinks_la_canyons_mt_wilson_hillclimb.json
    python tools/calibrate_kinks.py --track "<...>/simtraxx_pikes_peak_0.81" --layout pp100ahc \\
        --ai "<...>/pp100ahc/ai/_fast_lane.ai" --work <scratch dir> --out <json>

Writes ``--out`` (the measured row) and the scratch gate project under ``--work``; prints the drive_test
report. Exit 0 (a measurement, not a gate).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.geometry import drive_test  # noqa: E402
from scripts.modkit.extract_kn5 import _xform, parse  # noqa: E402
from scripts.modkit.inspect_kn5 import DEFAULT_SURFACE_KEYS, classify_surface  # noqa: E402
from scripts.modkit.inspect_track import parse_ini  # noqa: E402

CULL_M = 40.0            # keep road triangles with a vertex this close to the AI line (plan metres)
SMOOTH_PTS = 10          # lateral offset / width averaged over +-this many AI points
MIN_WIDTH_M = 2.0        # sideLeft + sideRight below this = no recorded road (dropped)
EDGE_IN_M = 0.4          # the side test probes this far inside each declared edge
SIGN_ASYM_M = 1.0        # only points whose sides differ by more than this decide the sign
AI_HEADER = "<4i"        # version, point count, lap time, sample count
AI_POINT = "<3ffi"       # x, y, z, cumulative length, id (20 B)
AI_EXTRA = "<18f"        # speed, gas, brake, obsoleteLatG, radius, sideLeft, sideRight, ... (72 B)


def read_ai(path: Path) -> list[tuple[float, float, float, float, float, float]]:
    """[(x, y, z, length_m, sideLeft, sideRight)] from a fast_lane.ai v7 (RESEARCH.md B6). A file without
    the extras block carries sides of 0 (every point then fails MIN_WIDTH_M: the caller says so)."""
    d = Path(path).read_bytes()
    ver, n, _lap, _samples = struct.unpack_from(AI_HEADER, d, 0)
    if ver != 7:
        raise SystemExit(f"{path}: fast_lane.ai version {ver}, this reads v7 only")
    o = 16
    pts = [struct.unpack_from(AI_POINT, d, o + i * 20) for i in range(n)]
    o += n * 20
    sides = [(0.0, 0.0)] * n
    if len(d) >= o + 4:
        ne = struct.unpack_from("<i", d, o)[0]
        o += 4
        if ne == n and len(d) >= o + ne * 72:
            sides = []
            for i in range(n):
                e = struct.unpack_from(AI_EXTRA, d, o + i * 72)
                sides.append((e[5], e[6]))
    return [(p[0], p[1], p[2], p[3], s[0], s[1]) for p, s in zip(pts, sides)]


def layout_kn5s(track: Path, layout: str) -> tuple[list[Path], list[str]]:
    """The [MODEL_*] kn5 files of models_<layout>.ini (models.ini, then <track>.kn5, when there is none);
    returns (existing paths, names listed but absent)."""
    ini = track / f"models_{layout}.ini"
    if not ini.exists():
        ini = track / "models.ini"
    if ini.exists():
        names = [kv["FILE"] for sect, kv in parse_ini(ini).items() if sect.startswith("MODEL") and kv.get("FILE")]
    else:
        names = [f"{track.name}.kn5"]
    have = [track / n for n in names if (track / n).exists()]
    missing = [n for n in names if not (track / n).exists()]
    return have, missing


def surface_keys(track: Path) -> list[str]:
    keys = set(DEFAULT_SURFACE_KEYS)
    for ini in sorted(track.glob("**/surfaces*.ini")):
        for sect, kv in parse_ini(ini).items():
            if sect.startswith("SURFACE") and kv.get("KEY"):
                keys.add(kv["KEY"].upper())
    return sorted(keys)


def _cells_near(pts, radius: float, cell: float) -> set:
    r = int(radius // cell) + 1
    out = set()
    for x, _y, z, *_ in pts:
        ci, cj = int(x // cell), int(z // cell)
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                out.add((ci + di, cj + dj))
    return out


def road_groups(kn5s: list[Path], keys: list[str], road_rx: str, ai) -> tuple[list[dict], dict]:
    """[{name, verts[(x,y,z)], tris[(a,b,c)]}] — every physics road mesh of the layout, in world space,
    triangles culled to the AI corridor."""
    rx = re.compile(road_rx, re.I)

    def is_road(name: str) -> bool:
        k = classify_surface(name, keys)
        return bool(k) and k != "PHYS?" and bool(rx.search(k))

    cell = 10.0
    near = _cells_near(ai, CULL_M, cell)
    groups, stats = [], {"kn5": [], "meshes": 0, "tris_read": 0, "tris_kept": 0}
    for kp in kn5s:
        parsed = parse(kp, keep=is_road, textures=False)
        n_here = 0
        for mesh in parsed["meshes"]:
            m = mesh["xf"]
            wv = [_xform(m, x, y, z) for (x, y, z, _u, _v) in mesh["verts"]]
            idx = mesh["idx"]
            tris = []
            for t in range(0, len(idx) - 2, 3):
                a, b, c = idx[t], idx[t + 1], idx[t + 2]
                stats["tris_read"] += 1
                if any((int(wv[k][0] // cell), int(wv[k][2] // cell)) in near for k in (a, b, c)):
                    tris.append((a, b, c))
            if tris:
                groups.append({"name": "1ROAD_" + re.sub(r"\s+", "_", mesh["name"]), "verts": wv, "tris": tris})
                stats["tris_kept"] += len(tris)
            n_here += 1
        stats["kn5"].append({"file": kp.name, "road_meshes": n_here})
        stats["meshes"] += n_here
    return groups, stats


def write_obj(path: Path, groups: list[dict]) -> None:
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("# kink calibration gate OBJ: reference physics road, kn5 frame (tools/calibrate_kinks.py)\n")
        base = 1
        for g in groups:
            used = sorted({k for t in g["tris"] for k in t})
            remap = {k: i for i, k in enumerate(used)}
            f.write(f"o {g['name']}\n")
            for k in used:
                x, y, z = g["verts"][k]
                f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            for a, b, c in g["tris"]:
                f.write(f"f {base + remap[a]} {base + remap[b]} {base + remap[c]}\n")
            base += len(used)


def _normals(pts):
    """drive_test's normal at each point: (-tz, tx) of the local tangent, unit length."""
    n = len(pts)
    out = []
    for i in range(n):
        a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1e-9
        out.append((-tz / L, tx / L))
    return out


def _smooth(vals: list[float], k: int) -> list[float]:
    n = len(vals)
    pre = [0.0]
    for v in vals:
        pre.append(pre[-1] + v)
    return [(pre[min(n, i + k + 1)] - pre[max(0, i - k)]) / (min(n, i + k + 1) - max(0, i - k)) for i in range(n)]


def lane_centre(ai, field) -> tuple[list[list[float]], list[float], dict]:
    """(centre points, widths, notes): the AI line moved to the middle of its recorded valid road."""
    kept = [p for p in ai if p[4] + p[5] >= MIN_WIDTH_M]
    if len(kept) < 10:
        raise SystemExit(f"the AI line has {len(kept)} points with recorded sides >= {MIN_WIDTH_M} m: no lane to "
                         f"centre on (a fast_lane.ai without the extras block?)")
    nrm = _normals(kept)
    votes = {1: 0, -1: 0}
    for i in range(0, len(kept), 5):
        x, y, z, _s, sl, sr = kept[i]
        if abs(sl - sr) < SIGN_ASYM_M:
            continue
        nx, nz = nrm[i]
        for s in (1, -1):
            lx, lz = x + s * nx * (sl - EDGE_IN_M), z + s * nz * (sl - EDGE_IN_M)
            rx, rz = x - s * nx * (sr - EDGE_IN_M), z - s * nz * (sr - EDGE_IN_M)
            hl, _ = field.top_at(lx, lz, y)
            hr, _ = field.top_at(rx, rz, y)
            votes[s] += (hl is not None) + (hr is not None)
    sign = 1 if votes[1] >= votes[-1] else -1
    off = _smooth([(p[4] - p[5]) / 2.0 for p in kept], SMOOTH_PTS)
    wid = _smooth([p[4] + p[5] for p in kept], SMOOTH_PTS)
    pts, on_road = [], 0
    for (x, y, z, *_), (nx, nz), o in zip(kept, nrm, off):
        cx, cz = x + sign * nx * o, z + sign * nz * o
        h, _ = field.top_at(cx, cz, y)
        on_road += h is not None
        pts.append([round(cx, 4), round(h if h is not None else y, 4), round(cz, 4)])
    notes = {"ai_points": len(ai), "points_used": len(kept), "sign": sign, "sign_votes": {"+1": votes[1], "-1": votes[-1]},
             "centre_on_road_frac": round(on_road / len(kept), 4),
             "width_m": {"p05": round(sorted(wid)[len(wid) // 20], 2), "median": round(sorted(wid)[len(wid) // 2], 2),
                         "p95": round(sorted(wid)[-(len(wid) // 20) - 1], 2)}}
    return pts, [round(w, 3) for w in wid], notes


def build_project(work: Path, slug: str, groups: list[dict], pts, widths) -> Path:
    (work / "data").mkdir(parents=True, exist_ok=True)
    for stale in ("drive_test.json", "centerline.local.json", "finished_centerline.json", "median_bands.json",
                  "barrier_bands.json", "flat_zones.json", "centerline.elevation.json", "environment.obj"):
        p = work / "data" / stale
        if p.exists():
            p.unlink()
    (work / "track.config.json").write_text(json.dumps(
        {"slug": slug, "loop": False, "mirror_x": False,
         "_doc": "kink calibration gate project (tools/calibrate_kinks.py): a reference road, not a k10 track"},
        indent=1), encoding="utf-8")
    (work / "data" / "gate_centerline.json").write_text(json.dumps(
        {"points_xyz_m": pts, "widths_m": widths, "frame": "kn5 (AC) frame, lane centre from the AI sides"}),
        encoding="utf-8")
    write_obj(work / "data" / "track.obj", groups)
    return work


def calibrate(track: Path, layout: str, work: Path, *, ai_path: Path | None = None, road_rx: str = r"^ROAD") -> dict:
    track = Path(track)
    ai_path = Path(ai_path) if ai_path else track / layout / "ai" / "fast_lane.ai"
    ai = read_ai(ai_path)
    kn5s, missing = layout_kn5s(track, layout)
    keys = surface_keys(track)
    groups, gstats = road_groups(kn5s, keys, road_rx, ai)
    if not groups:
        raise SystemExit(f"no physics road mesh (KEY ~ {road_rx!r}) within {CULL_M} m of the AI line in {kn5s}")
    field = drive_test.TriField()
    for g in groups:
        for t in g["tris"]:
            field.add(g["verts"], t, g["name"])
    pts, widths, notes = lane_centre(ai, field)
    slug = re.sub(r"[^a-z0-9_]+", "_", f"{track.name}_{layout}".lower())
    build_project(Path(work), slug, groups, pts, widths)
    rep = drive_test.run(Path(work))
    km = rep["lap_m"] / 1000.0
    return {
        "_doc": "drive_test's kink metric on a reference road (tools/calibrate_kinks.py; Lookout Lariat V3-PLAN P5, "
                "ledger 0048). A measurement, not a gate: kinks = slope change > KINK_PCT %-points between "
                "consecutive 1 m steps on drive_test's six interior wheel paths, per km of the lane centre.",
        "track": track.name, "layout": layout,
        "ai_file": str(ai_path.relative_to(track)) if ai_path.is_relative_to(track) else ai_path.name,
        "kn5": [k.name for k in kn5s], "kn5_listed_but_absent": missing,
        "road_rx": road_rx, "road": gstats, "lane": notes,
        "kink_pct": drive_test.KINK_PCT, "step_m": drive_test.STEP_M,
        "lap_m": rep["lap_m"],
        "kinks": round(rep["kinks_per_km"] * km),
        "kinks_per_km": rep["kinks_per_km"],
        "worst_kinks": rep["worst"]["kinks"],
        "context": {k: rep.get(k) for k in ("steps_per_km", "severe_steps", "severe_per_km", "soft_top_in_lane",
                                             "off_pavement_stations", "daylight_gaps")},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="drive_test's kink metric on a reference AC road (read only)")
    ap.add_argument("--track", type=Path, required=True, help="the reference track folder (read only)")
    ap.add_argument("--layout", required=True)
    ap.add_argument("--ai", type=Path, help="the AI line (default <track>/<layout>/ai/fast_lane.ai)")
    ap.add_argument("--road-rx", default=r"^ROAD", help="surfaces.ini KEYs that are the road (regex)")
    ap.add_argument("--work", type=Path, required=True, help="scratch folder for the gate project (outside airoso)")
    ap.add_argument("--out", type=Path, help="write the measured row here (JSON)")
    a = ap.parse_args(argv)
    work = a.work.resolve()
    if work == ROOT or ROOT in work.parents:
        raise SystemExit(f"--work {work} is inside airoso: the gate project (a multi-MB OBJ) belongs in scratch")
    if a.track.resolve() in (work, *work.parents):
        raise SystemExit("--work is inside the reference track: it is read only")
    row = calibrate(a.track, a.layout, work, ai_path=a.ai, road_rx=a.road_rx)
    print(f"KINK CALIBRATION {row['track']} / {row['layout']}: lap {row['lap_m'] / 1000:.2f} km, "
          f"{row['kinks']} kinks, {row['kinks_per_km']} /km (lane width median {row['lane']['width_m']['median']} m, "
          f"centre on road {row['lane']['centre_on_road_frac']:.1%})")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
        print(f"  -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
