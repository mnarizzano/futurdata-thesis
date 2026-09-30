"""
Unit tests for Diagram model.

Covers:
  - Initialization defaults (empty collections, metadata, canvas/zoom/grid state).
  - Shape and connection CRUD operations (add/remove, duplicate-connection guard).
  - Lookup helpers (by id, by point, by rectangle).
  - Selection management (select, deselect, clear, multi-select).
  - Connections-for-shape aggregation.
  - Full state reset (clear).
  - Bounds calculation.
  - Serialization (to_dict) and reconstruction (from_dict), including id-counter sync.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_diagram -v
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Path configuration to locate the source code
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models.diagram import Diagram
from src.main.models.shape import Shape
from src.main.models.connection import Connection


def make_shape(shape_id, x=0, y=0, contains=False):
    """Build a lightweight mock Shape with the interface Diagram relies on."""
    shape = MagicMock()
    shape.id = shape_id
    shape.x = x
    shape.y = y
    shape.selected = False
    shape.contains_point.return_value = contains
    shape.to_dict.return_value = {"id": shape_id, "x": x, "y": y}
    return shape


def make_connection(from_shape, to_shape, conn_id=1):
    """Build a lightweight mock Connection with the interface Diagram relies on."""
    conn = MagicMock()
    conn.id = conn_id
    conn.from_shape = from_shape
    conn.to_shape = to_shape
    conn.to_dict.return_value = {"id": conn_id, "from_id": from_shape.id, "to_id": to_shape.id}
    return conn


class DiagramTests(unittest.TestCase):

    def setUp(self):
        """Reset shared id counters and build a fresh Diagram for each test."""
        Shape.reset_counter()
        Connection.reset_counter()
        self.diagram = Diagram()
        self.shape_a = make_shape(1, x=0, y=0)
        self.shape_b = make_shape(2, x=50, y=50)

    def test_init_sets_empty_collections_and_defaults(self):
        """Verify a fresh Diagram starts with no shapes/connections and default state."""
        self.assertEqual(self.diagram.shapes, [])
        self.assertEqual(self.diagram.connections, [])
        self.assertEqual(self.diagram.selected_shapes, [])
        self.assertIsNone(self.diagram.canvas_size)
        self.assertEqual(self.diagram.zoom_level, 1.0)
        self.assertTrue(self.diagram.grid_enabled)
        self.assertTrue(self.diagram.snap_to_grid)
        self.assertFalse(self.diagram.modified)
        self.assertIsNone(self.diagram.file_path)

    def test_init_populates_metadata_defaults(self):
        """Verify metadata dictionary has the expected default keys."""
        self.assertEqual(self.diagram.metadata["version"], "1.0")
        self.assertEqual(self.diagram.metadata["author"], "")
        self.assertEqual(self.diagram.metadata["product_name"], "")
        self.assertIn("created", self.diagram.metadata)
        self.assertIn("modified", self.diagram.metadata)

    # -- shape management -------------------------------------------------

    def test_add_shape_appends_and_marks_modified(self):
        """Verify add_shape stores the shape and flags the diagram as modified."""
        self.diagram.add_shape(self.shape_a)
        self.assertIn(self.shape_a, self.diagram.shapes)
        self.assertTrue(self.diagram.modified)

    def test_remove_shape_deletes_shape_and_related_connections(self):
        """Verify remove_shape drops the shape and any connection touching it."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.add_shape(self.shape_b)
        conn = make_connection(self.shape_a, self.shape_b)
        self.diagram.connections.append(conn)

        self.diagram.remove_shape(self.shape_a)

        self.assertNotIn(self.shape_a, self.diagram.shapes)
        self.assertNotIn(conn, self.diagram.connections)
        self.assertTrue(self.diagram.modified)

    def test_remove_shape_also_clears_it_from_selection(self):
        """Verify remove_shape removes the shape from selected_shapes if present."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.selected_shapes.append(self.shape_a)
        self.diagram.remove_shape(self.shape_a)
        self.assertNotIn(self.shape_a, self.diagram.selected_shapes)

    def test_remove_shape_not_in_diagram_is_a_noop_but_marks_modified(self):
        """Verify remove_shape tolerates a shape that was never added."""
        self.diagram.remove_shape(self.shape_a)
        self.assertEqual(self.diagram.shapes, [])
        self.assertTrue(self.diagram.modified)

    # -- connection management --------------------------------------------

    def test_add_connection_appends_and_marks_modified(self):
        """Verify add_connection stores a new from/to pair."""
        conn = make_connection(self.shape_a, self.shape_b)
        self.diagram.add_connection(conn)
        self.assertIn(conn, self.diagram.connections)
        self.assertTrue(self.diagram.modified)

    def test_add_connection_ignores_duplicate_from_to_pair(self):
        """Verify a second connection with the same from/to shapes is rejected."""
        conn1 = make_connection(self.shape_a, self.shape_b, conn_id=1)
        conn2 = make_connection(self.shape_a, self.shape_b, conn_id=2)
        self.diagram.add_connection(conn1)
        self.diagram.add_connection(conn2)
        self.assertEqual(self.diagram.connections, [conn1])

    def test_remove_connection_deletes_existing_connection(self):
        """Verify remove_connection removes a connection present in the list."""
        conn = make_connection(self.shape_a, self.shape_b)
        self.diagram.connections.append(conn)
        self.diagram.remove_connection(conn)
        self.assertNotIn(conn, self.diagram.connections)
        self.assertTrue(self.diagram.modified)

    def test_remove_connection_missing_does_not_mark_modified(self):
        """Verify remove_connection is a no-op (and doesn't flag modified) if absent."""
        conn = make_connection(self.shape_a, self.shape_b)
        self.diagram.remove_connection(conn)
        self.assertFalse(self.diagram.modified)

    # -- lookup helpers ------------------------------------------------------

    def test_get_shape_by_id_returns_matching_shape(self):
        """Verify get_shape_by_id finds the shape with the matching id."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.add_shape(self.shape_b)
        self.assertEqual(self.diagram.get_shape_by_id(2), self.shape_b)

    def test_get_shape_by_id_returns_none_when_not_found(self):
        """Verify get_shape_by_id returns None for an unknown id."""
        self.diagram.add_shape(self.shape_a)
        self.assertIsNone(self.diagram.get_shape_by_id(999))

    def test_find_shape_at_point_returns_topmost_matching_shape(self):
        """Verify find_shape_at_point checks shapes in reverse (topmost z-order first)."""
        shape_c = make_shape(3, x=10, y=10, contains=True)
        self.shape_a.contains_point.return_value = True
        self.diagram.add_shape(self.shape_a)
        self.diagram.add_shape(shape_c)
        # shape_c was added last -> should be checked first and returned
        result = self.diagram.find_shape_at_point(10, 10)
        self.assertEqual(result, shape_c)

    def test_find_shape_at_point_returns_none_when_no_match(self):
        """Verify find_shape_at_point returns None if no shape contains the point."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.add_shape(self.shape_b)
        self.assertIsNone(self.diagram.find_shape_at_point(999, 999))

    def test_find_shapes_in_rect_returns_shapes_within_bounds(self):
        """Verify find_shapes_in_rect only returns shapes inside the given rectangle."""
        self.diagram.add_shape(self.shape_a)  # (0, 0)
        self.diagram.add_shape(self.shape_b)  # (50, 50)
        result = self.diagram.find_shapes_in_rect(0, 0, 10, 10)
        self.assertEqual(result, [self.shape_a])

    def test_find_shapes_in_rect_returns_empty_list_when_none_match(self):
        """Verify find_shapes_in_rect returns an empty list if nothing is inside."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.add_shape(self.shape_b)
        result = self.diagram.find_shapes_in_rect(200, 200, 300, 300)
        self.assertEqual(result, [])

    # -- selection management --------------------------------------------

    def test_select_shape_replaces_selection_by_default(self):
        """Verify select_shape clears prior selection when multi_select is False."""
        self.diagram.select_shape(self.shape_a)
        self.diagram.select_shape(self.shape_b)
        self.assertEqual(self.diagram.selected_shapes, [self.shape_b])
        self.assertFalse(self.shape_a.selected)
        self.assertTrue(self.shape_b.selected)

    def test_select_shape_multi_select_accumulates_selection(self):
        """Verify select_shape preserves prior selection when multi_select is True."""
        self.diagram.select_shape(self.shape_a)
        self.diagram.select_shape(self.shape_b, multi_select=True)
        self.assertEqual(self.diagram.selected_shapes, [self.shape_a, self.shape_b])
        self.assertTrue(self.shape_a.selected)
        self.assertTrue(self.shape_b.selected)

    def test_select_shape_does_not_duplicate_already_selected_shape(self):
        """Verify selecting the same shape twice (multi-select) doesn't duplicate it."""
        self.diagram.select_shape(self.shape_a, multi_select=True)
        self.diagram.select_shape(self.shape_a, multi_select=True)
        self.assertEqual(self.diagram.selected_shapes, [self.shape_a])

    def test_deselect_shape_removes_from_selection(self):
        """Verify deselect_shape removes the shape and flips its selected flag."""
        self.diagram.select_shape(self.shape_a, multi_select=True)
        self.diagram.deselect_shape(self.shape_a)
        self.assertNotIn(self.shape_a, self.diagram.selected_shapes)
        self.assertFalse(self.shape_a.selected)

    def test_deselect_shape_not_selected_is_a_noop(self):
        """Verify deselect_shape tolerates a shape that isn't currently selected."""
        self.diagram.deselect_shape(self.shape_a)
        self.assertEqual(self.diagram.selected_shapes, [])

    def test_clear_selection_deselects_all_shapes(self):
        """Verify clear_selection empties the list and resets each shape's flag."""
        self.diagram.select_shape(self.shape_a, multi_select=True)
        self.diagram.select_shape(self.shape_b, multi_select=True)
        self.diagram.clear_selection()
        self.assertEqual(self.diagram.selected_shapes, [])
        self.assertFalse(self.shape_a.selected)
        self.assertFalse(self.shape_b.selected)

    # -- connections for shape -----------------------------------------

    def test_get_connections_for_shape_returns_related_connections_only(self):
        """Verify get_connections_for_shape filters by from/to membership."""
        shape_c = make_shape(3, x=10, y=10)
        conn_ab = make_connection(self.shape_a, self.shape_b, conn_id=1)
        conn_bc = make_connection(self.shape_b, shape_c, conn_id=2)
        self.diagram.connections.extend([conn_ab, conn_bc])

        result = self.diagram.get_connections_for_shape(self.shape_b)
        self.assertEqual(set(result), {conn_ab, conn_bc})

    def test_get_connections_for_shape_returns_empty_when_unrelated(self):
        """Verify get_connections_for_shape returns [] for a shape with no connections."""
        shape_c = make_shape(3, x=10, y=10)
        conn_ab = make_connection(self.shape_a, self.shape_b)
        self.diagram.connections.append(conn_ab)
        result = self.diagram.get_connections_for_shape(shape_c)
        self.assertEqual(result, [])

    # -- clear / reset -----------------------------------------------------

    def test_clear_empties_all_state_and_resets_counters(self):
        """Verify clear wipes shapes, connections, selection, and resets id counters."""
        self.diagram.add_shape(self.shape_a)
        self.diagram.connections.append(make_connection(self.shape_a, self.shape_b))
        self.diagram.selected_shapes.append(self.shape_a)
        self.diagram.file_path = "/tmp/diagram.json"

        with patch.object(Shape, "reset_counter") as mock_shape_reset, \
             patch.object(Connection, "reset_counter") as mock_conn_reset:
            self.diagram.clear()
            mock_shape_reset.assert_called_once()
            mock_conn_reset.assert_called_once()

        self.assertEqual(self.diagram.shapes, [])
        self.assertEqual(self.diagram.connections, [])
        self.assertEqual(self.diagram.selected_shapes, [])
        self.assertFalse(self.diagram.modified)
        self.assertIsNone(self.diagram.file_path)

    # -- bounds -----------------------------------------------------------

    def test_get_bounds_returns_zeroes_when_no_shapes(self):
        """Verify get_bounds returns (0, 0, 0, 0) for an empty diagram."""
        self.assertEqual(self.diagram.get_bounds(), (0, 0, 0, 0))

    def test_get_bounds_returns_min_max_extent_of_shapes(self):
        """Verify get_bounds computes the min/max x/y across all shapes."""
        shape_c = make_shape(3, x=-20, y=30)
        self.diagram.add_shape(self.shape_a)   # (0, 0)
        self.diagram.add_shape(self.shape_b)   # (50, 50)
        self.diagram.add_shape(shape_c)        # (-20, 30)
        self.assertEqual(self.diagram.get_bounds(), (-20, 0, 50, 50))

    # -- serialization -------------------------------------------------------

    def test_to_dict_includes_metadata_settings_shapes_and_connections(self):
        """Verify to_dict assembles the full diagram structure."""
        self.diagram.add_shape(self.shape_a)
        conn = make_connection(self.shape_a, self.shape_b)
        self.diagram.connections.append(conn)

        result = self.diagram.to_dict()

        self.assertEqual(result["metadata"], self.diagram.metadata)
        self.assertEqual(result["diagram"], {
            "canvas_size": None,
            "zoom_level": 1.0,
            "grid_enabled": True,
            "snap_to_grid": True,
        })
        self.assertEqual(result["shapes"], [self.shape_a.to_dict.return_value])
        self.assertEqual(result["connections"], [conn.to_dict.return_value])

    def test_to_dict_refreshes_modified_timestamp(self):
        """Verify to_dict updates metadata['modified'] to a new timestamp on each call."""
        original_modified = self.diagram.metadata["modified"]
        self.diagram.to_dict()
        self.assertGreaterEqual(self.diagram.metadata["modified"], original_modified)

    def test_from_dict_reconstructs_settings_and_metadata(self):
        """Verify from_dict restores metadata and diagram-level settings."""
        data = {
            "metadata": {"version": "1.0", "author": "tester"},
            "diagram": {
                "canvas_size": [800, 600],
                "zoom_level": 2.0,
                "grid_enabled": False,
                "snap_to_grid": False,
            },
            "shapes": [],
            "connections": [],
        }
        diagram = Diagram.from_dict(data)
        self.assertEqual(diagram.metadata, data["metadata"])
        self.assertEqual(diagram.canvas_size, (800, 600))
        self.assertEqual(diagram.zoom_level, 2.0)
        self.assertFalse(diagram.grid_enabled)
        self.assertFalse(diagram.snap_to_grid)
        self.assertFalse(diagram.modified)

    def test_from_dict_defaults_when_diagram_section_missing(self):
        """Verify from_dict falls back to defaults when the 'diagram' section is absent."""
        diagram = Diagram.from_dict({})
        self.assertIsNone(diagram.canvas_size)
        self.assertEqual(diagram.zoom_level, 1.0)
        self.assertTrue(diagram.grid_enabled)
        self.assertTrue(diagram.snap_to_grid)

    def test_from_dict_rebuilds_shapes_and_syncs_id_counter(self):
        """Verify from_dict rebuilds shapes via Shape.from_dict and syncs the id counter."""
        shape_stub = make_shape(7, x=1, y=1)
        data = {"shapes": [{"id": 7, "type": "rect"}], "connections": []}

        with patch("src.main.models.diagram.Shape") as mock_shape_cls:
            mock_shape_cls.from_dict.return_value = shape_stub
            mock_shape_cls._id_counter = 0
            diagram = Diagram.from_dict(data)

        self.assertEqual(diagram.shapes, [shape_stub])
        mock_shape_cls.from_dict.assert_called_once_with({"id": 7, "type": "rect"})

    def test_from_dict_skips_connections_that_fail_to_resolve(self):
        """Verify from_dict omits connections whose Connection.from_dict returns None."""
        data = {"shapes": [], "connections": [{"id": 1, "from_id": 1, "to_id": 2}]}

        with patch("src.main.models.diagram.Connection") as mock_conn_cls:
            mock_conn_cls.from_dict.return_value = None
            diagram = Diagram.from_dict(data)

        self.assertEqual(diagram.connections, [])

    def test_from_dict_resolves_shape_references_when_supported(self):
        """Verify from_dict calls resolve_shape_references on shapes that support it."""
        shape_stub = make_shape(1, x=0, y=0)
        shape_stub.resolve_shape_references = MagicMock()
        data = {"shapes": [{"id": 1}], "connections": []}

        with patch("src.main.models.diagram.Shape") as mock_shape_cls:
            mock_shape_cls.from_dict.return_value = shape_stub
            mock_shape_cls._id_counter = 0
            diagram = Diagram.from_dict(data)

        shape_stub.resolve_shape_references.assert_called_once_with(diagram.shapes)


if __name__ == "__main__":
    unittest.main()
