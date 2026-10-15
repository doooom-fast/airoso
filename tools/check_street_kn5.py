"""The STREET-ONLY kn5's content guard (ledger 0055) — tools/ship_sd.sh runs it right after the export, on
scripts/modkit/inspect_kn5.py's --json of <slug>_street.kn5:

    python -m scripts.modkit.inspect_kn5 <slug>_street.kn5 --json <file>
    python tools/check_street_kn5.py <file>                                     (exit 1 on a FAIL)

<slug>_street.kn5 holds what stands in the street layout ONLY: the median island over each declared chicane's span
(track.config.json race.chicanes, street_only_island; tools/author_median_blend.py authors it, tools/
split_exports_blend.py routes it by name). Every non-race layout loads it beside the road kn5; no race layout does
(scripts/ac/track_folder.py, verified by scripts/ac/verify_kn5.py --inis). The guard:
  * at least one mesh, and EVERY mesh name carries scripts/geometry/race_chicane.STREET_TAG (a road, race or
    closure mesh here would be doubled in Free Roam or missing from a Speedway);
  * no node named AC_* (spawns ride in the per-layout spawn kn5s, L8 as amended);
  * every material binds a txDiffuse that is EMBEDDED with > 0 bytes (a texture-less kn5 material renders black, L7);
  * every mesh under the 65,535-vertex cap; no non-power-of-two texture (L7).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
VERT_CAP = 65535


def _race_chicane():
    spec = importlib.util.spec_from_file_location("_race_chicane_csk", AIROSO / "scripts" / "geometry" / "race_chicane.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(parsed: dict) -> dict:
    """{ok, fails, summary} for one inspect_kn5 parse of a street-only kn5"""
    rc = _race_chicane()
    fails = []
    meshes = parsed.get("meshes") or []
    if not meshes:
        fails.append("no mesh — an empty street-only kn5")
    alien = [m["name"] for m in meshes if not rc.is_street_only_name(m["name"])]
    if alien:
        fails.append(f"{len(alien)} meshes are not street-only (no {rc.STREET_TAG!r} in the name): {alien[:4]}")
    ac = [n for n in (parsed.get("nodes") or []) if str(n).upper().startswith("AC_")]
    if ac:
        fails.append(f"AC_* nodes in a street-only kn5: {ac[:4]}")
    tex = {t["name"]: int(t.get("bytes") or 0) for t in parsed.get("textures") or []}
    for mat in parsed.get("materials") or []:
        slots = dict((s[0], s[1]) for s in mat.get("textures") or [])
        d = slots.get("txDiffuse")
        if not d:
            fails.append(f"material {mat['name']} binds no txDiffuse (renders black)")
        elif tex.get(d, 0) <= 0:
            fails.append(f"material {mat['name']} binds {d}, which is not embedded (renders black)")
    over = [m["name"] for m in meshes if int(m.get("verts") or 0) > VERT_CAP]
    if over:
        fails.append(f"meshes over the {VERT_CAP}-vertex cap: {over}")
    npot = (parsed.get("summary") or {}).get("non_pot_textures") or []
    if npot:
        fails.append(f"non-power-of-two textures: {npot}")
    summ = {"meshes": len(meshes), "verts": sum(int(m.get("verts") or 0) for m in meshes),
            "tris": sum(int(m.get("tris") or 0) for m in meshes), "textures": sorted(tex),
            "surfaces": sorted({str(m.get("surface")) for m in meshes}), "file_bytes": parsed.get("file_bytes")}
    return {"ok": not fails, "fails": fails, "summary": summ}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python tools/check_street_kn5.py <inspect_kn5 --json output>")
        return 2
    parsed = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    r = check(parsed)
    s = r["summary"]
    print(f"[street-kn5] {Path(str(parsed.get('file') or argv[0])).name}: {s['meshes']} meshes, {s['verts']} verts, "
          f"{s['tris']} tris, surfaces {s['surfaces']}, textures {s['textures']} — {'OK' if r['ok'] else 'FAIL'}")
    for f in r["fails"]:
        print(f"[street-kn5] FAIL: {f}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
