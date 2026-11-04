"""ONE height per shared node of a road NETWORK (ledger 0075, opt-in: track.config.json ``network.join_nodes``).

A network draft treats every edge on its own: ``scripts.elevation.network_elev`` smooths and grade-caps each edge's
3DEP profile open-ended, and ``scripts.geometry.build_network_mesh`` lays each edge's OSM-layer deck lift on its own.
So a node two or three edges share gets two or three heights. On the San Diego freeway (2026-11-03 draft) 334 of 365
shared nodes disagree at grade by more than 6 cm and 169 by more than 0.5 m (worst 19.86 m: the forward-only 5 % cap
lets an edge's END drift from 3DEP), and 65 disagree in deck lift by more than 1 m (a flyover's layer lift ends at the
edge boundary, or a ramp's starts there at full height beside an at-grade mainline). drive_test read the reference
line's joints as severe steps (the 204 -> 102 joint: 2.406 m).

The rule here, used for both the at-grade profile and the deck lift:
  * a node's ONE value is the mean of its THROUGH pair: the two edge ends that continue each other most nearly
    straight, preferring two mainline (non-ramp) ends. A ramp branching off takes the mainline's value at the node,
    the mainline is never bent toward its ramps; at a plain two-edge node it is the mean of both;
  * each edge then reaches its node's value at both ends (``pinned_cap``: exactly, within the profile's own grade cap
    where that is feasible, else a straight grade between the two pins; ``ramped``: an end correction blended back
    to zero over a ramp length for the deck lift).
Stdlib only.
"""

from __future__ import annotations

import math

NODE_ROUND = 7          # lon/lat decimals that identify a shared node (network.py writes one coordinate per node)


def node_key(lon: float, lat: float) -> tuple[float, float]:
    return (round(float(lon), NODE_ROUND), round(float(lat), NODE_ROUND))


def away_dir(xy: list[tuple[float, float]], end: int, reach_m: float = 15.0) -> tuple[float, float]:
    """Unit plan direction from end ``end`` (0 = first vertex, 1 = last) INTO the edge, read ``reach_m`` along it
    (a single 5 m segment at a junction is noise)."""
    pts = xy if end == 0 else xy[::-1]
    x0, y0 = pts[0]
    acc = 0.0
    tx, ty = (pts[1][0] - x0, pts[1][1] - y0) if len(pts) > 1 else (1.0, 0.0)
    for k in range(1, len(pts)):
        acc += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
        tx, ty = pts[k][0] - x0, pts[k][1] - y0
        if acc >= reach_m:
            break
    tl = math.hypot(tx, ty) or 1.0
    return tx / tl, ty / tl


def through_targets(ends: dict) -> dict:
    """``ends``: {node: [(edge_id, end, value, (dx, dy) away direction, is_ramp), ...]} -> {node: value} for every
    node shared by two or more edge ends (a dead end keeps its own value and is not in the result). The value is the
    mean of the node's THROUGH pair: of every pair of ends, the two that run on most nearly straight through the node
    (their away directions most nearly opposite), two mainline ends before any pair with a ramp in it."""
    out = {}
    for node, rows in ends.items():
        if len(rows) < 2:
            continue
        best = None
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                straight = -(a[3][0] * b[3][0] + a[3][1] * b[3][1])        # 1 = dead straight through, -1 = folded back
                score = (0 if (a[4] or b[4]) else 1, straight)
                if best is None or score > best[0]:
                    best = (score, (a[2] + b[2]) / 2.0)
        out[node] = best[1]
    return out


def pinned_cap(vals: list[float], seg_d: list[float], z0: float, z1: float, max_grade: float) -> list[float]:
    """``vals`` brought to ``z0`` at its first vertex and ``z1`` at its last with no vertex-to-vertex grade over
    ``max_grade`` (by the real segment length ``seg_d[i]`` = metres from vertex i-1 to i, at least 0.5 m as the
    engine's caps read it), changing ``vals`` as little as the cap allows: clamp into the envelope both pins can reach,
    then one forward and one backward cap pass with the pins held (the envelope keeps both passes inside it, so the
    result meets the cap everywhere). Where the two pins are further apart than the cap allows over the edge, the
    edge runs one straight grade between them (the pins win: a node has one height)."""
    n = len(vals)
    if n == 0:
        return []
    if n == 1:
        return [(z0 + z1) / 2.0]
    d = [0.0] + [max(0.5, float(seg_d[i])) for i in range(1, n)]
    s = [0.0] * n
    for i in range(1, n):
        s[i] = s[i - 1] + d[i]
    total = s[-1]
    if abs(z1 - z0) > max_grade * total + 1e-9:
        return [z0 + (z1 - z0) * (s[i] / total if total > 0 else 0.0) for i in range(n)]
    out = []
    for i in range(n):
        r = total - s[i]
        hi = min(z0 + max_grade * s[i], z1 + max_grade * r)
        lo = max(z0 - max_grade * s[i], z1 - max_grade * r)
        out.append(min(hi, max(lo, float(vals[i]))))
    out[0], out[-1] = z0, z1
    for i in range(1, n - 1):                         # forward, start pinned
        cap = max_grade * d[i]
        out[i] = out[i - 1] + max(-cap, min(cap, out[i] - out[i - 1]))
    for i in range(n - 2, 0, -1):                     # backward, end pinned
        cap = max_grade * d[i + 1]
        out[i] = out[i + 1] + max(-cap, min(cap, out[i] - out[i + 1]))
    return out


def ramped(vals: list[float], seg_d: list[float], d0: float, d1: float, *, ramp_grade: float,
           ramp_min_m: float) -> list[float]:
    """``vals`` plus an end correction ``d0`` at the first vertex and ``d1`` at the last, each blended linearly back
    to zero over max(``ramp_min_m``, |d| / ``ramp_grade``) metres; where the two ramps would overlap the edge takes
    one straight blend from ``d0`` to ``d1`` (both ends still exact)."""
    n = len(vals)
    if n == 0:
        return []
    s = [0.0] * n
    for i in range(1, n):
        s[i] = s[i - 1] + max(0.0, float(seg_d[i]))
    total = s[-1]
    L0 = max(ramp_min_m, abs(d0) / ramp_grade) if d0 else 0.0
    L1 = max(ramp_min_m, abs(d1) / ramp_grade) if d1 else 0.0
    out = []
    for i in range(n):
        if total <= 0.0:
            c = (d0 + d1) / 2.0
        elif L0 + L1 >= total:
            c = d0 + (d1 - d0) * s[i] / total
        else:
            c = (d0 * max(0.0, 1.0 - s[i] / L0) if L0 else 0.0) + (d1 * max(0.0, 1.0 - (total - s[i]) / L1) if L1 else 0.0)
        out.append(float(vals[i]) + c)
    return out
