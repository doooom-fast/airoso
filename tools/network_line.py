"""A road NETWORK's reference line as an LM-engine port's line (ledger 0080, the SD freeway on Lake Murray's engine).

The LM engine's intake (tools/lm_engine_intake.py) reads a source track's ONE line: centerline.local.json, its 3DEP grid
and centerline.geojson. A network track (source.type osm-network) has no single line; its draft step network_reference
(scripts.geometry.network_reference) resolves the ONE real mainline the ship phase walks (track.config.json
network.reference_line) from the draft's own edges. This tool turns that draft's output into the intake's three files:

  centerline.local.json   network_reference's line (x / z, widths, source_by_vertex), with Y = the line's OWN 3DEP,
                          UNCAPPED: each vertex's raw sample (network.elevation.json z_raw_m at its [edge, vertex]),
                          de-spiked and smoothed as network_elev does (its 33 m median + 45 m mean, `_median_mean`),
                          WITHOUT network_elev's 5 % grade cap and without join_nodes' node pin (Kevin 2026-11-03: "I
                          just want real"; 0078's "profile uncapped"). The declared decks are the intake's job
                          (capture.bridges, levelled between the bank crests), as for every port.
  centerline.geojson      the same vertices in lon / lat, read from network.geojson at each [edge, vertex] (exact, no
                          inverse projection)
  heightfield.npy / .meta.json   the draft's 3DEP grid, as is

plus, as records: network.reference.json, network.caps.json (when the draft capped its dead ends) and
network_line.json (what was taken, the md5 of every input and output, the measured vs the draft's capped grade).

    python tools/network_line.py <network-draft-project-dir> <out-dir>

Stdlib only. Lake Murray never runs it.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

MEDIAN_M = 33.0   # network_elev.MEDIAN_M (scripts/elevation/network_elev.py, PR 34): its de-spike, not a new number
MEAN_M = 45.0     # network_elev.MEAN_M


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _smooth_open(vals: list[float], win: int) -> list[float]:
    """a centred moving mean over an OPEN run, the window shrinking at the ends (heightfield.smooth_open's rule)"""
    n, h = len(vals), win // 2
    out = []
    for i in range(n):
        a, b = max(0, i - h), min(n, i + h + 1)
        out.append(sum(vals[a:b]) / (b - a))
    return out


def _median_mean(z_raw: list[float], spacing_m: float) -> list[float]:
    n = len(z_raw)
    mw = max(3, round(MEDIAN_M / spacing_m)) | 1
    h = mw // 2
    med = [sorted(z_raw[max(0, i - h):min(n, i + h + 1)])[(min(n, i + h + 1) - max(0, i - h)) // 2] for i in range(n)]
    sw = max(3, round(MEAN_M / spacing_m)) | 1
    return _smooth_open(med, sw)


def _max_grade(xs, zs, ys, over_m: float = 10.0) -> float:
    st = [0.0]
    for i in range(1, len(xs)):
        st.append(st[-1] + math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]))
    best, j = 0.0, 0
    for i in range(len(st)):
        while j < len(st) and st[j] - st[i] < over_m:
            j += 1
        if j >= len(st):
            break
        best = max(best, abs(ys[j] - ys[i]) / (st[j] - st[i]))
    return best


def build(draft: Path, out: Path) -> dict:
    d = draft / "data"
    local = json.loads((d / "centerline.local.json").read_text(encoding="utf-8"))
    sbv = local.get("source_by_vertex")
    pts = local["points_xyz_m"]
    if not sbv or len(sbv) != len(pts):
        raise SystemExit("[network_line] centerline.local.json carries no source_by_vertex for every vertex — "
                         "run scripts.geometry.network_reference on this draft first")
    elev = json.loads((d / "network.elevation.json").read_text(encoding="utf-8"))
    rows = elev["edges"] if isinstance(elev, dict) and "edges" in elev else elev
    zraw = {int(r["id"]): r["z_raw_m"] for r in rows}
    gj = json.loads((d / "network.geojson").read_text(encoding="utf-8"))
    coords = {int(f["properties"]["id"]): f["geometry"]["coordinates"] for f in gj["features"]}
    elev0 = float(local["origin"]["elev_m"])
    raw = [float(zraw[int(e)][int(v)]) for e, v in sbv]
    xs = [p[0] for p in pts]
    zs = [p[2] for p in pts]
    L = sum(math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]) for i in range(1, len(pts)))
    spacing = L / max(1, len(pts) - 1)
    meas = _median_mean(raw, spacing)
    y_new = [round(z - elev0, 3) for z in meas]
    y_old = [p[1] for p in pts]
    out.mkdir(parents=True, exist_ok=True)
    loc2 = dict(local)
    loc2["points_xyz_m"] = [[p[0], y, p[2]] for p, y in zip(pts, y_new)]
    loc2["source"] = (f"{local.get('source', 'network_reference')}; Y = the line's own 3DEP (network.elevation.json "
                      f"z_raw_m), de-spiked + smoothed as network_elev (median {MEDIAN_M:.0f} m, mean {MEAN_M:.0f} m), "
                      f"no grade cap, no node pin (tools/network_line.py, ledger 0080)")
    loc2["loop"] = False
    (out / "centerline.local.json").write_text(json.dumps(loc2), encoding="utf-8")
    lonlat = [coords[int(e)][int(v)] for e, v in sbv]
    widths = local["widths_m"]
    feat = {"type": "Feature",
            "properties": {"name": "centerline", "kind": "full", "closed": False, "length_m": round(L, 1),
                           "default_width_m": round(sum(widths) / len(widths), 2), "widths_m": widths,
                           "source": "network_reference's line, lon / lat from network.geojson (tools/network_line.py)"},
            "geometry": {"type": "LineString", "coordinates": [[round(c[0], 8), round(c[1], 8)] for c in lonlat]}}
    (out / "centerline.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}), encoding="utf-8")
    for f in ("heightfield.npy", "heightfield.meta.json", "network.reference.json", "network.caps.json"):
        if (d / f).exists():
            shutil.copyfile(d / f, out / f)
    rep = {
        "tool": "tools/network_line.py", "ledger": "0080",
        "draft": str(draft), "points": len(pts), "length_m": round(L, 1), "spacing_m": round(spacing, 3),
        "y_measured_minus_draft_m": {"max_abs": round(max(abs(a - b) for a, b in zip(y_new, y_old)), 3),
                                     "mean": round(sum(a - b for a, b in zip(y_new, y_old)) / len(pts), 3)},
        "max_grade_10m_pct": {"measured_uncapped": round(100 * _max_grade(xs, zs, y_new), 2),
                              "draft_capped": round(100 * _max_grade(xs, zs, y_old), 2),
                              "raw_3dep_no_smoothing": round(100 * _max_grade(xs, zs, [z - elev0 for z in raw]), 2)},
        "inputs": {f: _md5(d / f) for f in ("centerline.local.json", "network.elevation.json", "network.geojson",
                                            "heightfield.npy", "heightfield.meta.json", "network.reference.json")},
        "outputs": {p.name: _md5(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "network_line.json"},
    }
    (out / "network_line.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[network_line] {len(pts)} points, {L:.0f} m; Y measured vs the draft's: max |dy| "
          f"{rep['y_measured_minus_draft_m']['max_abs']} m; max grade / 10 m measured "
          f"{rep['max_grade_10m_pct']['measured_uncapped']} % (draft capped {rep['max_grade_10m_pct']['draft_capped']} %)")
    return rep


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
