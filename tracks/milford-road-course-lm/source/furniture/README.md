# Milford Road Course: track-side furniture inventory (ledger 0082, pass 1, 2026-11-06)

What really stands beside the lap, read before anything is built. Kevin, 2026-11-06: "prioritizing furniture passes on
milford"; his standing words: "I just want real".

## Sources, and what each can and cannot say

| source | what it gave | what it cannot give |
|---|---|---|
| NAIP 2022-08-16, tile `m_4208327_ne_17_060_20220816`, as `tracks/milford-road-course/source/naip_2022_mrc.jpg` on its true extent (ledger 0062): 0.50 m E-W x 0.68 m N-S per pixel | every position and length below (pixel vertices read by eye off `grid.py` crops, +-1 px); identity by form (posts, terminals, segmented bars) and by tone (`rgb.py`: a shadow reads blue, b/r 1.1-1.9; the black bars read neutral, b/r 0.89-0.95, so they are black objects, not shadows) | heights (no lidar point is cached on this Mac); anything under ~1 m across: lamp poles, signs, posts at a marshal station; the east side under its tree shadow |
| The sun on the image (`sun.py`, NOAA's equations): the tent's shadow vector (4.5-5 m W, ~2 m N) reads azimuth ~113 deg, so 10:40 EDT and elevation ~42 deg (+-7 deg of azimuth = 36-46 deg) | an order of magnitude for tall things (F1, the tent) | a rail's or a tyre wall's height: their shadows are one pixel or less |
| The camber-survey lidar (`tracks/milford-road-course/source/lidar/camber-survey/`) | only the deck's plane fits (`crossfall.lidar.json`): ground class, 5 m half-width | nothing beside the road: no point cloud is in the repo or the caches |
| OSM | not cached here; the route notes quote the raceway ways only | no furniture read (a download: see ledger 0082 "Downloads") |
| DOSSIER Part D section 5 | the kind of place: proving-ground austerity, guardrail (Milford is where highway guardrail was developed), chain-link and security fencing, no grandstands, no sponsor signage | no inventory per stretch ("unknown, will verify from onboard video and NAIP") |

## The inventory (`inventory.json`; the pixel reads are `items.json`; drawn on `inventory_overview.jpg`)

Offsets are from the traced pavement edge (the source line `tracks/milford-road-course/data/centerline.geojson` and its
widths), stations on that line; a negative offset is a vertex inside the traced width.

| id | what | where | length / size | offset from the edge | height and its source | identity | built in pass 1 |
|---|---|---|---|---|---|---|---|
| G1 | W-beam guardrail | NW corner, outside, grass between the apron and the boundary (s 238-337 L) | 106.5 m | 3.7-11.3 m | 0.70 m [invented: an NCHRP-350-era strong-post W-beam's 27-28 in, a standard, not measured here] | high: posts, a turned-down end | yes |
| G2 | W-beam guardrail | front straight, east (infield) side, the NW opening to the SW corner (across S/F) | 556.1 m | -0.6-1.7 m | 0.70 m [invented, as G1] | high: post ticks at a steady spacing | yes |
| G3 | W-beam guardrail | front straight, west side, s 4,516-4,711 | 195.7 m | 0.4-4.2 m | 0.70 m [invented] | medium-high | yes |
| G4 | W-beam guardrail | infield, between the NW hairpin's exit and the esses (s 459-802 L) | 362.2 m | 10.6-38.8 m | 0.70 m [invented] | high: posts, a hooked terminal | yes |
| G5 | rail? | east straight, inside edge, short | 33.7 m | 2.7-4.8 m | - | low | no |
| G6 | rail or wall top? | the bright line behind T3 | 35.4 m | - | - | low | no |
| T1 | tyre wall | NW hairpin exit, 13 m west of G4's north end (s 456-485 L) | 43.9 m x 1.5 m | 14.4-23.2 m | 1.0 m [invented: five tyres]; width off NAIP (4 px less a pixel of blur) | medium: black, segmented, by tone not a shadow | yes |
| T2 | tyre wall | esses, in front of G4, outside the east leg's bend (s 1,303-1,344 L) | 52.9 m x 1.2 m | 15.8-23.5 m | 1.0 m [invented] | medium | yes |
| T3 | tyre wall | the back of the concrete run-off apron outside the s 1,000 left-hander (ledger 0069's corner) | 32.4 m x 1.5 m | 0.7-24.0 m | 1.0 m [invented] | medium | yes |
| T4 | tyre wall? | the unused inner hairpin short-cut's outer edge | 43.7 m | 19.6-25.7 m | - | low (the tone read is ambiguous) | no |
| T5, T6 | black bars | fields east and south-east of the ride pad, beside mown two-tracks | 83 m, 103 m | 46-225 m | - | low; far from the lap | no |
| F1 | something tall along the NW boundary | between the NW apron and the outside road / employee lot | 256.7 m | 12-74 m | its shadow (3-4.5 m wide, shadow blue) at the sun above: 4-5 m (3.7-6.0 m) [shadow, low confidence] | low: a screen fence, a wall or a clipped hedge; 0.6 m cannot say which | no (owed) |
| S1 | container / site trailer | west edge of the ride pad | 4.5 x 12.8 m | 257 m | 2.6 m [invented] | medium | yes (visual) |
| S2 | container / site trailer | west edge of the ride pad | 3.5 x 12.1 m | 207 m | 2.6 m [invented] | medium | yes (visual) |
| P1 | the pad tent | the ride pad | 20.0 x 53.3 m | 152 m | config eave 3.5 m [invented]; its shadow reads 3.6-5.6 m | high | already in 0.1.0 |
| U1 | underpass portal | the service road's headwall under the lap at the SW climb (route notes: the dip at s 3,605) | 12.6 m | 19.6-22.5 m | - | high | no (bridge not modelled) |

**Looked for and not found at 0.6 m:** concrete walls along the lap (none but T3's possible backing, G6); fences other
than F1 (the pad's east edge carries a thin line, likely its fence, 150+ m from the lap); pit / paddock / garage buildings
(none: the paddock is the ride pad and its tent; the 16 m front straight's wide west half and the dark lot west of it are
the only pit-like pavement, unmarked); timing or control towers (none); light poles, signs, marshal posts, gates (none
resolvable: each is under a metre across). Parked trailers on the pad and the containers on the gravel lot by the pond
are vehicles and stores, not built. A white transverse line crosses the front straight at about px (435, 1830), some
260 m south of the config's S/F: a line on the road, noted, not built.

## What 0.1.0 has, and lacks

- **Has:** the road and its edge strip, the ground (turf tile), the tree cards (4,431 stood), the pad tent with its
  collider, the ride pad, the two MPG plant blocks as far backdrop. No kerbs (ledger 0078: none on NAIP).
- **Lacks:** every rail (G1-G4: 1,220 m of W-beam), every tyre wall (T1-T3: 129 m), F1, the pad's two sheds, the
  underpass portal. 0.6.0's 145 m of W-beam stood on the draft's guard lips, not on measured lines; it was not ported
  (config `_guardrail_dropped`).

## Re-run

```
python grid.py <naip> <out.jpg> x0 y0 x1 y1 <scale>          # a crop with a labelled source-pixel grid, to read vertices
python inventory.py <airoso> inventory.json items.json         # the pixel reads -> lon/lat, lengths, offsets, stations
python draw_inventory.py <naip> inventory.json inventory_overview.jpg
python rgb.py <naip> name:x,y ...                              # the tone check (shadow blue vs black object)
python sun.py                                                  # the sun over 2022-08-16 at the centroid
python edge_lines.py <airoso> out.json out.jpg                 # an automatic ridge scan beside the lap: a cross-check only
```
The Blender python or the repo `.venv` (numpy, Pillow).
