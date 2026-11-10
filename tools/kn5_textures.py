"""Is every texture a kn5's materials name embedded in it? (ledger 0082, Milford furniture pass 2)

Why it exists: the PC's first rehearsal of Milford 0.1.1 (ledger 0082-1) built a road kn5 35,910 B short. Five textures
were named by its materials (ghost_alpha.png on the four 1WALL_GHOST_RAIL colliders, wbeam_rail_diffuse.png,
metal_wall_diffuse.jpg, metal_wall_normal.jpg, roof_tan_diffuse.jpg) and not embedded: the engine snapshot (ENG) lacked
airoso's assets/textures, and pbr's stock table reads only ENG's. Every gate passed. In Assetto Corsa a material whose
texture is not in the kn5 takes the shader's fallback: the transparent ghost colliders would likely have shown as solid
walls. Only the byte count caught it.

READ-ONLY on the built artifact (L5): the kn5's texture section (type, name, bytes) and its materials' texture maps
(sampler, slot, name). Nothing else is parsed.

    missing      a (material, sampler, name) whose name is not an embedded texture's name (exact; a name that matches only
                 when the case is folded is listed apart, and still counts as missing)
    empty        a texture map with an empty name
    zero_bytes   an embedded texture with no data
    unused       embedded textures no material names (reported, never a failure)

Exit 1 when any kn5 has a missing / empty / zero-byte texture, 0 when every one is whole, 2 on an input error (no kn5,
a file that is not a kn5). Arguments are kn5 files or directories (a directory: its *.kn5, or every *.kn5 below it with
--recursive).

    python tools/kn5_textures.py <kn5 | dir> [...] [--recursive] [--json <out>]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


class Kn5Error(Exception):
    pass


def _reader(buf: bytes):
    pos = [0]

    def take(n):
        if pos[0] + n > len(buf):
            raise Kn5Error(f"truncated at byte {pos[0]} (wanted {n})")
        b = buf[pos[0]:pos[0] + n]
        pos[0] += n
        return b

    def u32():
        return struct.unpack("<I", take(4))[0]

    def s():
        n = u32()
        if n > 1 << 16:
            raise Kn5Error(f"a string {n} bytes long at byte {pos[0] - 4}: not a kn5 string")
        return take(n).decode("utf-8", errors="replace")

    def skip(n):
        take(n)
    return take, u32, s, skip


def read_kn5_textures(path: Path) -> dict:
    """{"version", "textures": [{"name", "bytes"}], "materials": [{"name", "shader", "maps": [[sampler, slot, name]]}]}"""
    buf = Path(path).read_bytes()
    take, u32, s, skip = _reader(buf)
    if take(6) != b"sc6969":
        raise Kn5Error("no sc6969 magic")
    ver = u32()
    if ver > 5:
        u32()                                    # version 6 carries one more int before the textures
    textures = []
    for _ in range(u32()):
        u32()                                    # texture type
        name = s()
        n = u32()
        skip(n)
        textures.append({"name": name, "bytes": n})
    materials = []
    for _ in range(u32()):
        name, shader = s(), s()
        take(1); take(1); take(4)                # blend mode, alpha tested, depth mode
        for _ in range(u32()):
            s(); skip(4 + 8 + 12 + 16)           # a property: name, a float and the 2-, 3- and 4-vectors
        maps = []
        for _ in range(u32()):
            sampler = s(); slot = u32(); tex = s()
            maps.append([sampler, slot, tex])
        materials.append({"name": name, "shader": shader, "maps": maps})
    return {"version": ver, "textures": textures, "materials": materials}


def check(path: Path) -> dict:
    k = read_kn5_textures(path)
    have = {t["name"] for t in k["textures"]}
    fold = {t["name"].lower() for t in k["textures"]}
    missing, empty, used = [], [], set()
    for m in k["materials"]:
        for sampler, slot, tex in m["maps"]:
            if not tex:
                empty.append({"material": m["name"], "sampler": sampler})
            elif tex in have:
                used.add(tex)
            else:
                missing.append({"material": m["name"], "sampler": sampler, "texture": tex,
                                "case_only": tex.lower() in fold})
    zero = [t["name"] for t in k["textures"] if t["bytes"] == 0]
    names = sorted({x["texture"] for x in missing})
    return {"kn5": str(path), "bytes": Path(path).stat().st_size, "version": k["version"],
            "textures_embedded": len(k["textures"]), "materials": len(k["materials"]),
            "maps": sum(len(m["maps"]) for m in k["materials"]),
            "missing_textures": names, "missing": missing, "empty": empty, "zero_bytes": zero,
            "unused": sorted(have - used), "ok": not (missing or empty or zero)}


def gather(args, recursive: bool) -> list[Path]:
    out = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            out += sorted(p.rglob("*.kn5") if recursive else p.glob("*.kn5"))
        elif p.is_file():
            out.append(p)
        else:
            raise Kn5Error(f"{p}: no such file or directory")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    try:
        files = gather(a.paths, a.recursive)
        if not files:
            raise Kn5Error(f"no kn5 under {' '.join(a.paths)}")
        rows = []
        for f in files:
            try:
                rows.append(check(f))
            except Kn5Error as e:
                rows.append({"kn5": str(f), "error": str(e), "ok": False})
    except Kn5Error as e:
        print(f"kn5_textures: {e}", file=sys.stderr)
        return 2
    bad = 0
    for r in rows:
        if "error" in r:
            print(f"ERROR {r['kn5']}: {r['error']}")
            continue
        verdict = "PASS" if r["ok"] else "FAIL"
        bad += not r["ok"]
        print(f"{verdict} {r['kn5']}: {r['bytes']:,} B, {r['textures_embedded']} textures embedded, {r['materials']} materials,"
              f" {r['maps']} maps; missing {len(r['missing_textures'])}, empty {len(r['empty'])}, zero-byte {len(r['zero_bytes'])},"
              f" unused {len(r['unused'])}")
        for t in r["missing_textures"]:
            mats = sorted({x["material"] for x in r["missing"] if x["texture"] == t})
            case = " (matches only with the case folded)" if any(x["case_only"] for x in r["missing"] if x["texture"] == t) else ""
            print(f"    missing {t}{case}: {len(mats)} material(s), e.g. {', '.join(mats[:4])}")
        for x in r["empty"][:5]:
            print(f"    empty map: {x['material']} {x['sampler']}")
        for t in r["zero_bytes"]:
            print(f"    zero-byte texture: {t}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"kn5s": rows, "ok": all(r["ok"] for r in rows)}, indent=1), encoding="utf-8")
    if any("error" in r for r in rows):
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
