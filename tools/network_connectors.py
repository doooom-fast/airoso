"""A road NETWORK's other carriageways as LM-engine connectors (ledger 0080 phase 2, the SD freeway on Lake Murray's
engine).

The LM engine sweeps one line plus ``data/connectors.local.json`` (side streets, each with its own 3DEP; Lake Murray's
Del Cerro trunk is the precedent). tools/network_line.py made the network draft's reference line (I 8 eastbound) the
port's line; this tool makes each further declared carriageway a connector record, read from the SAME draft:

  chain        scripts.geometry.network_reference.resolve (the line's own resolver, unchanged): the longest directed
               chain of non-ramp edges of ``ref`` driving ``direction``, every point a vertex of a built edge;
  x / z        the chain's at-grade line (the edge's OSM vertices, projected by the draft);
  Y            the carriageway's OWN 3DEP (network.elevation.json z_raw_m at each [edge, vertex]) de-spiked and smoothed
               as network_line does (network_elev's 33 m median + 45 m mean), no grade cap, no node pin; and ON A DECK the
               deck as measured: the USGS lidar's class-17 returns (tools/network_deck_lidar.py,
               deck_profiles.lidar.json) interpolated along the edge. A bridged run (OSM layer != 0) with no reading runs
               straight between the measured readings either side of it; with no measured end it is levelled crest to
               crest as every port's unmeasured deck (scripts.capture.evidence.level_bridge_decks). Reported per
               connector; nothing comes from the draft's layer x 5.5 m model, nothing stays in the 3DEP dive;
  widths       the draft's per-vertex widths, steps flared at ``width_taper`` (widening only; the line's rule);
  deck         [first, last] vertex ranges where Y is a lidar deck (decks_all: + the levelled ones; the rails run on
               decks_all): what the assembler's terrain and engine-july's pin
               must not treat as ground (ledger 0080 map rows "Flyovers");
  terrain_xyz_m  the 3DEP line under the carriageway (the draft's at_grade_xyz_m Y), for the terrain passes.

    python tools/network_connectors.py <network-draft-project-dir> <out-dir> <track.config.json>

The config's ``lm_intake.network_connectors`` lists the carriageways: [{"name", "ref", "direction",
"bridge_max_edges"?}]. Writes <out-dir>/connectors.local.json (the intake copies it when lm_intake.connectors is
true) and <out-dir>/network_connectors.json (chains, decks, md5s). Stdlib only. Lake Murray never runs it.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.geometry import network_reference  # noqa: E402
from tools.network_line import _median_mean  # noqa: E402

BANK_SEEK_M = 80.0    # scripts.capture.evidence.level_bridge_decks' BANK_SEEK_M: how far out a deck's bank crest is sought
MATCH_M = 6.0        # [invented] a vertex takes a deck reading only with lidar stations within this along the edge
#                       (the readings are every 5 m: one station either side)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _cum(coords, lat0):
    from scripts.geometry.projection import _meters_per_degree
    m_lon, m_lat = _meters_per_degree(lat0)
    s = [0.0]
    for a, b in zip(coords, coords[1:]):
        s.append(s[-1] + math.hypot((b[0] - a[0]) * m_lon, (b[1] - a[1]) * m_lat))
    return s


def _taper(pts, widths, rate):
    st = [0.0]
    for a, b in zip(pts, pts[1:]):
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    hw = [w / 2.0 for w in widths]
    reach = (max(widths) - min(widths)) / 2.0 / rate
    new = list(hw)
    for i in range(len(hw)):
        j0 = bisect.bisect_left(st, st[i] - reach)
        j1 = bisect.bisect_right(st, st[i] + reach)
        for j in range(j0, j1):
            if hw[j] > new[i]:
                new[i] = max(new[i], hw[j] - rate * abs(st[i] - st[j]))
    return [round(2 * h, 3) for h in new], sum(1 for a, b in zip(hw, new) if b - a > 5e-4)


def one_way_paint(widths, *, edge_inset=0.55, lane_w=3.65, line_w=0.12, max_lanes_side=6):
    """The line's paint (v021 ``lane_markings(center_yellow=False)``: white edge lines ``edge_inset`` inside each edge,
    dashed white dividers every ``lane_w`` from the centre, clipped inside the edge lines) as an authored connector
    ``paint`` record, so the assembler's ``connector_markings`` paints a one-way carriageway with no yellow centre
    line (its plain-connector default is a two-way street's double yellow). The numbers are lane_markings' defaults."""
    lines = [{"color": "white", "dash": False, "off": [round(w / 2 - edge_inset, 3) for w in widths]},
             {"color": "white", "dash": False, "off": [round(-(w / 2 - edge_inset), 3) for w in widths]}]
    for k in range(1, max_lanes_side + 1):
        for sg in (1, -1):
            off = [sg * k * lane_w if k * lane_w + line_w / 2 <= w / 2 - edge_inset else None for w in widths]
            if any(o is not None for o in off):
                lines.append({"color": "white", "dash": True, "off": off})
    return {"lines": lines, "_doc": "one-way carriageway: tools/network_connectors.one_way_paint (the line's lane_markings)"}


def deck_heights(chain_src, coords, layers, lidar, elev0):
    """Per chain vertex: (Y of the measured deck or None, how). ``lidar`` = {edge: [(s, deck z)]} sorted, readings only."""
    out = []
    for e, v in chain_src:
        lp = layers.get(e) or []
        bridged = v < len(lp) and lp[v] != 0
        rd = lidar.get(e) or []
        if not rd:
            out.append((None, "bridged, no reading" if bridged else ""))
            continue
        s_v = coords[e][1][v]
        ss = [r[0] for r in rd]
        k = bisect.bisect_left(ss, s_v)
        lo = rd[k - 1] if k > 0 else None
        hi = rd[k] if k < len(rd) else None
        if lo and hi and hi[0] - lo[0] <= MATCH_M * 2 + 1e-6:
            t = 0.0 if hi[0] <= lo[0] else (s_v - lo[0]) / (hi[0] - lo[0])
            out.append((lo[1] + (hi[1] - lo[1]) * t - elev0, "lidar"))
        elif lo and abs(s_v - lo[0]) <= MATCH_M / 2 and not hi:
            out.append((lo[1] - elev0, "lidar"))
        elif hi and abs(hi[0] - s_v) <= MATCH_M / 2 and not lo:
            out.append((hi[1] - elev0, "lidar"))
        else:
            out.append((None, "bridged, no reading" if bridged else ""))
    return out


def _prepend_head(r: dict, head: dict, edges_rec: dict) -> None:
    """A declared HEAD (ledger 0080 2a, WB's east end): part of an edge whose travel the draft left undecided, run in
    its decided direction and put in front of the resolved chain. ``head`` = {"edge", "from_vertex", "to_vertex"}: the
    edge's vertices from_vertex .. to_vertex (either order = the travel), whose last must be the chain's first point
    (or one vertex short of it: the shared node is written once). The decision and its evidence are the config's
    (``_why``); the resolver's own rule (an undecided edge is never guessed) is unchanged."""
    rec = next((e for e in edges_rec["edges"] if int(e["id"]) == int(head["edge"])), None)
    if rec is None:
        raise SystemExit(f"[network_connectors] head edge {head['edge']} is not in the draft")
    a, b = int(head["from_vertex"]), int(head["to_vertex"])
    idx = list(range(a, b - 1, -1)) if a > b else list(range(a, b + 1))
    g = rec["at_grade_xyz_m"]
    first = r["grade"][0]
    nxt = b - 1 if a > b else b + 1
    if 0 <= nxt < len(g) and math.dist((g[nxt][0], g[nxt][2]), (first[0], first[2])) > 1e-3:
        raise SystemExit(f"[network_connectors] head edge {head['edge']} vertex {nxt} is not the chain's first point")
    gp = [list(g[i]) for i in idx]
    add = [0.0]
    for p, q in zip(gp, gp[1:] + [first]):
        add.append(add[-1] + math.hypot(q[0] - p[0], q[2] - p[2]))
    sh = add[-1]
    r["grade"] = gp + r["grade"]
    r["widths"] = [float(rec["widths_m"][i]) for i in idx] + list(r["widths"])
    r["source_by_vertex"] = [[int(rec["id"]), i] for i in idx] + r["source_by_vertex"]
    r["stations"] = add[:-1] + [s + sh for s in r["stations"]]
    r["chain"] = [int(rec["id"])] + r["chain"]
    r["how"] += f"; head: edge {rec['id']} vertices {a}..{b} ({sh:.0f} m, declared)"


def build(draft: Path, out: Path, cfg_path: Path) -> dict:
    d = draft / "data" if (draft / "data").is_dir() else draft     # a draft project, or the committed copy
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    li = cfg.get("lm_intake") or {}
    specs = li.get("network_connectors") or []
    if not specs:
        raise SystemExit("[network_connectors] lm_intake.network_connectors is empty")
    rate = li.get("width_taper")
    fc = json.loads((d / "network.geojson").read_text(encoding="utf-8"))
    edges_rec = json.loads((d / "network.edges.local.json").read_text(encoding="utf-8"))
    elev = json.loads((d / "network.elevation.json").read_text(encoding="utf-8"))
    zraw = {int(r["id"]): r["z_raw_m"] for r in elev["edges"]}
    nloc = json.loads((d / "network.local.json").read_text(encoding="utf-8"))
    elev0 = float(nloc["origin"]["elev_m"])
    coords, layers = {}, {}
    for f in fc["features"]:
        c = f["geometry"]["coordinates"]
        coords[int(f["properties"]["id"])] = (c, _cum(c, c[0][1]))
        layers[int(f["properties"]["id"])] = f["properties"].get("layer_profile") or []
    lid_p = out / "deck_profiles.lidar.json"
    lidar, lid_md5 = {}, None
    if lid_p.exists():
        lid = json.loads(lid_p.read_text(encoding="utf-8"))
        lid_md5 = _md5(lid_p)
        for r in lid["stations"]:
            if r[6] is not None:
                lidar.setdefault(int(r[0]), []).append((float(r[1]), float(r[6])))
        for k in lidar:
            lidar[k].sort()
    recs, rep = [], []
    for sp in specs:
        decl = {"ref": sp["ref"], "direction": sp["direction"],
                "bridge_max_edges": int(sp.get("bridge_max_edges", 2))}
        r = network_reference.resolve(decl, fc, edges_rec)
        head = sp.get("head")
        if head:
            _prepend_head(r, head, edges_rec)
        grade, src, widths = r["grade"], r["source_by_vertex"], list(r["widths"])
        raw = [float(zraw[int(e)][int(v)]) for e, v in src]
        L = r["stations"][-1]
        spacing = L / max(1, len(grade) - 1)
        y3 = [z - elev0 for z in _median_mean(raw, spacing)]
        dk = deck_heights([(int(e), int(v)) for e, v in src], coords, layers, lidar, elev0)
        ys = [yd if yd is not None else y for y, (yd, _h) in zip(y3, dk)]
        mask = [yd is not None for yd, _h in dk]
        how = [h for _yd, h in dk]
        # a bridged run (OSM layer != 0) the lidar does not reach: between two measured readings of the same deck the
        # deck runs straight from one to the other; with a measured end missing, the engine's rule for an unmeasured
        # deck (scripts.capture.evidence.level_bridge_decks, every port's capture.bridges: level crest to crest over
        # the bare-earth dip). Never the 3DEP dive, never the draft's layer x 5.5 m.
        st = r["stations"]
        n = len(ys)
        k = 0
        spans_lvl = []
        while k < n:
            if how[k] != "bridged, no reading":
                k += 1
                continue
            j = k
            while j + 1 < n and how[j + 1] == "bridged, no reading":
                j += 1
            a, b = k - 1, j + 1
            if a >= 0 and b < n and mask[a] and mask[b]:
                for q in range(k, j + 1):
                    t = (st[q] - st[a]) / max(1e-9, st[b] - st[a])
                    ys[q] = ys[a] + (ys[b] - ys[a]) * t
                    mask[q] = True
                    how[q] = "lidar, spanned between readings"
            else:
                spans_lvl.append((k, j))
            k = j + 1
        if spans_lvl:
            from scripts.capture import evidence
            lv = evidence.level_bridge_decks([(g[0], y, g[2]) for g, y in zip(grade, ys)],
                                             [(0.5 * (st[a] + st[b]), max(1.0, st[b] - st[a])) for a, b in spans_lvl])
            for a, b in spans_lvl:
                for q in range(a, b + 1):
                    how[q] = "levelled crest to crest (no lidar)"
            ys = [p[1] for p in lv]
        # THE APPROACHES: off a measured deck's end the 3DEP still reads the earth under the bridge's last span where
        # OSM's bridge way (or the lidar's class 17) stops short of the abutment (I 8 WB s 5,876: deck 17.05, then
        # 14.33, then 17.59 m). The deck end is anchored to the bank crest as every unmeasured deck is
        # (level_bridge_decks' BANK_SEEK_M, 80 m out): an approach point below the straight line from the deck end
        # to the highest point within that reach is raised onto it. Raise only; the deck itself is never moved.
        n_raised = 0
        di = 0
        while di < n:
            if not mask[di]:
                di += 1
                continue
            dj = di
            while dj + 1 < n and mask[dj + 1]:
                dj += 1
            for end, sgn in ((di, -1), (dj, 1)):
                reach = [q for q in range(end + sgn, -1 if sgn < 0 else n, sgn)
                         if abs(st[q] - st[end]) <= BANK_SEEK_M and not mask[q]]
                # stop at the next deck: the reach is this deck's own approach
                cut = []
                for q in reach:
                    cut.append(q)
                    if q + sgn >= 0 and q + sgn < n and mask[q + sgn]:
                        break
                if not cut:
                    continue
                crest = max(cut, key=lambda q: ys[q])
                for q in cut:
                    if (q - crest) * sgn >= 0:
                        break
                    t = (st[q] - st[end]) / (st[crest] - st[end]) if st[crest] != st[end] else 0.0
                    line = ys[end] + (ys[crest] - ys[end]) * t
                    if ys[q] < line - 1e-6:
                        ys[q] = line
                        n_raised += 1
            di = dj + 1
        ys = [round(y, 3) for y in ys]
        def _runs(flags):
            out_, i_ = [], 0
            while i_ < len(flags):
                if flags[i_]:
                    j_ = i_
                    while j_ + 1 < len(flags) and flags[j_ + 1]:
                        j_ += 1
                    out_.append([i_, j_])
                    i_ = j_ + 1
                else:
                    i_ += 1
            return out_
        ranges = _runs(mask)                                              # measured decks
        decks_all = _runs([m or h.startswith("levelled") for m, h in zip(mask, how)])   # + the levelled ones
        unread = sum(1 for h in how if h.startswith("levelled"))
        pts = [[round(g[0], 3), y, round(g[2], 3)] for g, y in zip(grade, ys)]
        nwid = 0
        if rate:
            widths, nwid = _taper(pts, widths, float(rate))
        paint = one_way_paint(widths)
        # the step at each deck end: the measured deck vs the 3DEP approach one vertex out
        ends = []
        for a, b in ranges:
            for k, o in ((a, a - 1), (b, b + 1)):
                if 0 <= o < len(ys):
                    ends.append(round(ys[k] - ys[o], 2))
        recs.append({"name": sp["name"], "kind": "connector", "points_xyz_m": pts, "widths_m": widths,
                     "terrain_xyz_m": [[round(g[0], 3), round(g[1], 3), round(g[2], 3)] for g in grade],
                     "deck": ranges, "decks_all": decks_all, "paint": paint, "source_by_vertex": src, "network": {"ref": sp["ref"], "direction": sp["direction"],
                                                                          "edges": r["chain"]}})
        rep.append({"name": sp["name"], "how": r["how"], "edges": r["chain"], "points": len(pts),
                    "length_m": round(L, 1), "decks": len(ranges),
                    "deck_points": sum(mask), "deck_points_spanned": sum(1 for h in how if h == "lidar, spanned between readings"),
                    "bridged_points_unmeasured_levelled": unread, "levelled_runs": len(spans_lvl), "approach_points_raised_to_crest": n_raised,
                    "deck_end_steps_m": ends,
                    "deck_minus_3dep_max_m": round(max([a - b for a, b, m in zip(ys, y3, mask) if m] or [0.0]), 2),
                    "widths_flared": nwid, "side_check": r["side_check"],
                    "same_ref_off_chain": [u["id"] for u in r["unjudged"] if u["why"].startswith("same road")]})
        print(f"[network_connectors] {sp['name']}: {len(pts)} points, {L:.0f} m, edges {r['chain']}; "
              f"{len(ranges)} lidar deck(s) over {sum(mask)} points, {unread} bridged points without lidar levelled crest to crest ({len(spans_lvl)} run(s))")
    out.mkdir(parents=True, exist_ok=True)
    (out / "connectors.local.json").write_text(json.dumps({"connectors": recs}), encoding="utf-8")
    doc = {"tool": "tools/network_connectors.py", "ledger": "0080 phase 2",
           "draft": str(draft.relative_to(ROOT)) if draft.is_relative_to(ROOT) else str(draft),
           "params": {"match_m": MATCH_M, "width_taper": rate, "_invented": "match_m"},
           "connectors": rep,
           "inputs": {**{f: _md5(d / f) for f in ("network.geojson", "network.edges.local.json", "network.elevation.json")},
                      "deck_profiles.lidar.json": lid_md5},
           "outputs": {"connectors.local.json": _md5(out / "connectors.local.json")}}
    (out / "network_connectors.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve())
