"""drive_test's replication reads the raw 3DEP profile in the LOCAL index space when one is written (Lariat V3,
ledger 0048). ``z_raw_m`` is per geojson vertex; centerline.local.json is that ring rotated to route.start_at (2
vertices on the Lariat's paint line), so pairing them by index compares points 2-6 m apart along a 10 % climb.
scripts.elevation.road_profile writes ``z_raw_local_m``; without it the gate reads ``z_raw_m`` exactly as before."""
from __future__ import annotations

import json

from scripts.geometry.drive_test import run
from tests.geometry.test_drive_test import _project


def _replication(elev: dict) -> dict:
    d = _project()
    (d / "data" / "centerline.elevation.json").write_text(json.dumps(elev))
    return run(d)["replication_vs_measured"]


def test_replication_prefers_the_local_raw_profile_and_falls_back_unchanged():
    n = len(json.loads((_project() / "data" / "centerline.local.json").read_text())["points_xyz_m"])
    assert _replication({"z_raw_m": [5.0] * n}) == {"median": 5.0, "p95": 5.0, "max": 5.0}       # as before
    assert _replication({"z_raw_m": [5.0] * n, "z_raw_local_m": [0.0] * n}) == {"median": 0.0, "p95": 0.0, "max": 0.0}
