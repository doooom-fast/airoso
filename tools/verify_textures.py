"""Does every visible mesh the track ships wear a texture? (ledger 0079, Kevin 2026-11-04: "Add textures" / nothing ships
with AC's default look.)

READ-ONLY on the BUILT kn5s (L5): the road kn5 and every other kn5 the track folder packs (street-only, race, closures;
the spawn kn5s carry nodes only). For each renderable mesh with vertices, its material must bind a txDiffuse slot whose
texture is EMBEDDED in that kn5 with bytes in it. A material with no diffuse renders black or in AC's flat default (LAWS L7:
"every material needs a texture"); engine-july's pbr gives a name with no TEXTURES row no texture at all, so a new
object prefix that misses the table is caught here, not in the game.

    python tools/verify_textures.py <project> [--json <out>]

Exit 1 when any visible mesh's material lacks an embedded diffuse; 0 otherwise; 2 on an input error. The threshold is 0
(no untextured visible mesh): a rule, not a tuned number.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.modkit.inspect_kn5 import parse_stats  # noqa: E402


def check(kn5: Path) -> dict:
    p = parse_stats(kn5)
    tex = {t["name"]: t["bytes"] for t in p["textures"]}
    mats = p["materials"]
    bad, seen_mats, n_vis = [], set(), 0
    for m in p["meshes"]:
        if not m.get("renderable", True) or not m["verts"]:
            continue
        n_vis += 1
        mat = mats[m["matid"]] if 0 <= m["matid"] < len(mats) else None
        if mat is None:
            bad.append({"mesh": m["name"], "why": f"material index {m['matid']} out of range"})
            continue
        seen_mats.add(mat["name"])
        diff = [t for s, t in mat["textures"] if s == "txDiffuse"]
        if not diff:
            bad.append({"mesh": m["name"], "material": mat["name"], "why": "no txDiffuse slot"})
        elif not tex.get(diff[0]):
            bad.append({"mesh": m["name"], "material": mat["name"], "why": f"txDiffuse {diff[0]!r} not embedded"})
    return {"kn5": kn5.name, "mb": round(kn5.stat().st_size / 1e6, 1), "visible_meshes": n_vis,
            "materials_used": len(seen_mats), "textures": len(tex),
            "texture_mb": round(sum(tex.values()) / 1e6, 1), "untextured": bad}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = None
    if "--json" in argv:
        i = argv.index("--json"); out = Path(argv[i + 1]); del argv[i:i + 2]
    if len(argv) != 1:
        print(__doc__)
        return 2
    proj = Path(argv[0])
    try:
        slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    except (OSError, KeyError, ValueError) as e:
        print(f"[textures] cannot read the project's slug: {e}")
        return 2
    folder = proj / "build" / slug
    kn5s = sorted(folder.glob("*.kn5")) if folder.is_dir() else []
    if not kn5s:
        print(f"[textures] no kn5 in {folder}")
        return 2
    rows = [check(k) for k in kn5s]
    total = sum(len(r["untextured"]) for r in rows)
    for r in rows:
        if not r["visible_meshes"]:
            continue
        print(f"[textures] {r['kn5']}: {r['mb']} MB, {r['visible_meshes']} visible meshes, {r['materials_used']} materials, "
              f"{r['textures']} textures embedded ({r['texture_mb']} MB), untextured {len(r['untextured'])}")
        for b in r["untextured"][:12]:
            print(f"    {b['mesh']}: {b.get('material', '')} {b['why']}")
    rep = {"_doc": "tools/verify_textures.py (ledger 0079): every visible mesh of every packed kn5 binds an embedded diffuse",
           "kn5": rows, "untextured": total, "fail": total > 0}
    if out:
        out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[textures] {'FAIL' if total else 'PASS'}: {total} visible mesh(es) without an embedded diffuse")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
