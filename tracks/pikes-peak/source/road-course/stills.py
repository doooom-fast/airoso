"""Stills for Kevin to judge the re-trace (ledger 0085 Re-trace). Writes to $PP_STILLS (default /Volumes/Drive/codex/pp_work/retrace/).

    python tracks/pikes-peak/source/road-course/stills.py     (after retrace.py and routes.py)

  overall.png        the full NAIP crop at its own 0.3 m resolution, 1 px lines: piece edges (cyan), centres (magenta),
                     kerb runs (red), the oval's inside edge (orange; dotted where bridged across a junction / opening),
                     the lidar wall face (yellow), the old eyeball lines (faint white)
  zoom_<name>.png    60 x 60 m crops, 4x: the same, plus the WEAR (light yellow tint where the asphalt darkens against the
                     clean pavement beside it; alpha <= 0.35, never hiding the asphalt)
  layout_<id>.png    each candidate layout's lap drawn over a dimmed crop, with its length and wear score
Lines are drawn in the image's own frame: the measured geometry (registration removed) is shifted back by naip.SHIFT
to land on the pixels it was measured from; the old eyeball lines are drawn where they were drawn (raw frame).
"""
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geo  # noqa: E402
import naip  # noqa: E402

OUT = Path(os.environ.get("PP_STILLS", "/Volumes/Drive/codex/pp_work/retrace"))
OUT.mkdir(parents=True, exist_ok=True)

C_EDGE = (0, 230, 255); C_CEN = (255, 0, 220); C_KERB = (255, 40, 40); C_IN = (255, 150, 0); C_WALL = (255, 240, 0)
C_OLD = (255, 255, 255)


def font(sz):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def to_px(E):
    px, py = naip.en_to_px(E[:, 0], E[:, 1])
    return np.c_[px, py]


def load():
    d = json.loads((HERE / "infield_pieces.naip.json").read_text())
    I = pickle.load(open(naip.CACHE / "internals.pkl", "rb"))
    ie = json.loads((HERE / "inside_edge.naip.json").read_text())
    lay = json.loads((HERE / "layouts.naip.json").read_text())
    old_net = json.loads((HERE / "infield_network.eyeball.json").read_text())
    old_in = json.loads((HERE / "inside_edge.eyeball.json").read_text())
    return d, I, ie, lay, old_net, old_in


def old_lines(old_net, old_in):
    lines = [np.array(e["px"], float) for e in old_net["edges"].values()]
    # the old inside edge: inner_edge.py measured from the LM workshop line (the port line with its right edge moved
    # onto the wall face: centre shifted by half the face offset) along its left normal, in the raw image frame
    ov = naip.oval_line()
    f = ov["face_off"] - ov["W"] / 2
    pts = []
    for r, P, L, ff in zip(old_in["rows"], ov["P"], ov["L"], f):
        if r["inside_edge_m"] is None or not np.isfinite(ff):
            pts.append(None); continue
        q = P - (ff / 2) * L + r["inside_edge_m"] * L
        px, py = geo.en_to_px(q[0], q[1])
        pts.append((float(px), float(py)))
    seg, segs = [], []
    for p in pts:
        if p is None:
            if len(seg) > 1:
                segs.append(np.array(seg))
            seg = []
        else:
            seg.append(p)
    if len(seg) > 1:
        segs.append(np.array(seg))
    return lines, segs


def wear_layer(I, shape):
    """Per-pixel darkening of each piece's asphalt against its section's clean (80th-percentile) pavement."""
    ch = naip.channels()
    W = np.zeros(shape, np.float32)
    for name, D in I.items():
        P, L, dl, dr = D["P"], D["L"], D["dl"], D["dr"]
        ring = D.get("mode") == "ring"
        for k in range(len(P)):
            lo = (-(18.0 - dl[k]) if ring else -dr[k]) + 0.5
            hi = dl[k] - 0.5
            if hi - lo < 2:
                continue
            o = np.arange(lo, hi, 0.15)
            E = P[k, 0] + o * L[k, 0]; N = P[k, 1] + o * L[k, 1]
            lum = naip.sample(ch["lum"], E, N)
            ref = np.percentile(lum, 80)
            dk = np.clip((ref - lum) / max(ref, 1), 0, 1)
            px, py = naip.en_to_px(E, N)
            ix = np.clip(np.round(px).astype(int), 0, shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, shape[0] - 1)
            np.maximum.at(W, (iy, ix), dk)
    from scipy import ndimage
    filled = ndimage.grey_dilation(W, size=(3, 3))
    return np.where(W > 0, W, filled)          # close the 1 px holes between sections


