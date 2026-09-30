"""
Utilities package for Disassembly Flow Diagram
"""

from .geometry import (
    distance,
    angle_between_points,
    snap_to_grid,
    point_in_rect,
    rect_intersects,
    get_arrow_points,
    calculate_bezier_point as calculate_bezier_point,
    find_alignment_guides as find_alignment_guides,
    normalize_rect as normalize_rect,
    calculate_bounding_rect as calculate_bounding_rect,
)
from .commands import (
    Command,
    CommandHistory,
    AddShapeCommand,
    RemoveShapeCommand,
    MoveShapeCommand,
    AddConnectionCommand,
    RemoveConnectionCommand,
    EditShapePropertiesCommand,
    MultiCommand,
)
from .serializer import DiagramSerializer

__all__ = [
    "distance",
    "angle_between_points",
    "snap_to_grid",
    "point_in_rect",
    "rect_intersects",
    "get_arrow_points",
    "Command",
    "CommandHistory",
    "AddShapeCommand",
    "RemoveShapeCommand",
    "MoveShapeCommand",
    "AddConnectionCommand",
    "RemoveConnectionCommand",
    "EditShapePropertiesCommand",
    "MultiCommand",
    "DiagramSerializer",
]
