# Reading the post panels by eye

The brief each panel reader worked from (posts_lap.py makes the panels; posts_apply.py takes the verdicts).

**A panel** is one JPEG, `Pnnn.jpg`: the same 58 m square of the lap twice, **2022 on the left, 2020 on the right**, at the
aerial's own resolution (7.6 cm a pixel), north up. White ticks on the edges are every 5 m in the survey's frame
(E along the top, N down the left side); the labels are metres. A magenta strip separates the two years.

**What a post looks like from above.** The post itself is a dot. Its **shadow** is a thin dark straight stroke that starts
at the post's foot: in 2022 it runs about **north** (up), in 2020 about **north-west** (up-left) and longer. A real post
shows both: two strokes of different direction leaving one point. The ring marks that point.
- **lamp**: one post; the shadow ends in a small blob (the head) or a short hooked arm (cobra head). A globe lamp shows
  a bright dot at the foot.
- **signal_mast**: a pole at a corner or on a median with a long arm reaching over the roadway. You see the arm itself
  (a thin grey or dark line from the foot, with small dark boxes on it: the heads) and the arm's shadow displaced from it.
- **signal_post**: a short post or pedestal at a corner by a crosswalk, with a short shadow that has a boxy head
  (pedestrian or side-mounted signal heads). No arm over the road.
- **sign_or_small_post**: a short thin post, short thin shadow, sometimes with a small flat plate's shadow at its end;
  parking meters and bollards do NOT count (too short: under about 1.5 m of shadow in 2022).
- **utility_pole**: a tall pole with cross-arms or wires leaving it.
- **post_unknown**: clearly a post (both years show a stroke from one foot), kind not clear.
- **not_a_post**: a tree trunk (the shadow ends in branches, or a bare crown surrounds the foot), a fence or railing, a
  person, a vehicle's edge or mirror, a kerb or joint, a flag, a building corner, a bench, a bus shelter, anything else.
- **cannot_tell**: use it rather than guess.

**Rings.** Yellow = the reader found strokes of two or three years at that foot. Orange = the same, but the reader thinks
it is a tree. Cyan = one year only (the other years are in a building's shadow there). Grey rings without a number belong
to the neighbouring panel: ignore them. **Give every numbered ring a class.**

**Then look for what has no ring**: any post, mast or lamp inside the panel with no ring (numbered or grey) within about
1.5 m of its foot. Read its foot's position off the ticks (E, N in metres, to the nearest half metre if you can) and add it
with its class. In deep building shadow nothing can be seen: do not guess there.

**Output**: one JSON file per batch, `verdicts_<batch>.json`:

    {"reader": "<who>", "panels": {
       "P012": {"candidates": {"341": "lamp", "342": "not_a_post", "343": "signal_mast"},
                "added": [{"E": -1364.5, "N": 559.0, "class": "signal_mast", "note": "arm reaches east over Speer"}],
                "note": "east half in tower shadow in both years"}}}

Be strict: a ring is a post only if you can see the post's signature (two strokes from one foot, or one clear
stroke with a head where the other year is shadowed). Count nothing as a post because it has a ring.
