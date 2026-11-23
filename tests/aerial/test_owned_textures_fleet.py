"""Ledger 0101 (Kevin 2026-11-22, asked "The owned asphalt and concrete on the other tracks?": "On every track now").

The owned asphalt (asphalt_dense_*, tools/make_owned_surfaces.py, CC0) binds 1ROAD on every installed track whose coder is
this ledger's, by texture_overrides, as Milford 0.1.13 and High Plains 0.1.8 do (ledger 0095); the road-wear tracks among
them take the pilot's 0.5 m detail high-pass too. The owned plain concrete (concrete_plain_*) binds every stage of those
tracks' installed builds (data/split_manifest.json) that wore pbr.TEXTURES' building_* (Hamburg, mined). No other track
binds either pair, and each changed track's ship.json syncs every owned file its config binds.

Lake Murray, Sand Creek, High Plains and Milford are their own coders' (2026-11-22): the pilot's two keep ledger 0095's
asphalt, and none of the four binds the owned concrete here; an integration adds their branches' tracks to these sets.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import ship_track_spec as spec_mod  # noqa: E402
from scripts.ac import pbr  # noqa: E402
from scripts.aerial import road_wear as rw  # noqa: E402

ASPHALT = ["assets/textures/asphalt_dense_diffuse.jpg", "assets/textures/asphalt_dense_normal.jpg"]
CONCRETE = ["assets/textures/concrete_plain_diffuse.jpg", "assets/textures/concrete_plain_normal.jpg"]
MD5 = {ASPHALT[0]: "339c4244d8b07494be81df14eb963c8c", ASPHALT[1]: "7a71dfcefbbce0267cb0d17f0c931fb0",
       CONCRETE[0]: "d77c7ca9c8faa202951821133628a4e4", CONCRETE[1]: "2692b4231be5d2c24c6b4f0f3705bb84"}
BORROWED = ("asphalt_cracked_", "building_", "warehouse_diffuse", "warehouse_normal")   # LA Canyons, Hamburg
# track: (the 1ROAD detail cut, the rows that bind the owned concrete)
FLEET = {
    "aspen-lm": (0.5, {"1KERB_SIDEWALK"}),
    "del-mar-lm": (0.5, {"1KERB_SIDEWALK"}),
    "exotics-racing-lv-lm": (0.5, {"1KERB_SIDEWALK", "1RUNOFF", "PADAPRON"}),
    "grand-junction-lm": (0.5, {"1KERB_SIDEWALK"}),
    "lookout-lariat-lm": (None, set()),                       # no road_wear; its verge is gravel, no building_* stage
    "pikes-peak-lm": (0.5, {"1KERB_SIDEWALK"}),
    "pueblo-lm": (0.5, {"1KERB_SIDEWALK"}),
    "san-diego-freeway-lm": (None, {"1KERB_SIDEWALK", "1WALL_GUARD"}),   # no road_wear
}
PILOT = {"high-plains-lm", "milford-road-course-lm"}         # ledger 0095: the asphalt and the cut
OTHERS = {"san-diego-lake-murray", "sand-creek-lm"}           # their own coders'


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def test_the_fleet_binds_the_owned_pairs_and_ship_json_syncs_them():
    for f, want in MD5.items():
        assert _md5(ROOT / f) == want, f
    # every installed track (fleet/ac-installed.json, role current) is this ledger's, the pilot's or another coder's
    man = json.loads((ROOT / "fleet" / "ac-installed.json").read_text(encoding="utf-8"))
    installed = {e["track"] for e in man["folders"].values() if e["role"] == "current"}
    assert installed - OTHERS - PILOT <= set(FLEET), installed - OTHERS - PILOT - set(FLEET)

    seen = set()
    for cfgp in sorted((ROOT / "tracks").glob("*/track.config.json")):
        slug = cfgp.parent.name
        cfg = json.loads(cfgp.read_text(encoding="utf-8"))
        ov = cfg.get("texture_overrides") or {}
        names = {k.upper(): v for k, v in ov.items() if isinstance(v, dict)}
        asphalt_rows = {k for k, v in names.items() if any(v.get(s) in ASPHALT for s in ("diffuse", "normal"))}
        concrete_rows = {k for k, v in names.items() if any(v.get(s) in CONCRETE for s in ("diffuse", "normal"))}
        if slug not in FLEET:
            # every track this ledger did not change: unchanged (the pilot's two keep ledger 0095's 1ROAD row)
            assert asphalt_rows == ({"1ROAD"} if slug in PILOT else set()), (slug, asphalt_rows)
            assert not concrete_rows, (slug, concrete_rows)
            continue
        seen.add(slug)
        cut, rows = FLEET[slug]
        assert asphalt_rows == {"1ROAD"} and [names["1ROAD"]["diffuse"], names["1ROAD"]["normal"]] == ASPHALT, slug
        assert concrete_rows == rows, (slug, concrete_rows)
        for r in rows:
            assert [names[r]["diffuse"], names[r]["normal"]] == CONCRETE, (slug, r)
        # the cut: only on road wear's bake (it filters the detail under the macro); none where there is no road_wear
        spec = rw.spec_from_config(cfg)
        if cut is None:
            assert spec is None and "road_wear" not in cfg, slug
        else:
            assert rw.highpass_cuts(spec) == {"1ROAD": cut}, slug               # the edge strip's detail is not cut
        # the installed build's own objects: none wears a borrowed asphalt or concrete any more
        man_p = cfgp.parent / "data" / "split_manifest.json"
        assert man_p.is_file(), slug
        resolved = pbr.load_overrides(cfgp.parent)
        for kn5 in json.loads(man_p.read_text(encoding="utf-8"))["outputs"].values():
            for n in kn5.get("names", []):
                r = pbr.resolve(n, resolved)
                for s in ("diffuse", "normal"):
                    assert not (r[s] and r[s].name.startswith(BORROWED)), (slug, n, r[s])
        # ship.json syncs every owned file the config binds (the workshop gets them whatever the engine copy holds), read by
        # the chain's own reader
        spec_ship = spec_mod.load(cfgp.parent / "ship.json", slug)
        bound = {v[s] for v in names.values() for s in ("diffuse", "normal") if v.get(s) in ASPHALT + CONCRETE}
        assert bound == set(ASPHALT) | (set(CONCRETE) if rows else set()), (slug, bound)
        assert bound <= set(spec_ship["sync_in"]["assets"]), (slug, bound - set(spec_ship["sync_in"]["assets"]))
        # a carried force covers the build it is carried to (Pikes Peak's hairpin, the Lariat's two rows)
        fx = ((cfg.get("gates") or {}).get("drive1") or {}).get("force_exemptions") or {}
        for blk in (fx, fx.get("stage") or {}):
            if blk.get("versions"):
                assert cfg["version"] in blk["versions"], slug
    assert seen == set(FLEET), set(FLEET) - seen                    # a sparse checkout may lack other tracks, not these
