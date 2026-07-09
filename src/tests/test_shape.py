"""
Unit tests for the Shape model hierarchy.

Covers:
  - Base Shape: id assignment/counter, move, to_dict, abstract method contracts,
    and from_dict dispatch/backward-compatibility logic.
  - ActionCircle: bounds, connection points, hit testing, serialization.
  - DiamondStep: bounds, connection points, hit testing (diamond/rhombus), serialization.
  - ComponentBox: dynamic properties dict, backward-compatible accessors, bounds,
    connection points, hit testing, serialization, and property loading.
  - ArrowShape: anchor auto-calculation, geometry derived from linked shapes,
    bounds, connection points, hit testing, serialization, and reference resolution.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_shape -v
"""
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Path configuration to locate the source code
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models.shape import (
    Shape,
    ActionCircle,
    DiamondStep,
    ComponentBox,
    ArrowShape,
)


def make_linked_shape(shape_id, x, y, points=None):
    """Build a lightweight mock shape usable as an ArrowShape endpoint."""
    shape = MagicMock()
    shape.id = shape_id
    shape.x = x
    shape.y = y
    shape.get_connection_points.return_value = points or {
        "top": (x, y - 10),
        "bottom": (x, y + 10),
        "left": (x - 10, y),
        "right": (x + 10, y),
    }
    return shape


