# Pikes Peak 0.2.3: why the pad aprons differ from 0.2.1 (PC, 2026-11-11)

compare_ab of 0.2.3 against the installed 0.2.1 reports PADAPRON_0 and PADAPRON_1 positions differ. Every other one
of the 25 meshes is bit-identical.

- **The difference.** Each apron has 8 triangles fewer: 15,256 -> 15,248 and 13,798 -> 13,790 in the kn5. The seat-pads
  log reads 58,946 -> 58,938 and 57,488 -> 57,480 triangles on the ground. The height range is unchanged.
- **The cause.** `tools/seat_pads_blend.py` 84fefe1a (Nevada 0.1.3's 1.5 mm ground fold, ledger 0087): a pad vertex
  where two ground pieces meet takes the higher ground.
  - main has it since 2026-11-09.
  - 0.2.1's branch (d7d40c2) did not.
  - The overnight 0.2.2 build (main 06d782f) already read 58,938.
- **The proof.** A scratch worktree at rw-ppir's beb2a64c with only `tools/seat_pads_blend.py` checked out from d7d40c2,
  built from an empty workshop (`pp_padab`, --no-install).
  - seat-pads reads 58,946 / 57,488 again;
  - split main 471,882 positions, 0.2.1's;
  - compare_ab against 0.2.1: **25 / 25 meshes' positions bit-identical**, the UVs changed only on the road-wear surfaces
    (`compare_ab_vs_021_old_pad_tool.json`).
- So 0.2.3 = 0.2.1 + the road wear (UVs and material) + main's pad-fold fix on the aprons. No other position moved.
