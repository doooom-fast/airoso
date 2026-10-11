# Lookout Mountain Lariat — V3 build plan

> **2026-10-11, revised twice the same day after review. This is a plan only: nothing is built
> and nothing is committed.**
> - The facts behind it are in [`DOSSIER.md`](DOSSIER.md); the ledger entry is
>   [0048](../../fleet/feedback/0048-lookout-lariat-rebuild-v3-style-no-extra-highways.md).
> - Priority: the Lariat is next after San Diego (`CLAUDE.md`, commit 918d7f1). Two status lines
>   elsewhere are stale and get fixed together in one change outside these files (P0 step 9):
>   `docs/V3-PLAN.md` still says "San Diego first, Sand Creek second", and
>   `fleet/DEFINITION-OF-DONE.md:45` lists the Lariat at T0 without saying the current pin fails.
>   *(Both fixed in P0, commit 324ec41.)*
> - *2026-10-11, after P0 (commit 324ec41):* P0 step 1's diagnosis is corrected, A1 needed one more
>   excluded way, and D2's total is measured (4.49 km). Each is noted where it applies; ledger 0048
>   records P0.
>
> Kevin's asks:
> - 2026-10-10: *"rebuild lookout mountain in the same high fidelity style with all of the fixes
>   applied, and no extra highways (they look like wavy ribbons now)"*.
> - 2026-10-11: *"what about lariat"*.
> - 2026-10-11, the race brief for "these" tracks (Lake Murray and the Lariat): *"racetrack
>   versions of these, we need full intersections available for turning. And the entire other lane
>   blocked off from access."* · *"We want more or less an Alvarado's width for the entire track with
>   deviances in various areas"* · open intersection boxes at the *"Corners the race turns at"*,
>   side streets sealed.

## Decisions for Kevin

**Eight questions. "Defaults" is a complete answer.** They are ordered by what they hold up first.

