"""tools/verify_race.py — the authored race furniture vs its declaration (ledgers 0047 + 0049).

A synthetic ring (200 vertices, R 100 m, 20 m wide) with a v2 declaration: both curb strips everywhere
(closed loops, edge_gaps none), race_cw's closure on the forward-left of its lane and race_acw's mirror, each
in two runs pinned on the far curb strip (v40-v90, v110-v190; a box v91-v109 between them), one race kerb
across the box, one sealed side-street mouth at v150 (behind race_cw's closure, on race_acw's race side) and one
bridge span. The authored file is built the way tools/author_race_furniture_blend.py writes it, from
tools/race_furniture's own plans (ring centres seated flat), then mutated one defect at a time: each mutation
must fail exactly where the gate says it does (C', D, E, J, K, L, M, N with a passing and a failing case; F, G,
H, I kept from ledger 0047).
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import race_furniture as rf  # noqa: E402
import verify_race as vr  # noqa: E402

N = 200
R = 100.0
W = 20.0
RUNS = ((40, 90), (110, 190))
FAR = W / 2.0 - 0.485
MOUTH = 150                       # a sealed mouth on the forward-LEFT curb
SPAN = (60, 64)                   # a declared bridge span (vertices)
WIDTHS = [W] * (N + 1)


def _pts():
    pts = [(R * math.cos(2 * math.pi * k / N), 5.0, R * math.sin(2 * math.pi * k / N)) for k in range(N)]
    return pts + [pts[0]]


def _bands():
    m, half = N, W / 2.0
    st = rf.stations(_pts())
    pins = {v for r in RUNS for v in r}
    zone = ["pin" if k in pins else "closure" if any(i < k < j for i, j in RUNS) else "box" if 90 < k < 110 else "whole"
            for k in range(m)] + ["whole"]
    cors = {}
    for lid, tok, direction, sgn in (("race_cw", "cw", "forward", 1.0), ("race_acw", "acw", "reverse", -1.0)):
        y = [None] * m
        for i, j in RUNS:
            for q, k in enumerate(range(i, j + 1)):
                f = min(1.0, min(q, j - i - q) / 8.0)
                y[k] = round(sgn * (FAR + (2.0 - FAR) * f), 6)
        y.append(y[0])
        lane = [([-(half - 0.82), y[k] - 0.335] if sgn > 0 else [y[k] + 0.335, half - 0.82])
                if (y[k] is not None and zone[k] == "closure") else [-(half - 0.82), half - 0.82] for k in range(m + 1)]
        far = "edge_L" if sgn > 0 else "edge_R"
        cors[lid] = {"token": tok, "direction": direction, "race_side": "R" if sgn > 0 else "L",
                     "closure_side": "L" if sgn > 0 else "R", "zone_by_vertex": zone, "closure_y_by_vertex": y,
                     "lane_by_vertex": lane,
                     "runs": [{"i": a, "j": b, "ends": [{"vertex": i, "y": y[i], "joins": far}, {"vertex": j, "y": y[j], "joins": far}]}
                              for i, j in RUNS for a, b in ((i, j) if sgn > 0 else (j, i),)],
                     "mouths": [{"host_vertex": MOUTH, "side": "L",
                                 "policy": "behind_closure" if sgn > 0 else "sealed_race_strip"}]}
    pts = _pts()
    mouth_line = []
    for k in range(MOUTH - 2, MOUTH + 3):
        tx, tz = rf.tangent(pts, k, m)
        lx, lz = rf.left_normal(tx, tz)
        mouth_line.append([round(pts[k][0] + lx * FAR, 3), 5.0, round(pts[k][2] + lz * FAR, 3)])
    return {"version": 2, "params": {"edge_mode": "road", "barrier_height_m": 1.2, "barrier_half_m": 0.335,
                                     "edge_centre_from_lip_m": -0.485, "kerb_width_m": 1.0},
            "centre_w_by_vertex": [0.0] * (m + 1), "edge_strip_by_vertex": [1] * (m + 1),
            "edge_inset_by_vertex": [0.82] * (m + 1), "edge_gaps": [], "runs": [],
            "streets": [{"street": "Alvarado Road", "vertex_from": 0, "vertex_to": 99},
                        {"street": "College Avenue", "vertex_from": 100, "vertex_to": 199}],
            "corners": [], "edge_corners": [], "bridge_spans_m": [[round(st[SPAN[0]], 3), round(st[SPAN[1]], 3)]],
            "closed_mouths": [{"connector": "side_st", "host_vertex": MOUTH, "side": "L", "vertex_from": MOUTH - 2,
                               "vertex_to": MOUTH + 2, "polyline_xyz_m": mouth_line}],
            "kerbs": [], "corridors": cors}


def _kerb_plan(pts, k0, k1, side="L"):
    st = rf.stations(pts)
    sgn = 1.0 if side == "L" else -1.0

    def at(s):
        k = max(i for i in range(N) if st[i] <= s)
        u = (s - st[k]) / (st[k + 1] - st[k])
        return pts[k][0] + (pts[k + 1][0] - pts[k][0]) * u, pts[k][2] + (pts[k + 1][2] - pts[k][2]) * u, k
    sts, s, q = [], st[k0], 0
    while s <= st[k1]:
        x, z, k = at(s)
        (xa, za, _), (xb, zb, _) = at(s - 1.0), at(s + 1.0)
        L = math.hypot(xb - xa, zb - za)
        sts.append({"s": s, "k": k, "cx": x, "cz": z, "y_hint": 5.1, "tx": (xb - xa) / L, "tz": (zb - za) / L,
                    "lip": sgn * (W / 2.0 - 0.82 - rf.KERB_CLEAR_M - rf.KERB_W), "h": rf.KERB_H, "arc": q * 0.3})
        s += rf.KERB_STEP_M
        q += 1
    return {"kind": "kerb", "apex": (k0 + k1) // 2, "side": side, "sub": "out", "run": [k0, k1], "stations": sts,
            "apex_station": st[(k0 + k1) // 2], "lap_m": st[-1]}


def _authored(pts=None, bands=None):
    """race_authored.json as the author tool writes it, from race_furniture's own plans (seated flat at y 5)"""
    pts = pts or _pts()
    bands = bands or _bands()
    plans = rf.edge_plans(pts, WIDTHS, bands)
    closures = [p for lid in ("race_cw", "race_acw") for p in rf.closure_plans(pts, WIDTHS, bands, lid)]
    kerb = rf.clip_kerbs([_kerb_plan(pts, 80, 120, "L")], closures)[0]
    kerb["run"] = [kerb["stations"][0]["k"], kerb["stations"][-1]["k"]]
    bands["kerbs"] = [{"apex": kerb["apex"], "side": "L", "kind": "outside", "i": kerb["run"][0], "j": kerb["run"][1]}]
    objects, centres, frames = [], {}, {}
    st = rf.stations(pts)
    span = bands["bridge_spans_m"][0]
    bridge = {"hit": 0, "near": 0, "interpolated": 0, "by_span": [{"span_m": span, "hit": 0, "near": 0, "interpolated": 0}]}
    for p in plans + closures:
        name = rf.object_name(p)
        tok = p.get("token") if p["kind"] == "close" else None
        cs = [[round(x, 2), 5.0, round(z, 2)] for (x, z) in (rf._strip_xz(r) for r in p["rings"])]
        centres[name] = cs
        frames[name] = [[round(r["tx"], 5), round(r["tz"], 5), round(r.get("ls", 1.0), 4)] for r in p["rings"]]
        inside = sum(1 for r in p["rings"] if span[0] <= r["s"] <= span[1])
        bridge["hit"] += inside
        bridge["by_span"][0]["hit"] += inside
        ends = []
        for idx, cap in enumerate((p["cap_start"], p["cap_end"])):
            ring = p["rings"][0 if idx == 0 else -1]
            e = {"vertex": ring["k"], "h": ring["h"], "ls": ring.get("ls", 1.0)}
            if p["kind"] == "close" and cap:
                e.update(kind="pin", joins=p["pins"][idx]["joins"], gap_m=0.0)
            else:
                e.update(kind="join" if not cap else "free", joins=None, gap_m=0.0)
            ends.append(e)
        objects.append({"name": name, "kind": p["kind"], "owner": tok, "layout": p.get("layout"),
                        "collection": rf.closure_collection(tok) if tok else rf.COMMON_COLLECTION, "side": p["side"],
                        "street": p["street"], "run": list(p["run"]), "part": p["part"], "rings": len(p["rings"]),
                        "seated": {"hit": len(p["rings"]), "near": 0, "interpolated": 0}, "seat_gap_max_m": 0.0,
                        "caps": [p["cap_start"], p["cap_end"]], "end_kinds": [p["start_kind"], p["end_kind"]],
                        "ends": ends, "fold_skipped_run": 0, "positions": 10 * len(p["rings"]),
                        "faces": 10 * len(p["rings"]), "loops": 40 * len(p["rings"])})
    kname = rf.object_name(kerb)
    centres[kname] = [[round(x, 2), 5.0, round(z, 2)] for (x, z) in (rf.kerb_mid_xz(s, 1.0) for s in kerb["stations"])]
    frames[kname] = [[round(s["tx"], 5), round(s["tz"], 5), round(s.get("ls", 1.0), 4)] for s in kerb["stations"]]
    objects.append({"name": kname, "kind": "kerb", "owner": None, "layout": None, "collection": rf.COMMON_COLLECTION,
                    "side": "L", "sub": "out", "apex": kerb["apex"], "run": kerb["run"], "stations": len(kerb["stations"]),
                    "clip": {"stations_removed": [0, 0], "by": []}, "seated": {"hit": len(kerb["stations"]), "near": 0, "interpolated": 0},
                    "seat_gap_max_m": 0.0, "positions": 4 * len(kerb["stations"]), "faces": 3 * len(kerb["stations"]),
                    "loops": 12 * len(kerb["stations"])})
    rings = sum(len(p["rings"]) for p in plans + closures)
    return {"standin_bands": False, "edge_mode": "road", "barrier_height_m": 1.2,
            "race_prefixes": ["1WALL_RACE", "1KERB_RACE"], "max_rings_per_object": 800,
            "tokens": {"race_cw": "cw", "race_acw": "acw"},
            "totals": {"objects": len(objects), "rings": rings, "kerb_stations": len(kerb["stations"]),
                       "seated_interpolated": 0, "deck_vs_data_max_m": 0.02, "other_deck_above_max_m": 0.0},
            "corners": [], "kerbs_declared_unmatched": [], "failed_runs": [],
            "spawn_clearance": {"race_cw": {"hard": [], "notes": [], "synthesised": False}},
            "bridge_seating": bridge, "other_deck_above": [], "objects": objects, "ring_centres": centres,
            "ring_frames": frames}


