"""The fleet control plane — registry, standards lint, and cross-repo build orchestration.

The ENGINE lives in ``scripts/`` (import paths unchanged from prodrive-ac-builder, so a consumer
repo's ``(cd .engine && python3 -m scripts.<pkg>.<mod>)`` keeps working). This package is the layer
ABOVE it: what repos exist, what tracks they own, whether they conform, and how a change reaches
all of them.
"""
