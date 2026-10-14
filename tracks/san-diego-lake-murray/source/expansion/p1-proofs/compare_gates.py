"""Ledger 0054 P1: the weld rehearsal's gate files vs v0.18.0's (the files tracks/san-diego-lake-murray/data/ holds,
synced back from the installed v0.18.0 ship), plus the steps at the two new mouths.

    python compare_gates.py <rehearsal project> <airoso track dir> [--json out.json]

Per layout: drive_test keys (soft top in lane, severe steps, steps / kinks per km, obstructions, barrier_missing,
excursion drops, daylight gaps, undrivable corners); audit totals; no_route BUILT; verify_mouths per mouth; and every
drive_test step / severe sample within the J1 / J5 boxes (box vertices +- 6) — "no step over 6 cm at J5 in any layout".
"""
import json
import math
import sys
from pathlib import Path

KEYS = ["soft_top_in_lane", "severe_steps", "severe_per_km", "steps_per_km", "kinks_per_km", "obstruction_stations",
        "barrier_missing", "excursion_drops", "daylight_gaps", "undrivable_corners", "floating_furniture"]
BOXES = {"J1": (1506, 1521), "J5": (2311, 2328)}


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def stations(proj):
    cl = load(proj / "data" / "gate_centerline.json") or load(proj / "data" / "centerline.local.json")
    P = cl["points_xyz_m"]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    return st


def box_samples(dt, st):
    """the worst-sample lists drive_test writes: (station, lateral, value) — those inside the boxes"""
    out = {}
    for j, (i, k) in BOXES.items():
        s0, s1 = st[i - 6], st[k + 6]
        hits = []
        for key, rows in (dt.get("worst") or {}).items():
            for r in rows or []:
                try:
                    s = float(r[0])
                except (TypeError, ValueError, IndexError):
                    continue
                if s0 <= s <= s1:
                    hits.append([key] + list(r))
        out[j] = hits
    return out


def main():
    proj, track = Path(sys.argv[1]), Path(sys.argv[2])
    rep = {"layouts": {}, "audit": {}, "no_route": {}, "verify_mouths": None}
    st = stations(proj)
    for lid in ("street", "race_cw", "race_acw"):
        new = load(proj / "data" / f"drive_test.{lid}.json") or {}
        old = load(track / "data" / f"drive_test.{lid}.json") or {}
        rows = {k: [old.get(k), new.get(k)] for k in KEYS}
        worse = [k for k in KEYS if isinstance(old.get(k), (int, float)) and isinstance(new.get(k), (int, float))
                 and new[k] > old[k] + 1e-9 and k not in ("floating_furniture",)]
        rep["layouts"][lid] = {"v0.18.0 -> rehearsal": rows, "worse": worse,
                               "box_samples": box_samples(new, st), "box_samples_v0.18.0": box_samples(old, st)}
        print(f"{lid:9} " + "  ".join(f"{k} {old.get(k)}->{new.get(k)}" for k in KEYS) + f"   WORSE: {worse or 'none'}")
    for name, fn in (("street", "audit.json"), ("race_cw", "audit.race_cw.json"), ("race_acw", "audit.race_acw.json")):
        a, b = load(track / "data" / fn), load(proj / "data" / fn)
        def tot(d):
            if not d:
                return None
            ks = [k for k in d if len(k) > 2 and k[1] == "_" and k[0].isupper() and isinstance(d[k], int)
                  and not isinstance(d[k], bool) and k not in ("F_skirt_off_terrain", "F_side_faces_skipped")]
            vals = {k: d[k] for k in ks}
            return [sum(vals.values()), vals]
        rep["audit"][name] = [tot(a), tot(b)]
        print(f"audit {name}: {(tot(a) or [None])[0]} -> {(tot(b) or [None])[0]}   {(tot(b) or [None, None])[1]}")
    for lid in ("race_cw", "race_acw"):
        n = load(proj / "data" / f"no_route.{lid}.json") or {}
        rep["no_route"][lid] = {k: n.get(k) for k in ("fail", "leak_m2", "leak_cells", "blocked", "forbidden_reached",
                                                      "spawns_unreached", "reached_m2")}
        rep["no_route"][lid]["probes"] = n.get("probes_total") or n.get("probes")
        print(f"no_route {lid}: {rep['no_route'][lid]}")
    vm = load(proj / "data" / "verify_mouths.json")
    if vm:
        rep["verify_mouths"] = [{k: m.get(k) for k in ("piece", "end", "host_vertex", "angle_deg", "fail", "fails",
                                                      "span_mouth_line_m")} |
                                {"mouth_line_max_m": m["mouth_line"]["max_dev_m"],
                                 "host_lane_above_max_m": m["host_lane"]["max_above_m"],
                                 "notch_max_m": m["notch"]["max_dev_m"],
                                 "approach_max_dg_per_m": m["approach"]["max_dg_per_m"]} for m in vm["mouths"]]
        for m in rep["verify_mouths"]:
            print("verify_mouths", m["piece"], "FAIL" if m["fail"] else "PASS", m["mouth_line_max_m"],
                  m["host_lane_above_max_m"], m["notch_max_m"], m["approach_max_dg_per_m"], m["fails"])
    for j in BOXES:
        for lid in ("street", "race_cw", "race_acw"):
            print(f"box {j} {lid}: {rep['layouts'][lid]['box_samples'][j]}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rep, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
