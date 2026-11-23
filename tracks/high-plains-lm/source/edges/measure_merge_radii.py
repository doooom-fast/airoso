"""The merge's corner radii off NAIP (ledger 0097 round 4, item 2): tools/mouth_radii.py (ledger 0086, Sand Creek's) on the
Full layout's merge, the north loop's end welded to the West lap.

    python -I measure_merge_radii.py <repo> <workshop-project>     (numpy + Pillow; writes mouth_radii.naip.json beside itself)

The workshop is an empty-workshop build of this branch (its data/mouths.json, connectors.local.json, centerline.local.json:
the BUILT corner frames). tools/mouth_radii.py reads the project's track.config.json "origin" as lon / lat; this port's
config says "centroid", so the run reads a copy of the workshop's data beside a config whose origin is the built line's
own (data/centerline.local.json), nothing else changed. The photo is tracks/high-plains/source/naip_2023_hp_z18.png
(NAIP 2023-09-28, the 0.3 m item as z18 web tiles, 0.46 m a pixel: mouth_radii's own reader, tools/naip_edge.Naip).
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(repo: Path, ws: Path):
    sys.path.insert(0, str(repo / "tools"))
    import mouth_radii    # noqa: E402
    src = repo / "tracks" / "high-plains" / "source"
    with tempfile.TemporaryDirectory() as td:
        T = Path(td)
        (T / "data").mkdir()
        for f in ("mouths.json", "connectors.local.json", "centerline.local.json"):
            shutil.copy(ws / "data" / f, T / "data" / f)
        cfg = json.loads((ws / "track.config.json").read_text(encoding="utf-8"))
        cfg["origin"] = json.loads((ws / "data" / "centerline.local.json").read_text(encoding="utf-8"))["origin"]
        (T / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return mouth_radii.main([str(T), "--naip", str(src / "naip_2023_hp_z18.png"),
                                 "--georef", str(src / "naip_2023_hp_z18.georef.json"), "--prefix", "full_north",
                                 "--out", str(HERE / "mouth_radii.naip.json"), "--sheet", str(HERE / "mouth_radii_merge.jpg")])


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
