"""tracks/san-diego-lake-murray/engine-july-snapshot/ — the read-only provenance copy of what
tools/ship_sd.sh executes from engine-july (a dangling git worktree nothing commits).

Always: every copied file matches MANIFEST.md5, every "$ENG/..." path ship_sd.sh names is in the
manifest, the snapshot stays small. When engine-july exists on this machine: every live file in
MANIFEST.md5 (and the textures in REFERENCED.md5) still has the recorded md5 — so an edit to the
build-of-record engine that nobody snapshotted fails the suite instead of drifting silently. Refresh
with `python tools/snapshot_engine_july.py` (README in the snapshot folder).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import snapshot_engine_july as snap  # noqa: E402

SNAP = snap.OUT


def _manifest(name):
    return snap.read_manifest(SNAP / name)


def _snapshot_files():
    """every file in the snapshot except bytecode caches — tests that import a snapshot copy leave
    __pycache__/ behind (gitignored, never snapshot content)"""
    return [p for p in SNAP.rglob("*") if p.is_file() and "__pycache__" not in p.relative_to(SNAP).parts]


def test_snapshot_copies_match_their_manifest_and_stay_small():
    rows = _manifest(snap.MANIFEST)
    assert len(rows) >= 20, len(rows)
    for h, rel in rows:
        p = SNAP / rel
        assert p.is_file(), f"manifest names {rel} but the snapshot has no copy"
        assert snap.md5(p) == h, f"snapshot copy {rel} was edited (md5 {snap.md5(p)} != manifest {h})"
    listed = {rel for _, rel in rows}
    extra = [p.relative_to(SNAP).as_posix() for p in _snapshot_files()
             if p.name not in ("README.md", snap.MANIFEST, snap.REFERENCED, snap.EXCLUDED, snap.PENDING)
             and p.relative_to(SNAP).as_posix() not in listed]
    assert not extra, f"files in the snapshot no manifest line covers: {extra}"
    total = sum(p.stat().st_size for p in _snapshot_files())
    assert total < snap.SIZE_CAP, f"snapshot is {total / 1e6:.2f} MB"
    assert not [p for p in _snapshot_files() if p.suffix.lower() in snap.EXCLUDE_SUFFIXES], "binaries copied"


def test_every_engine_file_ship_sd_executes_is_snapshotted():
    listed = {rel for _, rel in _manifest(snap.MANIFEST)}
    named = snap.ship_eng_paths()
    assert set(named) >= {"scripts/ac/build_kn5_loop.py", "scripts/ac/export_kn5_addon.py", "scripts/ac/build_spawn_kn5.py"}, named
    missing = [p for p in named if p not in listed]
    assert not missing, f"ship_sd.sh executes ENG files the snapshot lacks: {missing}"
    # the modules those scripts import from ENG, and the add-on that writes the kn5
    for rel in ("scripts/ac/pbr.py", "scripts/geometry/dummies.py", "vendor/io_import_accsv/__init__.py",
                "appdata-addons/blender-assetto-corsa-tools/exporter/__init__.py"):
        assert rel in listed, rel


def test_live_engine_july_has_not_drifted_from_the_snapshot():
    if not snap.ENG.is_dir():
        print(f"  ({snap.ENG} not on this machine — live drift check skipped)")
        return
    drift, skipped, pending = [], 0, []
    pend = snap.read_pending()
    for h, rel in _manifest(snap.MANIFEST):
        live = snap.live_path(rel)
        if rel.startswith(snap.APPDATA_PREFIX) and not snap.APPDATA_ADDONS.is_dir():
            skipped += 1
            continue
        if not live.is_file():
            drift.append(f"{rel}: gone from {live}")
        elif snap.md5(live) != h:
            if pend.get(rel) == (snap.md5(live), h):
                pending.append(rel)            # a recorded change not mirrored into ENG yet: exactly that old md5
            else:
                drift.append(f"{rel}: live {snap.md5(live)} != snapshot {h}")
    for h, rel in _manifest(snap.REFERENCED):
        live = snap.ENG / rel
        if not live.is_file():
            if pend.get(rel) == ("-", h):
                pending.append(rel)            # a referenced texture recorded as still to mirror (not in ENG yet)
            else:
                drift.append(f"{rel}: gone from ENG")
        elif snap.md5(live) != h:
            if pend.get(rel) == (snap.md5(live), h):
                pending.append(rel)
            else:
                drift.append(f"{rel}: live {snap.md5(live)} != recorded {h}")
    assert not drift, ("engine-july drifted from tracks/san-diego-lake-murray/engine-july-snapshot — refresh it on "
                       "purpose (python tools/snapshot_engine_july.py) or undo the change: " + "; ".join(drift[:8]))
    if skipped:
        print(f"  ({skipped} Blender add-on files not checked: no add-on dir on this machine)")
    if pending:
        print(f"  (PENDING MIRROR into {snap.ENG}: {pending} — engine-july-snapshot/{snap.PENDING})")


def test_pending_mirror_lines_name_the_snapshot_copies():
    """every PENDING-MIRROR line's NEW md5 is the snapshot's own (so the mirror copies exactly what was rehearsed),
    its old md5 differs, and it names a manifest path"""
    man = dict((rel, h) for h, rel in _manifest(snap.MANIFEST))
    man.update((rel, h) for h, rel in _manifest(snap.REFERENCED))      # a referenced texture may be pending too
    for rel, (old, new) in snap.read_pending().items():
        assert rel in man, f"PENDING names {rel}, which neither manifest lists"
        assert man[rel] == new, f"PENDING {rel}: new {new} != manifest {man[rel]}"
        assert old != new, rel


def test_pending_lines_excuse_only_their_own_old_md5():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / snap.PENDING).write_text("# header\naaa  bbb  scripts/ac/pbr.py\n", encoding="utf-8")
    assert snap.read_pending(d / snap.PENDING) == {"scripts/ac/pbr.py": ("aaa", "bbb")}


def test_the_race_rows_ship_in_the_snapshotted_pbr():
    """the 2026-10-11 texture-binding fix is in the build-of-record copy, not only in airoso's"""
    text = (SNAP / "scripts" / "ac" / "pbr.py").read_text(encoding="utf-8")
    assert '"1WALL_RACE": ("concrete_barrier_diffuse.png", "concrete_barrier_normal.png"' in text
    assert '"1KERB_RACE": ("kerb_race_worn_diffuse.jpg", "kerb_race_worn_normal.jpg"' in text
    airoso = (ROOT / "scripts" / "ac" / "pbr.py").read_bytes()
    assert (SNAP / "scripts" / "ac" / "pbr.py").read_bytes() == airoso, "ENG's pbr.py and airoso's must stay byte-identical"
