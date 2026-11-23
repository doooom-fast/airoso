"""Run tools/aerial_paint_north.py, unchanged, on the Phase 3 station frame.

The tool reads <track>/data/expansion.north.json and <track>/data/centerline.local.json and writes
<track>/source/expansion/aerial__paint_north.json. A scratch track is laid out here with the Phase 3 frame
(stations.west.json, p3x_profiles.py) in place of the north intermediate, so the tool measures the three new roads
with its own code and thresholds. Its NAIP windows (The National Map's NAIP ImageServer, EPSG:3857, 0.3 m) go to a
new cache folder; each request is followed by a PAUSE_S pause and sent with a generic User-Agent.

    python -I p3x_paint.py <airoso> <stations.west.json> <scratch-track-dir> <window-cache-dir>
"""
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p3x_ua  # noqa: E402,F401

PAUSE_S = 1.0


def main():
    airoso, frame_p, track, cache = (Path(a) for a in sys.argv[1:5])
    sys.path.insert(0, str(airoso / "tools"))
    sys.path.insert(0, str(airoso))
    import aerial_paint_north as apn
    apn.UA = {"User-Agent": p3x_ua.UA}
    _get = apn._get

    def polite(url, tries=8):
        try:
            return _get(url, tries)
        finally:
            time.sleep(PAUSE_S)
    apn._get = polite
    (track / "data").mkdir(parents=True, exist_ok=True)
    (track / "source" / "expansion").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frame_p, track / "data" / "expansion.north.json")
    shutil.copyfile(airoso / "tracks/san-diego-lake-murray/data/centerline.local.json",
                    track / "data" / "centerline.local.json")
    rc = apn.main(["--track", str(track), "--cache", str(cache)])
    print("aerial_paint_north exit", rc, flush=True)


if __name__ == "__main__":
    main()
