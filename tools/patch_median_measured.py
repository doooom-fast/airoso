"""Lake Murray's median bushes at their lidar heights, applied to an INSTALLED trees.txt (config-only, like 2026-11-13's
Bush.bin fix). Kevin 2026-11-18: "we've reduced lake murrays center bushes far too much" -> "B: lidar height each".

    python tools/patch_median_measured.py --trees-txt <track>/extension/trees/trees.txt \
        --models <track>/extension/trees --scatter tracks/san-diego-lake-murray/data/scatter_positions.json \
        --heights tracks/san-diego-lake-murray/source/vegetation/median_heights.lidar.json \
        --out <new trees.txt> --report <report.json>

Stdlib only. Reads each median model's tree.ini [BASIC] HEIGHT / WIDTH from the installed models (a .bin is a zip; a
folder <model>/tree.ini works too). Finds the median_planting block (make_treefx writes it after `configure: seed =
20261023`, 20261008 + len("median_planting")) and matches every tree line in it to its spot by the position as written
(pos = x, y, -z at 2 decimals). A spot whose lidar height is at least min_h_m gets size = h / HEIGHT (3 decimals) and
width = crown / (WIDTH x size), the same lines tools/make_treefx.py writes under scenery.treefx.median_measured; every
other line is copied byte for byte. Refuses (exit 1, writes nothing) when the block is missing, a line in it matches no
spot or two, or a model's HEIGHT / WIDTH can't be read.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

MEDIAN_SEED = 20261008 + len("median_planting")
LINE = re.compile(r"^tree:\s*(?P<model>[^;]+?)\s*;\s*pos=\s*(?P<x>-?\d+\.\d+),\s*(?P<y>-?\d+\.\d+),\s*(?P<nz>-?\d+\.\d+)\s*;(?P<rest>.*)$")


def tree_ini(models: Path, model: str) -> dict:
    """{'HEIGHT': float, 'WIDTH': float} off the model's tree.ini [BASIC]"""
    text = None
    p = models / model
    if p.is_file() and zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.lower().rsplit("/", 1)[-1] == "tree.ini"]
            if names:
                text = z.read(sorted(names, key=len)[0]).decode("utf-8", "replace")
    for d in (p, models / p.stem):
        if text is None and (d / "tree.ini").is_file():
            text = (d / "tree.ini").read_text(encoding="utf-8", errors="replace")
    if text is None:
        raise SystemExit(f"[median] no tree.ini for {model} under {models} (a .bin zip or a {model}/ folder)")
    sec, out = None, {}
    for raw in text.splitlines():
        ln = raw.split(";", 1)[0].strip()
        if ln.startswith("[") and ln.endswith("]"):
            sec = ln[1:-1].strip().upper()
        elif sec == "BASIC" and "=" in ln:
            k, v = (t.strip() for t in ln.split("=", 1))
            if k.upper() in ("HEIGHT", "WIDTH"):
                out[k.upper()] = float(v)
    if set(out) != {"HEIGHT", "WIDTH"}:
        raise SystemExit(f"[median] {model}: tree.ini [BASIC] HEIGHT / WIDTH not both found ({out})")
    return out


