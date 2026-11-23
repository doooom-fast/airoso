"""a scratch workshop made the way tools/ship_track.sh's sync-in makes one: ship.json sync_in required / optional / globs /
assets / seed, from the worktree into an EMPTY folder.   python make_ws.py <airoso> <track> <new workshop dir>"""
import glob
import json
import shutil
import sys
from pathlib import Path

air, track, ws = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
src = air / "tracks" / track
si = json.loads((src / "ship.json").read_text(encoding="utf-8"))["sync_in"]
if ws.exists() and any(ws.iterdir()):
    raise SystemExit(f"{ws} is not empty")
(ws / "data").mkdir(parents=True, exist_ok=True)
n = {"required": 0, "optional": 0, "globs": 0, "assets": 0, "seed": 0}
for f in si.get("required", []):
    (ws / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / f, ws / f)
    n["required"] += 1
for f in si.get("optional", []):
    if (src / f).is_file():
        (ws / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, ws / f)
        n["optional"] += 1
for g in si.get("globs", []):
    for f in glob.glob(str(src / g)):
        rel = Path(f).relative_to(src)
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, ws / rel)
        n["globs"] += 1
for f in si.get("assets", []):
    (ws / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(air / f, ws / f)
    n["assets"] += 1
for f in si.get("seed", []):
    if not (ws / f).exists():
        if (src / f).read_bytes()[:23] == b"version https://git-lfs":
            raise SystemExit(f"{f} is a Git LFS pointer")
        (ws / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, ws / f)
        n["seed"] += 1
print(n)
