from typing import List, Optional, Tuple
from datetime import datetime
from uuid import uuid4
from .shape import Shape, ArrowShape
from .connection import Connection


class Diagram:
    def __init__(self):
        self.diagram_id = str(uuid4())
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
        self.canvas_size = None  
        self.zoom_level = 1.0
        self.grid_enabled = True
        self.snap_to_grid = True
        self.modified = False
        self.file_path = None
        self.auto_sync_json = True 
        self.last_json_sync = None  

    def add_shape(self, shape: Shape):
        if isinstance(shape, ArrowShape) and self.has_edge(shape.from_shape, shape.to_shape):
            return
        self.shapes.append(shape)
        self.modified = True

    def remove_shape(self, shape: Shape):
        self.connections = [
            conn for conn in self.connections
            if conn.from_shape != shape and conn.to_shape != shape
        ]
        if shape in self.shapes:
            self.shapes.remove(shape)
        if shape in self.selected_shapes:
            self.selected_shapes.remove(shape)
        self.modified = True

    def has_edge(self, source, target):
        if source is None or target is None:
            return False
        return any(edge.from_shape is source and edge.to_shape is target
                   for edge in [*self.connections,
                                *(s for s in self.shapes if isinstance(s, ArrowShape))])

    def deduplicate_edges(self):
        """Normalize legacy mixed edge records at load boundaries, retaining arrows."""
        seen = set()
        shapes = []
        for shape in self.shapes:
            if isinstance(shape, ArrowShape) and shape.from_shape and shape.to_shape:
                key = (shape.from_shape.id, shape.to_shape.id)
                if key in seen:
                    continue
                seen.add(key)
            shapes.append(shape)
        self.shapes = shapes
        connections = []
        for edge in self.connections:
            key = (edge.from_shape.id, edge.to_shape.id)
            if key not in seen:
                connections.append(edge)
                seen.add(key)
        self.connections = connections

    def add_connection(self, connection: Connection):
        if self.has_edge(connection.from_shape, connection.to_shape):
            return
        self.connections.append(connection)
        self.modified = True

    def remove_connection(self, connection: Connection):
        if connection in self.connections:
            self.connections.remove(connection)
            self.modified = True

    def get_shape_by_id(self, shape_id: int) -> Optional[Shape]:
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
        return None

    def find_shape_at_point(self, x: float, y: float) -> Optional[Shape]:
        for shape in reversed(self.shapes):
            if shape.contains_point(x, y):
                return shape
        return None

    def find_shapes_in_rect(self, x1: float, y1: float, x2: float, y2: float) -> List[Shape]:
        shapes_in_rect = []
        for shape in self.shapes:
            if x1 <= shape.x <= x2 and y1 <= shape.y <= y2:
                shapes_in_rect.append(shape)
        return shapes_in_rect

    def select_shape(self, shape: Shape, multi_select: bool = False):
        if not multi_select:
            self.clear_selection()
        if shape not in self.selected_shapes:
            self.selected_shapes.append(shape)
            shape.selected = True

    def deselect_shape(self, shape: Shape):
        if shape in self.selected_shapes:
            self.selected_shapes.remove(shape)
            shape.selected = False

    def clear_selection(self):
        for shape in self.selected_shapes:
            shape.selected = False
        self.selected_shapes.clear()

    def get_connections_for_shape(self, shape: Shape) -> List[Connection]:
        return [
            conn for conn in self.connections
            if conn.from_shape == shape or conn.to_shape == shape
        ]

    def clear(self):
        self.diagram_id = str(uuid4())
        self.shapes.clear()
        self.connections.clear()
        self.selected_shapes.clear()
        Shape.reset_counter()
        Connection.reset_counter()
        self.modified = False
        self.file_path = None

    def get_bounds(self) -> Tuple[float, float, float, float]:
        if not self.shapes:
            return (0, 0, 0, 0)
        min_x = min(shape.x for shape in self.shapes)
        min_y = min(shape.y for shape in self.shapes)
        max_x = max(shape.x for shape in self.shapes)
        max_y = max(shape.y for shape in self.shapes)
        return (min_x, min_y, max_x, max_y)

    def to_dict(self) -> dict:
        return {
            "diagram_id": self.diagram_id,
            "metadata": dict(self.metadata),
            "diagram": {
                "canvas_size": self.canvas_size,
                "zoom_level": self.zoom_level,
                "grid_enabled": self.grid_enabled,
                "snap_to_grid": self.snap_to_grid
            },
            "shapes": [shape.to_dict() for shape in self.shapes],
            "connections": [conn.to_dict() for conn in self.connections]
        }

    @staticmethod
    def from_dict(data: dict) -> 'Diagram':
        diagram = Diagram()
        diagram.diagram_id = data.get("diagram_id") or diagram.diagram_id
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

        diagram.deduplicate_edges()
        diagram.modified = False
        return diagram
