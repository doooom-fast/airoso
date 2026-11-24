"""Ledger 0099 — Lake Murray round 1 toward finished (Kevin 2026-11-22):

- the empty workshop: ship.json sync_in.seed (tools/ship_track_spec.py + tools/ship_track.sh, opt-in), the round trip
  closed (every sync_out file airoso holds comes back in), every file the config names synced in, the seed block and the
  "no blend yet" guard probed in bash on the script's own text (nothing runs, no Blender);
- both heads of the two-arm lamps lit (tools/author_lamp_heads_blend.py, opt-in scenery.streetlights.light_both_heads;
  tools/check_lights_ini.py's both-heads count), on Lake Murray's own lamp record;
- the kerb rumble (kerb_ff_effect 1, sidewalks included);
- the owned asphalt and concrete on the road and the sidewalks (texture_overrides + sync_in.assets);
- every opt-in absent from every other track; the version.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LM = ROOT / "tracks" / "san-diego-lake-murray"
SH = ROOT / "tools" / "ship_track.sh"
TEXT = SH.read_text(encoding="utf-8").replace("\r\n", "\n")
CFG = json.loads((LM / "track.config.json").read_text(encoding="utf-8"))
SHIP = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
FINISH_FOUR = ("high-plains-lm", "milford-road-course-lm", "sand-creek-lm")   # the other three Kevin is finishing
OTHER_CONFIGS = sorted(p for p in (ROOT / "tracks").glob("*/track.config.json") if p.parent.name != LM.name)
OTHER_SPECS = sorted(p for p in (ROOT / "tracks").glob("*/ship.json") if p.parent.name != LM.name)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SPEC = _load("ship_track_spec_0099", ROOT / "tools" / "ship_track_spec.py")
HEADS = _load("author_lamp_heads_0099", ROOT / "tools" / "author_lamp_heads_blend.py")
LIGHTS_INI = _load("check_lights_ini_0099", ROOT / "tools" / "check_lights_ini.py")


def _expand(p):
    ids = [lo["id"] for lo in CFG["layouts"]]
    races = [lo["id"] for lo in CFG["layouts"] if lo.get("race_furniture")]
    laps = sorted({lo["lap"] for lo in CFG["layouts"] if lo.get("race_furniture") and lo.get("lap")})
    for tok, vals in (("{id}", ids), ("{race}", races), ("{lap}", laps)):
        if tok in p:
            return [p.replace(tok, v) for v in vals]
    return [p]


def _is_lfs_pointer(p: Path) -> bool:
    with open(p, "rb") as f:
        return f.read(23) == b"version https://git-lfs"


# --- the empty workshop ----------------------------------------------------------------------------------------
def test_spec_takes_a_seed_list_and_emits_it_only_when_named():
    s = SPEC.load(LM / "ship.json", "san-diego-lake-murray")
    seeds = [ln.split("\t", 1)[1] for ln in SPEC.lines(s) if ln.startswith("in.seed\t")]
    assert seeds == s["sync_in"]["seed"] and seeds[0] == "loop.blend" and len(seeds) == 101
    # no other spec names a seed: their key<TAB>value lines carry no in.seed line (the chain as before)
    for p in OTHER_SPECS:
        o = SPEC.load(p, json.loads(p.read_text(encoding="utf-8"))["track"])
        assert o["sync_in"]["seed"] == [] and not any(ln.startswith("in.seed\t") for ln in SPEC.lines(o)), p
    with tempfile.TemporaryDirectory() as tmp:
        for bad, why in ((["data/dummies_{id}.json"], "templates are for sync_out only"),
                         (["../escape.json"], "climbs out"), (["data/a b.json"], "not a plain relative path")):
            d = json.loads((LM / "ship.json").read_text(encoding="utf-8"))
            d["sync_in"]["seed"] = bad
            q = Path(tmp) / "ship.json"
            q.write_text(json.dumps(d), encoding="utf-8")
            try:
                SPEC.load(q, "san-diego-lake-murray")
            except SPEC.SpecError as e:
                assert why in str(e), (bad, str(e))
            else:
                raise AssertionError(f"seed {bad} was taken")


def test_the_round_trip_is_closed_every_synced_back_file_airoso_holds_comes_back_in():
    si = SHIP["sync_in"]
    inn = set(si["required"]) | set(si["optional"]) | set(si["seed"])
    held = [q for p in SHIP["sync_out"]["required"] + SHIP["sync_out"]["files"] for q in _expand(p) if (LM / q).is_file()]
    missing = sorted(set(held) - inn)
    assert not missing, missing
    assert "loop.blend" in si["seed"] and "loop.blend" in SHIP["sync_out"]["required"]
    # what the --skip-blend chain reads that crossed neither way before 0099: the lap length and the replication rows
    for f in ("data/centerline.geojson", "data/centerline.elevation.json"):
        assert f in si["seed"] and f in SHIP["sync_out"]["files"], f
    # every seed is airoso's own file; a seed is never also copied unconditionally
    for f in si["seed"]:
        assert (LM / f).is_file(), f
        assert f not in si["required"] and f not in si["optional"], f
    assert len(si["seed"]) == len(set(si["seed"]))


def test_the_committed_blend_is_the_one_the_last_install_synced_back():
    """0.20.5's install (2026-11-23, after 0.20.4's 495a2198..., 189,120,404 B) synced its authored blend back; the next
    empty workshop seeds it. 0.20.2's was
    189,063,384 B, sha256 3f13b887... Every author step on it is idempotent (ledger 0099), so a seed of an authored blend
    builds the same"""
    p = LM / "loop.blend"
    if _is_lfs_pointer(p):
        print("  (loop.blend is an LFS pointer on this checkout — the bytes check skipped; the chain refuses a pointer)")
        return
    assert p.stat().st_size == 204_545_652
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    assert h.hexdigest() == "bc7f772e57500efc34153ccb915bedea1ed3d2acd6750f0c6125c27df4a54b74"


def _config_files(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if not k.startswith("_"):
                yield from _config_files(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _config_files(v, f"{path}[{i}]")
    elif isinstance(o, str) and re.search(r"\.(json|gz|png|jpg|npy|npz|csv|geojson)$", o) and "/" in o:
        yield path, o


def test_every_file_the_config_names_reaches_the_workshop():
    """a project-relative file the config names that the track folder holds is synced in (required / optional / seed), or
    is one of airoso's assets in sync_in.assets. scenery.treefx.median_measured.file (2026-11-19) was in no list, so a
    rebuild stopped at the TreeFX step"""
    si = SHIP["sync_in"]
    inn = set(si["required"]) | set(si["optional"]) | set(si["seed"])
    named = list(_config_files(CFG))
    assert ("scenery.treefx.median_measured.file", "source/vegetation/median_heights.lidar.json") in \
        [(p.lstrip("."), f) for p, f in named]
    for path, f in named:
        if f.startswith("assets/"):
            assert f in si["assets"] or (ROOT / f).is_file() and f in ("assets/textures/grass_diffuse.jpg",
                                                                       "assets/textures/grass_normal.jpg"), (path, f)
        elif (LM / f).is_file():
            assert f in inn, (path, f)


def test_the_workshop_is_a_fresh_one_and_the_old_ones_are_left_as_records():
    assert SHIP["workshop_project"] == "lm_line"
    assert "lm_v4" in SHIP["_workshop_doc"] and "lm_phase2" in SHIP["_workshop_doc"]


def _seed_block() -> str:
    a = TEXT.index("if [ ${#IN_SEED[@]} -gt 0 ]; then")
    b = TEXT.index('echo "  seeds: ', a)
    return TEXT[a:TEXT.index("\nfi\n", b) + 4]


def _probe(script: str, *args, cwd=None):
    bash = shutil.which("bash")
    return subprocess.run([bash, "-c", "set -euo pipefail\n" + script, "probe", *args], capture_output=True, text=True,
                          timeout=60, check=False, cwd=cwd)


def test_the_seed_block_copies_into_an_empty_project_and_never_over_a_workshops_own():
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    block = _seed_block()
    assert 'if [ -e "$PROJ/$f" ]; then' in block and 'cp "$SRC/$f" "$PROJ/$f"' in block
    with tempfile.TemporaryDirectory() as tmp:
        src, proj = Path(tmp) / "src", Path(tmp) / "proj"
        (src / "data").mkdir(parents=True)
        (src / "loop.blend").write_bytes(b"BLENDER-v402" + b"\0" * 64)
        (src / "data" / "mouths.json").write_text("{}", encoding="utf-8")
        (src / "data" / "pads.built.json").write_text('{"a": 1}', encoding="utf-8")
        (proj / "data").mkdir(parents=True)
        (proj / "data" / "pads.built.json").write_text('{"workshop": true}', encoding="utf-8")
        script = (f'SRC="{src.as_posix()}"; PROJ="{proj.as_posix()}"; IN_SEED=("loop.blend" "data/mouths.json" '
                  f'"data/pads.built.json")\n' + block)
        r = _probe(script)
        assert r.returncode == 0, r.stderr
        assert (proj / "loop.blend").read_bytes() == (src / "loop.blend").read_bytes()
        assert (proj / "data" / "mouths.json").read_text(encoding="utf-8") == "{}"
        assert (proj / "data" / "pads.built.json").read_text(encoding="utf-8") == '{"workshop": true}'   # never overwritten
        assert "seeds: 2 copied from airoso, 1 kept as the workshop had them (1 of those differ from airoso's)" in r.stdout
        assert "seed kept the workshop's own data/pads.built.json" in r.stdout
        # a second run copies nothing
        r = _probe(script)
        assert r.returncode == 0 and "seeds: 0 copied from airoso, 3 kept" in r.stdout, r.stdout
        # an un-pulled LFS pointer is refused before anything is copied over it
        (src / "loop.blend").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:3f13b887\nsize 189063384\n",
                                        encoding="utf-8")
        (proj / "loop.blend").unlink()
        r = _probe(script)
        assert r.returncode == 1 and "is a Git LFS pointer" in r.stdout and not (proj / "loop.blend").exists()
        # a seed airoso lacks stops the chain
        r = _probe(f'SRC="{src.as_posix()}"; PROJ="{proj.as_posix()}"; IN_SEED=("data/nope.json")\n' + block)
        assert r.returncode == 1 and "sync_in.seed names data/nope.json but airoso has no" in r.stdout


def test_a_seeded_blend_passes_the_no_blend_yet_guard():
    if not shutil.which("bash"):
        print("  (no bash on PATH — skipped)")
        return
    a = TEXT.index("seed_blend_ready() {")
    fn = TEXT[a:TEXT.index("\n}\n", a) + 3]
    guard = TEXT[TEXT.index('if [ "$DRAFT_ONLY" = 0 ] && [ ! -f "$PROJ/loop.blend" ]'):].split("\n", 1)[0]
    assert "! seed_blend_ready && ! blend_builder_ready" in guard
    assert TEXT.index("seed_blend_ready() {") < TEXT.index(guard) < TEXT.index('step "sync inputs airoso -> workshop')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        probe = fn + 'if seed_blend_ready; then echo yes; else echo no; fi\n'
        r = _probe(f'SRC="{src.as_posix()}"; IN_SEED=("loop.blend")\n' + probe)
        assert r.stdout.strip() == "no", r.stderr                 # named, but airoso holds no blend
        (src / "loop.blend").write_bytes(b"BLENDER")
        r = _probe(f'SRC="{src.as_posix()}"; IN_SEED=("data/x.json" "loop.blend")\n' + probe)
        assert r.stdout.strip() == "yes", r.stderr
        r = _probe(f'SRC="{src.as_posix()}"; IN_SEED=("data/x.json")\n' + probe)
        assert r.stdout.strip() == "no"
        r = _probe(f'SRC="{src.as_posix()}"; IN_SEED=()\n' + probe)
        assert r.stdout.strip() == "no"


# --- both heads of the two-arm lamps ---------------------------------------------------------------------------
LIGHTS = json.loads((LM / "data" / "lights.local.json").read_text(encoding="utf-8"))
LED = json.loads((ROOT / "assets" / "models" / "streetlight_led.json").read_text(encoding="utf-8"))


def _obj_verts(name):
    return [tuple(float(q) for q in ln.split()[1:4]) for ln in (ROOT / "assets" / "models" / name).read_text().splitlines()
            if ln.startswith("v ")]


def test_the_twin_model_is_symmetric_so_the_turned_lens_is_the_back_heads():
    post = _obj_verts("streetlight_led_post_twin.obj")
    key = lambda v: (round(v[0], 4), round(v[1], 4), round(v[2], 4))
    have = {key(v) for v in post}
    assert all(key((-x, y, z)) in have for x, y, z in post)            # every vertex has its mirror at -x
    lens = _obj_verts("streetlight_led_lens.obj")
    lk = {key(v) for v in lens}
    assert all(key((x, y, -z)) in lk for x, y, z in lens)              # the lens is symmetric across its own z = 0
    cx = sum(v[0] for v in lens) / len(lens)
    assert abs(cx - LED["lens_centre_m"][0]) < 1e-3                    # 4.0376 m road-ward of the pole


def test_the_back_lenses_on_lake_murrays_lamps():
    rep = HEADS.plan(CFG, LIGHTS, LED)
    lens = LIGHTS["provenance"]["lens_xyz"]
    assert rep["lamps"] == 323 and rep["lenses"] == 646 and len(rep["back_lens_xyz"]) == 323
    assert rep["arm_m"] == {"model": 4.0376, "min": 4.0366, "max": 4.0386}
    assert rep["closest_lenses_m"] == 8.073 and rep["closest_lenses_m"] > HEADS.LENS_APART_M
    for l, b, k in zip(lens, LIGHTS["lamp_bases_xz"], rep["back_lens_xyz"]):
        assert k[1] == l[1]                                            # the same height as the front lens
        assert abs(math.hypot(k[0] - b[0], k[2] - b[1]) - math.hypot(l[0] - b[0], l[2] - b[1])) < 2e-3
        assert abs((k[0] + l[0]) / 2 - b[0]) < 1e-3 and abs((k[2] + l[2]) / 2 - b[1]) < 1e-3   # across the pole


def test_the_back_lens_needs_the_twin_led_lamp():
    for change in ({"model": "street_lamp_2026_10"}, {"arms": 1}):
        cfg = json.loads(json.dumps(CFG))
        cfg["scenery"]["streetlights"].update(change)
        try:
            HEADS.plan(cfg, LIGHTS, LED)
        except SystemExit as e:
            assert "needs model 'led_cobra' with arms 2" in str(e)
        else:
            raise AssertionError(f"{change} was taken")
    one_arm = json.loads(json.dumps(LIGHTS))
    one_arm["provenance"]["arms"] = 1
    try:
        HEADS.plan(CFG, one_arm, LED)
    except SystemExit as e:
        assert "not the twin-arm LED lamp" in str(e)
    else:
        raise AssertionError("a one-arm record was taken")
    near = json.loads(json.dumps(LIGHTS))                               # two lamps' back lenses 1 m apart: one light
    b0, l0 = near["lamp_bases_xz"][0], near["provenance"]["lens_xyz"][0]
    k0 = HEADS.back_of(l0, b0)
    near["lamp_bases_xz"][1] = [k0[0] + 1.0 + 4.0376, k0[2]]
    near["provenance"]["lens_xyz"][1] = [k0[0] + 1.0, l0[1], k0[2]]
    try:
        HEADS.plan(CFG, near, LED)
    except SystemExit as e:
        assert "would merge into one light" in str(e)
    else:
        raise AssertionError("two lenses 1 m apart were taken")


def _lens_quads(lens_xyz, bases_xz, back=False):
    """each lamp's lens quad as author_lamps_blend places it (the lens OBJ in the lamp's frame), local frame"""
    obj = _obj_verts("streetlight_led_lens.obj")
    lx, ly, _ = LED["lens_centre_m"]
    out = []
    for l, b in zip(lens_xyz, bases_xz):
        rx, rz = (l[0] - b[0]) / lx, (l[2] - b[1]) / lx
        n = math.hypot(rx, rz)
        rx, rz = rx / n, rz / n
        tx, tz = -rz, rx
        yd = l[1] - ly
        quad = [(b[0] + rx * v[0] + tx * v[2], yd + v[1], b[1] + rz * v[0] + tz * v[2]) for v in obj]
        if back:
            quad = [tuple(HEADS.back_of(q, b)) for q in quad]
        out.append(quad)
    return out


def test_ext_config_clusters_two_lights_per_lamp_and_the_check_wants_both():
    sys.path.insert(0, str(ROOT))
    from scripts.ac import ext_config
    lens, bases = LIGHTS["provenance"]["lens_xyz"], LIGHTS["lamp_bases_xz"]
    back = HEADS.plan(CFG, LIGHTS, LED)["back_lens_xyz"]
    pts = [(x, y, -z) for quad in _lens_quads(lens, bases) + _lens_quads(lens, bases, back=True) for x, y, z in quad]
    heads = ext_config.lamp_clusters(pts)
    assert len(heads) == 646
    want = [(l[0], l[1], -l[2]) for l in lens + back]
    for h in heads:
        assert min(math.dist(h, w) for w in want) < 0.01
    # the written ini as ext_config writes it, read back by check_lights_ini with the heads file
    sl = CFG["lighting"]["streetlight"]
    c = [round(255 * float(v)) for v in sl["color"]]
    blocks = "".join(f"[LIGHT_{i}]\nACTIVE = 1\nPOSITION = {x:.2f}, {y - 0.15:.2f}, {z:.2f}\nDIRECTION = 0, -1, 0\n"
                     f"COLOR = {c[0]}, {c[1]}, {c[2]}, {sl['intensity']}\nSPOT = {sl['spot_deg']}\nRANGE = {sl['range_m']}\n"
                     f"RANGE_GRADIENT_OFFSET = {sl['range_gradient_offset']}\nSPECULAR_MULT = {sl['specular_mult']}\n\n"
                     for i, (x, y, z) in enumerate(sorted(heads)))
    parsed = LIGHTS_INI.parse_lights(blocks)
    r = LIGHTS_INI.check(LIGHTS, parsed, sl, back)
    assert r["ok"] and r["matched"] == 646 and r["n_lenses"] == 646, r["problems"][:4]
    r = LIGHTS_INI.check(LIGHTS, parsed, sl)                            # the one-per-lamp check refuses two per lamp
    assert not r["ok"] and any("646 [LIGHT_N] blocks for 323 lamps" in p for p in r["problems"])
    fronts = LIGHTS_INI.parse_lights("".join(
        f"[LIGHT_{i}]\nPOSITION = {x:.2f}, {y - 0.15:.2f}, {-z:.2f}\n\n" for i, (x, y, z) in enumerate(sorted(lens))))
    r = LIGHTS_INI.check(LIGHTS, fronts, None, back)                    # opted in, back heads dark: refused
    assert not r["ok"] and any("lenses have no light" in p and "back head" in p for p in r["problems"])


def test_the_check_refuses_an_opted_in_build_without_the_heads_file():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        (proj / "data").mkdir()
        (proj / "track.config.json").write_text(json.dumps(CFG), encoding="utf-8")
        (proj / "data" / "lights.local.json").write_text(json.dumps(LIGHTS), encoding="utf-8")
        ini = proj / "ext_config.ini"
        ini.write_text("", encoding="utf-8")
        assert LIGHTS_INI.main([str(proj), "--ini", str(ini)]) == 1


def test_both_heads_is_lake_murrays_alone_and_wired_as_an_author_step():
    assert CFG["scenery"]["streetlights"]["light_both_heads"] is True
    au = SHIP["steps"]["author"]
    # (ledger 0055 round 2: College's own step and the medians' tops stand before it, on the scene as it ships)
    assert au[:4] == ["college_split", "median_rebuild", "median_tops", "lamp_heads"] and au[-3:] == ["race_author", "signs", "race_verify"]   # the race steps keep their order
    assert "author_lamp_heads() {" in TEXT and "tools/author_lamp_heads_blend.py" in TEXT
    assert "data/lights.heads.json" in SHIP["sync_out"]["files"]
    for p in OTHER_CONFIGS:
        sl = ((json.loads(p.read_text(encoding="utf-8")).get("scenery") or {}).get("streetlights") or {})
        if p.parent.name == "sand-creek-lm":
            # Sand Creek 0.2.10 (round 2): the same step, lamp_heads (its ship.json names it below)
            assert sl["light_both_heads"] is True and "both_heads_by" not in sl, p
            continue
        assert "light_both_heads" not in sl, p
    assert "both_heads_by" not in CFG["scenery"]["streetlights"]       # Lake Murray: lamp_heads lights the back head
    for p in OTHER_SPECS:
        steps = json.loads(p.read_text(encoding="utf-8"))["steps"]
        names = [n for ph in steps.values() if isinstance(ph, list) for n in ph]
        if p.parent.name == "sand-creek-lm":
            assert steps["author"][0] == "lamp_heads", p                 # Sand Creek 0.2.10 (round 2)
            continue
        assert "lamp_heads" not in names, p
    # not opted in: the tool removes a stale record and opens no blend (no bpy needed for that path)
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        (proj / "data").mkdir()
        cfg = json.loads(json.dumps(CFG))
        del cfg["scenery"]["streetlights"]["light_both_heads"]
        (proj / "track.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        (proj / "data" / "lights.heads.json").write_text("{}", encoding="utf-8")
        assert HEADS.main([str(proj)]) == 0 and not (proj / "data" / "lights.heads.json").exists()


# --- the kerb rumble -------------------------------------------------------------------------------------------
def test_the_kerb_rumble_is_on_sidewalks_included():
    sys.path.insert(0, str(ROOT))
    from scripts.ac import track_folder
    assert CFG["kerb_ff_effect"] == 1
    ini = track_folder.surfaces_ini(kerb_ff_effect=int(CFG["kerb_ff_effect"]))
    blocks = {re.search(r"KEY=(\w+)", b).group(1): b for b in ini.split("\n\n")}
    assert "FF_EFFECT=1" in blocks["KERB"]
    assert all("FF_EFFECT=0" in b for k, b in blocks.items() if k != "KERB")
    # KEY=KERB is every 1KERB_* mesh: the race kerbs and the street sidewalks (1KERB_sidewalk) alike
    assert "VIBRATION_GAIN=1.0" in blocks["KERB"] and "VIBRATION_LENGTH=1.5" in blocks["KERB"]
    for p in OTHER_CONFIGS:
        assert int(json.loads(p.read_text(encoding="utf-8")).get("kerb_ff_effect", 0) or 0) == 0, p


# --- the owned asphalt and concrete ----------------------------------------------------------------------------
OWNED = {"1ROAD": ("asphalt_dense_diffuse.jpg", "asphalt_dense_normal.jpg"),
         "1KERB_SIDEWALK": ("concrete_plain_diffuse.jpg", "concrete_plain_normal.jpg")}
MD5 = {"asphalt_dense_diffuse.jpg": ("339c4244d8b07494be81df14eb963c8c", 2_346_705),     # ledger 0095's runbook
       "asphalt_dense_normal.jpg": ("7a71dfcefbbce0267cb0d17f0c931fb0", 3_198_685)}


def test_the_road_and_the_sidewalks_bind_the_owned_pairs():
    sys.path.insert(0, str(ROOT))
    from scripts.ac import pbr
    tov = CFG["texture_overrides"]
    for key, (d, n) in OWNED.items():
        assert tov[key]["diffuse"] == f"assets/textures/{d}" and tov[key]["normal"] == f"assets/textures/{n}"
        for f in (d, n):
            assert f"assets/textures/{f}" in SHIP["sync_in"]["assets"] and (ROOT / "assets" / "textures" / f).is_file()
    for f, (md5, size) in MD5.items():
        b = (ROOT / "assets" / "textures" / f).read_bytes()
        assert len(b) == size and hashlib.md5(b).hexdigest() == md5, f
    assert "road_wear" not in CFG                     # no road wear on Lake Murray: no detail_highpass_m
    ov = pbr.load_overrides(LM)
    for name, want in (("1ROAD_road", "asphalt_dense"), ("1ROAD_pad_J2", "asphalt_dense"),
                       ("1ROAD_mouthfill_0", "asphalt_dense"), ("1KERB_sidewalk", "concrete_plain"),
                       ("1KERB_sidewalk_padJ3", "concrete_plain")):
        r = pbr.resolve(name, ov)
        assert r["overridden"] and r["diffuse"].name == f"{want}_diffuse.jpg" and r["normal"].name == f"{want}_normal.jpg", name
    r = pbr.resolve("1KERB_race_770_out", ov)        # the race kerbs keep their worn atlas
    assert r["diffuse"].name == "kerb_race_worn_diffuse.jpg" and not r["overridden"]
    # the 4 m tile the prep's planar UV lays (build_kn5_loop UV_TILE) is the pairs' own tile
    prep = (LM / "engine-july-snapshot" / "scripts" / "ac" / "build_kn5_loop.py").read_text(encoding="utf-8")
    assert "UV_TILE = 4.0" in prep
    # the owned asphalt is High Plains' and Milford's too (ledger 0095). Kevin 2026-11-22 "On every track now" for the owned
    # asphalt and concrete means the four tracks he is finishing (Lake Murray, Sand Creek, High Plains, Milford), never the
    # rest: Milford binds concrete_plain since 0.1.14 (ledger 0100), High Plains and Sand Creek in their finish rounds
    for p in OTHER_CONFIGS:
        t = p.read_text(encoding="utf-8")
        name = p.parent.name
        if "concrete_plain" in t:
            assert name in FINISH_FOUR, p
        if name in ("high-plains-lm", "milford-road-course-lm"):
            assert "asphalt_dense" in t, p
        elif "asphalt_dense" in t:
            assert name in FINISH_FOUR, p


def test_version_is_0_20_6():
    """0.20.3 round 1; 0.20.4 round 1c (the walk's back grade, tests/tools/test_lake_murray_0099_walk_grade.py); 0.20.5
    round 2 (College Avenue as two roads and the medians' grass tops, ledger 0055; the version the Mac named); 0.20.6
    round 3 (the Mac 2026-11-23: Mission Gorge's terracotta median first, tests/tools/test_terracotta_median_0099.py)"""
    assert CFG["version"] == "0.20.6"
