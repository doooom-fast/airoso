"""Extract a BUILT kn5 into ``data/track.obj`` so the OBJ gates can judge a Blender-first track.

The S8 hole that let 0013 ship: a Blender-first track (loop.blend → kn5) never writes a
``track.obj``, so ``drive_test`` and ``audit_mesh`` — the two gates that simulate the car — had
nothing to read and were silently skipped. This closes it from the artifact side, in the spirit of
L5: take the SHIPPED kn5 (not any intermediate), decode every mesh, and write the gate OBJ.

Frame: the kn5 is Z-MIRRORED relative to the engine local frame (engine x=E, y=up, z=N; verified
against dummies.json vs the installed kn5 on Lake Murray: kn5 z = −engine z, x/y equal). The
mirror inverts winding, so every face is emitted reversed — same discipline as L6's "reflection
inverts face winding" rule, applied in the opposite direction.

    python -m scripts.modkit.kn5_to_gate_obj <project-dir> [--kn5 <file>] [--out <obj>]

Defaults: kn5 = <project>/build/<slug>.kn5 (falls back to newest build/*.kn5), out =
<project>/data/track.obj. Then run, from the pinned .engine:

    python -m scripts.geometry.drive_test  <project-dir>
    python -m scripts.geometry.audit_mesh  <project-dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extract_kn5 import _xform, parse


def kn5_to_obj(kn5_path: Path, out_obj: Path, *, flip_z: bool = True) -> dict:
    parsed = parse(kn5_path)
    mats = parsed["materials"]
    stats = {"meshes": 0, "verts": 0, "tris": 0}
    with open(out_obj, "w", encoding="ascii", newline="\n") as f:
        f.write(f"# gate OBJ extracted from {kn5_path.name} (kn5->engine frame"
                f"{', z mirrored, winding reversed' if flip_z else ''})\n")
        voff = 0
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
            stats["meshes"] += 1
            stats["verts"] += len(mesh["verts"])
            stats["tris"] += len(idx) // 3
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract a built kn5 into the gate OBJ (data/track.obj).")
    ap.add_argument("project", type=Path)
    ap.add_argument("--kn5", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-flip-z", action="store_true",
                    help="kn5 already in engine frame (rare; default assumes the standard mirror)")
    args = ap.parse_args()

    kn5 = args.kn5
    if kn5 is None:
        slug = json.loads((args.project / "track.config.json").read_text(encoding="utf-8"))["slug"]
        cand = args.project / "build" / f"{slug}.kn5"
        if not cand.exists():
            builds = sorted((args.project / "build").glob("*.kn5"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
            if not builds:
                raise SystemExit(f"no kn5 found under {args.project}/build — build first")
            cand = builds[0]
        kn5 = cand
    out = args.out or (args.project / "data" / "track.obj")
    out.parent.mkdir(parents=True, exist_ok=True)
    s = kn5_to_obj(kn5, out, flip_z=not args.no_flip_z)
    print(f"{kn5.name} -> {out}  ({s['meshes']} groups, {s['verts']:,} v, {s['tris']:,} tri)")


if __name__ == "__main__":
    main()
