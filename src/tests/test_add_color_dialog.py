"""
Unit tests for AddColorDialog.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_add_color_dialog -v
"""

import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
from main.views.add_color_dialog import AddColorDialog

class TestAddColorDialog(unittest.TestCase):
    
    def setUp(self):
        """
        Executed automatically before every individual test method.
        Sets up the required environment and dependencies.
        """
        # Create a hidden background root Tkinter window to manage variables/widgets safely
        self.root = tk.Tk()
        self.root.withdraw()

        # Create a mock application controller to track interactions without needing the real backend
        self.controller = MagicMock()

    
    def tearDown(self):
        """
        Executed automatically after every individual test method finishes.
        Cleans up resources to prevent memory leaks or dangling UI components.
        """
        # Completely destroy the root Tkinter window created in setUp
        self.root.destroy()

    @patch('main.views.add_color_dialog.AddColorDialog.wait_window')
    @patch('main.views.add_color_dialog.AddColorDialog.grab_set')
    def test_init(self, mock_grab, mock_wait):
        """
        Tests the constructor (__init__) of the AddColorDialog class.
        Verifies variables initialize correctly and UI-blocking calls are made.
        """
        # Initialize the modal dialog window under test
        dialog = AddColorDialog(self.root, self.controller)

        # Verify that form data-binding variables are created with the correct Tkinter types
        self.assertIsInstance(dialog.name_var, tk.StringVar)
        self.assertIsInstance(dialog.hex_var, tk.StringVar)

        # Verify that the dialog's window title is set correctly
        self.assertEqual(dialog.title(), "Add New Color")

        # Confirm that the application safely locks focus and awaits closure without hanging the test
        mock_grab.assert_called_once()
        mock_wait.assert_called_once_with(dialog)

    @patch('main.views.add_color_dialog.AddColorDialog.wait_window')
    @patch('main.views.add_color_dialog.AddColorDialog.grab_set')
    @patch('main.views.add_color_dialog.colorchooser.askcolor')
    def test_choose_color(self, mock_askcolor, mock_grab, mock_wait):
        """
        Tests the 'choose_color' method which triggers the system color picker.
        Verifies that chosen colors are properly parsed and injected into the variables.
        """
        dialog = AddColorDialog(self.root, self.controller)

        # Simulate the user opening the color picker and selecting an orange color
        # Format matching tk.colorchooser output tuple: ((R, G, B), '#hex')
        mock_askcolor.return_value = ((255.0, 128.0, 0.0), '#ff8000')

        # Trigger the color choice workflow
        dialog.choose_color()

        # Verify that the underlying variables received the mapped values correctly
        self.assertEqual(dialog.hex_var.get(), '#ff8000')
        self.assertEqual(dialog.rgb_r_var.get(), '255')
        self.assertEqual(dialog.rgb_g_var.get(), '128')
        self.assertEqual(dialog.rgb_b_var.get(), '0')

    @patch('main.views.add_color_dialog.AddColorDialog.wait_window')
    @patch('main.views.add_color_dialog.AddColorDialog.grab_set')
    def test_on_save_success(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when all required input fields are valid.
        Verifies that data is properly forwarded to the controller and the dialog closes.
        """
        dialog = AddColorDialog(self.root, self.controller)

        # Mock the window's close/destroy sequence so the test can observe it without errors
        dialog.destroy = MagicMock()

        # Populate all necessary string and integer parameters across the simulated form
        dialog.name_var.set("Orange")
        dialog.hex_var.set("#ff8000")
        dialog.rgb_r_var.set("255")
        dialog.rgb_g_var.set("128")
        dialog.rgb_b_var.set("0")

        # Simulate pressing the "Save" button
        dialog.on_save()

        # Assert that the controller was requested to create the color using the clean data types
        self.controller.add_new_color.assert_called_once_with("Orange", "#ff8000", 255, 128, 0)

        # Assert that the dialog closed itself cleanly upon success
        dialog.destroy.assert_called_once()

    @patch('main.views.add_color_dialog.AddColorDialog.wait_window')
    @patch('main.views.add_color_dialog.AddColorDialog.grab_set')
    def test_on_save_missing_fields(self, mock_grab, mock_wait):
        """
        Tests 'on_save' behavior when validation fails due to empty parameters.
        Verifies that the controller database script is guarded against bad data.
        """
        dialog = AddColorDialog(self.root, self.controller)

        # Leave critical inputs blank (or explicitly clear them) to trigger form validation limits
        dialog.name_var.set("")

        # Attempt to save the incomplete form
        dialog.on_save()

        # Assert that validation successfully caught the problem and did NOT forward it to the database
        self.controller.add_new_color.assert_not_called()

if __name__ == '__main__':
    # Discover and run all unit tests defined inside this script file
    unittest.main()
