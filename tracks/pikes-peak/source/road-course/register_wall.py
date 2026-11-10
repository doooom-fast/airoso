"""Registration of NAIP 2023 0.3 m against the 2018 lidar wall (ledger 0085 Re-trace, step 1).

The lidar wall survey (source/lidar/wall-survey/wall_right.json, tools/lidar_wall.py) places the outer wall's inner FACE at
556 stations around the oval. On the NAIP the wall's concrete top is the brightest thin band at the outside of the
pavement (the 10 am sun throws its shadow inward on the south walls and outward on the north ones, so the band reads
dark-bright or bright-dark; its road-side edge is the same feature either way).

Per station, along the outward normal (0.05 m steps, bilinear), within +-2.5 m of the lidar face:
  - the band: the luminance maximum, kept only if >= 190 and >= 35 over the road's median 3-6 m inside;
  - its road-side edge: where luminance crosses half way between that peak and the darkest value within 1.5 m inside
    it, sub-pixel (linear between the two samples bracketing the crossing).
offset_i = NAIP edge - lidar face (m, + = outward). Fitted, iteratively 3-sigma trimmed:
    offset_i = b + dE * nE_i + dN * nN_i
(n = the outward normal). (dE, dN) is the image's displacement against the lidar (the oval's normals turn through 360
deg, so it separates from b); b is the constant between the two edge definitions (the lidar's 10th-percentile face of
returns 0.3-2.5 m up vs the top's road-side edge).
Caveat: the band is the wall's TOP, 1.27 m up; NAIP is orthorectified to a ground DEM, so the top carries relief
displacement h * tan(view angle) (<= ~0.4 m at 1.27 m for a frame edge) in the direction away from the camera's nadir:
a uniform shift indistinguishable here from registration. The shift below is therefore an UPPER bound on the ground
registration error in its direction; nothing on disk resolves a ground-level feature in the lidar.

Writes registration.json. "apply" is true only if |shift| >= 0.3 m (the brief: under one pixel, say so and leave it).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geo  # noqa: E402
import naip  # noqa: E402
from scipy import ndimage  # noqa: E402


def main():
    ov = naip.oval_line()
    lum = naip.channels()["lum"]
    offs = np.arange(-6.0, 2.5001, 0.05)
    rows = []
    for k in range(len(ov["s"])):
        if not np.isfinite(ov["face_off"][k]):
            rows.append(None); continue
        out = -ov["L"][k]
        base = ov["face"][k]
        e = base[0] + offs * out[0]; n = base[1] + offs * out[1]
        px, py = geo.en_to_px(e, n)            # the raw image frame: this IS the measurement of its displacement
        v = ndimage.map_coordinates(lum, [py, px], order=1)
        road = np.median(v[(offs >= -6) & (offs <= -3)])
        win = (offs >= -2.5) & (offs <= 2.5)
        iw = np.where(win)[0]
        ip = iw[np.argmax(v[iw])]
        peak = v[ip]
        if peak < 190 or peak - road < 35:
            rows.append(None); continue
        lo = max(0, ip - int(1.5 / 0.05))
        imn = lo + int(np.argmin(v[lo:ip + 1]))
        half = (peak + v[imn]) / 2
        edge = None
        for j in range(ip, imn, -1):
            if v[j - 1] < half <= v[j]:
                edge = offs[j - 1] + (half - v[j - 1]) / (v[j] - v[j - 1]) * 0.05
                break
        rows.append(None if edge is None else float(edge))
    S = ov["s"]
    ok = np.array([r is not None for r in rows])
    off = np.array([r if r is not None else np.nan for r in rows])
    nE, nN = -ov["L"][:, 0], -ov["L"][:, 1]
    A = np.c_[np.ones(len(S)), nE, nN]
    keep = ok.copy()
    for _ in range(6):
        coef = np.linalg.lstsq(A[keep], off[keep], rcond=None)[0]
        res = off - A @ coef
        sd = np.nanstd(res[keep])
        keep = ok & (np.abs(res) <= 3 * sd)
    res = off - A @ coef
    # bootstrap the shift's spread by section (blocks of 30 stations, ~90 m) to respect along-track correlation
    rng = np.random.default_rng(0)
    blocks = [np.arange(i, min(i + 30, len(S))) for i in range(0, len(S), 30)]
    bs = []
    for _ in range(400):
        idx = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        idx = idx[keep[idx]]
        bs.append(np.linalg.lstsq(A[idx], off[idx], rcond=None)[0])
    bs = np.array(bs)
    shift = coef[1:]
    mag = float(np.hypot(*shift))
    rep = {
        "_doc": __doc__.strip().splitlines()[0] + " See register_wall.py for the method.",
        "stations": int(len(S)), "with_band": int(ok.sum()), "used": int(keep.sum()),
        "shift_en_m": [round(float(shift[0]), 3), round(float(shift[1]), 3)],
        "shift_m": round(mag, 3),
        "shift_sd_en_m": [round(float(bs[:, 1].std()), 3), round(float(bs[:, 2].std()), 3)],
        "edge_definition_bias_m": round(float(coef[0]), 3),
        "residual_m": {"rms": round(float(np.sqrt(np.mean(res[keep] ** 2))), 3),
                       "p50_abs": round(float(np.percentile(np.abs(res[keep]), 50)), 3),
                       "p95_abs": round(float(np.percentile(np.abs(res[keep]), 95)), 3)},
        "apply": bool(mag >= 0.3),
        "note": ("|shift| >= 0.3 m: applied (naip.py subtracts it from every NAIP coordinate)" if mag >= 0.3 else
                 "|shift| < 0.3 m (one NAIP pixel): left alone, not applied"),
        "rows": [{"s": float(S[k]), "naip_minus_lidar_m": None if rows[k] is None else round(rows[k], 3),
                  "used": bool(keep[k])} for k in range(len(S))],
    }
    (HERE / "registration.json").write_text(json.dumps(rep, indent=0))
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
