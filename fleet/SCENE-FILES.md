# Scene files in git: only the ones a build starts from

Kevin, 2026-11-23/24, after GitHub refused an LFS upload (airoso's LFS budget used up): "Keep only build starts",
then "Yes, remove record-only scene files".

- A track's `loop.blend` is committed only when a build starts from it (`ship.json` `sync_in` names it).
  Today that is **Lake Murray** alone (`tracks/san-diego-lake-murray/loop.blend`, `sync_in.seed`). Its committed
  blend is the seed every empty workshop starts from, and the chain re-authors on it, every author step idempotent.
- Every other track drafts its `loop.blend` from scratch (lm_intake / the draft steps), so its synced-back blend
  is a record of a build, not an input. Those 22 were removed from the tree on 2026-11-24. Each is still in git
  history at its last commit, and `git checkout <commit> -- tracks/<track>/loop.blend` brings one back.
- From now on a record-only blend is kept in the PC's track archive with its md5 and a README line, and the track's
  ledger names where. `.gitignore` ignores `tracks/*/loop.blend` except Lake Murray's, so a sync-back can't re-add one.
- Removing them from the tree frees no LFS storage: GitHub keeps every version. Freeing it would mean deleting the
  stored objects, which can't be undone, and that hasn't been done.
- A track that comes to start from its committed blend gets its own `!tracks/<track>/loop.blend` line in `.gitignore`
  and a line here.
