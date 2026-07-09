"""
Unit tests for AddToolDialog.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_add_Tool_dialog -v
"""

import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
from main.views.add_tool_dialog import AddToolDialog

class TestAddToolDialog(unittest.TestCase):
    def setUp(self):
        """
        Executed automatically before every individual test method.
        Sets up the required isolated environment and mock application dependencies.
        """
        # Create a hidden background root Tkinter window to manage variables/widgets safely
        self.root = tk.Tk()
        self.root.withdraw()

        # Create a mock application controller to isolate the UI layer from backend/database interactions
        self.controller = MagicMock()

    def tearDown(self):
        """
        Executed automatically after every individual test method finishes.
        Cleans up graphical components to prevent memory leaks or hanging windows.
        """
        # Completely destroy the root Tkinter window created in setUp
        self.root.destroy()

    @patch('main.views.add_tool_dialog.AddToolDialog.wait_window')
    @patch('main.views.add_tool_dialog.AddToolDialog.grab_set')
    def test_init(self, mock_grab, mock_wait):
        """
        Tests the constructor (__init__) of the AddToolDialog class.
        Verifies that the window title is applied properly and the dialog intercepts user focus.
        """
        # Initialize the modal dialog window under test
        dialog = AddToolDialog(self.root, self.controller)

        # Verify that the dialog's window title is set correctly
        self.assertEqual(dialog.title(), "Add New Tool")

        # Confirm that the application safely locks input focus and awaits closure without hanging the test
        mock_grab.assert_called_once()
        mock_wait.assert_called_once_with(dialog)

    @patch('main.views.add_tool_dialog.AddToolDialog.wait_window')
    @patch('main.views.add_tool_dialog.AddToolDialog.grab_set')
    def test_on_save_success(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when all required tool input fields are valid.
        Verifies that inputs are correctly extracted and passed down to the application controller.
        """
        dialog = AddToolDialog(self.root, self.controller)

        # Mock the window's close/destroy sequence so the test can observe it without errors
        dialog.destroy = MagicMock()
        
        # Populate necessary string input parameters across the simulated form
        dialog.name_var.set("Power Drill")
        dialog.category_var.set("Power Tools")
        
        # Simulate pressing the "Save" button
        dialog.on_save()

        # Assert that the controller was successfully requested to save the tool with the accurate parameters
        self.controller.add_new_tool.assert_called_once_with("Power Drill", "Power Tools")

        # Assert that the dialog automatically closed itself cleanly upon success
        dialog.destroy.assert_called_once()

    @patch('main.views.add_tool_dialog.AddToolDialog.wait_window')
    @patch('main.views.add_tool_dialog.AddToolDialog.grab_set')
    def test_on_save_missing_name(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when validation fails due to a missing tool name.
        Verifies that incomplete forms are intercepted and prevented from saving to the system catalog.
        """
        dialog = AddToolDialog(self.root, self.controller)

        # Leave critical name input blank to intentionally trigger form validation limits
        dialog.name_var.set("")
        dialog.category_var.set("Hand Tools")
        
        # Attempt to save the incomplete form
        dialog.on_save()

        # Assert that validation successfully caught the problem and did NOT forward it to the database/controller
        self.controller.add_new_tool.assert_not_called()

if __name__ == '__main__':
    # Discover and run all unit tests defined inside this script file
    unittest.main()
