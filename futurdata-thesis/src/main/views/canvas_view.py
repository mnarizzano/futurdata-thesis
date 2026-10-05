from copy import copy
import tkinter as tk
from tkinter import font as tkfont
from ..utils.text_layout import wrap_measured
from typing import List
from PIL import Image, ImageOps, ImageTk
from ..utils.image_handler import get_image_handler

from ..models import Shape, ActionCircle, DiamondStep, ComponentBox, ArrowShape, Connection


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
        self.zoom_factor = 1.0
        self.canvas_width = self.MIN_CANVAS_WIDTH
        self.canvas_height = self.MIN_CANVAS_HEIGHT
        self._scroll_origin = (0, 0)
        self.config(scrollregion=(self._scroll_origin[0] * self.zoom_factor, self._scroll_origin[1] * self.zoom_factor, self.canvas_width * self.zoom_factor, self.canvas_height * self.zoom_factor))
        self.show_grid = True
        self.snap_to_grid = True
        self.alignment_guides = {'vertical': [], 'horizontal': []}
        self.color_resolver = None
        self._component_images = {}
        self._render_shapes = {}
        self._canvas_items = {}
        self._connection_items = {}
        self._preview_line_id = None
        self.draw_grid()
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
            self.config(scrollregion=(self._scroll_origin[0] * self.zoom_factor, self._scroll_origin[1] * self.zoom_factor, self.canvas_width * self.zoom_factor, self.canvas_height * self.zoom_factor))
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
        shape_x = self.render_shape(shape).x
        shape_y = self.render_shape(shape).y
        
        # Get visible area
        visible_width = self.winfo_width() / self.zoom_factor
        visible_height = self.winfo_height() / self.zoom_factor
        
        if visible_width <= 1 or visible_height <= 1:
            # Canvas not yet rendered, schedule for later
            self.after(100, lambda: self.scroll_to_shape(shape))
            return
        
        # Get current scroll position (as fractions 0.0 to 1.0)
        x_view = self.xview()
        y_view = self.yview()
        
        # Current visible area in canvas coordinates
        origin_x, origin_y = self._scroll_origin
        region_width, region_height = self.canvas_width - origin_x, self.canvas_height - origin_y
        visible_x1 = origin_x + x_view[0] * region_width
        visible_x2 = origin_x + x_view[1] * region_width
        visible_y1 = origin_y + y_view[0] * region_height
        visible_y2 = origin_y + y_view[1] * region_height
        
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
        target_x = max(origin_x, min(target_x, self.canvas_width - visible_width))
        target_y = max(origin_y, min(target_y, self.canvas_height - visible_height))
        
        # Convert to fractions
        x_fraction = (target_x - origin_x) / region_width if region_width > 0 else 0
        y_fraction = (target_y - origin_y) / region_height if region_height > 0 else 0
        
        # Scroll to position
        self.xview_moveto(x_fraction)
        self.yview_moveto(y_fraction)

    def center_on_shape(self, shape):
        """Center a model bounding box using the current viewport transform."""
        self.update_idletasks()
        left, top, right, bottom = self.render_bounds(shape)
        zoom = self.zoom_factor
        x0, y0, x1, y1 = map(float, self.tk.splitlist(self.cget('scrollregion')))
        # Include out-of-region imported geometry without moving model nodes.
        region = (min(x0, left * zoom - 40), min(y0, top * zoom - 40),
                  max(x1, right * zoom + 40), max(y1, bottom * zoom + 40))
        self.configure(scrollregion=region)
        self._scroll_origin = (region[0] / zoom, region[1] / zoom)
        self.canvas_width = max(self.canvas_width, region[2] / zoom)
        self.canvas_height = max(self.canvas_height, region[3] / zoom)
        x0, y0, x1, y1 = region
        inset = float(self.cget('borderwidth')) + float(self.cget('highlightthickness'))
        width = max(1, self.winfo_width() - 2 * inset)
        height = max(1, self.winfo_height() - 2 * inset)
        target_x = (left + right) * zoom / 2 - width / 2
        target_y = (top + bottom) * zoom / 2 - height / 2
        target_x = max(x0, min(target_x, x1 - width))
        target_y = max(y0, min(target_y, y1 - height))
        self.xview_moveto((target_x - x0) / max(1, x1 - x0))
        self.yview_moveto((target_y - y0) / max(1, y1 - y0))

    def update_scroll_region_from_shapes(self, shapes, redraw_grid=True) -> None:
        """Include rendered extents without translating document geometry."""
        bounds = [self.render_bounds(shape) for shape in shapes]
        left = min([0] + [b[0] - 40 for b in bounds])
        top = min([0] + [b[1] - 40 for b in bounds])
        self.canvas_width = max(self.MIN_CANVAS_WIDTH, int(max([0] + [b[2] + 40 for b in bounds]) + self.EXPANSION_MARGIN))
        self.canvas_height = max(self.MIN_CANVAS_HEIGHT, int(max([0] + [b[3] + 40 for b in bounds]) + self.EXPANSION_MARGIN))
        self._scroll_origin = (left, top)
        zoom = self.zoom_factor
        self.config(scrollregion=(left * zoom, top * zoom, self.canvas_width * zoom, self.canvas_height * zoom))
        if redraw_grid:
            self.draw_grid()

    def draw_grid(self):
        """Renders the grid overlay pattern onto the canvas background using default constants."""
        if not self.show_grid:
            return
        x1, y1 = self._scroll_origin
        x2, y2 = self.canvas_width, self.canvas_height
        self.delete("grid")
        for x in range(int(self._scroll_origin[0] // self.GRID_SIZE) * self.GRID_SIZE, int(x2) + 1, self.GRID_SIZE):
            self.create_line(x, y1, x, y2, fill=self.GRID_COLOR, tags="grid")
        for y in range(int(self._scroll_origin[1] // self.GRID_SIZE) * self.GRID_SIZE, int(y2) + 1, self.GRID_SIZE):
            self.create_line(x1, y, x2, y, fill=self.GRID_COLOR, tags="grid")
        self.tag_lower("grid")

    def render_shape(self, shape):
        """Return canvas-owned geometry; domain objects remain read-only."""
        rendered = self._render_shapes.get(shape)
        if rendered is None:
            return shape
        rendered.x += shape.x - rendered._logical_x
        rendered.y += shape.y - rendered._logical_y
        rendered._logical_x, rendered._logical_y = shape.x, shape.y
        return rendered

    def render_bounds(self, shape):
        if isinstance(shape, ArrowShape):
            (x1, y1), (x2, y2) = self.render_endpoints(shape)
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        return self.render_shape(shape).get_bounds()

    def render_endpoints(self, edge):
        if edge.from_shape is None or edge.to_shape is None:
            return (edge.x, edge.y), (edge.end_x, edge.end_y)
        start, end = self.render_shape(edge.from_shape), self.render_shape(edge.to_shape)
        from_anchor, to_anchor = edge.from_anchor, edge.to_anchor
        if isinstance(edge, ArrowShape):
            dx, dy = end.x - start.x, end.y - start.y
            if abs(dx) > abs(dy):
                from_anchor, to_anchor = ('right', 'left') if dx > 0 else ('left', 'right')
            else:
                from_anchor, to_anchor = ('bottom', 'top') if dy > 0 else ('top', 'bottom')
        return (start.get_connection_points().get(from_anchor, (start.x, start.y)),
                end.get_connection_points().get(to_anchor, (end.x, end.y)))

    def find_shape_at_point(self, diagram, x, y):
        """Hit testing uses the same geometry that the user sees."""
        for shape in reversed(diagram.shapes):
            if isinstance(shape, ArrowShape):
                (ax, ay), (bx, by) = self.render_endpoints(shape)
                length = (bx - ax) ** 2 + (by - ay) ** 2
                t = max(0, min(1, ((x-ax)*(bx-ax)+(y-ay)*(by-ay))/length)) if length else 0
                if (x-ax-t*(bx-ax))**2 + (y-ay-t*(by-ay))**2 <= 100:
                    return shape
            elif self.render_shape(shape).contains_point(x, y):
                return shape
        return None

    def preview_connection_from(self, shape, x=None, y=None):
        rendered = self.render_shape(shape)
        self.show_connection_preview(rendered.x, rendered.y,
                                     rendered.x + 100 if x is None else x,
                                     rendered.y if y is None else y)

    def show_connection_preview(self, x1, y1, x2, y2):
        self.clear_connection_preview()
        self._preview_line_id = self.create_line(
            x1, y1, x2, y2, fill="black", width=2, dash=(5, 5),
            arrow=tk.LAST, arrowshape=(12, 15, 6), tags="preview")

    def clear_connection_preview(self):
        if self._preview_line_id is not None:
            self.delete(self._preview_line_id)
            self._preview_line_id = None

    def _measure_shape(self, shape):
        if not isinstance(shape, (ComponentBox, ActionCircle, DiamondStep)):
            return False
        model = shape
        previous = self._render_shapes.get(model)
        shape = copy(model)
        self._render_shapes[model] = shape
        if previous is not None:
            # Individual repaint keeps the visual layout offset relative to the model.
            shape.x += previous.x - getattr(previous, '_logical_x', model.x)
            shape.y += previous.y - getattr(previous, '_logical_y', model.y)
        shape._logical_x, shape._logical_y = model.x, model.y
        old_bounds = model.get_bounds()
        font = tkfont.Font(self, family="Arial", size=8 if isinstance(shape, DiamondStep) else 9)
        shape._node_image = None
        image_path = (shape.properties.get('image_path') if isinstance(shape, ComponentBox)
                      else getattr(shape, 'image_path', None))
        if image_path:
            try:
                with Image.open(get_image_handler().get_full_path(image_path)) as source:
                    shape._node_image = ImageOps.exif_transpose(source).convert('RGBA')
            except (OSError, ValueError, Image.DecompressionBombError):
                pass  # Missing/corrupt images retain normal node rendering.
        if isinstance(shape, ComponentBox):
            width = shape.WIDTH - 16
            lines = wrap_measured(shape.text, width, font.measure)
            shape.HEIGHT = max(ComponentBox.HEIGHT, len(lines) * font.metrics('linespace') + 16)
            text_height = shape.HEIGHT - 16
            if shape._node_image is not None:
                text_height = len(lines) * font.metrics('linespace')
                shape.HEIGHT = ComponentBox.HEIGHT + text_height + 16
        else:
            # A centered inscribed rectangle keeps text inside curved/sloped edges.
            size = ActionCircle.RADIUS * 2 if isinstance(shape, ActionCircle) else DiamondStep.SIZE
            ratio = 0.65 if isinstance(shape, ActionCircle) else 0.46
            while True:
                width = size * ratio - 8
                lines = wrap_measured(shape.text, width, font.measure)
                if len(lines) * font.metrics('linespace') + 8 + (60 if shape._node_image is not None else 0) <= size * ratio:
                    break
                size += 10
            text_height = size * ratio - 8
            if isinstance(shape, ActionCircle):
                shape.RADIUS = size / 2
            else:
                shape.SIZE = size
        shape._display_text = "\n".join(lines)
        shape._text_width = width
        shape._text_height = text_height
        return shape.get_bounds() != old_bounds

    def _layout_shapes(self, diagram):
        self._render_shapes.clear()
        models = [s for s in diagram.shapes if not isinstance(s, ArrowShape)]
        changed = [self._measure_shape(s) for s in models]
        shapes = [self._render_shapes[s] for s in models]
        if not any(changed):
            self.update_scroll_region_from_shapes(models, redraw_grid=False)
            return
        # Keep expanded shapes reachable in the canvas's positive scroll region.
        dx = max(0, 20 - min(s.get_bounds()[0] for s in shapes))
        dy = max(0, 20 - min(s.get_bounds()[1] for s in shapes))
        for shape in shapes:
            shape.move(dx, dy)
        placed = []
        for shape in sorted(shapes, key=lambda s: (s.y, s.x)):
            for previous in placed:
                left, top, right, bottom = shape.get_bounds()
                pl, pt, pr, pb = previous.get_bounds()
                if left < pr + 16 and right > pl - 16 and top < pb + 20:
                    shape.y += pb + 20 - top
            placed.append(shape)
        self.update_scroll_region_from_shapes(models, redraw_grid=False)

    def draw_shape(self, shape: Shape, measure=True) -> None:
        """
        Clears existing instances of a shape model from the canvas and triggers 
        the appropriate specialized drawing routine based on its class type.

        Args:
            shape (Shape): The concrete instance model element requiring drawing.
        """
        if measure:
            self._measure_shape(shape)
        previous_image = self._component_images.pop(shape, None)
        if previous_image is not None:
            self.delete(previous_image[0])
        if self._canvas_items.setdefault(shape, {}).get('body') is not None:
            self.delete(self._canvas_items.setdefault(shape, {}).get('body'))
        if self._canvas_items.setdefault(shape, {}).get('text') is not None:
            self.delete(self._canvas_items.setdefault(shape, {}).get('text'))

        if isinstance(shape, ActionCircle):
            self._draw_action_circle(shape)
        elif isinstance(shape, DiamondStep):
            self._draw_diamond_step(shape)
        elif isinstance(shape, ComponentBox):
            self._draw_component_box(shape)
        elif isinstance(shape, ArrowShape):
            self._draw_arrow_shape(shape)


    def _draw_action_circle(self, shape: ActionCircle):
        """
        Generates graphical oval lines and internal metadata labels for an ActionCircle shape.

        Args:
            shape (ActionCircle): The target action model entity.
        """
        x1, y1, x2, y2 = self.render_bounds(shape)
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        self._canvas_items.setdefault(shape, {})['body'] = self.create_oval(
            x1, y1, x2, y2, fill=self.ACTION_FILL, outline=border_color, width=border_width, tags="shape"
        )
        label_y = self._draw_inscribed_image(shape)
        self._canvas_items.setdefault(shape, {})['text'] = self.create_text(
            self.render_shape(shape).x, label_y, text=self.render_shape(shape)._display_text, font=("Arial", 9), fill="black",
            width=0, tags="shape_text"
        )

    def _draw_diamond_step(self, shape: DiamondStep):
        """
        Generates diamond polygon outlines and text tags for a DiamondStep shape.

        Args:
            shape (DiamondStep): The target action element.
        """
        half = self.render_shape(shape).SIZE / 2
        points = [
            self.render_shape(shape).x, self.render_shape(shape).y - half,
            self.render_shape(shape).x + half, self.render_shape(shape).y,
            self.render_shape(shape).x, self.render_shape(shape).y + half,
            self.render_shape(shape).x - half, self.render_shape(shape).y
        ]
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        self._canvas_items.setdefault(shape, {})['body'] = self.create_polygon(
            points, fill=self.DIAMOND_FILL, outline=border_color, width=border_width, tags="shape"
        )
        label_y = self._draw_inscribed_image(shape)
        self._canvas_items.setdefault(shape, {})['text'] = self.create_text(
            self.render_shape(shape).x, label_y, text=self.render_shape(shape)._display_text, font=("Arial", 8), fill="black",
            width=0, tags="shape_text"
        )

    def _draw_component_box(self, shape: ComponentBox):
        """
        Generates rectangular block segments and reads optional JSON schema color configurations.

        Args:
            shape (ComponentBox): The target material component element box.
        """
        x1, y1, x2, y2 = self.render_bounds(shape)
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        
        # Determine fill color based on node type and color_id
        fill_color = self.COMPONENT_FILL
        node_type = str(shape.properties.get('node_type', '')).strip().lower()
        color_id = shape.properties.get('color_id')
        
        # If it's a leaf node with a color selected, use that color
        if node_type == "leaf" and color_id:
            try:
                color_data = self.color_resolver(int(color_id)) if self.color_resolver else None
                if color_data:
                    # The legacy catalog represents Transparent with black RGB.
                    if str(color_data.get('name', '')).strip().casefold() == 'transparent':
                        fill_color = ''
                    elif color_data.get('hex_code'):
                        fill_color = color_data['hex_code']
            except (TypeError, ValueError):
                pass  # Fall back to default white for invalid catalog data.
        
        # Validate catalog colors and choose the higher-contrast black/white label.
        try:
            rgb = self.winfo_rgb(fill_color or self.cget('background'))
            channels = [value / 65535 for value in rgb]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                      for v in channels]
            luminance = sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
            text_color = "black" if luminance > 0.179 else "white"
        except (tk.TclError, TypeError, ValueError):
            fill_color, text_color = self.COMPONENT_FILL, "black"

        source = self.render_shape(shape)._node_image
        label_y = self.render_shape(shape).y
        if source is not None:
            fill_color, text_color = "white", "black"
            label_y = y2 - (self.render_shape(shape)._text_height + 16) / 2
        self._canvas_items.setdefault(shape, {})['body'] = self.create_rectangle(
            x1, y1, x2, y2, fill=fill_color, outline=border_color, width=border_width, tags="shape"
        )
        if source is not None:
            inset = 2
            width = x2 - x1 - inset * 2
            height = ComponentBox.HEIGHT - inset
            photo = self._component_photo(source, width, height)
            item = self.create_image(self.render_shape(shape).x, y1 + inset + height / 2,
                                     image=photo, tags="shape")
            self._component_images[shape] = (item, source, width, height, photo)
        self._canvas_items.setdefault(shape, {})['text'] = self.create_text(
            self.render_shape(shape).x, label_y, text=self.render_shape(shape)._display_text, font=("Arial", 9), fill=text_color,
            width=0, tags="shape_text"
        )

    def _draw_inscribed_image(self, shape):
        """Use the component image lifecycle inside the circle/diamond safe rectangle."""
        if self.render_shape(shape)._node_image is None:
            return self.render_shape(shape).y
        size = self.render_shape(shape).RADIUS * 2 if isinstance(shape, ActionCircle) else self.render_shape(shape).SIZE
        ratio = 0.65 if isinstance(shape, ActionCircle) else 0.46
        width = size * ratio - 8
        text_height = len(self.render_shape(shape)._display_text.splitlines()) * tkfont.Font(
            self, family="Arial", size=9 if isinstance(shape, ActionCircle) else 8
        ).metrics('linespace')
        height = size * ratio - 8 - text_height - 8
        top = self.render_shape(shape).y - (size * ratio - 8) / 2
        photo = self._component_photo(self.render_shape(shape)._node_image, width, height)
        item = self.create_image(self.render_shape(shape).x, top + height / 2, image=photo, tags="shape")
        self._component_images[shape] = (item, self.render_shape(shape)._node_image, width, height, photo)
        return top + height + 8 + text_height / 2

    def _component_photo(self, source, width, height):
        """Fit the whole image proportionally on an opaque, neutral background."""
        size = (max(1, round(width * self.zoom_factor)),
                max(1, round(height * self.zoom_factor)))
        fitted = ImageOps.contain(source, size, Image.Resampling.LANCZOS)
        background = Image.new('RGBA', size, 'white')
        background.alpha_composite(fitted, ((size[0] - fitted.width) // 2,
                                            (size[1] - fitted.height) // 2))
        return ImageTk.PhotoImage(background, master=self)

    def _draw_arrow_shape(self, shape: ArrowShape):
        """
        Draws dynamic connecting arrow lines between elements.

        Args:
            shape (ArrowShape): The vector arrow shape structure to render.
        """
        (start_x, start_y), (end_x, end_y) = self.render_endpoints(shape)
        border_width = 3 if shape.selected else 2
        border_color = self.SELECT_COLOR if shape.selected else self.BORDER_COLOR
        self._canvas_items.setdefault(shape, {})['body'] = self.create_line(
            start_x, start_y, end_x, end_y, fill=border_color, width=border_width,
            arrow=tk.LAST, arrowshape=(12, 15, 6), tags="shape"
        )
        self._canvas_items.setdefault(shape, {})['text'] = None

    def draw_connection(self, connection: Connection) -> None:
        """
        Renders directional edge tracking line lines across shape model endpoint pairs.

        Args:
            connection (Connection): The connection model entity configuration.
        """
        if self._connection_items.get(connection) is not None:
            self.delete(self._connection_items.get(connection))
        (x1, y1), (x2, y2) = self.render_endpoints(connection)
        dash = (5, 5) if connection.connection_type == "dashed" else None
        self._connection_items[connection] = self.create_line(
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
        self._component_images.clear()
        self._canvas_items.clear()
        self._connection_items.clear()
        self._render_shapes.clear()
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

        self.diagram = diagram
        self._layout_shapes(diagram)

        # Clear existing elements and reset background grid
        self._component_images.clear()
        self._canvas_items.clear()
        self._connection_items.clear()
        self._preview_line_id = None
        self.delete("all")
        self.draw_grid()
        
       # Render diagram elements: shapes first, then connections
        for shape in diagram.shapes:
            self.draw_shape(shape, measure=False)
        for conn in diagram.connections:
            self.draw_connection(conn)



    def update_shape(self, shape: Shape):
        """
        Forces a targeted individual redraw of a specific shape model on the canvas.

        Args:
            shape (Shape): The object instance that requires updating.
        """
        if self.diagram is not None:
            self.redraw_all(self.diagram)
        else:
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
        rendered = self._render_shapes.get(shape)
        if rendered is not None:
            rendered.x += dx
            rendered.y += dy
            rendered._logical_x, rendered._logical_y = shape.x, shape.y
        image = self._component_images.get(shape)
        if image is not None:
            self.move(image[0], dx * self.zoom_factor, dy * self.zoom_factor)
        dx *= self.zoom_factor
        dy *= self.zoom_factor
        if self._canvas_items.setdefault(shape, {}).get('body') is not None:
            self.move(self._canvas_items.setdefault(shape, {}).get('body'), dx, dy)
        if self._canvas_items.setdefault(shape, {}).get('text') is not None:
            self.move(self._canvas_items.setdefault(shape, {}).get('text'), dx, dy)

    def update_connections_for_shapes(self, shapes: List[Shape], diagram):
        """Update only connections attached to the given shapes."""
        for arrow in diagram.shapes:
            if isinstance(arrow, ArrowShape) and (arrow.from_shape in shapes or arrow.to_shape in shapes):
                self.draw_shape(arrow)
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

    def zoom_in(self, x=None, y=None):
        """Increases the current zoom level by scaling all objects up by 10% ."""
        self._apply_zoom(1.1, x, y)

    def zoom_out(self, x=None, y=None):
        """Decreases the current zoom level by scaling all objects down by 10% ."""
        self._apply_zoom(1 / 1.1, x, y)

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

    def _scale_labels(self):
        """Canvas.scale changes positions only; scale label fonts and wrap widths too."""
        if self.diagram is None:
            return
        for shape in self.diagram.shapes:
            if not isinstance(shape, (ComponentBox, ActionCircle, DiamondStep)) or self._canvas_items.setdefault(shape, {}).get('text') is None:
                continue
            points = 8 if isinstance(shape, DiamondStep) else 9
            pixels = max(1, int(self.winfo_fpixels(f"{points}p") * self.zoom_factor))
            font = tkfont.Font(self, family="Arial", size=-pixels)
            lines = self.render_shape(shape)._display_text.split("\n")
            # Font hinting and integer line spacing do not scale linearly.
            # Check native metrics rather than assuming point-size arithmetic.
            while pixels > 1:
                if (max(font.measure(line) for line in lines) <= self.render_shape(shape)._text_width * self.zoom_factor
                        and font.metrics('linespace') * len(lines) <= self.render_shape(shape)._text_height * self.zoom_factor):
                    break
                pixels -= 1
                font.configure(size=-pixels)
            self.itemconfigure(self._canvas_items.setdefault(shape, {}).get('text'), font=("Arial", -pixels), width=0)

    def model_x(self, x):
        return self.canvasx(x) / self.zoom_factor

    def model_y(self, y):
        return self.canvasy(y) / self.zoom_factor

    def _create(self, item_type, args, kw):
        """Render model coordinates through the viewport transform, including previews."""
        from tkinter import _flatten
        args = tuple(value * self.zoom_factor for value in _flatten(args))
        kw = dict(kw)
        for option in ('width', 'activewidth', 'disabledwidth'):
            if option in kw:
                kw[option] *= self.zoom_factor
        if kw.get('arrow'):
            kw['arrowshape'] = tuple(v * self.zoom_factor for v in kw.get('arrowshape', (8, 10, 3)))
        if kw.get('dash'):
            kw['dash'] = tuple(max(1, round(v * self.zoom_factor)) for v in kw['dash'])
        if 'font' in kw:
            family, points = kw['font']
            kw['font'] = (family, -max(1, round(self.winfo_fpixels(f'{points}p') * self.zoom_factor)))
        return super()._create(item_type, args, kw)

    def _apply_zoom(self, factor: float, x=None, y=None):
        """Zoom only the viewport, keeping the model point under the cursor stable."""
        next_zoom = min(4.0, max(0.25, self.zoom_factor * factor))
        factor = next_zoom / self.zoom_factor
        if factor == 1:
            return
        x = self.winfo_width() / 2 if x is None else x
        y = self.winfo_height() / 2 if y is None else y
        anchor_x, anchor_y = self.canvasx(x), self.canvasy(y)
        self.zoom_factor = next_zoom
        self.scale('all', 0, 0, factor, factor)
        for item in self.find_all():
            if self.type(item) not in ('text', 'image'):
                self.itemconfigure(item, width=float(self.itemcget(item, 'width')) * factor)
            if self.type(item) == 'line' and self.itemcget(item, 'dash'):
                base = 4 if 'guide' in self.gettags(item) else 5
                self.itemconfigure(item, dash=(max(1, round(base * next_zoom)),) * 2)
            if self.type(item) == 'line' and self.itemcget(item, 'arrow') != 'none':
                arrow = self.tk.splitlist(self.itemcget(item, 'arrowshape'))
                self.itemconfigure(item, arrowshape=tuple(float(v) * factor for v in arrow))
        for shape, (item, source, image_width, image_height, _) in list(self._component_images.items()):
            photo = self._component_photo(source, image_width, image_height)
            self.itemconfigure(item, image=photo)
            self._component_images[shape] = (item, source, image_width, image_height, photo)
        self._scale_labels()
        width, height = self.canvas_width * next_zoom, self.canvas_height * next_zoom
        left, top = (value * next_zoom for value in self._scroll_origin)
        self.config(scrollregion=(left, top, width, height))
        self.xview_moveto((anchor_x * factor - x - left) / max(1, width - left))
        self.yview_moveto((anchor_y * factor - y - top) / max(1, height - top))
        self.draw_grid()
