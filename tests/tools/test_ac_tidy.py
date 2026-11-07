"""tools/ac_tidy.py — the AC content/tracks inventory, its classes and flags, and the moves / renames / restore it
makes (Kevin 2026-11-06: "a routine on the PC that keeps AC clean and up-to-date"). Plain ``test_*`` on a temp AC."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import ac_tidy as at  # noqa: E402

DASH = "—"


def _ui(folder: Path, name: str, version: str, author: str, layout: str = "", bom: bool = False):
    d = folder / "ui" / layout if layout else folder / "ui"
    d.mkdir(parents=True, exist_ok=True)
    raw = json.dumps({"name": name, "version": version, "author": author}, ensure_ascii=False).encode("utf-8")
    (d / "ui_track.json").write_bytes((b"\xef\xbb\xbf" if bom else b"") + raw)
    (folder / f"{folder.name}.kn5").write_bytes(b"x" * 100)


@pytest.fixture
def env(tmp_path):
    ac, arch = tmp_path / "tracks", tmp_path / "archive"
    ac.mkdir()
    _ui(ac / "trk_lm", f"doooom Colorado {DASH} Trk (LM engine)", "0.1.2", "doooom")
    _ui(ac / "trk", f"doooom Colorado {DASH} Trk", "0.67.1", "doooom")            # unlisted, has an _lm twin
    _ui(ac / "old", f"doooom Colorado {DASH} Old", "0.3.0", "doooom")             # manifest: superseded
    _ui(ac / "keepme", f"doooom Colorado {DASH} Keep", "0.2.1", "doooom")         # manifest: kept
    _ui(ac / "k10x", "K10 - Somewhere", "0.9.0", "k10-somewhere")                  # unlisted k10 build
    _ui(ac / "orphan", f"doooom Utah {DASH} Orphan", "0.1.0", "doooom")           # ours, unlisted, no successor
    _ui(ac / "ks_monza", "Monza", "1.0", "Kunos")                                   # not ours
    _ui(ac / "trk_lm_trap", "Somebody's track", "2.0", "someone")                   # not ours, never moved
    for lay in ("free", "race"):
        _ui(ac / "lm_v4", f"K10 - San Diego CANDIDATE v4 keep-roads {DASH} {lay}", "0.20.2", "k10-san-diego",
            layout=lay, bom=(lay == "race"))
    man = {"ac_tracks": str(ac), "archive": str(arch),
           "ours": {"authors": ["doooom", "airoso", "k10-san-diego"], "name_prefixes": ["doooom", "K10"]},
           "folders": {
               "trk_lm": {"track": "trk-lm", "role": "current", "version": "0.1.2", "branch": "b"},
               "old": {"track": "old", "role": "superseded", "successor": "trk_lm", "version": "0.3.0"},
               "keepme": {"track": "keep", "role": "kept", "version": "0.2.1"},
               "lm_v4": {"track": "lm", "role": "current", "version": "0.20.1", "ui_name_prefix": "doooom San Diego",
                         "old_name_prefix": "K10 - San Diego CANDIDATE v4 keep-roads"},
               "gone_lm": {"track": "gone", "role": "current", "version": "0.1.0"}}}
    mp = tmp_path / "ac-installed.json"
    mp.write_text(json.dumps(man), encoding="utf-8")
    return ac, arch, mp, man


def _classes(inv):
    return {r["folder"]: r["class"] for r in inv["rows"]}


def test_classes_and_flags(env):
    ac, _arch, _mp, man = env
    inv = at.inventory(man, ac, bv_fn=lambda b, t: "0.1.3" if t == "trk-lm" else None)
    c = _classes(inv)
    assert c == {"trk_lm": "current", "trk": "superseded", "old": "superseded", "keepme": "kept", "k10x": "k10-era",
                 "orphan": "unlisted", "ks_monza": "not-ours", "trk_lm_trap": "not-ours", "lm_v4": "current"}
    rows = {r["folder"]: r for r in inv["rows"]}
    assert rows["trk"]["successor"] == "trk_lm"
    assert any(f.startswith("newer (0.1.3") for f in rows["trk_lm"]["flags"])
    assert any(f.startswith("version-drift") for f in rows["lm_v4"]["flags"])
    assert any(f.startswith("old-name") for f in rows["lm_v4"]["flags"])
    assert inv["missing"] == ["gone_lm"]
    assert sorted(r["folder"] for r in at.plan_of(inv)) == ["k10x", "old", "trk"]
    assert rows["trk"]["size"] == 100 + len(json.dumps({"name": f"doooom Colorado {DASH} Trk", "version": "0.67.1",
                                                        "author": "doooom"}, ensure_ascii=False).encode())


def test_dry_run_moves_nothing(env, capsys, monkeypatch):
    ac, arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    before = sorted(p.name for p in ac.iterdir())
    assert at.main(["--manifest", str(mp)]) == 0
    assert sorted(p.name for p in ac.iterdir()) == before and not arch.exists()
    out = capsys.readouterr().out
    assert "PLAN: move 3 folders" in out and "rename offered: lm_v4" in out and "MISSING: manifest says gone_lm" in out


def test_apply_needs_a_pick_and_refuses_unplanned(env, monkeypatch):
    ac, _arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    monkeypatch.setattr(at, "acs_running", lambda: False)
    with pytest.raises(SystemExit, match="--only"):
        at.main(["--manifest", str(mp), "--apply"])
    for bad in ("ks_monza", "trk_lm", "keepme", "orphan"):
        with pytest.raises(SystemExit, match="not in the plan"):
            at.main(["--manifest", str(mp), "--apply", "--only", bad])
    assert (ac / "ks_monza").is_dir() and (ac / "trk_lm").is_dir()


def test_apply_refuses_while_ac_runs(env, monkeypatch):
    _ac, arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    monkeypatch.setattr(at, "acs_running", lambda: True)
    with pytest.raises(SystemExit, match="acs.exe"):
        at.main(["--manifest", str(mp), "--apply", "--all"])
    assert not arch.exists()


def test_apply_moves_then_restore(env, monkeypatch):
    ac, arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    monkeypatch.setattr(at, "acs_running", lambda: False)
    assert at.main(["--manifest", str(mp), "--apply", "--only", "trk,old"]) == 0
    (tidy,) = list(arch.glob("*_tidy"))
    assert (tidy / "trk" / "trk.kn5").is_file() and (tidy / "old").is_dir()
    assert not (ac / "trk").exists() and (ac / "k10x").is_dir() and (ac / "ks_monza").is_dir()
    lines = (tidy / "MOVES.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("from\tto") and len(lines) == 3
    assert at.main(["restore", str(tidy), "--manifest", str(mp)]) == 0
    assert (ac / "trk" / "trk.kn5").is_file() and (ac / "old").is_dir() and not (tidy / "trk").exists()


def test_apply_all_never_touches_not_ours_or_current(env, monkeypatch):
    ac, _arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    monkeypatch.setattr(at, "acs_running", lambda: False)
    at.main(["--manifest", str(mp), "--apply", "--all"])
    assert sorted(p.name for p in ac.iterdir()) == ["keepme", "ks_monza", "lm_v4", "orphan", "trk_lm", "trk_lm_trap"]


def test_rename_keeps_originals_and_restore_puts_them_back(env, monkeypatch):
    ac, arch, mp, _man = env
    monkeypatch.setattr(at, "branch_version", lambda b, t: None)
    monkeypatch.setattr(at, "acs_running", lambda: False)
    orig = {lay: (ac / "lm_v4" / "ui" / lay / "ui_track.json").read_bytes() for lay in ("free", "race")}
    assert at.main(["--manifest", str(mp), "--rename", "--only", "lm_v4"]) == 0
    for lay in ("free", "race"):
        raw = (ac / "lm_v4" / "ui" / lay / "ui_track.json").read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf") == (lay == "race")
        assert json.loads(raw.decode("utf-8-sig"))["name"] == f"doooom San Diego {DASH} {lay}"
    (tidy,) = list(arch.glob("*_tidy"))
    assert (tidy / "lm_v4.ui" / "ui" / "free" / "ui_track.json").read_bytes() == orig["free"]
    assert not (tidy / "MOVES.tsv").exists()
    at.main(["restore", str(tidy), "--manifest", str(mp)])
    for lay in ("free", "race"):
        assert (ac / "lm_v4" / "ui" / lay / "ui_track.json").read_bytes() == orig[lay]


def test_record_writes_the_installed_version(env):
    ac, _arch, mp, _man = env
    assert at.main(["record", "trk_lm", "--track", "trk-lm", "--branch", "claude/x", "--sha", "abc1234",
                    "--engine", "lm-v4", "--date", "2026-11-06", "--manifest", str(mp)]) == 0
    ent = json.loads(mp.read_text(encoding="utf-8"))["folders"]["trk_lm"]
    assert ent["version"] == "0.1.2" and ent["sha"] == "abc1234" and ent["branch"] == "claude/x"
    assert ent["role"] == "current" and ent["engine"] == "lm-v4" and ent["installed"] == "2026-11-06"


def test_the_repo_manifest_parses_and_names_known_roles():
    man = json.loads((ROOT / "fleet" / "ac-installed.json").read_text(encoding="utf-8"))
    for name, ent in man["folders"].items():
        assert ent["role"] in ("current", "kept", "superseded", "k10-era"), name
        assert ent.get("track"), name
        if ent["role"] == "superseded":
            assert man["folders"][ent["successor"]]["role"] == "current", name
