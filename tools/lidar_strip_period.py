"""tools/lidar_strip_period.py <npz>... (PC strips from tools/lidar_strip.py): does the lidar intensity along s carry a kerb's block period near the edge? (ledger 0081 round 3)
Per offset column: the intensity series along s (0.5 m cells, empty cells skipped), detrended; its strongest sine power
at periods 1.2-3.0 m (least squares on the occupied cells), against the same column shuffled 200 times (the null)."""
import sys
import numpy as np

rng = np.random.default_rng(0)
PER = np.arange(1.2, 3.01, 0.1)   # 0.5 m cells: 1.0 m is the Nyquist period (sin vanishes on the grid)


def power(s, v):
    v = v - v.mean()
    best = 0.0
    for p in PER:
        w = 2 * np.pi / p
        A = np.stack([np.cos(w * s), np.sin(w * s)], axis=1)
        c, *_ = np.linalg.lstsq(A, v, rcond=None)
        best = max(best, float(np.hypot(*c)))
    return best


for f in sys.argv[1:]:
    d = np.load(f)
    I, S, O, N = d["i_mean"], d["s"], d["o"], d["n"]
    print("----", f.split("/")[-1], "returns", int(d["points"]))
    for j, o in enumerate(O):
        ok = (N[:, j] > 0) & np.isfinite(I[:, j])
        if ok.sum() < 30:
            print(f"  o {o:+5.1f}: {ok.sum()} cells, too few")
            continue
        s, v = S[ok], I[ok, j]
        p = power(s, v)
        null = [power(s, rng.permutation(v)) for _ in range(200)]
        q = (np.array(null) >= p).mean()
        if o <= 4.0 or q < 0.05:
            print(f"  o {o:+5.1f}: cells {ok.sum():3d}  median {np.median(v):7.0f}  block-period amp {p:6.0f}  "
                  f"null p95 {np.percentile(null, 95):6.0f}  p-value {q:.3f}")