def draw_all(d, I, ie, old, sc=1, x0=0, y0=0, draw_old=True, d_=None, w=1):
    lines, segs = old
    def T(Q):
        return [((q[0] - x0 + 0.5) * sc, (q[1] - y0 + 0.5) * sc) for q in Q]
    if draw_old:
        for Q in lines + segs:
            d_.line(T(Q), fill=C_OLD + (90,), width=max(1, w))
    # oval: wall face + inside edge (seen solid, bridged dotted)
    rows = ie["rows"]
    E = np.array([r["edge_en_m"] for r in rows])
    lab = np.array([r["label"] for r in rows])
    wid = np.array([r["wall_face_to_edge_m"] for r in rows])
    ov = naip.oval_line()
    line = naip.resample(ov["line"], 1.0, closed=True)
    _, Lo = naip.normals(line, closed=True)
    face = E - wid[:, None] * Lo
    Pf = to_px(np.vstack([face, face[:1]]))
    d_.line(T(Pf), fill=C_WALL + (255,), width=w)
    Pe = to_px(E)
    for k in range(len(Pe)):
        a, b = Pe[k], Pe[(k + 1) % len(Pe)]
        if lab[k] == "seen" or (k // 2) % 2 == 0:
            d_.line(T([a, b]), fill=C_IN + (255,), width=w)
    for name, D in I.items():
        P, L, s = D["P"], D["L"], D["s"]
        for dd, sg, cv, kb in ((D["dl"], 1, D["covl"], D["kl"]), (D["dr"], -1, D["covr"], D["kr"])):
            if dd is None or cv is None or cv.sum() < 2 or (D.get("mode") == "ring" and sg < 0):
                continue
            Ed = P + (sg * dd)[:, None] * L
            Q = to_px(Ed)
            d_.line(T(Q[cv]), fill=C_EDGE + (255,), width=w)
            idx = np.where(kb & cv)[0]
            for k in idx:
                if k + 1 < len(Q) and kb[k + 1]:
                    d_.line(T(Q[k:k + 2]), fill=C_KERB + (255,), width=w + 1)
        d_.line(T(to_px(D["C"])), fill=C_CEN + (200,), width=w)


def overall(d, I, ie, old):
    im = Image.fromarray(naip.image().astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    draw_all(d, I, ie, old, d_=dr)
    f = font(14)
    for name, D in I.items():
        q = to_px(D["C"][len(D["C"]) // 2][None])[0]
        dr.text((q[0] + 4, q[1] - 8), name, fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    out = Image.alpha_composite(im, ov).convert("RGB")
    out.save(OUT / "overall.png", optimize=True)


def zoom(name, centre_en, d, I, ie, old, Wmap, half_m=30.0, sc=4, label=""):
    cpx = to_px(np.array([centre_en]))[0]
    hp = half_m / 0.3
    x0, y0 = int(cpx[0] - hp), int(cpx[1] - hp)
    x1, y1 = int(cpx[0] + hp), int(cpx[1] + hp)
    base = naip.image()[y0:y1, x0:x1].astype(np.float32)
    w = Wmap[y0:y1, x0:x1]
    # wear tint: light yellow, alpha up to 0.45 at 30 % darkening (never hides the asphalt)
    a = np.clip(w / 0.30, 0, 1)[..., None] * 0.35
    a = np.where(w[..., None] >= 0.06, a, 0)
    tint = np.array([255, 235, 60], np.float32)
    base = base * (1 - a) + tint * a
    im = Image.fromarray(base.astype(np.uint8)).resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.LANCZOS).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    draw_all(d, I, ie, old, sc=sc, x0=x0, y0=y0, d_=dr, w=2)
    f = font(22)
    dr.rectangle([0, 0, im.size[0], 34], fill=(0, 0, 0, 160))
    dr.text((8, 6), f"{name}  60 x 60 m, 4x.  {label}", fill=(255, 255, 255, 255), font=f)
    dr.text((8, im.size[1] - 30), "cyan edges  red kerb runs  magenta centre  orange oval inside edge (dotted = bridged)  "
            "yellow lidar wall  faint white = old eyeball  yellow tint = wear", fill=(255, 255, 255, 255), font=font(15),
            stroke_width=2, stroke_fill=(0, 0, 0, 255))
    Image.alpha_composite(im, ov).convert("RGB").save(OUT / f"zoom_{name}.png", optimize=True)


def layout_still(L, d, I, Pp_centres, ie):
    x0, y0, x1, y1 = 150, 120, 1400, 1300
    base = (naip.image()[y0:y1, x0:x1] * 0.55).astype(np.uint8)
    im = Image.fromarray(base).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    def T(Q):
        return [(q[0] - x0, q[1] - y0) for q in Q]
    cols = [(255, 60, 60), (255, 160, 0), (255, 255, 0), (0, 255, 120), (0, 220, 255), (120, 120, 255), (255, 0, 255),
            (255, 255, 255), (255, 120, 180), (160, 255, 60), (0, 160, 255)]
    if L.get("uses_oval"):
        mid = np.load(naip.CACHE / "oval_mid.npy")[:, 0:2]
        lay = json.loads((HERE / "layouts.naip.json").read_text())["oval"]
        smid = naip.cumlen(np.vstack([mid, mid[:1]]))[:-1]
        sNW = lay["nw_merge_mid_s_arc"] if L["pieces"][-1][0] == "arc_nw" else lay["nw_merge_mid_s_nroad"]
        sNE = lay["ne_diverge_mid_s"]
        sel = (smid >= sNW) | (smid <= sNE)
        order = np.r_[np.where(smid >= sNW)[0], np.where(smid <= sNE)[0]]
        dr.line(T(to_px(mid[order])), fill=(255, 255, 255, 255), width=3)
    for i, (p, dirn) in enumerate(L["pieces"]):
        Q = Pp_centres[p]
        if dirn < 0:
            Q = Q[::-1]
        q = to_px(Q)
        dr.line(T(q), fill=cols[i % len(cols)] + (255,), width=4)
        # direction arrow at the middle
        m = len(q) // 2
        if m + 3 < len(q):
            a, b = q[m], q[m + 3]
            v = (b - a) / max(np.hypot(*(b - a)), 1e-6)
            nrm = np.array([-v[1], v[0]])
            tip = b + v * 6
            dr.polygon(T([tip, b - v * 6 + nrm * 7, b - v * 6 - nrm * 7]), fill=cols[i % len(cols)] + (255,))
    f = font(24)
    dr.rectangle([0, 0, im.size[0], 96], fill=(0, 0, 0, 190))
    txt = f"{L['id']}  {L['name']}"
    dr.text((10, 6), txt[:110], fill=(255, 255, 255, 255), font=f)
    pub = "" if not L.get("vs_published_m") else f"   vs published 2,074 / 2,116 m: {L['vs_published_m'][0]:+.0f} / {L['vs_published_m'][1]:+.0f}"
    dr.text((10, 36), f"lap {L['lap_m']:.0f} m (+-{L['uncertainty_m']:.0f}){pub}   wear {L['wear_weighted']:.3f}", fill=(255, 255, 0, 255), font=font(20))
    agree = ", ".join(f"{a} {b}" for a, b in L["wear_direction"]) or "no piece's wear reads a direction"
    dr.text((10, 64), ("wear direction: " + agree)[:150], fill=(200, 200, 200, 255), font=font(16))
    Image.alpha_composite(im, ov).convert("RGB").save(OUT / f"layout_{L['id']}.png", optimize=True)


def main():
    d, I, ie, lay, old_net, old_in = load()
    old = old_lines(old_net, old_in)
    overall(d, I, ie, old)
    Wmap = wear_layer(I, naip.image().shape[:2])
    # zoom centres: every infield corner (curvature peaks of each piece's centre), both junctions, the oval's inside edge
    spots = []
    for name, rec in d["pieces"].items():
        C = np.array(rec["centre_en_m"])
        for c in rec["wear"]["corners"]:
            m = int(np.clip(np.mean(c["s"]), 0, len(C) - 1))
            spots.append((f"{name}_s{int(c['s'][0])}", C[m], f"{name} corner s {c['s'][0]:.0f}-{c['s'][1]:.0f}, {c['turn']}, R {c['radius_m']:.0f} m"))
    # thin the corner spots: drop any within 25 m of one kept
    kept = []
    for sp in spots:
        if all(np.hypot(*(sp[1] - k[1])) > 25 for k in kept):
            kept.append(sp)
    rows = ie["rows"]
    E = np.array([r["edge_en_m"] for r in rows])
    s = np.array([r["s"] for r in rows])
    ne = np.array(d["pieces"]["ne_lane"]["centre_en_m"])[0]
    nw = np.array(d["pieces"]["arc_nw"]["centre_en_m"])[0]
    kept.append(("junction_NE_diverge", ne, "NE diverge (back stretch -> infield lane)"))
    kept.append(("junction_NW_merge", nw, "NW merge (infield -> turns 3-4)"))
    for ss_ in (60, 520, 850, 1180):
        k = int(np.argmin(np.abs(s - ss_)))
        kept.append((f"oval_inside_s{ss_}", E[k], f"oval inside edge s {ss_}"))
    for name, c, lab in kept:
        zoom(name, c, d, I, ie, old, Wmap, label=lab)
    Pc = {k: np.array(v["centre_en_m"]) for k, v in d["pieces"].items()}
    sys.path.insert(0, str(HERE))
    import routes
    Pp = routes.split_pieces(Pc)
    for L in lay["layouts"]:
        if "error" not in L:
            layout_still(L, d, I, Pp, ie)
    print(len(kept), "zooms;", OUT)


if __name__ == "__main__":
    main()
