"""
Unit tests for src/main/utils/commands.py

Covers CommandHistory (undo/redo stack) and every Command subclass, using the
real dependency-free models (Diagram, shapes, Connection). No DB or Tk needed.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_commands -v
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models import ActionCircle, ArrowShape, ComponentBox, Connection, Diagram
from src.main.utils.commands import (
    Command,
    CommandHistory,
    AddShapeCommand,
    RemoveShapeCommand,
    MoveShapeCommand,
    AddConnectionCommand,
    RemoveConnectionCommand,
    EditShapePropertiesCommand,
    MultiCommand,
)


class RecordingCommand(Command):
    """Simple Command that records execute/undo calls for history tests."""

    def __init__(self, description="Recording"):
        self.executes = 0
        self.undos = 0
        self.description = description

    def execute(self):
        self.executes += 1

    def undo(self):
        self.undos += 1

    def get_description(self) -> str:
        return self.description


class CommandBaseTests(unittest.TestCase):
    def test_execute_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            Command().execute()

    def test_undo_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            Command().undo()

    def test_default_description(self):
        self.assertEqual(Command().get_description(), "Command")


class CommandHistoryTests(unittest.TestCase):
    def setUp(self):
        self.history = CommandHistory()

    def test_execute_runs_command_and_records_it(self):
        cmd = RecordingCommand()
        self.history.execute(cmd)
        self.assertEqual(cmd.executes, 1)
        self.assertEqual(self.history.history, [cmd])
        self.assertEqual(self.history.current_index, 0)

    def test_can_undo_and_can_redo_flags(self):
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        self.history.execute(RecordingCommand())
        self.assertTrue(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_undo_calls_command_undo(self):
        cmd = RecordingCommand()
        self.history.execute(cmd)
        self.assertTrue(self.history.undo())
        self.assertEqual(cmd.undos, 1)
        self.assertTrue(self.history.can_redo())

    def test_undo_on_empty_returns_false(self):
        self.assertFalse(self.history.undo())

    def test_redo_reexecutes_command(self):
        cmd = RecordingCommand()
        self.history.execute(cmd)
        self.history.undo()
        self.assertTrue(self.history.redo())
        self.assertEqual(cmd.executes, 2)

    def test_redo_when_nothing_to_redo_returns_false(self):
        self.history.execute(RecordingCommand())
        self.assertFalse(self.history.redo())

    def test_new_command_truncates_redo_branch(self):
        first = RecordingCommand("first")
        second = RecordingCommand("second")
        self.history.execute(first)
        self.history.undo()          # first is now redoable
        self.history.execute(second)  # should drop the redo branch
        self.assertEqual(self.history.history, [second])
        self.assertFalse(self.history.can_redo())

    def test_max_history_trims_oldest(self):
        history = CommandHistory(max_history=2)
        a, b, c = RecordingCommand("a"), RecordingCommand("b"), RecordingCommand("c")
        history.execute(a)
        history.execute(b)
        history.execute(c)
        self.assertEqual(history.history, [b, c])
        self.assertEqual(history.current_index, 1)

    def test_clear_resets_history(self):
        self.history.execute(RecordingCommand())
        self.history.clear()
        self.assertEqual(self.history.history, [])
        self.assertEqual(self.history.current_index, -1)
        self.assertFalse(self.history.can_undo())

    def test_undo_redo_descriptions(self):
        self.history.execute(RecordingCommand("do X"))
        self.assertEqual(self.history.get_undo_description(), "do X")
        self.assertEqual(self.history.get_redo_description(), "")
        self.history.undo()
        self.assertEqual(self.history.get_undo_description(), "")
        self.assertEqual(self.history.get_redo_description(), "do X")


class AddShapeCommandTests(unittest.TestCase):
    def setUp(self):
        self.diagram = Diagram()
        self.shape = ComponentBox(0, 0)

    def test_execute_adds_shape(self):
        AddShapeCommand(self.diagram, self.shape).execute()
        self.assertIn(self.shape, self.diagram.shapes)

    def test_undo_removes_shape(self):
        cmd = AddShapeCommand(self.diagram, self.shape)
        cmd.execute()
        cmd.undo()
        self.assertNotIn(self.shape, self.diagram.shapes)

    def test_description(self):
        cmd = AddShapeCommand(self.diagram, self.shape)
        self.assertEqual(cmd.get_description(), "Add component")


class RemoveShapeCommandTests(unittest.TestCase):
    def setUp(self):
        self.diagram = Diagram()
        self.comp_a = ComponentBox(0, 0)
        self.comp_b = ComponentBox(200, 0)
        self.diagram.add_shape(self.comp_a)
        self.diagram.add_shape(self.comp_b)
        self.connection = Connection(self.comp_a, self.comp_b)
        self.diagram.add_connection(self.connection)

    def test_execute_removes_shape_and_its_connections(self):
        RemoveShapeCommand(self.diagram, self.comp_a).execute()
        self.assertNotIn(self.comp_a, self.diagram.shapes)
        self.assertEqual(self.diagram.connections, [])

    def test_undo_restores_shape_and_connections(self):
        cmd = RemoveShapeCommand(self.diagram, self.comp_a)
        cmd.execute()
        cmd.undo()
        self.assertIn(self.comp_a, self.diagram.shapes)
        self.assertIn(self.connection, self.diagram.connections)

    def test_description(self):
        cmd = RemoveShapeCommand(self.diagram, self.comp_a)
        self.assertEqual(cmd.get_description(), "Remove component")


class MoveShapeCommandTests(unittest.TestCase):
    def test_execute_moves_single_shape(self):
        shape = ComponentBox(100, 100)
        MoveShapeCommand(shape, 50, -20).execute()
        self.assertEqual((shape.x, shape.y), (150, 80))

    def test_undo_reverses_move(self):
        shape = ComponentBox(100, 100)
        cmd = MoveShapeCommand(shape, 50, -20)
        cmd.execute()
        cmd.undo()
        self.assertEqual((shape.x, shape.y), (100, 100))

    def test_wraps_single_shape_in_list(self):
        shape = ComponentBox(0, 0)
        cmd = MoveShapeCommand(shape, 1, 1)
        self.assertEqual(cmd.shapes, [shape])

    def test_moves_multiple_shapes(self):
        a, b = ComponentBox(0, 0), ActionCircle(10, 10)
        MoveShapeCommand([a, b], 5, 5).execute()
        self.assertEqual((a.x, a.y), (5, 5))
        self.assertEqual((b.x, b.y), (15, 15))

    def test_description_single_vs_many(self):
        shape = ComponentBox(0, 0)
        self.assertEqual(MoveShapeCommand(shape, 1, 1).get_description(), "Move component")
        many = MoveShapeCommand([shape, ActionCircle(0, 0)], 1, 1)
        self.assertEqual(many.get_description(), "Move 2 shapes")


class ConnectionCommandTests(unittest.TestCase):
    def setUp(self):
        self.diagram = Diagram()
        self.comp_a = ComponentBox(0, 0)
        self.comp_b = ComponentBox(200, 0)
        self.diagram.add_shape(self.comp_a)
        self.diagram.add_shape(self.comp_b)
        self.connection = Connection(self.comp_a, self.comp_b)

    def test_add_connection_execute_and_undo(self):
        cmd = AddConnectionCommand(self.diagram, self.connection)
        cmd.execute()
        self.assertIn(self.connection, self.diagram.connections)
        cmd.undo()
        self.assertNotIn(self.connection, self.diagram.connections)

    def test_add_connection_description(self):
        cmd = AddConnectionCommand(self.diagram, self.connection)
        self.assertEqual(cmd.get_description(), "Add connection")

    def test_remove_connection_execute_and_undo(self):
        self.diagram.add_connection(self.connection)
        cmd = RemoveConnectionCommand(self.diagram, self.connection)
        cmd.execute()
        self.assertNotIn(self.connection, self.diagram.connections)
        cmd.undo()
        self.assertIn(self.connection, self.diagram.connections)

    def test_remove_connection_description(self):
        cmd = RemoveConnectionCommand(self.diagram, self.connection)
        self.assertEqual(cmd.get_description(), "Remove connection")


class EditShapePropertiesCommandTests(unittest.TestCase):
    def test_execute_updates_properties_dict(self):
        shape = ComponentBox(0, 0)
        old = {"name": shape.properties["name"]}
        new = {"name": "Gear"}
        cmd = EditShapePropertiesCommand(shape, old, new)
        cmd.execute()
        self.assertEqual(shape.properties["name"], "Gear")

    def test_undo_restores_old_properties(self):
        shape = ComponentBox(0, 0)
        shape.properties["name"] = "Original"
        cmd = EditShapePropertiesCommand(shape, {"name": "Original"}, {"name": "Changed"})
        cmd.execute()
        cmd.undo()
        self.assertEqual(shape.properties["name"], "Original")

    def test_falls_back_to_setattr_for_plain_attributes(self):
        # ActionCircle stores step_description as an attribute, not in a properties dict.
        step = ActionCircle(0, 0)
        cmd = EditShapePropertiesCommand(
            step, {"step_description": ""}, {"step_description": "Unscrew"}
        )
        cmd.execute()
        self.assertEqual(step.step_description, "Unscrew")

    def test_description(self):
        shape = ComponentBox(0, 0)
        cmd = EditShapePropertiesCommand(shape, {}, {})
        self.assertEqual(cmd.get_description(), "Edit component properties")


class MultiCommandTests(unittest.TestCase):
    def test_execute_runs_all_in_order(self):
        a, b = RecordingCommand(), RecordingCommand()
        MultiCommand([a, b]).execute()
        self.assertEqual((a.executes, b.executes), (1, 1))

    def test_undo_runs_all_in_reverse(self):
        order = []
        a, b = RecordingCommand("a"), RecordingCommand("b")
        a.undo = lambda: order.append("a")
        b.undo = lambda: order.append("b")
        MultiCommand([a, b]).undo()
        self.assertEqual(order, ["b", "a"])

    def test_default_and_custom_description(self):
        self.assertEqual(MultiCommand([]).get_description(), "Multiple actions")
        self.assertEqual(MultiCommand([], "Paste").get_description(), "Paste")


if __name__ == "__main__":
    unittest.main()
