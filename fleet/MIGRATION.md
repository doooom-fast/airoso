# Engine absorption — cutover plan

`prodrive-ac-builder` **is** this repo now. Its full git history (94 tags, every commit through
`3e1aa52`) was cloned in, and `scripts/` sits at the root with **identical package paths** — which
is the whole trick: consumers run `(cd .engine && python3 -m scripts.<pkg>.<mod>)`, so the cutover
is a **URL swap in `bootstrap.sh`**, not a code rewrite.

Status legend: ☐ not started · ◐ in progress · ☑ done

---

## ☑ M0 — Absorb the history

Done. `git clone` of the builder into this repo; its origin kept as the `engine-origin` remote so
nothing is lost and the old repo is still reachable.

**Nothing was deleted.** `apps/`, `projects/`, `tracks/`, `docs/`, `vendor/`, `tests/` all came
across as-is. Their dispositions are M4 and M5 below — each needs evidence before removal, not a
guess.

## ☑ M1 — Publish this repo

Done. `k10-motorsports/k10-track-agents`, **private** (matching `prodrive-ac-builder`; the track
repos stay public). `main` pushed, and all 94 absorbed tags pushed — consumers pinning `v0.16.0` or
`v0.19.0` can resolve them here.

`engine-origin` (the local builder checkout the history came from) has its push URL set to
`no_push`, so a bare `git push` can never write back to it.

Still owed: the **`k10-1978`** game repo's `PIPELINE_BRIDGE.md` points at `prodrive-ac-builder` for
`projects/gala-seed/` + `scripts/game/export_seed.py`. That contract now lives here.

Tag the absorption point once M2 is proven, so consumers have something to pin:

```bash
git tag v0.20.0 -m "Engine absorbed into k10-track-agents; control plane added"
```

## ☐ M2 — Re-point the consumers

**The cutover is content-neutral, and this is provable without building anything.** The absorbed
tags point at the same commits in both remotes:

```bash
git ls-remote --tags git@github.com:k10-motorsports/prodrive-ac-builder.git v0.19.0
git ls-remote --tags git@github.com:k10-motorsports/k10-track-agents.git   v0.19.0
# a5005e33… for v0.16.0, 8638edac… for v0.19.0 — identical in both
```

A consumer pinned at a tag therefore gets byte-identical code from either remote. The URL swap
cannot change build behaviour; anything that fails after it was already failing before it.

> **`ENGINE_REPO` does NOT work as a rehearsal when `.engine/` already exists.** `bootstrap.sh`
> only clones when `.engine/.git` is absent — otherwise it fetches from the *existing* origin and
> the override is silently ignored. A "rehearsal" run that way tests the old repo and reports
> success. To genuinely point an existing checkout at this repo:
> ```bash
> git -C .engine remote set-url origin git@github.com:k10-motorsports/k10-track-agents.git
> ./bootstrap.sh && git -C .engine rev-parse HEAD    # compare against the SHA above
> ```

Change the default in each repo's `bootstrap.sh`:

```diff
-REPO="${ENGINE_REPO:-git@github.com:k10-motorsports/prodrive-ac-builder.git}"
+REPO="${ENGINE_REPO:-git@github.com:k10-motorsports/k10-track-agents.git}"
```

Order matters — go **rally → san-diego → colorado**, cheapest and cleanest first. Rally is the
thinnest consumer (no local `scripts/` at all), so if the seam is wrong it fails there fastest and
nothing else has moved yet.

## ☐ M3 — Un-fork k10-colorado *(the big one)*

k10-colorado carries **72 local modules that shadow engine modules** — a whole parallel copy of the
pipeline living beside its `.engine` pin. This is precisely the failure the centralisation was
supposed to end: the copies went stale twice, which is why `k10-san-diego`'s notes say so in
capitals.

It cannot be deleted blind, because some of those 72 have almost certainly drifted *ahead* of the
engine (colorado is where the archetype work and the rainbow-road fixes happened). The safe order:

1. **Diff each shadow against its engine counterpart.** Three buckets: identical (delete),
   engine-is-newer (delete), colorado-is-newer (**port up into the engine first**).
2. Port the colorado-is-newer bucket into `scripts/` here, tag, and bump colorado's pin.
3. Delete the shadow tree; declare anything genuinely colorado-unique in the registry's
   `local_scripts_allowlist` with a reason.
4. `python3 -m fleet.cli lint` shows S4 clean for colorado.

The `standards-auditor` agent does step 1 and reports the three buckets.

## ☐ M4 — Retire the stale `projects/` duplicates

`projects/` inside this repo holds older copies of tracks now owned by project repos. The version
numbers make the staleness unambiguous:

| engine `projects/` | version here | live owner | live version |
|---|---|---|---|
| `sand-creek-raceway` | 0.15.3 | `k10-colorado/sand-creek` | **0.26.0** |
| `imi-motorsports` | 0.1.0 | `k10-colorado/imi` | **0.1.1** |
| `san-diego-loop` | 0.2.0 | `k10-san-diego/project` | **0.15.0** |
| `san-diego-freeway-loop` | 0.5.0 | `k10-san-diego/project_freeway` | 0.5.0 *(itself retired)* |

Before removing any of them, confirm the owner's `source/` actually carries every input the engine
copy has (the engine copy of Sand Creek is 29 MB — check what that is before assuming it is
redundant). History keeps them regardless; this is about the working tree.

**Do not touch `projects/gala-seed/`.** It is an external contract: the `k10-1978` game repo
consumes it through `scripts/game/export_seed.py` per its `PIPELINE_BRIDGE.md`. Absorbing the
engine moved that contract into this repo — the game repo's bridge doc now points at the wrong
place and needs updating as part of M1.

`dashcam-loop-0406` is the gps-track front-end's test fixture (`tests/fixtures/`, ONE-CHAIN §2 row 9). It
stays. `ats-colorado-sample` went with the SCS importer (row 7, 2026-10-29).

## ☐ M5 — Freeze `prodrive-ac-builder` *(needs Kevin's call)*

Once M2 is complete and a full build has passed from this engine, the old repo should stop being a
place anyone commits to: final tag, README pointing here, archive on GitHub. It still owns
`apps/prodrive-scan` (the iOS capture app) unless that moves too — worth deciding deliberately
rather than by default, since it feeds `scripts/capture/`.

Nothing in that repo has been modified. It is untouched and still buildable.

## ☐ M6 — Converge the pins

The point of all of the above. When M2 and M3 are done:

```bash
python3 -m fleet.cli pin v0.20.0
python3 -m fleet.cli lint            # expect S3 and S4 clean
python3 -m fleet.cli build --run --from mesh
```

That last command is the first fleet-wide rebuild — and the first time a change can be shown to
have reached all fifteen tracks.
