# scripts/diag — measurement tools for road-float work

Read-only probes over a **built** `data/track.obj`. They exist because `kn5_ground_check` reports one
aggregate number and a failing p95 tells you nothing about *which* geometry is failing. Nothing here
runs in a build or gates anything; they answer "where is the float, and what is holding that node
down" so a fix is aimed rather than guessed (L12 — show, don't assert).

Written for ledger **0019** (a divided street loses its embankment) and still the right instruments
for its open item: `kn5_ground_check` p95 0.198 m against a 0.100 m gate on Lake Murray, entirely on
connectors.

| script | question it answers |
|---|---|
| `gate_tail_by_group.py <obj>` | which `1ROAD_*` group owns the gate's failing tail — counts over 0.05/0.10 per group, mirrors the gate's stride-7 sampling |
| `deck_float_by_group.py <obj> [stride]` | per-group median/p95/max deck-over-grass gap, and where each group's worst sample is |
| `deck_float_window.py <obj> <group> <x> <z> <radius>` | every deck vertex in one XZ window, its gap, and whether another road's deck sits underneath (i.e. whether the gate would exempt it) |
| `what_covers_point.py <obj> <x> <z> [spread]` | every mesh group with a triangle over one point, by name and height — "which sheet is holding this node down" |

The build-time counterpart is `scripts/geometry/nodedbg.py`: arm it with `NODEDBG="<x>,<z>"` to trace
one grid node's height through every write between `grade_embankment` and `grass_terrain`, with the
source line that wrote it. Use these to find *where*, then NODEDBG to find *why*:

```bash
python3 -m scripts.diag.gate_tail_by_group <proj>/data/track.obj      # which group
python3 -m scripts.diag.deck_float_window <proj>/data/track.obj 1ROAD_del_cerro_blvd -702 -865.5 30
python3 -m scripts.diag.what_covers_point <proj>/data/track.obj -702.367 -865.566
NODEDBG="-702,-865.5" NODEDBG_STOP=1 python3 -m scripts.geometry.build_mesh <proj>
```

They parse the whole OBJ into memory (~860 MB file, a few minutes on Lake Murray). Fine for a
debugging loop, not for anything on the build path.
