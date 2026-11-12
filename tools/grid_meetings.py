"""Where a free roam's grid streets meet EACH OTHER (not the lap): the list tools/trim_connectors.py does not cut (ledger 0079
round B). READ-ONLY.

tools/grid_connectors.py eases two pieces to one height where they meet (MEET_R_M, its ease_meetings); the LM junction chain
then trims every piece against the LAP and against the hosts named in route.connector_hosts / route.divided_connectors,
nothing else. A meeting of two pieces is therefore one of:

    lap      within the lap's carriageway (trim cuts both at the lap edge: a mouth each)
    host     exactly one piece is a named host (an arterial): trim cuts the other at the host's edge (a mouth)
    overlap  neither or both are hosts: two coplanar ribbons cross or butt, no mouth, no weld (owed: a street-to-street weld)

and by shape: "T" when the meeting is at an end of one piece, "X" when it is inside both. Kind by OSM class (the piece name
grid_<class>_<k>): arterial = primary / secondary, minor = tertiary / unclassified / residential.

    python tools/grid_meetings.py <project-or-track> [--json <out>]

Reads data/connectors.local.json (the UNTRIMMED grid: .pre-trim when present), data/centerline.local.json and
track.config.json route.connector_hosts / divided_connectors; writes the list with each meeting's local x / z and lon / lat.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

MEET_R_M = 2.5          # grid_connectors' own meeting radius
END_M = 6.0             # [invented] a meeting this close to a piece's end is a T on that piece
ARTERIAL = {"primary", "secondary"}


def cls_of(name):
    p = name.split("_")
    return p[1] if len(p) > 2 and p[0] == "grid" else "other"


def host_match(name, hosts):
    for h in hosts:
        if h.endswith("*") and name.startswith(h[:-1]):
            return True
        if name == h or name.startswith(h + "#"):
            return True
    return False


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = None
    if "--json" in argv:
        i = argv.index("--json"); out = Path(argv[i + 1]); del argv[i:i + 2]
    proj = Path(argv[0])
    data = proj / "data"
    src = data / "connectors.local.json.pre-trim"
    if not src.exists():
        src = data / "connectors.local.json"
    conns = json.loads(src.read_text(encoding="utf-8"))["connectors"]
    local = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    lap = [(p[0], p[2]) for p in local["points_xyz_m"]]
    lap_w = local["widths_m"]
    route = (json.loads((proj / "track.config.json").read_text(encoding="utf-8")).get("route") or {})
    hosts = [str(x) for x in (route.get("connector_hosts") or [])] + [str(x) for x in (route.get("divided_connectors") or [])]
    o = local["origin"]
    m_lon = 111320.0 * math.cos(math.radians(o["lat"])); m_lat = 110540.0

    cell = MEET_R_M * 2
    grid = {}
    flat = []
    for ci, c in enumerate(conns):
        for pi, p in enumerate(c["points_xyz_m"]):
            flat.append((p[0], p[2], ci, pi))
            grid.setdefault((int(p[0] // cell), int(p[2] // cell)), []).append(len(flat) - 1)
    meets = {}
    for f in flat:
        g = (int(f[0] // cell), int(f[1] // cell))
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for k in grid.get((g[0] + dx, g[1] + dz), ()):
                    q = flat[k]
                    if q[2] <= f[2]:
                        continue
                    d = math.hypot(q[0] - f[0], q[1] - f[1])
                    key = (f[2], q[2], round(f[0] / 12.0), round(f[1] / 12.0))
                    if d <= MEET_R_M and (key not in meets or d < meets[key][0]):
                        meets[key] = (d, f[2], f[3], q[2], q[3])
    lgrid = {}
    for i, (x, z) in enumerate(lap):
        lgrid.setdefault((int(x // 20), int(z // 20)), []).append(i)

    def on_lap(x, z):
        best = None
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in lgrid.get((int(x // 20) + dx, int(z // 20) + dz), ()):
                    d = math.hypot(lap[i][0] - x, lap[i][1] - z)
                    if best is None or d < best[0]:
                        best = (d, i)
        return best is not None and best[0] <= lap_w[best[1]] / 2.0 + 2.0

    def arc_to_end(c, i):
        pts = c["points_xyz_m"]
        a = sum(math.dist(pts[k][::2], pts[k + 1][::2]) for k in range(i))
        b = sum(math.dist(pts[k][::2], pts[k + 1][::2]) for k in range(i, len(pts) - 1))
        return min(a, b)

    rows = []
    for _d, a, i, b, j in sorted(meets.values(), key=lambda r: (r[1], r[3], r[2])):
        ca, cb = conns[a], conns[b]
        pa = ca["points_xyz_m"][i]
        x, z = pa[0], pa[2]
        ka, kb = cls_of(ca["name"]), cls_of(cb["name"])
        kind = "/".join(sorted(("arterial" if k in ARTERIAL else "minor") for k in (ka, kb)))
        ta, tb = arc_to_end(ca, i) <= END_M, arc_to_end(cb, j) <= END_M
        shape = "X" if not (ta or tb) else ("L" if ta and tb else "T")
        ha, hb = host_match(ca["name"], hosts), host_match(cb["name"], hosts)
        # two hosts are never cut against each other (trim pass 2 trims non-hosts only): that is an overlap too
        fate = "lap" if on_lap(x, z) else ("host" if (ha != hb) else "overlap")
        rows.append({"a": ca["name"], "b": cb["name"], "kind": kind, "classes": [ka, kb], "shape": shape, "fate": fate,
                     "xz": [round(x, 1), round(z, 1)],
                     "lonlat": [round(o["lon"] + x / m_lon, 6), round(o["lat"] + z / m_lat, 6)]})
    summ = {}
    for r in rows:
        k = (r["fate"], r["kind"], r["shape"])
        summ[k] = summ.get(k, 0) + 1
    print(f"[grid-meetings] {len(rows)} meetings of {len(conns)} pieces ({src.name}); hosts {hosts or 'none'}")
    for k in sorted(summ):
        print(f"  {k[0]:8s} {k[1]:17s} {k[2]}: {summ[k]}")
    rep = {"_doc": "tools/grid_meetings.py (ledger 0079 round B): every place two grid pieces meet, its kind, shape and what the "
                   "LM junction chain does with it (lap / host = trimmed to a mouth; overlap = left as two ribbons)",
           "source": src.name, "hosts": hosts, "meetings": rows,
           "summary": [{"fate": k[0], "kind": k[1], "shape": k[2], "n": v} for k, v in sorted(summ.items())]}
    if out:
        out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
