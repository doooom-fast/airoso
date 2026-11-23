# Denver Grand Prix survey data (fetched 2026-11-23)

Data directory (outside git, on the persistent volume): `/Volumes/Sundowning/Claude/airoso-data/denver-grand-prix/`  
Total 7.27 GB, 216 files. Every file's size was checked against the bucket listing (DRAPP) or the node manifest (EPT); SHA-256 of all 216 files is in `DATA.manifest.json` beside this file.

Fetched with: `curl -C -` for the DRAPP tiles (no existing script downloads whole tiles), the EPT walk of `lidar_coverage.py` with a 60 m pad, `tools/naip_crop.py` for NAIP. A Python venv with pyproj/numpy/pillow/laspy/lazrs is at `/Volumes/Sundowning/Claude/airoso-data/.venv`.

The corridor is 60 m either side of `data/lap_line.plan.json` (nodes densified to ~5 m, tile extents from the world files, EPSG:2232). It needs the six lap tiles plus two neighbours, **N1E190a** and **N1E190d**, in both years.

## DRCOG DRAPP 3-inch (2022 and 2020), `drapp/<year>/<tile>.tif|.tfw`

| file | URL | bytes | sha256 |
|---|---|---|---|
| drapp/2022/N1E190a.tif | https://drapparchive.s3.amazonaws.com/2022/N1E190a.tif | 446185267 | affa5fcf39441877… |
| drapp/2022/N1E190a.tfw | https://drapparchive.s3.amazonaws.com/2022/N1E190a.tfw | 41 | b8d9bacd5453cd24… |
| drapp/2022/N1E190c.tif | https://drapparchive.s3.amazonaws.com/2022/N1E190c.tif | 446185467 | 0984100877f234bb… |
| drapp/2022/N1E190c.tfw | https://drapparchive.s3.amazonaws.com/2022/N1E190c.tfw | 41 | 3b6dd564985cf2c7… |
| drapp/2022/N1E190d.tif | https://drapparchive.s3.amazonaws.com/2022/N1E190d.tif | 446178937 | 9b5b137ff9b613bc… |
| drapp/2022/N1E190d.tfw | https://drapparchive.s3.amazonaws.com/2022/N1E190d.tfw | 41 | 1e495993befba0f2… |
| drapp/2022/N1W199b.tif | https://drapparchive.s3.amazonaws.com/2022/N1W199b.tif | 446183833 | 08f69dd76a52d2f1… |
| drapp/2022/N1W199b.tfw | https://drapparchive.s3.amazonaws.com/2022/N1W199b.tfw | 41 | f4955a09994b9cf9… |
| drapp/2022/N1W199d.tif | https://drapparchive.s3.amazonaws.com/2022/N1W199d.tif | 446179675 | 7f05bb9988f734c1… |
| drapp/2022/N1W199d.tfw | https://drapparchive.s3.amazonaws.com/2022/N1W199d.tfw | 41 | c274ab9243ba42da… |
| drapp/2022/S1E100a.tif | https://drapparchive.s3.amazonaws.com/2022/S1E100a.tif | 446180121 | 64285cb093631463… |
| drapp/2022/S1E100a.tfw | https://drapparchive.s3.amazonaws.com/2022/S1E100a.tfw | 41 | 38fae0622e8069b4… |
| drapp/2022/S1E100b.tif | https://drapparchive.s3.amazonaws.com/2022/S1E100b.tif | 446179433 | 85fdaaf981ec8441… |
| drapp/2022/S1E100b.tfw | https://drapparchive.s3.amazonaws.com/2022/S1E100b.tfw | 41 | 4b19db4ff12db07f… |
| drapp/2022/S1W109b.tif | https://drapparchive.s3.amazonaws.com/2022/S1W109b.tif | 446176419 | e55ba9d478b05d9a… |
| drapp/2022/S1W109b.tfw | https://drapparchive.s3.amazonaws.com/2022/S1W109b.tfw | 41 | c906927d5ef6048d… |
| drapp/2020/N1E190a.tif | https://drapparchive.s3.amazonaws.com/2020/N1E190a.tif | 446203673 | 4df07db257d04bf4… |
| drapp/2020/N1E190a.tfw | https://drapparchive.s3.amazonaws.com/2020/N1E190a.tfw | 41 | b8d9bacd5453cd24… |
| drapp/2020/N1E190c.tif | https://drapparchive.s3.amazonaws.com/2020/N1E190c.tif | 446201395 | 31da6d1b9961f163… |
| drapp/2020/N1E190c.tfw | https://drapparchive.s3.amazonaws.com/2020/N1E190c.tfw | 41 | 3b6dd564985cf2c7… |
| drapp/2020/N1E190d.tif | https://drapparchive.s3.amazonaws.com/2020/N1E190d.tif | 446199251 | a8ce441a65dde378… |
| drapp/2020/N1E190d.tfw | https://drapparchive.s3.amazonaws.com/2020/N1E190d.tfw | 41 | 1e495993befba0f2… |
| drapp/2020/N1W199b.tif | https://drapparchive.s3.amazonaws.com/2020/N1W199b.tif | 446202347 | a570d166479a8702… |
| drapp/2020/N1W199b.tfw | https://drapparchive.s3.amazonaws.com/2020/N1W199b.tfw | 41 | f4955a09994b9cf9… |
| drapp/2020/N1W199d.tif | https://drapparchive.s3.amazonaws.com/2020/N1W199d.tif | 446199609 | 302fefd77437697b… |
| drapp/2020/N1W199d.tfw | https://drapparchive.s3.amazonaws.com/2020/N1W199d.tfw | 41 | c274ab9243ba42da… |
| drapp/2020/S1E100a.tif | https://drapparchive.s3.amazonaws.com/2020/S1E100a.tif | 446199025 | a1b5929468f3d027… |
| drapp/2020/S1E100a.tfw | https://drapparchive.s3.amazonaws.com/2020/S1E100a.tfw | 41 | 38fae0622e8069b4… |
| drapp/2020/S1E100b.tif | https://drapparchive.s3.amazonaws.com/2020/S1E100b.tif | 446198969 | a64767f69cb998a1… |
| drapp/2020/S1E100b.tfw | https://drapparchive.s3.amazonaws.com/2020/S1E100b.tfw | 41 | 4b19db4ff12db07f… |
| drapp/2020/S1W109b.tif | https://drapparchive.s3.amazonaws.com/2020/S1W109b.tif | 446196739 | b6ffb46e5c326306… |
| drapp/2020/S1W109b.tfw | https://drapparchive.s3.amazonaws.com/2020/S1W109b.tfw | 41 | c906927d5ef6048d… |

