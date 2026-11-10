"""Cut one tools/menu_preview_blend.py render into a layout's AC menu files (Kevin 2026-11-07: "We need screenshots of the
tracks in the menus in AC"): preview_full.png = the render's centre crop at AC's 355:200, preview.png = that at 355x200
(Kunos' own size, LANCZOS), preview.json = the shot's sidecar (camera, sun, scenes, line) plus the cut.

    python tools/menu_preview_cut.py <render.png> <outdir>      # reads <render>.json beside the render
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

W, H = 355, 200


def cut(render: Path, outdir: Path) -> dict:
    side = json.loads(render.with_suffix(".json").read_text(encoding="utf-8"))
    im = Image.open(render).convert("RGB")
    w, h = im.size
    cw, ch = (w, w * H // W) if w * H // W <= h else (h * W // H, h)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    full = im.crop((x0, y0, x0 + cw, y0 + ch))
    outdir.mkdir(parents=True, exist_ok=True)
    full.save(outdir / "preview_full.png", optimize=True)
    full.resize((W, H), Image.LANCZOS).save(outdir / "preview.png", optimize=True)
    side["render"] = f"{side.get('render', 'EEVEE Next, AgX')} -> centre crop {cw}x{ch} (355:200) = preview_full.png " \
                     f"-> 355x200 LANCZOS = preview.png"
    side["source"] = ("Blender render of the installed build's split scenes, not an AC screenshot "
                      "(Kevin 2026-11-07: 'Render them in Blender')")
    side["script"] = "tools/menu_preview_blend.py + tools/menu_preview_cut.py"
    side["source"] += f" ({side.get('project', '?')}/blender/split)"
    (outdir / "preview.json").write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")
    return side


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    s = cut(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"[cut] {sys.argv[2]}: {s['layout']} {s['station']}")
