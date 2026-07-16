from typing import List, Optional, Tuple
from datetime import datetime
from .shape import Shape
from .connection import Connection
from ..models import ComponentBox

class Diagram:
    """Represents the core data model for a diagram, holding all shapes, connections, and metadata."""

    def __init__(self):
        """Initialize the diagram state, including shape lists, metadata, and canvas properties."""
        self.shapes: List[Shape] = []
        self.connections: List[Connection] = []
        self.selected_shapes: List[Shape] = []
        self.metadata = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "author": "",
            "product_name": "",
            "description": ""
        }
        self.canvas_size = None  # Unlimited canvas - size determined dynamically
        self.zoom_level = 1.0
        self.grid_enabled = True
        self.snap_to_grid = True
        self.modified = False
        self.file_path = None
        self.auto_sync_json = True 
        self.last_json_sync = None

    def add_shape(self, shape: Shape):
        """Add a new shape to the diagram and mark the diagram as modified."""
        self.shapes.append(shape)
        self.modified = True

    def remove_shape(self, shape: Shape):
        """Remove a shape and automatically clean up any associated connections."""
        self.connections = [
            conn for conn in self.connections
            if conn.from_shape != shape and conn.to_shape != shape
        ]
        if shape in self.shapes:
            self.shapes.remove(shape)
        if shape in self.selected_shapes:
            self.selected_shapes.remove(shape)
        self.modified = True

    def add_connection(self, connection: Connection):
        """Add a new connection between two shapes if it does not already exist."""
        for conn in self.connections:
            if conn.from_shape == connection.from_shape and conn.to_shape == connection.to_shape:
                return
        self.connections.append(connection)
        self.modified = True

    def remove_connection(self, connection: Connection):
        """Remove a specific connection from the diagram."""
        if connection in self.connections:
            self.connections.remove(connection)
            self.modified = True

    def get_shape_by_id(self, shape_id: int) -> Optional[Shape]:
        """Look up and return a shape from the diagram using its unique identifier."""
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
        return None

    def find_shape_at_point(self, x: float, y: float) -> Optional[Shape]:
        """Return the topmost shape located at the given (x, y) coordinates."""
        for shape in reversed(self.shapes):
            if shape.contains_point(x, y):
                return shape
        return None

    def find_shapes_in_rect(self, x1: float, y1: float, x2: float, y2: float) -> List[Shape]:
        """Find and return all shapes whose anchor points fall within the specified bounding box."""
        shapes_in_rect = []
        for shape in self.shapes:
            if x1 <= shape.x <= x2 and y1 <= shape.y <= y2:
                shapes_in_rect.append(shape)
        return shapes_in_rect

    def select_shape(self, shape: Shape, multi_select: bool = False):
        """Add a shape to the current selection, optionally clearing previous selections if multi_select is False."""
        if not multi_select:
            self.clear_selection()
        if shape not in self.selected_shapes:
            self.selected_shapes.append(shape)
            shape.selected = True

    def deselect_shape(self, shape: Shape):
        """Remove a specific shape from the current selection list."""
        if shape in self.selected_shapes:
            self.selected_shapes.remove(shape)
            shape.selected = False

    def clear_selection(self):
        """Deselect all currently selected shapes in the diagram."""
        for shape in self.selected_shapes:
            shape.selected = False
        self.selected_shapes.clear()

    def get_connections_for_shape(self, shape: Shape) -> List[Connection]:
        """Return a list of all connections attached to the specified shape."""
        return [
            conn for conn in self.connections
            if conn.from_shape == shape or conn.to_shape == shape
        ]

    def clear(self):
        """Reset the diagram to a completely empty state and reset global shape/connection counters."""
        self.shapes.clear()
        self.connections.clear()
        self.selected_shapes.clear()
        Shape.reset_counter()
        Connection.reset_counter()
        self.modified = False
        self.file_path = None

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate and return the bounding box encompassing all shapes in the diagram."""
        if not self.shapes:
            return (0, 0, 0, 0)
        min_x = min(shape.x for shape in self.shapes)
        min_y = min(shape.y for shape in self.shapes)
        max_x = max(shape.x for shape in self.shapes)
        max_y = max(shape.y for shape in self.shapes)
        return (min_x, min_y, max_x, max_y)

    def to_dict(self) -> dict:
        """Serialize the diagram's state, shapes, and connections into a dictionary, updating the modification timestamp."""
        self.metadata["modified"] = datetime.now().isoformat()
        return {
            "metadata": self.metadata,
            "diagram": {
                "canvas_size": self.canvas_size,
                "zoom_level": self.zoom_level,
                "grid_enabled": self.grid_enabled,
                "snap_to_grid": self.snap_to_grid
            },
            "shapes": [shape.to_dict() for shape in self.shapes],
            "connections": [conn.to_dict() for conn in self.connections]
        }

    def recalculate_node_types(self):
        """
        Dynamically determine if components are 'Root', 'Leaf', or 'Intermediate'.
        - Root: Component with NO incoming arrows.
        - Intermediate: Component with incoming AND outgoing arrows.
        - Leaf: Component with incoming arrows but NO outgoing arrows.
        """
        outgoing_ids = set()
        incoming_ids = set()
        
        # 1. Identify all active arrow directions (incoming and outgoing)
        for shape in self.shapes:
            s_type = getattr(shape, 'shape_type', '').lower() or getattr(shape, 'type', '').lower()
            if "arrow" in s_type:
                # Track Outgoing (From)
                from_shape = getattr(shape, 'from_shape', None)
                from_id = from_shape.id if from_shape else getattr(shape, '_from_shape_id', None)
                if not from_id and hasattr(shape, 'properties'):
                    from_id = shape.properties.get('from_shape_id')
                if from_id:
                    outgoing_ids.add(from_id)
                
                # Track Incoming (To)
                to_shape = getattr(shape, 'to_shape', None)
                to_id = to_shape.id if to_shape else getattr(shape, '_to_shape_id', None)
                if not to_id and hasattr(shape, 'properties'):
                    to_id = shape.properties.get('to_shape_id')
                if to_id:
                    incoming_ids.add(to_id)

        # Double check connections list
        for conn in self.connections:
            if conn.from_shape:
                outgoing_ids.add(conn.from_shape.id)
            if conn.to_shape:
                incoming_ids.add(conn.to_shape.id)

        # 2. Update Component node types based on connectivity
        for shape in self.shapes:
            s_type = getattr(shape, 'shape_type', '').lower() or getattr(shape, 'type', '').lower()
            if "component" in s_type:
                current_type = ""
                if hasattr(shape, 'properties') and shape.properties:
                    current_type = shape.properties.get("node_type", "")
                elif hasattr(shape, 'node_type'):
                    current_type = shape.node_type

                # Rules for node type classification:
                if current_type and str(current_type).strip().lower() == "root":
                    new_type = "Root"
                elif shape.id not in incoming_ids:
                    # If no other node points to this component, it is the Root (the product itself)
                    new_type = "Root"
                elif shape.id in outgoing_ids:
                    # Has outgoing connections -> Intermediate (composite)
                    new_type = "Intermediate"
                else:
                    # No outgoing connections -> Leaf
                    new_type = "Leaf"

                # Apply calculated type to both property dicts and fields
                if hasattr(shape, 'properties') and shape.properties is not None:
                    shape.properties["node_type"] = new_type
                if hasattr(shape, 'node_type'):
                    shape.node_type = new_type

    @staticmethod
    def from_dict(data: dict) -> 'Diagram':
        """Deserialize a dictionary into a Diagram object, restoring its shapes, connections, and internal reference tracking states."""
        diagram = Diagram()
        diagram.metadata = data.get("metadata", diagram.metadata)
        diagram_data = data.get("diagram", {})
        canvas_size_data = diagram_data.get("canvas_size")
        diagram.canvas_size = tuple(canvas_size_data) if canvas_size_data else None
        diagram.zoom_level = diagram_data.get("zoom_level", 1.0)
        diagram.grid_enabled = diagram_data.get("grid_enabled", True)
        diagram.snap_to_grid = diagram_data.get("snap_to_grid", True)

        Shape.reset_counter()
        Connection.reset_counter()

        for shape_data in data.get("shapes", []):
            shape = Shape.from_dict(shape_data)
            diagram.shapes.append(shape)
            if shape.id >= Shape._id_counter:
                Shape._id_counter = shape.id

        for shape in diagram.shapes:
            if hasattr(shape, 'resolve_shape_references'):
                shape.resolve_shape_references(diagram.shapes)

        for conn_data in data.get("connections", []):
            connection = Connection.from_dict(conn_data, diagram.shapes)
            if connection:
                diagram.connections.append(connection)
                if connection.id >= Connection._id_counter:
                    Connection._id_counter = connection.id

        diagram.modified = False
        return diagram
