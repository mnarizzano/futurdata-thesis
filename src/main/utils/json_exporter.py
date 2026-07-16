"""
Enhanced JSON Exporter/Importer
Exports complete diagram with all database relationships
Imports JSON and restores to database
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from ..models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape


class EnhancedJSONExporter:
    """Export/Import diagrams with full database information."""
    
    def __init__(self, database):
        """
        Initialize exporter.
        
        Args:
            database: DatabaseManager instance
        """
        self.db = database
    
    def export_diagram(self, diagram: Diagram, file_path: str, 
                      product_id: Optional[int] = None, copy_images: bool = True) -> bool:
        """
        Export diagram to JSON with complete database information.
        
        Args:
            diagram: Diagram object to export
            file_path: Path to save JSON file
            product_id: Optional product ID to include metadata
            copy_images: Whether to copy image files to the export directory
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build JSON structure
            data = {
                "metadata": self._build_metadata(diagram, product_id),
                "diagram": self._build_diagram_settings(diagram),
                "shapes": self._export_shapes(diagram),
                "connections": self._export_connections(diagram),
                "database": self._export_database_info(diagram, product_id)
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Copy images if requested
            if copy_images:
                self._copy_diagram_images(diagram, file_path)
            
            return True
            
        except (OSError, TypeError, ValueError, KeyError):
            return False
    
    def _copy_diagram_images(self, diagram: Diagram, json_file_path: str):
        """Copy all images referenced in diagram to export folder with duplicate detection."""
        try:
            import shutil
            import hashlib
            from .image_handler import get_image_handler
            
            # Create images folder next to JSON file
            json_dir = os.path.dirname(json_file_path)
            json_basename = os.path.splitext(os.path.basename(json_file_path))[0]
            images_export_dir = os.path.join(json_dir, f"{json_basename}_images")
            
            os.makedirs(images_export_dir, exist_ok=True)
            
            image_handler = get_image_handler()
            copied_count = 0
            skipped_count = 0
            
            # Collect and copy all images
            for shape in diagram.shapes:
                image_path = None
                
                if isinstance(shape, ComponentBox):
                    image_path = shape.properties.get('image_path', '')
                elif isinstance(shape, ActionCircle):
                    image_path = getattr(shape, 'image_path', '')
                elif isinstance(shape, DiamondStep):
                    image_path = getattr(shape, 'image_path', '')
                
                if image_path:
                    full_path = image_handler.get_full_path(image_path)
                    if os.path.exists(full_path):
                        dest_path = os.path.join(images_export_dir, os.path.basename(image_path))
                        
                        # Check if file already exists with same content
                        if os.path.exists(dest_path):
                            if self._files_are_identical(full_path, dest_path):
                                skipped_count += 1
                                continue
                        
                        # Copy if file doesn't exist or content is different
                        shutil.copy2(full_path, dest_path)
                        copied_count += 1
            
            if copied_count > 0:
                print(f"Copied {copied_count} images to {images_export_dir}")
            
        except (OSError, TypeError, ValueError):
            return
    
    def _files_are_identical(self, file1: str, file2: str) -> bool:
        """Check if two files have identical content using MD5 hash."""
        try:
            import hashlib
            
            def get_file_hash(filepath):
                hash_md5 = hashlib.md5()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                return hash_md5.hexdigest()
            
            return get_file_hash(file1) == get_file_hash(file2)
        except (OSError, TypeError, ValueError):
            return False
    
    def _build_metadata(self, diagram: Diagram, product_id: Optional[int]) -> Dict:
        """Build metadata section."""
        metadata = {
            "version": "2.0",  # Enhanced version
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "author": "",
            "product_name": "",
            "description": "",
            "export_type": "full"  # full = with DB info
        }
        
        # Add product info if available
        if product_id:
            product = self.db.get_product(product_id)
            if product:
                metadata["product_name"] = product.get('name', '')
                metadata["product_brand"] = product.get('brand', '')
                metadata["product_model"] = product.get('model', '')
                metadata["product_id"] = product_id
        
        return metadata
    
    def _build_diagram_settings(self, diagram: Diagram) -> Dict:
        """Build diagram settings."""
        return {
            "canvas_size": [2000, 2000],
            "zoom_level": 1.0,
            "grid_enabled": diagram.grid_enabled if hasattr(diagram, 'grid_enabled') else True,
            "snap_to_grid": diagram.snap_to_grid
        }
    
    def _export_shapes(self, diagram: Diagram) -> list:
        """Export all shapes with database IDs."""
        shapes = []
        
        for shape in diagram.shapes:
            if isinstance(shape, ArrowShape):
                # Handle arrows separately
                shapes.append(self._export_arrow(shape))
            else:
                shapes.append(self._export_shape(shape))
        
        return shapes
    
    def _export_shape(self, shape) -> Dict:
        """Export a single shape."""
        base_data = {
            "id": id(shape),  # Use memory ID for reference
            "x": shape.x,
            "y": shape.y,
            "text": shape.text
        }
        
        if isinstance(shape, ComponentBox):
            base_data.update({
                "type": "component",
                "db_id": shape.properties.get('db_id'),
                "node_type": shape.properties.get('node_type', 'Intermediate'),
                "name": shape.properties.get('name', ''),
                "brand": shape.properties.get('brand', ''),
                "model": shape.properties.get('model', ''),
                "color_id": shape.properties.get('color_id'),
                "material_id": shape.properties.get('material_id'),
                "weight": shape.properties.get('weight'),
                "weight_unit": shape.properties.get('weight_unit', 'g'),
                "description": shape.properties.get('description', ''),
                "image_path": shape.properties.get('image_path', '')
            })
            
            # Determine if it's a product
            if shape.properties.get('node_type') == 'Root':
                base_data["type"] = "product"
        
        elif isinstance(shape, ActionCircle):
            base_data.update({
                "type": "action",
                "db_step_id": getattr(shape, 'db_step_id', None),
                "step_description": getattr(shape, 'step_description', ''),
                "image_path": getattr(shape, 'image_path', ''),
                "tools": getattr(shape, 'tools', '')
            })
        
        elif isinstance(shape, DiamondStep):
            base_data.update({
                "type": "diamond",
                "db_action_id": getattr(shape, 'db_action_id', None),
                "db_step_id": getattr(shape, 'db_step_id', None),
                "db_step_action_id": getattr(shape, 'db_step_action_id', None),
                "db_action_order": getattr(shape, 'db_action_order', None),
                "name": getattr(shape, 'name', ''),
                "description": getattr(shape, 'description', ''),
                "tools": getattr(shape, 'tools', ''),
                "tool_id": getattr(shape, 'tool_id', None),
                "image_path": getattr(shape, 'image_path', '')
            })
        
        return base_data
    
    def _export_arrow(self, arrow: ArrowShape) -> Dict:
        """Export arrow shape."""
        return {
            "id": id(arrow),
            "type": "arrow",
            "x": arrow.x,
            "y": arrow.y,
            "text": arrow.text,
            "from_shape_id": id(arrow.from_shape),
            "to_shape_id": id(arrow.to_shape),
            "angle": getattr(arrow, 'angle', 0),
            "from_anchor": getattr(arrow, 'from_anchor', 'bottom'),
            "to_anchor": getattr(arrow, 'to_anchor', 'top')
        }
    
    def _export_connections(self, diagram: Diagram) -> list:
        """Export connection lines (not arrows)."""
        connections = []
        
        for conn in diagram.connections:
            connections.append({
                "from_shape_id": id(conn.from_shape),
                "to_shape_id": id(conn.to_shape),
                "from_anchor": conn.from_anchor,
                "to_anchor": conn.to_anchor
            })
        
        return connections
    
    def _export_database_info(self, diagram: Diagram, product_id: Optional[int]) -> Dict:
        """Export complete database information for reconstruction."""
        db_info = {
            "components": [],
            "steps": [],
            "actions": [],
            "relationships": []
        }
        
        if not product_id:
            return db_info
        
        # Export all components
        product = self.db.get_product(product_id)
        if product:
            db_info["components"].append({
                "type": "root",
                "db_id": product['id'],
                "data": product
            })
        
        components = self.db.get_components_by_product(product_id)
        for comp in components:
            db_info["components"].append({
                "type": comp['source_table'],
                "db_id": comp['component_id'],
                "data": comp
            })
        
        # Export all steps
        # TODO: Add step export logic
        
        return db_info
    
    def import_diagram(self, file_path: str, create_in_db: bool = True) -> Optional[Diagram]:
        """
        Import diagram from JSON and optionally create in database.
        
        Args:
            file_path: Path to JSON file
            create_in_db: If True, create entries in database
            
        Returns:
            Diagram object, or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create diagram
            diagram = Diagram()
            diagram.file_path = file_path
            
            # Set settings
            settings = data.get('diagram', {})
            diagram.snap_to_grid = settings.get('snap_to_grid', True)
            
            # Import shapes
            shape_id_map = {}  # old_id -> new_shape
            
            # First pass: Create all non-arrow shapes
            for shape_data in data.get('shapes', []):
                if shape_data['type'] != 'arrow':
                    shape = self._import_shape(shape_data, create_in_db)
                    if shape:
                        diagram.shapes.append(shape)
                        shape_id_map[shape_data['id']] = shape
            
            # Second pass: Create arrows
            for shape_data in data.get('shapes', []):
                if shape_data['type'] == 'arrow':
                    arrow = self._import_arrow(shape_data, shape_id_map)
                    if arrow:
                        diagram.shapes.append(arrow)
            
            # Import connections
            for conn_data in data.get('connections', []):
                from_shape = shape_id_map.get(conn_data['from_shape_id'])
                to_shape = shape_id_map.get(conn_data['to_shape_id'])
                
                if from_shape and to_shape:
                    from ..models.connection import Connection
                    conn = Connection(from_shape, to_shape)
                    conn.from_anchor = conn_data.get('from_anchor', 'bottom')
                    conn.to_anchor = conn_data.get('to_anchor', 'top')
                    conn.auto_calculate_anchors()
                    diagram.connections.append(conn)
            
            # Restore images if available
            self._restore_diagram_images(diagram, file_path)
            
            return diagram
            
        except Exception as e:
            print(f"Import error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _import_shape(self, data: Dict, create_in_db: bool) -> Optional[Any]:
        """Import a single shape."""
        shape_type = data.get('type')
        x, y = data.get('x', 0), data.get('y', 0)
        
        if shape_type in ('product', 'component'):
            shape = ComponentBox(x, y)
            shape.text = data.get('text', '')
            shape.properties['node_type'] = data.get('node_type', 'Intermediate')
            shape.properties['name'] = data.get('name', '')
            shape.properties['brand'] = data.get('brand', '')
            shape.properties['model'] = data.get('model', '')
            shape.properties['color_id'] = data.get('color_id')
            shape.properties['material_id'] = data.get('material_id')
            shape.properties['weight'] = data.get('weight')
            shape.properties['weight_unit'] = data.get('weight_unit', 'g')
            shape.properties['description'] = data.get('description', '')
            shape.properties['image_path'] = data.get('image_path', '')
            
            # If DB ID exists and not creating new, preserve it
            if data.get('db_id') and not create_in_db:
                shape.properties['db_id'] = data['db_id']
            
            return shape
        
        elif shape_type == 'action':
            shape = ActionCircle(x, y)
            shape.text = data.get('text', '')
            shape.step_description = data.get('step_description', '')
            shape.image_path = data.get('image_path', '')
            shape.tools = data.get('tools', '')
            
            if data.get('db_step_id') and not create_in_db:
                shape.db_step_id = data['db_step_id']
            
            return shape
        
        elif shape_type == 'diamond':
            shape = DiamondStep(x, y)
            shape.text = data.get('text', '')
            shape.name = data.get('name', '')
            shape.image_path = data.get('image_path', '')
            shape.description = data.get('description', '')
            shape.tools = data.get('tools', '')
            shape.tool_id = data.get('tool_id')
            
            if not create_in_db:
                shape.db_action_id = data.get('db_action_id')
                shape.db_step_id = data.get('db_step_id')
                shape.db_step_action_id = data.get('db_step_action_id')
                shape.db_action_order = data.get('db_action_order')
            
            return shape
        
        return None
    
    def _import_arrow(self, data: Dict, shape_map: Dict) -> Optional[ArrowShape]:
        """Import arrow shape."""
        from_shape = shape_map.get(data['from_shape_id'])
        to_shape = shape_map.get(data['to_shape_id'])
        
        if not from_shape or not to_shape:
            return None
        
        arrow = ArrowShape(0, 0, from_shape, to_shape)
        arrow.update_from_shapes()
        return arrow
    
    def _restore_diagram_images(self, diagram: Diagram, json_file_path: str):
        """Restore images from export folder to application images folder."""
        try:
            import shutil
            from .image_handler import get_image_handler
            
            # Check for images folder next to JSON
            json_dir = os.path.dirname(json_file_path)
            json_basename = os.path.splitext(os.path.basename(json_file_path))[0]
            images_import_dir = os.path.join(json_dir, f"{json_basename}_images")
            
            if not os.path.exists(images_import_dir):
                return  # No images folder found
            
            image_handler = get_image_handler()
            restored_count = 0
            
            # Process each shape and restore its image
            for shape in diagram.shapes:
                image_path = None
                
                if isinstance(shape, ComponentBox):
                    image_path = shape.properties.get('image_path', '')
                elif isinstance(shape, ActionCircle):
                    image_path = getattr(shape, 'image_path', '')
                elif isinstance(shape, DiamondStep):
                    image_path = getattr(shape, 'image_path', '')
                
                if image_path:
                    # Check if image exists in import folder
                    filename = os.path.basename(image_path)
                    source_path = os.path.join(images_import_dir, filename)
                    
                    if os.path.exists(source_path):
                        # Determine entity type for proper folder
                        entity_type = "component"
                        if isinstance(shape, ActionCircle):
                            entity_type = "step"
                        elif isinstance(shape, DiamondStep):
                            entity_type = "action"
                        
                        # Use image handler to upload (which copies to proper folder)
                        new_path = image_handler.upload_image(
                            source_path, 
                            entity_type,
                            None  # No entity ID yet
                        )
                        
                        if new_path:
                            # Update shape with new path
                            if isinstance(shape, ComponentBox):
                                shape.properties['image_path'] = new_path
                            elif isinstance(shape, ActionCircle):
                                shape.image_path = new_path
                            elif isinstance(shape, DiamondStep):
                                shape.image_path = new_path
                            
                            restored_count += 1
            
            print(f"Restored {restored_count} images from {images_import_dir}")
            
        except (OSError, TypeError, ValueError):
            return
