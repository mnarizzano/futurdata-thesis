from typing import Dict, Tuple, List
import math


class Shape:
    """Base class representing a generic visual diagram element with tracking coordinates and text properties."""
    _id_counter = 0

    def __init__(self, x: float, y: float, shape_type: str):
        """Initialize a new shape instance with base positional coordinates and a unique identifier."""
        Shape._id_counter += 1
        self.id = Shape._id_counter
        self.x = x
        self.y = y
        self.shape_type = shape_type
        self.text = ""
        self.shape_id = None
        self.text_id = None
        self.selected = False

    @classmethod
    def reset_counter(cls):
        """Reset the shared unique shape identifier counter back to zero."""
        cls._id_counter = 0

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate and return the bounding box coordinates (min_x, min_y, max_x, max_y) for the shape."""
        raise NotImplementedError()

    def get_connection_points(self) -> Dict[str, Tuple[float, float]]:
        """Retrieve the available attachment anchor points on the perimeter of the shape."""
        raise NotImplementedError()

    def contains_point(self, px: float, py: float) -> bool:
        """Determine whether a given (x, y) coordinate is located within the interior boundaries of the shape."""
        raise NotImplementedError()

    def move(self, dx: float, dy: float):
        """Adjust the base positional coordinates of the shape by the specified offsets."""
        self.x += dx
        self.y += dy

    def to_dict(self) -> dict:
        """Serialize the base attributes of the shape into a structured dictionary format."""
        return {
            "id": self.id,
            "type": self.shape_type,
            "x": self.x,
            "y": self.y,
            "text": self.text
        }

    @staticmethod
    def from_dict(data: dict) -> 'Shape':
        """Construct and restore a specific concrete Shape subclass instance from a serialized dictionary representation."""
        shape_type = data["type"]

        if shape_type == "product":
            # Backward compatibility: map legacy ProductBox to root ComponentBox.
            shape = ComponentBox(data["x"], data["y"])
            shape.properties["node_type"] = "Root"
            if data.get("text"):
                first_line = str(data.get("text", "")).splitlines()[0].strip()
                shape.properties["name"] = first_line
                shape.text = first_line or "Root Component"
            else:
                shape.text = "Root Component"
        elif shape_type == "action":
            shape = ActionCircle(data["x"], data["y"])
        elif shape_type == "diamond":
            shape = DiamondStep(data["x"], data["y"])
        elif shape_type == "component":
            shape = ComponentBox(data["x"], data["y"])
        elif shape_type == "arrow":
            shape = ArrowShape(data["x"], data["y"])
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")

        shape.id = data["id"]
        shape.text = data.get("text", "")

        if hasattr(shape, 'load_properties'):
            shape.load_properties(data)

        return shape


class ActionCircle(Shape):
    """Represents a circular process step shape with structural metadata for tools and custom descriptive context."""
    RADIUS = 60

    def __init__(self, x: float, y: float):
        """Initialize a new ActionCircle shape instance with default step attributes."""
        super().__init__(x, y, "action")
        self.text = "Step"
        self.step_description = ""
        self.tools = ""
        self.image_path = ""

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate and return the bounding box around the action circle based on its radius."""
        r = self.RADIUS
        return (self.x - r, self.y - r, self.x + r, self.y + r)

    def get_connection_points(self) -> Dict[str, Tuple[float, float]]:
        """Compute top, bottom, left, and right peripheral connection coordinates for the circle."""
        r = self.RADIUS
        return {
            'top': (self.x, self.y - r),
            'bottom': (self.x, self.y + r),
            'left': (self.x - r, self.y),
            'right': (self.x + r, self.y)
        }

    def contains_point(self, px: float, py: float) -> bool:
        """Verify if a specific coordinate sits inside the perimeter using the standard circle radius formula."""
        distance = math.sqrt((px - self.x)**2 + (py - self.y)**2)
        return distance <= self.RADIUS

    def to_dict(self) -> dict:
        """Serialize the specific process step properties along with the base shape dictionary."""
        data = super().to_dict()
        data.update({
            "step_description": self.step_description,
            "tools": self.tools,
            "image_path": self.image_path
        })
        return data

    def load_properties(self, data: dict):
        """Populate step-specific fields and metadata attributes from serialized dictionary data."""
        self.step_description = data.get("step_description", "")
        self.tools = data.get("tools", "")
        self.image_path = data.get("image_path", "")


