"""ledger 0075 mechanism 1+3, opt-in scenery.walls.seat "drape" (the freeway): the barrier on the deck edge where the road
rides a deck, at grade its base reaches the ground under it; the gap test also sees surface-street ribbons.
The default seat ("deck") builds exactly as before."""
import sys

root = sys.argv[1]
CRLF = chr(13) + chr(10)


def edit(p, pairs):
    p = f"{root}/{p}"
    s = open(p, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in s else chr(10)
    for old, new in pairs:
        old, new = old.replace(chr(10), nl), new.replace(chr(10), nl)
        assert s.count(old) == 1, (p, old[:70], s.count(old))
        s = s.replace(old, new)
    open(p, "w", encoding="utf-8", newline="").write(s)


edit("scripts/geometry/build_network_mesh.py", [
("""def _wall(pts, half, *, off, h, base_drop=0.35, tile_m=3.0, keep=None):""",
 """WALL_DECK_LIFT_M = 1.5      # a road this far above the ground under its centreline rides a deck: its barrier stands on the deck
WALL_GROUND_BURY_M = 0.5    # an at-grade barrier's base reaches this far under the raw ground (the conform may carve it)


def _wall(pts, half, *, off, h, base_drop=0.35, tile_m=3.0, keep=None, on_deck=None, deck_off=-0.35, ground=None):"""),
("""    pass through instead of being trapped. Outer walls (open dirt beyond) stay fully closed.\"\"\"""",
 """    pass through instead of being trapped. Outer walls (open dirt beyond) stay fully closed.

    SEATED (scenery.walls.seat "drape", ledger 0075): ``on_deck[i]`` puts the barrier ``deck_off`` past the half-width
    (negative = on the deck, inside its edge) where the road rides a deck, and elsewhere ``ground(x, z)`` sinks the base
    to WALL_GROUND_BURY_M under the ground at the barrier itself. Without them the barrier is swept at the deck's height
    ``off`` past the edge whatever stands under it (the 22,475 floating columns of ledger 0075).\"\"\""""),
("""            px, pz = x + nx * (half + off), z + nz * (half + off)
            r = len(V)
            V.append((px, y - base_drop, pz)); U.append((arc / tile_m, 0.0))""",
 """            deck = on_deck is not None and on_deck[i]
            o = deck_off if deck else off
            px, pz = x + nx * (half + o), z + nz * (half + o)
            base = y - base_drop
            if ground is not None and not deck:
                base = min(base, ground(px, pz) - WALL_GROUND_BURY_M)
            r = len(V)
            V.append((px, base, pz)); U.append((arc / tile_m, 0.0))"""),
("""    wall_off = float(_wcfg.get("offset_m", 3.2))""",
 """    wall_off = float(_wcfg.get("offset_m", 3.2))
    wall_seat = str(_wcfg.get("seat", "deck")).lower()    # "drape" (ledger 0075): deck edge on decks, base to the ground at grade
    if wall_seat not in ("deck", "drape"):
        raise SystemExit(f"scenery.walls.seat {wall_seat!r}: deck or drape")"""),
("""            kerb_meshes.append((f"k{eid}", _doubleside(cb)))""",
 """            kerb_meshes.append((f"k{eid}", _doubleside(cb)))
            if wall_seat == "drape":    # ledger 0075: a freeway barrier may never stand on a surface street either
                for wi in range(len(deck_pts)):
                    rx, ry, rz = deck_pts[wi]
                    a = deck_pts[max(0, wi - 1)]; b = deck_pts[min(len(deck_pts) - 1, wi + 1)]
                    st_road_hash[(int(rx // WCELL), int(rz // WCELL))].append(
                        (eid, rx, ry, rz, math.atan2(b[2] - a[2], b[0] - a[0]), w / 2.0))"""),
("""    fw_road_hash = _wdd(list)                        # deck pts (eid,x,y,z,tangent,half) for crossing/pier tests""",
 """    fw_road_hash = _wdd(list)                        # deck pts (eid,x,y,z,tangent,half) for crossing/pier tests
    st_road_hash = _wdd(list)                        # surface-street deck pts, the same shape (walls seat "drape" only)"""),
("""                            for (eid2, rx, ry, rz, rt, rhalf) in fw_road_hash.get((ci + di, cj + dj), ()):""",
 """                            for (eid2, rx, ry, rz, rt, rhalf) in (fw_road_hash.get((ci + di, cj + dj), [])
                                                                  + st_road_hash.get((ci + di, cj + dj), [])):"""),
("""            wm = _wall(dp, half, off=wall_off, h=wall_h, keep=keep)""",
 """            if wall_seat == "drape":
                deckv = [p[1] - terr_y(p[0], p[2]) > WALL_DECK_LIFT_M for p in dp]
                wm = _wall(dp, half, off=wall_off, h=wall_h, keep=keep, on_deck=deckv, ground=terr_y)
            else:
                wm = _wall(dp, half, off=wall_off, h=wall_h, keep=keep)"""),
])

test = '''"""ledger 0075: the network barrier's seat (scenery.walls.seat "drape", the freeway). Stdlib only."""
from scripts.geometry.build_network_mesh import WALL_GROUND_BURY_M, _wall

DECK = [(0.0, 10.0, float(z)) for z in range(0, 40, 4)]     # a straight road north at y 10, half-width 5


def test_the_default_seat_is_unchanged():
    a = _wall(DECK, 5.0, off=3.2, h=1.1)
    b = _wall(DECK, 5.0, off=3.2, h=1.1, on_deck=None, ground=None)
    assert a == b
    xs = sorted({round(abs(v[0]), 3) for v in a["vertices"]})
    assert xs == [8.2] and min(v[1] for v in a["vertices"]) == 10.0 - 0.35


def test_at_grade_the_base_reaches_the_ground_under_the_barrier():
    falls = lambda x, z: 10.0 - 3.0 if abs(x) > 5.0 else 10.0          # the ground drops 3 m past the pavement  # noqa: E731
    m = _wall(DECK, 5.0, off=0.5, h=1.1, on_deck=[False] * len(DECK), ground=falls)
    bases = [v[1] for v in m["vertices"][0::2]]
    assert all(abs(b - (7.0 - WALL_GROUND_BURY_M)) < 1e-9 for b in bases)
    assert all(abs(v[1] - 11.1) < 1e-9 for v in m["vertices"][1::2])     # the top still rides the deck


def test_on_a_deck_the_barrier_stands_inside_the_deck_edge():
    m = _wall(DECK, 5.0, off=0.5, h=1.1, on_deck=[True] * len(DECK), ground=lambda x, z: -20.0)
    assert {round(abs(v[0]), 3) for v in m["vertices"]} == {4.65}       # 5.0 - 0.35: on the deck, not over the valley
    assert min(v[1] for v in m["vertices"]) == 10.0 - 0.35
'''
open(f"{root}/tests/geometry/test_network_wall_seat.py", "w", encoding="utf-8", newline="").write(test)

p = f"{root}/tracks/san-diego-freeway/track.config.json"
s = open(p, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in s else chr(10)
old = '      "offset_m": 0.5' + nl
assert s.count(old) == 1, s.count(old)
s = s.replace(old, '      "offset_m": 0.5,' + nl + '      "seat": "drape",' + nl +
              '      "_seat_doc": "Ledger 0075 (2026-11-03): offset_m 3.2 -> 0.5 put the barrier on the 3 m graded shoulder '
              '(floating 22,475 -> 13,234); seat drape stands it on the deck edge where the road rides a deck and sinks its '
              'base to the ground at grade, and gaps it against surface streets too."' + nl)
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched", root)
