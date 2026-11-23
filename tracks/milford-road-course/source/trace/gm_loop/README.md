# GM's 2.9 mi loop (ledger 0102, Milford round 2)

Kevin, 2026-11-22, on the calls page ("Milford: which length?"): **"Build the 2.9 mi loop"**.

## What differs from our lap

The PC matched our 0.1.13 line against OpenStreetMap's raceways. The source is an Overpass read the Mac fetched on Kevin's
yes: `osm_mpg_overpass_20261123.json`, osm_base 2026-11-23T03:13:34Z, first-mapped dates from the way history. The match
was checked on NAIP 2022.

- GM's loop is the older ways, clockwise:
  - 72577419 (2010), the outer loop, from its node 41 (the NE junction) round east, south and west to its node 15 (the
    west straight);
  - then 72577413 (2010), the infield, end to end, back to node 41.
- On our projection it is 4,710 m. GM's own figure is "2.9 mi", which is 4,667 m.
- Our lap differs at ONE place, the hairpin at the bottom left of the infield (our s 768-1,299):
  - ours rides 1030539760 (first mapped 2022-02-11), 534 m, the long southern loop;
  - GM's takes 72577413's own inner turn (its nodes 41-59), 370 m.
  - Swapping only that piece on OSM gives 4,874 m, the same as our 4,887-4,898 m lap.
- 1030539761 (2022, the SE hook) is not on our lap.
- The NW corner differs only by the line through the wide apron (~20 m inside), on the same pavement: our measured line stays.

## The inner branch

The inner branch is **concrete**, with an asphalt band along its inner edge (Oakland County's 2025 ortho, 7.62 cm, the
Mac's crop: board asset `8a8086d41a7cbf20b69318824f7da18b`, md5 7f53c304b91f2a100e6db7b47c060022; georeference
`089196c463697260729e740b41ff8da8`). So its width is the whole pavement.

1. `trace_inner.py`: the centre off NAIP 2022 by the original tracer's method (net_extract's colour rule, a centre-seeking
   shortest path via OSM's inner-turn node, perpendicular scans), between `mrc_fixes.json` fixes 337 (s 834) and 518
   (s 1,286), where the two paths part and rejoin. Output: `inner_trace.naip2022.json`, 268 m. NAIP's width reads were
   unusable: the worn asphalt (lum 181-200) and the concrete (209-213) blur together at 0.6 m.
2. `ortho_width.py`: re-centred three rounds and measured every 2 m on the ortho. The classes, sampled on the crop:
   - grass: lum 149-156, chroma 34-35;
   - asphalt: lum 193-196, chroma 13-15;
   - concrete: lum 206-222.
   The centre and width are the whole pavement's. Output: `inner_ortho.ortho2025.json`.
3. `splice_gm_loop.py` writes `../../../data_gm/`, which the port reads through `lm_intake.source_data`.
   - Every station outside geojson points 279-369 keeps its committed position, width and raw 3DEP sample bit for bit;
     the projected heights agree to 1.1 cm (2 cm at the junction point: the profile's windows reach across it).
   - The new piece:
     - 91 points every 3 m, 276.5 m;
     - the joins a cubic Hermite over 30 m [invented], then 4 binomial passes [invented];
     - widths by finalize.py's rules and to_fixes.py's 9-16 m clamp: 10.8 / 15.0 / 16.0 m (min / p50 / max);
     - raw heights native 3DEP off `data/corridor.elev.json`, inverse distance over 4, as tools/lm_engine_intake.py's
       corner arcs read it. Against the committed samples at the kept stations: p50 1.6 cm, max 10.4 cm.
   - Controls: the stages' own code reproduces the committed profile and projection to 0.0067 m.
   - Lap 4,900.7 -> 4,726.0 m (450 m dropped, 277 m new). Max 3 m turn on the piece 10.6 deg (the lap's 9.4).

Re-run (from the repo root):

    python -I tracks/milford-road-course/source/trace/gm_loop/splice_gm_loop.py . \
        tracks/milford-road-course/source/trace/gm_loop/inner_ortho.ortho2025.json tracks/milford-road-course/data_gm 337 518

## Not part of the lap any more

- The 2022 loop builds as ground, like the other unused pavement (route-notes L8).
- On it, or now under the new lane, and out of the port's furniture: T3 (t3_s1000_apron_back), run-off pads R0998,
  L1175 and L0883 (L0883 was the inner branch's own concrete, drawn as a pad).
