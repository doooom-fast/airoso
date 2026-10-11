"""Extract a BUILT kn5 into ``data/track.obj`` so the OBJ gates can judge a Blender-first track.

The S8 hole that let 0013 ship: a Blender-first track (loop.blend → kn5) never writes a
``track.obj``, so ``drive_test`` and ``audit_mesh`` — the two gates that simulate the car — had
nothing to read and were silently skipped. This closes it from the artifact side, in the spirit of
L5: take the SHIPPED kn5 (not any intermediate), decode every mesh, and write the gate OBJ.

Frame: the kn5 is Z-MIRRORED relative to the engine local frame (engine x=E, y=up, z=N; verified
against dummies.json vs the installed kn5 on Lake Murray: kn5 z = −engine z, x/y equal). The
mirror inverts winding, so every face is emitted reversed — same discipline as L6's "reflection
inverts face winding" rule, applied in the opposite direction.

    python -m scripts.modkit.kn5_to_gate_obj <project-dir> [--kn5 <file>]... [--out <obj>]

Defaults: kn5 = <project>/build/<slug>.kn5 (falls back to newest build/*.kn5), out =
<project>/data/track.obj. Then run, from the pinned .engine:

    python -m scripts.geometry.drive_test  <project-dir>
    python -m scripts.geometry.audit_mesh  <project-dir>

MULTI-LAYOUT (ledger 0047): ``--kn5`` repeats. A race layout loads the road kn5 AND the
race-furniture kn5, so it is judged on ONE gate OBJ holding both (OBJ face indices are global —
the vertex offset carries across files):

    python -m scripts.modkit.kn5_to_gate_obj <project> --kn5 build/<slug>.kn5 \\
        --kn5 build/<slug>_race.kn5 --out <project>/data/track.race.obj

The race gate OBJ is named ``track.race.obj`` (a DOT) on purpose: the loop prep
(``build_kn5_loop.py`` step 1b) merges every ``data/track_*.obj`` into the scene, so a
``track_race.obj`` would be imported as geometry on the next ship run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extract_kn5 import _xform, parse


def kn5_to_obj(kn5_path: Path | list[Path], out_obj: Path, *, flip_z: bool = True) -> dict:
    """Decode one kn5, or a LIST of kn5s in load order, into one gate OBJ. With several files the
    vertex offset carries across them (OBJ face indices are global), so the OBJ is exactly the set
    AC loads for that layout; ``files`` in the returned stats records each file's share."""
    kn5_paths = [Path(p) for p in (kn5_path if isinstance(kn5_path, (list, tuple)) else [kn5_path])]
    if not kn5_paths:
        raise ValueError("kn5_to_obj: no kn5 given")
    stats = {"meshes": 0, "verts": 0, "tris": 0, "files": []}
    with open(out_obj, "w", encoding="ascii", newline="\n") as f:
        f.write(f"# gate OBJ extracted from {' + '.join(p.name for p in kn5_paths)} (kn5->engine frame"
                f"{', z mirrored, winding reversed' if flip_z else ''})\n")
        voff = 0
        for kp in kn5_paths:
            parsed = parse(kp)
            mats = parsed["materials"]
            fstat = {"file": kp.name, "meshes": 0, "verts": 0, "tris": 0, "vertex_offset": voff}
            for mesh in parsed["meshes"]:
                m = mesh["xf"]
                name = mesh["name"]
                mat = mats[mesh["matid"]]["name"] if mesh["matid"] < len(mats) else "m"
                f.write(f"o {name}\nusemtl {mat}\n")
                for (x, y, z, _u, _v) in mesh["verts"]:
                    wx, wy, wz = _xform(m, x, y, z)
                    if flip_z:
                        wz = -wz
                    f.write(f"v {wx:.4f} {wy:.4f} {wz:.4f}\n")
                idx = mesh["idx"]
                if flip_z:
                    for t in range(0, len(idx) - 2, 3):     # reversed winding restores up-facing normals
                        f.write(f"f {idx[t+2]+1+voff} {idx[t+1]+1+voff} {idx[t]+1+voff}\n")
                else:
                    for t in range(0, len(idx) - 2, 3):
                        f.write(f"f {idx[t]+1+voff} {idx[t+1]+1+voff} {idx[t+2]+1+voff}\n")
                voff += len(mesh["verts"])
                fstat["meshes"] += 1
                fstat["verts"] += len(mesh["verts"])
                fstat["tris"] += len(idx) // 3
            for k in ("meshes", "verts", "tris"):
                stats[k] += fstat[k]
            stats["files"].append(fstat)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract a built kn5 into the gate OBJ (data/track.obj).")
    ap.add_argument("project", type=Path)
    ap.add_argument("--kn5", type=Path, action="append",
                    help="kn5 to decode; repeat for a layout that loads several (road + race furniture)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-flip-z", action="store_true",
                    help="kn5 already in engine frame (rare; default assumes the standard mirror)")
    args = ap.parse_args()

    kn5s = list(args.kn5 or [])
    if not kn5s:
        slug = json.loads((args.project / "track.config.json").read_text(encoding="utf-8"))["slug"]
        cand = args.project / "build" / f"{slug}.kn5"
        if not cand.exists():
            builds = sorted((args.project / "build").glob("*.kn5"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
            if not builds:
                raise SystemExit(f"no kn5 found under {args.project}/build — build first")
            cand = builds[0]
        kn5s = [cand]
    for k in kn5s:
        if not k.exists():
            raise SystemExit(f"kn5 not found: {k}")
    out = args.out or (args.project / "data" / "track.obj")
    if out.name.startswith("track_") and out.suffix.lower() == ".obj":
        raise SystemExit(f"refusing to write {out.name}: the loop prep merges every data/track_*.obj into "
                         f"the scene (build_kn5_loop step 1b) — name a second gate OBJ track.<x>.obj")
    out.parent.mkdir(parents=True, exist_ok=True)
    s = kn5_to_obj(kn5s, out, flip_z=not args.no_flip_z)
    print(f"{' + '.join(k.name for k in kn5s)} -> {out}  ({s['meshes']} groups, {s['verts']:,} v, {s['tris']:,} tri)")
    if len(kn5s) > 1:
        for fs in s["files"]:
            print(f"  {fs['file']}: {fs['meshes']} groups, {fs['verts']:,} v, {fs['tris']:,} tri "
                  f"(vertex offset {fs['vertex_offset']:,})")
    # GATE CENTRELINE. The loop prep (build_kn5_loop) writes data/finished_centerline.json in the
    # KN5 frame (x, y, -z) for kn5_ground_check, which reads the kn5 itself. This OBJ is in the
    # ENGINE frame (z un-mirrored above), so drive_test/audit must walk the same line in the same
    # frame: write it beside the OBJ as data/gate_centerline.json. (2026-10-08: drive_test preferred
    # finished_centerline and swept a z-mirrored path over a local-frame OBJ — every finding was
    # from the wrong side of the map; the median-zone exemption inherited the same mismatch.)
    fin = args.project / "data" / "finished_centerline.json"
    if fin.exists() and not args.no_flip_z:
        f = json.loads(fin.read_text(encoding="utf-8"))
        f["points_xyz_m"] = [[p[0], p[1], -p[2]] for p in f["points_xyz_m"]]
        f["frame"] = "engine (x=E, y=up, z=N) — finished_centerline with z un-mirrored, matches track.obj"
        gc = args.project / "data" / "gate_centerline.json"
        gc.write_text(json.dumps(f), encoding="utf-8")
        print(f"  gate centreline -> {gc.name} (finished_centerline, z un-mirrored to the OBJ frame)")


if __name__ == "__main__":
    main()
