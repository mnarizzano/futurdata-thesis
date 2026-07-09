"""
Unit tests for DiagramCanvas view behaviors.

Covers:
  - Canvas initial configurations and geometric scaling.
  - Automatic expansion and edge scrolling during drag operations.
  - Focus tracking (scrolling to target shapes).
  - Shape and connection rendering calls.
  - Zoom transformations and state consistency.

Run from the project root:
    python3 -m unittest src.tests.test_canvas_view -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from src.main.views.canvas_view import DiagramCanvas
from src.main.models import ActionCircle, ArrowShape, ComponentBox, Connection, DiamondStep


class CanvasViewTests(unittest.TestCase):

    def setUp(self):
        self.mock_parent = MagicMock()
        
        patcher_config = patch.object(tk.Canvas, 'config')
        patcher_create_oval = patch.object(tk.Canvas, 'create_oval')
        patcher_create_poly = patch.object(tk.Canvas, 'create_polygon')
        patcher_create_rect = patch.object(tk.Canvas, 'create_rectangle')
        patcher_create_line = patch.object(tk.Canvas, 'create_line')
        patcher_create_text = patch.object(tk.Canvas, 'create_text')
        patcher_delete = patch.object(tk.Canvas, 'delete')
        patcher_scale = patch.object(tk.Canvas, 'scale')

        self.mock_config = patcher_config.start()
        self.mock_create_oval = patcher_create_oval.start()
        self.mock_create_poly = patcher_create_poly.start()
        self.mock_create_rect = patcher_create_rect.start()
        self.mock_create_line = patcher_create_line.start()
        self.mock_create_text = patcher_create_text.start()
        self.mock_delete = patcher_delete.start()
        self.mock_scale = patcher_scale.start()

        self.addCleanup(patcher_config.stop)
        self.addCleanup(patcher_create_oval.stop)
        self.addCleanup(patcher_create_poly.stop)
        self.addCleanup(patcher_create_rect.stop)
        self.addCleanup(patcher_create_line.stop)
        self.addCleanup(patcher_create_text.stop)
        self.addCleanup(patcher_delete.stop)
        self.addCleanup(patcher_scale.stop)

        # Initialize the canvas
        self.canvas = DiagramCanvas(self.mock_parent)

        # Reset the counters to ignore the initial grid lines
        self.mock_create_line.reset_mock()
        self.mock_create_text.reset_mock()

    

    def test_init_sets_default_dimensions_and_grid(self):
        """Verifies that the canvas initializes with correct default dimensions and grid visibility settings."""
        self.assertEqual(self.canvas.canvas_width, DiagramCanvas.MIN_CANVAS_WIDTH)
        self.assertEqual(self.canvas.canvas_height, DiagramCanvas.MIN_CANVAS_HEIGHT)
        self.assertTrue(self.canvas.show_grid)

    def test_draw_grid_creates_lines_when_enabled(self):
        """Checks that drawing the grid removes old grid 
        elements and recreates lines when grid is enabled."""
        self.canvas.show_grid = True
        self.mock_create_line.reset_mock()
        self.canvas.draw_grid()
        
        self.mock_delete.assert_called_with("grid")
        self.assertTrue(self.mock_create_line.called)

    def test_draw_grid_does_nothing_if_disabled(self):
        """Confirms that calling draw_grid does not 
        perform any action if the grid feature is turned off."""
        self.canvas.show_grid = False
        self.mock_delete.reset_mock()
        
        self.canvas.draw_grid()
        self.mock_delete.assert_not_called()

    def test_toggle_grid_switches_state(self):
        """Tests that the toggle_grid function 
        correctly flips the grid visibility boolean state."""
        initial_state = self.canvas.show_grid
        self.canvas.toggle_grid()
        self.assertNotEqual(self.canvas.show_grid, initial_state)

   

    def test_expand_canvas_if_needed_within_bounds_returns_false(self):
        """Verifies that the canvas does not expand when 
        requested coordinates are well within current dimensions."""
        expanded = self.canvas.expand_canvas_if_needed(500, 500)
        self.assertFalse(expanded)

    def test_expand_canvas_if_needed_near_edge_expands_and_returns_true(self):
        """Confirms that the canvas expands and returns true 
        when drawing reaches the proximity of the current bounds."""
        near_edge_x = self.canvas.canvas_width - 50
        expanded = self.canvas.expand_canvas_if_needed(near_edge_x, 500)
        
        self.assertTrue(expanded)
        self.assertEqual(self.canvas.canvas_width, int(near_edge_x + self.canvas.EXPANSION_MARGIN))

    def test_auto_scroll_triggers_when_mouse_near_viewport_edges(self):
        """Tests that auto-scrolling is triggered when 
        the mouse input is within the threshold of the viewport edges."""
        self.canvas.winfo_width = MagicMock(return_value=800)
        self.canvas.winfo_height = MagicMock(return_value=600)
        self.canvas.xview_scroll = MagicMock()
        self.canvas.yview_scroll = MagicMock()

        scrolled = self.canvas.auto_scroll(780, 580)
        self.assertTrue(scrolled)
        self.canvas.xview_scroll.assert_called_with(1, "units")
        self.canvas.yview_scroll.assert_called_with(1, "units")

    @patch.object(DiagramCanvas, 'after')
    def test_scroll_to_shape_schedules_if_not_rendered(self, mock_after):
        """Ensures that if a shape is requested to be in view before the canvas is ready, 
        the scroll action is deferred using 'after'."""
        shape = MagicMock(spec=ComponentBox)
        shape.x, shape.y = 500, 500
        self.canvas.winfo_width = MagicMock(return_value=0)
        
        self.canvas.scroll_to_shape(shape)
        mock_after.assert_called_once()

    def test_scroll_to_shape_calculates_fractions_and_moves_viewport(self):
        """Verifies that scrolling to a shape correctly calculates 
        viewport percentages and triggers the canvas move commands."""
        shape = MagicMock(spec=ComponentBox)
        shape.x, shape.y = 1000, 1000
        self.canvas.winfo_width = MagicMock(return_value=500)
        self.canvas.winfo_height = MagicMock(return_value=500)
        self.canvas.xview = MagicMock(return_value=(0.0, 0.25))
        self.canvas.yview = MagicMock(return_value=(0.0, 0.25))
        self.canvas.xview_moveto = MagicMock()
        self.canvas.yview_moveto = MagicMock()

        self.canvas.scroll_to_shape(shape)
        self.canvas.xview_moveto.assert_called()
        self.canvas.yview_moveto.assert_called()

    def test_update_scroll_region_from_shapes_with_empty_list(self):
        """Checks that updating the scroll region with no 
        shapes resets the canvas dimensions to the default minimum."""
        self.canvas.update_scroll_region_from_shapes([])
        self.assertEqual(self.canvas.canvas_width, self.canvas.MIN_CANVAS_WIDTH)

    def test_update_scroll_region_from_shapes_recalculates_dimensions(self):
        """Validates that the scroll region successfully 
        expands based on the coordinates of the furthest shape."""
        shape_far = MagicMock()
        shape_far.x = 2500
        shape_far.y = 2500
        
        self.canvas.update_scroll_region_from_shapes([shape_far])
        expected_width = 2500 + 200 + self.canvas.EXPANSION_MARGIN
        self.assertEqual(self.canvas.canvas_width, expected_width)



    def test_draw_action_circle(self):
        """Ensures that drawing an ActionCircle correctly 
        invokes the creation of both an oval and its label text."""
        shape = MagicMock(spec=ActionCircle)
        shape.x, shape.y, shape.text = 100, 100, "Action"
        shape.selected, shape.shape_id, shape.text_id = False, None, None
        shape.get_bounds.return_value = (50, 50, 150, 150)
        
        self.canvas.draw_shape(shape)
        self.mock_create_oval.assert_called_once()
        self.mock_create_text.assert_called_once()

    def test_draw_diamond_step(self):
        """Verifies that drawing a DiamondStep uses the 
        polygon creation method and adds the associated text."""
        shape = MagicMock(spec=DiamondStep)
        shape.x, shape.y, shape.text = 100, 100, "Decision"
        shape.SIZE = 80
        shape.selected, shape.shape_id, shape.text_id = False, None, None
        
        self.canvas.draw_shape(shape)
        self.mock_create_poly.assert_called_once()
        self.mock_create_text.assert_called_once()

    def test_draw_component_box_with_custom_hex_color(self):
        """Tests that a ComponentBox is rendered 
        with the specified custom hex color property."""
        shape = MagicMock(spec=ComponentBox)
        shape.x, shape.y, shape.text = 100, 100, "Component"
        shape.selected, shape.shape_id, shape.text_id = False, None, None
        shape.get_bounds.return_value = (50, 50, 150, 150)
        shape.properties = {'hex_code': '#ff00ff'}

        self.canvas.draw_shape(shape)
        self.mock_create_rect.assert_called_once_with(
            50, 50, 150, 150, fill='#ff00ff', outline=self.canvas.BORDER_COLOR, width=2, tags="shape"
        )

    def test_draw_arrow_shape(self):
        """Verifies that drawing an ArrowShape 
        correctly triggers the line creation on the canvas."""
        shape = MagicMock(spec=ArrowShape)
        shape.x, shape.y, shape.end_x, shape.end_y = 100, 100, 200, 200
        shape.selected, shape.shape_id, shape.text_id = False, None, None
        shape.from_shape, shape.to_shape = MagicMock(), MagicMock()
        
        self.canvas.draw_shape(shape)
        self.assertTrue(self.mock_create_line.called)

    def test_draw_connection_dashed_vs_solid(self):
        """Confirms that connection styling (specifically dashed patterns) 
        is correctly applied via canvas line parameters."""
        conn = MagicMock(spec=Connection)
        conn.connection_type = "dashed"
        conn.arrow_id = None
        conn.get_endpoints.return_value = ((10, 10), (100, 100))
        
        self.canvas.draw_connection(conn)
        self.mock_create_line.assert_called_once_with(
            10, 10, 100, 100, fill=self.canvas.BORDER_COLOR, width=2,
            arrow=tk.LAST, arrowshape=(10, 12, 5), dash=(5, 5), tags="connection"
        )



    def test_draw_alignment_guides(self):
        """Tests that alignment guides are drawn for all 
        provided vertical and horizontal coordinates."""
        guides = {'vertical': [100, 200], 'horizontal': [150]}
        self.canvas.draw_alignment_guides(guides)
        self.assertEqual(self.mock_create_line.call_count, 3)

    def test_clear_alignment_guides(self):
        """Verifies that the clear_alignment_guides function 
        specifically removes items tagged as 'guide'."""
        self.canvas.clear_alignment_guides()
        self.mock_delete.assert_called_with("guide")

    def test_clear_canvas_removes_essential_tags(self):
        """Confirms that clear_canvas thoroughly removes all 
        categorized diagram elements (shapes, connections, guides)."""
        self.canvas.clear_canvas()
        self.mock_delete.assert_any_call("shape")
        self.mock_delete.assert_any_call("shape_text")
        self.mock_delete.assert_any_call("connection")
        self.mock_delete.assert_any_call("guide")


    def test_redraw_all_renders_entire_diagram_and_applies_zoom_factor(self):
        """Verifies that the entire canvas is cleared, all shapes/connections 
        are re-rendered, and the current zoom scaling is applied."""
        diagram = MagicMock()
        shape = MagicMock(spec=ComponentBox)
        shape.x, shape.y, shape.text = 50, 50, "Box"
        shape.shape_id, shape.text_id, shape.selected = None, None, False
        shape.get_bounds.return_value = (0, 0, 10, 10)
        shape.properties = {}
        
        conn = MagicMock(spec=Connection)
        conn.arrow_id = None
        conn.connection_type = "solid"
        conn.get_endpoints.return_value = ((0, 0), (10, 10))
        
        diagram.shapes = [shape]
        diagram.connections = [conn]
        
        self.canvas.zoom_factor = 1.5
        self.canvas.redraw_all(diagram)
        
        self.mock_delete.assert_any_call("all")
        self.mock_create_rect.assert_called_once()
        self.assertTrue(self.mock_create_line.called)
        self.mock_scale.assert_called_once_with("all", 0, 0, 1.5, 1.5)

    def test_move_items_translates_ids_without_redrawing(self):
        """Checks that moving items uses the canvas translate command 
        on specific object IDs rather than a full redraw."""
        shape = MagicMock(spec=ComponentBox)
        shape.shape_id, shape.text_id = 101, 202
        self.canvas.move = MagicMock()
        
        self.canvas.move_items(shape, 15.0, -10.0)
        self.canvas.move.assert_any_call(101, 15.0, -10.0)
        self.canvas.move.assert_any_call(202, 15.0, -10.0)

    def test_update_connections_for_shapes_filters_correctly(self):
        """Tests that the connection updater correctly identifies and 
        processes connections associated with the provided shapes."""
        diagram = MagicMock()
        shape_a = MagicMock()
        shape_b = MagicMock()
        
        conn_1 = MagicMock(spec=Connection)
        conn_1.from_shape, conn_1.to_shape, conn_1.arrow_id = shape_a, shape_b, None
        conn_1.connection_type = "solid"
        conn_1.get_endpoints.return_value = ((0, 0), (10, 10))
        
        conn_2 = MagicMock(spec=Connection)
        conn_2.from_shape, conn_2.to_shape = MagicMock(), MagicMock()
        
        diagram.connections = [conn_1, conn_2]
        
        self.canvas.update_connections_for_shapes([shape_a], diagram)
        self.assertTrue(self.mock_create_line.called)



    def test_zoom_in_increases_factor(self):
        """Validates that the zoom factor is correctly multiplied by the scaling increment."""
        initial_zoom = self.canvas.zoom_factor
        self.canvas.zoom_in()
        self.assertAlmostEqual(self.canvas.zoom_factor, initial_zoom * 1.1)

    def test_zoom_out_decreases_factor(self):
        """Validates that the zoom factor is correctly multiplied by the scaling decrement."""
        initial_zoom = self.canvas.zoom_factor
        self.canvas.zoom_out()
        self.assertAlmostEqual(self.canvas.zoom_factor, initial_zoom * 0.9)

    def test_zoom_limits_prevent_excessive_scaling(self):
        """Confirms that the zoom logic enforces upper bounds and 
        prevents redundant scaling commands if the limit is reached."""
        self.canvas.zoom_factor = 2.9
        self.canvas.zoom_in()
        self.assertEqual(self.canvas.zoom_factor, 2.9)
        self.mock_scale.assert_not_called()

    def test_reset_zoom_restores_one_dot_zero_scale(self):
        """Ensures that resetting the zoom restores the factor to 1.0 and 
        applies the inverse scaling to the canvas."""
        self.canvas.zoom_factor = 2.0
        self.canvas.reset_zoom()
        
        self.assertEqual(self.canvas.zoom_factor, 1.0)
        self.mock_scale.assert_called_with("all", 0, 0, 0.5, 0.5)


if __name__ == "__main__":
    unittest.main()