def _fixture():
    b = _bands()
    a = _authored(_pts(), b)
    return a, b


def _run(authored, bands, **kw):
    return vr.verify(authored, bands, _pts(), [0.0] * (N + 1), widths=WIDTHS, **kw)


def _obj(a, name):
    return next(o for o in a["objects"] if o["name"] == name)


def _has(r, prefix, *subs):
    return any(f.startswith(prefix) and all(s in f for s in subs) for f in r["fails"])


def test_consistent_v2_authoring_passes_and_counts():
    a, b = _fixture()
    r = _run(a, b)
    assert r["ok"], r["fails"]
    c = r["counts"]
    assert c["edge_objects"] == 4 and c["kerb_objects"] == 1 and c["free_ends"] == 0 and c["pins"] == 8
    assert c["edge_missing"] == {"L": 0, "R": 0} and c["edge_declared_vertices"] == N
    for lid in ("race_cw", "race_acw"):
        row = c["by_layout"][lid]
        assert row["closure_objects"] == 2 and row["closure_runs"] == 2 and row["closure_off_curve_max_m"] < 0.01, row
        assert all(p["far_line_m"] is not None and p["far_line_m"] < 0.01 for p in row["pins"]), row["pins"]
    assert c["pin_gap_max_m"] < 0.01 and c["bridge_seating"]["hit"] > 0
    assert c["kerb_closure_clear_m"]["1KERB_race_100_out"][0] >= 0.05 and c["kbar_objects"] == 0