def patch(lines, spots, mpos, min_h, ratio, models):
    """(new lines, report). lines: trees.txt without newlines"""
    if len(spots) != len(mpos):
        raise SystemExit(f"[median] {len(spots)} measured spots but {len(mpos)} median_planting spots")
    by_key = {}
    for i, (e, (x, z, h, crown)) in enumerate(zip(mpos, spots)):
        if abs(e["x"] - x) > 0.006 or abs(e["z"] - z) > 0.006:
            raise SystemExit(f"[median] spot {i} at ({x}, {z}) is not median_planting[{i}] ({e['x']}, {e['z']})")
        key = (f"{round(e['x'], 2):.2f}", f"{-round(e['z'], 2):.2f}")
        by_key.setdefault(key, []).append(i)
    try:
        start = lines.index(f"configure: seed = {MEDIAN_SEED}")
    except ValueError:
        raise SystemExit(f"[median] no `configure: seed = {MEDIAN_SEED}` (the median_planting block) in trees.txt")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("configure: seed")), len(lines))
    ini, out = {}, list(lines)
    rep = {"block_lines": [start + 1, end], "tree_lines": 0, "measured": 0, "crown_measured": 0, "kept": 0,
           "per_model": {}, "drawn_h_before_m": [], "drawn_h_after_m": []}
    seen = set()
    for j in range(start + 1, end):
        if not lines[j].startswith("tree:"):
            continue
        m = LINE.match(lines[j])
        if not m:
            raise SystemExit(f"[median] line {j + 1} doesn't parse: {lines[j]!r}")
        hits = by_key.get((m["x"], m["nz"]), [])
        if len(hits) != 1:
            raise SystemExit(f"[median] line {j + 1} at pos ({m['x']}, {m['nz']}) matches {len(hits)} spots")
        i = hits[0]
        if i in seen:
            raise SystemExit(f"[median] spot {i} has two lines in the block")
        seen.add(i)
        rep["tree_lines"] += 1
        model = m["model"].strip()
        if model not in ini:
            ini[model] = tree_ini(models, model)
        H, W = ini[model]["HEIGHT"], ini[model]["WIDTH"]
        rest = m["rest"]
        old_size = float(re.search(r"size\s*=\s*(-?\d+(?:\.\d+)?)", rest).group(1))
        pm = rep["per_model"].setdefault(model, {"lines": 0, "measured": 0, "HEIGHT": H, "WIDTH": W})
        pm["lines"] += 1
        _x, _z, h, crown = spots[i]
        if h is None or h < min_h:
            rep["kept"] += 1
            continue
        size_txt = f"{h / H:.3f}"
        cw = float(crown) if crown is not None else float(h) * ratio
        rest = re.sub(r"size\s*=\s*-?\d+(?:\.\d+)?", f"size = {size_txt}", rest, count=1)
        rest = re.sub(r";\s*width\s*=\s*-?\d+(?:\.\d+)?", "", rest)
        rest = rest.rstrip() + f"; width = {cw / (W * float(size_txt)):.2f}"
        out[j] = f"tree: {model}; pos={m['x']}, {m['y']}, {m['nz']};{rest}"
        rep["measured"] += 1
        rep["crown_measured"] += crown is not None
        pm["measured"] += 1
        rep["drawn_h_before_m"].append(round(old_size * H, 2))
        rep["drawn_h_after_m"].append(round(float(size_txt) * H, 2))
    rep["spots_without_a_line"] = len(spots) - len(seen)      # dropped at build (a sign within 2.5 m), not an error
    for k in ("drawn_h_before_m", "drawn_h_after_m"):
        a = sorted(rep[k])
        rep[k] = ({f"p{p}": a[min(len(a) - 1, int(p / 100 * (len(a) - 1) + 0.5))] for p in (10, 25, 50, 75, 90)}
                  if a else {})
    return out, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for a in ("--trees-txt", "--models", "--scatter", "--heights", "--out", "--report"):
        ap.add_argument(a, required=True, type=Path)
    a = ap.parse_args(argv)
    raw = a.trees_txt.read_text(encoding="utf-8")
    lines = raw.split("\n")
    trail = lines[-1] == ""
    if trail:
        lines = lines[:-1]
    md = json.loads(a.heights.read_text(encoding="utf-8"))
    mpos = json.loads(a.scatter.read_text(encoding="utf-8"))["median_planting"]
    out, rep = patch(lines, md["spots"], mpos, float(md["min_h_m"]), float(md["crown_over_h_fallback"]), a.models)
    changed = sum(1 for x, y in zip(lines, out) if x != y)
    assert changed == rep["measured"] and len(out) == len(lines)
    a.out.write_text("\n".join(out) + ("\n" if trail else ""), encoding="utf-8")
    rep.update({"_doc": "tools/patch_median_measured.py (Kevin 2026-11-18: \"B: lidar height each\")",
                "trees_txt": str(a.trees_txt), "out": str(a.out), "lines_total": len(lines), "lines_changed": changed})
    a.report.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"[median] {rep['tree_lines']} median lines: {rep['measured']} set to their lidar height "
          f"({rep['crown_measured']} with a measured crown), {rep['kept']} kept; {changed} of {len(lines)} lines changed "
          f"-> {a.out}; drawn height before {rep['drawn_h_before_m']} after {rep['drawn_h_after_m']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
