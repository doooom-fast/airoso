"""A race layout's LAP — the one line every race tool counts along (ledger 0054 phase 2 groundwork).

Until now every race tool read exactly ONE lap line, the mainline centreline (data/centerline.local.json), and
counted along it by vertex number: the corridor declaration, the closures, the kerbs, the no-route probes, the
spawns, the AI line, the drive test's lane. Phase 2 (Mission Gorge Speedway) needs a second lap that runs partly
on the loop and partly on the expansion roads. This module is that lap, designed once:

    a STITCHED, CLOSED line: pieces of named source lines (MAINLINE = the loop; any connector in
    data/connectors.local.json by its `name`), each walked from one vertex to another, taken VERBATIM (a shared
    mainline vertex IS the mainline vertex — the furniture lands where the loop's own would), consecutive pieces
    BRIDGED by points resampled along the straight join at the pieces' own median spacing (a trimmed connector
    starts at the host's curb line, not on its centreline), closed back onto its first vertex (L13: the last
    point repeats v0) — with a per-vertex map back to (source line, source vertex) — so every per-vertex
    declaration (corridor widths, boxes, kerbs, closure pins, zone_by_vertex) keys on the LAP'S OWN vertices.

Declared (opt-in) in track.config.json:

    race.laps.<lap id> = {"pieces": [{"line": "MAINLINE", "from": 1086, "to": 4424},
                                     {"line": "<connector name>", "from": 0, "to": 851},
                                     {"line": "<connector name>", "from": 82, "to": 0}],     (open line: from > to
                                                                                               walks it backwards)
                          "corridor": {... race.corridor's schema, keyed on LAP vertices ...},
                          "kerbs": {"trims": [...]},      (optional; every other race.kerbs key is inherited)
                          "roads": ["street names in driving order from the lap's v0"],   (optional)
                          "join_spacing_m": 3.0}          (optional; default the pieces' median spacing)
    layouts[].lap = "<lap id>"   on a race layout (absent = today's mainline, byte-identical)

The lap id is a lower-case [a-z0-9]+ token: it rides in file names (data/lap.<id>.json,
data/barrier_bands.<id>.json, data/race_authored.<id>.json, build/<slug>_race_<id>.kn5) and in the lap's
common-furniture names (1WALL_race_edge_lap<id>_*, 1KERB_race_lap<id>_*) and collection (RACE_LAP_<ID>).

Written to data/lap.<id>.json by tools/barrier_bands.py (the first consumer) or by
``python -m scripts.geometry.race_lap <project>``. Shape = centerline.local.json's (points_xyz_m, widths_m,
engine frame x=E, y=up, z=N, closed) plus island_w_by_vertex (median_bands mapped through the source map),
source_by_vertex ([line, vertex] or ["join", k] into joins[]), the lap's own mouths (side streets of every
piece's line, the abandoned BRANCH beyond every junction with a probe point on it) and bridge spans in lap
stations. Pure Python, no bpy — loaded by file path inside Blender too.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

MAINLINE = "MAINLINE"
LAP_TOKEN_RE = re.compile(r"^[a-z0-9]+$")
DEDUPE_M = 0.25            # consecutive piece ends closer than this are one point (no join inserted)
BRANCH_PROBE_M = 10.0      # tools/barrier_bands.MOUTH_PROBE_M: the branch probe stands this far past the lap's curb
CONNECTOR_ISLAND_SNAP_M = 1.0   # a connector vertex takes the island width of the nearest connector-island point
#                                 within this (median_bands connector_islands are a separate polyline of the road)
BRANCH_ON_LAP_PAD_M = 1.0  # a "branch" whose probe point lies within half-width + this of the lap is the lap itself


def lap_file(lap_id: str) -> str:
    return f"lap.{lap_id}.json"


def bands_file(lap_id: str | None) -> str:
    """data/barrier_bands.json for the mainline, data/barrier_bands.<lap>.json for a lap"""
    return "barrier_bands.json" if not lap_id else f"barrier_bands.{lap_id}.json"


def authored_file(lap_id: str | None) -> str:
    return "race_authored.json" if not lap_id else f"race_authored.{lap_id}.json"


def lap_of(layout: dict | None) -> str | None:
    """the lap id a layout names (layouts[].lap), None = the mainline"""
    if not isinstance(layout, dict):
        return None
    v = layout.get("lap")
    return str(v) if v not in (None, "") else None


def layout_by_id(cfg: dict, layout_id) -> dict | None:
    return next((lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and str(lo.get("id")) == str(layout_id)),
                None)


def lap_of_layout(cfg: dict, layout_id) -> str | None:
    return lap_of(layout_by_id(cfg, layout_id))


def lap_ids(cfg: dict) -> list[str]:
    """every lap a race layout names, sorted (empty on every track today)"""
    return sorted({lap_of(lo) for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and lap_of(lo)})


def layouts_on(cfg: dict, lap_id: str | None) -> list[dict]:
    """the layouts that drive `lap_id` (None = every layout that names no lap — street layouts included)"""
    return [lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and lap_of(lo) == lap_id]


def groups(cfg: dict) -> list[str | None]:
    """the lap groups a race chain walks: None (the mainline) when any race layout names no lap, then every lap"""
    race = [lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict) and lo.get("race_furniture")]
    out: list[str | None] = []
    if any(lap_of(lo) is None for lo in race) or not race:
        out.append(None)
    return out + lap_ids(cfg)


def spec(cfg: dict, lap_id: str) -> dict:
    laps = (cfg.get("race") or {}).get("laps") or {}
    s = laps.get(lap_id)
    if not isinstance(s, dict):
        raise SystemExit(f"[lap] layouts name lap {lap_id!r} but track.config.json race.laps declares "
                         f"{sorted(laps)} — declare race.laps.{lap_id}.pieces (never derived)")
    return s


def validate(cfg: dict) -> list[str]:
    """the declaration's own shape: tokens, a lap only on a race layout, every named lap declared with pieces"""
    probs = []
    laps = (cfg.get("race") or {}).get("laps") or {}
    if laps and not isinstance(laps, dict):
        return [f"race.laps must be an object {{<lap id>: {{pieces, corridor, ...}}}}, got {type(laps).__name__}"]
    for lo in cfg.get("layouts") or []:
        lap = lap_of(lo)
        if lap is None:
            continue
        if not lo.get("race_furniture"):
            probs.append(f"layout {lo.get('id')}: lap {lap!r} on a layout without race_furniture — a lap is a race "
                         f"layout's line (the street layouts drive the whole network)")
        if not LAP_TOKEN_RE.match(lap):
            probs.append(f"layout {lo.get('id')}: lap id {lap!r} must be a lower-case [a-z0-9]+ token (it rides in "
                         f"file and mesh names)")
        if lap not in laps:
            probs.append(f"layout {lo.get('id')}: lap {lap!r} is not declared in race.laps ({sorted(laps)})")
    for lid, s in sorted(laps.items()):
        if not LAP_TOKEN_RE.match(str(lid)):
            probs.append(f"race.laps: id {lid!r} must be a lower-case [a-z0-9]+ token")
        if not isinstance(s, dict) or not isinstance(s.get("pieces"), list) or len(s.get("pieces") or []) < 1:
            probs.append(f"race.laps.{lid}: needs pieces [{{line, from, to}}, ...]")
    return probs


