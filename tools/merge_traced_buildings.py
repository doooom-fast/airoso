"""Add Lake Murray's aerial-traced buildings to the WORKSHOP's copy of the expansion cache, the file the assembler's buildings pass reads.

    python tools/merge_traced_buildings.py <project-dir>

The committed data/buildings.expansion.cache.json stays OSM's own bytes (its provenance pins the md5, tests/tools/
test_fetch_buildings_cache.py). data/buildings.traced.json holds what OSM does not have, in the same schema, each with its "_source":
ledger 0054's "Left": the Mission Gorge apartment blocks, read off NAIP. Idempotent: a footprint already in the copy is not added twice.
"""
import json
import sys
from pathlib import Path

proj = Path(sys.argv[1])
traced = proj / "data" / "buildings.traced.json"
cache = proj / "data" / "buildings.expansion.cache.json"
if not traced.exists():
    print("[traced buildings] none")
    raise SystemExit(0)
b = json.loads(cache.read_text(encoding="utf-8"))
have = {json.dumps(x["geom"]) for x in b}
new = [x for x in json.loads(traced.read_text(encoding="utf-8")) if json.dumps(x["geom"]) not in have]
b += [{k: x[k] for k in ("building", "levels", "height", "geom")} for x in new]
cache.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8", newline="\n")
print(f"[traced buildings] {len(new)} added to the workshop's cache ({len(b)} in all)")
