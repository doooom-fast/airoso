"""Road wear on the BUILT road kn5 (ledger 0084): the gate tools/road_wear_blend.py's bake answers to.

READ FROM THE SHIPPED ARTIFACT (L5): the kn5's road-wear materials (shader, slots, VARs), its embedded textures, and its
road-wear meshes' world positions and UVs. The declarations it is judged against are data/road_wear.json (which
materials, the texel, the amplitude) and data/road_wear.line.<layout>.json (where the line was declared); the aerial is
read again from the track's own image (track.config.json road_wear.aerial).

    rows (every one must pass; thresholds in GATE, logged in fleet/GATES-CHANGELOG.md 2026-11-09):
    materials    every declared material is in the kn5 with shader ksPerPixelMultiMap_NMDetail, the four slots
                 txDiffuse / txNormal / txDetail / txNormalDetail, each texture embedded, power of two, and
                 detailUVMultiplier = atlas_px * texel_m / detail_tile_m
    density      per triangle, the UV Jacobian over the ground (east, north) has both singular values within
                 density_tol of 1 / (atlas_px * texel_m) and no shear (roundness): one texel per texel_m, square
    no_repeat    no texel is claimed by two places on the ground more than repeat_m apart (corners and centroids of
                 every triangle): the atlas never repeats
    detail_phase the detail UV (UV x detailUVMultiplier) at every vertex equals east / 4, north / 4 modulo 1 within
                 phase_tol tiles: the grain is today's 4 m grid at today's phase, seams included
    tone         Pearson r between the shipped atlas and the aerial's luminance at triangle centroids off the line
                 (no rubber declared there) >= tone_r_min: the macro follows the photograph
    rubber       the mean cross-line profile of the shipped atlas at the line's high-rubber stations is darkest on the
                 declared line: its darkening centroid within line_offset_max_m of it, its depth within
                 [depth_min_frac, depth_max_frac] of the declared amplitude x rubber x tyre profile
    (only when data/road_wear.json carries "kerbs", i.e. the config names road_wear.kerbs; High Plains 0.1.7:)
    kerb_materials every declared kerb material is in the kn5 with its declared shader, the declared slots and textures
                 (the exporter's stock row with txDiffuse -> the levelled paint), each embedded, power of two, and
                 every declared VAR at its value
    kerb_paint   the shipped levelled paint is ``levels`` copies of the kerb's own paint side by side: copy 0 byte for
                 byte, copy k within kerb_paint_tol of round(paint x (1 - k step))
    kerb_levels  every shipped kerb triangle has one level (floor(u x levels)) at its three corners and lies inside a
                 declared face of that level; every declared face's level is the gate's own reading of the declared
                 line's rubber at its centroid within kerb_level_tol levels

Exit 1 when a row fails, 0 when all pass, 2 on an input error. Pure python + PIL (no numpy: the PC's interpreter).

    python tools/road_wear_check.py <proj> --kn5 <road.kn5> [--json <out>]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.modkit.extract_kn5 import parse, _world_verts  # noqa: E402

GATE = {
    "density_tol": 0.005,        # [invented] float32 UVs at 4096 px hold 1e-6; 0.5 % is a construction error, not rounding
    "shear_tol": 0.005,          # [invented]
    "repeat_m": 0.75,            # [invented] three texels at 0.25 m
    "phase_tol": 0.002,          # [invented] tiles (8 mm at 4 m)
    "tone_r_min": 0.60,          # [invented] the macro must follow the photo (the bake's own r is ~0.9)
    "line_offset_max_m": 0.15,   # [invented, ledger 0084's plan]
    "depth_min_frac": 0.5,       # [invented]
    "depth_max_frac": 1.5,       # [invented]
    # the race kerbs (opt-in road_wear.kerbs; High Plains 0.1.7)
    "kerb_paint_tol": 1,         # 8-bit rounding: a copy may differ from round(paint x (1 - k step)) by one level
    "kerb_level_tol": 0.55,      # [invented] levels: half a level (the rounding) + 5 % for the declared line's
                                 # 1 mm / 1e-4 rounding in road_wear.line.<layout>.json
}
SLOTS = ("txDiffuse", "txNormal", "txDetail", "txNormalDetail")


def materials_with_props(path: Path) -> list[dict]:
    """The kn5's material table with its VARs (extract_kn5.parse skips them)."""
    d = path.read_bytes()
    o = [10 if struct.unpack_from("<i", d, 6)[0] <= 5 else 14]

    def i32():
        v = struct.unpack_from("<i", d, o[0])[0]; o[0] += 4; return v

    def s():
        n = i32(); v = d[o[0]:o[0] + n].decode("utf-8", "replace"); o[0] += n; return v
    for _ in range(i32()):
        i32(); s(); size = i32(); o[0] += size     # not `o[0] += i32()`: that adds to the offset read before the size
    mats = []
    for _ in range(i32()):
        name = s(); shader = s(); o[0] += 2; i32()
        props = {}
        for _ in range(i32()):
            pn = s(); vals = struct.unpack_from("<10f", d, o[0]); o[0] += 40
            props[pn] = vals[0]
        slots = []
        for _ in range(i32()):
            sn = s(); i32(); tn = s(); slots.append((sn, tn))
        mats.append({"name": name, "shader": shader, "props": props, "textures": slots})
    return mats


