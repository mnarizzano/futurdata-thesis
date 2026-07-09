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
from src.main.models import ActionCircle, ArrowShape, ComponentBox, Connection, DiamondStep


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


class AddShapeTests(unittest.TestCase):
    """add_shape / _create_shape_instance / _get_next_shape_position."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram
        # Simulate a canvas that has not been rendered yet so the
        # position helper uses its deterministic default branch.
        self.controller.view.canvas.winfo_width.return_value = 0
        self.controller.view.canvas.winfo_height.return_value = 0

    def test_add_action_shape(self):
        self.controller.add_shape("action")
        self.assertEqual(len(self.diagram.shapes), 1)
        self.assertIsInstance(self.diagram.shapes[0], ActionCircle)

    def test_add_diamond_shape(self):
        self.controller.add_shape("diamond")
        self.assertIsInstance(self.diagram.shapes[0], DiamondStep)

    def test_add_root_component_sets_node_type_and_name(self):
        self.controller.add_shape("component_root")
        shape = self.diagram.shapes[0]
        self.assertIsInstance(shape, ComponentBox)
        self.assertEqual(shape.properties["node_type"], "Root")
        self.assertEqual(shape.text, "Root Component")

    def test_add_leaf_component_sets_node_type(self):
        self.controller.add_shape("component_leaf")
        self.assertEqual(self.diagram.shapes[0].properties["node_type"], "Leaf")

    def test_add_composite_component_maps_to_intermediate(self):
        self.controller.add_shape("component_composite")
        self.assertEqual(self.diagram.shapes[0].properties["node_type"], "Intermediate")

    def test_add_product_is_alias_for_root_component(self):
        self.controller.add_shape("product")
        self.assertEqual(self.diagram.shapes[0].properties["node_type"], "Root")

    def test_new_shape_is_selected(self):
        self.controller.add_shape("action")
        self.assertEqual(self.diagram.selected_shapes, [self.diagram.shapes[0]])

    def test_add_shape_is_undoable(self):
        self.controller.add_shape("action")
        self.assertTrue(self.controller.can_undo())
        self.controller.undo()
        self.assertEqual(self.diagram.shapes, [])

    def test_add_arrow_enters_arrow_mode_without_adding_shape(self):
        self.controller.add_shape("arrow")
        self.assertTrue(self.controller.arrow_mode)
        self.assertIsNone(self.controller.connecting_from)
        self.assertEqual(self.diagram.shapes, [])

    def test_unknown_shape_type_raises(self):
        with self.assertRaises(ValueError):
            self.controller._create_shape_instance("hexagon", 0, 0)

    def test_default_positions_are_staggered(self):
        first = self.controller._get_next_shape_position()
        self.controller.add_shape("action")
        second = self.controller._get_next_shape_position()
        self.assertNotEqual(first, second)


class SelectionTests(unittest.TestCase):
    """select_all and click-based selection state."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram

    def test_select_all_selects_every_shape(self):
        shapes = [ComponentBox(100, 100), ComponentBox(300, 100), ActionCircle(500, 100)]
        for shape in shapes:
            self.diagram.add_shape(shape)

        self.controller.select_all()

        self.assertEqual(set(self.diagram.selected_shapes), set(shapes))
        self.controller.view.set_status.assert_called_with("Selected 3 shapes")

    def test_select_all_on_empty_diagram(self):
        self.controller.select_all()
        self.assertEqual(self.diagram.selected_shapes, [])
        self.controller.view.set_status.assert_called_with("Selected 0 shapes")


