import math
from typing import Tuple, List


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calculates the straight-line Euclidean distance between two 2D coordinate points.

    Args:
        p1 (Tuple[float, float]): The coordinates of the first point (x1, y1).
        p2 (Tuple[float, float]): The coordinates of the second point (x2, y2).

    Returns:
        float: The calculated straight-line distance.
    """
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def angle_between_points(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Computes the absolute polar angle of a vector pointing from p1 to p2 relative to the positive X-axis.

    Args:
        p1 (Tuple[float, float]): The origin anchor point (x1, y1).
        p2 (Tuple[float, float]): The target destination point (x2, y2).

    Returns:
        float: The directional angle measured in radians, ranging between -pi and pi.
    """
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])


def snap_to_grid(x: float, y: float, grid_size: int = 50) -> Tuple[float, float]:
    """
    Snaps an arbitrary coordinate position to the nearest intersection point on a uniform spacing grid.

    Args:
        x (float): The unaligned horizontal coordinate position.
        y (float): The unaligned vertical coordinate position.
        grid_size (int): The uniform dimensions of each grid block increment. Defaults to 50.

    Returns:
        Tuple[float, float]: A pair of snapped (x, y) coordinates representing the nearest intersection.
    """
    snapped_x = round(x / grid_size) * grid_size
    snapped_y = round(y / grid_size) * grid_size
    return (snapped_x, snapped_y)


def point_in_rect(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    """
    Determines whether a single test coordinate point resides inside a defined rectangular box boundary.

    Args:
        px (float): Horizontal position coordinate of the target test point.
        py (float): Vertical position coordinate of the target test point.
        x1 (float): Horizontal coordinate value marking the left edge.
        y1 (float): Vertical coordinate value marking the top edge.
        x2 (float): Horizontal coordinate value marking the right edge.
        y2 (float): Vertical coordinate value marking the bottom edge.

    Returns:
        bool: True if the coordinate falls strictly within or on the rectangle borders, False otherwise.
    """
    return x1 <= px <= x2 and y1 <= py <= y2


def rect_intersects(r1: Tuple[float, float, float, float], r2: Tuple[float, float, float, float]) -> bool:
    """
    Evaluates whether two Axis-Aligned Bounding Boxes (AABB) overlap or collide on a 2D space canvas.

    Args:
        r1 (Tuple[float, float, float, float]): First boundary coordinates (x1, y1, x2, y2).
        r2 (Tuple[float, float, float, float]): Second boundary coordinates (x3, y3, x4, y4).

    Returns:
        bool: True if the two rectangular zones intersect or share space, False if they are separated.
    """
    x1, y1, x2, y2 = r1
    x3, y3, x4, y4 = r2
    return not (x2 < x3 or x4 < x1 or y2 < y3 or y4 < y1)


def get_arrow_points(x1: float, y1: float, x2: float, y2: float, arrow_size: int = 10) -> List[Tuple[float, float]]:
    """
    Calculates the 2D path coordinates required to render a directional triangular arrowhead 
    at the tip of a vector line.

    Args:
        x1 (float): Starting horizontal origin point of the line path.
        y1 (float): Starting vertical origin point of the line path.
        x2 (float): Terminal horizontal point where the arrowhead tip sits.
        y2 (float): Terminal vertical point where the arrowhead tip sits.
        arrow_size (int): Length scale constraint of the flanking wing elements. Defaults to 10.

    Returns:
        List[Tuple[float, float]]: A list containing exactly three corner coordinate pairs: [(tip_x, tip_y), (wing1_x, wing1_y), (wing2_x, wing2_y)].
    """
    angle = math.atan2(y2 - y1, x2 - x1)
    angle1 = angle + math.pi * 0.85
    angle2 = angle - math.pi * 0.85
    x3 = x2 - arrow_size * math.cos(angle1)
    y3 = y2 - arrow_size * math.sin(angle1)
    x4 = x2 - arrow_size * math.cos(angle2)
    y4 = y2 - arrow_size * math.sin(angle2)
    return [(x2, y2), (x3, y3), (x4, y4)]


def calculate_bezier_point(t: float, p0: Tuple[float, float], p1: Tuple[float, float],
                           p2: Tuple[float, float], p3: Tuple[float, float]) -> Tuple[float, float]:
    """
    Evaluates Bernstein basis polynomials to calculate an explicit 2D coordinate on a Cubic Bezier curve.

    Args:
        t (float): Parametric interpolation progression scale factor ranging from 0.0 to 1.0.
        p0 (Tuple[float, float]): Starting coordinate vertex anchor (x, y).
        p1 (Tuple[float, float]): First directional control handle vertex (x, y).
        p2 (Tuple[float, float]): Second directional control handle vertex (x, y).
        p3 (Tuple[float, float]): Destination ending coordinate vertex anchor (x, y).

    Returns:
        Tuple[float, float]: The calculated (x, y) intersection location mapped to value t along the curve.
    """
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def find_alignment_guides(moving_shape, other_shapes, tolerance: int = 5) -> dict:
    """
    Compares the center anchor position of a moving component against static layout items 
    to locate nearby alignment thresholds.

    Args:
        moving_shape (any): The active shape model currently undergoing drag displacement.
        other_shapes (Iterable[any]): Collection of stationary canvas shapes to match against.
        tolerance (int): Max screen pixel offset allowable to trigger alignment guides. Defaults to 5.

    Returns:
        dict: A tracking dictionary structure containing two matching keys: {'vertical': [matching_x_coords], 'horizontal': [matching_y_coords]}.
    """
    guides = {'vertical': [], 'horizontal': []}
    for shape in other_shapes:
        if shape == moving_shape:
            continue
        if abs(moving_shape.x - shape.x) < tolerance:
            guides['vertical'].append(shape.x)
        if abs(moving_shape.y - shape.y) < tolerance:
            guides['horizontal'].append(shape.y)
    return guides


def normalize_rect(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float, float]:
    """
    Standardizes loose drag-selection coordinates into structured bounding values where 
    min points are on the left/top and max points are on the right/bottom.

    Args:
        x1 (float): Initial horizontal screen cursor point.
        y1 (float): Initial vertical screen cursor point.
        x2 (float): Terminal horizontal drag boundary point.
        y2 (float): Terminal vertical drag boundary point.

    Returns:
        Tuple[float, float, float, float]: Standardized coordinate format (left_x, top_y, right_x, bottom_y).
    """
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def calculate_bounding_rect(points: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """
    Calculates the minimal bounding envelope enclosing an unstructured array of 2D coordinates.

    Args:
        points (List[Tuple[float, float]]): Collection array containing coordinate tuple vectors.

    Returns:
        Tuple[float, float, float, float]: Bounding window envelope format (min_x, min_y, max_x, max_y). Returns (0, 0, 0, 0) if the input list is empty.
    """
    if not points:
        return (0, 0, 0, 0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))
