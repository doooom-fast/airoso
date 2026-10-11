---
id: 0048
title: "Rebuild Lookout Mountain in the same high fidelity style with all of the fixes applied, and no extra highways (they look like wavy ribbons now)" — port the Lariat to the V3 method, route-only
status: open
scope: tracks/lookout-lariat (airoso source of truth; k10-colorado/lookout-lariat is the retired twin) — kind street_port, archetype real_road; the deck finding also names engine scripts/environment/build_env.py _build_highways (unconditional on every build_env track)
layer: project
train: -
---

## Status

**Open, queued after San Diego** (2026-10-10). Nothing built, nothing committed, no `.blend` touched.
The "wavy ribbons" half is measured and diagnosed below; the rebuild half waits on a LOCATION-DOSSIER
Kevin approves, on 0043/0044/0045/0046/0047 landing on Lake Murray first (their tools are what gets
ported), and on Kevin's explicit re-ordering of the priority line (see **Priority**; *2026-10-11:
done, see the status update*). 0047 (the
three-version / per-layout machinery) is on disk; 0044 (arrow signs) is cited by number as filed this
day — 0045 and 0046 already cite it — and its rule is restated here so nothing dangles if the file
lands later.

**P0 — approved and under way (2026-10-11).** Kevin: *"Those changes are good"*, which takes every
default in [`V3-PLAN.md`](../../tracks/lookout-lariat/V3-PLAN.md):
- **D1** keep the Colfax double-back (24.9 km).
- **D2 (a)** one slab with its real median; Street Reverse drives the four divided stretches against
  the arrows, and its text says so.
- **D3 (a)** a race version on the real narrow road, one-way: four layouts, `street_full`,
  `street_reverse`, `race_acw`, `race_cw`.
- **D4** both widths for Drive 1 (`road_profile.verge_m` 0.4 vs 1.25, two installs).
- **D5** static C-470 bridges.
- **D6 (i)** real relief beyond ~50 m — the L3 amendment shared with 0046, config and plan only
  for now, no geometry; **(ii)** the Denver skyline after Drive 2.
- **D7** all five July calls reversed.
- **A1–A13** as written.
- **D0** (the public download) is handled separately. Nothing in P0 touches a release or the site.

Status stays `open`. Nothing is committed, and there is no geometry, kn5 or Blender build. On disk
now, uncommitted, each step with its own record:
- **Step 1.** `scripts/tls.py` hands certificate checks to the operating system's verifier
  (`truststore`). Verification is never turned off, and the step-3 fetch ran with it on.
- **Step 2.** Five frame-free July files are restored to `tracks/lookout-lariat/data/source-july/`
  from k10-colorado `0a897bb^` with `git show`, byte-identical (`PROVENANCE.md` there). The
  retired repo was not checked out or changed.
- **Step 3.** `data/osm.cache.json` is the route stage's own Overpass snapshot: 197 ways, fetched
  2026-10-11T19:29:58Z.
- **Step 4.** The twin's `.blend` + `.blend1` are copied, with `MD5SUMS.txt`, to
  `D:/k10-track-archive/2026-10-11_lariat-july-blend/`. The originals in the retired repo are
  untouched.
- **Step 5.** `fleet/registry.json` points the Lariat at airoso and lists it under k10-colorado's
  `moved_out`. `fleet.cli tracks` lists `airoso/lookout-lariat` at 0.16.0.
- **Step 6.** `track.config.json` is rewritten to 0.16.0 in the V3 loop frame (`mirror_x` false,
  true north 0), with the four layouts and the D4 verge.
- **Step 7.** The re-derived centreline is 24,890.8 m, 8,302 points, closed. Against July's line
  it differs only at A1's three places, and it is 51 m shorter, mostly because the U-turn is gone
  (`data/PROVENANCE.md`).
- **Step 8.** `tools/route_oneway_check.py` writes `data/oneway_check.json`. Street Full runs
  against no one-way way. Street Reverse runs 4,486.5 m against the arrows, all of it on the four
  declared D2 stretches. The race layouts are closed roads and are not checked.
- **Step 9, the paper corrections.**
  - `docs/V3-PLAN.md:6` now reads San Diego, then the Lariat, then Sand Creek. Phase 4 gains a
    "Then Lookout Lariat" paragraph before "Then Sand Creek".
  - `fleet/DEFINITION-OF-DONE.md:45` now reads **T0** (July v0.46.0 build only; current pin fails
    drive_test).
  - `assets/licenses.json`'s `building_*` entry now says Hamburg by 4r, personal use only, not
    CC0, with a `_note`. The entry went stale at a7f4d6f (2026-06-27), which swapped the bytes
    and updated `SOURCES.txt` but not this file.
  - **Which packages that affects**, read today from each installed kn5's texture table:
    - the Hamburg `building_*` bytes are inside eight installed folders: `lookout_lariat`,
      `imi_motorsports`, `high_plains`, `pueblo_motorsports_park`, `second_creek`,
      `sand_creek_raceway`, `san_diego_freeway` and `san_diego_lake_murray_v3`;
    - each of the eight carries generated credits that call those bytes CC0 Concrete034;
    - `tools/pack_release.py` fixes this in Lake Murray's two zips (Full text, CC0 byte swap), but
      copies `san_diego_freeway`'s kn5 and its texts into `san_diego_freeway_v0.5.0.zip`
      unchanged.

    These are inputs for D0, and nothing was done about them here. Not checked: whether each
    published zip matches its installed copy, and Aspen and the rally stages (not installed).
  - **Found in passing, not corrected:** the same commit replaced `roof_*.jpg` with Hamburg maps
    (`TCom_Roofing_PVC`), but `licenses.json` still lists `roof_*` as ambientCG
    CorrugatedSteel002, CC0. `SOURCES.txt` gives CorrugatedSteel002 to `warehouse_metal_*`
    instead. It is the same class of fix, outside the approved item, and waits on Kevin's say-so.

P0's done-when list (V3-PLAN P0) is not claimed here. *(Now claimed, each item with its artifact:
see **P0 done** at the end of this entry.)*

## Symptom (Kevin, 2026-10-10)

> "Then we'll rebuild lookout mountain in the same high fidelity style with all of the fixes applied,
> and no extra highways (they look like wavy ribbons now)"

