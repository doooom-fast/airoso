"""The rock / grass choice over a cut band's triangles, as pure set rules (no bpy): tools/rock_faces_blend.py calls
them on the prepped ground, the tests call them on a lattice.

Ledger 0054 P4 integration fix round — the lace at the toe and the tongues up the face. The first rule (a face is rock
when it stands at slope_min or steeper) read every triangle on its own. The ground release lays the batter as lattice
rows, so where a flat row meets a raised row the triangles between them alternate flat / steep: a sawtooth of grass
teeth into the rock along the whole toe (view lens, Jackson north 1225-1525), and a flat bench row across a wall came
out as a grass tongue open to the hill (146 faces / 115 m2 within 30 m of Jackson). Three rules on top, in this order,
none of them moving a vertex:

  0. the caller drops rock patches under MIN_PATCH_M2 first (the outcrop speckles on a bank never join up into a wall).
  1. smooth_boundary: a grass face with two or more of its three edge-neighbours rock becomes rock (a tooth); a rock
     face with two or more grass edge-neighbours becomes grass (the inverse tooth); both read one state per pass,
     SMOOTH_PASSES passes. A straight lattice row is stable under both, so the boundary ends on a row, not a lace.
  2. fill_tongues: a grass component smaller than max_area_m2 whose boundary is TONGUE_ROCK_FRAC or more rock (its band-
     edge and mesh-edge sides count as open) becomes rock: a bench row across the wall, a tongue open to the hill.
  3. the caller's own small-patch / enclosed-hole clean-up (MIN_PATCH_M2 / MAX_HOLE_M2 in rock_faces_blend) as before.

``blocked(key)`` names the faces that may never become rock (a corner under a pavement sheet: the walk's buried apron,
the curtain behind a curb — the self-check refuses them); a component holding one is left whole, which is exactly the
toe shoulder along the walk.
"""
from __future__ import annotations

SMOOTH_PASSES = 2          # [invented] synchronous fill + erode passes: a tooth is a one-triangle feature, two passes catch
                           # the second-order ones; more only walks a strip's end back one triangle per pass
TONGUE_ROCK_FRAC = 0.6     # [invented] a small grass component with this share of its boundary against rock is a tongue


def teeth(rock, keys, adjacency):
    """(grass faces with two or more rock edge-neighbours, rock faces with two or more grass edge-neighbours) — the lace
    the smoothing removes; reported before and after"""
    rock = set(rock)
    g = sum(1 for k in keys if k not in rock and sum(1 for h in adjacency.get(k, ()) if h in rock) >= 2)
    r = sum(1 for k in rock if sum(1 for h in adjacency.get(k, ()) if h in keys and h not in rock) >= 2)
    return g, r


def smooth_boundary(rock, keys, adjacency, blocked=lambda k: False, passes=SMOOTH_PASSES):
    """rock: set of face keys; keys: every face key in the bands; adjacency: {key: set(key)} over edges. Each pass reads
    one state and flips both kinds of tooth at once (synchronous), so a flip never feeds the next flip inside a pass.
    Returns (rock', {"filled": n, "eroded": n, "passes": n, "teeth_before": (g, r), "teeth_after": (g, r)})."""
    rock = set(rock)
    keys = set(keys)
    stats = {"filled": 0, "eroded": 0, "passes": 0, "teeth_before": teeth(rock, keys, adjacency)}
    for _ in range(passes):
        add = {k for k in keys if k not in rock and not blocked(k)
               and sum(1 for h in adjacency.get(k, ()) if h in rock) >= 2}
        drop = {k for k in rock if sum(1 for h in adjacency.get(k, ()) if h in keys and h not in rock) >= 2}
        rock |= add
        rock -= drop
        stats["filled"] += len(add)
        stats["eroded"] += len(drop)
        stats["passes"] += 1
        if not add and not drop:
            break
    stats["teeth_after"] = teeth(rock, keys, adjacency)
    return rock, stats


def components(face_keys, adjacency):
    """connected components of a set of face keys over an edge adjacency {face key: set(face key)}"""
    seen, comps = set(), []
    for f in face_keys:
        if f in seen:
            continue
        stack, comp = [f], []
        seen.add(f)
        while stack:
            g = stack.pop()
            comp.append(g)
            for h in adjacency.get(g, ()):
                if h in face_keys and h not in seen:
                    seen.add(h)
                    stack.append(h)
        comps.append(comp)
    return comps


def fill_tongues(rock, keys, adjacency, area, blocked=lambda k: False, max_area_m2=60.0, rock_frac=TONGUE_ROCK_FRAC):
    """area: {key: m2}. A grass component (within keys) under max_area_m2, holding no blocked face, with rock_frac or
    more of its boundary sides against rock, becomes rock. Boundary sides = 3 per triangle less the sides shared inside
    the component; a side with no neighbour at all (band edge, mesh edge) is open, not rock.
    Returns (rock', filled_faces, filled_components)."""
    rock = set(rock)
    grass = {k for k in keys if k not in rock}
    nf = nc = 0
    for comp in components(grass, adjacency):
        if sum(area[k] for k in comp) >= max_area_m2 or any(blocked(k) for k in comp):
            continue
        cs = set(comp)
        sides = to_rock = 0
        for k in comp:
            nb = adjacency.get(k, ())
            inside = sum(1 for h in nb if h in cs)
            sides += 3 - inside
            to_rock += sum(1 for h in nb if h in rock)
        if sides and to_rock / sides >= rock_frac:
            rock |= cs
            nf += len(cs)
            nc += 1
    return rock, nf, nc
