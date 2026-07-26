# Build trains

A **train** is one batch of feedback, carried to every track at once: a set of ledger entries → one
engine tag → one fleet-wide rebuild → one results matrix.

Trains exist because per-item shipping does not work here. A geometry change touches road Z, edge
sweeps and terrain seating together; proving it on one track proves nothing about the other
fourteen, and shipping it to one track leaves the fleet inconsistent. So changes batch, and the
batch is proven against the whole fleet before it ships.

## The shape of a train

1. **Load** — pick ledger entries. Order them by blast radius: cheap and isolated first, invasive
   last, so a failure is attributable.
2. **Standards first** — any entry at `layer: standard` amends `LAWS.md`/`STANDARDS.md` *before* its
   code lands. A law and the code disagreeing is how a law gets quietly dropped.
3. **Land** — engine changes in `scripts/`, each with the gate that proves it.
4. **Tag** — one engine tag for the whole train.
5. **Converge** — `fleet.cli pin <tag>`, `./bootstrap.sh` in each repo.
6. **Rebuild** — `fleet.cli build --run --from mesh`, and record the matrix in the train file.
7. **Drive** — the part no gate replaces. Phase 6 is Windows-only: install, drive, record AI lines,
   look at it. Feedback from that drive opens the next train.

## Rules

- **A track that regresses blocks the train.** Not "note it and ship" — the matrix has to be green,
  or the train is held and the offending change backed out.
- **Blender-first tracks are never auto-rebuilt.** `k10-san-diego/project` and the k10-colorado
  live-Blender work have hand edits in a `.blend` that a regenerate would discard. They take engine
  fixes at the export stage, and full re-seeds only when Kevin says so.
- **`FABRICATED` tracks are excluded from proof.** `high-plains` and `second-creek` have invented
  geometry (L1); a gate passing on them means nothing until they are re-sourced.
- **Record what was skipped.** A train file that does not say which tracks were left out reads as
  "everything passed" when it did not.