def test_c_prime_closure_rings_on_the_declared_line_and_pinned():
    a, b = _fixture()
    name = "1WALL_race_close_cw_alvarado_40_0"
    p = a["ring_centres"][name][20]
    a["ring_centres"][name][20] = [p[0] * 1.003, p[1], p[2] * 1.003]          # ~0.3 m off the line
    assert _has(_run(a, b), "C': race_cw: 1 closure rings stand more than")
    a, b = _fixture()
    a["ring_centres"][name] = a["ring_centres"][name][:-3]                   # stops 3 rings short of its pin
    a["ring_frames"][name] = a["ring_frames"][name][:-3]
    r = _run(a, b)
    assert _has(r, "C': " + name, "last ring", "off the declared far curb-strip line"), r["fails"]
    a, b = _fixture()
    b["corridors"]["race_acw"]["zone_by_vertex"][60] = "box"                  # the declaration puts a closure in a box
    assert _has(_run(a, b), "C': race_acw: the declaration puts closure vertices in a BOX")
    a, b = _fixture()
    a["objects"] = [o for o in a["objects"] if o["name"] != "1WALL_race_close_acw_college_110_0"]
    assert _has(_run(a, b), "C': race_acw: declared closure run v110-v190 has no closure object")


def test_d_every_vertex_both_sides_bridges_included():
    a, b = _fixture()
    name = "1WALL_race_edge_L_alvarado_0_0"
    cs = a["ring_centres"][name]
    k_of = [vr.VertexGrid(_pts()[:N]).nearest(c[0], c[2]) for c in cs]
    keep = [i for i, k in enumerate(k_of) if not (SPAN[0] <= k <= SPAN[1])]  # the strip lifted off the bridge
    a["ring_centres"][name] = [cs[i] for i in keep]
    a["ring_frames"][name] = [a["ring_frames"][name][i] for i in keep]
    r = _run(a, b)
    assert _has(r, "D: edge L", "without a ring", "bridge spans included"), r["fails"]
    # a declared trim excuses exactly those vertices (a SET check)
    b["edge_corners"] = [{"side": "L", "in_vertex": SPAN[0] - 1, "out_vertex": SPAN[1] + 1,
                          "removed": list(range(SPAN[0], SPAN[1] + 1)), "xz": cs[keep[SPAN[0] - 1]][::2]}]
    assert not _has(_run(a, b), "D: edge L", "without a ring")


