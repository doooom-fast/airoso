#!/usr/bin/env bash
# The GitHub org move, k10-motorsports -> doooom-fast (docs/ORG-CONSOLIDATION.md; Kevin's decisions of 2026-10-28).
#
# This script is the ORG OWNER's to run: `gh` logged in as an owner of BOTH orgs, with the `repo`, `admin:org` and
# `delete_repo` scopes (`gh auth status`; `gh auth refresh -s admin:org,delete_repo`). No agent session holds that token.
#
#   bash tools/org_move.sh                 # DRY RUN: prints every command of every step, runs nothing
#   bash tools/org_move.sh --step 1 --yes  # run step 1 (repeat per step, in order; each step is safe to re-run)
#   bash tools/org_move.sh --step 6 --yes --delete   # step 6 deletes repositories: it needs the extra flag
#   bash tools/org_move.sh --verify        # list both orgs' repositories and the archived/renamed state
#
# Order (ORG-CONSOLIDATION.md "Order of operations"):
#   1  the public release home doooom-fast/track-releases + the current zips re-published there
#   2  transfer the four Vercel-backed repos (then: Vercel reconnect, by hand — printed)
#   3  re-point prodrive-server's tracks.ts at track-releases (by hand — printed)
#   4  transfer the rest of the product family; k10-1978 -> 1978, K10-mxc -> mxc, k10-stories -> stories
#   5  transfer, then archive: the retired track repos and the not-current product repos
#   6  delete prodrive-ac-builder and .github (then the empty org, in the web UI)
#   7  the app installs and secrets (by hand — printed)
#   8  airoso's references: the PR that ships with this script (merge it once steps 1-5 are done)
#
# GitHub keeps redirects for web, git and API URLs of a transferred or renamed repo until a repo with the old name is
# created, so nothing live breaks during the move; the Vercel projects are re-pointed in step 2 anyway.
set -euo pipefail

OLD=k10-motorsports
NEW=doooom-fast
RELEASE_REPO=track-releases
RELEASE_TAG="${RELEASE_TAG:-v0.23.0}"       # the public series continues k10-san-diego's (docs/PUBLISHING.md)
STEP=""; YES=0; DELETE=0; VERIFY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --step) STEP="$2"; shift 2 ;;
    --yes) YES=1; shift ;;
    --delete) DELETE=1; shift ;;
    --verify) VERIFY=1; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done

run() {   # print the command; run it only with --yes
  echo "+ $*"
  if [ "$YES" = 1 ]; then "$@"; fi
}
note() { echo "  # $*"; }
exists_in() { gh repo view "$1/$2" --json name -q .name >/dev/null 2>&1; }
transfer() {   # transfer <repo> [new-name]: idempotent (skips when it is already under $NEW), then renames when asked
  local repo="$1" newname="${2:-$1}"
  if [ "$YES" != 1 ]; then   # dry run: no gh calls, just the commands
    run gh api -X POST "repos/$OLD/$repo/transfer" -f new_owner="$NEW" --silent
    [ "$newname" = "$repo" ] || run gh repo rename "$newname" -R "$NEW/$repo" --yes
    return 0
  fi
  if exists_in "$NEW" "$newname" && ! exists_in "$OLD" "$repo"; then
    note "$NEW/$newname already exists and $OLD/$repo is gone: transferred"
  elif exists_in "$OLD" "$repo"; then
    run gh api -X POST "repos/$OLD/$repo/transfer" -f new_owner="$NEW" --silent
    if [ "$YES" = 1 ]; then
      for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do exists_in "$NEW" "$repo" && break; sleep 5; done
      exists_in "$NEW" "$repo" || { echo "!! $OLD/$repo did not appear under $NEW within 60 s"; exit 1; }
    fi
    if [ "$newname" != "$repo" ]; then
      run gh repo rename "$newname" -R "$NEW/$repo" --yes
    fi
  else
    note "neither $OLD/$repo nor $NEW/$newname exists: nothing to do"
  fi
}
archive() { run gh repo archive "$NEW/$1" --yes; }

if [ "$VERIFY" = 1 ]; then
  for org in "$OLD" "$NEW"; do
    echo "== $org"
    gh repo list "$org" --limit 100 --json name,isArchived,isPrivate,pushedAt \
      -q '.[] | "\(.name)\t\(if .isArchived then "archived" else "active" end)\t\(if .isPrivate then "private" else "public" end)\t\(.pushedAt)"' | sort
  done
  exit 0
fi

[ "$YES" = 1 ] || echo "DRY RUN (add --yes to execute; --step N for one step)"
if [ "$YES" = 1 ]; then
  gh auth status >/dev/null 2>&1 || { echo "gh is not logged in"; exit 1; }
  [ -n "$STEP" ] || { echo "--yes needs --step N: one step at a time, in order"; exit 2; }
fi
want() { [ -z "$STEP" ] || [ "$STEP" = "$1" ]; }

