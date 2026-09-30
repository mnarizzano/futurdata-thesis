"""
Unit tests for src/main/utils/geometry.py — pure geometry helpers, no deps.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_geometry -v
"""

import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.utils import geometry as g


class DistanceTests(unittest.TestCase):
    def test_3_4_5_triangle(self):
        self.assertEqual(g.distance((0, 0), (3, 4)), 5.0)

    def test_same_point_is_zero(self):
        self.assertEqual(g.distance((7, 7), (7, 7)), 0.0)


class AngleBetweenPointsTests(unittest.TestCase):
    def test_horizontal_is_zero(self):
        self.assertEqual(g.angle_between_points((0, 0), (5, 0)), 0.0)

    def test_straight_up_is_half_pi(self):
        self.assertAlmostEqual(g.angle_between_points((0, 0), (0, 5)), math.pi / 2)


class SnapToGridTests(unittest.TestCase):
    def test_rounds_to_nearest_grid(self):
        self.assertEqual(g.snap_to_grid(72, 121), (50, 100))

    def test_exact_multiple_unchanged(self):
        self.assertEqual(g.snap_to_grid(100, 150), (100, 150))

    def test_custom_grid_size(self):
        self.assertEqual(g.snap_to_grid(23, 8, grid_size=10), (20, 10))


class PointInRectTests(unittest.TestCase):
    def test_inside(self):
        self.assertTrue(g.point_in_rect(5, 5, 0, 0, 10, 10))

    def test_on_edge_is_inside(self):
        self.assertTrue(g.point_in_rect(0, 10, 0, 0, 10, 10))

    def test_outside(self):
        self.assertFalse(g.point_in_rect(11, 5, 0, 0, 10, 10))


class RectIntersectsTests(unittest.TestCase):
    def test_overlapping(self):
        self.assertTrue(g.rect_intersects((0, 0, 10, 10), (5, 5, 15, 15)))

    def test_disjoint(self):
        self.assertFalse(g.rect_intersects((0, 0, 10, 10), (20, 20, 30, 30)))

    def test_touching_edges_counts_as_intersect(self):
        self.assertTrue(g.rect_intersects((0, 0, 10, 10), (10, 0, 20, 10)))


class GetArrowPointsTests(unittest.TestCase):
    def test_tip_is_first_point(self):
        pts = g.get_arrow_points(0, 0, 10, 0)
        self.assertEqual(pts[0], (10, 0))
        self.assertEqual(len(pts), 3)

    def test_barbs_are_symmetric_in_y(self):
        # Arrow pointing right (+x): both barbs share an x and mirror in y.
        (_, _), (x3, y3), (x4, y4) = g.get_arrow_points(0, 0, 10, 0, arrow_size=10)
        self.assertAlmostEqual(x3, x4)
        self.assertAlmostEqual(y3, -y4)


class BezierPointTests(unittest.TestCase):
    def setUp(self):
        self.p0, self.p1, self.p2, self.p3 = (0, 0), (0, 10), (10, 10), (10, 0)

    def test_t0_is_start_point(self):
        self.assertEqual(g.calculate_bezier_point(0, self.p0, self.p1, self.p2, self.p3), (0, 0))

    def test_t1_is_end_point(self):
        x, y = g.calculate_bezier_point(1, self.p0, self.p1, self.p2, self.p3)
        self.assertAlmostEqual(x, 10)
        self.assertAlmostEqual(y, 0)

    def test_midpoint_matches_manual_calc(self):
        # Symmetric control points -> x=5 at t=0.5.
        x, y = g.calculate_bezier_point(0.5, self.p0, self.p1, self.p2, self.p3)
        self.assertAlmostEqual(x, 5)
        self.assertAlmostEqual(y, 7.5)


class FindAlignmentGuidesTests(unittest.TestCase):
    def _shape(self, x, y):
        return SimpleNamespace(x=x, y=y)

    def test_detects_vertical_and_horizontal_alignment(self):
        moving = self._shape(100, 100)
        others = [self._shape(102, 400), self._shape(400, 98)]
        guides = g.find_alignment_guides(moving, others)
        self.assertEqual(guides["vertical"], [102])
        self.assertEqual(guides["horizontal"], [98])

    def test_skips_the_moving_shape_itself(self):
        moving = self._shape(100, 100)
        guides = g.find_alignment_guides(moving, [moving])
        self.assertEqual(guides, {"vertical": [], "horizontal": []})

    def test_outside_tolerance_gives_no_guides(self):
        moving = self._shape(100, 100)
        others = [self._shape(120, 130)]
        guides = g.find_alignment_guides(moving, others)
        self.assertEqual(guides, {"vertical": [], "horizontal": []})

    def test_custom_tolerance(self):
        moving = self._shape(100, 100)
        others = [self._shape(108, 100)]
        self.assertEqual(g.find_alignment_guides(moving, others, tolerance=10)["vertical"], [108])


class NormalizeRectTests(unittest.TestCase):
    def test_reorders_swapped_corners(self):
        self.assertEqual(g.normalize_rect(10, 10, 0, 0), (0, 0, 10, 10))

    def test_already_normalized_unchanged(self):
        self.assertEqual(g.normalize_rect(0, 0, 10, 10), (0, 0, 10, 10))


class BoundingRectTests(unittest.TestCase):
    def test_empty_points_returns_zeros(self):
        self.assertEqual(g.calculate_bounding_rect([]), (0, 0, 0, 0))

    def test_encloses_all_points(self):
        pts = [(1, 5), (-2, 3), (4, -1)]
        self.assertEqual(g.calculate_bounding_rect(pts), (-2, -1, 4, 5))


if __name__ == "__main__":
    unittest.main()
