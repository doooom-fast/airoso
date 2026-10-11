"""Mac-native CSP **TreeFX** + **GrassFX** vegetation emitter.

The kn5 exporter is Blender-on-Windows; this module is the Mac-native alternative for *foliage*:
instead of baking billboard/OBJ tree meshes into the kn5, we emit the CSP (Custom Shaders Patch)
config that makes AC render real **TreeFX** 3D trees at runtime, plus a **GrassFX** block.

**Licensing (critical).** The actual ``.bin`` tree MODELS are third-party, licensed, and
USER-SUPPLIED — we never download or commit them. Everything here only *references* a species by
its ``.bin`` filename; the config we generate (``trees.txt`` + the ext_config ``[TREES]`` block) is
ours and license-clean. The user drops the licensed models into ``extension/trees/`` locally; a
build logs exactly which filenames it expects so nothing is guessed.

**Never ship a dangling manifest.** A ``tree:`` line naming a ``.bin`` that isn't in the packaged
``extension/trees/`` is the "tree manifest missing" failure — CSP loads the list, can't resolve the
model, and complains. So resolution is a BUILD-TIME gate, not a runtime hope: :func:`resolve_models`
looks each species up in the configured search dirs, and
:meth:`TreeFXCollector.drop_unresolved_species` deletes every tree of a species with no model file
*before* anything is written. What ships always references models that are actually present — either
because ``bundle`` copied them into the build, or because the species was dropped. If that leaves no
species at all, the caller skips the ``[TREES]`` block entirely rather than emit an empty manifest.

``scenery.treefx.bundle`` (with ``bundle_dir``, default ``source/trees/``) copies the resolved models
into the packaged track. That's for personal, non-distributed builds — bundling third-party models
into a track you publish is the licensing problem this module exists to avoid.

**The verified format** (validated against docs and a real pack — see ``docs/TREEFX-FORMAT.md``):

Per-track ``extension/trees/trees.txt``, one directive per line::

    ; comment
    configure: size variance = 0.9, 1.1        ; defaults for the trees that FOLLOW
    tree: MRS_pine_high_2_1.bin; 12.5, 2103.4, -55.2                        ; simple
    tree: pine.bin; pos=12.5, 2103.4, -55.2; angle = 137; size = 3.2        ; extended

The ``.bin`` filename comes first (terminated by ``;``) and *is* the species id; then position
``X, Y, Z`` (metres, AC/kn5 world space, **Y up**); then optional ``key = value`` params (``angle``
in degrees 0-360, ``size``/``width`` unitless multipliers where 1 = native, ``color`` an RGB
multiplier). ``configure:`` lines set defaults for all following trees so per-zone variance is
declared once instead of hand-jittered per line.

This module is pure stdlib (no bpy / numpy) so it runs under the dependency-free test harness and on
a Mac with system python. ``build_env`` computes real positions + ground Y + the same
pavement/clearance rejection it uses for baked foliage, hands them to a :class:`TreeFXCollector`,
and serialises ``data/treefx.json``; ``scripts/ac/ext_config`` renders the text list + the
``[TREES]`` / ``[GRASS_FX]`` sections into the track's ``extension/``.

**GrassFX** (:func:`grassfx_block`) is written in the grammar every shipped CSP track config
uses: ``[GRASS_FX]`` holds the lists (``GRASS_MATERIALS`` / ``GRASS_MESHES`` / ``OCCLUDING_MESHES`` /
``ORIGINAL_GRASS_MATERIALS``), the atlas (``TEXTURE`` + ``TEXTURE_GRID``), the ground-texel mask
(``MASK_*``) and the blade shape (``SHAPE_*``, ``TRIM_PERIOD``); extra blade shapes live in
``[GRASS_FX_TEXTURE_GROUP_n]`` and per-material / per-area looks in ``[GRASS_FX_CONFIGURATION_A..D]``
bound by ``[GRASS_FX_ADJUSTMENT_...]``. The earlier ``[GRASS_FX_TEXTURE_0]`` / ``[GRASS_FX_CONFIGURATION_0]``
/ ``BRIGHTNESS`` / ``HEALTH`` / ``grass_fx/grass_ks.dds`` block matched no shipped config (ledger 0045)
and is retired; a config that still sets those keys fails loud.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


# --------------------------------------------------------------------------------------------------
# Number formatting — trim trailing zeros so lines read like a real pack ("size = 1.05", not
# "1.050000"), stay deterministic (tests assert exact strings), and parse as plain floats in-engine.
# --------------------------------------------------------------------------------------------------
def _fmt(v: float, nd: int = 3) -> str:
    s = f"{float(v):.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _fmt_list(vals: Sequence[float], nd: int = 3) -> str:
    return ", ".join(_fmt(v, nd) for v in vals)


# --------------------------------------------------------------------------------------------------
# trees.txt directives
# --------------------------------------------------------------------------------------------------
@dataclass
class Tree:
    """One ``tree:`` directive. ``x, y, z`` are metres in AC world space (Y up). ``angle`` is yaw in
    degrees; ``size``/``width`` are unitless multipliers (1 = the model's native size); ``color`` is
    an RGB multiplier (``(1, 1, 1)`` neutral). Any of angle/size/width/color set → the *extended*
    line form (``pos=X, Y, Z; key = value; ...``); all unset → the *simple* form (``X, Y, Z``)."""

    species: str
    x: float
    y: float
    z: float
    angle: Optional[float] = None
    size: Optional[float] = None
    width: Optional[float] = None
    color: Optional[tuple] = None

    def line(self) -> str:
        # X/Y/Z at cm precision (nd=2): trunks land where we sampled; angle whole-ish (nd=1);
        # size/width/color fine (nd=3) — the multipliers matter to the eye at 2 decimals.
        pos = f"{_fmt(self.x, 2)}, {_fmt(self.y, 2)}, {_fmt(self.z, 2)}"
        extended = any(v is not None for v in (self.angle, self.size, self.width, self.color))
        if not extended:
            return f"tree: {self.species}; {pos}"
        parts = [f"tree: {self.species}; pos={pos}"]
        if self.angle is not None:
            parts.append(f"angle = {_fmt(self.angle % 360.0, 1)}")
        if self.size is not None:
            parts.append(f"size = {_fmt(self.size, 3)}")
        if self.width is not None:
            parts.append(f"width = {_fmt(self.width, 3)}")
        if self.color is not None:
            parts.append(f"color = {_fmt_list(self.color, 3)}")
        return "; ".join(parts)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"species": self.species, "x": self.x, "y": self.y, "z": self.z}
        if self.angle is not None:
            d["angle"] = self.angle
        if self.size is not None:
            d["size"] = self.size
        if self.width is not None:
            d["width"] = self.width
        if self.color is not None:
            d["color"] = list(self.color)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Tree":
        color = d.get("color")
        return cls(species=d["species"], x=d["x"], y=d["y"], z=d["z"],
                   angle=d.get("angle"), size=d.get("size"), width=d.get("width"),
                   color=tuple(color) if color is not None else None)


@dataclass
class Configure:
    """A ``configure:`` directive — sets a default for every tree that FOLLOWS it (until the next
    ``configure`` for the same key). Corroborated keys: ``size variance = lo, hi``,
    ``angle variance = lo, hi``, ``seed``."""

    key: str
    values: Any  # scalar or sequence

    def line(self) -> str:
        if isinstance(self.values, (list, tuple)):
            body = _fmt_list(self.values, 3)
        elif isinstance(self.values, float):
            body = _fmt(self.values, 3)
        else:
            body = str(self.values)
        return f"configure: {self.key} = {body}"

    def to_dict(self) -> dict:
        vals = list(self.values) if isinstance(self.values, (list, tuple)) else self.values
        return {"key": self.key, "values": vals}

    @classmethod
    def from_dict(cls, d: dict) -> "Configure":
        return cls(key=d["key"], values=d["values"])


DEFAULT_HEADER = [
    "; ============================================================================",
    "; CSP TreeFX tree list (generated by prodrive-ac-builder / scripts/environment/treefx.py)",
    "; Loaded via extension/ext_config.ini -> [TREES] LIST_0. Each 'tree:' line references a .bin",
    "; MODEL by filename; the licensed models are USER-SUPPLIED under extension/trees/ (see README,",
    "; never committed). Format: tree: <model>.bin; X, Y, Z  (metres, AC world space, Y up).",
    "; Spec + GrassFX keys: docs/TREEFX-FORMAT.md",
    "; ============================================================================",
    "",
]


def render_trees_txt(directives: Iterable, *, header: Optional[Sequence[str]] = None) -> str:
    """Render an ordered list of directives (``str`` comments, :class:`Configure`, :class:`Tree`) to
    the exact ``trees.txt`` text. Order is load-bearing: a ``configure`` applies to trees after it."""
    lines: list[str] = list(DEFAULT_HEADER if header is None else header)
    for d in directives:
        if isinstance(d, str):
            lines.append(d)
        else:
            lines.append(d.line())
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------------
# Density model
# --------------------------------------------------------------------------------------------------
def elevation_keep_prob(y: float, *, y_lo: float, y_hi: float,
                        keep_lo: float = 0.2, keep_hi: float = 1.0, curve: float = 1.0) -> float:
    """Keep-probability that rises MONOTONICALLY with elevation ``y`` — the mountain-forest model
    (sparse at the low end, thickening toward the summit). ``t`` = normalised elevation clamped to
    ``[0, 1]``, shaped by ``t ** curve`` (curve > 1 keeps the low slopes barer), lerped
    ``keep_lo -> keep_hi``. ``y_hi == y_lo`` degenerates to ``keep_hi``."""
    span = y_hi - y_lo
    t = 0.0 if span == 0 else (y - y_lo) / span
    t = max(0.0, min(1.0, t))
    if curve != 1.0:
        t = t ** curve
    return keep_lo + (keep_hi - keep_lo) * t


# Aspect (compass direction a slope FACES downhill) from a horizontal downhill vector. Convention:
# +X = East, and NORTH = -Z (documented in TREEFX-FORMAT.md). N/E-facing slopes hold more moisture
# in the northern hemisphere -> denser conifer forest, which is the effect we want on the Lariat.
def aspect_label(nx: float, nz: float) -> Optional[str]:
    """Dominant compass label ('N'/'S'/'E'/'W') of a horizontal aspect vector, or None if flat."""
    if abs(nx) < 1e-9 and abs(nz) < 1e-9:
        return None
    if abs(nx) >= abs(nz):
        return "E" if nx > 0 else "W"
    return "S" if nz > 0 else "N"


def aspect_keep_bonus(nx: float, nz: float, *, favored: Sequence[str] = ("N", "E"),
                      bonus: float = 0.0) -> float:
    """Extra keep-probability when the slope faces a favored compass direction (0 on flat ground or
    an unfavored aspect). Scaled by how strongly the aspect points that way, so a gentle slope gets a
    fraction of the full bonus and a dead-flat spot gets none."""
    label = aspect_label(nx, nz)
    if label is None or label not in favored:
        return 0.0
    mag = math.hypot(nx, nz)
    strength = min(1.0, mag / 0.15)   # ~0.15 m of relief across the sample step = full bonus
    return bonus * strength


# --------------------------------------------------------------------------------------------------
# Creek / riparian band selection
# --------------------------------------------------------------------------------------------------
def _point_segment_distance(px: float, pz: float,
                            ax: float, az: float, bx: float, bz: float) -> float:
    dx, dz = bx - ax, bz - az
    seg2 = dx * dx + dz * dz
    if seg2 <= 1e-12:
        return math.hypot(px - ax, pz - az)
    t = ((px - ax) * dx + (pz - az) * dz) / seg2
    t = max(0.0, min(1.0, t))
    cx, cz = ax + t * dx, az + t * dz
    return math.hypot(px - cx, pz - cz)


def min_distance_to_polylines(px: float, pz: float, lines: Iterable[Sequence[tuple]]) -> float:
    """Shortest distance from (px, pz) to any segment of any polyline (each ``[(x, z), ...]``)."""
    best = math.inf
    for line in lines:
        for i in range(1, len(line)):
            ax, az = line[i - 1][0], line[i - 1][1]
            bx, bz = line[i][0], line[i][1]
            d = _point_segment_distance(px, pz, ax, az, bx, bz)
            if d < best:
                best = d
    return best


def near_polylines(px: float, pz: float, lines: Iterable[Sequence[tuple]], band_m: float) -> bool:
    """True when (px, pz) lies within ``band_m`` of any polyline — the riparian-band test."""
    return min_distance_to_polylines(px, pz, lines) <= band_m


def select_creek_band(positions: Iterable[Sequence[float]], creek_lines: Iterable[Sequence[tuple]],
                      band_m: float) -> list:
    """Filter ``positions`` (``(x, z)`` or ``(x, y, z)``) down to those within ``band_m`` of a creek
    polyline. Keeps only near-water positions — the dense riparian planting stays on the banks."""
    lines = [list(l) for l in creek_lines]
    kept = []
    for p in positions:
        x = p[0]
        z = p[-1]
        if near_polylines(x, z, lines, band_m):
            kept.append(p)
    return kept


# --------------------------------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------------------------------
@dataclass
class Zone:
    """A vegetation zone (config-driven, keyed by name). ``source`` names which build_env placement
    loop feeds it (``poly_scatter`` / ``fill_terrain`` / ``forest3d`` / ``creek`` / ``bush``).
    ``species`` is the list of ``.bin`` filenames mixed within the zone. Dropping a new filename into
    a zone's ``species`` is all it takes to fill that zone with a new model."""

    name: str
    source: str = "fill_terrain"
    species: list = field(default_factory=list)
    weights: Optional[list] = None
    size_variance: Optional[tuple] = None
    angle_variance: Optional[tuple] = (0.0, 360.0)
    color: Optional[tuple] = None
    band_m: Optional[float] = None
    density: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, name: str, d: dict) -> "Zone":
        d = d or {}
        sv = d.get("size_variance")
        av = d.get("angle_variance", [0.0, 360.0])
        color = d.get("color")
        return cls(
            name=name,
            source=str(d.get("source", "fill_terrain")),
            species=list(d.get("species", [])),
            weights=list(d["weights"]) if d.get("weights") else None,
            size_variance=tuple(sv) if sv else None,
            angle_variance=tuple(av) if av else None,
            color=tuple(color) if color else None,
            band_m=float(d["band_m"]) if d.get("band_m") is not None else None,
            density=dict(d.get("density", {}) or {}),
        )

    def keep_prob(self, y: float, aspect: Optional[Sequence[float]] = None) -> float:
        """Probability of KEEPING a candidate at height ``y`` (with an optional horizontal aspect
        vector). ``density.by`` selects the model: ``elevation`` (mountain forest, rises with y,
        optional N/E aspect bonus) or ``constant`` (a flat ``keep`` — used by creek/urban zones,
        which are already spatially gated by their placement loop)."""
        dd = self.density
        by = dd.get("by", "constant")
        if by == "elevation":
            p = elevation_keep_prob(
                y,
                y_lo=float(dd.get("elev_lo_m", 0.0)),
                y_hi=float(dd.get("elev_hi_m", 1.0)),
                keep_lo=float(dd.get("keep_lo", 0.2)),
                keep_hi=float(dd.get("keep_hi", 1.0)),
                curve=float(dd.get("curve", 1.0)),
            )
            if aspect is not None and dd.get("aspect_bonus"):
                p += aspect_keep_bonus(
                    aspect[0], aspect[1],
                    favored=tuple(dd.get("aspect_favored", ("N", "E"))),
                    bonus=float(dd.get("aspect_bonus", 0.0)),
                )
            return max(0.0, min(1.0, p))
        return max(0.0, min(1.0, float(dd.get("keep", 1.0))))

    def pick_species(self, rng) -> str:
        if not self.species:
            return "tree.bin"
        if self.weights and len(self.weights) == len(self.species):
            return rng.choices(self.species, weights=self.weights, k=1)[0]
        return self.species[rng.randrange(len(self.species))]

    def configure_directives(self, seed: int) -> list:
        """The per-zone ``configure:`` lines emitted before its trees — declaring variance ONCE so
        CSP jitters size/angle instead of us hand-jittering every line."""
        out: list = [Configure("seed", int(seed))]
        if self.size_variance:
            out.append(Configure("size variance", list(self.size_variance)))
        if self.angle_variance:
            out.append(Configure("angle variance", list(self.angle_variance)))
        return out