## NAIP 2023 (0.3 m, 2023-09-25), `naip/` — crop of the lap bbox + 60 m: -105.004058,39.737231,-104.981631,39.750171

| file | bytes | sha256 |
|---|---|---|
| naip/co_m_3910417_nw_13_030_20230925_20240104_lap60m.json | 356 | 2184b0238215f90b… |
| naip/co_m_3910417_nw_13_030_20230925_20240104_lap60m.png | 60786172 | 81a09f728a3ee587… |
| naip/co_m_3910524_ne_13_030_20230925_20240104_lap60m.json | 356 | 26fee6ae34705004… |
| naip/co_m_3910524_ne_13_030_20230925_20240104_lap60m.png | 21984597 | f440e27d1e2df778… |

Scene 3910417_nw covers the lap; the 3910524_ne crop is the western margin past Auraria Pkwy (the part of the box outside that scene is blank). Each PNG has a .json sidecar (corners, GSD) beside it.

## Lidar CO_DRCOG_2_2020, `lidar/<d-x-y-z>.laz`

180 EPT nodes touching the 60 m corridor (7,612,795 points in the nodes), 50.4 MB, URLs `https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CO_DRCOG_2_2020/ept-data/<key>.laz`. Whole nodes are kept (not clipped to the corridor); clip when reading. `lidar/ept.json` and `lidar/hier/` hold the EPT header and hierarchy pages; per-node checksums are in `DATA.manifest.json`. (Dossier counted 141 nodes at 15 m; 180 at 60 m.)

## Refused or missing

Nothing refused. No host failed. 2024 DRAPP (403 per the dossier) was not requested. The 3DEP 1/3 arc-second DEM tiles are another session's.
