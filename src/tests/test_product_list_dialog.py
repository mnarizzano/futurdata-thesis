"""
Unit tests for ProductListDialog workflow behavior.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from src.main.views.product_list_dialog import ProductListDialog


class TestProductListDialog(unittest.TestCase):
    """Tests ProductListDialog lifecycle and choice validations."""

    def setUp(self):
        self.root = tk.Tk()
        self.mock_db = MagicMock()
        self.mock_callback = MagicMock()

        self.mock_products = [
            {"id": 42, "name": "Espresso Machine v1", "author": "Noé", "modified": "2026-07-01"}
        ]
        self.mock_db.get_all_products.return_value = self.mock_products
        self.mock_db.get_product.return_value = {"id": 42, "name": "Espresso Machine v1"}

        self.dialog_wrapper = ProductListDialog(self.root, self.mock_db, self.mock_callback)

    def tearDown(self):
        self.dialog_wrapper.dialog.destroy()
        self.root.destroy()

    def test_load_products_inserts_items_into_treeview(self):
        """Initialization must read existing saved products from database and insert into UI Treeview."""
        # Retrieve all rows in treeview
        children = self.dialog_wrapper.tree.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0], "42") # product_id is used as item identifier identifier
        
        values = self.dialog_wrapper.tree.item(children[0])["values"]
        self.assertIn("Espresso Machine v1", values)
        self.assertIn("Noé", values)

    @patch("tkinter.messagebox.showwarning")
    def test_load_selected_with_no_selection_warns_user(self, mock_warning):
        """Clicking load selection without an active highlight item row must raise a warning."""
        self.dialog_wrapper.tree.selection_remove(self.dialog_wrapper.tree.selection())
        self.dialog_wrapper.tree_on_double_click(None) # calls _load_selected
        
        mock_warning.assert_called_with("No Selection", "Please select a product to load")
        self.assertFalse(self.mock_callback.called)

    @patch("tkinter.messagebox.askyesno", return_value=True)
    @patch("tkinter.messagebox.showinfo")
    def test_delete_selected_confirmed_calls_database_and_refreshes(self, mock_info, mock_confirm):
        """Confirming product deletion must wipe product logs from database manager and clean tree view."""
        self.dialog_wrapper.tree.selection_set("42")
        self.dialog_wrapper._delete_selected()

        self.mock_db.delete_product.assert_called_once_with(42)
        self.mock_db.get_all_products.assert_called() # verifies reload call execution


if __name__ == "__main__":
    unittest.main()