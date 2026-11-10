"""tools/ac_tidy.py — keep Assetto Corsa's content/tracks clean and up to date.

Kevin 2026-11-06: "we need a routine on the PC that keeps AC clean and up-to-date. there are many versions in there,
both k10 still and doooom versions".

What it does (a dry run unless --apply / --rename is given):

  1. Inventory: every folder in content/tracks; for ours (manifest entry, a doooom / airoso / k10 author, or a doooom /
     K10 name) each layout's ui_track.json name + version, the folder's size and last-modified time.
  2. Classify each folder against the manifest `fleet/ac-installed.json` (the record every install updates):
       current     the build Kevin last installed for that track
       kept        an older copy Kevin chose to keep beside its successor (e.g. for comparison)
       superseded  an older copy whose successor is installed (manifest role; an unlisted `<folder>` beside an
                   installed `<folder>_lm`; an unlisted `<folder>_lm` beside a current plain `<folder>`)
       k10-era     a k10 build (K10 name / k10 author) with no manifest entry, or the manifest says so
       unlisted    ours, not in the manifest, no successor found: reported, never planned
       not-ours    Kunos and third-party tracks: counted, NEVER touched
  3. Flags on current folders: `version-drift` (installed version != manifest), `old-name` (a layout name still
     carries the manifest's `old_name_prefix`, e.g. LM v4's "K10 - San Diego CANDIDATE v4 keep-roads"), `newer` (the
     track's track.config.json on origin/<branch> has a higher version than installed: an OFFER, installs stay on
     Kevin's word), `missing` (a current manifest folder that is not in AC).
  4. The plan = every superseded / k10-era folder. `--apply --only a,b` (or `--all`) MOVES them to
     <archive>/<stamp>_tidy/ with a MOVES.tsv beside them, the way ship_track.sh parks old installs. Nothing is ever
     deleted; `restore <tidy dir>` moves them back. `--rename` rewrites the old-name prefix in ui_track.json "name"
     fields (the originals copied into the tidy dir first). Both refuse while acs.exe is running (Content Manager open
     is fine, Kevin 2026-10-27).

  python tools/ac_tidy.py                        # dry run: inventory, classes, flags, plan
  python tools/ac_tidy.py --fetch --json inv.json
  python tools/ac_tidy.py --apply --only high_plains,aspen_motorsports_park
  python tools/ac_tidy.py --rename --only san_diego_lake_murray_v4
  python tools/ac_tidy.py restore D:/k10-track-archive/2026-11-06_120000_tidy

Installs REPLACE (Kevin 2026-11-07: "We want to delete old copies from ac when installing new ones"): every folder
is a copy of one track, its `family` (the manifest's `family`, else the track slug without a trailing `-lm`).
`record`ing an install marks every other folder of that family superseded, so the next dry run plans their move
(old engine, `_lm`, an older plain folder alike); the install question lists them and `--apply --only` moves them.
  python tools/ac_tidy.py record san_diego_freeway_lm --track san-diego-freeway-lm --branch claude/freeway-lm \
      --sha e733c0a9 [--engine lm-v4] [--date YYYY-MM-DD]          # after an install: the manifest entry from the installed folder
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fleet" / "ac-installed.json"
PLANNED = ("superseded", "k10-era")


# ---------------------------------------------------------------- reading AC

def read_json_lenient(p: Path):
    """ui_track.json files in the wild carry BOMs, stray control characters and bad bytes: read what can be read."""
    try:
        return json.loads(p.read_text(encoding="utf-8-sig", errors="replace"), strict=False)
    except Exception:
        return None


def layouts(folder: Path) -> list[dict]:
    """each layout's ui_track.json (the single-layout ui/ui_track.json, or ui/<layout>/ui_track.json)"""
    out = []
    files = [folder / "ui" / "ui_track.json"] + sorted((folder / "ui").glob("*/ui_track.json"))
    for p in files:
        if not p.is_file():
            continue
        d = read_json_lenient(p) or {}
        layout = "" if p.parent.name == "ui" else p.parent.name
        out.append({"layout": layout, "file": str(p.relative_to(folder)).replace("\\", "/"),
                    "name": d.get("name"), "version": d.get("version"), "author": d.get("author")})
    return out


def folder_size(folder: Path) -> int:
    total = 0
    for dp, _dn, fn in os.walk(folder):
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def is_ours(lays: list[dict], ours: dict) -> bool:
    authors = {a.lower() for a in ours.get("authors", [])}
    prefixes = tuple(ours.get("name_prefixes", []))
    for l in lays:
        if str(l.get("author") or "").lower() in authors:
            return True
        if prefixes and str(l.get("name") or "").startswith(prefixes):
            return True
    return False


