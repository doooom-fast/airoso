# Publishing a track to doooom.fast

How a build gets from this repo onto the website. Learned 2026-10-09 while publishing Lake Murray
V3; written so it is never re-derived.

## How the site is fed

- **doooom.fast** (and racecor.io, k10motorsports.racing) is the Vercel project
  `k10-racecor-prodrive` on the "Alternate" team, deployed from
  `doooom-fast/prodrive-server` (`apps/web`, Next.js). Kevin's checkout:
  `C:\Users\Owner\Documents\GitHub\prodrive-server`. The copy under `prodrive-agents/` is a stale
  mirror — don't edit it.
- The Tracks section (`apps/web/src/app/(doooom)/_site/Tracks.tsx`) merges a **committed catalog**
  (`apps/web/src/lib/doooom/tracks.ts`: name, place, roads, length, layouts, outline art, keyed by
  asset base) with the **latest GitHub Release** of each track repo
  (`apps/web/src/lib/tracks.ts`: `doooom-fast/track-releases`, the one public release home since the org move of 2026-10-31 — docs/ORG-CONSOLIDATION.md; before it, `k10-motorsports/k10-colorado` and `k10-motorsports/k10-san-diego`).
  Every `.zip` asset on the latest release becomes a download; the asset filename minus
  `_vX.Y.Z` / `_ai` is the key (`san_diego_lake_murray_v0.23.0.zip` → `san_diego_lake_murray`).
  60 s ISR, so a published release shows within a minute. Nothing else to deploy.
- Consequences: **only the latest release's assets show**, so every release must carry every zip
  that should stay downloadable (re-upload the unchanged freeway zip beside Lake Murray).
  **Drafts are invisible** to the site (`releases/latest` skips them) — a draft is the safe
  staging step; publishing it is the one irreversible click. Catalog text (layouts, length) is
  static: change it in prodrive-server when the zip changes shape.

## Package shape

Zip root is the AC folder name — `san_diego_lake_murray/` — so a drag into Content Manager
replaces the previous install. Ship `ui/preview.png` (CM never reads the `preview.svg` the
engine's fallback emits; `tools/`-side rasterize), `README.txt`, `CREDITS.txt`, `LICENSES.md`
that tell the truth about what is in the kn5.

The public package must start at the lap seam, not at the per-issue debug start in
`tracks/<slug>/start_positions.json` (`active`): re-export with `active: seam-alvarado`
(`scratchpad/publish_reexport.sh` pattern: swap `active` in both the airoso and the v021 workshop
copies, `tools/ship_sd.sh --skip-blend --no-install`, restore). Geometry and gates are unchanged
by a start move, so no new drive test is owed.

## Licensing — the two variants

The V3 Lake Murray build binds third-party content that is **not licensed for redistribution**
(ledger 0040: "never leaves this machine"):

| What | From |
|---|---|
| `extension/trees/*.bin` TreeFX models (14) | No Hesi 1.10, Algarve Portimão 2023, Shutoko Revival Project |
| `asphalt_cracked_*.jpg` road texture | LA Canyons 1.2 |
| `building_*.jpg` concrete | Hamburg by 4r (TextureCom maps) |

**The split is a tool, not a rule** (Kevin, 2026-10-11: "No one actually cares about assets in free mods
for a 13 year old game"). Asset provenance never withholds or degrades a release. `tools/pack_release.py`
builds both zips every time; which one goes public — full or CC0, with or without the race layouts — is
Kevin's call at publish time, and publishing itself is still his go, per release.

So two zips exist per release, built from the same track folder:

- **Full** (Kevin's own install; what he drove) — everything above included; `CREDITS.txt` lists
  the third-party content by origin.
- **Race layouts (ledgers 0047 / 0049)** — the installed folder carries `models_street.ini` +
  `models_race_cw.ini` + `models_race_acw.ini`, `san_diego_lake_murray_race.kn5` (both curb walls + kerbs) and,
  since 0049, one `san_diego_lake_murray_closure_<id>.kn5` per race direction. The barriers sweep Kevin's owned
  K-rail pack (4 m jersey module; its licence terms are not recorded in `assets/licenses.json` — a fact, not a
  blocker). By default the CC0 zip is Lake Murray Free Roam only (`strip_race_layouts` drops the race kn5s, the two
  race `models_*.ini`, their `ui/<id>/` and `<id>/` dirs and their spawn kn5s); **`--with-race`** keeps all
  three layouts in it and renders the `[[with-race]]` blocks of the CC0 release texts (the K-rail credit, the
  three-version README). The default stays street-only for now only because prodrive-server's catalog
  (`layouts` text) describes one layout — update it in the same breath as a `--with-race` zip goes up.
- **CC0 variant** — `.bin` models stripped, `[TREES]` lines
  commented out with `extension/trees/README.txt` telling players how to drop in models they own;
  `tools/repack_kn5_textures.py` swaps the two mined texture pairs for CC0 bytes under the same
  names (Poly Haven `aerial_asphalt_01`, ambientCG `Concrete034` from
  `_salvage/k10-sd-v021/assets/textures/`) so every material binding survives and no gate needs
  re-running. It has no vegetation until free TreeFX models replace the mined ones.

## Packing — one command

```bash
python tools/pack_release.py --version 0.23.0              # CC0 zip = Lake Murray Free Roam only (default)
python tools/pack_release.py --version 0.24.0 --with-race  # CC0 zip keeps the two race layouts too
```

writes `full/<slug>_v0.23.0.zip`, `cc0/<slug>_v0.23.0.zip` and `san_diego_freeway_v0.5.0.zip` under
`k10-sd-v021/project/build/release/` from the installed `_v3` folder (or `--src`), applying the CC0
transforms above and the release texts in `tracks/san-diego-lake-murray/release/{full,cc0}/` (each text's
`[[street-only]]` / `[[with-race]]` blocks resolved for the package it goes into).
**A zip is a snapshot of `extension/ext_config.ini`:** any config-only change (lights, GrassFX) means
re-packing both variants and re-uploading before `--draft=false`; the kn5 does not change.
`--src` must be a build whose start is the public one — the installed `_v3` carries whatever per-issue
debug start `start_positions.json` is set to; until the layouts work puts the grid on Alvarado, pack from
a seam-start re-export (see above), not from the installed folder.

## Mechanics

`gh` is not logged in on this machine; the Git Credential Manager holds Kevin's GitHub token
(`alternatekev`, scopes gist/repo/workflow). Use it per command without printing it:

```bash
tok() { printf 'protocol=https\nhost=github.com\n\n' | git credential fill | sed -n 's/^password=//p'; }
GH_TOKEN="$(tok)" gh release create vX.Y.Z -R doooom-fast/track-releases --draft \
  --title "..." --notes-file NOTES.md lake_murray.zip freeway.zip
GH_TOKEN="$(tok)" gh release edit vX.Y.Z -R doooom-fast/track-releases --draft=false   # publish
```

Tags continue the public repo's own series (v0.22.0 → v0.23.0), not airoso's
`track.config.json` version; the release notes name the airoso build.

## History

- 2026-10-09 — v0.23.0 drafted (CC0 variant + unchanged `san_diego_freeway_v0.5.0.zip`);
  prodrive-server PR #89 drops the stale "Freeway" layout from the Lake Murray catalog entry.