class UndoRedoTests(unittest.TestCase):
    """undo / redo / can_undo / can_redo."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram
        self.controller.view.canvas.winfo_width.return_value = 0
        self.controller.view.canvas.winfo_height.return_value = 0

    def test_undo_with_empty_history(self):
        self.controller.undo()
        self.controller.view.set_status.assert_called_with("Nothing to undo")
        self.assertFalse(self.controller.can_undo())

    def test_redo_with_empty_history(self):
        self.controller.redo()
        self.controller.view.set_status.assert_called_with("Nothing to redo")
        self.assertFalse(self.controller.can_redo())

    def test_undo_then_redo_restores_shape(self):
        self.controller.add_shape("action")
        shape = self.diagram.shapes[0]

        self.controller.undo()
        self.assertEqual(self.diagram.shapes, [])
        self.assertTrue(self.controller.can_redo())

        self.controller.redo()
        self.assertEqual(self.diagram.shapes, [shape])

    def test_new_command_clears_redo_stack(self):
        self.controller.add_shape("action")
        self.controller.undo()
        self.controller.add_shape("diamond")
        self.assertFalse(self.controller.can_redo())


class ConnectModeTests(unittest.TestCase):
    """toggle_connect_mode / on_escape / _start_connection_from."""

    def setUp(self):
        self.controller = make_controller()

    def test_toggle_connect_mode_on(self):
        self.controller.toggle_connect_mode()
        self.assertTrue(self.controller.connect_mode)
        self.assertIsNone(self.controller.connecting_from)

    def test_toggle_connect_mode_off(self):
        self.controller.toggle_connect_mode()
        self.controller.toggle_connect_mode()
        self.assertFalse(self.controller.connect_mode)

    def test_start_connection_from_shape(self):
        shape = ComponentBox(100, 100)
        self.controller._start_connection_from(shape)
        self.assertTrue(self.controller.connect_mode)
        self.assertIs(self.controller.connecting_from, shape)

    def test_escape_cancels_arrow_mode(self):
        self.controller.arrow_mode = True
        self.controller.connecting_from = ComponentBox(100, 100)

        self.controller.on_escape(MagicMock())

        self.assertFalse(self.controller.arrow_mode)
        self.assertFalse(self.controller.connect_mode)
        self.assertIsNone(self.controller.connecting_from)

    def test_escape_without_active_mode_does_nothing(self):
        self.controller.on_escape(MagicMock())
        self.controller.view.set_status.assert_not_called()


class DuplicateShapeTests(unittest.TestCase):
    """_duplicate_shape for every shape family."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram

    def test_duplicate_component_copies_properties(self):
        shape = ComponentBox(100, 100)
        shape.text = "Battery"
        shape.properties["name"] = "Battery"
        shape.properties["node_type"] = "Leaf"
        self.diagram.add_shape(shape)

        self.controller._duplicate_shape(shape)

        self.assertEqual(len(self.diagram.shapes), 2)
        copy = self.diagram.shapes[1]
        self.assertEqual(copy.text, "Battery")
        self.assertEqual(copy.properties["node_type"], "Leaf")
        self.assertIsNot(copy.properties, shape.properties)
        self.assertEqual((copy.x, copy.y), (shape.x + 50, shape.y + 50))

    def test_duplicate_action_circle_copies_step_fields(self):
        shape = ActionCircle(100, 100)
        shape.step_description = "Remove screws"
        shape.image_path = "/img/step.png"
        shape.tools = "Screwdriver"
        self.diagram.add_shape(shape)

        self.controller._duplicate_shape(shape)

        copy = self.diagram.shapes[1]
        self.assertEqual(copy.step_description, "Remove screws")
        self.assertEqual(copy.image_path, "/img/step.png")
        self.assertEqual(copy.tools, "Screwdriver")

    def test_duplicate_diamond_copies_action_fields(self):
        shape = DiamondStep(100, 100)
        shape.name = "Unscrew"
        shape.tools = "Torx"
        self.diagram.add_shape(shape)

        self.controller._duplicate_shape(shape)

        copy = self.diagram.shapes[1]
        self.assertEqual(copy.name, "Unscrew")
        self.assertEqual(copy.tools, "Torx")

    def test_duplicate_is_undoable(self):
        shape = ComponentBox(100, 100)
        self.diagram.add_shape(shape)

        self.controller._duplicate_shape(shape)
        self.controller.undo()

        self.assertEqual(self.diagram.shapes, [shape])