def config_view(cfg: dict, lap_id: str | None) -> dict:
    """The config a per-lap consumer reads: race.corridor / race.kerbs / route.roads are the LAP's (its own vertex
    numbers), layouts are the ones on that lap. lap_id None = the mainline: race layouts that name a lap are left
    out, and with no lap declared anywhere the config comes back untouched (byte-identical consumers)."""
    if lap_id is None:
        if not lap_ids(cfg):
            return cfg
        out = dict(cfg)
        out["layouts"] = layouts_on(cfg, None)
        return out
    s = spec(cfg, lap_id)
    out = json.loads(json.dumps(cfg))
    race = out.setdefault("race", {})
    race.pop("laps", None)
    if "corridor" in s:
        race["corridor"] = s["corridor"]
    else:
        race.pop("corridor", None)
    kerbs = {k: v for k, v in (race.get("kerbs") or {}).items() if k != "trims"}
    kerbs.update(s.get("kerbs") or {})
    race["kerbs"] = kerbs
    route = out.setdefault("route", {})
    route["roads"] = list(s.get("roads") or [])
    out["layouts"] = layouts_on(cfg, lap_id)
    out["_lap"] = lap_id
    return out


# ---------------------------------------------------------------------------------------------
# source lines
def _closed(pts) -> bool:
    return len(pts) > 2 and math.dist((pts[0][0], pts[0][2]), (pts[-1][0], pts[-1][2])) < 1e-6


