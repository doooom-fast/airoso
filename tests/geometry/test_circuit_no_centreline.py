"""A race circuit's paint has edge lines and no centre line (ledger 0063, Kevin 2026-11-01)."""
import math
import unittest

from scripts.geometry import ribbon


class CircuitPaint(unittest.TestCase):
    def test_nothing_is_painted_on_the_centre(self):
        n = 72
        pts = [(100 * math.cos(2 * math.pi * i / n), 0.0, 100 * math.sin(2 * math.pi * i / n)) for i in range(n)]
        pts.append(pts[0])
        half = 6.0
        m = ribbon.road_markings(pts, [2 * half] * len(pts))
        self.assertTrue(m["tris"])
        radii = [math.hypot(x, z) for x, _, z in m["vertices"]]
        inset = half - 0.4
        for r in radii:                       # every painted vertex sits on one of the two edge lines
            self.assertGreater(abs(r - 100), inset - 0.5)


if __name__ == "__main__":
    unittest.main()
