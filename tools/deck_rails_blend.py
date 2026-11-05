"""Deck rails on the line's declared decks, Lake Murray's own I-8 bridge rails (ledger 0080, the SD freeway port).

drive_test's own rule (scripts/geometry/drive_test.py, the declared-span note): "a bridge with no railing is the defect,
not the railing". Lake Murray lays its deck rails in the assembler (scripts-v021 build_loop_blend.build_guardrails:
0.95 m double-sided panels GUARDRAIL_SET_M outside both lane edges wherever the lap is within 22 m of its I-8 polyline,
dilated 3 points onto the approaches). That keys on Lake Murray's data/i8.local.json, which a port has none of (and
which would also cut Lake Murray's I-8 trench). This step calls THE SAME function, unchanged, once per declared deck,
with that deck's own stretch of the line standing in for the I-8 polyline: so the rails run over each deck, 22 m past
its ends plus 3 points, exactly as Lake Murray's run past its I-8 cut. Heights and set are Lake Murray's (0.95 m,
0.15 m), not measured here.

The decks: data/lm_intake.json bridges_levelled ([center_m, len_m] on the draft line, the source's capture.bridges),
put on the assembler's smoothed line by index (v021's smoother keeps the point count; stations from the raw snapshot
data/centerline.raw.local.json, the line the decks were keyed to). The mesh is GUARDRAIL (engine-july's AC_NAME ->
1WALL_guard, double-sided as Lake Murray's), written into loop.blend. No declared deck = nothing written.

Opt-in by ship.json step (`deck_rails`, draft); Lake Murray never names it (its assembler lays its own).

    blender --background --python tools/deck_rails_blend.py -- <project-dir>
"""
from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: provided by Blender

AIROSO = Path(__file__).resolve().parents[1]
ASM = AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "blender" / "build_loop_blend.py"


def _assembler(*names):
    tree = ast.parse(ASM.read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns = {"json": json, "math": math, "bpy": bpy}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(ASM), "exec"), ns)
    return ns


def _network_connector_decks(data: Path):
    """[(name, smoothed points, widths, decks_all ranges)] of the network connectors (ledger 0080 phase 2); [] without."""
    p = data / "connectors.local.json"
    if not p.exists():
        return []
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "v021_smooth", AIROSO / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    out = []
    for c in json.loads(p.read_text(encoding="utf-8")).get("connectors") or []:
        if not c.get("network") or not c.get("decks_all"):
            continue
        cpts = sm.smooth_centerline([tuple(q) for q in c["points_xyz_m"]], sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
        out.append((c["name"], [tuple(q) for q in cpts], list(c["widths_m"]), c["decks_all"]))
    return out


def main():
    proj = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    data = proj / "data"
    rep = json.loads((data / "lm_intake.json").read_text(encoding="utf-8"))
    decks = rep.get("bridges_levelled") or []
    net = _network_connector_decks(data)
    if not decks and not net:
        print("[deck-rails] no declared deck: nothing written")
        return
    raw = json.loads((data / "centerline.raw.local.json").read_text(encoding="utf-8"))["points_xyz_m"]
    loc = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    cl = [tuple(p) for p in loc["points_xyz_m"]]
    widths = loc["widths_m"]
    if len(raw) != len(cl):
        raise SystemExit(f"[deck-rails] FATAL: the smoothed line has {len(cl)} points, its raw snapshot {len(raw)}")
    st = [0.0]
    for a, b in zip(raw, raw[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    # on a flare (the intake's width_taper widens a step over metres) the pavement edge between two rows is a chord,
    # and a panel set from each row's own half-width crosses it where the next row is wider (drive_test's wheel paths
    # met the panel at s 1,336-1,341 and 3,358-3,364): each row takes the widest of itself and its two neighbours, so
    # the rail stands outside the pavement over the whole flare (at most one row's widening further out)
    wr = [max(widths[max(0, k - 1):k + 2]) for k in range(len(widths))]
    asm = _assembler("_i8_nearest", "build_guardrails", "GUARDRAIL_SET_M", "make_mesh")
    out = {"vertices": [], "uvs": [], "tris": []}
    rows = []
    for c, ln in decks:
        a, b = float(c) - float(ln) / 2.0, float(c) + float(ln) / 2.0
        idx = [i for i, s in enumerate(st) if a <= s <= b]
        if len(idx) < 2:
            rows.append({"center_m": c, "len_m": ln, "panels": 0})
            continue
        stretch = [cl[i] for i in idx]
        g = asm["build_guardrails"](cl, wr, stretch)
        off = len(out["vertices"])
        out["vertices"] += g["vertices"]
        out["tris"] += [(p + off, q + off, r + off) for p, q, r in g["tris"]]
        rows.append({"center_m": c, "len_m": ln, "panels": len(g["tris"]) // 4})
    # ledger 0080 phase 2: each network connector's decks (tools/network_connectors.py decks_all: measured or levelled),
    # the same call on the connector as the assembler sweeps it (its smoothed points, its widths widest-of-three)
    for name, cpts, cw, ranges in net:
        cwr = [max(cw[max(0, k - 1):k + 2]) for k in range(len(cw))]
        for a, b in ranges:
            stretch = cpts[a:b + 1]
            if len(stretch) < 2:
                continue
            g = asm["build_guardrails"](cpts, cwr, stretch)
            off = len(out["vertices"])
            out["vertices"] += g["vertices"]
            out["tris"] += [(p + off, q + off, r + off) for p, q, r in g["tris"]]
            rows.append({"connector": name, "vertices": [a, b], "panels": len(g["tris"]) // 4})
    bpy.ops.wm.open_mainfile(filepath=str(proj / "loop.blend"))
    old = bpy.data.objects.get("GUARDRAIL")
    if old is not None:
        raise SystemExit("[deck-rails] FATAL: loop.blend already has a GUARDRAIL (the assembler's I-8 rails): not a port")
    asm["make_mesh"]("GUARDRAIL", out, (0.82, 0.82, 0.86, 1.0))
    bpy.ops.wm.save_as_mainfile(filepath=str(proj / "loop.blend"))
    (data / "deck_rails.json").write_text(json.dumps({"tool": "tools/deck_rails_blend.py", "ledger": "0080",
                                                      "height_m": 0.95, "set_m": asm["GUARDRAIL_SET_M"],
                                                      "decks": rows}, indent=1), encoding="utf-8")
    print(f"[deck-rails] {sum(r['panels'] for r in rows)} rail panels on {len(decks)} declared deck(s) "
          f"(Lake Murray's build_guardrails, 0.95 m, set {asm['GUARDRAIL_SET_M']} m): saved loop.blend")


main()
