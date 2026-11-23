"""Ledger 0100 item 6, on the BUILT road kn5: each pad mesh's writer vertices per triangle and how far its vertex normals stand
from its own face normals (what the PC reads after a rehearsal; pads_shade_check.py is the Blender A/B before the build).

    python pads_kn5_check.py <road.kn5> [--prefix 1RUNOFF_apron] [--crease-deg 10] [--json out.json]

The kn5's static meshes are read as scripts/modkit/extract_kn5.parse reads them (44 B a vertex: position, normal, uv,
tangent), keeping the normals. Per mesh: vertices, triangles, vertices per triangle (3.0 = flat, every triangle its own
corners; ~0.5 = shared); for every triangle the angle between its face normal (positions, oriented to its vertices' normals)
and each corner's normal, by corner and by area (p50 / p95 / p99), the largest on any face over 10 cm2, and the area share
over 2 deg. The Mac's Blender A/B on 0.1.5's ride pad (records/pads_shade_v015_ride_pad.json): flat 0 deg at 3.0 a triangle;
smooth 0.52 a triangle, by area p95 0.28 / p99 0.95 deg, at most 3.25 deg on a face over 10 cm2.

THE BOUND (ledger 0100 round 1b; a check the PC runs after a rehearsal, NOT a chain gate: tools/ship_track.sh does not run it):
with track.config.json scenery.bespoke.pads_shade_crease_deg c, a corner is shared only among faces within c of each other
(tools/pad_clip.crease_normals), so every corner normal stands within c of its own face. PASS when every pad's largest angle on
a face over 10 cm2 is at most c + TOL_DEG; exit 1 otherwise, naming the pads. TOL_DEG 0.5 [invented] covers float32 positions
on thin faces and the normal's encoding (0.1.13's flat pads read up to 1.71 deg on such slivers, where 0 is exact). Round 1b's
model on 0.1.13's own pads (records/pads_shade_0113_20pads.json, crease10): at most 9.83 deg, p95 at most 4.17 deg; 0.1.14's
pads, shared at every vertex, read up to 117 deg and failed it.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

TOL_DEG = 0.5          # [invented] float32 positions on thin faces + the custom normal's encoding

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from scripts.modkit.extract_kn5 import _IDENT, _Reader  # noqa: E402


def meshes_with_normals(path, prefix):
    d = Path(path).read_bytes()
    if d[:6] != b"sc6969":
        raise SystemExit(f"not a kn5: {path}")
    r = _Reader(d)
    r.o = 6
    if r.i32() > 5:
        r.i32()
    for _ in range(r.i32()):
        r.i32(); r.string()
        size = r.u32()                # (read first: `r.o += r.u32()` loses the u32's own 4 bytes)
        r.o += size
    for _ in range(r.u32()):
        r.string(); r.string(); r.blob(2); r.i32()
        for _ in range(r.u32()):
            r.string(); r.blob(40)
        for _ in range(r.u32()):
            r.string(); r.i32(); r.string()
    out = []

    def node():
        ncls = r.u32(); name = r.string(); kids = r.u32(); r.boolean()
        if ncls == 1:
            r.matrix()
            for _ in range(kids):
                node()
        elif ncls == 2:
            r.boolean(); r.boolean(); r.boolean()
            vc = r.u32()
            if not name.startswith(prefix):
                r.o += vc * 44
                ic = r.u32()
                r.o += ic * 2
            else:
                v = np.frombuffer(d, dtype="<f4", count=vc * 11, offset=r.o).reshape(vc, 11)
                r.o += vc * 44
                ic = r.u32()
                idx = np.frombuffer(d, dtype="<u2", count=ic, offset=r.o).reshape(-1, 3)
                r.o += ic * 2
                out.append({"name": name, "pos": v[:, 0:3].astype(float), "nrm": v[:, 3:6].astype(float), "tri": idx.astype(int)})
            r.u32(); r.u32(); r.f32(); r.f32(); r.blob(16); r.boolean()
            for _ in range(kids):
                node()
        else:
            raise SystemExit(f"node class {ncls} ({name!r}) not read here")
    node()
    return out


def check(m):
    P, N, T = m["pos"], m["nrm"], m["tri"]
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    cr = np.cross(b - a, c - a)
    area = np.linalg.norm(cr, axis=1) / 2
    fn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    vn = N[T]                                                          # (t, 3, 3)
    vn = vn / np.maximum(np.linalg.norm(vn, axis=2, keepdims=True), 1e-12)
    sign = np.sign(np.einsum("tj,tkj->t", fn, vn))
    fn = fn * np.where(sign == 0, 1, sign)[:, None]
    ang = np.degrees(np.arccos(np.clip(np.einsum("tj,tkj->tk", fn, vn), -1, 1)))      # (t, 3)
    w = np.repeat(area / 3, 3)
    flat = ang.ravel()
    o = np.argsort(flat)
    cw = np.cumsum(w[o]) / max(w.sum(), 1e-12)
    by_area = {q: round(float(flat[o][min(len(o) - 1, np.searchsorted(cw, q / 100))]), 3) for q in (50, 95, 99)}
    big = area > 1e-3
    return {"name": m["name"], "vertices": int(len(P)), "triangles": int(len(T)),
            "vertices_per_triangle": round(len(P) / max(1, len(T)), 3),
            "normal_vs_face_deg_by_corner": {q: round(float(np.percentile(flat, q)), 3) for q in (50, 95, 99)},
            "normal_vs_face_deg_by_area": by_area,
            "max_deg_on_faces_over_10cm2": round(float(ang[big].max()) if big.any() else 0.0, 2),
            "area_share_over_2deg_pct": round(100 * float(w[flat > 2].sum() / max(w.sum(), 1e-12)), 4)}


def verdict(rows, crease_deg, tol=TOL_DEG):
    """(PASS?, [pad names over the bound]): every pad's largest corner-to-face angle on a face over 10 cm2 within crease + tol"""
    over = [r["name"] for r in rows if r["max_deg_on_faces_over_10cm2"] > float(crease_deg) + tol]
    return (bool(rows) and not over), over


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kn5")
    ap.add_argument("--prefix", default="1RUNOFF_apron")
    ap.add_argument("--crease-deg", type=float, default=10.0, help="the track's scenery.bespoke.pads_shade_crease_deg")
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = [check(m) for m in meshes_with_normals(a.kn5, a.prefix)]
    tot_v, tot_t = sum(r["vertices"] for r in rows), sum(r["triangles"] for r in rows)
    ok, over = verdict(rows, a.crease_deg)
    rep = {"kn5": Path(a.kn5).name, "prefix": a.prefix, "meshes": len(rows), "vertices": tot_v, "triangles": tot_t,
           "bytes_vertices_44B": 44 * tot_v, "crease_deg": a.crease_deg, "tol_deg": TOL_DEG,
           "verdict": "PASS" if ok else "FAIL", "over": over, "rows": rows}
    print(f"[pads-kn5] {len(rows)} {a.prefix}* meshes: {tot_v} vertices for {tot_t} triangles "
          f"({tot_v / max(1, tot_t):.3f} a triangle, {44 * tot_v} B of vertices)")
    for r in rows:
        print(f"  {r['name']}: {r['vertices']} / {r['triangles']}, normal vs face by area p95 {r['normal_vs_face_deg_by_area'][95]} "
              f"p99 {r['normal_vs_face_deg_by_area'][99]} deg, max {r['max_deg_on_faces_over_10cm2']} deg on faces over 10 cm2")
    print(f"[pads-kn5] {'PASS' if ok else 'FAIL'}: every pad's corner normals within {a.crease_deg:g} + {TOL_DEG} deg of their faces "
          f"(faces over 10 cm2)" + ("" if ok else f"; over: {', '.join(over)}"))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
