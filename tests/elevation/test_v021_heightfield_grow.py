"""scripts-v021 elevation/heightfield.py — terrain.grid_grow (opt-in, whole cells; ledger 0054 P0 step 6, 2026-10-14).

Run in a subprocess with `scripts` registered as the scripts-v021 package (ship_sd.sh's V021_SHIM), so this process's
`scripts` (airoso's engine) is never shadowed. 3DEP is stubbed; no network.

- grid_grow ABSENT: fed the installed grid's own 3DEP values, build() writes the committed heightfield.npy and
  heightfield.meta.json byte for byte (the v0.18.0 grid, 123 x 93);
- grid_grow 37/37/26/0 (the committed config's): every old node is sampled at its bit-identical position (the stub
  answers by exact float position, so the old block IS the installed grid), 149 x 167 = 24,883 nodes, every old node
  projected (project_grid's formula) within 1e-9 deg of where it was, and the frame pin on the grown meta re-keys by
  whole cells;
- refusals: rows_n != rows_s, a non-integer or negative count, an unknown key.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACK = ROOT / "tracks" / "san-diego-lake-murray"
V021 = TRACK / "scripts-v021"

SCRIPT = r'''
import importlib.util, json, math, shutil, struct, sys
from pathlib import Path
V021, TRACK, OUT, ROOT = (Path(a) for a in sys.argv[1:5])
s = importlib.util.spec_from_file_location("scripts", V021 / "__init__.py", submodule_search_locations=[str(V021)])
m = importlib.util.module_from_spec(s); sys.modules["scripts"] = m; s.loader.exec_module(m)
from scripts.elevation import heightfield as hf, usgs_3dep
ts_ = importlib.util.spec_from_file_location("tt_air", ROOT / "scripts" / "geometry" / "terrain_tiers.py")
tt = importlib.util.module_from_spec(ts_); ts_.loader.exec_module(tt)
meta0 = json.loads((TRACK / "data" / "heightfield.meta.json").read_text())
npy0 = (TRACK / "data" / "heightfield.npy").read_bytes()
hl = struct.unpack("<H", npy0[8:10])[0]
NX0, NY0 = meta0["nx"], meta0["ny"]
vals0 = list(struct.unpack("<%dd" % (NX0 * NY0), npy0[10 + hl:]))
cfg = json.loads((TRACK / "track.config.json").read_text(encoding="utf-8"))
grow_cfg = cfg["terrain"].get("grid_grow")
res = {}

def proj(name, c):
    p = OUT / name
    (p / "data").mkdir(parents=True)
    shutil.copy(TRACK / "data" / "centerline.geojson", p / "data" / "centerline.geojson")
    (p / "track.config.json").write_text(json.dumps(c), encoding="utf-8")
    return p

cap = {}
def first(points, **k):
    if len(points) == NX0 * NY0:
        cap["pts"] = list(points); return list(vals0)
    return [100.0] * len(points)
usgs_3dep.sample_points = first
c0 = json.loads(json.dumps(cfg)); c0["terrain"].pop("grid_grow", None)
pa = proj("absent", c0); hf.build(pa)
res["absent_npy"] = (pa / "data" / "heightfield.npy").read_bytes() == npy0
res["absent_meta"] = (pa / "data" / "heightfield.meta.json").read_bytes() == (TRACK / "data" / "heightfield.meta.json").read_bytes()

look = dict(zip(cap["pts"], vals0))
usgs_3dep.sample_points = lambda pts, **k: ([look.get(p, -9999.0) for p in pts] if len(pts) > 20000 else [100.0] * len(pts))
pg = proj("grown", cfg); hf.build(pg)
mg = json.loads((pg / "data" / "heightfield.meta.json").read_text())
raw = (pg / "data" / "heightfield.npy").read_bytes(); hl = struct.unpack("<H", raw[8:10])[0]
NX, NY = mg["nx"], mg["ny"]; vg = struct.unpack("<%dd" % (NX * NY), raw[10 + hl:])
g = mg.get("grid_grow") or {}
rn, cw = g.get("rows_n", 0), g.get("cols_w", 0)
res["grow"] = g; res["nx"] = NX; res["ny"] = NY
res["old_block"] = all(vg[(j + rn) * NX + i + cw] == vals0[j * NX0 + i] for j in range(NY0) for i in range(NX0))
res["new_nodes"] = sum(1 for v in vg if v == -9999.0)
def node(meta, j, i):
    s_, w_, n_, e_ = meta["bbox_swne"]; mid = (s_ + n_) / 2; sp = meta["spacing_m"]
    return w_ + i * sp / (111000.0 * math.cos(math.radians(mid))), n_ - j * sp / 111000.0
res["max_dev_deg"] = max(max(abs(a - b) for a, b in zip(node(meta0, j, i), node(mg, j + rn, i + cw)))
                         for j in range(NY0) for i in range(NX0))
res["meta"] = mg
origin = json.loads((TRACK / "data" / "centerline.local.json").read_text())["origin"]
spec = tt.TierSpec(cfg["terrain"], origin)
pin = dict(cfg["terrain"]["tier_options"]["frame"]["pin"], rows_n=rn, cols_w=cw)
old = tt.Frame.heightfield(meta0, origin, 2, spec.levels, spec.base_m)
new = tt.Frame.heightfield(mg, origin, 2, spec.levels, spec.base_m, pin=pin)
kx, kz = tt.pin_key_shift(pin, 2, 8)
res["frame_dev_m"] = max(max(abs(old.x0 + I * old.ux - (new.x0 + (I + kx) * new.ux)),
                             abs(old.z0 + J * old.uz - (new.z0 + (J - kz) * new.uz)))
                         for I, J in ((0, 0), (100, -200), (1960, -1480), (-416, 592)))
errs = []
for bad in ({"rows_n": 2, "rows_s": 1}, {"rows_n": 1.5, "rows_s": 1.5}, {"rows_n": -1, "rows_s": -1}, {"rows_n": 1, "rows_s": 1, "cols_x": 2}):
    try:
        hf.grid_grow_spec({"terrain": {"grid_grow": bad}}); errs.append(None)
    except ValueError as e:
        errs.append(str(e)[:60])
res["refusals"] = errs
res["absent_spec"] = hf.grid_grow_spec({"terrain": {}}) is None and hf.grid_grow_spec(None) is None
print(json.dumps(res))
'''


def test_grid_grow_keeps_every_old_stake_and_absent_writes_todays_grid():
    with tempfile.TemporaryDirectory() as t:
        sp = Path(t) / "run.py"
        sp.write_text(SCRIPT, encoding="utf-8")
        r = subprocess.run([sys.executable, str(sp), str(V021), str(TRACK), str(Path(t) / "out"), str(ROOT)],
                           capture_output=True, text=True, timeout=600, env={**__import__("os").environ,
                                                                              "PYTHONUTF8": "1"})
        assert r.returncode == 0, r.stderr[-2000:]
        res = json.loads(r.stdout.strip().splitlines()[-1])
    assert res["absent_npy"] and res["absent_meta"], res
    assert res["grow"] == {"rows_n": 37, "rows_s": 37, "cols_w": 26, "cols_e": 0}
    assert (res["nx"], res["ny"]) == (149, 167) and res["nx"] * res["ny"] == 24883
    assert res["old_block"] and res["new_nodes"] == 24883 - 123 * 93
    assert res["max_dev_deg"] <= 1e-9 and res["frame_dev_m"] <= 1e-9, res
    mg = res["meta"]
    assert mg["base_bbox_swne"] == [32.771983, -117.069563, 32.805287, -117.017103]
    assert [round(v, 6) for v in mg["bbox_swne"]] == [32.75865, -117.080708, 32.81862, -117.017103]
    assert all(e is not None for e in res["refusals"]) and "rows_s" in res["refusals"][0]
    assert res["absent_spec"]