def load_lines(proj) -> dict:
    """{name: {"pts", "widths", "closed", "island_w"}} — MAINLINE (centerline.local.json, the closure duplicate
    dropped) and every connector piece of data/connectors.local.json"""
    data = Path(proj) / "data"
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    pts = [tuple(float(c) for c in p) for p in cl["points_xyz_m"]]
    widths = [float(w) for w in cl["widths_m"]]
    closed = _closed(pts)
    mb = data / "median_bands.json"
    mbj = json.loads(mb.read_text(encoding="utf-8")) if mb.exists() else {}
    iw = [float(v) for v in (mbj.get("island_w_by_vertex") or [])]
    if len(iw) != len(pts):
        iw = [0.0] * len(pts)
    m = len(pts) - 1 if closed else len(pts)
    out = {MAINLINE: {"pts": pts[:m], "widths": widths[:m], "closed": closed, "island_w": iw[:m]}}
    cp = data / "connectors.local.json"
    if cp.exists():
        isl = mbj.get("connector_islands") or []
        for c in json.loads(cp.read_text(encoding="utf-8")).get("connectors", []):
            cpts = [tuple(float(q) for q in p) for p in c["points_xyz_m"]]
            cw = [float(w) for w in c.get("widths_m") or [10.0] * len(cpts)]
            cc = _closed(cpts)
            if cc:
                cpts, cw = cpts[:-1], cw[:-1]
            base = str(c["name"]).split("#", 1)[0]
            ciw = [0.0] * len(cpts)
            for ci in isl:
                if str(ci.get("name", "")).split("#", 1)[0] != base:
                    continue
                ip, iwp = ci.get("points_xyz_m") or [], ci.get("island_w_by_point") or []
                for k, p in enumerate(cpts):
                    best, bw = CONNECTOR_ISLAND_SNAP_M, None
                    for q, w in zip(ip, iwp):
                        d = math.hypot(p[0] - q[0], p[2] - q[2])
                        if d <= best:
                            best, bw = d, float(w)
                    if bw is not None:
                        ciw[k] = max(ciw[k], bw)
            out[str(c["name"])] = {"pts": cpts, "widths": cw, "closed": cc, "island_w": ciw}
    return out


def _piece_vertices(line: dict, name: str, piece: dict) -> tuple[list[int], int]:
    """the source vertex indices a piece walks, and its step (+1 / -1)"""
    n = len(line["pts"])
    try:
        a, b = int(piece["from"]), int(piece["to"])
    except (KeyError, TypeError, ValueError):
        raise SystemExit(f"[lap] piece {piece!r} needs integer from / to")
    if not (0 <= a < n and 0 <= b < n):
        raise SystemExit(f"[lap] piece {name} v{a}->v{b}: out of range (the line has {n} vertices)")
    rev = piece.get("reverse")
    if line["closed"]:
        step = -1 if rev else 1
        out, k = [a], a
        while k != b:
            k = (k + step) % n
            out.append(k)
            if len(out) > n:
                raise SystemExit(f"[lap] piece {name} v{a}->v{b} never reaches its end")
        return out, step
    step = 1 if b >= a else -1
    if rev is not None and bool(rev) != (step < 0):
        raise SystemExit(f"[lap] piece {name} v{a}->v{b}: reverse {rev!r} contradicts from / to on an open line")
    return list(range(a, b + step, step)), step


