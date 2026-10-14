"""Provenance snapshot of the build-of-record engine — the code tools/ship_sd.sh executes from
engine-july, copied read-only into tracks/san-diego-lake-murray/engine-july-snapshot/ with an md5
manifest, so the files that build the Lake Murray kn5s exist somewhere git can see.

WHY: engine-july (C:/Users/Owner/Documents/GitHub/engine-july) is a DANGLING git worktree of the
retired k10-track-agents repo — `git status` refuses it, nothing in it is committed, and it is still
what ship_sd.sh runs for the prep, the exporter and the spawn kn5s. ENG stays the thing that RUNS; this
copy is evidence of what ran, and tests/tools/test_engine_july_snapshot.py fails the suite the moment a
live ENG file drifts from the manifest without the snapshot being refreshed.

What is copied (exactly what the ship chain loads, nothing else):
  scripts/ac/build_kn5_loop.py      the prep            ("$ENG/scripts/ac/build_kn5_loop.py")
  scripts/ac/export_kn5_addon.py    the exporter driver ("$ENG/scripts/ac/export_kn5_addon.py", x2)
  scripts/ac/build_spawn_kn5.py     the spawn kn5s      ("$ENG/scripts/ac/build_spawn_kn5.py")
  scripts/ac/pbr.py                 imported by the prep (from scripts.ac import pbr) and the exporter
  scripts/geometry/dummies.py       imported by the prep on its single-layout path
  scripts/__init__.py, scripts/ac/__init__.py, scripts/geometry/__init__.py   the package chain
  vendor/io_import_accsv/           zipped + installed by the exporter and build_spawn_kn5 (its .py and
                                    README only: kn52fbx/*.exe|.dll are the kn5->FBX IMPORT helpers, never
                                    loaded by an export — listed in EXCLUDED with their md5, not copied)
  appdata-addons/blender-assetto-corsa-tools/   the add-on that actually registers `exporter.kn5`
                                    (export_kn5_addon._find_export_op picks it first) — it lives in
                                    Blender's user add-on dir, not in ENG; copied for the same reason
Referenced, NOT copied (binaries the code reads by name): every assets/textures file a pbr.TEXTURES row
or the Lake Murray config names that exists in ENG — md5 + size in REFERENCED.md5.

    PYTHONUTF8=1 python tools/snapshot_engine_july.py            # (re)write the snapshot + manifests
    PYTHONUTF8=1 python tools/snapshot_engine_july.py --check    # compare only; exit 1 on any drift
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
_SIBLING = AIROSO.parent / "engine-july"
# the checkout's sibling, else tools/ship_sd.sh's own default (a git worktree's parent is not GitHub/)
DEFAULT_ENG = _SIBLING if _SIBLING.is_dir() else Path("C:/Users/Owner/Documents/GitHub/engine-july")
# ENG=<dir> (as in tools/ship_sd.sh): snapshot a scratch COPY of engine-july that carries a change not yet mirrored
# into the real one; the refresh then records each changed file in PENDING-MIRROR.md5 (see build())
ENG = Path(os.environ["ENG"]) if os.environ.get("ENG") else DEFAULT_ENG
APPDATA_ADDONS = Path(os.environ.get("APPDATA") or "C:/Users/Owner/AppData/Roaming") / \
    "Blender Foundation" / "Blender" / "4.2" / "scripts" / "addons"
OUT = AIROSO / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot"
SHIP = AIROSO / "tools" / "ship_sd.sh"
TRACK_CFG = AIROSO / "tracks" / "san-diego-lake-murray" / "track.config.json"

CODE = ["scripts/__init__.py", "scripts/ac/__init__.py", "scripts/ac/build_kn5_loop.py",
        "scripts/ac/export_kn5_addon.py", "scripts/ac/build_spawn_kn5.py", "scripts/ac/pbr.py",
        "scripts/geometry/__init__.py", "scripts/geometry/dummies.py"]
ADDON_DIRS = ["vendor/io_import_accsv", "appdata-addons/blender-assetto-corsa-tools"]
APPDATA_PREFIX = "appdata-addons/"
EXCLUDE_SUFFIXES = (".exe", ".dll", ".pyc", ".pyo")
MANIFEST = "MANIFEST.md5"
REFERENCED = "REFERENCED.md5"
EXCLUDED = "EXCLUDED.md5"
# "<live md5 in the real engine-july>  <snapshot md5>  <path>": a change made in the snapshot (and rehearsed on a
# scratch ENG copy) that the real engine-july has not received yet. The live drift test accepts exactly that old md5
# for exactly that path until the file is mirrored (cp + md5 check), after which the line is stale and the next
# refresh drops it.
PENDING = "PENDING-MIRROR.md5"
SIZE_CAP = 5_000_000


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def live_path(rel: str) -> Path:
    """where a snapshot-relative path lives today: appdata-addons/<x> -> Blender's user add-on dir, else ENG"""
    if rel.startswith(APPDATA_PREFIX):
        return APPDATA_ADDONS / rel[len(APPDATA_PREFIX):]
    return ENG / rel


