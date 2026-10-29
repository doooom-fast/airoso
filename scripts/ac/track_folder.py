"""Generate the installable Assetto Corsa track folder (everything except the kn5 + AI).

All layouts share one ROAD kn5 and differ in AC config plus the kn5s a layout ADDS beside it
(fleet/LAWS.md L8 as amended in ledger 0047). Emits, under build/<slug>/:

  SINGLE layout (suffix-free, AC's single-config structure):
    models.ini, data/{surfaces.ini,map.ini[,cameras.ini]}, map.png, ui/{ui_track.json,outline.png,
    preview.png}, ai/ (the project's ai/ or a README placeholder), README/CREDITS/LICENSES.
  MULTI layout (AC's models_<id>.ini structure — never both in one folder):
    models_<id>.ini  = [MODEL_0] <slug>.kn5 (shared road, carries NO AC_* spawn nodes)
                       [MODEL_1] <slug>_race.kn5   only for layouts with race_furniture: true (the COMMON
                                 race furniture: both curb strips + the kerbs, ledger 0049) — or, for a race
                                 layout that names a LAP (layouts[].lap, ledger 0054), <slug>_race_<lap>.kn5:
                                 that lap's own common set (scripts/geometry/race_lap.py)
                       [MODEL_2] <slug>_closure_<id>.kn5  only for a race layout of a track that declares
                                 race.corridor (ledger 0049): THIS direction's closure walls. A race ini
                                 never names another layout's closure — the clockwise closure stands in the
                                 anticlockwise lane and vice versa, so loading both would block both lanes
                       [MODEL_n] <slug>__<id>.kn5  this layout's nodes-only spawn kn5 (last)
    ui/<id>/{ui_track.json (name "<cfg.name> — <layout name>", run = layouts[].run),
             outline.png, preview.png}
    <id>/{map.png, data/{surfaces.ini,map.ini[,cameras.ini]}, ai/}  ai from <project>/ai/<id>/
             first, else <project>/ai/, else a README placeholder
    plus the root data/+map.png (harmless), extension/ext_config.ini (global), README/CREDITS.
  Stale structure from an earlier pack of the other shape (root ai/, root ui/ui_track.json,
  ui/<old>/, <old>/, models.ini beside models_<id>.ini) is removed: build/<slug>/ is never wiped
  between packs and tools/pack_release.py zips whatever it finds.

A multi-layout layout that declares its own spawn set (data/dummies_<id>.json) but has no
build/<slug>__<id>.kn5, declares race_furniture without build/<slug>_race.kn5, or (with race.corridor
declared) has no build/<slug>_closure_<id>.kn5, is a HARD error — never a silently plain or unsealed
layout. ``--allow-missing-kn5`` downgrades that to a loud print so the folder can be laid out before the
Blender passes (dry runs); the inis still name the files. A ``<slug>_closure_*.kn5`` in the folder that
no declared layout loads (a retired layout, an earlier corridor) is removed: pack_release zips whatever
it finds.

The kn5s are produced by Blender (scripts/ac/build_kn5.py / export_kn5_addon.py / build_spawn_kn5.py);
tools/make_map.py then redraws every map.png in the kn5 frame; the AI fast_lane is recorded
in-game (Windows) or drafted by scripts/ac/write_ai_line.py.

Run:  python -m scripts.ac.track_folder projects/<slug> [--allow-missing-kn5]
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.config import load_config
from scripts.ac import credits, ext_config


# --- AC config files -----------------------------------------------------------

# The ROAD surface, per surface type. This is the ONE thing that must genuinely differ between a
# gravel rally stage and a paved one — same 1ROAD_* mesh, different physics under it. Everything
# else (kerb/runoff/grass) is unchanged, so a gravel track still behaves correctly off-line.
#   tarmac — sealed asphalt: near-full grip, no damping, silent (tyre roll carries it), no dirt pickup.
#   gravel — loose graded county road: much less grip, a little damping for the energy the surface
#            absorbs, DIRT_ADDITIVE so the car actually picks up dust, and the stock gravel roll sound.
ROAD_SURFACES: dict = {
    "tarmac": (dict(FRICTION=0.99, DAMPING=0, IS_VALID_TRACK=1, DIRT_ADDITIVE=0, IS_PITLANE=0), "", 0),
    "gravel": (dict(FRICTION=0.70, DAMPING=0.03, IS_VALID_TRACK=1, DIRT_ADDITIVE=1, IS_PITLANE=0,
                    VIBRATION_GAIN=0.35, VIBRATION_LENGTH=1.8),
               "gravel.wav", 1.0),
}


def surfaces_ini(*, wall: bool = False, road_surface: str = "tarmac", kerb_ff_effect: int = 0) -> str:
    """data/surfaces.ini — physical surfaces keyed to the 1ROAD/1KERB/1RUNOFF/1GRASS mesh prefixes.
    WAV= names a STOCK AC sound resolved from the player's own content/sfx (FMOD GUIDs.txt) — NOTHING
    is bundled or redistributed. ROAD is intentionally silent on tarmac (tyre-roll covers it); KERB
    rumbles, RUNOFF/GRASS scrub. SIN_HEIGHT stays 0: no invented bump on top of the mesh (the race kerbs
    are a flat 5 cm plate with a 10 cm ramp — tools/race_furniture.py KERB_H / KERB_RAMP_W — not a
    ridged sausage; the rumble is the VIBRATION + WAV). ``wall=True`` (network tracks) adds the WALL
    surface for the swept 1WALL_* freeway barriers. ``road_surface`` selects the ROAD physics from
    :data:`ROAD_SURFACES` — ``"gravel"`` is what makes a rally stage drive like dirt instead of asphalt.
    ``kerb_ff_effect`` (ledger 0053, opt-in per track via track.config.json ``kerb_ff_effect``) writes
    FF_EFFECT=<n> on the KERB block ONLY — 1 is the Kunos convention (measured: Vallelunga, Silverstone,
    Laguna Seca, Brands Hatch, Red Bull Ring, Barcelona, Imola, Mugello) and puts the kerb in the wheel.
    KEY=KERB also covers every street curb/sidewalk (1KERB_sidewalk), so they get it too. Default 0:
    the output is byte-identical to before for every track that does not opt in."""
    if road_surface not in ROAD_SURFACES:
        raise ValueError(f"unknown road_surface {road_surface!r} "
                         f"(expected one of {', '.join(sorted(ROAD_SURFACES))})")
    if int(kerb_ff_effect) not in (0, 1):
        raise ValueError(f"kerb_ff_effect must be 0 or 1, got {kerb_ff_effect!r}")
    road_params, road_wav, road_pitch = ROAD_SURFACES[road_surface]
    # KEY, params, stock WAV (referenced by name), WAV_PITCH
    blocks = [
        ("ROAD",   dict(road_params), road_wav, road_pitch),
        ("KERB",   dict(FRICTION=0.92, DAMPING=0, IS_VALID_TRACK=1, DIRT_ADDITIVE=0, IS_PITLANE=0,
                        VIBRATION_GAIN=1.0, VIBRATION_LENGTH=1.5),
                   "kerb.wav", 1.3),
        # Paved corner run-off: drivable tarmac but slightly low grip and OFF-track (cutting it doesn't
        # count) — forgiving without turning the apron into a free track-extension.
        ("RUNOFF", dict(FRICTION=0.90, DAMPING=0.02, IS_VALID_TRACK=0, DIRT_ADDITIVE=0, IS_PITLANE=0,
                        VIBRATION_GAIN=0.4, VIBRATION_LENGTH=2.0),
                   "gravel.wav", 1.2),
        ("GRASS",  dict(FRICTION=0.60, DAMPING=0.1, IS_VALID_TRACK=0, DIRT_ADDITIVE=1, IS_PITLANE=0),
                   "grass.wav", 1.0),
        # LAWN = irrigated suburban turf (1LAWN_* tiles): a touch more grip than dry grass, same
        # off-track scrub. Keeps the green neighbourhood ground physical so you don't fall through it.
        ("LAWN",   dict(FRICTION=0.65, DAMPING=0.09, IS_VALID_TRACK=0, DIRT_ADDITIVE=1, IS_PITLANE=0),
                   "grass.wav", 1.0),
    ]
    if wall:
        # WALL = the physical freeway barrier (1WALL_* meshes) on network tracks. A vertical collision
        # surface, not driven on, so it never counts as valid track — it just bounces the car back
        # onto the road. Circuit tracks keep their barriers as plain collidable meshes (no entry).
        blocks.append(
            ("WALL", dict(FRICTION=0.30, DAMPING=0, IS_VALID_TRACK=0, DIRT_ADDITIVE=0, IS_PITLANE=0),
             "", 0))
    out = []
    for i, (key, p, wav, pitch) in enumerate(blocks):
        ff = int(kerb_ff_effect) if key == "KERB" else 0
        lines = [f"[SURFACE_{i}]", f"KEY={key}", f"WAV={wav}", f"WAV_PITCH={pitch}", f"FF_EFFECT={ff}",
                 "SIN_HEIGHT=0", "SIN_LENGTH=0", "BLACK_FLAG_TIME=0"]
        lines += [f"{k}={v}" for k, v in p.items()]
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def ui_track_json(cfg, layout: str, length_m: float, n_pits: int, width_m: float | None = None) -> dict:
    """ui/<id>/ui_track.json. Text comes from track.config.json, per layout first: ``layouts[].
    ui_description`` / ``ui_tags`` / ``ui_width_m``, then the track's ``ui_description`` / ``ui_tags`` /
    ``ui_width_m``, then defaults. ``width_m`` is the caller's measured road width (track_folder passes
    the narrowest declared width of data/centerline.local.json — Lake Murray's 13.0 m Alvarado, where
    default_width_m said 12); without either, default_width_m. The default tags no longer call every
    loop "fictional": only a track whose archetype is ``street_circuit`` (an invented circuit) is."""
    loc = cfg.raw.get("location", {})
    city = loc.get("city", "Commerce City")
    country = loc.get("country", "United States")
    freeroam = not cfg.raw.get("loop", True)
    # per-layout label: use the layout's configured `name` (e.g. "Sand Creek Raceway") so each config
    # in the in-game dropdown reads as its actual track, not the raw id.
    lo_meta = next((lo for lo in (cfg.raw.get("layouts", []) or []) if isinstance(lo, dict) and lo.get("id") == layout), {})
    lo_label = lo_meta.get("name") or layout
    # the default description says where the road came from (source.type) and what the place is (archetype), so a
    # closed circuit traced off aerial imagery is not called "a street circuit from OpenStreetMap" (Exotics' first
    # install, 2026-10-29, ledger 0060); a track that wants other words declares ui_description
    src_type = str((cfg.raw.get("source") or {}).get("type") or "osm")
    src_text = {"aerial": "traced from USDA NAIP aerial imagery", "kml": "built from a mapped route over the real roads",
                "from_track": "built from the real track's mapped outline"}.get(src_type, "built from OpenStreetMap")
    what = {"race_circuit": "Real-world circuit", "street_circuit": "Racing loop on real streets",
            "rally_stage": "Real-world stage"}.get(str(cfg.raw.get("archetype") or ""), "Real-world road course")
    desc = lo_meta.get("ui_description") or cfg.raw.get("ui_description") or (
        f"Open-world freeroam cruise of {city} — a real street network ({round(length_m/1000)} km) "
        f"merged from map exports, with real USGS terrain. Built with airoso. Just drive."
        if freeroam else
        f"{what} {src_text}, on USGS 3DEP elevation, with airoso ({city}, {country}).")
    # `loop: false` alone does NOT mean freeroam — a point-to-point rally stage is also not a loop,
    # and labelling it an open-world cruise is simply wrong. Let a track state its own tags.
    fictional = cfg.raw.get("archetype") == "street_circuit"
    tags = list(lo_meta.get("ui_tags") or cfg.raw.get("ui_tags") or (
        ["freeroam", "cruise", "street", "open-world", "real-roads"] if freeroam else
        ["street", "loop", *(["fictional"] if fictional else []), "real-roads"]))
    # Content Manager refuses Race and Track Day sessions on any track not tagged "circuit" — on a
    # closed loop the AI modes are simply unreachable without it (hit on Lake Murray 2026-08-06,
    # the day the first AI line shipped). A loop gets the tag even when ui_tags is explicit.
    if not freeroam and "circuit" not in tags:
        tags = ["circuit", *tags]
    width = lo_meta.get("ui_width_m") or cfg.raw.get("ui_width_m") or width_m or cfg.default_width_m
    # Content Manager display name: prefix the series so all K10 Colorado circuits group together in the
    # in-game list ("K10 Colorado - Sand Creek Raceway", ...). Override per track via `ui_series`.
    series = cfg.raw.get("ui_series", "K10 Colorado")
    base_name = f"{series} - {cfg.name}" if series else cfg.name
    # Only append a layout label when the track actually HAS multiple layouts — a single-layout track
    # (e.g. IMI's one "full_course") shouldn't read "… — full_course".
    n_layouts = len(cfg.raw.get("layouts", []) or [])
    suffix = "" if (layout in ("full", "freeroam") or n_layouts <= 1) else f" — {lo_label}"
    # `run` is hover text only (ORP ships "clockwise" on both its directions, PCH "Northbound" /
    # "Southbound"); a layout may carry its own wording (ledger 0047: Kevin's compass words),
    # every other track keeps the historical "clockwise".
    run = str(lo_meta.get("run") or "clockwise")
    return {
        "name": base_name + suffix,
        # build stamp UP FRONT: a full release cycle was burned diagnosing "fixed nothing" against a
        # stale install — the version must be visible at a glance in CM, not just the version field.
        "description": f"[build {cfg.version}] " + desc,
        "tags": tags,
        "geotags": [f"{cfg.lat}", f"{cfg.lon}"],
        "country": country, "city": city,
        "length": str(round(length_m)), "width": str(round(float(width))),
        "pitboxes": str(n_pits), "run": run,
        "author": cfg.author, "version": str(cfg.version), "year": cfg.year,
    }


def models_ini(kn5_name: str, extras: str | list[str] | None = None) -> str:
    """models[_<layout>].ini: MODEL_0 = the shared road kn5; ``extras`` = the kn5s THIS layout adds
    beside it, in load order (race-furniture kn5 first, the nodes-only spawn kn5 last). A single
    string is accepted for the old one-spawn-kn5 call shape."""
    if isinstance(extras, str):
        extras = [extras]
    s = f"[MODEL_0]\nFILE={kn5_name}\nPOSITION=0,0,0\nROTATION=0,0,0\n"
    for i, extra in enumerate(extras or [], start=1):
        s += f"\n[MODEL_{i}]\nFILE={extra}\nPOSITION=0,0,0\nROTATION=0,0,0\n"
    return s


def closure_kn5_name(cfg, layout: dict) -> str | None:
    """``<slug>_closure_<id>.kn5`` for a race layout of a track whose config declares ``race.corridor``
    (ledger 0049: each direction loads only its own closure walls), else None. The declaration must be
    whole: under a corridor every race_furniture layout names its ``closure_token`` (the token in its
    closure meshes' names, 1WALL_race_close_<token>_*), the tokens are distinct, and only a race layout
    carries one — anything else is a ValueError, never a silently unsealed or doubly closed layout."""
    raw = cfg.raw if hasattr(cfg, "raw") else cfg
    corridor = bool((raw.get("race") or {}).get("corridor")) or any(
        isinstance(v, dict) and v.get("corridor") for v in ((raw.get("race") or {}).get("laps") or {}).values())
    los = [lo for lo in (raw.get("layouts") or []) if isinstance(lo, dict)]
    tokens = [lo.get("closure_token") for lo in los if lo.get("closure_token")]
    if len(set(tokens)) != len(tokens):
        raise ValueError(f"layouts[].closure_token must be distinct, got {tokens}")
    lid, token = layout["id"], layout.get("closure_token")
    if token and not layout.get("race_furniture"):
        raise ValueError(f"layout {lid!r}: closure_token {token!r} on a layout without race_furniture")
    if not layout.get("race_furniture"):
        return None
    if corridor and not token:
        raise ValueError(f"layout {lid!r}: race.corridor is declared but the layout has no closure_token — "
                         f"its closure walls could not be told from the other direction's")
    slug = cfg.slug if hasattr(cfg, "slug") else raw["slug"]
    return f"{slug}_closure_{lid}.kn5" if (corridor or token) else None


def race_kn5_name(cfg, layout: dict) -> str:
    """the COMMON race-furniture kn5 a race layout loads: ``<slug>_race.kn5`` (the mainline's), or for a layout that
    names a lap (layouts[].lap, ledger 0054) ``<slug>_race_<lap>.kn5`` — that lap's own curb strips + kerbs"""
    slug = cfg.slug if hasattr(cfg, "slug") else cfg["slug"]
    lap = layout.get("lap") if isinstance(layout, dict) else None
    return f"{slug}_race.kn5" if not lap else f"{slug}_race_{lap}.kn5"


def street_kn5_name(cfg) -> str | None:
    """``<slug>_street.kn5`` when the track declares a street-only island (race.chicanes, ledger 0055 — the median over
    a Speedway chicane's span stands in the street layouts only), else None. Loaded by every NON-race layout."""
    from scripts.geometry import race_chicane as _rc
    raw = cfg.raw if hasattr(cfg, "raw") else cfg
    if not _rc.has_street_kn5(raw):
        return None
    slug = cfg.slug if hasattr(cfg, "slug") else raw["slug"]
    return f"{slug}{_rc.STREET_KN5_SUFFIX}.kn5"


def layout_kn5s(cfg, layout: dict | str, project_dir: Path, *, single: bool,
                strict: bool = True) -> list[tuple[str, Path | None]]:
    """The kn5s a layout adds beside the shared road kn5, as (file name, source path or None).

    * race furniture (``race_furniture: true``): ``build/<slug>_race.kn5`` — required.
    * its closure (a track with ``race.corridor``, ledger 0049): ``build/<slug>_closure_<id>.kn5`` —
      required; THIS layout's only (closure_kn5_name).
    * spawn set: ``build/<slug>__<id>.kn5`` — required whenever the layout declares its own
      ``data/dummies_<id>.json`` (a multi-layout road kn5 carries no spawns, so a layout without
      its spawn kn5 has no grid); a layout with neither keeps the baked-in dummies (legacy shape).
    ``strict=False`` turns a missing file into a loud print (dry runs); the name is still listed."""
    lo = layout if isinstance(layout, dict) else {"id": layout}
    lid = lo["id"]
    build = project_dir / "build"
    out: list[tuple[str, Path | None]] = []
    missing: list[str] = []
    if lo.get("race_furniture"):
        if lo.get("kind", "race") != "race":
            raise ValueError(f"layout {lid!r}: race_furniture needs kind 'race' (got {lo.get('kind')!r})")
        names = [race_kn5_name(cfg, lo)]
        closure = closure_kn5_name(cfg, lo)
        if closure:
            names.append(closure)
        for name in names:
            src = build / name
            if not src.exists():
                missing.append(name)
            out.append((name, src if src.exists() else None))
    elif lo.get("closure_token"):
        closure_kn5_name(cfg, lo)                          # raises: a token on a non-race layout
    if not lo.get("race_furniture") and isinstance(layout, dict):
        sk = street_kn5_name(cfg)                          # ledger 0055: the street-only island (Free Roam only)
        if sk:
            src = build / sk
            if not src.exists():
                missing.append(sk)
            out.append((sk, src if src.exists() else None))
    if not single:
        name = f"{cfg.slug}__{lid}.kn5"
        src = build / name
        declared = (project_dir / "data" / f"dummies_{lid}.json").exists()
        if src.exists():
            out.append((name, src))
        elif declared:
            missing.append(name)
            out.append((name, None))
        else:
            print(f"[track_folder] layout {lid}: no data/dummies_{lid}.json and no {name} — "
                  f"spawns must be baked into {cfg.slug}.kn5 (legacy shape)")
    if missing:
        msg = (f"layout {lid!r} needs {', '.join(missing)} in {build} — build it (export_kn5_addon "
               f"--keep-prefix / build_spawn_kn5) before packing; a layout never silently drops "
               f"its furniture or its grid")
        if strict:
            raise FileNotFoundError(msg)
        print(f"[track_folder] WARNING (--allow-missing-kn5): {msg}")
    return out


def _is_layout_dir(p: Path) -> bool:
    """A root-level dir that looks like AC's <track>/<layout>/ (map.png, data/ or ai/ inside)."""
    return p.is_dir() and ((p / "map.png").exists() or (p / "data").is_dir() or (p / "ai").is_dir())


def clean_stale_structure(out: Path, layouts: list[str], *, single: bool) -> list[str]:
    """Remove structure files/dirs from a pack of the OTHER shape or of a layout no longer declared.
    AC mis-detects a folder holding both shapes (ac-track-modding SKILL.md), and build/<slug>/ is
    never wiped between packs. Root data/ and map.png stay (harmless in both shapes)."""
    import shutil
    removed: list[str] = []
    keep_root = {"data", "ui", "ai", "extension"}

    def _rm(p: Path):
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        removed.append(str(p.relative_to(out)))

    if single:
        for st in out.glob("models_*.ini"):
            _rm(st)
        if (out / "ui").is_dir():
            for d in (out / "ui").iterdir():
                if d.is_dir():
                    _rm(d)
        for d in out.iterdir():
            if d.is_dir() and d.name not in keep_root and _is_layout_dir(d):
                _rm(d)
    else:
        if (out / "models.ini").exists():
            _rm(out / "models.ini")
        for st in out.glob("models_*.ini"):
            if st.stem[len("models_"):] not in layouts:
                _rm(st)
        if (out / "ui").is_dir():
            for d in (out / "ui").iterdir():
                if d.is_dir() and d.name not in layouts:
                    _rm(d)
            for f in ("ui_track.json", "outline.png", "preview.png", "preview.svg"):
                if (out / "ui" / f).exists():
                    _rm(out / "ui" / f)
        if (out / "ai").is_dir():
            _rm(out / "ai")
        for d in out.iterdir():
            if d.is_dir() and d.name not in keep_root and d.name not in layouts and _is_layout_dir(d):
                _rm(d)
    for r in removed:
        print(f"[track_folder] removed stale {r}")
    return removed


# --- minimap / images ----------------------------------------------------------

def _xz(local: dict, cfg=None) -> list[tuple[float, float]]:
    """(X, Z) in the SHIPPED frame — the one the car reports positions in.

    centerline.local.json is stored UNMIRRORED and UNROTATED; every other consumer converts before
    using it (kn5_write: `mpts = [(sx*q[0], q[2]) ...]`, audit_mesh check H the same). The minimap
    did not, so map.png and map.ini were built in a different handedness from the kn5: with
    mirror_x and true_north 180 the net effect is a reflection, and the car's dot traces the mirror
    image of the drawn line instead of following it (Kevin: "car doesn't follow it. Chirality?").
    Apply the same mirror and yaw kn5_write applies, so pixel space and car space agree."""
    pts = local["points_xyz_m"]
    if cfg is None:
        return [(p[0], p[2]) for p in pts]
    sx = -1.0 if getattr(cfg, "mirror_x", None) or (isinstance(cfg, dict) and cfg.get("mirror_x")) else 1.0
    ydeg = (getattr(cfg, "true_north_rotation_deg", None)
            if not isinstance(cfg, dict) else cfg.get("true_north_rotation_deg")) or 0.0
    yr = math.radians(float(ydeg))
    c, s_ = math.cos(yr), math.sin(yr)
    out = []
    for p in pts:                       # mirror first (projection), then true-north (kn5_write.rot)
        x, z = sx * p[0], p[2]
        out.append((x * c - z * s_, x * s_ + z * c))
    return out


def _map_params(xz, size: int = 900, margin: int = 28):
    """Square, centered canvas so nothing clips and map.png matches map.ini exactly."""
    xs = [p[0] for p in xz]; zs = [p[1] for p in xz]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    rx, rz = maxx - minx, maxz - minz
    scale = (size - 2 * margin) / max(rx, rz)
    ox, oz = (size - rx * scale) / 2, (size - rz * scale) / 2  # centering offsets (px)
    params = {"WIDTH": size, "HEIGHT": size,
              # AC semantics: pixel = (world + OFFSET) / SCALE_FACTOR -> SCALE is METERS PER
              # PIXEL (Kunos tracks ship ~5-9). We shipped px/m; every point mapped thousands
              # of px off-canvas and the minimap showed nothing ("map doesn't work").
              "SCALE_FACTOR": round(1.0 / scale, 6),
              "X_OFFSET": round(ox / scale - minx, 3), "Z_OFFSET": round(oz / scale - minz, 3),
              "MARGIN": margin, "DRAWING_SIZE": 10}
    geom = {"minx": minx, "minz": minz, "maxz": maxz, "scale": scale, "ox": ox, "oz": oz, "S": size}
    return params, geom


def _osm_preview(project_dir: Path, w: int = 1200, h: int = 675):
    """CM preview: the cached OSM street network (grey, class-weighted) with the ROUTE drawn
    bold on top — 'the osm with the route drawn on it'. Returns a PIL Image or None."""
    waysp = project_dir / "data" / "osm.ways.json"
    clp = project_dir / "data" / "centerline.geojson"
    if not (waysp.exists() and clp.exists()):
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    ways = json.loads(waysp.read_text())
    gj = json.loads(clp.read_text())
    feats = gj.get("features", [gj])
    line = next((f for f in feats if f.get("geometry", {}).get("type") == "LineString"), None)
    if line is None:
        return None
    route = [(c[0], c[1]) for c in line["geometry"]["coordinates"]]
    lons = [c[0] for c in route]; lats = [c[1] for c in route]
    lat0 = sum(lats) / len(lats)
    kx = math.cos(math.radians(lat0))
    x0, x1 = min(lons), max(lons)
    z0, z1 = min(lats), max(lats)
    padx = (x1 - x0) * 0.12 + 1e-9; padz = (z1 - z0) * 0.12 + 1e-9
    x0 -= padx; x1 += padx; z0 -= padz; z1 += padz
    sc = min(w / ((x1 - x0) * kx), h / (z1 - z0))
    ox = (w - (x1 - x0) * kx * sc) / 2; oz = (h - (z1 - z0) * sc) / 2

    def px(lon, lat):
        return (ox + (lon - x0) * kx * sc, h - (oz + (lat - z0) * sc))

    AA = 2
    img = Image.new("RGB", (w * AA, h * AA), (242, 239, 233))     # OSM-carto paper
    dr = ImageDraw.Draw(img)
    W = {"motorway": 7, "trunk": 7, "primary": 6, "secondary": 5, "tertiary": 4}
    for pass_i, (col, extra) in enumerate((((201, 196, 187), 2), ((255, 255, 255), 0))):
        for wv in ways:
            g = wv.get("geom") or []
            if len(g) < 2:
                continue
            wid = (W.get((wv.get("highway") or "").replace("_link", ""), 3) + extra) * AA
            pts = [tuple(c * AA for c in px(lo, la)) for lo, la in g]
            dr.line(pts, fill=col, width=wid, joint="curve")
    rpts = [tuple(c * AA for c in px(lo, la)) for lo, la in route]
    dr.line(rpts, fill=(224, 52, 44), width=8 * AA, joint="curve")
    dr.ellipse([rpts[0][0] - 10 * AA, rpts[0][1] - 10 * AA, rpts[0][0] + 10 * AA, rpts[0][1] + 10 * AA],
               fill=(224, 52, 44), outline=(255, 255, 255), width=3 * AA)
    return img.resize((w, h), Image.LANCZOS)


def map_ini(params: dict) -> str:
    body = "\n".join(f"{k}={v}" for k, v in params.items())
    return f"[PARAMETERS]\n{body}\n"


def _network_edges_xz(project_dir: Path):
    """For a freeroam NETWORK: return (edges_xz, length_m). Each edge is a [(x,z)...] polyline in the
    SAME mirrored local frame the mesh used, recomputed from network.geojson + network.local.json."""
    netp = project_dir / "data" / "network.geojson"
    locp = project_dir / "data" / "network.local.json"
    if not (netp.exists() and locp.exists()):
        return None
    loc = json.loads(locp.read_text())
    o = loc["origin"]; lon0, lat0 = o["lon"], o["lat"]
    sx = -1.0 if loc.get("mirror_x", True) else 1.0
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    # SUN FIX: the model is yawed by true_north_rotation_deg at export (build_kn5). Yaw the minimap
    # coords by the SAME angle so map.png + map.ini offsets stay aligned with the in-game world.
    tn = math.radians(float(loc.get("true_north_rotation_deg", 0.0)))
    ct, st = math.cos(tn), math.sin(tn)
    fc = json.loads(netp.read_text())
    edges, total = [], 0.0
    for f in fc["features"]:
        e = []
        for lon, lat in f["geometry"]["coordinates"]:
            x, z = sx * (lon - lon0) * m_lon, (lat - lat0) * m_lat
            e.append((x * ct - z * st, x * st + z * ct))
        edges.append(e)
        total += float(f["properties"].get("length_m") or 0.0)
    return edges, round(total, 1)


def _track_svg(xz, geom, *, stroke: str, width: float, bg: str | None, flip_y: bool = False,
               multi=None) -> str:
    minx, minz, maxz, scale, ox, oz, S = (geom[k] for k in ("minx", "minz", "maxz", "scale", "ox", "oz", "S"))

    def px(x, z):
        py = ((maxz - z) if flip_y else (z - minz)) * scale + oz  # flip_y=True → north up (UI); else AC HUD
        return round((x - minx) * scale + ox, 1), round(py, 1)

    rect = f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ""
    if multi is not None:  # freeroam network: one polyline per edge (no jumps between disjoint streets)
        paths = "".join(
            f'<polyline points="{" ".join(f"{a},{b}" for a, b in (px(x, z) for x, z in e))}" '
            f'fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" '
            f'stroke-linecap="round"/>' for e in multi)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">'
                f'{rect}{paths}</svg>')
    pts = " ".join(f"{a},{b}" for a, b in (px(x, z) for x, z in xz))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">'
            f'{rect}<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def _draw_track_png(xz, geom, png: Path, *, stroke=(255, 255, 255, 255), width: float = 10,
                    flip_y: bool = False, multi=None) -> None:
    """Draw the track line straight to a TRANSPARENT PNG with PIL. qlmanage flattens SVG
    transparency to opaque white — the shipped map.png was a white square (white line on
    white: the in-game minimap and the CM outline overlay were both invisible/blocky)."""
    from PIL import Image, ImageDraw
    minx, minz, maxz, scale, ox, oz, S = (geom[k] for k in ("minx", "minz", "maxz", "scale", "ox", "oz", "S"))
    AA = 2

    def px(x, z):
        py = ((maxz - z) if flip_y else (z - minz)) * scale + oz
        return ((x - minx) * scale + ox) * AA, py * AA

    img = Image.new("RGBA", (S * AA, S * AA), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for line in (multi if multi is not None else [xz]):
        pts = [px(x, z) for x, z in line]
        if len(pts) >= 2:
            dr.line(pts, fill=stroke, width=max(1, int(width * AA)), joint="curve")
    img.resize((S, S), Image.LANCZOS).save(png)


def _rasterize(svg: str, png: Path, size: int) -> bool:
    """SVG -> ``png``. macOS (the original build host): qlmanage. Any other OS — or qlmanage failing —
    Pillow (scripts/ac/svg_raster.py, the polyline drawer tools/pack_release.py used to patch this over
    at pack time). Content Manager reads only preview.png: the old fallback wrote a preview.svg it never
    reads, and the Lake Murray V3 install (built on Windows) shipped no ui/<id>/preview.png at all
    (ledger 0047 fix round, finding D). Nothing is written when neither can draw the SVG."""
    import shutil
    if sys.platform == "darwin" and shutil.which("qlmanage"):
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
                f.write(svg); tmp = f.name
            subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", str(png.parent), tmp],
                           capture_output=True, timeout=30)
            out = png.parent / (Path(tmp).name + ".png")
            if out.exists():
                out.replace(png)
                return True
        except Exception:
            pass
    try:
        from scripts.ac.svg_raster import rasterize_svg
        if rasterize_svg(svg, png, size):
            return True
    except Exception as e:                                     # Pillow missing, or a broken SVG
        print(f"[track_folder] Pillow preview rasterization failed: {e}")
    print(f"[track_folder] no preview rasterizer could draw this SVG — {png.name} not written")
    return False


