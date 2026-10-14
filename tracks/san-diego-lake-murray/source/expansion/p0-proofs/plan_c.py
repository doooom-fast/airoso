"""C: the new config's lattice (D2 far box + Cowles to 32.828), corridor = the v0.18.0 I-8 centreline (P2 re-builds
it over the grown far box): topology and how many 3DEP samples are not in the cache. No fetch."""
import json, sys, time
from pathlib import Path
AIR, PROJ, NEWC = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(AIR))
from scripts.elevation import terrain_sample as ts
from scripts.geometry import terrain_tiers as tt
cfg = json.loads(NEWC.read_text(encoding="utf-8"))
lines, origin, files = ts.road_inputs(PROJ)
spec = tt.TierSpec(cfg["terrain"], origin, False)
cor = json.loads((PROJ / "data" / "corridor.i8.json").read_text())
corridor_lines = [[(x, 0.0, z) for x, z in cor["centreline_local"]]]
frame = spec.frame(tt.load_heightfield_meta(PROJ))
t0 = time.time()
topo = tt.Topology(spec, lines, corridor_lines, closed_first=True, frame=frame)
st = topo.stats()
cache = ts.SampleCache(PROJ / "data" / ts.SAMPLES, spec, frame)
rkeys = topo.refine_keys(); aakeys = topo.aa_keys()
need = set(topo.vkeys) | set(rkeys) | set(tt.aa_taps(aakeys))
miss = cache.missing(sorted(need))
print(json.dumps({"stats": st, "need": len(need), "missing": len(miss), "requests": -(-len(miss) // ts.CHUNK),
                  "far_bbox": spec.far_bbox_swne, "secs": round(time.time() - t0, 1)}, indent=1))
