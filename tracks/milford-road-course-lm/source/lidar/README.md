# Milford Road Course: the lidar beside the lap (ledger 0082, furniture pass 2, 2026-11-06)

Kevin, 2026-11-06, asked "Fetch the lidar for Milford (size unmeasured, est. tens of MB) ...?": "Yes, fetch both". The
rule given with it: size the read first (the EPT nodes within ~45 m of the lap), fetch only under 100 MB.

## The read

| | |
|---|---|
| source | USGS 3DEP `USGS_LPC_MI_31Co_Oakland_2016_LAS_2019` (EPT, EPSG:3857) |
| **flown** | **2017-05-03, 14:10-14:39 UTC** (the points' GPS time; `scripts/gpsdate.py`). NAIP 2022-08-16 is five years later |
| selection | every node whose box comes within the lane edge + 45 m of the lap, all depths 0-9 (`scripts/ept_plan.py`, HEAD requests for the sizes before any point was fetched) |
| fetched | **71 nodes, 39,604,920 B of LAZ** + 46,380 B of metadata (`ept.json`, 9 hierarchy files) |
| read | **5,727,790 points**; **1,427,749** within the lane edge + 45 m (`scripts/ept_fetch.py`) |
| classes kept | ground (2) 931,962; unclassified (1) 495,390; noise (7) 291; water (9) 29; 10: 77. No building class |
| density on the item lines | 1.2-2.9 ground returns / m2 (`sumitems.json`) |

The raw tiles stay on the Mac (`/Volumes/Drive/codex/lidar_dl/milford_oakland2016/`), never in the repo. Committed here:
`lidar_read.json` (the read, the node list with sizes), `milford_lidar_1m.npz` (a 1 m grid in the port's local frame:
ground height in cm over `z0_m`, ground return count, and the non-ground returns per height-over-ground band 0.35-1.3 /
1.3-3 / 3-8 / 8+ m), `overview.jpg` (the 0.5 m grid: ground intensity grey, the bands red / orange / yellow / green, the
inventory in blue), `sumitems.json`, `f1.json`, `poles.json` and four cross-sections.

## Method

- **Height over ground** (`scripts/hag.py`): a least-squares plane through the 12 nearest class-2 returns within 4 m of
  each return. Ground returns sit within 0.07 m of it (p95).
- **Per inventory line** (`scripts/sumitems.py`, `scripts/probe2.py`): the non-ground returns within 1 m of the line per
  height band, per metre, against control strips 3-6 m either side. `probe2.py` re-fits the ground from class-2 returns
  OUTSIDE a 1.5-4 m corridor, so an object the classifier called ground would still stand out. `scripts/xsec.py` draws
  the cross-section and plan of one line.
- **Anywhere in the buffer**: linear structures per height band (`scripts/lines.py`), isolated poles and posts
  (`scripts/poles.py`), sparse low fence lines (`scripts/fence.py`).
- **F1** (`scripts/f1.py`): the canopy-free chain of 2-4.6 m returns nearest the NAIP line, a line fitted through it
  every 4 m, and per 4 m the top (p90 of the returns over 1.5 m within 0.9 m of the line), its plan spread and its
  return structure.

Re-run (the lidar venv: laspy + lazrs, pyproj, numpy, scipy, Pillow; `-I` because it reads downloaded data):

```
P=<venv>/bin/python; DL=/Volumes/Drive/codex/lidar_dl/milford_oakland2016; CL=<workshop>/data/centerline.local.json
$P -I scripts/ept_plan.py $CL $DL 45         # sizes only; writes $DL/plan.json
$P -I scripts/ept_fetch.py $CL $DL pts.npz    # fetches what plan.json lists (or reads the cached tiles)
$P -I scripts/hag.py pts.npz hag.npz
$P -I scripts/sumitems.py pts.npz hag.npz ../furniture/inventory.json 1.0 sumitems.json
$P -I scripts/f1.py pts.npz hag.npz ../furniture/inventory.json f1.json
$P -I scripts/poles.py pts.npz hag.npz $CL poles.json
$P -I scripts/xsec.py pts.npz hag.npz ../furniture/inventory.json F1 xsec_F1.png 14
```

## What it measured (pass 2)

**The flight is five years older than the furniture.** On 2017-05-03 the lap was already paved (the intensity grid
shows the whole circuit, its aprons and painted lines), but **no rail and no tyre wall stood on any line NAIP 2022
shows**. Within 1 m of each line, returns 0.35-1.6 m over the ground per metre (`sumitems.json`; a W-beam's rail, blockout
and post, ~0.35 m deep in plan at the 1.4-2.9 ground returns / m2 there, would give ~0.5-1.0 / m):

| item | returns / m, 0.35-1.6 m | what that means |
|---|---|---|
| G1 W-beam | 0.09 | nothing (a scatter under 0.6 m: grass) |
| G2 W-beam | 0.04 | nothing |
| G3 W-beam | 0.03 | nothing |
| G4 W-beam | 0.00 | nothing |
| T1 / T2 / T3 tyres | 0.00 / 0.00 / 0.00 | nothing: no ~1 m band of returns |
| G5 | 0.27 | ~10 low returns in a 7 m stretch at one end: a shrub's shape, not a 34 m rail |
| G6, T4 | 0.00 | nothing |
| **F1** | **3.1 (0.3 m and up)** | **the positive control: a thin structure the same flight reads plainly** |

The buffer-wide scan agrees (`scripts/lines.py`): **no linear structure 0.4-1.4 m tall longer than 16 m anywhere within 45
m of the lap**. So the lidar cannot measure the rails' or the tyre walls' heights; they stay [invented], and their
identity rests on NAIP 2022 alone.

**F1 is a screen, not a hedge** (`f1.json`, `xsec_F1.png`). 197 m of it lies inside the read (s 262-393, 11.7-44.6 m off
the lane edge; the NE ~60 m runs on to 74 m, outside it). Its returns stand on one thin line (plan sd 0.39 m), 93 % of
the top returns are single pulses (an opaque top, with returns down its face), and the top is level: p90 per 4 m bin
3.92-4.33 m over the NE 112 m (median **4.06 m**), stepping down over 20 m (**3.54 m**) to 3.1-3.35 m over the SW 63 m
(median **3.18 m**). A hedge's top would wander and spread. On NAIP 2022 the line itself is light grey (R 204-212) with
its shadow 2-4 m WNW (`scripts/f1_naip.py`): a light, opaque screen ~4 m tall, a precast screen wall or a screened fence;
the lidar cannot say which. Built as kind `screen` on the fitted line at those three heights (`f1_entries.json`).

**What NAIP missed** (`poles.json`, `scripts/fence.py`):
- single returns 10.7-12.8 m up with nothing under them along the east side (s 3,177-3,496, 27-32 m off the edge): an
  overhead line's wires; its poles stand in the treeline and are not separable. Not built.
- two small objects 2.4 and 4.3 m tall 3 m INSIDE the traced edge at the s 960-986 apron in May 2017: on the pavement, so
  transient (equipment); not built.
- sparse 1.7-2.4 m returns along the outer W / NW boundary that might be a chain-link fence's top rail, but they mix with
  shrubs and young planting and no chain holds a clean line: not confirmed, not built.
- no isolated light pole or sign post within 45 m of the edge.

The pad sheds (S1, S2) and the tent (P1) are 150-260 m from the lap, outside the read: their heights stay [invented].
