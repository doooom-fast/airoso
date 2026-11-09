"""Kevin's force for a stage port, by place and row (ledger 0078 round 12; the Lariat's round-7 pattern for a stage).

A stage port's drive_test is its road gate (tools/ship_track.sh gate drive_test_street). A red build installs only
with --force-install, and for a port that declares ``gates.drive1.force_exemptions.stage`` only where every red reason
is one Kevin forced, at the place he forced it:

    "gates": {"drive1": {"force_exemptions": {"stage": {
        "approved": "<Kevin's words, date>", "versions": ["0.1.0"],
        "undrivable_corners": [{"id": ..., "s_m": [a, b], "measured": "..."}],
        "excursion_drops":    [{"id": ..., "s_m": [a, b], "measured": "..."}]}}}}

(The key sits under gates.drive1.force_exemptions because scripts/geometry/drive_test.py writes every undrivable
corner with its station, worst.undrivable_all, only for a track declaring that key; this tool, not drive1_gates.py,
reads it for a stage.) Allowed only if the build's version is listed, every drive_test fail reason is undrivable
corners or excursion drops, every undrivable corner (station) lies inside a declared undrivable window, and every
gated excursion drop inside a declared drop window. Any other red row (a soft top, a severe-step rate, a corner or a
drop anywhere else) refuses the force. No threshold moves. Writes data/stage_force.json {force_install_ok,
why_not, covered}; exit 0 (drive_test stays the red gate).

    python tools/stage_force.py <project-dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def verdict(cfg, reports):
    fx = (((cfg.get("gates") or {}).get("drive1") or {}).get("force_exemptions") or {}).get("stage")
    if not fx:
        return {"force_install_ok": False, "why_not": ["no gates.drive1.force_exemptions.stage declared"], "covered": []}
    why, covered = [], []
    if str(cfg.get("version")) not in [str(v) for v in fx.get("versions") or []]:
        why.append(f"build version {cfg.get('version')} is not in the declared versions {fx.get('versions')}")
    # a window may name its layout ("layout", optional; ledger 0085, Pikes Peak: three laps, each with its own
    # stations): it then covers that layout's report only. Absent = every report, as before (a stage has one)
    def _wins(key, lid_):
        return [(w["id"], float(w["s_m"][0]), float(w["s_m"][1])) for w in fx.get(key) or []
                if w.get("layout") in (None, lid_)]
    for lid, r in reports.items():
        und_w, exc_w = _wins("undrivable_corners", lid), _wins("excursion_drops", lid)
        lap_km = float(r.get("lap_m") or 0) / 1000.0
        reasons = [k for k in ("soft_top_in_lane", "daylight_gaps", "obstruction_stations", "floating_furniture",
                               "barrier_missing") if (r.get(k) or 0) > 0]
        if float(r.get("severe_per_km") or 0) > 12.0:
            reasons.append("severe_per_km")
        for k in reasons:
            why.append(f"{lid}: {k} {r.get(k)} (not forced)")
        und = (r.get("worst") or {}).get("undrivable_all")
        if (r.get("undrivable_corners") or 0) > 0:
            if und is None or len(und) != int(r["undrivable_corners"]):
                why.append(f"{lid}: undrivable corners {r['undrivable_corners']} without their stations")
            else:
                for s, deg, w in und:
                    hit = next((i for i, a, b in und_w if a <= float(s) <= b), None)
                    if hit is None:
                        why.append(f"{lid}: undrivable corner at s {s:.0f} ({deg:.0f} deg, {w} m) outside every forced window")
                    else:
                        covered.append(f"{lid}: undrivable corner s {s:.0f} ({deg:.0f} deg at {w} m) — {hit}")
        for s, off, drop, gated in (r.get("worst_gated_excursions") or []):
            hit = next((i for i, a, b in exc_w if a <= float(s) <= b), None)
            if hit is None:
                why.append(f"{lid}: gated drop at s {s:.0f} ({drop} m) outside every forced window")
            else:
                covered.append(f"{lid}: gated drop s {s:.0f} at {off} m, {drop} m — {hit}")
        if (r.get("excursion_drops") or 0) > lap_km and not exc_w:
            why.append(f"{lid}: excursion drops {r.get('excursion_drops')} over the stage's {lap_km:.0f}")
    return {"force_install_ok": not why, "why_not": why, "covered": covered, "declared": fx}


def main(argv=None):
    proj = Path((argv or sys.argv[1:])[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    reports = {}
    for lay in cfg.get("layouts") or []:
        f = proj / "data" / f"drive_test.{lay['id']}.json"
        if f.exists():
            reports[lay["id"]] = json.loads(f.read_text(encoding="utf-8"))
    v = verdict(cfg, reports)
    (proj / "data" / "stage_force.json").write_text(json.dumps(v, indent=1), encoding="utf-8")
    for c in v["covered"]:
        print(f"[stage-force] covered: {c}")
    for w in v["why_not"]:
        print(f"[stage-force] NOT covered: {w}")
    print(f"[stage-force] --force-install would be {'allowed' if v['force_install_ok'] else 'REFUSED'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
