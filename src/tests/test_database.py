"""
Unit tests for the DatabaseManager (src/main/models/database.py).

Each test runs against a fresh temporary SQLite file, so no mocking is
needed and the real schema (foreign keys, unique indexes, CHECK
constraints) is exercised.

Run from the project root (futurdata-thesis/):
    python3 -m unittest src.tests.test_database -v
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.models import database
from src.main.models.database import DatabaseManager, get_database


class DatabaseTestCase(unittest.TestCase):
    """Base class: creates a DatabaseManager on a temporary file."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)


class InitDatabaseTests(DatabaseTestCase):
    """_init_database: schema creation and default data."""

    def test_default_colors_inserted(self):
        colors = self.db.get_all_colors()
        names = {c["name"] for c in colors}
        self.assertEqual(len(colors), 15)
        self.assertIn("Red", names)
        self.assertIn("Transparent", names)

    def test_default_materials_inserted(self):
        materials = self.db.get_all_materials()
        names = {m["name"] for m in materials}
        self.assertEqual(len(materials), 9)
        self.assertIn("Plastic", names)
        self.assertIn("Other", names)

    def test_reinit_is_idempotent(self):
        # Opening the same file again must not duplicate default data.
        db2 = DatabaseManager(self.db_path)
        self.assertEqual(len(db2.get_all_colors()), 15)
        self.assertEqual(len(db2.get_all_materials()), 9)

    def test_all_expected_tables_exist(self):
        stats = self.db.get_statistics()
        expected = {
            'color', 'material', 'tool', 'action', 'root_component',
            'intermediate_component', 'leaf_component', 'disassembly_step',
            'disassembly_step_action', 'step_output_intermediate', 'step_output_leaf',
        }
        self.assertEqual(set(stats.keys()), expected)


class ProductOperationTests(DatabaseTestCase):
    """create/get/update/delete product (root_component)."""

    def test_create_and_get_product(self):
        product_id = self.db.create_product("Laptop", brand="Acme", model="X1",
                                            description="Test laptop")
        product = self.db.get_product(product_id)
        self.assertIsNotNone(product)
        self.assertEqual(product["name"], "Laptop")
        self.assertEqual(product["brand"], "Acme")
        self.assertEqual(product["model"], "X1")
        self.assertEqual(product["node_type"], "Root")

    def test_get_product_missing_returns_none(self):
        self.assertIsNone(self.db.get_product(9999))

    def test_get_all_products(self):
        self.db.create_product("A")
        self.db.create_product("B")
        products = self.db.get_all_products()
        self.assertEqual(len(products), 2)
        self.assertEqual({p["name"] for p in products}, {"A", "B"})

    def test_update_product(self):
        product_id = self.db.create_product("Old name")
        result = self.db.update_product(product_id, name="New name", brand="Acme")
        self.assertTrue(result)
        product = self.db.get_product(product_id)
        self.assertEqual(product["name"], "New name")
        self.assertEqual(product["brand"], "Acme")

    def test_update_product_ignores_unknown_fields(self):
        product_id = self.db.create_product("P")
        # Only unknown keys -> nothing to update -> False.
        self.assertFalse(self.db.update_product(product_id, not_a_column="x"))

    def test_update_product_missing_id_returns_false(self):
        self.assertFalse(self.db.update_product(9999, name="X"))

    def test_delete_product(self):
        product_id = self.db.create_product("P")
        self.assertTrue(self.db.delete_product(product_id))
        self.assertIsNone(self.db.get_product(product_id))

    def test_delete_product_missing_returns_false(self):
        self.assertFalse(self.db.delete_product(9999))

    def test_delete_product_cascades_to_children(self):
        product_id = self.db.create_product("P")
        self.db.create_component("Child leaf", product_id=product_id, node_type="Leaf")
        self.db.create_component("Child mid", product_id=product_id, node_type="Intermediate")
        self.db.delete_product(product_id)
        self.assertEqual(self.db.get_components_by_product(product_id), [])


