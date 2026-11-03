"""Declared race CHICANES — pure (no bpy), ledger 0055 (Kevin, seat, 2026-10-14).

Kevin, of the College Ave swerve he asked to be straightened in Free Roam: "But for the racetrack versions, I do like
the chicane that kind of goes from one side of the road across to the other and back." v0.18.0's chicane was the ROAD
itself jogging ~12 m sideways (a median-tool defect, tools/median_envelope.py); with the road where it really runs (one
continuous divided slab, the island on it) the Speedways keep their crossing as DECLARED race geometry on that road —
never a second road kn5 (fleet/LAWS.md L8).

A chicane (track.config.json race.chicanes[]) names two legs on the loop's own vertices (data/centerline.local.json,
the frame race.corridor's boxes and closure_runs use) and the race layouts that drive it:

    {"name": "college_split", "out_leg": [1260, 1286], "back_leg": [1350, 1376],
     "layouts": ["race_cw", "race_acw"], "street_only_island": true, "why": "..."}

In each named race layout the lane leaves its own carriageway over one leg (in its OWN direction of travel), holds the
far carriageway between the legs and comes back over the other. Two walls carry it across, both in that layout's own
closure kn5 (tools/barrier_bands.py declares them, tools/race_furniture.py sweeps them):
  * the layout's CLOSURE (far side) sweeps from its line beside the island into the far curb strip, where it is pinned
    (it ends); between the legs the lane runs to the far curb strip itself; over the return leg it starts pinned there
    and sweeps back;
  * a RACE-SIDE wall (corridors.<id>.chicane_walls) starts pinned in the race-side curb strip, sweeps across parallel
    to the closure, holds the line beside the empty carriageway between the legs, and returns into the race-side strip.
The lane between them keeps the width it had at the chicane's entry. `street_only_island`: the median island between
the two legs' outer ends stands ONLY in the street layout (its <slug>_street.kn5, tools/split_exports_blend.py) — a
race layout's road there is the bare continuous slab the island stands on (docs/JUNCTIONS.md §2.2: the island is never
cut out of the pavement), so every race tool reads the island through race_island_w().

The legs' shape: an S with eased ends (slope_shape), so the steepest step is 1 / (1 - EASE) of the leg's mean and the
wall line has no corner. Its rate is judged by tools/barrier_bands.py against race.corridor.steepest_pin_rate (1:3).
"""
from __future__ import annotations

import math

EASE = 0.35  # [invented] each end of a leg eases its slope in / out over this fraction of the leg (sinusoidal ramp):
#              steepest slope = mean / (1 - EASE) = 1.54 x mean; the wall's plan curvature stays finite (no kink).
#              0.2 (an 18 m ramp on a 90 m leg) bunched the AI line's turn-in into a curvature peak narrower than
#              verify_ai_line's +-6 m car scale: 57 'spurious dip' points at College's out leg (0055, first rehearsal)
STREET_KN5_SUFFIX = "_street"   # <slug>_street.kn5: the street-only island pieces + the centre paint (loaded by every non-race layout)
STREET_TAG = "_streetonly"      # object-name tag the island author gives every street-only piece (split routes on it)
ISLAND_NOSE_VERTS = 3           # tools/author_median_blend.NOSE_VERTS (MEASURED): an island run's nose taper, vertices


def slope_shape(t: float, ease: float = EASE) -> float:
    """f(t) on [0, 1] -> [0, 1]: the leg's lateral progress. Slope 0 at both ends, ramping (sin^2) to a constant
    1 / (1 - ease) over the middle; C1-continuous, monotone, f(0) = 0, f(1) = 1."""
    t = max(0.0, min(1.0, float(t)))
    e = max(1e-9, min(0.5, float(ease)))
    total = 1.0 - e

    def head(u):            # integral of the rising ramp (1 - cos(pi u / e)) / 2 from 0 to u, u in [0, e]
        return u / 2.0 - (e / (2.0 * math.pi)) * math.sin(math.pi * u / e)
    if t <= e:
        a = head(t)
    elif t < 1.0 - e:
        a = e / 2.0 + (t - e)
    else:
        a = total - head(1.0 - t)
    return a / total


def slope_max(ease: float = EASE) -> float:
    """the steepest df/dt of slope_shape: 1 / (1 - ease)"""
    return 1.0 / (1.0 - max(1e-9, min(0.5, float(ease))))


def declared(cfg: dict) -> tuple[list[dict], list[str]]:
    """([chicane], [problems]) — track.config.json race.chicanes, validated: name, out_leg [a, b], back_leg [c, d] on
    increasing vertices a < b <= c < d, layouts (race layouts with race_furniture), street_only_island (default true)."""
    race = (cfg or {}).get("race") or {}
    rows = race.get("chicanes") or []
    race_ids = {str(lo.get("id")) for lo in (cfg or {}).get("layouts", []) if lo.get("race_furniture")}
    out, probs = [], []
    for c in rows:
        name = str(c.get("name") or "")
        try:
            a, b = (int(v) for v in c["out_leg"])
            cc, d = (int(v) for v in c["back_leg"])
        except (KeyError, TypeError, ValueError):
            probs.append(f"race.chicanes {name or '?'}: out_leg / back_leg must be [vertex, vertex]")
            continue
        if not name:
            probs.append("race.chicanes: a chicane without a name")
        if not (0 <= a < b <= cc < d):
            probs.append(f"race.chicanes {name}: legs must run a < b <= c < d on increasing vertices, got "
                         f"out_leg [{a}, {b}] back_leg [{cc}, {d}]")
            continue
        lays = [str(x) for x in (c.get("layouts") or [])]
        bad = [x for x in lays if x not in race_ids]
        if not lays or bad:
            probs.append(f"race.chicanes {name}: layouts {lays} must name race layouts (race_furniture) — "
                         f"unknown / not race: {bad}")
        out.append({"name": name, "out_leg": [a, b], "back_leg": [cc, d], "layouts": lays,
                    "street_only_island": bool(c.get("street_only_island", True)), "why": str(c.get("why") or "")})
    spans = sorted((c["out_leg"][0], c["back_leg"][1], c["name"]) for c in out)
    for (a0, b0, n0), (a1, b1, n1) in zip(spans, spans[1:]):
        if a1 <= b0:
            probs.append(f"race.chicanes {n0} / {n1} overlap (v{a0}-v{b0} / v{a1}-v{b1})")
    return out, probs


