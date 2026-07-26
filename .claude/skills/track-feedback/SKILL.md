---
name: track-feedback
description: File track feedback into the fleet ledger — turn "the sidewalks on Sand Creek are insane" or "the kerbs float on the switchbacks" into an evidence-grounded entry in fleet/feedback/, routed to the engine, a project, or the standards. Use whenever Kevin reports something he saw while driving or looking at a build.
---

# Filing track feedback

Kevin has said something is wrong with a track. Turn it into a ledger entry that can be acted on
across the whole fleet, not just the track he happened to be driving.

## Do this

1. **Read `fleet/feedback/README.md`** for the entry format, and **`fleet/LAWS.md`** before
   diagnosing anything. Most feedback is either a law being violated or a law being wrong.

2. **Check whether it is already filed.**
   ```bash
   python3 -m fleet.cli feedback
   ```
   If it is, add the new evidence to that entry rather than opening a duplicate.

3. **Keep his words verbatim** in the Symptom section. The phrasing carries information —
   "zigzaggy" and "juts into the road" are different defects with different causes.

4. **Find the mechanism before writing a Diagnosis.** Trace the value backwards through the pipeline
   stages to `file:line`: what wrote it, what read it, what transformed it. If you cannot get there,
   leave `status: open` with the evidence you do have and an empty Diagnosis. That is a correct
   outcome — a guessed diagnosis gets built.

5. **Route it.** `engine` (in `scripts/`, reaches every track), `project` (this track's config or
   data only), or `standard` (a law is wrong — amend `fleet/LAWS.md` first, then the code).

6. **Scope it properly.** Which `kind`s and which configs are affected; which track is the *proof*
   case and which is the *regression* case — the one that should barely change.

7. **Write the verification before the fix exists.** A gate, or a measured number with a threshold.

8. Assign the next free id, save as `fleet/feedback/NNNN-short-slug.md`, and show Kevin the entry
   plus a one-line summary of what you found.

## For a deeper investigation

If tracing the mechanism turns into real work — reading several pipeline stages, comparing built
artifacts across tracks — hand it to the **feedback-router** agent, which is set up for exactly that.

## Do not

- Do not rebuild a Blender-first track to investigate (`k10-san-diego/project`, the k10-colorado
  live-Blender scenes) — hand edits in the `.blend` would be discarded.
- Do not fix it in the same pass. Filing and fixing are separate, so the fix rides a train and
  reaches every track instead of one.