class ColorOperationTests(DatabaseTestCase):
    """create/get/delete color."""

    def test_create_and_get_color(self):
        color_id = self.db.create_color("TestTeal", "#008080", 0, 128, 128)
        color = self.db.get_color(color_id)
        self.assertEqual(color["name"], "TestTeal")
        self.assertEqual(color["hex_code"], "#008080")
        self.assertEqual((color["rgb_r"], color["rgb_g"], color["rgb_b"]), (0, 128, 128))

    def test_get_color_missing_returns_none(self):
        self.assertIsNone(self.db.get_color(9999))

    def test_duplicate_color_name_raises(self):
        self.db.create_color("Unique", "#111111")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.create_color("Unique", "#222222")

    def test_get_all_colors_sorted_by_name(self):
        colors = self.db.get_all_colors()
        names = [c["name"] for c in colors]
        self.assertEqual(names, sorted(names))

    def test_delete_color(self):
        color_id = self.db.create_color("Doomed", "#123456")
        self.assertTrue(self.db.delete_color(color_id))
        self.assertIsNone(self.db.get_color(color_id))

    def test_delete_color_missing_returns_false(self):
        self.assertFalse(self.db.delete_color(9999))

    def test_delete_color_sets_material_color_to_null(self):
        color_id = self.db.create_color("MatColor", "#101010")
        material_id = self.db.create_material("ColoredMat", color_id=color_id)
        self.db.delete_color(color_id)
        material = self.db.get_material(material_id)
        self.assertIsNone(material["color_id"])


