"""On-road brightness of the CSP streetlights, before and after a lamp-model change (ledger 0056).

Kevin approved the night look of v0.18.0 (ledger 0043: 80s low-pressure sodium, intensity 0.013 "a bit brighter but
not much", wide dim pools). A taller lamp moves every [LIGHT_N] up; this measures what that does ON THE ROAD with the
light settings unchanged, so the per-light intensity is scaled only if (and only as far as) the brightness under and
between the lamps needs it.

THE MODEL (CSP's track-light shading as its wiki documents it — acc-extension-config "Tracks – Lights" — with the
shapes ledger 0043 tuned the pools against; no CSP source is public, so every shape choice is recorded in
fleet/GATES-CHANGELOG.md and BOTH fade shapes are reported):
  E(p) = sum over lights of  I * A(d) * S(theta) * D(theta)
  A  range: 1 up to RANGE_GRADIENT_OFFSET * RANGE ("at what point of light travel it would start to fade"), then
     to 0 at RANGE — `linear` (the 0043 reading) or `quadratic` ((1 - t)^2, a softer tail)
  S  spot (DIRECTION straight down): saturate((cos theta - cos(SPOT/2)) / ((1 - cos(SPOT/2)) * (1 - SPOT_SHARPNESS)))
     — "with 0 the brightest point is in the middle, with 1 it's 100% bright right until the edge"
  D  DIFFUSE_CONCENTRATION c on the flat road: (1 - c) + c * cos theta — "with 1 surfaces orthogonal to the light
     would be in shadow, with 0 even surfaces facing away would be fully lit"
The road is the mainline: every centreline point, sampled every 0.5 m across its width at the centreline height.

METRICS (per model, per fade shape):
  under     E at the road point nearest each light's foot (the pavement right under / beside the lamp), mean
  between   E across the carriageway at the station midway (by arc length) between consecutive lamps, mean
  pool_r50  along the road at the lamp's near lane: the distance from the lamp where E falls to half its peak, median
  shoulder  E on the road samples 8-14 m (horizontally) from the nearest light, mean — the pool's flank
  road_mean E averaged over every road sample within RANGE of a light (the lit road as a whole)

    PYTHONUTF8=1 python tools/streetlight_pool.py <project-dir> [--new-intensity X] [--json <out>]
        old = street_lamp_2026_10 (v0.18.0), new = led_cobra, both rebuilt from data/lights.local.json heads the way
        tools/author_lamps_blend.py places them; the light settings from track.config.json lighting.streetlight
    ... --ini-old <ext_config.ini> --ini-new <ext_config.ini>
        measure the WRITTEN [LIGHT_N] blocks instead (kn5 frame -> local: z negated)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[1]
LIGHT_DROP_M = 0.15


def _author_constant(name: str) -> float:
    src = (AIROSO / "tools" / "author_lamps_blend.py").read_text(encoding="utf-8")
    m = re.search(rf"^{name}\s*=\s*([0-9]+(?:\.[0-9]+)?)", src, re.M)
    if not m:
        raise SystemExit(f"[pool] {name} not found in tools/author_lamps_blend.py")
    return float(m.group(1))


def _road_ward(cl, hx, hz):
    best, bi = float("inf"), 0
    for i, p in enumerate(cl):
        d = (p[0] - hx) ** 2 + (p[2] - hz) ** 2
        if d < best:
            best, bi = d, i
    c = cl[bi]
    L = math.hypot(c[0] - hx, c[2] - hz) or 1e-9
    return (c[0] - hx) / L, (c[2] - hz) / L


def predicted_lights(heads, cl):
    """(old, new) light positions (local frame) as author_lamps_blend + ext_config place them"""
    arm, post_h, head_above = _author_constant("ARM_M"), _author_constant("POST_H"), _author_constant("HEAD_ABOVE_ROAD_M")
    top = max(float(ln.split()[2]) for ln in (AIROSO / "assets" / "models" / "lamp_post.obj").read_text(
        encoding="utf-8", errors="ignore").splitlines() if ln.startswith("v "))
    scale = post_h / top
    old_r, old_up = 1.25 * scale, 0.1 - post_h + 7.7 * scale - 0.3 + 0.02 / 3
    spec = json.loads((AIROSO / "assets" / "models" / "streetlight_led.json").read_text(encoding="utf-8"))
    new_r, new_up = spec["lens_centre_m"][0], spec["lens_centre_m"][1] - head_above
    old, new = [], []
    for hx, hy, hz in heads:
        rx, rz = _road_ward(cl, hx, hz)
        bx, bz = hx - rx * arm, hz - rz * arm
        old.append((bx + rx * old_r, hy + old_up - LIGHT_DROP_M, bz + rz * old_r))
        new.append((bx + rx * new_r, hy + new_up - LIGHT_DROP_M, bz + rz * new_r))
    return old, new


def ini_lights(path: Path):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    out = []
    for m in re.finditer(r"^\[LIGHT_\d+\]\s*$(.*?)(?=^\[|\Z)", txt, re.M | re.S):
        pm = re.search(r"^POSITION\s*=\s*([^\n;]+)", m.group(1), re.M)
        if pm:
            x, y, z = (float(v) for v in pm.group(1).split(","))
            out.append((x, y, -z))
    return out


class Light:
    def __init__(self, sl: dict, intensity: float | None = None):
        self.I = float(intensity if intensity is not None else sl.get("intensity", 0.013))
        self.R = float(sl.get("range_m", 25.0))
        self.g = float(sl.get("range_gradient_offset", 0.5))
        half = math.radians(float(sl.get("spot_deg", 150)) / 2)
        self.cos_o = math.cos(half)
        self.sharp = float(sl.get("spot_sharpness", 0.2))
        self.c = float(sl.get("diffuse_concentration", 0.88))

    def E(self, light, p, fade="linear"):
        dx, dy, dz = p[0] - light[0], p[1] - light[1], p[2] - light[2]
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        if d >= self.R or dy >= 0:
            return 0.0
        t = max(0.0, (d - self.g * self.R) / ((1 - self.g) * self.R))
        a = (1 - t) if fade == "linear" else (1 - t) ** 2
        cos_t = -dy / d
        den = (1 - self.cos_o) * max(1e-6, 1 - self.sharp)
        s = max(0.0, min(1.0, (cos_t - self.cos_o) / den))
        return self.I * max(0.0, a) * s * ((1 - self.c) + self.c * cos_t)


def road_samples(cl, widths, step=0.5):
    """(station index, lateral, (x, y, z)) across every centreline point's width"""
    out = []
    n = len(cl)
    for i, p in enumerate(cl):
        a, b = cl[max(0, i - 1)], cl[min(n - 1, i + 1)]
        ex, ez = b[0] - a[0], b[2] - a[2]
        L = math.hypot(ex, ez) or 1.0
        nx, nz = -ez / L, ex / L
        hw = widths[i] / 2
        k = -hw
        while k <= hw + 1e-9:
            out.append((i, k, (p[0] + nx * k, p[1], p[2] + nz * k)))
            k += step
    return out


