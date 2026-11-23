# terracotta_paver: the Mission Gorge median top, and the tone it should match

`terracotta_paver_diffuse.jpg` and `terracotta_paver_normal.jpg` are ambientCG **PavingStones135**
(https://ambientcg.com/view?id=PavingStones135). The licence is CC0 1.0, read on the asset page and on
https://docs.ambientcg.com/license/ on 2026-11-23. They fill the dossier's "Terracotta median top" GAP row
(`tracks/san-diego-lake-murray/DOSSIER-EXPANSION-NORTH.md`, "Textures and gaps"). No track binds them yet.

- **The files.** They come from `PavingStones135_2K-JPG.zip` (34,342,706 B, md5 `49ce717a09805e8aa7e9ece098212037`),
  downloaded 2026-11-23. `_Color.jpg` became the diffuse (md5 `d51ef0ecbf182a1733e337c80546d66b`) and `_NormalGL.jpg`
  the normal (md5 `e1ecba2fbe1103523a7fa636a42b286e`). Both are copied byte for byte: 2048 × 2048 px as served, not
  resized and not tinted. ambientCG also offers 1K, 4K and 8K. One tile is about 1.9 m (the asset page says
  "ca. 1.9 m × 1.9 m").
- **The normal map is OpenGL**, like every map in this folder. Checked against the zip's own displacement map: G − 128
  correlates +0.77 with the height rising down the image, and R − 128 correlates −0.76 with it rising to the right.
  That matches `tests/tools/test_make_kerb_texture.py`'s convention, so no conversion was needed.
- **Why this set.** At 0.5 m the aerial shows one even salmon tone along the median, with no mottling. PavingStones135
  is a single-colour red-brown interlocking paver with no moss, weeds or mixed bricks. I compared 13 ambientCG Paving
  Stones and 14 Poly Haven brick, paver and tile sets by their colour maps. By mean chromaticity (r, g, b over their sum)
  PavingStones135 is 0.049 from MD13. It is not the nearest: Poly Haven `patterned_brick_floor_02` (0.011) and
  `concrete_pavers` (0.013) and ambientCG `PavingStones092` (0.025) are nearer, but they are grey-beige or pink-grey
  and do not read as terracotta. So the pick is a judgement on the look. The tone is then matched to the measured
  ratio below.

## The measured tone (NAIP 2022, 2026-11-23)

These are 8-bit sRGB values. Each island's pixels are its ring shrunk by 0.5 m, with canopy and shadow taken out
(see "How" below).

| | pixels: ring / inset / canopy / shadow / **kept** | mean RGB | median | p10 | p90 |
|---|---|---|---|---|---|
| **MD13**: piece C s 210–2245, 1.5–8.0 m wide | 40,236 / 32,153 / 1,469 / 2,292 / **28,392** | **147.9, 127.8, 115.6** | 150, 128, 116 | 136, 118, 105 | 158, 137, 125 |
| MD11: piece C s 45–167.5, 0.57–1.62 m wide | 592 / 121 / 11 / 0 / **110** | 126.4, 125.4, 118.9 | 120, 122, 117 | 114, 117, 112 | 145, 137, 128 |
| texture `terracotta_paver_diffuse.jpg` (all 4,194,304 px) | | 166.0, 123.7, 107.8 | 174, 126, 111 | 125, 103, 92 | 196, 142, 126 |

The standard deviation over MD13's kept pixels is 11.6 / 8.1 / 8.5. Its mean in linear light is
0.2981 / 0.2165 / 0.1747; the texture's is 0.3994 / 0.2064 / 0.1572.

**Island ÷ texture, per channel (R / G / B).** This is the number to match. The texture itself carries no tint.

| | sRGB mean | sRGB median | linear-light mean |
|---|---|---|---|
| **MD13** | **0.891 / 1.033 / 1.072** | 0.862 / 1.016 / 1.045 | 0.746 / 1.049 / 1.112 |
| MD11 (do not use, below) | 0.761 / 1.014 / 1.103 | 0.690 / 0.968 / 1.054 | 0.533 / 1.006 / 1.176 |

- **Use MD13.** On the photo the median is less red and a little brighter in blue than the paver. NAIP is a sensor
  product with its own haze and processing, not albedo. So the ratio matches the texture to how the 2022 photo shows
  the median, which is what the aerial-led builds are compared against.
- **MD11 reads near-grey, so its numbers are not the terracotta's.** It is 0.57–1.62 m wide, and the 0.5 m inset
  leaves only 121 pixels. The mosaic's JPEG stores colour at 4:2:0, one chroma sample per 2 × 2 px (about 1 m), which
  is as wide as the strip. Across MD11, binned by offset from its centre line, R − G peaks at +2.9. It holds about +2
  for 4.5 m to the north-west and reads −2.5 on the asphalt to the south-east. MD13's first 100 m (2.3 m wide)
  peaks at +12.0. MD13 shows the same dilution where it
  narrows to its 1.5 m strips: its eighth of the run at s ~970–1230 reads R − G +6.6, against +16 to +22 elsewhere.
- **MD12 was not sampled.** Its declared 12 m island lies on the crossover's asphalt in NAIP 2022: R − G −1.5 over
  its 45 pixels, the asphalt's own value. The terracotta nose visible on the photo stands beside it, not under it.

## How

- **The photo.** `tracks/san-diego-lake-murray/source/naip_2022_lm_full_z18.jpg` + `.georef.json` (Git LFS, sha256
  `1764a80b7f29b2946aec740193d346091bcc4a7fcded35fc62866c3fafa0ccd2`, branch `claude/lm-naip-full-20261123`
  commit 5b8da63e, not on main when measured). It is USDA NAIP flown 2022-04-25, 0.6 m, public domain, stitched at
  Web Mercator z18, about 0.50 m/px here.
- **The islands.** `medians[].polygon_xz` of MD11 and MD13 in `tracks/san-diego-lake-murray/data/expansion.north.json`.
  These are local ENU metres about its `frame.origin`, the same origin as `data/centerline.local.json`. A ring goes to
  mosaic pixels as `tools/naip_edge.py`'s `Naip.px` does: the WGS84 metres-per-degree series of
  `scripts/geometry/projection.py`, then the georef's z18 tiles. A pixel counts when its centre is inside.
- **The masks.** All three thresholds are [invented]:
  - **Inset 0.5 m [invented]**, one pixel, so no sampled pixel straddles the curb.
  - **Canopy: G − R > 5 [invented].** The asphalt beside the median reads G − R +1.6..+3.7 (bin means 3.5–6 m from
    the centre line: both sides of two MD13 stretches, and south-east of MD11). MD13's lit pixels read
    −29 / −20 / −7 (p10 / p50 / p90). The pixels the rule takes read +6 / +10 / +18, at luminance 54 / 64 / 103: the
    median's shrubs and tree crowns.
  - **Shadow: Rec. 709 luminance under 0.72 × the island's own median [invented on terracotta].** 0.72 is
    `scripts/aerial/road_wear.py`'s `tone.shadow_lum`, measured on Milford's NAIP asphalt and never on terracotta.
  - Both masks grow by one pixel, road_wear's rule for mixed edge pixels. The overlays were looked at: the shrubs, their
    shadows and a building's shadow across the median are what the masks take.
- **Registration checked, not corrected.** MD13 was cut into 8 pieces and each was slid ±3 m across its own axis in
  0.25 m steps. The R − G peak sat at 0.00, +0.75, −0.25, −0.25, −0.75, +0.25, +0.25 and +0.75 m: within 0.75 m of
  where it is declared.
- **Re-run** from the repo root with the mosaic pulled. It prints the JSON these tables come from:

```bash
python -I tools/measure_median_tone.py --mosaic tracks/san-diego-lake-murray/source/naip_2022_lm_full_z18.jpg \
  --islands MD11,MD13 --texture assets/textures/terracotta_paver_diffuse.jpg
```
