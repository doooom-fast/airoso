"""Load the registry and DISCOVER the fleet from it.

Repos are declared in ``fleet/registry.json``; tracks are found by scanning each repo's
``tracks_glob``, so adding a track to a project repo needs no edit here. Everything below is
stdlib-only (same constraint as the engine — system python3, no numpy).
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "fleet" / "registry.json"

# The archetypes the engine actually implements (scripts/config.py ARCHETYPES). `rally_stage` is
# proposed but NOT in that table — lint must not pretend otherwise.
ENGINE_ARCHETYPES = ("real_road", "street_circuit", "race_circuit")


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo``; return stripped stdout, or '' if the command fails."""
    try:
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


@dataclass
class Track:
    repo: str
    dirname: str
    config_path: Path
    config: dict
    annotation: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.repo}/{self.dirname}"

    @property
    def slug(self) -> str:
        return self.config.get("slug", "?")

    @property
    def kind(self) -> str:
        return self.annotation.get("kind", "?")

    @property
    def archetype(self) -> str | None:
        return self.config.get("archetype")

    @property
    def project_dir(self) -> Path:
        return self.config_path.parent


@dataclass
class Repo:
    name: str
    path: Path
    spec: dict
    exists: bool

    @property
    def pin(self) -> str | None:
        f = self.path / ".engine-version"
        return f.read_text(encoding="utf-8").strip() if f.is_file() else None

    @property
    def branch(self) -> str:
        return git(self.path, "branch", "--show-current")

    @property
    def dirty(self) -> bool:
        return bool(git(self.path, "status", "--porcelain"))

    @property
    def head(self) -> str:
        return git(self.path, "log", "--oneline", "-1")

    def tracks(self) -> list[Track]:
        found: list[Track] = []
        ann = load_registry().get("track_annotations", {})
        for cfg in sorted(self.path.glob(self.spec["tracks_glob"])):
            if ".claude/worktrees" in str(cfg):        # worktrees are scratch copies, not the fleet
                continue
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            dirname = cfg.parent.name
            found.append(Track(self.name, dirname, cfg, data,
                               ann.get(f"{self.name}/{dirname}", {})))
        return found

    def local_scripts(self) -> list[str]:
        """Repo-local python modules under scripts/, as paths relative to the repo."""
        d = self.path / "scripts"
        if not d.is_dir():
            return []
        return sorted(str(p.relative_to(self.path)) for p in d.rglob("*.py"))


def engine_modules() -> set[str]:
    """Every engine module, as 'scripts/<pkg>/<mod>.py' — the shadowing comparison set."""
    return {str(p.relative_to(ROOT)) for p in (ROOT / "scripts").rglob("*.py")}


def engine_tags() -> list[str]:
    """Engine version tags, oldest → newest by semver."""
    raw = [t for t in git(ROOT, "tag").splitlines() if t.startswith("v")]

    def key(t: str) -> tuple:
        try:
            return tuple(int(x) for x in t[1:].split("."))
        except ValueError:
            return (0,)

    return sorted(raw, key=key)


def latest_tag() -> str | None:
    tags = engine_tags()
    return tags[-1] if tags else None


def repos(reg: dict | None = None) -> list[Repo]:
    reg = reg or load_registry()
    out = []
    for spec in reg["repos"]:
        p = (ROOT / spec["path"]).resolve()
        out.append(Repo(spec["name"], p, spec, p.is_dir()))
    return out


def all_tracks() -> list[Track]:
    return [t for r in repos() if r.exists for t in r.tracks()]
