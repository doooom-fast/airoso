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
a map, the root as well (harmless).

PER-LAYOUT SCOPE (ledger 0054 P4, EXPANSION-PLAN A12 — opt-in): a layout whose track.config.json entry says
``"map": "lap"`` gets a map of ITS LAP ALONE — the mainline (finished_centerline.json) without the connector
pieces — drawn to its own extent, with its own map.ini scale and offsets: the Speedways run the 13.5 km loop and
would otherwise shrink 1.21x to fit 6 km of north roads they can never reach (sealed). The default, ``"network"``
(or no key), is the whole network: Free Roam drives all of it. The root map is always the network. The same
scope redraws ``ui/<layout>/outline.png`` (the Content Manager outline, the same line in the same frame, north up,
the track_folder colours) so the outline and the minimap agree on what the layout drives; preview.png (the OSM
map with the route) is track_folder's and untouched. Any other value of "map" is refused.

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
SCOPES = ("network", "lap")
OUTLINE_STROKE = (232, 236, 240, 255)      # scripts/ac/track_folder.py's ui/<id>/outline.png colour
OUTLINE_WIDTH = 5


def layout_scopes(cfg):
    """{layout id: 'network' | 'lap'} from track.config.json layouts[].map (absent = network); ValueError otherwise"""
    out = {}
    for lo in cfg.get("layouts") or []:
        if not isinstance(lo, dict):
            continue
        scope = str(lo.get("map") or "network").lower()
        if scope not in SCOPES:
            raise ValueError("layout %s: map = %r is not one of %s" % (lo.get("id"), lo.get("map"), "/".join(SCOPES)))
        out[str(lo.get("id"))] = scope
    return out


def load_lines(project_dir):
    """(main, connectors): the mainline in the kn5 frame and every connector piece mirrored into it"""
    proj = Path(project_dir)
    data = proj / "data"
    fin = json.loads((data / "finished_centerline.json").read_text(encoding="utf-8"))
    main = [(p[0], p[2]) for p in fin["points_xyz_m"]]               # kn5 frame already
    conns = []
    cp = data / "connectors.local.json"
    if cp.exists():
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            conns.append([(p[0], -p[2]) for p in c["points_xyz_m"]])  # engine -> kn5: z mirrored
    # A ROAD NETWORK (opt-in: data/network.edges.local.json, written by build_network_mesh when the config declares
    # network.reference_line): the mainline above is the ONE reference line the gates walk; Free Roam drives every
    # built edge, so every other edge is drawn too (the swept surface line, mesh frame -> kn5: z mirrored).
    ep = data / "network.edges.local.json"
    if ep.exists():
        on = set()
        rp = data / "network.reference.json"
        if rp.exists():
            on = set((json.loads(rp.read_text(encoding="utf-8")).get("line") or {}).get("edges") or [])
        for e in json.loads(ep.read_text(encoding="utf-8")).get("edges", []):
            if e.get("id") not in on and len(e.get("surface_xyz_m") or []) >= 2:
                conns.append([(p[0], -p[2]) for p in e["surface_xyz_m"]])
    return main, conns


def frame(lines):
    """(scale m/px, ox, oz) centring the lines on the W x H canvas with MARGIN"""
    xs = [x for ln in lines for x, _ in ln]
    zs = [z for ln in lines for _, z in ln]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    span = max(maxx - minx, maxz - minz)
    scale = span / (W - 2 * MARGIN)                 # metres per pixel
    ox = MARGIN * scale - minx + ((W - 2 * MARGIN) * scale - (maxx - minx)) / 2
    oz = MARGIN * scale - minz + ((H - 2 * MARGIN) * scale - (maxz - minz)) / 2
    return scale, ox, oz


def draw(lines, stroke=(255, 255, 255, 255), width=DRAW):
    """(image, ini text) for these lines: the HUD map (white, transparent) and its map.ini"""
    scale, ox, oz = frame(lines)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for ln in lines:
        pts = [((x + ox) / scale, (z + oz) / scale) for x, z in ln]
        if len(pts) >= 2:
            dr.line(pts, fill=stroke, width=width, joint="curve")
    ini = ("[PARAMETERS]\n"
           f"WIDTH={W}\nHEIGHT={H}\nSCALE_FACTOR={scale:.6f}\n"
           f"X_OFFSET={ox:.3f}\nZ_OFFSET={oz:.3f}\nMARGIN={MARGIN}\nDRAWING_SIZE={DRAW}\n")
    return img, ini, scale


def build(project_dir, install_dir=None):
    proj = Path(project_dir)
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    slug = cfg["slug"]
    scopes = layout_scopes(cfg)
    main, conns = load_lines(proj)
    sets = {"network": [main] + conns, "lap": [main]}
    drawn = {k: draw(v) for k, v in sets.items() if k == "network" or "lap" in scopes.values()}
    outlines = {k: draw(v, OUTLINE_STROKE, OUTLINE_WIDTH)[0] for k, v in sets.items() if k in drawn}
    roots = [proj / "build" / slug]
    if install_dir:
        roots.append(Path(install_dir))
    written = []
    for root in roots:
        if not root.exists():
            continue
        for t in map_targets(root):
            lid = t.name if t != root else None
            scope = scopes.get(lid, "network") if lid else "network"
            img, ini, scale = drawn[scope]
            img.save(t / "map.png")
            (t / "data").mkdir(exist_ok=True)
            (t / "data" / "map.ini").write_text(ini, encoding="utf-8")
            written.append(t)
            print(f"[map] wrote {t / 'map.png'} + data/map.ini (kn5 frame, {scope}: {len(sets[scope])} line(s), "
                  f"{scale:.3f} m/px)")
            # the CM outline of a layout follows the same scope (ledger 0054 P4 / A12)
            uid = root / "ui" / lid if lid else None
            if uid is not None and uid.is_dir():
                outlines[scope].save(uid / "outline.png")
                print(f"[map] wrote {uid / 'outline.png'} ({scope})")
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