# --------------------------------------------------------------------------------------------------
# Collector — build_env populates this from real placements, then serialises it.
# --------------------------------------------------------------------------------------------------
class TreeFXCollector:
    """Accumulates real tree placements from build_env's foliage loops, applies each zone's density
    model, and renders ``trees.txt`` + the ``[TREES]`` block. One source maps to at most one zone
    (first declared wins); a source with no zone places nothing (build_env skips that loop)."""

    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.enabled = bool(cfg.get("enabled", False))
        self.seed = int(cfg.get("seed", 1))
        self.surface_materials = list(cfg.get("surface_materials") or []) or None
        self.surface_meshes = list(cfg.get("surface_meshes") or [])
        self.grassfx = cfg.get("grassfx")  # optional per-track GrassFX tuning (dict) or None
        self.compiled_list = cfg.get("compiled_list")  # optional baked VAO filename (not produced here)
        self.header = cfg.get("header")  # optional custom trees.txt header (list of lines)
        # Copy the resolved .bin models into the packaged track (personal builds — see the module
        # docstring's licensing note). bundle_dir is where the user keeps them, relative to the project.
        self.bundle = bool(cfg.get("bundle", False))
        self.bundle_dir = str(cfg.get("bundle_dir", "source/trees"))
        self.zones: dict[str, Zone] = {
            name: Zone.from_config(name, z) for name, z in (cfg.get("zones") or {}).items()
        }
        self._source_index: dict[str, str] = {}
        for name, zone in self.zones.items():
            self._source_index.setdefault(zone.source, name)
        self._by_zone: dict[str, list] = {name: [] for name in self.zones}
        self._expected: set[str] = set()

    # ---- queries build_env uses to gate each loop ----
    def has_source(self, source: str) -> bool:
        return source in self._source_index

    def zone_for(self, source: str) -> Optional[Zone]:
        name = self._source_index.get(source)
        return self.zones.get(name) if name else None

    # ---- placement ----
    def add(self, source: str, x: float, y: float, z: float, *, rng,
            aspect: Optional[Sequence[float]] = None, angle: Optional[float] = None,
            size: Optional[float] = None, width: Optional[float] = None) -> bool:
        """Offer a candidate (already ground-sampled + pavement/clearance-rejected by build_env) to
        the zone that owns ``source``. Applies the zone's density keep-test with ``rng``; on keep,
        picks a species and records the tree. Returns True iff a tree was placed."""
        zone = self.zone_for(source)
        if zone is None:
            return False
        if rng.random() > zone.keep_prob(y, aspect):
            return False
        species = zone.pick_species(rng)
        self._expected.add(species)
        self._by_zone[zone.name].append(
            Tree(species, x, y, z, angle=angle, size=size, width=width, color=zone.color)
        )
        return True

    # ---- outputs ----
    def counts(self) -> dict:
        return {name: len(trees) for name, trees in self._by_zone.items()}

    def total(self) -> int:
        return sum(len(t) for t in self._by_zone.values())

    def expected_species(self) -> list:
        """Every ``.bin`` filename this build references — the models the user must supply. Includes
        each zone's declared species even if density happened to place none, so the manifest is
        stable across seeds."""
        declared = {sp for zone in self.zones.values() for sp in zone.species}
        return sorted(self._expected | declared)

    def drop_unresolved_species(self, resolved: Iterable[str]) -> list:
        """Delete every tree whose species has no model file, and stop declaring those species.

        ``resolved`` is the set of ``.bin`` filenames that actually exist (see :func:`resolve_models`).
        Returns the sorted list of dropped species so the caller can report them. This is what keeps a
        shipped ``trees.txt`` honest: after this call, every ``tree:`` line names a model that is
        really there. Call it BEFORE :meth:`trees_txt` / :meth:`expected_species`."""
        keep = set(resolved)
        dropped = sorted(sp for sp in self.expected_species() if sp not in keep)
        if not dropped:
            return []
        for zone in self.zones.values():
            zone.species = [sp for sp in zone.species if sp in keep]
            self._by_zone[zone.name] = [t for t in self._by_zone[zone.name] if t.species in keep]
        self._expected = {sp for sp in self._expected if sp in keep}
        return dropped

    def directives(self) -> list:
        """Ordered directive list: per zone, a header comment, its ``configure`` lines, then its
        trees. Zones with no placed trees are skipped."""
        out: list = []
        for name, zone in self.zones.items():
            trees = self._by_zone[name]
            if not trees:
                continue
            sp = "/".join(zone.species) if zone.species else "(unspecified)"
            out.append(f"; --- zone '{name}' ({zone.source}): {len(trees)} trees, species={sp} ---")
            out.extend(zone.configure_directives(self.seed))
            out.extend(trees)
        return out

    def trees_txt(self) -> str:
        return render_trees_txt(self.directives(), header=self.header)

    def to_json(self) -> dict:
        zones_json = {}
        for name, zone in self.zones.items():
            zones_json[name] = {"source": zone.source, "species": zone.species,
                                "size_variance": list(zone.size_variance) if zone.size_variance else None,
                                "angle_variance": list(zone.angle_variance) if zone.angle_variance else None,
                                "color": list(zone.color) if zone.color else None,
                                "trees": [t.to_dict() for t in self._by_zone[name]]}
        return {
            "enabled": self.enabled,
            "seed": self.seed,
            "surface_materials": self.surface_materials,
            "surface_meshes": self.surface_meshes,
            "grassfx": self.grassfx,
            "compiled_list": self.compiled_list,
            "header": self.header,
            "bundle": self.bundle,
            "bundle_dir": self.bundle_dir,
            "expected_species": self.expected_species(),
            "zones": zones_json,
        }

    def write_json(self, path) -> None:
        import json
        Path(path).write_text(json.dumps(self.to_json(), indent=1) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, obj: dict) -> "TreeFXCollector":
        """Reconstruct a collector from ``data/treefx.json`` — used by ext_config to render the
        text list + [TREES] block without re-running placement."""
        self = cls.__new__(cls)
        self.enabled = bool(obj.get("enabled", False))
        self.seed = int(obj.get("seed", 1))
        self.surface_materials = obj.get("surface_materials")
        self.surface_meshes = list(obj.get("surface_meshes") or [])
        self.grassfx = obj.get("grassfx")
        self.compiled_list = obj.get("compiled_list")
        self.header = obj.get("header")
        self.bundle = bool(obj.get("bundle", False))
        self.bundle_dir = str(obj.get("bundle_dir", "source/trees"))
        self.zones = {}
        self._source_index = {}
        self._by_zone = {}
        self._expected = set(obj.get("expected_species") or [])
        for name, zj in (obj.get("zones") or {}).items():
            zone = Zone(name=name, source=zj.get("source", "fill_terrain"),
                        species=list(zj.get("species") or []),
                        size_variance=tuple(zj["size_variance"]) if zj.get("size_variance") else None,
                        angle_variance=tuple(zj["angle_variance"]) if zj.get("angle_variance") else None,
                        color=tuple(zj["color"]) if zj.get("color") else None)
            self.zones[name] = zone
            self._source_index.setdefault(zone.source, name)
            self._by_zone[name] = [Tree.from_dict(t) for t in (zj.get("trees") or [])]
        return self


