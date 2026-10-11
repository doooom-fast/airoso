"""The race-furniture kn5's CONTENT guard (ledger 0047) — tools/ship_sd.sh runs it right after the race
export, on scripts/modkit/inspect_kn5.py's --json of build/<slug>_race.kn5:

    python -m scripts.modkit.inspect_kn5 <slug>_race.kn5 --json <file>   (the parse)
    python tools/check_race_kn5.py <file>                                (this gate: exit 1 on a FAIL)

It replaces the 20 MB SIZE heuristic ("the split leaked road geometry or textures into it"), which
fired on the 2026-10-11 rehearsal for a kn5 that leaked nothing: 36 meshes, all 1WALL_RACE* /
1KERB_RACE*, only the race textures — 35.6 MB because the flat-shaded strips exported one vertex per
triangle corner (719,576 v / 241,190 tri). Size says nothing about a leak; content does:

  every mesh   upper-case name starts with 1WALL_RACE or 1KERB_RACE (race_furniture.RACE_PREFIXES —
               the prefixes the split keys on); at least one mesh
  every texture is one of the race set: the diffuse / normal files of scripts/ac/pbr.py's TEXTURES rows
               whose key starts with 1WALL_RACE or 1KERB_RACE (read from the table, never restated:
               kerb_diffuse.png, concrete_barrier_diffuse.png, concrete_barrier_normal.png today)
  no node      named AC_* (mesh or transform): spawns ride in the per-layout spawn kn5s (L8 as amended)

The size is printed with the vertex / triangle totals and their ratio; above 20 MB it is a WARN (a
lost-shading regression reads as ~3 verts per triangle again), never the gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")   # tools/race_furniture.RACE_PREFIXES (verify_race pins the same tuple)
SIZE_WARN_B = 20_000_000
AC_PREFIX = "AC_"


def race_texture_set(textures: dict | None = None) -> set[str]:
    """the texture files the race rows of scripts/ac/pbr.py TEXTURES bind (diffuse + normal, None skipped)"""
    if textures is None:
        if str(AIROSO) not in sys.path:
            sys.path.insert(0, str(AIROSO))
        from scripts.ac import pbr
        textures = pbr.TEXTURES
    out = set()
    for key, row in textures.items():
        if key.upper().startswith(RACE_PREFIXES):
            out |= {f for f in row[:2] if f}
    return out


def check(parsed: dict, allowed: set[str], size_warn_b: int = SIZE_WARN_B) -> dict:
    """{ok, fails, warns, summary} for one inspect_kn5 parse of the race kn5"""
    fails, warns = [], []
    meshes = parsed.get("meshes") or []
    names = [m.get("name", "") for m in meshes]
    if not meshes:
        fails.append("no mesh in the race kn5")
    leak = [n for n in names if not n.upper().startswith(RACE_PREFIXES)]
    if leak:
        fails.append(f"{len(leak)} non-race meshes (not 1WALL_RACE* / 1KERB_RACE*): {leak[:8]}")
    tex = [t.get("name", "") for t in parsed.get("textures") or []]
    alien = [t for t in tex if t not in allowed]
    if alien:
        fails.append(f"{len(alien)} textures outside the race set {sorted(allowed)}: {alien[:8]}")
    ac = sorted(n for n in list(parsed.get("nodes") or []) + names if n.startswith(AC_PREFIX))
    if ac:
        fails.append(f"{len(ac)} AC_* nodes (spawns belong in the per-layout spawn kn5s): {ac[:8]}")
    if "nodes" not in parsed:
        fails.append("the parse carries no transform-node list (scripts/modkit/inspect_kn5.py too old to prove 0 AC_* nodes)")
    verts = sum(int(m.get("verts", 0)) for m in meshes)
    tris = sum(int(m.get("tris", 0)) for m in meshes)
    size = int(parsed.get("file_bytes", 0) or 0)
    if size >= size_warn_b:
        warns.append(f"race kn5 is {size:,} B (>= {size_warn_b:,}) — size is not the gate; look at the vertex count "
                     f"({verts / max(1, tris):.2f} per triangle; ~0.8 smooth-shaded, 3.0 when the shading is lost)")
    summary = {"file_bytes": size, "meshes": len(meshes), "verts": verts, "tris": tris,
               "verts_per_tri": round(verts / max(1, tris), 3), "textures": tex, "nodes": list(parsed.get("nodes") or []),
               "max_mesh_verts": max([int(m.get("verts", 0)) for m in meshes] or [0])}
    return {"ok": not fails, "fails": fails, "warns": warns, "summary": summary}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        raise SystemExit("usage: python tools/check_race_kn5.py <inspect_kn5 --json output of build/<slug>_race.kn5>")
    p = Path(argv[0])
    parsed = json.loads(p.read_text(encoding="utf-8"))
    allowed = race_texture_set()
    r = check(parsed, allowed)
    s = r["summary"]
    print(f"[race-kn5] {Path(parsed.get('file', p)).name}: {s['file_bytes']:,} B; {s['meshes']} meshes (max {s['max_mesh_verts']:,} v), "
          f"{s['verts']:,} v / {s['tris']:,} tri = {s['verts_per_tri']} per triangle; textures {s['textures']}; nodes {s['nodes']}")
    for w in r["warns"]:
        print(f"[race-kn5] WARN {w}")
    for f in r["fails"]:
        print(f"[race-kn5] FAIL {f}")
    print(f"[race-kn5] {'OK' if r['ok'] else 'FAILED'}: only RACE meshes, only the race textures {sorted(allowed)}, no AC_* node"
          if r["ok"] else "[race-kn5] FAILED — the split leaked into the race kn5")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
