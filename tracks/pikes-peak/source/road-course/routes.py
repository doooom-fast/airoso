"""Assemble candidate layouts from the measured pieces and give each its lap length (ledger 0085 Re-trace).

    python tracks/pikes-peak/source/road-course/routes.py       (after retrace.py; reads infield_pieces.naip.json,
                                                                 inside_edge.naip.json, the lidar wall survey)

The pieces are measured once (infield_pieces.naip.json); a layout is a list of (piece, direction). Junctions:
  - piece ends within 14 m of each other are one junction;
  - a piece end that lands on ANOTHER piece's interior (within 9 m of its centre line, >= 8 m from its ends) splits that
    piece there: <name>.a (start -> mouth) and <name>.b (mouth -> end).
The oval: its MID-SURFACE line, half way between the 2018 lidar wall face and the measured inside edge
(inside_edge.naip.json), every 1 m. The infield pieces join it where their centre lines, extended, cross it: the NE
diverge (ne_lane's start) and the NW merge (arc_nw's / n_road's start). The oval share of a CCW road-course lap is that
mid line from the NW merge round turns 1-2 to the NE diverge. A lap's length is a sum of centre lines; each junction
adds an unmeasured join of a few metres (a piece's centre line stops at the junction's middle, so joins neither double
count nor drop more than ~half a road width: +-6 m per junction, stated as the length's uncertainty).

Wear support: each layout's length-weighted mean wear index of its infield pieces (pieces.py WEAR), and per piece
the direction the corner apex shifts favour (retrace.py corner_direction: + = the piece's own direction).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import naip  # noqa: E402

PUBLISHED = (2074.0, 2116.0)
J_EPS = 6.0          # [invented] per-junction join uncertainty, m


def load():
    d = json.loads((HERE / "infield_pieces.naip.json").read_text())
    ie = json.loads((HERE / "inside_edge.naip.json").read_text())
    P = {k: np.array(v["centre_en_m"]) for k, v in d["pieces"].items()}
    return d, ie, P


def oval_mid(ie):
    ov = naip.oval_line()
    rows = ie["rows"]
    E = np.array([r["edge_en_m"] for r in rows])
    wid = np.array([r["wall_face_to_edge_m"] for r in rows])
    # the wall face at each 1 m station: the inside edge pushed back out by the measured width along the line's normal
    line = naip.resample(ov["line"], 1.0, closed=True)
    T, L = naip.normals(line, closed=True)
    face = E - wid[:, None] * L
    mid = (face + E) / 2
    f15 = E - (15 * 0.3048) * L          # NASCAR-style measuring line: 15 ft off the inside edge
    return dict(mid=mid, face=face, edge=E, f15=f15, L=L, wid=wid)


def closed_len(Q):
    return float(naip.cumlen(np.vstack([Q, Q[:1]]))[-1])


def project(Q, p):
    d = np.hypot(Q[:, 0] - p[0], Q[:, 1] - p[1])
    i = int(np.argmin(d))
    return i, float(d[i])


# where one piece's end lands on another's interior: that piece splits there (.a = start -> mouth, .b = mouth -> end)
SPLITS = {"c_road": ("s_curve", 0), "ring_ne": ("par_lane", -1)}
# the junction each piece end stands in (named for the stills and the report; the vias put them there)
ENDS = {"ne_lane": ("NE", "TOP"), "hairpin_w": ("TOP", "CJ"), "diag_n": ("CJ", "PAR"), "diag_s": ("PAR", "LOTN"),
        "n_road": ("NW", "TOP"), "arc_nw": ("NW", "WTOP"), "c_road.a": ("WTOP", "SMOUTH"), "c_road.b": ("SMOUTH", "CJ"),
        "west_n": ("WTOP", "SW"), "bottom": ("SW", "LOTW"), "s_curve": ("SMOUTH", "SW"), "par_lane": ("PAR", "PARM"),
        "ring_nw": ("LOTW", "LOTN"), "ring_ne.a": ("LOTN", "PARM"), "ring_ne.b": ("PARM", "LOTE"), "ring_s": ("LOTE", "LOTW")}


def split_pieces(P):
    out = dict(P)
    for b, (a, e) in SPLITS.items():
        B = out.pop(b)
        i, dist = project(B, P[a][e])
        out[b + ".a"] = B[:i + 1]
        out[b + ".b"] = B[i:]
    return out


def nodes_of(Pp):
    nid = {}
    pts = {}
    for k, (s0, s1) in ENDS.items():
        nid[(k, 0)] = s0; nid[(k, 1)] = s1
        pts.setdefault(s0, []).append(Pp[k][0]); pts.setdefault(s1, []).append(Pp[k][-1])
    return nid, {k: np.mean(v, axis=0) for k, v in pts.items()}


# Layouts: (id, name, oval?, [(piece, +1 forward / -1 reversed), ...], note)
LAYOUTS = [
    ("RC-A", "road course, newest loop: lane, hairpin, diag, lot corner, bottom, west road, sweeper", True,
     [("ne_lane", 1), ("hairpin_w", 1), ("diag_n", 1), ("diag_s", 1), ("ring_nw", -1), ("bottom", -1), ("west_n", -1),
      ("arc_nw", -1)], "the previous agent's loop, now edge-measured"),
    ("RC-B", "road course with the S-curve: ... bottom, S-curve, C road west, sweeper", True,
     [("ne_lane", 1), ("hairpin_w", 1), ("diag_n", 1), ("diag_s", 1), ("ring_nw", -1), ("bottom", -1), ("s_curve", -1),
      ("c_road.a", -1), ("arc_nw", -1)], "the S-curve run backwards against its own wear's apex shifts"),
    ("RC-C", "road course with the parallel lane: ... diag north, parallel lane, lot ring back west, bottom, west road", True,
     [("ne_lane", 1), ("hairpin_w", 1), ("diag_n", 1), ("par_lane", 1), ("ring_ne.a", -1), ("ring_nw", -1), ("bottom", -1),
      ("west_n", -1), ("arc_nw", -1)], ""),
    ("RC-D", "road course round the lot ring the long way", True,
     [("ne_lane", 1), ("hairpin_w", 1), ("diag_n", 1), ("diag_s", 1), ("ring_ne.a", 1), ("ring_ne.b", 1), ("ring_s", 1),
      ("bottom", -1), ("west_n", -1), ("arc_nw", -1)], ""),
    ("RC-E", "short road course: lane, hairpin, N road back to the oval (skips the infield's south)", True,
     [("ne_lane", 1), ("n_road", -1)], "a bypass; far short of the published length"),
    ("IF-1", "infield only, the road course's infield closed by the N road (never on the oval's racing surface)", False,
     [("hairpin_w", 1), ("diag_n", 1), ("diag_s", 1), ("ring_nw", -1), ("bottom", -1), ("west_n", -1), ("arc_nw", -1),
      ("n_road", 1)], "crosses the NW junction on the oval's inside apron"),
    ("IF-2", "infield only, inner loop: C road, west road, bottom, lot corner, diag", False,
     [("c_road.b", -1), ("c_road.a", -1), ("west_n", 1), ("bottom", 1), ("ring_nw", 1), ("diag_s", -1), ("diag_n", -1)],
     "direction free: no oval to fix it"),
    ("IF-3", "infield only, S-curve loop: C road east, S-curve, bottom, lot corner, diag", False,
     [("c_road.b", -1), ("s_curve", 1), ("bottom", 1), ("ring_nw", 1), ("diag_s", -1), ("diag_n", -1)],
     "S-curve in its wear's direction"),
    ("IF-4", "infield only, the N-road loop: N road, sweeper, C road, hairpin", False,
     [("n_road", 1), ("hairpin_w", 1), ("c_road.b", -1), ("c_road.a", -1), ("arc_nw", -1)],
     "the smallest loop through the NW apron"),
    ("LOT-1", "the lot ring alone (the skidpad lot's perimeter)", False,
     [("ring_nw", 1), ("ring_ne.a", 1), ("ring_ne.b", 1), ("ring_s", 1)], "reading (b); Kevin confirmed (a), listed for the wear"),
]


def main():
    d, ie, P = load()
    Pp = split_pieces(P)
    nid, nodes = nodes_of(Pp)
    om = oval_mid(ie)
    mid = om["mid"]
    lap_mid = closed_len(mid); lap_f15 = closed_len(om["f15"])
    lap_line = closed_len(naip.oval_line()["line"])
    smid = naip.cumlen(np.vstack([mid, mid[:1]]))
    # junction stations on the oval mid line
    def oval_station(Q):
        i, dist = project(mid, Q)
        return i, float(smid[i]), dist
    iNE, sNE, dNE = oval_station(P["ne_lane"][0])
    iNW, sNW, dNW = oval_station(P["arc_nw"][0])
    iNWn, sNWn, dNWn = oval_station(P["n_road"][0])
    # CCW: the line's stations increase with the lap direction; share = NW merge -> 0 -> NE diverge
    share = (smid[iNE] - smid[iNW]) % lap_mid
    share_n = (smid[iNE] - smid[iNWn]) % lap_mid
    wear = {k: v["wear"]["index"] for k, v in d["pieces"].items()}
    dirs = {}
    for k, v in d["pieces"].items():
        cs = [c for c in v["wear"]["corners"] if abs(c["apex_minus_middle_m"]) >= 2]
        fw = sum(c["band_peak"] for c in cs if c["apex_minus_middle_m"] > 0)
        bw = sum(c["band_peak"] for c in cs if c["apex_minus_middle_m"] < 0)
        dirs[k] = {"forward_weight": round(fw, 3), "reverse_weight": round(bw, 3),
                   "reads": "forward" if fw > 1.5 * bw and fw > 0 else ("reverse" if bw > 1.5 * fw and bw > 0 else "mixed")}
    out = {"_doc": __doc__.strip().splitlines()[0],
           "oval": {"lap_mid_surface_m": round(lap_mid, 1), "lap_15ft_off_inside_edge_m": round(lap_f15, 1),
                    "lap_port_line_m": round(lap_line, 1), "published_m": 1609.0,
                    "ne_diverge_mid_s": round(sNE, 1), "nw_merge_mid_s_arc": round(sNW, 1), "nw_merge_mid_s_nroad": round(sNWn, 1),
                    "share_ccw_nw_to_ne_m": round(float(share), 1), "share_ccw_nroad_to_ne_m": round(float(share_n), 1),
                    "piece_end_to_mid_line_m": {"ne_lane": round(dNE, 1), "arc_nw": round(dNW, 1), "n_road": round(dNWn, 1)}},
           "split_pieces": {k: round(float(naip.cumlen(Q)[-1]), 1) for k, Q in Pp.items()},
           "junctions_en_m": {k: [round(float(c[0]), 1), round(float(c[1]), 1)] for k, c in nodes.items()},
           "junction_spread_m": {k: round(float(max(np.hypot(*(q - nodes[k])) for q in v)), 1) for k, v in
                                 {n_: [Pp[p][0 if e == 0 else -1] for (p, e), m_ in nid.items() if m_ == n_] for n_ in nodes}.items()},
           "piece_direction_from_wear": dirs,
           "layouts": []}
    for lid, name, oval, seq, note in LAYOUTS:
        if any(p not in Pp for p, _ in seq):
            out["layouts"].append({"id": lid, "name": name, "error": "piece missing: " + ",".join(p for p, _ in seq if p not in Pp)})
            continue
        # continuity check: each piece's exit node is the next one's entry node
        breaks = []
        for (a, da), (b, db) in zip(seq, seq[1:] + ([] if oval else seq[:1])):
            ex = nid[(a, 1 if da > 0 else 0)]; en = nid[(b, 0 if db > 0 else 1)]
            if ex != en:
                breaks.append(f"{a}->{b}")
        def plen(p):
            # an unsplit piece: its measured centre length; a split part: its share of it
            b = p.split(".")[0]
            full = d["pieces"][b]["length_m"]
            if p == b:
                return full
            return full * float(naip.cumlen(Pp[p])[-1]) / float(naip.cumlen(P[b])[-1])
        infield = sum(plen(p) for p, _ in seq)
        L_ = infield + (share if (oval and seq[-1][0] == "arc_nw") else share_n if oval else 0.0)
        nj = len(seq) + (1 if oval else 0)
        base = [p.split(".")[0] for p, _ in seq]
        wl = sum(wear[b] * plen(p) for b, (p, _) in zip(base, seq)) / infield
        agree = []
        for b, (p, dr) in zip(base, seq):
            r = dirs[b]["reads"]
            if r != "mixed":
                agree.append((b, "agrees" if (r == "forward") == (dr > 0) else "against"))
        out["layouts"].append({
            "id": lid, "name": name, "uses_oval": oval, "note": note,
            "pieces": [[p, dr] for p, dr in seq],
            "infield_m": round(infield, 1), "oval_share_m": round(float(L_ - infield), 1),
            "lap_m": round(float(L_), 1), "uncertainty_m": round(J_EPS * nj, 0),
            "vs_published_m": None if not oval else [round(float(L_ - PUBLISHED[0]), 1), round(float(L_ - PUBLISHED[1]), 1)],
            "wear_weighted": round(float(wl), 4),
            "wear_direction": agree,
            "continuity_breaks": breaks})
    (HERE / "layouts.naip.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["oval"], indent=1))
    print(out["split_pieces"])
    for l in out["layouts"]:
        print(l["id"], l.get("lap_m"), l.get("vs_published_m"), l.get("wear_weighted"), l.get("continuity_breaks"), l.get("error", ""))
    print(json.dumps(dirs))
    naip.CACHE.mkdir(parents=True, exist_ok=True)
    np.save(naip.CACHE / "oval_mid.npy", np.c_[om["mid"], om["face"], om["edge"]])
    return out


if __name__ == "__main__":
    main()