# --------------------------------------------------------------------------------------------------
# ext_config sections
# --------------------------------------------------------------------------------------------------
def trees_ext_section(list_files: Sequence[str], *, surface_materials: Sequence[str],
                      surface_meshes: Optional[Sequence[str]] = None,
                      compiled_list: Optional[str] = None,
                      expected_species: Optional[Sequence[str]] = None,
                      autumn_conditions: Optional[Sequence[str]] = None,
                      winter_conditions: Optional[Sequence[str]] = None) -> list:
    """The ``[TREES]`` ext_config block. ``LIST_0..N`` point at text lists (relative to
    ``extension/``); ``SURFACE_MATERIALS`` are THIS track's real grass/road materials the trees snap
    vertically onto (and align lighting to). ``COMPILED_LIST`` (the optional baked VAO from the
    external bakery — not produced here) is emitted commented-out."""
    out = ["; --- TreeFX: 3D trees rendered by CSP from a text list (models are user-supplied .bin) -",
           "; SURFACE_MATERIALS = this track's real grass/road materials; trees snap onto them.",
           "[TREES]"]
    for i, lf in enumerate(list_files):
        out.append(f"LIST_{i} = {lf}")
    out.append(f"SURFACE_MATERIALS = {', '.join(surface_materials)}")
    if surface_meshes:
        out.append(f"SURFACE_MESHES = {', '.join(surface_meshes)}")
    for i, cond in enumerate(autumn_conditions or []):
        out.append(f"SEASON_AUTUMN_{i} = {cond}")
    for i, cond in enumerate(winter_conditions or []):
        out.append(f"SEASON_WINTER_{i} = {cond}")
    if compiled_list:
        out.append(f"; COMPILED_LIST = {compiled_list}   ; optional baked VAO (external bakery runs "
                   "AC headless; not required — the text list above loads directly)")
    if expected_species:
        out.append("; Expects these user-supplied .bin models under extension/trees/ (see README):")
        out.append("; " + ", ".join(expected_species))
    out.append("")
    return out