def readme_text(cfg, layout_cfgs: list[dict], extras_by_layout: dict, kn5_name: str, length_m: float, *,
                single: bool, ai_kind: dict[str, str], has_ext: bool) -> str:
    """The root README.txt: what this folder is, its layouts, what it needs, where it installs.

    Written from track.config.json and what this pack actually put in the folder — never a to-do list
    (the old text listed the kn5 and the AI under "STILL NEEDED" in a folder that shipped both, named
    the builder prodrive-ac-builder and the install folder <slug> where Lake Murray installs as
    san_diego_lake_murray_v3). The install folder is ``install_folder`` in the config, else the slug."""
    folder = str(cfg.raw.get("install_folder") or cfg.slug)
    loc = cfg.raw.get("location", {}) or {}
    where = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
    lines = [f"{cfg.name} — Assetto Corsa track, build {cfg.version}" + (f" ({where})" if where else ""),
             "",
             (str(cfg.raw.get("readme_about")) if cfg.raw.get("readme_about") else
              f"Real roads from OpenStreetMap at real USGS 3DEP elevation, {length_m / 1000:.1f} km a lap."),
             "Built with airoso (the K10 track engine): the folder is generated from track.config.json; "
             "the road is one shared kn5.",
             ""]
    if single:
        lines += ["ONE LAYOUT — models.ini, ui/ (name, preview, outline), ai/, data/, map.png."]
    else:
        lines += [f"{len(layout_cfgs)} LAYOUTS — pick one in Content Manager (one models_<id>.ini each):"]
        import textwrap
        for lo in layout_cfgs:
            lid = lo["id"]
            name = str(lo.get("name") or lid)
            kn5s = [kn5_name] + [n for n, _ in extras_by_layout.get(lid, [])]
            lines.append(f"  {name} ({lid})")
            lines += textwrap.wrap(str(lo.get("run") or ""), 96, initial_indent="    ", subsequent_indent="    ")
            lines += textwrap.wrap("loads " + " + ".join(kn5s), 96, initial_indent="    ", subsequent_indent="      ")
        lines += ["  Each layout has its own <id>/ (map.png, data/, ai/) and ui/<id>/ (name, preview, outline)."]
        if any(n.startswith(f"{cfg.slug}_closure_") for ex in extras_by_layout.values() for n, _ in ex):
            lines += textwrap.wrap(f"  Each race layout loads only its OWN {cfg.slug}_closure_<id>.kn5 (the walls closing "
                                   f"off the other direction's lanes); listing another layout's closure in a "
                                   f"models_<id>.ini would wall off its lane.", 98, subsequent_indent="  ")
    lines += [""]
    if has_ext:
        lines += ["REQUIRES Custom Shaders Patch (CSP): extension/ext_config.ini carries the lights, GrassFX,",
                  "RainFX and sky glow; without CSP the track still loads, with none of them.", ""]
    kinds = set(ai_kind.values())
    if kinds == {"draft"}:
        lines += ["AI: every layout's ai/fast_lane.ai is a GENERATED DRAFT from the built centreline, not an",
                  "in-game recording (whether the AI laps on it is decided in game). Record over it per layout",
                  "with CSP's AI recorder (fast_lane.ai.candidate) to replace it.", ""]
    elif kinds == {"none"}:
        lines += ["AI: none shipped — record ai/fast_lane.ai in game (CSP), or draft one with",
                  "python -m scripts.ac.write_ai_line <project-dir>.", ""]
    else:
        for lid, kind in ai_kind.items():
            lines.append({"draft": f"AI ({lid}): a GENERATED DRAFT from the built centreline, not an in-game recording.",
                          "project": f"AI ({lid}): shipped from the project's ai/ (its provenance is not recorded here).",
                          "none": f"AI ({lid}): none shipped — record it in game (CSP)."}[kind])
        lines += [""]
    lines += [f"INSTALL: copy this folder to <Assetto Corsa>/content/tracks/{folder}/ — the folder name",
              f"must stay {folder}. Then pick the track (and layout) in Content Manager.", ""]
    return "\n".join(lines)


