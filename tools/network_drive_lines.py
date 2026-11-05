"""The freeway port's other carriageways as drive_test LINES (ledger 0080 phase 2; drive_test --line network).

drive_test walks the port's line (I 8 eastbound) only; every carriageway tools/network_connectors.py adds is a connector
the assembler sweeps beside it, which no wheel-path gate would otherwise drive. This writes them in drive_test's --line
contract (``data/drive_lines.network.json``: {"lines": {id: {"points_xyz_m", "widths_m"}}}, the local frame the gate
OBJ is in; tools/expansion_lines.py's shape), each connector exactly as the assembler sweeps it: its points through
v021's ``smooth_centerline`` with the assembler's connector call (sigma 1.5 points, 1 pass, sigma_y 1.0;
scripts-v021/blender/build_loop_blend.py), its widths as recorded. A connector record that carries ``network``
(network_connectors') is a line; Lake Murray's side streets carry none and never get here (Lake Murray never runs it).

    python tools/network_drive_lines.py <project-dir>      (stdlib + scripts-v021's smooth.py)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOOTH = ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py"


def _smooth_mod():
    spec = importlib.util.spec_from_file_location("v021_smooth", SMOOTH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build(proj: Path) -> dict:
    data = proj / "data"
    conn = json.loads((data / "connectors.local.json").read_text(encoding="utf-8"))
    sm = _smooth_mod()
    lines = {}
    for c in conn.get("connectors") or []:
        if not c.get("network") or len(c["points_xyz_m"]) < 2:
            continue
        pts = sm.smooth_centerline([tuple(p) for p in c["points_xyz_m"]], sigma_pts=1.5, passes=1, sigma_y_pts=1.0)
        lines[c["name"]] = {"points_xyz_m": [[round(v, 3) for v in p] for p in pts],
                            "widths_m": [round(float(w), 3) for w in c["widths_m"]]}
    if not lines:
        raise SystemExit("[network_lines] no network connector in data/connectors.local.json")
    (data / "drive_lines.network.json").write_text(json.dumps({
        "_doc": "ledger 0080 phase 2: the freeway port's network connectors as drive_test --line network lines "
                "(tools/network_drive_lines.py)",
        "frame": "local = engine (x E, y up, z N), the gate OBJ's", "lines": lines}), encoding="utf-8")
    print(f"[network_lines] {len(lines)} line(s): " + ", ".join(f"{k} ({len(v['points_xyz_m'])} pts)" for k, v in lines.items()))
    return lines


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]).resolve())
