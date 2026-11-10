# DATA-MANIFEST: public source files to re-fetch onto the PC

Written 2026-11-10 from the Mac, because `/Volumes/Drive` is damaged (cannot create files, one corrupt read).
Machine-readable list: `fleet/reference/DATA-MANIFEST.json` (schema 1). Nothing was downloaded to make it; every hash was
computed by reading the files. The PC re-downloads into `D:/k10-data/` (each file has a `dest`), only what was
downloaded before (Kevin: "PC re-fetches it"). Nothing new.

## Totals (re-fetchable, public)

| source | track | files | bytes | byte-exact? | where it is now |
|---|---|---|---|---|---|
| lidar_del_mar_d24 | del-mar-lm | 5 | 380.53 MB | yes | /Volumes/Drive |
| lidar_milford_oakland2016 | milford-road-course-lm | 81 | 39.65 MB | yes | /Volumes/Drive |
| lidar_livingston2018 | milford-road-course-lm | 7 | 1.04 MB | yes | system disk |
| lidar_co_eastern_b3_2018 | high-plains | 113 | 21.84 MB | yes | system disk |
| lidar_nv_clarkco_2_b22 | exotics-racing-lv-lm | 46 | 8.26 MB | yes | system disk |
| naip_2022_west_strip | milford-road-course-lm | 1 | 1.03 MB | unlikely | system disk |
| naip_planetary_computer_2023 | 5 circuits | 5 (9 listed, 4 need no fetch) | 42.99 MB | probably | /Volumes/Drive |
| maps_ppir | pikes-peak | 2 (3 listed, the png is a conversion) | 0.78 MB | yes if the publisher has not replaced the image | /Volumes/Drive |
| **total** | | | **496.12 MB** | | |

On `/Volumes/Drive` (the damaged SD): the D24 tiles, the Milford EPT, the 2023 crops, the maps. On the Mac's system disk only
(`/private/tmp/.../scratchpad/sys/dl`, 31 MB, not backed up either): the Livingston, High Plains and Nevada EPT sets and
the NAIP west strip.

## How to fetch each kind

- **ept_nodes / static_file**: HTTP GET `url`, check `size` then `sha256`. S3 (`usgs-lidar-public`) and `rockyweb.usgs.gov`.
  Byte-for-byte expected. USGS rockyweb answered HTTP 429 once: back off and retry.
- **naip_planetary_computer_2023**: the crops are not files on a server, they are a render. Recipe in the group's `params`
  (`tools/naip_crop.py` on `origin/claude/circuit-kerbs-lm`; each file also carries a ready `cli`). Same item + same box +
  same m/px gives the same tiles; compare `sha256` first, else width x height, corners and mean abs pixel difference.
  The 0.6 m High Plains file is derived (2x2 average of the 0.3 m one), not fetched. Exotics 2019/2022 are already in git.
- **naip_2022_west_strip**: ImageServer `exportImage`; renders can change, compare 328 x 3112 and the picture.
- **maps_ppir**: two published map images. The racingcircuits.info URL was NOT recorded in the repo; it was recovered from the
  2026-11-07 session transcript. Verify it serves the same map. `scca_trackmap_ppir.png` is a local conversion of the webp.

## Already safe in git (no re-fetch)

12 entries, 60.09 MB (sha-equal to a blob/LFS object on origin): the six `roadwear_work/img` NAIP images
(Lake Murray and Sand Creek z18 mosaics via LFS, Del Mar 2012, Milford 2022, Sand Creek 2023), `mf_work/inv/naip.jpg`, the
Exotics 2019/2022 0.6 m crops and a few kerb check stills. `git lfs pull` brings the z18 ones.

## Unique, not public: cannot be re-fetched

| file | size | what |
|---|---|---|
| `pp_work/sketch/routes/infield_only.json` | 11043 B | Kevin's own pen strokes (saved_at 2026-11-07T23:41:06Z), pixel coords on the PP NAIP 2023 crop. Used by maps_route.py (PPIR_SKETCH). NOT public, NOT re-fetchable. |
| `pp_work/sketch/routes/road_course.json` | 31398 B | Kevin's own pen strokes, road-course sketch over the same crop (same tool). NOT public. |
| `pp_work/sketch/sketch_overlay.jpg` | 972199 B | Render of Kevin's sketch over the crop (derived by pp_work/sketch/render_sketch.py, 963 B script, also on the SD): regenerable from the two JSONs; copy anyway, it is 0.97 MB |
| `pp_work/sketch/render_sketch.py` | 963 B | script that renders the sketch overlay (tiny) |

These need another way across (copy over the network or the PC's remote-control session): Kevin's two sketch JSONs
are the only irreplaceable files found (42,441 B together). The SD copy is the only one.

## Derived, regenerable once the sources are back (not listed for fetch)

46 files, 228.90 MB: Milford `veg.npz`/`veg_canopy.npz`/crowns/naip features (`mf_work/veg`), Del Mar
`points.npz`/`ground.npz`/`heightfield.npy` (`dm_work/p4*`), the `*_edges` scans and traced edges (`kerb_work`), `pave_mask.npy`
and caches (`pp_work`), `edges_work` JSON read off builds, `roadwear_work/scratch`. Hashes are in the JSON (`derived_regenerable`).
`pp_work/network.json` (570 B) is a by-eye pixel trace; the committed `infield_network.eyeball.json` is the same shape.

## UNTRACED

None among the raw downloads: every file in the inventoried directories is a ledger-recorded download, a sidecar-described
crop, a duplicate, a derivative or a build output. (The one weak link is the racingcircuits.info URL above.)

## Not inventoried

Build workshops and repo copies (`mf_work/*_src`, `v01x`, `c*`; `kerb_work/{hp012,r2,r3,nv012}`; `pp_work/ppir_base`;
`dm_work/{v02x,p*,b1}`; `edges_work/{mf,tmp}`; `roadwear_work/{lm,lmdata}`), and `fwlm_work`, `sclm_work`, `sc_mouths`, `g10`,
`claude_scratch`, `k10-colorado*`, `racing-desk*`, `menu_previews` (no raw downloads found). `dm_work` and `edges_work` hold no raw
downloads of their own: Del Mar's tiles are in `lidar_dl/del_mar_d24`.
