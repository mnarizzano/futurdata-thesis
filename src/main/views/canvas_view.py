import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Tuple
import math

from ..models import Shape, ActionCircle, DiamondStep, ComponentBox, ArrowShape, Connection
from ..utils.geometry import get_arrow_points


class DiagramCanvas(tk.Canvas):
    """
    A specialized Tkinter Canvas workspace customized for rendering, scaling,
    and interacting with graph diagram models such as boxes, actions, and connectives.
    """
    GRID_SIZE = 50
    GRID_COLOR = "#e0e0e0"
    SELECT_COLOR = "#667eea"
    GUIDE_COLOR = "#ff6b6b"
    ACTION_FILL = "white"
    DIAMOND_FILL = "white"
    COMPONENT_FILL = "white"
    BORDER_COLOR = "black"
    #added colors for root, leaf and intermediate components
    #plus constants for leaf corner radius and intermediate cut
    ROOT_COMPONENT_OUTLINE = "#1f2937"
    LEAF_COMPONENT_OUTLINE = "#15803d"
    INTERMEDIATE_COMPONENT_OUTLINE = "#92400e"
    LEAF_COMPONENT_FILL = "#ecfdf5"
    LEAF_CORNER_RADIUS = 60
    INTERMEDIATE_CUT = 18

    MIN_CANVAS_WIDTH = 2000
    MIN_CANVAS_HEIGHT = 2000
    EXPANSION_MARGIN = 500



    def __init__(self, parent, **kwargs):
        """
        Initializes the diagram workspace viewport panel, establishing bounding configurations,
        tracking flags, alignment matrix properties, and base grid structures.

        Args:
            parent (any): The parent Tkinter container view nesting this widget.
            **kwargs: Dictated configuration attributes passed directly to the tk.Canvas base.
        """
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
        self.zoom_factor = 1.0
        self.diagram = None

    def expand_canvas_if_needed(self, x: float, y: float, margin: float = 100, redraw_grid: bool = False) -> bool:
        """Expands canvas if point is near the edge. Returns True if expanded."""
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
            shape: Shape to scroll to.
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
        """Updates scroll region to encompass all shapes with padding."""
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
        """Renders the grid overlay pattern onto the canvas background using default constants."""
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
        """
        Clears existing instances of a shape model from the canvas and triggers 
        the appropriate specialized drawing routine based on its class type.

        Args:
            shape (Shape): The concrete instance model element requiring drawing.
        """
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
        """
        Generates graphical oval lines and internal metadata labels for an ActionCircle shape.

        Args:
            shape (ActionCircle): The target action model entity.
        """
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
        """
        Generates diamond polygon outlines and text tags for a DiamondStep shape.

        Args:
            shape (DiamondStep): The target diamond step element.
        """
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
    
    """method that creates a rounded leaf box clockwise from the top-left corner
        x1 and y1 are the coordinates of the top-left corner, x2 and y2 are the coordinates of the bottom-right corner, 
        radius is the radius of the rounded corners""" 
    def _create_rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle on the canvas for leaf nodes."""
        radius = min(radius, abs((x2 - x1) / 2), abs((y2 - y1) / 2))            #limit radius to half the width or height to avoid overlap
        segments = 16           #number of segments to approximate the rounded corners
        points = []             #will hold the points for the rounded rectangle

        # Add points of the top edge
        points.append((x1 + radius, y1))
        points.append((x2 - radius, y1))

        # Top-right corner
        for i in range(segments + 1):
            angle = -math.pi / 2 + (math.pi / 2) * i / segments
            points.append((x2 - radius + radius * math.cos(angle), y1 + radius + radius * math.sin(angle)))

        # Right edge
        points.append((x2, y1 + radius))
        points.append((x2, y2 - radius))

        # Bottom-right corner
        for i in range(segments + 1):
            angle = 0 + (math.pi / 2) * i / segments
            points.append((x2 - radius + radius * math.cos(angle), y2 - radius + radius * math.sin(angle)))

        # Bottom edge
        points.append((x2 - radius, y2))
        points.append((x1 + radius, y2))

        # Bottom-left corner
        for i in range(segments + 1):
            angle = math.pi / 2 + (math.pi / 2) * i / segments
            points.append((x1 + radius + radius * math.cos(angle), y2 - radius + radius * math.sin(angle)))

        # Left edge
        points.append((x1, y2 - radius))
        points.append((x1, y1 + radius))

        # Top-left corner
        for i in range(segments + 1):
            angle = math.pi + (math.pi / 2) * i / segments
            points.append((x1 + radius + radius * math.cos(angle), y1 + radius + radius * math.sin(angle)))

        # Flatten the list of points for create_polygon
        flat_points = [coord for point in points for coord in point]
        return self.create_polygon(flat_points, smooth=False, **kwargs)

    #create a trimmed rectangle for intermediate nodes, with a cut on the top-left and bottom-right corners
    def _create_trimmed_rectangle(self, x1, y1, x2, y2, trim, **kwargs):
        points = [
            x1 + trim, y1,
            x2 - trim, y1,
            x2, y1 + trim,
            x2, y2 - trim,
            x2 - trim, y2,
            x1 + trim, y2,
            x1, y2 - trim,
            x1, y1 + trim
        ]
        return self.create_polygon(points, smooth=False, **kwargs)

    def _draw_component_box(self, shape: ComponentBox):
        """
        Generates rectangular block segments and reads optional database schema color configurations.

        Args:
            shape (ComponentBox): The target material component element box.
        """
        x1, y1, x2, y2 = shape.get_bounds()
        node_type = str(shape.properties.get('node_type', '')).strip().lower()
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR

        if node_type == 'root':
            shape.shape_id = self.create_rectangle(
                x1, y1, x2, y2,
                fill=self.COMPONENT_FILL,
                outline=self.ROOT_COMPONENT_OUTLINE,
                width=border_width,
                tags="shape"
            )
            outline_color = self.SELECT_COLOR if shape.selected else self.ROOT_COMPONENT_OUTLINE
        elif node_type == 'leaf':
            shape.shape_id = self._create_rounded_rectangle(
                x1, y1, x2, y2, self.LEAF_CORNER_RADIUS,
                fill=self.COMPONENT_FILL,
                outline=self.LEAF_COMPONENT_OUTLINE,
                width=border_width,
                tags="shape"
            )
            outline_color = self.SELECT_COLOR if shape.selected else self.LEAF_COMPONENT_OUTLINE
        else:
            shape.shape_id = self._create_trimmed_rectangle(
                x1, y1, x2, y2, self.INTERMEDIATE_CUT,
                fill=self.COMPONENT_FILL,
                outline=self.INTERMEDIATE_COMPONENT_OUTLINE,
                width=border_width,
                tags="shape"
            )
            outline_color = self.SELECT_COLOR if shape.selected else self.INTERMEDIATE_COMPONENT_OUTLINE

        if shape.selected:                 #if the shape is selected, change the outline color to the selection color
            self.itemconfig(shape.shape_id, outline=self.SELECT_COLOR)
        else:
            self.itemconfig(shape.shape_id, outline=outline_color)
            
        shape.text_id = self.create_text(
            shape.x, shape.y, text=shape.text, font=("Arial", 9), fill="black", 
            width=145, tags="shape_text"
        )

    def _draw_arrow_shape(self, shape: ArrowShape):
        """
        Draws dynamic connecting arrow lines between elements.

        Args:
            shape (ArrowShape): The vector arrow shape structure to render.
        """
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
        """
        Renders directional edge tracking line lines across shape model endpoint pairs.

        Args:
            connection (Connection): The connection model entity configuration.
        """
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
        """
        Renders temporary horizontal and vertical alignment guides to assist in layout placement.

        Args:
            guides (dict): Alignment tracker dictionary specifying matching coordinates ('vertical', 'horizontal').
        """
        self.delete("guide")
        for x in guides.get('vertical', []):
            self.create_line(x, 0, x, self.canvas_height, fill=self.GUIDE_COLOR, width=1, dash=(4, 4), tags="guide")
        for y in guides.get('horizontal', []):
            self.create_line(0, y, self.canvas_width, y, fill=self.GUIDE_COLOR, width=1, dash=(4, 4), tags="guide")

    def clear_alignment_guides(self):
        """Flushes and deletes all temporary alignment indicator lines from the active canvas layer."""
        self.delete("guide")

    def clear_canvas(self):
        """Removes core visual entities including shapes, text strings, linkages, and alignment markers."""
        self.delete("shape")
        self.delete("shape_text")
        self.delete("connection")
        self.delete("guide")

    def redraw_all(self, diagram):
        """
        Clears the canvas and performs a full re-render of the diagram.

        Args:
            diagram: An object containing collections of shapes and 
                     connections to be drawn on the canvas.
        
        Note:
            This method resets the canvas, redraws the grid background, 
            iterates through all objects to recreate them, and reapplies 
            the current zoom transformation to maintain state consistency.
        """
        if diagram is None:
            return 

        # Clear existing elements and reset background grid
        self.delete("all")
        self.draw_grid()
        
       # Render diagram elements: shapes first, then connections
        for shape in diagram.shapes:
            self.draw_shape(shape)
        for conn in diagram.connections:
            self.draw_connection(conn)

        # Reapply current zoom scale if a transformation is active    
        if self.zoom_factor != 1.0:
            self.scale("all", 0, 0, self.zoom_factor, self.zoom_factor)


    def update_shape(self, shape: Shape):
        """
        Forces a targeted individual redraw of a specific shape model on the canvas.

        Args:
            shape (Shape): The object instance that requires updating.
        """
        self.draw_shape(shape)

    def update_connection(self, connection: Connection):
        """
        Forces a targeted individual redraw of a specific vector connection wire line.

        Args:
            connection (Connection): The configuration connector segment requiring re-routing.
        """
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
        """Toggles the grid overlay visibility status and triggers appropriate layout redraws."""
        self.show_grid = not self.show_grid
        if self.show_grid:
            self.draw_grid()
        else:
            self.delete("grid")

    def zoom_in(self):
        """Increases the current zoom level by scaling all objects up by 10% ."""
        self._apply_zoom(1.1)

    def zoom_out(self):
        """Decreases the current zoom level by scaling all objects down by 10% ."""
        self._apply_zoom(0.9)

    def reset_zoom(self):
        """
        Resets the zoom factor back to the default 100% scale (1.0).

        Calculates the inverse factor based on the current zoom level 
        to revert the layout to its original scale.
        """
        if self.zoom_factor != 1.0:
            factor = 1.0 / self.zoom_factor
            self._apply_zoom(factor)
            self.zoom_factor = 1.0

    def _apply_zoom(self, factor: float):
        """
        Applies mathematical scaling to all graphical items in the canvas.

        Args:
            factor (float): The multiplier to apply to the current zoom.

        Note:
            Handles scroll region recalculation, grid adjustment, and
            uses the native Tkinter .scale() method with (0,0) as the anchor.
        """
        next_zoom = self.zoom_factor * factor
        if not (0.4 <= next_zoom <= 3.0) and factor != (1.0 / self.zoom_factor):
            return

        self.zoom_factor = next_zoom

       
        self.scale("all", 0, 0, factor, factor)
        
       
        self.canvas_width = int(self.canvas_width * factor)
        self.canvas_height = int(self.canvas_height * factor)
        self.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        
        
        self.draw_grid()