Three statements in one sentence, kept apart because they ship separately: **(1)** the Lariat is next
after Lake Murray; **(2)** it gets the V3 build — Blender-authored on the engine's underlay, the
0032–0047 fix classes applied, gated, seat-verified; **(3)** the road set is the lap and nothing else,
because the highways the current build adds beside the lap "look like wavy ribbons". The artifact he
means is the only Lariat on this machine: `D:/SteamLibrary/.../content/tracks/lookout_lariat/`
(`lookout_lariat.kn5` 550.5 MB, 2026-07-27 09:14, ui `[build 0.15.0]`), i.e. the public
**k10-colorado v0.14.0** release.

## Evidence

### Where the Lariat lives

- `fleet/registry.json:101-105` — `k10-colorado/lookout-lariat`, kind `street_port`, fidelity real,
  "OSM route (named + ref: + id: ways)". The repo at `C:/Users/Owner/Documents/GitHub/k10-colorado`
  is **retired** (its `README.md` / `CLAUDE.md`: "DO NOT WORK HERE … exists only as read-only
  history"; last commit a28e8a1 2026-08-19). Its `tracks/lookout-lariat/track.config.json` and
  `source/route-notes.md` are byte-identical to `airoso/tracks/lookout-lariat/` (`diff` empty, both
  files) — **airoso's copy is the one to edit**. Derived data (`data/`, `build/`) was deleted in
  k10-colorado 0a897bb (2026-08-09, "Delete all generated output"). *Corrected 2026-10-11: the
  Overpass snapshot does survive, in the twin's history at `0a897bb^` (see the status update).*
- `k10-colorado/tracks/lookout-lariat/blender/lookout_lariat.blend` (586.8 MB, 2026-08-08 13:27,
  plus `.blend1`) is **not** the source of the installed kn5 (built Jul 27). *Corrected 2026-10-11,
  after inspection: it is not a live-Blender refinement workspace but build_kn5's phase-5 output
  from the 0024 barrier-winding measurement builds (0 collections, 0 text blocks, 0 modifiers,
  identity transforms). It carries no authored layer. Archive it rather than delete it, since
  vertex-level edits can't be ruled out.* V3-PLAN Phase 0 already flags the ~3.5 GB of Colorado
  `.blend` workspaces for archival.

### The route, as configured (`tracks/lookout-lariat/track.config.json`)

`route.roads` = `19th Street`, `Lookout Mountain Road`, `Paradise Road`, `ref:US 40`, `ref:US 6`,
`id:484287799,1351773584,533503588,533503214` (the US-6 northbound off-ramp at 19th St — the lap
"must climb the real ramp" because 19th St crosses US-6 on a bridge, `_roads_doc`). `route.bbox`
`[39.693, -105.265, 39.758, -105.183]` (7.0 × 7.2 km). `loop: true`, `width_profile: mountain`,
`osm_road_widths: true` (6.5 m Lariat Trail / 9 m US-40 / one 9 m US-6 carriageway), `kerb` and
`runoff` off, `max_grade_pct 16`, measured crossfall, `mirror_x: true`, `true_north_rotation_deg
180`, `layouts[]` = `full` + `reverse`. The lap itself is right: `scripts/gps/overpass.py:39-41`
builds `way["highway"]["highway"!~"motorway"]["ref"~…]` so `ref:US 40` / `ref:US 6` can never drag
I-70 in, and `_parse_payload` (`:123`) re-checks it; `scripts/gps/widths_from_osm.py:330-350` locks
freeway widths to declared roads only. **Nothing in `route.*` asks for a second road.**

### What the build adds beyond the lap, and why it is wavy

The extra highways are not route data. They come from the **environment stage**, which the engine
`build.sh` runs after mesh (`scripts/build.sh:88`, `scripts.environment.build_env`):

1. **The fetch.** `scripts/environment/zones.py:34-35` queries Overpass for every
   `way["highway"~"motorway|trunk|motorway_link|trunk_link"]` in the bbox; `:50-51` classes each as
   `("highway","line")`; `:94` takes the bbox from **`route.bbox`** — the whole 7 × 7 km box, not the
   lap. In that box: I-70 (both carriageways, exits 254–260), US-6 (trunk — both carriageways where
   divided, the Clear Creek Canyon reach west of Golden, the 6th Ave reach south), and every
   `*_link` ramp at the I-70 exits, the US-6/19th St diamond and the US-6/Colfax junction. The way
   count could not be re-derived today: Overpass is unreachable from this box (overpass-api.de and
   its mirrors fail TLS "certificate has expired"; kumi unreachable; private.coffee 504, 2026-10-10
   ~20:00) and no cache exists — so the set is stated from the query and the route notes and must
   be measured again when the dossier's extract is pulled. The **built** artifact is the better
   evidence anyway (L5), and it was measured instead:
2. **The deck builder.** `scripts/environment/build_env.py:313-411` `_build_highways` — called
   **unconditionally** at `:626-627` (`hwy_deck, hwy_struct = _build_highways(env, project,
   ground_y, on_track=hwy_corridor)`); there is **no config key** that turns it off (grep of
   `build_env.py` and `scripts/config.py` for a `highways` key: none). The docstring says what it is
   for: "Re-build the I-70 / US-36 decks ALONGSIDE the route" — Sand Creek's Commerce City
   freeways (module header `:7`, "I-70/I-270/Vasquez as raised visual highway decks"). Every
   fetched line ≥ 240 m (`min_len=240.0`) that survives the 16 m corridor clip becomes a slab:
   - **width `half_w=11.0` → 22.0 m, constant** (`:313`), the Commerce City freeway width, applied
     to a 2-lane canyon carriageway and to every ramp alike;
   - resampled at 8 m (`_resample_xz(step=8.0)`, `:292`, `:384`), the deck height per station is
     `deck_e = max(sm[i], terr[i] + 0.2)` (`:343`) where `sm` is a running mean of the ground over
     ±22 stations (±176 m) and `terr` is `ground_y` — the triangle-exact conformed grass grid
     (`:552-562`) or the heightfield upsampled ×3 (`:538`, "40 m → ~13 m"). "Ride crests, bridge
     dips": wherever the ground pokes above the 350 m mean the deck follows the **raw facet**,
     wherever it drops the deck floats on piers (`:367-371`, one per 24 m when > 2.5 m up);
   - mesh names `HIGHWAY` / `HWYSTRUCT*` (`:1467-1468`), no numeric prefix → visual-only (L7),
     `HIGHWAY` material = the lap's own `asphalt_cracked` (`scripts/ac/pbr.py:44`), UV one tile per
     station across the full 22 m (`:351`): no crossfall, no lanes, no edge line.
3. **Measured on the installed kn5** (`scripts/modkit/inspect_kn5` + `extract_kn5 --no-recenter`,
   scratch analysis of the 22.0 m cross-section edges, read-only; frame x/z local metres, y up):

   | mesh | verts / tris | extent (x, z) | y |
   |---|---|---|---|
   | `1ROAD_main` (the lap) | 49,902 / 16,636 | −2195..3286, −2829..3147 | 0.0..506.0 |
   | `HIGHWAY` | 30,328 / 10,132 | **−6127..4435, −4270..3651** | −28.9..464.9 |
   | `HWYSTRUCT_0` | 34,502 / 24,694 | −849..4435, −4270..3651 | −29.9..348.4 |
   | `HWYSTRUCT_1` | 12,534 / 8,198 | −6127..−841, 1404..2823 | 325.4..465.8 |
   | `MOUNTAINS` | 960 / 320 | −12861..−8574, ±12213 | −200..1251 |

   - **5,127 deck stations, 37.3 km of 22 m-wide deck** against a 24.9 km lap — 1.5× the lap's
     length of pavement that is not the lap. **9.6 km of it within 100 m of the lap, 15.3 km within
     300 m** (the US-40 / I-70 pairing down Mt Vernon Canyon and both US-6 carriageways beside the
     return leg); the rest reaches **3.9 km past the lap's west edge** (`HWYSTRUCT_1`, y 325–466:
     *corrected 2026-10-11, this is I-70 west toward Genesee, not the Clear Creek Canyon US-6*) and
     1.4 km south.
   - **Wavy, measured:** 408 vertical direction reversals > 5 cm along the deck centrelines =
     **10.9 per km** overall; individual runs 20–74/km (run #11, 811 m beside the lap at 577 m:
     66.6/km, max second difference **1.82 m per 8 m station**; run #5, 1,349 m at 49 m from the
     lap: 33.4/km; run #27, 432 m: 74.1/km). Max station-to-station grade **24.8 %** on a deck
     that is supposed to be an interstate. The 132 runs the chain found are fragments of the same
     slabs (chaining breaks on the > 1.5 m steps) — the fragmentation is itself the symptom.
   - The mechanism of the waviness is **L3b on a canyon wall**: a 12 m carriageway benched into a
     30–45° slope is narrower than the ~13 m ground cells the deck samples, so the sampler returns
     the wall, not the shelf; a few metres of OSM-vs-DEM registration on that slope is metres of
     height; `max(sm, terr+0.2)` then pins the deck to every facet that crests the mean and floats
     it across every facet that does not. Two OSM carriageways each get their own 22 m slab, so a
     split-level canyon freeway renders as two overlapping ribbons at different heights.
4. **No gate sees it.** `audit_mesh.py:181` reads `HWYSTRUCT` only as a support class; `drive_test.py:14`
   names it only as a possible obstruction; `kn5_ground_check.py:28` buckets `HIGHWAY`/`HWYSTRUCT`
   for assembly fidelity and `:288-315` uses `HWYSTRUCT` as a foot support. **Nothing measures a
   deck against the road it claims to be**, and the drivable-corridor clip (`:626`, margin 16 m)
   is the only thing that ever removed one. This is the same coverage shape as TreeFX in 0040 —
   invisible to the gates, so only the seat finds it.

### The rest of the current build is July-era engine output

Every defect class the SD V3 ledger fixed on Lake Murray is present here in its July form:

| class | Lake Murray V3 fix | the Lariat today |
|---|---|---|
| split carriageways as independent ribbons | 0032 / 0035 (deleted), 0037 (one slab, median island ON it), 0039 (divided connector → one trunk) | US-6 driven as one 9 m carriageway; the opposing carriageway and I-70 exist only as `HIGHWAY` slabs (above) |
| mouths swept through, edges follow the flare | 0033 / 0036 / 0041 (trimmed, gapped, authored per `docs/JUNCTIONS.md`) | no authored mouth anywhere; the lap has five turns from one road onto another (19th St → Lariat Trail gates; Lookout Mtn Rd → Paradise Rd tee; Paradise Rd → US-40 at exit 256; US-40 → US-6; US-6 off-ramp → 19th St) plus the Buffalo Bill summit and the Windy Saddle side roads |
| terrain seating / facets under the road | 0041 addendum + 0042 (`tools/seat_terrain_blend.py`, audit F 60 → 15) | 0010: 6.67 m cells float the road p95 **+1.56 m**; 5 m cells need 1.44 M verts and drop 11 guardrail posts — the two-resolution bind never resolved; `corridor_refine_factor 4` is the compensation |
| far relief | 0046 (3DEP far ring, tiered cells, `MOUNTAINS` sine ridge named "L1 broken", "Colorado removal: follow-up") | `MOUNTAINS` = 960-vert sine-wave silhouette (`build_env.py:1312-1333`) for a track that sits **on** the Front Range; the real Lookout Mountain, Mt Zion and Clear Creek Canyon walls beyond the heightfield margin are absent |
| roughness | 0042 (`smooth_sigma_y_pts` 5.0, kinks 8.09 → 4.97/km) | 0025 (v0.63.0 rebuild, never installed): severe 251, kinks **68.3/km**, excursion drops 690, far ledges 378 — "the mountain road is its own campaign"; road grid 2.93 m single-layer (`fleet/reference/MEASURED.md:40`) vs the 0.3–1.1 m references |
| trees | 0040 (TreeFX, 15,261 plants, real species) | `scenery.treefx.enabled: false` — ~120 k TurboSquid-derived conifer billboards + 2,500 OBJ pines baked into the kn5 (128 `PINETREE` + 48 `CONIFER` meshes); the `MRS_*` conifer `.bin` zone config is kept but off |
| lamps | 0040 pass 2 + 0043 (owned model; 255× intensity scale fixed; sodium from the civic record) | **304 `[LIGHT_N]`** at 96 m spacing (`light_spacing_m 96`) along a Denver Mountain Parks road that has no continuous lighting — "Streetlights ON per Kevin" (July); `COLOR = 255, 217, 76, 0.35` → effective 89, the same decade error 0043 §Scope already names for `lookout-lariat` |
| signs | 0044 (arrow signs at the hazard, the rule) | `road_signs.enabled: false`, `signs.enabled: false` — stripped at rc14 "the abstraction baseline" (k10-colorado c35e5a2); the config's own `_doc` still plans "sharp-turn arrows at warning-barrier entries" |
| GrassFX | 0045 | `lighting.grassfx: true` on 49 `1GRASS_*` meshes — one of the "six installed Colorado inis" 0045 says carry the fictional grammar |
| layouts | 0047 (per-layout `direction` + declared `start`, a nodes-only spawn kn5 per layout, `drive_test --layout`, multi-layout ship; L8 amended "layouts may add kn5s, never alter the shared road") | already two: `models_full.ini` = `models_reverse.ini` = one `lookout_lariat.kn5` and **no spawn kn5 in either** (the config `_doc` promises "dummies_reverse.json + spawn kn5"; the folder carries only the main kn5, and `grep -a` finds the whole grid baked into it: `AC_START_0`, `AC_PIT_0-3`, `AC_TIME_0/1/2_L/R`, `AC_HOTLAP_START_0` — one forward-built node set shared by both directions, the 0016/0026 contract gap 0047 Diagnosis 1 names), `full/` + `reverse/` AI, reverse heading flip at `scripts/ac/kn5_write.py:346,363` only ever runs for a spawn kn5 that was never written — this is the one thing to **keep**, rebuilt on 0047's shape |

### Public release state

k10-colorado **v0.14.0** ("AI lines: every track can be driven by the AI"), published 2026-08-10
18:27 UTC, not a draft, assets `lookout_lariat_ai.zip` **311.4 MB** beside the five circuits (read
via `gh release view`, read-only). doooom.fast's committed catalog
(`prodrive-server/apps/web/src/lib/doooom/tracks.ts:38-47`) shows it as **"Lookout Mountain
Lariat — Golden, Colorado — 24.94 km — Full / Reverse"**, which matches the installed
`ui/full/ui_track.json` (`length 24942`, version 0.15.0; its tags include `fictional` on a real
road — fix in the rebuilt folder). Per `docs/PUBLISHING.md` only the latest release's assets show,
so the rebuilt Lariat must be re-uploaded beside every other Colorado zip, and the Full / CC0 split
applies the moment TreeFX `.bin` models ride in it (the current zip carries baked billboards, not
`.bin` files; `extension/` holds only `ext_config.ini`).

### Priority

`CLAUDE.md:12` — "Priority: San Diego, then Sand Creek"; `docs/V3-PLAN.md` opens with "San Diego
first, Sand Creek second" and Phase 4 ends "Then Sand Creek". Kevin's sentence puts the Lariat
next. **Both lines need his explicit edit** — not changed here, and this entry does not out-rank
them until he does.

*2026-10-11: Kevin re-ordered it ("what about lariat"). `CLAUDE.md:12` now reads "San Diego, then
Lookout Lariat …, then Sand Creek" (918d7f1); `docs/V3-PLAN.md:6` still needs the same edit
(V3-PLAN P0 step 9).* *Later the same day: done in P0 step 9 — `docs/V3-PLAN.md:6` and a "Then
Lookout Lariat" paragraph before Phase 4's "Then Sand Creek" (see Status).*

## Diagnosis

Two things, not one.

**The ribbons are a Sand Creek feature running on a mountain.** `_build_highways` was written to
put Commerce City's interstates beside a flat street circuit, with a freeway's width and a running
mean that is fine on a plain. The Lariat's bbox hands it two canyon freeways, two trunk carriageways
and ~30 ramps; the sampler cannot resolve a benched shelf (L3b), so the decks inherit the canyon
wall's facets; nothing in config can switch the pass off and nothing in the gates measures it. The
"wavy ribbons" are the feature working exactly as written on terrain it was never meant for. Kevin's
"no extra highways" is also the doctrine's answer: route-only drafts (REALISM §8, 0029/0035 "DELETE,
don't compensate"), with a real divided road rendered as one slab plus its median (0037) — never as a
second ribbon.

**The rest is a July build.** The installed Lariat predates every V3 fix class; its own open ledger
(0003 banking, 0010 terrain bind, 0025 roughness) describes a track the engine alone could not
finish. Under V3 the engine's job is the underlay; the switchbacks, the five mouths, the US-6 median
and the bridge at 19th St are authored once, per place, and gated.

## Fix — port the V3 method, in this order

Everything below is the Lake Murray chain applied to a mountain route; no new kind of code path
(the dossier template's own rule). Honest gaps in the chain are marked **[gap]**.

0. **Dossier first** (`fleet/templates/LOCATION-DOSSIER.md` → `tracks/lookout-lariat/DOSSIER.md`,
   Kevin approves before geometry). Sections that decide this build: §2 widths per segment measured
   off the aerial (Lariat Trail 6.1 m, 7.5 at hairpins; `docs/ROAD-CONSTRUCTION.md:71-76` already
   holds the 1913 construction parameters — 6 % max grade, R 15–25 m hairpins, dry-stone walls at
   1:6 batter, stone parapets at drops > 2 m); §3 the real grades (the config's 16 % cap is for
   Paradise Rd's −14.5 %); §4 the switchbacks numbered with imagery; §5 the **real lamp inventory**
   (19th St in Golden, the US-6 interchange, Heritage Square — and whether Lookout Mountain Rd has
   any at all) and the **real sign inventory** at each hairpin; §6 Front Range species per band
   (ponderosa / Douglas-fir / juniper and Gambel-oak scrub on the lower face, denser conifer on the
   N/E aspects — the config's `aspect_favored` idea, now from the dossier); §7 the Golden lighting
   rule — **0043's LPS finding is San Diego's (Palomar) and does not transfer**; Golden/Jefferson
   County lamps are the ordinary HPS → LED history, so the "sodium" hue here is 0043's HPS line
   (`255,183,76`, `SINGLE_FREQUENCY 0.7`), one config line, *after* the dossier confirms which era
   Kevin wants; §10 the look-rows the seat must confirm (below).
   *2026-10-11, from the dossier: Paradise Rd measures −10.3 % over 100 m (−11.5 % worst over 20 m),
   so the 16 % cap never binds (V3-PLAN A7); the OSM hairpins are R≈12–14 m and faceted, so each is
   measured on the aerial and fitted before the road is built (A2); and Gambel oak is dropped, since
   no source puts it on Lookout Mountain (dossier §6a).*
1. **Draft, route-only.** Same `route.roads`; the draft is the lap's ribbon, its own ramp, and the
   terrain underlay — **no `build_env` highways, no `MOUNTAINS`**. In the V3 chain that is by
   construction (SD's draft never runs `build_env`); as a separate engine courtesy for Sand Creek
   and the circuits, `_build_highways` gets a `scenery.highways.enabled` key defaulting to today's
   behaviour (byte-identical elsewhere) — the Lariat sets it false. **[gap]** `tools/ship_sd.sh` is
   hard-wired to the `k10-sd-v021` workshop, the SD slug and SD's quarantined `build_loop_blend.py`;
   `scripts/blender/underlay.py` from REALISM §4 does not exist yet (`scripts/blender/` is empty).
   The Lariat needs the generalised `draft` verb or a `tools/ship_lariat.sh` that reuses the same
   tools against `tracks/lookout-lariat/` — a decision for whoever lands 0047's layout machinery.
   *2026-10-11: V3-PLAN P1 decides it: a generic `tools/ship_track.sh` driven by
   `tracks/<track>/ship.json`, with `ship_sd.sh` left byte-identical.*
2. **US-6 as one slab with its median** (0037 pattern, `tools/median_envelope.py` +
   `author_median_blend.py`): the driven carriageway is the `1ROAD`; the opposing carriageway and the
   median island are authored *on* the same pavement, physics single-coverage, never a second
   ribbon. Kevin's call in the dossier: full divided US-6 vs driven carriageway only. *2026-10-11: the
   same treatment covers the lap's other divided pieces (309 m of Colfax, 105 m of 19th St and, found
   in the second revision, the 85 m divided pair at exit 259); Kevin's options are V3-PLAN D2
   (a)/(b)/(c), each of which says what Reverse drives there.*
3. **Five mouths + the bridge, per `docs/JUNCTIONS.md`** (R1–R9, R18): pad topology at Paradise/US-40
   and US-40/US-6, ribbon-through at the Paradise tee and the gates, the off-ramp butt-welded to
   19th St; every strip terminates at the mouth; the 19th St deck over US-6 held level between
   abutments (L3 "Bridges dip"; 0017 is the failure it prevents). Side-road mouths off the lap
   (Charros Dr, Colorow Rd, the summit lot) are set-dressing mouths (R18c) or omitted — route-only
   means no second drivable road. *2026-10-11: the five mouths are now the corners where the lap
   turns from one road to another: C12 Paradise tee, C14 Paradise → US-40, C15 exit 259, C16 Colfax
   → US-6 and C18 ramp → 19th St (V3-PLAN P3b). The lap reaches US-6 from Colfax, not from US-40,
   and the night gates are not a turn.*
4. **Terrain: fine where the road is, real where it is not** — resolves 0010's bind. 0046 E1 tiers
   (`terrain.tiers`, corridor cells finer than the 6.1 m road per L3b, far cells coarse,
   `far_extent_m` to the Clear Creek Canyon walls and Genesee), `tools/seat_terrain_blend.py` on the
   mainline (its connectors-only restriction lifted, 0046 E3), guardrail/parapet props seated
   **after** the final terrain (0010's fix), far ring visual-only and never a GrassFX occluder
   (`ext_config.py:60-75`). 0046 already names the Lariat its second proof and the L4 case: a far
   shelf must not grab the wrong leg's height on the stacked switchbacks.
5. **Switchback cross-slope** — 0003 is still `open`/`standard`: L10's "streets are not
   superelevated" must be amended before the hairpins get their crown + superelevation; the
   measured-crossfall pass (`data/crossfall.json`, 6 % cap) is the interim, as today. *2026-10-11:
   that file is DEM-estimated, not measured (~10 % of stations at the cap, sign swings within 30 m on
   the climb). V3 re-measures it inside the real-width footprint, under a roll-rate gate (V3-PLAN P2).*
6. **TreeFX with Front Range species** (0040's `tools/make_treefx.py` zones: forest band by elevation
   and aspect, corridor guard half-width + 1 m, no `;` comment lines; L7: every species resolved or
   dropped). `.bin` models stay gitignored under `source/trees/` and ride only the **Full** package;
   the public zip is the **CC0 variant** with `[TREES]` commented and no `.bin` (PUBLISHING.md
   "Licensing — the two variants"; the config's "BUNDLED (personal, non-distributed build)" note
   already says the same). `docs/ASSET-ROLLOUT.md:74`'s overhead-gantry plan for "US-6 canyon +
   I-70/US-40 junction" is void under route-only.
7. **Lamps only where real** (dossier §5): `tools/author_lamps_blend.py` at the surveyed positions,
   not `light_spacing_m 96`; intensity in the 255-scale decade (0043), HPS hue per §7 above;
   `[LIGHT_N]` count = inventory count. Expect a few dozen, not 304.
8. **Arrow signs at the switchbacks** (0044 rule): the hazard-marking face at each hairpin from the
   dossier §4 inventory (US faces, not the Euro atlas the old config planned), placed on true ground
   (dossier §5 rule), nothing collidable in the lane. *2026-10-11: the Euro faces were Kevin's July
   call ("Euro faces per Kevin"), so the switch to US faces is put to him as a reversal (V3-PLAN
   D7), not treated as a defect. The same applies to the July lamps, the alpine grass and the
   concrete-barrier modules.*
9. **GrassFX** per 0045's corrected grammar, occluders = the allow-list.
10. **Full / Reverse** via 0047's layout machinery, with no race overlay: `layouts[]` `direction`
    `forward` / `reverse`, a declared `start` at the stone gates (station 0) in each layout's own
    frame, `race_furniture: false` on both; one road kn5 plus a nodes-only `__<layout>.kn5` spawn
    kn5 per layout from `dummies_<layout>.json` (0047 D — the main kn5 carries no grid); a reversed
    AI draft from the **built** centreline, then one in-game recording per layout (0047 E,
    HANDOFF's rule); the multi-layout folder (0047 F); `drive_test --layout` walked in each
    direction and `verify_kn5`'s per-layout spawn check (0047 G); the L8 sentence 0047 H adds
    (L8, L11, 0016/0026 direction contract). The current `full`/`reverse` pair is 0047's
    `street_port` regression case: a direction pair with no chain.
    *2026-10-11: superseded in part by V3-PLAN D3 (Kevin's race brief, 2026-10-11). By default
    (D3 a) the Lariat gets four layouts: these two street layouts (`race_furniture: false`) plus
    Race anticlockwise and Race clockwise (`race_furniture: true`, one shared race kn5). Under D3 (b)
    it stays the two street layouts described here.*
11. **Gates, then seat**: all four on the built artifact (L5), JUNCTIONS §4 checks at the five
    mouths, then DRIVE-TEST-REPORT. Package as `lookout_lariat` with `ui/preview.png`, honest
    `README`/`CREDITS`/`LICENSES`, tags without `fictional`; release beside every other Colorado zip.

**Cost:** one dossier; the generalised draft/ship chain (**[gap]** above — the only real engineering
item); a 3DEP re-sample at tiered spacing (≈ 7 × 7 km far ring); authoring time for five mouths, one
median, one bridge and ~20 hairpins; TreeFX/GrassFX/lamp/sign lists regenerated; a release. *2026-10-11: the dossier counts 11 corners
of ≥ 135° (the 7 named hairpins among them), four divided slabs (D2), the lid and two C-470 decks
(D5); V3-PLAN's phases replace this estimate.*
**Not in this entry:** Sand Creek's own I-70 decks (its feature, its call), the circuits (no
motorway in their bboxes — `HIGHWAY` is empty there), San Diego (untouched), 0003's law amendment
(its own entry).

## Scope

- **Proof:** `tracks/lookout-lariat` — the only mountain street port, 24.9 km, both directions. The
  deck finding is proven on its installed kn5; the port is proven only in Kevin's seat.
- **Second proof of the shared tools:** 0046's tiers and 0047's layouts land here second; a big
  change in their SD numbers from the Lariat work means the port leaked back.
- **Regression (must not change):** Sand Creek — `_build_highways` keeps its exact output while the
  key defaults on (its decks are its own decision); IMI / Pueblo / Aspen / High Plains / Second Creek
  — no `HIGHWAY` mesh today, byte-identical after; `san-diego-lake-murray` — not touched;
  k10-colorado — not built from, not committed to (retired).
- **Kinds:** `street_port` only; `rally_stage` is the next consumer of route-only + tiered terrain
  (0014's long thin strip), not this entry.

## Verification (decided now, before anything is built)

1. **Road inventory (the "no extra highways" gate).** On the built kn5: **zero** meshes named
   `HIGHWAY*` / `HWYSTRUCT*` / `MOUNTAINS*`; every pavement triangle (any mesh carrying a road
   material or a `1ROAD*` name) lies within half-width + 2 m of the route centreline **or inside a
   declared exemption polygon for authored pavement** (hairpin pads, junction mouths, side-road
   stubs, the Windy Saddle lot, overlooks, the lid, the static C-470 decks, the divided-road slabs:
   V3-PLAN P5); total pavement centreline length within 1 % of each layout's lap. Today: 37.3 km of
   deck, 9.6 km of it within 100 m of the lap. Add the check to `verify_kn5` so it stays true.
2. **Wavy is gone by construction, and nothing else is:** `drive_test` severe 0, kinks ≤ 5/km (SD V3
   reached 4.97; the Lariat's last measure was 68.3; *2026-10-11: a suburban number copied onto
   R≈12 m hairpins, so it is marked invented until it is derived from reference mountain roads,
   per V3-PLAN P5*), obstruction 0, replication vs independent 3DEP
   p95 ≤ 0.5 m; `audit_mesh` B 0, J 0, K hard = 0 at the five mouths (0036's promotion), F not above
   SD V3's 15; `kn5_ground_check` road-over-ground **p95 ≤ 0.10 m AND floating_furniture 0 at the
   same cell size** — 0010's two numbers, finally in one build; the 19th St deck: no step > 0.10 m
   at either abutment.
3. **JUNCTIONS §4 at the five mouths:** pavement single-coverage 0 overlaps, seam-weld binarity 0
   near-misses, junction density ratio in [0.6, 1.0], no dead-end ring inside any mouth polygon.
4. **Terrain is the data:** far ring within 1 m of 3DEP outside the conform corridor; a sightline
   check (0046's `tools/sightline_check.py`) from the 19th St gates toward the Lookout Mountain
   summit and from Windy Saddle toward Golden reaches the real elevation angles; no `MOUNTAINS`
   sine mesh; no terrain vertex below the real canyon floor.
5. **Lamps and signs match the dossier:** `[LIGHT_N]` count = §5 inventory (not 304); every
   `COLOR` 4th term in the 255-scale decade; hue per §7; one arrow/chevron set per numbered hairpin
   in §4, none in the lane. *2026-10-11: superseded by V3-PLAN A5 and D7: arrows face both
   directions at each qualifying corner (≈ 44, the count Kevin approves), chevron runs go only where
   the survey shows them, and the lamp count and sign faces follow Kevin's D7 answers.*
6. **TreeFX loads:** CSP log has no "Failed to load trees"; 0 trees within half-width + 1 m of any
   centreline; species = the dossier's Front Range set; the public zip contains no `.bin`.
7. **Both layouts (0047's checks):** `models_full.ini` and `models_reverse.ini` both list the one
   road kn5 and each its own `__<layout>.kn5`; the road kn5 carries **0** `AC_START`/`AC_PIT`; each
   spawn kn5 carries ≥ `n_pits` `AC_START_n` facing within 25° of the tangent in its own direction;
   `AC_TIME` fires in each; `drive_test --layout` green in each; AI launches and laps in each (T4
   harness). `map.png` orientation checked against the real map (0038's class). *2026-10-11: under
   V3-PLAN D3 (a), the default from Kevin's race brief (2026-10-11), these checks run on all four
   layouts, and the two race layouts' `models_<layout>.ini` also list the race kn5. The facing check
   that shipped in `verify_kn5` is 30° (`HEADING_MIN_DEG`, flagged ⚠ invented), not 25° (V3-PLAN
   P5).*
8. **Kevin's seat (the only verdict that closes it):** T3 = three clean laps each direction; then
   the §10 look-rows: the M-curves read as the real stacked switchbacks with their stone walls and
   parapets; US-40 descends Mt Vernon Canyon with **nothing beside it but the canyon**; US-6 home is
   one divided highway with its median, not two ribbons; nothing drawn in Clear Creek Canyon; the
   Front Range is the real skyline from the summit; night drive lit only where Golden is lit.
   *2026-10-11: stone only where the survey puts it; between stacked legs the ground is rock cut
   and fill (V3-PLAN A3/A4). The night look follows Kevin's D7 answer on lamps.*

## Status update (2026-10-11): dossier and plan written, four corrections

Kevin's "what about lariat" (2026-10-11) puts the Lariat next after San Diego. `CLAUDE.md` already
says so (918d7f1). `docs/V3-PLAN.md`'s "Sand Creek second" still needs the same edit.

Two files are now written:
- [`tracks/lookout-lariat/DOSSIER.md`](../../tracks/lookout-lariat/DOSSIER.md), the LOCATION-DOSSIER,
  awaiting Kevin's approval.
- [`tracks/lookout-lariat/V3-PLAN.md`](../../tracks/lookout-lariat/V3-PLAN.md): phases P0–P7, the
  tool map, budget and gates. It opens with eight decisions for Kevin (D0–D7, each with a
  default), followed by the defaults it applies unless he objects (A1–A13).

Nothing has been built or committed, and no `.blend` has been touched.

Four corrections to the Evidence above, measured read-only today:
1. **The Overpass snapshot does survive.** All 19 data files are in k10-colorado at
   `0a897bb^:tracks/lookout-lariat/data/`, including `osm.widths.cache.json` (2,493 ways,
   2026-07-27).
2. **The extra road set is larger than stated.** `HWYSTRUCT_1` is I-70 running west toward Genesee,
   not the Clear Creek Canyon US-6. C-470 (32 ways, ~5.75 km of deck) is also part of the extra set.
   In all, 202 ways make ≈ 40.6 km of deck.
3. **The twin's `lookout_lariat.blend` is engine output, not a hand-edit workspace.**
   - It is build_kn5's intermediate from the 0024 barrier-winding measurement builds: 0 collections,
     0 text blocks, 0 modifiers.
   - It was saved 2 min 31 s after 62bc1fa and 45 s after 56a0e3d.
   - Archive it; there is nothing to salvage.
4. **A route defect at the ramp terminal.**
   - The `id:` list ends on way 533503214, the ramp's right-turn branch onto 19th St east.
   - That gives a ~190° U-turn at st ~24,250, followed by ~100 m driven the wrong way.
   - The fix is ways 533503210 + 1283267904 (default A1).

Also measured: the lap runs anticlockwise in plan view, although both installed ui files say
clockwise.

### Revision after review (2026-10-11)

A review of the first draft found 25 gaps, 5 of them high severity. Kevin's race brief also
arrived the same day. Both files were revised, and nothing is built or committed. The changes that
matter:

- **The race version is in (D3).** *Second revision: D3 is now an explicit choice, (a) this race
  version (the default) or (b) none; see below.*
  - Kevin, for Lake Murray and the Lariat: *"racetrack versions of these, we need full
    intersections available for turning. And the entire other lane blocked off from access."*;
    *"We want more or less an Alvarado's width for the entire track with deviances in various
    areas"*; open boxes at the *"Corners the race turns at"*.
  - The Lariat gets four layouts: Street Full, Street Reverse, Race anticlockwise and Race
    clockwise.
  - On the 6–7 m mountain road the race uses the whole road one-way, with no K-rail down it or
    along its historic edges. Side roads are closed at their edges.
  - Open boxes at C12, C14, C15, C16 and C18. About Alvarado's width on Golden's multi-lane
    streets. One carriageway on US-6.
  - The race tools are adapted from Lake Murray's corridor run, not forked (dossier §4c).
- **A second wrong-way run.** At exit 259 the July lap drives 84 m against one-way way 42005706
  (st ~16,602–16,686). The fix is its north-east-bound partner 119006778. A one-way check now gates
  P0. Both route fixes are default A1.
- **C-470 crosses over the lap twice,** at st ~19,300 on Colfax and ~21,100 on US-6
  (`bridge=yes, layer=1`). Bare-earth 3DEP keeps the approach fills. The default is static decks
  and abutments only (D5), exempted from the road-inventory gate.
- **The hairpins are faceted in the data.** The base hairpin steps up to 25° between 3 m points,
  and the engine never smooths an OSM line in plan. A hairpin fit plus a heading gate now precede
  the ribbon (A2). Kevin's July 14 m widening is re-asked only after he drives the fitted curve.
- **Road width is Kevin's call (D4).** July gave him ~22.6 m of drivable surface; the real road is
  6.1–6.7 m. Both a real-width edge and a 1–1.5 m firm gravel strip are built for Drive 1.
- **The live public v0.14.0 zip misstates its licences (D0, urgent, separate from V3).**
  - Its CC0 claim covers LA Canyons and Hamburg textures, a TurboSquid-derived tree atlas, and the
    `pine_tree.zip` pines and barrier pack (licences not recorded).
  - The default is to take the Lariat zip down and re-pack any other Colorado zip that carries the
    LA Canyons road texture.
  - Separately, `assets/licenses.json` labels `building_*` as ambientCG Concrete034, but
    `SOURCES.txt` says those bytes were mined from Hamburg.
- **Kevin's July calls are put to him as reversals (D7), not called defects:** the lamps, the Euro
  sign faces, the alpine grass, and the concrete-barrier modules.
- **Walls.** Between stacked legs the default is rock cut + fill (A3). Walls go in only where
  surveyed or genuinely needed, since the Register lists two on the climb.
- **Seating and data.**
  - Seating is station-matched; there is no height window. The stacked-leg gate is defined as
    pairs < 40 m apart on the map and > 150 m apart along the lap: 1,188 pairs on the July line.
  - Only frame-free July data is restored.
  - The lid is declared from the US-6 tunnel footprint. It sits ~550 m before the pylons, not at
    the seam, and both July auto spans are treated as suspects.
- **Views.** A 20–30 m terrain tier now runs to ~3 km on the view side, with a tier-seam check.
  There is an OSM-height Denver skyline option (D6 ii).
- **Gates.** Every new gate threshold is marked invented, and the Drive-1 gate set is named.
  *Second revision: every number is now tagged [std] or [invented] by a stated rule (V3-PLAN P5).*
- **Packaging.** Per-package budgets: the Full install ~145–180 MB with trees, the CC0 zip ~80–100
  MB with no vegetation.

Status stays `open` until Kevin answers D0–D7 (or says "defaults") and approves the dossier.

### Second revision after review (2026-10-11)

A second review found six problems. Both files are revised again; nothing is built or committed.

- **Exit 259 is a divided pair too.** After A1's fix, Full drives the 2-lane north-east-bound way
  119006778 with its arrows, but Reverse would drive it against them; the 4-lane south-west-bound
  way 42005706 is its other half. Exit 259 joins US-6, Colfax and 19th St in D2, whose three options
  now each say what Reverse drives (about 4.6 km against the arrows under the default).
- **Every gate number is tagged** [std] or [invented] in V3-PLAN P5, by a stated rule. Three
  corrections fell out of the tagging:
  - the spawn-facing check that shipped in `verify_kn5` is 30° and flagged ⚠ (the plan said 25°,
    [std]);
  - `audit_mesh` reports J and K without gating them, so 0 at the mouths is new ([invented], was
    [std]);
  - severe steps 0 is new against drive_test's own > 12/km line ([invented], was [std]).

  F ≤ 15 is now labelled as what it is: a relaxation of `audit_mesh`'s hard gate at 0.
- **Stale text in this entry** is annotated inline rather than rewritten: Status, Priority, Fix 0,
  1, 2, 3 and 10, Cost, and Verification 5, 7 and 8.
- **Tree density.** The dossier said Kevin's July *"more trees the higher up"* was kept, while its
  own bands make the top open woodland. The research supports the bands (densest on the
  north-facing upper hairpins, open ponderosa woodland with meadows on top), so it is now D7's
  fifth July call, proposed for reversal.
- **D3 is now an explicit choice.** About Alvarado's width exists only on Golden's streets (15 % of
  the lap, 34 % counting its narrower roads), and no layout can widen the shared mountain road
  (L8). The options are (a) a race version on the real narrow road, the default, or (b) no race
  version. A town-only race loop was checked and dropped: the only loop that closes (≈ 5.2 km via
  Heritage Rd) uses a road outside the lap that is mostly 2 lanes.
- **Physical wording and small fixes.**
  - D5 and D6(i) now say what the driver sees, not which rule applies.
  - The hairpin gate reads (spacing ÷ R_fit) × 57.3° + 1°.
  - The race layouts are due in Drive 3 and slip past it if Lake Murray's tools are late; P1 now
    matches A13 and the risks.
  - The July install is 559 MB (534 MiB), not "534 MB".

## P0 done (2026-10-11)

P0 is committed (airoso 324ec41), and its done-when list (V3-PLAN P0) is met. Each item has its
artifact. Status stays `open` and the tier stays T0: there is no geometry, kn5 or Blender build.
- **`fleet.cli tracks`** lists `airoso/lookout-lariat` at 0.16.0. **`fleet.cli lint`** exits 1 on
  two FAILs, S0 (k10-san-diego not found) and S3 (engine pins disagree). Both failed before P0 too,
  so none is new. Re-run after the follow-ups below: same result.
- **`data/source-july/`** holds the five July files, byte-identical to k10-colorado `0a897bb^`
  (`git hash-object` matches all five), with `PROVENANCE.md`.
- **The centreline is re-derived:** 24,890.8 m, 8,302 points, closed. The ramp end is an ordinary
  left, about +87° over 12 m. No vertex turns more than 90°, and July's 168° U-turn is gone.
- **The one-way check** (`data/oneway_check.json`): Street Full runs 0 m against a one-way way.
  Street Reverse runs 4,486.5 m against, all of it on its four declared D2 stretches. The race
  layouts are not checked.
- **Kevin sees** `data/route_map.png` and `data/route_map_switchbacks.png`, both sent to him. They
  show corners C0–C18, both route fixes before and after, the five race boxes and the two C-470
  crossings. The script that draws them lives in session scratch, not the repo.

**Three deviations from the plan's letter, for Kevin:**
- **A1 needed one more excluded way:** 533500102, 19th St's eastbound side. With only the two
  ramp-end ids, the lap still ran 59.6 m against its arrows.
- **D2 totals 4.49 km, not ~4.6.** 19th St is 54 m on its westbound side; the 105 m was the
  eastbound side July drove.
- **The street layouts are `street_full` and `street_reverse`,** because `tools/layout_dummies.py`
  refuses the id `full`.

**Follow-ups after the commit (on disk, uncommitted):**
- **Every Python HTTPS fetch now verifies through `scripts/tls.https_context()`.**
  - Eight more modules route their fetches through it: buildings, zones, trace/osm, build_seed,
    map_overlay, usgs_3dep, srtm and `tools/fetch_osm.py`.
  - `scripts/elevation/srtm.py` had verification switched off (`CERT_NONE`). That is removed, and
    opentopodata, Open-Meteo and USGS 3DEP verify live through the engine's own transports.
  - `tests/net/test_https_everywhere.py` scans `scripts/`, `tools/`, `fleet/` and `tracks/` and
    fails on any call that skips the context or weakens verification. Lake Murray's frozen
    `scripts-v021/` is not scanned and keeps six unrouted calls; that track owns it.
- **P0 step 1's diagnosis is corrected on paper.** The cause was the expired cross-certificate
  "ISRG Root X2, issued by ISRG Root X1" in the Windows Intermediate store, which Python loads as a
  trust anchor. It was not Python's own store or `certifi`, which `urllib` never reads. V3-PLAN P0
  step 1 and risk 11 are fixed, and so are dossier §9 and §11.
- **Stale mirrors.**
  - `widths_from_osm` now names the mirror that answered and its OSM data timestamp. It refuses to
    snapshot data older than `route.osm_max_age_days` (default 7) unless run with
    `--allow-stale-osm`. Tests: `tests/gps/test_widths_osm_freshness.py`.
  - overpass.kumi.systems was serving OSM as of 2026-07-28. The July snapshot itself holds OSM as
    of 2026-07-02, fetched on 07-27.
- **OSM retag.**
  - OSM now tags exit 259's pair, ways 42005706 and 119006778, as `secondary` with no name. The
    dossier, from July data, had them as `primary` "Lariat Loop Scenic Byway".
  - All 26 lap ways on I-70 Business and Colfax (3.66 km) changed the same way, with the same
    lanes.
  - In the mountain width table each of them drafts 1.0 m narrower, for example 119006778 goes
    from 10.0 to 9.0 m. Dossier §2a has the detail.
- **Tests:** `tests/run_tests.py` 470 passed, 0 failed.

**Still owed:**
- the GATES-CHANGELOG entry for the one-way gate (that file belongs to the race-corridor run);
- C9's hairpin fit, at 2.04 m against the invented 1.5 m limit;
- P1 onward.