| # | Question | Default | Why |
|---|---|---|---|
| **D0** | **Take the Lariat download that is public right now down, or re-pack it?** Urgent, and separate from V3. It is k10-colorado v0.14.0, `lookout_lariat_ai.zip`, listed on doooom.fast. Its credits say everything in it is free to share (CC0). It isn't. The road, dirt and bush textures were taken from the LA Canyons mod. The concrete texture was taken from the Hamburg mod. The tree pictures are a TurboSquid-derived sheet. The 3D pines and the concrete barriers come from your own model packs, whose licences aren't on record. | **Take the Lariat zip down now.** That's your click on the release; I prepare the matching catalog edit in prodrive-server. Once `gh` is logged in, I check the texture lists of the other five Colorado zips. Any that carry the LA Canyons road texture (the engine's default road texture) get re-packed with `tools/repack_kn5_textures.py` plus honest credits. | A texture swap can't take the tree and barrier models out of the Lariat file. If you know both packs allow sharing, say so: I re-pack the Lariat instead (free textures, blank tree sheet, honest credits) and it stays listed. |
| **D1** | **Keep the lap's double-back at Colfax, or take Heritage Rd like the real byway?** At the US-6/Colfax signal the lap turns 152° back on itself, then runs 1.9 km back beside the Colfax it just drove. Keeping it gives 24.9 km; Heritage Rd gives ≈ 22.7 km with no reversal. | **Keep it.** The in-game text says the turn is unverified. | It is the lap you have driven, and the length doooom.fast lists. Nobody has confirmed the turn is legal. |
| **D2** | **Four stretches of the lap are one side of a divided road. What does Reverse drive there?** The four: US-6 plus its off-ramp to 19th St (4.1 km), 309 m of Colfax, 105 m of 19th St, and 85 m at exit 259. *(Measured on the P0 line: 4,035.1 m, 311.6 m, **53.6 m** of 19th St's westbound side (the 105 m was the eastbound side July drove; see A1) and 86.2 m; 4,486.5 m in all.)* At exit 259 the lap (after A1) takes the 2-lane north-east-bound side, OSM way 119006778; the 4-lane south-west-bound side, way 42005706, is the other half. Full drives all four with the arrows. Reverse, driving the same line backwards, would drive all four against them.<br>**(a)** Build each as one piece of pavement carrying both sides and the real median. Every layout drives the Full side, so **Reverse drives all four stretches against the arrows, about 4.6 km in all, including the 85 m at exit 259**, and its in-game text says so. *(P0 measured 4.49 km: `tools/route_oneway_check.py`, `data/oneway_check.json`.)*<br>**(b)** As (a), plus a second route so Reverse drives each stretch the legal way: US-6's other carriageway, the 19th St → US-6 on-ramp (way 642334992), 19th St's eastbound side at the ramp terminals, the southbound Colfax approach, and exit 259's south-west-bound side (way 42005706). Reverse then gets its own centreline and a different lap length. This brings back, as real road, the opposite carriageway that today's build draws as one of the ribbons beside the return leg (26 ways, ~1.3 km).<br>**(c)** Only the side Full drives, with no median and ground beside it. Reverse drives that single side against the arrows on all four stretches, and its in-game text says so. | **(a): one slab with its real median; Reverse drives the four stretches against the arrows, and its text says so.** | It looks like the real divided road without adding a second route. If D3 keeps the race version, its layouts close the other side anyway. |
| **D3** | **Does the Lariat get a race version, when its mountain road is half Alvarado's width?** Your race brief asks for *"more or less an Alvarado's width for the entire track with deviances in various areas"*; Alvarado is about 13 m curb to curb. On the Lariat only Golden's streets come near that. I-70 Business and Colfax (2–6 lanes) are 3.7 km, 15 % of the 24.94 km lap. Add US-6's 2-lane carriageway, the ramp and 19th St and Golden is 8.4 km (34 %), but those are narrower. The 6 km climb is 6.1–6.7 m; the summit and back side are 2-lane roads and Paradise Rd is unmeasured; US-40's three canyon lanes may come close once measured. Every layout drives the same road surface (rule L8), so a race layout cannot make any of it wider.<br>**(a) A race version on the real narrow road.** Race anticlockwise and Race clockwise, beside Street Full and Street Reverse. The race runs one way over the whole mountain road, edge to edge: half Alvarado's width on the climb, with its real stone, steel and open edges and nothing added in it or along it. Every side road is closed with a barrier at its edge. The five corners where the race turns from one road to another (the Paradise tee, Paradise → US-40, exit 259, Colfax → US-6, ramp → 19th St) are open boxes. Golden's multi-lane streets are narrowed to about Alvarado's width with lane barriers, and on each divided stretch (D2) the race keeps one side, with every gap to the other side closed.<br>**(b) No race version of the Lariat.** Street Full and Street Reverse only: no race barriers, no race file, and no wait on Lake Murray's race tools.<br>*Checked and dropped: a race only on a town loop that has Alvarado's width.* The only loop that closes in Golden (≈ 5.2 km: Colfax → US-6 → Heritage Rd) needs 1.5 km of Heritage Rd, which isn't part of the lap, and Heritage Rd is mostly 2 lanes, like US-6's carriageway, so it doesn't have Alvarado's width either. | **(a): a race version on the real narrow road, one-way, half Alvarado's width on the climb.** | It is the race you asked for, on the road that is really there; width is the one part of the brief the mountain can't give, and the race arrives last (Drive 3), so nothing waits on it. Pick (b) if Alvarado's width was the point. |
| **D4** | **How wide is the mountain road under your wheels?** The July Lariat you have driven has about **22.6 m** you can drive on: a 9.8 m road plus 6.4 m of drivable shoulder each side. The real road is **6.1–6.7 m** with no shoulder. **A:** real width, then the real edge (rock cut, ditch or drop). **B:** real pavement plus a 1–1.5 m firm gravel strip each side that you can put a wheel on. | **Build both for Drive 1** (two installs, identical apart from the edge), and you pick by driving. | The July shoulders went in because the narrow lane, lined with rumble-strip lips, was *"undriveable slop"* (your words, July). The lips are gone either way, so only the seat can say whether the real width is enough. |
| **D5** | **Where C-470 crosses over the lap: build its bridges, or dig its embankments away?** The lap passes under C-470 twice: on Colfax at st ~19,300 (both directions plus two ramps) and on US-6 at st ~21,100. With C-470's road removed, its two approach embankments stand on either side of the lap with a gap in the air between them. The bridges would be scenery only: deck and abutments, no road on top, nothing running along the lap. | **Build the bridges.** | That is what is really there, overhead. Digging the embankments away would replace real ground with made-up ground, and a bridge you pass under is not the wavy ribbon beside the road you asked to remove. |
| **D6** | **The views: let the real mountains stand at their real height, and add a Denver skyline?**<br>**(i)** Let the real mountains, Clear Creek Canyon and Golden stand at their real height. Near the road (out to ~60–100 m) the ground stays shaped to the road, as now; beyond that it blends back to its real surveyed height within a few hundred metres. Today a written rule (L3) presses all ground to within 22 m of the nearest road's height. Changing that is a one-line edit to rule L3, the same one Lake Murray asks for to bring back Cowles Mountain (ledger 0046).<br>**(ii)** Add a low-poly Denver skyline, built from OpenStreetMap building heights at its real bearing? It would be visible from the lower hairpins up. | **(i) Yes. (ii) Yes, after Drive 2.** | (i) The lap climbs 505 m. Under the rule as written, Clear Creek Canyon below Wildcat Point and Golden below Windy Saddle would be lifted to within 22 m of the road: no canyon and no town below you. (ii) The skyline comes from mapped building heights, so it is the real skyline, not an invented one. |
| **D7** | **Five of your July calls: keep them, or swap each for what is really on the road?**<br>1. *"Streetlights ON per Kevin: yellow, 96 m, dim wide pools"* → lamps only where they really stand: a few dozen in Golden, exit 259, Johnson Rd and 19th St, in warm sodium orange. The mountain and the canyon are dark. Night stays available, and your wide, dim pool shape stays.<br>2. *"Euro faces per Kevin: … 70 disc on the climb, 110 discs on the plains legs"* → US signs: the real 20 mph limits and advisory plaques where they are mapped, plus the yellow arrows from your approved 0044 rule.<br>3. *"Alpine grass instead of dry dirt (Kevin)"* → tawny late-summer grass.<br>4. *"Kevin's model pack: 4 m concrete barrier modules instanced along warning-barrier runs"* → the road's real edges: 1913 stone guardrails and walls, steel W-beam where it really is, and open edges where it's open. The module stays for the one real concrete barrier at the summit and for the race closures (D3).<br>5. *"more trees the higher up"* (the July forest ran *"sparse at the Golden base, dense at the Buffalo Bill summit"*) → trees where the real forest is: thickening from the bare lower east face to the closed pine and Douglas-fir canopy of the north-facing upper hairpins, then opening into ponderosa woodland and meadows over the summit and the back side (dossier §6a). | **Reverse all five.** | Each one swaps a stand-in for what is really on that road. Tell me any you want to keep. |

### Defaults I will apply unless you say otherwise

- **A1 — Two route fixes.**
  - The ramp end turns left onto 19th St west (OSM ways 533503210 + 1283267904, replacing 533503214). Today it makes a ~190° U-turn and runs ~100 m the wrong way up a one-way.
  - Exit 259 uses the northeast-bound way 119006778. Today the lap drives 84 m up the southwest-bound way 42005706.
  - A check fails any build whose lap runs against a one-way. Both defects are errors in the July route list, not choices.
  - *P0 deviation (2026-10-11), for Kevin:* the two ramp-end ids on their own still left the lap
    59.6 m against the arrows on 19th St's eastbound one-way way **533500102**: the 19th St path
    ran on the eastbound side, and the ring is cut at the ramp node, so 1283267904 was never
    driven. `route.exclude_ids` drops 533500102 as well as 42005706 (the same mechanism as exit
    259), so the left turn runs 1283267904 → 1106864351 → 533504135 on the westbound side, with
    the arrows. That is A1's intent with one more excluded way. It shortens D2's 19th St stretch
    to 54 m and the D2 total to **4.49 km** (4,486.5 m), not ~4.6 km.
- **A2 — The hairpins become smooth curves before the road is built.** Each hairpin is fitted as an arc or transition curve at the radius measured on the aerial, and a gate checks the turn is smooth from point to point.
  - Today's line kinks up to 25° between 3 m points at the base hairpin, and that is likely what made it "impossible".
  - Your July widening there (14 m; *"the turn on the mountain route is impossible"*) is **off for Drive 1** but one switch away.
  - I ask again after you have driven the smoothed curve.
- **A3 — Rock cut and rock fill between stacked hairpins.** Between stacked hairpin legs the ground is a rock cut above and a rock fill below, the way the 1913 crews built it. Stone walls go in only where the survey shows them, or where the slope cannot close without one, and those are labelled authored. The National Register lists two walls on the climb; walls at every hairpin would invent Register structures.
- **A4 — The 1913 stone works are built as themselves:** the pylons, the stone guardrails with their gaps, the Wildcat Point walls, Sensation Point's wall and the Windy Saddle walls. W-beam goes only where it really is. A Street View pass decides which edge is which. Where the survey is silent, a drop-height rule decides and the run is labelled authored.
- **A5 — Signs come in one pass.** The mapped 20 mph limits and advisory plaques go in first.
  - The rule-placed yellow arrows are authored, since none is mapped. I count them for you on the preview map before building: about 44, which is 14 corners × 2 directions plus the hairpins' second plates.
  - At a stone guardrail, the post stands on real ground behind the wall, or the sign is left out.
- **A6 — No banking: the road is not tilted into the hairpins, because the real one isn't** (rule L10; ledger 0003 stays open). The sideways tilt is re-measured at the real width and gated for smoothness. Until a lidar sample agrees, it is called "estimated", not "measured".
- **A7 — The grade cap stays at 16 %.** It never binds: the steepest 20 m on the lap is −11.5 %. July's 6 % cap "floated the road metres above the canyon floor". Any change is gated on the road still matching the 3DEP elevation data, checked before and after.
- **A8 — Trees.** The trees are TreeFX stand-ins already on this machine, zoned by which way the slope faces and by height band (dossier §6a; how dense the top is follows D7 item 5). They ship in the Full package only, so the public zip has no vegetation.
- **A9 — Golden looks like Golden.**
  - Buildings: OpenStreetMap building footprints within ~150 m of the road on the town stretches (Beverly Heights, the back side, Paradise Rd, Colfax/Heritage, 19th St).
  - Kerbs and sidewalks where they are real.
  - Short, non-drivable stubs for the ~45 named side roads, so a signal junction has a road crossing it.
- **A10 — Golden's three speed humps are left out of the first build.**
- **A11 — One name.**
  - Every file inside is `lookout_lariat`.
  - The folder on this machine is `lookout_lariat_v3` while the July build stays installed.
  - July is parked only after V3 reaches T3 (three clean laps each way).
  - The release zip's folder is `lookout_lariat`, so it replaces the old public copy.
- **A12 — The public V3 zip comes after T3.**
  - It carries free textures, the two street layouts and no trees.
  - The race closures use the barrier pack whose licence isn't recorded, so as on Lake Murray they stay in the Full package. The Full package stays local.
- **A13 — Three drives.**
  1. Road + ground, in both widths (D4).
  2. Adds edges, signs, trees, lamps and buildings.
  3. Adds Street Reverse, the two race layouts if D3 keeps them, and the AI.

**Asked again later, not now:** the base hairpin's widening (after Drive 1); the width pick (in Drive
1); the one photo that sets the mood (dossier §7).

## The short version

- **Same method that shipped Lake Murray.**
  1. The engine draws a first draft of the road and the ground.
  2. Claude shapes it in Blender with scripted tools.
  3. The gates check the built file.
  4. Kevin's drive decides.
- **The road set is the lap and nothing else.**
  - The "wavy ribbons" were never route data. They come from a Sand Creek feature that lays 22 m
    freeway decks beside the road; on the Lariat it lays ~40 km of them (I-70, C-470 and ramps).
  - The V3 draft never runs that feature, so the ribbons are gone by construction, and a new gate
    proves it on every build.
  - Two kinds of structure cross the lap and stay, as structure only:
    - the C-470 bridges overhead (D5);
    - the 19th St lid.
- **Four pieces of real engineering, all things San Diego never needed:**
  1. A ship chain that isn't hard-wired to San Diego.
  2. Smooth hairpins. The OSM line is faceted, and the engine never smooths an OSM line in plan.
  3. Mountain ground: cut and fill seated leg by leg on stacked switchbacks that sit 6.5–14.7 m apart
     vertically and 20.5 m apart on the map at the closest. Plus real terrain out to the views.
  4. If D3 keeps it (the default), a race version on a 6 m road, on the corridor rules Lake
     Murray is landing now.
- **Expected size.**
  - The Full install comes to about 145–180 MB, against 559 MB installed today (the folder; its
    track file alone is 550 MB). The TreeFX tree models are ~60 MB of the 145–180 MB.
  - The public zip comes to about 80–100 MB (budget below).
