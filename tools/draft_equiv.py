"""Two builds of one track, from two branches, compared file by file and object by object (ledger 0078).

The PC's apples-to-apples check for Lake Murray: the same chain run on claude/lm-v4-line and on claude/fleet-lm-engine,
each in its own scratch copy of lm_v4, must leave the same project. This compares

- every file under both project dirs (bytes), except blends (judged by digest, below) and build/ (kn5s: tools/kn5_equiv.py).
  A .gz is judged by its content (the gzip header holds a write time). A text file that differs only by the project's own
  path (the two scratch copies have different names), or a JSON file only in its write-time stamps (WRITE_TIME_KEYS, e.g.
  terrain.tiers.json.gz's _provenance.written_utc), is reported as path / time only and is not a difference;
- each pair of tools/blend_digest.py digests given with --digest: objects present in one only, and any object whose type,
  parent, world matrix, materials, vertex / face counts or position / face / UV md5 differ.

THE TERRAIN STAGE IS NOT BIT-STABLE (--terrain-noise, ledger 0078 step 5, the PC 2026-11-04). Lake Murray's chain drafted
twice on the SAME branch (lm-v4-line 6f96224, two fresh copies of lm_v4, one ENG) does not give the same terrain: TERRAIN
632,014 vs 631,989 vertices, ground_release welding 6,963 vs 7,014 coincident vertices and listing its face caps in another
order, so every house seated on that ground and every prepped ground tile moves with it. Everything else came out
identical. --terrain-noise allows exactly that, as a written list (TERRAIN_NOISE), and nothing else:
  - files: the terrain stage's own reports (TERRAIN_NOISE["files"]), the split manifest's two position censuses, the stub
    report's count of terrain vertices it pinned (stubs.built.json terrain.verts_pinned: 14,467 / 14,468 on the same
    branch, the PC 2026-11-05), and any JSON key named "seconds" (wall-clock run time);
  - objects: TERRAIN, every 1GRASS* tile (rock faces included), any change; the house meshes (BUILDING_*, ROOFTOP_*,
    FARBLOCK_*, 1WALL_TILTUP*) in their vertex positions ONLY: the same counts, faces, UVs, materials and matrix.
Each allowed difference is still printed, marked "(terrain-stage noise)"; the verdict is SAME only when nothing else
differs. Every road / curb / marking / race / closure / spawn / street object and every other data file must be identical.

Exit 0 = no difference (or only the allowed terrain-stage noise, with --terrain-noise); 1 = differences (listed); 2 = usage.

    python tools/draft_equiv.py <proj-a> <proj-b> [--digest <a.json> <b.json>]... [--terrain-noise]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

SKIP_DIRS = {"build", "__pycache__"}
SKIP_SUFFIX = (".blend", ".blend1", ".blend2")
TEXT_SUFFIX = (".json", ".ini", ".txt", ".csv", ".geojson", ".kml", ".lut", ".md")
WRITE_TIME_KEYS = ("written_utc", "check_date")      # when a file was written, never what it holds
TERRAIN_NOISE = {                                     # --terrain-noise: the written exception list (module doc)
    "files": ("data/ground_release.report.json", "data/terrain_thin.json", "data/terrain_thin.nodes.json.gz",
              "data/rock_faces.json"),
    "file_keys": {"blender/split/split_manifest.json": (("input_census", "positions"),
                                                        ("outputs", "loop_main.blend", "positions")),
                  "data/stubs.built.json": (("terrain", "verts_pinned"),)},     # the terrain's vertices the stubs pin
    "timing_keys": ("seconds",),
    "objects_any": ("TERRAIN", "1GRASS"),
    "objects_positions_only": ("BUILDING_", "ROOFTOP_", "FARBLOCK_", "1WALL_TILTUP"),
}


def _drop_times(x):
    if isinstance(x, dict):
        return {k: _drop_times(v) for k, v in x.items() if k not in WRITE_TIME_KEYS}
    if isinstance(x, list):
        return [_drop_times(v) for v in x]
    return x


def _files(root: Path):
    out = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if not p.is_file() or rel.parts[0] in SKIP_DIRS or p.name.endswith(SKIP_SUFFIX):
            continue
        out[rel.as_posix()] = p
    return out


def _spellings(root: Path):
    s = str(root.resolve())
    forms = {s, s.replace("\\", "/"), s.replace("/", "\\"), s.replace("\\", "\\\\"), str(root), str(root).replace("\\", "/")}
    if len(s) > 2 and s[1] == ":":
        forms |= {f.replace(s[0] + ":", s[0].swapcase() + ":", 1) for f in list(forms)}
        forms.add("/" + s[0].lower() + s[2:].replace("\\", "/"))          # Git Bash's /d/k10-scratch/...
    return sorted((f for f in forms if f), key=len, reverse=True)


def _norm(text: str, root: Path):
    for f in _spellings(root):
        text = text.replace(f, "<PROJ>")
    return text


def _drop_keys(x, keys):
    if isinstance(x, dict):
        return {k: _drop_keys(v, keys) for k, v in x.items() if k not in keys}
    if isinstance(x, list):
        return [_drop_keys(v, keys) for v in x]
    return x


def _drop_path(x, path):
    """a copy of x with the key at path (a tuple of dict keys) removed"""
    if not path or not isinstance(x, dict) or path[0] not in x:
        return x
    y = dict(x)
    if len(path) == 1:
        del y[path[0]]
    else:
        y[path[0]] = _drop_path(y[path[0]], path[1:])
    return y


def _noise_file(rel: str, ja, jb) -> bool:
    """--terrain-noise: True when this file's difference is on the written list"""
    if rel in TERRAIN_NOISE["files"]:
        return True
    if ja is None or jb is None:
        return False
    for k in (rel,):
        for path in TERRAIN_NOISE["file_keys"].get(k, ()):
            ja, jb = _drop_path(ja, path), _drop_path(jb, path)
    ja, jb = _drop_keys(ja, TERRAIN_NOISE["timing_keys"]), _drop_keys(jb, TERRAIN_NOISE["timing_keys"])
    return ja == jb


