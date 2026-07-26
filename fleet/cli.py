"""The fleet CLI — one command to see and drive every track in the fleet.

    python3 -m fleet.cli status            # repos: branch, dirt, engine pin, drift
    python3 -m fleet.cli tracks            # every track, its kind, archetype, version
    python3 -m fleet.cli lint              # standards check (exit 1 on any FAIL)
    python3 -m fleet.cli pin v0.20.0       # rewrite every .engine-version (use --repo to narrow)
    python3 -m fleet.cli build             # print the build command for each selected track
    python3 -m fleet.cli build --run --kind rally_stage --from mesh
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from . import lint as lintmod
from .registry import ROOT, all_tracks, latest_tag, load_registry, repos


def _c(s: str, code: str) -> str:
    return s if not sys.stdout.isatty() else f"\033[{code}m{s}\033[0m"


RED, YEL, GRN, DIM = "31", "33", "32", "2"


# ---------------------------------------------------------------- status
def cmd_status(args) -> int:
    reg = load_registry()
    newest = latest_tag()
    eng = reg["engine"]
    print(f"engine   {eng['name']}  latest tag {newest or '(none)'}")
    absorbed = eng.get("absorbed_from", {})
    if absorbed:
        print(_c(f"         absorbed {absorbed['repo']} @ {absorbed['at_commit']} — "
                 f"{absorbed['status']}", DIM))
    print()
    for r in repos(reg):
        if not r.exists:
            print(f"{r.name:20} {_c('MISSING', RED)}  {r.path}")
            continue
        pin = r.pin or "-"
        flag = ""
        if newest and pin != newest:
            flag = _c(f"  (engine {newest})", YEL)
        dirt = _c("  dirty", YEL) if r.dirty else ""
        n = len(r.tracks())
        print(f"{r.name:20} pin {pin:9}{flag}  {r.branch or '?':22} {n} tracks{dirt}")
        print(_c(f"{'':20} {r.head}", DIM))
    return 0


# ---------------------------------------------------------------- tracks
def cmd_tracks(args) -> int:
    rows = _select(args)
    if not rows:
        print("no tracks match")
        return 0
    w = max(len(t.key) for t in rows)
    print(f"{'TRACK'.ljust(w)}  {'KIND':26} {'ARCHETYPE':15} {'VER':8} {'LOOP':5} SLUG")
    for t in rows:
        arch = t.archetype or _c("(none)", RED)
        pad = 15 + (len(arch) - len(t.archetype or "(none)"))
        loop = "loop" if t.config.get("loop") else "p2p"
        fid = t.annotation.get("fidelity", "")
        line = (f"{t.key.ljust(w)}  {t.kind:26} {arch:<{pad}} "
                f"{str(t.config.get('version', '?')):8} {loop:5} {t.slug}")
        if fid.startswith("FABRICATED"):
            line += _c("   FABRICATED GEOMETRY", RED)
        if t.annotation.get("status", "").startswith("RETIRED"):
            line += _c("   retired", DIM)
        print(line)
    print(f"\n{len(rows)} tracks")
    return 0


# ---------------------------------------------------------------- lint
def cmd_lint(args) -> int:
    findings = lintmod.check()
    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    for f in findings:
        tag = _c(f.level, RED if f.level == "FAIL" else YEL)
        print(f"{tag:>16} {f.rule:4} {f.where:34} {f.message}")
    if not findings:
        print(_c("clean — every repo conforms to fleet/STANDARDS.md", GRN))
    else:
        print(f"\n{len(fails)} FAIL, {len(warns)} WARN  (rules: fleet/STANDARDS.md)")
    return 1 if fails else 0


# ---------------------------------------------------------------- feedback
STATUS_ORDER = ["open", "diagnosed", "in-train", "shipped", "rejected"]


def _parse_entry(path):
    """Pull the --- header off a ledger entry. Returns {} if it has none."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    head = text.split("---", 2)[1]
    out = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def cmd_feedback(args) -> int:
    entries = []
    for f in sorted((ROOT / "fleet" / "feedback").glob("[0-9]*.md")):
        h = _parse_entry(f)
        if h:
            entries.append((h, f))
    if args.status:
        entries = [e for e in entries if e[0].get("status") == args.status]
    entries.sort(key=lambda e: (STATUS_ORDER.index(e[0].get("status", "open"))
                                if e[0].get("status") in STATUS_ORDER else 9,
                                e[0].get("id", "")))
    for h, f in entries:
        st = h.get("status", "?")
        colour = {"open": YEL, "diagnosed": YEL, "shipped": GRN}.get(st, DIM)
        train = h.get("train", "-")
        print(f"  {h.get('id', '????')}  {_c(st.ljust(10), colour)} "
              f"{('train ' + train) if train != '-' else '':10} "
              f"{h.get('layer', '?'):9} {h.get('title', f.stem)}")
        print(_c(f"        {h.get('scope', '')}", DIM))
    if not entries:
        print("  (no entries)")
        return 0
    counts = {}
    for h, _ in entries:
        counts[h.get("status", "?")] = counts.get(h.get("status", "?"), 0) + 1
    print("\n  " + "  ".join(f"{v} {k}" for k, v in counts.items())
          + "   — fleet/feedback/README.md")
    return 0