- **Three drives, not one** (A13).

## Where it stands today

| | State |
|---|---|
| Installed | `content/tracks/lookout_lariat`, built 2026-07-27 (engine v0.46.0, config 0.15.0). 550 MB track file: trees are 62 % of it, the highway decks under 1 %. Full + Reverse share one start grid, and Reverse spawns facing forward |
| Public | k10-colorado **v0.14.0** `lookout_lariat_ai.zip` (311 MB) on doooom.fast. **Its CC0 claim is false (D0).** The installed kn5, which is that build, binds `asphalt_cracked_*`, `ground_dry_diffuse` and `bushes_atlas` (LA Canyons, personal use only), `building_*` (Hamburg / TextureCom), `conifer_atlas` (TurboSquid-derived), `pine_leaves` + the 3D pine geometry (`pine_tree.zip`, licence not recorded), `concrete_barrier_*` + its model (`UNRECORDED` in `assets/licenses.json`), and `stone_tan` (source not recorded). Separately, `assets/licenses.json` lists `building_*` as ambientCG Concrete034, while `assets/textures/SOURCES.txt` says those bytes were mined from Hamburg. That record needs fixing (outside this change) |
| airoso `tracks/lookout-lariat/` | `track.config.json` (July-era), `source/route-notes.md`, and now `DOSSIER.md` + this plan. No `data/`, no `.blend`, no `ai/` |
| Recoverable | all 19 July data files at k10-colorado `0a897bb^:tracks/lookout-lariat/data/`, including a full Overpass snapshot (2,493 ways). Ledger 0048 first said none survives; it is corrected |
| The twin's `.blend` (587 MB, Aug 8) | **engine output, not hand edits.** It was saved minutes after the 0024 barrier-winding commits, and has 0 collections, 0 scripts and 0 modifiers. Archive it; there is nothing to salvage. Vertex-level edits can't be ruled out, which is why it is archived rather than deleted |
| Last gate run | engine v0.66.3 (2026-08-09): drive_test **FAIL**. Severe steps 1,033 (41.7/km), kinks 108.9/km, soft-top-in-lane 1,940, floating furniture 33, worst step 4.46 m at st 5,357 |
| DoD tier | the DoD file lists **T0**. True only of the July v0.46.0 build; the current pin fails drive_test. No drive report exists, so nothing above T0 is claimable |

## Engine choice

**Use airoso's own `scripts/`, the lineage that built the installed Lariat, for the first draft
only.**

| Use | From | Why |
|---|---|---|
| Route, widths, elevation, crossfall, bridge spans, projection | airoso `scripts/gps`, `scripts/elevation`, crossfall, span detection | it already knows this route. It drops motorways from `ref:` matches, has the `mountain` width profile, and samples 3DEP along the corridor |
| Road ribbon (the road as a strip of connected rectangles laid along the centreline) | airoso `scripts/geometry/ribbon.py` | it narrows the inside edge where a tight corner would fold the strip over itself, and it has the crossfall hook and a rural shoulder. SD's v021 ribbon has none of these. It ribbons whatever line it is given, so the hairpin fit (P2) runs first |
| Prep, exporter, spawn builder, materials | airoso `scripts/ac/build_kn5_loop.py`, `export_kn5_addon.py`, `build_spawn_kn5.py`, `pbr.py` | the last three are byte-identical to engine-july's. The prep needs three fixes first (P1) |

**Not used:**
- **engine-july**: a dangling worktree nothing commits to. A second consumer would trip SD's
  snapshot test the first time anyone patched it.
- **SD's `build_loop_blend.py`**: quarantined. It is built for a city: sidewalks on every edge, the
  ±22 m terrain clamp, the I-8 trench, palms, a scene reset that wipes authored work, no crossfall,
  no fold guard. Its OSM building pass (`:419-491`) is the one piece worth porting, and it gets
  ported into the underlay (P2) rather than run in place.
- **The engine's own mesh + environment stages**: these fail drive_test on this track at v0.66.3,
  and the environment stage is what adds the highways, the sine-wave mountains and the baked forest.

## Phases

Each phase lists its tools, what "done" means, and what Kevin sees. Tool status is marked
**reused** (as-is), **adapted** (opt-in change, SD output byte-identical), or **new**.

### P0 — Import, correct, make runnable (no geometry)

1. **Fix Python's HTTPS trust first.** *(Corrected 2026-10-11 after P0 ran it. This step first
   blamed a stale Python trust store and proposed refreshing `certifi`. `urllib` never reads
   `certifi`, so that would have changed nothing.)*
   - Overpass failed in Python with "certificate has expired" while curl worked. **The cause is in
     the Windows Intermediate ("CA") certificate store, not in Python:** it still holds Let's
     Encrypt's 2020 cross-certificate "ISRG Root X2, issued by ISRG Root X1", which expired
     2025-09-15. Python's default context loads both Windows stores (Trusted Root and
     Intermediate) as trust anchors, so OpenSSL takes that expired copy and fails. overpass-api.de
     sends a valid 2026 cross-certificate for the same link (leaf → YE2 → Root YE → Root X2 →
     Root X1). curl uses Schannel, so Windows itself verifies the chain, finds the valid path and
     succeeds. Of the engine's hosts, only overpass-api.de's chain runs through that link.
   - **The fix:** `scripts/tls.https_context()` hands verification to the operating system's
     verifier (`truststore`, the library pip uses), with hostname and chain checks on. No
     certificate store was edited. Every Python HTTPS fetch in `scripts/`, `tools/`, `fleet/` and
     `tracks/` now passes `context=https_context()`, and `tests/net/test_https_everywhere.py` fails
     on any that doesn't. Lake Murray's frozen trees of record (`scripts-v021/`,
     `engine-july-snapshot/`) are not scanned; six unrouted `urlopen` calls remain in five files of
     `scripts-v021/`.
   - **Never disable verification.** `scripts/elevation/srtm.py` had turned it off
     (`CERT_NONE`) for the same symptom. That is removed, and opentopodata, Open-Meteo and USGS
     3DEP are shown to verify through `https_context()`.
   - The widths stage fetches over `urllib` (`scripts/gps/widths_from_osm.py`, `_overpass`), and
     its cache fingerprint depends on the bbox. So any bbox change after D1 forces a live re-fetch,
     and that must work. Its mirror fallback now names the mirror that answered and the OSM data
     timestamp it served. It refuses to snapshot data older than `route.osm_max_age_days` (default
     7) unless run with `--allow-stale-osm`. overpass.kumi.systems was serving OSM as of
     2026-07-28.
2. **Restore only frame-free July data, into `tracks/lookout-lariat/data/source-july/`.** Copy with
   `git -C ../k10-colorado show 0a897bb^:tracks/lookout-lariat/data/<file>`, and never check out the
   retired repo.
   - **Restored:**
     - `osm.widths.cache.json` (the 2,493-way Overpass payload);
     - `osm.ways.json`;
     - `centerline.geojson` (lon/lat; a reference to compare the re-derived line against);
     - `corridor.elev.json` (1 m 3DEP samples keyed by lon/lat stations; reference only);
     - `environment.geojson` (reference only, never built).
   - **Not restored, regenerated instead:** everything keyed to the July frame or July stations.
     That is `finished_centerline.json` (mirrored), `centerline.local.json`, `crossfall.json`
     (4,159 July stations), `bridge.spans.auto.json` (24,802.6 m built frame), `dummies*.json`,
     `heightfield.npy`, `flat_zones.json`, `drive_test.json` and `street_labels.json`. Ledger 0015
     (two station frames, one key) and 0038 (the mirror) are what reusing them would repeat.
   - A `PROVENANCE.md` beside the restored files records each file's source commit and fetch date.
     Every regenerated file records its frame.
3. **Make the route step runnable offline.** Store a fresh Overpass payload where the gps stage reads
   its cache, with the fetch date. Verify the cache format against the stage before relying on it.
4. **Archive the twin's `.blend`** (+ `.blend1`, 1.17 GB) to `D:/k10-track-archive/`. This clears
   V3-PLAN Phase 0's Colorado item for this track.
5. **Registry.** Point the Lariat at `airoso/tracks/lookout-lariat` in `fleet/registry.json`, and
   confirm `fleet.cli tracks` resolves it there. Today a fleet build would build in the retired repo.
