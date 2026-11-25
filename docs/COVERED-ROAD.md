# A road under a roof: `capture.covered_spans`

*2026-11-23, ledger [0096](../fleet/feedback/0096-denver-grand-prix-and-the-front-range-backdrop.md), Denver Grand Prix
PLAN §4 item 1. Stout St runs 344 m under the Colorado Convention Center (OSM `tunnel=building_passage`, `covered=yes`,
`maxheight=5`).*

A bridge span (`capture.bridges`) is declared so the gates accept what is **below** a deck. A covered span is the same
declaration the other way up: the gates accept what is **above** the road, and only where it is declared. A track that
declares none is read exactly as before; no installed track declares one.

```json
"capture": {
  "covered_spans": [
    {"name": "Stout St under the Colorado Convention Center",
     "center_m": 1712.0, "len_m": 344.0,
     "clear_m": 5.0,
     "source": "OSM way <id>: tunnel=building_passage, covered=yes, maxheight=5"}
  ]
}
```

| Key | Meaning |
|---|---|
| `center_m`, `len_m` | stations along the track's centreline, as `capture.bridges` (required). On a closed lap a span may run through the seam |
| `clear_m` | the real clearance over the road, from a survey. With it written, a roof built lower fails `drive_test` |
| `min_clear_m` | from this height over the road, geometry is the roof's. Default 2.5 m [invented]; under 2.0 m is refused, so nothing inside `drive_test`'s 1.8 m strike ceiling is ever set aside |
| `reach_m` | how far past the road's half-width the roof is taken to run. Default 6.0 m [invented] |
| `name`, `source` | for the report and the reader |

## What the gates do with it

Inside a span's footprint (the centreline between its two stations, **squared off at both ends**, the road's half-width
plus `reach_m` each side), a triangle whose every vertex is `min_clear_m` or more above the road there is **overhead**.

| Gate | Overhead geometry is | Everything else |
|---|---|---|
| `drive_test` | not a surface a wheel could land on, not a thing in the corridor; a wall up there is not floating furniture | read as before. A wall, a column or a kerb rises from the road, has a vertex at the road, and is never set aside |
| `kn5_ground_check` | not ground under the deck, not a deck to stand on, not a foot, not a lamp head needing a mast | read as before, after the fidelity half has run on every vertex |
| `audit_mesh` | not changed. It reads upward only at `1GRASS`: check H within 6 m of the deck where the terrain raster nominates it, check J for a grass triangle over 60 m across lying over the road. A roof has no reason to be `1GRASS`; one that is would be read by those two | |

**What a declaration owes.** With `clear_m` written, overhead geometry over the road's own width that hangs lower than
`clear_m` − 0.5 m [invented] (and above 1.8 m, under which it is an obstruction already) fails `drive_test`
(`covered_low_overhead`). A span declared before its roof is built passes and says "none built": Denver's Drive 1
declares the span before the building stands.

Reports: `drive_test` and `kn5_ground_check` list each span with what was set aside and the lowest overhead found. Only
a track that declares a span carries those keys.

## What it was measured against

A 200 m synthetic road with a roof 5 m over 80 m of it (`tests/geometry/test_covered_spans.py`):

| The roof carries | Undeclared | Declared |
|---|---|---|
| a parapet (`1WALL`) | `drive_test`: 4 floating furniture; `kn5_ground_check`: walls 100 % no-ground | both pass |
| lights hung from the soffit (`LIGHTS`) | `kn5_ground_check`: 32 lamp heads without a mast | passes; the street lamp outside the span is still judged |
| a pavement on top (`1ROAD`) | `kn5_ground_check`: road floating 5.02 m over the ground | passes |
| a grass-named top (`1GRASS`) | passes, with the road under the roof **not judged** (7 of 12 samples read) | passes, all 12 read |
| nothing but a `BUILDING` slab | both pass | both pass |

So a plain roof 5 m up did not turn either gate red by itself: both already window their readings by height. What does is
what stands on the roof and hangs from it.

## Not covered by this

- **A column standing in the lane is not an obstruction to `drive_test`, declared span or not**, when its mesh has
  vertices only at the road and at the roof: the obstruction scan reads vertices between 0.25 m and 1.8 m over the deck.
  Found while testing; true of every track today. The Convention Center's columns need either subdivided meshes or a
  change to the scan.
- The prep's terrain conform and canopy trim, the AI and rain configs, and lights that are on by day (PLAN §4 item 1's
  second sentence).
- A `--line` run of `drive_test` reads no covered span, as it reads no bridge span.