class DbSyncTests(unittest.TestCase):
    """_ensure_*_db_id and _sync_connection_to_db against a mocked DB."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram
        self.db = self.controller.db
        self.db.create_component.return_value = 1
        self.db.get_next_step_order.return_value = 1
        self.db.create_step.return_value = 11
        self.db.create_action.return_value = 21
        self.db.add_action_to_step.return_value = {
            "link_id": 31, "action_order": 1, "already_linked": False,
        }
        self.db.add_component_to_step.return_value = {
            "link_id": 41, "already_linked": False,
        }

    def _add_root(self):
        root = ComponentBox(100, 100)
        root.properties["node_type"] = "Root"
        root.properties["name"] = "Root Component"
        self.diagram.add_shape(root)
        return root

    def test_ensure_component_reuses_existing_db_id(self):
        shape = ComponentBox(100, 100)
        shape.properties["db_id"] = 99
        self.assertEqual(self.controller._ensure_component_db_id(shape), 99)
        self.db.create_component.assert_not_called()

    def test_ensure_component_creates_root_row(self):
        root = self._add_root()
        comp_id = self.controller._ensure_component_db_id(root)
        self.assertEqual(comp_id, 1)
        self.assertEqual(root.properties["db_id"], 1)
        self.assertEqual(self.db.create_component.call_args.kwargs["node_type"], "Root")

    def test_ensure_component_child_without_root_raises(self):
        orphan = ComponentBox(100, 100)
        orphan.properties["node_type"] = "Leaf"
        self.diagram.add_shape(orphan)
        with self.assertRaises(ValueError):
            self.controller._ensure_component_db_id(orphan)

    def test_ensure_component_child_links_to_root(self):
        self._add_root()
        leaf = ComponentBox(300, 100)
        leaf.properties["node_type"] = "Leaf"
        self.diagram.add_shape(leaf)

        self.controller._ensure_component_db_id(leaf)

        # Second create_component call is the leaf, linked to the root's id.
        leaf_call = self.db.create_component.call_args_list[-1]
        self.assertEqual(leaf_call.kwargs["product_id"], 1)
        self.assertEqual(leaf_call.kwargs["node_type"], "Leaf")

    def test_ensure_action_db_id_creates_once(self):
        diamond = DiamondStep(100, 100)
        diamond.name = "Unscrew"

        first = self.controller._ensure_action_db_id(diamond)
        second = self.controller._ensure_action_db_id(diamond)

        self.assertEqual(first, 21)
        self.assertEqual(second, 21)
        self.db.create_action.assert_called_once()

    def test_component_to_circle_creates_step(self):
        root = self._add_root()
        circle = ActionCircle(300, 100)
        self.diagram.add_shape(circle)

        self.controller._sync_connection_to_db(root, circle)

        self.assertEqual(circle.db_step_id, 11)
        self.db.create_step.assert_called_once()
        self.assertEqual(self.db.create_step.call_args.kwargs["component_id"], 1)

    def test_circle_to_component_registers_step_output(self):
        root = self._add_root()
        circle = ActionCircle(300, 100)
        circle.db_step_id = 11
        self.diagram.add_shape(circle)
        leaf = ComponentBox(500, 100)
        leaf.properties["node_type"] = "Leaf"
        leaf.properties["db_id"] = 2_000_001
        self.diagram.add_shape(leaf)

        self.controller._sync_connection_to_db(circle, leaf)

        self.db.add_component_to_step.assert_called_once_with(11, 2_000_001)

    def test_circle_to_diamond_links_action_to_step(self):
        self._add_root()
        circle = ActionCircle(300, 100)
        circle.db_step_id = 11
        self.diagram.add_shape(circle)
        diamond = DiamondStep(500, 100)
        self.diagram.add_shape(diamond)

        self.controller._sync_connection_to_db(circle, diamond)

        self.db.add_action_to_step.assert_called_once_with(11, 21)
        self.assertEqual(diamond.db_step_id, 11)
        self.assertEqual(diamond.db_action_id, 21)
        self.assertEqual(diamond.db_step_action_id, 31)

    def test_diamond_to_diamond_requires_linked_first_diamond(self):
        first = DiamondStep(100, 100)
        second = DiamondStep(300, 100)
        self.diagram.add_shape(first)
        self.diagram.add_shape(second)

        self.controller._sync_connection_to_db(first, second)

        # No step could be resolved: surfaced as a status warning, no link made.
        self.db.add_action_to_step.assert_not_called()
        status = self.controller.view.set_status.call_args[0][0]
        self.assertIn("DB sync warning", status)

    def test_diamond_to_diamond_chains_actions_on_same_step(self):
        first = DiamondStep(100, 100)
        first.db_step_id = 11
        second = DiamondStep(300, 100)
        self.diagram.add_shape(first)
        self.diagram.add_shape(second)

        self.controller._sync_connection_to_db(first, second)

        self.db.add_action_to_step.assert_called_once_with(11, 21)
        self.assertEqual(second.db_step_id, 11)


class ArrowConnectionFlowTests(unittest.TestCase):
    """_handle_arrow_connection_click two-click flow."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram
        self.controller.arrow_mode = True

    def test_first_click_sets_source(self):
        shape = ComponentBox(100, 100)
        self.diagram.add_shape(shape)

        self.controller._handle_arrow_connection_click(shape)

        self.assertIs(self.controller.connecting_from, shape)
        self.assertTrue(self.controller.arrow_mode)

    def test_second_click_creates_arrow(self):
        comp_a = ComponentBox(100, 100)
        comp_b = ComponentBox(300, 100)
        comp_a.properties["db_id"] = 1
        comp_b.properties["db_id"] = 2
        self.diagram.add_shape(comp_a)
        self.diagram.add_shape(comp_b)

        self.controller._handle_arrow_connection_click(comp_a)
        self.controller._handle_arrow_connection_click(comp_b)

        arrows = [s for s in self.diagram.shapes if isinstance(s, ArrowShape)]
        self.assertEqual(len(arrows), 1)
        self.assertIs(arrows[0].from_shape, comp_a)
        self.assertIs(arrows[0].to_shape, comp_b)
        self.assertFalse(self.controller.arrow_mode)

    def test_clicking_same_shape_twice_cancels(self):
        shape = ComponentBox(100, 100)
        self.diagram.add_shape(shape)

        self.controller._handle_arrow_connection_click(shape)
        self.controller._handle_arrow_connection_click(shape)

        self.assertEqual([s for s in self.diagram.shapes if isinstance(s, ArrowShape)], [])
        self.assertFalse(self.controller.arrow_mode)
        self.assertIsNone(self.controller.connecting_from)


