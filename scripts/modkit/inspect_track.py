"""Measure an installed AC track FOLDER — the study kit's per-track instrument (REALISM.md R1).

``inspect_kn5`` measures one model file; this walks the whole shipped artifact the way AC loads
it: every kn5 named by models*.ini, every surfaces.ini (the FEEL parameters), the AI lines, the
CSP ext_config features, the VAO patch, the UI card. Output is the per-track row of the reference
shelf — our tracks and the masters', measured with the same ruler.

    python -m scripts.modkit.inspect_track "D:/.../content/tracks/ks_laguna_seca"
    python -m scripts.modkit.inspect_track <dir> --json fleet/reference/raw/<slug>.json

Feel parameters read per surface: FRICTION, DAMPING, WAV(+PITCH), SIN_HEIGHT/SIN_LENGTH (the
procedural bump texture), VIBRATION_GAIN/LENGTH (FFB), _EXT_SURFACE_TYPE (CSP SurfacesFX — the
2026 gravel path the rally stages want). AI spacing comes from the fast_lane.ai v7 header + the
cumulative length field, no full decode.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from .inspect_kn5 import DEFAULT_SURFACE_KEYS, parse_stats, summarize

SURFACE_PARAMS = ["FRICTION", "DAMPING", "WAV", "WAV_PITCH", "SIN_HEIGHT", "SIN_LENGTH",
                  "VIBRATION_GAIN", "VIBRATION_LENGTH", "DIRT_ADDITIVE", "IS_VALID_TRACK",
                  "_EXT_SURFACE_TYPE"]


def _read_text(path: Path) -> str:
    """AC configs arrive in UTF-8, UTF-8-BOM, UTF-16 or latin-1 depending on the author's editor."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    return raw.decode("utf-8", "replace")


