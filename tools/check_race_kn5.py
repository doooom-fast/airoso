"""The race-furniture kn5s' CONTENT guard (ledgers 0047 + 0049) — tools/ship_sd.sh runs it right after each
race export, on scripts/modkit/inspect_kn5.py's --json of the file:

    python -m scripts.modkit.inspect_kn5 <kn5> --json <file>                     (the parse)
    python tools/check_race_kn5.py <file> --role common                          (<slug>_race.kn5)
    python tools/check_race_kn5.py <file> --role closure --owner <token>         (<slug>_closure_<layout>.kn5)
        [--bands <barrier_bands.json>] [--expect-kerbs N]                        (exit 1 on a FAIL)

Since ledger 0049 the race layouts load TWO furniture kn5s each: the COMMON <slug>_race.kn5 (both curb strips as
closed loops + the race kerbs, identical for race_cw and race_acw) and their OWN <slug>_closure_<id>.kn5 (that
direction's closure). Which file a mesh belongs in is decided by its name (race_furniture.race_owner):

  --role common   every mesh upper-case starts with 1WALL_RACE / 1KERB_RACE; NONE is a closure
                  (1WALL_RACE_CLOSE_*) or the retired centre chain (1WALL_RACE_KBAR_*); at least one curb strip
                  (1WALL_RACE_EDGE_*); exactly the declared number of race kerbs (1KERB_RACE_*: --expect-kerbs, else
                  len(kerbs) of --bands, else of the barrier_bands.json beside the parse when there is one — 10 on SD)
  --role closure  every mesh is 1WALL_RACE_CLOSE_<OWNER>_* (no kerb, no curb strip, no other layout's closure);
                  at least one
  both roles      every texture is one of the race set (the diffuse / normal files of scripts/ac/pbr.py's TEXTURES
                  rows whose key starts with 1WALL_RACE or 1KERB_RACE — read from the table, never restated); no node
                  named AC_* (spawns ride in the per-layout spawn kn5s, L8 as amended)

The size is printed with the vertex / triangle totals and their ratio; above 20 MB it is a WARN (a
lost-shading regression reads as ~3 verts per triangle again), never the gate. `check(parsed, allowed)` with no
role is the role-free content guard (RACE meshes, race textures, no AC_* node) the ledger-0047 chain ran.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
RACE_PREFIXES = ("1WALL_RACE", "1KERB_RACE")   # tools/race_furniture.RACE_PREFIXES (verify_race pins the same tuple)
EDGE_TAG, CLOSE_TAG, KBAR_TAG, KERB_TAG = "1WALL_RACE_EDGE_", "1WALL_RACE_CLOSE_", "1WALL_RACE_KBAR_", "1KERB_RACE_"
SIZE_WARN_B = 20_000_000
AC_PREFIX = "AC_"
ROLES = ("common", "closure")


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


def check(parsed: dict, allowed: set[str], size_warn_b: int = SIZE_WARN_B, *, role: str | None = None,
          owner: str | None = None, expect_kerbs: int | None = None) -> dict:
    """{ok, fails, warns, summary} for one inspect_kn5 parse of a race-furniture kn5 (see the module doc for the roles)"""
    fails, warns = [], []
    if role is not None and role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}, got {role!r}")
    meshes = parsed.get("meshes") or []
    names = [m.get("name", "") for m in meshes]
    upper = [n.upper() for n in names]
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
    kerbs = [n for n, u in zip(names, upper) if u.startswith(KERB_TAG)]
    edges = [n for n, u in zip(names, upper) if u.startswith(EDGE_TAG)]
    closes = [n for n, u in zip(names, upper) if u.startswith(CLOSE_TAG)]
    kbar = [n for n, u in zip(names, upper) if u.startswith(KBAR_TAG)]
    if role == "common":
        if closes:
            fails.append(f"{len(closes)} closure meshes in the COMMON kn5 (each belongs in its layout's "
                         f"<slug>_closure_<id>.kn5 — loading it here would block the other direction): {closes[:4]}")
        if kbar:
            fails.append(f"{len(kbar)} retired centre-chain meshes (1WALL_race_kbar_*, ledger 0049): {kbar[:4]}")
        if not edges:
            fails.append("no curb strip (1WALL_RACE_EDGE_*) in the common kn5")
        if expect_kerbs is None:
            warns.append(f"the kerb count is not pinned (no --expect-kerbs / --bands): {len(kerbs)} 1KERB_RACE_* meshes")
            if not kerbs:
                fails.append("no race kerb (1KERB_RACE_*) in the common kn5")
        elif len(kerbs) != int(expect_kerbs):
            fails.append(f"{len(kerbs)} race kerbs (1KERB_RACE_*), the declaration has {int(expect_kerbs)}")
    elif role == "closure":
        tok = str(owner or "").lower()
        if not tok:
            fails.append("--role closure needs --owner <token>")
        want = f"{CLOSE_TAG}{tok.upper()}_"
        wrong = [n for n, u in zip(names, upper) if not u.startswith(want)]
        if wrong:
            fails.append(f"{len(wrong)} meshes that are not {tok!r}'s closure ({want}*) — a kerb, a curb strip or another "
                         f"layout's closure leaked into it: {wrong[:6]}")
        if not [u for u in upper if u.startswith(want)]:
            fails.append(f"no {want}* mesh — the {tok!r} closure kn5 is empty")
    verts = sum(int(m.get("verts", 0)) for m in meshes)
    tris = sum(int(m.get("tris", 0)) for m in meshes)
    size = int(parsed.get("file_bytes", 0) or 0)
    if size >= size_warn_b:
        warns.append(f"race kn5 is {size:,} B (>= {size_warn_b:,}) — size is not the gate; look at the vertex count "
                     f"({verts / max(1, tris):.2f} per triangle; ~0.8 smooth-shaded, 3.0 when the shading is lost)")
    summary = {"file_bytes": size, "meshes": len(meshes), "verts": verts, "tris": tris,
               "verts_per_tri": round(verts / max(1, tris), 3), "textures": tex, "nodes": list(parsed.get("nodes") or []),
               "max_mesh_verts": max([int(m.get("verts", 0)) for m in meshes] or [0]),
               "role": role, "owner": owner, "edges": len(edges), "kerbs": len(kerbs), "closures": len(closes)}
    return {"ok": not fails, "fails": fails, "warns": warns, "summary": summary}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    usage = ("usage: python tools/check_race_kn5.py <inspect_kn5 --json output> [--role common|closure] "
             "[--owner <token>] [--bands <barrier_bands.json>] [--expect-kerbs N]")
    role, owner, bands_p, expect = "common", None, None, None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--role", "--owner", "--bands", "--expect-kerbs") and i + 1 >= len(argv):
            raise SystemExit(usage)
        if a == "--role":
            role = argv[i + 1]; i += 2
        elif a == "--owner":
            owner = argv[i + 1]; i += 2
        elif a == "--bands":
            bands_p = Path(argv[i + 1]); i += 2
        elif a == "--expect-kerbs":
            expect = int(argv[i + 1]); i += 2
        else:
            rest.append(a); i += 1
    if len(rest) != 1 or role not in ROLES:
        raise SystemExit(usage)
    p = Path(rest[0])
    parsed = json.loads(p.read_text(encoding="utf-8"))
    if role == "common" and expect is None:
        bp = bands_p or (p.parent / "barrier_bands.json")
        if bp.exists():
            expect = len(json.loads(bp.read_text(encoding="utf-8")).get("kerbs") or [])
    allowed = race_texture_set()
    r = check(parsed, allowed, role=role, owner=owner, expect_kerbs=expect)
    s = r["summary"]
    what = "COMMON" if role == "common" else f"CLOSURE {owner!r}"
    print(f"[race-kn5] {Path(parsed.get('file', p)).name} ({what}): {s['file_bytes']:,} B; {s['meshes']} meshes "
          f"({s['edges']} curb strips, {s['kerbs']} kerbs, {s['closures']} closure; max {s['max_mesh_verts']:,} v), "
          f"{s['verts']:,} v / {s['tris']:,} tri = {s['verts_per_tri']} per triangle; textures {s['textures']}; nodes {s['nodes']}")
    for w in r["warns"]:
        print(f"[race-kn5] WARN {w}")
    for f in r["fails"]:
        print(f"[race-kn5] FAIL {f}")
    if r["ok"]:
        print(f"[race-kn5] OK: {what} meshes only, textures {sorted(s['textures'])} all within the race set "
              f"{sorted(allowed)}, no AC_* node")
    else:
        print(f"[race-kn5] FAILED — the split leaked into the {what} kn5")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
