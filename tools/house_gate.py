"""Are the houses still there? — Lake Murray v4's houses, counted off the BUILT road kn5 (ledger 0065, Kevin 2026-11-03:
"Lake Murray v4 had many more houses I[n] it this time, don't lose those").

READ-ONLY on the shipped road kn5 (L5: the artifact, never the data that placed it). Every block tools/author_bespoke_blend.py
stands is one roof (ROOFTOP_<class>), one ring of walls (BUILDING_<skin> near the lap, FARBLOCK_<skin> past the ground) and,
on fine ground near the lap, one collider skirt (1WALL_TILTUP). The exporter splits a mesh's vertices at every UV seam and
normal, so a block is counted as a CONNECTED SHELL: triangles joined by shared positions (welded at WELD_M), per mesh.

    roofs     ROOFTOP_* shells
    blocks    BUILDING_<skin> + FARBLOCK_<skin> shells (near walls + far blocks)
    colliders 1WALL_TILTUP shells

Floors are the track's (track.config.json scenery.bespoke.house_gate: the counts the build Kevin picked carried). Exit 1 when
any count is below its floor; exit 0 with "no floor declared" on a track without one; exit 2 on an input error.

    python tools/house_gate.py <project> [--kn5 <road kn5>] [--json <out>]

The kn5 defaults to <project>/build/<slug>.kn5 (the road kn5, the one every layout loads).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WELD_M = 0.001      # positions closer than this are one vertex (the exporter's seam splits are bit-identical copies)
ROOF_RE = re.compile(r"^ROOFTOP_[A-Z]+")
BLOCK_RE = re.compile(r"^(BUILDING|FARBLOCK)_(STUCCO|METAL|TILTUP|SIDING|DRYSTONE|FABRICB)")
COLLIDER_RE = re.compile(r"^1WALL_TILTUP")
KEYS = ("roofs", "blocks", "colliders")


def shells(P, T, weld=WELD_M):
    """connected shells of one mesh: triangles (index triples into P) joined through positions welded at ``weld`` m"""
    q = 1.0 / weld
    vid, canon = {}, []
    for x, y, z in P:
        k = (round(x * q), round(y * q), round(z * q))
        canon.append(vid.setdefault(k, len(vid)))
    parent = list(range(len(vid)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    used = set()
    for t in range(0, len(T) - 2, 3):
        a, b, c = canon[T[t]], canon[T[t + 1]], canon[T[t + 2]]
        used.update((a, b, c))
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    return len({find(v) for v in used})


def count(meshes):
    """{roofs, blocks, colliders} shells + the per-name-class detail, from verify_kn5._parse_full's meshes"""
    out = {k: 0 for k in KEYS}
    detail: dict[str, int] = {}
    for m in meshes:
        name = m["name"]
        if ROOF_RE.match(name):
            key, cls = "roofs", ROOF_RE.match(name).group(0)
        elif BLOCK_RE.match(name):
            key, cls = "blocks", BLOCK_RE.match(name).group(0)
        elif COLLIDER_RE.match(name):
            key, cls = "colliders", "1WALL_TILTUP"
        else:
            continue
        n = shells(m["P"], m["T"])
        out[key] += n
        detail[cls] = detail.get(cls, 0) + n
    return out, dict(sorted(detail.items()))


def verdict(counts, floor):
    """[(key, count, floor)] of every count below its floor; [] = PASS"""
    return [(k, int(counts.get(k, 0)), int(floor[k])) for k in KEYS if k in floor and int(counts.get(k, 0)) < int(floor[k])]


def floors(cfg):
    g = ((cfg.get("scenery") or {}).get("bespoke") or {}).get("house_gate")
    if not g:
        return None
    bad = [k for k in KEYS if not isinstance(g.get(k), int) or g[k] < 0]
    if bad:
        raise SystemExit(f"[house_gate] scenery.bespoke.house_gate: {bad} must be counts (non-negative integers)")
    return {k: int(g[k]) for k in KEYS}


def main(argv):
    args = list(argv)
    kn5 = out = None
    if "--kn5" in args:
        i = args.index("--kn5"); kn5 = Path(args[i + 1]); del args[i:i + 2]
    if "--json" in args:
        i = args.index("--json"); out = Path(args[i + 1]); del args[i:i + 2]
    if len(args) != 1:
        print(__doc__.strip().splitlines()[-4]); return 2
    proj = Path(args[0])
    try:
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"[house_gate] cannot read {proj / 'track.config.json'}: {e}"); return 2
    floor = floors(cfg)
    if floor is None:
        print("[house_gate] no floor declared (track.config.json scenery.bespoke.house_gate): skipped"); return 0
    kn5 = kn5 or proj / "build" / f"{cfg['slug']}.kn5"
    if not kn5.exists():
        print(f"[house_gate] no road kn5 at {kn5}"); return 2
    from scripts.ac.verify_kn5 import _parse_full
    _nodes, meshes, _mats = _parse_full(kn5)
    counts, detail = count(meshes)
    low = verdict(counts, floor)
    rep = {"kn5": str(kn5), "counts": counts, "floor": floor, "detail": detail, "weld_m": WELD_M,
           "fail": bool(low), "below": [{"key": k, "count": c, "floor": f} for k, c, f in low]}
    for k in KEYS:
        print(f"[house_gate] {k:9s} {counts[k]:6d}  floor {floor[k]:6d}  {'LOW' if counts[k] < floor[k] else 'ok'}")
    print("[house_gate] " + ", ".join(f"{c} {n}" for c, n in detail.items()))
    if out:
        out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[house_gate] {'FAIL: ' + '; '.join(f'{k} {c} < {f}' for k, c, f in low) if low else 'PASS'}")
    return 1 if low else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