class DiamondStep(Shape):
    """Represents a diamond-shaped decision or action element with specific identifier tracking and assigned tool associations."""
    SIZE = 100

    def __init__(self, x: float, y: float):
        """Initialize a new DiamondStep shape instance with default decision attributes."""
        super().__init__(x, y, "diamond")
        self.text = "Action"
        self.action_id = ""
        self.name = ""
        self.description = ""
        self.tool_id = None
        self.tools = ""
        self.image_path = ""

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate the rectangular outer bounding box surrounding the diamond shape."""
        half = self.SIZE / 2
        return (self.x - half, self.y - half, self.x + half, self.y + half)

    def get_connection_points(self) -> Dict[str, Tuple[float, float]]:
        """Compute the corner vertices of the diamond to serve as primary peripheral attachment points."""
        half = self.SIZE / 2
        return {
            'top': (self.x, self.y - half),
            'bottom': (self.x, self.y + half),
            'left': (self.x - half, self.y),
            'right': (self.x + half, self.y)
        }

    def contains_point(self, px: float, py: float) -> bool:
        """Determine if a coordinate is within the diamond perimeter using absolute manhattan-distance limits."""
        dx = abs(px - self.x)
        dy = abs(py - self.y)
        half = self.SIZE / 2
        return (dx + dy) <= half

    def to_dict(self) -> dict:
        """Serialize the custom decision and tool property fields alongside the core shape dataset."""
        data = super().to_dict()
        data.update({
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "tool_id": self.tool_id,
            "tools": self.tools,
            "image_path": self.image_path
        })
        return data

    def load_properties(self, data: dict):
        """Unpack custom decision properties, description text, and tool IDs from serialized dictionary state."""
        self.action_id = data.get("action_id", "")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.tool_id = data.get("tool_id")
        self.tools = data.get("tools", "")
        self.image_path = data.get("image_path", "")


class ComponentBox(Shape):
    """
    Component shape with fully dynamic properties.
    Properties are stored in a dict - matches database columns directly.
    Add new column to database = new property automatically available.
    """
    WIDTH = 160
    HEIGHT = 80

    # Default properties - these match database column names exactly
    DEFAULT_PROPERTIES = {
        'name': '',
        'brand': '',
        'model': '',
        'description': '',
        'root_component_id': None,
        'color_id': None,
        'material_id': None,
        'weight': '',
        'weight_unit': 'g',
        'node_type': '', # 'Root', 'Leaf', or '' (intermediate)
        'image_path': ''
    }

    def __init__(self, x: float, y: float):
        """Initialize a new rectangular component box with fully decoupled dynamic property mapping fields."""
        super().__init__(x, y, "component")
        self.text = "Component"
        # Dynamic properties dict - stores all component properties
        self.properties = dict(self.DEFAULT_PROPERTIES)

    # Property accessors for backward compatibility
    @property
    def component_name(self):
        """Get the localized or underlying descriptive name property of the component."""
        return self.properties.get('name', '')

    @component_name.setter
    def component_name(self, value):
        """Set the underlying name property in the dynamic parameters dictionary."""
        self.properties['name'] = value

    @property
    def color_id(self):
        """Get the database table identifier tracking the component color attribute."""
        return self.properties.get('color_id', None)

    @color_id.setter
    def color_id(self, value):
        """Set the assigned database identifier tracking the component color attribute."""
        self.properties['color_id'] = value

    @property
    def material_id(self):
        """Get the database table identifier tracking the component material property attribute."""
        return self.properties.get('material_id', None)

    @material_id.setter
    def material_id(self, value):
        """Set the assigned database identifier tracking the component material property attribute."""
        self.properties['material_id'] = value

    @property
    def weight(self):
        """Get the character or numeric measurement value string representing the physical item weight."""
        return self.properties.get('weight', '')

    @weight.setter
    def weight(self, value):
        """Set the character or numeric measurement value string representing the physical item weight."""
        self.properties['weight'] = value

    @property
    def weight_unit(self):
        """Get the current physical mass context metric suffix code (e.g. 'g', 'kg')."""
        return self.properties.get('weight_unit', 'g')

    @weight_unit.setter
    def weight_unit(self, value):
        """Set the current physical mass context metric suffix code (e.g. 'g', 'kg')."""
        self.properties['weight_unit'] = value

    @property
    def node_type(self):
        """Get the hierarchical placement structure designation flag ('Root', 'Leaf', or empty)."""
        return self.properties.get('node_type', '')

    @node_type.setter
    def node_type(self, value):
        """Set the hierarchical placement structure designation flag ('Root', 'Leaf', or empty)."""
        self.properties['node_type'] = value

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate and return the bounding box coordinates using predefined dimensional box widths and heights."""
        half_w = self.WIDTH / 2
        half_h = self.HEIGHT / 2
        return (self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h)

    def get_connection_points(self) -> Dict[str, Tuple[float, float]]:
        """Retrieve structural alignment coordinates on midpoints of the outer rectangular box faces."""
        half_h = self.HEIGHT / 2
        half_w = self.WIDTH / 2
        return {
            'top': (self.x, self.y - half_h),
            'bottom': (self.x, self.y + half_h),
            'left': (self.x - half_w, self.y),
            'right': (self.x + half_w, self.y)
        }

    def contains_point(self, px: float, py: float) -> bool:
        """Verify if target point coordinates intersect inside this bounding block area."""
        x1, y1, x2, y2 = self.get_bounds()
        return x1 <= px <= x2 and y1 <= py <= y2

    def to_dict(self) -> dict:
        """Serialize custom component mapping attributes, storing properties dynamically while retaining legacy key indexes."""
        data = super().to_dict()
        # Save all properties from dict - fully dynamic
        data.update(self.properties)
        # Keep backward compatibility key
        data['component_name'] = self.properties.get('name', '')
        return data

    def load_properties(self, data: dict):
        """Reconstruct full dictionary properties dynamically from data while parsing standard legacy key index targets safely."""
        # Load all properties dynamically
        for key, value in data.items():
            if key not in ['id', 'type', 'x', 'y', 'text']:
                # Map old 'component_name' to 'name'
                if key == 'component_name':
                    self.properties['name'] = value
                else:
                    self.properties[key] = value


