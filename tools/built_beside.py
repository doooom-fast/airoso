"""The aerial beside what was built: one pair of top-down cells per built object group (ledger 0081; L12 "show, don't assert").

For each OBJ group whose name starts with --prefix (default 1KERB_circuit_) in a BUILT gate OBJ (data/track.obj: the road
kn5 read back, the engine frame x = east, y = up, z = north about data/centerline.local.json's origin), the left cell is
the georeferenced aerial round the group, the right the same aerial dimmed with the built faces filled over it (the
group magenta, the road 1ROAD outline cyan), so the paint and the built kerb can be compared where they lie.

    python tools/built_beside.py <workshop-project> --image <png> --corners W,N,E,S --out <sheet.jpg>
                                 [--prefix 1KERB_circuit_] [--cell-m 40] [--groups 0,3,7] [--pairs-per-row 3]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

CELL_PX = 360


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def read_obj(path: Path, want):
    groups, verts, cur = {}, [], None
    with path.open(encoding="utf-8", errors="replace") as f:
        for ln in f:
            if ln.startswith("v "):
                p = ln.split()
                verts.append((float(p[1]), float(p[3])))
            elif ln.startswith(("o ", "g ")):
                name = ln.split(maxsplit=1)[1].strip()
                cur = name if want(name) else None
                if cur:
                    groups.setdefault(cur, [])
            elif cur and ln.startswith("f "):
                groups[cur].append([int(t.split("/")[0]) for t in ln.split()[1:]])
    return groups, verts


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    proj = Path(argv.pop(0))
    opt = {}
    while argv:
        k = argv.pop(0)
        opt[k] = argv.pop(0)
    prefix = opt.get("--prefix", "1KERB_circuit_")
    cell_m = float(opt.get("--cell-m", 40))
    per_row = int(opt.get("--pairs-per-row", 3))
    img = Image.open(opt["--image"]).convert("RGB")
    W_, H_ = img.size
    cw, cn, ce, cs = (float(v) for v in opt["--corners"].split(","))
    local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
    lon0, lat0 = float(local["origin"]["lon"]), float(local["origin"]["lat"])
    m_lon, m_lat = mpd(lat0)
    mpp = (ce - cw) * m_lon / W_

    def px(x, n):
        return ((lon0 + x / m_lon - cw) / (ce - cw) * W_, (cn - (lat0 + n / m_lat)) / (cn - cs) * H_)

    groups, V = read_obj(proj / "data" / "track.obj", lambda n: n.startswith((prefix, "1ROAD")))
    names = sorted((g for g in groups if g.startswith(prefix)), key=lambda g: int(g[len(prefix):]) if g[len(prefix):].isdigit() else 0)
    if "--groups" in opt:
        keep = {f"{prefix}{k}" for k in opt["--groups"].split(",")}
        names = [g for g in names if g in keep]
    road = [f for g, fs in groups.items() if g.startswith("1ROAD") for f in fs]
    rows = math.ceil(len(names) / per_row) or 1
    sheet = Image.new("RGB", (per_row * 2 * CELL_PX, rows * (CELL_PX + 18)), (20, 20, 20))
    d0 = ImageDraw.Draw(sheet)
    half = cell_m / 2 / mpp
    for k, g in enumerate(names):
        ids = {i for f in groups[g] for i in f}
        cx = sum(V[i - 1][0] for i in ids) / len(ids)
        cz = sum(V[i - 1][1] for i in ids) / len(ids)
        X, Y = px(cx, cz)
        box = (int(X - half), int(Y - half), int(X + half), int(Y + half))
        raw = img.crop(box)
        sc = CELL_PX / raw.size[0]
        raw = raw.resize((CELL_PX, CELL_PX), Image.LANCZOS)
        built = ImageEnhance.Brightness(raw).enhance(0.55)
        d = ImageDraw.Draw(built, "RGBA")

        def loc(i):
            a, b = px(*V[i - 1])
            return (a - box[0]) * sc, (b - box[1]) * sc
        r2 = (cell_m * 1.5) ** 2
        for f in road:
            x0, z0 = V[f[0] - 1]
            if (x0 - cx) ** 2 + (z0 - cz) ** 2 < r2:
                d.polygon([loc(i) for i in f], outline=(0, 200, 220, 255))
        for f in groups[g]:
            d.polygon([loc(i) for i in f], fill=(255, 0, 255, 150))
        r, c = divmod(k, per_row)
        y0 = r * (CELL_PX + 18) + 18
        sheet.paste(raw, (c * 2 * CELL_PX, y0))
        sheet.paste(built, (c * 2 * CELL_PX + CELL_PX, y0))
        d0.text((c * 2 * CELL_PX + 4, y0 - 15), f"{g}: aerial | built (magenta), {cell_m:.0f} m", fill=(255, 255, 255))
    out = Path(opt["--out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)
    print(f"[built_beside] {len(names)} groups -> {out}")


if __name__ == "__main__":
    main()
