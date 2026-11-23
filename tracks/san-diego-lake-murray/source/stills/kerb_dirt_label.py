"""Label the kerb stills (kerb_dirt_stills_blend.py's PNGs + kerb_dirt_stills.json) as Blender stand-ins and write the JPGs
kerb_dirt_*.jpg beside them (ledger 0099). Pillow only.

    python tracks/san-diego-lake-murray/source/stills/kerb_dirt_label.py <render-dir> [<out-dir>]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    src = Path(argv[0])
    out = Path(argv[1]) if len(argv) > 1 else src
    side = json.loads((src / "kerb_dirt_stills.json").read_text(encoding="utf-8"))
    big, small = font(26), font(19)
    for s in side["stills"]:
        im = Image.open(src / s["png"]).convert("RGB")
        w, h = im.size
        lv = "/".join(f"{m:g}" for m in s["m_by_level"])
        head = (f"BLENDER STAND-IN, not Assetto Corsa  |  Lake Murray {side['blend_version']} race kerbs as built "
                f"(loop.blend)  |  {s['kerb']}")
        body = (f"{s['what']}. Kerb {s['kerb_length_m']:g} m; metres at rubber level 0/1/2/3: {lv}. Eye {side['eye_m']:g} m, "
                f"{s['lateral_from_kerb_m']:g} m in from the kerb, fov {side['fov_deg']:g} deg; sun az "
                f"{side['sun']['azimuth_deg']:g} el {side['sun']['elevation_deg']:g} ({side['sun']['as']}).")
        probe = ImageDraw.Draw(im)
        lines, cur = [], ""
        for word in body.split(" "):                    # wrap the caption to the picture's width
            t = (cur + " " + word).strip()
            if probe.textlength(t, font=small) > w - 32 and cur:
                lines.append(cur)
                cur = word
            else:
                cur = t
        lines.append(cur)
        bar = 20 + 34 + 26 * len(lines)
        canvas = Image.new("RGB", (w, h + bar), (18, 18, 18))
        canvas.paste(im, (0, 0))
        d = ImageDraw.Draw(canvas)
        d.text((16, h + 10), head, fill=(255, 210, 80), font=big)
        for k, ln in enumerate(lines):
            d.text((16, h + 46 + 26 * k), ln, fill=(225, 225, 225), font=small)
        jpg = out / (Path(s["png"]).stem + ".jpg")
        canvas.save(jpg, quality=90, optimize=True)
        print(f"[kerb-label] {jpg} ({jpg.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
