# The feedback ledger

**How a thing Kevin noticed while driving becomes a fix on every track.**

The problem this solves: feedback arrives per-track ("the sidewalks on Sand Creek are insane"), but
the cause is almost always in the engine, and the fix should reach fifteen tracks — not one. Left
informal, that turns into the same note being re-discovered on the next track, and a fix landing in
one repo's local copy where nothing else can see it.

## Filing one

Say it however you like — "the kerbs on Lariat float on the switchbacks", a screenshot, a clip.
Use `/track-feedback` to have it written up, or write the file directly:

```
fleet/feedback/NNNN-short-slug.md
```

with this header, then the sections below it:

```markdown
---
id: 0007
title: Kerbs float on switchbacks
status: open          # open | diagnosed | in-train | shipped | rejected
scope: kind:street_port, k10-colorado/lookout-lariat
layer: engine         # engine | project | standard
train: -              # the train that carries it, once assigned
---
```

`status` and `train` are what `python3 -m fleet.cli feedback` reads, so keep them accurate.

## The sections

| Section | What goes in it |
|---|---|
| **Symptom** | What it looks like *from the driver's seat*. Kevin's words, kept. |
| **Evidence** | `file:line`, gate output, measured numbers. Not a guess about the cause. |
| **Diagnosis** | Why it happens. Written only once the evidence supports it — an entry can sit at `status: open` with an empty diagnosis indefinitely, and that is better than a confident wrong one. |
| **Fix** | What changes, where, and what it costs. |
| **Scope** | Which tracks are affected, and which are the proof cases. |
| **Verification** | The gate, measurement, or drive that proves it fixed — decided *before* the fix. |

## Layers

- **`engine`** — the fix belongs in `scripts/`. Affects every track on the next pin bump. Most
  feedback is this.
- **`project`** — genuinely local: this track's config, its route, its source data.
- **`standard`** — the feedback shows a law or standard is wrong or missing. Amend `fleet/LAWS.md`
  or `fleet/STANDARDS.md` *first*, then fix the code to match. `0003` is one of these.

## From ledger to build

Entries are batched into a **train** (`fleet/trains/`): a set of feedback items, one engine tag, one
fleet-wide rebuild, one results matrix. Nothing ships per-item — the whole point is that a batch of
fixes gets proven against every track at once.

```bash
python3 -m fleet.cli feedback                 # the ledger, by status
python3 -m fleet.cli build --run --from mesh  # the rebuild a train ends with
```
