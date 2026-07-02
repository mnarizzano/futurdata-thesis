"""
Unit tests for AppController delete and clear behaviours.

Covers:
  - Delete button (#45): deleting a component must also remove any
    connections/arrows attached to it, even when it is connected to
    another component.
  - Clear button (#7): clearing the canvas must reset the command
    history back to the beginning, even if there are no visible
    components on the canvas.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_app_controller -v
"""

import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.controllers.app_controller import AppController
from src.main.models import ActionCircle, ArrowShape, ComponentBox, Connection


def make_controller():
    """Create an AppController with a mocked database and view (no Tk needed)."""
    with patch("src.main.controllers.app_controller.get_database") as mock_get_db:
        mock_get_db.return_value = MagicMock()
        controller = AppController()
    controller.view = MagicMock()
    return controller


class DeleteShapeTests(unittest.TestCase):
    """Delete button #45: deleting a component connected to another one."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram

    def _add_component(self, x=100, y=100):
        shape = ComponentBox(x, y)
        self.diagram.add_shape(shape)
        return shape

    def test_delete_selected_removes_shape(self):
        shape = self._add_component()
        self.diagram.select_shape(shape)

        self.controller.delete_selected()

        self.assertNotIn(shape, self.diagram.shapes)
        self.assertNotIn(shape, self.diagram.selected_shapes)

    def test_delete_selected_with_no_selection_keeps_shapes(self):
        shape = self._add_component()

        self.controller.delete_selected()

        self.assertIn(shape, self.diagram.shapes)
        self.controller.view.set_status.assert_called_with("No shapes selected")

    def test_delete_connected_component_removes_its_connections(self):
        # Two components joined by a connection: deleting one must
        # remove the connection as well.
        comp_a = self._add_component(100, 100)
        comp_b = self._add_component(300, 100)
        connection = Connection(comp_a, comp_b)
        self.diagram.add_connection(connection)

        self.diagram.select_shape(comp_a)
        self.controller.delete_selected()

        self.assertNotIn(comp_a, self.diagram.shapes)
        self.assertIn(comp_b, self.diagram.shapes)
        self.assertEqual(self.diagram.connections, [])

    def test_delete_connected_component_removes_attached_arrows(self):
        comp_a = self._add_component(100, 100)
        comp_b = self._add_component(300, 100)
        arrow = ArrowShape(0, 0, comp_a, comp_b)
        arrow.update_from_shapes()
        self.diagram.add_shape(arrow)

        self.diagram.select_shape(comp_a)
        self.controller.delete_selected()

        self.assertNotIn(comp_a, self.diagram.shapes)
        self.assertNotIn(arrow, self.diagram.shapes)
        self.assertIn(comp_b, self.diagram.shapes)

    def test_context_menu_delete_removes_shape_and_arrows(self):
        comp_a = self._add_component(100, 100)
        comp_b = self._add_component(300, 100)
        arrow = ArrowShape(0, 0, comp_a, comp_b)
        arrow.update_from_shapes()
        self.diagram.add_shape(arrow)

        self.controller._delete_shape(comp_a)

        self.assertNotIn(comp_a, self.diagram.shapes)
        self.assertNotIn(arrow, self.diagram.shapes)
        self.assertIn(comp_b, self.diagram.shapes)

    def test_delete_multiple_selected_shapes(self):
        comp_a = self._add_component(100, 100)
        comp_b = self._add_component(300, 100)
        comp_c = self._add_component(500, 100)
        self.diagram.add_connection(Connection(comp_a, comp_b))

        self.diagram.select_shape(comp_a)
        self.diagram.select_shape(comp_b, multi_select=True)
        self.controller.delete_selected()

        self.assertEqual(self.diagram.shapes, [comp_c])
        self.assertEqual(self.diagram.connections, [])

    def test_delete_component_with_db_id_deletes_db_row(self):
        shape = self._add_component()
        shape.properties["db_id"] = 42

        self.diagram.select_shape(shape)
        self.controller.delete_selected()

        self.controller.db.delete_component.assert_called_once_with(42)
        self.assertNotIn(shape, self.diagram.shapes)

    def test_delete_step_with_db_id_deletes_db_step(self):
        step = ActionCircle(100, 100)
        step.db_step_id = 7
        self.diagram.add_shape(step)

        self.diagram.select_shape(step)
        self.controller.delete_selected()

        self.controller.db.delete_step.assert_called_once_with(7)
        self.assertNotIn(step, self.diagram.shapes)

    def test_delete_aborts_when_db_rejects_delete(self):
        # If the DB refuses (integrity error), the shape must stay on canvas.
        shape = self._add_component()
        shape.properties["db_id"] = 42
        self.controller.db.delete_component.side_effect = sqlite3.IntegrityError

        self.diagram.select_shape(shape)
        self.controller.delete_selected()

        self.assertIn(shape, self.diagram.shapes)
        self.controller.view.set_status.assert_called_with(
            "Cannot delete in DB due to existing references."
        )

    def test_undo_after_delete_restores_shape_and_connections(self):
        comp_a = self._add_component(100, 100)
        comp_b = self._add_component(300, 100)
        connection = Connection(comp_a, comp_b)
        self.diagram.add_connection(connection)

        self.diagram.select_shape(comp_a)
        self.controller.delete_selected()
        self.controller.undo()

        self.assertIn(comp_a, self.diagram.shapes)
        self.assertIn(connection, self.diagram.connections)

    def test_delete_selected_exits_arrow_mode(self):
        shape = self._add_component()
        self.diagram.select_shape(shape)
        self.controller.arrow_mode = True
        self.controller.connecting_from = shape

        self.controller.delete_selected()

        self.assertFalse(self.controller.arrow_mode)
        self.assertFalse(self.controller.connect_mode)
        self.assertIsNone(self.controller.connecting_from)


class ClearCanvasTests(unittest.TestCase):
    """Clear button #7: reset command history even with an empty canvas."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram

    def _add_and_delete_shape(self):
        """Leave the canvas empty but the command history populated."""
        shape = ComponentBox(100, 100)
        self.diagram.add_shape(shape)
        self.diagram.select_shape(shape)
        self.controller.delete_selected()

    def test_clear_empty_canvas_resets_history(self):
        self._add_and_delete_shape()
        self.assertEqual(self.diagram.shapes, [])
        self.assertTrue(self.controller.can_undo())

        self.controller.clear_canvas()

        self.assertFalse(self.controller.can_undo())
        self.assertFalse(self.controller.can_redo())
        self.assertEqual(self.controller.command_history.history, [])
        self.controller.view.set_status.assert_called_with("Canvas is already empty")

    def test_clear_empty_canvas_does_not_ask_confirmation(self):
        with patch("tkinter.messagebox.askyesno") as mock_ask:
            self.controller.clear_canvas()
        mock_ask.assert_not_called()

    def test_clear_empty_canvas_discards_redo_history(self):
        self._add_and_delete_shape()
        self.controller.undo()  # canvas has the shape again
        self.diagram.select_shape(self.diagram.shapes[0])
        self.controller.delete_selected()  # canvas empty, redo stack rewritten
        self.assertTrue(self.controller.can_undo())

        self.controller.clear_canvas()

        self.assertFalse(self.controller.can_undo())
        self.assertFalse(self.controller.can_redo())

    def test_clear_canvas_with_shapes_confirmed_removes_everything(self):
        self.diagram.add_shape(ComponentBox(100, 100))
        self.diagram.add_shape(ActionCircle(300, 100))

        with patch("tkinter.messagebox.askyesno", return_value=True):
            self.controller.clear_canvas()

        self.assertEqual(self.diagram.shapes, [])
        self.assertEqual(self.diagram.connections, [])
        self.assertFalse(self.controller.can_undo())
        self.controller.view.set_status.assert_called_with("Canvas cleared")

    def test_clear_canvas_cancelled_keeps_shapes_and_history(self):
        shape = ComponentBox(100, 100)
        command = MagicMock()
        self.controller.command_history.execute(command)
        self.diagram.add_shape(shape)

        with patch("tkinter.messagebox.askyesno", return_value=False):
            self.controller.clear_canvas()

        self.assertIn(shape, self.diagram.shapes)
        self.assertTrue(self.controller.can_undo())

    def test_undo_after_clear_reports_nothing_to_undo(self):
        self._add_and_delete_shape()
        self.controller.clear_canvas()

        self.controller.undo()

        self.controller.view.set_status.assert_called_with("Nothing to undo")


if __name__ == "__main__":
    unittest.main()
