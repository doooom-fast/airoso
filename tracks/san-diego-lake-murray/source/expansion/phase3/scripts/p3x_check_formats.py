"""Read the Phase 3 data files through the same code that reads Phase 2's (tools/author_expansion.py,
tools/make_treefx.py, the assertions of tests/tools/test_p3_repair_round2.py), and check the folder against its own
provenance.json. Exit 0 when every check passes.

    python -I p3x_check_formats.py <airoso repo> <phase3 folder>
"""
import csv
import hashlib
import json
import sys
import tempfile
import shutil
from pathlib import Path


def main():
    repo, ph = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(repo / "tools"))
    sys.path.insert(0, str(repo))
    import author_expansion as ae
    import make_treefx as mt
    fails, n = [], 0

    def check(ok, what):
        nonlocal n
        n += 1
        print(("PASS " if ok else "FAIL ") + what)
        if not ok:
            fails.append(what)

    prov = json.loads((ph / "provenance.json").read_text())["files"]
    for name, rec in prov.items():
        p = ph / name
        check(p.exists() and p.stat().st_size == rec["bytes"] and
              hashlib.sha256(p.read_bytes()).hexdigest() == rec["sha256"], f"provenance: {name}")
    # the eye table: author_expansion's reader (csv.DictReader) and its per-row arithmetic
    rows = list(csv.DictReader((ph / "aerial__widths_eye.csv").open(encoding="utf-8")))
    ref = next(csv.reader((repo / "tracks/san-diego-lake-murray/source/expansion/aerial__widths_eye.csv")
                          .open(encoding="utf-8")))
    check(list(rows[0].keys())[:len(ref)] == ref, "widths: Phase 2's columns first, in order")
    ok = True
    for r in rows:
        if not r["eye_curb_to_curb_m"]:
            continue
        rec = {"row": r, "mirrored": False}
        lft, rgt, m, off = ae.reading_offsets(rec, bool(float(r["median_m"] or 0) > 0))
        ok &= abs((lft - rgt) - float(r["eye_curb_to_curb_m"])) < 0.3 or not r["cw_left_m"]
        ae.median_type(r["median_kind"])
    check(ok, "widths: author_expansion.reading_offsets reproduces every row's curb to curb")
    st = [r for r in rows if " st " in r["label"]]
    check(len(st) == 29, f"widths: 29 A4 stations ({len(st)})")
    # the paint: author_expansion.load_paint_measured on a scratch track, and the round-2 test's assertions
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "source" / "expansion").mkdir(parents=True)
        shutil.copyfile(ph / "aerial__paint_west.json", t / "source" / "expansion" / "aerial__paint_north.json")
        meas, pv = ae.load_paint_measured(t)
    check(set(meas) == {"P3-WAR", "P3-ZION", "P3-MG"} and all(meas.values()), "paint: load_paint_measured reads all three")
    p = json.loads((ph / "aerial__paint_west.json").read_text())
    check(p["windows"] and all(w["url"].startswith("https://imagery.nationalmap.gov/") for w in p["windows"]),
          "paint: every window from The National Map")
    check(all(k in p["parameters"] for k in ("SEG_MIN", "MEDIAN_SEP_M", "MEDIAN_MIN_M", "FRAME_SIGMA_M", "OUTLIER_M",
                                             "GAP_MAX_M", "SANITY_M")), "paint: thresholds recorded")
    fsha = hashlib.sha256((ph / "routes__stations.west.json").read_bytes()).hexdigest()[:12]
    check(p["intermediate_sha256_12"] == fsha, "paint: measured in routes__stations.west.json (sha matches)")
    # the vegetation bins: make_treefx's own lookup
    bins = json.loads((ph / "aerial__veg_bins.json").read_text())
    obj = type("B", (), {})()
    obj.bins, obj.bin_m = bins, 250.0
    sh = [mt.North.shares(obj, pid, side, s) if hasattr(mt, "North") else None
          for pid in bins for side in (1, -1) for s in (0.0, 600.0, 5000.0)]
    check(all(x is not None and 0 <= x[0] <= 1 and 0 <= x[1] <= 1 for x in sh), "veg bins: make_treefx shares() reads them")
    check(all(len(v) == 4 and sum(v) > 0 for b in bins.values() for v in b.values()), "veg bins: four classes per bin")
    # the station frame: make_treefx's piece reader (columns / stations)
    fr = json.loads((ph / "routes__stations.west.json").read_text())
    ok = all({"s", "x", "z", "left_m", "right_m", "median_type", "median_w_m"} <= set(pc["columns"]) for pc in fr["pieces"])
    check(ok, "frame: the columns make_treefx / aerial_paint_north read")
    # the lamps / signals file: Phase 2's keys
    ls = json.loads((ph / "pipeline__osm_lamps_signals.json").read_text())
    check({"source", "osm_base", "bbox", "street_lamps", "traffic_signals"} <= set(ls), "lamps: Phase 2's keys")
    print(f"{n - len(fails)} passed, {len(fails)} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
