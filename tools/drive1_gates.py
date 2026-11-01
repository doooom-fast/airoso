"""The Drive-1 verdict: V3-PLAN P5's "Drive-1 gate set" read off the gate reports of ONE build (Lookout Lariat; ledger
0048). Road + ground only, "named so Drive 1 isn't red by design". Written on branch 793441f (2026-10-12) against that
branch's chain; carried onto main 2026-11-01 (ledger 0048 "Started") on main's report names: kn5_ground_check per
layout as data/kn5_ground_check.<id>.json (the chain's kn5_ground step, on the kn5 set the layout loads), the underlay's
data/underlay.report.json, the parked layouts under track.config.json _layouts_v3_owed, the D4 verge from
road_profile.verge_m (SHIP_VARIANT writes the variant's into the workshop config).

Every gate below has already run and written its own report; this tool runs none of them. It reads each report,
judges the P5 thresholds the Lariat declares in ``track.config.json gates.drive1`` (each value tagged there), and
writes ``data/drive1_gates.json``: one row per gate, ``gating`` or ``recorded``, with its numbers. A gating row
that is missing (its report was not written: the gate did not run or died) is red, never a pass.

Gating (P5):
  drive_test, per STREET layout  soft-top / obstruction / floating furniture / undrivable / daylight 0 each [std],
                                 severe steps <= severe_steps_max [invented], replication p95 <= the ceiling
                                 [invented in 0048], kinks <= gates.drive_test.kinks_per_km_max [std: MEASURED §8].
                                 drive_test's OWN pass line also counts unguarded drops: that count is recorded here,
                                 not gated (Drive 1 builds no edges); the per-layout verdict is this table's, not its.
  audit_mesh (street)            P5's hard classes A B D E G H I = 0 [std]; F (curb not flush) <= f_curb_max
                                 [invented]; J / K are race-mouth gates (Drive 3), recorded.
  verify_kn5                     hard in the ship phase (the chain stops on red), so a build that reached the
                                 gates passed it; recorded as such.
  kn5_ground_check               its own verdict per street layout (road over ground p95 <= 0.10 m [std]) from
                                 data/kn5_ground_check.<id>.json; the lid: no step > lid_end_step_max_m at either end
                                 [invented in 0048], read from drive_test's severe-step list within +/- 5 m.
  one-way, hairpin/paint, roll rate   the draft's hard gates (data/oneway_check.json, data/aerial/paint_gate.json,
                                 data/crossfall_gate.json), re-read so the verdict carries them.
  road inventory, stacked legs   data/road_inventory.json, data/stacked_legs.json.
  tier seams                     not applicable until P3a's tiers land (the draft's ground is the engine's one grid,
                                 data/underlay.report.json); recorded as n/a, never as a pass.
Recorded, not gating: unguarded drop-offs, bumps/km, far ledges (drive_test), verify_edges, verify_signs, TreeFX,
sightline_check (Drive 2: not built), every race gate (race layouts parked until Drive 3).

--force-install (P5, 0047's rule): a red street run may still install only if it is no worse than the July
reference on every drive_test key it has (``gates.drive1.july_reference`` [measured on v0.46.0]) and obstruction,
floating furniture and soft-top are 0. ``force_install_ok`` carries that; tools/ship_track.sh refuses a forced
install when it is false.

    python tools/drive1_gates.py <project-dir>          exit 0 green, 1 red, 2 input error
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ZERO_KEYS = ("soft_top_in_lane", "obstruction_stations", "floating_furniture", "undrivable_corners", "daylight_gaps")
ALWAYS_ZERO = ("obstruction_stations", "floating_furniture", "soft_top_in_lane")   # P5: red or not, forced or not
AUDIT_HARD = ("A_supports_in_road", "B_terrain_poke", "D_wall_on_road", "E_wall_floating", "G_prop_floating",
              "H_ground_above_deck", "I_sidewalk_isolating")
LID_WINDOW_M = 5.0      # a severe step counts as "at the lid's end" within this distance of it (display window)


class InputError(Exception):
    pass


def _load(p: Path):
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InputError(f"{p}: unreadable ({e})")


def _row(name, kind, ok, numbers, note=""):
    return {"gate": name, "kind": kind, "pass": ok, "numbers": numbers, **({"note": note} if note else {})}


def _missing(name, what):
    return _row(name, "gating", False, {}, f"not run: {what} missing (a gate that did not run is red)")


def judge(project_dir) -> dict:
    proj = Path(project_dir)
    data = proj / "data"
    cfg = _load(proj / "track.config.json")
    if cfg is None:
        raise InputError(f"{proj / 'track.config.json'} missing")
    d1 = ((cfg.get("gates") or {}).get("drive1"))
    if not isinstance(d1, dict):
        raise InputError("track.config.json declares no gates.drive1 block (the Drive-1 thresholds)")
    dt_cfg = d1.get("drive_test") or {}
    try:
        severe_max = int(dt_cfg["severe_steps_max"])
        rep_max = float(dt_cfg["replication_p95_max_m"])
        f_max = int((d1.get("audit") or {})["f_curb_max"])
        lid_max = float((d1.get("kn5_ground_check") or {})["lid_end_step_max_m"])
        july = {k: float(v) for k, v in (d1.get("july_reference") or {}).items() if not k.startswith("_")}
    except (KeyError, TypeError, ValueError) as e:
        raise InputError(f"gates.drive1 is incomplete or malformed ({e!r})")
    if not july:
        raise InputError("gates.drive1.july_reference is empty")
    kink_max = ((cfg.get("gates") or {}).get("drive_test") or {}).get("kinks_per_km_max")
    street = [str(lo["id"]) for lo in cfg.get("layouts") or [] if not lo.get("race_furniture")]
    race = [str(lo["id"]) for lo in cfg.get("layouts") or [] if lo.get("race_furniture")]
    if not street:
        raise InputError("no street layout declared")
    rows, force_why = [], []

    # --- drive_test, per street layout ------------------------------------------------------------------------
    lid_spans = [(b.get("center_m", 0.0) - b.get("len_m", 0.0) / 2.0, b.get("center_m", 0.0) + b.get("len_m", 0.0) / 2.0,
                  b.get("id", "deck")) for b in ((cfg.get("capture") or {}).get("bridges") or [])]
    lid_rows = []
    for lid in street:
        r = _load(data / f"drive_test.{lid}.json")
        name = f"drive_test {lid}"
        if r is None:
            rows.append(_missing(name, f"data/drive_test.{lid}.json"))
            force_why.append(f"{lid}: drive_test not run")
            continue
        rep = r.get("replication_vs_measured") or {}
        nums = {k: r.get(k) for k in ZERO_KEYS}
        nums.update(severe_steps=r.get("severe_steps"), severe_per_km=r.get("severe_per_km"),
                    replication_p95_m=rep.get("p95"), replication_median_m=rep.get("median"),
                    replication_max_m=rep.get("max"), kinks_per_km=r.get("kinks_per_km"),
                    kinks_per_km_max=kink_max, lap_m=r.get("lap_m"))
        why = [k for k in ZERO_KEYS if (r.get(k) or 0) > 0]
        if (r.get("severe_steps") or 0) > severe_max:
            why.append(f"severe_steps {r.get('severe_steps')} > {severe_max}")
        if rep.get("p95") is None:
            why.append("replication vs 3DEP not measured (no z_raw in data/centerline.elevation.json)")
        elif float(rep["p95"]) > rep_max:
            why.append(f"replication p95 {rep['p95']} m > {rep_max} m")
        if kink_max is not None and (r.get("kinks_per_km") or 0) > float(kink_max):
            why.append(f"kinks {r.get('kinks_per_km')}/km > {kink_max}/km")
        rows.append(_row(name, "gating", not why, nums, "; ".join(why)))
        rows.append(_row(f"drive_test {lid} (recorded)", "recorded", None,
                         {"excursion_drops": r.get("excursion_drops"), "excursion_far_ledges": r.get("excursion_far_ledges"),
                          "steps_per_km": r.get("steps_per_km"), "apron_steps": r.get("apron_steps"),
                          "drive_test_own_fail": r.get("fail")},
                         "unguarded drop-offs are recorded, not gating, in Drive 1 (no edges are built); drive_test's "
                         "own pass line counts them, so its own 'fail' is recorded here too"))
        # July reference (--force-install)
        for k, ref in july.items():
            v = r.get(k)
            if v is None:
                force_why.append(f"{lid}: {k} not reported")
            elif float(v) > ref:
                force_why.append(f"{lid}: {k} {v} > July {ref:g}")
        for k in ALWAYS_ZERO:
            if (r.get(k) or 0) > 0:
                force_why.append(f"{lid}: {k} {r.get(k)} (always 0, red or not)")
        # the lid's ends: severe steps (>= 6 cm) within LID_WINDOW_M of either end, in this layout's stations
        lap = float(r.get("lap_m") or 0.0)
        sev = (r.get("worst") or {}).get("severe_all") or []
        for a, b, did in lid_spans:
            ends = (a, b) if r.get("direction") != "reverse" else (lap - b, lap - a)
            near = [abs(float(s[2])) for s in sev if any(abs(float(s[0]) - e) <= LID_WINDOW_M for e in ends)]
            lid_rows.append({"layout": lid, "deck": did, "ends_m": [round(e, 1) for e in ends],
                             "worst_step_m": round(max(near), 3) if near else None, "severe_steps_at_ends": len(near)})

    # --- audit_mesh (street) ----------------------------------------------------------------------------------
    a = _load(data / "audit.json")
    if a is None:
        rows.append(_missing("audit_mesh", "data/audit.json"))
    else:
        nums = {k: a.get(k) for k in AUDIT_HARD + ("F_curb_not_flush", "J_terrain_span", "K_kerb_in_carriageway",
                                                   "C_junction_crossings", "worst_poke_m", "worst_ground_cut_m")}
        why = [f"{k} {a.get(k)}" for k in AUDIT_HARD if (a.get(k) or 0) > 0]
        if (a.get("F_curb_not_flush") or 0) > f_max:
            why.append(f"F_curb_not_flush {a.get('F_curb_not_flush')} > {f_max}")
        rows.append(_row("audit_mesh", "gating", not why, nums, "; ".join(why) or
                         "J / K gate at the race-turn mouths (Drive 3): recorded"))

    # --- verify_kn5 (hard in the ship phase) ------------------------------------------------------------------
    slug = cfg.get("slug", "")
    kn5 = proj / "build" / f"{slug}.kn5"
    rows.append(_row("verify_kn5", "gating", kn5.is_file(), {"road_kn5": kn5.name, "exists": kn5.is_file()},
                     "hard in the ship phase: tools/ship_track.sh stops on red before any gate runs, so a build that "
                     "reached this verdict passed it" if kn5.is_file() else "no shipped road kn5"))

    # --- kn5_ground_check (per street layout, main's chain: the kn5 set the layout loads) + the lid's ends ---------
    for lid in street:
        kp = data / f"kn5_ground_check.{lid}.json"
        name = f"kn5_ground_check {lid}"
        k = _load(kp)
        if k is None:
            rows.append(_missing(name, f"data/kn5_ground_check.{lid}.json"))
            continue
        rog = k.get("road_over_ground") or {}
        seat = ((k.get("seating") or {}).get("walls") or {})
        nums = {"road_over_ground_p95_m": rog.get("p95_m"), "road_over_ground_max_m": rog.get("max_m"),
                "samples_over_gap": rog.get("over"), "samples": rog.get("samples"),
                "double_sheet_cells": k.get("double_sheet_cells"), "walls_hovering": seat.get("hovering"),
                "fidelity": k.get("fidelity"), "fail": k.get("fail")}
        ok = k.get("fail") is False
        rows.append(_row(name, "gating", ok, nums, "" if ok else "; ".join(k.get("reasons") or []) or "its own verdict: FAIL"))
    if lid_spans:
        bad = [x for x in lid_rows if x["worst_step_m"] is not None and x["worst_step_m"] > lid_max]
        rows.append(_row("lid ends (no step > %g m)" % lid_max, "gating", (not bad) and bool(lid_rows),
                         {"decks": lid_rows}, "" if lid_rows else "no street drive_test to read the lid's ends from"))

    # --- the draft's hard gates, re-read -----------------------------------------------------------------------
    o = _load(data / "oneway_check.json")
    rows.append(_missing("one-way", "data/oneway_check.json") if o is None else
                _row("one-way", "gating", not o.get("fails") and o.get("verdict") == "PASS",
                     {"verdict": o.get("verdict"), "fails": o.get("fails"),
                      "layouts": {x["id"]: {"verdict": x.get("verdict"), "against_total_m": x.get("against_total_m"),
                                            "undeclared_against_m": x.get("undeclared_against_m")}
                                  for x in o.get("layouts") or [] if x.get("checked")}}))
    pg = _load(data / "aerial" / "paint_gate.json")
    rows.append(_missing("hairpin / paint centreline", "data/aerial/paint_gate.json") if pg is None else
                _row("hairpin / paint centreline", "gating", bool(pg.get("pass")),
                     {k: (pg.get(k) or {}).get("pass") for k in ("a_paint", "b_curvature", "c_topology", "d_closure")}))
    cg = _load(data / "crossfall_gate.json")
    if cg is None:
        rows.append(_missing("roll rate", "data/crossfall_gate.json"))
    else:
        h = cg.get("halves") or {}
        rows.append(_row("roll rate", "gating", cg.get("fail") is False,
                         {"status_of_file": cg.get("status_of_file"), "stations": cg.get("stations"),
                          "worst_change_pct": max((h.get(s) or {}).get("worst_change_pct") or 0 for s in ("left", "right")),
                          "swings": sum((h.get(s) or {}).get("swings") or 0 for s in ("left", "right"))},
                         "; ".join(cg.get("problems") or [])))

    # --- road inventory, stacked legs ------------------------------------------------------------------------
    ri = _load(data / "road_inventory.json")
    if ri is None:
        rows.append(_missing("road inventory", "data/road_inventory.json"))
    else:
        keep = {k: ri.get(k) for k in ri if not isinstance(ri.get(k), (list, dict))}
        for k in ("forbidden_groups", "forbidden", "lap", "laps"):
            if k in ri:
                keep[k] = ri[k] if not isinstance(ri[k], list) else ri[k][:12]
        rows.append(_row("road inventory", "gating", ri.get("fail") is False, keep))
    sl = _load(data / "stacked_legs.json")
    if sl is None:
        rows.append(_missing("stacked legs", "data/stacked_legs.json"))
    else:
        keep = {k: sl.get(k) for k in sl if not isinstance(sl.get(k), (list, dict))}
        rows.append(_row("stacked legs", "gating", sl.get("fail") is False, keep))

    # --- tier seams (P3a) --------------------------------------------------------------------------------------
    u = _load(data / "underlay.report.json") or {}
    rows.append(_row("tier seams", "n/a", None, {"underlay_obj_md5": u.get("obj_md5"), "groups": len(u.get("groups") or [])},
                     "not applicable: the draft's ground is the engine's one grid (build_mesh, data/track.obj into "
                     "GEN_terrain) until P3a's tiers land (V3-PLAN P3a); this is NOT a pass"))

    # --- recorded only -----------------------------------------------------------------------------------------
    for g, why in (("verify_edges", "Drive 2: no edges built"), ("verify_signs", "Drive 2: no signs built"),
                   ("TreeFX check", "Drive 2: no trees"), ("sightline_check", "Drive 2: the far tiers")):
        rows.append(_row(g, "recorded", None, {}, why))
    rows.append(_row("race gates", "recorded", None, {"race_layouts_declared": race},
                     "Drive 3: the race layouts are parked (track.config.json _layouts_v3_owed)" if not race
                     else "race layouts are declared: their own gates run in tools/ship_track.sh"))

    gating = [x for x in rows if x["kind"] == "gating"]
    red = [x["gate"] for x in gating if not x["pass"]]
    return {
        "tool": "tools/drive1_gates.py", "plan": "V3-PLAN P5, the Drive-1 gate set (road + ground only)",
        "verge_m": ((cfg.get("road_profile") or {}).get("verge_m")),
        "street_layouts": street, "rows": rows, "red": red, "fail": bool(red),
        "force_install_ok": not force_why, "force_install_why_not": force_why,
        "july_reference": july,
    }


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python tools/drive1_gates.py <project-dir>")
        return 2
    try:
        rep = judge(argv[0])
    except InputError as e:
        print(f"[drive1] INPUT ERROR: {e}")
        return 2
    out = Path(argv[0]) / "data" / "drive1_gates.json"
    out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(f"[drive1] Drive-1 gate set (P5), {', '.join(rep['street_layouts'])}; D4 verge {rep['verge_m']} m "
          f"(track.config.json road_profile.verge_m)")
    for r in rep["rows"]:
        mark = {True: "PASS", False: "FAIL", None: "----"}[r["pass"]]
        nums = ", ".join(f"{k} {v}" for k, v in r["numbers"].items() if not isinstance(v, (list, dict)))
        print(f"[drive1]   {mark} {r['kind']:9} {r['gate']:34} {nums[:150]}")
        if r.get("note") and r["pass"] is False:
            print(f"[drive1]        {r['note'][:200]}")
    print(f"[drive1] --force-install would be {'allowed' if rep['force_install_ok'] else 'REFUSED'} (July reference"
          f"{'' if rep['force_install_ok'] else ': ' + '; '.join(rep['force_install_why_not'][:6])})")
    print(f"[drive1] {'FAIL: ' + ', '.join(rep['red']) if rep['fail'] else 'PASS'} -> {out}")
    return 1 if rep["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
