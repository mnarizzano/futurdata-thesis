"""
Unit tests for Connection model.

Covers:
  - Instance creation, id assignment, and id counter increment behaviour.
  - Endpoint resolution via anchor lookup (get_endpoints).
  - Automatic anchor selection based on relative shape position (auto_calculate_anchors).
  - Dictionary serialization (to_dict).
  - Dictionary deserialization / reconstruction (from_dict), including failure cases.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_connection -v
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Path configuration to locate the source code
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models.connection import Connection


def make_shape(shape_id, x, y, points=None):
    """Build a lightweight mock Shape with the interface Connection relies on."""
    shape = MagicMock()
    shape.id = shape_id
    shape.x = x
    shape.y = y
    shape.get_connection_points.return_value = points if points is not None else {
        "top": (x, y - 10),
        "bottom": (x, y + 10),
        "left": (x - 10, y),
        "right": (x + 10, y),
    }
    return shape


class ConnectionTests(unittest.TestCase):

    def setUp(self):
        """Reset the shared id counter before every test for deterministic ids."""
        Connection.reset_counter()
        self.shape_a = make_shape(1, x=0, y=0)
        self.shape_b = make_shape(2, x=100, y=100)

    def test_init_assigns_incrementing_ids(self):
        """Verify each new Connection receives a unique, incrementing id."""
        conn1 = Connection(self.shape_a, self.shape_b)
        conn2 = Connection(self.shape_a, self.shape_b)
        self.assertEqual(conn1.id, 1)
        self.assertEqual(conn2.id, 2)

    def test_init_sets_default_attributes(self):
        """Verify defaults for connection_type, anchors, and arrow_id."""
        conn = Connection(self.shape_a, self.shape_b)
        self.assertEqual(conn.from_shape, self.shape_a)
        self.assertEqual(conn.to_shape, self.shape_b)
        self.assertEqual(conn.connection_type, "solid")
        self.assertEqual(conn.from_anchor, "bottom")
        self.assertEqual(conn.to_anchor, "top")
        self.assertIsNone(conn.arrow_id)

    def test_init_accepts_custom_type_and_anchors(self):
        """Verify custom connection_type and anchor overrides are stored."""
        conn = Connection(self.shape_a, self.shape_b,
                           connection_type="dashed",
                           from_anchor="left",
                           to_anchor="right")
        self.assertEqual(conn.connection_type, "dashed")
        self.assertEqual(conn.from_anchor, "left")
        self.assertEqual(conn.to_anchor, "right")

    def test_reset_counter_restarts_id_sequence(self):
        """Verify reset_counter brings the next assigned id back to 1."""
        Connection(self.shape_a, self.shape_b)
        Connection.reset_counter()
        conn = Connection(self.shape_a, self.shape_b)
        self.assertEqual(conn.id, 1)

    def test_get_endpoints_resolves_anchor_coordinates(self):
        """Verify get_endpoints looks up the correct anchor point on each shape."""
        conn = Connection(self.shape_a, self.shape_b, from_anchor="right", to_anchor="left")
        start, end = conn.get_endpoints()
        self.assertEqual(start, (10, 0))
        self.assertEqual(end, (90, 100))
        self.shape_a.get_connection_points.assert_called_once()
        self.shape_b.get_connection_points.assert_called_once()

    def test_get_endpoints_falls_back_to_shape_xy_when_anchor_missing(self):
        """Verify get_endpoints falls back to shape.x/shape.y if the anchor key is absent."""
        shape_a = make_shape(1, x=5, y=7, points={})
        shape_b = make_shape(2, x=20, y=30, points={})
        conn = Connection(shape_a, shape_b, from_anchor="bottom", to_anchor="top")
        start, end = conn.get_endpoints()
        self.assertEqual(start, (5, 7))
        self.assertEqual(end, (20, 30))

    def test_auto_calculate_anchors_horizontal_positive_dx(self):
        """Verify horizontal dominant movement to the right picks right/left anchors."""
        shape_a = make_shape(1, x=0, y=0)
        shape_b = make_shape(2, x=100, y=10)  # dx=100 > dy=10
        conn = Connection(shape_a, shape_b)
        conn.auto_calculate_anchors()
        self.assertEqual(conn.from_anchor, "right")
        self.assertEqual(conn.to_anchor, "left")

    def test_auto_calculate_anchors_horizontal_negative_dx(self):
        """Verify horizontal dominant movement to the left picks left/right anchors."""
        shape_a = make_shape(1, x=100, y=0)
        shape_b = make_shape(2, x=0, y=10)  # dx=-100
        conn = Connection(shape_a, shape_b)
        conn.auto_calculate_anchors()
        self.assertEqual(conn.from_anchor, "left")
        self.assertEqual(conn.to_anchor, "right")

    def test_auto_calculate_anchors_vertical_positive_dy(self):
        """Verify vertical dominant movement downward picks bottom/top anchors."""
        shape_a = make_shape(1, x=0, y=0)
        shape_b = make_shape(2, x=5, y=100)  # dy=100 > dx=5
        conn = Connection(shape_a, shape_b)
        conn.auto_calculate_anchors()
        self.assertEqual(conn.from_anchor, "bottom")
        self.assertEqual(conn.to_anchor, "top")

    def test_auto_calculate_anchors_vertical_negative_dy(self):
        """Verify vertical dominant movement upward picks top/bottom anchors."""
        shape_a = make_shape(1, x=0, y=100)
        shape_b = make_shape(2, x=5, y=0)  # dy=-100
        conn = Connection(shape_a, shape_b)
        conn.auto_calculate_anchors()
        self.assertEqual(conn.from_anchor, "top")
        self.assertEqual(conn.to_anchor, "bottom")

    def test_to_dict_serializes_all_fields(self):
        """Verify to_dict returns a dictionary with the expected keys and values."""
        conn = Connection(self.shape_a, self.shape_b,
                           connection_type="dashed",
                           from_anchor="left",
                           to_anchor="right")
        result = conn.to_dict()
        self.assertEqual(result, {
            "id": conn.id,
            "from_id": 1,
            "to_id": 2,
            "type": "dashed",
            "from_anchor": "left",
            "to_anchor": "right",
        })

    def test_from_dict_rebuilds_connection_with_matching_shapes(self):
        """Verify from_dict resolves shape ids and restores the persisted id."""
        data = {
            "id": 42,
            "from_id": 1,
            "to_id": 2,
            "type": "dashed",
            "from_anchor": "left",
            "to_anchor": "right",
        }
        conn = Connection.from_dict(data, [self.shape_a, self.shape_b])
        self.assertIsNotNone(conn)
        self.assertEqual(conn.id, 42)
        self.assertEqual(conn.from_shape, self.shape_a)
        self.assertEqual(conn.to_shape, self.shape_b)
        self.assertEqual(conn.connection_type, "dashed")
        self.assertEqual(conn.from_anchor, "left")
        self.assertEqual(conn.to_anchor, "right")

    def test_from_dict_uses_defaults_when_optional_fields_missing(self):
        """Verify from_dict falls back to default type/anchors when absent from data."""
        data = {"id": 5, "from_id": 1, "to_id": 2}
        conn = Connection.from_dict(data, [self.shape_a, self.shape_b])
        self.assertIsNotNone(conn)
        self.assertEqual(conn.connection_type, "solid")
        self.assertEqual(conn.from_anchor, "bottom")
        self.assertEqual(conn.to_anchor, "top")

    def test_from_dict_returns_none_when_from_shape_missing(self):
        """Verify from_dict returns None if the from_id cannot be resolved."""
        data = {"id": 1, "from_id": 999, "to_id": 2}
        conn = Connection.from_dict(data, [self.shape_a, self.shape_b])
        self.assertIsNone(conn)

    def test_from_dict_returns_none_when_to_shape_missing(self):
        """Verify from_dict returns None if the to_id cannot be resolved."""
        data = {"id": 1, "from_id": 1, "to_id": 999}
        conn = Connection.from_dict(data, [self.shape_a, self.shape_b])
        self.assertIsNone(conn)

    def test_from_dict_returns_none_with_empty_shape_list(self):
        """Verify from_dict returns None when no candidate shapes are provided."""
        data = {"id": 1, "from_id": 1, "to_id": 2}
        conn = Connection.from_dict(data, [])
        self.assertIsNone(conn)


if __name__ == "__main__":
    unittest.main()