# --------------------------------------------------------------------------------------------------
# GrassFX — the grammar every shipped CSP track config uses (census of 73 third-party inis + 19 CSP
# loaded/*.ini on this machine, 2026-10-10, fleet/feedback/0045): lists + atlas + mask + shape in
# [GRASS_FX]; extra blade shapes in [GRASS_FX_TEXTURE_GROUP_N]; per-material / per-area looks in
# [GRASS_FX_CONFIGURATION_A..D] bound by [GRASS_FX_ADJUSTMENT_...]. The previous writer's
# [GRASS_FX_TEXTURE_0] / [GRASS_FX_CONFIGURATION_0] / BRIGHTNESS / HEALTH / grass_fx/grass_ks.dds
# matched NONE of them (the .dds exists nowhere, not even inside dwrite.dll), so that grammar is
# retired and a config that still sets it fails loud (L2) instead of silently drawing nothing.
# --------------------------------------------------------------------------------------------------
_GFX_HEADER = [
    "; --- GrassFX: CSP 3D grass on the terrain tiles -------------------------------",
    "; Grammar = the one every shipped CSP track config uses: lists + atlas + mask + shape in [GRASS_FX];",
    "; optional [GRASS_FX_TEXTURE_GROUP_N], [GRASS_FX_CONFIGURATION_A..D], [GRASS_FX_ADJUSTMENT_...].",
    "; GRASS_* / OCCLUDING_MESHES are OUR kn5 names. OCCLUDING_MESHES is an ALLOW-LIST of near-field,",
    "; ground-seated solids only (road, kerbs, building + house footprints): a far-field or oversized",
    "; mesh here busts the GPU watchdog (shipped v0.12.1-v0.12.6). Blades take the colour of the ground",
    "; texel under them, so the look follows the 1GRASS texture. VERIFY IN-GAME.",
]
_GFX_DEFAULT_TEXTURE = "grass_fx/highlands.dds"   # the atlas embedded in CSP (dwrite.dll); no file on disk
_GFX_DEFAULT_GRID = (8, 3)
_GFX_RETIRED_TEXTURE = "grass_fx/grass_ks.dds"    # the old writer's default; exists nowhere
# MASK quartet presets = (MAIN_THRESHOLD, RED_THRESHOLD, MIN_LUMINANCE, MAX_LUMINANCE). Every mask key is
# about the GROUND texel under the blade (blades take its colour).
_GFX_MASK_PRESETS = {
    # colorado-2013's shipped quartet = the fleet's numbers since the first GrassFX block. Colour-gated,
    # so a terrain texture that mixes dirt does not sprout grass on the dirt.
    "default": (0.5, 0.05, 0.02, 0.35),
    # the wiki's spawn-everywhere preset (la_canyons A, willow_springs): every texel of the listed grass
    # grows blades. For meshes that are 100% grass; it removes any dependence on the undocumented
    # MASK_MAIN_THRESHOLD formula.
    "open": (-1, 0, -1, 1),
}
_GFX_MASK_COMMENT = {
    "default": "; mask: colour-gated (colorado-2013 quartet) - blades only where the ground texel reads as grass",
    "open": "; mask: spawn on every texel (wiki preset) - both listed tiles are 100% grass, no colour gating",
}
_GFX_MASK_KEYS = (("mask_main_threshold", "MASK_MAIN_THRESHOLD"),
                  ("mask_red_threshold", "MASK_RED_THRESHOLD"),
                  ("mask_min_luminance", "MASK_MIN_LUMINANCE"),
                  ("mask_max_luminance", "MASK_MAX_LUMINANCE"))
