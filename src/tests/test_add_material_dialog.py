"""
Unit tests for AddMaterialDialog.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_add_material_dialog -v
"""

import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
from main.views.add_material_dialog import AddMaterialDialog

class TestAddMaterialDialog(unittest.TestCase):
    def setUp(self):
        """
        Executed automatically before every individual test method.
        Sets up the required environment and mocks the relational database layer.
        """
        # Create a hidden background root Tkinter window to manage variables/widgets safely
        self.root = tk.Tk()
        self.root.withdraw()

        # Create a mock application controller to isolate the UI layer from the backend logic
        self.controller = MagicMock()

        # Mock the database response for fetching colors.
        # This simulates having existing rows in your database color table.
        self.controller.db.get_all_colors.return_value = [
            {'id': 1, 'name': 'Red'},
            {'id': 2, 'name': 'Blue'}
        ]

    def tearDown(self):
        """
        Executed automatically after every individual test method finishes.
        Cleans up resources to prevent memory leaks or dangling UI components.
        """
        # Completely destroy the root Tkinter window created in setUp
        self.root.destroy()

    @patch('main.views.add_material_dialog.AddMaterialDialog.wait_window')
    @patch('main.views.add_material_dialog.AddMaterialDialog.grab_set')
    def test_init(self, mock_grab, mock_wait):
        """
        Tests the constructor (__init__) of the AddMaterialDialog class.
        Verifies window setup and that the database results are correctly converted into a lookup map.
        """
        # Initialize the modal dialog window under test
        dialog = AddMaterialDialog(self.root, self.controller)

        # Verify that the dialog's window title is set correctly
        self.assertEqual(dialog.title(), "Add New Material")

        # Verify that the array of color dictionaries from the database was successfully
        # parsed into a clean {'Name': ID} key-value lookup map for the Combobox dropdown.
        self.assertDictEqual(dialog.color_map, {'Red': 1, 'Blue': 2})

        # Confirm that the application safely locks focus and awaits closure without hanging the test
        mock_grab.assert_called_once()
        mock_wait.assert_called_once_with(dialog)

    @patch('main.views.add_material_dialog.AddMaterialDialog.wait_window')
    @patch('main.views.add_material_dialog.AddMaterialDialog.grab_set')
    def test_on_save_success(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when all required material input fields are valid.
        Verifies that the text color name is translated back to its relational integer ID.
        """
        dialog = AddMaterialDialog(self.root, self.controller)

        # Mock the window's close/destroy sequence so the test can observe it without errors
        dialog.destroy = MagicMock()
        
        # Populate all necessary string entries across the simulated form
        dialog.name_var.set("Oak Wood")
        dialog.sci_name_var.set("Quercus")
        dialog.color_var.set("Blue") # Selected from the mocked dropdown values
        
        # Simulate pressing the "Save" button
        dialog.on_save()

        # Assert that the controller was called with correct data and that "Blue" 
        # was successfully mapped to its primary key integer ID (2) from the database mock.
        self.controller.add_new_material.assert_called_once_with("Oak Wood", "Quercus", 2)

        # Assert that the dialog closed itself cleanly upon success
        dialog.destroy.assert_called_once()

    @patch('main.views.add_material_dialog.AddMaterialDialog.wait_window')
    @patch('main.views.add_material_dialog.AddMaterialDialog.grab_set')
    def test_on_save_missing_name(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when validation fails due to a missing material name.
        Verifies that the controller database script is guarded against bad data.
        """
        dialog = AddMaterialDialog(self.root, self.controller)

        # Leave critical name input blank to trigger form validation limits
        dialog.name_var.set("")
        dialog.color_var.set("Red")
        
        # Attempt to save the incomplete form
        dialog.on_save()

        # Assert that validation successfully caught the problem and did NOT forward it to the database
        self.controller.add_new_material.assert_not_called()

if __name__ == '__main__':
    # Discover and run all unit tests defined inside this script file
    unittest.main()
