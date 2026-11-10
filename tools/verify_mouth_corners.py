"""GATE (opt-in): every side-street mouth's CORNERS on the BUILT road (ledger 0086, Sand Creek 0.2.7).

    python tools/verify_mouth_corners.py <project-dir> [--obj data/track.obj] [--json data/verify_mouth_corners.json]

Kevin, 2026-11-07, on Sand Creek's grid streets: "They don't connect to the main road very well at all", "Doesn't
connect, floats". verify_mouths judged every one of the 113 mouths flush: its notch runs inside the street's span, its
approach lines are straight, and the corners beside the street are in neither. tools/mouth_survey.py measured them
(0.2.6: corner lip median 0.175 m, max 0.327; Lake Murray v4 0.033) and this gate promotes three of its readings, on the
gate OBJ of the shipped kn5 (L5), with mouth_survey's own sampler:

  CORNER LIP   per corner (both sides of the street, 0-6 m along the host from the street's edge), the host's road edge
               over the top surface just past it (b 0.05 and 0.15 m): <= LIP_MAX_M = kn5_ground_check.ROAD_GAP_M 0.05 m
               [measured: kn5_ground_check's contact limit, the barycentric sampling ceiling]
  TEETH        along the streets' edge strips, 20 m from the host: the share of samples where the ground stands over the
               strip, over every judged mouth: <= TEETH_MAX 2.1 % [measured: Sand Creek's own lap, edge_report's ground
               share at 1 m on rr2]
  EDGE PAINT   the host's edge line (its own band) painted across the opening: <= 0.25 m, one 0.25 m sample [invented:
               policy — real paint breaks at a mouth; the one sample is the sampler's step]
  TURN DROP    the R 9 m inside wheel round each corner: reported, not gated

Opt-in by track.config.json route.verify_mouth_corners: true (the mouths route.mouth_returns names; every mouth when it
names none) or {"prefixes": [...]}; `route.verify_mouth_corners_allowed` [{"piece", "end", "why"}] lets a named mouth's
red rows stand, printed as ALLOWED. Not opted in: prints that and exits 0. Exit 1 on any red row.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mouth_returns as mr  # noqa: E402
import mouth_survey as ms  # noqa: E402

TEETH_MAX = 0.021
PAINT_MAX_M = 0.25   # [invented] one sample: the survey steps 0.25 m along the opening, so a lone hit at an opening's end is the step, not a line


def lip_max():
    from scripts.ac import kn5_ground_check as K
    return float(K.ROAD_GAP_M)


def selection(cfg):
    v = (cfg.get("route") or {}).get("verify_mouth_corners")
    if not v:
        return None
    if isinstance(v, dict):
        return list(v.get("prefixes") or [])
    return mr.config(cfg)[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--obj", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    data = proj / "data"
    out = Path(a.json) if a.json else data / "verify_mouth_corners.json"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    pre = selection(cfg)
    if pre is None:
        if out.exists():
            out.unlink()
        print("[mouth-corners] not opted in (route.verify_mouth_corners): nothing judged")
        return 0
    LIP = lip_max()
    allowed = {(x["piece"], x["end"]): x.get("why", "") for x in
               (cfg.get("route") or {}).get("verify_mouth_corners_allowed") or []}
    mouths = json.loads((data / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    conns = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))["connectors"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    sel = [mo for mo in mouths if not pre or mr.selected(mo, pre)]
    obj = Path(a.obj) if a.obj else data / "track.obj"
    F = ms.Field(ms.load(obj, [(m["cut_xyz"][0], m["cut_xyz"][2]) for m in sel]))
    rows, red, tot_t, tot_g = [], 0, 0, 0
    drops = []
    for mo in sel:
        hp, pp, end = ms._frames(mo, conns, local)
        r = ms.survey_mouth(mo, F, hp, pp, end)
        r.pop("_in_corner", None)
        tag = f"{mo['piece']}({end})->{mo['host']}"
        if "error" in r:
            rows.append({"mouth": tag, "error": r["error"], "pass": False})
            red += (mo["piece"], end) not in allowed
            print(f"[mouth-corners] {tag}: {r['error']} — {'ALLOWED' if (mo['piece'], end) in allowed else 'FAIL'}")
            continue
        lo, hi = r["corners"]["lo"], r["corners"]["hi"]
        lip = max(lo["lip_m"], hi["lip_m"])
        paint = r["markings"]["edge_line_across_opening_m"]
        tot_t += r["strip_teeth"]["samples"]
        tot_g += r["strip_teeth"]["grass_over_strip"]
        t9 = {k: v.get("r9", {}).get("max_drop_m") for k, v in r["turns"].items()}
        drops += [d for d in t9.values() if d is not None]
        bad = []
        if lip > LIP + 1e-9:
            bad.append(f"corner lip {lip:.3f} m > {LIP} (lo {lo['lip_m']} at {lo['lip_at']}, hi {hi['lip_m']} at {hi['lip_at']})")
        if paint > PAINT_MAX_M:
            bad.append(f"edge line across the opening {paint} m")
        ok = not bad
        allow = (mo["piece"], end) in allowed
        if not ok and not allow:
            red += 1
        rows.append({"mouth": tag, "pass": ok, "allowed": allow and not ok, "corner_lip_m": lip,
                     "corners": {"lo": {k: lo[k] for k in ("lip_m", "lip_at", "bare_m")},
                                 "hi": {k: hi[k] for k in ("lip_m", "lip_at", "bare_m")}},
                     "teeth": r["strip_teeth"], "edge_paint_m": paint, "turn_r9_drop_m": t9,
                     "conn_edges": r["conn_edges"]})
        print(f"[mouth-corners] {tag}: lip {lip:.3f} m (lo {lo['lip_m']}, hi {hi['lip_m']}), teeth "
              f"{r['strip_teeth']['grass_over_strip']}/{r['strip_teeth']['samples']}, edge paint {paint} m, R9 drop "
              f"{t9} — " + ("PASS" if ok else ("ALLOWED: " + allowed[(mo['piece'], end)] if allow else "FAIL: " + "; ".join(bad))))
    share = tot_g / tot_t if tot_t else 0.0
    teeth_ok = share <= TEETH_MAX + 1e-12
    lips = sorted(r["corner_lip_m"] for r in rows if "corner_lip_m" in r)
    drops.sort()
    res = {"obj": str(obj), "mouths": len(sel), "lip_max_m": LIP, "teeth_max": TEETH_MAX, "paint_max_m": PAINT_MAX_M,
           "red_mouths": red, "teeth": {"samples": tot_t, "grass_over_strip": tot_g, "share": round(share, 4),
                                         "pass": teeth_ok},
           "corner_lip": {"median_m": lips[len(lips) // 2] if lips else None, "max_m": lips[-1] if lips else None},
           "turn_r9_drop": {"median_m": drops[len(drops) // 2] if drops else None,
                            "p90_m": drops[int(0.9 * (len(drops) - 1))] if drops else None,
                            "max_m": drops[-1] if drops else None, "gated": False},
           "rows": rows}
    res["pass"] = red == 0 and teeth_ok
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"[mouth-corners] {len(sel)} mouth(s): corner lip median {res['corner_lip']['median_m']} max "
          f"{res['corner_lip']['max_m']} (<= {LIP}); teeth {tot_g}/{tot_t} = {share:.2%} (<= {TEETH_MAX:.1%}); R9 turn "
          f"drop median {res['turn_r9_drop']['median_m']} p90 {res['turn_r9_drop']['p90_m']} (reported); "
          f"{red} red mouth(s) — {'PASS' if res['pass'] else 'FAIL'}")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
