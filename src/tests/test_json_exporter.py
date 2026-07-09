import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models import ActionCircle, ComponentBox, Connection, Diagram
from src.main.utils.json_exporter import EnhancedJSONExporter


class EnhancedJSONExporterTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.get_product.return_value = {
            "id": 7,
            "name": "Coffee Maker",
            "brand": "BrandX",
            "model": "CM100",
        }
        self.db.get_components_by_product.return_value = [
            {"source_table": "component", "component_id": 88, "name": "Motor"}
        ]
        self.exporter = EnhancedJSONExporter(self.db)

    def _write_temp_json(self, data):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        try:
            json.dump(data, handle)
            handle.flush()
            return handle.name
        finally:
            handle.close()

    def test_export_diagram_writes_expected_json_structure(self):
        diagram = Diagram()
        component = ComponentBox(100, 100)
        component.properties.update({
            "name": "Pump",
            "brand": "Acme",
            "model": "P1",
            "color_id": 3,
            "material_id": 2,
            "db_id": 11,
            "node_type": "Root",
        })
        action = ActionCircle(300, 100)
        action.step_description = "Assemble part"
        action.tools = "Screwdriver"
        action.image_path = "step.png"

        diagram.add_shape(component)
        diagram.add_shape(action)
        diagram.add_connection(Connection(component, action))

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            path = handle.name

        try:
            exported = self.exporter.export_diagram(diagram, path, product_id=7)
            self.assertTrue(exported)

            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            self.assertIn("metadata", data)
            self.assertIn("diagram", data)
            self.assertIn("shapes", data)
            self.assertIn("connections", data)
            self.assertIn("database", data)
            self.assertEqual(data["metadata"]["product_name"], "Coffee Maker")
            self.assertEqual(len(data["shapes"]), 2)
            self.assertEqual(len(data["connections"]), 1)
            self.assertEqual(data["shapes"][0]["type"], "product")
            self.assertEqual(data["shapes"][1]["type"], "action")
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_import_diagram_restores_shapes_and_connections(self):
        diagram = Diagram()
        component = ComponentBox(100, 100)
        component.properties.update({
            "name": "Motor",
            "brand": "BrandY",
            "model": "M2",
            "color_id": 5,
            "material_id": 9,
            "db_id": 21,
            "node_type": "Intermediate",
        })
        action = ActionCircle(300, 100)
        action.db_step_id = 44
        diagram.add_shape(component)
        diagram.add_shape(action)
        diagram.add_connection(Connection(component, action))

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            path = handle.name

        try:
            self.assertTrue(self.exporter.export_diagram(diagram, path, product_id=7))

            imported = self.exporter.import_diagram(path, create_in_db=False)
            self.assertIsNotNone(imported)
            self.assertEqual(len(imported.shapes), 2)
            self.assertEqual(len(imported.connections), 1)

            component_imported = next(shape for shape in imported.shapes if isinstance(shape, ComponentBox))
            action_imported = next(shape for shape in imported.shapes if isinstance(shape, ActionCircle))

            self.assertEqual(component_imported.properties["name"], "Motor")
            self.assertEqual(component_imported.properties["db_id"], 21)
            self.assertEqual(action_imported.db_step_id, 44)
            self.assertEqual(imported.connections[0].from_shape, component_imported)
            self.assertEqual(imported.connections[0].to_shape, action_imported)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