def is_k10(lays: list[dict]) -> bool:
    return any(str(l.get("name") or "").startswith("K10") or str(l.get("author") or "").lower().startswith("k10")
               for l in lays)


def vkey(v) -> tuple:
    """'0.20.2' -> (0, 20, 2); anything unparsable sorts first"""
    nums = re.findall(r"\d+", str(v or ""))
    return tuple(int(n) for n in nums) if nums else (-1,)


def installed_version(lays: list[dict]):
    vs = sorted({str(l["version"]) for l in lays if l.get("version") is not None}, key=vkey)
    return vs[-1] if vs else None


# ---------------------------------------------------------------- git (the "up to date" check)

def branch_version(branch: str, track: str, repo: Path = ROOT):
    """the track's track.config.json version at origin/<branch>, or None (branch / track not on origin)"""
    r = subprocess.run(["git", "-C", str(repo), "show", f"origin/{branch}:tracks/{track}/track.config.json"],
                       capture_output=True)
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout.decode("utf-8-sig")).get("version")
    except Exception:
        return None


def acs_running() -> bool:
    if os.name != "nt":
        return False
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/NH"], capture_output=True, text=True)
    return "acs.exe" in r.stdout.lower()


# ---------------------------------------------------------------- classify

def inventory(man: dict, ac: Path, bv_fn=None, sizes: bool = True) -> dict:
    bv_fn = bv_fn or branch_version
    entries = man.get("folders", {})
    ours_rule = man.get("ours", {})
    present = sorted(p.name for p in ac.iterdir() if p.is_dir())
    rows = []
    for name in present:
        f = ac / name
        lays = layouts(f)
        ent = entries.get(name)
        ours = ent is not None or is_ours(lays, ours_rule)
        row = {"folder": name, "ours": ours}
        if not ours:
            row["class"] = "not-ours"
            rows.append(row)
            continue
        ver = installed_version(lays)
        st = f.stat()
        row.update({"layouts": lays, "version": ver,
                    "modified": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "size": folder_size(f) if sizes else None, "flags": []})
        if ent:
            row["track"] = ent.get("track")
            row["engine"] = ent.get("engine")
            role = ent.get("role", "current")
            row["class"] = role if role in ("current", "kept", "superseded", "k10-era") else "unlisted"
            if ent.get("successor"):
                row["successor"] = ent["successor"]
            if row["class"] == "current":
                if ent.get("version") and ver and str(ent["version"]) != str(ver):
                    row["flags"].append(f"version-drift (manifest {ent['version']}, installed {ver})")
                old = ent.get("old_name_prefix")
                if old and any(str(l.get("name") or "").startswith(old) for l in lays):
                    row["flags"].append(f"old-name ('{old}' -> '{ent.get('ui_name_prefix')}')")
                if ent.get("branch") and ent.get("track"):
                    bv = bv_fn(ent["branch"], ent["track"])
                    row["branch_version"] = bv
                    if bv is None:
                        row["flags"].append(f"no tracks/{ent['track']} on origin/{ent['branch']} (yet)")
                    elif ver is not None and vkey(bv) > vkey(ver):
                        row["flags"].append(f"newer ({bv} on origin/{ent['branch']}; install on Kevin's word)")
        elif (ac / f"{name}_lm").is_dir():
            row["class"], row["successor"] = "superseded", f"{name}_lm"
        elif name.endswith("_lm") and entries.get(name[:-3], {}).get("role", "current") == "current" and name[:-3] in entries:
            row["class"], row["successor"] = "superseded", name[:-3]
        elif is_k10(lays):
            row["class"] = "k10-era"
        else:
            row["class"] = "unlisted"
        rows.append(row)
    missing = [n for n, e in entries.items() if e.get("role", "current") == "current" and n not in present]
    return {"ac_tracks": str(ac), "rows": rows, "missing": missing}


def plan_of(inv: dict) -> list[dict]:
    return [r for r in inv["rows"] if r["class"] in PLANNED]


def renames_of(inv: dict, man: dict) -> list[dict]:
    return [r for r in inv["rows"] if r["class"] == "current" and any(x.startswith("old-name") for x in r["flags"])]


# ---------------------------------------------------------------- report

def mb(n) -> str:
    return "-" if n is None else f"{n / 1e6:,.0f} MB"


