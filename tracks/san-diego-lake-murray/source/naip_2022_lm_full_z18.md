# NAIP 2022 at z18 over the whole box: `naip_2022_lm_full_z18.jpg` (2026-11-23)

Made for road wear at 10 cm (ledgers 0084 and 0099), which needs an aerial for the whole road. `naip_2022_lm_z18.jpg` and
its georef are unchanged.

- **The photo:** USDA FSA NAIP, flown 2022-04-25, 0.6 m, public domain, from the Microsoft Planetary Computer data API.
  It is stitched at Web Mercator z18, 0.597 m/px at the equator and about 0.50 m/px here.
- **The file:** 15,872 × 10,496 px, which is 62 × 41 = 2,542 tiles. It is 42,705,339 B, stored in Git LFS like the old
  file (`.gitattributes`: `tracks/*/source/naip_*_z18.jpg`). The JPEG uses quality 86 and 4:2:0, which are the old
  file's own quantisation tables.
- **The box:** `-117.101, 32.771978, -117.017012, 32.818386`. That is `naip_box.json` grown west from -117.0808 to -117.101
  for Phase 3. The tile grid reaches W -117.10190, E -117.01675, N 32.81844 and S 32.77111.
- **The georef:** `naip_2022_lm_full_z18.georef.json` keeps the old georef's keys. It adds `items`, `box`, `tiles`,
  `missing`, `partial`, `quality` and `source`. The tile origin is x0 45801, y0 105749, the old file's grid 15 tiles
  further west, so old pixel (px, py) is new pixel (px + 3840, py).
- **The items:** the four quarter-quads in `naip_2022_scenes.json`, used in that order. The sw quad gave 1,110 tiles, se
  1,184, nw 120 and ne 128. Each tile came whole from the first item whose STAC footprint holds it.
  - **Missing tiles: 0.** Partial tiles: 0. No pixel is magenta and none is nodata black.
- **The download:** 2,542 tile requests, with no 404s, came to 42,133,616 B. The four STAC items added 11,669 B.

Re-run from the repo root (Pillow only). `--raw` keeps the tiles as served and reuses them:

```bash
python -I tracks/exotics-racing-lv/source/trace/pc_tiles.py \
  ca_m_3211716_sw_11_060_20220425,ca_m_3211716_se_11_060_20220425,ca_m_3211716_nw_11_060_20220425,ca_m_3211716_ne_11_060_20220425 \
  18 -117.101 32.77197825417559 -117.0170118316261 32.81838584221009 \
  tracks/san-diego-lake-murray/source/naip_2022_lm_full_z18.jpg --raw <a new empty folder> --quality 86
```

**`pc_tiles.py` had to change.** The data API's old route, `/collections/naip/items/{item}/tiles`, now answers 404 "Not
Found" for every tile (checked 2026-11-23). Run on its old command line, the tool would now stitch an all-magenta
image. It now reads `/item/tiles`, which is the template in each item's tilejson asset. It also takes several items, and
fills a tile that one item covers only in part from the next item, using the tile's alpha.

**What the old file really holds.** Measured on its pixels, 2026-11-23:
- Its georef says `missing_tiles` 1,319. That count is from the fetch of the sw item alone, whose footprint touches 608
  tiles (16 columns × 38 rows).
- The picture itself has photo in all 1,927 tiles, and none is magenta. Nothing records where the other 1,319 came from.
- 87 tiles hold black nodata strips, 2.3 % of its pixels. They sit at the sw item's east edge (tile column 15), at the
  sw/se north edge (row 3), and at the ne item's south edge (row 6).
- Away from those strips, the new file matches the old one to a mean of 0.47 grey levels (JPEG noise). Both registrations
  agree to the pixel: a 1 px shift doubles the difference.
- The 74 tiles that differ by more than 1.5 levels are all strip tiles. There the new file has photo from the one item
  that holds the tile.