class ShapeBaseTests(unittest.TestCase):
    """Tests for the abstract Shape base class using ActionCircle as a concrete stand-in."""

    def setUp(self):
        Shape.reset_counter()

    def test_init_assigns_incrementing_ids(self):
        """Verify each new Shape subclass instance gets a unique incrementing id."""
        s1 = ActionCircle(0, 0)
        s2 = ActionCircle(10, 10)
        self.assertEqual(s1.id, 1)
        self.assertEqual(s2.id, 2)

    def test_init_sets_common_default_attributes(self):
        """Verify shape_type, text placeholders, and selection state defaults."""
        s = ActionCircle(5, 7)
        self.assertEqual(s.x, 5)
        self.assertEqual(s.y, 7)
        self.assertEqual(s.shape_type, "action")
        self.assertIsNone(s.shape_id)
        self.assertIsNone(s.text_id)
        self.assertFalse(s.selected)

    def test_reset_counter_restarts_id_sequence(self):
        """Verify reset_counter brings the next assigned id back to 1."""
        ActionCircle(0, 0)
        Shape.reset_counter()
        s = ActionCircle(0, 0)
        self.assertEqual(s.id, 1)

    def test_get_bounds_not_implemented_on_base_class(self):
        """Verify the abstract get_bounds raises when called directly on Shape."""
        s = Shape(0, 0, "generic")
        with self.assertRaises(NotImplementedError):
            s.get_bounds()

    def test_get_connection_points_not_implemented_on_base_class(self):
        """Verify the abstract get_connection_points raises on Shape."""
        s = Shape(0, 0, "generic")
        with self.assertRaises(NotImplementedError):
            s.get_connection_points()

    def test_contains_point_not_implemented_on_base_class(self):
        """Verify the abstract contains_point raises on Shape."""
        s = Shape(0, 0, "generic")
        with self.assertRaises(NotImplementedError):
            s.contains_point(0, 0)

    def test_move_translates_position_by_delta(self):
        """Verify move adds dx/dy to the current x/y coordinates."""
        s = ActionCircle(10, 10)
        s.move(5, -3)
        self.assertEqual(s.x, 15)
        self.assertEqual(s.y, 7)

    def test_base_to_dict_contains_common_fields(self):
        """Verify Shape.to_dict returns id, type, position, and text."""
        s = Shape(1, 2, "generic")
        s.id = 99
        s.text = "hello"
        result = s.to_dict()
        self.assertEqual(result, {"id": 99, "type": "generic", "x": 1, "y": 2, "text": "hello"})

    def test_from_dict_dispatches_action_type(self):
        """Verify from_dict builds an ActionCircle for type 'action'."""
        data = {"id": 3, "type": "action", "x": 1, "y": 2, "text": "Go"}
        shape = Shape.from_dict(data)
        self.assertIsInstance(shape, ActionCircle)
        self.assertEqual(shape.id, 3)
        self.assertEqual(shape.text, "Go")

    def test_from_dict_dispatches_diamond_type(self):
        """Verify from_dict builds a DiamondStep for type 'diamond'."""
        data = {"id": 4, "type": "diamond", "x": 1, "y": 2}
        shape = Shape.from_dict(data)
        self.assertIsInstance(shape, DiamondStep)

    def test_from_dict_dispatches_component_type(self):
        """Verify from_dict builds a ComponentBox for type 'component'."""
        data = {"id": 5, "type": "component", "x": 1, "y": 2}
        shape = Shape.from_dict(data)
        self.assertIsInstance(shape, ComponentBox)

    def test_from_dict_dispatches_arrow_type(self):
        """Verify from_dict builds an ArrowShape for type 'arrow'."""
        data = {"id": 6, "type": "arrow", "x": 1, "y": 2}
        shape = Shape.from_dict(data)
        self.assertIsInstance(shape, ArrowShape)

    def test_from_dict_raises_on_unknown_type(self):
        """Verify from_dict raises ValueError for an unrecognized shape type."""
        with self.assertRaises(ValueError):
            Shape.from_dict({"id": 1, "type": "hexagon", "x": 0, "y": 0})

    @unittest.expectedFailure
    def test_from_dict_legacy_product_maps_to_component_root_with_text(self):
        """Verify legacy 'product' type maps to a root ComponentBox, using first text line as name.

        KNOWN BUG: inside the 'product' branch, Shape.from_dict computes a trimmed
        shape.text (first line only). However, right after the if/elif chain, the
        unconditional line `shape.text = data.get("text", "")` overwrites it with the
        raw, untrimmed text for every shape type, including 'product'. So shape.text
        ends up as the full raw text instead of just the first line, even though
        properties['name'] and properties['node_type'] are set correctly. This test
        documents the intended behavior and is expected to fail until that overwrite
        is scoped to exclude the 'product' branch (out of scope for this test task).
        """
        data = {"id": 7, "type": "product", "x": 0, "y": 0, "text": "Bike Frame\nExtra info"}
        shape = Shape.from_dict(data)
        self.assertIsInstance(shape, ComponentBox)
        self.assertEqual(shape.properties["node_type"], "Root")
        self.assertEqual(shape.properties["name"], "Bike Frame")
        self.assertEqual(shape.text, "Bike Frame")

    @unittest.expectedFailure
    def test_from_dict_legacy_product_without_text_uses_default_label(self):
        """Verify legacy 'product' type without text falls back to 'Root Component'.

        KNOWN BUG: same root cause as above -- the unconditional
        `shape.text = data.get("text", "")` after the if/elif chain overwrites the
        'Root Component' default computed inside the 'product' branch, leaving
        shape.text as an empty string instead. Expected to fail until fixed.
        """
        data = {"id": 8, "type": "product", "x": 0, "y": 0}
        shape = Shape.from_dict(data)
        self.assertEqual(shape.text, "Root Component")

    def test_from_dict_calls_load_properties_when_available(self):
        """Verify from_dict invokes load_properties on subclasses that define it."""
        data = {"id": 9, "type": "action", "x": 0, "y": 0,
                "step_description": "desc", "tools": "wrench", "image_path": "img.png"}
        shape = Shape.from_dict(data)
        self.assertEqual(shape.step_description, "desc")
        self.assertEqual(shape.tools, "wrench")
        self.assertEqual(shape.image_path, "img.png")


