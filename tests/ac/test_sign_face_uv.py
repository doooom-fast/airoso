"""Sign plates keep their own UVs through the prep (Denver Grand Prix PLAN 4b item 8; ledger 0096).

The prep gives every mesh a top-down planar projection (u = x / 4 m, v = y / 4 m) unless its name is in a skip list.
On a vertical sign plate that projection is a line, so a face could not carry artwork and the W1-6 arrow had to be
geometry (tools/make_sign_textures.py's note). The rule now: **a mesh whose name starts with SIGNFACE keeps the UVs it
was authored with, and is not welded.** Nothing else moved: SIGNPLATE (today's flat yellow plate), SIGNARROW, SIGNPOST
and every other name are projected or kept exactly as before.

Both preps carry the rule: airoso's (scripts/ac/build_kn5_loop.py) and the engine-july copy an lm-v4 track runs
(tracks/san-diego-lake-murray/engine-july-snapshot), which Denver Grand Prix is.

Read off the source, the way tests/ac/test_planar_uv_skip_walls.py reads it. What a real Blender run of the prep does
with a SIGNFACE mesh, and that every other mesh comes out byte for byte as before, is in ledger 0096's note (it needs
Blender, which this suite does not run). Plain ``test_*``, stdlib only.
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREPS = {
    "airoso": ROOT / "scripts" / "ac" / "build_kn5_loop.py",
    "engine-july": ROOT / "tracks" / "san-diego-lake-murray" / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py",
}
UV_RE = re.compile(r"if not ob\.name\.upper\(\)\.startswith\(\((.*?)\)\):\s*\n\s*planar_uv\(me\)", re.S)
WELD_RE = re.compile(r"if not ob\.name\.upper\(\)\.startswith\(\((.*?)\)\):\s*\n\s*bmesh\.ops\.remove_doubles\(bm, verts=bm\.verts, dist=1e-4\)",
                     re.S)


def _tuples(text: str):
    uv, weld = UV_RE.search(text), None
    assert uv, "the planar_uv call site with its skip tuple"
    weld = WELD_RE.search(text[uv.end():])
    assert weld, "the weld call site with its skip tuple"
    return ast.literal_eval("(" + uv.group(1) + ")"), ast.literal_eval("(" + weld.group(1) + ")")


def test_a_sign_face_keeps_its_uvs_and_is_not_welded_in_both_preps():
    for which, path in PREPS.items():
        uv, weld = _tuples(path.read_text(encoding="utf-8"))
        assert "SIGNFACE" in uv and "SIGNFACE" in weld, which
        for name in ("SIGNFACE_R1_1", "SIGNFACE_W1_6R", "signface_r2_1_0", "SIGNFACE"):
            assert name.upper().startswith(uv) and name.upper().startswith(weld), (which, name)


def test_every_other_sign_mesh_is_projected_as_before():
    for which, path in PREPS.items():
        uv, _weld = _tuples(path.read_text(encoding="utf-8"))
        for name in ("SIGNPLATE", "SIGNPLATE_w16", "SIGNARROW", "SIGNPOST", "SIGNS", "USSIGN", "EUROSIGN", "FWSIGN",
                     "LIGHTPOST", "LIGHTS", "1ROAD_road", "1GRASS_3", "1KERB_sidewalk", "MARKINGS", "YLINE"):
            assert not name.upper().startswith(uv), (which, name)


def test_signface_is_the_only_name_added_to_either_list():
    """against the commit this branch left main at: each prep's two lists are main's plus SIGNFACE, nothing else moved
    in or out. Skipped where git or the merge base is not there (a tarball, a shallow checkout)."""
    try:
        base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return
    if not base:
        return
    for which, path in PREPS.items():
        old = subprocess.run(["git", "show", f"{base}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=30)
        if old.returncode != 0:
            return
        o_uv, o_weld = _tuples(old.stdout)
        n_uv, n_weld = _tuples(path.read_text(encoding="utf-8"))
        if "SIGNFACE" in o_uv:
            continue                        # main already carries the rule (this branch has landed): nothing to compare
        assert [k for k in n_uv if k != "SIGNFACE"] == list(o_uv), which
        assert [k for k in n_weld if k != "SIGNFACE"] == list(o_weld), which


def test_the_sign_texture_tools_note_still_names_the_problem_this_closes():
    """tools/make_sign_textures.py (the assets session's file, not edited here) says a plate needs the prep to exempt
    its prefix; the prefix it gets is SIGNFACE, and docs/INVENTORY.md says so beside the mesh-name table"""
    doc = (ROOT / "docs" / "INVENTORY.md").read_text(encoding="utf-8")
    assert "SIGNFACE" in doc and "pbr.TEXTURES" in doc
