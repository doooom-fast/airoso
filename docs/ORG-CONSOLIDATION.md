# GitHub org consolidation — k10-motorsports → doooom-fast

*Drafted 2026-10-28 from Kevin's ask: "clean up all of the repos and delete or archive the
k10-motorsports ones and move everything that's current to the doooom-fast org."*
*Status: **decided 2026-10-28** (Kevin's answers in §Decisions). Nothing has been transferred, archived or deleted
yet; the commands below are the org owner's to run, since no agent session holds that token.*

## What is live today (the things that must not break)

| Live thing | Where it runs | Depends on |
|---|---|---|
| **doooom.fast**, racecor.io, prodrive.racecor.io, k10motorsports.racing | Vercel project `k10-racecor-prodrive` (team Alternate) | deploys from `k10-motorsports/prodrive-server` `apps/web`; its Tracks page reads the **latest GitHub Release** of `k10-motorsports/k10-colorado` and `k10-motorsports/k10-san-diego` (`apps/web/src/lib/tracks.ts`; docs/PUBLISHING.md) |
| api.prodrive.racecor.io | Vercel `racecor-prodrive-api` | deploys from `prodrive-server` |
| images.racecor.io | Vercel `prodrive-images-api` | deploys from `k10-motorsports/prodrive-images-api` |
| support.racecor.io | Vercel `prodrive-support` | deploys from `k10-motorsports/prodrive-support` |
| Track downloads (public zips) | GitHub Releases on `k10-san-diego` (Lake Murray, SD freeway) and `k10-colorado` (the Colorado zips) | both repos are **public**; a private repo's release assets cannot be downloaded anonymously |
| The track work itself | `doooom-fast/airoso` (private, LFS) | already in doooom-fast; references the old org in 20 files (list below) |

## Disposition — the 23 repos under k10-motorsports

Legend: **TRANSFER** = move to doooom-fast (GitHub keeps redirects for web, git and API URLs
until a repo with the old name is created); **ARCHIVE** = read-only history; **DELETE** = gone;
**CONFIRM** = Kevin decides, default shown. Last push from the GitHub listing of 2026-10-28.

### The racing product (prodrive / racecor / doooom.fast)

| Repo | Vis. | Last push | Default | Why |
|---|---|---|---|---|
| prodrive-server | private | 2026-10-27 | **TRANSFER** | The website and API. Live on Vercel. Step 2 below reconnects Vercel and re-points `tracks.ts` |
| prodrive-agents | private | 2026-09-30 | **TRANSFER** (confirm) | The telemetry product (airoso CLAUDE.md: "unrelated, leave it alone"). Holds a stale mirror of prodrive-server (PUBLISHING.md) that can be deleted after the move |
| prodrive-images-api | private | 2026-06-03 | **TRANSFER** | Live on Vercel (images.racecor.io) |
| prodrive-support | private | 2026-06-02 | **TRANSFER** | Live on Vercel (support.racecor.io) |
| prodrive-plugin | public | 2026-07-29 | **TRANSFER** (confirm) | Product family; public, so a user-facing URL may be printed somewhere |
| prodrive-windows | public | 2026-07-21 | **TRANSFER** (confirm) | Product family |
| prodrive-overlay | public | 2026-07-21 | **TRANSFER** (confirm) | Product family |
| prodrive-macos, prodrive-ios, prodrive-tvos | private | 2026-07-21 | **TRANSFER** (confirm) | Product family; any App Store / signing config that names the repo path needs a check |
| prodrive-edit | public | 2026-06-02 | **TRANSFER → ARCHIVE** | Kevin: not current |
| prodrive-homebridge | public | 2026-06-02 | **TRANSFER → ARCHIVE** | Kevin: not current |
| prodrive-designer | public | 2026-06-02 | **TRANSFER → ARCHIVE** | Kevin: not current |
| prodrive-narrative | private | 2026-05-16 | **TRANSFER → ARCHIVE** | Kevin: not current |

### The track work

| Repo | Vis. | Last push | Default | Why |
|---|---|---|---|---|
| k10-san-diego | public | 2026-08-28 | **ARCHIVE** after its zips are re-published on the fresh **`doooom-fast/track-releases`** (Kevin: fresh repo) | It is the public release host the website reads today. Step 1 creates `track-releases` (public, README only), re-publishes the current Lake Murray + freeway zips there, `tracks.ts` reads that one repo; then this repo is archived, read-only, under doooom-fast |
| k10-colorado | public | 2026-08-28 | **TRANSFER → ARCHIVE** after its releases are re-published on `track-releases` | Public zips live here today. The Lariat zip carries mined textures (Lariat V3-PLAN D0: take it down). Source retired; harvested into airoso 2026-08-19 |
| k10-track-agents | private | 2026-10-28 | **TRANSFER → ARCHIVE** | Retired (its CLAUDE.md). airoso carries its history, **but** airoso's history was rewritten 2026-10-27 (LFS), so the commit IDs the ledger quotes before that date resolve only here and in `D:/k10-track-archive/2026-10-27_airoso_before_lfs.git`. Keep it, read-only, in the one org |
| k10-colorado-rally | private | 2026-08-10 | **ARCHIVE** (transfer first so the old org can close) | Retired; the four stages' configs and STAGE-SOURCING are in airoso |
| prodrive-ac-builder | private | 2026-08-28 | **DELETE** (Kevin: delete) | Frozen 2026-07-25; verified strict git ancestor of k10-track-agents with zero unique files (docs/V3-PLAN.md §0). Its history is inside k10-track-agents |
| k10-1978 | private | 2026-07-09 | **TRANSFER** (confirm) | The game *1978*; airoso owes it the gala seed (`scripts/game/export_seed.py`, `projects/gala-seed/`). Current unless Kevin says otherwise |
| K10-mxc | private | 2026-07-26 | **TRANSFER → ARCHIVE** as `mxc` | Kevin: not current |
| k10-stories | private | 2026-07-26 | **TRANSFER → ARCHIVE** as `stories` | Kevin: not current |
| .github | public | 2026-04-27 | **DELETE** with the org | Org profile README. Recreate in doooom-fast if a profile is wanted |

After the table is settled, the k10-motorsports org is empty and can be deleted
(Organization settings → Danger zone). The `k10motorsports.racing` domain lives on Vercel, not on
GitHub, and is unaffected.

### Names after the move (Kevin: yes — and "K10 is gone. doooom.")

The `k10-` prefix stops meaning anything inside doooom-fast: `k10-1978` → `1978`,
`K10-mxc` → `mxc`, `k10-stories` → `stories`. `prodrive-*` stays; it is the product's name. Renames
also keep GitHub redirects.

## Order of operations

1. **Create the public release home first**: a fresh public `doooom-fast/track-releases` (Kevin's choice). Re-publish the current Lake Murray and freeway zips there as one release,
   and the Colorado zips Kevin still wants public (not the Lariat: D0). Until this exists the
   website's downloads depend on the old org.
2. **Transfer the four Vercel-backed repos** (`prodrive-server`, `prodrive-images-api`,
   `prodrive-support`, and `prodrive-agents` if confirmed). Then in each Vercel project:
   Settings → Git → disconnect and reconnect to the doooom-fast repo (the Vercel GitHub App must
   be installed on doooom-fast first). Push one commit to prove production deploys.
3. **Re-point `prodrive-server` `apps/web/src/lib/tracks.ts`** at the new release repo(s); deploy.
4. **Transfer the rest of the product family**, then `k10-1978` and whatever of `K10-mxc`,
   `k10-stories` is current.
5. **Transfer, then archive**: `k10-track-agents`, `k10-colorado` (after step 1), `k10-colorado-rally`.
6. **Delete**: `prodrive-ac-builder`, `.github`. Then the empty org.
7. **Install access**: the Claude GitHub App on doooom-fast is in "selected repositories" mode
   (airoso had to be added by hand today); add the transferred repos or switch it to all
   repositories. Same check for any CI secrets or deploy keys scoped to the old org.
8. **Update references** (one airoso PR, after the transfers so the URLs are real):
   `CLAUDE.md:13`, `fleet/registry.json` (5 remotes), `fleet/MIGRATION.md` (6), `docs/PUBLISHING.md`
   (4), `assets/licenses.json` (2), the `USER_AGENT` strings in `scripts/gps/overpass.py`,
   `scripts/elevation/usgs_3dep.py`, `scripts/trace/osm.py`, `scripts/environment/buildings.py`,
   `scripts/environment/zones.py`, `scripts/game/map_overlay.py` (and their `scripts-v021`
   copies, which are quarantined and stay byte-exact), `scripts/game/export_seed.py:63`,
   `scripts/game/__init__.py:1`, `projects/gala-seed/track.config.json:7`, and the `author`
   field in five `tracks/*/track.config.json`. Local clones: `git remote set-url origin` on
   astra and the Windows box.

## Commands (for the org owner; `gh` authenticated with `repo`, `admin:org`, `delete_repo`)

```bash
# transfer (one per repo; GitHub asks the new owner to accept only when it is a user, not an org you own)
gh api -X POST repos/k10-motorsports/<repo>/transfer -f new_owner=doooom-fast
# rename after transfer
gh repo rename track-releases -R doooom-fast/k10-san-diego --yes
# archive (read-only, reversible)
gh repo archive doooom-fast/<repo> --yes
# delete (irreversible)
gh repo delete k10-motorsports/prodrive-ac-builder --yes
```

Each of these is a click Kevin makes, or a command run from a machine where `gh` is logged in as
an owner of both orgs. An agent session can prepare the list and verify the result; it should not
hold the token that deletes repositories.

## Decisions (Kevin, 2026-10-28)

1. Release home: **a fresh `doooom-fast/track-releases`**.
2. `prodrive-edit`, `prodrive-homebridge`, `prodrive-designer`, `prodrive-narrative`, `K10-mxc`, `k10-stories`: **none are current** → transfer, then archive.
3. `prodrive-ac-builder`: **delete**.
4. **Drop the `k10-` prefixes.** And the brand itself: "K10 is gone. doooom." — the website catalog text, `ui_series` strings and the series names in Content Manager follow (docs/ONE-CHAIN.md §3).

```bash
# step 1, the release home (owner):
gh repo create doooom-fast/track-releases --public --description "doooom track downloads: every Assetto Corsa track's release zips"
```
