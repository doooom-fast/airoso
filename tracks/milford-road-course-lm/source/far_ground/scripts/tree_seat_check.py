"""The written trees on the built ground, before and after the far ground (ledger 0082 'Far ground (0.1.11)'): every tree of each
build's trees.txt (kn5 frame x, y, -z) against that build's gate OBJ ground (data/track.obj, 1GRASS*, tools/make_treefx.py
BuiltGround): planted = the lines, orphans = a tree with no ground under it, the start height's offset from the ground; and,
line by line between the two builds, what changed (only the y of a tree past the 3DEP grid may: model, angle, size, width and
plan position equal).

    python tree_seat_check.py <before project> <after project> [--json out.json]
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
from make_treefx import BuiltGround  # noqa: E402

TREE = re.compile(r"^tree:\s*([^;]+);\s*pos=([-0-9.eE+]+),\s*([-0-9.eE+]+),\s*([-0-9.eE+]+);(.*)$")


def read(proj):
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    out = []
    for ln in (proj / "build" / slug / "extension" / "trees" / "trees.txt").read_text(encoding="utf-8").splitlines():
        m = TREE.match(ln.strip())
        if m:
            out.append((m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)))
    return out


def seat(proj, trees):
    g = BuiltGround(proj / "data" / "track.obj")
    off, orphans = [], 0
    for _m, x, y, zk, _rest in trees:
        gz = g.at(x, -zk)
        if gz is None:
            orphans += 1
        else:
            off.append(y - gz)
    a = np.abs(np.array(off))
    return {"planted": len(trees), "orphans": orphans,
            "start_over_ground_m": {"p50_abs": round(float(np.median(a)), 3), "p95_abs": round(float(np.percentile(a, 95)), 3),
                                    "max_abs": round(float(a.max()), 3), "over_1m": int((a > 1.0).sum())}}


def main(argv):
    pa, pb = Path(argv[0]), Path(argv[1])
    A, B = read(pa), read(pb)
    rep = {"before": seat(pa, A), "after": seat(pb, B)}
    same = ydiff = other = 0
    dy = []
    for a, b in zip(A, B):
        if a == b:
            same += 1
        elif (a[0], a[1], a[3], a[4]) == (b[0], b[1], b[3], b[4]):
            ydiff += 1
            dy.append(b[2] - a[2])
        else:
            other += 1
    d = np.array(dy) if dy else np.zeros(1)
    rep["lines"] = {"before": len(A), "after": len(B), "identical": same, "only_y_moved": ydiff, "other_change": other,
                    "y_moved_m": {"min": round(float(d.min()), 2), "p50": round(float(np.median(d)), 2), "max": round(float(d.max()), 2)}}
    print(json.dumps(rep, indent=1))
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return 0 if rep["after"]["orphans"] == 0 and other == 0 and len(A) == len(B) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
