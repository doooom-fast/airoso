"""The Blender seam (fleet/REALISM.md §4): the engine's draft goes INTO an editable .blend, and the
authored .blend comes back out through the prep (scripts/ac/build_kn5_loop.py) and the exporter.

- ``underlay``: the data underlay — data/track.obj (the engine's own draft: road, kerbs, verge, ground)
  into loop.blend as ``GEN_*`` collections, beside and never through anything ``AUTH_*``.

Everything here runs inside Blender 4.2 (``blender --background --python <file> -- <project>``) or under
the ``bpy`` module; the parsing, frame and planning functions have no bpy dependency so they are
unit-tested on any machine.
"""
