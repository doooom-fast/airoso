"""One CSP light per lamp, at its lens — a hard check on the WRITTEN ext_config.ini (ledger 0054 P4 step 2).

scripts/ac/ext_config.py clusters the exported LIGHTS mesh's vertices into one [LIGHT_N] per lens. v0.18.0 shipped 4
coincident pairs from that clustering (ledger 0043 / 0056's duplicate class); the P4 lamps grow the list from 238 to
~320, so the written file is read back and refused unless:
  * the [LIGHT_N] count equals the lamp count (data/lights.local.json lampheads);
  * every [LIGHT_N] POSITION stands within POS_TOL_M of exactly one recorded lens (lights.local.json
    provenance.lens_xyz, local frame; the kn5 frame negates z; POSITION y = lens y - LIGHT_DROP_M), and every lens has
    its light — no duplicate, no orphan, no light off a lens;
  * every light keeps the approved look (ledger 0043 / 0056): COLOR, SPOT, RANGE, RANGE_GRADIENT_OFFSET,
    SPECULAR_MULT as track.config.json lighting.streetlight writes them — the same on every block.
BOTH HEADS (ledger 0099, opt-in: scenery.streetlights.light_both_heads true): tools/author_lamp_heads_blend.py gave every
two-arm lamp a back lens (data/lights.heads.json back_lens_xyz, local frame, lens_xyz's order), so the file must hold one
light at every front AND every back lens: 2 per lamp. The key set and the heads file missing is a FAIL; the key absent =
exactly the one-per-lamp check above.
BOTH HEADS BY THE LAMPS STEP (ledger 0098, opt-in: light_both_heads true WITH scenery.streetlights.both_heads_by "lamps";
Sand Creek): tools/author_lamps_blend.py laid both lenses itself, recorded in provenance.lens_xyz with heads_lit 2, so the
count is the lamp count times heads_lit and NO heads file is wanted; heads_lit not 2 there is a FAIL. The same key was
written twice in two rounds (2026-11-22); both_heads_by tells the two apart until Sand Creek's round 2 moves onto
lamp_heads. No tolerance, count rule or matching rule differs between the two paths.
Pure python; exit 1 with the first problems named.

    PYTHONUTF8=1 python tools/check_lights_ini.py <project-dir> [--ini <ext_config.ini>] [--json <out>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

POS_TOL_M = 0.05        # a light is "at" its lens within this (the writer rounds POSITION to 0.01 m)
LIGHT_DROP_M = 0.15     # scripts/ac/ext_config.py: POSITION = lens centroid - 0.15 m y
_BLOCK_RE = re.compile(r"^\[LIGHT_(\d+)\]\s*$")


def parse_lights(text: str) -> list[dict]:
    """every [LIGHT_N] block of an ext_config.ini: {n, pos (x, y, z kn5 frame), keys}"""
    out, cur = [], None
    for ln in text.replace("\r\n", "\n").split("\n"):
        s = ln.strip()
        m = _BLOCK_RE.match(s)
        if m:
            cur = {"n": int(m.group(1)), "keys": {}}
            out.append(cur)
            continue
        if s.startswith("[") and s.endswith("]"):
            cur = None
            continue
        if cur is not None and "=" in s and not s.startswith(";"):
            k, v = s.split("=", 1)
            cur["keys"][k.strip().upper()] = v.split(";")[0].strip()
    for b in out:
        p = b["keys"].get("POSITION")
        try:
            b["pos"] = tuple(float(q) for q in p.split(","))
        except (AttributeError, ValueError):
            b["pos"] = None
    return out


def check(lights: dict, blocks: list[dict], streetlight_cfg: dict | None = None, back_lenses: list | None = None) -> dict:
    """the verdict: {ok, n_lamps, n_lights, problems: [...], matched}; ``back_lenses`` (ledger 0099, both heads lit): the
    back heads' lenses, lens_xyz's order — every lamp then wants two lights, one at each of its lenses"""
    heads = lights.get("lampheads") or []
    lenses = ((lights.get("provenance") or {}).get("lens_xyz")) or []
    # ledger 0098 (opt-in at the author: light_both_heads with both_heads_by "lamps"): a lamp may record two lit heads, and
    # then every recorded lens is one light; absent = one per lamp, as before. No tolerance changes
    per = int((lights.get("provenance") or {}).get("heads_lit", 1))
    problems: list[str] = []
    n_lamps, n_lights = len(heads), len(blocks)
    if back_lenses is not None:
        if per != 1:
            problems.append(f"lights.local.json records {per} lit heads AND data/lights.heads.json gives back lenses: "
                            "the back head lit twice (one of both_heads_by \"lamps\" / the lamp_heads step)")
        if len(back_lenses) != n_lamps:
            problems.append(f"data/lights.heads.json has {len(back_lenses)} back lenses for {n_lamps} lamps")
        lenses = list(lenses) + list(back_lenses)
    n_want = n_lamps * per + (len(back_lenses) if back_lenses is not None else 0)
    if n_lights != n_want:
        problems.append(f"{n_lights} [LIGHT_N] blocks for {n_lamps} lamps" + (f" x {per} lit heads" if per != 1 else "")
                        + ("" if back_lenses is None else f" with both heads lit ({n_want} lenses)"))
    nums = [b["n"] for b in blocks]
    if nums != list(range(len(nums))):
        problems.append("[LIGHT_N] numbering is not 0..n-1 in order")
    matched = 0
    if lenses:
        if len(lenses) != n_want:
            if back_lenses is None:
                problems.append(f"provenance.lens_xyz has {len(lenses)} lenses for {n_lamps} lamps"
                                + (f" x {per} lit heads" if per != 1 else ""))
            else:
                problems.append(f"provenance.lens_xyz has {len(lenses) - (n_want - n_lamps * per)} lenses for {n_lamps} lamps")
        # lens -> kn5: (x, y - drop, -z)
        want = [(float(l[0]), float(l[1]) - LIGHT_DROP_M, -float(l[2])) for l in lenses]
        cells: dict[tuple[int, int], list[int]] = {}
        for i, (x, _y, z) in enumerate(want):
            cells.setdefault((int(x // 2.0), int(z // 2.0)), []).append(i)
        taken: dict[int, int] = {}
        for b in blocks:
            if b["pos"] is None or len(b["pos"]) != 3:
                problems.append(f"LIGHT_{b['n']}: no POSITION")
                continue
            x, y, z = b["pos"]
            near = []
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for i in cells.get((int(x // 2.0) + dx, int(z // 2.0) + dz), ()):
                        wx, wy, wz = want[i]
                        if abs(wx - x) <= POS_TOL_M and abs(wz - z) <= POS_TOL_M and abs(wy - y) <= POS_TOL_M:
                            near.append(i)
            if not near:
                problems.append(f"LIGHT_{b['n']} at ({x}, {y}, {z}) stands at no recorded lens")
            elif len(near) > 1:
                problems.append(f"LIGHT_{b['n']} stands at {len(near)} recorded lenses (lamps {near})")
            else:
                i = near[0]
                if i in taken:
                    problems.append(f"LIGHT_{b['n']} and LIGHT_{taken[i]} both stand at lamp {i}'s lens (duplicate light)")
                else:
                    taken[i] = b["n"]
                    matched += 1
        missing = [i for i in range(len(want)) if i not in taken]
        if missing:
            problems.append(f"{len(missing)} lamps have no light at their lens, e.g. {missing[:6]}" if back_lenses is None
                            else f"{len(missing)} lenses have no light, e.g. {missing[:6]} (index >= {n_lamps} = a back head)")
    else:
        problems.append("lights.local.json has no provenance.lens_xyz (the legacy lamp model records no lens): count only")
        problems = [p for p in problems if not p.startswith("lights.local.json has no")] if n_lights == n_lamps else problems
    if streetlight_cfg and blocks:
        c = [round(255 * float(v)) for v in streetlight_cfg.get("color", [1.0, 0.82, 0.55])]
        want_keys = {"COLOR": f"{c[0]}, {c[1]}, {c[2]}, {streetlight_cfg.get('intensity')}",
                     "SPOT": str(streetlight_cfg.get("spot_deg")), "RANGE": str(streetlight_cfg.get("range_m")),
                     "RANGE_GRADIENT_OFFSET": str(streetlight_cfg.get("range_gradient_offset")),
                     "SPECULAR_MULT": str(streetlight_cfg.get("specular_mult"))}
        for k, v in want_keys.items():
            got = {b["keys"].get(k) for b in blocks}
            if len(got) != 1:
                problems.append(f"{k} differs between lights: {sorted(str(g) for g in got)[:4]}")
            elif v != "None" and next(iter(got)) != v:
                problems.append(f"{k} = {next(iter(got))!r} on every light, the config says {v!r}")
    out = {"ok": not problems, "n_lamps": n_lamps, "n_lights": n_lights, "matched": matched, "problems": problems}
    if per != 1:
        out["heads_lit"] = per
    if back_lenses is not None:
        out["both_heads"] = True
        out["n_lenses"] = n_want
    return out


def both_heads_path(cfg: dict) -> str | None:
    """which step lit the back heads: "lamps" (ledger 0098: light_both_heads with both_heads_by "lamps", the draft's lamps
    step), "lamp_heads" (ledger 0099: light_both_heads alone, the author step lamp_heads and its data/lights.heads.json),
    None (one head per lamp)"""
    sl = (cfg.get("scenery") or {}).get("streetlights") or {}
    by = sl.get("both_heads_by")
    if by not in (None, "lamps"):
        raise SystemExit(f"[lights-ini] FAIL: scenery.streetlights.both_heads_by {by!r}: \"lamps\" or absent")
    if sl.get("light_both_heads") is not True:
        if by is not None:
            raise SystemExit("[lights-ini] FAIL: scenery.streetlights.both_heads_by \"lamps\" needs light_both_heads true")
        return None
    return "lamps" if by == "lamps" else "lamp_heads"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--ini", default=None, help="the ext_config.ini (default build/<slug>/extension/ext_config.ini)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    ini = Path(a.ini) if a.ini else proj / "build" / cfg["slug"] / "extension" / "ext_config.ini"
    lamps_p = proj / "data" / "lights.local.json"
    if not lamps_p.exists():
        # no lamps authored (every track but Lake Murray today; ledger 0060, the Exotics run of 2026-10-29 crashed
        # here): nothing to match — and a [LIGHT_N] with no lamp behind it is a stray, refused
        blocks = parse_lights(ini.read_text(encoding="utf-8", errors="replace")) if ini.exists() else []
        problems = [f"{len(blocks)} [LIGHT_N] blocks in {ini.name} but no data/lights.local.json — no lamp authored"] if blocks else []
        r = {"ok": not problems, "n_lamps": 0, "n_lights": len(blocks), "matched": 0, "problems": problems,
             "ini": str(ini), "lamps": None}
        if a.json:
            Path(a.json).write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(f"[lights-ini] no data/lights.local.json — no lamps authored; {len(blocks)} [LIGHT_N] in the ini: "
              f"{'PASS' if r['ok'] else 'FAIL — ' + problems[0]}")
        return 0 if r["ok"] else 1
    lights = json.loads(lamps_p.read_text(encoding="utf-8"))
    if not ini.exists():
        print(f"[lights-ini] FAIL: no {ini}")
        return 1
    blocks = parse_lights(ini.read_text(encoding="utf-8", errors="replace"))
    back = None
    path = both_heads_path(cfg)
    if path == "lamps":
        per = int((lights.get("provenance") or {}).get("heads_lit", 1))
        if per != 2:
            print(f"[lights-ini] FAIL: scenery.streetlights.both_heads_by \"lamps\" but data/lights.local.json records "
                  f"heads_lit {per} (tools/author_lamps_blend.py lays both lenses and records 2)")
            return 1
    elif path == "lamp_heads":
        hp = proj / "data" / "lights.heads.json"
        if not hp.exists():
            print("[lights-ini] FAIL: scenery.streetlights.light_both_heads is set but there is no data/lights.heads.json "
                  "(tools/author_lamp_heads_blend.py, the author step lamp_heads, writes it)")
            return 1
        back = json.loads(hp.read_text(encoding="utf-8")).get("back_lens_xyz") or []
    r = check(lights, blocks, (cfg.get("lighting") or {}).get("streetlight"), back)
    r["ini"] = str(ini)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"[lights-ini] {r['n_lights']} [LIGHT_N] for {r['n_lamps']} lamps"
          + (f" (both heads: {r['n_lenses']} lenses)" if back is not None else "") + f", {r['matched']} at their lens: "
          f"{'PASS' if r['ok'] else 'FAIL'}" + ("" if r["ok"] else " — " + "; ".join(r["problems"][:8])))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