def _img_size(blob: bytes):
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", blob[16:24])
    try:
        from PIL import Image
        return Image.open(io.BytesIO(blob)).size
    except Exception:
        return None


def tyre_profile(u: float, track_m: float, spread_m: float) -> float:
    """scripts/aerial/road_wear.tyre_profile, restated (this gate imports no numpy)."""
    h = 0.5 * track_m; s2 = 2 * spread_m ** 2
    peak = 1.0 + math.exp(-((2 * h) ** 2) / s2)
    if spread_m > h:
        peak = max(peak, 2 * math.exp(-(h * h) / s2))
    return (math.exp(-((u - h) ** 2) / s2) + math.exp(-((u + h) ** 2) / s2)) / peak


def _pip(x: float, y: float, ring) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def make_darkness(line_pts: list, closed: bool, w: dict, layer: float, amp: float):
    """The gate's own reading of the declared lines' rubber (scripts/aerial/road_wear.wear_at restated without numpy):
    darkness(x, y, z) = 1 - prod over the lines of (1 - amp x rubber x tyre_profile(distance to the line))."""
    reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
    segs = {}
    for li, (pts, rub) in enumerate(line_pts):
        n = len(pts)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            segs.setdefault((int(pts[i][0] // 8), int(pts[i][1] // 8)), []).append((li, pts[i], pts[j], rub[i], rub[j]))

    def darkness(x, y, z):
        keep = 1.0
        for li in range(len(line_pts)):
            best = (1e18, 0.0)
            for ci in range(int(x // 8) - 1, int(x // 8) + 2):
                for cj in range(int(y // 8) - 1, int(y // 8) + 2):
                    for (lj, a_, b_, ia, ib) in segs.get((ci, cj), ()):
                        if lj != li or (len(a_) > 2 and abs(a_[2] - z) >= layer):
                            continue
                        ex, ey = b_[0] - a_[0], b_[1] - a_[1]
                        l2 = max(ex * ex + ey * ey, 1e-12)
                        t = min(1.0, max(0.0, ((x - a_[0]) * ex + (y - a_[1]) * ey) / l2))
                        d = math.hypot(x - a_[0] - t * ex, y - a_[1] - t * ey)
                        if d < best[0]:
                            best = (d, ia * (1 - t) + ib * t)
            if best[0] <= reach:
                keep *= 1.0 - amp * best[1] * tyre_profile(best[0], w["track_m"], w["spread_m"])
        return 1.0 - keep

    return darkness


def kerb_rows(proj: Path, cfg: dict, decl: dict, kd: dict, mats: list, p: dict, line_pts: list, w: dict) -> dict:
    """The race kerbs (road_wear.kerbs): their materials as declared, the shipped levelled paint against the kerb's own
    paint, and every shipped kerb triangle's level against the rubber the declared line puts on its face."""
    from PIL import Image
    out = {}
    L = int(kd["levels"]); step = float(kd["step"]); amp = float(kd["amplitude"])
    by_name = {m["name"]: m for m in mats}
    bad = []
    for mn in kd["materials"]:
        row = decl["materials"][mn]
        m = by_name.get(mn)
        if m is None:
            bad.append(f"{mn}: not in the kn5"); continue
        if m["shader"] != row["shader"]:
            bad.append(f"{mn}: shader {m['shader']} != {row['shader']}")
        want = [(t[0], t[1]) for t in row["textures"]]
        if [tuple(t) for t in m["textures"]] != want:
            bad.append(f"{mn}: textures {m['textures']} != {want}")
        for sl, tn in want:
            blob = p["textures"].get(tn)
            sz = _img_size(blob) if blob else None
            if not blob:
                bad.append(f"{mn}: {sl} {tn} not embedded")
            elif not sz or any(v & (v - 1) for v in sz):
                bad.append(f"{mn}: {sl} {tn} {sz} not a power of two")
        for pn, pv in (row.get("props") or {}).items():
            kv = m["props"].get(pn)
            if kv is None or abs(kv - float(pv)) > 1e-3:
                bad.append(f"{mn}: {pn} {kv} != declared {pv}")
    out["kerb_materials"] = {"pass": not bad, "materials": len(kd["materials"]), "problems": bad}

    # the shipped levelled paint: copy 0 is the kerb's own paint byte for byte, copy k = round(paint x (1 - k step)) +- 1
    bad = []
    for src_name, rec in kd["paint"].items():
        blob = p["textures"].get(rec["atlas"])
        src = Path(rec["source"])
        if not src.is_absolute() or not src.exists():
            src = proj / "textures" / src_name
        if not blob or not src.exists():
            bad.append(f"{rec['atlas']}: not embedded or its paint {src} missing"); continue
        a = Image.open(io.BytesIO(blob)).convert("RGB"); b = Image.open(src).convert("RGB")
        (aw, ah), (bw, bh) = a.size, b.size
        if (aw, ah) != (bw * L, bh):
            bad.append(f"{rec['atlas']}: {aw} x {ah} != {L} x the paint's {bw} x {bh}"); continue
        A_ = a.tobytes(); B_ = b.tobytes()
        worst = 0
        for k in range(L):
            f = 1.0 - k * step
            for y in range(0, bh, max(1, bh // 64)):
                for x in range(bw):
                    o_a = 3 * (y * aw + k * bw + x); o_b = 3 * (y * bw + x)
                    for c in range(3):
                        e = abs(A_[o_a + c] - round(B_[o_b + c] * f))
                        if k == 0 and e:
                            worst = max(worst, 99)
                        worst = max(worst, e)
        if worst > GATE["kerb_paint_tol"]:
            bad.append(f"{rec['atlas']}: a copy is {worst} off the paint x (1 - k step)" if worst < 99 else
                       f"{rec['atlas']}: copy 0 is not the paint")
    out["kerb_paint"] = {"pass": not bad, "levels": L, "step": round(step, 5), "problems": bad}

    # every shipped kerb triangle: one level at all three corners, inside a declared face of that level; every declared
    # face's level the gate's own reading of the declared line's rubber at its centroid (within half a level + 5 %)
    darkness = make_darkness(line_pts, bool(cfg.get("loop", True)), w, float(decl["spec"].get("layer_m", 10.0)), amp)

    faces = []
    fh = {}
    for on, fs in kd["faces"].items():
        for f in fs:
            fi = len(faces); faces.append(f)
            xs = [q[0] for q in f["ring"]]; ys = [q[1] for q in f["ring"]]
            for ci in range(int(min(xs) // 4), int(max(xs) // 4) + 1):
                for cj in range(int(min(ys) // 4), int(max(ys) // 4) + 1):
                    fh.setdefault((ci, cj), []).append(fi)
    off_line = 0; worst_lv = 0.0
    for f in faces:
        e = abs(darkness(*f["c"]) / step - f["level"]) if f["level"] < L - 1 else 0.0
        worst_lv = max(worst_lv, e)
        if e > GATE["kerb_level_tol"]:
            off_line += 1
    tris = 0; split = 0; unmatched = 0; wrong = 0
    kerb_mat_ids = {i for i, m in enumerate(mats) if m["name"] in kd["materials"]}
    for me in p["meshes"]:
        if me["matid"] not in kerb_mat_ids:
            continue
        V = _world_verts(me); idx = me["idx"]
        for t in range(0, len(idx), 3):
            c3 = [V[idx[t]], V[idx[t + 1]], V[idx[t + 2]]]
            tris += 1
            lv = {int(math.floor(q[3] * L)) for q in c3}
            if len(lv) != 1:
                split += 1; continue
            x = sum(q[0] for q in c3) / 3; y = -sum(q[2] for q in c3) / 3; z = sum(q[1] for q in c3) / 3
            hit = None
            for fi in fh.get((int(x // 4), int(y // 4)), ()):
                f = faces[fi]
                if abs(f["c"][2] - z) < 1.0 and _pip(x, y, f["ring"]):
                    hit = f; break
            if hit is None:
                unmatched += 1
            elif hit["level"] != next(iter(lv)):
                wrong += 1
    lv_count = [0] * L
    for f in faces:
        lv_count[f["level"]] += 1
    out["kerb_levels"] = {"pass": tris > 0 and split == 0 and unmatched == 0 and wrong == 0 and off_line == 0,
                          "triangles": tris, "corners_in_two_levels": split, "outside_every_declared_face": unmatched,
                          "level_not_its_face": wrong, "faces": len(faces), "faces_off_the_line_rubber": off_line,
                          "worst_level_err": round(worst_lv, 4), "faces_darkened": sum(lv_count[1:]),
                          "darkest_face": kd.get("darkest"), "per_level": lv_count}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proj"); ap.add_argument("--kn5", required=True); ap.add_argument("--json")
    a = ap.parse_args(argv)
    proj = Path(a.proj); kn5 = Path(a.kn5)
    try:
        decl = json.loads((proj / "data" / "road_wear.json").read_text(encoding="utf-8"))
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"[road_wear_check] input error: {e}")
        return 2
    if not kn5.exists():
        print(f"[road_wear_check] input error: no {kn5}")
        return 2
    spec = decl["spec"]; plan = decl["stats"]["plan"]
    tex = float(spec["texel_m"]); A = int(plan["atlas_px"]); tile = float(spec["detail_tile_m"])
    mult = A * tex / tile
    rows = {}
    mats = materials_with_props(kn5)
    # the race kerbs (opt-in road_wear.kerbs, High Plains 0.1.7) have rows of their own in decl["materials"] (the exporter
    # binds them) but are judged by the kerb rows below, not as road-wear surfaces
    kdecl = decl.get("kerbs")
    kerb_mats = set(kdecl["materials"]) if kdecl else set()
    kpre = kdecl["spec"]["prefix"] if kdecl else None
    road_mats = {k: v for k, v in decl["materials"].items() if k not in kerb_mats}
    p = parse(kn5, keep=lambda n: any(n.upper().startswith(s) for s in spec["surfaces"]) or
              (kpre is not None and n.upper().startswith(kpre)), textures=True)
    by_name = {m["name"]: m for m in mats}
    bad = []
    atlas_name = None
    for mn, row in road_mats.items():
        m = by_name.get(mn)
        if m is None:
            bad.append(f"{mn}: not in the kn5"); continue
        if m["shader"] != row["shader"]:
            bad.append(f"{mn}: shader {m['shader']} != {row['shader']}")
        tx = dict(m["textures"])
        for sl in SLOTS:
            if sl not in tx:
                bad.append(f"{mn}: no {sl}"); continue
            blob = p["textures"].get(tx[sl])
            if not blob:
                bad.append(f"{mn}: {sl} {tx[sl]} not embedded"); continue
            sz = _img_size(blob)
            if not sz or any(v & (v - 1) for v in sz):
                bad.append(f"{mn}: {sl} {tx[sl]} {sz} not a power of two")
        got = m["props"].get("detailUVMultiplier")
        if got is None or abs(got - mult) > 1e-3:
            bad.append(f"{mn}: detailUVMultiplier {got} != {mult}")
        # every VAR the bake declared is in the kn5 at its value; and the lighting pair is there at all (without it AC
        # falls back to its shader defaults: 0.1.9's first build shipped the road with neither)
        for pn, pv in (row.get("props") or {}).items():
            kv = m["props"].get(pn)
            if kv is None or abs(kv - float(pv)) > 1e-3:
                bad.append(f"{mn}: {pn} {kv} != declared {pv}")
        for pn in ("ksAmbient", "ksDiffuse"):
            if pn not in m["props"]:
                bad.append(f"{mn}: no {pn} (AC would use its shader default)")
        atlas_name = tx.get("txDiffuse", atlas_name)
    rows["materials"] = {"pass": not bad, "materials": sorted(road_mats), "problems": bad}
    if atlas_name is None or atlas_name not in p["textures"]:
        print("[road_wear_check] input error: no shipped atlas to read")
        return 2

    # the meshes: world (east, north), uv
    tris = []
    road_tris = set()            # the first surface's (1ROAD): the tone row reads only these (the edge strip's tone is
    for me in p["meshes"]:       # the road's carried outward, not the photo's verge)
        if me["matid"] >= len(mats) or mats[me["matid"]]["name"] not in road_mats:
            continue
        V = _world_verts(me)
        idx = me["idx"]
        first = me["name"].upper().startswith(spec["surfaces"][0])
        for t in range(0, len(idx), 3):
            if first:
                road_tris.add(len(tris))
            a_, b_, c_ = V[idx[t]], V[idx[t + 1]], V[idx[t + 2]]
            tris.append((((a_[0], -a_[2]), (b_[0], -b_[2]), (c_[0], -c_[2])),
                         ((a_[3], a_[4]), (b_[3], b_[4]), (c_[3], c_[4]))))
    if not tris:
        print("[road_wear_check] input error: no road-wear triangles in the kn5")
        return 2
    s0 = 1.0 / (A * tex)
    worst_d = 0.0; worst_sh = 0.0; n_bad = 0
    tex_claim = {}; repeats = 0; phase_by = [0.0, 0.0]
    for (P0, P1, P2), (U0, U1, U2) in tris:
        ex, ey = P1[0] - P0[0], P1[1] - P0[1]; fx, fy = P2[0] - P0[0], P2[1] - P0[1]
        det = ex * fy - ey * fx
        if abs(det) < 1e-6:
            continue
        du1, dv1 = U1[0] - U0[0], U1[1] - U0[1]; du2, dv2 = U2[0] - U0[0], U2[1] - U0[1]
        j11 = (du1 * fy - du2 * ey) / det; j12 = (du2 * ex - du1 * fx) / det
        j21 = (dv1 * fy - dv2 * ey) / det; j22 = (dv2 * ex - dv1 * fx) / det
        sA = j11 * j11 + j12 * j12 + j21 * j21 + j22 * j22
        dt = abs(j11 * j22 - j12 * j21)
        r = math.sqrt(max(0.0, sA * sA / 4 - dt * dt))
        s1 = math.sqrt(sA / 2 + r); s2 = math.sqrt(max(0.0, sA / 2 - r))
        d = max(abs(s1 / s0 - 1), abs(s2 / s0 - 1)); sh = (s1 - s2) / s0
        worst_d = max(worst_d, d); worst_sh = max(worst_sh, sh)
        if d > GATE["density_tol"] or sh > GATE["shear_tol"]:
            n_bad += 1
        cen = ((P0[0] + P1[0] + P2[0]) / 3, (P0[1] + P1[1] + P2[1]) / 3)
        cu = ((U0[0] + U1[0] + U2[0]) / 3, (U0[1] + U1[1] + U2[1]) / 3)
        for (pe, pn), (u, v) in ((P0, U0), (P1, U1), (P2, U2), (cen, cu)):
            key = (int(math.floor(u * A)), int(math.floor(v * A)))
            prev = tex_claim.get(key)
            if prev is None:
                tex_claim[key] = (pe, pn)
            elif math.hypot(prev[0] - pe, prev[1] - pn) > GATE["repeat_m"]:
                repeats += 1
        for (pe, pn), (u, v) in ((P0, U0), (P1, U1), (P2, U2)):
            # the kn5 stores v as the add-on writes it (Blender's v or 1 - v): the phase is read in both, the better kept
            pu = (u * mult - pe / tile) % 1.0
            for c, vv in enumerate((v, 1.0 - v)):
                pv = (vv * mult - pn / tile) % 1.0
                phase_by[c] = max(phase_by[c], min(pu, 1 - pu), min(pv, 1 - pv))
    worst_phase = min(phase_by)
    rows["density"] = {"pass": n_bad == 0, "triangles": len(tris), "off": n_bad, "worst_scale_err": round(worst_d, 6),
                       "worst_shear": round(worst_sh, 6), "texel_m": tex, "atlas_px": A}
    rows["no_repeat"] = {"pass": repeats == 0, "texels_claimed": len(tex_claim), "claimed_twice": repeats}
    rows["detail_phase"] = {"pass": worst_phase <= GATE["phase_tol"], "worst_tiles": round(worst_phase, 5),
                            "detail_uv_multiplier": mult}

    # the atlas as shipped
    from PIL import Image
    im = Image.open(io.BytesIO(p["textures"][atlas_name])).convert("RGBA")
    px = im.load()
    W, H = im.size

    # the v the kn5 stores against Blender's (v up from the image's bottom row): the add-on writes -v (measured on Milford
    # 0.1.7: 1ROAD v in -0.85..-0.01); the gate reads all three conventions on the tone row and keeps the one that fits
    VB = {"v": lambda v: v, "-v": lambda v: -v, "1-v": lambda v: 1.0 - v}

    def atlas_lum(u, v, flip):
        x = min(W - 1, max(0, int(u * W)))
        yy = 1.0 - VB[flip](v)
        y = min(H - 1, max(0, int(yy * H)))
        r_, g_, b_, _a = px[x, y]
        return (0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_) / 255.0

    cell = 4.0
    hsh = {}
    for ti, ((P0, P1, P2), _uv) in enumerate(tris):
        xs = (P0[0], P1[0], P2[0]); ys = (P0[1], P1[1], P2[1])
        for i in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
            for j in range(int(math.floor(min(ys) / cell)), int(math.floor(max(ys) / cell)) + 1):
                hsh.setdefault((i, j), []).append(ti)

    def uv_at(x, y):
        for ti in hsh.get((int(math.floor(x / cell)), int(math.floor(y / cell))), ()):
            (P0, P1, P2), (U0, U1, U2) = tris[ti]
            d = (P1[1] - P2[1]) * (P0[0] - P2[0]) + (P2[0] - P1[0]) * (P0[1] - P2[1])
            if abs(d) < 1e-12:
                continue
            l1 = ((P1[1] - P2[1]) * (x - P2[0]) + (P2[0] - P1[0]) * (y - P2[1])) / d
            l2 = ((P2[1] - P0[1]) * (x - P2[0]) + (P0[0] - P2[0]) * (y - P2[1])) / d
            l3 = 1 - l1 - l2
            if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
                return (l1 * U0[0] + l2 * U1[0] + l3 * U2[0], l1 * U0[1] + l2 * U1[1] + l3 * U2[1])
        return None

    aer = spec.get("aerial")
    line_pts = []
    for lf in sorted((proj / "data").glob("road_wear.line.*.json")):
        L = json.loads(lf.read_text(encoding="utf-8"))
        line_pts.append((L["points"], L["rubber"]))
    w = spec["wear"]
    amp = float(w["amplitude"])
    reach = 0.5 * w["track_m"] + 4 * w["spread_m"]
    ch = {}
    for pts, _r in line_pts:
        for q in pts:
            ch.setdefault((int(q[0] // 8), int(q[1] // 8)), []).append(q)

    def near_line(x, y):
        best = 1e18
        for i in range(int(x // 8) - 1, int(x // 8) + 2):
            for j in range(int(y // 8) - 1, int(y // 8) + 2):
                for q in ch.get((i, j), ()):
                    best = min(best, (q[0] - x) ** 2 + (q[1] - y) ** 2)
        return math.sqrt(best)

    if aer:
        img = Image.open(proj / aer["image"]).convert("RGB")
        apx = img.load(); aw, ah = img.size
        Wb, Sb, Eb, Nb = aer["bbox_lonlat"]
        o = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
        phi = math.radians(o["lat"])
        m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
        m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
        reg = (decl["stats"].get("aerial") or {}).get("registration") or {"dx_m": 0.0, "dy_m": 0.0}

        def aerial_lum(x, y):
            lon = o["lon"] + (x + reg["dx_m"]) / m_lon; lat = o["lat"] + (y + reg["dy_m"]) / m_lat
            u = (lon - Wb) / (Eb - Wb) * aw; v = (Nb - lat) / (Nb - Sb) * ah
            if not (0 <= u < aw and 0 <= v < ah):
                return None
            r_, g_, b_ = apx[int(u), int(v)]
            return (0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_) / 255.0, b_ / max(1, r_)
        rt = sorted(road_tris)
        step = max(1, len(rt) // 6000)
        samples = []
        for ti in rt[::step]:
            (P0, P1, P2), (U0, U1, U2) = tris[ti]
            x = (P0[0] + P1[0] + P2[0]) / 3; y = (P0[1] + P1[1] + P2[1]) / 3
            if near_line(x, y) < reach + 0.5:
                continue
            al = aerial_lum(x, y)
            if al is None or al[1] > spec["tone"]["shadow_blue"]:
                continue
            samples.append((al[0], (U0[0] + U1[0] + U2[0]) / 3, (U0[1] + U1[1] + U2[1]) / 3))
        # the lit asphalt only: a shadow's edge and anything the bake clipped or filled is not the photo by design
        if samples:
            med = sorted(s_[0] for s_ in samples)[len(samples) // 2]
            lo, hi = spec["tone"]["clip"]
            samples = [s_ for s_ in samples if max(0.8, lo) * med <= s_[0] <= hi * med]

        def pearson(pairs):
            n = len(pairs)
            if n < 10:
                return None
            mx = sum(q[0] for q in pairs) / n; my = sum(q[1] for q in pairs) / n
            sxy = sum((q[0] - mx) * (q[1] - my) for q in pairs)
            sx = math.sqrt(sum((q[0] - mx) ** 2 for q in pairs)); sy = math.sqrt(sum((q[1] - my) ** 2 for q in pairs))
            return sxy / max(1e-12, sx * sy)
        tone_r = {f: pearson([(s_[0], atlas_lum(s_[1], s_[2], f)) for s_ in samples]) for f in VB}
        flip = max(tone_r, key=lambda k: tone_r[k] if tone_r[k] is not None else -2)
        r_best = tone_r[flip]
        rows["tone"] = {"pass": r_best is not None and r_best >= GATE["tone_r_min"], "pearson_r": round(r_best or 0, 4),
                        "samples": len(samples), "v_convention": flip,
                        "r_by_convention": {k: round(v or 0, 4) for k, v in tone_r.items()}}
    else:
        flip = "-v"
        rows["tone"] = {"pass": True, "note": "no aerial declared: tone = 1 (nothing to follow)"}

    # rubber on the declared line
    prof = {}
    nst = 0
    rub_used = []
    for pts, rub in line_pts:
        n = len(pts)
        for i in range(0, n, 5):
            if rub[i] < 0.7:
                continue
            a_ = pts[(i - 1) % n]; b_ = pts[(i + 1) % n]
            tx_, ty_ = b_[0] - a_[0], b_[1] - a_[1]; tl = math.hypot(tx_, ty_) or 1.0
            nx, ny = -ty_ / tl, tx_ / tl
            row = {}
            for k in range(-16, 17):
                u_ = k * 0.25
                uv = uv_at(pts[i][0] + nx * u_, pts[i][1] + ny * u_)
                if uv is None:
                    break
                row[k] = atlas_lum(uv[0], uv[1], flip)
            else:
                ref = sorted(row[k] for k in row if abs(k) >= 12)
                ref = ref[len(ref) // 2]
                if ref <= 0:
                    continue
                for k, v in row.items():
                    prof.setdefault(k, []).append(1.0 - v / ref)
                nst += 1
                rub_used.append(rub[i])
    if nst >= 10:
        mean = {k: sum(v) / len(v) for k, v in prof.items()}
        core = {k: max(0.0, mean[k]) for k in mean if abs(k) <= 10}
        tot = sum(core.values())
        centroid = sum(k * 0.25 * v for k, v in core.items()) / tot if tot > 0 else float("nan")
        ks = [k for k in mean if abs(k) <= 3]
        depth = sum(mean[k] for k in ks) / len(ks)
        # the declared darkening over the same |u| <= 0.75 m, less what is left at the reference 3-4 m out
        want = amp * (sum(rub_used) / len(rub_used)) * (
            sum(tyre_profile(k * 0.25, w["track_m"], w["spread_m"]) for k in ks) / len(ks)
            - tyre_profile(3.5, w["track_m"], w["spread_m"]))
        rows["rubber"] = {"pass": (abs(centroid) <= GATE["line_offset_max_m"] and
                                   GATE["depth_min_frac"] * want <= depth <= GATE["depth_max_frac"] * want),
                          "stations": nst, "centroid_m": round(centroid, 3), "depth_on_line": round(depth, 4),
                          "declared_depth": round(want, 4), "declared_amplitude": amp,
                          "profile": {round(k * 0.25, 2): round(mean[k], 4) for k in sorted(mean)}}
    else:
        rows["rubber"] = {"pass": False, "stations": nst, "note": "too few full cross-sections on the built road"}
    if kdecl:
        rows.update(kerb_rows(proj, cfg, decl, kdecl, mats, p, line_pts, w))
    ok = all(r["pass"] for r in rows.values())
    out = {"pass": ok, "gate": GATE, "kn5": kn5.name, "rows": rows}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    for k, r in rows.items():
        print(f"[road_wear_check] {k:13s} {'PASS' if r['pass'] else 'FAIL'}  " +
              ", ".join(f"{kk} {vv}" for kk, vv in r.items() if kk not in ("pass", "profile", "materials")))
    print(f"[road_wear_check] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
