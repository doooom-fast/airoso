"""Copy b17's records (ship.json sync_out data files + the split manifest) into the worktree; compare ai/full. loop.blend
is left as the PC synced it (its 0.1.7 copy comes back with the PC's rehearsal / install)."""
import hashlib, json, shutil, sys
from pathlib import Path
A = Path("/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/wt-roadtex/tracks/milford-road-course-lm")
B = Path("/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys/work/roadtex/b17")
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None
spec = json.loads((A / "ship.json").read_text())
for f in sorted((B / "ai" / "full").iterdir()):
    a, b = md5(A / "ai" / "full" / f.name), md5(f)
    print("ai/full", f.name, "SAME" if a == b else "DIFFER")
for rel in spec["sync_out"]["files"]:
    rel = rel.replace("{id}", "full")
    s = B / rel
    if s.exists():
        same = md5(A / rel) == md5(s)
        (A / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, A / rel)
        print(rel, "unchanged" if same else "updated")
    else:
        print(rel, "(not written by this build)")
for s, d in spec["sync_out"]["map"]:
    shutil.copyfile(B / s, A / d); print(d, "copied")
