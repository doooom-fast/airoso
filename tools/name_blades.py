"""Street-name blades (MUTCD D3-1) at a lap's junctions, from the OSM `name` of each street — the PLAN and the ATLAS
(ledger 0079 round K; Kevin 2026-11-05, asked about arrow signs and street-name signs: "Both").

Run ONCE on the Mac against a built workshop (its data/), the outputs committed beside the track; the chain's
tools/author_name_blades_blend.py stands them on the built ground (track.config.json signs_name_blades.file). Nothing
here runs in the chain, so the PC needs no font and no Pillow.

WHAT IS REAL: the names (OpenStreetMap `name` of the nearest named way, the source track's own Overpass cache), the
junctions (the build's own mouths and pad arms), and the MUTCD 2009 rules cited per number:
  2D.43 para 01   Street Name signs at all street intersections in urban areas;
  2D.43 para 04   initial upper-case letters >= 6 in, lower-case >= 4.5 in (post-mounted): CAP_IN, LOWER_IN;
  2D.43 para 18 / 2D.03 para 02   white legend and border on green;
  2D.43 para 20   "Signs naming both streets should be installed at each intersection. They should be mounted with
                  their faces parallel to the streets they name." / principal arterials: "at least on diagonally
                  opposite corners" — each arm's post on its own corner, a crossing's two arms on opposite corners;
  Table 2D-1      Street Name (1 line) D3-1: "Varies x 12" (conventional road): BLADE_H_IN;
  1A.15 Table 1A-2  the abbreviations (Avenue Ave, Boulevard Blvd, Drive Dr, Street St, North N ...).
AUTHORED (GATES-CHANGELOG 2026-11-05 round K): the blade's side margins MARGIN_IN, its border BORDER_IN, the stock
length step LEN_STEP_IN, the font (Arial Narrow Bold standing in for FHWA Series E(M), which this Mac does not have), the
post's place (CORNER_M past the side street's edge along the lap, SETBACK_M outside the lane edge), and which corner
(the right-hand arm's near corner, the left-hand arm's far corner, so a crossing gets diagonally opposite corners).

    .venv/bin/python tools/name_blades.py <workshop-project> --osm <osm cache json> --out-plan <json> --out-atlas <png>
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

CAP_IN, LOWER_IN = 6.0, 4.5   # MUTCD 2009 2D.43 para 04 (post-mounted, the minimum; Sand Creek's streets are 25-45 mph)
BLADE_H_IN = 12.0             # MUTCD 2009 Table 2D-1, D3-1 conventional road "Varies x 12"
MARGIN_IN = 3.0               # [authored] legend to blade end, each side
BORDER_IN = 0.5               # [authored] the white border's width, inset BORDER_IN from the edge
LEN_STEP_IN = 6.0             # [authored] blade lengths in 6 in steps (stock blanks)
CORNER_M = 3.0                # [authored] gap_mouths' CORNER_M: the post stands this far past the side street's edge
SETBACK_M = 2.1               # [authored] lane edge + Sand Creek's 1.8 m edge strip + 1 ft (2A.19 para 11's minimum)
PX_PER_IN = 10.0              # atlas resolution: a 12 in blade is 120 px high
ROW_PX = 128                  # one blade per atlas row (120 px + 8 px gutter)
ATLAS_W = 1024                # 102 in at PX_PER_IN: the longest blade must fit
FONT = "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf"
GREEN, WHITE = (0, 105, 60), (255, 255, 255)   # MUTCD green (FHWA colour spec PR#1 ~ #006B3F) / white
NAME_MIN_M, NAME_MAX_M = 6.0, 40.0             # a side street is named by its points this far past the mouth cut
ABBR = [("North ", "N "), ("South ", "S "), ("East ", "E "), ("West ", "W "),
        (" Avenue", " Ave"), (" Boulevard", " Blvd"), (" Street", " St"), (" Drive", " Dr"), (" Parkway", " Pkwy"),
        (" Place", " Pl"), (" Road", " Rd"), (" Court", " Ct"), (" Lane", " Ln"), (" Circle", " Cir"),
        (" Highway", " Hwy"), (" Frontage", " Frtg")]


def abbreviate(name):
    """MUTCD 1A.15 (Table 1A-2) abbreviations, whole words only"""
    s = name
    for a, b in ABBR:
        s = re.sub(r"\b" + re.escape(a.strip()) + r"\b", b.strip(), s)
    return re.sub(r"\s+", " ", s).strip()


def mpd(lat0):
    phi = math.radians(lat0)
    return (111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi),
            111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi))


def named_ways(osm_path, lon0, lat0):
    o = json.loads(Path(osm_path).read_text(encoding="utf-8"))
    els = (o.get("payload") or o).get("elements", [])
    m_lon, m_lat = mpd(lat0)
    out = []
    for e in els:
        nm = (e.get("tags") or {}).get("name")
        if e.get("type") != "way" or not nm or not e.get("geometry"):
            continue
        hw = (e.get("tags") or {}).get("highway", "")
        if hw in ("motorway", "motorway_link", "footway", "cycleway", "path", "service", "track"):
            continue
        out.append((nm, [((g["lon"] - lon0) * m_lon, (g["lat"] - lat0) * m_lat) for g in e["geometry"]]))
    return out


def seg_d(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dz * t)


def nearest_name(ways, pts, reach=15.0):
    """the name most of `pts` lie nearest to (each within reach), else None"""
    votes = {}
    for p in pts:
        best = None
        for nm, g in ways:
            d = min(seg_d(p, a, b) for a, b in zip(g, g[1:]))
            if d <= reach and (best is None or d < best[0]):
                best = (d, nm)
        if best:
            votes[best[1]] = votes.get(best[1], 0) + 1
    return max(votes, key=votes.get) if votes else None


def plan(proj, osm, osm_lap=None):
    data = Path(proj) / "data"
    cl = json.loads((data / "centerline.local.json").read_text(encoding="utf-8"))
    P = [(p[0], p[2]) for p in cl["points_xyz_m"]]
    W = cl["widths_m"]
    m = len(P) - 1
    ways = named_ways(osm, float(cl["origin"]["lon"]), float(cl["origin"]["lat"]))
    # the lap is named by the ROUTE's own ways (the source track's osm.cache.json: route.roads and nothing else), so a
    # frontage road or a ramp beside it never names it
    lap_ways = named_ways(osm_lap, float(cl["origin"]["lon"]), float(cl["origin"]["lat"])) if osm_lap else ways
    # the streets whole, as the draft had them before the trim (connectors.local.json.pre-trim: the trimmed file holds the
    # joined pieces under other names); a side street is named by its own points 6-40 m from the mouth's cut
    pre = data / "connectors.local.json.pre-trim"
    conns = {c["name"]: c for c in json.loads((pre if pre.exists() else data / "connectors.local.json").read_text(
        encoding="utf-8"))["connectors"]}
    arms = []
    for mo in json.loads((data / "mouths.json").read_text(encoding="utf-8")).get("mouths", []):
        if mo.get("host") == "MAINLINE":
            arms.append({"connector": mo["connector"], "vertex": int(mo["host_vertex"]), "side": int(mo["side"]),
                         "width_m": float(mo.get("connector_width_m") or 8.0), "via": "mouth",
                         "cut": (float(mo["cut_xyz"][0]), float(mo["cut_xyz"][2]))})
    pb = data / "pads.built.json"
    for pad in (json.loads(pb.read_text(encoding="utf-8")).get("pads", []) if pb.exists() else []):
        k = int(pad["node"])
        for a in pad.get("arm_rows") or []:
            c = conns.get(a["connector"].split("#")[0])
            if c is None:
                continue
            ends = [(c["points_xyz_m"][0][0], c["points_xyz_m"][0][2]), (c["points_xyz_m"][-1][0], c["points_xyz_m"][-1][2])]
            q = min(ends, key=lambda e: math.dist(e, P[k]))
            t = (P[(k + 1) % m][0] - P[k - 1][0], P[(k + 1) % m][1] - P[k - 1][1])
            side = 1 if t[0] * (q[1] - P[k][1]) - t[1] * (q[0] - P[k][0]) > 0 else -1
            arms.append({"connector": a["connector"].split("#")[0], "vertex": k, "side": side,
                         "width_m": float((c.get("widths_m") or [8.0])[0]), "via": f"pad {pad['id']}", "cut": q})
    posts, skipped = [], []
    for a in sorted(arms, key=lambda r: (r["vertex"], r["side"])):
        c = conns.get(a["connector"].split("#")[0])
        if c is None:
            skipped.append(dict(a, why="no such street in connectors.local.json(.pre-trim)"))
            continue
        cut = a["cut"]
        allp = [(p[0], p[2]) for p in c["points_xyz_m"]]
        far = [p for p in allp if NAME_MIN_M <= math.dist(p, cut) <= NAME_MAX_M] or \
            sorted(allp, key=lambda p: math.dist(p, cut))[1:4]
        d = (sum(p[0] for p in far) / len(far) - cut[0], sum(p[1] for p in far) / len(far) - cut[1])
        k = a["vertex"]
        cross = nearest_name(ways, far)
        lap = nearest_name(lap_ways, [P[(k + d) % m] for d in (-3, -1, 0, 1, 3)])
        if not cross or not lap:
            skipped.append(dict(a, why=f"unnamed in OSM (cross {cross!r}, lap {lap!r})"))
            continue
        if abbreviate(cross) == abbreviate(lap):
            skipped.append(dict(a, why=f"the side street carries the lap's own name ({cross})"))
            continue
        # MUTCD 2D.43 para 20: a crossing's two arms on diagonally opposite corners — the right-hand arm (side -1, right
        # of the race's travel) at its near corner (before the mouth), the left-hand arm at its far corner (after it)
        along = -(a["width_m"] / 2.0 + CORNER_M) if a["side"] < 0 else (a["width_m"] / 2.0 + CORNER_M)
        posts.append({"id": f"nb{len(posts)}", "connector": a["connector"], "via": a["via"], "vertex": k,
                      "side": "L" if a["side"] > 0 else "R", "along_m": round(along, 2), "setback_m": SETBACK_M,
                      "lap_name": abbreviate(lap), "cross_name": abbreviate(cross), "osm_lap": lap, "osm_cross": cross,
                      "cross_dir_xz": [round(d[0] / (math.hypot(*d) or 1), 4), round(d[1] / (math.hypot(*d) or 1), 4)]})
    # one post per corner: two arms naming the same pair within 15 m on one side are one post
    keep = []
    for p in posts:
        if any(q["side"] == p["side"] and {q["lap_name"], q["cross_name"]} == {p["lap_name"], p["cross_name"]}
               and abs(q["vertex"] - p["vertex"]) <= 5 for q in keep):
            skipped.append({"connector": p["connector"], "vertex": p["vertex"], "why": "the same corner's post already names both"})
            continue
        keep.append(p)
    for i, p in enumerate(keep):
        p["id"] = f"nb{i}"
    return keep, skipped


def atlas(names, out_png):
    from PIL import Image, ImageDraw, ImageFont
    rows = {}
    img = Image.new("RGB", (ATLAS_W, max(ROW_PX, ROW_PX * len(names))), GREEN)
    dr = ImageDraw.Draw(img)
    # the font size whose capital height is CAP_IN (measured on "H"), lower case as the face draws it
    size = 10
    while True:
        f = ImageFont.truetype(FONT, size)
        bb = dr.textbbox((0, 0), "H", font=f)
        if bb[3] - bb[1] >= CAP_IN * PX_PER_IN:
            break
        size += 1
    for i, nm in enumerate(names):
        tb = dr.textbbox((0, 0), nm, font=f)
        tw = tb[2] - tb[0]
        L_in = math.ceil((tw / PX_PER_IN + 2 * MARGIN_IN) / LEN_STEP_IN) * LEN_STEP_IN
        wpx = int(round(L_in * PX_PER_IN))
        if wpx > ATLAS_W:
            raise SystemExit(f"[name-blades] {nm!r}: a {L_in} in blade does not fit the {ATLAS_W} px atlas")
        y0 = i * ROW_PX
        hpx = int(round(BLADE_H_IN * PX_PER_IN))
        b = int(round(BORDER_IN * PX_PER_IN))
        dr.rectangle([b, y0 + b, wpx - 1 - b, y0 + hpx - 1 - b], outline=WHITE, width=max(2, int(0.75 * PX_PER_IN)))
        hb = dr.textbbox((0, 0), "H", font=f)
        ty = y0 + (hpx - (hb[3] - hb[1])) / 2.0 - hb[1]
        dr.text(((wpx - tw) / 2.0 - tb[0], ty), nm, font=f, fill=WHITE)
        rows[nm] = {"row": i, "length_in": L_in, "u": [0.0, wpx / ATLAS_W],
                    "v": [1.0 - (y0 + hpx) / img.height, 1.0 - y0 / img.height]}
    img.save(out_png, optimize=True)
    return rows, img.size, size


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    proj = argv[0]
    get = lambda k: argv[argv.index(k) + 1]
    posts, skipped = plan(proj, get("--osm"), get("--osm-lap") if "--osm-lap" in argv else None)
    names = sorted({p["lap_name"] for p in posts} | {p["cross_name"] for p in posts})
    rows, size, font_px = atlas(names, get("--out-atlas"))
    rec = {"_doc": ("MUTCD D3-1 street-name blades at Sand Creek's lap junctions (tools/name_blades.py; ledger 0079 round K). "
                    "Names: OpenStreetMap `name`, abbreviated per MUTCD 1A.15; sizes MUTCD 2009 2D.43 / Table 2D-1; the "
                    "corner, margins, border, length step, font and set-back AUTHORED (GATES-CHANGELOG 2026-11-05)."),
           "mutcd": {"blade_h_in": BLADE_H_IN, "cap_in": CAP_IN, "lower_in": LOWER_IN, "mount_bottom_ft": 7.0,
                     "margin_in": MARGIN_IN, "border_in": BORDER_IN, "len_step_in": LEN_STEP_IN},
           "corner_m": CORNER_M, "setback_m": SETBACK_M,
           "atlas": {"file": Path(get("--out-atlas")).name, "size_px": list(size), "px_per_in": PX_PER_IN,
                     "font": Path(FONT).name, "font_px": font_px, "rows": rows},
           "posts": posts, "skipped": skipped}
    Path(get("--out-plan")).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[name-blades] {len(posts)} posts, {len(names)} names, {len(skipped)} skipped -> {get('--out-plan')}")
    for p in posts:
        print(f"[name-blades]   {p['id']:5} v{p['vertex']:<5} {p['side']} {p['along_m']:+6.1f} m  {p['lap_name']} / "
              f"{p['cross_name']}  ({p['via']})")
    for s in skipped:
        print(f"[name-blades]   skipped {s.get('connector')} v{s.get('vertex')}: {s['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