# --- orchestration -------------------------------------------------------------

def generate(project_dir: str | Path, kn5_name: str | None = None, *, strict_kn5: bool = True) -> dict:
    project_dir = Path(project_dir)
    cfg = load_config(project_dir)
    dummies = json.loads((project_dir / "data" / "dummies.json").read_text(encoding="utf-8")) \
        if (project_dir / "data" / "dummies.json").exists() else {}
    n_pits = sum(1 for k in dummies if k.startswith("AC_PIT_"))
    kn5_name = kn5_name or f"{cfg.slug}.kn5"

    # Freeroam NETWORK (this project) vs single-loop (legacy): the minimap draws every edge and the
    # "length" is the total drivable road, not a lap.
    net = _network_edges_xz(project_dir)
    road_width_m = None
    if net is not None:
        edges_xz, length_m = net
        xz = [p for e in edges_xz for p in e]      # all points (for bbox/centering)
        multi = edges_xz
    else:
        local = json.loads((project_dir / "data" / "centerline.local.json").read_text(encoding="utf-8"))
        xz = _xz(local, cfg)
        multi = None
        length_m = json.loads((project_dir / "data" / "centerline.geojson").read_text())["features"][0]["properties"]["length_m"]
        # CM's "width": the narrowest declared width of the lap (Lake Murray: Alvarado's 13.0 m)
        if local.get("widths_m"):
            road_width_m = min(float(v) for v in local["widths_m"])

    # Network tracks (top-level "network" config block, or built from network.geojson) carry the
    # swept 1WALL_* freeway barriers and need the WALL surface entry; circuits don't emit one.
    # Loop-path (Blender-first) tracks carry hand-authored 1WALL_guard rails, so a project with a
    # loop.blend gets the entry too (build_kn5_loop renames GUARDRAIL -> 1WALL_guard).
    wall_surface = (bool(cfg.raw.get("network")) or net is not None
                    or (project_dir / "loop.blend").exists())

    # Gravel vs tarmac: the ROAD physics fork. Set once in config (road_surface) so the whole variant
    # is reproducible from track.config.json — the geometry above is identical either way.
    road_surface = str(cfg.raw.get("road_surface", "tarmac"))
    # ledger 0053: the wheel's kerb effect, opt-in per track (absent = 0 = byte-identical surfaces.ini)
    kerb_ff = int(cfg.raw.get("kerb_ff_effect", 0) or 0)

    out = project_dir / "build" / cfg.slug
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "surfaces.ini").write_text(
        surfaces_ini(wall=wall_surface, road_surface=road_surface, kerb_ff_effect=kerb_ff), encoding="utf-8")

    params, geom = _map_params(xz)
    (out / "data" / "map.ini").write_text(map_ini(params), encoding="utf-8")
    # HUD minimap — white track, transparent, AC convention (consistent with map.ini)
    _draw_track_png(xz, geom, out / "map.png", stroke=(255, 255, 255, 255),
                    width=params["DRAWING_SIZE"], flip_y=False, multi=multi)
    # preview — OSM street map with the route drawn on it (Kevin), from the widths stage's
    # cached ways (data/osm.ways.json) so pack needs no network. Falls back to the 3D render
    # or the plain outline when no ways cache exists (aerial-traced facilities).
    preview_img = _osm_preview(project_dir)
    render_svg = project_dir / "data" / "track_render.svg"
    # Only use the 3D render as preview source if it is a sane size for the rasterizer. On a
    # 25 km stage it is 275 MB, qlmanage times out, and _rasterize's fallback then wrote the
    # ENTIRE SVG into ui/ — Dragon Tail v0.1.0 shipped a 288 MB ui/preview.svg that CM never
    # reads (it wants preview.png). The plain outline is always small and always rasterizes.
    _use_render = render_svg.exists() and render_svg.stat().st_size < 5_000_000
    outline_svg = _track_svg(xz, geom, stroke="#ff3b30", width=5, bg="#0c1116", flip_y=True, multi=multi)
    preview_src = render_svg.read_text(encoding="utf-8") if _use_render else outline_svg

    import shutil
    ai_kind: dict[str, str] = {}
    layout_cfgs = [lo if isinstance(lo, dict) else {"id": str(lo)} for lo in cfg.layouts]
    layouts = [lo["id"] for lo in layout_cfgs]
    if len(set(layouts)) != len(layouts):
        raise ValueError(f"duplicate layout ids in track.config.json: {layouts}")
    # SINGLE-LAYOUT tracks use the suffix-FREE structure: models.ini, ui/ui_track.json, ai/ at
    # the root. Writing models_<layout>.ini makes AC treat the track as multi-layout and look
    # for <track>/<layout>/map.png — which doesn't exist, so the in-game minimap NEVER rendered.
    single = len(layouts) == 1
    # clean STALE structure from previous packs of the other shape or of retired layouts:
    # models.ini beside models_<layout>.ini makes AC mis-detect the layout structure (and vice
    # versa); the installed v0.22 carried ui/full + ui/freeway + a freeway kn5 the same way.
    clean_stale_structure(out, layouts, single=single)
    # the kn5s each layout adds beside the road kn5 — resolved up front so a missing race or spawn
    # kn5 fails BEFORE anything is written (strict), never after a half-packed folder
    extras_by_layout = {lo["id"]: layout_kn5s(cfg, lo, project_dir, single=single, strict=strict_kn5)
                        for lo in layout_cfgs}
    # a closure kn5 no declared layout loads (a retired layout, an earlier corridor) must not ride along:
    # pack_release zips the whole folder, and an extra closure is a wall in somebody's lane
    _wanted = {name for ex in extras_by_layout.values() for name, _ in ex}
    for _stale in sorted(out.glob(f"{cfg.slug}_closure_*.kn5")):
        if _stale.name not in _wanted:
            print(f"[track_folder] removed stale {_stale.name} (no declared layout loads it)")
            _stale.unlink()
    for _stale in sorted(out.glob(f"{cfg.slug}_race_*.kn5")):     # a retired lap's common set (ledger 0054)
        if _stale.name not in _wanted:
            print(f"[track_folder] removed stale {_stale.name} (no declared layout loads it)")
            _stale.unlink()
    for _stale in sorted(out.glob(f"{cfg.slug}_street.kn5")):      # a retired chicane's street set (ledger 0055)
        if _stale.name not in _wanted:
            print(f"[track_folder] removed stale {_stale.name} (no declared layout loads it)")
            _stale.unlink()
    for lo in layout_cfgs:
        layout = lo["id"]
        # Per-layout spawn set: count pits from THIS layout's dummies_<layout>.json when it exists.
        sp_dummies_path = project_dir / "data" / f"dummies_{layout}.json"
        layout_dummies = json.loads(sp_dummies_path.read_text(encoding="utf-8")) if sp_dummies_path.exists() else dummies
        layout_pits = sum(1 for k in layout_dummies if k.startswith("AC_PIT_")) or n_pits or 1
        extras = extras_by_layout[layout]
        (out / ("models.ini" if single else "models_%s.ini" % layout)).write_text(
            models_ini(kn5_name, [name for name, _ in extras]), encoding="utf-8")
        for name, src in extras:
            if src is not None:
                shutil.copyfile(src, out / name)
        uid = (out / "ui") if single else (out / "ui" / layout)
        uid.mkdir(parents=True, exist_ok=True)
        # ledger 0054: a race layout on a LAP reports and outlines its lap (length, narrowest width, the drawn line);
        # every other layout keeps the track's
        _lap = lo.get("lap") if net is None else None
        if _lap:
            _lrec = json.loads((project_dir / "data" / f"lap.{_lap}.json").read_text(encoding="utf-8"))
            _ll, _lw, _lxz = float(_lrec["lap_m"]), min(float(v) for v in _lrec["widths_m"]), _xz(_lrec, cfg)
            _lgeom = _map_params(_lxz)[1]
        else:
            _ll, _lw, _lxz, _lgeom = length_m, road_width_m, xz, geom
        (uid / "ui_track.json").write_text(json.dumps(ui_track_json(cfg, layout, _ll, layout_pits,
                                                                  _lw), indent=2),
                                           encoding="utf-8")
        _draw_track_png(_lxz, _lgeom, uid / "outline.png", stroke=(232, 236, 240, 255),
                        width=3, flip_y=True, multi=multi)
        if preview_img is not None:
            preview_img.save(uid / "preview.png")
        elif not _rasterize(preview_src, uid / "preview.png", 600) and preview_src is not outline_svg:
            _rasterize(outline_svg, uid / "preview.png", 600)        # the 3D render drew nothing: the outline
        # STALE OUTPUT. build/<slug>/ is not cleaned between runs and pack re-zips whatever it
        # finds, so an artifact a fixed build no longer writes still ships. Dragon Tail's 288 MB
        # ui/preview.svg survived the fix that stopped emitting it and went out in v0.1.0 — a file
        # the game never reads, at 60% of the zip. Once a real preview.png exists, drop it.
        # Nothing writes a preview.svg any more (CM never reads one): any left from an older pack goes.
        _stale_svg = uid / "preview.svg"
        if _stale_svg.exists():
            print(f"[track_folder] removing stale {_stale_svg.relative_to(out)} "
                  f"({_stale_svg.stat().st_size/1e6:.1f} MB)"
                  + (" — superseded by preview.png" if (uid / "preview.png").exists() else ""))
            _stale_svg.unlink()
        if not single:
            # Kunos multi-layout: <track>/<layout>/ holds map.png + data/ + ai/ per layout
            _lroot = out / layout
            (_lroot / "data").mkdir(parents=True, exist_ok=True)
            (_lroot / "data" / "surfaces.ini").write_text(
                surfaces_ini(wall=wall_surface, road_surface=road_surface, kerb_ff_effect=kerb_ff), encoding="utf-8")
            (_lroot / "data" / "map.ini").write_text(map_ini(params), encoding="utf-8")
            _draw_track_png(xz, geom, _lroot / "map.png", stroke=(255, 255, 255, 255),
                            width=params["DRAWING_SIZE"], flip_y=False, multi=multi)
        aid = (out / "ai") if single else (out / layout / "ai")
        aid.mkdir(parents=True, exist_ok=True)
        # SHIP THE PROJECT'S AI (ledger 0022, re-landed): write_ai_line generates
        # ai/fast_lane.ai offline since R2 — a pack that ships only a README silently
        # strips the AI from every install (the original 0022 fix died with the remote
        # cleanup of 2026-08-07; this is its permanent home). Recorded-in-game lines
        # land in the same project ai/ and ride identically.
        # Per-layout source first (<project>/ai/<id>/ — a reverse layout's line is a DISTINCT
        # file, never the forward one byte-reversed; copying ONE ai/ into every layout would send
        # both race layouts down the centre chain and the reverse one backwards), else the
        # project-wide <project>/ai/ (single-layout tracks, or a layout with no line of its own).
        _per_layout_ai = project_dir / "ai" / layout
        _src_ai = _per_layout_ai if (not single and _per_layout_ai.is_dir()
                                     and any(p.suffix.lower() == ".ai" for p in _per_layout_ai.iterdir())) \
            else project_dir / "ai"
        _shipped_ai = 0
        # what the README may honestly say about this layout's line: write_ai_line leaves ai_draft.json
        # beside every draft; a line without one came from elsewhere (a recording, or an old draft)
        _has_ai = _src_ai.is_dir() and any(p.suffix.lower() == ".ai" for p in _src_ai.iterdir())
        ai_kind[layout] = ("draft" if (_src_ai / "ai_draft.json").exists() else "project") if _has_ai else "none"
        if _src_ai.is_dir():
            for _f in sorted(_src_ai.iterdir()):
                if _f.is_file() and _f.suffix.lower() in (".ai", ".csv", ".ini"):
                    shutil.copyfile(_f, aid / _f.name)
                    _shipped_ai += 1
        if _shipped_ai:
            (aid / "README.txt").unlink(missing_ok=True)   # stale placeholder must not ship beside real AI
            print(f"[track_folder] {'ai' if single else layout + '/ai'}/: shipped {_shipped_ai} file(s) from {_src_ai}")
        else:
            (aid / "README.txt").write_text(
                "fast_lane.ai is recorded in-game (AC + Content Manager, Windows) — see "
                "ac-track-modding — or generated offline: python -m scripts.ac.write_ai_line "
                "<project-dir>.\n",
                encoding="utf-8")
        # TV cameras ride in data/ (write_cameras emits data/cameras.ini — REALISM R5)
        _cam = project_dir / "data" / "cameras.ini"
        if _cam.exists():
            _dst_data = (out / "data") if single else (out / layout / "data")
            _dst_data.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_cam, _dst_data / "cameras.ini")
            print(f"[track_folder] data/cameras.ini shipped")

    credits.generate(project_dir, cfg)  # CREDITS.txt + LICENSES.md from assets/licenses.json
    ext_config.generate(project_dir)  # extension/ext_config.ini — GrassFX / RainFX / light pollution / water
    (out / "README.txt").write_text(readme_text(cfg, layout_cfgs, extras_by_layout, kn5_name, length_m,
                                                single=single, ai_kind=ai_kind,
                                                has_ext=(out / "extension" / "ext_config.ini").exists()),
                                    encoding="utf-8")
    # the structure the installer discovers (install.py: models_*.ini) must be exactly the
    # declared layouts — a leftover or a missing ini here is the stale-folder class, not a build
    packed = sorted(p.stem[len("models_"):] for p in out.glob("models_*.ini"))
    if single:
        if packed or not (out / "models.ini").exists():
            raise RuntimeError(f"single-layout pack must leave exactly models.ini (found models_*: {packed})")
    elif packed != sorted(layouts):
        raise RuntimeError(f"packed models_*.ini {packed} != declared layouts {sorted(layouts)}")
    print(f"[track_folder] layouts packed: {layouts} "
          f"({'models.ini' if single else ', '.join('models_%s.ini' % l for l in layouts)})")
    return {"out": str(out), "layouts": layouts, "length_m": length_m, "n_pits": n_pits,
            "map_px": f"{params['WIDTH']}x{params['HEIGHT']}", "kn5": kn5_name,
            "models": {lid: [kn5_name] + [name for name, _ in ex] for lid, ex in extras_by_layout.items()}}


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="scripts.ac.track_folder",
                                 description="Generate the installable AC track folder.")
    ap.add_argument("project_dir", help="projects/<slug>")
    ap.add_argument("--install", action="store_true",
                    help="after generating, install into a local AC content/tracks folder "
                         "(auto-detects it, asks if it can't find it)")
    ap.add_argument("--allow-missing-kn5", action="store_true",
                    help="lay the folder out even when a layout's race/spawn kn5 is not built yet "
                         "(dry runs only — the inis still name the files; the ship chain never passes this)")
    args = ap.parse_args()

    info = generate(args.project_dir, strict_kn5=not args.allow_missing_kn5)
    print(f"wrote track folder → {info['out']}")
    for k, v in info.items():
        if k != "out":
            print(f"  {k}: {v}")

    if args.install:
        from scripts.ac import install
        raise SystemExit(install.main([args.project_dir]))


if __name__ == "__main__":
    main()
