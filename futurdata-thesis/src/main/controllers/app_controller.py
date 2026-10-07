from ..utils.feedback import FeedbackType
from typing import Tuple
import os

from ..models import Diagram, ActionCircle, DiamondStep, ComponentBox, ArrowShape, Connection
import copy
from uuid import uuid4
from ..repositories import get_repository, DuplicateValueError
from ..services import ProjectArchiveService
from .catalog_controller import CatalogController
from .navigator import topology_snapshot, build_outline
from ..utils import (
    CommandHistory, AddShapeCommand, RemoveShapeCommand, MoveShapeCommand,
    AddConnectionCommand, EditShapePropertiesCommand, MultiCommand, snap_to_grid,
    find_alignment_guides, DiagramSerializer
)
from ..utils.diagram_loader import DiagramLoader
from ..utils.json_exporter import EnhancedJSONExporter
from ..services.document_export_service import DocumentExportService
from ..services.project_persistence import ProjectPersistence
from ..services.workflow_validation import connection_error
from ..utils.image_handler import get_image_handler


class AppController:

    def __init__(self, repository=None, catalog=None, diagram_loader=None, json_exporter=None,
                 archive_service=None, document_export_service=None, persistence_factory=ProjectPersistence, image_handler=None):
        """Initialize controller state, models and helper services."""
        self.diagram = Diagram()
        self.command_history = CommandHistory()
        self.view = None
        self.repository = repository if repository is not None else get_repository()
        self.catalog = catalog if catalog is not None else CatalogController(self.repository)
        self.diagram_loader = diagram_loader if diagram_loader is not None else DiagramLoader(self.repository)
        self.json_exporter = json_exporter if json_exporter is not None else EnhancedJSONExporter(self.repository)
        self.archive_service = archive_service if archive_service is not None else ProjectArchiveService(self.json_exporter)
        self.document_export_service = document_export_service if document_export_service is not None else DocumentExportService(self.json_exporter)
        self.image_handler = image_handler
        self.persistence_factory = persistence_factory
        self.current_product_id = None  # Track currently loaded product
        self.dragging = False
        self.drag_start = None
        self.drag_initial_positions = {}
        self.drag_shapes = []
        self.connect_mode = False
        self.arrow_mode = False
        self.connecting_from = None
        self.auto_save_timer = None  

    def set_view(self, view):
        """Attach the view and wire up canvas event bindings."""
        self.view = view
        self._bind_canvas_events()
        self._sync_navigator()

    def _bind_canvas_events(self):
        """Bind mouse, keyboard and scroll events to the canvas."""
        canvas = self.view.canvas
        canvas.bind("<Button-1>", self.on_canvas_click)
        canvas.bind("<B1-Motion>", self.on_canvas_drag)
        canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        canvas.bind("<Button-3>", self.on_canvas_right_click)
        canvas.bind("<Motion>", self.on_canvas_motion)
        canvas.bind("<Escape>", self.on_escape)
        canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        canvas.bind("<Button-4>", self.on_mouse_wheel)
        canvas.bind("<Button-5>", self.on_mouse_wheel)
        canvas.bind("<Shift-MouseWheel>", self.on_shift_mouse_wheel)
        for sequence in ("<Control-MouseWheel>", "<Control-Button-4>", "<Control-Button-5>"):
            canvas.bind(sequence, self.on_zoom_wheel)

    def on_zoom_wheel(self, event):
        direction = 1 if getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0) > 0 else -1
        self.view.canvas._apply_zoom(1.1 ** direction, event.x, event.y)
        self.view.set_status(f"Zoom: {self.view.canvas.zoom_factor:.0%}")
        return "break"


    def on_mouse_wheel(self, event):
        """Scroll the canvas vertically with the mouse wheel."""
        if event.num == 4:
            self.view.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.view.canvas.yview_scroll(1, "units")
        else:
            self.view.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_shift_mouse_wheel(self, event):
        """Scroll the canvas horizontally with Shift + mouse wheel."""
        self.view.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_canvas_motion(self, event):
        """Show preview line when in arrow/connect mode and have a starting shape."""
        if (self.arrow_mode or self.connect_mode) and self.connecting_from is not None:
            x = self.view.canvas.model_x(event.x)
            y = self.view.canvas.model_y(event.y)
            # Draw preview line from connecting_from shape to mouse cursor
            self.view.canvas.preview_connection_from(self.connecting_from, x, y)

    def _clear_preview_line(self):
        self.view.canvas.clear_connection_preview()

    def on_escape(self, event):
        """Cancel arrow/connect mode."""
        if self.arrow_mode or self.connect_mode:
            self._clear_preview_line()
            self.arrow_mode = False
            self.connect_mode = False
            self.connecting_from = None
            self.view.canvas.config(cursor="")
            self.view.set_status("Cancelled")

    def on_canvas_click(self, event):
        """Handle left-click: select a shape, start a drag, or start a connection."""
        x = self.view.canvas.model_x(event.x)
        y = self.view.canvas.model_y(event.y)
        clicked_shape = self.view.canvas.find_shape_at_point(self.diagram, x, y)

        if self.arrow_mode:
            if clicked_shape:
                self._handle_arrow_connection_click(clicked_shape)
            return

        if self.connect_mode:
            if clicked_shape:
                self._handle_connection_click(clicked_shape)
            return

        multi_select = event.state & 0x0004

        if clicked_shape:
            self.diagram.select_shape(clicked_shape, multi_select=multi_select)
            self.dragging = True
            self.drag_start = (x, y)
            self.drag_shapes = list(self.diagram.selected_shapes)
            self.drag_initial_positions = {shape: (shape.x, shape.y) for shape in self.drag_shapes}
        else:
            if not multi_select:
                self.diagram.clear_selection()

        self._update_view()

    def on_canvas_drag(self, event):
        """Move the selected shapes as the mouse is dragged."""
        if not self.dragging or not self.drag_shapes:
            return

        self._auto_scroll_viewport(event.x, event.y)

        x = self.view.canvas.model_x(event.x)
        y = self.view.canvas.model_y(event.y)
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        # Prevent dragging shapes into negative coords, where they'd hide behind the
        # left panel / above the canvas and be unreachable (only CTRL+Z could recover them).
        min_x1 = min(s.get_bounds()[0] for s in self.drag_shapes)
        min_y1 = min(s.get_bounds()[1] for s in self.drag_shapes)
        if min_x1 + dx < 0:
            dx = -min_x1
        if min_y1 + dy < 0:
            dy = -min_y1

        # Move each shape freely during drag (no snapping)
        for shape in self.drag_shapes:
            shape.x += dx
            shape.y += dy
            # Fast move - just moves existing canvas items
            self.view.canvas.move_items(shape, dx, dy)
            # Expand canvas if needed
            self.view.canvas.expand_canvas_if_needed(shape.x, shape.y)

        self.drag_start = (x, y)

        # Update connections attached to dragged shapes
        self.view.canvas.update_connections_for_shapes(self.drag_shapes, self.diagram)

        if len(self.drag_shapes) == 1:
            guides = find_alignment_guides(
                self.drag_shapes[0],
                [s for s in self.diagram.shapes if s not in self.drag_shapes]
            )
            self.view.canvas.draw_alignment_guides(guides)

    def _auto_scroll_viewport(self, mouse_x: int, mouse_y: int):
        self.view.canvas.auto_scroll(mouse_x, mouse_y)

    def on_canvas_release(self, event):
        """Finish a drag: snap, record the move command and redraw."""
        if self.dragging and self.drag_shapes and self.drag_initial_positions:
            # Snap to grid on release if enabled
            if self.diagram.snap_to_grid:
                for shape in self.drag_shapes:
                    shape.x, shape.y = snap_to_grid(shape.x, shape.y)

            moves = []
            for shape in self.drag_shapes:
                initial_x, initial_y = self.drag_initial_positions[shape]
                dx, dy = shape.x - initial_x, shape.y - initial_y
                if dx or dy:
                    moves.append(MoveShapeCommand(shape, dx, dy, self.diagram))
            if moves:
                # Dragging previews positions in memory. Restore the starting points
                # before committing the final translation through normal commands.
                for shape in self.drag_shapes:
                    shape.x, shape.y = self.drag_initial_positions[shape]
                command = moves[0] if len(moves) == 1 else MultiCommand(moves, "Move selected shapes")
                self.command_history.execute(command)

        self.dragging = False
        self.drag_start = None
        self.drag_shapes = []
        self.drag_initial_positions = {}
        self.view.canvas.clear_alignment_guides()
        self._update_view()

    def on_canvas_right_click(self, event):
        """Show the context menu for the shape under the cursor."""
        x = self.view.canvas.model_x(event.x)
        y = self.view.canvas.model_y(event.y)
        clicked_shape = self.view.canvas.find_shape_at_point(self.diagram, x, y)

        if clicked_shape:
            if self.arrow_mode or self.connect_mode:
                self._clear_preview_line()
                self.arrow_mode = False
                self.connect_mode = False
                self.connecting_from = None
            self._show_context_menu(event, clicked_shape)

    def _show_context_menu(self, event, shape):
        self.view.show_shape_context_menu(
            event, lambda: self._edit_shape_properties(shape),
            lambda: self._duplicate_shape(shape), lambda: self._delete_shape(shape))

    def _handle_arrow_connection_click(self, shape):
        """Pick source then target shape to create an arrow in arrow mode."""
        # Also select the shape so Delete key works
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()

        if self.connecting_from is None:
            self.connecting_from = shape
            # Draw initial preview line from shape center (draw AFTER update_view)
            self.view.canvas.preview_connection_from(shape)
            self.view.set_status(f"Arrow started from {self._shape_display_name(shape)}. Click target shape or press Delete to remove.")
        else:
            self._clear_preview_line()
            if self.connecting_from != shape:
                if self._create_arrow_connection(self.connecting_from, shape):
                    self.view.set_status("Arrow created.", FeedbackType.SUCCESS)
            else:
                self.view.set_status("Cancelled - same shape.")
            self.connecting_from = None
            self.arrow_mode = False
            self.view.canvas.config(cursor="")
            self._update_view()

    def _handle_connection_click(self, shape):
        """Pick source then target shape to create a connection in connect mode."""
        if self.connecting_from is None:
            self.connecting_from = shape
            self.view.set_status(f"Connection started from {self._shape_display_name(shape)}. Click target shape or press ESC to cancel.")
        else:
            self._clear_preview_line()
            if self.connecting_from != shape:
                if self._create_connection(self.connecting_from, shape):
                    self.view.set_status("Connection created.", FeedbackType.SUCCESS)
            else:
                self.view.set_status("Cancelled - same shape.")
            self.connecting_from = None
            self.connect_mode = False

    def _validate_workflow_connection(self, from_shape, to_shape) -> bool:
        error = connection_error(from_shape, to_shape)
        if error is None:
            return True
        message, status = error
        self.view.show_workflow_error("Invalid workflow connection", message)
        self.view.set_status(status, FeedbackType.ERROR)
        return False

    def _create_arrow_connection(self, from_shape, to_shape):
        """Create an unsaved arrow after validating the existing graph grammar."""
        if not self._validate_workflow_connection(from_shape, to_shape):
            return False
        if self.diagram.has_edge(from_shape, to_shape):
            return False
        arrow = ArrowShape(0, 0, from_shape, to_shape)
        arrow.update_from_shapes()
        command = AddShapeCommand(self.diagram, arrow)
        self.command_history.execute(command)
        self._update_view()
        return True

    def _create_connection(self, from_shape, to_shape):
        """Create an unsaved connection after validating the existing graph grammar."""
        if not self._validate_workflow_connection(from_shape, to_shape):
            return False
        if self.diagram.has_edge(from_shape, to_shape):
            return False
        connection = Connection(from_shape, to_shape)
        connection.auto_calculate_anchors()
        command = AddConnectionCommand(self.diagram, connection)
        self.command_history.execute(command)
        self._update_view()
        return True

    def _ensure_component_id(self, shape):
        return self._storage_operation('_ensure_component_id', shape)

    def _ensure_step_id(self, shape, input_shape=None):
        return self._storage_operation('_ensure_step_id', shape, input_shape)

    def _ensure_action_id(self, shape):
        return self._storage_operation('_ensure_action_id', shape)

    def _edit_shape_properties(self, shape):
        """Select a shape so its properties show in the panel."""
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()

    def _allow_new_root(self):
        if any(isinstance(shape, ComponentBox) and
               str(shape.properties.get('node_type', '')).strip().lower() == 'root'
               for shape in self.diagram.shapes):
            self.view.show_error(
                "Root component already exists",
                "This diagram already has a Root Component. Only one root is allowed.\n\n"
                "Add a Leaf or Composite Component, or create a new diagram for another root.")
            return False
        return True

    def _duplicate_shape(self, shape):
        """Create a copy of a shape offset from the original."""
        if (isinstance(shape, ComponentBox) and
                str(shape.properties.get('node_type', '')).strip().lower() == 'root' and
                not self._allow_new_root()):
            return
        new_shape = self._create_shape_instance(shape.shape_type, shape.x + 50, shape.y + 50)
        new_shape.text = shape.text

        if isinstance(shape, ActionCircle):
            new_shape.step_description = shape.step_description
            new_shape.image_path = shape.image_path
            new_shape.tools = shape.tools
        elif isinstance(shape, DiamondStep):
            new_shape.action_id = shape.action_id
            new_shape.name = shape.name
            new_shape.tools = shape.tools
        elif isinstance(shape, ComponentBox):
            new_shape.properties = dict(shape.properties)

        command = AddShapeCommand(self.diagram, new_shape)
        self.command_history.execute(command)
        self._update_view()
        self.view.set_status(f"Duplicated {self._shape_display_name(shape)}", FeedbackType.SUCCESS)

    def _delete_shape(self, shape):
        """Delete a shape, removing any arrows/connections attached to it."""
        commands = [RemoveShapeCommand(self.diagram, arrow)
                    for arrow in self._get_attached_arrows(shape)]
        commands.append(RemoveShapeCommand(self.diagram, shape))
        if len(commands) == 1:
            self.command_history.execute(commands[0])
        else:
            self.command_history.execute(MultiCommand(commands, f"Remove {self._shape_display_name(shape)}"))
        self._update_view()
        self.view.set_status(f"Deleted {self._shape_display_name(shape)}", FeedbackType.SUCCESS)

    def _get_attached_arrows(self, shape) -> list:
        """Return the arrow shapes whose endpoints reference the given shape."""
        if isinstance(shape, ArrowShape):
            return []
        return [s for s in self.diagram.shapes
                if isinstance(s, ArrowShape) and (s.from_shape == shape or s.to_shape == shape)]

    def _start_connection_from(self, shape):
        """Enter connect mode starting from the given shape."""
        self.connect_mode = True
        self.connecting_from = shape
        self.view.set_status(f"Connection started from {self._shape_display_name(shape)}. Click target shape.")

    @staticmethod
    def _shape_display_name(shape):
        """Translate internal model types into the palette's user-facing terms."""
        if isinstance(shape, ComponentBox):
            subtype = str(shape.properties.get("node_type", "")).lower()
            return {"root": "Root Component", "leaf": "Leaf Component",
                    "intermediate": "Composite Component"}.get(subtype, "Component")
        if isinstance(shape, ActionCircle):
            return "Step"
        if isinstance(shape, DiamondStep):
            return "Action"
        return "Arrow"

    def _reset_interaction(self):
        """Leave pending connection modes without changing diagram data."""
        self._clear_preview_line()
        self.arrow_mode = False
        self.connect_mode = False
        self.connecting_from = None
        self.dragging = False
        self.drag_start = None
        self.drag_shapes = []
        self.drag_initial_positions = {}
        self.view.canvas.config(cursor="")

    def add_shape(self, shape_type: str):
        """Add a new shape of the given type to the diagram."""
        if shape_type == "product":
            shape_type = "component_root"

        if shape_type == "component_root" and not self._allow_new_root():
            return

        if shape_type == "arrow":
            self.arrow_mode = True
            self.connecting_from = None
            self.view.canvas.config(cursor="")
            self.view.set_status("⚡ ARROW MODE: Click source shape, then target shape (Press ESC to cancel)")
            return

        self._reset_interaction()
        shape = self._create_shape_instance(shape_type, 0, 0)
        shape.x, shape.y = self._get_next_shape_position(shape)

        # Handle specialized component types
        if shape_type.startswith("component_"):
            requested = shape_type.split('_')[1].lower()
            node_type_map = {
                "root": "Root",
                "leaf": "Leaf",
                "composite": "Intermediate",
            }
            node_type = node_type_map.get(requested, "Intermediate")
            shape.properties['node_type'] = node_type
            if requested == "root":
                shape.properties.setdefault("name", "Root Component")
                shape.text = shape.properties.get("name") or "Root Component"

        command = AddShapeCommand(self.diagram, shape)
        self.command_history.execute(command)
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()
        self.view.set_status(f"Added {self._shape_display_name(shape)}", FeedbackType.SUCCESS)

    def _get_next_shape_position(self, shape=None) -> Tuple[float, float]:
        """Ask the View for initial document coordinates; creation stays undoable."""
        if shape is None:
            shape = ComponentBox(0, 0)
        return self.view.canvas.find_free_position(shape, self.diagram)

    def _create_shape_instance(self, shape_type: str, x: float, y: float):
        """Create a shape object of the given type at (x, y)."""
        if shape_type == "action":
            return ActionCircle(x, y)
        elif shape_type == "diamond":
            return DiamondStep(x, y)
        elif shape_type.startswith("component"):
            return ComponentBox(x, y)
        elif shape_type == "arrow":
            return ArrowShape(x, y)
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")

    def delete_selected(self):
        """Delete all currently selected shapes along with their arrows/connections."""
        if not self.diagram.selected_shapes:
            self.view.set_status("No shapes selected")
            return

        if self.arrow_mode or self.connect_mode:
            self._clear_preview_line()
            self._reset_interaction()

        selected = list(self.diagram.selected_shapes)

        to_delete = []
        for shape in selected:
            for arrow in self._get_attached_arrows(shape):
                if arrow not in to_delete and arrow not in selected:
                    to_delete.append(arrow)
        to_delete.extend(selected)

        commands = [RemoveShapeCommand(self.diagram, shape) for shape in to_delete]
        if len(commands) == 1:
            self.command_history.execute(commands[0])
        else:
            self.command_history.execute(MultiCommand(commands, "Remove selected shapes"))

        self._update_view()
        self.view.set_status("Deleted selected shapes", FeedbackType.SUCCESS)

    def select_all(self):
        """Select every shape in the diagram."""
        for shape in self.diagram.shapes:
            self.diagram.select_shape(shape, multi_select=True)
        self._update_view()
        self.view.set_status(f"Selected {len(self.diagram.shapes)} shapes")

    def toggle_connect_mode(self):
        """Turn connection mode on or off."""
        self.connect_mode = not self.connect_mode
        self.connecting_from = None

        if self.connect_mode:
            self.view.set_status("⚡ CONNECTION MODE ACTIVE: Click source shape, then target shape (Press C or ESC to exit)")
            self.view.canvas.config(cursor="")
        else:
            self.view.set_status("Connection mode disabled")
            self.view.canvas.config(cursor="")

    def apply_properties(self, shape, old_properties, new_properties):
        """Apply model edits; only explicit Save persists project changes."""
        structural = {'id', 'db_id', 'db_step_id', 'db_action_id', 'db_step_action_id',
                      'db_action_order', 'node_type', 'root_component_id', 'diagram_id', 'parent_id'}
        new_properties = {key: value for key, value in new_properties.items() if key not in structural}
        old_properties = {
            key: copy.deepcopy(shape.properties[key] if isinstance(shape, ComponentBox) and key in shape.properties
                               else getattr(shape, key, None))
            for key in new_properties
        }
        new_properties = {key: value for key, value in new_properties.items()
                          if old_properties[key] != value}
        old_properties = {key: old_properties[key] for key in new_properties}
        command = EditShapePropertiesCommand(shape, old_properties, new_properties, self.diagram)
        try:
            if isinstance(shape, ComponentBox):
                for field, getter in (("material_id", self.repository.get_material),
                                      ("color_id", self.repository.get_color)):
                    value = new_properties.get(field)
                    if value not in (None, "") and not getter(int(value)):
                        raise ValueError(f"Unknown {field.replace('_id', '')} selection")
                weight = new_properties.get("weight")
                if weight not in (None, ""):
                    float(weight)
            elif isinstance(shape, DiamondStep) and new_properties.get("tool_id"):
                if not self.repository.get_tool(int(new_properties["tool_id"])):
                    raise ValueError("Unknown tool selection")
        except (ValueError, TypeError) as exc:
            self.view.show_error("Cannot apply changes", str(exc))
            return False
        source = new_properties.get('image_path')
        if source and not str(source).replace('\\', '/').startswith('images/') and os.path.isfile(source):
            handler = getattr(self, 'image_handler', None) or get_image_handler()
            kind = 'component' if isinstance(shape, ComponentBox) else 'step' if isinstance(shape, ActionCircle) else 'action'
            product = next((s.properties.get('name') or s.text for s in self.diagram.shapes
                            if isinstance(s, ComponentBox) and str(s.properties.get('node_type', '')).lower() == 'root'), 'Product')
            try:
                stored = handler.upload_image(source, entity_type=kind, product_name=product)
            except (OSError, ValueError) as exc:
                self.view.show_error("Cannot apply changes", f"Failed to store the selected image: {exc}")
                return False
            if not stored:
                self.view.show_error("Cannot apply changes", "Failed to store the selected image.")
                return False
            new_properties = dict(new_properties, image_path=stored)
            command = EditShapePropertiesCommand(shape, old_properties, new_properties, self.diagram)
        if new_properties:
            self.command_history.execute(command)
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()
        self.view.set_status("Properties updated. Save to keep project changes.", FeedbackType.SUCCESS)
        return True

    def _storage_operation(self, method, *args):
        factory = getattr(self, 'persistence_factory', ProjectPersistence)
        storage = factory(self.repository, self.diagram, getattr(self, 'current_product_id', None))
        result = getattr(storage, method)(*args)
        self.current_product_id = storage.current_product_id
        return result

    def _persist_diagram(self):
        self._storage_operation('save')

    def _persist_shape_properties(self, shape):
        return self._storage_operation('_persist_shape_properties', shape)

    def undo(self):
        """Undo the last command."""
        if self.command_history.undo():
            self._update_view()
            self.view.set_status(f"Undone: {self.command_history.get_redo_description()}")
        else:
            self.view.set_status("Nothing to undo")

    def redo(self):
        """Redo the last undone command."""
        if self.command_history.redo():
            self._update_view()
            self.view.set_status(f"Redone: {self.command_history.get_undo_description()}")
        else:
            self.view.set_status("Nothing to redo")

    def can_undo(self) -> bool:
        """Return True if there is a command to undo."""
        return self.command_history.can_undo()

    def can_redo(self) -> bool:
        """Return True if there is a command to redo."""
        return self.command_history.can_redo()

    def toggle_grid(self):
        """Toggle the canvas grid display."""
        self.view.canvas.toggle_grid()
        self.view.set_status(f"Grid: {'on' if self.view.canvas.show_grid else 'off'}")

    def toggle_snap_mode(self):
        self.diagram.snap_to_grid = not self.diagram.snap_to_grid

        if hasattr(self.view.canvas, 'snap_to_grid'):
            self.view.canvas.snap_to_grid = self.diagram.snap_to_grid

        self.view.update_snap_button(snap_enabled=self.diagram.snap_to_grid)

        if self.diagram.snap_to_grid:
            self.view.set_status("Snap to grid: on")
        else:
            self.view.set_status("Snap to grid: off")
            
        self._update_view()

    def toggle_snap(self):
        """Toggle snap-to-grid for shape positioning."""
        self.diagram.snap_to_grid = not self.diagram.snap_to_grid
        self.view.set_status(f"Snap to grid: {'on' if self.diagram.snap_to_grid else 'off'}")

    def zoom_in(self):
        """
        Event handler triggered by the 'Zoom In' action shortcut.
        Instructs the view canvas component to perform the upscale algorithm 
        and updates the status bar message with the live zoom percentage.
        """
        
        self.view.canvas.zoom_in()
        self.view.set_status(f"Zoom: {int(self.view.canvas.zoom_factor * 100)}%")

    def zoom_out(self):
        """
        Event handler triggered by the 'Zoom Out' action shortcut.
        Instructs the view canvas component to perform the downscale algorithm 
        and updates the status bar message with the live zoom percentage.
        """
        self.view.canvas.zoom_out()
        self.view.set_status(f"Zoom: {int(self.view.canvas.zoom_factor * 100)}%")

    def reset_zoom(self):
        """
        Event handler triggered to restore default sizing.
        Resets the canvas view back to 100% scale and updates the status bar text.
        """
        self.view.canvas.reset_zoom()
        self.view.set_status("Zoom: 100%")


    def new_diagram(self):
        """Create a new diagram. Existing JSON storage entries are preserved."""
        if not self.check_unsaved_changes():
            return
        self._reset_interaction()
        self.diagram.clear()
        self.command_history.clear()
        self.current_product_id = None
        # Reset canvas to minimum size
        self.view.canvas.update_scroll_region_from_shapes([])
        self._update_view()
        self.view.set_status("New diagram created", FeedbackType.SUCCESS)

    def open_diagram(self):
        """Load a diagram from a JSON file chosen by the user."""
        if not self.check_unsaved_changes():
            return

        file_path = self.view.ask_file_path(save=False)
        if not file_path:
            return

        diagram = DiagramSerializer.load_from_file(file_path)
        if diagram:
            self._detach_imported_diagram(diagram)
            self._reset_interaction()
            self.diagram = diagram
            self.command_history.clear()
            # Update canvas scroll region to fit loaded shapes
            self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
            self._update_view()
            self.view.set_status(f"Opened: {os.path.basename(file_path)}", FeedbackType.SUCCESS)
        else:
            self.view.show_error("Error", "Failed to open file")

    def save_diagram(self):
        """Save diagram to JSON storage only (no JSON sync)."""
        try:
            # Save to JSON storage
            self._persist_diagram()
            
            # Get product name for status message
            product_name = "Diagram"
            if self.current_product_id:
                product = self.repository.get_product(self.current_product_id)
                if product:
                    product_name = product.get('name', 'Diagram')
            
            self.view.set_status(f"💾 Saved to JSON storage: {product_name}", FeedbackType.SUCCESS)
            return True
        except Exception as e:
            self.view.show_error("Save Error", f"Failed to save to JSON storage: {e}")
            return False

    def save_diagram_as(self):
        """
        Legacy JSON save function (for backward compatibility).
        Prefer using save_diagram() for storage and export_diagram_enhanced() for JSON.
        """
        file_path = self.view.ask_file_path(save=True)
        if not file_path:
            return False

        try:
            # Save to JSON file (legacy format)
            if DiagramSerializer.save_to_file(self.diagram, file_path):
                self.view.set_status(f"💾 Saved JSON: {os.path.basename(file_path)} (Legacy format)", FeedbackType.SUCCESS)
                return True
            else:
                self.view.show_error("Error", "Failed to save file")
                return False
        except Exception as e:
            self.view.show_error("Save Error", f"Failed to save: {e}")
            return False

    def clear_canvas(self):
        """Remove all shapes from the canvas after confirmation."""
        if not self.diagram.shapes:
            # Even with an empty canvas the command history may still hold
            # undoable commands (e.g. deletions), so reset it anyway.
            self.command_history.clear()
            self._update_view()
            self.view.set_status("Canvas is already empty")
            return

        if not self.view.ask_confirmation("Clear Canvas", "Are you sure you want to clear the canvas?"):
            return

        self.diagram.clear_selection()
        self.diagram.shapes.clear()
        self.diagram.connections.clear()
        self.command_history.clear()
        # Reset canvas to minimum size
        self.view.canvas.update_scroll_region_from_shapes([])
        self._update_view()
        self.diagram.modified = True
        self.view.set_status("Canvas cleared", FeedbackType.SUCCESS)

    def check_unsaved_changes(self) -> bool:
        """Prompt to save unsaved changes; return False to cancel the action."""
        self._cancel_auto_save()
        if not self.diagram.modified:
            return True

        result = self.view.ask_save_changes()

        if result == 'save':
            return self.save_diagram()
        elif result == 'discard':
            return True
        else:
            self.view.set_status("Operation cancelled.", FeedbackType.INFO)
            return False

    def show_add_color_dialog(self):
        """Open the dialog for adding a new color."""
        return self.view.show_catalog_dialog('color', self)

   

    def show_manage_colors_dialog(self):
        """Open the dialog for managing colors."""
        self.view.show_catalog_dialog('color', self, manage=True)


    def show_manage_materials_dialog(self):
        """Open the dialog for managing materials."""
        self.view.show_catalog_dialog('material', self, manage=True)

    def show_add_catalog_dialog(self, kind):
        return {'color': self.show_add_color_dialog,
                'material': self.show_add_material_dialog,
                'tool': self.show_add_tool_dialog}[kind]()

    def show_manage_tools_dialog(self):
        self.view.show_catalog_dialog('tool', self, manage=True)

    def delete_tool(self, tool_id):
        # Protect unsaved diagrams as well as references in repository records.
        if any(isinstance(shape, DiamondStep) and shape.tool_id == tool_id
               for shape in getattr(getattr(self, 'diagram', None), 'shapes', [])):
            raise ValueError("The tool cannot be deleted because it is assigned to an action.")
        try:
            success = self.repository.delete_tool(tool_id)
        except ValueError as exc:
            raise ValueError("The tool cannot be deleted because it is assigned to an action.") from exc
        if success:
            self.view.refresh_properties_panel()
        if success:
            self.view.set_status("Tool deleted successfully.", FeedbackType.SUCCESS)
        return success

    def add_new_color(self, name, hex_code, r, g, b):
        try:
            color_id = self.repository.create_color(name, hex_code, r, g, b)
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new color: {name}", FeedbackType.SUCCESS)
            return color_id
        except DuplicateValueError as exc:
            raise ValueError("Color already exists or violates a JSON storage rule.") from exc

    def delete_color(self, color_id: int) -> bool:
        """Deletes a color and refreshes the properties panel if needed."""
        if any(isinstance(shape, ComponentBox) and shape.properties.get("color_id") == color_id
               for shape in self.diagram.shapes):
            raise ValueError("The color cannot be deleted because it is assigned to a component.")
        try:
            success = self.repository.delete_color(color_id)
            if success:
                # If the property panel is open, we refresh it
                if hasattr(self.view, 'refresh_properties_panel'):
                    self.view.refresh_properties_panel()
            if success:
                self.view.set_status("Color deleted successfully.", FeedbackType.SUCCESS)
            return success
        except ValueError:
            raise ValueError("The color cannot be deleted because it is already assigned to a component.")
        except Exception as e:
            raise Exception(f"Error when deleting the color: {e}")

    def show_add_material_dialog(self):
        """Open the dialog for adding a new material."""
        return self.view.show_catalog_dialog('material', self)

    def add_new_material_category(self, name):
        try:
            category_id = self.repository.create_material_category(name)
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new material category: {name}", FeedbackType.SUCCESS)
            return category_id
        except DuplicateValueError as exc:
            raise ValueError("Material category already exists.") from exc

    def add_new_material_subcategory(self, category_id, name):
        try:
            subcategory_id = self.repository.create_material_subcategory(category_id, name)
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new material subcategory: {name}", FeedbackType.SUCCESS)
            return subcategory_id
        except DuplicateValueError as exc:
            raise ValueError("Material subcategory already exists or is invalid.") from exc

    def add_new_material_type(self, category_id, name, subcategory_id=None):
        try:
            type_id = self.repository.create_material_type(category_id, name, subcategory_id)
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new material type: {name}", FeedbackType.SUCCESS)
            return type_id
        except DuplicateValueError as exc:
            raise ValueError("Material type already exists or is invalid.") from exc

    def add_new_material(self, name, category_id=None, subcategory_id=None, type_id=None,
                         technical_name=""):
        try:
            material_id = self.repository.create_material(
                name=name,
                category_id=category_id,
                subcategory_id=subcategory_id,
                type_id=type_id,
                technical_name=technical_name,
            )
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new material: {name}", FeedbackType.SUCCESS)
            return material_id
        except DuplicateValueError as exc:
            raise ValueError("Material could not be saved because the selection is already in use or invalid.") from exc

    def delete_material(self, material_id: int) -> bool:
        """Deletes a material and refreshes the view."""
        if any(isinstance(shape, ComponentBox) and shape.properties.get("material_id") == material_id
               for shape in self.diagram.shapes):
            raise ValueError("The material cannot be deleted because it is assigned to a component.")
        try:
            success = self.repository.delete_material(material_id)
            if success:
                if hasattr(self.view, 'refresh_properties_panel'):
                    self.view.refresh_properties_panel()
            if success:
                self.view.set_status("Material deleted successfully.", FeedbackType.SUCCESS)
            return success
        except ValueError:
            raise ValueError("The material cannot be deleted because it is already assigned to a component.")
        except Exception as e:
            raise Exception(f"Error when deleting a material: {e}")

    def show_add_tool_dialog(self):
        """Open the dialog for adding a new tool."""
        return self.view.show_catalog_dialog('tool', self)

    def add_new_tool(self, name, category):
        try:
            tool_id = self.repository.create_tool(name, category)
            self.view.refresh_properties_panel()
            self.view.set_status(f"Added new tool: {name}", FeedbackType.SUCCESS)
            return tool_id
        except DuplicateValueError as exc:
            raise ValueError("Tool already exists or violates a JSON storage rule.") from exc

    def _cancel_auto_save(self):
        """Cancel legacy pending callbacks before prompting or replacing a project."""
        if self.auto_save_timer:
            self.view.root.after_cancel(self.auto_save_timer)
            self.auto_save_timer = None

    def _sync_navigator(self):
        navigator = getattr(self.view, 'navigator', None)
        if navigator is None:
            return
        snapshot = topology_snapshot(self.diagram)
        owner = (id(self.diagram), self.diagram.diagram_id)
        changed_owner = getattr(self, '_navigator_owner', None) != owner
        if changed_owner or getattr(self, '_navigator_snapshot', None) != snapshot:
            navigator.show_rows(build_outline(snapshot), reset=changed_owner)
            self._navigator_owner = owner
            self._navigator_snapshot = snapshot
        navigator.select_shapes([shape.id for shape in self.diagram.selected_shapes])

    def navigate_to_shape(self, shape_id):
        """Use normal model selection, without running geometry/layout edits."""
        shape = self.diagram.get_shape_by_id(shape_id)
        if shape is None:
            self._sync_navigator()
            return
        self.on_escape(None)
        self.dragging = False
        self.drag_shapes = []
        self.drag_initial_positions = {}
        self.drag_start = None
        previous = list(self.diagram.selected_shapes)
        self.diagram.select_shape(shape)
        for affected in dict.fromkeys(previous + [shape]):
            self.view.canvas.draw_shape(affected)
        self.view.update_properties_panel(shape)
        self._sync_navigator()
        self.view.canvas.center_on_shape(shape)
        self.view.update_ui_state()

    def _update_view(self):
        """Redraw the canvas and sync the properties panel with the selection."""
        self.view.canvas.redraw_all(self.diagram)

        if len(self.diagram.selected_shapes) == 1:
            selected_shape = self.diagram.selected_shapes[0]
            self.view.update_properties_panel(selected_shape)
            # Auto-scroll to show selected shape
            self.view.canvas.scroll_to_shape(selected_shape)
        else:
            self.view.update_properties_panel(None)

        self._sync_navigator()
        self.view.update_ui_state()
    
    # ==================== NEW: PRODUCT LIST & LOAD ====================
    
    def delete_product(self, product_id: int) -> bool:
        """Delete a saved product through the controller boundary."""
        return self.repository.delete_product(product_id)

    def show_product_list(self):
        """Show product list dialog to load a saved diagram."""
        self.view.show_product_list(self, self.load_product_diagram)
    
    def load_product_diagram(self, product_id: int):
        """
        Load complete diagram for a product from JSON storage.
        
        Args:
            product_id: Root component ID to load
        """
        if not self.check_unsaved_changes():
            return
        
        try:
            # Load diagram from JSON storage
            diagram = self.diagram_loader.load_product_diagram(product_id)
            
            if diagram:
                self._reset_interaction()
                self.diagram = diagram
                self.current_product_id = product_id
                self.command_history.clear()
                
                # Update canvas scroll region to fit loaded shapes
                self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
                self._update_view()
                
                # Get product info for status
                product = self.repository.get_product(product_id)
                product_name = product.get('name', 'Product') if product else 'Product'
                self.view.set_status(f"Loaded: {product_name} (ID: {product_id})", FeedbackType.SUCCESS)
            else:
                self.view.show_error("Error", f"Failed to load product diagram (ID: {product_id})")
                
        except Exception as e:
            self.view.show_error("Error", f"Failed to load diagram: {e}")
            import traceback
            traceback.print_exc()
    
    def export_diagram_enhanced(self):
        """Export a portable ZIP containing diagram.json and all referenced images."""
        file_path = self.view.ask_file_path(
            save=True, file_types=[("ARIADNE project", "*.zip"), ("ZIP files", "*.zip")]
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".zip"):
            file_path += ".zip"
        try:
            # Export is intentionally independent of internal persistence:
            # serialize the active in-memory diagram and its referenced images.
            self.archive_service.export_zip(self.diagram, file_path)
            warnings = self.archive_service.last_export_warnings
            if warnings:
                self.view.set_status(
                    f"Exported {os.path.basename(file_path)}; "
                    f"skipped {len(warnings)} missing image(s)", FeedbackType.WARNING
                )
            else:
                self.view.set_status(f"Exported project: {os.path.basename(file_path)}", FeedbackType.SUCCESS)
        except Exception as exc:
            # Do not hide the real filesystem/serialization/ZIP error.
            self.view.show_error(
                "Export failed",
                f"Could not export project ZIP:\n\n{type(exc).__name__}: {exc}"
            )
            import traceback
            traceback.print_exc()

    def export_document(self, format_id: str):
        """Export the active in-memory diagram using one of the document converters."""
        label, ext = self.document_export_service.FORMATS[format_id]
        file_path = self.view.ask_file_path(save=True, file_types=[(label, f"*{ext}")])
        if not file_path:
            return
        try:
            result = self.document_export_service.export(self.diagram, file_path, format_id)
            self.view.set_status(f"Exported {label}: {os.path.basename(result)}", FeedbackType.SUCCESS)
        except Exception as exc:
            self.view.show_error(f"{label} export failed", f"Could not export {label}:\n\n{type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()

    def export_presentation(self):
        return self.export_document("pptx")

    def _detach_imported_diagram(self, diagram):
        """An imported project is an independent copy, never a name-based merge."""
        diagram.diagram_id = str(uuid4())
        self.current_product_id = None
        for shape in diagram.shapes:
            if isinstance(shape, ComponentBox):
                shape.properties["db_id"] = None
            else:
                for key in ("db_step_id", "db_action_id", "db_step_action_id", "db_action_order"):
                    if hasattr(shape, key):
                        setattr(shape, key, None)

    def import_diagram_enhanced(self):
        """Import a portable ARIADNE ZIP (diagram JSON + images)."""
        if not self.check_unsaved_changes():
            return
        file_path = self.view.ask_file_path(
            save=False, file_types=[("ARIADNE project", "*.zip"), ("ZIP files", "*.zip"), ("JSON files", "*.json")]
        )
        if not file_path:
            return
        try:
            if file_path.lower().endswith(".zip"):
                diagram = self.archive_service.import_zip(file_path)
            else:
                diagram = self.json_exporter.import_diagram(file_path, create_in_repository=False)
            if not diagram:
                self.view.show_error("Error", "Failed to import project")
                return
            self._detach_imported_diagram(diagram)
            self._reset_interaction()
            self.diagram = diagram
            self.diagram.file_path = None
            self.diagram.auto_sync_json = False
            self.current_product_id = None
            self.command_history.clear()
            self._persist_diagram()
            self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
            self._update_view()
            notices = getattr(diagram, "import_warnings", [])
            if notices:
                self.view.set_status("Imported with warnings: " + "; ".join(notices), FeedbackType.WARNING)
            else:
                self.view.set_status(f"Imported project: {os.path.basename(file_path)}", FeedbackType.SUCCESS)
        except Exception as exc:
            self.view.show_error("Error", f"Import failed: {exc}")