_GFX_SHAPE_KEYS = (("shape_width", "SHAPE_WIDTH"), ("shape_tidy", "SHAPE_TIDY"), ("shape_cut", "SHAPE_CUT"))
_GFX_WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
_GFX_LETTERS = ("A", "B", "C", "D")              # dwrite.dll carries exactly CONFIGURATION_A..D
_GFX_MAX_GROUPS, _GFX_MAX_PIECES = 4, 8
# Accepted config keys. Keys beginning with '_' are documentation and skipped; ANY other key — the
# retired brightness / health included — is a ValueError naming it and this set (L2: a stale or
# mistyped config must not silently produce a different track). Every fleet config today passes a
# bare bool, so nothing breaks.
_GFX_TOP_KEYS = frozenset({
    "enabled", "original_grass_materials", "texture", "texture_grid",
    "mask", "mask_main_threshold", "mask_red_threshold", "mask_min_luminance", "mask_max_luminance",
    "mask_blur", "shape_size", "shape_width", "shape_tidy", "shape_cut", "trim_period",
    "height_mult", "texture_brightness", "color_factor",
    "texture_groups", "configurations", "adjustments"})
_GFX_CONF_KEYS = frozenset({
    "mask", "mask_main_threshold", "mask_red_threshold", "mask_min_luminance", "mask_max_luminance",
    "mask_blur", "shape_size", "shape_width", "shape_tidy", "shape_cut", "trim_period", "height_mult",
    "texture_base_chance", "texture_group_chances"})
_GFX_PIECE_KEYS = frozenset({"piece", "chance", "size_mult", "wind"})
_GFX_ADJ_KEYS = frozenset({"name", "map", "materials", "meshes", "rect"})
_GFX_RECT_KEYS = frozenset({"center", "size", "angle", "fade"})


def _gfx_err(where: str, msg: str) -> ValueError:
    return ValueError(f"lighting.grassfx{where}: {msg}")


def _gfx_check_keys(d: Any, allowed: frozenset, where: str) -> None:
    if not isinstance(d, dict):
        raise _gfx_err(where, f"expected an object, got {d!r}")
    bad = sorted(str(k) for k in d if not str(k).startswith("_") and k not in allowed)
    if bad:
        raise _gfx_err(where, f"unknown key(s) {', '.join(bad)}; accepted: {', '.join(sorted(allowed))}")


def _gfx_num(v: Any, key: str, where: str = "") -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise _gfx_err(where, f"{key} must be a number, got {v!r}")
    return v


def _gfx_pair(v: Any, key: str, where: str = "") -> str:
    """A GrassFX 'pair': a number, or a 2-list emitted ``a, b`` (CSP: a per-blade range, spanning
    TRIM_PERIOD for the shape keys — just cut -> fully grown)."""
    if isinstance(v, (list, tuple)):
        if len(v) != 2:
            raise _gfx_err(where, f"{key} must be a number or [a, b], got {v!r}")
        return _fmt_list([_gfx_num(x, key, where) for x in v], 3)
    return _fmt(_gfx_num(v, key, where), 3)


def _gfx_dedup(names: Iterable[str]) -> list:
    seen: set = set()
    out: list = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _gfx_names(v: Any, key: str, where: str = "") -> list:
    if not isinstance(v, (list, tuple)) or not all(isinstance(s, str) and s for s in v):
        raise _gfx_err(where, f"{key} must be a list of names, got {v!r}")
    return _gfx_dedup(v)