def test_e_kerbs_declared_and_clear_of_every_closure():
    a, b = _fixture()
    assert _run(a, b)["ok"]
    b["kerbs"][0]["i"] -= 3                                                   # the declaration's i/j moved
    assert _has(_run(a, b), "E: 1KERB_race_100_out: authored run")
    a, b = _fixture()
    kn = "1KERB_race_100_out"
    # slide the kerb back over race_cw's pin at v90: its footprint now crosses the closure funnel
    pts = _pts()
    over = rf.clip_kerbs([_kerb_plan(pts, 86, 100, "L")], [])[0]
    a["ring_centres"][kn] = [[round(x, 2), 5.0, round(z, 2)] for (x, z) in (rf.kerb_mid_xz(s, 1.0) for s in over["stations"])]
    a["ring_frames"][kn] = [[s["tx"], s["tz"], 1.0] for s in over["stations"]]
    r = _run(a, b)
    assert _has(r, "E: " + kn, "race_cw's authored closure", "a kerb under a wall"), r["fails"]
    a, b = _fixture()
    _obj(a, kn)["sub"] = "in"
    assert _has(_run(a, b), "E: declared kerbs")


def test_j_zero_free_ends():
    a, b = _fixture()
    o = _obj(a, "1WALL_race_edge_R_college_100_0")
    o["caps"] = [True, False]
    o["ends"][0]["kind"] = "free"
    assert _has(_run(a, b), "J: 1 free strip / closure ends")
    a, b = _fixture()
    name = "1WALL_race_edge_R_college_100_0"
    a["ring_centres"][name] = a["ring_centres"][name][2:]                     # its start no longer meets the loop
    a["ring_frames"][name] = a["ring_frames"][name][2:]
    assert _has(_run(a, b), "J: " + name, "`join` but no neighbour")
    a, b = _fixture()
    name = "1WALL_race_close_cw_college_110_0"
    c0 = a["ring_centres"][name][0]
    a["ring_centres"][name][0] = [c0[0] * 0.997, c0[1], c0[2] * 0.997]        # the pin ring 0.3 m inward
    assert _has(_run(a, b), "J: " + name, "pinned start stands", "off the authored edge_L strip")
    a, b = _fixture()
    _obj(a, name)["ends"][1]["h"] = 0.3                                       # a tapered closure end
    assert _has(_run(a, b), "J: " + name, "not full height")


def test_k_ownership_tokens_and_collections():
    a, b = _fixture()
    name = "1WALL_race_close_acw_alvarado_40_0"
    o = _obj(a, name)
    o["collection"] = "RACE"                                                  # a closure in the common collection
    assert _has(_run(a, b), "K: " + name, "not RACE_CLOSE_ACW")
    a, b = _fixture()
    _obj(a, name)["owner"] = "cw"
    assert _has(_run(a, b), "K: " + name, "record owner")
    a, b = _fixture()
    new = name.replace("_acw_", "_xx_")
    a["ring_centres"][new] = a["ring_centres"].pop(name)
    a["ring_frames"][new] = a["ring_frames"].pop(name)
    _obj(a, name)["name"] = new
    assert _has(_run(a, b), "K: " + new, "not declared")
    a, b = _fixture()
    _obj(a, "1WALL_race_edge_L_alvarado_0_0")["owner"] = "cw"
    assert _has(_run(a, b), "K: 1WALL_race_edge_L_alvarado_0_0", "common furniture records an owner")
    a, b = _fixture()
    a["objects"].append(dict(_obj(a, "1WALL_race_edge_L_alvarado_0_0"), name="1WALL_racecol_0", kind="collider"))
    a["ring_centres"]["1WALL_racecol_0"] = [[0, 0, 0], [1, 0, 0]]
    assert _has(_run(a, b), "K: 1WALL_racecol_0", "no known kind")


def test_l_nothing_interpolated_on_a_bridge():
    a, b = _fixture()
    a["bridge_seating"]["interpolated"] = 2
    assert _has(_run(a, b), "L: 2 rings inside the declared bridge spans")
    a, b = _fixture()
    a["bridge_seating"]["by_span"][0].update(hit=0, near=0)
    assert _has(_run(a, b), "L: no strip ring seated on the declared bridge span")
    a, b = _fixture()
    del a["bridge_seating"]
    assert _has(_run(a, b), "L: race_authored.json carries no bridge_seating")
    b["bridge_spans_m"] = []                                                  # no bridge declared: nothing to measure
    assert not _has(_run(a, b), "L:")


