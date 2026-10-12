"""Blender-side engine tools (fleet/REALISM.md §4). Each module here runs INSIDE Blender (`blender --background
--python-exit-code 1 --python scripts/blender/<tool>.py -- ...`); importing one outside Blender fails on `bpy`."""
