"""<name>.final.json -> source/mrc_fixes.json (from_track fixes with measured widths, S/F at station 0).

Widths: the perpendicular scan reads aprons, the pit strip and shadowed edges too, so a station's width
is clamped to 9-16 m (nothing on the course is narrower than ~9-10 m in the photo; 16 m is the front
straight without its pit strip), stations wider than 22 m (aprons) or off the paved mask take the
nearest measured neighbour, then a running median over +-12 stations (+-24 m).
"""
import json, math, sys

name, out = sys.argv[1], sys.argv[2]
SF = (-83.667269, 42.570480)  # west front straight, raced north (track.config.json route.start_at)
d = json.load(open(name + '.final.json'))
ll, raw = d['lonlat'], d['raw_width_m']
n = len(raw)
v = [(min(max(x, 9.0), 16.0) if (x and x <= 22) else None) for x in raw]
for i in range(n):
    if v[i] is None:
        for r in range(1, n):
            c = [v[(i + s * r) % n] for s in (-1, 1) if v[(i + s * r) % n] is not None]
            if c:
                v[i] = c[0]; break
k = 12
w = [round(sorted(v[(i + j) % n] for j in range(-k, k + 1))[k], 2) for i in range(n)]
k0 = min(range(n), key=lambda i: math.hypot((ll[i][0] - SF[0]) * 81960, (ll[i][1] - SF[1]) * 111132))
ll, w = ll[k0:] + ll[:k0], w[k0:] + w[:k0]
json.dump([{'t': '%05d' % i, 'lat': round(p[1], 7), 'lon': round(p[0], 7), 'w': w[i]} for i, p in enumerate(ll)],
          open(out, 'w'), separators=(',', ':'))
print(f'{len(ll)} fixes, width median {sorted(w)[n // 2]} min {min(w)} max {max(w)}')