def test_m_mouths_sealed_by_the_strip_and_behind_the_closure():
    a, b = _fixture()
    assert _run(a, b)["counts"]["mouths"][0]["strip_off_m"] < 0.02
    b["closed_mouths"][0]["polyline_xyz_m"] = [[p[0] * 1.004, p[1], p[2] * 1.004] for p in b["closed_mouths"][0]["polyline_xyz_m"]]
    assert _has(_run(a, b), "M: mouth side_st at v150 (L)", "the mouth is open")
    a, b = _fixture()
    b["corridors"]["race_acw"]["mouths"][0]["policy"] = "behind_closure"     # race_acw's closure is on the other side
    assert _has(_run(a, b), "M: race_acw: mouth v150 (L)", "lane", "reaches past the closure")
    a, b = _fixture()
    b["corridors"]["race_cw"]["mouths"] = []
    assert _has(_run(a, b), "M: race_cw: mouth at v150 (L) has no declared policy")
    a, b = _fixture()
    b["corridors"]["race_cw"]["mouths"][0]["policy"] = "open"
    assert _has(_run(a, b), "M: race_cw: mouth v150 (L): unknown policy")
    a, b = _fixture()
    b["corridors"]["race_cw"]["mouths"][0]["policy"] = "sealed_far_strip"   # the other agent's third policy: the strip
    assert not _has(_run(a, b), "M:")


def test_n_the_centre_chain_is_retired():
    a, b = _fixture()
    a["objects"].append(dict(_obj(a, "1WALL_race_edge_L_alvarado_0_0"), name="1WALL_race_kbar_t_61_0", kind="chain"))
    a["ring_centres"]["1WALL_race_kbar_t_61_0"] = [[0, 0, 0], [1, 0, 0]]
    assert _has(_run(a, b), "N: 1 centre-chain objects")
    a, b = _fixture()
    b["centre_w_by_vertex"][10] = 0.67
    assert _has(_run(a, b), "N: barrier_bands.json still declares centre_w_by_vertex")
    a, b = _fixture()
    b.pop("corridors")
    assert _has(_run(a, b), "K: barrier_bands.json declares no corridors")


def test_budgets_seating_and_provenance():
    a, b = _fixture()
    a["objects"][0]["seat_gap_max_m"] = 0.2
    a["objects"][1]["rings"] = 901
    a["objects"][2]["loops"] = 50_000
    r = _run(a, b)
    f = " | ".join(r["fails"])
    assert "seating gap" in f and "901 rings" in f and "flat render verts" in f, f
    a, b = _fixture()
    a["standin_bands"] = True
    assert not _run(a, b)["ok"] and _run(a, b, allow_standin=True)["ok"]
    a, b = _fixture()
    a["edge_mode"] = "walk"
    assert any("edge_mode" in x for x in _run(a, b)["fails"])
    a, b = _fixture()
    a["totals"]["seated_interpolated"] = 500
    assert any("interpolation" in x for x in _run(a, b)["fails"])
    a, b = _fixture()
    a["spawn_clearance"]["race_cw"]["hard"] = ["AC_START_1 overlaps 1WALL_race_edge_R"]
    assert _has(_run(a, b), "F: race_cw: a spawn overlaps")


def test_h_density_and_i_inside_out_on_strips_and_closures():
    a, b = _fixture()
    c = _run(a, b)["counts"]
    assert c["chord_max_m"] < 0.02 and c["chord_spans_over"] == 0 and c["inside_out_spans"] == 0
    name = "1WALL_race_close_cw_college_110_0"
    cs = a["ring_centres"][name]
    a["ring_centres"][name] = cs[:20] + cs[26:]                               # six rings gone: a 7-interval chord
    a["ring_frames"][name] = a["ring_frames"][name][:20] + a["ring_frames"][name][26:]
    r = _run(a, b)
    assert any(x.startswith("H: ") for x in r["fails"]) and r["counts"]["chord_worst"]["object"] == name, r["fails"]
    a, b = _fixture()
    fr = a["ring_frames"][name][30]
    a["ring_frames"][name][30] = [-fr[0], -fr[1], fr[2]]                      # one closure ring's profile turned round
    r = _run(a, b)
    assert r["counts"]["inside_out_spans"] == 2 and name in r["counts"]["inside_out_by_object"]


def test_cli_writes_the_report_and_exits_nonzero_on_a_miss():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _pts()
    a, b = _fixture()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": WIDTHS}))
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": [0.0] * (N + 1)}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(b))
    (d / "data" / "race_authored.json").write_text(json.dumps(a))
    assert vr.main([str(d)]) == 0
    rep = json.loads((d / "data" / "race_verify.json").read_text(encoding="utf-8"))
    assert rep["ok"] is True and set(rep["counts"]["by_layout"]) == {"race_cw", "race_acw"}
    bad = copy.deepcopy(a)
    bad["failed_runs"] = ["1WALL_race_close_cw_alvarado_40_0"]
    (d / "data" / "race_authored.json").write_text(json.dumps(bad))
    assert vr.main([str(d)]) == 1
    assert json.loads((d / "data" / "race_verify.json").read_text(encoding="utf-8"))["ok"] is False


