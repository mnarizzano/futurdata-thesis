import os
import sys
import unittest
from types import ModuleType
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock Environment
def setup_mocks():
    # Mock the 'models' package if it's not present locally
    models_mod = ModuleType('models')
    sys.modules['models'] = models_mod
    for cls_name in ['Diagram', 'ComponentBox', 'ActionCircle', 'DiamondStep', 'ArrowShape', 'Connection']:
        setattr(models_mod, cls_name, MagicMock())

    # Mock GUI dependencies
    tk_mock = MagicMock()
    class MockToplevel:
        def __init__(self, *args, **kwargs): pass
        def grab_set(self): pass
        def wait_window(self, *args): pass
        def destroy(self): pass
    
    tk_mock.Toplevel = MockToplevel
    tk_mock.END = 'end'
    sys.modules['tkinter'] = tk_mock
    sys.modules['tkinter.ttk'] = MagicMock()
    sys.modules['tkinter.messagebox'] = MagicMock()

setup_mocks()

from src.main.views.manage_colors_dialog import ManageColorsDialog


class TestManageColorsDialog(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_controller = MagicMock()
        self.mock_controller.db = self.mock_db

    def test_load_colors_logic(self):
        """Tests that colors are correctly fetched from DB and stored in the listbox records."""
        self.mock_db.get_all_colors.return_value = [
            {'id': 1, 'name': 'Red', 'hex_code': '#FF0000'}
        ]
        
        with patch.object(ManageColorsDialog, '__init__', return_value=None):
            dialog = ManageColorsDialog()
            dialog.controller = self.mock_controller
            dialog.listbox = MagicMock()
            dialog.color_records = {}
            
            ManageColorsDialog.load_colors(dialog)
            
            self.mock_db.get_all_colors.assert_called_once()
            self.assertIn('Red (#FF0000)', dialog.color_records)
            self.assertEqual(dialog.color_records['Red (#FF0000)'], 1)

    def test_on_delete_success(self):
        """Tests the deletion logic when a user confirms the action."""
        with patch.object(ManageColorsDialog, '__init__', return_value=None):
            dialog = ManageColorsDialog()
            dialog.controller = self.mock_controller
            dialog.listbox = MagicMock()
            dialog.listbox.curselection.return_value = [0]
            dialog.listbox.get.return_value = 'Red (#FF0000)'
            dialog.color_records = {'Red (#FF0000)': 1}
            
            # Mock user clicking 'Yes' on the confirmation dialog
            with patch('tkinter.messagebox.askyesno', return_value=True):
                ManageColorsDialog.on_delete(dialog)
                self.mock_controller.delete_color.assert_called_with(1)

    def test_on_delete_no_selection_shows_warning(self):
        """Tests that no deletion happens if the user has not selected a color."""
        with patch.object(ManageColorsDialog, '__init__', return_value=None):
            dialog = ManageColorsDialog()
            dialog.controller = self.mock_controller
            dialog.listbox = MagicMock()
            dialog.listbox.curselection.return_value = []

            with patch('src.main.views.manage_colors_dialog.messagebox.showwarning') as mock_warning:
                ManageColorsDialog.on_delete(dialog)

            mock_warning.assert_called_once()
            self.mock_controller.delete_color.assert_not_called()

    def test_on_delete_cancelled_does_not_delete(self):
        """Tests that cancelling the confirmation dialog does not delete the color."""
        with patch.object(ManageColorsDialog, '__init__', return_value=None):
            dialog = ManageColorsDialog()
            dialog.controller = self.mock_controller
            dialog.listbox = MagicMock()
            dialog.listbox.curselection.return_value = [0]
            dialog.listbox.get.return_value = 'Red (#FF0000)'
            dialog.color_records = {'Red (#FF0000)': 1}

            with patch('src.main.views.manage_colors_dialog.messagebox.askyesno', return_value=False):
                ManageColorsDialog.on_delete(dialog)

            self.mock_controller.delete_color.assert_not_called()

    def test_on_delete_value_error_shows_constraint_error(self):
        """Tests that database constraint errors are surfaced to the user."""
        with patch.object(ManageColorsDialog, '__init__', return_value=None):
            dialog = ManageColorsDialog()
            dialog.controller = self.mock_controller
            dialog.listbox = MagicMock()
            dialog.listbox.curselection.return_value = [0]
            dialog.listbox.get.return_value = 'Red (#FF0000)'
            dialog.color_records = {'Red (#FF0000)': 1}
            self.mock_controller.delete_color.side_effect = ValueError('Color in use')

            with patch('src.main.views.manage_colors_dialog.messagebox.askyesno', return_value=True), \
                 patch('src.main.views.manage_colors_dialog.messagebox.showerror') as mock_error:
                ManageColorsDialog.on_delete(dialog)

            mock_error.assert_called_once()
            self.assertIn('Color in use', mock_error.call_args[0][1])

if __name__ == '__main__':
    unittest.main()