# Satellite / aerial imagery → hi-res road textures in AC

*Research study, 2026-10-28, for an Opus build session. Kevin's question: "Look into using satellite
images of the roads to create hi-res textures for use in AC."*

> **Repo note.** Researched in a `k10-track-agents` cloud session on 2026-10-28 and ported here the
> same day. The engine work in §6 lands in this repo's `scripts/` (never move its paths).

**How to read the evidence.** `[repo]` means read from this checkout today. `[src]` means the claim
is backed by the linked source. **[unverified]** means it was not confirmed this session. Two limits
applied. The session's network policy blocked overtake.gg, assettocorsamods.net, every county/USGS
GIS host and the AWS registry page, so endpoint URLs below come from search results and were
**not probed live**. The shared web-search budget also ran out mid-study, so the NAIP per-state
vintages (Nevada, Colorado, Michigan), the Maxar/Planet EULAs, shadow-removal literature and Kunos
road texture sizes stay **[unverified]**. Each one has a named way to verify it.

---

## 0. The answer in one paragraph

Yes, with one constraint. Use public-domain or owned orthoimagery as the **macro colour layer** on
the road: real patches, seal lines, stains, the rubbered line. Bake it into a **road-following
strip atlas** so texels are spent only on asphalt. Then multiply it by an **owned/CC0 tiled micro
asphalt detail** through the stock Kunos shader `ksPerPixelMultiMap_NMDetail`
(`txDetail` × `detailUVMultiplier`, masked by `txDiffuse` alpha). Lane paint stays as the
geometry it already is.

Texture memory is not the constraint: a 1.2-mile lap at 5 cm/px fits in **one 4096²** atlas. The
constraints are (1) the **real GSD** of imagery you are allowed to ship, (2) the **registration**
between the OSM-derived mesh and the photo, and (3) **baked shadows** under AC's moving sun. The
cleanest shippable sources at our tracks are NAIP (public domain, 30–60 cm) and **Kevin's own drone
orthomosaic** (1–3 cm, owned). County 3–15 cm orthos are often *not* redistributable. Clark County
NV in particular licenses its data "for the licensee's own business use".

---

## 1. Where the engine is today `[repo]`

| Fact | Where | Consequence for this work |
|---|---|---|
| The **road ribbon's UVs already follow the road**: U = lateral offset / `tile_m`, V = cumulative arc / `tile_m` (4 m on the main path, 8 m on connectors). Only the **grass terrain** is world-planar (x/tile, z/tile). | `scripts/geometry/ribbon.py:71-110` (`road_ribbon`), `:667-694` (`grass_terrain`); `build_mesh.py:960,1010` | Option (b) below is a **re-mapping of UVs that already exist**, plus splitting the ribbon at strip boundaries. It is not a new parameterisation. |
| Projection is a local equirectangular ENU plane about the centroid: `x=(lon-lon0)·m_lon`, `z=(lat-lat0)·m_lat`, WGS84 series. | `scripts/geometry/projection.py:58-80` | Inverts in closed form (x,z → lon,lat), so a bake can map texel → world → ortho pixel exactly as the mesh was placed. |
| The kn5 exporter writes **only `txDiffuse` + `txNormal`** and picks `ksPerPixelMultiMap` if a normal exists, else `ksPerPixel` (or `ksTree` for billboards). No `txMaps`, `txDetail`, `txNormalDetail`, `detailUVMultiplier`. | `scripts/ac/export_kn5_addon.py:83-103`; native path `kn5_write.py:186-199`, `kn5_native.py:35-48` | The macro+micro material needs the exporter to emit three more texture slots and two VARs (§6.4). |
| `1ROAD` gets **no shader VARs**: `KS_PROPS` has no road entry, so `VARCOUNT=0`. The `_SHADERS` road scalars in `materials.py` are never written by the addon path. | `export_kn5_addon.py:120-126`, `pbr.py KS_PROPS`, `materials.py:14-16` | The road runs on shader defaults today. Fix this in the same change. |
| **The shipped road texture is mined.** `1ROAD`/`1RUNOFF` bind `asphalt_cracked_*.jpg`, extracted from LA Canyons and marked "Personal/non-distributed use only". | `pbr.py:16-17`, `assets/textures/SOURCES.txt` | Every distributed k10 kn5 embeds a non-redistributable road texture **today**. A clean macro+micro road fixes a licensing hole as well as the look. |
| Clean candidates already in the repo: `asphalt_diffuse/normal.jpg` (Poly Haven `aerial_asphalt_01`, CC0, ~30 m real-world scale), the procedural generator pattern in `scripts/assets/make_gravel.py` (seeded, ours), and `scripts/capture/textures.py`, which builds a de-lit, seamless road texture from Kevin's own capture video by **temporal median**. | `SOURCES.txt`, `scripts/assets/`, `scripts/capture/textures.py:1-15` | The micro layer can be **owned** (capture-derived or procedural). The temporal-median idea also carries over to multi-vintage ortho cleaning (§4.5). |
| The aerial georef is a 2-point north-up affine for screenshots. | `scripts/aerial/georef.py` | Unsuitable for orthos: use the GeoTIFF's own geotransform + CRS (often State Plane **feet**) via pyproj. |
| L7: **NPOT textures can hard-freeze the GPU**; every material needs a texture. L5: gate the built artifact. | `fleet/LAWS.md` | Atlases are PoT. Gates read UVs from the built `track.obj`/kn5 and the shipped DDS. |

---

## 2. Imagery sources: GSD, vintage, licence for a free mod

