"""
Unit tests for ManageMaterialsDialog logic.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from src.main.views.manage_materials_dialog import ManageMaterialsDialog


class TestManageMaterialsDialog(unittest.TestCase):
    """Tests ManageMaterialsDialog behaviors using completely mocked environments."""

    def setUp(self):
        self.root = tk.Tk()
        self.mock_controller = MagicMock()
        
        # Mock database setup on controller
        self.mock_materials = [
            {"id": 1, "name": "Copper"},
            {"id": 2, "name": "Stainless Steel"}
        ]
        self.mock_controller.db.get_all_materials.return_value = self.mock_materials

        # Instantiate dialog
        with patch.object(ManageMaterialsDialog, "wait_window"):
            self.dialog = ManageMaterialsDialog(self.root, self.mock_controller)

    def tearDown(self):
        self.dialog.destroy()
        self.root.destroy()

    def test_load_materials_populates_listbox_and_records(self):
        """The dialog must fetch materials from DB and populate the Listbox on creation."""
        self.dialog.load_materials()
        
        # Verify Listbox content
        listbox_items = self.dialog.listbox.get(0, tk.END)
        self.assertIn("Copper", listbox_items)
        self.assertIn("Stainless Steel", listbox_items)
        
        # Verify internal mapping record dictionary
        self.assertEqual(self.dialog.material_records["Copper"], 1)
        self.assertEqual(self.dialog.material_records["Stainless Steel"], 2)

    @patch("tkinter.messagebox.showwarning")
    def test_on_delete_with_no_selection_triggers_warning(self, mock_warning):
        """Attempting to click delete without selecting an item must raise a warning."""
        self.dialog.listbox.selection_clear(0, tk.END) # ensure nothing selected
        self.dialog.on_delete()
        
        mock_warning.assert_called_once()
        self.assertFalse(self.mock_controller.delete_material.called)

    @patch("tkinter.messagebox.askyesno", return_value=True)
    @patch("tkinter.messagebox.showinfo")
    def test_on_delete_confirmed_calls_controller_and_reloads(self, mock_info, mock_confirm):
        """Confirming deletion must call controller.delete_material and refresh active records."""
        # Setup simulated selection
        self.dialog.listbox.insert(tk.END, "Copper")
        self.dialog.material_records["Copper"] = 1
        self.dialog.listbox.selection_set(0)

        self.dialog.on_delete()

        self.mock_controller.delete_material.assert_called_once_with(1)
        mock_info.assert_called_once_with("Success", "Material deleted successfully.", parent=self.dialog)


if __name__ == "__main__":
    unittest.main()