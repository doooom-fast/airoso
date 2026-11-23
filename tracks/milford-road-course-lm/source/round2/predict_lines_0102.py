"""Milford round 2 (ledger 0102): the GM loop's intake line and swept line, as 0.1.15's build will write them, written into
tracks/milford-road-course-lm/data/ ahead of the build, so the round's plans on the swept line (the start / finish, the verge
trees, the trunk colliders: tools/circuit_dummies_blend.py and source/vegetation/scripts/veg_naip_verge.py /
veg_trunks_reach.py read data/centerline.local.json) are made, committed and tested on the lap that will be built.

    python -I tracks/milford-road-course-lm/source/round2/predict_lines_0102.py [--check]     (from the repo root)

The build itself never reads these two files: tools/lm_engine_intake.py deletes the raw snapshot and writes the intake line,
and ship.json's sync_in copies neither into the workshop, so the rehearsal makes its own and its sync_out brings them back.

  1. an empty workshop with ship.json's sync_in (as tools/ship_track.sh fills one), then tools/lm_engine_intake.intake:
     data/centerline.local.json there = the intake line = what the draft snapshots as data/centerline.raw.local.json;
  2. the draft's own smoothing (tracks/san-diego-lake-murray/scripts-v021/blender/build_loop_blend.py: smooth_centerline
     with route.smooth_sigma_pts / smooth_passes / smooth_sigma_y_pts; Milford declares no road_datum.profiles windows and
     no connectors), the points rounded to 4 decimals and written with json.dumps, as the draft writes them.
On 0.1.14's config the two reproduce the committed 0.1.14 files byte for byte (md5 0923d812... raw, 1244fc50... swept).
--check: write nothing, exit 1 unless the committed files are these.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MF = ROOT / "tracks" / "milford-road-course-lm"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _sync_in(ws: Path):
    spec = json.loads((MF / "ship.json").read_text(encoding="utf-8"))
    sin = spec.get("sync_in") or {}
    for rel in sin.get("required", []) + [r for r in sin.get("optional", []) if (MF / r).exists()]:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes((MF / rel).read_bytes())


def lines():
    """(raw text, swept text): the intake line and the draft's swept line, as the build writes them"""
    import lm_engine_intake as L
    spec = importlib.util.spec_from_file_location(
        "_v021_smooth", ROOT / "tracks" / "san-diego-lake-murray" / "scripts-v021" / "geometry" / "smooth.py")
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    cfg = json.loads((MF / "track.config.json").read_text(encoding="utf-8"))
    if [p for p in ((cfg.get("road_datum") or {}).get("profiles") or []) if p.get("assembler_sigma_y_pts")]:
        raise SystemExit("[predict] road_datum.profiles windows: the draft's y windows are not reproduced here")
    ws = Path(tempfile.mkdtemp(prefix="mf0102_"))
    try:
        _sync_in(ws)
        L.intake(ws)
        local = json.loads((ws / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        if (ws / "data" / "connectors.local.json").exists():
            con = json.loads((ws / "data" / "connectors.local.json").read_text(encoding="utf-8"))
            if con.get("connectors") or con.get("narrow_main"):
                raise SystemExit("[predict] connectors: the draft's narrowing is not reproduced here")
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    raw = json.dumps(local)
    route = cfg.get("route", {})
    cl = sm.smooth_centerline([tuple(p) for p in local["points_xyz_m"]], sigma_pts=float(route.get("smooth_sigma_pts", 2.0)),
                              passes=int(route.get("smooth_passes", 2)), sigma_y_pts=float(route.get("smooth_sigma_y_pts", 1.5)))
    local["points_xyz_m"] = [[round(c, 4) for c in p] for p in cl]
    return raw, json.dumps(local)


def main():
    raw, swept = lines()
    d = MF / "data"
    if "--check" in sys.argv:
        ok = ((d / "centerline.raw.local.json").read_text(encoding="utf-8") == raw
              and (d / "centerline.local.json").read_text(encoding="utf-8") == swept)
        print(f"[predict] committed data/centerline.raw.local.json + centerline.local.json {'ARE' if ok else 'are NOT'} the prediction")
        return 0 if ok else 1
    (d / "centerline.raw.local.json").write_text(raw, encoding="utf-8", newline="\n")
    (d / "centerline.local.json").write_text(swept, encoding="utf-8", newline="\n")
    pts = json.loads(swept)["points_xyz_m"]
    lap = sum(((b[0] - a[0]) ** 2 + (b[2] - a[2]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:]))
    print(f"[predict] wrote data/centerline.raw.local.json + centerline.local.json: {len(pts)} points, swept lap {lap:.2f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
