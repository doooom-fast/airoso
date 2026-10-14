"""PHASE 5 identity proof, part B: the FULL chain (tools/ship_sd.sh from the worktree, the patched ENG copy) on a fresh
scratch copy of the workshop with NO stub declaration, against the installed v0.18.0's own outputs (the workshop
project, read only): every data/ file and every built file the chain wrote, byte for byte."""
import hashlib
import json
import sys
from pathlib import Path

S = Path(r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/p5")
WS = Path(r"C:/Users/Owner/Documents/GitHub/k10-sd-v021/project")
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else S / "proj_id"
T0 = (RUN / "track.config.json").stat().st_mtime - 2.0     # the chain's first step re-copies it


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


rows = {"identical": [], "differ": [], "new_only": [], "stub_files": []}
for sub in ("data", "build", "ai", "blender/split"):
    base = RUN / sub
    if not base.exists():
        continue
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.stat().st_mtime < T0:
            continue                           # only what this run wrote
        rel = p.relative_to(RUN).as_posix()
        if "stub" in p.name.lower():
            rows["stub_files"].append(rel)
            continue
        if p.suffix in (".blend", ".blend1"):
            continue
        q = WS / rel
        if not q.exists():
            rows["new_only"].append(rel)
        elif p.stat().st_size == q.stat().st_size and md5(p) == md5(q):
            rows["identical"].append(rel)
        else:
            rows["differ"].append(rel)
out = {"run": str(RUN), "counts": {k: len(v) for k, v in rows.items()}, **rows}
(S / "identity_B.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["counts"]))
print("differ:", rows["differ"][:60])
print("new_only:", rows["new_only"][:30])
print("stub files:", rows["stub_files"])