6. **Rewrite the config from the dossier.**
   - **Route:**
     - A1's two fixes: the ramp-end ways, and exit 259's way 119006778 in place of 42005706.
       *(P0 also excluded 533500102; see A1.)*
     - D1.
     - The grade cap stays at 16 % (A7).
     - Exit 259 needs a way to drop one OSM way from a `ref:` match. A new opt-in route key (e.g.
       `exclude_ids`) in `scripts/gps` does it, with every other track byte-identical. The aerial
       confirms 119006778 first.
   - **Frame:** switch to the loop frame used by every V3 tool (`mirror_x` false, true north 0).
     Every coordinate moves, so the July AI lines, map and light positions regenerate.
   - **Layouts (D3):** in ledger 0047's form, `full` and `reverse` (street,
     `race_furniture: false`), plus, under D3(a), `race_acw` and `race_cw`
     (`race_furniture: true`). Each has a `direction`, a declared `start` at the pylons facing its
     own way, and `ui_description` / `run` text that says anticlockwise or clockwise truthfully.
     Under D2(a) or (c), Reverse's text says it drives the four divided stretches (~4.6 km;
     measured in P0, 4.49 km) against the arrows. *(P0 named the two street layouts `street_full`
     and `street_reverse`, because `tools/layout_dummies.py` refuses the id `full`.)*
   - **Width:** `widths` overrides from the dossier; the D4 A/B verge as one parameter
     (`road_profile.verge_m`: 0.4 for A, 1.25 for B).
   - **July build knobs to drop:**
     - `tree_cap`, `fill_*`, `forest3d`, `corridor_refine_factor`, `pylons`;
     - the `fictional` tag;
     - the `wide_corners` 14 m entry, off for Drive 1 (A2), kept in the config's history so it is
       one switch away.
   - **Knobs that follow D7:** `light_spacing_m 96`, the Euro `road_signs` plan,
     `props.concrete_barriers`, the alpine-grass texture override, and the TreeFX forest ramp
     (`by: elevation`, densest at the summit). They are dropped only for the items Kevin reverses.
   - **New blocks:**
     - `treefx` zones (dossier §6);
     - streetlight intensity in the 255-scale range (0043);
     - `grassfx` in 0045's grammar;
     - `terrain` tiers (P3a);
     - `race` corridor, open boxes and closures (dossier §4c);
     - `install_folder` (A11).
7. **Re-run the centreline.**
   - **Length:** expect 24.9 km, or ~22.7 km if D1 picks Heritage Rd.
   - **No reversal** at the ramp end or at exit 259.
   - **No step at the seam**, where the lap closes on itself (L13).
8. **A one-way check (new, `tools/route_oneway_check.py`).**
   - It map-matches the re-derived centreline to the snapshot and lists every `oneway=yes` way the
     Full direction drives against.
   - It must list **none**.
   - Under D2(a) or (c), Street Reverse lists its four divided stretches as declared exceptions,
     and nothing else; under D2(b) it lists none.
   - The race layouts are closed roads and are not checked.
9. **Corrections on paper, in one change with Kevin's say-so:**
   - `docs/V3-PLAN.md`'s priority line;
   - `fleet/DEFINITION-OF-DONE.md:45` → "T0 (July v0.46.0 build only; current pin fails drive_test)";
   - `assets/licenses.json`'s `building_*` provenance;
   - ledger 0048's Evidence (done inline in this change).

**Done when:**
- `fleet.cli tracks` lists the Lariat at airoso, and `fleet.cli lint` shows no new failures;
- `data/source-july/` is restored with provenance;
- the centreline is re-derived with an ordinary left at the ramp end;
- **the one-way check finds no wrong-way run on any one-way way in the Full direction.**

**Kevin sees:** a route map with corners C0–C18 numbered, both route fixes drawn, the five race-turn
boxes marked, and the two C-470 crossings marked, before any geometry (L12, show-don't-assert).

### P1 — A ship chain that isn't San Diego

`tools/ship_sd.sh` installed SD's three versions. Its exact text is pinned by
`test_ship_sd_chain.py` and `test_engine_july_snapshot.py`, so **it stays byte-identical**.

- **New `tools/ship_track.sh <track>`, driven by `tracks/<track>/ship.json`.**
  - `ship.json` picks steps from a closed vocabulary. Each step name maps to a function written in
    the script. An unknown name exits 2. No command string from JSON is ever executed.
  - Copied verbatim from `ship_sd.sh`:
    - `set -euo pipefail`;
    - `--python-exit-code 1` on every Blender call;
    - absolute paths only;
    - scratch isolation: a scratch project never syncs back and never installs;
    - refusal to work inside airoso;
    - `--dry-run`, `--skip-blend` and `--force-install`.
  - **Race stages run** only when a layout declares `race_furniture` (two do under D3 a).
  - The install folder comes from config (A11).
- **New `tests/tools/test_ship_track_chain.py`.** It covers:
  - stage order and the exit-code flag;
  - the scratch rails and the closed vocabulary;
  - "no engine-july unless the slug is SD".

  Only after `ship_track.sh san-diego-lake-murray --dry-run` reproduces `ship_sd.sh`'s step sequence
  and an md5-identical `split_manifest.json` may `ship_sd.sh` become a two-line shim. That is
  optional.
- **Three preconditions in airoso's prep (`scripts/ac/build_kn5_loop.py`).** These come before the
  Lariat ships through it.
  1. **Frame bug.** `_corridor_hash` builds from `finished_centerline.json` in the kn5 frame
     (north/south flipped) but is queried in Blender's frame. It would cull trees and verges in the
     mirror-image places. Prove it and fix it.
  2. **Tiling.** Split meshes by balanced halving, at ≤ 50k positions per piece (AC's hard cap is
     65,535). Today's equal-width bands overflow where switchbacks bunch up.
  3. **Stacked legs (L4): station matching only.** Every point that seats onto a surface carries the
     arc station of the road leg it belongs to, and seats against that leg's own stretch of road.
     - No vertical-window variant: the smallest gap between legs is 6.5 m, so a window under 6 m
       leaves under 1 m of margin. It also misreads ground points on a ~30 % side slope.
     - The same station matching goes into every "seat onto the nearest surface" tool:
       `seat_terrain_blend`, `place_signs`, the edge and closure authoring, and the prep's
       `LAYER_WIN`.
- **The race tools come from Lake Murray, not a fork.** The Lake Murray corridor design run (in
  progress, 2026-10-11) is reshaping the race tools for the same brief:
  - per-direction corridor, closure barriers, open boxes, and a no-route-to-the-other-side gate;
  - the tools are `race_furniture.py`, `barrier_bands`, `author_race_furniture_blend`,
    `verify_race`, `check_race_kn5` and `plot_race_furniture`.

  The Lariat **adapts what that run lands**: SD's hard-coded `STREETS` become a `race` block in
  config, and SD stays byte-identical. The Lariat is that machinery's second proof. The race
  layouts are due in Drive 3 (A13). If the run lands late, they slip to a drive of their own after
  Drive 3, and the street layouts don't wait for them. Under D3(b) none of this is needed.
- **Other adapted tools** (opt-in, SD byte-identical):
  - `split_exports_blend`: a far-terrain scene;
  - `pack_release`: takes `--slug`;
  - `make_treefx`: reads zones, species and ground-tile names from config;
  - `place_signs`: signs both directions, gains more plate types and layer-aware tests;
  - `author_lamps_blend`: takes a positions file.
- **The workshop lives outside airoso** (the sync rails require it), e.g.
  `C:/Users/Owner/Documents/k10-workshops/lookout-lariat/`.

**Done when:**
- the SD parity dry-run matches;
- a Lariat dry-run stops cleanly at "no blend yet";
- every existing test still passes.

### P2 — Draft, route-only

1. **Engine phases 1–3** on the re-derived route:
   - route + widths (`mountain` profile, real widths from the dossier as overrides);
   - 3DEP corridor elevation;
   - crossfall, re-measured (step 4);
   - bridge spans (step 5);
   - projection into the loop frame.
2. **New `tools/fit_hairpins.py`. It runs before any ribbon exists.**
   - **Why:** the OSM hairpin ways (1432442175 at the base; 1432442169/71/73; 1432422186) have
     nodes every 4–5 m that turn 17–27° each. The engine's OSM path never smooths in plan
     (Catmull-Rom runs only for KML, `scripts/gps/centerline.py:357-417`), so the 3 m centreline
     keeps the facets. Measured on the July line, the base hairpin (st 252–297) steps 0, 9, 17, 14,
     12, 20, 9, 16, 16, 5 and **25°** between consecutive 3 m points. A smooth R 12 m arc would
     step an even 14°.
   - **What it does:** each corner of ≥ 90° on the climb and at C12–C13 is replaced by a
     curvature-continuous arc with transition curves. The radius is the one measured on the aerial
     (dossier §12), and the fit stays within the OSM way's lateral tolerance. The result is
     resampled at ≤ 1 m through the corner.
   - **Gate** (new; tagged as in P5, logged in `GATES-CHANGELOG.md`):
     - on the fitted line, every heading change between consecutive points ≤ (spacing ÷ R_fit) ×
       57.3° + 1°. The first term is the fitted arc's own turn per point (spacing ÷ radius is in
       radians; × 57.3 makes degrees); the + 1° of slack is [invented];
     - adjacent steps differ by ≤ 1.5° [invented];
     - 0 points fail on the climb [invented].
   - The 14 m widening at C1 (A2) is decided only after Drive 1 on the fitted curve.
