"""
Unit tests for PropertiesPanel view component.

Covers:
  - Component initialization and dynamic widget building based on DB schemas.
  - Loading / showing fields specifically for ActionCircle, ComponentBox, and DiamondStep.
  - Value extraction from dynamic entry fields, textareas, and specialized comboboxes.
  - Data application from UI widgets back to the Shape model instances.
  - Integration with the Database mapping layers without launching a visible window.

Run from the project root:
    python3 -m unittest src.tests.test_properties_panel -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Path configuration to locate the source code
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from tkinter import ttk

from src.main.models import ActionCircle, ComponentBox, DiamondStep
from src.main.views.properties_panel import PropertiesPanel


class PropertiesPanelTests(unittest.TestCase):

    def setUp(self):
        """Initialize a native Tkinter environment in headless mode."""
        # Create a real but invisible root to prevent Tkinter hierarchy errors
        self.root = tk.Tk()
        self.root.withdraw()

        # Database mock to simulate dynamic table schemas
        self.mock_db = MagicMock()
        self.mock_db.get_table_columns.side_effect = self._mock_columns_schema

        # Patch the global get_database function to use our mock
        self.db_patcher = patch("src.main.views.properties_panel.get_database", return_value=self.mock_db)
        self.db_patcher.start()
        self.addCleanup(self.db_patcher.stop)

        # Simulated callback to listen to the "Apply" button
        self.mock_on_apply = MagicMock()
        
        # Instantiate the real properties panel attached to the hidden root
        self.panel = PropertiesPanel(self.root, on_apply_callback=self.mock_on_apply)

    def tearDown(self):
        """Cleanly destroy interface components after each test."""
        self.root.destroy()

    def _mock_columns_schema(self, table_name):
        """Helper to emulate dynamic columns read from the database."""
        if table_name == "component_boxes":
            return [("id", "INTEGER"), ("name", "TEXT"), ("description", "TEXT"), ("color", "TEXT")]
        elif table_name == "action_circles":
            return [("id", "INTEGER"), ("title", "TEXT"), ("description", "TEXT"), ("image_path", "TEXT")]
        elif table_name == "diamond_steps":
            return [("id", "INTEGER"), ("name", "TEXT"), ("description", "TEXT"), ("tool_id", "INTEGER")]
        return []

    def test_init_sets_defaults_and_creates_base_widgets(self):
        """Verify the panel configures correctly with its callback and database."""
        self.assertEqual(self.panel.on_apply_callback, self.mock_on_apply)
        self.assertEqual(self.panel.db, self.mock_db)
        self.assertEqual(self.panel.dynamic_fields, {})

    def test_load_shape_none_clears_panel_and_hides_widgets(self):
        """Verify that passing None hides the visual form."""
        self.panel.load_shape(None)
        
        self.assertIsNone(self.panel.current_shape)
        # We don't assert dynamic_fields is {} because the real app only hides the grid (grid_remove).

    def test_load_shape_loads_fields_for_component_box(self):
        """Validate that selecting a ComponentBox generates dynamic fields omitting 'id'."""
        shape = MagicMock(spec=ComponentBox)
        shape.properties = {
            "name": "Test Block",
            "description": "Short Description",
            "color": "#ffffff"
        }
        
        # Simulate db_id is returned and DB responds
        shape.properties["db_id"] = 1
        self.mock_db.get_component.return_value = shape.properties
        self.mock_db.get_component_fields.return_value = [
            {'name': 'name', 'type': 'TEXT', 'display_name': 'Name'},
            {'name': 'description', 'type': 'TEXT', 'display_name': 'Description'},
            {'name': 'color', 'type': 'TEXT', 'display_name': 'Color'}
        ]

        self.panel.load_shape(shape)

        self.assertEqual(self.panel.current_shape, shape)
        self.assertIn("name", self.panel.dynamic_fields)
        self.assertIn("description", self.panel.dynamic_fields)
        self.assertIn("color", self.panel.dynamic_fields)

    def test_load_shape_loads_fields_for_action_circle(self):
        """Ensure exclusive properties of an ActionCircle are loaded correctly."""
        shape = MagicMock(spec=ActionCircle)
        shape.text = "Action Circle"
        shape.step_description = "Action to perform"
        shape.image_path = "/path/to/img.png"
        shape.db_step_id = None
        
        self.mock_db.get_step_fields.return_value = [
            {'name': 'title', 'type': 'TEXT', 'display_name': 'Title'},
            {'name': 'description', 'type': 'TEXT', 'display_name': 'Description'},
            {'name': 'image_path', 'type': 'TEXT', 'display_name': 'Image Path'}
        ]

        self.panel.load_shape(shape)

        self.assertIn("title", self.panel.dynamic_fields)
        self.assertIn("description", self.panel.dynamic_fields)
        self.assertIn("image_path", self.panel.dynamic_fields)

    def test_load_shape_loads_fields_for_diamond_step_with_combobox(self):
        """Validate that special fields like 'tool_id' load dropdown menus (Combobox)."""
        shape = MagicMock(spec=DiamondStep)
        shape.name = "Decision A"
        shape.description = "Evaluate condition"
        shape.tool_id = 2
        shape.db_action_id = None

        self.mock_db.get_action_fields.return_value = [
            {'name': 'name', 'type': 'TEXT', 'display_name': 'Name'},
            {'name': 'description', 'type': 'TEXT', 'display_name': 'Description'},
            {'name': 'tool_id', 'type': 'INTEGER', 'display_name': 'Tool', 'widget_type': 'dropdown'}
        ]
        self.mock_db.get_all_tools.return_value = [{'id': 1, 'name': "Tool 1"}, {'id': 2, 'name': "Tool 2"}]

        self.panel.load_shape(shape)

        self.assertIn("name", self.panel.dynamic_fields)
        self.assertIn("description", self.panel.dynamic_fields)
        self.assertIn("tool_id", self.panel.dynamic_fields)
        
        widget = self.panel.dynamic_fields["tool_id"]
        self.assertIsInstance(widget, ttk.Combobox)

    def test_on_apply_extracts_and_updates_component_box_model(self):
        """Test that data written in the UI saves into the ComponentBox model."""
        shape = ComponentBox(10, 20)
        shape.properties = {}
        self.panel.current_shape = shape

        # Add 'spec=ttk.Entry' so _get_widget_value recognizes it
        mock_name_widget = MagicMock(spec=ttk.Entry)
        mock_name_widget.get.return_value = "New Block Name"
        
        mock_desc_widget = MagicMock(spec=ttk.Entry)
        mock_desc_widget.get.return_value = "New Desc"
        
        self.panel.dynamic_fields = {
            "name": mock_name_widget,
            "description": mock_desc_widget
        }

        self.panel._on_apply()

        self.assertEqual(shape.properties["name"], "New Block Name")
        self.assertEqual(shape.properties["description"], "New Desc")
        self.assertEqual(shape.text, "New Block Name")
        
        self.mock_on_apply.assert_called_once()

    def test_on_apply_extracts_and_updates_action_circle_model(self):
        """Test that UI data saves correctly into the ActionCircle model."""
        shape = ActionCircle(50, 50)
        self.panel.current_shape = shape

        mock_title_widget = MagicMock(spec=ttk.Entry)
        mock_title_widget.get.return_value = "Operation Title"
        
        mock_desc_widget = MagicMock(spec=ttk.Entry)
        mock_desc_widget.get.return_value = "Operation Description"
        
        mock_img_widget = MagicMock(spec=ttk.Entry)
        mock_img_widget.get.return_value = "/assets/icon.png"

        self.panel.dynamic_fields = {
            "title": mock_title_widget,
            "description": mock_desc_widget,
            "image_path": mock_img_widget
        }

        self.panel._on_apply()

        self.assertEqual(shape.text, "Operation Title")
        self.assertEqual(shape.step_description, "Operation Description")
        self.assertEqual(shape.image_path, "/assets/icon.png")
        self.mock_on_apply.assert_called_once()

    def test_on_apply_extracts_and_updates_diamond_step_with_combobox_mapping(self):
        """Test that the Combobox correctly assigns ids and reverse mappings."""
        shape = DiamondStep(100, 100)
        self.panel.current_shape = shape

        mock_name_widget = MagicMock(spec=ttk.Entry)
        mock_name_widget.get.return_value = "System Question"
        
        mock_desc_widget = MagicMock(spec=ttk.Entry)
        mock_desc_widget.get.return_value = "Validate token"
        
        # Must be ttk.Combobox to extract using maps
        mock_tool_widget = MagicMock(spec=ttk.Combobox)
        mock_tool_widget.get.return_value = "Special Tool"
        mock_tool_widget.tool_map = {"Special Tool": 5}
        mock_tool_widget.tool_map_reverse = {5: "Special Tool"}

        self.panel.dynamic_fields = {
            "name": mock_name_widget,
            "description": mock_desc_widget,
            "tool_id": mock_tool_widget
        }

        self.panel._on_apply()

        self.assertEqual(shape.name, "System Question")
        self.assertEqual(shape.text, "System Question")
        self.assertEqual(shape.description, "Validate token")
        self.assertEqual(shape.tool_id, 5)
        self.assertEqual(shape.tools, "Special Tool")
        self.mock_on_apply.assert_called_once()

    def test_refresh_reloads_values_from_current_shape(self):
        """Validate that the refresh method re-invokes load_shape to update fields from the DB."""
        shape = MagicMock(spec=ComponentBox)
        self.panel.current_shape = shape
        
        with patch.object(self.panel, "load_shape") as mock_load_shape:
            self.panel.refresh()
            mock_load_shape.assert_called_with(shape)


if __name__ == "__main__":
    unittest.main()