class MaterialOperationTests(DatabaseTestCase):
    """create/get/update/delete material."""

    def test_create_and_get_material(self):
        material_id = self.db.create_material("Steel", scientific_name="Fe/C")
        material = self.db.get_material(material_id)
        self.assertEqual(material["name"], "Steel")
        self.assertEqual(material["scientific_name"], "Fe/C")

    def test_get_material_missing_returns_none(self):
        self.assertIsNone(self.db.get_material(9999))

    def test_duplicate_material_name_raises(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.create_material("Plastic")  # default material already exists

    def test_get_all_materials_puts_other_last(self):
        self.db.create_material("Zinc")  # would sort after 'Other' alphabetically
        materials = self.db.get_all_materials()
        self.assertEqual(materials[-1]["name"], "Other")

    def test_update_material(self):
        material_id = self.db.create_material("Alu")
        self.assertTrue(self.db.update_material(material_id, name="Aluminium"))
        self.assertEqual(self.db.get_material(material_id)["name"], "Aluminium")

    def test_update_material_no_valid_fields_returns_false(self):
        material_id = self.db.create_material("M1")
        self.assertFalse(self.db.update_material(material_id, bogus="x"))

    def test_delete_material(self):
        material_id = self.db.create_material("Temp")
        self.assertTrue(self.db.delete_material(material_id))
        self.assertIsNone(self.db.get_material(material_id))


class ComponentIdEncodingTests(DatabaseTestCase):
    """_encode_component_id / _decode_component_id."""

    def test_root_encoding_is_identity(self):
        self.assertEqual(self.db._encode_component_id("root_component", 5), 5)

    def test_intermediate_encoding_roundtrip(self):
        encoded = self.db._encode_component_id("intermediate_component", 5)
        self.assertEqual(encoded, 1_000_005)
        self.assertEqual(self.db._decode_component_id(encoded),
                         ("intermediate_component", 5))

    def test_leaf_encoding_roundtrip(self):
        encoded = self.db._encode_component_id("leaf_component", 7)
        self.assertEqual(encoded, 2_000_007)
        self.assertEqual(self.db._decode_component_id(encoded), ("leaf_component", 7))

    def test_decode_root(self):
        self.assertEqual(self.db._decode_component_id(3), ("root_component", 3))

    def test_encode_unknown_table_raises(self):
        with self.assertRaises(ValueError):
            self.db._encode_component_id("not_a_table", 1)


class ComponentOperationTests(DatabaseTestCase):
    """create/get/update/delete component across the three tables."""

    def setUp(self):
        super().setUp()
        self.product_id = self.db.create_product("Product")

    def test_create_root_component(self):
        comp_id = self.db.create_component("Root comp", node_type="Root")
        self.assertLess(comp_id, self.db._INTERMEDIATE_OFFSET)
        comp = self.db.get_component(comp_id)
        self.assertEqual(comp["node_type"], "Root")
        self.assertEqual(comp["source_table"], "root_component")

    def test_create_intermediate_component(self):
        comp_id = self.db.create_component("Mid", product_id=self.product_id,
                                           node_type="Intermediate")
        self.assertGreaterEqual(comp_id, self.db._INTERMEDIATE_OFFSET)
        self.assertLess(comp_id, self.db._LEAF_OFFSET)
        self.assertEqual(self.db.get_component(comp_id)["node_type"], "Intermediate")

    def test_create_leaf_component(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.assertGreaterEqual(comp_id, self.db._LEAF_OFFSET)
        self.assertEqual(self.db.get_component(comp_id)["node_type"], "Leaf")

    def test_create_child_without_product_raises(self):
        with self.assertRaises(ValueError):
            self.db.create_component("Orphan", node_type="Leaf")

    def test_unknown_node_type_defaults_to_intermediate(self):
        comp_id = self.db.create_component("What", product_id=self.product_id,
                                           node_type="banana")
        self.assertEqual(self.db.get_component(comp_id)["node_type"], "Intermediate")

    def test_get_component_includes_color_and_material_names(self):
        color_id = self.db.create_color("CompColor", "#0F0F0F")
        material_id = self.db.create_material("CompMat")
        comp_id = self.db.create_component("Styled", product_id=self.product_id,
                                           color_id=color_id, material_id=material_id,
                                           node_type="Leaf")
        comp = self.db.get_component(comp_id)
        self.assertEqual(comp["color_name"], "CompColor")
        self.assertEqual(comp["material_name"], "CompMat")

    def test_get_component_missing_returns_none(self):
        self.assertIsNone(self.db.get_component(2_009_999))

    def test_get_components_by_product(self):
        self.db.create_component("Mid", product_id=self.product_id, node_type="Intermediate")
        self.db.create_component("Leaf", product_id=self.product_id, node_type="Leaf")
        comps = self.db.get_components_by_product(self.product_id)
        self.assertEqual(len(comps), 2)
        tables = {c["source_table"] for c in comps}
        self.assertEqual(tables, {"intermediate_component", "leaf_component"})

    def test_get_root_component(self):
        root = self.db.get_root_component(self.product_id)
        self.assertEqual(root["name"], "Product")

    def test_update_component_basic(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.assertTrue(self.db.update_component(comp_id, name="Renamed leaf"))
        self.assertEqual(self.db.get_component(comp_id)["name"], "Renamed leaf")

    def test_update_component_normalizes_weight_string(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.db.update_component(comp_id, weight="12.5")
        self.assertEqual(self.db.get_component(comp_id)["weight"], 12.5)

    def test_update_component_empty_fk_becomes_null(self):
        color_id = self.db.create_color("Temp color", "#0A0A0A")
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           color_id=color_id, node_type="Leaf")
        self.db.update_component(comp_id, color_id="")
        self.assertIsNone(self.db.get_component(comp_id)["color_id"])

    def test_update_component_no_valid_fields_returns_false(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.assertFalse(self.db.update_component(comp_id, bogus="x"))

    def test_delete_component(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.assertTrue(self.db.delete_component(comp_id))
        self.assertIsNone(self.db.get_component(comp_id))

    def test_get_component_root_component_id(self):
        comp_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        self.assertEqual(self.db.get_component_root_component_id(comp_id),
                         self.product_id)
        # A root component resolves to itself.
        self.assertEqual(self.db.get_component_root_component_id(self.product_id),
                         self.product_id)


class StepOperationTests(DatabaseTestCase):
    """create/get/update/delete disassembly steps and step ordering."""

    def setUp(self):
        super().setUp()
        self.product_id = self.db.create_product("Product")

    def test_create_and_get_step(self):
        step_id = self.db.create_step(self.product_id, step_order=1,
                                      title="Open case", description="Remove screws")
        step = self.db.get_step(step_id)
        self.assertEqual(step["title"], "Open case")
        self.assertEqual(step["step_order"], 1)
        self.assertEqual(step["input_root_component_id"], self.product_id)

    def test_create_step_for_intermediate_component(self):
        comp_id = self.db.create_component("Mid", product_id=self.product_id,
                                           node_type="Intermediate")
        step_id = self.db.create_step(comp_id, step_order=1)
        step = self.db.get_step(step_id)
        self.assertIsNone(step["input_root_component_id"])
        self.assertIsNotNone(step["input_intermediate_component_id"])

    def test_create_step_with_action_links_action(self):
        action_id = self.db.create_action("Unscrew")
        step_id = self.db.create_step(self.product_id, step_order=1, action_id=action_id)
        self.assertEqual(self.db.get_next_action_order(step_id), 2)

    def test_get_step_missing_returns_none(self):
        self.assertIsNone(self.db.get_step(9999))

    def test_get_next_step_order_starts_at_one(self):
        self.assertEqual(self.db.get_next_step_order(self.product_id), 1)

    def test_get_next_step_order_increments(self):
        self.db.create_step(self.product_id, step_order=1)
        self.assertEqual(self.db.get_next_step_order(self.product_id), 2)

    def test_duplicate_step_order_same_input_raises(self):
        self.db.create_step(self.product_id, step_order=1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.create_step(self.product_id, step_order=1)

    def test_get_step_for_component(self):
        step_id = self.db.create_step(self.product_id, step_order=1, title="S")
        step = self.db.get_step_for_component(self.product_id)
        self.assertEqual(step["id"], step_id)

    def test_update_step_title(self):
        step_id = self.db.create_step(self.product_id, step_order=1, title="Old")
        self.assertTrue(self.db.update_step(step_id, title="New"))
        self.assertEqual(self.db.get_step(step_id)["title"], "New")

    def test_update_step_reassigns_input_component(self):
        comp_id = self.db.create_component("Mid", product_id=self.product_id,
                                           node_type="Intermediate")
        step_id = self.db.create_step(self.product_id, step_order=1)
        self.db.update_step(step_id, component_id=comp_id)
        step = self.db.get_step(step_id)
        self.assertIsNone(step["input_root_component_id"])
        self.assertIsNotNone(step["input_intermediate_component_id"])

    def test_update_step_no_valid_fields_returns_false(self):
        step_id = self.db.create_step(self.product_id, step_order=1)
        self.assertFalse(self.db.update_step(step_id, bogus="x"))

    def test_delete_step(self):
        step_id = self.db.create_step(self.product_id, step_order=1)
        self.assertTrue(self.db.delete_step(step_id))
        self.assertIsNone(self.db.get_step(step_id))

    def test_get_step_root_component_id_for_root_input(self):
        step_id = self.db.create_step(self.product_id, step_order=1)
        self.assertEqual(self.db.get_step_root_component_id(step_id), self.product_id)

    def test_get_step_root_component_id_for_leaf_input(self):
        leaf_id = self.db.create_component("Leaf", product_id=self.product_id,
                                           node_type="Leaf")
        step_id = self.db.create_step(leaf_id, step_order=1)
        self.assertEqual(self.db.get_step_root_component_id(step_id), self.product_id)

    def test_get_step_root_component_id_missing_step(self):
        self.assertIsNone(self.db.get_step_root_component_id(9999))


class StepActionLinkTests(DatabaseTestCase):
    """add_action_to_step / get_next_action_order."""

    def setUp(self):
        super().setUp()
        self.product_id = self.db.create_product("Product")
        self.step_id = self.db.create_step(self.product_id, step_order=1)

    def test_link_action_appends_order(self):
        a1 = self.db.create_action("First")
        a2 = self.db.create_action("Second")
        r1 = self.db.add_action_to_step(self.step_id, a1)
        r2 = self.db.add_action_to_step(self.step_id, a2)
        self.assertEqual(r1["action_order"], 1)
        self.assertEqual(r2["action_order"], 2)
        self.assertFalse(r1["already_linked"])

    def test_link_same_action_twice_reports_already_linked(self):
        action_id = self.db.create_action("Once")
        first = self.db.add_action_to_step(self.step_id, action_id)
        second = self.db.add_action_to_step(self.step_id, action_id)
        self.assertTrue(second["already_linked"])
        self.assertEqual(second["link_id"], first["link_id"])
        self.assertEqual(second["action_order"], first["action_order"])

    def test_get_next_action_order_empty_step(self):
        self.assertEqual(self.db.get_next_action_order(self.step_id), 1)


class StepOutputTests(DatabaseTestCase):
    """add/get/remove step output components."""

    def setUp(self):
        super().setUp()
        self.product_id = self.db.create_product("Product")
        self.step_id = self.db.create_step(self.product_id, step_order=1)
        self.mid_id = self.db.create_component("Mid", product_id=self.product_id,
                                               node_type="Intermediate")
        self.leaf_id = self.db.create_component("Leaf", product_id=self.product_id,
                                                node_type="Leaf")

    def test_add_intermediate_output(self):
        result = self.db.add_component_to_step(self.step_id, self.mid_id)
        self.assertFalse(result["already_linked"])

    def test_add_leaf_output(self):
        result = self.db.add_component_to_step(self.step_id, self.leaf_id)
        self.assertFalse(result["already_linked"])

    def test_add_duplicate_output_reports_already_linked(self):
        self.db.add_component_to_step(self.step_id, self.leaf_id)
        result = self.db.add_component_to_step(self.step_id, self.leaf_id)
        self.assertTrue(result["already_linked"])

    def test_root_component_cannot_be_output(self):
        with self.assertRaises(ValueError):
            self.db.add_component_to_step(self.step_id, self.product_id)

    def test_output_from_another_root_rejected(self):
        other_product = self.db.create_product("Other")
        foreign_leaf = self.db.create_component("Foreign", product_id=other_product,
                                                node_type="Leaf")
        with self.assertRaises(ValueError):
            self.db.add_component_to_step(self.step_id, foreign_leaf)

    def test_get_components_from_step(self):
        self.db.add_component_to_step(self.step_id, self.mid_id)
        self.db.add_component_to_step(self.step_id, self.leaf_id)
        outputs = self.db.get_components_from_step(self.step_id)
        self.assertEqual({c["id"] for c in outputs}, {self.mid_id, self.leaf_id})

    def test_remove_component_from_step(self):
        self.db.add_component_to_step(self.step_id, self.leaf_id)
        self.assertTrue(self.db.remove_component_from_step(self.step_id, self.leaf_id))
        self.assertEqual(self.db.get_components_from_step(self.step_id), [])

    def test_remove_component_not_linked_returns_false(self):
        self.assertFalse(self.db.remove_component_from_step(self.step_id, self.leaf_id))

    def test_remove_root_component_returns_false(self):
        self.assertFalse(self.db.remove_component_from_step(self.step_id, self.product_id))


class ActionOperationTests(DatabaseTestCase):
    """create/get/update/delete actions."""

    def test_create_and_get_action(self):
        tool_id = self.db.create_tool("Screwdriver", "Hand tool")
        action_id = self.db.create_action("Unscrew", description="Turn left",
                                          tool_id=tool_id)
        action = self.db.get_action(action_id)
        self.assertEqual(action["name"], "Unscrew")
        self.assertEqual(action["tool_name"], "Screwdriver")
        self.assertEqual(action["tool_category"], "Hand tool")

    def test_get_action_missing_returns_none(self):
        self.assertIsNone(self.db.get_action(9999))

    def test_get_action_chain(self):
        action_id = self.db.create_action("Head")
        chain = self.db.get_action_chain(action_id)
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["id"], action_id)
        self.assertEqual(self.db.get_action_chain(9999), [])

    def test_update_action(self):
        action_id = self.db.create_action("Old")
        self.assertTrue(self.db.update_action(action_id, name="New",
                                              description="desc"))
        action = self.db.get_action(action_id)
        self.assertEqual(action["name"], "New")
        self.assertEqual(action["description"], "desc")

    def test_update_action_no_valid_fields_returns_false(self):
        action_id = self.db.create_action("A")
        self.assertFalse(self.db.update_action(action_id, bogus="x"))

    def test_delete_action(self):
        action_id = self.db.create_action("Doomed")
        self.assertTrue(self.db.delete_action(action_id))
        self.assertIsNone(self.db.get_action(action_id))


class ToolOperationTests(DatabaseTestCase):
    """create/get/delete tools."""

    def test_create_and_get_tool(self):
        tool_id = self.db.create_tool("T20 Torx", "Screwdriver")
        tool = self.db.get_tool(tool_id)
        self.assertEqual(tool["name"], "T20 Torx")
        self.assertEqual(tool["category"], "Screwdriver")

    def test_create_duplicate_tool_returns_existing_id(self):
        first = self.db.create_tool("Hammer", "Hand tool")
        second = self.db.create_tool("Hammer", "Different category")
        self.assertEqual(first, second)

    def test_get_tool_missing_returns_none(self):
        self.assertIsNone(self.db.get_tool(9999))

    def test_get_all_tools(self):
        self.db.create_tool("Wrench", "B-cat")
        self.db.create_tool("Pliers", "A-cat")
        tools = self.db.get_all_tools()
        self.assertEqual(len(tools), 2)
        # Ordered by category then name.
        self.assertEqual(tools[0]["name"], "Pliers")

    def test_delete_tool(self):
        tool_id = self.db.create_tool("Doomed")
        self.assertTrue(self.db.delete_tool(tool_id))
        self.assertIsNone(self.db.get_tool(tool_id))

    def test_delete_tool_sets_action_tool_to_null(self):
        tool_id = self.db.create_tool("Linked")
        action_id = self.db.create_action("Act", tool_id=tool_id)
        self.db.delete_tool(tool_id)
        self.assertIsNone(self.db.get_action(action_id)["tool_id"])


class SchemaFieldTests(DatabaseTestCase):
    """Dynamic UI schema helpers."""

    def test_get_table_schema_returns_columns(self):
        columns = self.db.get_table_schema("color")
        names = {c["name"] for c in columns}
        self.assertEqual(names, {"id", "name", "hex_code", "rgb_r", "rgb_g", "rgb_b"})
        id_col = next(c for c in columns if c["name"] == "id")
        self.assertTrue(id_col["pk"])

    def test_get_component_fields_excludes_internal_columns(self):
        for kind in ("root", "intermediate", "leaf"):
            names = {c["name"] for c in self.db.get_component_fields(kind)}
            self.assertNotIn("id", names)
            self.assertIn("name", names)

    def test_get_component_fields_dropdowns(self):
        fields = {c["name"]: c for c in self.db.get_component_fields("leaf")}
        self.assertEqual(fields["color_id"]["widget_type"], "dropdown")
        self.assertEqual(fields["color_id"]["display_name"], "Color")
        self.assertEqual(fields["material_id"]["widget_type"], "dropdown")

    def test_get_product_fields_excludes_timestamps(self):
        names = {c["name"] for c in self.db.get_product_fields()}
        self.assertNotIn("created_at", names)
        self.assertNotIn("modified_at", names)
        self.assertNotIn("node_type", names)
        self.assertIn("brand", names)

    def test_get_action_fields(self):
        fields = {c["name"]: c for c in self.db.get_action_fields()}
        self.assertNotIn("id", fields)
        self.assertEqual(fields["tool_id"]["display_name"], "Tool")

    def test_get_step_fields_excludes_inputs_and_order(self):
        names = {c["name"] for c in self.db.get_step_fields()}
        self.assertNotIn("step_order", names)
        self.assertNotIn("input_root_component_id", names)
        self.assertIn("title", names)

    def test_get_material_fields(self):
        fields = {c["name"]: c for c in self.db.get_material_fields()}
        self.assertNotIn("id", fields)
        self.assertEqual(fields["color_id"]["widget_type"], "dropdown")


class StatisticsTests(DatabaseTestCase):

    def test_statistics_counts_rows(self):
        stats = self.db.get_statistics()
        self.assertEqual(stats["color"], 15)
        self.assertEqual(stats["material"], 9)
        self.assertEqual(stats["root_component"], 0)

        self.db.create_product("P")
        self.assertEqual(self.db.get_statistics()["root_component"], 1)


class GetDatabaseSingletonTests(unittest.TestCase):
    """get_database convenience function."""

    def setUp(self):
        self._original = database._default_db
        database._default_db = None
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        fd, self.other_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        database._default_db = self._original
        for path in (self.db_path, self.other_path):
            if os.path.exists(path):
                os.remove(path)

    def test_returns_same_instance_for_same_path(self):
        db1 = get_database(self.db_path)
        db2 = get_database(self.db_path)
        self.assertIs(db1, db2)

    def test_new_instance_for_different_path(self):
        db1 = get_database(self.db_path)
        db2 = get_database(self.other_path)
        self.assertIsNot(db1, db2)
        self.assertEqual(db2.db_path, self.other_path)


if __name__ == "__main__":
    unittest.main()
