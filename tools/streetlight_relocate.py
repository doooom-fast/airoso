"""Named streetlight relocations — the pure-python half of tools/author_lamps_blend.py's RELOCATIONS (v0.18.1).

`track.config.json` `scenery.streetlights.relocate` = [{name, from_base_xz, to_base_xz, seat, why}]. The draft
(build_loop_blend.build_streetlights) records each lamp by its HEAD (arm tip); author_lamps_blend stands the post
ARM_M behind it, away from the road (road-ward = head -> nearest centreline point). An entry names a post by that
base as the draft placed it and gives the base it should have; this module finds the post (exactly one within
MATCH_TOL_M, or ValueError) and solves the head that puts the post at the new base under the author's own rule.
Heights are the Blender half's job (it reads the authored ground). No bpy here, so the tests import it.
"""
from __future__ import annotations

import math

SEATS = ("ground", "keep")


def entries(cfg: dict) -> list[dict]:
    """the validated relocate list (ValueError on a malformed entry)"""
    sl = ((cfg.get("scenery") or {}).get("streetlights") or {})
    out = []
    for k, e in enumerate(sl.get("relocate") or []):
        name = str(e.get("name") or f"relocate[{k}]")
        for key in ("from_base_xz", "to_base_xz"):
            v = e.get(key)
            if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(q, (int, float)) for q in v)):
                raise ValueError(f"{name}: {key} must be [x, z] (local metres), got {v!r}")
        seat = str(e.get("seat", "ground"))
        if seat not in SEATS:
            raise ValueError(f"{name}: seat must be one of {SEATS}, got {seat!r}")
        if not str(e.get("why") or "").strip():
            raise ValueError(f"{name}: a relocation says why")
        out.append({"name": name, "from": (float(e["from_base_xz"][0]), float(e["from_base_xz"][1])),
                    "to": (float(e["to_base_xz"][0]), float(e["to_base_xz"][1])), "seat": seat})
    return out


def roadward(x: float, z: float, nearest_cl) -> tuple[float, float]:
    c = nearest_cl(x, z)
    dx, dz = c[0] - x, c[2] - z
    L = math.hypot(dx, dz) or 1e-9
    return dx / L, dz / L


def base_of(head, nearest_cl, arm: float) -> tuple[float, float]:
    """the post base author_lamps_blend stands under a recorded head"""
    rx, rz = roadward(head[0], head[2], nearest_cl)
    return head[0] - rx * arm, head[2] - rz * arm


def head_for_base(bx: float, bz: float, nearest_cl, arm: float, iters: int = 8) -> tuple[float, float]:
    """the head (x, z) whose post, under the author's rule, stands at (bx, bz): head = base + arm * road-ward(head)"""
    rx, rz = roadward(bx, bz, nearest_cl)
    hx, hz = bx + rx * arm, bz + rz * arm
    for _ in range(iters):
        rx, rz = roadward(hx, hz, nearest_cl)
        hx, hz = bx + rx * arm, bz + rz * arm
    return hx, hz


def plan(heads, nearest_cl, ents: list[dict], arm: float, match_tol: float, max_move: float) -> list[dict]:
    """one row per entry: the lamp index it moves, its old base, the new base and head x/z (ValueError when an entry
    names no post or several, two entries name one post, or the move is longer than max_move)"""
    bases = [base_of(h, nearest_cl, arm) for h in heads]
    rows, taken = [], {}
    for e in ents:
        near = [i for i, b in enumerate(bases) if math.dist(b, e["from"]) <= match_tol]
        if len(near) != 1:
            best = min(range(len(bases)), key=lambda i: math.dist(bases[i], e["from"])) if bases else None
            hint = (f"; nearest post is lamp {best} at ({bases[best][0]:.2f}, {bases[best][1]:.2f}), "
                    f"{math.dist(bases[best], e['from']):.2f} m away") if best is not None else ""
            raise ValueError(f"{e['name']}: {len(near)} posts within {match_tol} m of from_base_xz "
                             f"({e['from'][0]}, {e['from'][1]}){hint}")
        i = near[0]
        if i in taken:
            raise ValueError(f"{e['name']}: lamp {i} is already moved by {taken[i]}")
        taken[i] = e["name"]
        move = math.dist(bases[i], e["to"])
        if move > max_move:
            raise ValueError(f"{e['name']}: a {move:.2f} m move (> {max_move} m) is a new lamp, not a relocation")
        hx, hz = head_for_base(e["to"][0], e["to"][1], nearest_cl, arm)
        rows.append({"name": e["name"], "lamp": i, "seat": e["seat"], "old_base": [round(bases[i][0], 3), round(bases[i][1], 3)],
                     "new_base": [round(e["to"][0], 3), round(e["to"][1], 3)], "head_xz": (hx, hz), "move_m": round(move, 3)})
    return rows