def report(inv: dict, man: dict, dry: bool = True) -> str:
    rows = inv["rows"]
    order = ["current", "kept", "superseded", "k10-era", "unlisted"]
    out = [f"AC tracks: {inv['ac_tracks']}  ({len(rows)} folders)"]
    for cls in order:
        sel = [r for r in rows if r["class"] == cls]
        if not sel:
            continue
        out.append(f"\n{cls} ({len(sel)}, {mb(sum(r['size'] or 0 for r in sel))})")
        for r in sel:
            names = sorted({str(l.get('name')) for l in r["layouts"]})
            extra = f"  -> {r['successor']}" if r.get("successor") else ""
            out.append(f"  {r['folder']:<40} {str(r['version']):<8} {mb(r['size']):>9}  {r['modified']}{extra}")
            out.append(f"      {names[0]}" + (f"  (+{len(names) - 1} layouts)" if len(names) > 1 else ""))
            for fl in r["flags"]:
                out.append(f"      FLAG {fl}")
    nn = sum(1 for r in rows if r["class"] == "not-ours")
    out.append(f"\nnot-ours ({nn}): Kunos and third-party, never touched")
    for m in inv["missing"]:
        out.append(f"MISSING: manifest says {m} is installed; it is not in AC")
    pl = plan_of(inv)
    out.append(f"\nPLAN: move {len(pl)} folders ({mb(sum(r['size'] or 0 for r in pl))}) to "
               f"{man.get('archive', 'D:/k10-track-archive')}/<stamp>_tidy/" + (" (dry run: nothing moved)" if dry else ""))
    for r in pl:
        out.append(f"  move {r['folder']}")
    for r in renames_of(inv, man):
        out.append(f"  rename offered: {r['folder']} (--rename)")
    return "\n".join(out)


# ---------------------------------------------------------------- act

def pick(cands: list[dict], only: str | None, all_: bool) -> list[dict]:
    if all_:
        return cands
    want = [s.strip() for s in (only or "").split(",") if s.strip()]
    names = {r["folder"] for r in cands}
    bad = [w for w in want if w not in names]
    if bad:
        raise SystemExit(f"not in the plan (refusing): {', '.join(bad)}")
    return [r for r in cands if r["folder"] in want]


def tidy_dir(man: dict, stamp: str | None = None) -> Path:
    stamp = stamp or dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return Path(man.get("archive", "D:/k10-track-archive")) / f"{stamp}_tidy"


