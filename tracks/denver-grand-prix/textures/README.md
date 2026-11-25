# Denver Grand Prix — track textures

## `blades/` — street-name blades (generated, CC0-1.0)

38 PNGs, 512 x 128, one per street: the 13 the lap runs on and every driveable street that meets it, read from
`source/osm.json` (OSM as of 2026-11-23). Written by `tools/make_sign_faces.py` (`DENVER_STREETS`); rerun it to
reproduce them, `--check` to compare. `tests/tools/test_street_furniture.py` holds the list to the lap.

- Plate: `assets/models/sign_plate_rect_36x9.obj` (36 x 9 in, a typical post-mounted blade; scale the plate to
  72 x 18 in for an overhead mast-arm name sign, the texture is the same 4:1). UV 0..1 = the blade, left to right,
  bottom to top. The legend per street is in `assets/models/sign_faces.json` `blades.streets`.
- **The style is unverified.** Green, white capitals, a small direction prefix and a small raised street type is
  what Denver's blades are remembered to look like. Nobody has checked it against a street-level frame, and
  Denver's blades may also carry a block number or a city mark that these do not. Check before one is placed.
- The letters are the repo's own stroke alphabet (`tools/street_furniture_draw.py`), an approximation of the
  FHWA Standard Alphabets. No font file is read.
- Not bound by `track.config.json` and not in any `ship.json`: nothing is placed yet.