def _gfx_trim(v: Any, where: str = "") -> str:
    """TRIM_PERIOD: a weekday name (emitted upper-cased; THURSDAY = the mown idiom) or a positive int
    of days (365 = never mown)."""
    if isinstance(v, str):
        u = v.strip().upper()
        if u not in _GFX_WEEKDAYS:
            raise _gfx_err(where, f"trim_period must be a weekday name or an int of days, got {v!r}")
        return u
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise _gfx_err(where, f"trim_period must be a weekday name or a positive int of days, got {v!r}")
    return str(v)


def _gfx_mask_lines(cfg: dict, *, where: str, top: bool) -> tuple:
    """The MASK_* lines. ``mask`` names a preset; each ``mask_*`` key overrides its one line on top of
    it. The top level always emits the full quartet (preset 'default' when unset); a configuration
    emits only what it sets. Returns ``(preset_or_None, lines)``."""
    preset = cfg.get("mask", "default" if top else None)
    vals: dict = {}
    if preset is not None:
        if not isinstance(preset, str) or preset not in _GFX_MASK_PRESETS:
            raise _gfx_err(where, f"mask must be one of {', '.join(sorted(_GFX_MASK_PRESETS))}, got {preset!r}")
        vals = dict(zip((k for k, _ in _GFX_MASK_KEYS), _GFX_MASK_PRESETS[preset]))
    for key, _ in _GFX_MASK_KEYS:
        if key in cfg:
            vals[key] = _gfx_num(cfg[key], key, where)
    return preset, [f"{ini} = {_fmt(vals[key], 3)}" for key, ini in _GFX_MASK_KEYS if key in vals]


def _gfx_shape_comment(cfg: dict) -> str:
    tp = cfg.get("trim_period")
    if isinstance(tp, str):
        return "; shape: weekly-mown suburban turf; 'a, b' pairs span TRIM_PERIOD (just cut -> a week's growth)"
    if tp is not None:
        return f"; shape: mown every {tp} days; 'a, b' pairs span TRIM_PERIOD (just cut -> {tp} days' growth)"
    return "; shape: blade size multiplier (1 = CSP default); 'a, b' pairs are a per-blade range"


def _gfx_look_lines(cfg: dict, *, where: str, top: bool, n_groups: int) -> list:
    """The look keys shared by [GRASS_FX] (``top``) and a [GRASS_FX_CONFIGURATION_X]: mask, blur,
    shape, trim period, height, then the top-only (texture_brightness, color_factor) or the
    configuration-only (texture_base_chance, texture_group_chances) tail."""
    out: list = []
    preset, mask = _gfx_mask_lines(cfg, where=where, top=top)
    if top:
        out.append(_GFX_MASK_COMMENT[preset])
    out += mask
    if "mask_blur" in cfg:
        out.append(f"MASK_BLUR = {max(0, min(3, int(_gfx_num(cfg['mask_blur'], 'mask_blur', where))))}")
    if top:
        out.append(_gfx_shape_comment(cfg))
        out.append(f"SHAPE_SIZE = {_gfx_pair(cfg.get('shape_size', 0.9), 'shape_size', where)}")
    elif "shape_size" in cfg:
        out.append(f"SHAPE_SIZE = {_gfx_pair(cfg['shape_size'], 'shape_size', where)}")
    for key, ini in _GFX_SHAPE_KEYS:
        if key in cfg:
            out.append(f"{ini} = {_gfx_pair(cfg[key], key, where)}")
    if "trim_period" in cfg:
        out.append(f"TRIM_PERIOD = {_gfx_trim(cfg['trim_period'], where)}")
    elif any(isinstance(cfg.get(k), (list, tuple)) for k in ("shape_size", "shape_width", "shape_tidy", "shape_cut")):
        print(f"  [grassfx] note{where or ' [GRASS_FX]'}: a shape key is an 'a, b' pair but trim_period is "
              "unset - pairs span TRIM_PERIOD, so CSP's default period applies")
    if "height_mult" in cfg:
        out.append(f"HEIGHT_MULT = {_gfx_pair(cfg['height_mult'], 'height_mult', where)}")
    if top:
        # shipped (fn_bahrain, Nords template, black_cat) but undocumented: passed through verbatim.
        for key, ini in (("texture_brightness", "TEXTURE_BRIGHTNESS"), ("color_factor", "COLOR_FACTOR")):
            if key in cfg:
                out.append(f"{ini} = {_gfx_pair(cfg[key], key, where)}")
    else:
        if "texture_base_chance" in cfg:
            out.append(f"TEXTURE_BASE_CHANCE = {_fmt(_gfx_num(cfg['texture_base_chance'], 'texture_base_chance', where), 3)}")
        chances = cfg.get("texture_group_chances")
        if chances is not None:
            if not isinstance(chances, (list, tuple)):
                raise _gfx_err(where, f"texture_group_chances must be a list of numbers, got {chances!r}")
            if len(chances) > n_groups:
                raise _gfx_err(where, f"texture_group_chances names {len(chances)} group(s) but only "
                                      f"{n_groups} texture_groups are defined")
            for i, c in enumerate(chances):
                out.append(f"TEXTURE_GROUP_{i}_CHANCE = {_fmt(_gfx_num(c, 'texture_group_chances', where), 3)}")
    return out


def _gfx_group_lines(groups: Any) -> list:
    """``[GRASS_FX_TEXTURE_GROUP_n]`` blocks: ``PIECE_k = col, row[, w, h]`` cells of the atlas (row 0 is
    the base blades, so rows 1+ are the meaningful ones) with optional CHANCE / SIZE_MULT / WIND."""
    if not isinstance(groups, (list, tuple)):
        raise _gfx_err(".texture_groups", f"must be a list of groups (each a list of pieces), got {groups!r}")
    if len(groups) > _GFX_MAX_GROUPS:
        raise _gfx_err(".texture_groups", f"at most {_GFX_MAX_GROUPS} groups, got {len(groups)}")
    out: list = []
    for gi, pieces in enumerate(groups):
        where = f".texture_groups[{gi}]"
        if not isinstance(pieces, (list, tuple)) or not pieces:
            raise _gfx_err(where, f"a group must be a non-empty list of pieces, got {pieces!r}")
        if len(pieces) > _GFX_MAX_PIECES:
            raise _gfx_err(where, f"at most {_GFX_MAX_PIECES} pieces per group, got {len(pieces)}")
        out.append(f"[GRASS_FX_TEXTURE_GROUP_{gi}]")
        for pi, piece in enumerate(pieces):
            pw = f"{where}[{pi}]"
            _gfx_check_keys(piece, _GFX_PIECE_KEYS, pw)
            cell = piece.get("piece")
            if not isinstance(cell, (list, tuple)) or len(cell) not in (2, 4):
                raise _gfx_err(pw, f"piece must be [col, row] or [col, row, w, h], got {cell!r}")
            out.append(f"PIECE_{pi} = {_fmt_list([_gfx_num(c, 'piece', pw) for c in cell], 3)}")
            if "chance" in piece:
                out.append(f"PIECE_{pi}_CHANCE = {_fmt(_gfx_num(piece['chance'], 'chance', pw), 3)}")
            if "size_mult" in piece:
                out.append(f"PIECE_{pi}_SIZE_MULT = {_gfx_pair(piece['size_mult'], 'size_mult', pw)}")
            if "wind" in piece:
                out.append(f"PIECE_{pi}_WIND = {_fmt(_gfx_num(piece['wind'], 'wind', pw), 3)}")
        out.append("")
    return out


