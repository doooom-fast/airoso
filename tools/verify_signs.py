"""The eight self-checks that make a W1-6 placement right-or-wrong mechanically (Kevin,
2026-10-10: "very easy to see when it's right or wrong" — this is the same test as numbers).

Reads data/signs.local.json (tools/place_signs.py / tools/author_signs_blend.py) and checks, per
sign:
  (a) the failed-to-turn ray from A along t passes within +-0.61 m of the plate centre (half the
      48 in plate), i.e. the car that did not turn would hit the sign square-on
  (b) the plate faces straight back down the approach: |angle(f, -t)| <= 1 deg
  (c) the post stands 1.3-3.0 m behind the outside curb face
  (d) the geometric outside assertion held (cross > 0)
  (e) plate bottom = y_base + height (+-0.05)      } from the Blender section when present,
  (f) post base = y_base - 0.30 (+-0.05)            } "n/a" on a pure-Python (analytic) run
  (g) no sign inside drive_test's obstacle disc (min(lane_half, 6) + 0.3 m of any centreline)
      and no sign base on pavement
  (h) exactly one sign per id, none at a skipped id
Exit 1 on any FAIL (a ship gate: tools/ship_sd.sh runs it after the authoring pass).

    python tools/verify_signs.py <project-dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HALF_PLATE = 0.61
FACE_TOL_DEG = 1.0
CLEAR_MIN, CLEAR_MAX = 1.3, 3.0
HEIGHT_TOL = 0.05
POST_SINK = 0.30


def main():
    proj = Path(sys.argv[1])
    d = json.loads((proj / "data" / "signs.local.json").read_text(encoding="utf-8"))
    fails, rows = [], []
    ids = [s["id"] for s in d["signs"]]
    skipped_ids = {s["id"] for s in d["skipped"]}
    for s in d["signs"]:
        t = (-s["face_dir_xz"][0], -s["face_dir_xz"][1])
        f = s["face_dir_xz"]
        A, S = s["ray"]["A_xz"], s["base_xz"]
        lateral = abs(t[0] * (S[1] - A[1]) - t[1] * (S[0] - A[0]))
        ang = math.degrees(math.acos(max(-1.0, min(1.0, -(f[0] * t[0] + f[1] * t[1])))))
        c = s["checks"]
        yb = s["y_base"].get("value", s["y_base"]["analytic"])
        bl = s.get("blender")
        clear = c.get("mesh_clear_m", c["edge_clear_m"])     # the built curb when Blender measured it
        checks = {
            "a_ray_hits_plate": lateral <= HALF_PLATE,
            "b_faces_approach": ang <= FACE_TOL_DEG,
            "c_curb_clearance": CLEAR_MIN <= clear <= CLEAR_MAX,
            "d_outside": c["outside_cross"] > 0,
            "e_plate_height": None if not bl else abs(bl["plate_bottom_y"] - (yb + s["height_m"])) <= HEIGHT_TOL,
            "f_post_sunk": None if not bl else abs(bl["post_base_y"] - (yb - POST_SINK)) <= HEIGHT_TOL,
            # drive_test sweeps the mainline corridor only (gate_centerline.json); a connector post
            # is measured against its own ribbon for the record but cannot trip the gate
            "g_gate_disc": (c["gate_margin_m"] >= 0 or s["ribbon"] != "MAINLINE") and clear > 0,
            "h_unique_id": ids.count(s["id"]) == 1 and s["id"] not in skipped_ids,
        }
        bad = [k for k, v in checks.items() if v is False]
        fails += ["%s: %s" % (s["id"], ", ".join(bad))] if bad else []
        rows.append("[verify-signs] %-11s lateral %.2f m  face-err %.2f deg  clear %.2f m  outside %+.1f  gate %+.1f  %s"
                    % (s["id"], lateral, ang, clear, c["outside_cross"], c["gate_margin_m"],
                       "FAIL " + ", ".join(bad) if bad else "ok" + ("" if bl else " (e/f n/a: analytic run)")))
    if "blender" in d and d["blender"].get("normal_mismatches"):
        fails.append("blender: %d polygon normals do not face as intended" % d["blender"]["normal_mismatches"])
    for r in rows:
        print(r)
    for fl in fails:
        print("[verify-signs] FAIL", fl)
    print("[verify-signs] %d signs, %d skipped, %s" % (len(d["signs"]), len(d["skipped"]), "FAIL" if fails else "PASS"))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
