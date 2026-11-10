"""The aerial reading stage (ledger 0088): orthophoto + optional lidar + optional published map(s) + optional hand
sketch -> measured pieces and layouts. Opt-in: nothing in an existing build path imports it.

    python -m scripts.aerial.engine <engine.json | project-dir> [--out DIR] [--layout ID ...]

Kevin, 2026-11-07, while Pikes Peak's infield was traced badly three times: "Follow curbs and road wear, it's easy for
human eye", "Why aren't you using actual track maps?", "Stop guessing", "I feel like this should be handled by the
engine by now". This package is that engine stage. Its rules (the skill `.claude/skills/aerial-tracing/SKILL.md`):

  - the route comes from published maps (similarity fit + handedness check), then a hand sketch as a SHAPE aid, then the
    dark driven band; never a point placed by eye;
  - every coordinate is measured: pavement edges at the sub-pixel boundary, kerbs and painted edge lines first, robust
    curvature-limited fits with residuals and inferred stretches logged;
  - the aerial is registered to lidar-measured features where they exist, and the offset is reported;
  - the CRS comes from the image's own metadata (GeoTIFF tags, a crop sidecar, a tile georeference), never a constant;
  - stills are clean: one line on the band, light tint, nothing else lit.

Modules: ``ortho`` (georeference + local frame), ``channels`` (pavement / kerb / line / wear scores), ``register``
(aerial against lidar), ``edges`` (edge finding + fits), ``kerbs`` (colour and block kerb readers), ``maps``
(published-map registration and course line), ``band`` (the driven dark band on open pavement), ``route`` (route line
-> guide through the pavement), ``network`` (pieces and layouts), ``emit`` (engine-intake files), ``stills``,
``run`` (the orchestrator), ``config`` (the per-track data file).
"""
