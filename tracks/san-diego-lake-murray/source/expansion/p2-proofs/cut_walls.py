"""Ledger 0054 P2 step 3 (EXPANSION-PLAN): how well the near-road ground keeps the real cut walls beside the two
sidehill roads - Mission Gorge (piece C) s 1115 -> J4 and all of Jackson north (piece D) - 12-20 m from the centreline.

P2 builds no north road (the route is held), so the ground there is the 3DEP lattice and keeps every wall. What
matters is the ground P3 will build: within keep_surface_m 20 m of a pavement the ground IS the assembler's graded
20 m grid (0046 criterion 7) - the grown 40 m heightfield upsampled x2, conform_terrain_to_road (corridor 20 m + blend
16 m, clearance 0.08 m, to the nearest road sample: centre + both edges) and the +-terrain_band_m hard band clamp,
exactly as scripts-v021 build_loop_blend does it, with the four pieces added to its roads at their
route_connectors-style profile (y_smooth) and their real curb offsets. 12-20 m from the centreline is inside that
band on both roads (half-widths 8.5-16.5 m), so this graded surface is what P3 builds there before any hand
authoring (the seat and the kn5 prep only flatten it further: an optimistic bound).

Per station (every 5 m) and side, 3DEP 1 m at offsets 12, 13, ... 20 m (fresh, TLS, cached in
cut_walls.samples.json.gz with provenance) and the projected ground at the same points:
  real wall  = max over the offsets of (3DEP - road)        (a cut: ground standing above the road)
  built wall = max over the offsets of (built - road)
  LOST       = real wall >= 3.0 m and built wall < 0.5 x real wall   [invented: "a wall of 3 m or more is lost" =
               less than half of it is left]
A stretch = consecutive lost stations on one side; >= 50 m of road -> a hand-authored cut slope in Blender (REALISM:
lean in, never eject; not an engine change). Fills (3DEP dropping >= 3 m below the road) are reported alongside.

    python cut_walls.py <airoso> <rehearsal project> <out.json> [--offline]
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import struct
import sys
import time
from pathlib import Path

AIR, PROJ, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OFFLINE = "--offline" in sys.argv
sys.path.insert(0, str(AIR))
from scripts.elevation import usgs_3dep  # noqa: E402

TRACK = AIR / "tracks" / "san-diego-lake-murray"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cut_walls.samples.json.gz"
OFFS = [12.0 + k for k in range(9)]
STEP = 5.0
WALL_M, KEEP_FRAC, STRETCH_M = 3.0, 0.5, 50.0
SPANS = {"C": (1115.0, None), "D": (0.0, None)}          # piece -> (s from, s to); None = to the piece's end

spec = importlib.util.spec_from_file_location("_v021_ribbon", TRACK / "scripts-v021" / "geometry" / "ribbon.py")
ribbon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ribbon)


def read_npy(path):
    raw = path.read_bytes()
    hl = struct.unpack("<H", raw[8:10])[0]
    hdr = raw[10:10 + hl].decode("latin1")
    ny, nx = (int(v) for v in hdr.split("'shape': (")[1].split(")")[0].replace(" ", "").split(",")[:2])
    v = struct.unpack("<%dd" % (nx * ny), raw[10 + hl:10 + hl + 8 * nx * ny])
    return [list(v[j * nx:(j + 1) * nx]) for j in range(ny)]


def mpd(lat0):
    m_lat = 111_132.92 - 559.82 * math.cos(2 * math.radians(lat0))
    m_lon = 111_412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    return m_lon, m_lat


def project_grid(grid, meta, lon0, lat0, elev0):              # build_loop_blend.project_grid, verbatim
    s, w, n, e = meta["bbox_swne"]
    nx, ny, sp = meta["nx"], meta["ny"], meta["spacing_m"]
    midlat = (s + n) / 2
    gy = sp / 111_000.0
    gx = sp / (111_000.0 * math.cos(math.radians(midlat)))
    m_lon, m_lat = mpd(lat0)
    return [[((w + i * gx - lon0) * m_lon, grid[j][i] - elev0, ((n - j * gy) - lat0) * m_lat) for i in range(nx)]
            for j in range(ny)]


def band_clamp(grid_xyz, road_pts, band):                    # build_loop_blend.band_clamp, verbatim logic
    B = 130.0
    buck = {}
    for (x, y, z) in road_pts:
        buck.setdefault((int(x // B), int(z // B)), []).append((x, y, z))

    def nearest_y(x, z):
        bx, bz = int(x // B), int(z // B)
        best_y, best_d, r = None, 1e18, 1
        while best_y is None and r < 40:
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if r > 1 and max(abs(dx), abs(dz)) != r:
                        continue
                    for (rx, ry, rz) in buck.get((bx + dx, bz + dz), ()):
                        d = (x - rx) ** 2 + (z - rz) ** 2
                        if d < best_d:
                            best_d, best_y = d, ry
            r += 1
        return best_y

    for j in range(len(grid_xyz)):
        for i in range(len(grid_xyz[0])):
            x, y, z = grid_xyz[j][i]
            ry = nearest_y(x, z)
            if ry is not None:
                grid_xyz[j][i] = (x, max(ry - band, min(ry + band, y)), z)


def legacy_surface(grid_xyz):                                # build_loop_blend._legacy_surface, verbatim
    ny = len(grid_xyz); nx = len(grid_xyz[0])
    x0 = grid_xyz[0][0][0]; z0 = grid_xyz[0][0][2]
    dxg = grid_xyz[0][1][0] - x0; dzg = z0 - grid_xyz[1][0][2]

    def h(x, z):
        fi = (x - x0) / dxg; fj = (z0 - z) / dzg
        if fi < 0 or fj < 0 or fi > nx - 1 or fj > ny - 1:
            return None
        i0 = max(0, min(nx - 2, int(fi))); j0 = max(0, min(ny - 2, int(fj)))
        ti = fi - i0; tj = fj - j0
        a = grid_xyz[j0][i0][1]; b = grid_xyz[j0][i0 + 1][1]
        c = grid_xyz[j0 + 1][i0 + 1][1]; d = grid_xyz[j0 + 1][i0][1]
        if ti >= tj:
            return a + (b - a) * ti + (c - b) * tj
        return a + (c - d) * ti + (d - a) * tj
    return h


cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
local = json.loads((PROJ / "data" / "centerline.local.json").read_text(encoding="utf-8"))
o = local["origin"]
lon0, lat0, elev0 = o["lon"], o["lat"], o["elev_m"]
X = json.loads((TRACK / "data" / "expansion.north.json").read_text(encoding="utf-8"))
pieces = {p["id"]: p for p in X["pieces"]}


def piece_rows(p):
    col = {c: k for k, c in enumerate(p["columns"])}
    rows = []
    st = p["stations"]
    for k, r in enumerate(st):
        a, b = st[max(0, k - 1)], st[min(len(st) - 1, k + 1)]
        tx, tz = b[col["x"]] - a[col["x"]], b[col["z"]] - a[col["z"]]
        L = math.hypot(tx, tz) or 1.0
        tx, tz = tx / L, tz / L
        rows.append({"s": r[col["s"]], "x": r[col["x"]], "z": r[col["z"]], "y": r[col["y_smooth"]],
                     "l": r[col["left_m"]], "r": r[col["right_m"]], "nx": -tz, "nz": tx})
    return rows


# --- the projected P3 graded ground ---
t0 = time.time()
grid = read_npy(TRACK / "data" / "heightfield.npy")
meta = json.loads((TRACK / "data" / "heightfield.meta.json").read_text(encoding="utf-8"))
grid, meta = ribbon.upsample_grid(grid, meta, 2)
gxyz = project_grid(grid, meta, lon0, lat0, elev0)
centerline = [tuple(p) for p in local["points_xyz_m"]]
widths = list(local["widths_m"])
extra = []
cp = PROJ / "data" / "connectors.local.json"
if cp.exists():
    for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
        if len(c["points_xyz_m"]) >= 2:
            extra.append(([tuple(q) for q in c["points_xyz_m"]], list(c["widths_m"])))
north = {}
for pid, p in pieces.items():
    rows = piece_rows(p)
    north[pid] = rows
    mid = [(q["x"] + q["nx"] * (q["l"] + q["r"]) / 2, q["y"], q["z"] + q["nz"] * (q["l"] + q["r"]) / 2) for q in rows]
    extra.append((mid, [q["l"] - q["r"] for q in rows]))
ribbon.conform_terrain_to_road(gxyz, centerline, widths, corridor=20.0, blend=16.0, clearance=0.08, extra_roads=extra)
band = float(cfg["terrain"].get("terrain_band_m", 22.0))
band_clamp(gxyz, list(centerline) + [q for ln, _w in extra for q in ln], band)
built = legacy_surface(gxyz)
print(f"[walls] graded grid {len(gxyz)} x {len(gxyz[0])} conformed to the loop + {len(extra)} lines "
      f"({time.time() - t0:.0f} s)", flush=True)

# --- the transects ---
pts, idx = [], []
for pid, (s0, s1) in SPANS.items():
    rows = north[pid]
    s_end = rows[-1]["s"] if s1 is None else s1
    for q in rows:
        if q["s"] < s0 - 1e-6 or q["s"] > s_end + 1e-6 or abs((q["s"] - s0) / STEP - round((q["s"] - s0) / STEP)) > 1e-6:
            continue
        for side, sg in (("left", 1.0), ("right", -1.0)):
            for off in OFFS:
                x, z = q["x"] + q["nx"] * sg * off, q["z"] + q["nz"] * sg * off
                pts.append((x, z))
                idx.append((pid, q["s"], side, off, q["y"]))
m_lon, m_lat = mpd(lat0)
lonlat = [(lon0 + x / m_lon, lat0 + z / m_lat) for x, z in pts]
key = json.loads(json.dumps({"points": len(pts), "first": [round(v, 9) for v in lonlat[0]],
                             "last": [round(v, 9) for v in lonlat[-1]], "offsets": OFFS, "step": STEP, "spans": SPANS}))
dep = None
if CACHE.exists():
    d = json.loads(gzip.decompress(CACHE.read_bytes()))
    if d.get("_key") == key:
        dep = d["h"]
if dep is None:
    if OFFLINE:
        raise SystemExit("[walls] --offline: the transect samples are not cached")
    chunks = [lonlat[a:a + 450] for a in range(0, len(lonlat), 450)]
    dep = []
    for c in chunks:
        dep += usgs_3dep._sample_batch(c, retries=4)
    if any(v is None for v in dep):
        raise SystemExit("[walls] 3DEP no-data on a transect point - no silent fill (L2)")
    dep = [round(float(v), 2) for v in dep]
    CACHE.write_bytes(gzip.compress(json.dumps({
        "_key": key, "_provenance": {"source": "USGS 3DEP 1 m bare earth, ImageServer getSamples (TLS verified)",
                                     "endpoint": usgs_3dep.GET_SAMPLES, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                                     time.gmtime()),
                                     "requests": len(chunks), "what": "cut-wall transects, ledger 0054 P2 step 3"},
        "h": dep}, separators=(",", ":")).encode("utf-8"), 9, mtime=0))

# --- walls per station / side ---
by = {}
for (pid, s, side, off, ry), (x, z), h in zip(idx, pts, dep):
    b = built(x, z)
    rec = by.setdefault((pid, s, side), {"road": ry + elev0, "real": [], "built": []})
    rec["real"].append(h)
    rec["built"].append(None if b is None else b + elev0)
rows_out = []
for (pid, s, side), r in sorted(by.items()):
    real_cut = max(v - r["road"] for v in r["real"])
    real_fill = max(r["road"] - v for v in r["real"])
    bb = [v for v in r["built"] if v is not None]
    built_cut = max(v - r["road"] for v in bb) if bb else None
    lost = real_cut >= WALL_M and (built_cut is None or built_cut < KEEP_FRAC * real_cut)
    rows_out.append({"piece": pid, "s": s, "side": side, "real_cut_m": round(real_cut, 2), "real_fill_m": round(real_fill, 2),
                     "built_cut_m": None if built_cut is None else round(built_cut, 2), "lost": lost})


def stretches(rows, flag, height="real_cut_m"):
    out = []
    for pid in SPANS:
        for side in ("left", "right"):
            seq = [q for q in rows if q["piece"] == pid and q["side"] == side]
            cur = None
            for q in seq:
                if flag(q):
                    if cur is None:
                        cur = {"piece": pid, "side": side, "s_from": q["s"], "s_to": q["s"], "max_real_m": q[height],
                               "stations": 0}
                    cur["s_to"] = q["s"]
                    cur["max_real_m"] = max(cur["max_real_m"], q[height])
                    cur["stations"] += 1
                elif cur is not None:
                    out.append(cur)
                    cur = None
            if cur is not None:
                out.append(cur)
    for c in out:
        c["length_m"] = round(c["s_to"] - c["s_from"] + STEP, 1)
    return out


lost = stretches(rows_out, lambda q: q["lost"])
walls = stretches(rows_out, lambda q: q["real_cut_m"] >= WALL_M)
need = [c for c in lost if c["length_m"] >= STRETCH_M]
fills = stretches(rows_out, lambda q: q["real_fill_m"] >= WALL_M, "real_fill_m")
road = {"C": "Mission Gorge Rd", "D": "Jackson Dr north"}
for c in need:
    c["road"] = road[c["piece"]]
    a = [q for q in rows_out if q["piece"] == c["piece"] and q["side"] == c["side"] and c["s_from"] <= q["s"] <= c["s_to"]]
    c["max_built_m"] = max((q["built_cut_m"] or 0.0) for q in a)
rep = {"what": __doc__.split("\n\n")[0], "definition": {"offsets_m": OFFS, "step_m": STEP, "wall_m": WALL_M,
                                                       "lost_if_built_below_fraction": KEEP_FRAC, "stretch_m": STRETCH_M,
                                                       "invented": "wall 3 m and stretch 50 m are EXPANSION-PLAN's; "
                                                                   "'lost' = under half the wall left [invented]"},
       "stations": len(by) // 2, "station_sides": len(by),
       "real_walls_ge_3m": {"station_sides": sum(1 for q in rows_out if q["real_cut_m"] >= WALL_M),
                            "stretches": len(walls)},
       "lost_station_sides": sum(1 for q in rows_out if q["lost"]),
       "kept_station_sides_with_a_wall": sum(1 for q in rows_out if q["real_cut_m"] >= WALL_M and not q["lost"]),
       "stretches_lost": len(lost), "stretches_needing_a_hand_authored_cut_slope": need,
       "fill_stretches_ge_3m": [{k: v for k, v in c.items()} for c in fills if c["length_m"] >= STRETCH_M],
       "p2_as_built": "no north road in P2 (held): the rehearsal's ground there is the 3DEP lattice; see measure_v7.py",
       "rows": rows_out}
OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
print(f"[walls] {rep['stations']} stations x 2 sides; real walls >= {WALL_M} m at {rep['real_walls_ge_3m']['station_sides']} "
      f"station-sides; lost {rep['lost_station_sides']}; {len(need)} stretches >= {STRETCH_M} m need a hand-authored "
      f"cut slope:", flush=True)
for c in need:
    print(f"   {c['road']:18} {c['side']:5} s {c['s_from']:.0f}-{c['s_to']:.0f} ({c['length_m']:.0f} m), real wall up to "
          f"{c['max_real_m']:.1f} m, built up to {c['max_built_m']:.1f} m")
