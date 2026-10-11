"""Pack the two Lake Murray release zips (full + CC0) and the unchanged freeway zip from a track folder.

The procedure docs/PUBLISHING.md describes, as one deterministic command, so a config-only change
(lights, GrassFX) re-packs in seconds instead of being redone by hand:

    python tools/pack_release.py --version 0.23.0 [--src <track folder>] [--out <dir>]

  full/  <slug>_v<ver>.zip   the folder as installed (third-party TreeFX models + mined textures
                             included — personal use; CREDITS.txt names every third-party item)
  cc0/   <slug>_v<ver>.zip   the redistributable variant: extension/trees/*.bin stripped, the
                             [TREES] lines commented out with a bring-your-own README, the two mined
                             texture pairs swapped for CC0 bytes under the same names
                             (tools/repack_kn5_textures.py), CC0 credits/licences
  <freeway>_v0.5.0.zip       the freeway network, unchanged since v0.21.0, re-zipped from its
                             installed folder because only the latest release's assets show on the site

Release texts live in tracks/<slug>/release/{full,cc0}/ (README.txt, CREDITS.txt, LICENSES.md) and
release/cc0/trees-README.txt. ui/preview.svg (the engine's fallback) is rasterised to preview.png —
Content Manager never reads the SVG.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

AIROSO = Path(__file__).resolve().parent.parent
GH = AIROSO.parent
AC_TRACKS = Path("D:/SteamLibrary/steamapps/common/assettocorsa/content/tracks")
SLUG = "san_diego_lake_murray"
TRACK_DIR = AIROSO / "tracks" / "san-diego-lake-murray"
FREEWAY_FILES = ["CREDITS.txt", "LICENSES.md", "README.txt", "ai/README.txt", "data/map.ini", "data/surfaces.ini",
                 "extension/ext_config.ini", "map.png", "models.ini", "san_diego_freeway.kn5", "ui/outline.png",
                 "ui/preview.png", "ui/ui_track.json"]
# CC0 bytes for the two mined pairs the V3 kn5 binds (names kept so the material bindings survive)
TEXTURE_SWAPS = {
    "asphalt_cracked_diffuse.jpg": GH / "engine-july/assets/textures/asphalt_diffuse.jpg",      # Poly Haven aerial_asphalt_01
    "asphalt_cracked_normal.jpg": GH / "engine-july/assets/textures/asphalt_normal.jpg",
    "building_diffuse.jpg": GH / "_salvage/k10-sd-v021/assets/textures/building_diffuse.jpg",   # ambientCG Concrete034
    "building_normal.jpg": GH / "_salvage/k10-sd-v021/assets/textures/building_normal.jpg",
}


def rasterize_preview(ui: Path) -> None:
    svg = ui / "preview.svg"
    if not svg.exists():
        return
    from PIL import Image, ImageDraw
    s = svg.read_text(encoding="utf-8")
    w = int(re.search(r'width="(\d+)"', s).group(1)); h = int(re.search(r'height="(\d+)"', s).group(1))
    bg = re.search(r'<rect[^>]*fill="(#[0-9a-fA-F]{6})"', s)
    im = Image.new("RGB", (w, h), bg.group(1) if bg else "#0c1116"); d = ImageDraw.Draw(im)
    for m in re.finditer(r'<polyline([^>]*)points="([^"]+)"([^>]*)/?>', s):
        attrs = m.group(1) + m.group(3)
        stroke = re.search(r'stroke="([^"]+)"', attrs); width = re.search(r'stroke-width="([\d.]+)"', attrs)
        pts = [tuple(map(float, p.split(","))) for p in m.group(2).split()]
        d.line(pts, fill=(stroke.group(1) if stroke else "#ffffff"), width=max(1, round(float(width.group(1)) if width else 2)), joint="curve")
    im.save(ui / "preview.png", optimize=True)
    svg.unlink()


def disable_treefx(ini: Path) -> None:
    s = ini.read_text(encoding="utf-8")
    sec = re.search(r"(\[TREES\]\r?\n)(.*?)(?=\r?\n\[|\Z)", s, re.S)
    if not sec:
        raise SystemExit("[pack] no [TREES] section in ext_config.ini")
    body = sec.group(2)
    body = re.sub(r"^(LIST_0\s*=)", r";\1", body, flags=re.M)
    body = re.sub(r"^(SURFACE_MATERIALS\s*=)", r";\1", body, flags=re.M)
    body = re.sub(r"^;.*personal-use.*$", "; placements kept in trees/trees.txt, no models shipped — see trees/README.txt to enable with your own",
                  body, flags=re.M)
    ini.write_text(s[:sec.start(2)] + body + s[sec.end(2):], encoding="utf-8")


def strip_race_layouts(folder: Path, cfg_path: Path = TRACK_DIR / "track.config.json") -> list[str]:
    """CC0 variant: drop the race layouts and the race-furniture kn5. The K-rail pack the strips sweep
    (assets/models/concrete_barrier_4m.obj + its two PNGs) has an UNRECORDED licence
    (assets/licenses.json, ledger 0047 Q10), so san_diego_lake_murray_race.kn5, every
    models_<id>.ini / ui/<id>/ / <id>/ / <slug>__<id>.kn5 of a layout with race_furniture: true leave
    the public package; the street layout stays. Returns the relative paths removed. Refuses to leave
    the folder without a layout."""
    layouts = json.loads(cfg_path.read_text(encoding="utf-8")).get("layouts", []) or []
    race_ids = [str(lo["id"]) for lo in layouts if isinstance(lo, dict) and lo.get("race_furniture")]
    keep_ids = [str(lo["id"]) for lo in layouts if isinstance(lo, dict) and not lo.get("race_furniture")]
    removed: list[str] = []

    def _rm(p: Path):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        else:
            return
        removed.append(str(p.relative_to(folder)).replace("\\", "/"))

    _rm(folder / f"{SLUG}_race.kn5")
    for lid in race_ids:
        for rel in (f"models_{lid}.ini", f"ui/{lid}", lid, f"{SLUG}__{lid}.kn5"):
            _rm(folder / rel)
    if race_ids and not any((folder / f"models_{lid}.ini").exists() for lid in keep_ids):
        raise SystemExit(f"[pack] cc0: dropping {race_ids} would leave no layout ini — refusing")
    return removed


def zip_folder(folder: Path, out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                p = Path(root) / f
                z.write(p, f"{folder.name}/{p.relative_to(folder).as_posix()}")
    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        names = z.namelist()
    print(f"  {out.name}: {out.stat().st_size / 1e6:.1f} MB, {len(names)} entries, testzip {'OK' if bad is None else bad}, "
          f"bins {sum(n.endswith('.bin') for n in names)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="asset version suffix, e.g. 0.23.0")
    ap.add_argument("--src", type=Path, default=AC_TRACKS / f"{SLUG}_v3", help="track folder to pack (default: the installed _v3)")
    ap.add_argument("--freeway", type=Path, default=AC_TRACKS / "san_diego_freeway")
    ap.add_argument("--out", type=Path, default=GH / "k10-sd-v021/project/build/release")
    a = ap.parse_args()
    texts = TRACK_DIR / "release"
    out = a.out
    stage = out / "_stage"
    shutil.rmtree(stage, ignore_errors=True)
    (out / "full").mkdir(parents=True, exist_ok=True); (out / "cc0").mkdir(parents=True, exist_ok=True)

    full = stage / "full" / SLUG
    shutil.copytree(a.src, full, ignore=shutil.ignore_patterns("*.pre-*"))
    rasterize_preview(full / "ui")
    for f in ("README.txt", "CREDITS.txt", "LICENSES.md"):
        shutil.copy(texts / "full" / f, full / f)
    print("[pack] full:")
    zip_folder(full, out / "full" / f"{SLUG}_v{a.version}.zip")

    cc0 = stage / "cc0" / SLUG
    shutil.copytree(full, cc0)
    for rel in strip_race_layouts(cc0):
        print(f"[pack] cc0: dropped {rel} (race layouts stay in the FULL package until the K-rail pack's licence is recorded — 0047 Q10)")
    for b in (cc0 / "extension" / "trees").glob("*.bin"):
        b.unlink()
    shutil.copy(texts / "cc0" / "trees-README.txt", cc0 / "extension" / "trees" / "README.txt")
    for f in ("README.txt", "CREDITS.txt", "LICENSES.md"):
        shutil.copy(texts / "cc0" / f, cc0 / f)
    disable_treefx(cc0 / "extension" / "ext_config.ini")
    kn5 = cc0 / f"{SLUG}.kn5"
    swaps = [f"{name}={path}" for name, path in TEXTURE_SWAPS.items()]
    subprocess.run([sys.executable, str(AIROSO / "tools" / "repack_kn5_textures.py"), str(kn5), str(kn5) + ".new", *swaps], check=True)
    os.replace(str(kn5) + ".new", kn5)
    print("[pack] cc0:")
    zip_folder(cc0, out / "cc0" / f"{SLUG}_v{a.version}.zip")

    fw = stage / "freeway" / "san_diego_freeway"
    fw.mkdir(parents=True)
    for rel in FREEWAY_FILES:
        (fw / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(a.freeway / rel, fw / rel)
    print("[pack] freeway (unchanged):")
    zip_folder(fw, out / "san_diego_freeway_v0.5.0.zip")
    shutil.rmtree(stage)
    print(f"[pack] done -> {out}")


if __name__ == "__main__":
    main()