def ship_eng_paths(text: str | None = None) -> list[str]:
    """every "$ENG/<path>" ship_sd.sh names (the files the chain executes from ENG)"""
    text = SHIP.read_text(encoding="utf-8") if text is None else text
    return sorted(set(re.findall(r'"\$ENG/([^"\s]+)"', text)))


def _addon_files(rel_dir: str) -> tuple[list[str], list[str]]:
    root = live_path(rel_dir)
    keep, skip = [], []
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        if "__pycache__" in f.parts or ".git" in f.parts:
            continue
        rel = f"{rel_dir}/{f.relative_to(root).as_posix()}"
        (skip if f.suffix.lower() in EXCLUDE_SUFFIXES else keep).append(rel)
    return keep, skip


def referenced_textures() -> list[str]:
    """assets/textures/<name> for every pbr.TEXTURES diffuse/normal (ENG's pbr) and every Lake Murray
    texture_overrides path, that exists in ENG"""
    spec = importlib.util.spec_from_file_location("_eng_pbr_snapshot", ENG / "scripts" / "ac" / "pbr.py")
    pbr = importlib.util.module_from_spec(spec)
    was, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # read-only: no __pycache__ written into ENG
    try:
        spec.loader.exec_module(pbr)
    finally:
        sys.dont_write_bytecode = was
    names = {n for row in pbr.TEXTURES.values() for n in row[:2] if n}
    rels = {f"assets/textures/{n}" for n in names}
    try:
        cfg = json.loads(TRACK_CFG.read_text(encoding="utf-8"))
        for o in (cfg.get("texture_overrides") or {}).values():
            for k in ("diffuse", "normal"):
                if o.get(k):
                    rels.add(str(o[k]).replace("\\", "/"))
    except (OSError, ValueError):
        pass
    return sorted(r for r in rels if (ENG / r).is_file())


def read_manifest(path: Path) -> list[tuple[str, str]]:
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        out.append((parts[0], parts[-1]))
    return out


def read_pending(path: Path | None = None) -> dict[str, tuple[str, str]]:
    """{path: (old md5 still live in the real engine-july, new md5 in the snapshot)}"""
    path = OUT / PENDING if path is None else path
    out = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                old, new, rel = ln.split()[:3]
                out[rel] = (old, new)
    return out


def _write_pending(rows, refs=()) -> None:
    """after a refresh from ENG: every snapshotted file whose md5 differs from the REAL engine-july's is a change
    still to mirror — and every referenced texture the real engine-july lacks or holds at another md5 (ledger 0053's
    worn kerb atlas, v0.18.0: old md5 "-" = not there yet); none -> no PENDING file"""
    p = OUT / PENDING
    lines = []
    if ENG.resolve() != DEFAULT_ENG.resolve() and DEFAULT_ENG.is_dir():
        for h, r in rows:
            live = DEFAULT_ENG / r if not r.startswith(APPDATA_PREFIX) else live_path(r)
            if live.is_file() and md5(live) != h:
                lines.append(f"{md5(live)}  {h}  {r}\n")
        for h, _n, r in refs:
            live = DEFAULT_ENG / r
            if not live.is_file():
                lines.append(f"-  {h}  {r}\n")
            elif md5(live) != h:
                lines.append(f"{md5(live)}  {h}  {r}\n")
    if lines:
        p.write_text("# old md5 (still live in " + DEFAULT_ENG.as_posix() + ")  new md5 (this snapshot)  path —\n"
                     "# changes rehearsed on a scratch ENG copy, to mirror into the real engine-july (cp, then check the\n"
                     "# md5). Written by tools/snapshot_engine_july.py; tests accept the old md5 until then.\n"
                     + "".join(lines), encoding="utf-8")
        print(f"[snapshot] {len(lines)} file(s) pending a mirror into {DEFAULT_ENG} -> {p.name}")
    elif p.exists() and ENG.resolve() == DEFAULT_ENG.resolve():
        p.unlink()