# --- F (re-measured from the dummies that ship) and G (lamp masts vs the strips and closures) --------
# Forward travel is anticlockwise, so + lateral (left) points at the centre; the curb strip's road-side face is at
# |lat| = W/2 - 0.82 = 9.18 m, its back at W/2 - 0.15 = 9.85 m.

def _radial(k, r):
    """a point r metres OUTWARD (right of forward travel) from vertex k"""
    a = 2 * math.pi * k / N
    return [round((R + r) * math.cos(a), 4), 5.4, round((R + r) * math.sin(a), 4)]


def _dummies(slots, kind="race"):
    d = {"_layout": "race_cw", "_kind": kind, "_yaw_deg": {}, "AC_TIME_0_L": _radial(20, -9.7)}
    d.update(slots)
    return d


def _run_fg(spawns=None, lamps=None, bands=None, **kw):
    return vr.verify(None, bands or _bands(), _pts(), [0.0] * (N + 1), pre_author=True, widths=WIDTHS,
                     spawns=spawns, lamps=lamps, **kw)


def test_spawn_clearance_is_remeasured_against_the_strips_and_the_lane():
    ok = _dummies({"AC_START_0": _radial(10, 7.0), "AC_START_1": _radial(12, 7.5), "AC_PIT_0": _radial(30, 7.0)})
    r = _run_fg({"race_cw": ok})
    assert r["ok"], r["fails"]
    assert abs(r["counts"]["spawn_min_clear_m"]["race_cw"] - 0.73) < 1e-3          # 9.18 - (7.5 + 0.95)
    assert [s["name"] for s in r["counts"]["spawn_slots"]["race_cw"]] == ["AC_PIT_0", "AC_START_0", "AC_START_1"]
    tight = _dummies({"AC_START_1": _radial(12, 8.0)})                              # 0.23 m: hard
    r = _run_fg({"race_cw": tight})
    assert _has(r, "F: race_cw: AC_START_1", "0.23 m clear of the edge-strip face"), r["fails"]
    over = _dummies({"AC_START_1": _radial(12, 8.5)})
    assert any("OVERLAPS" in f for f in _run_fg({"race_cw": over})["fails"])
    # in a closure zone the lane's far face is the closure: race_cw's at v60 stands 2.0 m LEFT of the centreline
    # (face at +1.665): a car at 1.0 m left of the centreline is 1.665 - (1.0 + 0.95) = -0.285 -> outside its lane
    lane = _dummies({"AC_START_0": _radial(60, -1.0)})
    r = _run_fg({"race_cw": lane})
    assert _has(r, "F: race_cw: AC_START_0", "lane face", "OVERLAPS"), r["fails"]
    assert _run_fg({"race_acw": dict(lane, _layout="race_acw")})["ok"]             # race_acw's lane is the left side
    assert any("no data/dummies_race_acw.json" in f for f in _run_fg({"race_acw": None})["fails"])
    synth = dict(ok, _synthesised=True)
    assert any("SYNTHESISED" in f for f in _run_fg({"race_cw": synth})["fails"])


def test_lamp_masts_stand_outside_every_strip_and_closure_footprint():
    # heads 1.8 m road-ward of the mast (author_lamps_blend ARM_M): head at R + 11.0 -> mast at R + 12.8
    clear = [_radial(30, 11.0), _radial(170, 11.0)]
    r = _run_fg(lamps=clear, mast_r_m=0.5)
    assert r["ok"], r["fails"]
    c = r["counts"]
    assert c["lamps"] == 2 and c["lamps_checked"] == 2 and c["lamp_arm_m"] == 1.8
    assert abs(c["lamp_min_margin_m"] - (12.8 - 9.85 - 0.5)) < 1e-3, c["lamp_min_margin_m"]
    inside = clear + [_radial(60, 7.8)]                    # mast at R + 9.6: inside [9.18, 9.85]
    r = _run_fg(lamps=inside, mast_r_m=0.5)
    assert not r["ok"] and _has(r, "G: lamp 2 at v60", "inside the edge strip footprint"), r["fails"]
    # a mast standing on race_acw's closure (2.0 m RIGHT of the centreline at v60): head 1.8 m further out
    on_closure = [_radial(60, 2.0 - 1.8)]
    r = _run_fg(lamps=on_closure, mast_r_m=0.3)
    assert _has(r, "G: lamp 0 at v60", "closure_race_acw"), r["fails"]
    assert r["counts"]["lamp_min_vs_closure"]["closure"] == "closure_race_acw"


