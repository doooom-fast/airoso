"""Pack the two Lake Murray release zips (full + CC0) and the unchanged freeway zip from a track folder.

The procedure docs/PUBLISHING.md describes, as one deterministic command, so a config-only change
(lights, GrassFX) re-packs in seconds instead of being redone by hand:

    python tools/pack_release.py --version 0.23.0 [--src <track folder>] [--out <dir>] [--with-race]

  full/  <slug>_v<ver>.zip   the folder as installed (third-party TreeFX models + mined textures
                             included; CREDITS.txt names every third-party item)
  cc0/   <slug>_v<ver>.zip   the variant with the mined content swapped out: extension/trees/*.bin
                             stripped, the [TREES] lines commented out with a bring-your-own README,
                             the two mined texture pairs swapped for CC0 bytes under the same names
                             (tools/repack_kn5_textures.py), CC0 credits/licences. By default it is
                             Lake Murray Free Roam only; --with-race keeps the two race layouts, their
                             _race / _closure_* kn5s and the K-rail credit in it
  <freeway>_v0.5.0.zip       the freeway network, unchanged since v0.21.0, re-zipped from its
                             installed folder because only the latest release's assets show on the site

THE SPLIT IS A TOOL, NOT A RULE (Kevin, 2026-10-11: "No one actually cares about assets in free mods for a
13 year old game"). Asset provenance never withholds or degrades a release: this command builds both zips,
and which one goes public — the full one, the CC0 one, with or without the race layouts — is Kevin's call at
publish time (publishing itself is still his go, per release). --with-race is opt-in only because the
public catalog text in prodrive-server still describes one layout; the default stays street-only until
Kevin says otherwise.

Release texts live in tracks/<slug>/release/{full,cc0}/ (README.txt, CREDITS.txt, LICENSES.md) and
release/cc0/trees-README.txt. Where the race layouts change the words, a text carries both alternatives as
`[[street-only]] ... [[/street-only]]` and `[[with-race]] ... [[/with-race]]` blocks (each marker on its own
line); render_variant keeps the one the package is and drops the other. Every preview.svg an older engine left as its fallback — the root ui/ of a
single-layout folder AND each layout's ui/<id>/ of a multi-layout one (ledger 0047: street, race_cw,
race_acw) — is rasterised to preview.png beside it with scripts/ac/svg_raster.py (the drawer
track_folder itself now uses on every OS, so a fresh pack has no SVG left); Content Manager never
reads the SVG.
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


def rasterize_previews(ui_root: Path) -> list[str]:
    """rasterize_preview over ui/ itself and every layout directory ui/<id>/ — a multi-layout folder has
    no root preview, one per layout. Returns the ui-relative dirs that held an SVG."""
    done = []
    for d in [ui_root] + (sorted(p for p in ui_root.iterdir() if p.is_dir()) if ui_root.is_dir() else []):
        if (d / "preview.svg").exists():
            rasterize_preview(d)
            done.append(d.relative_to(ui_root).as_posix())
    return done


def rasterize_preview(ui: Path) -> None:
    svg = ui / "preview.svg"
    if not svg.exists():
        return
    if (ui / "preview.png").exists():
        # the engine wrote a real preview (the OSM street map) and the SVG is a stale fallback:
        # never overwrite the real picture with the polyline sketch
        svg.unlink()
        return
    # the engine's own Pillow drawer (scripts/ac/svg_raster.py — track_folder uses it too since the
    # 0047 fix round, so a fresh engine pack carries preview.png already; this remains for older folders)
    if str(AIROSO) not in sys.path:
        sys.path.insert(0, str(AIROSO))
    from scripts.ac.svg_raster import rasterize_svg
    if not rasterize_svg(svg.read_text(encoding="utf-8"), ui / "preview.png"):
        raise SystemExit(f"[pack] {svg}: nothing drawable — no preview.png")
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
    """The street-only CC0 package (the default; --with-race skips this): drop the race layouts and every
    race-furniture kn5 — san_diego_lake_murray_race.kn5, EVERY san_diego_lake_murray_closure_*.kn5 (ledger
    0049: one per race direction — matched by name, so a closure of a layout no longer declared goes too), and
    every models_<id>.ini / ui/<id>/ / <id>/ / <slug>__<id>.kn5 of a layout with race_furniture: true; the street
    layout stays. A packaging choice, not a licence verdict: which package goes public is Kevin's call at
    publish time (module docstring). Returns the relative paths removed. Refuses to leave the folder without a
    layout."""
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
    for p in sorted(folder.glob(f"{SLUG}_race_*.kn5")):      # a lap's common set (ledger 0054: <slug>_race_<lap>.kn5)
        _rm(p)
    for p in sorted(folder.glob(f"{SLUG}_closure_*.kn5")):
        _rm(p)
    for lid in race_ids:
        for rel in (f"models_{lid}.ini", f"ui/{lid}", lid, f"{SLUG}__{lid}.kn5"):
            _rm(folder / rel)
    if race_ids and not any((folder / f"models_{lid}.ini").exists() for lid in keep_ids):
        raise SystemExit(f"[pack] cc0: dropping {race_ids} would leave no layout ini — refusing")
    return removed


_VARIANT_RE = re.compile(r"^\[\[(street-only|with-race)\]\]\r?\n(.*?)^\[\[/\1\]\]\r?\n", re.S | re.M)
_MARKER_RE = re.compile(r"^\[\[/?(street-only|with-race)\]\]", re.M)


def render_variant(text: str, with_race: bool) -> str:
    """a release text as THIS package: keep the `[[with-race]]` blocks when the race layouts ship in it, else the
    `[[street-only]]` ones; the other kind is dropped, every marker line removed. A text without markers comes back
    unchanged (byte for byte, CRLF kept). An unbalanced or nested marker is a SystemExit — a half-rendered README
    never ships."""
    keep = "with-race" if with_race else "street-only"
    out = _VARIANT_RE.sub(lambda m: m.group(2) if m.group(1) == keep else "", text)
    if _MARKER_RE.search(out):
        raise SystemExit(f"[pack] unbalanced [[street-only]] / [[with-race]] markers: {_MARKER_RE.search(out).group(0)}")
    return out


def copy_text(src: Path, dst: Path, with_race: bool) -> None:
    dst.write_bytes(render_variant(src.read_bytes().decode("utf-8"), with_race).encode("utf-8"))


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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="asset version suffix, e.g. 0.23.0")
    ap.add_argument("--src", type=Path, default=AC_TRACKS / f"{SLUG}_v3", help="track folder to pack (default: the installed _v3)")
    ap.add_argument("--freeway", type=Path, default=AC_TRACKS / "san_diego_freeway")
    ap.add_argument("--out", type=Path, default=GH / "k10-sd-v021/project/build/release")
    ap.add_argument("--with-race", action="store_true",
                    help="keep the race layouts (and their _race / _closure_* kn5s, K-rail credit) in the CC0 package "
                         "too; default: the CC0 package is Lake Murray Free Roam only. Kevin decides at publish time")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    texts = TRACK_DIR / "release"
    out = a.out
    stage = out / "_stage"
    shutil.rmtree(stage, ignore_errors=True)
    (out / "full").mkdir(parents=True, exist_ok=True); (out / "cc0").mkdir(parents=True, exist_ok=True)

    full = stage / "full" / SLUG
    shutil.copytree(a.src, full, ignore=shutil.ignore_patterns("*.pre-*"))
    for rel in rasterize_previews(full / "ui"):
        print(f"[pack] full: ui/{rel + '/' if rel != '.' else ''}preview.svg -> preview.png")
    for f in ("README.txt", "CREDITS.txt", "LICENSES.md"):
        copy_text(texts / "full" / f, full / f, with_race=True)     # the full package is the installed folder: every layout
    print("[pack] full:")
    zip_folder(full, out / "full" / f"{SLUG}_v{a.version}.zip")

    cc0 = stage / "cc0" / SLUG
    shutil.copytree(full, cc0)
    if a.with_race:
        print("[pack] cc0: --with-race — the race layouts, the _race kn5 and every _closure_* kn5 stay in this package")
    else:
        for rel in strip_race_layouts(cc0):
            print(f"[pack] cc0: dropped {rel} (street-only CC0 package, the default; --with-race keeps the race layouts)")
    for b in (cc0 / "extension" / "trees").glob("*.bin"):
        b.unlink()
    shutil.copy(texts / "cc0" / "trees-README.txt", cc0 / "extension" / "trees" / "README.txt")
    for f in ("README.txt", "CREDITS.txt", "LICENSES.md"):
        copy_text(texts / "cc0" / f, cc0 / f, with_race=a.with_race)
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