def apply_moves(sel: list[dict], ac: Path, dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    log, done = dest / "MOVES.tsv", []
    new = not log.exists()
    with log.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("from\tto\tversion\tclass\tbytes\n")
        for r in sel:
            src, dst = ac / r["folder"], dest / r["folder"]
            if dst.exists():
                raise SystemExit(f"{dst} already exists (refusing to overwrite)")
            shutil.move(str(src), str(dst))
            fh.write(f"{src.as_posix()}\t{dst.as_posix()}\t{r.get('version')}\t{r['class']}\t{r.get('size')}\n")
            done.append(r["folder"])
    return done


def apply_renames(sel: list[dict], ac: Path, man: dict, dest: Path) -> list[str]:
    done = []
    for r in sel:
        ent = man["folders"][r["folder"]]
        old, new = ent["old_name_prefix"], ent["ui_name_prefix"]
        for l in r["layouts"]:
            p = ac / r["folder"] / l["file"]
            raw = p.read_bytes()
            text = raw.decode("utf-8-sig", errors="strict")
            m = re.search(r'("name"\s*:\s*")' + re.escape(old), text)
            if not m:
                continue
            keep = dest / f"{r['folder']}.ui" / l["file"]
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_bytes(raw)
            text = text[:m.start()] + m.group(1) + new + text[m.end():]
            p.write_bytes((b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8"))
            done.append(f"{r['folder']}/{l['file']}")
    return done


def restore(d: Path, ac: Path) -> list[str]:
    done = []
    moves = d / "MOVES.tsv"
    for line in (moves.read_text(encoding="utf-8").splitlines()[1:] if moves.exists() else []):
        src, dst = line.split("\t")[:2]
        name = Path(dst).name
        if not (d / name).is_dir():
            continue
        if (ac / name).exists():
            print(f"skip {name}: already in AC")
            continue
        shutil.move(str(d / name), str(ac / name))
        done.append(name)
    for keep in sorted(d.glob("*.ui")):
        folder = ac / keep.name[:-3]
        for p in keep.rglob("ui_track.json"):
            target = folder / p.relative_to(keep)
            if target.parent.is_dir():
                shutil.copy2(p, target)
                done.append(f"{keep.name[:-3]}/{p.relative_to(keep).as_posix()} (name)")
    return done


def record(man: dict, ac: Path, folder: str, track: str, branch: str | None, sha: str | None, engine: str | None,
           role: str = "current", date: str | None = None) -> dict:
    lays = layouts(ac / folder)
    if not lays:
        raise SystemExit(f"{ac / folder}: no ui_track.json (not installed?)")
    ent = dict(man.setdefault("folders", {}).get(folder, {}))
    ent.update({"track": track, "role": role, "version": installed_version(lays),
                "installed": date or dt.date.today().isoformat()})
    for k, v in (("branch", branch), ("sha", sha), ("engine", engine)):
        if v:
            ent[k] = v
    man["folders"][folder] = dict(sorted(ent.items()))
    if role == "current":
        fam = family_of(ent)
        for other, oe in man["folders"].items():
            if other != folder and family_of(oe) == fam and oe.get("role", "current") in ("current", "kept"):
                oe["role"], oe["successor"] = "superseded", folder
                man["folders"][other] = dict(sorted(oe.items()))
    return ent


def family_of(ent: dict) -> str:
    """the track a folder is a copy of: the manifest's `family`, else the track slug without a trailing -lm"""
    return ent.get("family") or re.sub(r"-lm$", "", str(ent.get("track") or ""))


def replaced_by(man: dict, ac: Path, folder: str) -> list[str]:
    """the folders still in AC that an install of `folder` replaces (same family, superseded by it)"""
    return sorted(n for n, e in man["folders"].items()
                  if e.get("successor") == folder and e.get("role") == "superseded" and (ac / n).is_dir())


def load_manifest(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(man: dict, p: Path):
    man["folders"] = dict(sorted(man["folders"].items()))
    p.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="scan", choices=["scan", "record", "restore"])
    ap.add_argument("target", nargs="?", help="record: the AC folder; restore: the <stamp>_tidy dir")
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--ac", help="content/tracks (default: the manifest's ac_tracks)")
    ap.add_argument("--fetch", action="store_true", help="git fetch origin before the up-to-date check")
    ap.add_argument("--json", help="also write the inventory here")
    ap.add_argument("--apply", action="store_true", help="move the planned folders named by --only (or --all)")
    ap.add_argument("--rename", action="store_true", help="rewrite old-name prefixes in the folders named by --only")
    ap.add_argument("--only", help="comma-separated folder names")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--track"), ap.add_argument("--branch"), ap.add_argument("--sha"), ap.add_argument("--engine")
    ap.add_argument("--role", default="current")
    ap.add_argument("--date", help="record: the install date (default today)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mp = Path(a.manifest)
    man = load_manifest(mp)
    ac = Path(a.ac or man["ac_tracks"])

    if a.cmd == "record":
        if not (a.target and a.track):
            ap.error("record needs <folder> and --track")
        ent = record(man, ac, a.target, a.track, a.branch, a.sha, a.engine, a.role, a.date)
        save_manifest(man, mp)
        print(f"recorded {a.target}: {json.dumps(ent, ensure_ascii=False)}")
        rep = replaced_by(man, ac, a.target)
        if rep:
            print(f"replaces (still in AC, now planned to move): {', '.join(rep)}"
                  f"  -> python tools/ac_tidy.py --apply --only {','.join(rep)}")
        return 0
    if a.cmd == "restore":
        if not a.target:
            ap.error("restore needs the <stamp>_tidy dir")
        if acs_running():
            raise SystemExit("acs.exe is running: close Assetto Corsa first")
        for d in restore(Path(a.target), ac):
            print(f"restored {d}")
        return 0

    if a.fetch:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin"], check=False)
    inv = inventory(man, ac)
    print(report(inv, man, dry=not (a.apply or a.rename)))
    if a.json:
        Path(a.json).write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    if not (a.apply or a.rename):
        return 0
    if not (a.only or a.all):
        raise SystemExit("--apply / --rename need --only <folders> or --all (Kevin picks folder by folder)")
    if acs_running():
        raise SystemExit("acs.exe is running: close Assetto Corsa first (Content Manager may stay open)")
    dest = tidy_dir(man)
    if a.apply:
        for f in apply_moves(pick(plan_of(inv), a.only, a.all), ac, dest):
            print(f"moved {f} -> {dest.as_posix()}/{f}")
    if a.rename:
        for f in apply_renames(pick(renames_of(inv, man), a.only, a.all), ac, man, dest):
            print(f"renamed {f} (original kept in {dest.as_posix()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
