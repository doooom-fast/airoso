"""Microsoft GlobalMLBuildingFootprints -> a track's footprint source for tools/plan_buildings.py (ledger 0062, Lake Murray).

  python tools/msft_footprints.py <track-dir> --find                    the tile URL(s) covering source/naip_box.json
  python tools/msft_footprints.py <track-dir> <tile.csv.gz> [out.json]  the footprints inside the box, in the planner's
                                                                        cache row shape (default source/bespoke/msft_buildings.json)

The dataset (ODbL) is tiled by Bing quadkey at level 9; dataset-links.csv lists every tile's URL and size. The tile is
downloaded data: run this with python -I. Each row carries the dataset's own ML height estimate in metres (-1 = none).

The self-check it prints is the reason to trust the file or not: how many of its footprints stand where the track's other
sources (the plan's earlier footprint files) have nothing, how many of theirs it lacks, and its heights against OSM's
height tags and building:levels where both exist. On Lake Murray (2026-11-01) the two sets were nearly disjoint — 10,549 of
12,035 Microsoft footprints where OSM has none, 19,153 of OSM's 20,649 without a Microsoft polygon — so the file is the
houses OSM lacks, not OSM's houses shifted; its heights ran 4.3 / 5.6 / 8.9 m at OSM's 1 / 2 / 3 levels (n 5 / 7 / 6).
"""
import gzip, json, math, sys
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.tls import https_context  # noqa: E402  (verification on, never disabled)

LINKS = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
CELL = 0.0005                   # degrees (~50 m): the lon/lat index cell


def quadkey(lat, lon, z=9):
    s = math.sin(math.radians(lat))
    x, y = (lon + 180) / 360, 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    n = 1 << z
    tx, ty = min(n - 1, int(x * n)), min(n - 1, int(y * n))
    q = ""
    for i in range(z, 0, -1):
        d, m = 0, 1 << (i - 1)
        d += 1 if tx & m else 0
        d += 2 if ty & m else 0
        q += str(d)
    return q


def ring_of(row):
    if "geom" in row:
        return [[float(a), float(b)] for a, b in row["geom"]]
    g = row.get("geometry")
    if isinstance(g, list):                        # overpass out:geom
        return [[n["lon"], n["lat"]] for n in g]
    if isinstance(g, dict):
        return [[float(a), float(b)] for a, b in g["coordinates"][0]]
    return None


def centroid(r):
    return sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)


def pip(pt, r):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            inside = not inside
    return inside


def index(rings):
    g = defaultdict(list)
    for i, r in enumerate(rings):
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        for cx in range(int(min(xs) / CELL), int(max(xs) / CELL) + 1):
            for cy in range(int(min(ys) / CELL), int(max(ys) / CELL) + 1):
                g[(cx, cy)].append(i)
    return g


def find(g, rings, pt):
    for i in g.get((int(pt[0] / CELL), int(pt[1] / CELL)), ()):
        if pip(pt, rings[i]):
            return i
    return None


def own_footprints(track, out_rel):
    """the plan's footprint files other than the one being written: (rings, (height, levels) per ring)"""
    plan = json.loads((track / "source/bespoke/buildings.plan.json").read_text(encoding="utf-8"))
    rings, hl = [], []
    for src in plan["footprints"]:
        if src["file"] == out_rel:
            continue
        rows = json.loads((track / src["file"]).read_text(encoding="utf-8"))
        rows = rows.get("elements", rows) if isinstance(rows, dict) else rows
        for row in rows:
            r = ring_of(row)
            if not r or len(r) < 4:
                continue
            tags = row.get("tags", row)
            h, lv = tags.get("height"), tags.get("building:levels", tags.get("levels"))
            try:
                h = float(str(h).split()[0]) if h not in (None, "") else None
            except ValueError:
                h = None
            try:
                lv = float(lv) if lv not in (None, "") else None
            except ValueError:
                lv = None
            rings.append(r)
            hl.append((h, lv))
    return rings, hl


def main():
    track = Path(sys.argv[1])
    W, S, E, N = json.loads((track / "source/naip_box.json").read_text(encoding="utf-8"))
    if "--find" in sys.argv:
        keys = sorted({quadkey(lat, lon) for lat in (S, N) for lon in (W, E)})
        print("quadkeys at level 9 over the box:", keys)
        with urlopen(LINKS, timeout=120, context=https_context()) as f:
            for line in f.read().decode("utf-8").splitlines():
                parts = line.split(",")
                if len(parts) >= 5 and parts[1] in keys:
                    print(f"  {parts[0]} {parts[1]} {parts[3]} {parts[4]}  {parts[2]}")
        return 0
    gz = Path(sys.argv[2])
    out_rel = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "source/bespoke/msft_buildings.json"
    src = (f"Microsoft GlobalMLBuildingFootprints (ODbL), tile {gz.name.split('.')[0]}; height = the dataset's ML estimate "
           f"in metres")
    ms, n = [], 0
    with gzip.open(gz, "rt", encoding="utf-8") as f:
        for line in f:
            n += 1
            try:
                g = json.loads(line)
            except ValueError:
                continue
            if g.get("geometry", {}).get("type") != "Polygon":
                continue
            r = [[round(float(a), 7), round(float(b), 7)] for a, b in g["geometry"]["coordinates"][0]]
            if not any(W <= p[0] <= E and S <= p[1] <= N for p in r):
                continue
            p = g.get("properties", {})
            h = p.get("height", -1)
            c = p.get("confidence", -1)
            ms.append({"building": "yes", "levels": None, "height": None if h is None or h < 0 else round(float(h), 2),
                       "confidence": None if c is None or c < 0 else round(float(c), 3), "geom": r, "_source": src})
    print(f"[msft] tile rows {n}, in the box {len(ms)}, with a height {sum(1 for m in ms if m['height'] is not None)}")

    own, own_hl = own_footprints(track, out_rel)
    own_idx = index(own)
    ms_rings = [m["geom"] for m in ms]
    ms_idx = index(ms_rings)
    new = sum(1 for m in ms if find(own_idx, own, centroid(m["geom"])) is None)
    missed = sum(1 for r in own if find(ms_idx, ms_rings, centroid(r)) is None)
    print(f"[msft] the track's other sources hold {len(own)} footprints; Microsoft stands where they have none: {new}; "
          f"theirs Microsoft has no polygon for: {missed}")
    q = lambda a, f: a[min(len(a) - 1, int(f * len(a)))]
    pairs_h, by_level = [], defaultdict(list)
    for r, (h, lv) in zip(own, own_hl):
        j = find(ms_idx, ms_rings, centroid(r))
        if j is None or ms[j]["height"] is None:
            continue
        if h:
            pairs_h.append(ms[j]["height"] / h)
        elif lv:
            by_level[int(lv)].append(ms[j]["height"])
    if pairs_h:
        pairs_h.sort()
        print(f"[msft] Microsoft / OSM height tag, n {len(pairs_h)}: p10 {q(pairs_h, .1):.2f}, p50 {q(pairs_h, .5):.2f}, p90 {q(pairs_h, .9):.2f}")
    for lv in sorted(by_level):
        v = sorted(by_level[lv])
        print(f"[msft] at OSM building:levels {lv}: n {len(v)}, Microsoft height p10 {q(v, .1):.1f}, p50 {q(v, .5):.1f}, p90 {q(v, .9):.1f} m")
    out = track / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ms, separators=(",", ":")), encoding="utf-8", newline="\n")
    print(f"[msft] wrote {out_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
