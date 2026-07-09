"""
Unit tests for DiagramSerializer behavior.

Covers:
  - Serialization / Save to file
  - Deserialization / Load from file
  - Structure Validation
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.utils.serializer import DiagramSerializer
from src.main.models.diagram import Diagram


class TestDiagramSerializer(unittest.TestCase):
    """Tests the integrity of the DiagramSerializer logic without writing to real disks."""

    def setUp(self):
        self.diagram = Diagram()
        self.diagram.metadata["product_name"] = "Test Coffee Machine"
        self.diagram.metadata["author"] = "Noé"

    @patch("os.makedirs")
    @patch("json.dump")
    def test_save_to_file_success_updates_diagram_state(self, mock_json_dump, mock_makedirs):
        """Saving a valid diagram must set diagram.modified to False and update file_path."""
        m_open = mock_open()
        with patch("builtins.open", m_open):
            result = DiagramSerializer.save_to_file(self.diagram, "dummy_path.json")

        self.assertTrue(result)
        self.assertEqual(self.diagram.file_path, "dummy_path.json")
        self.assertFalse(self.diagram.modified)
        mock_makedirs.assert_called_once_with("", exist_ok=True)
        m_open.assert_called_once_with("dummy_path.json", 'w', encoding='utf-8')

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": "json"}')
    def test_load_from_file_with_invalid_structure_returns_none(self, mock_file):
        """Loading a file that fails structure validation must return None."""
        # execution
        loaded_diagram = DiagramSerializer.load_from_file("dummy_path.json")
        self.assertIsNone(loaded_diagram)

    def test_validate_structure_with_missing_keys_returns_false(self):
        """Validation must reject dictionaries missing metadata, shapes, or connections."""
        incomplete_data = {
            "metadata": {},
            "shapes": []
            # 'connections' missing
        }
        self.assertFalse(DiagramSerializer.validate_structure(incomplete_data))

    def test_validate_structure_with_correct_keys_returns_true(self):
        """Validation must accept dictionaries containing all required structure parameters."""
        complete_data = {
            "metadata": {},
            "shapes": [],
            "connections": []
        }
        self.assertTrue(DiagramSerializer.validate_structure(complete_data))


if __name__ == "__main__":
    unittest.main()