# ---------------------------------------------------------------- pin
def cmd_pin(args) -> int:
    tag = args.tag
    if tag not in set(lintmod.engine_tags()):
        print(f"{tag} is not a tag in this engine repo", file=sys.stderr)
        return 1
    for r in repos():
        if not r.exists or (args.repo and r.name != args.repo):
            continue
        f = r.path / ".engine-version"
        old = r.pin
        if old == tag:
            print(f"{r.name:20} already {tag}")
            continue
        if args.dry_run:
            print(f"{r.name:20} {old} -> {tag}  (dry run)")
            continue
        f.write_text(tag + "\n", encoding="utf-8")
        print(f"{r.name:20} {old} -> {tag}")
    if args.dry_run:
        print("\nnothing written — drop --dry-run to apply, then run ./bootstrap.sh in each repo")
    else:
        print("\nnow run ./bootstrap.sh in each repo, then: python3 -m fleet.cli build --run")
    return 0


# ---------------------------------------------------------------- build
def cmd_build(args) -> int:
    reg = load_registry()
    by_name = {r["name"]: r for r in reg["repos"]}
    rows = _select(args)
    rc = 0
    results = []
    for t in rows:
        spec = by_name[t.repo]["build"]
        repo_path = (ROOT / by_name[t.repo]["path"]).resolve()
        cmd = [spec["cmd"], str(t.project_dir.relative_to(repo_path))]
        if args.from_stage:
            cmd.append(args.from_stage)
        shown = f"(cd {repo_path.name} && {' '.join(cmd)})"
        if not args.run:
            print(shown)
            continue
        print(f"\n━━━━ {t.key}  {shown}")
        p = subprocess.run(cmd, cwd=repo_path)
        results.append((t.key, p.returncode))
        rc |= 1 if p.returncode else 0
    if results:
        print("\n---- build matrix")
        for k, code in results:
            print(f"  {_c('PASS', GRN) if code == 0 else _c('FAIL', RED)}  {k}"
                  + (f"  (exit {code})" if code else ""))
    elif not args.run:
        print(f"\n{len(rows)} tracks — add --run to execute")
    return rc


# ---------------------------------------------------------------- selection
def _select(args):
    rows = all_tracks()
    if getattr(args, "repo", None):
        rows = [t for t in rows if t.repo == args.repo]
    if getattr(args, "kind", None):
        rows = [t for t in rows if t.kind == args.kind]
    if getattr(args, "track", None):
        rows = [t for t in rows if args.track in t.key or args.track == t.slug]
    if not getattr(args, "all", False):
        rows = [t for t in rows if not t.annotation.get("status", "").startswith("RETIRED")]
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fleet", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def sel(sp):
        sp.add_argument("--repo", help="limit to one repo")
        sp.add_argument("--kind", help="limit to one kind (see registry.kinds)")
        sp.add_argument("--track", help="substring of <repo>/<dir>, or an exact slug")
        sp.add_argument("--all", action="store_true", help="include retired tracks")
        return sp

    sub.add_parser("status", help="repos, pins, drift").set_defaults(fn=cmd_status)
    sel(sub.add_parser("tracks", help="every track in the fleet")).set_defaults(fn=cmd_tracks)
    sub.add_parser("lint", help="standards check").set_defaults(fn=cmd_lint)

    sp = sub.add_parser("feedback", help="the feedback ledger")
    sp.add_argument("--status", choices=STATUS_ORDER)
    sp.set_defaults(fn=cmd_feedback)

    sp = sub.add_parser("pin", help="set .engine-version across repos")
    sp.add_argument("tag")
    sp.add_argument("--repo")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(fn=cmd_pin)

    sp = sel(sub.add_parser("build", help="build selected tracks"))
    sp.add_argument("--run", action="store_true", help="actually execute (default: print)")
    sp.add_argument("--from", dest="from_stage", help="resume from a stage, e.g. mesh")
    sp.set_defaults(fn=cmd_build)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
