import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Tuple
import math

from ..models import Shape, ActionCircle, DiamondStep, ComponentBox, ArrowShape, Connection
from ..utils.geometry import get_arrow_points


class DiagramCanvas(tk.Canvas):
    GRID_SIZE = 50
    GRID_COLOR = "#e0e0e0"
    SELECT_COLOR = "#667eea"
    GUIDE_COLOR = "#ff6b6b"
    ACTION_FILL = "white"
    DIAMOND_FILL = "white"
    COMPONENT_FILL = "white"
    BORDER_COLOR = "black"

    MIN_CANVAS_WIDTH = 2000
    MIN_CANVAS_HEIGHT = 2000
    EXPANSION_MARGIN = 500

    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', 'white')
        kwargs.setdefault('highlightthickness', 0)
        super().__init__(parent, **kwargs)
        self.canvas_width = self.MIN_CANVAS_WIDTH
        self.canvas_height = self.MIN_CANVAS_HEIGHT
        self.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.show_grid = True
        self.snap_to_grid = True
        self.alignment_guides = {'vertical': [], 'horizontal': []}
        self.draw_grid()

    def expand_canvas_if_needed(self, x: float, y: float, margin: float = 100, redraw_grid: bool = False) -> bool:
        """Expand canvas if point is near the edge. Returns True if expanded."""
        expanded = False

        # Check if we need to expand width
        if x > self.canvas_width - margin:
            self.canvas_width = int(x + self.EXPANSION_MARGIN)
            expanded = True

        # Check if we need to expand height
        if y > self.canvas_height - margin:
            self.canvas_height = int(y + self.EXPANSION_MARGIN)
            expanded = True

        if expanded:
            self.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            if redraw_grid:
                self.draw_grid()

        return expanded

    def auto_scroll(self, event_x: int, event_y: int, scroll_margin: int = 50, scroll_amount: int = 20):
        """Auto-scroll canvas when mouse is near the edge during drag."""
        # Get visible area dimensions
        visible_width = self.winfo_width()
        visible_height = self.winfo_height()

        scrolled = False

        # Scroll right
        if event_x > visible_width - scroll_margin:
            self.xview_scroll(1, "units")
            scrolled = True
        # Scroll left
        elif event_x < scroll_margin:
            self.xview_scroll(-1, "units")
            scrolled = True

        # Scroll down
        if event_y > visible_height - scroll_margin:
            self.yview_scroll(1, "units")
            scrolled = True
        # Scroll up
        elif event_y < scroll_margin:
            self.yview_scroll(-1, "units")
            scrolled = True

        return scrolled
    
    def scroll_to_shape(self, shape: Shape):
        """
        Scroll canvas to make shape visible in viewport.
        
        Args:
            shape: Shape to scroll to
        """
        if not shape:
            return
        
        # Get shape position
        shape_x = shape.x
        shape_y = shape.y
        
        # Get visible area
        visible_width = self.winfo_width()
        visible_height = self.winfo_height()
        
        if visible_width <= 1 or visible_height <= 1:
            # Canvas not yet rendered, schedule for later
            self.after(100, lambda: self.scroll_to_shape(shape))
            return
        
        # Get current scroll position (as fractions 0.0 to 1.0)
        x_view = self.xview()
        y_view = self.yview()
        
        # Current visible area in canvas coordinates
        visible_x1 = x_view[0] * self.canvas_width
        visible_x2 = x_view[1] * self.canvas_width
        visible_y1 = y_view[0] * self.canvas_height
        visible_y2 = y_view[1] * self.canvas_height
        
        # Check if shape is already fully visible with some margin
        margin = 100
        if (visible_x1 + margin < shape_x < visible_x2 - margin and
            visible_y1 + margin < shape_y < visible_y2 - margin):
            # Already visible, no need to scroll
            return
        
        # Calculate target scroll position to center the shape
        target_x = shape_x - (visible_width / 2)
        target_y = shape_y - (visible_height / 2)
        
        # Clamp to valid range
        target_x = max(0, min(target_x, self.canvas_width - visible_width))
        target_y = max(0, min(target_y, self.canvas_height - visible_height))
        
        # Convert to fractions
        x_fraction = target_x / self.canvas_width if self.canvas_width > 0 else 0
        y_fraction = target_y / self.canvas_height if self.canvas_height > 0 else 0
        
        # Scroll to position
        self.xview_moveto(x_fraction)
        self.yview_moveto(y_fraction)

    def update_scroll_region_from_shapes(self, shapes) -> None:
        """Update scroll region to encompass all shapes with padding."""
        if not shapes:
            self.canvas_width = self.MIN_CANVAS_WIDTH
            self.canvas_height = self.MIN_CANVAS_HEIGHT
        else:
            max_x = max(shape.x + 200 for shape in shapes)  # Add padding for shape size
            max_y = max(shape.y + 200 for shape in shapes)
            self.canvas_width = max(self.MIN_CANVAS_WIDTH, int(max_x + self.EXPANSION_MARGIN))
            self.canvas_height = max(self.MIN_CANVAS_HEIGHT, int(max_y + self.EXPANSION_MARGIN))

        self.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.draw_grid()

    def draw_grid(self):
        if not self.show_grid:
            return
        x1, y1 = 0, 0
        x2, y2 = self.canvas_width, self.canvas_height
        self.delete("grid")
        for x in range(0, x2 + 1, self.GRID_SIZE):
            self.create_line(x, y1, x, y2, fill=self.GRID_COLOR, tags="grid")
        for y in range(0, y2 + 1, self.GRID_SIZE):
            self.create_line(x1, y, x2, y, fill=self.GRID_COLOR, tags="grid")
        self.tag_lower("grid")

    def draw_shape(self, shape: Shape) -> None:
        if shape.shape_id is not None:
            self.delete(shape.shape_id)
        if shape.text_id is not None:
            self.delete(shape.text_id)

        if isinstance(shape, ActionCircle):
            self._draw_action_circle(shape)
        elif isinstance(shape, DiamondStep):
            self._draw_diamond_step(shape)
        elif isinstance(shape, ComponentBox):
            self._draw_component_box(shape)
        elif isinstance(shape, ArrowShape):
            self._draw_arrow_shape(shape)

        if shape.selected:
            self._draw_selection(shape)

    def _draw_action_circle(self, shape: ActionCircle):
        x1, y1, x2, y2 = shape.get_bounds()
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        shape.shape_id = self.create_oval(
            x1, y1, x2, y2, fill=self.ACTION_FILL, outline=border_color, width=border_width, tags="shape"
        )
        shape.text_id = self.create_text(
            shape.x, shape.y, text=shape.text, font=("Arial", 9), fill="black", 
            width=75, tags="shape_text"
        )

    def _draw_diamond_step(self, shape: DiamondStep):
        half = shape.SIZE / 2
        points = [
            shape.x, shape.y - half,
            shape.x + half, shape.y,
            shape.x, shape.y + half,
            shape.x - half, shape.y
        ]
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        shape.shape_id = self.create_polygon(
            points, fill=self.DIAMOND_FILL, outline=border_color, width=border_width, tags="shape"
        )
        shape.text_id = self.create_text(
            shape.x, shape.y, text=shape.text, font=("Arial", 8), fill="black", 
            width=65, tags="shape_text"
        )

    def _draw_component_box(self, shape: ComponentBox):
        x1, y1, x2, y2 = shape.get_bounds()
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        
        # Determine fill color based on node type and color_id
        fill_color = self.COMPONENT_FILL
        node_type = str(shape.properties.get('node_type', '')).strip().lower()
        color_id = shape.properties.get('color_id')
        
        # If it's a leaf node with a color selected, use that color
        if node_type == "leaf" and color_id:
            try:
                from ..models.database import get_database
                db = get_database()
                color_data = db.get_color(int(color_id))
                if color_data and color_data.get('hex_code'):
                    fill_color = color_data['hex_code']
            except Exception:
                pass  # Fall back to default white if error occurs
        
        shape.shape_id = self.create_rectangle(
            x1, y1, x2, y2, fill=fill_color, outline=border_color, width=border_width, tags="shape"
        )
        shape.text_id = self.create_text(
            shape.x, shape.y, text=shape.text, font=("Arial", 9), fill="black", 
            width=145, tags="shape_text"
        )

    def _draw_arrow_shape(self, shape: ArrowShape):
        if shape.from_shape and shape.to_shape:
            shape.update_from_shapes()
        end_x = shape.end_x
        end_y = shape.end_y
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        shape.shape_id = self.create_line(
            shape.x, shape.y, end_x, end_y, fill=border_color, width=border_width,
            arrow=tk.LAST, arrowshape=(12, 15, 6), tags="shape"
        )
        shape.text_id = None

    def _draw_selection(self, shape: Shape):
        pass

    def draw_connection(self, connection: Connection) -> None:
        if connection.arrow_id is not None:
            self.delete(connection.arrow_id)
        (x1, y1), (x2, y2) = connection.get_endpoints()
        dash = (5, 5) if connection.connection_type == "dashed" else None
        connection.arrow_id = self.create_line(
            x1, y1, x2, y2, fill=self.BORDER_COLOR, width=2,
            arrow=tk.LAST, arrowshape=(10, 12, 5), dash=dash, tags="connection"
        )
        self.tag_lower("connection", "shape")

    def draw_alignment_guides(self, guides: dict):
        self.delete("guide")
        for x in guides.get('vertical', []):
            self.create_line(x, 0, x, self.canvas_height, fill=self.GUIDE_COLOR, width=1, dash=(4, 4), tags="guide")
        for y in guides.get('horizontal', []):
            self.create_line(0, y, self.canvas_width, y, fill=self.GUIDE_COLOR, width=1, dash=(4, 4), tags="guide")

    def clear_alignment_guides(self):
        self.delete("guide")

    def clear_canvas(self):
        self.delete("shape")
        self.delete("shape_text")
        self.delete("connection")
        self.delete("guide")

    def redraw_all(self, diagram):
        self.clear_canvas()
        for connection in diagram.connections:
            self.draw_connection(connection)
        for shape in diagram.shapes:
            self.draw_shape(shape)

    def update_shape(self, shape: Shape):
        self.draw_shape(shape)

    def update_connection(self, connection: Connection):
        self.draw_connection(connection)

    def move_items(self, shape: Shape, dx: float, dy: float):
        """Move shape's canvas items by dx, dy - much faster than redrawing."""
        if shape.shape_id is not None:
            self.move(shape.shape_id, dx, dy)
        if shape.text_id is not None:
            self.move(shape.text_id, dx, dy)

    def update_connections_for_shapes(self, shapes: List[Shape], diagram):
        """Update only connections attached to the given shapes."""
        for conn in diagram.connections:
            if conn.from_shape in shapes or conn.to_shape in shapes:
                self.draw_connection(conn)

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.show_grid:
            self.draw_grid()
        else:
            self.delete("grid")

    def zoom_in(self):
        pass

    def zoom_out(self):
        pass

    def reset_zoom(self):
        pass
