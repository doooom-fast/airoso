"""Plan the HELD Mission Gorge Speedway (ledger 0054 Phase 2, step 2) in a scratch folder, never in the track.

The race tools' plan modes on Lake Murray v4's committed intermediates: scripts/geometry/race_lap.stitch (the lap, its
34 exits), tools/layout_dummies.py (grid, pits, start, sectors), tools/barrier_bands.py (the corridor, closures, kerbs
and the PLANNED no_route per layout, every self-gate on). The mainline group is declared again beside it and compared to
the committed data/barrier_bands.json: the existing Speedways must not move when the lap is declared.

    .venv/bin/python tracks/san-diego-lake-murray/source/expansion/phase2/plan_north.py [<out dir>]

Default out dir <repo>/build/phase2/north-plan (gitignored). Writes <out>/plan_north.json (the report) and the tools'
own files under <out>/data. Exit 1 = a refused plan (any self-gate, any of the 34 exits reached by the planned fill,
the mainline declaration changed, or a source file changed). No Blender, no export, no install, no AI line.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import barrier_bands as bands  # noqa: E402
import layout_dummies as dummies  # noqa: E402
import race_furniture as rf  # noqa: E402
from scripts.geometry import race_lap  # noqa: E402

INPUTS = ("centerline.local.json", "connectors.local.json", "median_bands.json", "mouths.json", "pads.plan.json",
          "bridge.spans.auto.json", "aprons.json", "barrier_bands.json", "dummies.json", "dummies_race_cw.json",
          "dummies_race_acw.json", "stubs.built.json", "pads.built.json", "mouth_welds.json")
LAP_OWN = ("whole", "boxes", "closure_runs", "pin_rate")


def compose(base: dict, decl: dict) -> dict:
    """the scratch config: the existing one + race.laps.<lap> + the two held layouts. The lap's corridor takes the
    Speedway's limits unchanged and only its own zones (LAP_OWN); no chicane, no mainline vertex number"""
    cfg = copy.deepcopy(base)
    lap_id = decl["lap"]
    spec = copy.deepcopy(decl["laps"][lap_id])
    cor = {k: v for k, v in copy.deepcopy(base["race"]["corridor"]).items() if not k.startswith("_") and k not in LAP_OWN}
    cor.pop("clear_width_source", None)
    cor.update({k: v for k, v in spec["corridor"].items() if not k.startswith("_")})
    spec["corridor"] = cor
    cfg["race"].setdefault("laps", {})[lap_id] = spec
    cfg["layouts"] += copy.deepcopy(decl["layouts"])
    return cfg


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in ("seconds", "_path", "_ctx")}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]) if argv else ROOT / "build" / "phase2" / "north-plan"
    decl = json.loads((HERE / "race.north.declaration.json").read_text(encoding="utf-8"))
    base = json.loads((PROJECT / "track.config.json").read_text(encoding="utf-8"))
    cfg = compose(base, decl)
    lap_id = decl["lap"]
    data = out / "data"
    data.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in INPUTS:
        src = PROJECT / "data" / name
        if src.exists():
            hashes[name] = hashlib.sha256(src.read_bytes()).hexdigest()
            shutil.copyfile(src, data / name)
    jf = decl["laps"][lap_id]["joins_file"]
    (out / jf).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT / jf, out / jf)
    (out / "track.config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    fails = [f"race.laps: {p}" for p in race_lap.validate(cfg)]
    rec = race_lap.stitch(out, cfg, lap_id)
    race_lap.write(out, rec)
    line = dummies.Line(rec["points_xyz_m"], rec["widths_m"])
    for lo in decl["layouts"]:
        dd, problems = dummies.layout_dummies(line, lo, cfg["race"], rec["island_w_by_vertex"])
        dd["_lap"] = lap_id
        (data / f"dummies_{lo['id']}.json").write_text(json.dumps(dd, indent=2) + "\n", encoding="utf-8")
        fails += [f"dummies {lo['id']}: {p}" for p in problems]

    # the mainline group, declared with and without the lap on the same inputs: must be the same declaration
    (out / "track.config.base.json").write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
    main_base = bands.build(out, lap=None, config_path=out / "track.config.base.json", write=False)
    main_out = bands.build(out, lap=None)
    main_same = (json.dumps(_strip({k: v for k, v in main_base.items() if k != "fails"}), sort_keys=True, default=str)
                 == json.dumps(_strip({k: v for k, v in main_out.items() if k != "fails"}), sort_keys=True, default=str))
    committed = json.loads((PROJECT / "data" / "barrier_bands.json").read_text(encoding="utf-8"))
    on_disk = json.loads((data / "barrier_bands.json").read_text(encoding="utf-8"))
    vs_committed = sorted(k for k in set(committed) | set(on_disk) if _strip(committed.get(k)) != _strip(on_disk.get(k)))
    if main_out["fails"]:
        fails += [f"mainline: {f}" for f in main_out["fails"]]
    if not main_same:
        fails.append("mainline: the declaration changed with the lap declared")

    try:
        res = bands.build(out, lap=lap_id)
    except SystemExit as e:          # a refusal inside the planners (e.g. a kerb fold no trim resolves): recorded, not raised
        res = {"fails": [f"refused: {e}"], "corridors": {}, "corners": None, "summary": None}
    fails += [f"{lap_id}: {f}" for f in res["fails"]]

    # every north kerb's own geometry (ledger 0054 Phase 2 step 2d): each span's columns advance by at least the author's
    # record resolution (race_furniture.COLUMN_ADVANCE_MIN_M), else verify_race I can read the built kerb inside-out —
    # a refusal names the pull-back the kerb's geometry allows (race_furniture.kerb_standing_run), for race.kerbs.trims
    kerb_margins = {}
    if res.get("corridors"):
        nb = json.loads((data / f"barrier_bands.{lap_id}.json").read_text(encoding="utf-8"))
        _p, _w, _iw, kplans, _c = rf.plan_all(out, nb, (nb.get("params") or {}).get("edge_mode", "road"), lap=lap_id)
        for kp in kplans:
            if kp["kind"] != "kerb":
                continue
            mg, under = rf.kerb_column_margin(kp)
            nm = rf.object_name(kp)
            kerb_margins[nm] = {"run": list(kp["run"]), "stations": len(kp["stations"]),
                                "column_advance_min_m": round(mg, 4), "spans_under": len(under)}
            if under:
                sr = rf.kerb_standing_run(kp, rf.stations(_p))
                fails.append(f"{lap_id}: kerb {nm} v{kp['run'][0]}-v{kp['run'][1]}: {len(under)} spans advance under "
                             f"{rf.COLUMN_ADVANCE_MIN_M:.4f} m (min {mg:.4f} m) — "
                             + (f"the run that stands is v{sr[0]}-v{sr[1]} ({sr[4]} m): declare that pull-back in "
                                f"race.kerbs.trims" if sr else "no run stands: drop it in race.kerbs.trims"))
    exits = []
    for mo in rec["mouths"]:
        row = {"exit": mo["connector"], "kind": mo["kind"], "lap_vertex": mo["host_vertex"],
               "probe_xz": mo.get("probe_xz")}
        for lid, c in res["corridors"].items():
            pl = c["no_route"].get("planned") or {}
            reached = [p for p in (pl.get("forbidden_reached") or []) if mo["connector"] in json.dumps(p)]
            pol = next((p for p in c.get("mouths") or [] if p.get("connector") == mo["connector"]), {})
            row[lid] = {"planned": "REACHED" if reached else "sealed", "policy": pol.get("policy") or pol.get("state")}
            if reached:
                fails.append(f"{lid}: exit {mo['connector']} reached by the planned fill")
        exits.append(row)
    planned = {lid: {k: v for k, v in (c["no_route"].get("planned") or {}).items() if k != "seconds"}
               for lid, c in res["corridors"].items()}
    same_src = all(hashlib.sha256((PROJECT / "data" / n).read_bytes()).hexdigest() == h for n, h in hashes.items())
    if not same_src:
        fails.append("a source file under the track changed")
    report = {
        "_doc": "plan_north.py: the held Mission Gorge Speedway planned on v4's intermediates (ledger 0054 Phase 2 step 2). "
                "PLANNED only: no built-artifact gate ran.",
        "status": "REFUSED" if fails else "PLANNED",
        "lap_m": rec["lap_m"], "unique_vertices": rec["point_count"] - 1,
        "joins": rec["joins"], "pieces": rec["pieces"],
        "corners": res.get("corners"),
        "exits": exits,
        "exit_counts": {k: sum(1 for e in exits if e["kind"] == k) for k in ("side_street", "pad_arm", "branch")},
        "planned_no_route": planned,
        "summary": res.get("summary"),
        "kerb_column_margins": kerb_margins,
        "mainline_declaration_unchanged": main_same,
        "mainline_keys_differing_from_committed": vs_committed,
        "source_unchanged": same_src,
        "fails": fails,
    }
    (out / "plan_north.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "lap_m", "unique_vertices", "exit_counts",
                                              "mainline_declaration_unchanged", "source_unchanged")}, indent=1))
    for f in fails[:40]:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
