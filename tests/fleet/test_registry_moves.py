"""fleet/ — the V3 one-repo move (Lariat V3-PLAN P0 step 5): ``moved_out``, ``engine_repo`` and a
held build.

Pins:
  * a repo never discovers a track dir it lists under ``moved_out``;
  * the engine repo (``engine_repo: true``) is exempt from S1-S4 (no pin, no shadowing), while an
    otherwise identical consumer still FAILs them;
  * a ``build.cmd: null`` track is reported HOLD, counts as not-a-pass, and runs nothing;
  * the real registry: the Lariat is discovered exactly once, at airoso/tracks/lookout-lariat.
Plain ``test_*`` for tests/run_tests.py. Hermetic: synthetic repos in a temp dir, plus reads of
this repo's own files.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fleet import cli, lint  # noqa: E402
from fleet.registry import ROOT as FLEET_ROOT, Repo, load_registry  # noqa: E402

GATES_SH = "#!/bin/sh\n# drive_test audit_mesh verify_kn5 kn5_ground_check\n"


def _cfg(d: Path, slug: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "track.config.json").write_text(json.dumps({
        "slug": slug, "name": slug, "version": "0.0.1", "loop": True, "source": {"type": "osm"},
        "location": {"lat": 0, "lon": 0}, "layouts": [{"id": "full"}], "archetype": "real_road",
    }), encoding="utf-8")


def test_moved_out_dir_is_not_discovered():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _cfg(repo / "tracks" / "kept", "kept_slug")
        _cfg(repo / "tracks" / "gone", "gone_slug")
        spec = {"name": "old", "tracks_glob": "tracks/*/track.config.json",
                "moved_out": {"gone": "airoso/tracks/gone"}}
        names = [t.dirname for t in Repo("old", repo, spec, True).tracks()]
        assert names == ["kept"], names
        spec.pop("moved_out")
        names = sorted(t.dirname for t in Repo("old", repo, spec, True).tracks())
        assert names == ["gone", "kept"], names


def _engine_like_repo(root: Path) -> None:
    """No bootstrap.sh, no .engine-version, and a scripts/ module at an engine path."""
    mod = root / "scripts" / "gps" / "widths_from_osm.py"
    mod.parent.mkdir(parents=True)
    mod.write_text("# same path as an engine module\n", encoding="utf-8")
    (root / "scripts" / "build.sh").write_text(GATES_SH, encoding="utf-8")
    _cfg(root / "tracks" / "only", "engine_repo_test_slug")


def test_engine_repo_is_exempt_from_pin_and_shadowing_rules():
    assert (FLEET_ROOT / "scripts" / "gps" / "widths_from_osm.py").is_file()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "eng"
        _engine_like_repo(root)
        spec = {"name": "eng", "path": str(root), "tracks_glob": "tracks/*/track.config.json",
                "local_scripts_allowlist": []}
        as_consumer = {f.rule for f in lint.check({"repos": [dict(spec)]}) if f.where == "eng"}
        assert {"S1", "S4"} <= as_consumer, as_consumer
        as_engine = [f for f in lint.check({"repos": [dict(spec, engine_repo=True)]})]
        assert as_engine == [], [(f.rule, f.where, f.message) for f in as_engine]


class _FakeTrack:
    repo, key = "held", "held/track"


def test_held_build_reports_hold_and_runs_nothing():
    reg = {"repos": [{"name": "held", "path": ".", "build": {"cmd": None, "hold": "not yet"}}]}
    saved = (cli.load_registry, cli._select, cli.subprocess.run)

    def _never(*a, **k):
        raise AssertionError("a held build must not run anything")

    cli.load_registry, cli._select, cli.subprocess.run = (lambda: reg), (lambda a: [_FakeTrack()]), _never
    try:
        for run, want_rc in ((False, 0), (True, 1)):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli.cmd_build(argparse.Namespace(run=run, from_stage=None))
            out = buf.getvalue()
            assert rc == want_rc, (run, rc, out)
            assert "HOLD held/track: not yet" in out, out
            assert ("PASS" not in out) and (("HOLD  held/track" in out) == run), out
    finally:
        cli.load_registry, cli._select, cli.subprocess.run = saved


def test_real_registry_puts_the_lariat_at_airoso_once():
    reg = load_registry()
    by_name = {r["name"]: r for r in reg["repos"]}
    air = by_name["airoso"]
    assert air["engine_repo"] is True and air["path"] == "."
    assert air["build"]["cmd"] is None and air["build"]["hold"]
    assert "lookout-lariat" in by_name["k10-colorado"]["moved_out"]
    ann = reg["track_annotations"]
    assert "airoso/lookout-lariat" in ann and "k10-colorado/lookout-lariat" not in ann
    found = Repo("airoso", FLEET_ROOT, air, True).tracks()
    assert [(t.key, t.slug) for t in found] == [("airoso/lookout-lariat", "lookout_lariat")]
    assert found[0].project_dir == FLEET_ROOT / "tracks" / "lookout-lariat"
    assert found[0].kind == "street_port"