def build(check_only: bool = False) -> int:
    if not ENG.is_dir():
        print(f"[snapshot] {ENG} does not exist — nothing to snapshot")
        return 1
    copy, excluded = list(CODE), []
    for d in ADDON_DIRS:
        if not live_path(d).is_dir():
            print(f"[snapshot] WARNING {live_path(d)} missing — {d} not snapshotted")
            continue
        keep, skip = _addon_files(d)
        copy += keep
        excluded += skip
    missing = [p for p in ship_eng_paths() if p not in copy]
    if missing:
        print(f"[snapshot] FAIL ship_sd.sh executes ENG files the snapshot does not list: {missing}")
        return 1
    rows = [(md5(live_path(r)), r) for r in copy]
    refs = [(md5(ENG / r), (ENG / r).stat().st_size, r) for r in referenced_textures()]
    excl = [(md5(live_path(r)), live_path(r).stat().st_size, r) for r in excluded]
    if check_only:
        man = dict((r, h) for h, r in read_manifest(OUT / MANIFEST))
        pend = read_pending()
        drift = [r for h, r in rows if man.get(r) != h and not (r in pend and pend[r] == (h, man.get(r)))] \
            + [r for r in man if r not in dict((r, h) for h, r in rows)]
        for r in sorted(set(pend) & {r for h, r in rows if man.get(r) != h}):
            print(f"[snapshot] PENDING MIRROR {r} (live {pend[r][0]}, snapshot {pend[r][1]})")
        refm = dict((r, h) for h, r in read_manifest(OUT / REFERENCED))
        drift += [r for h, _, r in refs if refm.get(r) != h]
        for r, rh in refm.items():          # a referenced texture still to mirror: pending, not drift
            if r not in dict((r2, h2) for h2, _n2, r2 in refs):
                if pend.get(r) == ("-", rh):
                    print(f"[snapshot] PENDING MIRROR {r} (not in ENG yet, snapshot {rh})")
                else:
                    drift.append(r)
        for r in drift:
            print(f"[snapshot] DRIFT {r}")
        print(f"[snapshot] {'OK' if not drift else 'DRIFT'}: {len(rows)} copied files, {len(refs)} referenced textures checked")
        return 1 if drift else 0
    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            if p.is_file() and p.name not in ("README.md", PENDING):
                p.unlink()
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
    for h, r in rows:
        dst = OUT / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(live_path(r), dst)
        if md5(dst) != h:
            raise SystemExit(f"[snapshot] copy of {r} does not match its source md5")
    hdr = ("# md5  path — the engine-july files tools/ship_sd.sh executes, as copied into this snapshot.\n"
           "# path is relative to this folder; live source = engine-july/<path>, except appdata-addons/<x> =\n"
           "# %APPDATA%/Blender Foundation/Blender/4.2/scripts/addons/<x>. Written by tools/snapshot_engine_july.py.\n")
    (OUT / MANIFEST).write_text(hdr + "".join(f"{h}  {r}\n" for h, r in rows), encoding="utf-8")
    (OUT / REFERENCED).write_text(
        "# md5  bytes  path — binaries the snapshotted code reads by name from engine-july, NOT copied (size).\n"
        "# Checked against the live files by tests/tools/test_engine_july_snapshot.py like MANIFEST.md5.\n" +
        "".join(f"{h}  {n:>9}  {r}\n" for h, n, r in refs), encoding="utf-8")
    (OUT / EXCLUDED).write_text(
        "# md5  bytes  path — files of the snapshotted add-on folders deliberately NOT copied: the kn5->FBX\n"
        "# IMPORT helpers (never loaded by an export). Recorded so the omission is visible, not silent.\n" +
        "".join(f"{h}  {n:>9}  {r}\n" for h, n, r in excl), encoding="utf-8")
    _write_pending(rows, refs)
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"[snapshot] {len(rows)} files copied, {len(refs)} referenced textures, {len(excl)} excluded binaries; "
          f"snapshot {total / 1e6:.2f} MB -> {OUT}")
    if total > SIZE_CAP:
        print(f"[snapshot] WARNING snapshot is {total / 1e6:.2f} MB (> {SIZE_CAP / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(build(check_only="--check" in sys.argv[1:]))