# ---------------------------------------------------------------------------------------------------------------
if want 1; then
  echo; echo "### STEP 1 — the public release home, with the current zips"
  if exists_in "$NEW" "$RELEASE_REPO"; then
    note "$NEW/$RELEASE_REPO exists"
  else
    run gh repo create "$NEW/$RELEASE_REPO" --public \
      --description "doooom track downloads: every Assetto Corsa track's release zips"
  fi
  note "the zips the website serves today: the LATEST release of $OLD/k10-san-diego (Lake Murray + the freeway) and of"
  note "$OLD/k10-colorado (the Colorado zips). The Lariat zip carries mined textures (Lariat V3-PLAN D0): it is NOT re-published."
  TMP="${TMPDIR:-/tmp}/org-move-zips"; run mkdir -p "$TMP"
  run gh release download -R "$OLD/k10-san-diego" --pattern '*.zip' --dir "$TMP" --clobber
  run gh release download -R "$OLD/k10-colorado" --pattern '*.zip' --dir "$TMP" --clobber
  run bash -c "rm -f '$TMP'/*lariat*.zip '$TMP'/*Lariat*.zip; ls -la '$TMP'"
  note "one release carries every zip that must stay downloadable (PUBLISHING.md: only the latest release's assets show)"
  run bash -c "gh release create '$RELEASE_TAG' -R '$NEW/$RELEASE_REPO' --draft --title 'doooom tracks $RELEASE_TAG' \
    --notes 'The current doooom Assetto Corsa tracks. Moved here from k10-motorsports/k10-san-diego and k10-colorado on $(date -u +%Y-%m-%d); the Lariat zip is withdrawn (Lariat V3-PLAN D0).' '$TMP'/*.zip"
  note "check the draft on github.com/$NEW/$RELEASE_REPO/releases, then publish it:"
  run gh release edit "$RELEASE_TAG" -R "$NEW/$RELEASE_REPO" --draft=false
fi

if want 2; then
  echo; echo "### STEP 2 — the four Vercel-backed repos"
  for r in prodrive-server prodrive-images-api prodrive-support prodrive-agents; do transfer "$r"; done
  note "BY HAND, now, for each Vercel project (team Alternate): Settings -> Git -> Disconnect, then Connect to $NEW/<repo>."
  note "The Vercel GitHub App must be installed on $NEW first (github.com/organizations/$NEW/settings/installations)."
  note "  k10-racecor-prodrive  <- $NEW/prodrive-server (apps/web)      doooom.fast, racecor.io, prodrive.racecor.io, k10motorsports.racing"
  note "  racecor-prodrive-api  <- $NEW/prodrive-server                 api.prodrive.racecor.io"
  note "  prodrive-images-api   <- $NEW/prodrive-images-api             images.racecor.io"
  note "  prodrive-support      <- $NEW/prodrive-support                support.racecor.io"
  note "Then push one commit to each and watch production deploy."
fi

if want 3; then
  echo; echo "### STEP 3 — re-point the website's release reader (by hand, in $NEW/prodrive-server)"
  note "apps/web/src/lib/tracks.ts reads the latest GitHub Release of '$OLD/k10-colorado' and '$OLD/k10-san-diego'."
  note "Make it read ONE repo: '$NEW/$RELEASE_REPO' (step 1). Keep the asset-name -> catalog-key rule (name minus _vX.Y.Z / _ai)."
  note "The catalog text in apps/web/src/lib/doooom/tracks.ts says 'K10' nowhere any more: the series is doooom (ONE-CHAIN §3)."
  note "Deploy; confirm the Tracks page lists every zip of the $RELEASE_TAG release."
fi

if want 4; then
  echo; echo "### STEP 4 — the rest of the product family, and the k10- prefixes dropped"
  for r in prodrive-plugin prodrive-windows prodrive-overlay prodrive-macos prodrive-ios prodrive-tvos; do transfer "$r"; done
  note "any App Store / signing config that names a repo path needs a check after these three move"
  transfer k10-1978 1978
  transfer K10-mxc mxc
  transfer k10-stories stories
fi

if want 5; then
  echo; echo "### STEP 5 — transfer, then archive (read-only, reversible)"
  note "the retired track repos keep their names: the ledger's pre-2026-10-27 commit IDs resolve only in k10-track-agents"
  for r in k10-track-agents k10-colorado k10-colorado-rally k10-san-diego; do transfer "$r"; done
  for r in k10-track-agents k10-colorado k10-colorado-rally k10-san-diego; do archive "$r"; done
  note "the not-current product repos (Kevin, 2026-10-28)"
  for r in prodrive-edit prodrive-homebridge prodrive-designer prodrive-narrative; do transfer "$r"; archive "$r"; done
  archive mxc
  archive stories
fi

if want 6; then
  echo; echo "### STEP 6 — delete (irreversible)"
  if [ "$YES" = 1 ] && [ "$DELETE" != 1 ]; then echo "step 6 needs --delete as well as --yes"; exit 2; fi
  note "prodrive-ac-builder: frozen 2026-07-25, a strict git ancestor of k10-track-agents with zero unique files (docs/V3-PLAN.md §0)"
  run gh repo delete "$OLD/prodrive-ac-builder" --yes
  note ".github: the old org's profile README"
  run gh repo delete "$OLD/.github" --yes
  note "then, when 'bash tools/org_move.sh --verify' shows $OLD empty: Organization settings -> Danger zone -> Delete."
  note "k10motorsports.racing lives on Vercel, not GitHub; unaffected."
fi

if want 7; then
  echo; echo "### STEP 7 — access (by hand)"
  note "Claude GitHub App on $NEW: 'selected repositories' today (airoso was added by hand) -> add the transferred repos or switch to all."
  note "Vercel GitHub App on $NEW (step 2). CI secrets / deploy keys scoped to $OLD: none are known in airoso; check prodrive-server's."
  note "Local clones: git remote set-url origin git@github.com:$NEW/<repo>.git  (astra, the Windows box; airoso already points at $NEW)."
fi

if want 8; then
  echo; echo "### STEP 8 — airoso's references"
  note "the PR that carries this script updates every k10-motorsports reference in airoso (CLAUDE.md, fleet/registry.json,"
  note "fleet/MIGRATION.md, docs/PUBLISHING.md, assets/licenses.json, the USER_AGENT strings, the game seed, five track"
  note "configs' author, the Lake Murray release texts). Merge it once steps 1-5 are done, so every URL in it is real."
fi
echo; echo "done ($([ "$YES" = 1 ] && echo executed || echo dry run)). 'bash tools/org_move.sh --verify' lists both orgs."
