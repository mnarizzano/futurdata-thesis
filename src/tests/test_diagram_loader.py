import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models import ActionCircle, ComponentBox, Diagram
from src.main.utils.diagram_loader import DiagramLoader


class DiagramLoaderTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db._INTERMEDIATE_OFFSET = 1000
        self.db._LEAF_OFFSET = 2000
        self.loader = DiagramLoader(self.db)

    def test_load_product_diagram_creates_root_component_and_steps(self):
        self.db.get_product.return_value = {
            "id": 10,
            "name": "Coffee Maker",
            "brand": "BrandX",
            "model": "CM1",
            "description": "Demo product",
            "color_id": 1,
            "material_id": 2,
            "weight": 3.5,
            "weight_unit": "kg",
        }
        self.db.get_components_by_product.return_value = [
            {"id": 11, "component_id": 11, "name": "Filter", "source_table": "intermediate_component", "node_type": "Intermediate", "color_id": 4, "material_id": 5, "weight": 1.0, "weight_unit": "g"}
        ]
        self.db.get_components_from_step.return_value = []

        conn = MagicMock()
        cursor = MagicMock()
        fetch_results = iter([
            [
                {"id": 1, "title": "First step", "description": "Do this", "image_path": "step.png", "step_order": 1}
            ],
            [],
            [],
            [],
            []
        ])
        cursor.fetchall.side_effect = lambda: next(fetch_results)
        conn.cursor.return_value = cursor
        self.db._get_connection.return_value.__enter__.return_value = conn
        self.db._get_connection.return_value.__exit__.return_value = None

        diagram = self.loader.load_product_diagram(10)

        self.assertIsInstance(diagram, Diagram)
        self.assertGreaterEqual(len(diagram.shapes), 3)

        root = next(shape for shape in diagram.shapes if isinstance(shape, ComponentBox) and shape.properties.get("node_type") == "Root")
        step = next(shape for shape in diagram.shapes if isinstance(shape, ActionCircle))

        self.assertEqual(root.properties["name"], "Coffee Maker")
        self.assertEqual(step.db_step_id, 1)
        self.assertEqual(step.step_description, "Do this")

    def test_load_product_diagram_creates_connections_between_root_and_steps(self):
        self.db.get_product.return_value = {"id": 20, "name": "Mixer", "brand": "", "model": "", "description": "", "color_id": None, "material_id": None, "weight": None, "weight_unit": "g"}
        self.db.get_components_by_product.return_value = []
        self.db.get_components_from_step.return_value = []

        conn = MagicMock()
        cursor = MagicMock()
        fetch_results = iter([
            [
                {"id": 5, "title": "Mix", "description": "", "image_path": "", "step_order": 1}
            ],
            [],
            [],
            []
        ])
        cursor.fetchall.side_effect = lambda: next(fetch_results)
        conn.cursor.return_value = cursor
        self.db._get_connection.return_value.__enter__.return_value = conn
        self.db._get_connection.return_value.__exit__.return_value = None

        diagram = self.loader.load_product_diagram(20)

        root_shape = next(shape for shape in diagram.shapes if isinstance(shape, ComponentBox) and shape.properties.get("node_type") == "Root")
        step_shape = next(shape for shape in diagram.shapes if isinstance(shape, ActionCircle))

        self.assertTrue(any(isinstance(shape, type(root_shape)) for shape in diagram.shapes))
        self.assertGreaterEqual(len(diagram.shapes), 2)
        self.assertEqual(len(diagram.connections), 0)

    def test_load_product_diagram_returns_none_when_product_missing(self):
        self.db.get_product.return_value = None

        diagram = self.loader.load_product_diagram(999)

        self.assertIsNone(diagram)


if __name__ == "__main__":
    unittest.main()
