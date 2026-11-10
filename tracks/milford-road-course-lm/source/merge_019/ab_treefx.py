"""A/B: make_treefx.plan() at 48daf25a vs this branch, on every track whose config names scenery.treefx (all_species=True:
positions and model choice without the .bin files). Ledger 0082 vegetation pass, the Lake Murray check."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

W = Path(sys.argv[1])
base = Path(sys.argv[2])
sys.path.insert(0, str(W))
sys.path.insert(0, str(W / "tools"))


def load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


A = load(base, "mt_base")
B = load(W / "tools" / "make_treefx.py", "mt_branch")
for cfgp in sorted((W / "tracks").glob("*/track.config.json")):
    cfg = json.loads(cfgp.read_text(encoding="utf-8"))
    if "treefx" not in (cfg.get("scenery") or {}) or cfgp.parent.name.startswith("milford"):
        continue
    out = []
    for m in (A, B):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                p = m.plan(cfgp.parent, all_species=True)
            out.append(hashlib.md5("\n".join(p["lines"]).encode()).hexdigest() + f" lines {len(p['lines'])}")
        except BaseException as e:
            out.append(f"ERR {type(e).__name__}: {str(e)[:160]}")
    print(cfgp.parent.name, "| base", out[0], "| branch", out[1], "| SAME" if out[0] == out[1] else "| DIFFER", flush=True)
