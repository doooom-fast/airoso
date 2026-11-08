"""How smooth the BUILT road's edges are: the 1ROAD boundary and the edge strip's outer lip (ledger 0087).

Kevin, 2026-11-07: "Some of the curves and straights on Milford and sand creek have messy edges ... Milford should very
smooth edges and they're ragged in places." edge_report reads what stands beside the lane; this reads the lane's own
outline. Stdlib only (the PC's python runs it as a gate).

For each reference line (the gate centre line; with --connectors also every connector in data/connectors.local.json,
smoothed as the assembler smooths them) and each side, every ``--step`` m (1 m) a ray is cast from the line along its
plan normal and the built boundary crossings are read off the OBJ:
  road   the first 1ROAD boundary crossing past 0.3 x the half width (the lane edge)
  strip  the first 1KERB_SIDEWALK / CURB boundary crossing past the lane edge (the strip's outer lip)
That gives d(s), the edge's offset from the line, at 1 m. A built edge that is a clean offset curve has d(s) smooth,
whatever the line's curvature. Two measures per edge sample:
  d2      d(s-1) - 2 d(s) + d(s+1)                         the 1 m second difference (a notch or a kink)
  resid   d(s) - fit(s)                                     against a robust local-quadratic fit of d over +-FIT_HALF_M
                                                            (tricube kernel, Tukey bisquare reweighting, ROBUST_ITERS)
A sample whose road edge sits more than FLARE_M off the line's own half width is a mouth, pad or flare: counted, never
judged. A side with no crossing (an open mouth) is "open".

Ragged stretches: samples with |resid| > RAGGED_RESID_M or |d2| > RAGGED_D2_M, merged across gaps <= MERGE_GAP_M, each
with its station range, side, worst resid / d2 and its world position (for stills and for the imagery check).

    python tools/edge_smoothness.py <project-dir> [--obj <track.obj>] [--line <gate_centerline.json>] [--connectors]
                                    [--json <summary out>] [--lines <every sample out>]
                                    [--gate <thresholds.json>|--gate-default] [--quiet]

--gate: exit 1 when a side's p99 |d2| or p99 |resid| (lane edge, judged samples) is over the thresholds, or the count of
ragged stretches is (thresholds: tools/edge_smoothness.py GATE_DEFAULT, or a JSON {"d2_p99_m", "resid_p99_m",
"ragged_runs_max"}). Without --gate it is a report (exit 0).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROAD_PREFIX = ("1ROAD",)
ROAD_SKIP = ("1ROAD_SHOULDER",)
STRIP_PREFIX = ("1KERB_SIDEWALK", "CURB")
STEP_M = 1.0                 # the sample spacing along the line: Kevin's "1 m second difference"
FLARE_M = 1.5                # [invented] a lane edge this far off the line's half width is a mouth / pad / flare, not judged
INNER_FRAC = 0.3             # crossings nearer the line than 0.3 x half width are an island / median, not the lane edge
REACH_M = 6.0                # rays reach the half width + this
FIT_HALF_M = 8.0             # [invented] the fit's half window: a real width change (a 0.1 m/m taper) takes longer than this
ROBUST_ITERS = 3
RAGGED_RESID_M = 0.05        # [measured on Milford 0.1.2's cleanest straights, ledger 0087 §1: p99.9 under 2 cm]
RAGGED_D2_M = 0.04           # [measured: the facet sag of a 1.5 m row on the R 15 m hairpin's inner edge is ~2 cm]
MERGE_GAP_M = 4.0
GATE_DEFAULT = {"d2_p99_m": 0.02, "resid_p99_m": 0.012, "ragged_runs_max": 0,
                "_doc": "ledger 0087 §4 (opt-in) ⚠ [a mirror: calibrated on our own output, Milford 0.1.4 = Mac c5's built "
                        "lane edge, so a no-regression bar, not a measured envelope (GATES-CHANGELOG)]: a side's p99 may not "
                        "pass what 0.1.4 reaches at its single worst sample (d2 max 0.0200 m, resid max 0.0111 m; its p99 is "
                        "0.0122 / 0.0039 m); 0.1.2's staircase (p99 0.045 / 0.084 m) fails; 0 ragged stretches as on c5"}
BUCKET = 4.0


# ------------------------------------------------------------------------------------------------- the OBJ boundary
def _matches(name: str, pre, skip=()) -> bool:
    u = name.upper()
    return u.startswith(pre) and not u.startswith(skip) and "RACE" not in u and "STREETONLY" not in u


def read_boundaries(obj_path: Path):
    """{'road': [((x0,z0),(x1,z1)), ...], 'strip': [...]}: plan segments on exactly one triangle of their kind (the
    vertices welded at 1 mm, so split normals / UV seams do not read as boundary)."""
    V = []
    cur = None
    edges = {"road": {}, "strip": {}}
    key_of = {}
    with open(obj_path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            c = ln[:2]
            if c == "v ":
                p = ln.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif c in ("g ", "o "):
                t = ln.split()
                nm = t[1] if len(t) > 1 else ""
                cur = "road" if _matches(nm, ROAD_PREFIX, ROAD_SKIP) else "strip" if _matches(nm, STRIP_PREFIX) else None
            elif c == "f " and cur is not None:
                ids = [int(t.split("/")[0]) for t in ln.split()[1:]]
                ids = [i - 1 if i > 0 else len(V) + i for i in ids]
                ks = []
                for i in ids:
                    k = key_of.get(i)
                    if k is None:
                        x, _y, z = V[i]
                        k = key_of[i] = (round(x * 1000), round(z * 1000))
                    ks.append(k)
                E = edges[cur]
                for a, b in zip(ks, ks[1:] + ks[:1]):
                    if a == b:
                        continue
                    e = (a, b) if a < b else (b, a)
                    E[e] = E.get(e, 0) + 1
    out = {}
    for kind, E in edges.items():
        out[kind] = [((a[0] / 1000, a[1] / 1000), (b[0] / 1000, b[1] / 1000)) for (a, b), n in E.items() if n == 1]
    return out


class SegIndex:
    def __init__(self, segs):
        self.b: dict = {}
        for s in segs:
            (x0, z0), (x1, z1) = s
            for bx in range(int(math.floor(min(x0, x1) / BUCKET)), int(math.floor(max(x0, x1) / BUCKET)) + 1):
                for bz in range(int(math.floor(min(z0, z1) / BUCKET)), int(math.floor(max(z0, z1) / BUCKET)) + 1):
                    self.b.setdefault((bx, bz), []).append(s)

    def crossings(self, ox, oz, nx, nz, t0, t1):
        """sorted ray parameters t in [t0, t1] where the ray o + t n crosses a segment"""
        seen, out = set(), []
        steps = int((t1 - t0) / (BUCKET * 0.5)) + 2
        for k in range(steps + 1):
            t = t0 + (t1 - t0) * k / steps
            key = (int(math.floor((ox + nx * t) / BUCKET)), int(math.floor((oz + nz * t) / BUCKET)))
            for s in self.b.get(key, ()):
                if id(s) in seen:
                    continue
                seen.add(id(s))
                (x0, z0), (x1, z1) = s
                ex, ez = x1 - x0, z1 - z0
                den = nx * ez - nz * ex
                if abs(den) < 1e-12:
                    continue
                wx, wz = x0 - ox, z0 - oz
                tt = (wx * ez - wz * ex) / den
                u = (wx * nz - wz * nx) / den
                if -1e-9 <= u <= 1 + 1e-9 and t0 <= tt <= t1:
                    out.append(tt)
        return sorted(out)


# ------------------------------------------------------------------------------------------------- the reference lines
def resample(points, widths, step):
    """(s, x, z, w, tx, tz) every ``step`` m along a polyline, linear in x/z/width; tangents from +-1 step"""
    P = [(p[0], p[2]) for p in points]
    st = [0.0]
    for a, b in zip(P, P[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = st[-1]
    rows, j = [], 0
    n = int(L // step)
    for k in range(n + 1):
        s = k * step
        while j < len(st) - 2 and st[j + 1] < s:
            j += 1
        seg = (st[j + 1] - st[j]) or 1e-9
        f = min(1.0, max(0.0, (s - st[j]) / seg))
        x = P[j][0] + (P[j + 1][0] - P[j][0]) * f
        z = P[j][1] + (P[j + 1][1] - P[j][1]) * f
        w = widths[j] + (widths[j + 1] - widths[j]) * f
        rows.append([s, x, z, w])
    out = []
    for i, (s, x, z, w) in enumerate(rows):
        a, b = rows[max(0, i - 1)], rows[min(len(rows) - 1, i + 1)]
        tx, tz = b[1] - a[1], b[2] - a[2]
        Lt = math.hypot(tx, tz) or 1.0
        out.append((s, x, z, w, tx / Lt, tz / Lt))
    return out


def reference_lines(proj: Path, line_path: Path | None, connectors: bool):
    lines = []
    lp = line_path or proj / "data" / "gate_centerline.json"
    g = json.loads(lp.read_text(encoding="utf-8"))
    lines.append(("mainline", g["points_xyz_m"], g["widths_m"]))
    if connectors and (proj / "data" / "connectors.local.json").exists():
        import importlib.util
        here = Path(__file__).resolve().parents[1]
        f = here / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py"
        sm = None
        if f.exists():                          # the assembler's own smoothing of a connector (sigma 1.5, one pass)
            spec = importlib.util.spec_from_file_location("_lm_smooth", f)
            sm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sm)
        cd = json.loads((proj / "data" / "connectors.local.json").read_text(encoding="utf-8"))
        for c in cd.get("connectors", []):
            pts = [tuple(p) for p in c["points_xyz_m"]]
            if len(pts) < 4:
                continue
            if sm is not None:
                pts = sm.smooth_centerline(pts, sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
            lines.append((c["name"], pts, list(c["widths_m"])))
    return lines


# ------------------------------------------------------------------------------------------------- the fit
def robust_fit(s, d, half=FIT_HALF_M, iters=ROBUST_ITERS):
    """robust local-quadratic (LOESS) fit of d(s): tricube in station, Tukey bisquare on the residual (6 x MAD)"""
    n = len(s)
    rw = [1.0] * n
    fit = list(d)
    for it in range(iters + 1):
        lo = 0
        for i in range(n):
            while s[i] - s[lo] > half:
                lo += 1
            S = [0.0] * 5
            T = [0.0] * 3
            j = lo
            while j < n and s[j] - s[i] <= half:
                u = (s[j] - s[i]) / half
                w = (1 - abs(u) ** 3) ** 3 * rw[j]
                if w > 0:
                    x = s[j] - s[i]
                    xp = 1.0
                    for k in range(5):
                        S[k] += w * xp
                        if k < 3:
                            T[k] += w * xp * d[j]
                        xp *= x
                j += 1
            # solve the 3x3 normal equations for the value at x = 0
            A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
            fit[i] = _solve0(A, T, d[i])
        if it == iters:
            break
        r = sorted(abs(a - b) for a, b in zip(d, fit))
        mad = r[len(r) // 2] or 1e-4
        c = 6.0 * max(mad, 0.002)
        rw = [(1 - ((a - b) / c) ** 2) ** 2 if abs(a - b) < c else 0.0 for a, b in zip(d, fit)]
    return fit


def _solve0(A, b, default):
    import copy
    M = copy.deepcopy(A)
    v = list(b)
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return default
        M[c], M[p] = M[p], M[c]
        v[c], v[p] = v[p], v[c]
        for r in range(c + 1, 3):
            f = M[r][c] / M[c][c]
            for k in range(c, 3):
                M[r][k] -= f * M[c][k]
            v[r] -= f * v[c]
    x = [0.0] * 3
    for c in (2, 1, 0):
        x[c] = (v[c] - sum(M[c][k] * x[k] for k in range(c + 1, 3))) / M[c][c]
    return x[0]


# ------------------------------------------------------------------------------------------------- measure
def measure_line(name, pts, widths, idx_road, idx_strip, step=STEP_M):
    rows = resample(pts, widths, step)
    closed = math.hypot(pts[0][0] - pts[-1][0], pts[0][2] - pts[-1][2]) < 1e-3
    sides = {}
    for side, sg in (("left", 1.0), ("right", -1.0)):
        ser = []
        for s, x, z, w, tx, tz in rows:
            nx, nz = -tz * sg, tx * sg
            hw = w / 2.0
            cr = idx_road.crossings(x, z, nx, nz, INNER_FRAC * hw, hw + REACH_M)
            d = cr[0] if cr else None
            st = None
            if d is not None and idx_strip is not None:
                cs = [t for t in idx_strip.crossings(x, z, nx, nz, d - 0.3, d + REACH_M) if t > d + 0.05]
                st = cs[0] if cs else None
            state = "open" if d is None else ("flare" if abs(d - hw) > FLARE_M else "edge")
            ser.append({"s": round(s, 2), "x": round(x + nx * (d or hw), 3), "z": round(z + nz * (d or hw), 3),
                        "hw": round(hw, 3), "d": None if d is None else round(d, 4),
                        "strip": None if st is None else round(st, 4), "state": state})
        for key in ("d", "strip"):
            _metrics(ser, key, closed)
        sides[side] = ser
    return {"name": name, "closed": closed, "length_m": rows[-1][0] if rows else 0.0, "sides": sides}


def _metrics(ser, key, closed):
    """per sample: d2_<key> and resid_<key>, on the runs of consecutive judged samples ('edge' state)"""
    n = len(ser)
    ok = [ser[i]["state"] == "edge" and ser[i][key] is not None for i in range(n)]
    # runs of consecutive ok samples (wrapping on a closed line)
    runs, i = [], 0
    while i < n:
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and ok[j + 1]:
            j += 1
        runs.append(list(range(i, j + 1)))
        i = j + 1
    if closed and len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == n - 1:
        runs[0] = runs[-1] + runs[0]
        runs.pop()
    elif closed and len(runs) == 1 and len(runs[0]) == n:
        pass
    for run in runs:
        if len(run) < 5:
            continue
        ring = closed and len(run) == n
        dv = [ser[k][key] for k in run]
        sv = []
        acc = 0.0
        for a, k in enumerate(run):
            sv.append(acc)
            acc += STEP_M
        if ring:   # pad the ring so the fit wraps
            pad = int(FIT_HALF_M / STEP_M) + 1
            dvp = dv[-pad:] + dv + dv[:pad]
            svp = [(-pad + a) * STEP_M for a in range(len(dvp))]
            fit = robust_fit(svp, dvp)[pad:pad + len(dv)]
        else:
            fit = robust_fit(sv, dv)
        for a, k in enumerate(run):
            ser[k]["fit_" + key] = round(fit[a], 4)
            ser[k]["resid_" + key] = round(dv[a] - fit[a], 4)
            if ring or 0 < a < len(run) - 1:
                pa, nb = dv[(a - 1) % len(dv)], dv[(a + 1) % len(dv)]
                ser[k]["d2_" + key] = round(pa - 2 * dv[a] + nb, 4)


def q(v, f):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(f * len(v)))], 4) if v else None


def ragged_runs(line, key="d", resid_m=RAGGED_RESID_M, d2_m=RAGGED_D2_M, gap=MERGE_GAP_M):
    out = []
    for side, ser in line["sides"].items():
        bad = [r for r in ser if abs(r.get("resid_" + key) or 0) > resid_m or abs(r.get("d2_" + key) or 0) > d2_m]
        cur = None
        for r in bad:
            if cur and r["s"] - cur["s1"] <= gap:
                cur["s1"] = r["s"]
                cur["n"] += 1
                cur["resid_max"] = max(cur["resid_max"], abs(r.get("resid_" + key) or 0))
                cur["d2_max"] = max(cur["d2_max"], abs(r.get("d2_" + key) or 0))
                if abs(r.get("resid_" + key) or 0) >= cur["resid_max"]:
                    cur["x"], cur["z"], cur["s_worst"] = r["x"], r["z"], r["s"]
            else:
                if cur:
                    out.append(cur)
                cur = {"line": line["name"], "side": side, "kind": key, "s0": r["s"], "s1": r["s"], "n": 1,
                       "resid_max": abs(r.get("resid_" + key) or 0), "d2_max": abs(r.get("d2_" + key) or 0),
                       "x": r["x"], "z": r["z"], "s_worst": r["s"]}
        if cur:
            out.append(cur)
    for r in out:
        r["resid_max"] = round(r["resid_max"], 3)
        r["d2_max"] = round(r["d2_max"], 3)
    return out


def summarise(lines, key="d"):
    out = {}
    for side in ("left", "right"):
        R = [r for ln in lines for r in ln["sides"][side]]
        d2 = [abs(r["d2_" + key]) for r in R if r.get("d2_" + key) is not None]
        rs = [abs(r["resid_" + key]) for r in R if r.get("resid_" + key) is not None]
        out[side] = {"samples": len(R), "judged": len(rs),
                     "flare": sum(1 for r in R if r["state"] == "flare"), "open": sum(1 for r in R if r["state"] == "open"),
                     "d2_m": {"p50": q(d2, .5), "p95": q(d2, .95), "p99": q(d2, .99), "max": q(d2, 1.0)},
                     "resid_m": {"p50": q(rs, .5), "p95": q(rs, .95), "p99": q(rs, .99), "max": q(rs, 1.0)}}
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    def opt(flag, default=None, has_val=True):
        if flag in argv:
            i = argv.index(flag)
            if has_val:
                v = argv[i + 1]
                del argv[i:i + 2]
                return v
            del argv[i]
            return True
        return default
    obj = opt("--obj")
    line = opt("--line")
    conn = opt("--connectors", False, False)
    out = opt("--json")
    lines_out = opt("--lines")
    gate = opt("--gate")
    gate_def = opt("--gate-default", False, False)
    quiet = opt("--quiet", False, False)
    if len(argv) != 1:
        print(__doc__)
        return 2
    proj = Path(argv[0])
    objp = Path(obj) if obj else proj / "data" / "track.obj"
    B = read_boundaries(objp)
    ir = SegIndex(B["road"])
    ist = SegIndex(B["strip"]) if B["strip"] else None
    lines = [measure_line(n, p, w, ir, ist) for n, p, w in reference_lines(proj, Path(line) if line else None, conn)]
    runs = [r for ln in lines for k in ("d", "strip") for r in ragged_runs(ln, k)]
    rep = {"_doc": "tools/edge_smoothness.py, ledger 0087: the built road edge's 1 m second difference and residual to a "
                   "robust fit, per side", "obj": str(objp), "step_m": STEP_M,
           "thresholds": {"FLARE_M": FLARE_M, "FIT_HALF_M": FIT_HALF_M, "RAGGED_RESID_M": RAGGED_RESID_M,
                          "RAGGED_D2_M": RAGGED_D2_M},
           "boundary_segments": {k: len(v) for k, v in B.items()},
           "lane_edge": summarise(lines, "d"), "strip_outer": summarise(lines, "strip"),
           "ragged_runs": {"lane_edge": sum(1 for r in runs if r["kind"] == "d"),
                           "strip_outer": sum(1 for r in runs if r["kind"] == "strip")},
           "worst_runs": sorted(runs, key=lambda r: -r["resid_max"])[:40]}
    verdict = 0
    if gate or gate_def:
        th = dict(GATE_DEFAULT)
        if gate:
            th.update(json.loads(Path(gate).read_text(encoding="utf-8")))
        fails = []
        for side, m in rep["lane_edge"].items():
            if m["d2_m"]["p99"] is not None and m["d2_m"]["p99"] > th["d2_p99_m"]:
                fails.append(f"{side} lane edge p99 |d2| {m['d2_m']['p99']} > {th['d2_p99_m']}")
            if m["resid_m"]["p99"] is not None and m["resid_m"]["p99"] > th["resid_p99_m"]:
                fails.append(f"{side} lane edge p99 |resid| {m['resid_m']['p99']} > {th['resid_p99_m']}")
        if rep["ragged_runs"]["lane_edge"] > th["ragged_runs_max"]:
            fails.append(f"{rep['ragged_runs']['lane_edge']} ragged lane-edge stretches > {th['ragged_runs_max']}")
        rep["gate"] = {"thresholds": th, "fails": fails, "verdict": "FAIL" if fails else "PASS"}
        verdict = 1 if fails else 0
    if out:
        Path(out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    if lines_out:
        full = dict(rep)
        full["lines"] = lines
        Path(lines_out).write_text(json.dumps(full), encoding="utf-8")
    if not quiet:
        print("[edges] " + json.dumps({k: rep[k] for k in ("boundary_segments", "lane_edge", "strip_outer", "ragged_runs")}))
        for r in rep["worst_runs"][:12]:
            print(f"[edges]   {r['line']} {r['side']:5s} {r['kind']:5s} s {r['s0']:.0f}-{r['s1']:.0f}  n {r['n']}  "
                  f"resid {r['resid_max'] * 100:.1f} cm  d2 {r['d2_max'] * 100:.1f} cm  at ({r['x']:.1f}, {r['z']:.1f})")
        if "gate" in rep:
            print(f"[edges] gate {rep['gate']['verdict']}: " + ("; ".join(rep["gate"]["fails"]) or "every row under"))
    return verdict


if __name__ == "__main__":
    raise SystemExit(main())
