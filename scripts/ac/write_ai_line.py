"""Write AC ``fast_lane.ai`` (v7) offline from the engine's racing line — R2's keystone.

No k10 track ships an AI line, so nothing can drive them but a human, so no automated in-game
test exists (REALISM.md §7). This retires that: the engine already holds the line in world metres
(``data/finished_centerline.json``: ``points_xyz_m`` + ``widths_m``, L6 frame = AC frame), and the
.ai binary is documented (fleet/reference/RESEARCH.md §B6, verified against gro-ove/actools
AcTools/AiFile):

    header  : 4×i32   version=7, pointCount, lapTime_ms, sampleCount
    points  : N×20 B  position 3×f32, cumulative length f32, id i32
    extras  : i32 N, then N×18×f32: speed, gas, brake, obsoleteLatG, radius, sideLeft, sideRight,
              camber, direction, normal xyz, length, forwardVector xyz, tag, grade
    trailer : i32 hasGrid (0 — AC/ksEditor rebuilds derived data; see the re-save caveat in B6)

Measured floor (fleet/reference/MEASURED.md §2): every reference ships ~1.5 m point spacing; the
freeroam/traffic trick is ``pit_lane.ai`` = copy of ``fast_lane.ai`` (how point-to-point roads get
working AI). Speed profile is physics-derived from curvature (lat-g cap + braking/accel passes) —
a hypothesis generator: whether the AI actually laps is decided in game, by the harness (rule 0).

    python -m scripts.ac.write_ai_line <project-dir>                    # -> <project>/ai/
    python -m scripts.ac.write_ai_line <project-dir> --install <AC-track-dir>
    python -m scripts.ac.write_ai_line <centerline.json> --out <dir> --spacing 1.5

L13 applies: a closed lap repeats its first vertex — detect, drop the duplicate, and wrap every
neighbour/distance computation; an open stage wraps nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
from pathlib import Path

G = 9.81


def _resample(pts: list[list[float]], widths: list[float], spacing: float, closed: bool):
    """Linear resample of the polyline (+widths) to ~spacing metres. Returns (pts, widths, ds)."""
    n = len(pts)
    seg = []
    total = 0.0
    m = n if not closed else n  # closed input arrives WITHOUT the duplicate vertex
    for i in range(m - (0 if closed else 1)):
        a, b = pts[i], pts[(i + 1) % n]
        d = math.dist(a, b)
        seg.append(d)
        total += d
    count = max(8, round(total / spacing))
    step = total / count
    out_p, out_w = [], []
    i, acc = 0, 0.0
    tgt = 0.0
    steps = count if closed else count + 1
    for _ in range(steps):
        while i < len(seg) and acc + seg[i] < tgt - 1e-9:
            acc += seg[i]; i += 1
        if i >= len(seg):
            out_p.append(list(pts[-1] if not closed else pts[0]))
            out_w.append(widths[-1] if not closed else widths[0])
        else:
            t = (tgt - acc) / seg[i] if seg[i] > 1e-12 else 0.0
            a, b = pts[i], pts[(i + 1) % n]
            out_p.append([a[k] + (b[k] - a[k]) * t for k in range(3)])
            wa, wb = widths[i], widths[(i + 1) % n]
            out_w.append(wa + (wb - wa) * t)
        tgt += step
    return out_p, out_w, step


def _circumradius(a, b, c) -> float:
    """Radius through three XZ points (planar — banking/grade handled separately)."""
    ax, az, bx, bz, cx, cz = a[0], a[2], b[0], b[2], c[0], c[2]
    d = 2.0 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz))
    if abs(d) < 1e-9:
        return 10000.0
    ux = ((ax * ax + az * az) * (bz - cz) + (bx * bx + bz * bz) * (cz - az)
          + (cx * cx + cz * cz) * (az - bz)) / d
    uz = ((ax * ax + az * az) * (cx - bx) + (bx * bx + bz * bz) * (ax - cx)
          + (cx * cx + cz * cz) * (bx - ax)) / d
    return min(10000.0, math.hypot(ax - ux, az - uz))


def build_line(pts, widths, *, closed: bool, spacing: float, lat_g: float, decel_g: float,
               accel_g: float, vmax_kmh: float, margin_m: float) -> dict:
    pts, widths, ds = _resample(pts, widths, spacing, closed)
    n = len(pts)
    idx = (lambda i: i % n) if closed else (lambda i: min(max(i, 0), n - 1))

    radius = [_circumradius(pts[idx(i - 1)], pts[i], pts[idx(i + 1)]) for i in range(n)]
    for _ in range(2):                                     # light smooth: min of neighbours window
        radius = [min(radius[idx(i - 1)], radius[i], radius[idx(i + 1)]) for i in range(n)]

    vmax = vmax_kmh / 3.6
    v = [min(vmax, math.sqrt(lat_g * G * r)) for r in radius]
    passes = 2 if closed else 1
    for _ in range(passes):                                # backward: braking limit
        for i in range(n - 1, -1, -1):
            vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
            v[i] = min(v[i], math.sqrt(vn * vn + 2 * decel_g * G * ds))
    for _ in range(passes):                                # forward: acceleration limit
        for i in range(n):
            vp = v[idx(i - 1)] if (closed or i > 0) else v[i]
            v[i] = min(v[i], math.sqrt(vp * vp + 2 * accel_g * G * ds))

    length = [i * ds for i in range(n)]
    lap_s = sum(ds / max(v[i], 1.0) for i in range(n if closed else n - 1))

    fwd, grade, gas, brake = [], [], [], []
    for i in range(n):
        a, b = pts[idx(i - 1)], pts[idx(i + 1)]
        span = max(1e-6, (2 * ds if closed or 0 < i < n - 1 else ds))
        t = [(b[k] - a[k]) / span for k in range(3)]
        norm = math.sqrt(sum(x * x for x in t)) or 1.0
        fwd.append([x / norm for x in t])
        grade.append(t[1] / norm)
        vn = v[idx(i + 1)] if (closed or i < n - 1) else v[i]
        acc = (vn * vn - v[i] * v[i]) / (2 * ds)
        brake.append(max(0.0, min(1.0, -acc / (decel_g * G))))
        gas.append(0.0 if brake[-1] > 0.05 else max(0.25, min(1.0, acc / (accel_g * G) + 0.55)))

    side = [max(0.5, w / 2.0 - margin_m) for w in widths]
    return {"pts": pts, "v": v, "length": length, "radius": radius, "fwd": fwd, "grade": grade,
            "gas": gas, "brake": brake, "side": side, "ds": ds, "lap_s": lap_s, "closed": closed}


def write_ai(line: dict, out: Path) -> None:
    n = len(line["pts"])
    buf = bytearray()
    buf += struct.pack("<4i", 7, n, int(line["lap_s"] * 1000), n)
    for i, p in enumerate(line["pts"]):
        buf += struct.pack("<4fi", p[0], p[1], p[2], line["length"][i], i)
    buf += struct.pack("<i", n)
    for i in range(n):
        f = line["fwd"][i]
        buf += struct.pack(
            "<18f",
            line["v"][i], line["gas"][i], line["brake"][i], 0.0,
            line["radius"][i], line["side"][i], line["side"][i],
            0.0, 0.0,                                  # camber, direction
            0.0, 1.0, 0.0,                             # normal (up)
            line["length"][i],
            f[0], f[1], f[2],
            0.0, line["grade"][i],
        )
    buf += struct.pack("<i", 0)                        # hasGrid = 0
    out.write_bytes(bytes(buf))


def write_sides(line: dict, out_dir: Path) -> None:
    """side_l/side_r.csv — lateral offsets of the drivable edge (the Shift-rebuild inputs)."""
    for name, sign in (("side_l.csv", -1.0), ("side_r.csv", 1.0)):
        rows = []
        for i, p in enumerate(line["pts"]):
            f = line["fwd"][i]
            px, pz = -f[2], f[0]                       # perpendicular in XZ, left of travel
            nrm = math.hypot(px, pz) or 1.0
            o = line["side"][i] * sign
            rows.append(f"{p[0] + px / nrm * o:.3f},{p[1]:.3f},{p[2] + pz / nrm * o:.3f}")
        (out_dir / name).write_text("\n".join(rows) + "\n", encoding="ascii")


def verify(path: Path) -> str:
    d = path.read_bytes()
    ver, count, lap, _ = struct.unpack_from("<4i", d, 0)
    first = struct.unpack_from("<f", d, 16 + 12)[0]
    last = struct.unpack_from("<f", d, 16 + (count - 1) * 20 + 12)[0]
    sp = (last - first) / (count - 1) if count > 1 else 0
    return (f"{path.name}: v{ver}, {count:,} pts, {sp:.2f} m spacing over {last - first:,.0f} m, "
            f"lap {lap / 1000:.1f} s, extras={'yes' if len(d) > 16 + count * 20 + 4 else 'NO'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate fast_lane.ai (v7) from the racing line.")
    ap.add_argument("src", type=Path, help="project dir (reads data/finished_centerline.json) or a json path")
    ap.add_argument("--out", type=Path, help="output dir (default <project>/ai)")
    ap.add_argument("--install", type=Path, help="AC track dir to copy ai/ into")
    ap.add_argument("--spacing", type=float, default=1.5, help="point spacing m (measured ref floor)")
    ap.add_argument("--lat-g", type=float, default=1.6)
    ap.add_argument("--decel-g", type=float, default=1.0)
    ap.add_argument("--accel-g", type=float, default=0.4)
    ap.add_argument("--vmax-kmh", type=float, default=250.0)
    ap.add_argument("--margin-m", type=float, default=1.2, help="kept clear of each road edge")
    ap.add_argument("--no-pit-copy", action="store_true", help="skip pit_lane.ai = fast_lane.ai")
    args = ap.parse_args()

    src = args.src / "data" / "finished_centerline.json" if args.src.is_dir() else args.src
    j = json.loads(src.read_text(encoding="utf-8"))
    pts, widths = j["points_xyz_m"], j["widths_m"]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    if closed:
        pts, widths = pts[:-1], widths[:-1]            # L13: drop the duplicate, wrap everything
    line = build_line(pts, widths, closed=closed, spacing=args.spacing, lat_g=args.lat_g,
                      decel_g=args.decel_g, accel_g=args.accel_g, vmax_kmh=args.vmax_kmh,
                      margin_m=args.margin_m)

    out = args.out or ((args.src if args.src.is_dir() else src.parent.parent) / "ai")
    out.mkdir(parents=True, exist_ok=True)
    write_ai(line, out / "fast_lane.ai")
    if not args.no_pit_copy:
        shutil.copyfile(out / "fast_lane.ai", out / "pit_lane.ai")
    write_sides(line, out)
    kind = "closed loop" if closed else "point-to-point"
    print(f"{kind}, {len(line['pts']):,} pts at {line['ds']:.2f} m; "
          f"est lap {line['lap_s']:.1f} s ({max(line['v']) * 3.6:.0f} km/h peak)")
    print("  " + verify(out / "fast_lane.ai"))
    if args.install:
        dst = args.install / "ai"
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("fast_lane.ai", "pit_lane.ai", "side_l.csv", "side_r.csv"):
            if (out / f).exists():
                shutil.copyfile(out / f, dst / f)
        print(f"  -> installed to {dst}")


if __name__ == "__main__":
    main()
