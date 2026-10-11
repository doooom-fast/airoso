"""Redraw the HUD minimap (map.png + data/map.ini) in the KN5 frame — the frame the car lives in.

Kevin, 2026-10-08, from the seat: "the map is wrong. It doesn't seem to be tracking with the
actual track or the car on it ... there's a chirality issue somewhere." Measured: the engine's
track_folder draws map.png from data/centerline.local.json (ENGINE frame, z = north) and writes
map.ini offsets from that same frame, but AC places the car using KN5 coordinates, where
z is mirrored (kn5_to_gate_obj.py:8-10). The car's pixel sits on a north-south mirror image of
the drawn line; the July reference shipped the identical map.ini, so its map was wrong too.

This draws from data/finished_centerline.json — written by the kn5 prep IN the kn5 frame — plus
the connector pieces (z negated: engine -> kn5) so the side streets show, using AC's convention
exactly as track_folder states it: pixel = (world + OFFSET) / SCALE_FACTOR, SCALE_FACTOR in
metres per pixel. Run after track_folder; it overwrites map.png + data/map.ini in the build
folder (and installs into the AC track dir when --install <dir> is given).

MULTI-LAYOUT (ledger 0047): AC reads <track>/<layout>/map.png + <layout>/data/map.ini when the
folder carries models_<layout>.ini, so every layout dir found beside a models_<layout>.ini gets
the same map (identical content — all layouts share the road), the root as well (harmless).

    python tools/make_map.py <project-dir> [--install <ac-track-dir>]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W = H = 900
MARGIN = 28
DRAW = 10


def build(project_dir, install_dir=None):
    proj = Path(project_dir)
    data = proj / "data"
    slug = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))["slug"]
    fin = json.loads((data / "finished_centerline.json").read_text(encoding="utf-8"))
    main = [(p[0], p[2]) for p in fin["points_xyz_m"]]               # kn5 frame already
    lines = [main]
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            lines.append([(p[0], -p[2]) for p in c["points_xyz_m"]])  # engine -> kn5: z mirrored
    xs = [x for ln in lines for x, _ in ln]
    zs = [z for ln in lines for _, z in ln]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    span = max(maxx - minx, maxz - minz)
    scale = span / (W - 2 * MARGIN)                 # metres per pixel
    ox = MARGIN * scale - minx + ((W - 2 * MARGIN) * scale - (maxx - minx)) / 2
    oz = MARGIN * scale - minz + ((H - 2 * MARGIN) * scale - (maxz - minz)) / 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for ln in lines:
        pts = [((x + ox) / scale, (z + oz) / scale) for x, z in ln]
        if len(pts) >= 2:
            dr.line(pts, fill=(255, 255, 255, 255), width=DRAW, joint="curve")
    ini = ("[PARAMETERS]\n"
           f"WIDTH={W}\nHEIGHT={H}\nSCALE_FACTOR={scale:.6f}\n"
           f"X_OFFSET={ox:.3f}\nZ_OFFSET={oz:.3f}\nMARGIN={MARGIN}\nDRAWING_SIZE={DRAW}\n")
    roots = [proj / "build" / slug]
    if install_dir:
        roots.append(Path(install_dir))
    written = []
    for root in roots:
        if not root.exists():
            continue
        for t in map_targets(root):
            img.save(t / "map.png")
            (t / "data").mkdir(exist_ok=True)
            (t / "data" / "map.ini").write_text(ini, encoding="utf-8")
            written.append(t)
            print(f"[map] wrote {t / 'map.png'} + data/map.ini (kn5 frame, {len(lines)} line(s), "
                  f"{scale:.3f} m/px)")
    return written


def map_targets(root: Path) -> list[Path]:
    """The root plus every <root>/<layout>/ named by a models_<layout>.ini (AC's multi-layout
    structure); a single-layout folder (models.ini) is the root alone."""
    out = [root]
    for ini in sorted(root.glob("models_*.ini")):
        out.append(root / ini.stem[len("models_"):])
    for t in out[1:]:
        t.mkdir(parents=True, exist_ok=True)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    inst = args[args.index("--install") + 1] if "--install" in args else None
    build(args[0], inst)
