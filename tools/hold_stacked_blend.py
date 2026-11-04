"""The stacked-leg hold again on the PREPPED ground, before the split (ledger 0078 round 7).

tools/cutfill_blend.py grades the draft's ground to the road's section and holds every point between stacked legs on its
own leg's side of the midpoint height (scripts/geometry/cutfill.py, ownership read as tools/verify_stacked_legs.py reads
it). engine-july's prep then splits every ground edge over 4.5 m (3-D) within 16 m of a road at its midpoint. The hold is
discontinuous at the medial line between two legs (one side held under the midpoint, the other over it), so an edge that
crosses it can be split again and again and stay long: cutfill pre-splits what it can (the prep's own predicate, by
bisection), and on the Lariat a few hundred long edges still cross the medial line between the climb's legs. Their
midpoints, the average of a held-low and a held-high end, are what the gate read as ground seated to the other leg
(round 7, run 4: 26). The prep's pin, contact band and feather move a point toward its nearest road, never across the
midline; only those split midpoints do.

So the hold runs once more after the prep, on its 1GRASS tiles, from the very line cutfill graded on
(data/cutfill.line.json): a ground vertex between stacked legs on the wrong side of the midpoint height goes back to its
own side by the section's margin (0.3 m). Nothing else moves: the hold leaves a point already on its own side where it
is, so the pinned, banded and feathered ground beside each road stays exactly as the prep put it. Opt-in: the prep step
`hold_stacked` (ship.json steps.prep, between prep and split) and terrain.cross_section.build true; Lake Murray never runs
it. Self-check (exit 1, the blend not saved): no data/cutfill.line.json (cutfill did not run).

    blender --background --python-exit-code 1 --python tools/hold_stacked_blend.py -- <prepped.blend> --project <dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.geometry import cutfill  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend = Path(argv[0])
    proj = Path(argv[argv.index("--project") + 1])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    if not cutfill.section_enabled(cfg):
        print("[hold] terrain.cross_section.build is not true: nothing to do")
        return
    lp = proj / "data" / "cutfill.line.json"
    if not lp.exists():
        raise SystemExit("[hold] FATAL: no data/cutfill.line.json (the draft step cutfill did not run)")
    rec = json.loads(lp.read_text(encoding="utf-8"))
    xs = (cfg.get("terrain") or {}).get("cross_section") or {}
    decks = [tuple(d) for d in rec.get("decks") or []]
    cs = cutfill.CrossSection([tuple(q) for q in rec["line"]], rec["widths"], verge_m=float(rec["verge_m"]),
                              fill_bench_m=float(xs.get("fill_bench_m", 0.0) or 0.0),
                              cut_bench_m=float(xs.get("cut_bench_m", 0.0) or 0.0),
                              cut_hv=cutfill.parse_ratio(xs.get("rock_cut_slope"), 0.25),
                              fill_hv=cutfill.parse_ratio(xs.get("fill_slope"), 1.5),
                              clearance=0.02, bank_at=None,
                              bridge_of=(lambda st: any(a <= st <= b for a, b in decks)) if decks else None)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    moved = {}
    worst = 0.0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.upper().startswith("1GRASS"):
            continue
        mw = ob.matrix_world
        inv = mw.inverted()
        n = 0
        for v in ob.data.vertices:
            w = mw @ v.co
            g = cs.hold(w.x, w.y, w.z, count=True)
            if abs(g - w.z) > 1e-6:
                worst = max(worst, abs(g - w.z))
                w.z = g
                v.co = inv @ w
                n += 1
        if n:
            ob.data.update()
            moved[ob.name] = n
    print(f"[hold] {sum(moved.values())} ground vertices between stacked legs held back to their own leg's side "
          f"(largest move {worst:.2f} m) {dict(cs.stats)} in {moved}; saved {blend.name}")
    bpy.ops.wm.save_mainfile(filepath=str(blend))


main()
