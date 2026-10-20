"""Ledger 0054 P1: verify_mouths' HOST LANE check, run over the SAME host span on two built road OBJs — the v0.18.0
road kn5 (no Jackson-north mouth) and the rehearsal's — so a HOST LANE count the host carried before any weld is told
apart from one the weld adds.

    python host_lane_baseline.py <v0.18.0 project (data/track.obj)> <rehearsal project> <mouth piece prefix>

The span, sides and island exclusions are the rehearsal's verify_mouths record for that mouth (data/verify_mouths.json);
the sampling is tools/verify_mouths.py's own (check_mouth's HOST LANE loop, reproduced on each OBJ with its own HD).
Each sample is classified by WHO is above: the host's own sheet (the lowest ROAD sheet at the point is above HD — the
level-across HD model on a corner's fanned / levelled deck) or another sheet over the host (the mouth's road).
"""
import json
import sys
from pathlib import Path

AIROSO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(AIROSO / "tools"))
import verify_mouths as vm  # noqa: E402


def lane(proj: Path, rec: dict, mo: dict, local: dict):
    obj = proj / "data" / "track.obj"
    tris = vm.load_obj(obj, [(mo["cut_xyz"][0], mo["cut_xyz"][2])])
    field = vm.Field(tris)
    hp = vm.Path2(local["points_xyz_m"], local["widths_m"])
    cx, _cy, cz = mo["cut_xyz"]
    _d, c, _lat = hp.project(cx, cz)
    side = rec["side"]
    hw = rec["span_half_m"]

    def HD(s):
        x, z = hp.point(s, 0.0)
        r = field.heights(x, z)["ROAD"]
        return min(r) if r else None
    out = {"samples": 0, "own_sheet_above": 0, "other_sheet_above": 0, "grass_at_or_above": 0, "max_own": 0.0,
           "max_other": 0.0, "max_grass": None}
    s = c - hw - vm.LANE_PAD_M
    while s <= c + hw + vm.LANE_PAD_M + 1e-9:
        hd = HD(s)
        if hd is not None:
            hhalf = hp.frame(s)[3] / 2.0
            isl = vm._island_half(mo, hp, proj / "data", s) if (proj / "data" / "median_bands.json").exists() else 0.0
            o = isl + 0.3 if isl > 0 else 0.0
            while o <= hhalf - vm.LANE_EDGE_M + 1e-9:
                x, z = hp.point(s, side * o)
                h = field.heights(x, z)
                out["samples"] += 1
                roads = sorted(h["ROAD"])
                if roads and roads[0] - hd > vm.LANE_TOL_M:
                    out["own_sheet_above"] += 1
                    out["max_own"] = max(out["max_own"], round(roads[0] - hd, 3))
                top = max(h["ROAD"] + h["KERB"], default=None)
                if top is not None and top - hd > vm.LANE_TOL_M and not (roads and roads[0] - hd > vm.LANE_TOL_M):
                    out["other_sheet_above"] += 1
                    out["max_other"] = max(out["max_other"], round(top - hd, 3))
                if h["GRASS"]:
                    g = max(h["GRASS"]) - hd
                    out["max_grass"] = round(g, 3) if out["max_grass"] is None else max(out["max_grass"], round(g, 3))
                    if g >= -vm.GRASS_AT_M:
                        out["grass_at_or_above"] += 1
                o += vm.STEP_LANE_M
        s += vm.STEP_LANE_M
    return out


def main():
    ref, reh, prefix = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    vmj = json.loads((reh / "data" / "verify_mouths.json").read_text(encoding="utf-8"))
    rec = next(m for m in vmj["mouths"] if str(m["piece"]).startswith(prefix))
    mouths = json.loads((reh / "data" / "mouths.json").read_text(encoding="utf-8"))["mouths"]
    mo = next(m for m in mouths if str(m.get("piece")).startswith(prefix))
    res = {}
    for name, proj in (("v0.18.0", ref), ("rehearsal", reh)):
        local = json.loads((proj / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        res[name] = lane(proj, rec, mo, local)
        print(name, res[name])
    print(json.dumps({"mouth": prefix, "verify_mouths_record": {k: rec[k] for k in ("span_half_m", "host_half_m",
                                                                                     "angle_deg")}, **res}))


if __name__ == "__main__":
    main()
