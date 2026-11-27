"""Denver Grand Prix: Colfax's raised bus-lane median between Sherman and Grant, as a declared island centre line.

    python3 colfax_median.py            # rewrites colfax_median.json beside this file from committed inputs only

Kevin, 2026-11-25: "Colfax today yes" (Colfax as it is now, with the bus lanes); 2026-11-27, asked whether the 6 ft median
is built raised: "raised"; asked which side of it the race takes: "the correct side of the street" (the lap runs west,
so the north side).

WHERE IT STANDS (source/survey/colfax_today/COLFAX-TODAY.md; the city's "E Colfax Ave BRT Proposed Improvements, 100%
Design, August 2024", Denver Roll 1 of 4, DOTI / Parsons; crops in source/survey/colfax_today/stills):
  - LATERAL: section A-A (cut between Sherman and Grant, labelled dimensions): north kerb to the median's north face 24 ft
    (7.32 m), the median 6 ft (1.83 m). The centre line therefore stands 27 ft (8.230 m) south of the north kerb. The north
    kerb is MEASURED (source/widths/widths.json, the 2020 lidar kerb step, 30 measured stations E 12-97): a Theil-Sen line
    N = SLOPE * E + ICEPT (residuals within 0.30 m except two driveway rows). The drawing's 19.51 m kerb to kerb is 0.73 m
    narrower than the measured 20.24 m, so the median is anchored on the north kerb (the race side) and the south side
    takes the difference [invented: which kerb to anchor on].
  - ALONG: the drawing's 6 ft band (bus-lane lines 108 px apart at the crop's 12.28 px/m, the teal median line between)
    runs from the Sherman stop bar (crop px 290, station 107+62) to px 975 (station 109+45); east of it the band narrows
    to two abutting bus lanes with a double line (90 px) toward Grant. Stations map to the local frame through the two
    junction centres (OSM: Sherman E 3.2, Grant E 112.0; drawing 107+18, 110+71): E = 3.2 + (station - 10718 ft) x
    108.8 / 353. Read off the crops by pixel, about +-1 m along.
  - The drawing draws the west part of the median line dashed (px 290-750, E 16.8-57.5) and the rest solid; its legend is
    not in the crop. Both carry the 6 ft band, so both are built raised [invented: what the dash means].
  - Height: none is published; the fleet's island rule (tools/median_island.py CURB_H 0.18 m) [invented].
NOT HERE: Logan to Grant draws two abutting 12 ft bus lanes with a double line, no 6 ft band (the crop's 90 px); Sherman
to Lincoln waits for the Colfax curb redo (the 2020 lidar measures a median there, against the drawing's transition).
"""
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parents[1]
KERB_TO_CENTRE_M = (24 + 3) * 0.3048       # section A-A: 24 ft north kerb to the median face + half the 6 ft median
WIDTH_M = 6 * 0.3048                        # 1.829 m
FT_PER_STATION = 1.0


def station_to_e(st_ft):
    return 3.2 + (st_ft - 10718.0) * 108.8 / 353.0


def main():
    w = json.loads((TRACK / "source" / "widths" / "widths.json").read_text(encoding="utf-8"))["stations"]
    rows = sorted((x["right"]["EN"][0], x["right"]["EN"][1]) for x in w
                  if (x["s"] > 6400 or x["s"] < 30) and 3.2 <= x["line_EN"][0] <= 112.0 and x["right"]["grade"] == "measured")
    slopes = [(b[1] - a[1]) / (b[0] - a[0]) for i, a in enumerate(rows) for b in rows[i + 1:] if abs(b[0] - a[0]) > 5]
    slope = statistics.median(slopes)
    icept = statistics.median([n - slope * e for e, n in rows])
    resid = [n - (slope * e + icept) for e, n in rows]
    e0, e1 = station_to_e(10762.0), station_to_e(10945.0)
    import math
    L = math.hypot(1.0, slope)
    sx, sz = slope / L, -1.0 / L                 # unit normal toward the south (the kerb line's right side going east)
    pts = []
    n_pts = int(round(e1 - e0)) + 1
    for q in range(n_pts):
        e = e0 + (e1 - e0) * q / (n_pts - 1)
        nk = slope * e + icept
        pts.append([round(e + sx * KERB_TO_CENTRE_M, 3), round(nk + sz * KERB_TO_CENTRE_M, 3)])
    out = {
        "_doc": "Colfax's raised bus-lane median, Sherman to Grant: its centre line in the lap's local frame (E, N metres; "
                "origin -104.9849, 39.7401 as source/widths/widths.json) and its width. Written by colfax_median.py; read "
                "by tools/declared_medians.py (track.config.json route.declared_medians).",
        "islands": [{
            "name": "colfax_brt_sherman_grant",
            "width_m": round(WIDTH_M, 3),
            "centre_EN": pts,
            "sources": {"lateral": "DOTI 100% design Aug 2024, section A-A: north kerb to median face 24 ft, median 6 ft",
                        "north_kerb": f"source/widths/widths.json, {len(rows)} measured stations, Theil-Sen N = {slope:.5f} E "
                                      f"+ {icept:.3f}, residual p50 {statistics.median(abs(r) for r in resid):.2f} m",
                        "along": "DOTI 100% design Aug 2024, Denver Roll 1 of 4: the 6 ft band from station 107+62 to "
                                 "109+45 (crop px 290-975), E = 3.2 + (station - 10718) x 108.8 / 353",
                        "invented": ["anchored on the north kerb (the drawing is 0.73 m narrower kerb to kerb than measured)",
                                     "the dashed west part (E 16.8-57.5) built raised like the solid part",
                                     "curb height 0.18 m and the concrete top (the fleet's island rule)",
                                     "as built against the 2024 design (no photograph after the rebuild)"]},
        }],
    }
    (HERE / "colfax_median.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"colfax_median: {len(pts)} points, E {e0:.1f} -> {e1:.1f}, north kerb N = {slope:.5f} E + {icept:.3f}")


if __name__ == "__main__":
    main()
