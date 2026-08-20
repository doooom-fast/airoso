"""Standards lint — the machine half of fleet/STANDARDS.md.

Every check here maps to a numbered rule in that document. A check reports FAIL (a standards
violation, exit 1) or WARN (drift that is allowed to exist briefly, e.g. a repo one tag behind).
Nothing here mutates a repo — `fleet.cli pin` does that, deliberately and one repo at a time.
"""
from __future__ import annotations

from dataclasses import dataclass

from .registry import (ENGINE_ARCHETYPES, Repo, engine_modules, engine_tags,
                       latest_tag, load_registry, repos)

REQUIRED_CONFIG_KEYS = ("slug", "name", "version", "loop", "source", "location", "layouts")


@dataclass
class Finding:
    rule: str
    level: str          # FAIL | WARN
    where: str
    message: str


def check(reg: dict | None = None) -> list[Finding]:
    reg = reg or load_registry()
    rs = repos(reg)
    out: list[Finding] = []
    tags = set(engine_tags())
    newest = latest_tag()

    # ---- S1/S2/S3: the engine pin --------------------------------------------------------
    pins: dict[str, str | None] = {}
    for r in rs:
        if not r.exists:
            out.append(Finding("S0", "FAIL", r.name, f"repo not found at {r.path}"))
            continue
        if not (r.path / "bootstrap.sh").is_file():
            out.append(Finding("S1", "FAIL", r.name, "no bootstrap.sh — cannot fetch the engine"))
        if r.pin is None:
            out.append(Finding("S1", "FAIL", r.name, "no .engine-version — engine version is unpinned"))
            continue
        pins[r.name] = r.pin
        if r.pin not in tags:
            out.append(Finding("S2", "FAIL", r.name,
                               f"pin {r.pin} is not a tag in this engine repo"))
        elif newest and r.pin != newest:
            out.append(Finding("S3", "WARN", r.name,
                               f"pinned {r.pin}, engine is at {newest}"))
    distinct = {p for p in pins.values() if p}
    if len(distinct) > 1:
        out.append(Finding("S3", "FAIL", "fleet",
                           "engine pins disagree across repos: "
                           + ", ".join(f"{k}={v}" for k, v in sorted(pins.items()))
                           + " — a fix landed once does not reach every track"))

    # ---- S4: no undeclared shadowing of engine modules ------------------------------------
    engine = engine_modules()
    for r in rs:
        if not r.exists:
            continue
        allow = set(r.spec.get("local_scripts_allowlist", []))
        shadows = [m for m in r.local_scripts() if m in engine and m not in allow]
        if shadows:
            head = ", ".join(shadows[:6])
            more = f" (+{len(shadows) - 6} more)" if len(shadows) > 6 else ""
            out.append(Finding("S4", "FAIL", r.name,
                               f"{len(shadows)} local module(s) shadow the engine: {head}{more}"))

    # ---- S5/S6/S7: track configs ----------------------------------------------------------
    slugs: dict[str, str] = {}
    for r in rs:
        if not r.exists:
            continue
        for t in r.tracks():
            missing = [k for k in REQUIRED_CONFIG_KEYS if k not in t.config]
            if missing:
                out.append(Finding("S5", "FAIL", t.key, f"config missing {', '.join(missing)}"))
            if t.archetype is None:
                out.append(Finding("S6", "FAIL", t.key,
                                   "no `archetype` — construction philosophy is implicit, so the "
                                   "ARCHETYPES presets never apply"))
            elif t.archetype not in ENGINE_ARCHETYPES:
                out.append(Finding("S6", "FAIL", t.key,
                                   f"archetype '{t.archetype}' is not implemented in "
                                   f"scripts/config.py ARCHETYPES {ENGINE_ARCHETYPES}"))
            if t.slug in slugs:
                out.append(Finding("S7", "FAIL", t.key,
                                   f"slug '{t.slug}' already used by {slugs[t.slug]} — "
                                   "AC installs collide"))
            else:
                slugs[t.slug] = t.key

    # ---- S8: the build gates are wired ----------------------------------------------------
    for r in rs:
        if not r.exists:
            continue
        missing = _missing_gates(r)
        if missing:
            out.append(Finding("S8", "FAIL", r.name,
                               f"build path never runs {', '.join(missing)} — "
                               "geometry ships that no gate ever looked at"))
    return out


# The four gates the engine's own build.sh runs, in build order. A consumer that skips one is
# shipping past a check that exists and is known to catch real defects.
ENGINE_GATES = ("drive_test", "audit_mesh", "verify_kn5", "kn5_ground_check")


def _missing_gates(r: Repo) -> list[str]:
    """Gates no build script in the repo reaches. Delegating to the engine's build.sh counts as
    running all of them, since that script runs the full set itself."""
    seen: set[str] = set()
    for sh in list(r.path.glob("*.sh")) + list(r.path.glob("scripts/*.sh")):
        try:
            body = sh.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "engine/scripts/build.sh" in body:
            return []
        seen |= {g for g in ENGINE_GATES if g in body}
    return [g for g in ENGINE_GATES if g not in seen]
