"""NODEDBG — follow ONE terrain grid node's height through every write in build_mesh.

Arm it with ``NODEDBG="<x>,<z>"`` (local metres). build_mesh then swaps the grid row that owns the
nearest node for a :class:`WatchRow`, and the contact pin's flat node view for a :class:`WatchFlat`;
every assignment landing on that node prints the new height, the delta, and the exact source line
that wrote it. Decision probes (:func:`note`) fill in the gaps where a pass *declines* to write —
a silent node is the interesting case, and a height trace alone cannot show it.

Same instrument shape as the RINGDBG trace that cracked ledger 0012: measure the node, don't argue
about it. ``NODEDBG_STOP=1`` aborts the build right after the last pre-grass write, so a trace costs
a corridor pass instead of a full 860 MB OBJ.

Zero cost when the env var is unset: ENABLED is False and build_mesh skips every hook.
"""

from __future__ import annotations

import os
import sys

_spec = os.environ.get("NODEDBG", "").strip()
ENABLED = bool(_spec)
STOP = bool(os.environ.get("NODEDBG_STOP", "").strip())

TARGET: tuple[float, float] | None = None
if ENABLED:
    _p = [_q for _q in _spec.replace(" ", "").split(",") if _q]
    TARGET = (float(_p[0]), float(_p[1]))

# resolved by attach(): the watched node's place in the grid
COL = -1          # i (column)
ROW = -1          # j (row)
NX = -1           # row length, so the flat index is ROW * NX + COL
FLAT = -1
POS: tuple[float, float] | None = None   # the node's actual (x, z)

_n = 0
_last: float | None = None


def _where(depth: int) -> str:
    f = sys._getframe(depth)
    return f"{os.path.basename(f.f_code.co_filename)}:{f.f_lineno} {f.f_code.co_name}()"


def emit(y: float, site: str) -> None:
    """One write landed on the watched node."""
    global _n, _last
    _n += 1
    d = "" if _last is None else f"dy {y - _last:+8.3f}"
    print(f"[NODEDBG {_n:3d}] y {y:10.3f}  {d:>13}   {site}", flush=True)
    _last = y


def note(msg: str) -> None:
    """A decision about the watched node that produced no write.

    Silent when disarmed — the pass labels are called unconditionally from build_mesh, so an
    ungated print here puts NODEDBG chatter in every build's log.
    """
    if ENABLED:
        print(f"[NODEDBG   .] {msg}", flush=True)


def current() -> float | None:
    return _last


class WatchRow(list):
    """A grid row that reports every assignment to column ``COL``."""

    def __setitem__(self, k, v):          # noqa: D105
        list.__setitem__(self, k, v)
        if k == COL:
            emit(v[1], _where(2))


class WatchFlat(list):
    """The contact pin's flat node view, reporting assignments to index ``FLAT``."""

    def __setitem__(self, k, v):          # noqa: D105
        list.__setitem__(self, k, v)
        if k == FLAT:
            emit(v[1], _where(2))


def attach(grid_xyz: list) -> None:
    """Find the node nearest TARGET, swap its row for a WatchRow, print the baseline."""
    global COL, ROW, NX, FLAT, POS
    if not ENABLED or TARGET is None:
        return
    tx, tz = TARGET
    x0, z0 = grid_xyz[0][0][0], grid_xyz[0][0][2]
    NX = len(grid_xyz[0])
    ny = len(grid_xyz)
    dx = (grid_xyz[0][1][0] - x0) if NX > 1 else 1.0
    dz = (grid_xyz[1][0][2] - z0) if ny > 1 else 1.0
    COL = max(0, min(NX - 1, int(round((tx - x0) / dx))))
    ROW = max(0, min(ny - 1, int(round((tz - z0) / dz))))
    FLAT = ROW * NX + COL
    grid_xyz[ROW] = WatchRow(grid_xyz[ROW])
    vx, vy, vz = grid_xyz[ROW][COL]
    POS = (vx, vz)
    print(f"[NODEDBG] watching grid node (i={COL}, j={ROW}) at x {vx:.3f}, z {vz:.3f} "
          f"— asked for x {tx:.3f}, z {tz:.3f}; grid {NX}x{ny} @ {dx:.3f}x{dz:.3f} m", flush=True)
    emit(vy, "project_grid (bare 3DEP, before any pass)")


def attach_flat(gv: list) -> list:
    """Wrap the contact pin's flat node view so its writes are traced too."""
    if not ENABLED:
        return gv
    out = WatchFlat(gv)
    note(f"flat view built — index {FLAT} carries y {out[FLAT][1]:.3f}")
    return out


def is_node(i: int, j: int) -> bool:
    return ENABLED and i == COL and j == ROW


def is_flat(i: int) -> bool:
    return ENABLED and i == FLAT


def stop_if_asked() -> None:
    if ENABLED and STOP:
        print(f"[NODEDBG] NODEDBG_STOP set — {_n} writes traced, final y {_last:.3f}. "
              f"Stopping before the grass mesh.", flush=True)
        raise SystemExit(0)