class ActionCircleTests(unittest.TestCase):

    def setUp(self):
        Shape.reset_counter()
        self.shape = ActionCircle(100, 100)

    def test_init_sets_defaults(self):
        """Verify ActionCircle default text and metadata fields."""
        self.assertEqual(self.shape.text, "Step")
        self.assertEqual(self.shape.step_description, "")
        self.assertEqual(self.shape.tools, "")
        self.assertEqual(self.shape.image_path, "")

    def test_get_bounds_returns_square_around_center(self):
        """Verify get_bounds returns a bounding box of radius RADIUS around (x, y)."""
        r = ActionCircle.RADIUS
        self.assertEqual(self.shape.get_bounds(), (100 - r, 100 - r, 100 + r, 100 + r))

    def test_get_connection_points_returns_four_cardinal_points(self):
        """Verify get_connection_points returns top/bottom/left/right at radius distance."""
        r = ActionCircle.RADIUS
        points = self.shape.get_connection_points()
        self.assertEqual(points["top"], (100, 100 - r))
        self.assertEqual(points["bottom"], (100, 100 + r))
        self.assertEqual(points["left"], (100 - r, 100))
        self.assertEqual(points["right"], (100 + r, 100))

    def test_contains_point_true_within_radius(self):
        """Verify contains_point returns True for a point inside the circle."""
        self.assertTrue(self.shape.contains_point(100, 100))
        self.assertTrue(self.shape.contains_point(100 + ActionCircle.RADIUS, 100))

    def test_contains_point_false_outside_radius(self):
        """Verify contains_point returns False for a point outside the circle."""
        self.assertFalse(self.shape.contains_point(100 + ActionCircle.RADIUS + 1, 100))

    def test_to_dict_includes_action_specific_fields(self):
        """Verify to_dict merges base fields with step_description/tools/image_path."""
        self.shape.step_description = "Cut material"
        self.shape.tools = "saw"
        self.shape.image_path = "/img/saw.png"
        result = self.shape.to_dict()
        self.assertEqual(result["step_description"], "Cut material")
        self.assertEqual(result["tools"], "saw")
        self.assertEqual(result["image_path"], "/img/saw.png")
        self.assertEqual(result["type"], "action")

    def test_load_properties_populates_action_fields(self):
        """Verify load_properties reads step_description/tools/image_path with defaults."""
        self.shape.load_properties({"step_description": "Weld", "tools": "torch"})
        self.assertEqual(self.shape.step_description, "Weld")
        self.assertEqual(self.shape.tools, "torch")
        self.assertEqual(self.shape.image_path, "")


class DiamondStepTests(unittest.TestCase):

    def setUp(self):
        Shape.reset_counter()
        self.shape = DiamondStep(50, 50)

    def test_init_sets_defaults(self):
        """Verify DiamondStep default text and metadata fields."""
        self.assertEqual(self.shape.text, "Action")
        self.assertEqual(self.shape.action_id, "")
        self.assertEqual(self.shape.name, "")
        self.assertIsNone(self.shape.tool_id)

    def test_get_bounds_returns_square_around_center(self):
        """Verify get_bounds returns a bounding box of half-SIZE around (x, y)."""
        half = DiamondStep.SIZE / 2
        self.assertEqual(self.shape.get_bounds(), (50 - half, 50 - half, 50 + half, 50 + half))

    def test_get_connection_points_returns_four_cardinal_points(self):
        """Verify get_connection_points returns top/bottom/left/right at half-SIZE distance."""
        half = DiamondStep.SIZE / 2
        points = self.shape.get_connection_points()
        self.assertEqual(points["top"], (50, 50 - half))
        self.assertEqual(points["right"], (50 + half, 50))

    def test_contains_point_true_at_center(self):
        """Verify contains_point is True exactly at the shape's center."""
        self.assertTrue(self.shape.contains_point(50, 50))

    def test_contains_point_true_at_diamond_vertex(self):
        """Verify contains_point is True at a vertex of the diamond (Manhattan distance == half)."""
        half = DiamondStep.SIZE / 2
        self.assertTrue(self.shape.contains_point(50 + half, 50))

    def test_contains_point_false_outside_diamond(self):
        """Verify contains_point is False at a point outside the rhombus, e.g. bounding-box corner."""
        half = DiamondStep.SIZE / 2
        # Bounding box corner is outside a rhombus inscribed within it.
        self.assertFalse(self.shape.contains_point(50 + half, 50 + half))

    def test_to_dict_includes_diamond_specific_fields(self):
        """Verify to_dict merges base fields with action_id/name/description/tool_id/tools."""
        self.shape.action_id = "A1"
        self.shape.name = "Cut"
        self.shape.tool_id = 3
        result = self.shape.to_dict()
        self.assertEqual(result["action_id"], "A1")
        self.assertEqual(result["name"], "Cut")
        self.assertEqual(result["tool_id"], 3)

    def test_load_properties_populates_diamond_fields_with_defaults(self):
        """Verify load_properties reads diamond-specific keys and defaults missing ones."""
        self.shape.load_properties({"name": "Drill"})
        self.assertEqual(self.shape.name, "Drill")
        self.assertEqual(self.shape.action_id, "")
        self.assertIsNone(self.shape.tool_id)