def parse_ini(path: Path) -> dict[str, dict[str, str]]:
    """Tolerant AC-flavoured INI: [SECTION], KEY=VALUE, ';' and '//' comments, dup sections merged."""
    out: dict[str, dict[str, str]] = {}
    sect = ""
    for line in _read_text(path).splitlines():
        line = line.split(";")[0].split("//")[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            sect = line[1:-1].strip().upper()
            out.setdefault(sect, {})
        elif "=" in line:
            k, v = line.split("=", 1)
            out.setdefault(sect, {})[k.strip().upper()] = v.strip()
    return out


def read_models(track: Path) -> dict[str, list[str]]:
    """{layout_name: [kn5 filenames]} from models*.ini; AC's no-ini default is <dirname>.kn5."""
    out: dict[str, list[str]] = {}
    for ini in sorted(track.glob("models*.ini")):
        layout = ini.stem.replace("models", "").strip("_") or "default"
        files = [s["FILE"] for s in parse_ini(ini).values() if s.get("FILE")]
        if files:
            out[layout] = files
    if not out:
        cand = track / f"{track.name}.kn5"
        if cand.exists():
            out["default"] = [cand.name]
    return out


def read_surfaces(track: Path) -> dict[str, dict]:
    """Union of every surfaces.ini under the track (layouts carry their own): KEY -> params."""
    keys: dict[str, dict] = {}
    for ini in sorted(track.glob("**/surfaces.ini")):
        for sect, kv in parse_ini(ini).items():
            if not sect.startswith("SURFACE") or "KEY" not in kv:
                continue
            row = {p: kv[p] for p in SURFACE_PARAMS if p in kv}
            row["_from"] = str(ini.relative_to(track))
            keys.setdefault(kv["KEY"].upper(), row)
    return keys


def read_ai(track: Path) -> list[dict]:
    """Every fast_lane/pit_lane .ai under the track: version, points, spacing from length field."""
    out = []
    for ai in sorted(track.glob("**/*.ai")):
        d = ai.read_bytes()
        if len(d) < 16:
            continue
        ver, count = struct.unpack_from("<2i", d, 0)
        row = {"file": str(ai.relative_to(track)), "version": ver, "points": count}
        if ver == 7 and count > 1 and len(d) >= 16 + count * 20:
            first = struct.unpack_from("<f", d, 16 + 12)[0]
            last = struct.unpack_from("<f", d, 16 + (count - 1) * 20 + 12)[0]
            length = last - first
            row["length_m"] = round(length, 1)
            row["spacing_m"] = round(length / (count - 1), 2)
            row["has_extras"] = len(d) > 16 + count * 20 + 4
        out.append(row)
    return out


def read_ext_config(track: Path) -> dict:
    """CSP feature floor from every ext_config.ini (track dir + skins are out of scope)."""
    feats = {"grass_fx": False, "rain_fx": False, "lights": 0, "light_series": 0,
             "trees": False, "mesh_adjustments": 0, "includes": [], "files": 0}
    for ini in sorted(track.glob("**/ext_config.ini")):
        feats["files"] += 1
        cfg = parse_ini(ini)
        for sect, kv in cfg.items():
            if sect.startswith("GRASS_FX"):
                feats["grass_fx"] = True
            elif sect.startswith("RAIN_FX"):
                feats["rain_fx"] = True
            elif sect.startswith("LIGHT_SERIES"):
                feats["light_series"] += 1
            elif sect.startswith("LIGHT_"):
                feats["lights"] += 1
            elif sect.startswith("TREE"):
                feats["trees"] = True
            elif sect.startswith("MESH_ADJUSTMENT"):
                feats["mesh_adjustments"] += 1
            elif sect.startswith("INCLUDE"):
                feats["includes"] += [v for k, v in kv.items() if k.startswith("INCLUDE")]
    return feats


def read_ui(track: Path) -> dict:
    for ui in sorted(track.glob("ui/**/ui_track.json")):
        try:
            j = json.loads(_read_text(ui))
            return {k: j.get(k) for k in ("name", "length", "width", "pitboxes", "run")}
        except Exception:
            continue
    return {}


def inspect(track: Path, *, kn5_detail: str | None = None) -> dict:
    models = read_models(track)
    surfaces_ini = read_surfaces(track)
    keys = sorted(set(DEFAULT_SURFACE_KEYS) | set(surfaces_ini))

    kn5_names = sorted({f for files in models.values() for f in files})
    kn5s, agg_surf, errors = [], {}, []
    tot = {"meshes": 0, "verts": 0, "tris": 0, "bytes": 0, "texture_bytes": 0}
    for fname in kn5_names:
        fpath = track / fname
        if not fpath.exists():
            errors.append(f"{fname}: named by models.ini but missing")
            continue
        try:
            parsed = parse_stats(fpath, surface_keys=keys, detail_rx=kn5_detail)
        except Exception as e:                        # skinned mesh, corrupt file: keep going
            errors.append(f"{fname}: {e}")
            continue
        summ = summarize(parsed)
        kn5s.append({"file": fname, "summary": summ})
        tot["meshes"] += summ["meshes"]; tot["verts"] += summ["verts"]
        tot["tris"] += summ["tris"]; tot["bytes"] += parsed["file_bytes"]
        tot["texture_bytes"] += summ["texture_bytes"]
        for k, s in summ["surfaces"].items():
            a = agg_surf.setdefault(k, {"meshes": 0, "invisible": 0, "verts": 0, "tris": 0,
                                        "area_m2": 0.0, "_wed": 0.0, "_wgr": 0.0, "_wt": 0})
            for f in ("meshes", "invisible", "verts", "tris"):
                a[f] += s[f]
            a["area_m2"] += s["area_m2"]
            if s["edge_med_m"] is not None:
                a["_wed"] += s["edge_med_m"] * s["tris"]; a["_wt"] += s["tris"]
            if s["grid_m"] is not None:
                a["_wgr"] += s["grid_m"] * s["tris"]
    for a in agg_surf.values():
        wt = a.pop("_wt"); wed = a.pop("_wed"); wgr = a.pop("_wgr")
        a["edge_med_m"] = round(wed / wt, 3) if wt else None
        a["grid_m"] = round(wgr / wt, 3) if wt else None
        a["area_m2"] = round(a["area_m2"], 1)

    return {
        "track": track.name, "path": str(track), "ui": read_ui(track),
        "layouts": models, "kn5_count": len(kn5_names), "totals": tot,
        "surfaces_ini": surfaces_ini, "surface_geometry": agg_surf,
        "ai": read_ai(track), "ext_config": read_ext_config(track),
        "vao_patches": [p.name for p in track.glob("*.vao-patch")],
        "cameras": sum(1 for s in (parse_ini(c) for c in track.glob("**/cameras*.ini"))
                       for name in s if name.startswith("CAMERA_")),
        "errors": errors, "kn5s": kn5s,
    }


def format_track_report(t: dict) -> str:
    ui = t["ui"]
    out = [f"== {t['track']}  ({ui.get('name') or '?'}; length {ui.get('length') or '?'}, "
           f"pitboxes {ui.get('pitboxes') or '?'})",
           f"   {t['kn5_count']} kn5 / {t['totals']['bytes'] / 1e6:,.0f} MB "
           f"({t['totals']['texture_bytes'] / 1e6:,.0f} MB textures) -- "
           f"{t['totals']['meshes']:,} meshes, {t['totals']['verts']:,} v, "
           f"{t['totals']['tris']:,} tri; layouts: {', '.join(t['layouts']) or '-'}"]
    if t["surface_geometry"]:
        out.append(f"   {'SURFACE':<8} {'meshes':>6} {'invis':>5} {'verts':>10} {'tris':>10} "
                   f"{'area m2':>11} {'edge med':>8} {'grid':>6}")
        for k, s in sorted(t["surface_geometry"].items(), key=lambda kv: -kv[1]["area_m2"]):
            out.append(f"   {k:<8} {s['meshes']:>6} {s['invisible']:>5} {s['verts']:>10,} "
                       f"{s['tris']:>10,} {s['area_m2']:>11,.0f} "
                       f"{s['edge_med_m'] if s['edge_med_m'] is not None else '-':>8} "
                       f"{s['grid_m'] if s['grid_m'] is not None else '-':>6}")
    if t["surfaces_ini"]:
        rows = []
        for k, p in sorted(t["surfaces_ini"].items()):
            bits = [f"fric={p.get('FRICTION', '?')}"]
            if p.get("DAMPING") not in (None, "0"):
                bits.append(f"damp={p['DAMPING']}")
            if p.get("WAV"):
                bits.append(f"wav={p['WAV']}@{p.get('WAV_PITCH', '1')}")
            if p.get("SIN_HEIGHT") not in (None, "0"):
                bits.append(f"sin={p['SIN_HEIGHT']}x{p.get('SIN_LENGTH', '?')}")
            if p.get("VIBRATION_GAIN") not in (None, "0"):
                bits.append(f"vib={p['VIBRATION_GAIN']}x{p.get('VIBRATION_LENGTH', '?')}")
            if p.get("_EXT_SURFACE_TYPE"):
                bits.append(f"SFX={p['_EXT_SURFACE_TYPE']}")
            rows.append(f"     {k:<10} " + " ".join(bits))
        out.append("   surfaces.ini:")
        out.extend(rows)
    ai = t["ai"]
    if ai:
        for a in ai:
            sp = f", {a['spacing_m']} m spacing over {a['length_m']:,.0f} m" if "spacing_m" in a else ""
            out.append(f"   ai: {a['file']} v{a['version']}, {a['points']:,} pts{sp}")
    else:
        out.append("   ai: NONE")
    e = t["ext_config"]
    csp = [f"grass_fx={'yes' if e['grass_fx'] else 'NO'}", f"rain_fx={'yes' if e['rain_fx'] else 'NO'}",
           f"lights={e['lights']}+{e['light_series']}srs", f"trees={'yes' if e['trees'] else 'no'}",
           f"vao={'yes' if t['vao_patches'] else 'NO'}", f"cameras={t['cameras']}"]
    out.append("   csp/presentation: " + "  ".join(csp))
    for err in t["errors"]:
        out.append(f"   ! {err}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure an installed AC track folder.")
    ap.add_argument("track", type=Path)
    ap.add_argument("--json", type=Path, help="write full stats (incl. per-kn5) as JSON")
    ap.add_argument("--detail", help="regex of extra mesh names to fully measure in every kn5")
    args = ap.parse_args()

    t = inspect(args.track, kn5_detail=args.detail)
    print(format_track_report(t))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(t, indent=1), encoding="utf-8")
        print(f"   -> {args.json}")


if __name__ == "__main__":
    main()