class DiagramLifecycleTests(unittest.TestCase):
    """new_diagram / save_diagram / check_unsaved_changes."""

    def setUp(self):
        self.controller = make_controller()
        self.diagram = self.controller.diagram

    def test_new_diagram_clears_shapes_history_and_product(self):
        self.diagram.add_shape(ComponentBox(100, 100))
        self.controller.command_history.execute(MagicMock())
        self.controller.current_product_id = 5
        self.diagram.modified = False

        self.controller.new_diagram()

        self.assertEqual(self.diagram.shapes, [])
        self.assertFalse(self.controller.can_undo())
        self.assertIsNone(self.controller.current_product_id)

    def test_new_diagram_cancelled_by_unsaved_changes(self):
        shape = ComponentBox(100, 100)
        self.diagram.add_shape(shape)
        self.diagram.modified = True
        self.controller.view.ask_save_changes.return_value = "cancel"

        self.controller.new_diagram()

        self.assertIn(shape, self.diagram.shapes)

    def test_check_unsaved_changes_clean_diagram(self):
        self.diagram.modified = False
        self.assertTrue(self.controller.check_unsaved_changes())
        self.controller.view.ask_save_changes.assert_not_called()

    def test_check_unsaved_changes_discard(self):
        self.diagram.modified = True
        self.controller.view.ask_save_changes.return_value = "discard"
        self.assertTrue(self.controller.check_unsaved_changes())

    def test_check_unsaved_changes_save_triggers_save(self):
        self.diagram.modified = True
        self.controller.view.ask_save_changes.return_value = "save"
        with patch.object(self.controller, "save_diagram", return_value=True) as mock_save:
            self.assertTrue(self.controller.check_unsaved_changes())
        mock_save.assert_called_once()

    def test_save_diagram_reports_product_name(self):
        self.controller.current_product_id = 3
        self.controller.db.get_product.return_value = {"name": "Washing Machine"}

        self.assertTrue(self.controller.save_diagram())

        status = self.controller.view.set_status.call_args[0][0]
        self.assertIn("Washing Machine", status)

    def test_save_diagram_failure_shows_error(self):
        with patch.object(self.controller, "_persist_diagram_to_db",
                          side_effect=Exception("disk full")):
            self.assertFalse(self.controller.save_diagram())
        self.controller.view.show_error.assert_called_once()


class CatalogHelperTests(unittest.TestCase):
    """add_new_color / delete_color / add_new_material / delete_material / add_new_tool."""

    def setUp(self):
        self.controller = make_controller()
        self.db = self.controller.db

    def test_add_new_color_creates_and_refreshes(self):
        self.controller.add_new_color("Teal", "#008080", 0, 128, 128)
        self.db.create_color.assert_called_once_with("Teal", "#008080", 0, 128, 128)
        self.controller.view.refresh_properties_panel.assert_called_once()

    def test_delete_color_success_refreshes_panel(self):
        self.db.delete_color.return_value = True
        self.assertTrue(self.controller.delete_color(4))
        self.controller.view.refresh_properties_panel.assert_called_once()

    def test_delete_color_in_use_raises_value_error(self):
        self.db.delete_color.side_effect = sqlite3.IntegrityError
        with self.assertRaises(ValueError):
            self.controller.delete_color(4)

    def test_add_new_material_creates_and_refreshes(self):
        self.controller.add_new_material("Steel", "Fe/C", 2)
        self.db.create_material.assert_called_once_with("Steel", "Fe/C", 2)
        self.controller.view.refresh_properties_panel.assert_called_once()

    def test_delete_material_in_use_raises_value_error(self):
        self.db.delete_material.side_effect = sqlite3.IntegrityError
        with self.assertRaises(ValueError):
            self.controller.delete_material(4)

    def test_add_new_tool_creates_and_refreshes(self):
        self.controller.add_new_tool("Torx", "Screwdriver")
        self.db.create_tool.assert_called_once_with("Torx", "Screwdriver")
        self.controller.view.refresh_properties_panel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
