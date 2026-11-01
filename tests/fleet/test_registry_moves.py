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
    # the glob is a list since Milford (2026-10-28), the first track born in airoso; since 2026-11-01 (Kevin: "a
    # complete track list") it names EVERY tracks/<dir>/track.config.json, one by one: each discovered exactly once, in
    # path order, nothing else under tracks/ coming along (tracks/_reference has no config)
    keys = [t.key for t in found]
    assert keys == sorted(keys) and len(keys) == len(set(keys)), "discovered once each, in path order"
    on_disk = sorted(f"airoso/{d.name}" for d in (FLEET_ROOT / "tracks").iterdir() if (d / "track.config.json").is_file())
    assert keys == on_disk, (keys, on_disk)
    assert len(keys) >= 17
    by_key = {t.key: t for t in found}
    lariat = by_key["airoso/lookout-lariat"]
    assert lariat.project_dir == FLEET_ROOT / "tracks" / "lookout-lariat" and lariat.slug == "lookout_lariat"
    assert lariat.kind == "street_port"
    assert by_key["airoso/exotics-racing-lv"].kind == "circuit_port" and by_key["airoso/milford-road-course"].kind == "circuit_port"
    # the freeway network (2026-10-29, ONE-CHAIN §4 row 8): moved from k10-san-diego/project_freeway_net
    assert by_key["airoso/san-diego-freeway"].kind == "street_port" and ann["airoso/san-diego-freeway"]["network"] is True
    # every retired repo lists its old copy under moved_out, so nothing is discovered twice when those repos are present
    for old_repo, dirs in (("k10-colorado", ("imi", "pueblo", "aspen", "grand-junction", "pikes-peak", "second-creek",
                                             "high-plains", "sand-creek", "lookout-lariat")),
                           ("k10-colorado-rally", ("dragon-tail-gravel", "dragon-tail-tarmac", "under-the-dragon-gravel",
                                                   "under-the-dragon-tarmac")),
                           ("k10-san-diego", ("project", "project_freeway_net"))):
        for d in dirs:
            assert d in by_name[old_repo]["moved_out"], (old_repo, d)
    assert not any(k.startswith(("k10-colorado/", "k10-colorado-rally/")) for k in ann), "annotations keyed at airoso"
    assert "project_freeway_net" in by_name["k10-san-diego"]["moved_out"]
