"""Per-vertex position deltas of named meshes between two kn5s (same vertex order assumed; reports counts if not).
usage: mesh_delta.py <worktree> <a.kn5> <b.kn5> <mesh prefix> [...]"""
import math, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from scripts.modkit.extract_kn5 import parse, _world_verts
A, B = Path(sys.argv[2]), Path(sys.argv[3]); pre = tuple(s.upper() for s in sys.argv[4:])
def load(p):
    q = parse(p.read_bytes()) if 'bytes' in parse.__code__.co_varnames[:1] else parse(p)
    return {m['name']: m for m in q['meshes'] if m['name'].upper().startswith(pre)}
a, b = load(A), load(B)
for n in sorted(set(a) | set(b)):
    if n not in a or n not in b:
        print(n, 'only in', 'a' if n in a else 'b'); continue
    va, vb = _world_verts(a[n]), _world_verts(b[n])
    print(f'{n}: verts {len(va)} / {len(vb)}, tris {len(a[n]["idx"])//3} / {len(b[n]["idx"])//3}')
    if len(va) != len(vb):
        za = sorted(v[1] for v in va); zb = sorted(v[1] for v in vb)
        print('   y range a', round(za[0],3), round(za[-1],3), 'b', round(zb[0],3), round(zb[-1],3)); continue
    d = [(math.dist(p[:3], q[:3]), p[1] - q[1]) for p, q in zip(va, vb)]
    moved = [x for x in d if x[0] > 0]
    print(f'   moved {len(moved)} of {len(d)}; max |d| {max(x[0] for x in d):.6f} m; max |dy| {max(abs(x[1]) for x in d):.6f} m')
