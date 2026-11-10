"""ledger 0075, the deck barrier's support: a 1KERB parapet base at deck height beyond the pavement edge on deck runs
(seat "drape" only), the barrier standing in its middle"""
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
("""WALL_GROUND_BURY_M = 0.5    # an at-grade barrier's base reaches this far under the raw ground (the conform may carve it)
""",
 """WALL_GROUND_BURY_M = 0.5    # an at-grade barrier's base reaches this far under the raw ground (the conform may carve it)
PARAPET_BASE_W = 0.6        # [invented] the deck slab beyond the pavement a viaduct's barrier stands on (seat "drape")


def _parapet_base(pts, half, on_deck, *, width=PARAPET_BASE_W, lift=0.0, tile_m=3.0):
    \"\"\"1KERB strip ``width`` wide beyond both pavement edges at the deck's own height, on the deck runs only (``on_deck``
    true at both ends of a span): the slab a viaduct carries its barrier on, beyond the travelled way, so the barrier
    stands on a surface without standing on the road (ledger 0075: inside the pavement edge it read 90,101 walls on the
    road; 0.05 m outside it, 13,421 floating columns over the valley). Face up.\"\"\"
    V, U, T = [], [], []
    for side in (1.0, -1.0):
        rows = []
        arc = 0.0
        for i, (x, y, z) in enumerate(pts):
            if i > 0:
                arc += math.hypot(x - pts[i - 1][0], z - pts[i - 1][2])
            a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
            tx, tz = b[0] - a[0], b[2] - a[2]; tl = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / tl * side, tx / tl * side
            rows.append(len(V))
            V.append((x + nx * half, y + lift, z + nz * half)); U.append((0.0, arc / tile_m))
            V.append((x + nx * (half + width), y + lift, z + nz * (half + width))); U.append((width / tile_m, arc / tile_m))
        for k in range(len(pts) - 1):
            if on_deck[k] and on_deck[k + 1]:
                a0, a1, b0, b1 = rows[k], rows[k] + 1, rows[k + 1], rows[k + 1] + 1
                T += [(a0, a1, b1), (a0, b1, b0)]
    used = sorted({v for t in T for v in t})
    if not used:
        return {"vertices": [], "uvs": [], "tris": []}
    remap = {v: i for i, v in enumerate(used)}
    mesh = {"vertices": [V[v] for v in used], "uvs": [U[v] for v in used], "tris": [tuple(remap[v] for v in t) for t in T]}
    return orient_up(mesh)
"""),
("""def _wall(pts, half, *, off, h, base_drop=0.35, tile_m=3.0, keep=None, on_deck=None, deck_off=0.05, ground=None):""",
 """def _wall(pts, half, *, off, h, base_drop=0.35, tile_m=3.0, keep=None, on_deck=None, deck_off=PARAPET_BASE_W / 2.0, ground=None):"""),
("""    where the road rides a deck: at its edge, base under the deck, so it stands off the pavement (inside it, 0.35 m in, read
    90,101 walls on the road and 334 obstructed stations on the freeway) on the shoulder's first drop,""",
 """    where the road rides a deck: on the middle of the deck's parapet base (_parapet_base), off the pavement,""",),
("""                wm = _wall(dp, half, off=wall_off, h=wall_h, keep=keep, on_deck=deckv, ground=terr_y)""",
 """                wm = _wall(dp, half, off=wall_off, h=wall_h, keep=keep, on_deck=deckv, ground=terr_y)
                pb = _parapet_base(dp, half, deckv, lift=ROAD_LIFT_M)
                if pb["tris"]:
                    parapet_meshes.append((f"p{eid}", pb))"""),
("""    st_road_hash = _wdd(list)                        # surface-street deck pts, the same shape (walls seat "drape" only)""",
 """    st_road_hash = _wdd(list)                        # surface-street deck pts, the same shape (walls seat "drape" only)
    parapet_meshes: list[tuple[str, dict]] = []      # 1KERB parapet base under the deck barrier (walls seat "drape" only)"""),
("""    groups += _pack_groups("1WALL_part", "barrier", wall_meshes)   # physical freeway barrier (KEY=WALL)""",
 """    groups += _pack_groups("1WALL_part", "barrier", wall_meshes)   # physical freeway barrier (KEY=WALL)
    if parapet_meshes:   # seat "drape" (ledger 0075): the deck slab the barrier stands on, beyond the pavement
        groups += _pack_groups("1KERB_parapet", "kerb", parapet_meshes)"""),
])

p = f"{root}/tests/geometry/test_network_wall_seat.py"
s = open(p, encoding="utf-8", newline="").read()
s = s.replace("from scripts.geometry.build_network_mesh import WALL_GROUND_BURY_M, _wall",
              "from scripts.geometry.build_network_mesh import PARAPET_BASE_W, WALL_GROUND_BURY_M, _parapet_base, _wall")
s = s.replace('''def test_on_a_deck_the_barrier_stands_at_the_deck_edge():
    m = _wall(DECK, 5.0, off=0.5, h=1.1, on_deck=[True] * len(DECK), ground=lambda x, z: -20.0)
    assert {round(abs(v[0]), 3) for v in m["vertices"]} == {5.05}       # at the edge, not 0.5 m out over the valley''',
'''def test_on_a_deck_the_barrier_stands_on_its_parapet_base():
    m = _wall(DECK, 5.0, off=0.5, h=1.1, on_deck=[True] * len(DECK), ground=lambda x, z: -20.0)
    assert {round(abs(v[0]), 3) for v in m["vertices"]} == {round(5.0 + PARAPET_BASE_W / 2, 3)}   # mid-slab, off the road
    pb = _parapet_base(DECK, 5.0, [True] * len(DECK))
    xs = sorted({round(abs(v[0]), 3) for v in pb["vertices"]})
    assert xs == [5.0, round(5.0 + PARAPET_BASE_W, 3)] and {v[1] for v in pb["vertices"]} == {10.0}


def test_the_parapet_base_covers_deck_runs_only():
    on = [False, False, True, True, True, False, False, False, False, False]
    pb = _parapet_base(DECK, 5.0, on)
    zs = sorted({v[2] for v in pb["vertices"]})
    assert zs == [8.0, 12.0, 16.0] and len(pb["tris"]) == 2 * 2 * 2      # two spans each side, two tris a span
    assert _parapet_base(DECK, 5.0, [False] * len(DECK))["tris"] == []''')
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched", root)
