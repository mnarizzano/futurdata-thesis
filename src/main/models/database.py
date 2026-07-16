"""
SQLite Database Module for ARIADNE Disassembly Workflow Diagram Builder

Schema:
- root_component: Root product definition and material selection
- color: Color catalog with RGB values for leaf sorting
- material: Material catalog and hierarchy for root components
- intermediate_component: Mid-level components
- leaf_component: Leaf components with color-based sorting
- disassembly_step: Steps to disassemble components
- disassembly_step_action: Ordered actions in a step
- step_output_intermediate: Step outputs for intermediate components
- step_output_leaf: Step outputs for leaf components
- action: Activities in a step
- tool: Tools used in actions
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """Manages SQLite database operations for the diagram application."""

    def __init__(self, db_path: str = None):
        """
        Initializes the DatabaseManager with a specific database filesystem path.

        If no custom file path is provided, it automatically provisions a hidden application 
        directory named '.disassembly_diagram' inside the user's home path, utilizing a default 
        file name 'disassembly_flow.db'.

        Args:
            db_path (str, optional): The absolute or relative filesystem path to the target 
                                     SQLite database file. Defaults to None.
        """
        if db_path is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".disassembly_diagram")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "disassembly_flow.db")

        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: An active and configured connection to the SQLite database.

        Raises:
            Exception: Re-raises any underlying execution exceptions encountered after executing a rollback.
        """
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
        """Initializes the database schema."""
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
            
            # ==================== MATERIAL CATEGORY TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_category (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE
                )
            ''')

            # ==================== MATERIAL SUBCATEGORY TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_subcategory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES material_category(id) ON DELETE CASCADE
                )
            ''')

            # ==================== MATERIAL TYPE TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_type (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    subcategory_id INTEGER,
                    name VARCHAR(100) NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES material_category(id) ON DELETE CASCADE,
                    FOREIGN KEY (subcategory_id) REFERENCES material_subcategory(id) ON DELETE CASCADE
                )
            ''')

            # ==================== MATERIAL TABLE ====================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER,
                    subcategory_id INTEGER,
                    type_id INTEGER,
                    name VARCHAR(100) NOT NULL,
                    scientific_name VARCHAR(255),
                    technical_name VARCHAR(255),
                    surface VARCHAR(100),
                    FOREIGN KEY (category_id) REFERENCES material_category(id) ON DELETE SET NULL,
                    FOREIGN KEY (subcategory_id) REFERENCES material_subcategory(id) ON DELETE SET NULL,
                    FOREIGN KEY (type_id) REFERENCES material_type(id) ON DELETE SET NULL
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
            self._migrate_material_structure(cursor)
            self._insert_default_material_categories(cursor)

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
                pass

    def _migrate_material_structure(self, cursor):
        """Migration: Add new columns to material table."""
        try:
            cursor.execute("PRAGMA table_info(material)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add new columns if they don't exist
            if 'category_id' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN category_id INTEGER')
            if 'subcategory_id' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN subcategory_id INTEGER')
            if 'type_id' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN type_id INTEGER')
            if 'scientific_name' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN scientific_name VARCHAR(255)')
            if 'technical_name' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN technical_name VARCHAR(255)')
            if 'surface' not in columns:
                cursor.execute('ALTER TABLE material ADD COLUMN surface VARCHAR(100)')
                
        except Exception as e:
            print(f"Migration error: {e}")
            pass

    def _insert_default_material_categories(self, cursor):
        """Insert default material categories, subcategories, and types."""
        try:
            # Check if categories already exist
            cursor.execute("SELECT COUNT(*) FROM material_category")
            if cursor.fetchone()[0] > 0:
                return  # Already populated
            
            # Insert categories
            categories = [
                'Plastic', 'Metal', 'Glass', 'Ceramic', 
                'Composite', 'Wood', 'Rubber', 'Textile'
            ]
            for cat in categories:
                cursor.execute('INSERT OR IGNORE INTO material_category (name) VALUES (?)', (cat,))
            
            # Insert subcategories
            subcategories = [
                (1, 'Thermoplastic'),   # Plastic
                (1, 'Thermoset'),
                (2, 'Ferrous'),         # Metal
                (2, 'Non-Ferrous'),
                (3, 'Tempered'),        # Glass
                (3, 'Laminated'),
                (4, 'Porcelain'),       # Ceramic
                (4, 'Earthenware'),
                (5, 'Fiber-Reinforced'),# Composite
                (5, 'Particle'),
                (6, 'Hardwood'),        # Wood
                (6, 'Softwood'),
                (7, 'Natural'),         # Rubber
                (7, 'Synthetic'),
                (8, 'Natural Fiber'),   # Textile
                (8, 'Synthetic Fiber'),
            ]
            for cat_id, subcat in subcategories:
                cursor.execute(
                    'INSERT OR IGNORE INTO material_subcategory (category_id, name) VALUES (?, ?)',
                    (cat_id, subcat)
                )
            
            # Insert sample types
            # Format: (category_id, subcategory_id, name)
            # subcategory_id = None means type is directly under category
            types = [
                # Plastic > Thermoplastic types
                (1, 1, 'ABS'),
                (1, 1, 'PET'),
                (1, 1, 'PP'),
                (1, 1, 'PVC'),
                # Plastic > Thermoset types
                (1, 2, 'Epoxy'),
                (1, 2, 'Polyester'),
                # Metal > Ferrous types
                (2, 3, 'Steel'),
                (2, 3, 'Cast Iron'),
                # Metal > Non-Ferrous types
                (2, 4, 'Aluminum'),
                (2, 4, 'Copper'),
                (2, 4, 'Brass'),
                # Metal direct types (no subcategory)
                (2, None, 'Titanium'),
            ]
            for cat_id, subcat_id, type_name in types:
                cursor.execute(
                    'INSERT OR IGNORE INTO material_type (category_id, subcategory_id, name) VALUES (?, ?, ?)',
                    (cat_id, subcat_id, type_name)
                )
        except Exception as e:
            print(f"Insert categories error: {e}")
            pass  # Column might already exist or table doesn't exist

    def _insert_default_colors(self, cursor):
        """
        Inserts default colors if they do not exist.
        Args:
            cursor (sqlite3.Cursor): An active database query cursor.
        """
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
        """
        Inserts default materials if not exist.
        
        Args:
            cursor (sqlite3.Cursor): An active database query cursor.
        """
        default_materials = [
            ("Plastic", "PC"),
            ("Metal", "N/A"),
            ("Glass", "N/A"),
            ("Rubber", "N/A"),
            ("Wood", "N/A"),
            ("Composite", "N/A"),
            ("Ceramic", "N/A"),
            ("PCB", "N/A"),
            ("Other", "N/A"),
        ]

        for name, scientific_name in default_materials:
            cursor.execute('''
                INSERT OR IGNORE INTO material (name, scientific_name, technical_name)
                VALUES (?, ?, ?)
            ''', (name, scientific_name, scientific_name))

    # ==================== PRODUCT OPERATIONS ====================
    _INTERMEDIATE_OFFSET = 1_000_000
    _LEAF_OFFSET = 2_000_000

    def _encode_component_id(self, table_name: str, row_id: int) -> int:
        """
        Encodes a database table row identifier into a globally unified, table-agnostic component ID.

        Applies specific virtual mathematical numeric offsets depending on the category of 
        the source table to maintain a collision-free ID schema inside application view modules.

        Args:
            table_name (str): Name of the component database table source.
            row_id (int): The absolute database primary integer key.

        Returns:
            int: The globally unique encoded integer component ID.

        Raises:
            ValueError: If an unsupported table mapping name is provided.
        """
        if table_name == "root_component":
            return row_id
        if table_name == "intermediate_component":
            return self._INTERMEDIATE_OFFSET + row_id
        if table_name == "leaf_component":
            return self._LEAF_OFFSET + row_id
        raise ValueError(f"Unsupported component table: {table_name}")

    def _decode_component_id(self, component_id: int) -> Tuple[str, int]:
        """
        Decodes a unified virtual component ID back into its physical table name and database row ID.

        Args:
            component_id (int): The encoded virtual component identifier.

        Returns:
            Tuple[str, int]: A mapping tuple containing the string database table name and target row ID.
        """
        if component_id >= self._LEAF_OFFSET:
            return "leaf_component", component_id - self._LEAF_OFFSET
        if component_id >= self._INTERMEDIATE_OFFSET:
            return "intermediate_component", component_id - self._INTERMEDIATE_OFFSET
        return "root_component", component_id

    def create_product(self, name: str, brand: str = "", model: str = "",
                       description: str = "", x: float = 400, y: float = 100) -> int:
        """
        Creates a root component (product) entry inside the database records.

        Args:
            name (str): Comprehensive title of the product.
            brand (str, optional): Brand or manufacturer tag. Defaults to "".
            model (str, optional): Model identification code. Defaults to "".
            description (str, optional): Verbose textual details. Defaults to "".
            x (float, optional): Initial visual canvas x-coordinate anchor. Defaults to 400.
            y (float, optional): Initial visual canvas y-coordinate anchor. Defaults to 100.

        Returns:
            int: The physical database row ID assigned to the new product record.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO root_component (name, brand, model, description, modified_at, node_type)
                VALUES (?, ?, ?, ?, ?, 'Root')
            ''', (name, brand, model, description, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets root product by ID.

        Args:
            product_id (int): The target primary key row ID.

        Returns:
            Optional[Dict[str, Any]]: Row representation data converted to a key-value dictionary 
                                      or None if no match is found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM root_component WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_products(self) -> List[Dict[str, Any]]:
        """
        Gets all root products sorted chronologically by modification date.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing every product root trace.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM root_component ORDER BY modified_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_product(self, product_id: int, **kwargs) -> bool:
        """
        Updates root product properties.

        Args:
            product_id (int): The structural root product target row ID.
            **kwargs: Dynamic keyword attributes matching valid columns inside 'root_component'.

        Returns:
            bool: True if an update affected one or more records successfully, False otherwise.
        """
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
        """
        Deletes a root product and all related data.

        Args:
            product_id (int): The target database product row entry to strip.

        Returns:
            bool: True if structural removal affected records, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM root_component WHERE id = ?', (product_id,))
            return cursor.rowcount > 0

    # ==================== COLOR OPERATIONS ====================

    def get_all_colors(self) -> List[Dict[str, Any]]:
        """
        Get all colors for dropdown.

        Returns:
            List[Dict[str, Any]]: List of dictionary rows detailing names, hex strings, and RGB metadata.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM color ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def get_color(self, color_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets a color by ID.
        Args:
            color_id (int): Target color entry key.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing the matching color fields, or None if missing.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM color WHERE id = ?', (color_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_color(self, name: str, hex_code: str, rgb_r: int = 0,
                     rgb_g: int = 0, rgb_b: int = 0) -> int:
        """Create a new color. Returns its color ID.
        
        Args:
            name (str): Display title for the color record.
            hex_code (str): Regular hex representation code string (e.g., '#FF0000').
            rgb_r (int, optional): Red standard integer metric component. Defaults to 0.
            rgb_g (int, optional): Green standard integer metric component. Defaults to 0.
            rgb_b (int, optional): Blue standard integer metric component. Defaults to 0.

        Returns:
            int: The primary key index allocated to the new color entry.
        """
        name = (name or "").strip()
        hex_code = (hex_code or "").strip()
        if not name:
            raise ValueError("Color name is required.")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hex_code):
            raise ValueError("Hex code must be in the format #RRGGBB.")
        for channel_name, channel_value in (("red", rgb_r), ("green", rgb_g), ("blue", rgb_b)):
            if not isinstance(channel_value, int) or not 0 <= channel_value <= 255:
                raise ValueError(f"{channel_name.capitalize()} channel must be an integer between 0 and 255.")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO color (name, hex_code, rgb_r, rgb_g, rgb_b)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, hex_code, rgb_r, rgb_g, rgb_b))
            return cursor.lastrowid

# ==================== MATERIAL CATEGORY OPERATIONS ====================

    def get_all_material_categories(self) -> List[Dict[str, Any]]:
        """Get all material categories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM material_category ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def create_material_category(self, name: str) -> int:
        """Create a material category. Returns the category ID."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Material category name is required.")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO material_category (name) VALUES (?)', (name,))
            return cursor.lastrowid

    # ==================== MATERIAL SUBCATEGORY OPERATIONS ====================

    def get_subcategories_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """Get all subcategories for a specific category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM material_subcategory 
                WHERE category_id = ? 
                ORDER BY name
            ''', (category_id,))
            return [dict(row) for row in cursor.fetchall()]

    def create_material_subcategory(self, category_id: int, name: str) -> int:
        """Create a material subcategory. Returns the subcategory ID."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Material subcategory name is required.")
        if not category_id:
            raise ValueError("Category is required for a subcategory.")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO material_subcategory (category_id, name) 
                VALUES (?, ?)
            ''', (category_id, name))
            return cursor.lastrowid

    # ==================== MATERIAL TYPE OPERATIONS ====================

    def get_types_by_category(self, category_id: int, subcategory_id: int = None) -> List[Dict[str, Any]]:
        """
        Get material types for a category.
        If subcategory_id is provided, get types for that subcategory.
        If subcategory_id is None, get types directly under category.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if subcategory_id:
                cursor.execute('''
                    SELECT * FROM material_type 
                    WHERE category_id = ? AND subcategory_id = ?
                    ORDER BY name
                ''', (category_id, subcategory_id))
            else:
                cursor.execute('''
                    SELECT * FROM material_type 
                    WHERE category_id = ? AND subcategory_id IS NULL
                    ORDER BY name
                ''', (category_id,))
            return [dict(row) for row in cursor.fetchall()]

    def create_material_type(self, category_id: int, name: str, subcategory_id: int = None) -> int:
        """
        Create a material type. Returns the type ID.
        If subcategory_id is provided, type belongs to that subcategory.
        Otherwise, type belongs directly to category.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("Material type name is required.")
        if not category_id:
            raise ValueError("Category is required for a material type.")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO material_type (category_id, subcategory_id, name) 
                VALUES (?, ?, ?)
            ''', (category_id, subcategory_id, name))
            return cursor.lastrowid

    def delete_color(self, color_id: int) -> bool:
        """
        Deletes a color by its ID.

        Args:
            color_id (int): Primary key identifying the target color record.

        Returns:
            bool: True if the color record was dropped, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM color WHERE id = ?', (color_id,))
            return cursor.rowcount > 0

    # ==================== MATERIAL OPERATIONS ====================

    def create_material(self, name: str, category_id: int = None, subcategory_id: int = None,
                       type_id: int = None, technical_name: str = "", surface: str = "") -> int:
        """Create a material with new hierarchical structure. Returns the material ID."""
        name = (name or "").strip()
        technical_name = (technical_name or "").strip()
        surface = (surface or "").strip()

        if not name:
            raise ValueError("Material name is required.")
        if (subcategory_id or type_id) and not category_id:
            raise ValueError("Category is required when subcategory or type is selected.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO material (name, category_id, subcategory_id, type_id, 
                                     scientific_name, technical_name, surface)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, category_id, subcategory_id, type_id, technical_name, technical_name, surface))
            return cursor.lastrowid

    def get_material(self, material_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets a material by ID.
        Args:
            material_id (int): target index code row tracking key.

        Returns:
            Optional[Dict[str, Any]]: A data map dictionary describing the target material properties if found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*,
                       mc.name as category_name,
                       ms.name as subcategory_name,
                       mt.name as type_name
                FROM material m
                LEFT JOIN material_category mc ON m.category_id = mc.id
                LEFT JOIN material_subcategory ms ON m.subcategory_id = ms.id
                LEFT JOIN material_type mt ON m.type_id = mt.id
                WHERE m.id = ?
            ''', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_materials(self) -> List[Dict[str, Any]]:
        """
        Gets all materials with 'Other' always at the end.

        Returns:
            List[Dict[str, Any]]: Ordered query trace result list dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*,
                       mc.name as category_name,
                       ms.name as subcategory_name,
                       mt.name as type_name
                FROM material m
                LEFT JOIN material_category mc ON m.category_id = mc.id
                LEFT JOIN material_subcategory ms ON m.subcategory_id = ms.id
                LEFT JOIN material_type mt ON m.type_id = mt.id
                ORDER BY m.name
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def update_material(self, material_id: int, **kwargs) -> bool:
        """
        Updates material properties.

        Args:
            material_id (int): primary key index defining the targeted material row.
            **kwargs: Updates list properties containing keys from 'name', 'scientific_name', 'color_id'.

        Returns:
            bool: True if modification execution updated records, False otherwise.
        """
        allowed = {'name', 'category_id', 'subcategory_id', 'type_id', 
                  'technical_name', 'surface'}
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
        """
        Deletes a material.

        Args:
            material_id (int): Target primary index key row tracking identifier.

        Returns:
            bool: True if structural row subtraction impacted records, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM material WHERE id = ?', (material_id,))
            conn.commit()
            return cursor.rowcount > 0
        
    def delete_material_category(self, category_id: int) -> bool:
        """Deletes a material category. Dependent materials will have category_id set to NULL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM material_category WHERE id = ?", (category_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_material_display_name(self, material_id: int) -> str:
        """Get formatted display name for material (Category > Subcategory > Type > Name)."""
        material = self.get_material(material_id)
        if not material:
            return "Unknown"
        
        parts = []
        if material.get('category_name'):
            parts.append(material['category_name'])
        if material.get('subcategory_name'):
            parts.append(material['subcategory_name'])
        if material.get('type_name'):
            parts.append(material['type_name'])
        parts.append(material['name'])
        
        return ' > '.join(parts)

    # ==================== COMPONENT OPERATIONS ====================

    def create_component(self, name: str, product_id: int = None, color_id: int = None,
                         material_id: int = None, weight: float = None, weight_unit: str = "g",
                         node_type: str = "", x: float = 0, y: float = 0) -> int:
        """
        Creates component in root/intermediate/leaf tables; returns encoded component ID.

        Args:
            name (str): Structural title name of the sub-component.
            product_id (int, optional): Parent product root component trace key link. Defaults to None.
            color_id (int, optional): Reference color lookup table target key. Defaults to None.
            material_id (int, optional): Reference material lookup table target key. Defaults to None.
            weight (float, optional): Numeric weight metric evaluation score. Defaults to None.
            weight_unit (str, optional): Text metric weight unit identifier. Defaults to "g".
            node_type (str, optional): Hierarchy mapping text ('Root', 'Intermediate', 'Leaf'). Defaults to "".
            x (float, optional): Visual element component canvas layout X metric. Defaults to 0.
            y (float, optional): Visual element component canvas layout Y metric. Defaults to 0.

        Returns:
            int: Encoded unified component identifier integer.

        Raises:
            ValueError: If creating an intermediate or leaf component without a valid parent product_id.
        """
        normalized = (node_type or "Intermediate").strip().lower()
        if normalized in ("root", "product"):
            table = "root_component"
        elif normalized in ("leaf",):
            table = "leaf_component"
        else:
            table = "intermediate_component"

        # Enforce the current UI/schema rules:
        # - Root components show no material/color fields in the UI.
        # - Leaf components show both material and color.
        # - Intermediate components show neither.
        if table == "root_component":
            material_id = None
            color_id = None
        elif table == "leaf_component":
            pass
        else:
            color_id = None
            material_id = None

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
        """
        Gets a component by encoded ID with color/material info.

        Args:
            component_id (int): Virtual unified component tracking code identifier.

        Returns:
            Optional[Dict[str, Any]]: Integrated attributes dictionary context map, or None if no record matches.
        """
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
        """
        Get all intermediate+leaf components for a root product.

        Args:
            product_id (int): Target parent product identifier root tracing index.

        Returns:
            List[Dict[str, Any]]: Flat data map array representing all children records attached to the product.
        """
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
        """
        Gets root product components.

        Args:
            product_id (int): Target primary entry product key row index identifier.

        Returns:
            Optional[Dict[str, Any]]: Root component properties key-value dictionary, or None if missing.
        """
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
        """
        Updates component properties.
        
        Args:
            component_id (int): Encoded virtual unified sub-component item tracking ID.
            **kwargs: Dynamic values matching target table column fields.

        Returns:
            bool: True if operational database queries changed rows successfully, False otherwise.
        """
        table_name, row_id = self._decode_component_id(component_id)
        if table_name == "root_component":
            allowed = {'name', 'weight', 'weight_unit', 'node_type', 'image_path', 'brand', 'model', 'description'}
        elif table_name == "leaf_component":
            # Leaf components are allowed to update both color and material fields
            allowed = {
                'name', 'weight', 'weight_unit', 'node_type', 'image_path', 'brand', 'model', 'description',
                'color_id', 'material_id', '_material_category_id', '_material_subcategory_id', '_material_type_id'
            }
        else:
            allowed = {'name', 'weight', 'weight_unit', 'node_type', 'image_path', 'root_component_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Normalize UI values before sending them to SQLite.
        for fk_field in ('color_id', 'material_id', '_material_category_id', '_material_subcategory_id', '_material_type_id'):
            if fk_field in updates:
                value = updates[fk_field]
                if value is None or str(value).strip() == "":
                    updates[fk_field] = None
                else:
                    updates[fk_field] = int(value)

        if 'root_component_id' in updates:
            value = updates['root_component_id']
            if value is None or str(value).strip() == "":
                updates['root_component_id'] = None
            else:
                updates['root_component_id'] = int(value)

        if 'weight' in updates:
            value = updates['weight']
            if value is None or str(value).strip() == "":
                updates['weight'] = None
            else:
                updates['weight'] = float(value)

        # Enforce stored-schema rules even if older data or external callers try to pass hidden fields.
        # Root components should not have color/material updated via this path.
        if table_name == "root_component":
            updates.pop('color_id', None)
            updates.pop('material_id', None)
        elif table_name == "leaf_component":
            # Leaf supports both color and material — keep them as allowed above.
            pass
        else:
            updates.pop('color_id', None)
            updates.pop('material_id', None)

        if table_name == "root_component":
            updates["modified_at"] = datetime.now().isoformat()

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [row_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE {table_name} SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0

    def delete_component(self, component_id: int) -> bool:
        """
        Deletes a component.
        
        Args:
            component_id (int): Encoded unified item identification code tracking index.

        Returns:
            bool: True if removal operation processing updated rows, False otherwise.
        """
        table_name, row_id = self._decode_component_id(component_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (row_id,))
            return cursor.rowcount > 0

    # ==================== DISASSEMBLY_STEP OPERATIONS ====================

    def create_step(self, component_id: int, step_order: int, description: str = "",
                    image_path: str = "", action_id: int = None, title: str = "",
                    x: float = 0, y: float = 0) -> int:
        """
        Creates a disassembly step and returns its step ID.
        
        Args:
            component_id (int): Virtual unified component track key undergoing disassembly parsing.
            step_order (int): Chromatic progression ranking integer location trace.
            description (str, optional): Instruction notes explaining step procedures. Defaults to "".
            image_path (str, optional): Filesystem route linking reference drawings or snapshots. Defaults to "".
            action_id (int, optional): Reference database identifier tracking primary action task hooks. Defaults to None.
            title (str, optional): Brief clear name describing step tasks context. Defaults to "".
            x (float, optional): Layout canvas element drawing X metric indicator. Defaults to 0.
            y (float, optional): Layout canvas element drawing Y metric indicator. Defaults to 0.

        Returns:
            int: Primary tracking identification key index assigned to the newly initialized process step.
        """
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
        """
        Gets next step_order value for a specific input component.
        
        Args:
            component_id (int): Virtual unified identifier for the targeted source item record.

        Returns:
            int: Next logical progression order index sequence number (starts at 1 if none exist).
        """
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
        """Gets next action_order value for a specific step.

        Deletion does not renumber existing action_order values, so gaps are allowed.
        New actions always append at MAX(action_order) + 1.

        Args:
            dissasembly_step_id (int): Virtual unified identifier for the targeted source item record.

        Returns:
            int: Next logical progression order index sequence number.
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
        """
        Resolves the owning root_component for any encoded component id.
        """
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
        """
        Gets a step by ID.
        Args:
            step_id (int): The unique database identifier of the step.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the row data if found, 
                                      otherwise None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM disassembly_step WHERE id = ?', (step_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_step_for_component(self, component_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets the disassembly step for a component (1:1).

        Args:
            component_id (int): Encoded composite or raw ID of the parent component.

        Returns:
            Optional[Dict[str, Any]]: Step dictionary if matching record exists, else None.
        """
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
        """
        Updates step properties.
        
        Args:
            step_id (int): Target step row index.
            **kwargs: Arbitrary keyword arguments corresponding to editable schema keys.

        Returns:
            bool: True if any matching rows were updated or synchronized, False otherwise.
        """
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
        """
        Deletes a step.
        
        Args:
            step_id (int): Step primary key index.

        Returns:
            bool: True if a row was matched and deleted, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM disassembly_step WHERE id = ?', (step_id,))
            return cursor.rowcount > 0

    # ==================== STEP OUTPUT OPERATIONS ====================

    def add_component_to_step(self, disassembly_step_id: int, component_id: int) -> Dict[str, Any]:
        """
        Adds a component as output of a step (1:N relationship).
        
        Args:
            disassembly_step_id (int): Parent flowchart step identifier.
            component_id (int): Encoded child component identifier.

        Returns:
            Dict[str, Any]: Trace metadata tracking the assigned link index and duplicate status.
        """
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
        """
        Gets all components produced by a step (1:N).
        
        Args:
            disassembly_step_id (int): Target parent step.

        Returns:
            List[Dict[str, Any]]: Flat collection of fully annotated component dictionaries.
        """
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
        """
        Removes a component from a step.
        
        Args:
            disassembly_step_id (int): Parent step identifier.
            component_id (int): Encoded target child component index.

        Returns:
            bool: True if the junction entry was found and purged, False otherwise.
        """
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
        """
        Creates an action and returns its action ID.
        
        Args:
            name (str): Label string representing the activity (e.g., "Unscrew").
            description (str): Verbose documentation notes detailing the step execution.
            tool_id (Optional[int]): Database primary index reference for a linked tool.

        Returns:
            int: The primary key ID of the newly generated action record.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO action (name, description, tool_id)
                VALUES (?, ?, ?)
            ''', (name, description, tool_id))
            return cursor.lastrowid

    def get_action(self, action_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets an action by ID with tool info.
        
        Args:
            action_id (int): Action primary key index.

        Returns:
            Optional[Dict[str, Any]]: Joined action and tool attribute map, or None.
        """
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
        """
        Compatibility helper: returns one action as chain head.
        
        Args:
            action_id (int): The unique ID of the action to retrieve.

        Returns:
            List[Dict[str, Any]]: A list containing the action dictionary if found, otherwise an empty list.
        """
        action = self.get_action(action_id)
        return [action] if action else []

    def update_action(self, action_id: int, **kwargs) -> bool:
        """
        Updates action properties.
        
        Args:
            action_id (int): Action database identifier.
            **kwargs: Configuration dictionary matching allowed keys ('name', 'description', 'tool_id').

        Returns:
            bool: True if an action row was successfully modified, False otherwise.
        """
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
        """
        Deletes an action.
        
        Args:
            action_id (int): Target action index.

        Returns:
            bool: True if row match successfully purged, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM action WHERE id = ?', (action_id,))
            return cursor.rowcount > 0

    # ==================== TOOL OPERATIONS ====================

    def create_tool(self, name: str, category: str = "") -> int:
        """
        Creates a tool and returns the tool ID.
        
        Args:
            name (str): Unique text identifier for the tool (e.g., "T20 Torx Screwdriver").
            category (str): Optional tracking group tag string.

        Returns:
            int: Verified primary key index pointing to the unique tool item.
        """
        name = (name or "").strip()
        category = (category or "").strip()
        if not name:
            raise ValueError("Tool name is required.")
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
        """
        Gets a tool by ID.
        
        Args:
            tool_id (int): The primary key of the tool in the database.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the tool data if found, or None if no record matches.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tool WHERE id = ?', (tool_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Gets all tools.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing all tools.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tool ORDER BY category, name')
            return [dict(row) for row in cursor.fetchall()]

    def delete_tool(self, tool_id: int) -> bool:
        """
        Deletes a tool.
        
        Args:
            tool_id (int): The primary key of the tool to be deleted.

        Returns:
            bool: True if the tool existed and was successfully deleted, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tool WHERE id = ?', (tool_id,))
            return cursor.rowcount > 0

    # ==================== TABLE SCHEMA (for dynamic UI) ====================

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Gets the schema of a table for dynamic UI generation.
        
        Args:
            table_name (str): Exact target catalog name string being evaluated.

        Returns:
            List[Dict[str, Any]]: Schema metrics tracking collection arrays documenting item configurations.
        """
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
        """
        Gets editable fields for component tables (root/intermediate/leaf).
        
        Args:
            component_kind (str): String identifier ('root', 'intermediate', or 'leaf').

        Returns:
            List[Dict[str, Any]]: Collection tracking arrays describing entry column fields.
        """
        kind = (component_kind or "intermediate").strip().lower()
        if kind == "root":
            table_name = "root_component"
            exclude = {'id', 'created_at', 'modified_at', 'color_id', 'material_id'}
        elif kind == "leaf":
            table_name = "leaf_component"
            exclude = {'id', 'root_component_id'}
        else:
            # Treat "composite" as intermediate in current schema.
            table_name = "intermediate_component"
            exclude = {'id', 'root_component_id', 'color_id', 'material_id'}

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
        """
        Gets editable fields for product table.
        
        Returns:
            List[Dict[str, Any]]: A list of column schemas filtered and configured for UI rendering.
        """
        all_columns = self.get_table_schema('root_component')
        exclude = {'id', 'created_at', 'modified_at', 'node_type'}

        editable_fields = []
        for col in all_columns:
            if col['name'] not in exclude:
                col['display_name'] = col['name'].replace('_', ' ').title()
                editable_fields.append(col)
        return editable_fields

    def get_action_fields(self) -> List[Dict[str, Any]]:
        """
        Gets editable fields for action table.
        
        Returns:
            List[Dict[str, Any]]: Field definitions configured for the Action UI panel.
        """
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
        """
        Gets editable fields for disassembly_step table.

        Returns:
            List[Dict[str, Any]]: Field definitions configured for the Disassembly Step UI form.
        """
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
        """
        Gets editable fields for material table.
        
        Returns:
            List[Dict[str, Any]]: Field definitions configured for the Material UI form.
        """
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
        """
        Gets database statistics.

        Returns:
            Dict[str, Any]: Map trace linking table metadata keys to integer row quantities.
        """
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
    """
    Gets or creates the default database manager.
    
    Args:
        db_path (str, optional): Overriding target absolute route filesystem database path. Defaults to None.

    Returns:
        DatabaseManager: Active singleton instance entity managing application transactions.
    """
    global _default_db
    if _default_db is None or (db_path and _default_db.db_path != db_path):
        _default_db = DatabaseManager(db_path)
    return _default_db
