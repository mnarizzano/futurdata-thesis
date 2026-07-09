from typing import Tuple, Optional
from .shape import Shape


class Connection:
    _id_counter = 0

    def __init__(self, from_shape: Shape, to_shape: Shape,
                 connection_type: str = "solid",
                 from_anchor: str = "bottom",
                 to_anchor: str = "top"):
        """Initialize a connection between two shapes with anchor points."""
        Connection._id_counter += 1
        self.id = Connection._id_counter
        self.from_shape = from_shape
        self.to_shape = to_shape
        self.connection_type = connection_type
        self.from_anchor = from_anchor
        self.to_anchor = to_anchor
        self.arrow_id = None

    @classmethod
    def reset_counter(cls):
        """Reset the connection id counter."""
        cls._id_counter = 0

    def get_endpoints(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return the start and end coordinates of the connection."""
        from_points = self.from_shape.get_connection_points()
        to_points = self.to_shape.get_connection_points()
        start = from_points.get(self.from_anchor, (self.from_shape.x, self.from_shape.y))
        end = to_points.get(self.to_anchor, (self.to_shape.x, self.to_shape.y))
        return (start, end)

    def auto_calculate_anchors(self):
        """Pick anchor sides based on the relative position of the shapes."""
        dx = self.to_shape.x - self.from_shape.x
        dy = self.to_shape.y - self.from_shape.y
        if abs(dx) > abs(dy):
            self.from_anchor = 'right' if dx > 0 else 'left'
        else:
            self.from_anchor = 'bottom' if dy > 0 else 'top'
        if abs(dx) > abs(dy):
            self.to_anchor = 'left' if dx > 0 else 'right'
        else:
            self.to_anchor = 'top' if dy > 0 else 'bottom'

    def to_dict(self) -> dict:
        """Serialize the connection to a dictionary."""
        return {
            "id": self.id,
            "from_id": self.from_shape.id,
            "to_id": self.to_shape.id,
            "type": self.connection_type,
            "from_anchor": self.from_anchor,
            "to_anchor": self.to_anchor
        }

    @staticmethod
    def from_dict(data: dict, shapes: list) -> Optional['Connection']:
        """Rebuild a connection from a dictionary, resolving shape ids."""
        from_shape = None
        to_shape = None
        for shape in shapes:
            if shape.id == data["from_id"]:
                from_shape = shape
            if shape.id == data["to_id"]:
                to_shape = shape
        if from_shape is None or to_shape is None:
            return None
        connection = Connection(
            from_shape, to_shape,
            data.get("type", "solid"),
            data.get("from_anchor", "bottom"),
            data.get("to_anchor", "top")
        )
        connection.id = data["id"]
        return connection
