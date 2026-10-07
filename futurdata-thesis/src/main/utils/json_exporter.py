"""
Enhanced JSON Exporter/Importer
Exports complete diagram with all repository relationships
Imports JSON and restores to repository
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from ..services.catalog_resolver import CatalogResolver
from ..models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape


class EnhancedJSONExporter:
    """Export/Import diagrams with full repository information."""
    
    def __init__(self, repository):
        """
        Initialize exporter.
        
        Args:
            repository: RepositoryManager instance
        """
        self.repository = repository
    
    def serialize_active_diagram(self, diagram: Diagram) -> Dict[str, Any]:
        """Serialize the active diagram for all document converters.

        Preserve ArrowShape objects for the editable ARIADNE diagram while also
        normalizing their relationships into ``connections`` for document
        converters. PPTX, DOCX, Markdown, TXT and HTML therefore receive the same
        canonical graph without losing the visual arrow data.
        """
        snapshot = {
            "diagram_id": diagram.diagram_id,
            "metadata": self._build_metadata(diagram, None),
            "diagram": self._build_diagram_settings(diagram),
            "shapes": self._export_shapes(diagram),
            "connections": self._export_connections(diagram, include_arrows=True),
        }

        return CatalogResolver(self.repository).enrich(snapshot)

    def export_diagram(self, diagram: Diagram, file_path: str, 
                      product_id: Optional[int] = None, copy_images: bool = True) -> bool:
        """
        Export diagram to JSON with complete repository information.
        
        Args:
            diagram: Diagram object to export
            file_path: Path to save JSON file
            product_id: Optional product ID to include metadata
            
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
                "repository": self._export_repository_info(diagram, product_id)
            }
            
            data = CatalogResolver(self.repository).enrich(data)
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
            product = self.repository.get_product(product_id)
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
        """Export all canvas shapes, including visual ArrowShape connectors."""
        shapes = []

        for shape in diagram.shapes:
            if isinstance(shape, ArrowShape):
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
            
            for field in ("material", "color", "material_details", "unresolved_image_path", "legacy_references"):
                if field in shape.properties:
                    base_data[field] = shape.properties[field]
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
    
    def _export_connections(self, diagram: Diagram, include_arrows: bool = False) -> list:
        """Normalize Connection and ArrowShape relationships into graph edges."""
        connections = []
        seen = set()

        def add_edge(from_shape, to_shape, from_anchor="bottom", to_anchor="top"):
            if from_shape is None or to_shape is None:
                return
            key = (id(from_shape), id(to_shape))
            if key in seen:
                return
            seen.add(key)
            connections.append({
                "from_shape_id": key[0],
                "to_shape_id": key[1],
                "from_anchor": from_anchor or "bottom",
                "to_anchor": to_anchor or "top",
            })

        for conn in getattr(diagram, "connections", []):
            add_edge(
                getattr(conn, "from_shape", None),
                getattr(conn, "to_shape", None),
                getattr(conn, "from_anchor", "bottom"),
                getattr(conn, "to_anchor", "top"),
            )

        if include_arrows:
            for shape in getattr(diagram, "shapes", []):
                if isinstance(shape, ArrowShape):
                    add_edge(
                        getattr(shape, "from_shape", None),
                        getattr(shape, "to_shape", None),
                        getattr(shape, "from_anchor", "bottom"),
                        getattr(shape, "to_anchor", "top"),
                    )

        return connections

    def _export_repository_info(self, diagram: Diagram, product_id: Optional[int]) -> Dict:
        """Export the JSON-persistence records needed to reconstruct this product."""
        snapshot = self.repository.export_snapshot()
        info = {
            "schema_version": snapshot.get("schema_version", 1),
            "catalogs": {
                "colors": snapshot.get("colors", []),
                "material_categories": snapshot.get("material_categories", []),
                "material_subcategories": snapshot.get("material_subcategories", []),
                "material_types": snapshot.get("material_types", []),
                "materials": snapshot.get("materials", []),
                "tools": snapshot.get("tools", []),
            },
            "product": None, "components": [], "steps": [], "actions": [],
            "step_actions": [], "step_outputs": [],
        }
        if not product_id:
            return info
        info["product"] = self.repository.get_product(product_id)
        components = self.repository.get_components_by_product(product_id)
        info["components"] = components
        component_ids = [product_id] + [c["component_id"] for c in components]
        steps = []
        for component_id in component_ids:
            steps.extend(self.repository.get_steps_for_component(component_id))
        info["steps"] = steps
        action_ids = set()
        for step in steps:
            for link in self.repository.get_actions_for_step(step["id"]):
                info["step_actions"].append({
                    "step_id": step["id"], "action_id": link["action_id"],
                    "action_order": link["action_order"]
                })
                action_ids.add(link["action_id"])
            for component in self.repository.get_components_from_step(step["id"]):
                info["step_outputs"].append({"step_id": step["id"], "component_id": component["component_id"]})
        info["actions"] = [self.repository.get_action(action_id) for action_id in sorted(action_ids)]
        return info

    def import_diagram(self, file_path: str, create_in_repository: bool = True):
        from contextlib import nullcontext
        try:
            with self.repository.transaction() if self.repository is not None else nullcontext():
                diagram = self._import_diagram(file_path, create_in_repository)
                if diagram is None:
                    raise ValueError("Invalid diagram import")
                return diagram
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def _import_diagram(self, file_path: str, create_in_repository: bool = True) -> Optional[Diagram]:
        """
        Import diagram from JSON and optionally create in repository.
        
        Args:
            file_path: Path to JSON file
            create_in_repository: If True, create entries in repository
            
        Returns:
            Diagram object, or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            catalog_warnings = []
            catalogs = data.get("catalogs", data.get("repository", {}).get("catalogs", data.get("repository", {})))
            references = [(shape, field, collection) for shape in data.get("shapes", []) for field, collection in (("color_id", "colors"), ("material_id", "materials"), ("tool_id", "tools")) if shape.get(field) is not None]
            if references:
                maps = self.repository.import_catalogs(catalogs)
                for shape, field, collection in references:
                    old = shape[field]
                    shape[field] = maps.get(collection, {}).get(old)
                    if shape[field] is None:
                        catalog_warnings.append(f"Unresolved legacy {field}={old}; no portable definition")
                        shape.setdefault("legacy_references", {})[field] = old
            # Create diagram
            diagram = Diagram()
            diagram.file_path = file_path
            
            # Set settings
            settings = data.get('diagram', {})
            diagram.snap_to_grid = settings.get('snap_to_grid', True)
            diagram.grid_enabled = settings.get('grid_enabled', True)
            diagram.zoom_level = settings.get('zoom_level', 1.0)
            canvas_size = settings.get('canvas_size')
            diagram.canvas_size = tuple(canvas_size) if canvas_size else None
            diagram.metadata = data.get('metadata', diagram.metadata)
            
            # Import shapes
            shape_id_map = {}  # old_id -> new_shape
            
            # First pass: Create all non-arrow shapes
            for shape_data in data.get('shapes', []):
                if shape_data['type'] != 'arrow':
                    shape = self._import_shape(shape_data, create_in_repository)
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
                from_id = conn_data.get('from_shape_id', conn_data.get('from_id'))
                to_id = conn_data.get('to_shape_id', conn_data.get('to_id'))
                if from_id is None or to_id is None:
                    raise ValueError('Connection is missing a source or target ID')
                from_shape = shape_id_map.get(from_id)
                to_shape = shape_id_map.get(to_id)
                
                if from_shape and to_shape:
                    from ..models.connection import Connection
                    conn = Connection(from_shape, to_shape, conn_data.get('type', 'solid'))
                    conn.from_anchor = conn_data.get('from_anchor', 'bottom')
                    conn.to_anchor = conn_data.get('to_anchor', 'top')
                    if 'from_anchor' not in conn_data or 'to_anchor' not in conn_data:
                        conn.auto_calculate_anchors()
                    diagram.connections.append(conn)
            
            diagram.deduplicate_edges()

            # Restore images if available
            self._restore_diagram_images(diagram, file_path)
            diagram.import_warnings.extend(catalog_warnings)
            
            return diagram
            
        except Exception as e:
            print(f"Import error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _import_shape(self, data: Dict, create_in_repository: bool) -> Optional[Any]:
        """Import a single shape."""
        shape_type = data.get('type')
        x, y = data.get('x', 0), data.get('y', 0)
        
        if shape_type in ('product', 'component'):
            shape = ComponentBox(x, y)
            shape.text = data.get('text', '')
            shape.properties['node_type'] = data.get(
                'node_type', 'Root' if shape_type == 'product' else 'Intermediate'
            )
            shape.properties['name'] = data.get('name', '')
            shape.properties['brand'] = data.get('brand', '')
            shape.properties['model'] = data.get('model', '')
            shape.properties['color_id'] = data.get('color_id')
            shape.properties['material_id'] = data.get('material_id')
            shape.properties['weight'] = data.get('weight')
            shape.properties['weight_unit'] = data.get('weight_unit', 'g')
            shape.properties['description'] = data.get('description', '')
            shape.properties['image_path'] = data.get('image_path', '')
            for field in ('material', 'color', 'material_details', 'unresolved_image_path', 'legacy_references'):
                if field in data:
                    shape.properties[field] = data[field]
            
            # If DB ID exists and not creating new, preserve it
            if data.get('db_id') and not create_in_repository:
                shape.properties['db_id'] = data['db_id']
            
            return shape
        
        elif shape_type == 'action':
            shape = ActionCircle(x, y)
            shape.text = data.get('text', '')
            shape.step_description = data.get('step_description', '')
            shape.image_path = data.get('image_path', '')
            shape.tools = data.get('tools', '')
            
            if data.get('db_step_id') and not create_in_repository:
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
            
            if not create_in_repository:
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
    
    def _restore_diagram_images(self, diagram, json_file_path):
        """Resolve exact paths first; never guess among duplicate legacy basenames."""
        from pathlib import Path
        from .image_handler import get_image_handler
        root = Path(json_file_path).parent.resolve()
        folders = [root / "images", root / (Path(json_file_path).stem + "_images")]
        handler = get_image_handler()
        self.last_import_warnings = []
        for shape in diagram.shapes:
            props = shape.properties if isinstance(shape, ComponentBox) else None
            ref = props.get("image_path", "") if props is not None else getattr(shape, "image_path", "")
            if not ref:
                continue
            normalized = str(ref).replace("\\", "/")
            exact = (root / normalized).resolve()
            source = exact if root in exact.parents and exact.is_file() else None
            if source is None:
                matches = {p.resolve() for folder in folders if folder.is_dir()
                           for p in folder.rglob("*") if p.is_file() and p.name == normalized.rsplit("/", 1)[-1]}
                if len(matches) == 1:
                    source = matches.pop()
                else:
                    reason = "Ambiguous" if matches else "Missing"
                    self.last_import_warnings.append(f"{reason} image for {shape.text}: {ref}")
            new_path = None
            if source:
                kind = "component" if props is not None else "step" if isinstance(shape, ActionCircle) else "action"
                new_path = handler.upload_image(str(source), kind, None)
                if not new_path:
                    self.last_import_warnings.append(f"Could not restore image: {ref}")
            # An unresolved archive path must not resolve to an unrelated local file.
            if props is not None:
                props["image_path"] = new_path or ""
                if not new_path:
                    props["unresolved_image_path"] = ref
            else:
                shape.image_path = new_path or ""
                if not new_path:
                    shape.unresolved_image_path = ref
        diagram.import_warnings = list(self.last_import_warnings)