def _median(vals):
    s = sorted(vals)
    return s[len(s) // 2] if s else 0.0


def _walk_line(line: dict, v: int, step: int, dist: float):
    """the point `dist` metres along the source line from vertex v in direction step (None past an open end)"""
    pts, n = line["pts"], len(line["pts"])
    k, left = v, dist
    while True:
        k2 = k + step
        if line["closed"]:
            k2 %= n
        elif not 0 <= k2 < n:
            return None
        a, b = pts[k], pts[k2]
        L = math.hypot(b[0] - a[0], b[2] - a[2])
        if L >= left:
            t = left / L if L > 0 else 0.0
            return (a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t), k2
        left -= L
        k = k2


def stitch(proj, cfg: dict, lap_id: str, *, lines: dict | None = None, mouths: list | None = None,
           spans: list | None = None) -> dict:
    """The lap line of race.laps.<lap_id> (see the module doc). `lines` / `mouths` / `spans` default to the
    project's own files (tests pass them in memory)."""
    if not LAP_TOKEN_RE.match(str(lap_id)):
        raise SystemExit(f"[lap] lap id {lap_id!r} must be a lower-case [a-z0-9]+ token")
    s = spec(cfg, lap_id)
    lines = lines if lines is not None else load_lines(proj)
    pieces = s.get("pieces") or []
    if not pieces:
        raise SystemExit(f"[lap] race.laps.{lap_id}.pieces is empty")
    walked = []
    gaps = []
    for pc in pieces:
        name = str(pc.get("line", ""))
        if name not in lines:
            raise SystemExit(f"[lap] race.laps.{lap_id}: piece line {name!r} is not a source line ({sorted(lines)})")
        vs, step = _piece_vertices(lines[name], name, pc)
        walked.append((name, vs, step))
        P = lines[name]["pts"]
        gaps += [math.hypot(P[b][0] - P[a][0], P[b][2] - P[a][2]) for a, b in zip(vs, vs[1:])]
    spacing = float(s.get("join_spacing_m") or _median(gaps) or 3.0)
    P, W, IW, SRC, joins = [], [], [], [], []

    def _join(a_src, b_src):
        la, va = a_src
        lb, vb = b_src
        A, B = lines[la]["pts"][va], lines[lb]["pts"][vb]
        d = math.hypot(B[0] - A[0], B[2] - A[2])
        if d < DEDUPE_M:
            return False
        k = len(joins)
        n_ins = max(0, int(math.ceil(d / spacing)) - 1)
        wa, wb = lines[la]["widths"][va], lines[lb]["widths"][vb]
        for q in range(1, n_ins + 1):
            t = q / (n_ins + 1)
            P.append((A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t))
            W.append(wa + (wb - wa) * t)
            IW.append(0.0)
            SRC.append(["join", k])
        joins.append({"from": [la, va], "to": [lb, vb], "length_m": round(d, 3), "points": n_ins})
        return True

    piece_rows = []
    merged = {}                                              # a piece end merged into its neighbour's vertex
    for i, (name, vs, step) in enumerate(walked):
        ln = lines[name]
        first = 0
        if P and SRC:
            prev = next(x for x in reversed(SRC) if x[0] != "join")
            if not _join((prev[0], prev[1]), (name, vs[0])):
                first = 1                                    # the same point: the previous piece's vertex stands
                merged[(name, vs[0])] = len(P) - 1
        start = len(P)
        for v in vs[first:]:
            P.append(tuple(ln["pts"][v]))
            W.append(float(ln["widths"][v]))
            IW.append(float(ln["island_w"][v]) if v < len(ln["island_w"]) else 0.0)
            SRC.append([name, v])
        piece_rows.append({"line": name, "from": vs[0], "to": vs[-1], "step": step, "lap_from": start,
                           "lap_to": len(P) - 1, "vertices": len(vs) - first})
    last = next(x for x in reversed(SRC) if x[0] != "join")
    if not _join((last[0], last[1]), (SRC[0][0], SRC[0][1])):
        # the last piece ends ON the first vertex: that vertex is the closure duplicate, not a vertex of its own
        dropped = SRC.pop()
        P.pop(); W.pop(); IW.pop()
        merged[(dropped[0], dropped[1])] = 0
        piece_rows[-1]["lap_to"] = len(P) - 1
    m = len(P)
    if m < 8:
        raise SystemExit(f"[lap] race.laps.{lap_id}: {m} vertices — not a lap")
    # the lap's mouths: every side street of a piece's line inside the lap, and the abandoned branch at every junction
    lap_index = {}
    for k, sv in enumerate(SRC):
        if sv[0] != "join":
            lap_index.setdefault((sv[0], sv[1]), k)
    for key, k in merged.items():
        lap_index.setdefault(key, k)
    step_of = {name: step for name, _vs, step in walked}
    piece_names = {name for name, _vs, _s in walked}
    st = [0.0]
    for k in range(1, m + 1):
        a, b = P[k - 1], P[k % m]
        st.append(st[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))

    def tangent(k):
        a, b = P[(k - 1) % m], P[(k + 1) % m]
        tx, tz = b[0] - a[0], b[2] - a[2]
        L = math.hypot(tx, tz) or 1.0
        return tx / L, tz / L

    if mouths is None:
        mp = Path(proj) / "data" / "mouths.json"
        mouths = json.loads(mp.read_text(encoding="utf-8")).get("mouths", []) if mp.exists() else []
    lap_mouths, skipped = [], []
    for mo in mouths:
        host, piece = str(mo.get("host")), str(mo.get("piece", mo.get("connector")))
        if host not in piece_names:
            continue
        k = lap_index.get((host, int(mo.get("host_vertex", -1))))
        if k is None:
            continue
        if piece in piece_names:
            skipped.append({"connector": mo.get("connector"), "piece": piece, "host": host, "lap_vertex": k,
                            "why": "the lap's own junction"})
            continue
        side = int(mo.get("side", 1))
        if step_of[host] < 0:
            side = -side                                     # the lap walks this host backwards: left is right
        lap_mouths.append({"connector": mo.get("connector"), "piece": piece, "host": host,
                           "host_vertex_source": int(mo["host_vertex"]), "host_vertex": k, "side": side,
                           "connector_width_m": mo.get("connector_width_m"), "kind": "side_street"})
    # branches: where the lap leaves a source line part-way (a ring always; an open line short of its end), the
    # rest of that line is pavement the lap turns away from — sealed by the curb strips, probed BRANCH_PROBE_M past
    # the lap's curb along the abandoned line
    for i, (name, vs, step) in enumerate(walked):
        ln = lines[name]
        for end, v, d in (("beyond", vs[-1], step), ("before", vs[0], -step)):
            k = lap_index.get((name, v))
            if k is None:
                continue
            n = len(ln["pts"])
            nxt = v + d
            if not ln["closed"] and not 0 <= nxt < n:
                continue                                     # the line ends here: nothing abandoned
            if (name, nxt % n) in lap_index and abs(lap_index[(name, nxt % n)] - k) in (1, m - 1):
                continue                                     # the lap carries on along it (a one-piece ring lap)
            reach = W[k] / 2.0 + BRANCH_PROBE_M
            got = _walk_line(ln, v, d, reach)
            if got is None:
                continue
            (px, pz), _kv = got
            near = min(range(m), key=lambda q: (P[q][0] - px) ** 2 + (P[q][2] - pz) ** 2)
            if math.hypot(P[near][0] - px, P[near][2] - pz) <= W[near] / 2.0 + BRANCH_ON_LAP_PAD_M:
                skipped.append({"connector": f"{name} {end} v{v}", "lap_vertex": k, "why": "the branch is the lap"})
                continue
            tx, tz = tangent(k)
            dx, dz = px - P[k][0], pz - P[k][2]
            side = 1 if (tx * dz - tz * dx) > 0 else -1      # left of the lap's travel = +1 (mouths.json's side)
            lap_mouths.append({"connector": f"{name} {end} v{v}", "piece": name, "host": "LAP",
                               "host_vertex": k, "side": side, "connector_width_m": round(ln["widths"][v], 3),
                               "kind": "branch", "probe_xz": [round(px, 3), round(pz, 3)]})
    lap_mouths.sort(key=lambda r: (r["host_vertex"], r["connector"]))
    # bridge spans (mainline stations) -> lap stations over the mainline vertices the lap shares
    if spans is None:
        bp = Path(proj) / "data" / "bridge.spans.auto.json"
        spans = [tuple(map(float, x)) for x in json.loads(bp.read_text(encoding="utf-8"))] if bp.exists() else []
    lap_spans = []
    if spans and MAINLINE in lines:
        mp_ = lines[MAINLINE]["pts"]
        mst = [0.0]
        for q in range(1, len(mp_)):
            mst.append(mst[-1] + math.hypot(mp_[q][0] - mp_[q - 1][0], mp_[q][2] - mp_[q - 1][2]))
        for s0, s1 in spans:
            ks = sorted(k for k, sv in enumerate(SRC) if sv[0] == MAINLINE and s0 <= mst[sv[1]] <= s1)
            if ks:
                lap_spans.append([round(st[ks[0]], 1), round(st[ks[-1]], 1)])
    pts = [[round(c, 4) for c in p] for p in P] + [[round(c, 4) for c in P[0]]]
    return {
        "_doc": "A race layout's LAP (scripts/geometry/race_lap.py, ledger 0054 phase 2): race.laps.<id>.pieces "
                "stitched — each piece's source vertices VERBATIM, consecutive pieces bridged by points resampled "
                "on the straight join, closed (the last point repeats v0). Engine frame x=E, y=up, z=N, like "
                "centerline.local.json. source_by_vertex[k] = [line, vertex] (or ['join', j] into joins); every "
                "per-vertex race declaration of a layout on this lap keys on THESE vertices.",
        "lap": lap_id,
        "frame": "engine x=E, y=up, z=N",
        "point_count": m + 1,
        "lap_m": round(st[-1], 1),
        "spacing_m": round(spacing, 3),
        "points_xyz_m": pts,
        "widths_m": [round(w, 3) for w in W] + [round(W[0], 3)],
        "island_w_by_vertex": [round(w, 3) for w in IW] + [round(IW[0], 3)],
        "source_by_vertex": SRC + [list(SRC[0])],
        "pieces": piece_rows,
        "joins": joins,
        "mouths": lap_mouths,
        "mouths_skipped": skipped,
        "bridge_spans_m": lap_spans,
    }


def write(proj, lap: dict) -> Path:
    p = Path(proj) / "data" / lap_file(lap["lap"])
    p.write_text(json.dumps(lap), encoding="utf-8")
    return p


def load(proj, lap_id: str) -> dict:
    p = Path(proj) / "data" / lap_file(lap_id)
    if not p.exists():
        raise SystemExit(f"[lap] data/{p.name} does not exist — tools/barrier_bands.py (or python -m "
                         f"scripts.geometry.race_lap <project>) writes it from race.laps.{lap_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def line_for(proj, cfg: dict | None, layout_id) -> dict:
    """THE accessor: the line a layout counts along. {"pts", "widths", "island_w", "lap" (id or None), "lap_rec"
    (the lap file or None), "bands_path"}. A layout that names no lap gets data/centerline.local.json +
    median_bands.json + barrier_bands.json exactly as every tool read them before."""
    proj = Path(proj)
    data = proj / "data"
    if cfg is None:
        cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    lap = lap_of_layout(cfg, layout_id) if layout_id is not None else None
    if lap is None:
        cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
        mb = data / "median_bands.json"
        iw = json.loads(mb.read_text(encoding="utf-8")).get("island_w_by_vertex", []) if mb.exists() else []
        return {"pts": [tuple(p) for p in cl["points_xyz_m"]], "widths": [float(w) for w in cl["widths_m"]],
                "island_w": iw, "lap": None, "lap_rec": None, "bands_path": data / bands_file(None)}
    rec = load(proj, lap)
    return {"pts": [tuple(p) for p in rec["points_xyz_m"]], "widths": [float(w) for w in rec["widths_m"]],
            "island_w": [float(w) for w in rec["island_w_by_vertex"]], "lap": lap, "lap_rec": rec,
            "bands_path": data / bands_file(lap)}


def bands_path_for(proj, cfg: dict, layout_id) -> Path:
    return Path(proj) / "data" / bands_file(lap_of_layout(cfg, layout_id))


def lap_source_vertex(rec: dict, k: int, line: str = MAINLINE):
    """the source vertex of lap vertex k on `line` (None on a join or another line)"""
    sv = rec["source_by_vertex"][k]
    return int(sv[1]) if sv[0] == line else None


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: python -m scripts.geometry.race_lap <project-dir>   (writes data/lap.<id>.json "
                         "for every lap a race layout names)")
    proj = Path(argv[0])
    cfg = json.loads((proj / "track.config.json").read_text(encoding="utf-8"))
    probs = validate(cfg)
    if probs:
        for p in probs:
            print("[lap] FAIL:", p)
        return 1
    for lap in lap_ids(cfg):
        rec = stitch(proj, cfg, lap)
        p = write(proj, rec)
        print(f"[lap] {lap}: {rec['point_count'] - 1} vertices, {rec['lap_m']} m, {len(rec['pieces'])} pieces, "
              f"{len(rec['joins'])} joins, {len(rec['mouths'])} mouths -> {p}")
    if not lap_ids(cfg):
        print("[lap] no layout names a lap — nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
