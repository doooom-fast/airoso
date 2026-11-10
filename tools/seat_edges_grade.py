"""The steep stretches of a line, for tools/seat_edges_blend.py's opt-in route.seat_edges_grade_pct (ledger 0083, Del Mar).

engine-july's prep pins the ground under the pavement to the deck - 0.02 m and holds a 3 m shelf past each lane edge at the
edge's height - 0.02 m, its corridor cut no finer than 4.5 m (seat_edges_blend.py's header). Where the measured profile
turns steeply (Del Mar's uncapped line crossing the planted banks of Jimmy Durante Blvd: 25 % over 10 m), a grass
triangle with a vertex on that shelf and one under the lane is a chord across the grade's turn, and on Del Mar's built
OBJ it stood 0.7 mm over the lane at s 1,099 (drive_test "ground on top" 2). The same finer cut seat_edges gives a
banked edge, given here by the grade: every line point whose measured grade (the centred difference over its two
neighbours) is past the declared percentage is treated as a point banked at atan(grade), so the cut rule (CHORD_M /
tan) reaches MAX_EDGE_M there. Absent key = nothing (every track without it builds as before).
"""
from __future__ import annotations

import math


def grade_points(P, pct: float):
    """[(x, z, atan(grade))] for every point of P ([x, y, z] metres, closed or open) whose centred grade exceeds pct %"""
    n = len(P)
    closed = n > 2 and math.hypot(P[0][0] - P[-1][0], P[0][2] - P[-1][2]) < 1e-6
    m = n - 1 if closed else n                      # L13: a closed lap repeats its first vertex
    out = []
    for i in range(m):
        if closed:
            a, b = P[(i - 1) % m], P[(i + 1) % m]
        else:
            a, b = P[max(0, i - 1)], P[min(n - 1, i + 1)]
        run = math.hypot(b[0] - a[0], b[2] - a[2])
        if run < 1e-6:
            continue
        g = abs(b[1] - a[1]) / run
        if 100.0 * g > pct:
            out.append((P[i][0], P[i][2], math.atan(g)))
    return out
