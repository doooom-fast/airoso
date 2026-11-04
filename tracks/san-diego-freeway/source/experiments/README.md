# Freeway barrier experiments (ledger 0075 addendum, 2026-11-03), NOT applied

**Superseded (2026-11-03, the Mac agent, ledger 0075 second addendum):** `scenery.walls.seat: "seated"` in
`scripts/geometry/build_network_mesh.py` (`_wall_seated`, `_deck_edge`) is the fix these experiments pointed at, built
the way the addendum asked: decks from the network's own viaduct lift (plus the spans the mesh already builds slab +
piers under), the at-grade base reaching the BUILT ground, the barrier gapped and the deck-edge slab clipped wherever
another edge's pavement lies under them. The scripts below are kept as the record; do not apply them.

Two patch scripts from the Windows box, kept so the next agent can read them. Neither is in `scripts/`; the branch
carries only `scenery.walls.offset_m` 3.2 -> 0.5 (experiment 1).

- `exp2_3_wall_drape.py`: opt-in `scenery.walls.seat: "drape"` in `scripts/geometry/build_network_mesh.py`. On a deck
  (centreline > 1.5 m over the raw 3DEP ground under it) the barrier stands `deck_off` past the half-width, its base
  0.35 m under the deck; at grade it stays `offset_m` out with its base sunk 0.5 m under the raw ground at the barrier;
  the crossing gap test also reads surface-street ribbons. Experiment 2 ran it with `deck_off` -0.35, experiment 3 with
  +0.05 (an edit after the script; the script as kept has -0.35). Its test, `tests/geometry/test_network_wall_seat.py`,
  is written by the script.
- `exp4_parapet_base.py`: on top of the drape, a `1KERB_parapet` strip 0.6 m wide beyond the pavement on the deck runs,
  the barrier in its middle (`deck_off` = 0.3).

Apply with `python <script> <airoso root>`, in order, and between them edit `_wall`'s `deck_off=-0.35` to `deck_off=0.05`
(experiment 3, a hand edit): the parapet script expects that line. The ledger's
addendum says why neither is the fix: the deck test must come from `data/network.viaduct.json`, not from height over
raw terrain, and the parapet strip must be clipped where another edge's pavement lies under it.
