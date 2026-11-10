"""TreeFX .bin LOD mesh extents (read-only): header (u32 version, u8 flag, u32 ntex, per texture: 4-byte hash + u32 len +
name), then parts of (u32 a, u32 b, u32 nidx, u16 idx[nidx], u32 nverts, nverts x 11 f32: pos3 normal3 uv2 + 3 zero).
usage: treefx_mesh_extent.py <bin or .mesh> ..."""
import struct
import sys
import zipfile

import numpy as np


def parse(d):
    o = 4; o += 1
    ntex = struct.unpack_from('<I', d, o)[0]; o += 4
    for _ in range(ntex):
        o += 4; n = struct.unpack_from('<I', d, o)[0]; o += 4 + n
    parts = []
    while o + 12 <= len(d):
        a, b, nidx = struct.unpack_from('<3I', d, o)
        if nidx == 0 or nidx > 200000 or o + 12 + nidx * 2 + 4 > len(d):
            break
        o2 = o + 12 + nidx * 2
        nv = struct.unpack_from('<I', d, o2)[0]
        if nv == 0 or nv > 100000 or o2 + 4 + nv * 44 > len(d):
            break
        V = np.frombuffer(d, dtype='<f4', count=nv * 11, offset=o2 + 4).reshape(nv, 11)
        parts.append((a, b, nidx, nv, V))
        o = o2 + 4 + nv * 44
    return parts, o


for p in sys.argv[1:]:
    if p.endswith('.bin'):
        z = zipfile.ZipFile(p)
        ini = z.read('tree.ini').decode('utf-8', 'replace')
        H = next((l.split('=')[1].strip() for l in ini.splitlines() if l.strip().upper().startswith('HEIGHT')), '?')
        W = next((l.split('=')[1].strip() for l in ini.splitlines() if l.strip().upper().startswith('WIDTH')), '?')
        meshes = sorted(n for n in z.namelist() if n.endswith('.mesh'))
        print('==', p.replace(chr(92), '/').split('/')[-1], 'tree.ini HEIGHT', H, 'WIDTH', W)
        for m in meshes:
            d = z.read(m)
            parts, o = parse(d)
            allp = np.vstack([V[:, :3] for *_, V in parts])
            lo, hi = allp.min(0), allp.max(0)
            nn = np.linalg.norm(parts[0][4][:, 3:6], axis=1)
            print(f"  {m}: parts {[(a, b, ni, nv) for a, b, ni, nv, _ in parts]} read {o}/{len(d)} B; pos min {lo.round(4)} max {hi.round(4)} "
                  f"extent {(hi - lo).round(4)}; normal |n| p50 {np.median(nn):.3f}")
