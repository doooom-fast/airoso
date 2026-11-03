# E 45th Ave line check, stations 6,200 to 6,750 m (2026-11-03)

Analysis only: no mesh, config or build change. Data: USGS 3DEP `CO_DRCOG_2_2020` (ground class 2, bridge deck class 17, intensity), `data/finished_centerline.json`, OSM `East 45th Avenue` from `data/osm.widths.cache.json`. Every 3 m; sections -20 to +20 m, 0.5 m bins, stacked 9 m along the line with the line's grade removed. Offsets are + = left of travel (south, we drive west). Per-station numbers: `e45th_line_check.json`; picture: `e45th_line_check.png`.

## Named OSM ways near the stretch
- East 45th Avenue (ids 944920189, 947575123, 944920187, 16986954, 864873958, 955933786, 864873961), primary/secondary: the road we follow.
- North Northfield Quebec Street (primary): we leave it at about 6,200 to 6,260 (the Quebec to 45th corner; E 45th is 24 m off at 6,201, 6.6 m at 6,230, 0.1 m at 6,260).
- Tuskegee Airmen Memorial Highway (I-70, motorway) and unnamed motorway_link / primary_link ramps: alongside, never the nearest named way after 6,260.

## Is our line on the pavement?
- Against OSM: yes. From 6,275 to 6,750 the line is within -1.8 to +3.1 m of the E 45th centreline (median |offset| 0.9 m; largest +3.1 m at 6,345; +2.3 m at 6,700 to 6,750; -1.8 m at 6,600). Nothing like an embankment-sized miss; between 6,260 and 6,275 the corner still reads up to 4.6 m.
- Against lidar: the line is on the flat paved platform at every station with returns (lidar height within 0.0 to 0.3 m of the line's, except the bridge), but it **sits near the platform's right (north) edge** from 6,290 to 6,620:
  - right edge of the flat platform is 1 to 2.5 m right of the line at 6,290 to 6,470 and 3 to 4.5 m at 6,470 to 6,620;
  - beyond that edge the ground drops 3 to 9 m (6,320 to 6,350: 1 to 3 m; 6,370 to 6,500: 6 to 9 m; 6,560 to 6,600: 4 to 6 m);
  - the platform runs 14 to 20 m to the left of the line (it includes shoulder, frontage and apron, wider than a carriageway).
- Detected carriageway centre (low-intensity run inside the platform, rough, plus or minus 2 to 3 m): +1 to +5 m at 6,290 to 6,500, against OSM 0 to +2.7 m. Both put the real centre left of our line there, so the line rides the right edge. At 6,560 to 6,700 detected centre is -2 to +1 m and OSM -1.7 to +1 m: the line is close to centred.
- Bridge, 6,513 to 6,558: **no deck returns in the cloud** (ground at the line reads 7 to 8 m below the line). The declared span is 6,494 to 6,604, so nothing here can be measured; the creek bed is what the old fits saw. Stations 6,486 to 6,510 and 6,561 to 6,570 are the approach slabs and abutments.
- 6,200 to 6,290 is the corner onto E 45th Ave beside a parallel ramp; the platform is wide and open, and the line is on the pavement but 3 to 7 m from the carriageway centre estimate. Not a concern for this check.

## Where does the -7 % to +9 % come from?
- Not from the line leaving the pavement. It is in two parts, both real surface geometry, but only one is a real road tilt.
- **-7 % at 6,594 to 6,610 is an artefact of the fit window.** The surface has a 0.3 to 0.4 m step about 0.5 m left of the line (right strip at 7.15, left strip 6.75 to 6.85 above 1600 m). The old fit, a plane across the line plus or minus 4.5 m, straddles the step and reads -7 %; each side is nearly flat (-0.6 % on the detected carriageway at 6,603).
- **+9 % at 6,633 to 6,645 is real**: carriageway fit +3.7 to +9.2 %, sd 5 cm (6,642: +9.2 % on the detected strip, +8.6 % old). Height rises 0.7 m over the 9 m from -4 to +5 m, no step. It rolls from about 0 % at 6,621 to +9 % at 6,642 (21 m): the road surface really twists there (junction or ramp mouth), it is not the line.
- **Earlier long -6 to -10 % run at 6,350 to 6,480** (the "steps and drops" the spans note mentions): fits are clean (sd 3 to 7 cm) but cover only the 5 m strip right of the platform's gutter line. At 6,366 and 6,420 the whole strip from the drop edge (-1.5 m) to a swale at +3 m falls 0.6 m, -8 to -9 %, then rises again to the left. Wider carriageway slope there is -0.6 to +1.7 %. So it is a real edge strip (shoulder/gutter berm), and our line rides it because it is 1 to 2 m from the drop edge.
- The 6,386 to 6,430 stations with +90 to +116 % fits are the drop edge itself inside the window (line 1.5 m from a 9 m wall); `is_road` rejected them, so they were interpolated.

## Recommendation
- Leave the line from 6,260 to 6,290 and 6,560 to 6,750: on the pavement, within 2.3 m of OSM.
- **Nudge left (south, + side) by about 1.5 m between 6,300 and 6,500**, tapering over 30 m at each end (6,270 to 6,300 and 6,500 to 6,530). Why 1.5 m: OSM says the centre is only +0.6 m median there (range -0.8 to +3.1), the lidar carriageway estimate +1 to +5 m; 1.5 m is a compromise that takes the line from 1 to 2 m off the drop edge to 2.5 to 3.5 m. It is a judgement, not a measurement. Check it on the aerial before moving anything.
- Do not widen `road_profile.crossfall.spans_m` over 6,300 to 6,500 until the line is moved and `tools/lidar_crossfall.py` is rerun there: the current -6 to -10 % is the edge strip. A cheaper fix for any rerun: centre the fit window on the detected carriageway (not the line), and drop windows that contain a step greater than 15 cm.
- 6,594 to 6,610: same tool change (reject windows straddling a step). The +5 to +9 % at 6,630 to 6,650 can stay if drive-tested; it is measured, but it is a short twist.
- Bridge 6,494 to 6,604: leave the declared deck as is; there is no lidar to say anything better.

## Uncertain
- Intensity is not a clean pavement signature in this cloud (scan-line banding, concrete vs asphalt), so the carriageway centre and width are plus or minus 2 to 3 m; edges bounded by drops are firm, the rest is not.
- OSM centreline precision is unknown here; OSM and lidar disagree by 1 to 4 m on the centre at 6,300 to 6,500, so the size of the nudge is the weakest number in this note.
- The heights above are lidar heights; line heights come from the DEM, differing 0.0 to 0.3 m on the pavement.