def test_lamp_constants_come_from_the_author_tool_and_the_model():
    assert vr._author_lamps_constant("ARM_M", -1.0) == 1.8
    assert vr._author_lamps_constant("POST_H", -1.0) == 11.5
    assert vr._author_lamps_constant("NOT_THERE", -1.0) == -1.0
    r = vr.mast_radius_m(11.5)
    assert 0.5 < r < 0.7, r                                # the base plate corner, 0.585 m at 11.5 m


def test_race_layout_spawns_reads_every_race_dummies_file():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "dummies_race_cw.json").write_text(json.dumps({"_kind": "race", "AC_START_0": [0, 0, 0]}))
    (d / "dummies_street.json").write_text(json.dumps({"_kind": "street", "AC_START_0": [0, 0, 0]}))
    cfg = {"layouts": [{"id": "street"}, {"id": "race_cw", "race_furniture": True}, {"id": "race_acw", "race_furniture": True}]}
    sp = vr.race_layout_spawns(d, cfg)
    assert set(sp) == {"race_cw", "race_acw"} and sp["race_acw"] is None and sp["race_cw"]["_kind"] == "race"
    assert set(vr.race_layout_spawns(d, {"layouts": [{"id": "full"}]})) == {"race_cw"}


def test_cli_pre_author_needs_no_authored_file():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _pts()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": WIDTHS}))
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": [0.0] * (N + 1)}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_bands()))
    (d / "data" / "lights.local.json").write_text(json.dumps({"lampheads": [_radial(30, 11.0)]}))
    (d / "data" / "dummies_race_cw.json").write_text(json.dumps(_dummies({"AC_START_1": _radial(12, 7.5)})))
    out = d / "pre.json"
    assert vr.main([str(d), "--pre-author", "--out", str(out)]) == 0
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["ok"] and "race_cw" in rep["counts"]["spawn_slots"] and rep["counts"]["lamps_checked"] == 1
    assert not (d / "data" / "race_verify.json").exists()
    (d / "data" / "dummies_race_cw.json").write_text(json.dumps(_dummies({"AC_START_1": _radial(12, 8.0)})))
    assert vr.main([str(d), "--pre-author", "--out", str(out)]) == 1


# --- 0049 fix round: E kerb under a road sheet / dropped kerbs; G scenery (TreeFX trunks + sign posts) ----------

def test_e_a_kerb_under_another_road_sheet_fails_and_a_dropped_kerb_may_not_be_authored():
    a, b = _fixture()
    kn = "1KERB_race_100_out"
    r = _run(a, b)
    assert r["ok"] and any("no under_road measure" in w for w in r["warnings"]), r["warnings"]   # older authored file
    _obj(a, kn)["under_road"] = {"stations": 0, "max_m": 0.0, "vertices": []}
    r = _run(a, b)
    assert r["ok"] and r["counts"]["kerb_under_road"] == {kn: 0} and not any("under_road" in w for w in r["warnings"])
    _obj(a, kn)["under_road"] = {"stations": 9, "max_m": 0.135, "vertices": [99, 100]}       # laid across a ribbon fold
    r = _run(a, b)
    assert _has(r, "E: " + kn, "9 stations sit UNDER another ROAD sheet", "0.135", "race.kerbs.trims"), r["fails"]
    # the declaration drops the kerb, the author still sweeps it: both the set check and the drop check fire
    a, b = _fixture()
    b["kerbs_dropped"] = [dict(b["kerbs"][0], why="on a fold")]
    b["kerbs"] = []
    r = _run(a, b)
    assert _has(r, "E: the outside kerb at v100 is declared DROPPED but was authored"), r["fails"]
    assert _has(r, "E: declared kerbs")
    assert r["counts"]["kerbs_dropped"] == [[100, "outside"]]


def _run_scenery(items, bands=None):
    return vr.verify(None, bands or _bands(), _pts(), [0.0] * (N + 1), pre_author=True, widths=WIDTHS, scenery=items,
                     scenery_source="test")


def _item(kind, k, r_out, rr=None):
    p = _radial(k, r_out)
    return {"kind": kind, "id": f"{kind}@{k}/{r_out}", "x": p[0], "z": p[2],
            "r": rr if rr is not None else (vr.TREE_TRUNK_R_M if kind == "tree" else vr.SIGN_POST_R_M)}


