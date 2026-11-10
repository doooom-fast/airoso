"""The GrassFX zones on the built ground, before and after the far ground (ledger 0082 'Far ground (0.1.11)'): every rectangle of
data/grassfx.aerial.json (tools/plan_grassfx_aerial.py; kn5 frame centre x, y, -z, size on the ground) sampled every STEP_M,
against each build's gate OBJ ground (1GRASS*, tools/make_treefx.py BuiltGround); and every 1GRASS* mesh of the gate OBJ
named in the written ext_config.ini's GRASS_MESHES (CSP grows its blades on those).

    python grass_zone_check.py <project> [<project> ...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
from make_treefx import BuiltGround  # noqa: E402

STEP_M = 6.0


def check(proj):
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    g = BuiltGround(proj / "data" / "track.obj")
    adj = json.loads((proj / "data" / "grassfx.aerial.json").read_text(encoding="utf-8"))["adjustments"]
    samples = off = rects_off = 0
    for a in adj:
        cx, _cy, czk = a["rect"]["center"]
        w, h = a["rect"]["size"]
        miss = 0
        nx, nz = max(1, int(w // STEP_M)), max(1, int(h // STEP_M))
        for i in range(nx + 1):
            for j in range(nz + 1):
                x = cx - w / 2 + w * i / nx
                n = -czk - h / 2 + h * j / nz
                samples += 1
                if g.at(x, n) is None:
                    miss += 1
        off += miss
        rects_off += miss > 0
    ini = (proj / "build" / slug / "extension" / "ext_config.ini").read_text(encoding="utf-8")
    meshes = [m.strip() for m in re.search(r"^GRASS_MESHES = (.*)$", ini, re.M).group(1).split(",")]
    groups = sorted({ln[2:].strip() for ln in (proj / "data" / "track.obj").open(encoding="utf-8", errors="replace")
                     if ln.startswith(("o ", "g ")) and ln[2:].strip().upper().startswith("1GRASS")})
    return {"rectangles": len(adj), "samples": samples, "samples_without_ground": off, "rectangles_touching_no_ground": rects_off,
            "grass_meshes_in_ext_config": meshes, "ground_meshes_not_listed": [x for x in groups if x not in meshes]}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, json.dumps(check(Path(p)), indent=1))