def _compare_files(a: Path, b: Path, terrain_noise: bool = False):
    fa, fb = _files(a), _files(b)
    diffs, path_only, noise = [], [], []
    for rel in sorted(set(fa) - set(fb)):
        diffs.append(f"only in A: {rel}")
    for rel in sorted(set(fb) - set(fa)):
        diffs.append(f"only in B: {rel}")
    for rel in sorted(set(fa) & set(fb)):
        ba, bb = fa[rel].read_bytes(), fb[rel].read_bytes()
        if ba == bb:
            continue
        if rel.endswith(".gz"):                         # the gzip header carries a write time: judge the content
            ba, bb = gzip.decompress(ba), gzip.decompress(bb)
            if ba == bb:
                continue
            rel_t = rel[:-3]
        else:
            rel_t = rel
        ja = jb = None
        if rel_t.endswith(TEXT_SUFFIX):
            try:
                ta, tb = _norm(ba.decode("utf-8"), a), _norm(bb.decode("utf-8"), b)
                if ta == tb:
                    path_only.append(rel)
                    continue
                if rel_t.endswith((".json", ".geojson")):
                    ja, jb = _drop_times(json.loads(ta)), _drop_times(json.loads(tb))
                    if ja == jb:
                        path_only.append(rel)
                        continue
            except (UnicodeDecodeError, ValueError):
                pass
        if terrain_noise and _noise_file(rel, ja, jb):
            noise.append(f"differs: {rel} ({len(ba)} vs {len(bb)} bytes) (terrain-stage noise)")
            continue
        diffs.append(f"differs: {rel} ({len(ba)} vs {len(bb)} bytes)")
    return len(set(fa) & set(fb)), diffs, path_only, noise


def _noise_object(name: str, keys) -> bool:
    """--terrain-noise: True when this object's difference is on the written list"""
    if name == TERRAIN_NOISE["objects_any"][0] or name.startswith(TERRAIN_NOISE["objects_any"][1:]):
        return True
    return name.startswith(TERRAIN_NOISE["objects_positions_only"]) and set(keys) <= {"co_md5"}


def _compare_digests(da: Path, db: Path, terrain_noise: bool = False):
    A = json.loads(da.read_text(encoding="utf-8"))["objects"]
    B = json.loads(db.read_text(encoding="utf-8"))["objects"]
    diffs = [f"object only in A: {n}" for n in sorted(set(A) - set(B))]
    diffs += [f"object only in B: {n}" for n in sorted(set(B) - set(A))]
    noise = []
    for n in sorted(set(A) & set(B)):
        keys = [k for k in sorted(set(A[n]) | set(B[n])) if A[n].get(k) != B[n].get(k)]
        if keys:
            extra = ""
            if "verts" in keys or "faces" in keys:
                extra = f" (verts {A[n].get('verts')} vs {B[n].get('verts')}, faces {A[n].get('faces')} vs {B[n].get('faces')})"
            line = f"object {n}: {', '.join(keys)} differ{extra}"
            if terrain_noise and _noise_object(n, keys):
                noise.append(line + " (terrain-stage noise)")
            else:
                diffs.append(line)
    return len(set(A) & set(B)), diffs, noise


def compare_files(a: Path, b: Path):
    """(files in both, differences, path / time only): the strict file comparison"""
    n, diffs, path_only, _ = _compare_files(a, b)
    return n, diffs, path_only


def compare_digests(da: Path, db: Path):
    """(objects in both, differences): the strict object comparison"""
    m, diffs, _ = _compare_digests(da, db)
    return m, diffs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--digest", nargs=2, action="append", default=[], metavar=("A_JSON", "B_JSON"))
    ap.add_argument("--terrain-noise", action="store_true",
                    help="allow exactly the written list of terrain-stage differences (TERRAIN_NOISE; module doc)")
    args = ap.parse_args(argv)
    if not args.a.is_dir() or not args.b.is_dir():
        print("both arguments must be project directories")
        return 2
    n, diffs, path_only, noise = _compare_files(args.a, args.b, args.terrain_noise)
    print(f"[draft-equiv] files: {n} in both, {len(diffs)} differ, {len(path_only)} differ only by the project path or a write time"
          + (f", {len(noise)} terrain-stage noise" if args.terrain_noise else ""))
    for d in diffs + noise:
        print(f"  {d}")
    n_noise = len(noise)
    for pa, pb in args.digest:
        m, dd, nn = _compare_digests(Path(pa), Path(pb), args.terrain_noise)
        print(f"[draft-equiv] {Path(pa).name} vs {Path(pb).name}: {m} objects in both, {len(dd)} differ"
              + (f", {len(nn)} terrain-stage noise" if args.terrain_noise else ""))
        for d in dd + nn:
            print(f"  {d}")
        diffs += dd
        n_noise += len(nn)
    if diffs:
        print("[draft-equiv] => DIFFERENT")
    elif n_noise:
        print(f"[draft-equiv] => SAME (terrain-stage noise only: {n_noise} allowed differences, the written list)")
    else:
        print("[draft-equiv] => SAME")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
