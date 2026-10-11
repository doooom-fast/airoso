"""scripts/ac/export_kn5_addon.py — the --blend / --out arguments (ledger 0047) and the engine-july
mirror. The module runs Blender at import, so the argument parser is lifted out of the source by
AST and exercised alone; the mirror check pins that the pinned build-of-record copy
(C:/Users/Owner/Documents/GitHub/engine-july) is byte-identical when it exists on this box.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "ac" / "export_kn5_addon.py"
ENG = Path("C:/Users/Owner/Documents/GitHub/engine-july/scripts/ac/export_kn5_addon.py")


def _parser():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_args_from_argv")
    mod = ast.Module(body=[fn], type_ignores=[])
    ns = {"Path": Path}
    exec(compile(mod, str(SRC), "exec"), ns)
    return ns["_args_from_argv"]


def test_defaults_and_overrides():
    p = _parser()
    a = p(["blender", "--background", "--python", "x.py", "--", "C:/proj"])
    assert a["project"] == Path("C:/proj").resolve() and a["blend"] is None and a["out"] is None
    a = p(["b", "--", "C:/proj", "--blend", "C:/proj/blender/split/loop_race.blend", "--out", "slug_race.kn5"])
    assert a["blend"] == Path("C:/proj/blender/split/loop_race.blend").resolve()
    assert a["out"] == "slug_race.kn5"


def test_out_must_be_a_bare_kn5_name_and_unknown_flags_fail():
    p = _parser()
    for bad in ("build/x.kn5", "x.ini", "C:/x/y.kn5"):
        try:
            p(["b", "--", "C:/proj", "--out", bad])
        except SystemExit:
            pass
        else:
            raise AssertionError(f"--out {bad!r} accepted")
    try:
        p(["b", "--", "C:/proj", "--keep-prefix", "1WALL_RACE"])
    except SystemExit:
        pass
    else:
        raise AssertionError("unknown flag accepted")


def test_ini_is_named_after_the_pass_and_the_kn5_is_asserted():
    s = SRC.read_text(encoding="utf-8")
    assert 'f"{kn5.stem}.ini"' in s, "one .ini per pass, named after its kn5"
    assert 'for old in build.glob("*.ini"):' in s, "the purge that leaves exactly one ini for read_settings"
    assert "no kn5 written" in s, "a pass that writes nothing must exit nonzero"


def test_engine_july_mirror_is_byte_identical():
    if not ENG.exists():
        print("  (engine-july not on this box — mirror check skipped)")
        return
    assert hashlib.md5(ENG.read_bytes()).hexdigest() == hashlib.md5(SRC.read_bytes()).hexdigest(), \
        "scripts/ac/export_kn5_addon.py differs from the engine-july copy — cp and record the md5"
