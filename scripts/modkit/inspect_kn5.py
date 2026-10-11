"""Measure a kn5 the way the study kit needs (fleet/REALISM.md R1).

``extract_kn5`` materialises geometry for reuse; this module *measures* it and throws it away.
Different decode strategy on the same format: skip every blob we don't need (texture bytes, visual
vertex data), keep everything extract discards (shader property values, isRenderable, bounding
spheres, texture dimensions). The point is the numbers the fleet gates on:

  - per-surface mesh density on the PHYSICAL surfaces (median edge length, area-derived grid
    spacing) — the "Nordschleife physics road is ~0.5 m" class of fact, measured not quoted
  - the invisible-physics-mesh split (isRenderable=false but surface-prefixed)
  - per-material shader + scalar params + texture sizes (the Kunos asphalt setup, copyable)
  - inventory pressure against the 65,535-vert cap (L7)

Vertex decode happens only for meshes whose name carries a physics prefix (digit + surface key,
the L7 rule), so a 700 MB SRP kn5 walks in seconds. The 65k cap bounds per-mesh decode cost.

    python -m scripts.modkit.inspect_kn5 <file.kn5>                    # report
    python -m scripts.modkit.inspect_kn5 <file.kn5> --json out.json    # machine-readable
    python -m scripts.modkit.inspect_kn5 <file.kn5> --detail '1ROAD'   # extra per-mesh detail
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from array import array
from pathlib import Path

from .extract_kn5 import _IDENT, _Reader, _matmul, _xform

# Surface keys AC ships defaults for; a track's own surfaces.ini extends this set (inspect_track
# passes the real keys in). Order longest-first so 'ROAD' can't shadow a longer key.
DEFAULT_SURFACE_KEYS = ["ROAD", "KERB", "GRASS", "SAND", "GRAVEL", "WALL", "ICE", "SNOW", "DIRT"]

_PREFIX_RX = re.compile(r"^(\d+)(.*)$")


def classify_surface(name: str, keys: list[str]) -> str | None:
    """AC physics rule: a mesh named <digits><KEY>... is physical, keyed to surfaces.ini KEY.
    Returns the matched KEY, 'PHYS?' for prefixed-but-unmatched, None for visual-only."""
    m = _PREFIX_RX.match(name)
    if not m:
        return None
    rest = m.group(2).upper()
    for k in sorted(keys, key=len, reverse=True):
        if rest.startswith(k.upper()):
            return k.upper()
    return "PHYS?"


def _dds_dims(blob_head: bytes) -> tuple[int, int, str] | None:
    """(width, height, fourcc) from a DDS header, or None if not DDS."""
    if len(blob_head) < 96 or blob_head[:4] != b"DDS ":
        return None
    h = struct.unpack_from("<I", blob_head, 12)[0]
    w = struct.unpack_from("<I", blob_head, 16)[0]
    four = blob_head[84:88].decode("ascii", "replace").strip("\x00 ")
    return (w, h, four or "rgb")


def _pot(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def parse_stats(path: Path, *, surface_keys: list[str] | None = None,
                detail_rx: str | None = None) -> dict:
    """Single-pass stats over one kn5. Decodes vertices only for physical (or --detail) meshes."""
    keys = surface_keys or DEFAULT_SURFACE_KEYS
    drx = re.compile(detail_rx, re.I) if detail_rx else None
    d = Path(path).read_bytes()
    if d[:6] != b"sc6969":
        raise ValueError(f"not a kn5 (bad magic {d[:6]!r})")
    r = _Reader(d)
    r.o = 6
    version = r.i32()
    if version > 5:
        r.i32()

    textures = []                      # {name, bytes, w, h, fourcc, pot}
    for _ in range(r.i32()):
        r.i32()
        name = r.string()
        size = r.u32()
        dims = _dds_dims(d[r.o:r.o + 128])
        r.o += size                    # skip the blob itself
        t = {"name": name, "bytes": size}
        if dims:
            t.update({"w": dims[0], "h": dims[1], "fourcc": dims[2],
                      "pot": _pot(dims[0]) and _pot(dims[1])})
        textures.append(t)

    materials = []                     # {name, shader, props{name:valueA}, textures[(slot,name)]}
    for _ in range(r.u32()):
        name = r.string(); shader = r.string()
        r.blob(2); r.i32()
        props = {}
        for _ in range(r.u32()):
            pname = r.string()
            vals = struct.unpack_from("<10f", d, r.o)   # valueA f32, then vec2/vec3/vec4
            r.o += 40
            props[pname] = round(vals[0], 6)
        slots = []
        for _ in range(r.u32()):
            sname = r.string(); r.i32(); tname = r.string()
            slots.append((sname, tname))
        materials.append({"name": name, "shader": shader, "props": props, "textures": slots})

    meshes = []                        # inventory rows for every mesh; measured rows carry more
    nodes = []                         # every transform (class 1) node's name: the AC_* dummies live here

    def _measure(name: str, world: list[float], vcount: int, vo: int, idx: array) -> dict:
        """Decode positions, apply world transform, return area/edge/bbox stats."""
        raw = struct.unpack_from(f"<{vcount * 11}f", d, vo)
        pts = [_xform(world, raw[i * 11], raw[i * 11 + 1], raw[i * 11 + 2]) for i in range(vcount)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
        area = 0.0
        tris = len(idx) // 3
        for t in range(tris):
            a, b, c = pts[idx[t * 3]], pts[idx[t * 3 + 1]], pts[idx[t * 3 + 2]]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            cxp = uy * vz - uz * vy; cyp = uz * vx - ux * vz; czp = ux * vy - uy * vx
            area += math.sqrt(cxp * cxp + cyp * cyp + czp * czp) / 2.0
        stride = max(1, tris // 20000)
        edges = []
        for t in range(0, tris, stride):
            a, b, c = pts[idx[t * 3]], pts[idx[t * 3 + 1]], pts[idx[t * 3 + 2]]
            for p, q in ((a, b), (b, c), (c, a)):
                edges.append(math.dist(p, q))
        edges.sort()
        n = len(edges)
        pct = lambda f: edges[min(n - 1, int(f * n))] if n else 0.0
        return {
            "area_m2": round(area, 1),
            "edge_p10_m": round(pct(0.10), 3), "edge_med_m": round(pct(0.50), 3),
            "edge_p90_m": round(pct(0.90), 3),
            "grid_m": round(math.sqrt(2.0 * area / tris), 3) if tris else 0.0,
            "bbox_m": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1),
                       round(max(zs) - min(zs), 1)],
        }

    def read_node(parent: list[float]):
        ncls = r.u32(); name = r.string(); child_count = r.u32(); r.boolean()
        if ncls == 1:
            nodes.append(name)
            world = _matmul(r.matrix(), parent)
            for _ in range(child_count):
                read_node(world)
        elif ncls == 2:
            r.boolean(); r.boolean(); r.boolean()
            vcount = r.u32()
            vo = r.o
            r.o += vcount * 44
            icount = r.u32()
            surf = classify_surface(name, keys)
            want = surf is not None or (drx is not None and drx.search(name))
            idx = None
            if want:
                idx = array("H"); idx.frombytes(d[r.o:r.o + icount * 2])
                if sys.byteorder == "big":
                    idx.byteswap()
            r.o += icount * 2
            matid = r.u32(); r.u32(); r.f32(); r.f32()
            bs = struct.unpack_from("<4f", d, r.o); r.o += 16
            renderable = r.boolean()
            row = {"name": name, "verts": vcount, "tris": icount // 3, "matid": matid,
                   "surface": surf, "renderable": renderable,
                   "radius_m": round(bs[3], 1)}
            if want and vcount:
                row.update(_measure(name, parent, vcount, vo, idx))
            meshes.append(row)
            for _ in range(child_count):
                read_node(parent)
        elif ncls == 3:
            raise NotImplementedError(f"skinned mesh {name!r} — track kn5s are static; aborting walk")
        else:
            raise ValueError(f"unknown node class {ncls} at {r.o} ({name!r})")

    read_node(_IDENT)
    return {"file": str(path), "version": version, "file_bytes": len(d),
            "textures": textures, "materials": materials, "meshes": meshes, "nodes": nodes}


def summarize(parsed: dict, *, top: int = 12) -> dict:
    """Roll one kn5's stats up into the tables the report prints."""
    meshes = parsed["meshes"]
    mats = parsed["materials"]

    surfaces: dict[str, dict] = {}
    for m in meshes:
        if not m["surface"]:
            continue
        s = surfaces.setdefault(m["surface"], {"meshes": 0, "verts": 0, "tris": 0, "area_m2": 0.0,
                                               "invisible": 0, "edge_meds": [], "grids": []})
        s["meshes"] += 1; s["verts"] += m["verts"]; s["tris"] += m["tris"]
        s["area_m2"] += m.get("area_m2", 0.0)
        if not m["renderable"]:
            s["invisible"] += 1
        if m.get("edge_med_m"):
            s["edge_meds"].append((m["edge_med_m"], m["tris"]))
        if m.get("grid_m"):
            s["grids"].append((m["grid_m"], m["tris"]))
    for s in surfaces.values():
        for src, dst in (("edge_meds", "edge_med_m"), ("grids", "grid_m")):
            pairs = s.pop(src)
            tot = sum(w for _v, w in pairs)
            s[dst] = round(sum(v * w for v, w in pairs) / tot, 3) if tot else None
        s["area_m2"] = round(s["area_m2"], 1)

    by_shader: dict[str, dict] = {}
    for m in meshes:
        sh = mats[m["matid"]]["shader"] if m["matid"] < len(mats) else "?"
        row = by_shader.setdefault(sh, {"meshes": 0, "tris": 0})
        row["meshes"] += 1; row["tris"] += m["tris"]

    over = [m["name"] for m in meshes if m["verts"] > 60000]
    npot = [t["name"] for t in parsed["textures"] if t.get("pot") is False]
    return {
        "meshes": len(meshes), "verts": sum(m["verts"] for m in meshes),
        "tris": sum(m["tris"] for m in meshes),
        "textures": len(parsed["textures"]),
        "texture_bytes": sum(t["bytes"] for t in parsed["textures"]),
        "materials": len(mats),
        "surfaces": surfaces,
        "shaders_by_tris": dict(sorted(by_shader.items(), key=lambda kv: -kv[1]["tris"])[:top]),
        "near_vert_cap": over, "non_pot_textures": npot,
    }