def _gfx_configuration_lines(confs: Any, n_groups: int) -> list:
    if not isinstance(confs, dict):
        raise _gfx_err(".configurations", f"must be an object keyed A..D, got {confs!r}")
    out: list = []
    seen: set = set()
    for letter, body in confs.items():
        up = str(letter).upper()
        if up not in _GFX_LETTERS or up in seen:
            raise _gfx_err(".configurations", f"letter {letter!r} must be one of A..D, used once "
                                              "(dwrite.dll carries exactly CONFIGURATION_A..D)")
        seen.add(up)
        where = f".configurations[{up}]"
        _gfx_check_keys(body, _GFX_CONF_KEYS, where)
        out.append(f"[GRASS_FX_CONFIGURATION_{up}]")
        out += _gfx_look_lines(body, where=where, top=False, n_groups=n_groups)
        out.append("")
    return out


def _gfx_map(m: Any, letters: set, where: str) -> str:
    """``MAP = A`` | ``A, 0.5`` | ``0.8, 0.5, 0.2, 0`` (weights for A..D). A letter must name a
    configuration that exists."""
    toks = [t.strip() for t in str(m).split(",")]
    first = toks[0].upper()
    if first in _GFX_LETTERS:
        if first not in letters:
            raise _gfx_err(where, f"map {m!r} names configuration {first}, which is not in configurations")
        if len(toks) > 2:
            raise _gfx_err(where, f"map must be 'A' | 'A, weight' | 'wA, wB, wC, wD', got {m!r}")
        if len(toks) == 2:
            float(toks[1])
        return ", ".join([first] + toks[1:])
    try:
        ws = [float(t) for t in toks]
    except ValueError:
        raise _gfx_err(where, f"map must be 'A' | 'A, weight' | 'wA, wB, wC, wD', got {m!r}") from None
    if len(ws) > len(_GFX_LETTERS):
        raise _gfx_err(where, f"map has {len(ws)} weights; CSP has exactly {len(_GFX_LETTERS)} (A..D)")
    for w, letter in zip(ws, _GFX_LETTERS):
        if w and letter not in letters:
            raise _gfx_err(where, f"map {m!r} weights configuration {letter}, which is not in configurations")
    return ", ".join(toks)


def _gfx_adjustment_lines(adjs: Any, letters: set) -> list:
    """``[GRASS_FX_ADJUSTMENT_<name>]``: bind a configuration to materials, to meshes, or to a world
    rectangle (kn5 frame — z-mirrored vs the gate OBJ; the writer does not convert)."""
    if not isinstance(adjs, (list, tuple)):
        raise _gfx_err(".adjustments", f"must be a list, got {adjs!r}")
    out: list = []
    for i, adj in enumerate(adjs):
        where = f".adjustments[{i}]"
        _gfx_check_keys(adj, _GFX_ADJ_KEYS, where)
        targets = [k for k in ("materials", "meshes", "rect") if k in adj]
        if len(targets) != 1:
            raise _gfx_err(where, "exactly one of materials | meshes | rect is required")
        if "map" not in adj:
            raise _gfx_err(where, "map is required ('A' | 'A, 0.5' | 'wA, wB, wC, wD')")
        name = adj.get("name", "...")
        if not isinstance(name, str) or not name or "]" in name or "\n" in name:
            raise _gfx_err(where, f"name must be a plain string, got {name!r}")
        out.append(f"[GRASS_FX_ADJUSTMENT_{name}]")
        target = targets[0]
        if target == "materials":
            out.append(f"MATERIALS = {', '.join(_gfx_names(adj['materials'], 'materials', where))}")
        elif target == "meshes":
            out.append(f"MESHES = {', '.join(_gfx_names(adj['meshes'], 'meshes', where))}")
        else:
            rect = adj["rect"]
            rw = f"{where}.rect"
            _gfx_check_keys(rect, _GFX_RECT_KEYS, rw)
            center, size = rect.get("center"), rect.get("size")
            if not isinstance(center, (list, tuple)) or len(center) != 3:
                raise _gfx_err(rw, f"center must be [x, y, z] (kn5 frame), got {center!r}")
            if not isinstance(size, (list, tuple)) or len(size) != 2:
                raise _gfx_err(rw, f"size must be [w, d] metres, got {size!r}")
            out.append(f"CENTER = {_fmt_list([_gfx_num(c, 'center', rw) for c in center], 3)}")
            out.append(f"SIZE = {_fmt_list([_gfx_num(c, 'size', rw) for c in size], 3)}")
            if "angle" in rect:
                out.append(f"ANGLE = {_fmt(_gfx_num(rect['angle'], 'angle', rw), 3)}")
            if "fade" in rect:
                out.append(f"FADE = {_fmt(_gfx_num(rect['fade'], 'fade', rw), 3)}")
        out.append(f"MAP = {_gfx_map(adj['map'], letters, where)}")
        out.append("")
    return out


