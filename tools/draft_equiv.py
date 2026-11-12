"""Two builds of one track, from two branches, compared file by file and object by object (ledger 0078).

The PC's apples-to-apples check for Lake Murray: the same chain run on claude/lm-v4-line and on claude/fleet-lm-engine,
each in its own scratch copy of lm_v4, must leave the same project. This compares

- every file under both project dirs (bytes), except blends (judged by digest, below) and build/ (kn5s: tools/kn5_equiv.py).
  A .gz is judged by its content (the gzip header holds a write time). A text file that differs only by the project's own
  path (the two scratch copies have different names), or a JSON file only in its write-time stamps (WRITE_TIME_KEYS, e.g.
  terrain.tiers.json.gz's _provenance.written_utc), is reported as path / time only and is not a difference;
- each pair of tools/blend_digest.py digests given with --digest: objects present in one only, and any object whose type,
  parent, world matrix, materials, vertex / face counts or position / face / UV md5 differ.

Exit 0 = no difference; 1 = differences (listed); 2 = usage.

    python tools/draft_equiv.py <proj-a> <proj-b> [--digest <a.json> <b.json>]...
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


def compare_files(a: Path, b: Path):
    fa, fb = _files(a), _files(b)
    diffs, path_only = [], []
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
        if rel_t.endswith(TEXT_SUFFIX):
            try:
                ta, tb = _norm(ba.decode("utf-8"), a), _norm(bb.decode("utf-8"), b)
                if ta == tb:
                    path_only.append(rel)
                    continue
                if rel_t.endswith((".json", ".geojson")) and _drop_times(json.loads(ta)) == _drop_times(json.loads(tb)):
                    path_only.append(rel)
                    continue
            except (UnicodeDecodeError, ValueError):
                pass
        diffs.append(f"differs: {rel} ({len(ba)} vs {len(bb)} bytes)")
    return len(set(fa) & set(fb)), diffs, path_only


def compare_digests(da: Path, db: Path):
    A = json.loads(da.read_text(encoding="utf-8"))["objects"]
    B = json.loads(db.read_text(encoding="utf-8"))["objects"]
    diffs = [f"object only in A: {n}" for n in sorted(set(A) - set(B))]
    diffs += [f"object only in B: {n}" for n in sorted(set(B) - set(A))]
    for n in sorted(set(A) & set(B)):
        keys = [k for k in sorted(set(A[n]) | set(B[n])) if A[n].get(k) != B[n].get(k)]
        if keys:
            extra = ""
            if "verts" in keys or "faces" in keys:
                extra = f" (verts {A[n].get('verts')} vs {B[n].get('verts')}, faces {A[n].get('faces')} vs {B[n].get('faces')})"
            diffs.append(f"object {n}: {', '.join(keys)} differ{extra}")
    return len(set(A) & set(B)), diffs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--digest", nargs=2, action="append", default=[], metavar=("A_JSON", "B_JSON"))
    args = ap.parse_args(argv)
    if not args.a.is_dir() or not args.b.is_dir():
        print("both arguments must be project directories")
        return 2
    n, diffs, path_only = compare_files(args.a, args.b)
    print(f"[draft-equiv] files: {n} in both, {len(diffs)} differ, {len(path_only)} differ only by the project path or a write time")
    for d in diffs:
        print(f"  {d}")
    for pa, pb in args.digest:
        m, dd = compare_digests(Path(pa), Path(pb))
        print(f"[draft-equiv] {Path(pa).name} vs {Path(pb).name}: {m} objects in both, {len(dd)} differ")
        for d in dd:
            print(f"  {d}")
        diffs += dd
    print("[draft-equiv] => SAME" if not diffs else "[draft-equiv] => DIFFERENT")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
