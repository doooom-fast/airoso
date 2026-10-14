"""Fresh scratch copy of the v021 workshop project for the P1 weld rehearsal: everything but build/ (and release/,
loop.blend1, the regenerable gate OBJs). Read-only on the workshop."""
import shutil
import sys
from pathlib import Path

WS = Path(r"C:/Users/Owner/Documents/GitHub/k10-sd-v021/project")
OUT = Path(sys.argv[1])
if OUT.exists():
    raise SystemExit(f"{OUT} exists - remove it first (a FRESH copy)")


def ignore(d, names):
    d = Path(d)
    out = set()
    for n in names:
        if d == WS and n in ("build", "release", "loop.blend1"):
            out.add(n)
        elif d == WS / "data" and n.endswith(".obj"):
            out.add(n)
    return out


shutil.copytree(WS, OUT, ignore=ignore)
n = sum(1 for _ in OUT.rglob("*"))
print("copied", n, "entries to", OUT)
