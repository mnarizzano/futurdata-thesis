"""
SQLite Database Module for Disassembly Flow Diagram Builder

Schema:
- root_component: Root product definition
- color: Color catalog with RGB values
- material: Material catalog for components
- intermediate_component: Mid-level components
- leaf_component: Leaf components
- disassembly_step: Steps to disassemble components
- disassembly_step_action: Ordered actions in a step
- step_output_intermediate: Step outputs for intermediate components
- step_output_leaf: Step outputs for leaf components
- action: Activities in a step
- tool: Tools used in actions
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """Manages SQLite database operations for the diagram application."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".disassembly_diagram")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "disassembly_flow.db")

        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

            # ==================== COLOR TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS color (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    hex_code VARCHAR(7) NOT NULL,
                    rgb_r INTEGER,
                    rgb_g INTEGER,
                    rgb_b INTEGER
                )
            ''')
            
            # ==================== MATERIAL TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    scientific_name VARCHAR(50),
                    color_id INTEGER,
                    FOREIGN KEY (color_id) REFERENCES color(id) ON DELETE SET NULL
                )
            ''')

            # ==================== TOOL TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    category VARCHAR(50)
                )
            ''')

            # ==================== ACTION TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    tool_id INTEGER,
                    image_path VARCHAR(500),
                    FOREIGN KEY (tool_id) REFERENCES tool(id) ON DELETE SET NULL
                )
            ''')

            # ==================== ROOT COMPONENT (PRODUCT) TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS root_component (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    brand VARCHAR(100),
                    model VARCHAR(100),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    color_id INTEGER,
                    material_id INTEGER,
                    weight DECIMAL,
                    weight_unit VARCHAR(10) DEFAULT 'g',
                    node_type VARCHAR(20) DEFAULT 'Root',
                    image_path VARCHAR(500),
                    FOREIGN KEY (color_id) REFERENCES color(id) ON DELETE SET NULL,
                    FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE SET NULL
                )
            ''')

            # ==================== INTERMEDIATE COMPONENT TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS intermediate_component (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_component_id INTEGER NOT NULL,
                    color_id INTEGER,
                    material_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    weight DECIMAL,
                    weight_unit VARCHAR(10) DEFAULT 'g',
                    node_type VARCHAR(20) DEFAULT 'Intermediate',
                    image_path VARCHAR(500),
                    FOREIGN KEY (root_component_id) REFERENCES root_component(id) ON DELETE CASCADE,
                    FOREIGN KEY (color_id) REFERENCES color(id) ON DELETE SET NULL,
                    FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE SET NULL
                )
            ''')

            # ==================== LEAF COMPONENT TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leaf_component (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_component_id INTEGER NOT NULL,
                    color_id INTEGER,
                    material_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    weight DECIMAL,
                    weight_unit VARCHAR(10) DEFAULT 'g',
                    node_type VARCHAR(20) DEFAULT 'Leaf',
                    image_path VARCHAR(500),
                    FOREIGN KEY (root_component_id) REFERENCES root_component(id) ON DELETE CASCADE,
                    FOREIGN KEY (color_id) REFERENCES color(id) ON DELETE SET NULL,
                    FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE SET NULL
                )
            ''')

            # ==================== DISASSEMBLY STEP TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disassembly_step (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_root_component_id INTEGER,
                    input_intermediate_component_id INTEGER,
                    input_leaf_component_id INTEGER,
                    step_order INTEGER NOT NULL,
                    title VARCHAR(255),
                    description TEXT,
                    image_path VARCHAR(500),
                    FOREIGN KEY (input_root_component_id) REFERENCES root_component(id) ON DELETE CASCADE,
                    FOREIGN KEY (input_intermediate_component_id) REFERENCES intermediate_component(id) ON DELETE CASCADE,
                    FOREIGN KEY (input_leaf_component_id) REFERENCES leaf_component(id) ON DELETE CASCADE,
                    CHECK (
                        (CASE WHEN input_root_component_id IS NOT NULL THEN 1 ELSE 0 END) +
                        (CASE WHEN input_intermediate_component_id IS NOT NULL THEN 1 ELSE 0 END) +
                        (CASE WHEN input_leaf_component_id IS NOT NULL THEN 1 ELSE 0 END)
                        = 1
                    )
                )
            ''')

            # ==================== DISASSEMBLY STEP ACTION TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disassembly_step_action (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disassembly_step_id INTEGER NOT NULL,
                    action_id INTEGER NOT NULL,
                    action_order INTEGER NOT NULL,
                    FOREIGN KEY (disassembly_step_id) REFERENCES disassembly_step(id) ON DELETE CASCADE,
                    FOREIGN KEY (action_id) REFERENCES action(id) ON DELETE CASCADE
                )
            ''')

            # ==================== STEP OUTPUT INTERMEDIATE TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS step_output_intermediate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disassembly_step_id INTEGER NOT NULL,
                    intermediate_component_id INTEGER NOT NULL,
                    FOREIGN KEY (disassembly_step_id) REFERENCES disassembly_step(id) ON DELETE CASCADE,
                    FOREIGN KEY (intermediate_component_id) REFERENCES intermediate_component(id) ON DELETE CASCADE
                )
            ''')

            # ==================== STEP OUTPUT LEAF TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS step_output_leaf (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disassembly_step_id INTEGER NOT NULL,
                    leaf_component_id INTEGER NOT NULL,
                    FOREIGN KEY (disassembly_step_id) REFERENCES disassembly_step(id) ON DELETE CASCADE,
                    FOREIGN KEY (leaf_component_id) REFERENCES leaf_component(id) ON DELETE CASCADE
                )
            ''')

            # ==================== INDEXES ====================
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_material_color ON material(color_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_root_component_color ON root_component(color_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_root_component_material ON root_component(material_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_intermediate_root ON intermediate_component(root_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_intermediate_color ON intermediate_component(color_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_intermediate_material ON intermediate_component(material_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_leaf_root ON leaf_component(root_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_leaf_color ON leaf_component(color_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_leaf_material ON leaf_component(material_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_input_root ON disassembly_step(input_root_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_input_intermediate ON disassembly_step(input_intermediate_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_input_leaf ON disassembly_step(input_leaf_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_action_step ON disassembly_step_action(disassembly_step_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_action_action ON disassembly_step_action(action_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_output_intermediate_step ON step_output_intermediate(disassembly_step_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_output_intermediate_component ON step_output_intermediate(intermediate_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_output_leaf_step ON step_output_leaf(disassembly_step_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_output_leaf_component ON step_output_leaf(leaf_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_tool ON action(tool_id)')

            # ==================== UNIQUENESS CONSTRAINTS ====================
            # One step cannot have two actions with the same order.
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_action_order
                ON disassembly_step_action(disassembly_step_id, action_order)
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_action_unique
                ON disassembly_step_action(disassembly_step_id, action_id)
            ''')
            # Prevent duplicate output component links for a step.
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_out_inter
                ON step_output_intermediate(disassembly_step_id, intermediate_component_id)
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_out_leaf
                ON step_output_leaf(disassembly_step_id, leaf_component_id)
            ''')
            # Enforce unique step order per specific input component type.
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_order_root
                ON disassembly_step(input_root_component_id, step_order)
                WHERE input_root_component_id IS NOT NULL
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_order_intermediate
                ON disassembly_step(input_intermediate_component_id, step_order)
                WHERE input_intermediate_component_id IS NOT NULL
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS uq_step_order_leaf
                ON disassembly_step(input_leaf_component_id, step_order)
                WHERE input_leaf_component_id IS NOT NULL
            ''')

            # ==================== INSERT DEFAULT DATA ====================
            self._insert_default_colors(cursor)
            self._insert_default_materials(cursor)
            
            # ==================== MIGRATIONS ====================
            self._migrate_add_image_path(cursor)

    def _migrate_add_image_path(self, cursor):
        """Migration: Add image_path column to existing tables."""
        tables = ['action', 'root_component', 'intermediate_component', 'leaf_component']
        for table in tables:
            try:
                # Check if column exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                if 'image_path' not in columns:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN image_path VARCHAR(500)')
            except Exception:
                pass  # Column might already exist or table doesn't exist

    def _insert_default_colors(self, cursor):
        """Insert default colors if not exist."""
        default_colors = [
            ('Red', '#FF0000', 255, 0, 0),
            ('Green', '#00FF00', 0, 255, 0),
            ('Blue', '#0000FF', 0, 0, 255),
            ('Black', '#000000', 0, 0, 0),
            ('White', '#FFFFFF', 255, 255, 255),
            ('Yellow', '#FFFF00', 255, 255, 0),
            ('Orange', '#FFA500', 255, 165, 0),
            ('Gray', '#808080', 128, 128, 128),
            ('Silver', '#C0C0C0', 192, 192, 192),
            ('Brown', '#8B4513', 139, 69, 19),
            ('Pink', '#FFC0CB', 255, 192, 203),
            ('Purple', '#800080', 128, 0, 128),
            ('Cyan', '#00FFFF', 0, 255, 255),
            ('Gold', '#FFD700', 255, 215, 0),
            ('Transparent', '#000000', 0, 0, 0),
        ]

        for name, hex_code, r, g, b in default_colors:
            cursor.execute('''
                INSERT OR IGNORE INTO color (name, hex_code, rgb_r, rgb_g, rgb_b)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, hex_code, r, g, b))

    def _insert_default_materials(self, cursor):
        """Insert default materials if not exist."""
        default_materials = [
            ("Plastic", "PC", None),
            ("Metal", "N/A", None),
            ("Glass", "N/A", None),
            ("Rubber", "N/A", None),
            ("Wood", "N/A", None),
            ("Composite", "N/A", None),
            ("Ceramic", "N/A", None),
            ("PCB", "N/A", None),
            ("Other", "N/A", None),
        ]

        for name, scientific_name, color_id in default_materials:
            cursor.execute('''
                INSERT OR IGNORE INTO material (name, scientific_name, color_id)
                VALUES (?, ?, ?)
            ''', (name, scientific_name, color_id))

    # ==================== PRODUCT OPERATIONS ====================
    _INTERMEDIATE_OFFSET = 1_000_000
    _LEAF_OFFSET = 2_000_000

    def _encode_component_id(self, table_name: str, row_id: int) -> int:
        if table_name == "root_component":
            return row_id
        if table_name == "intermediate_component":
            return self._INTERMEDIATE_OFFSET + row_id
        if table_name == "leaf_component":
            return self._LEAF_OFFSET + row_id
        raise ValueError(f"Unsupported component table: {table_name}")

    def _decode_component_id(self, component_id: int) -> Tuple[str, int]:
        if component_id >= self._LEAF_OFFSET:
            return "leaf_component", component_id - self._LEAF_OFFSET
        if component_id >= self._INTERMEDIATE_OFFSET:
            return "intermediate_component", component_id - self._INTERMEDIATE_OFFSET
        return "root_component", component_id

    def create_product(self, name: str, brand: str = "", model: str = "",
                       description: str = "", x: float = 400, y: float = 100) -> int:
        """Create a root component (product). Returns the product ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO root_component (name, brand, model, description, modified_at, node_type)
                VALUES (?, ?, ?, ?, ?, 'Root')
            ''', (name, brand, model, description, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get root product by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM root_component WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all root products."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM root_component ORDER BY modified_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update root product properties."""
        allowed = {'name', 'brand', 'model', 'description', 'color_id',
                   'material_id', 'weight', 'weight_unit', 'node_type', 'image_path'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        updates['modified_at'] = datetime.now().isoformat()
        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [product_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE root_component SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0

    def delete_product(self, product_id: int) -> bool:
        """Delete a root product and all related data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM root_component WHERE id = ?', (product_id,))
            return cursor.rowcount > 0

    # ==================== COLOR OPERATIONS ====================

    def get_all_colors(self) -> List[Dict[str, Any]]:
        """Get all colors for dropdown."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM color ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def get_color(self, color_id: int) -> Optional[Dict[str, Any]]:
        """Get a color by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM color WHERE id = ?', (color_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_color(self, name: str, hex_code: str, rgb_r: int = 0,
                     rgb_g: int = 0, rgb_b: int = 0) -> int:
        """Create a new color. Returns the color ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO color (name, hex_code, rgb_r, rgb_g, rgb_b)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, hex_code, rgb_r, rgb_g, rgb_b))
            return cursor.lastrowid

    # ==================== MATERIAL OPERATIONS ====================

    def create_material(self, name: str, scientific_name: str = "", color_id: int = None) -> int:
        """Create a material. Returns the material ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO material (name, scientific_name, color_id)
                VALUES (?, ?, ?)
            ''', (name, scientific_name, color_id))
            return cursor.lastrowid

    def get_material(self, material_id: int) -> Optional[Dict[str, Any]]:
        """Get a material by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM material WHERE id = ?', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_materials(self) -> List[Dict[str, Any]]:
        """Get all materials."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM material ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def update_material(self, material_id: int, **kwargs) -> bool:
        """Update material properties."""
        allowed = {'name', 'scientific_name', 'color_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [material_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE material SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0

    def delete_material(self, material_id: int) -> bool:
        """Delete a material."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM material WHERE id = ?', (material_id,))
            return cursor.rowcount > 0

    # ==================== COMPONENT OPERATIONS ====================

    def create_component(self, name: str, product_id: int = None, color_id: int = None,
                         material_id: int = None, weight: float = None, weight_unit: str = "g",
                         node_type: str = "", x: float = 0, y: float = 0) -> int:
        """Create component in root/intermediate/leaf tables; returns encoded component ID."""
        normalized = (node_type or "Intermediate").strip().lower()
        if normalized in ("root", "product"):
            table = "root_component"
        elif normalized in ("leaf",):
            table = "leaf_component"
        else:
            table = "intermediate_component"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if table == "root_component":
                cursor.execute('''
                    INSERT INTO root_component (
                        name, color_id, material_id, weight, weight_unit, node_type, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, color_id, material_id, weight, weight_unit, "Root", datetime.now().isoformat()))
            else:
                if product_id is None:
                    raise ValueError("product_id (root_component_id) is required for intermediate/leaf components")
                default_node = "Leaf" if table == "leaf_component" else "Intermediate"
                cursor.execute(f'''
                    INSERT INTO {table} (
                        root_component_id, color_id, material_id, name, weight, weight_unit, node_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, color_id, material_id, name, weight, weight_unit, default_node))
            return self._encode_component_id(table, cursor.lastrowid)

    def get_component(self, component_id: int) -> Optional[Dict[str, Any]]:
        """Get a component by encoded ID with color/material info."""
        table_name, row_id = self._decode_component_id(component_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT c.*,
                       col.name as color_name, col.hex_code,
                       mat.name as material_name, mat.scientific_name as material_scientific_name
                FROM {table_name} c
                LEFT JOIN color col ON c.color_id = col.id
                LEFT JOIN material mat ON c.material_id = mat.id
                WHERE c.id = ?
            ''', (row_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["id"] = component_id
            data["component_id"] = component_id
            data["source_table"] = table_name
            return data

    def get_components_by_product(self, product_id: int) -> List[Dict[str, Any]]:
        """Get all intermediate+leaf components for a root product."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            results: List[Dict[str, Any]] = []
            for table_name in ("intermediate_component", "leaf_component"):
                cursor.execute(f'''
                    SELECT c.*,
                           col.name as color_name, col.hex_code,
                           mat.name as material_name, mat.scientific_name as material_scientific_name
                    FROM {table_name} c
                    LEFT JOIN color col ON c.color_id = col.id
                    LEFT JOIN material mat ON c.material_id = mat.id
                    WHERE c.root_component_id = ?
                ''', (product_id,))
                rows = [dict(row) for row in cursor.fetchall()]
                for row in rows:
                    encoded = self._encode_component_id(table_name, row["id"])
                    row["id"] = encoded
                    row["component_id"] = encoded
                    row["source_table"] = table_name
                results.extend(rows)
            return results

    def get_root_component(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get root product component."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*,
                       col.name as color_name, col.hex_code,
                       mat.name as material_name, mat.scientific_name as material_scientific_name
                FROM root_component c
                LEFT JOIN color col ON c.color_id = col.id
                LEFT JOIN material mat ON c.material_id = mat.id
                WHERE c.id = ?
            ''', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_component(self, component_id: int, **kwargs) -> bool:
        """Update component properties."""
        table_name, row_id = self._decode_component_id(component_id)
        allowed = {'name', 'color_id', 'material_id', 'weight', 'weight_unit', 'node_type', 'image_path'}
        if table_name == "root_component":
            allowed.update({'brand', 'model', 'description'})
        else:
            allowed.add('root_component_id')
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Normalize UI values before sending them to SQLite.
        for fk_field in ('color_id', 'material_id'):
            if fk_field in updates:
                value = updates[fk_field]
                updates[fk_field] = int(value) if str(value).strip() else None

        if 'root_component_id' in updates:
            value = updates['root_component_id']
            updates['root_component_id'] = int(value) if str(value).strip() else None

        if 'weight' in updates:
            value = updates['weight']
            updates['weight'] = float(value) if str(value).strip() else None

        if table_name == "root_component":
            updates["modified_at"] = datetime.now().isoformat()

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [row_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE {table_name} SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0

    def delete_component(self, component_id: int) -> bool:
        """Delete a component."""
        table_name, row_id = self._decode_component_id(component_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (row_id,))
            return cursor.rowcount > 0

    # ==================== DISASSEMBLY_STEP OPERATIONS ====================

    def create_step(self, component_id: int, step_order: int, description: str = "",
                    image_path: str = "", action_id: int = None, title: str = "",
                    x: float = 0, y: float = 0) -> int:
        """Create a disassembly step. Returns the step ID."""
        table_name, row_id = self._decode_component_id(component_id)
        input_root_id = row_id if table_name == "root_component" else None
        input_intermediate_id = row_id if table_name == "intermediate_component" else None
        input_leaf_id = row_id if table_name == "leaf_component" else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO disassembly_step (
                    input_root_component_id, input_intermediate_component_id, input_leaf_component_id,
                    step_order, title, description, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (input_root_id, input_intermediate_id, input_leaf_id, step_order, title, description, image_path))
            step_id = cursor.lastrowid
            if action_id is not None:
                cursor.execute('''
                    INSERT INTO disassembly_step_action (disassembly_step_id, action_id, action_order)
                    VALUES (?, ?, 1)
                ''', (step_id, action_id))
            return step_id

    def get_next_step_order(self, component_id: int) -> int:
        """Get next step_order value for a specific input component."""
        table_name, row_id = self._decode_component_id(component_id)
        if table_name == "root_component":
            input_col = "input_root_component_id"
        elif table_name == "intermediate_component":
            input_col = "input_intermediate_component_id"
        else:
            input_col = "input_leaf_component_id"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'''
                SELECT COALESCE(MAX(step_order), 0) + 1
                FROM disassembly_step
                WHERE {input_col} = ?
                ''',
                (row_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 1

    def get_next_action_order(self, disassembly_step_id: int) -> int:
        """Get next action_order value for a specific step.

        Deletion does not renumber existing action_order values, so gaps are allowed.
        New actions always append at MAX(action_order) + 1.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COALESCE(MAX(action_order), 0) + 1
                FROM disassembly_step_action
                WHERE disassembly_step_id = ?
                ''',
                (disassembly_step_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 1

    def get_component_root_component_id(self, component_id: int) -> Optional[int]:
        """Resolve the owning root_component for any encoded component id."""
        table_name, row_id = self._decode_component_id(component_id)
        if table_name == "root_component":
            return row_id

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT root_component_id FROM {table_name} WHERE id = ?', (row_id,))
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    def get_step_root_component_id(self, disassembly_step_id: int) -> Optional[int]:
        """Resolve the owning root_component for a step based on its input component."""
        step = self.get_step(disassembly_step_id)
        if not step:
            return None

        if step.get('input_root_component_id') is not None:
            return int(step['input_root_component_id'])
        if step.get('input_intermediate_component_id') is not None:
            return self.get_component_root_component_id(
                self._encode_component_id("intermediate_component", int(step['input_intermediate_component_id']))
            )
        if step.get('input_leaf_component_id') is not None:
            return self.get_component_root_component_id(
                self._encode_component_id("leaf_component", int(step['input_leaf_component_id']))
            )
        return None

    def add_action_to_step(self, disassembly_step_id: int, action_id: int,
                           action_order: int = None) -> Dict[str, Any]:
        """
        Link an action to a step with ordering.
        Returns status dict with link_id, action_order, already_linked.

        Ordering policy is append-only: existing gaps are preserved and new links use
        MAX(action_order) + 1 for the step.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # If already linked, keep existing order.
            cursor.execute(
                '''
                SELECT id, action_order
                FROM disassembly_step_action
                WHERE disassembly_step_id = ? AND action_id = ?
                ''',
                (disassembly_step_id, action_id),
            )
            existing = cursor.fetchone()
            if existing:
                return {
                    "link_id": int(existing[0]),
                    "action_order": int(existing[1]),
                    "already_linked": True,
                }

            final_order = self.get_next_action_order(disassembly_step_id)
            cursor.execute(
                '''
                INSERT INTO disassembly_step_action (disassembly_step_id, action_id, action_order)
                VALUES (?, ?, ?)
                ''',
                (disassembly_step_id, action_id, final_order),
            )
            return {
                "link_id": int(cursor.lastrowid),
                "action_order": int(final_order),
                "already_linked": False,
            }

    def get_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        """Get a step by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM disassembly_step WHERE id = ?', (step_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_step_for_component(self, component_id: int) -> Optional[Dict[str, Any]]:
        """Get the disassembly step for a component (1:1)."""
        table_name, row_id = self._decode_component_id(component_id)
        if table_name == "root_component":
            where_clause = "input_root_component_id = ?"
        elif table_name == "intermediate_component":
            where_clause = "input_intermediate_component_id = ?"
        else:
            where_clause = "input_leaf_component_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM disassembly_step WHERE ''' + where_clause,
                (row_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_step(self, step_id: int, **kwargs) -> bool:
        """Update step properties."""
        allowed = {'component_id', 'step_order', 'title', 'description', 'image_path', 'action_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if "component_id" in updates:
                table_name, row_id = self._decode_component_id(updates.pop("component_id"))
                updates["input_root_component_id"] = row_id if table_name == "root_component" else None
                updates["input_intermediate_component_id"] = row_id if table_name == "intermediate_component" else None
                updates["input_leaf_component_id"] = row_id if table_name == "leaf_component" else None

            action_id = updates.pop("action_id", None)

            rowcount = 0
            if updates:
                set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
                values = list(updates.values()) + [step_id]
                cursor.execute(f'UPDATE disassembly_step SET {set_clause} WHERE id = ?', values)
                rowcount = cursor.rowcount

            if action_id is not None:
                cursor.execute('DELETE FROM disassembly_step_action WHERE disassembly_step_id = ?', (step_id,))
                cursor.execute('''
                    INSERT INTO disassembly_step_action (disassembly_step_id, action_id, action_order)
                    VALUES (?, ?, 1)
                ''', (step_id, action_id))
                rowcount = max(rowcount, 1)

            return rowcount > 0

    def delete_step(self, step_id: int) -> bool:
        """Delete a step."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM disassembly_step WHERE id = ?', (step_id,))
            return cursor.rowcount > 0

    # ==================== STEP OUTPUT OPERATIONS ====================

    def add_component_to_step(self, disassembly_step_id: int, component_id: int) -> Dict[str, Any]:
        """Add a component as output of a step (1:N relationship)."""
        table_name, row_id = self._decode_component_id(component_id)
        step_root_id = self.get_step_root_component_id(disassembly_step_id)
        component_root_id = self.get_component_root_component_id(component_id)
        if step_root_id is not None and component_root_id is not None and step_root_id != component_root_id:
            raise ValueError("Output component belongs to another root component")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if table_name == "intermediate_component":
                cursor.execute('''
                    SELECT id FROM step_output_intermediate
                    WHERE disassembly_step_id = ? AND intermediate_component_id = ?
                ''', (disassembly_step_id, row_id))
                existing = cursor.fetchone()
                if existing:
                    return {"link_id": int(existing[0]), "already_linked": True}
                cursor.execute('''
                    INSERT INTO step_output_intermediate (disassembly_step_id, intermediate_component_id)
                    VALUES (?, ?)
                ''', (disassembly_step_id, row_id))
                return {"link_id": int(cursor.lastrowid), "already_linked": False}
            elif table_name == "leaf_component":
                cursor.execute('''
                    SELECT id FROM step_output_leaf
                    WHERE disassembly_step_id = ? AND leaf_component_id = ?
                ''', (disassembly_step_id, row_id))
                existing = cursor.fetchone()
                if existing:
                    return {"link_id": int(existing[0]), "already_linked": True}
                cursor.execute('''
                    INSERT INTO step_output_leaf (disassembly_step_id, leaf_component_id)
                    VALUES (?, ?)
                ''', (disassembly_step_id, row_id))
                return {"link_id": int(cursor.lastrowid), "already_linked": False}
            else:
                raise ValueError("Root component cannot be an output component for a step")

    def get_components_from_step(self, disassembly_step_id: int) -> List[Dict[str, Any]]:
        """Get all components produced by a step (1:N)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            results: List[Dict[str, Any]] = []

            cursor.execute('''
                SELECT c.*,
                       col.name as color_name, col.hex_code,
                       mat.name as material_name, mat.scientific_name as material_scientific_name
                FROM intermediate_component c
                JOIN step_output_intermediate so ON c.id = so.intermediate_component_id
                LEFT JOIN color col ON c.color_id = col.id
                LEFT JOIN material mat ON c.material_id = mat.id
                WHERE so.disassembly_step_id = ?
            ''', (disassembly_step_id,))
            for row in cursor.fetchall():
                data = dict(row)
                data["id"] = self._encode_component_id("intermediate_component", data["id"])
                data["component_id"] = data["id"]
                data["source_table"] = "intermediate_component"
                results.append(data)

            cursor.execute('''
                SELECT c.*,
                       col.name as color_name, col.hex_code,
                       mat.name as material_name, mat.scientific_name as material_scientific_name
                FROM leaf_component c
                JOIN step_output_leaf so ON c.id = so.leaf_component_id
                LEFT JOIN color col ON c.color_id = col.id
                LEFT JOIN material mat ON c.material_id = mat.id
                WHERE so.disassembly_step_id = ?
            ''', (disassembly_step_id,))
            for row in cursor.fetchall():
                data = dict(row)
                data["id"] = self._encode_component_id("leaf_component", data["id"])
                data["component_id"] = data["id"]
                data["source_table"] = "leaf_component"
                results.append(data)

            return results

    def remove_component_from_step(self, disassembly_step_id: int, component_id: int) -> bool:
        """Remove a component from a step."""
        table_name, row_id = self._decode_component_id(component_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if table_name == "intermediate_component":
                cursor.execute('''
                    DELETE FROM step_output_intermediate
                    WHERE disassembly_step_id = ? AND intermediate_component_id = ?
                ''', (disassembly_step_id, row_id))
            elif table_name == "leaf_component":
                cursor.execute('''
                    DELETE FROM step_output_leaf
                    WHERE disassembly_step_id = ? AND leaf_component_id = ?
                ''', (disassembly_step_id, row_id))
            else:
                return False
            return cursor.rowcount > 0

    # ==================== ACTION OPERATIONS ====================

    def create_action(self, name: str, description: str = "", tool_id: int = None,
                      next_action_id: int = None, x: float = 0, y: float = 0) -> int:
        """Create an action. Returns the action ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO action (name, description, tool_id)
                VALUES (?, ?, ?)
            ''', (name, description, tool_id))
            return cursor.lastrowid

    def get_action(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Get an action by ID with tool info."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*, t.name as tool_name, t.category as tool_category
                FROM action a
                LEFT JOIN tool t ON a.tool_id = t.id
                WHERE a.id = ?
            ''', (action_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_action_chain(self, action_id: int) -> List[Dict[str, Any]]:
        """Compatibility helper: returns one action as chain head."""
        action = self.get_action(action_id)
        return [action] if action else []

    def update_action(self, action_id: int, **kwargs) -> bool:
        """Update action properties."""
        allowed = {'name', 'description', 'tool_id', 'image_path'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [action_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE action SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0

    def delete_action(self, action_id: int) -> bool:
        """Delete an action."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM action WHERE id = ?', (action_id,))
            return cursor.rowcount > 0

    # ==================== TOOL OPERATIONS ====================

    def create_tool(self, name: str, category: str = "") -> int:
        """Create a tool. Returns the tool ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO tool (name, category) VALUES (?, ?)
            ''', (name, category))
            if cursor.lastrowid:
                return cursor.lastrowid
            cursor.execute('SELECT id FROM tool WHERE name = ?', (name,))
            return cursor.fetchone()[0]

    def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get a tool by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tool WHERE id = ?', (tool_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tool ORDER BY category, name')
            return [dict(row) for row in cursor.fetchall()]

    def delete_tool(self, tool_id: int) -> bool:
        """Delete a tool."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tool WHERE id = ?', (tool_id,))
            return cursor.rowcount > 0

    # ==================== TABLE SCHEMA (for dynamic UI) ====================

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get the schema of a table for dynamic UI generation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': bool(row[3]),
                    'default': row[4],
                    'pk': bool(row[5])
                })
            return columns

    def get_component_fields(self, component_kind: str = "intermediate") -> List[Dict[str, Any]]:
        """Get editable fields for component tables (root/intermediate/leaf)."""
        kind = (component_kind or "intermediate").strip().lower()
        if kind == "root":
            table_name = "root_component"
            exclude = {'id', 'created_at', 'modified_at'}
        elif kind == "leaf":
            table_name = "leaf_component"
            exclude = {'id', 'root_component_id'}
        else:
            # Treat "composite" as intermediate in current schema.
            table_name = "intermediate_component"
            exclude = {'id', 'root_component_id'}

        all_columns = self.get_table_schema(table_name)

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                if col['name'] == 'color_id':
                    col['widget_type'] = 'dropdown'
                    col['display_name'] = 'Color'
                elif col['name'] == 'material_id':
                    col['widget_type'] = 'dropdown'
                    col['display_name'] = 'Material'
                editable_fields.append(col)
        return editable_fields

    def get_product_fields(self) -> List[Dict[str, Any]]:
        """Get editable fields for product table."""
        all_columns = self.get_table_schema('root_component')
        exclude = {'id', 'created_at', 'modified_at', 'node_type'}

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                editable_fields.append(col)
        return editable_fields

    def get_action_fields(self) -> List[Dict[str, Any]]:
        """Get editable fields for action table."""
        all_columns = self.get_table_schema('action')
        exclude = {'id'}

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                if col['name'] == 'tool_id':
                    col['widget_type'] = 'dropdown'
                    col['display_name'] = 'Tool'
                editable_fields.append(col)
        return editable_fields

    def get_step_fields(self) -> List[Dict[str, Any]]:
        """Get editable fields for disassembly_step table."""
        all_columns = self.get_table_schema('disassembly_step')
        # step_order is auto-managed by database, should not be editable
        exclude = {'id', 'input_root_component_id', 'input_intermediate_component_id', 
                   'input_leaf_component_id', 'step_order'}

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                if col['name'] == 'action_id':
                    col['widget_type'] = 'dropdown'
                    col['display_name'] = 'Action'
                editable_fields.append(col)
        return editable_fields
        
    def get_material_fields(self) -> List[Dict[str, Any]]:
        """Get editable fields for material table."""
        all_columns = self.get_table_schema('material')
        exclude = {'id'}

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                if col['name'] == 'color_id':
                    col['widget_type'] = 'dropdown'
                    col['display_name'] = 'Color'
                editable_fields.append(col)
        return editable_fields

    # ==================== STATISTICS ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}
            tables = [
                'color', 'material', 'tool', 'action', 'root_component',
                'intermediate_component', 'leaf_component', 'disassembly_step',
                'disassembly_step_action', 'step_output_intermediate', 'step_output_leaf'
            ]

            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[table] = cursor.fetchone()[0]

            return stats


# Convenience function
_default_db = None

def get_database(db_path: str = None) -> DatabaseManager:
    """Get or create the default database manager."""
    global _default_db
    if _default_db is None or (db_path and _default_db.db_path != db_path):
        _default_db = DatabaseManager(db_path)
    return _default_db
