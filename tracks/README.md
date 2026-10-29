# tracks/

A track is `tracks/<place>/` (hyphenated slug). That folder is the **source of truth** for the track:

```
tracks/<place>/
├── track.config.json   # identity, layouts, install_folder, version
├── ship.json           # how the chain builds and ships it
├── DOSSIER.md          # the research the geometry rests on
├── data/ · source/     # centerline, elevation, aerials, evidence
└── loop.blend          # the hand-authored scene (Git LFS), never regenerated over
```

It is built by `tools/ship_track.sh <place>` (docs/ONE-CHAIN.md §1), installed under its
`install_folder` (`content/tracks/<install_folder>`), and published from GitHub Releases
(docs/PUBLISHING.md).

**Built outputs are never committed.** No kn5, no installable track folder, no packed zip lives in this
repo; the engine-era "git-pullable installs" (`imi_motorsports`, `san_diego_lake_murray`,
`sand_creek_raceway`) were removed 2026-10-28 (ONE-CHAIN §2 row 10). Download a track from its Release.
