"""Phase 3 Step 0.5: grow the installed 40 m heightfield to cols_w 88 with the plan's own tools/grow_heightfield.py.

The tool grows from the INSTALLED (ungrown, v0.18.0) grid and fetches every node it does not hold; Phase 1 already
fetched the 26-column growth (13,444 nodes, data/heightfield.npy today). Its ``fetch`` hook answers those from the
26-column grid (matched by position within 1e-9 deg) and sends only the rest to 3DEP: the plan's +62 columns.

    python -I p3_grow.py <airoso> <growproj> <grown26-data-dir> <out-dir> <cap-bytes> <log.jsonl>
growproj: track.config.json (grid_grow cols_w 88) + data/{centerline.geojson, heightfield.npy, heightfield.meta.json}
(the installed grid, from git e8561e03^).
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    airoso, proj, g26, out, cap, log = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]),
                                        int(sys.argv[5]), sys.argv[6])
    sys.path.insert(0, str(HERE))
    import p3_net
    import numpy as np
    from scipy.spatial import cKDTree
    spec = importlib.util.spec_from_file_location("grow_heightfield", airoso / "tools" / "grow_heightfield.py")
    gh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gh)
    hf = gh.load_v021_heightfield()

    # the 26-column grid's own positions, by the same layout code (no fetch)
    meta26 = json.loads((g26 / "heightfield.meta.json").read_text())
    grid26, ny26, nx26 = gh.read_npy(g26 / "heightfield.npy")
    gj = json.loads((proj / "data" / "centerline.geojson").read_text())
    full = next(f for f in gj["features"] if f["properties"].get("kind") == "full")
    coords = [(lon, lat) for lon, lat in full["geometry"]["coordinates"]]
    seen = {}

    def capture(points, **_k):
        seen["p"] = list(points)
        return [0.0] * len(points)

    real = hf.usgs_3dep
    hf.usgs_3dep = type("S", (), {"sample_points": staticmethod(capture)})
    try:
        _g, m26 = hf.build_heightfield(list(coords), hf.HF_SPACING_M, hf.HF_MARGIN_M, grow=meta26["grid_grow"])
    finally:
        hf.usgs_3dep = real
    if m26 != meta26:
        raise SystemExit(f"the 26-column layout {m26} is not data/heightfield.meta.json {meta26}")
    p26 = np.array(seen["p"])
    v26 = np.array([grid26[k // nx26][k % nx26] for k in range(nx26 * ny26)])
    tree = cKDTree(p26)
    budget = p3_net.Budget(cap, log)
    stat = {}

    def fetch(points):
        pts = np.array(points)
        d, j = tree.query(pts)
        hit = d <= 1e-9
        out_v = [None] * len(points)
        for k in np.nonzero(hit)[0]:
            out_v[k] = float(v26[j[k]])
        todo = [k for k in range(len(points)) if not hit[k]]
        stat.update({"asked": len(points), "from_grown26": int(hit.sum()), "to_3dep": len(todo),
                     "max_match_deg": float(d[hit].max()) if hit.any() else None})
        print(f"[p3_grow] {len(points)} non-installed nodes: {int(hit.sum())} from the 26-column grid, "
              f"{len(todo)} to 3DEP ({-(-len(todo) // 450)} requests)", flush=True)
        vals = p3_net.sample_points([tuple(points[k]) for k in todo], budget,
                                    progress=lambda a, n: print(f"  [p3_grow] {a}/{n}", flush=True))
        for k, v in zip(todo, vals):
            out_v[k] = None if v is None else float(v)
        return out_v

    t0 = time.time()
    proof = gh.grow(proj, out, offline=False, fetch=fetch)
    grid88, ny88, nx88 = gh.read_npy(out / "heightfield.npy")
    meta88 = json.loads((out / "heightfield.meta.json").read_text())
    dc = meta88["grid_grow"]["cols_w"] - meta26["grid_grow"]["cols_w"]
    dr = meta88["grid_grow"]["rows_n"] - meta26["grid_grow"]["rows_n"]
    same26 = all(grid88[j + dr][i + dc] == grid26[j][i] for j in range(ny26) for i in range(nx26))
    proof.update({"p3": {"what": "EXPANSION-PHASE3-PLAN Step 0.5, cols_w 26 -> 88 (data host data run 2026-11-22)",
                         "fetch_hook": stat, "grown26_block_identical": same26,
                         "requests_sent": budget.requests, "bytes": budget.used, "backoffs": budget.backoffs,
                         "user_agent": p3_net.UA, "seconds": round(time.time() - t0, 1),
                         "note": "the tool's own 'requests' / 'new_nodes_from_3dep' count every non-installed node; "
                                 "the fetch hook served the 26-column growth from data/heightfield.npy"}})
    (out / "heightfield.grow.proof.json").write_text(json.dumps(proof, indent=1))
    print(json.dumps(proof["p3"]), flush=True)
    if not same26:
        raise SystemExit("the 26-column block is not the current grid")


if __name__ == "__main__":
    main()
