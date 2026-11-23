"""Shared mesh helpers for the street-furniture makers (ledger 0096: Denver Grand Prix's signals, lamp classes,
sign plates and rail set). Pure Python, no Blender, no numpy: the makers write OBJ text and a test pins it.

A ``Model`` is an ordered list of named objects. Each object carries ONE material class (the ``usemtl`` name, which
is the pbr.TEXTURES prefix the engine is asked to bind) and its faces with per-corner UVs and smoothing groups, the
way ``tools/make_streetlight_led.py`` writes them (`s 1..n` smooth, `s off` flat). The difference from that maker:
one file holds several ``o`` objects, so a lens can be a separate NAMED mesh next to its housing.
``tools/author_lamps_blend.py``'s ``load_obj_full`` ignores ``o`` and would merge them; a placer that needs the
lenses apart reads the file with ``read_obj_objects`` below.

FRAME (L6): metres, +y up. Each maker states its own x and z.
"""
from __future__ import annotations

import math

FT = 0.3048
IN = 0.0254


def _normal(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def _unit(v):
    L = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / L for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


class Obj:
    """one named mesh: vertices, faces (indices, per-corner uv, smoothing group), a material class"""

    def __init__(self, name: str, material: str):
        self.name, self.material = name, material
        self.v: list[tuple[float, float, float]] = []
        self.f: list[tuple[tuple[int, ...], tuple[tuple[float, float], ...], int]] = []
        self._group = 0

    def new_group(self) -> int:
        self._group += 1
        return self._group

    def add_v(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def add_f_dir(self, idx, uv, group, outward):
        """orient so the face normal points along ``outward``"""
        idx, uv = list(idx), list(uv)
        n = _normal([self.v[i] for i in idx])
        if sum(n[k] * outward[k] for k in range(3)) < 0:
            idx.reverse()
            uv.reverse()
        self.f.append((tuple(idx), tuple(uv), group))

    def add_f(self, idx, uv, group, inside):
        """orient so the face normal points AWAY from the point ``inside``"""
        c = [sum(self.v[i][k] for i in idx) / len(idx) for k in range(3)]
        self.add_f_dir(idx, uv, group, tuple(c[k] - inside[k] for k in range(3)))

    def tris(self) -> int:
        return sum(len(f[0]) - 2 for f in self.f)

    def bounds(self):
        return tuple(min(p[k] for p in self.v) for k in range(3)), tuple(max(p[k] for p in self.v) for k in range(3))

    # ---- primitives -------------------------------------------------------------------------------------------
    def tube(self, path, radii, sides, cap_start=False, cap_end=True, smooth=True, arc=(0.0, 360.0), two_sided=False):
        """a round tube swept along ``path`` (3-D points) with one radius per point. ``arc`` (degrees) keeps only part
        of the wall (a tunnel visor); ``two_sided`` adds the inner wall so an open shell is seen from inside too."""
        g = self.new_group() if smooth else 0
        n = len(path)
        seg = [0.0]
        for i in range(1, n):
            seg.append(seg[-1] + math.dist(path[i], path[i - 1]))
        a0, a1 = math.radians(arc[0]), math.radians(arc[1])
        full = abs((arc[1] - arc[0]) - 360.0) < 1e-9
        cols = sides if full else sides + 1
        rings = []
        for i, c in enumerate(path):
            a, b = path[max(0, i - 1)], path[min(n - 1, i + 1)]
            t = _unit(tuple(b[k] - a[k] for k in range(3)))
            ref = (0.0, 0.0, 1.0) if abs(t[2]) < 0.9 else (1.0, 0.0, 0.0)
            n1 = _unit(_cross(ref, t))
            n2 = _cross(t, n1)
            ring = []
            for k in range(cols):
                ang = a0 + (a1 - a0) * k / sides
                ca, sa = math.cos(ang), math.sin(ang)
                ring.append(self.add_v(tuple(c[j] + radii[i] * (ca * n1[j] + sa * n2[j]) for j in range(3))))
            rings.append(ring)
        for i in range(n - 1):
            mid = tuple((path[i][k] + path[i + 1][k]) / 2 for k in range(3))
            for k in range(sides):
                k1 = (k + 1) % cols
                uv = ((k / sides, seg[i] / 4), ((k + 1) / sides, seg[i] / 4), ((k + 1) / sides, seg[i + 1] / 4), (k / sides, seg[i + 1] / 4))
                idx = (rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k])
                self.add_f(idx, uv, g, mid)
                if two_sided:
                    self.f.append((tuple(reversed(self.f[-1][0])), tuple(reversed(self.f[-1][1])), g))
        if full:
            for want, ring, i in ((cap_start, rings[0], 0), (cap_end, rings[-1], n - 1)):
                if want:
                    j = 1 if i == 0 else n - 2
                    out = tuple(path[i][k] - path[j][k] for k in range(3))
                    uv = tuple((0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides))
                    self.add_f_dir(ring, uv, 0, out)
        return rings

    def box(self, lo, hi, skip=()):
        """an axis-aligned box, flat faces, box-projected UVs in metres; ``skip`` drops faces by name (e.g. "-y")"""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        c = [self.add_v(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        faces = {"-z": ((0, 1, 2, 3), (0, 0, -1)), "+z": ((4, 5, 6, 7), (0, 0, 1)), "-x": ((0, 3, 7, 4), (-1, 0, 0)),
                 "+x": ((1, 2, 6, 5), (1, 0, 0)), "-y": ((0, 1, 5, 4), (0, -1, 0)), "+y": ((3, 2, 6, 7), (0, 1, 0))}
        for name, (q, out) in faces.items():
            if name in skip:
                continue
            ax = max(range(3), key=lambda k: abs(out[k]))
            a, b = [(2, 1), (0, 2), (0, 1)][ax]
            idx = tuple(c[i] for i in q)
            self.add_f_dir(idx, tuple((self.v[i][a], self.v[i][b]) for i in idx), 0, out)

    def revolve(self, profile, sides, centre=(0.0, 0.0), smooth=True, cap_top=False, cap_bottom=False):
        """revolve ``profile`` [(radius, y), ...] (bottom to top) about the vertical axis through ``centre`` (x, z)"""
        g = self.new_group() if smooth else 0
        cx, cz = centre
        rings = [[self.add_v((cx + r * math.cos(2 * math.pi * k / sides), y, cz + r * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
                 for r, y in profile]
        run = [0.0]
        for (ra, ya), (rb, yb) in zip(profile, profile[1:]):
            run.append(run[-1] + math.hypot(rb - ra, yb - ya))
        for i, ((ra, ya), (rb, yb)) in enumerate(zip(profile, profile[1:])):
            dr, dy = rb - ra, yb - ya
            for k in range(sides):
                k1 = (k + 1) % sides
                am = 2 * math.pi * (k + 0.5) / sides
                out = (dy * math.cos(am), -dr, dy * math.sin(am))
                uv = ((k / sides, run[i] / 4), ((k + 1) / sides, run[i] / 4), ((k + 1) / sides, run[i + 1] / 4), (k / sides, run[i + 1] / 4))
                idx = (rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k])
                if ra < 1e-9:                                 # a cone tip below: one triangle per column
                    idx, uv = (rings[i][0], rings[i + 1][k1], rings[i + 1][k]), (uv[0], uv[2], uv[3])
                elif rb < 1e-9:                               # a cone tip above
                    idx, uv = (rings[i][k], rings[i][k1], rings[i + 1][0]), (uv[0], uv[1], uv[2])
                self.add_f_dir(idx, uv, g, out)
        disc_uv = tuple((0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides))
        if cap_top and profile[-1][0] > 1e-9:
            self.add_f_dir(rings[-1], disc_uv, 0, (0.0, 1.0, 0.0))
        if cap_bottom and profile[0][0] > 1e-9:
            self.add_f_dir(rings[0], disc_uv, 0, (0.0, -1.0, 0.0))

    def polygon(self, pts, uv, outward):
        """one flat n-gon with the given per-corner UVs"""
        self.add_f_dir([self.add_v(p) for p in pts], uv, 0, outward)


class Model:
    def __init__(self, name: str, note: str, frame: str, maker: str):
        self.name, self.note, self.frame, self.maker = name, note, frame, maker
        self.objects: list[Obj] = []

    def obj(self, name: str, material: str) -> Obj:
        o = Obj(name, material)
        self.objects.append(o)
        return o

    def tris(self) -> int:
        return sum(o.tris() for o in self.objects)

    def bounds(self):
        lo = tuple(min(o.bounds()[0][k] for o in self.objects) for k in range(3))
        hi = tuple(max(o.bounds()[1][k] for o in self.objects) for k in range(3))
        return lo, hi

    def summary(self) -> dict:
        return {"tris": self.tris(),
                "objects": {o.name: {"material": o.material, "tris": o.tris()} for o in self.objects}}

    def text(self) -> str:
        out = [f"# {self.name} — {self.note}", f"# generated by {self.maker} (ledger 0096); self-made, CC0-1.0",
               f"# frame: {self.frame}"]
        vt, vt_ix, base = [], {}, 0
        body = []
        for o in self.objects:
            body += [f"o {o.name}"] + [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in o.v] + [f"usemtl {o.material}"]
            cur = None
            for idx, uv, g in o.f:
                if g != cur:
                    body.append("s off" if g == 0 else f"s {g}")
                    cur = g
                refs = []
                for i, u in zip(idx, uv):
                    key = (round(u[0], 5), round(u[1], 5))
                    if key not in vt_ix:
                        vt_ix[key] = len(vt) + 1
                        vt.append(key)
                    refs.append(f"{base + i + 1}/{vt_ix[key]}")
                body.append("f " + " ".join(refs))
            base += len(o.v)
        return "\n".join(out + [f"vt {u:.5f} {v:.5f}" for u, v in vt] + body) + "\n"


def read_obj_objects(text: str) -> dict:
    """split an OBJ written by ``Model.text`` back into its objects:
    {name: {"material": str, "verts": [(x, y, z)], "faces": [(indices into verts, uvs, smoothing group)]}}"""
    verts, uvs, objs, cur, group = [], [], {}, None, 0
    for ln in text.splitlines():
        p = ln.split()
        if not p or p[0] == "#":
            continue
        if p[0] == "v":
            verts.append(tuple(map(float, p[1:4])))
        elif p[0] == "vt":
            uvs.append((float(p[1]), float(p[2])))
    for ln in text.splitlines():
        p = ln.split()
        if not p:
            continue
        if p[0] == "o":
            cur = objs.setdefault(p[1], {"material": None, "verts": [], "faces": [], "_ix": {}})
            group = 0
        elif p[0] == "usemtl" and cur is not None:
            cur["material"] = p[1]
        elif p[0] == "s":
            group = 0 if p[1] in ("off", "0") else int(p[1])
        elif p[0] == "f" and cur is not None:
            ix, uv = [], []
            for q in p[1:]:
                a = q.split("/")
                gi = int(a[0]) - 1
                if gi not in cur["_ix"]:
                    cur["_ix"][gi] = len(cur["verts"])
                    cur["verts"].append(verts[gi])
                ix.append(cur["_ix"][gi])
                uv.append(uvs[int(a[1]) - 1] if len(a) > 1 and a[1] else (0.0, 0.0))
            cur["faces"].append((ix, uv, group))
    for o in objs.values():
        del o["_ix"]
    return objs


def write_or_check(out_dir, outputs: dict[str, str], argv, tag: str) -> int:
    """the makers' shared tail: write every text output, or with --check exit 1 if a committed file differs"""
    if "--check" in argv:
        bad = [n for n, t in outputs.items() if not (out_dir / n).exists() or (out_dir / n).read_text(encoding="utf-8") != t]
        print(f"{tag} --check: " + ("differs: " + ", ".join(bad) if bad else "committed files match"))
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, t in outputs.items():
        (out_dir / n).write_text(t, encoding="utf-8", newline="\n")
        if n.endswith(".obj"):
            nv = sum(1 for ln in t.splitlines() if ln.startswith("v "))
            nt = sum(len(ln.split()) - 3 for ln in t.splitlines() if ln.startswith("f "))
            print(f"[{tag}] wrote {n}  ({nv} v, {nt} tris)")
        else:
            print(f"[{tag}] wrote {n}")
    return 0