class ComponentBoxTests(unittest.TestCase):

    def setUp(self):
        Shape.reset_counter()
        self.shape = ComponentBox(0, 0)

    def test_init_sets_default_properties_dict(self):
        """Verify ComponentBox starts with a copy of DEFAULT_PROPERTIES."""
        self.assertEqual(self.shape.properties, ComponentBox.DEFAULT_PROPERTIES)
        # Must be a copy, not the same dict object (mutation safety).
        self.assertIsNot(self.shape.properties, ComponentBox.DEFAULT_PROPERTIES)

    def test_mutating_properties_does_not_affect_class_default(self):
        """Verify changing one instance's properties doesn't leak into the class default."""
        self.shape.properties["name"] = "Wheel"
        self.assertEqual(ComponentBox.DEFAULT_PROPERTIES["name"], "")

    def test_component_name_property_getter_and_setter(self):
        """Verify component_name reads/writes properties['name']."""
        self.shape.component_name = "Frame"
        self.assertEqual(self.shape.component_name, "Frame")
        self.assertEqual(self.shape.properties["name"], "Frame")

    def test_color_id_property_getter_and_setter(self):
        """Verify color_id reads/writes properties['color_id']."""
        self.shape.color_id = 7
        self.assertEqual(self.shape.color_id, 7)
        self.assertEqual(self.shape.properties["color_id"], 7)

    def test_material_id_property_getter_and_setter(self):
        """Verify material_id reads/writes properties['material_id']."""
        self.shape.material_id = 2
        self.assertEqual(self.shape.material_id, 2)

    def test_weight_and_weight_unit_properties(self):
        """Verify weight and weight_unit read/write their respective properties keys."""
        self.shape.weight = "250"
        self.shape.weight_unit = "kg"
        self.assertEqual(self.shape.weight, "250")
        self.assertEqual(self.shape.weight_unit, "kg")

    def test_node_type_property_getter_and_setter(self):
        """Verify node_type reads/writes properties['node_type']."""
        self.shape.node_type = "Leaf"
        self.assertEqual(self.shape.node_type, "Leaf")

    def test_get_bounds_returns_box_around_center(self):
        """Verify get_bounds uses half WIDTH/HEIGHT around (x, y)."""
        shape = ComponentBox(100, 100)
        half_w, half_h = ComponentBox.WIDTH / 2, ComponentBox.HEIGHT / 2
        self.assertEqual(shape.get_bounds(), (100 - half_w, 100 - half_h, 100 + half_w, 100 + half_h))

    def test_get_connection_points_returns_four_cardinal_points(self):
        """Verify get_connection_points returns edge midpoints of the box."""
        shape = ComponentBox(100, 100)
        half_w, half_h = ComponentBox.WIDTH / 2, ComponentBox.HEIGHT / 2
        points = shape.get_connection_points()
        self.assertEqual(points["left"], (100 - half_w, 100))
        self.assertEqual(points["bottom"], (100, 100 + half_h))

    def test_contains_point_true_inside_box(self):
        """Verify contains_point is True for a point within the rectangle."""
        self.assertTrue(self.shape.contains_point(0, 0))

    def test_contains_point_false_outside_box(self):
        """Verify contains_point is False for a point outside the rectangle."""
        self.assertFalse(self.shape.contains_point(1000, 1000))

    def test_to_dict_includes_all_properties_and_legacy_key(self):
        """Verify to_dict flattens the properties dict and keeps 'component_name' for backward compat."""
        self.shape.properties["name"] = "Seat"
        self.shape.properties["brand"] = "Acme"
        result = self.shape.to_dict()
        self.assertEqual(result["name"], "Seat")
        self.assertEqual(result["brand"], "Acme")
        self.assertEqual(result["component_name"], "Seat")

    def test_load_properties_maps_dynamic_keys(self):
        """Verify load_properties copies arbitrary keys (excluding id/type/x/y/text) into properties."""
        data = {"id": 1, "type": "component", "x": 0, "y": 0, "text": "t",
                "brand": "Acme", "custom_field": "value"}
        self.shape.load_properties(data)
        self.assertEqual(self.shape.properties["brand"], "Acme")
        self.assertEqual(self.shape.properties["custom_field"], "value")
        self.assertNotIn("id", self.shape.properties)
        self.assertNotIn("type", self.shape.properties)

    def test_load_properties_maps_legacy_component_name_key(self):
        """Verify load_properties maps the legacy 'component_name' key onto properties['name']."""
        self.shape.load_properties({"component_name": "Legacy Part"})
        self.assertEqual(self.shape.properties["name"], "Legacy Part")