class ArrowShape(Shape):
    """Represents a directional vector connecting two structural shapes, updating paths dynamically as endpoints modify."""
    LENGTH = 150
    WIDTH = 10

    def __init__(self, x: float, y: float, from_shape=None, to_shape=None):
        """Initialize an ArrowShape instance, binding references to endpoint tracking elements if provided."""
        super().__init__(x, y, "arrow")
        self.text = ""
        self.from_shape = from_shape
        self.to_shape = to_shape
        self.from_anchor = "bottom"
        self.to_anchor = "top"

        if from_shape and to_shape:
            self.update_from_shapes()
        else:
            self.angle = 0
            self.end_x = x + self.LENGTH
            self.end_y = y

    def update_from_shapes(self):
        """Synchronize start and end vector coordinates automatically based on the positions of bound structural elements."""
        if self.from_shape and self.to_shape:
            self.auto_calculate_anchors()
            from_points = self.from_shape.get_connection_points()
            to_points = self.to_shape.get_connection_points()
            start = from_points.get(self.from_anchor, (self.from_shape.x, self.from_shape.y))
            end = to_points.get(self.to_anchor, (self.to_shape.x, self.to_shape.y))
            self.x, self.y = start
            self.end_x, self.end_y = end
            dx = self.end_x - self.x
            dy = self.end_y - self.y
            self.angle = math.degrees(math.atan2(dy, dx))

    def auto_calculate_anchors(self):
        """Evaluate relative offsets of bound shapes to systematically select closest peripheral facing anchor directions."""
        if not (self.from_shape and self.to_shape):
            return
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

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Obtain a dynamic bounding region containing both vector endpoints wrapped within protective padding bounds."""
        if self.from_shape and self.to_shape:
            self.update_from_shapes()
        padding = 15
        x1 = min(self.x, self.end_x) - padding
        y1 = min(self.y, self.end_y) - padding
        x2 = max(self.x, self.end_x) + padding
        y2 = max(self.y, self.end_y) + padding
        return (x1, y1, x2, y2)

    def get_connection_points(self) -> Dict[str, Tuple[float, float]]:
        """Compute alignment context points evaluated along the center line span or endpoints of the arrow axis."""
        if self.from_shape and self.to_shape:
            self.update_from_shapes()
        mid_x = (self.x + self.end_x) / 2
        mid_y = (self.y + self.end_y) / 2
        return {
            'top': (mid_x, mid_y - 20),
            'bottom': (mid_x, mid_y + 20),
            'left': (self.x, self.y),
            'right': (self.end_x, self.end_y)
        }

    def contains_point(self, px: float, py: float) -> bool:
        """Determine if user cursor position lands close enough to vector axis lines within specified threshold margins."""
        if self.from_shape and self.to_shape:
            self.update_from_shapes()
        line_length_sq = (self.end_x - self.x) ** 2 + (self.end_y - self.y) ** 2
        if line_length_sq == 0:
            distance = math.sqrt((px - self.x) ** 2 + (py - self.y) ** 2)
        else:
            t = max(0, min(1, ((px - self.x) * (self.end_x - self.x) +
                               (py - self.y) * (self.end_y - self.y)) / line_length_sq))
            proj_x = self.x + t * (self.end_x - self.x)
            proj_y = self.y + t * (self.end_y - self.y)
            distance = math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)
        return distance <= 10

    def to_dict(self) -> dict:
        """Serialize positional coordinates, geometric angles, and corresponding tracking IDs into standard schema fields."""
        data = super().to_dict()
        data.update({
            "angle": self.angle,
            "end_x": self.end_x,
            "end_y": self.end_y,
            "from_shape_id": self.from_shape.id if self.from_shape else None,
            "to_shape_id": self.to_shape.id if self.to_shape else None,
            "from_anchor": self.from_anchor,
            "to_anchor": self.to_anchor
        })
        return data

    def load_properties(self, data: dict):
        """Restore directional orientations, anchor fields, and placeholder tracking IDs from raw serialized dataset configurations."""
        self.angle = data.get("angle", 0)
        self.end_x = data.get("end_x", self.x + self.LENGTH)
        self.end_y = data.get("end_y", self.y)
        self.from_anchor = data.get("from_anchor", "bottom")
        self.to_anchor = data.get("to_anchor", "top")
        self._from_shape_id = data.get("from_shape_id")
        self._to_shape_id = data.get("to_shape_id")

    def resolve_shape_references(self, shapes: list):
        """Resolve shape IDs to actual shape references after all shapes are loaded."""
        if hasattr(self, '_from_shape_id') and self._from_shape_id is not None:
            for shape in shapes:
                if shape.id == self._from_shape_id:
                    self.from_shape = shape
                    break
        if hasattr(self, '_to_shape_id') and self._to_shape_id is not None:
            for shape in shapes:
                if shape.id == self._to_shape_id:
                    self.to_shape = shape
                    break