def measure(lights, cl, widths, model: Light, fade: str) -> dict:
    samples = road_samples(cl, widths)
    cell = 10.0
    grid: dict[tuple[int, int], list[int]] = {}
    for j, L in enumerate(lights):
        grid.setdefault((int(L[0] // cell), int(L[2] // cell)), []).append(j)
    reach = int(math.ceil(model.R / cell))

    def E_at(p):
        cx, cz = int(p[0] // cell), int(p[2] // cell)
        e = 0.0
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                for j in grid.get((cx + dx, cz + dz), ()):
                    e += model.E(lights[j], p, fade)
        return e

    # station of each light (nearest centreline index) and arc length
    cum = [0.0]
    for i in range(1, len(cl)):
        cum.append(cum[-1] + math.dist((cl[i][0], cl[i][2]), (cl[i - 1][0], cl[i - 1][2])))
    sgrid: dict[tuple[int, int], list[int]] = {}
    for si, (i, k, p) in enumerate(samples):
        sgrid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(si)

    def nearest_sample(x, z):
        best, bs = float("inf"), None
        cx, cz = int(x // cell), int(z // cell)
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                for si in sgrid.get((cx + dx, cz + dz), ()):
                    p = samples[si][2]
                    d = (p[0] - x) ** 2 + (p[2] - z) ** 2
                    if d < best:
                        best, bs = d, si
        return bs, math.sqrt(best)

    under, foot_off, st = [], [], []
    for L in lights:
        si, d = nearest_sample(L[0], L[2])
        if si is None:
            continue
        under.append(E_at(samples[si][2]))
        foot_off.append(d)
        st.append(samples[si][0])
    order = sorted(range(len(st)), key=lambda j: cum[st[j]])
    between = []
    by_station: dict[int, list[int]] = {}
    for si, (i, k, p) in enumerate(samples):
        by_station.setdefault(i, []).append(si)
    for a, b in zip(order, order[1:]):
        sa, sb = cum[st[a]], cum[st[b]]
        if sb - sa > 120:            # a lamp gap (bridge / cut): not a "between lamps" station
            continue
        mid = min(range(len(cum)), key=lambda i: abs(cum[i] - (sa + sb) / 2))
        between.append(statistics.fmean(E_at(samples[si][2]) for si in by_station.get(mid, [])))
    # pool half-width along the near lane of each lamp: walk the near-lane samples away from the lamp
    r50 = []
    for j in order[: len(order)]:
        si, _ = nearest_sample(lights[j][0], lights[j][2])
        i0, k0, _p = samples[si]
        peak = None
        for dist in range(0, 40):
            # the station dist metres further along, same lateral
            tgt = cum[i0] + dist
            i1 = min(range(max(0, i0 - 5), min(len(cum), i0 + 60)), key=lambda i: abs(cum[i] - tgt))
            pts = [samples[s] for s in by_station.get(i1, []) if abs(samples[s][1] - k0) < 0.26]
            if not pts:
                break
            e = model.E(lights[j], pts[0][2], fade)
            peak = e if peak is None else peak
            if peak and e < 0.5 * peak:
                r50.append(dist)
                break
    lit, shoulder = [], []
    for si, (i, k, p) in enumerate(samples):
        e = E_at(p)
        if e > 0:
            lit.append(e)
            cx, cz = int(p[0] // cell), int(p[2] // cell)
            dmin = min((math.hypot(lights[j][0] - p[0], lights[j][2] - p[2]) for dx in (-2, -1, 0, 1, 2)
                        for dz in (-2, -1, 0, 1, 2) for j in grid.get((cx + dx, cz + dz), ())), default=99.0)
            if 8.0 <= dmin <= 14.0:
                shoulder.append(e)
    return {"lights": len(lights), "under_mean": statistics.fmean(under), "under_median": statistics.median(under),
            "foot_offset_m_median": statistics.median(foot_off),
            "between_mean": statistics.fmean(between) if between else 0.0,
            "between_lit_fraction": (sum(1 for b in between if b > 0) / len(between)) if between else 0.0,
            "pool_r50_m_median": statistics.median(r50) if r50 else None,
            "shoulder_8_14m_mean": statistics.fmean(shoulder) if shoulder else 0.0,
            "road_mean_lit": statistics.fmean(lit) if lit else 0.0,
            "road_lit_samples": len(lit), "road_samples": len(samples)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--new-intensity", type=float, default=None)
    ap.add_argument("--ini-old", type=Path)
    ap.add_argument("--ini-new", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    proj = Path(a.project)
    data = proj / "data"
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    sl = (cfg.get("lighting") or {}).get("streetlight") or {}
    cl = [tuple(p) for p in json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["points_xyz_m"]]
    widths = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))["widths_m"]
    heads = json.loads((data / "lights.local.json").read_text(encoding="utf-8"))["lampheads"]
    old, new = predicted_lights(heads, cl)
    src = "predicted from data/lights.local.json heads"
    if a.ini_old:
        old = ini_lights(a.ini_old)
        src = f"written: {a.ini_old.name}"
    if a.ini_new:
        new = ini_lights(a.ini_new)
        src += f" / {a.ini_new.name}"
    base_i = float(sl.get("intensity", 0.013))
    new_i = a.new_intensity if a.new_intensity is not None else base_i
    report = {"source": src, "settings": {k: sl.get(k) for k in ("intensity", "range_m", "spot_deg", "spot_sharpness",
                                                                  "range_gradient_offset", "diffuse_concentration")},
              "new_intensity": new_i, "height_over_road_m": {}, "fades": {}}
    for fade in ("linear", "quadratic"):
        mo = measure(old, cl, widths, Light(sl), fade)
        mn = measure(new, cl, widths, Light(sl, new_i), fade)
        ratio = {k: (mn[k] / mo[k] if isinstance(mo[k], float) and mo[k] else None)
                 for k in ("under_mean", "between_mean", "shoulder_8_14m_mean", "road_mean_lit")}
        report["fades"][fade] = {"old": mo, "new": mn, "new_over_old": ratio,
                                 "intensity_to_match_under": round(new_i * mo["under_mean"] / mn["under_mean"], 5)
                                 if mn["under_mean"] else None,
                                 "intensity_to_match_road_mean": round(new_i * mo["road_mean_lit"] / mn["road_mean_lit"], 5)
                                 if mn["road_mean_lit"] else None}
        print(f"[pool] {fade:9s} old: under {mo['under_mean']:.5f}  between {mo['between_mean']:.5f} "
              f"(lit {mo['between_lit_fraction']:.0%})  r50 {mo['pool_r50_m_median']} m  road-mean {mo['road_mean_lit']:.5f} "
              f"({mo['road_lit_samples']}/{mo['road_samples']} lit)")
        print(f"[pool] {fade:9s} new: under {mn['under_mean']:.5f}  between {mn['between_mean']:.5f} "
              f"(lit {mn['between_lit_fraction']:.0%})  r50 {mn['pool_r50_m_median']} m  road-mean {mn['road_mean_lit']:.5f} "
              f"({mn['road_lit_samples']}/{mn['road_samples']} lit)   new/old: "
              + ", ".join(f"{k} {v:.3f}" if v is not None else f"{k} -" for k, v in ratio.items()))
        print(f"[pool] {fade:9s} intensity matching under: {report['fades'][fade]['intensity_to_match_under']}, "
              f"road mean: {report['fades'][fade]['intensity_to_match_road_mean']}")
    ys = lambda Ls: statistics.median(L[1] - cl[min(range(len(cl)), key=lambda i: (cl[i][0] - L[0]) ** 2 + (cl[i][2] - L[2]) ** 2)][1] for L in Ls)
    report["height_over_road_m"] = {"old_median": round(ys(old), 3), "new_median": round(ys(new), 3)}
    print(f"[pool] light height over the nearest centreline point, median: old {report['height_over_road_m']['old_median']} m, "
          f"new {report['height_over_road_m']['new_median']} m ({src})")
    if a.json:
        a.json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
