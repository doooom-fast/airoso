"""Give the draft's centreline the road heights its source fixes carry (ledger 0065, Lake Murray's redraft).

A ``source.type: from_track`` line whose fixes carry ``ele`` (metres, absolute) already knows its road's heights: Lake Murray's are the
approved road's own, decks held straight between their real abutments (tools/deck_datum.py), profile windows smoothed, grades capped
(LAWS L3). The elev stage would resample bare-earth 3DEP along the line instead, and bare earth has no bridge: College Avenue's deck
over I-8 falls into the trench. This step runs after the projection and replaces each vertex's height with the fixes' height at the
same place, interpolated along the nearest fix segment; the plan stays the draft's own.

    python tools/profile_from_fixes.py <project-dir>      (no ``ele`` in the fixes = no-op)

Refuses (exit 1) when a vertex lies more than MATCH_M from every fix segment: the fixes then describe another road.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MATCH_M = 3.0      # [invented] the draft resamples the fixes at 3 m with no smoothing (source.smooth_window 0): it stays on them


def _mpd(lat):
    """the projection's own metres per degree (scripts.geometry.projection): a sphere here put Lake Murray's fixes 4.4 m off"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.geometry.projection import _meters_per_degree
    return _meters_per_degree(lat)


def main(project_dir):
    proj = Path(project_dir)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    src = cfg.get("source") or {}
    if src.get("type") != "from_track" or not src.get("track"):
        print("[profile] not a from_track source: nothing to do")
        return
    fixes = json.loads((proj / src["track"]).read_text(encoding="utf-8"))
    if not all("ele" in f for f in fixes):
        print("[profile] the fixes carry no ele: the elev stage's heights stand")
        return
    lp = proj / "data" / "centerline.local.json"
    local = json.loads(lp.read_text(encoding="utf-8"))
    o = local["origin"]
    m_lon, m_lat = _mpd(o["lat"])
    F = [((f["lon"] - o["lon"]) * m_lon, (f["lat"] - o["lat"]) * m_lat, f["ele"] - o["elev_m"]) for f in fixes]
    if cfg.get("loop", True) and F[0] != F[-1]:
        F.append(F[0])
    cell = {}
    for k in range(len(F) - 1):
        for q in (F[k], F[k + 1]):
            cell.setdefault((int(q[0] // 20), int(q[1] // 20)), set()).add(k)
    out, worst, moved = [], 0.0, 0.0
    for x, y, z in local["points_xyz_m"]:
        c = (int(x // 20), int(z // 20))
        best = None
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in cell.get((c[0] + dx, c[1] + dz), ()):
                    (ax, az, ay), (bx, bz, by) = F[k], F[k + 1]
                    ex, ez = bx - ax, bz - az
                    L2 = ex * ex + ez * ez
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * ex + (z - az) * ez) / L2))
                    d = math.hypot(x - (ax + t * ex), z - (az + t * ez))
                    if best is None or d < best[0]:
                        best = (d, ay + t * (by - ay))
        if best is None or best[0] > MATCH_M:
            raise SystemExit(f"[profile] vertex ({x:.1f}, {z:.1f}) is {'-' if best is None else round(best[0], 2)} m from every fix: "
                             f"the fixes describe another road")
        worst = max(worst, best[0])
        moved = max(moved, abs(best[1] - y))
        out.append([x, round(best[1], 3), z])
    local["points_xyz_m"] = out
    local["height_m"] = round(max(p[1] for p in out) - min(p[1] for p in out), 2)
    local["profile_source"] = f"{src['track']} ele (tools/profile_from_fixes.py)"
    lp.write_text(json.dumps(local), encoding="utf-8")
    print(f"[profile] {len(out)} vertices take the fixes' heights: plan match worst {worst:.2f} m, height change from the elev stage up to "
          f"{moved:.2f} m")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/profile_from_fixes.py <project-dir>")
    main(sys.argv[1])