def grassfx_block(*, grass_meshes: Sequence[str], occluding_meshes: Sequence[str],
                  grass_materials: Optional[Sequence[str]] = None, cfg: Optional[dict] = None) -> list:
    """The GrassFX ext_config lines in the grammar every shipped CSP track config uses.

    Always: a ``[GRASS_FX]`` block binding OUR grass twice (``GRASS_MATERIALS`` = the kn5 material
    names, the key 23/23 third-party configs use; ``GRASS_MESHES`` = the mesh names, wiki-documented
    and used by CSP's own Nordschleife override), ``OCCLUDING_MESHES`` (the caller's crash-safe
    ALLOW-LIST, omitted when empty), ``ORIGINAL_GRASS_MATERIALS`` (a missing line hides every
    ksGrass object), the four ``MASK_*`` lines and ``SHAPE_SIZE``. Only when ``cfg`` asks: the atlas
    (``TEXTURE`` + ``TEXTURE_GRID``), ``MASK_BLUR``, ``SHAPE_WIDTH/TIDY/CUT``, ``TRIM_PERIOD``,
    ``HEIGHT_MULT``, ``TEXTURE_BRIGHTNESS``, ``COLOR_FACTOR``, then ``[GRASS_FX_TEXTURE_GROUP_n]``,
    ``[GRASS_FX_CONFIGURATION_A..D]`` and ``[GRASS_FX_ADJUSTMENT_...]`` blocks.

    ``cfg`` is ``lighting.grassfx`` when it is a dict (``{}`` for a bare ``true``). Keys beginning with
    ``_`` are documentation; any other unknown key — including the retired ``brightness`` / ``health``
    and ``texture = grass_fx/grass_ks.dds`` — raises ``ValueError``. Comments are own-line ``;``
    lines, ASCII only, never trailing a value. Full key table: docs/TREEFX-FORMAT.md. VERIFY IN-GAME.
    """
    cfg = dict(cfg or {})
    _gfx_check_keys(cfg, _GFX_TOP_KEYS, "")
    if cfg.get("texture") == _GFX_RETIRED_TEXTURE:
        raise _gfx_err("", f"texture {_GFX_RETIRED_TEXTURE!r} is retired (it exists nowhere); omit texture "
                           f"for CSP's built-in atlas or set {_GFX_DEFAULT_TEXTURE!r}")
    grass_meshes = _gfx_dedup(grass_meshes)
    grass_materials = _gfx_dedup(grass_materials or [f"{g}_mat" for g in grass_meshes])
    occluders = _gfx_dedup(occluding_meshes)

    out = list(_GFX_HEADER)
    out += ["[GRASS_FX]",
            f"GRASS_MATERIALS = {', '.join(grass_materials)}",
            f"GRASS_MESHES = {', '.join(grass_meshes)}"]
    if occluders:   # fn_bahrain / ks_black_cat_county ship none; never an empty 'OCCLUDING_MESHES ='
        out.append(f"OCCLUDING_MESHES = {', '.join(occluders)}")
    original = _gfx_names(cfg.get("original_grass_materials", []), "original_grass_materials")
    out.append(("ORIGINAL_GRASS_MATERIALS = " + ", ".join(original)).rstrip())

    groups = cfg.get("texture_groups") or []
    texture = cfg.get("texture")
    if texture is None and groups:
        texture = _GFX_DEFAULT_TEXTURE
        print(f"  [grassfx] note: texture_groups set without texture - defaulting to {_GFX_DEFAULT_TEXTURE} "
              f"{_GFX_DEFAULT_GRID[0]}x{_GFX_DEFAULT_GRID[1]} (the piece coordinates index that atlas)")
    if texture is not None:
        if not isinstance(texture, str) or not texture:
            raise _gfx_err("", f"texture must be a path string, got {texture!r}")
        grid = cfg.get("texture_grid", list(_GFX_DEFAULT_GRID))
        if not isinstance(grid, (list, tuple)) or len(grid) != 2:
            raise _gfx_err("", f"texture_grid must be [cols, rows], got {grid!r}")
        out.append(f"TEXTURE = {texture}")
        out.append(f"TEXTURE_GRID = {_fmt_list([_gfx_num(g, 'texture_grid') for g in grid], 3)}")
    elif "texture_grid" in cfg:
        raise _gfx_err("", "texture_grid needs texture (TEXTURE_GRID is never emitted alone)")

    out += _gfx_look_lines(cfg, where="", top=True, n_groups=len(groups))
    out.append("")
    out += _gfx_group_lines(groups)
    confs = cfg.get("configurations") or {}
    out += _gfx_configuration_lines(confs, len(groups))
    out += _gfx_adjustment_lines(cfg.get("adjustments") or [],
                                 {str(k).upper() for k in confs})
    return out


# --------------------------------------------------------------------------------------------------
# Model resolution — the gate that stops a build shipping a manifest it can't satisfy.
# --------------------------------------------------------------------------------------------------
def resolve_models(species: Iterable[str], search_dirs: Iterable) -> tuple:
    """Locate each species' ``.bin`` model. Returns ``(found, missing)`` where ``found`` maps
    ``species -> Path`` and ``missing`` is the sorted list with no file anywhere.

    ``search_dirs`` are tried in order, first hit wins — typically the project's own model dir
    (``scenery.treefx.bundle_dir``) then a shared engine-level library. A species is matched on its
    exact filename; a species declared without the ``.bin`` suffix is also tried with it, since
    ``trees.txt`` requires the suffix but configs are written both ways."""
    dirs = [Path(d) for d in search_dirs]
    found: dict = {}
    missing: list = []
    for sp in sorted(set(species)):
        names = [sp] if sp.endswith(".bin") else [sp, f"{sp}.bin"]
        hit = next((d / n for d in dirs for n in names if (d / n).is_file()), None)
        if hit is not None:
            found[sp] = hit
        else:
            missing.append(sp)
    return found, missing


# --------------------------------------------------------------------------------------------------
# extension/trees/README — what this build actually references, and where those models came from.
# --------------------------------------------------------------------------------------------------
def trees_readme(slug: str, expected_species: Sequence[str], *, bundled: bool = False) -> str:
    lines = [
        f"{slug} — TreeFX models",
        "=" * 56,
        "",
        "This track renders 3D trees via CSP TreeFX. The tree MODELS are third-party and licensed;",
        "prodrive-ac-builder never downloads or commits them. We generate only the config that",
        "REFERENCES each species by its .bin filename (trees.txt + ext_config [TREES]) — those config",
        "files are ours and license-clean.",
        "",
    ]
    if bundled:
        lines += [
            "This build BUNDLES its models: the .bin files listed below were copied into THIS folder",
            "from the project's own model dir at pack time, so the track runs as-is. That is fine for a",
            "personal build; do NOT redistribute the packaged track unless you hold the right to",
            "redistribute those models.",
        ]
    else:
        lines += [
            "This build REFERENCES its models without bundling them. PLACE the .bin files listed below",
            "in THIS folder (extension/trees/). They are gitignored (*.bin) so they never end up in a",
            "committed or published track.",
        ]
    lines += [
        "",
        "Every species listed here was VERIFIED to exist when this build was packaged — a species",
        "whose model could not be found is dropped from trees.txt entirely rather than left dangling,",
        "so this list and the config never disagree.",
        "",
        "Species referenced by this build:",
    ]
    if expected_species:
        lines += [f"  - {sp}" for sp in expected_species]
    else:
        lines.append("  (none — no TreeFX zones placed any trees)")
    lines += ["", "Format + GrassFX reference: docs/TREEFX-FORMAT.md", ""]
    return "\n".join(lines)
