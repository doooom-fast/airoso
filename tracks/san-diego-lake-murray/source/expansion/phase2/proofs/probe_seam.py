"""Probe ONE drive_test bump on the built road at millimetre spacing (ledger 0054 Phase 2 step 2g).

drive_test samples a wheel path every STEP_M (1.0 m). A bump that appears or vanishes when the line's stations shift by a
few millimetres (0.20.2's regenerated expansion line moved its stations 7.6 mm at J4 — the line itself is unchanged
there — and a 0.045 m bump appeared at s 4342, lat +3.46) is the sample landing on something narrower than its own
shift: a hairline gap between two decks (the ray reaching the ground pinned 0.02 m under them) or a lip. This walks
the same wheel path every 2 mm over +- 1 m around the bump and reports the top surface (1ROAD / 1KERB / 1GRASS) and its
owner, every change of owner, every jump between neighbouring samples over 5 mm, and the widths of any gap through
which the ground is the top. verify_pads gates the pads' seams at <= 10 mm.

    python probe_seam.py <gate.obj> <drive_lines.json> <line id> <x> <z> <lat> [--half 1.0] [--step 0.002]
                         [--band 0.10]

--band: also walk the paths this far either side of it, every 0.01 m (the bump's x, z carry drive_test's rounding).

x, z: the bump (engine frame, drive_test's steps_at); lat: its lateral off the line (+ = left).
"""
import json
import math
import sys

TOP = ("1ROAD", "1KERB", "1GRASS")


def main(argv):
    pos = [a for a in argv if not a.startswith("--")]
    opt = {argv[i][2:]: float(argv[i + 1]) for i in range(len(argv)) if argv[i].startswith("--")}
    obj, lines_p, lid, x0, z0, lat = pos[0], pos[1], pos[2], float(pos[3]), float(pos[4]), float(pos[5])
    half, step = opt.get("half", 1.0), opt.get("step", 0.002)
    P = json.load(open(lines_p, encoding="utf-8"))["lines"][lid]["points_xyz_m"]
    k = min(range(len(P)), key=lambda i: (P[i][0] - x0) ** 2 + (P[i][2] - z0) ** 2)
    a, b = P[max(0, k - 1)], P[min(len(P) - 1, k + 1)]
    tx, tz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(tx, tz) or 1.0
    tx, tz = tx / L, tz / L
    # the wheel path through the bump, parallel to the line there
    cx, cz = x0, z0
    reach = half + 0.5
    V, tris, cur = [], [], None
    with open(obj, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            t = ln[:2]
            if t == "v ":
                p = ln.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif t in ("o ", "g "):
                nm = ln[2:].strip()
                cur = nm if nm.upper().startswith(TOP) else None
            elif t == "f " and cur is not None:
                idx = [int(q.partition("/")[0]) - 1 for q in ln.split()[1:]]
                for j in range(1, len(idx) - 1):
                    tri = (idx[0], idx[j], idx[j + 1])
                    if all(abs(V[i][0] - cx) <= reach + 30 and abs(V[i][2] - cz) <= reach + 30 for i in tri):
                        tris.append((cur, tri))
    band = opt.get("band", 0.10)
    nb = int(round(band / 0.01))
    report = []
    for lb in range(-nb, nb + 1):
        report.append(walk(V, tris, cx - tz * lb * 0.01, cz + tx * lb * 0.01, tx, tz, half, step, lb * 0.01))
    worst = max(report, key=lambda r: (len(r["ground_on_top_widths_m"]), max([abs(j["dh"]) for j in r["jumps_over_5mm"]] or [0])))
    print(json.dumps({"at": [x0, z0], "lat": lat, "line_vertex": k, "tangent": [round(tx, 4), round(tz, 4)],
                      "paths": len(report), "paths_with_a_gap": sum(1 for r in report if r["ground_on_top_widths_m"]),
                      "paths_with_a_jump": sum(1 for r in report if r["jumps_over_5mm"]),
                      "widest_gap_m": max([w for r in report for w in r["ground_on_top_widths_m"]] or [0.0]),
                      "largest_jump_m": max([abs(j["dh"]) for r in report for j in r["jumps_over_5mm"]] or [0.0]),
                      "worst_path": worst}, indent=1))


def walk(V, tris, cx, cz, tx, tz, half, step, lat_off):
    rows = []
    n = int(round(half / step))
    for q in range(-n, n + 1):
        s = q * step
        x, z = cx + tx * s, cz + tz * s
        best = None
        for name, (i0, i1, i2) in tris:
            (xa, ya, za), (xb, yb, zb), (xc, yc, zc) = V[i0], V[i1], V[i2]
            den = (zb - zc) * (xa - xc) + (xc - xb) * (za - zc)
            if abs(den) < 1e-12:
                continue
            wa = ((zb - zc) * (x - xc) + (xc - xb) * (z - zc)) / den
            wb = ((zc - za) * (x - xc) + (xa - xc) * (z - zc)) / den
            wc = 1.0 - wa - wb
            if min(wa, wb, wc) < -1e-9:
                continue
            h = wa * ya + wb * yb + wc * yc
            if best is None or h > best[0]:
                best = (h, name)
        rows.append((round(s, 4), None if best is None else round(best[0], 4), None if best is None else best[1]))
    changes = [(r0, r1) for r0, r1 in zip(rows, rows[1:]) if r0[2] != r1[2]]
    jumps = [(r0, r1) for r0, r1 in zip(rows, rows[1:]) if r0[1] is not None and r1[1] is not None
             and abs(r1[1] - r0[1]) > 0.005]
    gaps, run = [], None
    for r in rows:
        ground = r[2] is None or r[2].upper().startswith("1GRASS")
        if ground and run is None:
            run = [r[0], r[0]]
        elif ground:
            run[1] = r[0]
        elif run is not None:
            gaps.append(run)
            run = None
    if run is not None:
        gaps.append(run)
    return {"lateral_off_m": round(lat_off, 3), "samples": len(rows), "step_m": step, "owners": sorted({r[2] for r in rows if r[2]}),
                      "owner_changes": [{"s": c[1][0], "from": c[0][2], "to": c[1][2], "dh": None if None in (c[0][1], c[1][1])
                                         else round(c[1][1] - c[0][1], 4)} for c in changes],
                      "jumps_over_5mm": [{"s": j[1][0], "dh": round(j[1][1] - j[0][1], 4), "owners": [j[0][2], j[1][2]]}
                                         for j in jumps],
            "ground_on_top_widths_m": [round(g[1] - g[0] + step, 4) for g in gaps]}


if __name__ == "__main__":
    main(sys.argv[1:])