| Source | Real GSD | Vintage / cadence | Coverage at our tracks | Licence for redistribution in a free mod | Verdict |
|---|---|---|---|---|---|
| **USDA NAIP** | 60 cm standard since 2018, 30 cm optional ([CA 2024 metadata](https://gis.data.ca.gov/datasets/naip-2024-60cm-california)). 2023 cycle: USDA briefing says "most states successfully acquired at 15–30 cm" ([USDA FPAC GEO slides](https://ftpgeoinfo.msl.mt.gov/Documents/MSDI/Imagery/Presentations/USDA%20FPAC%20GEO%20Montana%20Imagery%20Slides.pdf)). States can buy up to 30/15 cm ([AZ AGIC notes](https://agic.az.gov/agic/sites/default/files/Statewide%20Imagery%20Program%20Discussion%20Agenda%20-%20December%202022%20Meeting%20Notes.pdf)). 2025: about half the states at 30 cm ([CA metadata](https://gis.data.ca.gov/datasets/naip-2024-60cm-california)). | Leaf-on, ~2–3 yr cycle, ≤10 % cloud per quarter-quad ([FEMA NAIP sheet](https://hazards.fema.gov/femaportal/docs/6_NAIP.pdf)). | All CONUS. **CA 2024 = 60 cm** ([src](https://gis.data.ca.gov/datasets/naip-2024-60cm-california)). **NV / CO / MI latest GSD: [unverified]**; read the `{res}` folder in `naip-visualization/manifest.txt` (§6.2). | **Public domain**: "may be freely distributed or copied, but … credits are requested" ([GEE NAIP catalog](https://developers.google.com/earth-engine/datasets/catalog/USDA_NAIP_DOQQ)). | **Ship.** Baseline macro for every track; too coarse alone near the car (§3). |
| **USGS High-Resolution Orthoimagery (HRO)** via EarthExplorer | 0.3–0.75 m urban ([archived USGS](https://webarchive.library.unt.edu/eot2008/20090114021326/http://seamless.usgs.gov/website/seamless/products/highortho.asp); [MN 2012 HRO](https://gisdata.mn.gov/it/dataset/base-usgs-msp-2012-airphotos)) | Irregular, often 2004–2012 vintages | Metro areas only | Public access under the USGS Standard Disclaimer ([MN record](https://gisdata.mn.gov/it/dataset/base-usgs-msp-2012-airphotos)); explicit PD wording **[unverified]** | Usually older and coarser than NAIP 30 cm. Fallback only. |
| **Michigan MiSAIL** (statewide) | Contract allows 3–12 inch ([DTMB](https://www.michigan.gov/dtmb/procurement/mideal-extended-purchasing-program/mideal-contract-search/categories/folder-2/aerial-imagery-services)) | Leaf-off, ~¼ of the state per year ([NSGIC 2023](https://nsgic.org/wp-content/uploads/2024/02/2023GMAMichiganReportCard.pdf)) | Statewide | 12-inch statewide is **view-only, not downloadable** ([MiSAIL](https://www.michigan.gov/dtmb/services/maps/misail)) | **Don't.** Go to the county. |
| **Oakland County, MI** | **3 inch (7.6 cm)**, 0.25 ft, 4-band; Sanborn, UltraCam Osprey M3 ([OC 2025 service](https://data.ferndalemi.gov/datasets/oakgov::oc-2025-tc-cir-ortho-image-service)) | **2025-04-27 → 05-12**, leaf-off spring; annual-ish ([OC current](https://data.ferndalemi.gov/datasets/oakgov::oc-ortho-current-image-service)) | Pontiac / Clarkston: **M1 Concourse and Waterford Hills sit in Oakland County** | "Open Data Terms of Use Agreement" (custom); full text **[unverified]**. Uncompressed TIFF/TFW + MrSID downloads. | **Best Michigan candidate.** Read the terms and get written OK before shipping. |
| **Clark County, NV** (GISMO) | Cached map service "Most Current Aerial Imagery": finest cache level 0.434 ft ≈ **13 cm** ([MapServer](https://maps.clarkcountynv.gov/arcgis_images/rest/services/CACHED/mostcurrentflight/MapServer)). Project path hints Spring 2020 **[vintage unverified]**. | Periodic | Countywide incl. Speed Vegas | Subscriber agreement: county holds copyright, licenses for "the licensee's own business use", reformats keep the same restrictions ([agreement](https://maps.clarkcountynv.gov/Gismo/pdf/subscriber-agreement.PDF)). The free-data page is "reference only, no warranty" ([free GIS data](https://www.clarkcountynv.gov/government/departments/geographic_info_systems/services/free-gis-data1)). | **Not shippable without written permission.** Fine as a Blender reference underlay (§4d). Ask GISMO (gismo@co.clark.nv.us). |
| **Vexcel** (NV) | Statewide 15 cm; metro TrueOrtho / Urban 7.5 cm ([Vexcel](https://vexceldata.com/?p=16610)) | Annual programme | NV statewide | Commercial licence | Paid; redistribution in a mod unlikely. |
| **DRCOG DRAPP** (Denver) | 3 in / 6 in products ([DRAPP 2016](https://geodata.colorado.gov/datasets/drapp-2016); [2022 3 in](https://online.greenwoodvillage.com/imgserver/rest/services/Imagery/GVImagery2022_3in_6scale/ImageServer/info/iteminfo)) | Every 2 yr since 2002 | IMI, Second Creek | **Current vintage sold via Sanborn; past vintages free** from the Regional Data Catalog ([DRCOG](https://drcog.org/data-maps-modeling/data-acquisition-projects)). The CC0 tag is on the *tile index* ([data.colorado.gov](https://data.colorado.gov/Environment/DRCOG-Denver-Regional-Aerial-Photography-Project-D/x58c-gn3h)), not proven for the imagery. | Past vintage likely OK; confirm with geospatial@drcog.org. |
| **SanGIS** (San Diego) | **9 inch** countywide for 2019 and 2023 ([request form](https://gis.sangis.org/Documents/services/Aeria_Imagery_Request_Form.pdf)). The 2023 grid is titled "**NearMap** Imagery … Flown January 2023" ([index](https://gis.sangis.org/Documents/services/2023_Aerial_Imagery_Index.pdf)). | 2019, 2023 | Lake Murray, SD freeway | $200 GeoTIFF. The SANDAG 2017 service cites Pictometry licence constraints ([SANDAG](https://gis.sandag.org/sdgis/rest/services/Imagery/SD2017_9inch/ImageServer/info/iteminfo)). | **Treat as licensed (Nearmap/Pictometry).** Underlay only. |
| **Nearmap** | ~5.5–7.5 cm **[unverified]** | Several flights/yr | Metro US | Derivatives only for a "Permitted Purpose" excluding any Commercial Purpose. Attribution required; image databases prohibited ([OSM wiki](https://wiki.openstreetmap.org/wiki/Nearmap); [reseller EULA](https://mindsightstudios.com/eula/nearmap-3d/)). | No. |
| **Maxar / Planet 30 cm satellite** | 30 cm **[unverified]** | Tasked | Global | Commercial EULA **[unverified]**. Maxar Open Data is CC BY-NC 4.0 and event-scoped ([OSM wiki](https://wiki.openstreetmap.org/wiki/Vertical_Aerial_Photographs)). | No. Satellite 30 cm is also worse than county aerial. |
| **Google Maps / Earth** | – | – | – | Maps Platform ToS §3.2.3(a): "will not export, extract, or otherwise scrape Google Maps Content for use outside the Services", incl. bulk tile download ([quoted](https://community.cesium.com/t/saving-google-map-data/31228)). Photorealistic 3D Tiles: no offline use (RESEARCH.md B5). | **Prohibited. Never in a shipped asset.** |
| **Bing Maps** | – | – | – | No derivative works. "Tracing or extracting features … including imagery" is prohibited, and Bing forbids derivative datasets/tiles ([Bing blog](https://blogs.bing.com/maps/August-2008/Purchase-Standalone-Microsoft-Virtual-Earth-Photog); [OSM legal-talk](https://lists.openstreetmap.org/pipermail/legal-talk/2010-December/005570.html)). The only exception is OSM tracing ([OSM wiki](https://wiki.openstreetmap.org/wiki/Bing_Maps)). | **Prohibited.** |
| **Esri World Imagery** | – | – | – | Standard layer not for export. The "(for Export)" layer is for small-volume offline use **in ArcGIS apps**, capped at 100k / 150k tiles ([Esri community](https://community.esri.com/t5/arcgis-image-server-questions/arcgis-online-basemap-imagery-licensing/m-p/257788); [Wayback Export](https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/imagery/wayback-export)). Content is third-party (Maxar etc.). | **Not a redistribution licence. Prohibited.** |
| **OpenAerialMap** | Varies (drone) | Ad hoc | Rarely at US tracks | CC-BY 4.0 by default, some uploads add SA/NC ([OAM legal](https://openaerialmap.org/legal)) | Ship with attribution if a BY-only scene exists. Unlikely. |
| **Kevin's drone** | **~1–3 cm** at 40–80 m AGL with a 1-inch sensor **[unverified, use the vendor GSD calculator]** | Whenever, at noon, track closed | Exactly the track | **Owned.** | **The clean high-res path.** See below. |

**Drone rules for that last row.** Recreational flight under 49 USC 44809 needs TRUST and is capped
at 400 ft AGL in Class G. Break any condition of the statute and the flight is treated as a Part 107
operation. LAANC covers both 44809 and Part 107, but only Part 107 can ask above the UAS Facility
Map ceiling ([FAA AIM 11-4](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap11_section_4.html);
[FAA JO 7210.914](https://www.faa.gov/documentLibrary/media/Notice/N_JO_7210.914_Low_Altitude_Authorization_and_Notification_Capability_-_LAANC.pdf)).
Whether a free public mod counts as "recreational" is a grey area. Hold a **Part 107** certificate
to remove the doubt ([Drone Girl, 2025](https://www.thedronegirl.com/2025/12/18/fly-drones-recreationally/)
advises 107 "if there's any chance" of other use).

Always get the track's written permission; it is private property. **Speed Vegas sits under Las
Vegas Class B shelving and near Henderson Executive's Class D**, so check B4UFLY for the exact grid
ceiling ([summary, weak source](https://dronepilothq-pages.pages.dev/can-i-fly-a-drone-in-henderson-nv)).

Processing: OpenDroneMap produces orthomosaic + DSM, and it is open source **[unverified this
session]**. The DSM also gives independent surface truth for R4.

---

## 3. What resolution actually matters in AC

**Viewing geometry.** Assume eye height 1.1 m, a 1920-px screen and 90° HFOV, so one screen pixel
spans 0.047°. Footprint of one screen pixel on the road (computed):

| Distance ahead | Grazing angle | Lateral footprint | Longitudinal footprint |
|---|---|---|---|
| 5 m | 12.4° | 0.4 cm | 1.9 cm |
| 20 m | 3.2° | 1.6 cm | 30 cm |
| 50 m | 1.3° | 4.1 cm | 1.9 m |
| 100 m | 0.6° | 8.2 cm | 7.4 m |
| 200 m | 0.3° | 16 cm | 30 m |

The ortho is texel-starved closer than **d\* ≈ GSD × 1222**: **~370 m at 30 cm, ~180 m at 15 cm,
~60 m at 5 cm, ~30 m at 2.5 cm**. This is the quantitative form of "mush at 20 m, right at 200 m".
Inside d\*, something other than the photo must carry the look, and that is the **micro detail
layer**. Hardware **anisotropic filtering** (max 16× in D3D11 ([MS Learn](https://learn.microsoft.com/windows/win32/direct3d11/overviews-direct3d-11-resources-limits)))
resolves the longitudinal smear. It cannot invent lateral detail.

**The standard technique (macro + micro).** The road material carries a low-frequency macro colour
map: one large diffuse for the whole road, "you only want to use one single diffuse for your entire
road". Colour variation and close-up grain come from detail textures
([assettocorsamods "Photo Quality Road Surface"](https://assettocorsamods.net/threads/photo-quality-road-surface.834/page-5),
via search snippet). Kunos's road shader per the same thread is `ksMultilayer_fresnel_nm`.

**Shaders that accept a detail texture, and how the UVs work:**

| Shader | Slots | Detail mapping | Mask | Native / CSP |
|---|---|---|---|---|
| **`ksPerPixelMultiMap_NMDetail`** | `txDiffuse`, `txNormal`, `txMaps`, `txDetail`, `txNormalDetail` | **UV0 × `detailUVMultiplier`**, one scalar for both axes | **`txDiffuse` alpha.** Reimplemented in Content Manager's renderer as `diffuse *= detail*(1-a) + a`, and the normal as `n += (detailN-0.5)·detailNormalBlend·(1-a)`. So a=0 gives full detail, a=1 none ([actools `SimpleMaterial.fx` L206-224](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Shaders/Simple/SimpleMaterial.fx); [`Kn5MaterialSimpleMaps.cs`](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificForward/Materials/Kn5MaterialSimpleMaps.cs)). Matches "the more black the more detail" ([RD thread](https://racedepartment.com/threads/the-dumb-questions-thread.129295/page-5)). | Native Kunos |
| `ksPerPixelMultiMap_AT_NMDetail` | same + alpha test | same | same | Native (in CM's shader switch, [`MaterialsProviderSimple.cs`](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificForward/Materials/MaterialsProviderSimple.cs)) |
| `ksPerPixelMultiMap` (what we use) | `txDiffuse`, `txNormal`, `txMaps`, `txDetail` | UV0 × `detailUVMultiplier` | diffuse alpha | Native. A detail slot exists, but there is no detail normal. |
| **`ksMultilayer_fresnel_nm`** (Kunos roads) | `txDiffuse`, `txMask` (RGBA), `txDetailR/G/B/A`, `txNormal` | Per-channel scale `multR/G/B/A`. One snippet claims "top-down projection rather than UV" **[unverified; read it with Objects Inspector]**. | `txMask` channel picks the detail; `txDiffuse` alpha = specular level ([forum snippets](https://assettocorsamods.net/threads/how-could-i-get-this-out-of-blender-to-configure-it-in-kseditor.3023/)) | Native |
| `ksMultilayer_fresnel_nm4` | adds 4 detail normals aligned with the details; `tilingFixR/G/B/A` | as above | `txMask` | **CSP** ([doc](https://gitlab.com/ac-custom-shaders-patch/public/acc-shaders/-/raw/master/docs/ksMultilayer_fresnel_nm4.md)) |
| `nePerPixelMultiMap_AT_NMDetail_stickers` | adds `txStickers` on **UV2** (`.uv2` sidecar file beside the kn5) | UV2 is **half precision**: fine in 0–1. fp16 steps near 1.0 are 2⁻¹¹ ≈ **4 texels on an 8k map** (computed), so only ≤2k overlays register | sticker alpha | **CSP** ([UV2 wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-UV2)) |

CSP's `[SHADER_REPLACEMENT_…]` can retrofit any of these without re-exporting: `SHADER=`,
`PROP_…=detailUVMultiplier, N`, `RESOURCE_n=txDetail` + `RESOURCE_FILE_n=custom.dds`,
`FILL_MISSING_TEXTURES=1`, and **`FORCE_MINUS_TWO_LOD_BIAS=1`** for sharper sampling
([CSP wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)).
The wiki's own example names the detail-normal slot `txDetailNM`, while CM's code reads
`txNormalDetail`. **Read the real slot name off a Kunos material with CSP Objects Inspector before
coding it** (RESEARCH.md A2).

**Isotropy constraint (load-bearing design fact).** Detail is sampled at **UV0 × one scalar**. If
one UV unit covers 15 m across and 1000 m along, the detail stretches 67:1. **The macro atlas must
map one UV unit to square ground** for the detail to stay round. World-planar UVs satisfy this, and
so does the strip atlas of §4(b). A naive "U across width, V = 0..1 along a 1 km piece" does not.

**Why many "satellite" mods drape imagery on the terrain, not the road.** Terrain is seen at long
range, where d\* is satisfied, so a 30–60 cm drape reads right and replaces a thousand hand-painted
decisions. The road is seen at 0–50 m, which is inside d\* for every public source, so a draped ortho
alone looks like mush. Builders tile a detail texture on the road and add a mask
([RTB/terrain snippets](https://assettocorsamods.net/threads/terrain-texture.1073/);
[GTPlanet reviews: "blurry or crusty"](https://www.gtplanet.net/forum/threads/assetto-corsa-track-reviews.398544/)).
Specific build notes for Pikes Peak / LA Canyons / Transfagarasan imagery use are **[unverified this
session]**: overtake.gg was unreachable. RESEARCH.md A1 records that Transfagarasan used
laser-scan + photogrammetry rather than satellite.

---

## 4. Pipeline options

| | (a) World-planar drape | (b) Road-following strip atlas | (c) Hybrid macro+micro | (d) Reference underlay only |
|---|---|---|---|---|
| UV | `(x-x0)/S, (z-z0)/S` over the whole bbox (as `grass_terrain` does) | Each ribbon piece's (s,t) packed into vertical strips of a PoT atlas; 1 UV unit = S m in both axes | (a) or (b) for macro + `txDetail` | n/a (Blender image plane) |
| Texels on asphalt | ~1–5 % of the texture | ~85 % (road + shoulder + gutter) | as chosen | – |
| Fits 1 × 8k at 15 cm | bbox ≤ 1.23 km square | **~86 km of 15 m road** (computed) | – | – |
| Registration | exact by construction | exact by construction, if baked from the mesh | – | – |
| Seams | none | at strip ends (cut the mesh there) | – | – |
| Best for | compact circuits; terrain + runoff | long street ports, rally stages, freeways | **ship this** | **every track, always** |

**Recommendation: (c) = (b) macro + owned micro, with (d) always on.** Keep (a) for terrain and
runoff on compact circuits, where the bbox fits: 700 × 500 m at 7.5 cm is 9333 × 6667 px, which
fits in one 16384 tile or two 8k tiles.

### 4.1 The strip-atlas math (option b)

Let the centerline polyline have arc length `s ∈ [0, L]`, left normal `n(s)`, and width `w(s)`.
Ribbon vertices are `P(s,t) = C(s) + t·n(s)` with `t ∈ [-w/2, +w/2]` (exactly `road_ribbon`'s
construction, including `_cap_offset`). Pick GSD `g` (m/px), atlas size `N` (PoT), and strip width
`Wpx = ceil(W_max/g) + 2·gutter`. The mesh is already split into ≤1 km pieces (RESEARCH.md A3).
Choose **strip length = piece length ≤ N·g** so seams coincide with existing piece cuts. Strip `k`
occupies columns `[k·Wpx, (k+1)·Wpx)`:

```
u = (k·Wpx + gutter + (t + W_max/2)/g) / N
v = (s - s_k0) / (g·N)                      # 1 UV unit = g·N metres on both axes → isotropic
detailUVMultiplier = g·N / D                # D = micro tile size in metres (e.g. 4 m)
```

On curves the ground under a texel is scaled by `(1 - κ·t)` along `s`. The bake absorbs this, so
the image does not distort; only texel density varies. The gate bounds it (§6.5).

**Bake from the mesh, not the formula.** Rasterise each ribbon triangle in UV space and
barycentrically interpolate its world `(x,z)` per texel. Then:

```
x,z  → lon = lon0 + x/m_lon,  lat = lat0 + z/m_lat              (projection.py inverse)
lon,lat → ortho CRS (pyproj; NAIP = UTM/NAD83, Oakland = MI South State Plane intl ft, Clark = NV East ft)
→ (col,row) = ~geotransform · (X,Y) → bicubic sample
```

Interpolate world positions across each triangle exactly the way the GPU interpolates UVs, so
**misregistration between texture and mesh is zero by construction**. All remaining error is
imagery-vs-centerline error (risk R2).

Gutters are filled by edge-extend (dilate) and must be ≥ 2^m px for the deepest mip `m` you care
about. With 8–16 px, the gutter holds to mip 3–4. Beyond that a 116-px strip is under 8 px and the
neighbour is asphalt anyway.

**Texture budget** (computed: W = 15 m incl. shoulder, 8 px gutters, PoT strip packing):

| GSD | 1.2 mi lap (Speed Vegas) | 3 km corridor | 25 km (Lariat-class) |
|---|---|---|---|
| 30 cm | 0.4 Mpx → **1024²** | 0.7 Mpx → 1024² | 5.5 Mpx → 4096² |
| 15 cm | 1.5 Mpx → **2048²** | 2.3 Mpx → 2048² | 19 Mpx → 8192² |
| 7.5 cm | 5.6 Mpx → **4096²** | 8.6 Mpx → 4096² | 72 Mpx → 2 × 8192² |
| 5 cm | 12 Mpx → **4096²** | 19 Mpx → 8192² | 158 Mpx → 3 × 8192² |
| 2.5 cm (drone) | 48 Mpx → **8192²** | 74 Mpx → 2 × 8192² | 616 Mpx → 10 × 8192² |

Sizes in VRAM, with mips adding +33 %: BC1 is 0.5 B/px, BC3/BC7 are 1 B/px. So **8192² is 32 MB BC1
or 64 MB BC7**, and 4096² is 8 / 16 MB. D3D11 FL11 allows **16384²** (128 MB BC1); the per-resource
cap is min(max(128 MB, ¼·VRAM), 2 GB) ([MS Learn limits](https://learn.microsoft.com/windows/win32/direct3d11/overviews-direct3d-11-resources-limits);
[feature levels](https://learn.microsoft.com/windows/win32/direct3d11/overviews-direct3d-11-devices-downlevel-intro)).
A forum report of a 16384×4096 BC7 DDS loading in AC is consistent with this
([GTPlanet](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-5085)).
Prefer **8192 as the per-file ceiling** for driver headroom; L7 freeze history argues against
pushing limits.

Use **BC1** for macro RGB with 1-bit alpha. Use **BC3/BC7** if the diffuse alpha carries a graded
detail mask, which it does here. **Conclusion: the texture budget is a non-issue.** Even the whole
fleet at 5 cm is a few hundred MB on disk, and only one track loads at a time.

Precision is fine. Today's `V = arc/4 m` at 25 km is 6250 with an fp32 ULP of ~3 mm (computed). The
atlas keeps UVs in 0–1.

**How Kunos ships it.** Do not guess texture sizes and parameters. Measure 2–3 `ks_*` roads in game
with **CSP Objects Inspector** (shader, every param, texture sizes) and `modkit.inspect_kn5`, per
RESEARCH.md A2 / REALISM §3. Record the numbers in `fleet/reference/MEASURED.md`, and copy
`detailUVMultiplier`, `ksAmbient/ksDiffuse/ksSpecular/ksSpecularEXP` and the txMaps balance from
them.

### 4.2 The micro layer

An **owned/CC0** asphalt grain at ~2–5 mm/px, e.g. a 2048² tile covering 4–8 m. Three sources, in
order: (1) `scripts/capture/textures.py` output from Kevin's own drive capture (owned; already
de-lit and seamless); (2) a seeded procedural generator in the `make_gravel.py` mould; (3) a
close-range CC0 asphalt from Poly Haven / ambientCG **[specific asset unverified]**. The current
`asphalt_diffuse.jpg` is ~30 m-scale aerial asphalt and is the wrong scale for micro.

Because the shader **multiplies**, normalise the detail to **mean ≈ 1** (store at ~0.8 mean and
pre-brighten the macro by 1/0.8). Otherwise the photo darkens. Supply `txNormalDetail` with
`detailNormalBlend` around 0.5–1 **[tune in game]**.

Use **`txDiffuse` alpha as a detail mask**: 0 on asphalt (full grain); towards 1 on paint, concrete
patches and kerb-adjacent gutter, where asphalt grain is wrong.

### 4.3 Lane paint

At 15 cm GSD a 10–15 cm lane line is 1 px, soft and mis-registered. The engine already builds
`MARKINGS`/`YLINE` geometry from data. **Inpaint paint out of the macro**: mask by brightness plus
the known marking polylines, then fill. Keep markings as geometry. Only at ≤ 3 cm (drone) may the
ortho's own paint survive, and even then the mesh lines win on crispness.

### 4.4 Option (d): the underlay, always

REALISM Job 1 already calls for "aerial imagery draped for reference". The same fetched ortho
becomes a `GEN_ortho_ref` image plane in the `.blend`: world-planar, slightly below the road,
regenerated freely per the §4 collection contract. Even unshippable imagery (Clark County, SanGIS,
Nearmap) is fine here because it **never enters the kn5**. It is also the tool for fixing R2: trace
or nudge the centerline against it.

### 4.5 Cleaning the ortho

| Problem | Treatment | Notes |
|---|---|---|
| **Baked shadows** (poles, trees, stands, buildings) | (1) Prefer **high-sun vintages**: NAIP is summer leaf-on; Oakland 2025 was flown late April–mid May, when solar noon elevation at 42.6°N is ≈ 62° (computed). (2) Detect shadows by low luminance plus blue shift, then relight each region by the lit/shadow ratio per channel from adjacent same-surface pixels, or inpaint. (3) **Multi-vintage median** after colour matching, the ortho analogue of `capture/textures.py`'s temporal median. | Shadow-removal literature **[unverified this session]**. Speed Vegas is open desert with low shadow risk. |
| Parked cars, **cones** (Exotics Racing runs cone-defined courses daily), people | Same multi-vintage median, or a mask + inpaint. A drone capture with the track closed avoids it. | – |
| Lens vignetting / mosaic seamlines / tile colour jumps | Flat-field per source tile; Poisson-blend across seamlines | County mosaics are colour-balanced; NAIP DOQQs can jump between quads |
| Haze / "blue" lift | Dark-object subtraction per channel (darkest asphalt-in-shadow percentile), then white-balance on a neutral reference (concrete, fresh paint) | Standard remote-sensing practice **[method not cited this session]** |
| Vintage colour mismatch | Histogram/mean-std matching inside an asphalt mask to one anchor vintage | – |
| To albedo | sRGB → linear, divide out the estimated illumination, re-encode. Then **calibrate in game** against a Kunos road under the same sun preset (Objects Inspector + screenshot station). | AC's stock shaders aren't PBR; CSP has a linear colour space option ([wiki index](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki)) |

**AI upscaling.** Real-ESRGAN "is trained with pure synthetic data"
([README](https://github.com/xinntao/Real-ESRGAN)). It invents plausible high-frequency texture
from a prior, not from the scene. It is **acceptable for micro grain**, where no fact is encoded,
and as a ≤2× display smoother on macro *colour*. It is **not acceptable** for anything whose
*position* is a fact: paint, seal lines, patch boundaries, kerb edges. Upscaled 30 cm NAIP is still
30 cm of information (L12: show, don't assert). Topaz-style tools are the same class, and their
licence terms are **[unverified]**.

---

## 5. Legal stance (consistent with `SOURCES.txt`)

1. **Shippable:** NAIP (public domain, credit requested), USGS HRO (USGS disclaimer), OpenAerialMap
   CC-BY scenes (attribute), **Kevin's drone imagery** (owned), and county orthos **only where the
   licence text explicitly allows redistribution or the county grants it in writing**.
2. **Underlay only, never in the kn5:** Clark County GISMO, SanGIS/SANDAG (Nearmap/Pictometry),
   current-vintage DRAPP, Nearmap, Vexcel, Maxar, Planet.
3. **Never touched:** Google Maps/Earth/3D Tiles, Bing, Esri World Imagery tiles. Their ToS forbid
   extraction and derivative works (§2). Don't use them even "for reference" in an automated fetch.
   A human glancing at Google Maps to place control pins (aerial-tracing) is the existing,
   different use.
4. **Fix the existing hole:** the shipped `1ROAD` texture is mined (`asphalt_cracked_*`, LA Canyons,
   personal use). The macro+micro road replaces it with owned/PD content.
5. **Per-track provenance line** in the dossier (§9 "Data sources") and in `licenses.json`:

   ```
   road_macro: <source> <vintage> <GSD> <CRS> <licence + URL> <permission ref if any>
               <sha256 of source tiles> <bake commit>  |  micro: <asset> <licence>
   ```

   Credit NAIP as "USDA FPAC-BC Geospatial Enterprise Operations" in the track's `ui_track.json`
   description and the credits file (`scripts/ac/credits.py`).

---

## 6. Recommendation and Opus handoff

### 6.1 Minimal engine addition (in **airoso**, the engine seam: never move `scripts/` paths)

| Piece | Module | In | Out |
|---|---|---|---|
| Fetch | `scripts/aerial/ortho_fetch.py` | `track.config.json` `road_texture.source` (`naip` / `imageserver` / `file`), corridor = centerline buffered by W/2 + 30 m | `data/ortho/<source>_<vintage>.tif` (COG/GeoTIFF + CRS), `data/ortho/PROVENANCE.json` |
| Clean | `scripts/aerial/ortho_clean.py` | the GeoTIFF(s) + marking polylines | `data/ortho/clean.tif` + shadow/transient masks (debug PNGs) |
| Bake | `scripts/aerial/ortho_bake.py` | `data/centerline.geojson` + widths, `data/origin` (projection), `clean.tif`, `g`, `N`, ribbon pieces | `textures/road_macro_NNNN.png` (PoT, RGB + alpha detail-mask) → DDS; `data/road_uv_atlas.json` (strip table); UV override for `1ROAD_*` |
| UVs | `ribbon.road_ribbon(..., uv_fn=None)` hook | atlas strip table | same verts/tris; strip ends duplicated; UVs per §4.1 |
| Material | `pbr.py` + `export_kn5_addon.py` + `kn5_write.py` | `data/road_macro.json` | `1ROAD`: `ksPerPixelMultiMap_NMDetail`; `txDiffuse=road_macro_k`, `txNormal` (flat or macro-derived), `txMaps`, `txDetail`, `txNormalDetail` (owned micro); VARs `detailUVMultiplier = g·N/D`, `detailNormalBlend`, ksAmbient/ksDiffuse/ksSpecular/ksSpecularEXP copied from a measured Kunos road |
| Underlay | `scripts/blender/underlay.py` | same `clean.tif` (or raw unshippable ortho) | `GEN_ortho_ref` plane |

Config sketch:

```json
"road_texture": { "mode": "ortho_macro", "source": {"type": "naip", "year": 2023},
                  "gsd_m": 0.15, "atlas_px": 4096, "detail": "owned_asphalt_v1", "detail_tile_m": 4.0 }
```

Default `"mode": "tiled"` keeps today's behaviour (L2: reproducible from config; pilot-first).
Dependencies: `rasterio` (GDAL), `pyproj`, `numpy`. The capture stack already depends on numpy and
opencv. Keep them optional imports so the stdlib-only stages still run.

### 6.2 Fetching programmatically

- **NAIP on AWS:** `s3://naip-visualization/{st}/{year}/{res}/rgb/{quad}/m_….tif` (RGB COG, 5
  overview levels). Also `naip-analytic` (4-band MRF) and `naip-source` (4-band GeoTIFF). **Requester
  pays, us-west-2.** Set `AWS_REQUEST_PAYER=requester`; the bucket-root `manifest.txt` lists every
  key and gives each state's latest year and GSD ([registry](https://registry.opendata.aws/naip/);
  [kylebarron/naip-cogeo-mosaic](https://github.com/kylebarron/naip-cogeo-mosaic)). The registry
  says the catalog covers 2010–2023. Probing `naip-visualization` from this session returned 403,
  which is consistent with requester-pays.
- **NAIP on Planetary Computer (free egress):** STAC collection `naip`; sign asset URLs with the
  `planetary-computer` package (anonymous SAS tokens) ([PC SAS docs](https://planetarycomputer.microsoft.com/docs/concepts/sas)).
  Read only the corridor window from the COG with `rasterio` windowed reads.
- **County ImageServer:** `…/ImageServer/exportImage?bbox=xmin,ymin,xmax,ymax&bboxSR=<wkid>&size=W,H&imageSR=<wkid>&format=tiff&f=image`.
  If size is omitted the server returns 400×400, and `adjustAspectRatio` defaults true
  ([Esri exportImage help, mirrored](https://geodata.md.gov/imap/sdk/rest/02ss/02ss00000075000000.htm)).
  Tile the corridor under the server's `maxImageWidth/Height` (read it from the service JSON
  **[unverified per server]**). Clark County's endpoint is a **cached MapServer**
  (`maps.clarkcountynv.gov/arcgis_images/rest/services/CACHED/mostcurrentflight/MapServer`), not an
  ImageServer, and its licence bars redistribution, so it is underlay-only. Oakland County publishes
  "OC 2025 TC/CIR Ortho Image Service" and downloadable TIFF/MrSID by township
  ([OC](https://data.ferndalemi.gov/datasets/oakgov::oc-2025-tc-cir-ortho-image-service)). Find the
  exact REST URL from the item page: **not resolvable from this session**.
- **Drone:** ODM orthomosaic GeoTIFF → `source.type = "file"`.

### 6.3 The gates (built artifact, L5)

| Gate | Reads | Pass |
|---|---|---|
| **Texel density** | built `track.obj` UVs + DDS sizes | per-triangle texels/m ≥ 0.5 × (1/g) on ≥ 99 % of `1ROAD` area; lateral:longitudinal density ratio within [0.5, 2] outside κ·w/2 > 0.5 hairpins (reported, not failed) |
| **Isotropy for detail** | UV Jacobian per triangle | detail footprint aspect ≤ 1.5 (catches any non-square UV unit) |
| **Registration** (independent data: ortho vs OSM-placed mesh) | shipped DDS + UVs | asphalt/verge edge found in each baked cross-section within ±0.5 m of the mesh edge, p95 over stations; report the median lateral offset (it names the centerline bias) |
| **Seams** | pairs of duplicated strip-end vertices | identical world position; ΔE (Lab) of the texel rows each side < 3 on the mean |
| **Mip chain / format** | DDS headers | PoT, full mip count, BC1/BC3/BC7, gutter ≥ 8 px, no NPOT (L7) |
| **Provenance** | `PROVENANCE.json` vs `licenses.json` | the source is on the shippable list (§5) or carries a permission ref, else the build fails |

### 6.4 Drive test: what to look for (`fleet/templates/DRIVE-TEST-REPORT.md` §Look rows)

1. 0–30 m: grain crisp, no smear band, no visible micro tiling at 100–200 km/h.
2. 30–200 m (the d\* crossover): no "mush ring"; macro patches/stains appear smoothly, no swimming
   or moiré (test aniso 16× and CSP -2 LOD bias on/off).
3. Baked shadows vs the dynamic sun at three time presets (morning / noon / golden hour): no
   shadow pointing the wrong way, no double shadow under the real pole/stand.
4. Lane paint: geometry crisp; no ghost line from the photo beside it (registration).
5. Strip seams invisible at piece boundaries, including in curves.
6. RainFX wet and night (LightsFX): the macro doesn't turn blotchy under puddles or lamp cones.
7. Place read: "this is Speed Vegas's surface", e.g. the real patch or seal-line pattern at a named
   corner from the dossier §10.

### 6.5 First tracks

1. **Exotics Racing Las Vegas, at Speed Vegas** (14200 S Las Vegas Blvd, ~1.2–1.3 mi;
   [Exotics Racing](https://exoticsracing.com/racetrack/)). Flat, sunny, few trees. Macro: NAIP
   (shippable; check the NV vintage/GSD in the manifest) at **2048²**. Clark County 13 cm stays in
   the Blender underlay unless GISMO grants permission. Upgrade path: a **drone flight** (Part 107 +
   LAANC under Class B/D + track permission) at 2–3 cm into one 8192² atlas, the full-fidelity proof.
2. **Michigan: a circuit in Oakland County** (M1 Concourse, Pontiac, or Waterford Hills, Clarkston;
   align with the sibling dossier). Macro: **Oakland County 2025 3-inch** at **4096²** if the Open
   Data Terms permit redistribution; otherwise NAIP + drone. A leaf-off spring flight means bare-tree
   shadows: exercise the shadow cleaner here.

### 6.6 Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Baked shadows** read wrong under AC's dynamic sun | high-sun vintages, relight/inpaint, multi-vintage median; drive-test row 3 |
| R2 | **Registration**: OSM centerlines can sit metres off the photo, so the photo's road edge and paint land off the mesh | the registration gate measures it; re-trace or nudge the centerline on the same ortho (aerial-tracing / Blender underlay) before baking; circuits traced from that ortho are consistent by construction |
| R3 | **Resolution cliff** inside d\* (≈180 m at 15 cm) | the micro layer carries 0–d\*; drone GSD shrinks d\* to ~30 m |
| R4 | Fleet texture memory | non-issue with strip atlases (§4.1 table); cap files at 8192² |
| R5 | Licence drift (counties change terms; NAIP licensing was floated in 2017, [Geography Realm](https://www.geographyrealm.com/naip-aerial-imagery-might-moved-public-domain-licensing-model/)) | provenance line pins licence URL + date + hash; the provenance gate |
| R6 | Shader slot / param names differ from CM's reimplementation | read a Kunos road with Objects Inspector first (RESEARCH A2) |
| R7 | Multiply detail darkens the macro | normalise detail mean; calibrate against a Kunos road in game |
| R8 | Realism doctrine | this is Job 1 (prepare truth). The macro is regenerable `GEN_` content; authored road paint in Blender (`AUTH_`) always wins |

---

*Sources not reachable this session (allow them in network settings to deepen §3): overtake.gg,
assettocorsamods.net, ascobash.wordpress.com, tracktracer.trackgrind.com (a "satellite imagery to
AC tracks" tool worth reviewing as prior art), plus all county GIS and USGS hosts. Web search hit
the shared per-turn limit before NAIP state vintages, Maxar/Planet EULAs and shadow-removal methods
were confirmed.*