3. **New `scripts/blender/underlay.py`** (REALISM §4, the generalised draft builder). It writes these
   objects into `tracks/lookout-lariat/loop.blend`:
   - `GEN_road`: the engine ribbon on the fitted line, at real width.
   - `GEN_verge`: the D4 edge, either A's 0.3–0.5 m gravel or B's 1–1.5 m firm drivable gravel. It
     replaces the July 6.4 m drivable shoulder.
   - `GEN_terrain` tiles (P3a's tiers).
   - `GEN_buildings`: OSM footprints within ~150 m on the town stretches, extruded to OSM height or
     levels (SD's `build_loop_blend.py:419-491` method, ported). Each building is seated at its
     footprint's lowest true ground.
   - `GEN_refs`: centreline, stations, the corner list, the stacked-leg pairs, the race-turn boxes.

   It never resets the scene and never touches anything named `AUTH_*`. That rule is what makes
   "engine drafts, Claude edits" safe.
4. **Crossfall, re-measured and gated.**
   - **Why "estimated" for now:** the July file is DEM-estimated, not measured.
     - About 10 % of stations sit exactly at the 6 % cap, and 19 % on US-40.
     - In 9 separate places (8 on the climb), the tilt swings from ≥ 3 % one way to ≥ 3 % the
       other within 30 m. A looser count of the same swings finds 16.
     - On a 6.1 m road, a lateral pair of 1 m DEM samples at the pavement edge reads the cut or
       the fill, not the road (L3b).
   - **The method:**
     - Re-measure with sample pairs inside the real-width footprint only.
     - Add a **roll-rate gate** (new): the tilt changes ≤ 4 % per 30 m [invented], and no swing
       from ≥ +3 % to ≤ −3 % within 30 m [invented].
     - Check a sample of stations against 3DEP's source lidar (REALISM §5).
   - Until that sample agrees, the file is labelled "estimated", and the construction standard
     fills any failing stretch: 2 % crown, or 2 % toward the cut ditch on bench sections. Nothing is
     banked (A6).
5. **Bridge spans.**
   - **The lid:** declared from the OSM tunnel footprint, not the auto-detector. The US-6 tunnel
     ways 533503591 and 533679737 cross the lap ~550 m before the pylons, so the deck is the
     stretch of lap over that footprint plus its abutments: tens of metres, held level.
   - **Both July auto spans are suspects:**
     - `[24,278–24,803]` is 525 m long and ends on the lap's last vertex: a wrap artefact (L13).
       Holding it level would erase 19th St's real +5.7 % climb.
     - `[20,742–21,166]` contains the C-470 underpass at ~21,100 on US-6, where the lap passes
       *under* a bridge, not over one.
   - Both are dropped unless the aerial shows a real lap bridge.
   - **Seam test (new):** the span detector gets an L13 test. A span may not end on the closing
     vertex unless it continues from vertex 0.
6. **Not run:** `build_env` (no highways, no sine-wave mountains, no baked forest, no lamps).
7. **Optional engine courtesy, off the critical path:** a `scenery.highways.enabled` key in
   `build_env`, defaulting on, so Sand Creek stays byte-identical and the switch exists for anyone
   else.

**Done when:**
- the road-inventory check passes on the draft, with its declared exemptions;
- the hairpin gate passes;
- drive_test has been run once on the draft as a baseline (recorded, not gating).

### P3 — Author in Blender (scripted tools, `AUTH_*` collections)

**3a. Ground: seating, cut/fill, tiers, overpasses.**
- **adapted `seat_terrain_blend`**: covers the mainline, with station matching (P1 precondition 3).
- **new `terrain_cutfill`**: the road-building cross-section from `docs/ROAD-CONSTRUCTION.md`.
  - The section, uphill to downhill:
    - rock cut 0.25:1 on the uphill side (soil 1–1.5:1);
    - a 0.4 × 1.2 m ditch at its toe;
    - the D4 verge;
    - fill 1.5:1 (hand-placed rock) on the downhill side, meeting natural 3DEP ground.
  - **Between stacked legs the default is cut + fill, not walls (A3).** The July line's stacked legs
    sit ≥ 13.8 m apart edge to edge at real width, with 6.5–14.7 m between them vertically.
    ROAD-CONSTRUCTION's own section closes 13 m of height in 11 m: a 6.8 m rock cut needs 1.7 m, and
    a 6.2 m fill at 1.5:1 needs 9.3 m.
  - The doc's fill→wall trigger is "edge fill height > ~4–8 m". Between legs on unsurveyed ground
    the tool uses the 8 m end.
  - It authors a wall only where:
    - the survey shows one: Wildcat Point's two battered walls, the Windy Saddle walls, and the
      stone guardrails' own footings; or
    - the section still cannot close.

    Each such wall is labelled `AUTH_wall_authored_*` and listed for Kevin.
- **engine opt-in: terrain tiers** (0046 E1, extended for the views):

  | Tier | Cells | Extent | Physics |
  |---|---|---|---|
  | Corridor | ≤ 3 m | ~20–25 m past the pavement edge | yes (`1GRASS`) |
  | Medium | 15–20 m | to ~500 m | yes |
  | **View** (new) | 20–30 m | to ~3 km, **north and east (the view side)** | no |
  | Far | 60–100 m | ≥ 10 km west, south and north | no |
  | Plains | ~250 m | ~25 km east | no |

  - **Why the view tier:** the views the gates check sit 0.5–3 km out: the Clear Creek mouth at
    −11.8° from 1.5–2.2 km, Golden at 1.6–2.9 km, Mount Zion and the M at ~1 km. At far-ring cells
    of 60–100 m, a canyon a few hundred metres wide smears away.
  - **Visual-only tiers** carry no digit prefix, so physics, GrassFX and the gates never touch them.
    They ship in their own backdrop kn5, listed in every layout.
  - **Seam check (new):** no open edge or crack where two tiers meet. Each shared boundary either
    coincides within 0.05 m [invented] or is skirted down.
  - **If D6(i) is declined:** no view, far or plains tier. Terrain beyond the corridor is clamped
    within ±22 m of the nearest road height, as L3 is written, and the views from the climb are
    lost. Note that the airoso engine has no band clamp today (0046: "the band clamp itself is
    SD-only"), so declining means writing one.
  - **Confirm in game (Drive 2 look row)** that AC/CSP actually draws terrain at 10–25 km. If it
    clips, shrink the far tier to what draws.
- **new `overpass_decks` (D5).** Static C-470 bridges at st ~19,300 on Colfax and ~21,100 on US-6.
  - **What gets built:** deck slabs at the real C-470 alignment and width (OSM ways 84720931 /
    84720904 / 84721006 / 1459465701, and 84720905), with abutments that meet the approach fills
    3DEP already contains.
  - **Clearance:** the real clearance over the lap, read off the aerial and Street View.
  - **Placement:** piers stand outside the lap corridor.
  - **Rules:** no prefix (visual-only), named `AUTH_overpass_*`, never `HIGHWAY*`. No pavement
    continues along the lap. The road-inventory gate exempts them by name and footprint.
- **new `tools/sightline_check.py`** (named in 0046 and 0048; it does not exist yet).

**3b. Junctions: race-turn boxes, side-road stubs, the lid.** Per `docs/JUNCTIONS.md`, by hand in
Blender as on Lake Murray.
- **Drivable mouths at the five corners where the lap turns from one road to another.** Under D3(a)
  these are also the race's open boxes:
  - C12 Paradise tee (Lookout Mtn Rd's south leg welded on);
  - C14 Paradise → US-40;
  - C15 exit 259 signals;
  - C16 Colfax → US-6;
  - C18 ramp → 19th St.
- **C17**, the US-6 diverge, is a gore, not a box.
- **Side-road stubs (A9)** at the ~45 named side roads and ramps listed in dossier §4b, the four
  signalised ones first. They follow JUNCTIONS R18(c): a short visual stub with full curb returns,
  no physics, and an invisible wall straight across the mouth line in every layout.
- **Unnamed service drives** get flush aprons on the town stretches and nothing on the mountain.
  The pull-offs, the overlooks and the Windy Saddle lot stay open, flat ground.
- **The lid** is level across its footprint span (P2 step 5).
- **reused (no-op on an empty config):** `route_connectors`, `divide_connectors`,
  `trim_connectors`.

**3c. Hairpin pads, only where the measured width calls for one.**
- **new `hairpin_pads`**: the JUNCTIONS pad shape, at the width measured on the aerial (the 1913
  design widened turns to ~24–26 ft, 7.3–7.9 m; ROAD-CONSTRUCTION).
- It caps the grade spike on the inside edge, where a 9 % road at R 9 m reads ~15 %.
- C1's 14 m pad exists as an `AUTH_` object, **hidden for Drive 1** (A2).

> **→ Drive 1: the road and the ground, nothing else.** Two installs, `lookout_lariat_v3` (D4 A)
> and `lookout_lariat_v3_verge` (D4 B), identical apart from the edge. The C-470 decks are in; the
> buildings are not yet.
> Questions: does the climb drive like the real road, which width, is the base hairpin still
> impossible, and is US-40 just the canyon?
> Gates for Drive 1: the **Drive-1 set** in P5.

**3d. Edges.**
- **new `stone_works`** (rule + author + verify):
  - the pylons (hand-authored);
  - stone guardrails with their gaps;
  - the battered (sloping) walls at Wildcat Point;
  - Sensation Point's wall;
  - the Windy Saddle walls.
- **new `guardrail`**: W-beam where the survey puts it. On unsurveyed drops a rule decides (fill
  height × slope, ROAD-CONSTRUCTION "Barriers"), and those runs are labelled authored.
  - Posts every 1.905 m, with proper end pieces.
  - Physical `1WALL_`.
  - Placed after the ground is final, with station matching (0010's floating posts were placed
    before).
- **reused as a library:** `race_furniture.py`'s offset-curve and module-sweep code.
- **Survey first.** The Street View pass of dossier §12 decides which edge is stone, steel or open.

**3e. The divided stretches (D2).**
- **adapted** `median_envelope` + `author_median_blend`, with the separation values moved into
  config.
- One slab per divided stretch, with its median: US-6, the 309 m of Colfax, the 105 m of 19th St,
  and the 85 m at exit 259 (ways 119006778 + 42005706). *(P0: 19th St is 54 m on its westbound
  side, beside 533500102. The stretches and both sides' ways are in the config's `divided` block.)*
- Under D2(b) only, the second Reverse route is added: US-6's other carriageway, the on-ramp
  (642334992), 19th St's eastbound side, the southbound Colfax approach and exit 259's way
  42005706. It gets its own centreline, and road-inventory exemptions.

**3f. Signs (A5, D7.2).**
- **adapted** `place_signs`:
  - both directions;
  - set-back for a road with no sidewalk;
  - station-matched, layer-aware pavement tests;
  - wall or rail mounting where the ground falls away.
- **The stone-guardrail case:** the post stands on true ground within 2 m behind the wall, or the
  sign is omitted. A sign never sits on the stone and never floats over a drop.
- **First pass:**
  - the sourced signs: 13 mapped 20 mph limits, the 35 mph at the summit, and the advisory plaques
    on hairpin ways 1432442175 / 69 / 71 / 73 and 1432422186;
  - then the rule-placed W1-6 arrows, marked authored.
- `signs_preview.svg` shows Kevin the authored arrow count (≈ 44 estimated) **before** any build.
  He can cap it.
- **reused:** `author_signs_blend`, `signs_mesh`, `make_sign_textures` (the W1-8 chevron artwork
  already exists), `plot_signs`, `verify_signs`.
- `tracks/lookout-lariat/signs.json` holds the overrides.

**3g. TreeFX (A8).**
- **adapted** `make_treefx`: zones by slope direction and height from dossier §6, with no `;`
  lines.
- The `.bin` files stay gitignored in `source/trees/`.

**3h. Lamps + GrassFX (D7.1).**
- **new** `lamp_inventory`: turns the dossier's surveyed lat/lon list into
  `data/lights.local.json`.
- **adapted** `author_lamps_blend`: takes those positions, with lamp height per lamp.
- **reused** `ext_config.py`:
  - HPS colour, at 255-scale intensity;
  - Kevin's July wide, dim pool shape;
  - `light_pollution` glowing east toward Denver;
  - GrassFX on the corridor and medium ground tiles only.

**3i. Town dressing (A9).**
- Kerbs and sidewalks where they are real: 19th St, Colfax, I-70 Business, and Beverly Heights if
  the aerial shows them.
- Driveway aprons on the town stretches.
- Utility poles where OSM maps them.
- The `GEN_buildings` draft gets checked on the aerial.

**3j. Race furniture (D3 a only), on Lake Murray's machinery.** The full spec is in dossier §4c.
One shared race kn5 serves both race layouts.
- **Closures** at every side road the race doesn't take: a barrier straight across the mouth at the
  junction edge.
- **Open boxes** at the five race-turn corners. The legs the race doesn't take are sealed at the
  box edge.
- **Lane-closure barriers** on the multi-lane town streets. They give the race about Alvarado's
  width (~13 m / ~11.4 m clear) and close the rest; like Lake Murray's, they lead up to medians but
  never sit on them.
- **US-6's median gaps sealed,** and exit 259's 4-lane south-west-bound side closed at the C15
  box edge.
- **On the mountain: nothing in the road and nothing added along the edges.** The real stone,
  W-beam and open edges are the race edges.
- **Race kerbs:** none on the mountain. The July rumble lips were "undriveable slop".

> **→ Drive 2: edges, signs, trees, lamps, buildings, and the far views.**

### P4 — Layouts: four (two under D3 b) on 0047's machinery

- **reused** `tools/layout_dummies.py`, to `data/dummies_<layout>.json` for `full`, `reverse`,
  `race_acw` and `race_cw`. Each has its own start in its own direction.
- **Road kn5:** the prep writes **no** start or pit nodes into the shared road kn5.
- **Spawn kn5s:** **reused** `build_spawn_kn5.py`, one `lookout_lariat__<layout>.kn5` per layout
  (nodes only, ~2 KB each).
- **Folder:** each `models_<layout>.ini` lists:
  - the road kn5;
  - the backdrop kn5;
  - its own spawn kn5;
  - the race layouts also list `lookout_lariat_race.kn5`.

  **reused** `track_folder.py`.
- **AI:** **reused** `write_ai_line --layout <id>` writes a generated draft per layout. Then one
  in-game recording per layout (the HANDOFF rule).
- **Map:** **reused** `make_map.py` (multi-layout, kn5 frame). Check `map.png` orientation against
  the real map (0038).
- **Cameras + Content Manager images** (REALISM §6 floor, as SD ships):
  - TV cameras per layout (`data/cameras_*.ini`);
  - `ui/<layout>/preview.png` and `outline.png` for each layout.

> **→ Drive 3: every layout (four by default), and the AI launches the way the grid faces.**

### P5 — Gates (on the built file, never the data that placed it — L5)

Every number in this section carries a tag:
- **[std]**: it has a basis outside this plan that can be cited: an outside source (AC's file
  format, MUTCD, OSM tags, CSP's own behaviour, Kevin's own words), a reference track, or an
  existing gate value that `fleet/GATES-CHANGELOG.md` records without a ⚠.
- **[invented]**: everything else. That includes every value new in this plan, values copied from
  our own output (Lake Murray's included), and existing values the changelog flags ⚠.
- **[measured]**: a measurement or arithmetic quoted for context, not a threshold.

Invented values are logged as such in `fleet/GATES-CHANGELOG.md` in the same commit that lands them.

| Gate | Lariat threshold |
|---|---|
| `drive_test --layout <each>` | • Obstruction, floating furniture, soft-top-in-lane, undrivable corners, daylight gaps: 0 each [std: drive_test's existing count gates].<br>• Severe steps (a step ≥ 6 cm [invented: drive_test's own ⚠ value]): 0 [invented: drive_test's own line is > 12/km; 0 is new here].<br>• Replication vs 3DEP: p95 ≤ 0.5 m [invented in 0048].<br>• Kinks: ≤ 5/km [invented: Lake Murray V3's own 4.97/km, copied onto R≈12 m hairpins]. Before Drive 1 the kink metric runs on la_canyons and simtraxx Pikes Peak (both on this machine); a ceiling re-set from those reference mountain roads becomes [std]. |
| `audit_mesh` | • Hard classes A, B, D, E, G, H, I: 0 each [std: audit_mesh's existing hard total].<br>• F (curb not flush): ≤ 15 [invented: the hard total gates F at 0; 15 is Lake Murray V3's own count].<br>• J (terrain span) and K (kerb in the carriageway) at the five race-turn mouths: 0 [invented: audit_mesh reports both today without gating them; K's promotion is 0036's]. |
| `verify_kn5` | • Positions per mesh: ≤ 65,535 [std: AC's file-format limit].<br>• Drivable faces pointing up: ≥ 90 % [std: verify_kn5's existing value].<br>• Start/pit nodes in the road kn5: 0 [std: 0047's check (a)].<br>• Each spawn kn5 carries exactly its layout's grid, ≥ `n_pits` starts [std: 0047's check (b)].<br>• Each start faces within 30° of its own layout's direction [invented: verify_kn5's `HEADING_MIN_DEG`, flagged ⚠]. |
| `kn5_ground_check` | • Road over ground: p95 ≤ 0.10 m [std: the existing gate, set from four circuits' measured p95s] **and** floating furniture 0 [std: existing count gate], at the same terrain cell size (0010's two numbers in one build).<br>• The lid: no step > 0.10 m at either end [invented in 0048]. |
| **new** route one-way check (P0 step 8) | • Runs against a `oneway=yes` way in the Full direction: 0 [std: the real road's direction, from its OSM `oneway` tags].<br>• Street Reverse: only on its four declared D2 stretches under D2(a) or (c); none under D2(b).<br>• Race layouts are closed roads and are not checked. |
| **new** hairpin smoothness (P2 step 2) | • Heading change between consecutive points ≤ (spacing ÷ R_fit) × 57.3° + 1°. The first term is the fitted arc's own turn per point (geometry: spacing ÷ radius is in radians, × 57.3 makes degrees); the + 1° of slack is [invented].<br>• Adjacent steps differ by ≤ 1.5° [invented].<br>• Points failing on the climb: 0 [invented]. |
| **new** roll rate (P2 step 4) | • Tilt change ≤ 4 % per 30 m [invented].<br>• Swings from ≥ +3 % to ≤ −3 % within 30 m: 0 [invented]. |
| **new** road inventory (in `verify_kn5`) | • `HIGHWAY*` / `HWYSTRUCT*` meshes: 0 [std: Kevin's "no extra highways", 0048]. `MOUNTAINS*` meshes: 0 [std: rule L1, as 0046 applies it to the sine ridge].<br>• Every pavement triangle lies within half-width + 2 m of the route [invented], **or inside a declared exemption polygon** (`tracks/lookout-lariat/pavement_exemptions.json`). Each polygon names the `AUTH_*` object it covers: C1's pad, the five mouths, the side-road stubs, the Windy Saddle lot, the paved overlooks, the lid, the C-470 decks (D5), the D2 slabs and D2(b)'s route.<br>• Pavement centreline length within 1 % of each layout's lap [invented]. |
| **new** stacked-leg check (L4) | • **Pairs:** two lap points < 40 m apart on the map [invented] and > 150 m apart along the lap [invented]. On the July line that gives 1,188 pairs, vertical gap 6.5–14.7 m (median 10.1 m), nearest 20.5 m on the map [measured]; the count is re-measured and recorded on the V3 line.<br>• **Test:** at every pair, every ground, edge, sign and closure vertex is seated to its own leg's station, and none sits closer in height to the other leg's road than to its own: 0 failures [invented]. |
| **new** `verify_edges` | • Every wall and rail post seated within 0.05 m of final ground [std: kn5_ground_check's existing 0.05 m ground tolerance].<br>• Posts or walls in a lane: 0 [std: drive_test's obstruction count].<br>• Stone runs keep their surveyed gaps; every rule-flagged drop is covered, or declared open by the survey.<br>• Unguarded drop-offs ≤ 1/km [invented: drive_test's own excursion line, flagged ⚠].<br>• **Not gating in Drive 1.** |
| **new** tier seams (P3a) | • Open edges between terrain tiers: 0 [invented].<br>• Each shared boundary coincides within 0.05 m [invented], or is skirted down. |
| **new** `sightline_check` | • Each of dossier §6d's sightlines within ±0.5° of the 3DEP angle [invented]. At 1.5–3 km that is ±13–26 m of ground height [measured], which is why the view tier exists. |
| `verify_signs` (both-directions extension) | • Its existing checks (a)–(j) [std: MUTCD and the sign's own dimensions, GATES-CHANGELOG 2026-10-10], except the edge clearance in (c): its 1.3–3.0 m comes from Lake Murray's sidewalk, so the Lariat's no-sidewalk set-back is [invented].<br>• At a stone guardrail, the post stands on true ground within 2 m behind the wall, or there is no sign [invented].<br>• Authored arrows: exactly the count Kevin approved [std: Kevin's approval]. |
| TreeFX check | • `;` lines in the tree list: 0 [std: 0040 measured CSP reading such a line as a path].<br>• Every species file present.<br>• Trees within half-width + 1 m of any centreline: 0 [invented in 0040].<br>• "Failed to load trees" in the CSP log: none [std: CSP's own log], read on the Windows box. |
| Race (D3 a only): `verify_race`, `check_race_kn5`, race kn5 size, `plot_race_furniture`, **no-route-to-the-other-side** | • Every value as Lake Murray's corridor run lands it, carrying the tag `GATES-CHANGELOG.md` gives it there (e.g. ring seating gap ≤ 0.05 m [std]; race kn5 < 20 MB [invented, ⚠]). The Lariat is their second proof.<br>• Race barriers inside the mountain road: 0 [invented: D3(a)'s rule].<br>• Non-race junction mouths left open: 0, and the open boxes connect only the race's own legs [std: Kevin's race brief]. |

**The Drive-1 gate set** is road + ground only, named so Drive 1 isn't red by design.
- **Gating:**
  - drive_test (severe, obstruction, soft-top, undrivable, daylight, replication, kinks);
  - `audit_mesh`, `verify_kn5`, `kn5_ground_check`;
  - the one-way, hairpin, roll-rate, road-inventory, stacked-leg and tier-seam checks.
- **Recorded, not gating:** unguarded drop-offs, `verify_edges`, `verify_signs`, TreeFX,
  `sightline_check` (the far tiers arrive for Drive 2), and every race gate.

**`--force-install` rule (0047).**
- **When it applies:** a red street-layout run may still install only if it is no worse than the
  July reference on every key in the active gate set [std: 0047's rule].
- **The July reference** is the installed v0.46.0 build: severe 253, kinks 68.3/km, excursion drops
  738, far ledges 382, obstruction 0, floating 0, soft-top 0 [measured on that build].
- **Always 0, red or not:** obstruction, floating furniture and soft-top [std: drive_test's count
  gates].
- **Race layouts** never install red on `barrier_missing` or obstruction, since no reference exists
  to be "no worse than" [std: 0047, as shipped].
- No advisory environment variables.

### P6 — Kevin's drives

- A `DRIVE-TEST-REPORT` per drive (`fleet/templates/`), with dossier §10's look rows as its §Look
  section.
- **T2:** it loads to the spawn.
- **T3:** three clean laps in each street direction.
- **T4:** the AI laps each layout.

### P7 — Release (after T3; D0 is separate and comes first)

1. `pack_release --slug lookout_lariat`. The zip's folder is `lookout_lariat`, so it replaces the
   old public copy (A11).
2. Two zips:
   - **Full**, kept local: TreeFX `.bin` files, mined textures, and the race layouts (D3 a).
   - **CC0**, public:
     - the street layouts only;
     - no `.bin`, with `[TREES]` commented out;
     - asphalt, ground and concrete textures swapped for CC0 ones with
       `tools/repack_kn5_textures.py`;
     - honest `CREDITS` / `LICENSES`.

     The race kn5 joins the CC0 zip only once its closures are rebuilt from CC0 parts, or once the
     barrier pack's licence is recorded, as on Lake Murray.
3. Draft a k10-colorado release carrying **every** Colorado zip; only the latest release shows on
   doooom.fast.
4. Update prodrive-server's catalog text (length, layouts).
5. Publishing the draft is Kevin's click.

## Tool map

| Tool | Status | Change |
|---|---|---|
| airoso `scripts/gps`, `scripts/elevation`, `ribbon.py` | reused | — |
| `scripts/gps` route key `exclude_ids` | adapted (opt-in) | drops one way from a `ref:` match (exit 259) |
| `tools/route_oneway_check.py` | **new** | no wrong-way runs on one-way ways |
| `tools/fit_hairpins.py` | **new** | curvature-continuous hairpin fit + heading gate, before the ribbon |
| crossfall stage | adapted | real-width footprint + roll-rate gate |
| span detection | adapted | L13 seam test; the lid is declared from the tunnel footprint |
| `scripts/blender/underlay.py` | **new** | the draft builder (REALISM §4), incl. ported OSM buildings |
| `tools/ship_track.sh` + `ship.json` + `test_ship_track_chain.py` | **new** | generic ship chain |
| `tools/ship_sd.sh`, SD's `build_loop_blend.py`, engine-july | not used | stay untouched |
| airoso `scripts/ac/build_kn5_loop.py` | adapted | frame fix, balanced tiling, station-matched layers |
| `export_kn5_addon`, `build_spawn_kn5`, `pbr`, `track_folder`, `write_ai_line`, `make_map`, `layout_dummies`, `kn5_to_gate_obj` | reused | — |
| `drive_test`, `audit_mesh`, `kn5_ground_check`, `verify_signs` | reused | — |
| `verify_kn5` | adapted | + road inventory with exemption polygons |
| `seat_terrain_blend` | adapted | mainline + station matching |
| `terrain_cutfill`, `hairpin_pads`, `overpass_decks`, `stone_works`, `guardrail`, `verify_edges`, `lamp_inventory`, `sightline_check` | **new** | — |
| `scripts/elevation/heightfield.py` (0046 E1 tiers) | adapted (engine opt-in) | tiers incl. the 3 km view tier + seam check |
| `median_envelope`, `author_median_blend` | adapted | the four divided stretches (D2) from config |
| `place_signs` | adapted | both directions, no-sidewalk set-back, station-matched |
| `author_signs_blend`, `signs_mesh`, `make_sign_textures`, `plot_signs` | reused | — |
| `make_treefx` | adapted | zones/species/tiles from config |
| `author_lamps_blend` | adapted | positions input |
| `ext_config.py` | reused | — |
| `split_exports_blend` | adapted | far scene; the race split already exists |
| `race_furniture.py`, `barrier_bands`, `author_race_furniture_blend`, `verify_race`, `check_race_kn5`, `plot_race_furniture` + the no-route gate | adapted, **from Lake Murray's corridor run** | SD `STREETS` → config `race` block |
| `pack_release` | adapted | `--slug` |
| `slim_far_terrain_blend`, `gap_mouths_blend`, `export_scatter_blend`, `strip_scenery_blend`, `snapshot_engine_july` | not used | SD-specific |
| `build_env` `_build_highways` | not run | optional `scenery.highways` switch for other tracks |

## Budget, per package

AC counts "positions": vertices after it splits them for textures. Today's file is 10.86 M
positions / 550 MB. Lake Murray V3's road kn5 is 91.9 MB, its race kn5 12.5 MB, and its trees
folder 61 MB.

| Item | Positions | Size |
|---|---|---|
| Road: 1 m stations through the hairpins, 2 m elsewhere, 5–7 points across | 80–110k (2 meshes) | |
| Verge / ditch | ~60k | |
| Markings (double yellow, edge lines) | ~50k | |
| Corridor + medium ground | 150–250k (3–5 pieces of ≤ 50k) | |
| Stone works, authored walls, W-beam | 100–200k | |
| Lamps (a few dozen at ~4k each, D7.1) | 120–240k | |
| Signs | 10–30k | |
| Buildings, kerbs, sidewalks, side-road stubs (A9) | 60–120k | |
| Pylons, the lid, C-470 decks | ~20k | |
| **Road kn5** | **~0.65–1.1 M** | **75–90 MB, hard ceiling ~100 MB** |
| Backdrop kn5 (view + far + plains tiers, D6 skyline) | 100–140k | 5–9 MB |
| Race kn5 (closures + lane barriers, D3 a) | 60–150k | 3–8 MB (Lake Murray's, for 13.5 km of both-side strips, is 12.5 MB) |
| Spawn kn5s, one per layout (four, or two under D3 b) | — | ~2 KB each |
| TreeFX `.bin` models (A8) | — | ~60 MB |

| Package | Contents | Size |
|---|---|---|
| **Full install** (this machine) | road + backdrop + race + spawns + trees + mined textures | **~145–180 MB** (vs 559 MB installed today) |
| **CC0 public zip** | road + backdrop + street spawns, CC0 textures, no trees, no race kn5 (A12) | **~80–100 MB** (vs the live 311 MB) |

A smoother, lower-detail lamp would halve the lamp share if frame rate or size needs it.

## Risks

1. **Stacked switchbacks (L4).** Every "seat onto the nearest surface" step grabs the wrong leg
   unless it is station-matched first: the "rainbow road" failure again. Mitigation: P1
   precondition 3 plus the stacked-leg gate.
2. **Prep frame bug.** Trees and verges get culled in mirror-image places. Prove and fix it before
   the first ship (P1).
3. **Hairpins.**
   - The OSM line is faceted (P2 step 2): 11 corners of ≥ 135°, 30 stretches tighter than R 10 m,
     12 stations where the strip would fold.
   - AI draft lines cut inside tight corners (0047 measured an R 0.3 m line).
   - The fit plus authored pads are the fix, and they cost time.
4. **Drop-offs read as defects.** Real drop-offs count as "excursion drops" until walls and W-beam
   exist. Hence the named Drive-1 gate set, and no advisory bypass.
5. **The lid and the seam.** The July auto span ran 525 m to the lap's last vertex, a detector wrap
   (L13). The real lid sits ~550 m before the pylons, clear of the seam. Mitigation: the lid is
   declared from the tunnel footprint, and the detector gets its seam test.
6. **Laws are Kevin's.**
   - Real mountains beyond the road need the one-line change to rule L3 (D6 i). The airoso engine
     has no flattening clamp today, so this is Kevin's sign-off, not a code dependency.
   - Tilting the hairpins (banking) would need 0003's change to rule L10, which this plan does not
     ask for (A6).
7. **SD regression.** Any edit to `ship_sd.sh`, engine-july or a shared tool's defaults breaks the
   pinned tests or the installed Lake Murray. Every Lariat change is opt-in and proven
   byte-identical for SD.
8. **The race tools are mid-design on Lake Murray (D3 a only).** The Lariat adapts what that run
   lands. If it slips, the race layouts slip to a drive after Drive 3; the street layouts don't.
9. **Sign count.** ≈ 44 authored arrows on a Register road. Kevin sees the count before the build
   and can cap it (A5).
10. **Lamp weight.** At ~4k positions per lamp, the July 304 alone would add 60 MB. The inventory
    keeps it to dozens.
11. **Network.**
    - Python's certificate store fails Overpass today; P0 step 1 fixes it properly. *(Done in
      P0. The fault was an expired cross-certificate in the Windows Intermediate store, not
      Python's store. Every Python fetch now verifies through `scripts/tls.https_context()`.)*
    - The far tiers need a live USGS fetch.
    - `gh` isn't logged in; PUBLISHING.md's credential-manager method covers that, and D0 needs it.
12. **Gate runtime.** Gate time and memory grow with ground detail (Dragon Tail peaked at 7 GB for
    2.9 M vertices). Balanced tiling and visual-only far tiers keep the physical ground at
    ~150–250k positions.
13. **Survey dependence.** Nothing in the data gives these:
    - the stone / W-beam / open edge inventory;
    - the hairpin radii and widths;
    - the C-470 clearances;
    - Golden's kerbs.

    Without the Street View and aerial passes, those parts are authored rather than replicated, and
    are labelled that way.
14. **Licensing (D0).** The live public zip misstates its licences today, independent of V3.

## Not in this plan

- Sand Creek's own I-70 decks (its feature, its decision).
- The circuits (no motorway in their boxes), except D0's texture check on their live zips.
- San Diego (untouched; its race-corridor run is the source of the race tools, not a target).
- Anything built from or committed to `k10-colorado` (retired).
- Living traffic (REALISM §6), and the later landmarks of dossier §5e.

## First three moves after approval

1. **D0 first.** Prepare the take-down or re-pack, and the catalog edit, for Kevin's click. Then
   P0 steps 1–5: the certificate store, the frame-free restore, the offline route, the blend
   archive, the registry. No geometry.
2. **The config rewrite and the centreline.** Re-run the centreline with both route fixes and run
   the one-way check. That gives Kevin the numbered route map.
3. **In parallel:**
   - P1's prep proofs (frame bug, tiling, station matching) on a scratch copy;
   - the hairpin fit;
   - the aerial and Street View passes that dossier §12 needs (hairpin radii, edges, C-470
     clearances).
