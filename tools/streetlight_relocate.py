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


# --- ledger 0054 P4 step 2: the seat rule, pure (tools/author_lamps_blend.reseat_and_check reads the built ground) ---
def needs_reseat(ground_y, base_y: float, tol_m: float) -> bool:
    """True when a pole's BASE (the road datum under its head, never the model's buried footing) stands more than
    ``tol_m`` under or over the built ground under it — or when there is no ground at all"""
    return ground_y is None or abs(float(ground_y) - float(base_y)) > float(tol_m)


def reseat_head_y(ground_y: float, head_over_ground_m: float) -> float:
    """the head height the draft's rule gives a post on this ground (build_loop_blend.build_streetlights)"""
    return float(ground_y) + float(head_over_ground_m)


def heads_too_close(heads, apart_m: float) -> list[tuple[int, int, float]]:
    """every pair of heads closer than ``apart_m`` horizontally — their lenses (a constant offset from the heads)
    would be clustered into ONE CSP light by scripts/ac/ext_config.py (LAMP_LINK_M)"""
    cells: dict = {}
    for i, h in enumerate(heads):
        cells.setdefault((int(float(h[0]) // apart_m), int(float(h[2]) // apart_m)), []).append(i)
    out = []
    for (cx, cz), ids in cells.items():
        for i in ids:
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in cells.get((cx + dx, cz + dz), ()):
                        if j > i:
                            d = math.hypot(float(heads[i][0]) - float(heads[j][0]), float(heads[i][2]) - float(heads[j][2]))
                            if d < apart_m:
                                out.append((i, j, round(d, 3)))
    return sorted(out)


# --- ledger 0098 0.2.13 (opt-in scenery.streetlights.measured, Sand Creek's Colorado Blvd): measured posts ---
MEASURED_KEYS = ("file",)


def measured_spec(cfg: dict, read_json) -> dict | None:
    """scenery.streetlights.measured {"file": <a path in the project>} -> the validated record, or None (absent).
    The record: {"zone_s_built_m": [s0, s1], "max_move_m", "step_m", "posts": [{"id", "base_xz", "out_xz"}, ...]}.
    ValueError on a malformed one. ``read_json(rel)`` reads a project file."""
    sl = ((cfg.get("scenery") or {}).get("streetlights") or {})
    m = sl.get("measured")
    if not m:
        return None
    if not isinstance(m, dict) or set(m) - set(MEASURED_KEYS) - {k for k in m if str(k).startswith("_")}:
        raise ValueError(f"scenery.streetlights.measured must be {{'file': ...}}, got {m!r}")
    rel = str(m.get("file") or "")
    if not rel or rel.startswith(("/", "\\")) or ".." in rel.replace("\\", "/").split("/"):
        raise ValueError(f"scenery.streetlights.measured.file {rel!r} must be a plain path inside the project")
    rec = read_json(rel)
    z = rec.get("zone_s_built_m")
    if not (isinstance(z, list) and len(z) == 2 and float(z[0]) < float(z[1])):
        raise ValueError(f"{rel}: zone_s_built_m must be [s0, s1], got {z!r}")
    posts = []
    for p in rec.get("posts") or []:
        for key in ("base_xz", "out_xz"):
            v = p.get(key)
            if not (isinstance(v, (list, tuple)) and len(v) == 2):
                raise ValueError(f"{rel}: post {p.get('id')!r}: {key} must be [x, z], got {v!r}")
        ox, oz = float(p["out_xz"][0]), float(p["out_xz"][1])
        if abs(math.hypot(ox, oz) - 1.0) > 1e-3:
            raise ValueError(f"{rel}: post {p.get('id')!r}: out_xz must be a unit vector")
        posts.append({"id": str(p["id"]), "base": (float(p["base_xz"][0]), float(p["base_xz"][1])), "out": (ox, oz)})
    if not posts:
        raise ValueError(f"{rel}: no posts")
    return {"file": rel, "zone": (float(z[0]), float(z[1])), "posts": posts,
            "max_move_m": float(rec.get("max_move_m", 0.75)), "step_m": float(rec.get("step_m", 0.05))}


def measured_plan(heads, base_of_head, s_of, spec: dict, nearest_cl, arm: float, on_road, ground_y,
                  head_over_ground_m: float):
    """the measured posts in place of the draft's posts inside the spec's zone (stations on the built line; module doc):
      * a draft post whose base s_of(base) lies in the zone is left out (recorded: "replaced");
      * each measured post stands at its base; when on_road(bx, bz) (its footprint + setback reaches a road surface) it
        steps out along out_xz by step_m to the first clear spot, at most max_move_m (recorded: moved_m); still on a road
        there, it is kept at its measured base, recorded "on_road", and left to drop_on_road (never moved further);
      * its head: the author's own rule solved for that base (head_for_base), head_over_ground_m over ground_y(bx, bz).
    The measured posts go where the zone's first draft post was (the draft's order is along the lap, so LIGHTPOST's
    batches keep their stretches). Returns (new heads, record)."""
    keep, replaced, at = [], [], None
    for i, h in enumerate(heads):
        bx, bz = base_of_head(i, h)
        s = s_of(bx, bz)
        if spec["zone"][0] <= s <= spec["zone"][1]:
            replaced.append({"i": i, "base_xz": [round(bx, 3), round(bz, 3)], "s_built_m": round(s, 1)})
            if at is None:
                at = len(keep)
        else:
            keep.append(list(h))
    new, rows = [], []
    for p in sorted(spec["posts"], key=lambda q: s_of(*q["base"])):
        bx, bz = p["base"]
        moved, status = 0.0, "placed"
        if on_road(bx, bz):
            status = "on_road"
            n = int(round(spec["max_move_m"] / spec["step_m"]))
            for k in range(1, n + 1):
                d = k * spec["step_m"]
                x, z = bx + p["out"][0] * d, bz + p["out"][1] * d
                if not on_road(x, z):
                    bx, bz, moved, status = x, z, d, "moved"
                    break
        g = ground_y(bx, bz)
        if g is None:
            raise ValueError(f"measured post {p['id']}: no ground under ({bx:.2f}, {bz:.2f})")
        hx, hz = head_for_base(bx, bz, nearest_cl, arm)
        new.append([round(hx, 3), round(float(g) + head_over_ground_m, 4), round(hz, 3)])
        rows.append({"id": p["id"], "base_measured_xz": [round(p["base"][0], 3), round(p["base"][1], 3)],
                     "base_xz": [round(bx, 3), round(bz, 3)], "moved_m": round(moved, 3), "status": status,
                     "s_built_m": round(s_of(bx, bz), 1)})
    at = len(keep) if at is None else at
    out = keep[:at] + new + keep[at:]
    rec = {"file": spec["file"], "zone_s_built_m": list(spec["zone"]), "max_move_m": spec["max_move_m"],
           "replaced": replaced, "posts": rows, "inserted_at": at}
    return out, rec