def format_report(parsed: dict, summ: dict) -> str:
    out = [f"{Path(parsed['file']).name}  (kn5 v{parsed['version']}, "
           f"{parsed['file_bytes'] / 1e6:.1f} MB): "
           f"{summ['meshes']} meshes, {summ['verts']:,} v, {summ['tris']:,} tri, "
           f"{summ['textures']} textures ({summ['texture_bytes'] / 1e6:.0f} MB), "
           f"{summ['materials']} materials"]
    if summ["surfaces"]:
        out.append("  physical surfaces:")
        out.append(f"    {'KEY':<8} {'meshes':>6} {'invis':>5} {'verts':>9} {'tris':>9} "
                   f"{'area m2':>10} {'edge med':>8} {'grid':>6}")
        for k, s in sorted(summ["surfaces"].items(), key=lambda kv: -kv[1]["area_m2"]):
            out.append(f"    {k:<8} {s['meshes']:>6} {s['invisible']:>5} {s['verts']:>9,} "
                       f"{s['tris']:>9,} {s['area_m2']:>10,.0f} "
                       f"{s['edge_med_m'] if s['edge_med_m'] is not None else '-':>8} "
                       f"{s['grid_m'] if s['grid_m'] is not None else '-':>6}")
    out.append("  shaders by tris: " + ", ".join(
        f"{sh} ({v['tris']:,}t/{v['meshes']}m)" for sh, v in summ["shaders_by_tris"].items()))
    if summ["near_vert_cap"]:
        out.append(f"  ! near 65k vert cap: {', '.join(summ['near_vert_cap'][:6])}")
    if summ["non_pot_textures"]:
        out.append(f"  ! non-PoT textures: {', '.join(summ['non_pot_textures'][:6])}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure an AC kn5 (density, surfaces, materials).")
    ap.add_argument("kn5", type=Path)
    ap.add_argument("--detail", help="regex of extra mesh names to fully measure")
    ap.add_argument("--json", type=Path, help="write full stats as JSON")
    ap.add_argument("--materials", action="store_true", help="dump material shader params")
    args = ap.parse_args()

    parsed = parse_stats(args.kn5, detail_rx=args.detail)
    summ = summarize(parsed)
    print(format_report(parsed, summ))
    if args.materials:
        for m in parsed["materials"]:
            texs = ", ".join(f"{s}={t}" for s, t in m["textures"])
            props = ", ".join(f"{k}={v}" for k, v in m["props"].items() if v)
            print(f"  [{m['shader']}] {m['name']}: {props}  |  {texs}")
    if args.json:
        parsed["summary"] = summ
        args.json.write_text(json.dumps(parsed, indent=1), encoding="utf-8")
        print(f"  -> {args.json}")


if __name__ == "__main__":
    main()
