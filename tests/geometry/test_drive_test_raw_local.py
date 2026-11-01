"""drive_test's replication reads the raw 3DEP profile in the LOCAL index space — by the one mapping main records.

The branch of 2026-10-12 (307a3b7, Lariat P2) had scripts.elevation.road_profile write ``z_raw_local_m`` (``z_raw_m``
rotated into centerline.local.json's order) and drive_test prefer it, because pairing ``z_raw_m`` (per geojson
vertex) with the local ring by bare index compared points 2-6 m apart along a 10 % climb (the Lariat's paint line is
rotated 2 vertices to route.start_at). Main fixed the same defect generally on 2026-10-29 (ledger 0060, High Plains:
815 of 1,074 points): projection records the permutation as ``source_index`` and drive_test applies
``projection.in_local_order`` to ``z_raw_m`` (tests/geometry/test_projection_orientation.py pins the mapping). So
``z_raw_local_m`` is NOT read here — it would be rotated twice — and this test pins that: a file carrying both keys
is judged on ``z_raw_m`` alone, exactly as a file carrying ``z_raw_m`` only.
"""
from __future__ import annotations

import json

from scripts.geometry.drive_test import run
from tests.geometry.test_drive_test import _project


def _replication(elev: dict) -> dict:
    d = _project()
    (d / "data" / "centerline.elevation.json").write_text(json.dumps(elev))
    return run(d)["replication_vs_measured"]


def test_replication_reads_z_raw_m_once_through_the_recorded_permutation_and_ignores_z_raw_local_m():
    n = len(json.loads((_project() / "data" / "centerline.local.json").read_text())["points_xyz_m"])
    assert _replication({"z_raw_m": [5.0] * n}) == {"median": 5.0, "p95": 5.0, "max": 5.0}       # as before
    # the branch's pre-rotated copy is not a second input: main's in_local_order is the one mapping
    assert _replication({"z_raw_m": [5.0] * n, "z_raw_local_m": [0.0] * n}) == {"median": 5.0, "p95": 5.0, "max": 5.0}
