"""Aerial measurement helpers for ``tools/aerial_measure.py`` (Lookout Lariat V3, ledger 0048).

Ported 2026-10-11 from the aerial pass's session-scratch scripts (``lariat2/v2`` + ``lariat2/lib``) so
``tracks/lookout-lariat/data/aerial/aerial_measurements.json`` reproduces from the repo. Pure Python +
Pillow. Every coordinate in this package is one of three frames, always named:

- **imagery frame**: NAD83 / UTM zone 13N metres (EPSG:26913), the NAIP quarter-quads' own projection,
  in which every window is requested and every measurement is made (``geo.to_utm`` / ``geo.from_utm``,
  GRS80 Krueger series);
- **OSM frame**: WGS84 lon/lat as OpenStreetMap, ``data/centerline.geojson`` and ``track.config.json``
  carry them. Imagery points are moved into it by the measured OSM-minus-imagery offset (registration);
- **plan / engine frame**: local ENU metres about a centreline centroid (``scripts/geometry/projection``'s
  metres-per-degree series). Lap stations are metres from geojson v0 in a plan frame.

Modules: ``geo`` (UTM, circle fits), ``naip`` (TLS-verified window fetch + pixel access), ``lap`` (the
centreline + OSM ways), ``profile`` (paint and pavement-edge tracing on profiles), ``circles`` (robust,
concentric and line fits), ``corners`` (hairpin cores), ``junction`` (kerb-return fillets), ``widths``,
``registration``, ``crossings`` (C-470 decks), ``overlay`` (pictures), ``traces`` (paint_traces.json) and
``report`` (aerial_measurements.json).
"""
