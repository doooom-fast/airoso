"""Aerial measurement of a real road from public-domain NAIP imagery: hairpin radii, widths, painted lines,
edges, bridge crossings, and the paint traces the centreline follows.

Lookout Lariat V3 (ledger 0048, dossier section 12 "aerial owed"). Ported 2026-10-11 from the aerial pass's
session-scratch scripts so its results reproduce from the repo; the algorithms live in ``tools/aerial/``
(one module per kind of measurement, every threshold tagged [invented] in its docstring). Pure Python +
Pillow. No geometry is changed here: this tool measures.

Inputs (all read-only): ``<project>/data/aerial/aerial_spec.json`` (the plan + the authored observations),
the lap centreline and Overpass snapshot it names, ``track.config.json`` (corner names), and the NAIP window
cache (``--cache``; default ``%LOCALAPPDATA%/airoso/naip`` or ``$AIROSO_NAIP_CACHE``). Missing windows are
fetched from USGS The National Map's NAIP ImageServer over HTTPS with certificate verification ON
(``scripts.tls.https_context``); ``--no-fetch`` refuses to touch the network.

What it runs, in order:
1. each corner window: the perpendicular trace (yellow, edge lines, pavement edges), the hairpin core
   (centre, concentric edge pairs, yellow circle), the ridge search where the apex is shadowed;
2. each width station: edge-line and pavement widths;
3. registration: the traced yellow vs the raw OSM ways on straight road -> the OSM-minus-imagery offset that
   moves every imagery point into the OSM frame;
4. the junction fillets, the leg widths, the edge appearance (dark lines / marks beside the edge);
5. the bridge crossings over the lap;
6. writes ``aerial_measurements.json``, ``overlays/<id>.png`` and ``paint_traces.json``.

Outputs go to ``--out-dir`` (default ``<project>/data/aerial``). ``--work-dir`` also dumps every
intermediate (pickles) for inspection.

    python tools/aerial_measure.py <project-dir> [--cache DIR] [--no-fetch] [--out-dir DIR]
                                   [--work-dir DIR] [--no-overlays]

Exit 0 on success, 2 on a usage / input error.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from aerial import corners, crossings, junction, overlay, registration, report, traces, widths  # noqa: E402
from aerial.context import Ctx  # noqa: E402


def run(project_dir, cache=None, fetch=True, out_dir=None, work_dir=None, overlays=True, log=print) -> dict:
    t0 = time.time()
    ctx = Ctx(project_dir, cache, fetch)
    spec = ctx.spec
    out_dir = Path(out_dir) if out_dir else ctx.data / "aerial"
    work = Path(work_dir) if work_dir else None
    if work:
        work.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        if work:
            (work / name).write_bytes(pickle.dumps(obj))

    traced = list(spec["hairpins"]) + list(spec.get("traced_unmeasured") or [])
    corner_traces, cores, core_errors, ridges = {}, {}, {}, {}
    for cid in traced:
        corner_traces[cid] = corners.trace_corner(ctx, cid)
        try:
            cores[cid] = corners.measure(ctx, cid, corner_traces[cid])
        except RuntimeError as e:
            core_errors[cid] = repr(e)
        log(f"[aerial] {cid}: traced{'' if cid in cores else ' (core: ' + core_errors[cid] + ')'}  {time.time() - t0:.0f}s")
    for cid in spec.get("force_ridge") or []:
        ridges[cid] = corners.ridge_for(ctx, cid, cores[cid])
        cores[cid] = corners.measure(ctx, cid, corner_traces[cid], ridge=ridges[cid])
        log(f"[aerial] {cid}: ridge circle R {ridges[cid]['R']:.2f} forced")
    width_res = {}
    for st in spec["width_stations"]:
        width_res[widths.win_id(st)] = widths.measure_station(ctx, st)
    log(f"[aerial] {len(width_res)} width stations  {time.time() - t0:.0f}s")

    groups = {}
    for cid in sorted(corner_traces):
        W, ref, recs, s_lo, span = corner_traces[cid]
        groups[cid] = registration.samples_from(ctx.ways_highway, ref.p, recs)
    for wid in sorted(width_res):
        groups[wid] = registration.samples_from(ctx.ways_highway, width_res[wid]["ref"], width_res[wid]["rows"])
    reg = registration.register(ctx.ways_highway, groups)
    ctx.V = tuple(reg["global"]["v_osm_minus_paint_EN_m"])
    log(f"[aerial] registration: OSM - imagery = {ctx.V} m (E, N), {reg['global']['n_points']} points")

    for cid in spec["hairpins"]:
        if cid not in ridges and cid in cores:
            ridges[cid] = corners.ridge_for(ctx, cid, cores[cid])
    jds = {cid: junction.measure(ctx, cid) for cid in spec["junctions"]}
    log(f"[aerial] junctions  {time.time() - t0:.0f}s")

    recs, images = {}, {}
    for cid in spec["hairpins"]:
        rec, lab, final = report.hairpin(ctx, cid, cores[cid], ridges.get(cid))
        recs[cid] = rec
        if overlays:
            images[cid] = overlay.draw_core(ctx, cid, cores[cid], final=final, label=lab)
    for cid in spec.get("traced_unmeasured") or []:
        recs[cid] = report.unmeasured(ctx, cid)
    for cid in spec["junctions"]:
        rec, lab = report.junction(ctx, cid, jds[cid])
        recs[cid] = rec
        if overlays:
            images[cid] = overlay.draw_junction(ctx, cid, jds[cid], label=lab)
    legs = {cid: corners.leg_widths(cores[cid]) for cid in spec["hairpins"]}
    estats = {cid: corners.edge_stats(cores[cid]) for cid in spec["hairpins"]}

    bways, _ = crossings.load_bridge_ways(ctx.project / spec["bridge_snapshot"], set(spec["bridge_way_ids"]))
    xosm = crossings.osm_crossings(ctx, bways)
    xres, corr = {}, {}
    for xs in spec["crossings"]:
        r, data = crossings.measure(ctx, bways, xs)
        xres[xs["id"]] = r
        if overlays:
            lab = ["%s  (lap st %.0f-%.0f under the deck, %.1f m)" % (r["name"], r["lap_stations_under_deck_m"][0],
                                                                     r["lap_stations_under_deck_m"][1], r["lap_length_under_deck_m"]),
                   "deck %.1f m wide (p10-p90 %.1f-%.1f), axis %.0f deg, crossing angle %.1f deg" % (
                       r["deck_width_m"]["median"], r["deck_width_m"]["p10"], r["deck_width_m"]["p90"],
                       r["deck_axis_heading_deg_from_N"], r["crossing_angle_deg"]),
                   "magenta: traced deck edges + fitted edge lines   cyan: OSM bridge ways   red: OSM lap line (datum-shifted)   yellow: dark lines on the deck"]
            images[xs["id"]] = overlay.draw_crossing(ctx, bways, xs, r, data, label=lab)
    for xs in spec["crossings"]:
        for st in xs["corridor_stations"]:
            corr["%s_%d" % (xs["id"], st)] = crossings.corridor(ctx, xs["id"], st)
    log(f"[aerial] crossings  {time.time() - t0:.0f}s")

    metas = [ctx.window_meta(w["id"]) for w in spec["windows"]]
    metas.sort(key=lambda m: m["id"] + ".json")
    out = report.assemble(ctx, metas, reg, recs, estats, {k: v["res"] for k, v in width_res.items()}, legs, xosm, xres, corr,
                          [f"{k}.png" for k in images] if overlays else [f"{k}.png" for k in _overlay_ids(spec)])
    corner_conf = {cid: recs[cid].get("confidence") for cid in recs}
    pt = traces.build(ctx, corner_traces, cores, width_res, jds, corner_conf)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "aerial_measurements.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8",
                                                    newline="\n")
    (out_dir / "paint_traces.json").write_text(traces.dumps(pt), encoding="utf-8", newline="\n")
    for k, im in images.items():
        overlay.save_palette(im, out_dir / "overlays" / f"{k}.png")
    dump("corner_traces.pkl", {k: (v[1].p, [{kk: vv for kk, vv in r.items() if kk != "pr"} for r in v[2]], v[3], v[4])
                               for k, v in corner_traces.items()})
    dump("cores.pkl", cores)
    dump("ridges.pkl", ridges)
    dump("widths.pkl", {k: {"res": v["res"], "rows": v["rows"], "ref": v["ref"]} for k, v in width_res.items()})
    dump("registration.pkl", reg)
    dump("junctions.pkl", {k: {kk: vv for kk, vv in v.items()} for k, v in jds.items()})
    log(f"[aerial] wrote {out_dir / 'aerial_measurements.json'}, {out_dir / 'paint_traces.json'} and {len(images)} overlays "
        f"in {time.time() - t0:.0f}s")
    return {"measurements": out, "traces": pt, "core_errors": core_errors}


def _overlay_ids(spec):
    return list(spec["hairpins"]) + list(spec["junctions"]) + [x["id"] for x in spec["crossings"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir")
    ap.add_argument("--cache", help="NAIP window cache directory (never inside the repo)")
    ap.add_argument("--no-fetch", action="store_true", help="use cached windows only; never touch the network")
    ap.add_argument("--out-dir", help="where to write (default <project>/data/aerial)")
    ap.add_argument("--work-dir", help="also dump every intermediate here")
    ap.add_argument("--no-overlays", action="store_true")
    a = ap.parse_args(argv)
    try:
        run(a.project_dir, a.cache, not a.no_fetch, a.out_dir, a.work_dir, not a.no_overlays)
    except (SystemExit, FileNotFoundError, KeyError) as e:
        print(f"[aerial] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
