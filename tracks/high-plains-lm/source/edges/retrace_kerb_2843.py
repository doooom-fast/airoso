"""The T13 kerb at L s 2,843 re-traced onto its paint (ledger 0097 round 3), by round 2's own rule (retrace_stripe_2673.py).

    python -I retrace_kerb_2843.py <repo>      (numpy + Pillow; rewrites kerbs.lm.json beside itself)

The kerb (ledger 0081's L s 2,843-2,856, blue / white, 1KERB_circuit_8) is the inside of the Full course's T13, where Ladder To
Heaven comes down into the Prairie Corkscrew: on NAIP 2023 its paint wraps round that corner, but the run was laid at one
in / out along the West lap's edge, so its west end (and the engine's 4 m end ramp beyond it) stood across the north loop's
welded mouth (verify_mouths NOTCH, round 3's first Full build: the ramp 1.3-3.3 cm over the road along the mouth's last
1.25 m). Here each of its edge points moves across by the paint it stands on, exactly as retrace_stripe_2673.py moves
R s 2,673's (the same crop, the same paint rule, the same MOVE_MIN_M); in_m / out_m, the ends and every other run stay. The
port's kerbs.lm.json keeps R s 2,673's round-2 re-trace.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import retrace_stripe_2673 as rs  # noqa: E402

RUN = ("left", 2843.0)


def retrace(repo: Path):
    rs.RUN = RUN
    one, rows = rs.retrace(repo)                      # the source's file with this run re-traced
    run = next(k for k in one["kerbs"] if k["side"] == RUN[0] and k["s0"] == RUN[1])
    run["_retrace"] = run["_retrace"].replace("ledger 0097 round 2", "ledger 0097 round 3 (retrace_kerb_2843.py, round 2's rule)")
    run["_retrace"] = run["_retrace"].replace("(retrace_stripe_2673.py, NAIP 2023 0.3 m)", "(NAIP 2023 0.3 m)")
    cur = json.loads((HERE / "kerbs.lm.json").read_text(encoding="utf-8"))
    cur["kerbs"] = [run if (k["side"], k["s0"]) == RUN else k for k in cur["kerbs"]]
    cur["_doc_lm"] = ("High Plains' port copy of tracks/high-plains/source/edges/kerbs.json (route.kerbs_file, synced in by "
                      "ship.json): the same 20 runs, R s 2,673 re-traced onto its paint (retrace_stripe_2673.py; ledger 0097 "
                      "round 2) and L s 2,843, the T13 kerb, by the same rule (retrace_kerb_2843.py; round 3)")
    return cur, rows


if __name__ == "__main__":
    repo = Path(sys.argv[1]).resolve()
    out, rows = retrace(repo)
    (HERE / "kerbs.lm.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in rows:
        print(r)
