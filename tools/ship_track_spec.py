"""Read and validate a track's ship.json for tools/ship_track.sh (V3-PLAN P1 "a ship chain that isn't San Diego").

``tracks/<track>/ship.json`` says WHICH steps of ship_track.sh run for that track, in what order, and which
files cross between airoso and the workshop. It never says HOW a step runs: every step name is a function
written in tools/ship_track.sh (the closed vocabulary), and ship_track.sh refuses (exit 2) a name it has no
function for. Nothing in ship.json is ever executed: this module checks every value against a strict
pattern and hands ship_track.sh plain ``key<TAB>value`` lines, which it reads into variables and arrays
(no eval, no ``bash -c``, no command substitution on a value).

Schema (unknown keys are refused, so a typo is never silently ignored):

- ``track`` (str, required): the folder name under ``tracks/``; must match the command line.
- ``workshop`` (absolute path, required): the workshop root. ship_track.sh refuses one inside airoso.
- ``workshop_project`` (name, required): the project folder inside the workshop (``project``).
- ``require_race_layout`` (bool): the chain refuses a config that declares no race layout (SD's
  three-version chain, ledger 0047).
- ``ui_name_prefix`` (str, required): the installed ``ui_track.json`` name is ``<prefix> - <layout name>``.
- ``street_ai_july`` (absolute path, optional): where ``STREET_AI=july`` copies the July AI line from (SD).
- ``audit_note`` (str, optional): printed in the street audit's step header (SD's regression floor).
- ``steps`` (required): ``{"draft": [...], "author": [...], "prep": ["prep", "split"], "ship": [...],
  "gate": [...]}``. ``draft`` = the steps ``--skip-blend`` skips (the engine draft and the scripted
  authoring that edit loop.blend); ``author`` = the steps every ship runs (layout dummies + the race
  furniture, idempotent); ``prep`` = exactly prep then split (the ``--dry-run`` stop comes after split);
  ``ship`` = exports, AI, packer, map, trees; ``gate`` = the gates on the built kn5.
- ``sync_in`` : ``{"required": [...], "optional": [...], "globs": [...], "dirs": [...], "assets": [...]}`` paths
  relative to ``tracks/<track>/`` copied into the workshop project before the chain runs. ``assets`` alone is
  relative to airoso's root and must lie under ``assets/``: each file is copied to the SAME relative path in the
  project, every one required (Lake Murray v4's house textures, ledger 0065: a config ``texture_overrides`` path
  ``assets/textures/<f>`` resolves to the engine's own file first and to the project's copy when the engine lacks it).
- ``sync_out``: ``{"required": [...], "files": [...], "map": [[from, to], ...], "dirs": [...], "remove": [...]}``
  paths relative to the workshop project copied back into ``tracks/<track>/`` after the gates (the real
  workshop only). ``{id}`` expands to every layout id, ``{race}`` to every race layout id.
- keys starting with ``_`` are documentation and are ignored.

Exit 0 with the lines on stdout; exit 2 with the reason on stderr.

    python tools/ship_track_spec.py <ship.json> <track>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PHASES = ("draft", "author", "prep", "ship", "gate")
STEP_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
TRACK_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# a relative path: plain segments, optional {id} / {race} templates, a '*' only in globs
REL_RE = re.compile(r"^[A-Za-z0-9_.{}-]+(/[A-Za-z0-9_.{}-]+)*$")
GLOB_RE = re.compile(r"^[A-Za-z0-9_.{}-]+(/[A-Za-z0-9_.{}-]+)*/[A-Za-z0-9_.-]*\*[A-Za-z0-9_.-]*$")
ABS_RE = re.compile(r"^[A-Za-z]:/[A-Za-z0-9_. /()-]*$")
TEXT_RE = re.compile(r"^[^\t\r\n\x00-\x1f]{0,240}$")
TOP = {"track", "workshop", "workshop_project", "require_race_layout", "ui_name_prefix", "street_ai_july",
       "audit_note", "steps", "sync_in", "sync_out"}
SYNC_IN = {"required", "optional", "globs", "dirs", "assets"}
SYNC_OUT = {"required", "files", "map", "dirs", "remove"}


class SpecError(Exception):
    pass


def _rel(p, what, glob=False):
    if not isinstance(p, str) or not (GLOB_RE if glob else REL_RE).match(p):
        raise SpecError(f"{what}: {p!r} is not a plain relative path")
    if any(seg in (".", "..") for seg in p.split("/")):
        raise SpecError(f"{what}: {p!r} climbs out of its folder")
    for t in re.findall(r"\{([^}]*)\}", p):
        if t not in ("id", "race"):
            raise SpecError(f"{what}: {p!r} has an unknown template {{{t}}} (only {{id}} and {{race}})")
    return p


def _abs(p, what):
    if not isinstance(p, str) or not ABS_RE.match(p) or ".." in p.split("/"):
        raise SpecError(f"{what}: {p!r} is not an absolute Windows path (C:/...)")
    return p.rstrip("/")


def _text(s, what):
    if not isinstance(s, str) or not TEXT_RE.match(s):
        raise SpecError(f"{what}: {s!r} must be one line of printable text (<= 240 chars)")
    return s


def _list(d, key, what):
    v = d.get(key, [])
    if not isinstance(v, list):
        raise SpecError(f"{what}.{key} must be a list")
    return v


def load(path, track: str) -> dict:
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"cannot read {path}: {e}")
    if not isinstance(spec, dict):
        raise SpecError("ship.json must be an object")
    unknown = sorted(k for k in spec if not k.startswith("_") and k not in TOP)
    if unknown:
        raise SpecError(f"unknown key(s) {unknown} (known: {sorted(TOP)})")
    if not isinstance(track, str) or not TRACK_RE.match(track):
        raise SpecError(f"track {track!r} is not a track folder name")
    if spec.get("track") != track:
        raise SpecError(f"ship.json is for track {spec.get('track')!r}, not {track!r}")
    out = {"track": track,
           "workshop": _abs(spec.get("workshop"), "workshop"),
           "workshop_project": spec.get("workshop_project"),
           "require_race_layout": spec.get("require_race_layout", False),
           "ui_name_prefix": _text(spec.get("ui_name_prefix"), "ui_name_prefix"),
           "audit_note": _text(spec.get("audit_note", ""), "audit_note"),
           "street_ai_july": _abs(spec["street_ai_july"], "street_ai_july") if spec.get("street_ai_july") else ""}
    if not isinstance(out["workshop_project"], str) or not NAME_RE.match(out["workshop_project"]) \
            or out["workshop_project"] in (".", ".."):
        raise SpecError(f"workshop_project {out['workshop_project']!r} must be one folder name")
    if not isinstance(out["require_race_layout"], bool):
        raise SpecError("require_race_layout must be true or false")
    steps = spec.get("steps")
    if not isinstance(steps, dict):
        raise SpecError("steps must be an object of phase -> [step, ...]")
    bad = sorted(k for k in steps if not k.startswith("_") and k not in PHASES)
    if bad:
        raise SpecError(f"steps: unknown phase(s) {bad} (phases: {list(PHASES)})")
    out["steps"] = {}
    for ph in PHASES:
        names = steps.get(ph, [])
        if not isinstance(names, list):
            raise SpecError(f"steps.{ph} must be a list")
        for n in names:
            if not isinstance(n, str) or not STEP_RE.match(n):
                raise SpecError(f"steps.{ph}: {n!r} is not a step name (closed vocabulary: lower_snake names "
                                "of functions in tools/ship_track.sh)")
        out["steps"][ph] = names
    if out["steps"]["prep"] != ["prep", "split"]:
        raise SpecError(f"steps.prep must be exactly [\"prep\", \"split\"] (the --dry-run stop follows the "
                        f"split), got {out['steps']['prep']}")
    si = spec.get("sync_in") or {}
    so = spec.get("sync_out") or {}
    for d, known, what in ((si, SYNC_IN, "sync_in"), (so, SYNC_OUT, "sync_out")):
        if not isinstance(d, dict):
            raise SpecError(f"{what} must be an object")
        bad = sorted(k for k in d if not k.startswith("_") and k not in known)
        if bad:
            raise SpecError(f"{what}: unknown key(s) {bad} (known: {sorted(known)})")
    out["sync_in"] = {"required": [_rel(p, "sync_in.required") for p in _list(si, "required", "sync_in")],
                      "optional": [_rel(p, "sync_in.optional") for p in _list(si, "optional", "sync_in")],
                      "globs": [_rel(p, "sync_in.globs", glob=True) for p in _list(si, "globs", "sync_in")],
                      "dirs": [_rel(p, "sync_in.dirs") for p in _list(si, "dirs", "sync_in")],
                      "assets": [_rel(p, "sync_in.assets") for p in _list(si, "assets", "sync_in")]}
    for p in out["sync_in"]["assets"]:
        if not p.startswith("assets/"):
            raise SpecError(f"sync_in.assets: {p!r} is not under airoso's assets/")
    for k in ("required", "optional", "dirs", "assets"):
        for p in out["sync_in"][k]:
            if "{" in p:
                raise SpecError(f"sync_in.{k}: {p!r}: templates are for sync_out only")
    maps = []
    for m in _list(so, "map", "sync_out"):
        if not (isinstance(m, list) and len(m) == 2):
            raise SpecError(f"sync_out.map: {m!r} must be [from, to]")
        maps.append([_rel(m[0], "sync_out.map"), _rel(m[1], "sync_out.map")])
    out["sync_out"] = {"required": [_rel(p, "sync_out.required") for p in _list(so, "required", "sync_out")],
                       "files": [_rel(p, "sync_out.files") for p in _list(so, "files", "sync_out")],
                       "map": maps,
                       "dirs": [_rel(p, "sync_out.dirs") for p in _list(so, "dirs", "sync_out")],
                       "remove": [_rel(p, "sync_out.remove") for p in _list(so, "remove", "sync_out")]}
    return out


def lines(spec: dict) -> list[str]:
    """the key<TAB>value lines ship_track.sh reads (one value per line; lists repeat their key)"""
    out = [f"workshop\t{spec['workshop']}", f"workshop_project\t{spec['workshop_project']}",
           f"require_race_layout\t{1 if spec['require_race_layout'] else 0}",
           f"ui_name_prefix\t{spec['ui_name_prefix']}", f"audit_note\t{spec['audit_note']}",
           f"street_ai_july\t{spec['street_ai_july']}"]
    for ph in PHASES:
        out += [f"step.{ph}\t{n}" for n in spec["steps"][ph]]
    for k in ("required", "optional", "globs", "dirs", "assets"):
        out += [f"in.{k}\t{p}" for p in spec["sync_in"][k]]
    for k in ("required", "files", "dirs", "remove"):
        out += [f"out.{k}\t{p}" for p in spec["sync_out"][k]]
    out += [f"out.map\t{a}\t{b}" for a, b in spec["sync_out"]["map"]]
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: ship_track_spec.py <ship.json> <track>", file=sys.stderr)
        return 2
    try:
        spec = load(argv[0], argv[1])
    except SpecError as e:
        print(f"ship.json: {e}", file=sys.stderr)
        return 2
    # bytes, LF only: Windows text mode would end every line in CR LF and the CR would ride into bash's values
    sys.stdout.buffer.write(("\n".join(lines(spec)) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
