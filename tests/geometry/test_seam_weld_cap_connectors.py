"""Ledger 0067 (Sand Creek 0.31.2): the seam weld's floor cap sees the connectors' decks.

The floor off the lap's ring edge raises grass toward edge - 0.20 m/m within 5 m and caps it under any pavement
in its table. The table held the lap's own sheets only, so where grid_tertiary_104 joins the lap in a cut the
floor lifted 1GRASS to 28.53 m over the street's deck at 28.11 m (audit B, +0.45 m). Stdlib only.
"""
from scripts.geometry.build_mesh import pavement_below, seam_weld_tables


def _quad(x0, x1, z0, z1, y):
    """two triangles of a flat sheet over [x0, x1] x [z0, z1] at height y"""
    v = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    return {"vertices": v, "tris": [(0, 1, 2), (0, 2, 3)]}


def _tris(sheet):
    v = sheet["vertices"]
    return [(v[a], v[b], v[c]) for a, b, c in sheet["tris"]]


ROAD = _quad(50.0, 58.0, -880.0, -860.0, 28.0)          # the lap's deck
EMPTY = {"vertices": [], "tris": []}
STREET = _quad(58.0, 70.0, -876.0, -871.0, 28.11)        # a street joining it from the east


def test_the_cap_holds_a_connector_deck_and_the_excavation_does_not():
    deck, cap = seam_weld_tables((ROAD, EMPTY, EMPTY), EMPTY, _tris(STREET))
    assert abs(pavement_below(cap, 60.3, -873.3, 28.6) - 28.11) < 1e-9     # the poke node, under the street
    assert pavement_below(deck, 60.3, -873.3, 28.6) is None                 # the excavation still sees the lap only
    floor = 28.6                                                            # what the ring edge asked for there
    assert min(floor, pavement_below(cap, 60.3, -873.3, floor) - 0.06) < 28.11


def test_no_connectors_leaves_both_tables_as_they_were():
    shoulder = _quad(48.0, 50.0, -880.0, -860.0, 27.9)
    shoulder["hem_idx"] = [0]
    a = seam_weld_tables((ROAD, EMPTY, EMPTY), shoulder)
    b = seam_weld_tables((ROAD, EMPTY, EMPTY), shoulder, [])
    assert a == b
    deck, cap = a
    assert len(deck) == 3 * 6 and all(len(ts) == 2 for ts in deck.values())  # the road's two tris in each of its 18 cells
    hemmed = [t for ts in cap.values() for t in ts if t[0] == shoulder["vertices"][0]]
    assert not hemmed                                                       # the buried hem stays out of the cap
