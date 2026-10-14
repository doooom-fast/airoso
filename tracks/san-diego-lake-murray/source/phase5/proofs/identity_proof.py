"""PHASE 5 identity proof, part A (tool level): with NO stub declaration every output of every changed tool is
byte-identical to main (HEAD) on the real v0.18.0 workshop data. Part B (the full chain) is identity_chain.py.

  A1 trim_connectors  HEAD vs worktree on the workshop's connectors.local.json.pre-trim: every file in data/ identical
  A2 stub_roads apply no declaration: every file in data/ untouched (bytes)
  A3 verify_stubs     no plan: exit 0, nothing written
  A4 audit_mesh       HEAD vs worktree on the v0.18.0 BUILT gate OBJs (street + race_cw + race_acw): audit*.json identical
  A5 pbr              HEAD vs worktree: every mesh name in the three v0.18.0 gate OBJs binds the same row + textures
  A6 ship_sd.sh       every line the worktree adds runs only under a stub-file test, or only names stub files
"""
import difflib
import hashlib
import importlib.util
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

S = Path(r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-Documents-GitHub-airoso/59395b0b-e098-4e22-9ea8-1346efc0cf70/scratchpad/p5")
W = Path(r"C:/Users/Owner/Documents/GitHub/airoso/.claude/worktrees/wf_f07e8864-ebf-1")
WS = Path(r"C:/Users/Owner/Documents/GitHub/k10-sd-v021/project")      # read only
H = S / "head"
out = {}
env = dict(os.environ, PYTHONUTF8="1")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def snap(d):
    return {p.name: md5(p) for p in sorted(Path(d).iterdir()) if p.is_file()}


# A1 + A2
tmp = Path(tempfile.mkdtemp(dir=S))
for tag in ("head", "new"):
    d = tmp / tag
    (d / "data").mkdir(parents=True)
    for f in ("connectors.local.json.pre-trim", "connectors.local.json", "centerline.local.json", "median_bands.json"):
        shutil.copy2(WS / "data" / f, d / "data" / f)
    shutil.copy2(WS / "track.config.json", d / "track.config.json")
before = snap(tmp / "new" / "data")
r = subprocess.run([sys.executable, str(W / "tools" / "stub_roads.py"), "apply", str(tmp / "new")], capture_output=True,
                   text=True, env=env)
after = snap(tmp / "new" / "data")
out["A2_stub_roads_apply_no_declaration"] = {"exit": r.returncode, "stdout": r.stdout.strip(), "untouched": before == after}
subprocess.run([sys.executable, str(H / "trim_connectors.py"), str(tmp / "head")], capture_output=True, env=env, check=True)
subprocess.run([sys.executable, str(W / "tools" / "trim_connectors.py"), str(tmp / "new")], capture_output=True, env=env,
               check=True)
a, b = snap(tmp / "head" / "data"), snap(tmp / "new" / "data")
out["A1_trim_connectors"] = {"files": sorted(a), "identical": a == b,
                             "md5": {k: v for k, v in b.items()}}

# A3
d3 = tmp / "vs"
(d3 / "data").mkdir(parents=True)
shutil.copy2(WS / "track.config.json", d3 / "track.config.json")
r = subprocess.run([sys.executable, str(W / "tools" / "verify_stubs.py"), str(d3)], capture_output=True, text=True, env=env)
out["A3_verify_stubs_no_plan"] = {"exit": r.returncode, "stdout": r.stdout.strip(),
                                  "wrote": sorted(p.name for p in (d3 / "data").iterdir())}

# A4 — the audits on the v0.18.0 BUILT OBJs (copied: the audit writes data/audit*.json beside them)
d4 = S / "id_audit"
if not d4.exists():
    shutil.copytree(WS / "data", d4 / "data")
    shutil.copy2(WS / "track.config.json", d4 / "track.config.json")
assert not (d4 / "data" / "stubs.built.json").exists()
res = {}
for label, args in (("street", []), ("race_cw", ["--layout", "race_cw"]), ("race_acw", ["--layout", "race_acw"])):
    name = "audit.json" if label == "street" else f"audit.{label}.json"
    got = {}
    for tag, path in (("head", H / "audit_mesh.py"), ("new", W / "scripts" / "geometry" / "audit_mesh.py")):
        code = ("import runpy, sys; sys.path.insert(0, r'%s'); sys.argv = ['audit_mesh', r'%s'] + %r; "
                "runpy.run_path(r'%s', run_name='__main__')" % (W, d4, args, path))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=str(W))
        got[tag] = (r.returncode, md5(d4 / "data" / name), r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    res[label] = {"head": got["head"], "new": got["new"], "identical": got["head"] == got["new"]}
out["A4_audit_mesh_on_v018_built"] = res

# A5
def load(p, nm):
    spec = importlib.util.spec_from_file_location(nm, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
ph, pn = load(H / "pbr.py", "_pbr_head"), load(W / "scripts" / "ac" / "pbr.py", "_pbr_new")
names = set()
for objn in ("track.obj", "track.race_cw.obj", "track.race_acw.obj"):
    with open(WS / "data" / objn, encoding="ascii", errors="replace") as f:
        for ln in f:
            if ln.startswith("o "):
                names.add(ln[2:].strip())
ov_h, ov_n = ph.load_overrides(WS), pn.load_overrides(WS)
TD = Path(str(W)) / "assets" / "textures"
def bind(m, ov, n):
    r = m.resolve(n, ov, tex_dir=TD)
    k = m.match_key(n)
    return (k, m.TEXTURES.get(k), Path(r["diffuse"]).name if r["diffuse"] else None, Path(r["normal"]).name if r["normal"] else None, r["overridden"])
diff = [n for n in sorted(names) if bind(ph, ov_h, n) != bind(pn, ov_n, n)]
out["A5_pbr"] = {"mesh_names": len(names), "differ": diff, "stub_names_in_v018": [n for n in names if n.upper().startswith("1WALL_STUB")],
                 "new_rows": [k for k in pn.TEXTURES if k not in ph.TEXTURES]}

# A6
old = (H / "ship_sd.sh").read_text(encoding="utf-8").splitlines()
new = (W / "tools" / "ship_sd.sh").read_text(encoding="utf-8").splitlines()
added = [l for l in difflib.ndiff(old, new) if l.startswith("+ ")]
removed = [l for l in difflib.ndiff(old, new) if l.startswith("- ")]
depth, guarded_lines, unguarded = 0, [], []
in_stub = False
stack = []
for ln in new:
    s = ln.strip()
    if s.startswith("if ") and "stubs" in s and s.endswith("then"):
        stack.append(True)
        continue
    if s.startswith("if ") and s.endswith("then"):
        stack.append(False)
        continue
    if s == "fi" and stack:
        stack.pop()
        continue
added_set = [l[2:] for l in added]
for l in added_set:
    s = l.strip()
    if not s or s.startswith("#"):
        continue
    unguarded.append(l)
# every executable added line: inside a stub-guarded block (checked by position) or a line that only adds stub file names
positions = []
stack = []
for i, ln in enumerate(new):
    s = ln.strip()
    if s.startswith("if ") and s.endswith("then"):
        stack.append(("stubs" in s) or (stack[-1] if stack else False) if False else ("stub" in s.lower()))
    elif s == "else" and stack:
        pass
    elif s == "fi" and stack:
        stack.pop()
    positions.append(any(stack))
bad = []
for i, ln in enumerate(new):
    s = ln.strip()
    if ln in added_set and s and not s.startswith("#"):
        names_only = re.sub(r"(stubs\.json|stubs\.plan\.json|stubs\.built\.json|verify_stubs\.json|stubs\.3dep\.json)", "", ln)
        if positions[i] or s.startswith(("if [", "fi", "else", 'STUBS="${STUBS:-$SRC/stubs.json}"')):
            continue
        # a modified line: identical to a removed one once the stub file names are dropped
        if any(re.sub(r'\s+', ' ', names_only.replace('"$PROJ/data/"', '').replace(' "$PROJ/data/"', '')).strip() ==
               re.sub(r'\s+', ' ', r[2:]).strip() for r in removed):
            continue
        bad.append(ln)
out["A6_ship_sd"] = {"added_lines": len(added), "removed_lines": [r[2:] for r in removed],
                     "executable_added_outside_a_stub_guard": bad}
shutil.rmtree(tmp, ignore_errors=True)
(S / "identity_A.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: (v if k != "A1_trim_connectors" else {"identical": v["identical"], "files": v["files"]}) for k, v in out.items()}, indent=1))