def span_of(ch: dict) -> tuple[int, int]:
    """(first, last) vertex of the chicane, inclusive: out_leg start .. back_leg end"""
    return int(ch["out_leg"][0]), int(ch["back_leg"][1])


def street_only_spans(cfg: dict) -> list[tuple[int, int]]:
    """[(a, b)] inclusive vertex spans whose median island stands only in the street layout"""
    chs, _ = declared(cfg)
    return [span_of(c) for c in chs if c["street_only_island"]]


def race_island_w(island_w, cfg: dict) -> list[float]:
    """the island the RACE layouts drive beside: island_w with every street-only span's INTERIOR zeroed (a copy).

    The road kn5 keeps the island up to and including each span's end vertices, CAPPED there at full width (no nose:
    in the street layout the street-only piece continues from that ring). Every race tool models an island run's end
    as a nose tapering over ISLAND_NOSE_VERTS vertices (race_corridor.authored_half and its copies), so the race
    island stays non-zero ISLAND_NOSE_VERTS vertices past each cap: the modelled nose then lies wholly beyond the
    physical cap (full width AT the cap, as built; a phantom taper past it the walls keep clear of — conservative)."""
    iw = [float(w) for w in (island_w or [])]
    for a, b in street_only_spans(cfg):
        for k in range(max(0, a + 1 + ISLAND_NOSE_VERTS), min(len(iw), b - ISLAND_NOSE_VERTS)):
            iw[k] = 0.0
    return iw


def island_pieces(i: int, j: int, spans) -> list[tuple[int, int, bool]]:
    """[(a, b, street_only)] — an island segment [i, j) (vertex range, j exclusive) cut at every street-only span
    [s0, s1] (inclusive) it overlaps; consecutive pieces SHARE their cut vertex (a ring of each). No span: one piece,
    (i, j - 1, False) — the segment exactly as authored before ledger 0055."""
    cuts = []
    for s0, s1 in spans:
        a, b = max(i, s0), min(j - 1, s1)
        if a < b:
            cuts.append((a, b))
    if not cuts:
        return [(i, j - 1, False)]
    out, cur = [], i
    for a, b in sorted(cuts):
        if a > cur:
            out.append((cur, a, False))
        out.append((a, b, True))
        cur = b
    if cur < j - 1:
        out.append((cur, j - 1, False))
    return out


def is_race_layout(layout: dict) -> bool:
    """a race layout: it declares race furniture or kind "race" (Sand Creek's lap has no furniture and is still a race)"""
    return bool(layout.get("race_furniture")) or layout.get("kind") == "race"


def centre_paint_is_street_only(cfg: dict) -> bool:
    """a track with both kinds of layout keeps its centre line in the street layouts alone (ledger 0063, Kevin 2026-11-01:
    "only keep for actual roads ... keep only on freeroam"); a track that paints no yellow line has nothing to route"""
    layouts = [lo for lo in (cfg.get("layouts") or []) if isinstance(lo, dict)]
    if not (any(is_race_layout(lo) for lo in layouts) and any(not is_race_layout(lo) for lo in layouts)):
        return False
    mk = cfg.get("road_markings") or {}
    return mk.get("style") != "none" and mk.get("center_yellow", True) is not False


def has_street_kn5(cfg: dict) -> bool:
    """does the track ship a street-only kn5 (<slug>_street.kn5, every non-race layout loads it)?"""
    return bool(street_only_spans(cfg)) or centre_paint_is_street_only(cfg)


def street_kn5_name(cfg: dict) -> str:
    return f"{cfg['slug']}{STREET_KN5_SUFFIX}.kn5"


def is_centre_paint_name(name: str) -> bool:
    """the road's own double yellow (YLINE, YLINE_<tile>). The I-8's YLINE_I8_* is the freeway's median edge line, scenery
    every layout looks at, not a centre line on a road a race layout drives"""
    up = str(name).upper()
    return up.startswith("YLINE") and not up.startswith("YLINE_I8")


def is_street_only_name(name: str) -> bool:
    return STREET_TAG in str(name).lower() or is_centre_paint_name(name)


def legs_in_travel(ch: dict, direction: str) -> tuple[list[int], list[int]]:
    """(out leg, back leg) as [enter, leave] vertices in THIS layout's direction of travel: forward enters at
    out_leg[0]; reverse enters at back_leg[1] (its out leg is the forward back_leg, walked backwards)"""
    a, b = ch["out_leg"]
    c, d = ch["back_leg"]
    if direction == "reverse":
        return [d, c], [b, a]
    return [a, b], [c, d]