class ArrowShapeTests(unittest.TestCase):

    def setUp(self):
        Shape.reset_counter()

    def test_init_without_linked_shapes_uses_horizontal_default(self):
        """Verify a standalone arrow (no from/to shape) defaults to a rightward horizontal line."""
        arrow = ArrowShape(10, 20)
        self.assertEqual(arrow.angle, 0)
        self.assertEqual(arrow.end_x, 10 + ArrowShape.LENGTH)
        self.assertEqual(arrow.end_y, 20)
        self.assertIsNone(arrow.from_shape)
        self.assertIsNone(arrow.to_shape)

    def test_init_with_linked_shapes_computes_geometry(self):
        """Verify an arrow linked to two shapes derives its start/end from their anchors."""
        from_shape = make_linked_shape(1, x=0, y=0)
        to_shape = make_linked_shape(2, x=100, y=0)  # purely horizontal offset
        arrow = ArrowShape(0, 0, from_shape=from_shape, to_shape=to_shape)
        self.assertEqual(arrow.from_anchor, "right")
        self.assertEqual(arrow.to_anchor, "left")
        self.assertEqual((arrow.x, arrow.y), (10, 0))     # from_shape's 'right' point
        self.assertEqual((arrow.end_x, arrow.end_y), (90, 0))  # to_shape's 'left' point
        self.assertEqual(arrow.angle, 0)

    def test_auto_calculate_anchors_without_linked_shapes_is_noop(self):
        """Verify auto_calculate_anchors does nothing when shapes aren't linked."""
        arrow = ArrowShape(0, 0)
        arrow.auto_calculate_anchors()
        self.assertEqual(arrow.from_anchor, "bottom")
        self.assertEqual(arrow.to_anchor, "top")

    def test_auto_calculate_anchors_picks_vertical_when_dy_dominant(self):
        """Verify vertical dominant offset selects bottom/top anchors."""
        from_shape = make_linked_shape(1, x=0, y=0)
        to_shape = make_linked_shape(2, x=5, y=100)
        arrow = ArrowShape(0, 0, from_shape=from_shape, to_shape=to_shape)
        self.assertEqual(arrow.from_anchor, "bottom")
        self.assertEqual(arrow.to_anchor, "top")

    def test_get_bounds_includes_padding_around_line(self):
        """Verify get_bounds pads 15px around the min/max of start and end coordinates."""
        arrow = ArrowShape(0, 0)  # end at (LENGTH, 0)
        x1, y1, x2, y2 = arrow.get_bounds()
        self.assertEqual(x1, 0 - 15)
        self.assertEqual(y1, 0 - 15)
        self.assertEqual(x2, ArrowShape.LENGTH + 15)
        self.assertEqual(y2, 0 + 15)

    def test_get_bounds_refreshes_geometry_when_linked(self):
        """Verify get_bounds re-derives geometry from linked shapes before computing bounds."""
        from_shape = make_linked_shape(1, x=0, y=0)
        to_shape = make_linked_shape(2, x=100, y=0)
        arrow = ArrowShape(0, 0, from_shape=from_shape, to_shape=to_shape)
        # Move the linked shape and confirm bounds reflect the new position.
        to_shape.x = 200
        to_shape.get_connection_points.return_value = {
            "top": (200, -10), "bottom": (200, 10), "left": (190, 0), "right": (210, 0)
        }
        x1, y1, x2, y2 = arrow.get_bounds()
        self.assertEqual(x2, 190 + 15)

    def test_get_connection_points_returns_midpoint_offsets_and_endpoints(self):
        """Verify get_connection_points computes top/bottom at the midpoint and left/right at the endpoints."""
        arrow = ArrowShape(0, 0)  # start (0,0), end (LENGTH, 0)
        points = arrow.get_connection_points()
        mid_x = ArrowShape.LENGTH / 2
        self.assertEqual(points["top"], (mid_x, -20))
        self.assertEqual(points["bottom"], (mid_x, 20))
        self.assertEqual(points["left"], (0, 0))
        self.assertEqual(points["right"], (ArrowShape.LENGTH, 0))

    def test_contains_point_true_on_the_line(self):
        """Verify contains_point is True for a point sitting on the arrow's line."""
        arrow = ArrowShape(0, 0)  # horizontal line to (LENGTH, 0)
        self.assertTrue(arrow.contains_point(ArrowShape.LENGTH / 2, 0))

    def test_contains_point_false_far_from_the_line(self):
        """Verify contains_point is False for a point far from the arrow's line."""
        arrow = ArrowShape(0, 0)
        self.assertFalse(arrow.contains_point(ArrowShape.LENGTH / 2, 100))

    def test_contains_point_handles_zero_length_line(self):
        """Verify contains_point falls back to plain distance when start == end (degenerate line)."""
        arrow = ArrowShape(0, 0)
        arrow.end_x, arrow.end_y = 0, 0
        self.assertTrue(arrow.contains_point(5, 0))
        self.assertFalse(arrow.contains_point(50, 0))

    def test_to_dict_includes_arrow_specific_fields_and_shape_ids(self):
        """Verify to_dict includes angle/end coordinates/anchors and linked shape ids (or None)."""
        from_shape = make_linked_shape(1, x=0, y=0)
        to_shape = make_linked_shape(2, x=100, y=0)
        arrow = ArrowShape(0, 0, from_shape=from_shape, to_shape=to_shape)
        result = arrow.to_dict()
        self.assertEqual(result["from_shape_id"], 1)
        self.assertEqual(result["to_shape_id"], 2)
        self.assertEqual(result["from_anchor"], "right")
        self.assertEqual(result["to_anchor"], "left")
        self.assertIn("angle", result)
        self.assertIn("end_x", result)
        self.assertIn("end_y", result)

    def test_to_dict_uses_none_for_unlinked_shape_ids(self):
        """Verify to_dict reports None for from_shape_id/to_shape_id when unlinked."""
        arrow = ArrowShape(0, 0)
        result = arrow.to_dict()
        self.assertIsNone(result["from_shape_id"])
        self.assertIsNone(result["to_shape_id"])

    def test_load_properties_sets_geometry_and_pending_shape_ids(self):
        """Verify load_properties restores geometry fields and stashes shape ids for later resolution."""
        arrow = ArrowShape(0, 0)
        arrow.load_properties({
            "angle": 45, "end_x": 30, "end_y": 40,
            "from_anchor": "left", "to_anchor": "right",
            "from_shape_id": 11, "to_shape_id": 22
        })
        self.assertEqual(arrow.angle, 45)
        self.assertEqual((arrow.end_x, arrow.end_y), (30, 40))
        self.assertEqual(arrow.from_anchor, "left")
        self.assertEqual(arrow.to_anchor, "right")
        self.assertEqual(arrow._from_shape_id, 11)
        self.assertEqual(arrow._to_shape_id, 22)

    def test_resolve_shape_references_links_matching_shapes(self):
        """Verify resolve_shape_references finds and assigns from_shape/to_shape by id."""
        arrow = ArrowShape(0, 0)
        arrow.load_properties({"from_shape_id": 1, "to_shape_id": 2})
        shape1 = make_linked_shape(1, x=0, y=0)
        shape2 = make_linked_shape(2, x=50, y=50)
        arrow.resolve_shape_references([shape1, shape2])
        self.assertEqual(arrow.from_shape, shape1)
        self.assertEqual(arrow.to_shape, shape2)

    def test_resolve_shape_references_leaves_shapes_unset_when_ids_missing(self):
        """Verify resolve_shape_references is a no-op when no pending ids were loaded."""
        arrow = ArrowShape(0, 0)
        shape1 = make_linked_shape(1, x=0, y=0)
        arrow.resolve_shape_references([shape1])
        self.assertIsNone(arrow.from_shape)
        self.assertIsNone(arrow.to_shape)

    def test_resolve_shape_references_no_match_leaves_from_shape_none(self):
        """Verify resolve_shape_references leaves from_shape as None if the id isn't found."""
        arrow = ArrowShape(0, 0)
        arrow.load_properties({"from_shape_id": 99, "to_shape_id": None})
        shape1 = make_linked_shape(1, x=0, y=0)
        arrow.resolve_shape_references([shape1])
        self.assertIsNone(arrow.from_shape)


if __name__ == "__main__":
    unittest.main()