def test_g_scenery_trunks_and_posts_stay_out_of_every_lane_and_wall():
    # + lateral = toward the centre; _radial(k, r) stands r m OUTWARD (lat -r). Curb strips |lat| 9.18-9.85; at v60
    # race_cw's closure stands at lat +2.0 (its lane -9.18 .. +1.665), race_acw's at -2.0 (its lane -1.665 .. +9.18)
    clear = [_item("tree", 60, 11.0), _item("tree", 150, 12.0), _item("sign", 30, 10.9), _item("tree", 60, 40.0)]
    r = _run_scenery(clear)
    assert r["ok"], r["fails"]
    c = r["counts"]
    assert c["scenery_items"] == {"tree": 3, "sign": 1} and c["scenery_beside"] == 3 and c["scenery_hits"] == 0
    assert abs(c["scenery_min"]["race_cw"]["margin_m"] - (11.0 - 9.85 - 0.30)) < 1e-3, c["scenery_min"]
    # a palm in race_cw's lane (lat -5): in race_acw's dead lane behind its closure, which is fine for race_acw
    r = _run_scenery(clear + [_item("tree", 60, 5.0)])
    assert _has(r, "G: scenery: race_cw: tree tree@60/5.0 at v60", "in the lane"), r["fails"]
    assert not _has(r, "G: scenery: race_acw"), r["fails"]
    # a sign post inside the curb strip: both layouts (the strips are common)
    r = _run_scenery([_item("sign", 120, 9.5)])
    assert _has(r, "G: scenery: race_cw: sign", "inside the curb strip") and _has(r, "G: scenery: race_acw: sign",
                                                                                  "inside the curb strip"), r["fails"]
    # a trunk ON race_acw's closure (lat -2.0): inside race_acw's wall, in race_cw's lane
    r = _run_scenery([_item("tree", 60, 2.0)])
    assert _has(r, "G: scenery: race_acw: tree", "inside the closure") and _has(r, "G: scenery: race_cw: tree", "in the lane")
    # in an open box (v100) the lane is the whole road: a bush on the road is in both lanes
    r = _run_scenery([_item("tree", 100, 0.0)])
    assert _has(r, "G: scenery: race_cw:", "in the lane") and _has(r, "G: scenery: race_acw:", "in the lane")


def test_g_scenery_reads_trees_txt_in_the_kn5_frame_and_sign_posts():
    p = _radial(60, 5.0)
    txt = ("configure: seed = 20261013\nconfigure: size variance = 1, 1\n"
           f"tree: PalmV1.bin; pos={p[0]:.2f}, 5.00, {-p[2]:.2f}; angle = 10; size = 0.80\n"
           "tree: Sage.bin; pos=0.00, 1.00, -0.00; angle = 0; size = 1.00\n")
    items = vr.tree_items_from_txt(txt)
    assert [i["id"] for i in items] == ["PalmV1.bin#0", "Sage.bin#1"]
    assert abs(items[0]["x"] - p[0]) < 0.01 and abs(items[0]["z"] - p[2]) < 0.01 and items[0]["r"] == vr.TREE_TRUNK_R_M
    signs = {"signs": [{"id": "M1", "base_xz": [1.0, 2.0]}, {"id": "M2"}]}
    assert vr.sign_items(signs) == [{"kind": "sign", "id": "M1", "x": 1.0, "z": 2.0, "r": vr.SIGN_POST_R_M}]


def test_cli_scenery_only_judges_the_written_trees_txt():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    pts = _pts()
    (d / "data" / "centerline.local.json").write_text(json.dumps({"points_xyz_m": [list(p) for p in pts], "widths_m": WIDTHS}))
    (d / "data" / "median_bands.json").write_text(json.dumps({"island_w_by_vertex": [0.0] * (N + 1)}))
    (d / "data" / "barrier_bands.json").write_text(json.dumps(_bands()))
    s = _radial(30, 10.4)
    (d / "data" / "signs.local.json").write_text(json.dumps({"signs": [{"id": "M1", "base_xz": [s[0], s[2]]}]}))
    ok, bad = _radial(60, 11.0), _radial(60, 5.0)
    trees = d / "trees.txt"
    trees.write_text(f"tree: PalmV1.bin; pos={ok[0]:.2f}, 5.00, {-ok[2]:.2f}; angle = 1; size = 1.00\n", encoding="utf-8")
    assert vr.main([str(d), "--scenery-only", "--trees", str(trees)]) == 0      # no race_authored.json needed
    rep = json.loads((d / "data" / "race_verify.scenery.json").read_text(encoding="utf-8"))
    assert rep["ok"] and rep["counts"]["scenery_items"] == {"tree": 1, "sign": 1} and "spawn_slots" not in rep["counts"]
    assert not (d / "data" / "race_verify.json").exists()
    trees.write_text(trees.read_text(encoding="utf-8") +
                     f"tree: PalmV2.bin; pos={bad[0]:.2f}, 5.00, {-bad[2]:.2f}; angle = 1; size = 1.00\n", encoding="utf-8")
    assert vr.main([str(d), "--scenery-only", "--trees", str(trees)]) == 1
    rep = json.loads((d / "data" / "race_verify.scenery.json").read_text(encoding="utf-8"))
    assert any(f.startswith("G: scenery: race_cw: tree PalmV2.bin#1") for f in rep["fails"]), rep["fails"]
