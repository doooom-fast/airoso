"""The density row before (06d782f) and after (density_row) on each installed road-wear track's own road, rebuilt from
its records: data/finished_centerline.json (the line the road was swept along, its widths) as a ribbon of quads at the
recorded stations (+ a 1 m edge strip each side), each face in its cell's tile of the recorded plan (road_wear.json
stats.plan, spec.texel_m / layer_m) exactly as the bake maps it (road_wear.uv_of), every number stored as float32 and
v negated, as the kn5 add-on writes them. Not the kn5 (it is on the PC): the triangles the bake maps, at the tracks'
own coordinates and sizes."""
import json, math, struct, sys
from pathlib import Path
A = Path(sys.argv[1]); sys.path.insert(0, str(A / "tools")); sys.path.insert(0, str(A)); sys.path.insert(0, str(A / "tests" / "aerial"))
import numpy as np
import road_wear_check as rwc
from scripts.aerial import road_wear as rw
f32 = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]

def old_row(tris, Aa, tex):
    s0 = 1 / (Aa * tex); off = 0; worst = 0.0; wsh = 0.0
    for (P0, P1, P2), (U0, U1, U2) in tris:
        ex, ey = P1[0] - P0[0], P1[1] - P0[1]; fx, fy = P2[0] - P0[0], P2[1] - P0[1]
        det = ex * fy - ey * fx
        if abs(det) < 1e-6: continue
        du1, dv1 = U1[0] - U0[0], U1[1] - U0[1]; du2, dv2 = U2[0] - U0[0], U2[1] - U0[1]
        j11 = (du1 * fy - du2 * ey) / det; j12 = (du2 * ex - du1 * fx) / det
        j21 = (dv1 * fy - dv2 * ey) / det; j22 = (dv2 * ex - dv1 * fx) / det
        sA = j11**2 + j12**2 + j21**2 + j22**2; dt = abs(j11 * j22 - j12 * j21)
        r = math.sqrt(max(0, sA * sA / 4 - dt * dt)); s1 = math.sqrt(sA / 2 + r); s2 = math.sqrt(max(0, sA / 2 - r))
        d = max(abs(s1 / s0 - 1), abs(s2 / s0 - 1)); sh = (s1 - s2) / s0
        worst = max(worst, d); wsh = max(wsh, sh); off += d > 0.005 or sh > 0.005
    return {"pass": off == 0, "off": off, "worst_scale_err": round(worst, 6), "worst_shear": round(wsh, 6)}

for name, fin, rwj in sys.argv[2:] and [a.split(",") for a in sys.argv[2:]]:
    d = json.load(open(fin)); decl = json.load(open(rwj))
    plan = decl["stats"]["plan"]; spec = decl["spec"]; tex = float(spec["texel_m"]); Aa = int(plan["atlas_px"])
    p = np.array(d["points_xyz_m"], dtype=np.float64); Wd = np.array(d["widths_m"], dtype=np.float64)
    E = p[:, 0]; N = -p[:, 2]; H = p[:, 1]
    n = len(p) - 1 if np.allclose(p[0], p[-1]) else len(p)
    tx = np.roll(E[:n], -1) - np.roll(E[:n], 1); ty = np.roll(N[:n], -1) - np.roll(N[:n], 1)
    ln = np.hypot(tx, ty); nx, ny = -ty / ln, tx / ln
    offs = lambda i: [-(Wd[i] / 2 + 1.0), -Wd[i] / 2, Wd[i] / 2, Wd[i] / 2 + 1.0]
    pts = [[(f32(E[i] + nx[i] * o), f32(N[i] + ny[i] * o)) for o in offs(i)] for i in range(n)]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        for k in range(3):
            a, b, c, e = pts[i][k], pts[i][k + 1], pts[j][k + 1], pts[j][k]
            faces.append(((a, b, c, e), (H[i] + H[j]) / 2))
    cen = np.array([[sum(q[0] for q in f) / 4, sum(q[1] for q in f) / 4] for f, _h in faces])
    keys = rw.cell_keys(cen, np.array([h for _f, h in faces]), plan, spec)
    slots = rw.tile_slots(keys, plan)
    tris = []
    for (quad, _h), kk in zip(faces, keys):
        uv = [rw.uv_of(np.array([q[0]]), np.array([q[1]]), kk, slots[kk], plan, tex) for q in quad]
        U = [(f32(float(u[0][0])), f32(-float(u[1][0]))) for u in uv]
        for t3 in ((0, 1, 2), (0, 2, 3)):
            tris.append((tuple(quad[t] for t in t3), tuple(U[t] for t in t3)))
    o = old_row(tris, Aa, tex); nw = rwc.density_row(tris, Aa, tex)
    print(f"{name}: {len(tris)} triangles (atlas {Aa} px, texel {tex} m, {len(set(keys))} cells)")
    print(f"  before: {o}")
    print(f"  after : pass {nw['pass']}, off {nw['off']}, worst_scale_err {nw['worst_scale_err']}, worst_shear "
          f"{nw['worst_shear']}, jacobian_judged {nw['jacobian_judged']}, edge_judged {nw['edge_judged']} "
          f"(worst {nw['worst_edge_err']}), unjudged {nw['unjudged']}, v_sign {nw['v_sign']}")
    assert o["pass"] == nw["pass"] and o["worst_scale_err"] == nw["worst_scale_err"] or nw["edge_judged"], "verdicts differ"
