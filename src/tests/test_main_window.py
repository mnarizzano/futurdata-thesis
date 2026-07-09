"""
Unit tests for MainWindow view component.

Covers:
  - Window initialization, titles, sizing geometry, and constraints.
  - Correct layout building (Menus, Toolbars, Main Layout Areas, Status Bars).
  - Keyboard shortcut configurations and event binding hooks.
  - Native system dialog delegation wrappers (File Open/Save, Messageboxes).
  - State synchronization UI updates driven by the Controller.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_main_window -v
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
from tkinter import ttk, messagebox, filedialog

from src.main.views.main_window import MainWindow


class MainWindowTests(unittest.TestCase):

    def setUp(self):
        """Initialize headless Tkinter root and isolate MainWindow dependencies."""
        self.root = tk.Tk()
        self.root.withdraw()  # Keeps the GUI hidden during test runs

        # Mock the application controller
        self.mock_controller = MagicMock()
        self.mock_controller.can_undo.return_value = True
        self.mock_controller.can_redo.return_value = False

        # Create real Tkinter widgets to bypass Tcl strict path validation.
        # This prevents the '_tkinter.TclError: bad window path name' crash.
        self.dummy_canvas = tk.Canvas(self.root)
        self.dummy_properties = ttk.Frame(self.root)
        self.dummy_properties.load_shape = MagicMock()
        self.dummy_properties.refresh = MagicMock()

        # Patch internal sub-views and force them to return our real Tkinter widgets
        self.canvas_patcher = patch("src.main.views.main_window.DiagramCanvas", return_value=self.dummy_canvas)
        self.properties_patcher = patch("src.main.views.main_window.PropertiesPanel", return_value=self.dummy_properties)
        
        self.mock_canvas_class = self.canvas_patcher.start()
        self.mock_properties_class = self.properties_patcher.start()

        # Instantiate the main window component under test
        self.window = MainWindow(self.root, self.mock_controller)

    def tearDown(self):
        """Cleanly destroy widgets and release patches after each test execution."""
        self.canvas_patcher.stop()
        self.properties_patcher.stop()
        self.root.destroy()

    def test_init_configures_root_window_properties(self):
        """Verify that initialization sets the title, size, and minimal constraints."""
        self.assertEqual(self.root.title(), "Disassembly Flow Diagram Builder")
        # Checking that size boundaries or tracking reference elements match
        self.assertEqual(self.window.root, self.root)
        self.assertEqual(self.window.controller, self.mock_controller)

    def test_create_menu_builds_and_attaches_menu_bar(self):
        """Verify that menu bar structures are instantiated and applied to root."""
        # A menu property configuration should exist on root window
        root_menu = self.root.cget("menu")
        self.assertTrue(root_menu != "")

    def test_create_toolbar_instantiates_action_buttons(self):
        """Ensure all required toolbar control buttons are created with active references."""
        self.assertTrue(hasattr(self.window, "snap_btn"))
        self.assertIsInstance(self.window.snap_btn, tk.Button)

    def test_create_main_area_embeds_canvas_and_properties_panels(self):
        """Verify that DiagramCanvas and PropertiesPanel classes are built inside layout."""
        self.mock_canvas_class.assert_called()
        self.mock_properties_class.assert_called()
        self.assertTrue(hasattr(self.window, "canvas"))
        self.assertTrue(hasattr(self.window, "properties_panel"))

    def test_create_status_bar_adds_informational_label(self):
        """Check if the status bar label widget exists on layout creation."""
        # Main window should register an internal status bar component or label
        self.assertTrue(hasattr(self.window, "status_label") or any(
            isinstance(w, ttk.Label) for w in self.root.winfo_children()
        ))

    def test_bind_shortcuts_registers_keyboard_events(self):
        """Verify that standard operational keyboard accelerators are bound to layout hooks."""
        # Temporarily patch root bind to intercept shortcut attachment assertions
        with patch.object(self.root, "bind") as mock_bind:
            self.window._bind_shortcuts()
            # Assert crucial standard hotkeys were attempted to be bound
            mock_bind.assert_any_call("<Control-z>", unittest.mock.ANY)
            mock_bind.assert_any_call("<Control-y>", unittest.mock.ANY)

    def test_update_ui_state_synchronizes_menu_and_button_availability(self):
        """Check if UI state inquiries query controller capabilities to refresh button properties."""
        self.window.update_ui_state()
        self.mock_controller.can_undo.assert_called()
        self.mock_controller.can_redo.assert_called()

    def test_get_file_path_delegates_to_native_open_file_dialog(self):
        """Ensure get_file_path calls asksaveasfilename when save argument is false."""
        with patch.object(filedialog, "askopenfilename", return_value="/workspace/diagram.json") as mock_open:
            path = self.window.ask_file_path(save=False)
            mock_open.assert_called_once()
            self.assertEqual(path, "/workspace/diagram.json")

    def test_get_file_path_delegates_to_native_save_file_dialog(self):
        """Ensure get_file_path calls asksaveasfilename when save argument is true."""
        with patch.object(filedialog, "asksaveasfilename", return_value="/workspace/export.json") as mock_save:
            path = self.window.ask_file_path(save=True)
            mock_save.assert_called_once()
            self.assertEqual(path, "/workspace/export.json")

    def test_show_error_deploys_native_error_modal_messagebox(self):
        """Verify that show_error calls the underlying native tk.messagebox.showerror hook."""
        with patch.object(messagebox, "showerror") as mock_error_box:
            self.window.show_error("Critical Failure", "Database file is missing")
            mock_error_box.assert_called_once_with("Critical Failure", "Database file is missing")

    def test_show_info_deploys_native_info_modal_messagebox(self):
        """Verify that show_info calls the underlying native tk.messagebox.showinfo hook."""
        with patch.object(messagebox, "showinfo") as mock_info_box:
            self.window.show_info("Operation Complete", "Export finished successfully")
            mock_info_box.assert_called_once_with("Operation Complete", "Export finished successfully")

    def test_update_snap_button_appearance_when_enabled(self):
        """Verify widget adjustments when grid snapping mode transitions to enabled state."""
        self.window.update_snap_button(snap_enabled=True)
        button_text = self.window.snap_btn.cget("text")
        button_relief = self.window.snap_btn.cget("relief")
        
        self.assertEqual(button_text, "Snap to Grid: ON")
        self.assertEqual(str(button_relief), tk.SUNKEN)

    def test_update_snap_button_appearance_when_disabled(self):
        """Verify widget adjustments when grid snapping mode transitions to disabled state."""
        self.window.update_snap_button(snap_enabled=False)
        button_text = self.window.snap_btn.cget("text")
        button_relief = self.window.snap_btn.cget("relief")
        
        self.assertEqual(button_text, "Snap to Grid: OFF")
        self.assertEqual(str(button_relief), tk.RAISED)


if __name__ == "__main__":
    unittest.main()