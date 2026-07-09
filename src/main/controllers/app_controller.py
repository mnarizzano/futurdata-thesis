import tkinter as tk
from typing import Optional, Tuple
import os
import sqlite3

from ..models import Diagram, ActionCircle, DiamondStep, ComponentBox, ArrowShape, Connection
from ..models.database import get_database
from ..views.add_color_dialog import AddColorDialog
from ..views.add_material_dialog import AddMaterialDialog
from ..views.add_tool_dialog import AddToolDialog
from ..utils import (
    CommandHistory, AddShapeCommand, RemoveShapeCommand, MoveShapeCommand,
    AddConnectionCommand, EditShapePropertiesCommand, MultiCommand, snap_to_grid,
    find_alignment_guides, DiagramSerializer
)
from ..utils.diagram_loader import DiagramLoader
from ..utils.json_exporter import EnhancedJSONExporter
from ..views.manage_colors_dialog import ManageColorsDialog
from ..views.manage_materials_dialog import ManageMaterialsDialog


class AppController:

    def __init__(self):
        """Initialize controller state, models and helper services."""
        self.diagram = Diagram()
        self.command_history = CommandHistory()
        self.view = None
        self.db = get_database()
        self.diagram_loader = DiagramLoader(self.db)
        self.json_exporter = EnhancedJSONExporter(self.db)
        self.current_product_id = None  # Track currently loaded product
        self.selected_shape = None
        self.dragging = False
        self.drag_start = None
        self.drag_initial_positions = {}
        self.drag_shapes = []
        self.connect_mode = False
        self.arrow_mode = False
        self.connecting_from = None
        self.preview_line_id = None

    def set_view(self, view):
        """Attach the view and wire up canvas event bindings."""
        self.view = view
        self._bind_canvas_events()

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
            x = self.view.canvas.canvasx(event.x)
            y = self.view.canvas.canvasy(event.y)
            # Draw preview line from connecting_from shape to mouse cursor
            self._update_preview_line(self.connecting_from.x, self.connecting_from.y, x, y)

    def _update_preview_line(self, x1, y1, x2, y2):
        """Draw or update the preview line for arrow/connection."""
        canvas = self.view.canvas
        if self.preview_line_id is not None:
            canvas.delete(self.preview_line_id)
        self.preview_line_id = canvas.create_line(
            x1, y1, x2, y2,
            fill="black", width=2, dash=(5, 5),
            arrow=tk.LAST, arrowshape=(12, 15, 6),
            tags="preview"
        )

    def _clear_preview_line(self):
        """Remove the preview line."""
        if self.preview_line_id is not None:
            self.view.canvas.delete(self.preview_line_id)
            self.preview_line_id = None

    def on_escape(self, event):
        """Cancel arrow/connect mode."""
        if self.arrow_mode or self.connect_mode:
            self._clear_preview_line()
            self.arrow_mode = False
            self.connect_mode = False
            self.connecting_from = None
            self.view.canvas.config(cursor="")
            self.view.set_status("Cancelled")
            self.view.root.after(1500, lambda: self.view.set_status("Ready"))

    def on_canvas_click(self, event):
        """Handle left-click: select a shape, start a drag, or start a connection."""
        x = self.view.canvas.canvasx(event.x)
        y = self.view.canvas.canvasy(event.y)
        clicked_shape = self.diagram.find_shape_at_point(x, y)

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

        x = self.view.canvas.canvasx(event.x)
        y = self.view.canvas.canvasy(event.y)
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
        """Scroll the canvas when mouse is near the edge of visible area."""
        canvas = self.view.canvas
        margin = 50  # Distance from edge to trigger scroll

        visible_width = canvas.winfo_width()
        visible_height = canvas.winfo_height()

        # Scroll right
        if mouse_x > visible_width - margin:
            canvas.xview_scroll(1, "units")
        # Scroll left
        elif mouse_x < margin:
            canvas.xview_scroll(-1, "units")

        # Scroll down
        if mouse_y > visible_height - margin:
            canvas.yview_scroll(1, "units")
        # Scroll up
        elif mouse_y < margin:
            canvas.yview_scroll(-1, "units")

    def on_canvas_release(self, event):
        """Finish a drag: snap, record the move command and redraw."""
        if self.dragging and self.drag_shapes and self.drag_initial_positions:
            # Snap to grid on release if enabled
            if self.diagram.snap_to_grid:
                for shape in self.drag_shapes:
                    shape.x, shape.y = snap_to_grid(shape.x, shape.y)

            first_shape = self.drag_shapes[0]
            initial_pos = self.drag_initial_positions[first_shape]
            dx = first_shape.x - initial_pos[0]
            dy = first_shape.y - initial_pos[1]

            if abs(dx) > 1 or abs(dy) > 1:
                command = MoveShapeCommand(self.drag_shapes, dx, dy)
                self.command_history.history.append(command)
                self.command_history.current_index += 1

        self.dragging = False
        self.drag_start = None
        self.drag_shapes = []
        self.drag_initial_positions = {}
        self.view.canvas.clear_alignment_guides()
        # Redraw grid to cover expanded canvas area
        self.view.canvas.draw_grid()
        # Full redraw to sync canvas with snapped positions
        self.view.canvas.redraw_all(self.diagram)
        self._update_view()

    def on_canvas_right_click(self, event):
        """Show the context menu for the shape under the cursor."""
        x = self.view.canvas.canvasx(event.x)
        y = self.view.canvas.canvasy(event.y)
        clicked_shape = self.diagram.find_shape_at_point(x, y)

        if clicked_shape:
            if self.arrow_mode or self.connect_mode:
                self._clear_preview_line()
                self.arrow_mode = False
                self.connect_mode = False
                self.connecting_from = None
            self._show_context_menu(event, clicked_shape)

    def _show_context_menu(self, event, shape):
        """Build and display the right-click context menu for a shape."""
        menu = tk.Menu(self.view.root, tearoff=0)
        menu.add_command(label="Edit Properties", command=lambda: self._edit_shape_properties(shape))
        menu.add_separator()
        menu.add_command(label="Duplicate", command=lambda: self._duplicate_shape(shape))
        menu.add_command(label="Delete", command=lambda: self._delete_shape(shape))
        menu.post(event.x_root, event.y_root)

    def _handle_arrow_connection_click(self, shape):
        """Pick source then target shape to create an arrow in arrow mode."""
        # Also select the shape so Delete key works
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()

        if self.connecting_from is None:
            self.connecting_from = shape
            # Draw initial preview line from shape center (draw AFTER update_view)
            self._update_preview_line(shape.x, shape.y, shape.x + 100, shape.y)
            self.view.set_status(f"Arrow started from {shape.shape_type}. Click target shape or press Delete to remove.")
        else:
            self._clear_preview_line()
            if self.connecting_from != shape:
                self._create_arrow_connection(self.connecting_from, shape)
                self.view.set_status("Arrow created.")
            else:
                self.view.set_status("Cancelled - same shape.")
            self.connecting_from = None
            self.arrow_mode = False
            self.view.canvas.config(cursor="")
            self.view.root.after(2000, lambda: self.view.set_status("Ready"))
            self._update_view()

    def _handle_connection_click(self, shape):
        """Pick source then target shape to create a connection in connect mode."""
        if self.connecting_from is None:
            self.connecting_from = shape
            self.view.set_status(f"Connection started from {shape.shape_type}. Click target shape or press ESC to cancel.")
        else:
            self._clear_preview_line()
            if self.connecting_from != shape:
                self._create_connection(self.connecting_from, shape)
                self.view.set_status("Connection created.")
            else:
                self.view.set_status("Cancelled - same shape.")
            self.connecting_from = None
            self.connect_mode = False
            self.view.root.after(2000, lambda: self.view.set_status("Ready"))

    def _create_arrow_connection(self, from_shape, to_shape):
        """Create an arrow shape between two shapes and sync it to the DB."""
        arrow = ArrowShape(0, 0, from_shape, to_shape)
        arrow.update_from_shapes()
        command = AddShapeCommand(self.diagram, arrow)
        self.command_history.execute(command)
        self._sync_connection_to_db(from_shape, to_shape)
        self._update_view()

    def _create_connection(self, from_shape, to_shape):
        """Create a connection between two shapes and sync it to the DB."""
        connection = Connection(from_shape, to_shape)
        connection.auto_calculate_anchors()
        command = AddConnectionCommand(self.diagram, connection)
        self.command_history.execute(command)
        self._sync_connection_to_db(from_shape, to_shape)
        self._update_view()

    def _sync_connection_to_db(self, from_shape, to_shape):
        """Persist key canvas relationships to DB."""
        try:
            # Component -> Circle defines step input.
            if isinstance(from_shape, ComponentBox) and isinstance(to_shape, ActionCircle):
                self._ensure_component_db_id(from_shape)
                self._ensure_step_db_id(to_shape, input_shape=from_shape)
                return

            # Circle -> Component defines step outputs.
            if isinstance(from_shape, ActionCircle) and isinstance(to_shape, ComponentBox):
                step_id = self._ensure_step_db_id(from_shape)
                component_id = self._ensure_component_db_id(to_shape)
                if step_id and component_id:
                    result = self.db.add_component_to_step(step_id, component_id)
                    if result.get("already_linked"):
                        self.view.set_status("Output already linked to this step.")
                return

            # Circle -> Diamond defines step-action mapping.
            if isinstance(from_shape, ActionCircle) and isinstance(to_shape, DiamondStep):
                step_id = self._ensure_step_db_id(from_shape)
                existing_step_id = self._resolve_step_id_for_diamond(to_shape)
                if existing_step_id is not None and existing_step_id != step_id:
                    self.view.set_status("Action belongs to another step.")
                    return
                action_id = self._ensure_action_db_id(to_shape)
                result = self.db.add_action_to_step(step_id, action_id)
                to_shape.db_step_id = step_id
                to_shape.db_action_id = action_id
                to_shape.db_step_action_id = result["link_id"]
                to_shape.db_action_order = result["action_order"]
                if result.get("already_linked"):
                    self.view.set_status("Action already linked to this step.")
                return

            # Diamond -> Diamond encodes action sequence for the same step.
            if isinstance(from_shape, DiamondStep) and isinstance(to_shape, DiamondStep):
                step_id = self._resolve_step_id_for_diamond(from_shape)
                if step_id is None:
                    raise ValueError("Connect circle to first diamond before chaining actions")
                target_step_id = self._resolve_step_id_for_diamond(to_shape)
                if target_step_id is not None and target_step_id != step_id:
                    self.view.set_status("Action belongs to another step.")
                    return

                action_id = self._ensure_action_db_id(to_shape)
                result = self.db.add_action_to_step(step_id, action_id)
                to_shape.db_step_id = step_id
                to_shape.db_action_id = action_id
                to_shape.db_step_action_id = result["link_id"]
                to_shape.db_action_order = result["action_order"]
                if result.get("already_linked"):
                    self.view.set_status("Action already linked to this step.")
                return
        except sqlite3.IntegrityError:
            # Ignore duplicate links constrained by unique indexes.
            pass
        except Exception as exc:
            self.view.set_status(f"DB sync warning: {exc}")

    def _ensure_component_db_id(self, shape: ComponentBox) -> Optional[int]:
        """Return the component's DB id, creating the DB row if needed."""
        db_id = shape.properties.get("db_id")
        if db_id:
            return int(db_id)

        node_type = str(shape.properties.get("node_type", "Intermediate")).strip() or "Intermediate"
        node_type = node_type.capitalize()

        name = str(shape.properties.get("name") or shape.text or f"{node_type} Component").strip()
        color_id = shape.properties.get("color_id") or None
        material_id = shape.properties.get("material_id") or None
        weight_val = shape.properties.get("weight")
        try:
            weight = float(weight_val) if str(weight_val).strip() else None
        except (TypeError, ValueError):
            weight = None
        weight_unit = shape.properties.get("weight_unit") or "g"

        if node_type == "Root":
            comp_id = self.db.create_component(
                name=name,
                color_id=color_id,
                material_id=material_id,
                weight=weight,
                weight_unit=weight_unit,
                node_type="Root",
            )
        else:
            root_component_id = self._get_root_component_id()
            if root_component_id is None:
                raise ValueError("Add a Root Component first so Leaf/Composite can link to it")
            comp_id = self.db.create_component(
                name=name,
                product_id=root_component_id,
                color_id=color_id,
                material_id=material_id,
                weight=weight,
                weight_unit=weight_unit,
                node_type=node_type,
            )

        shape.properties["db_id"] = comp_id
        return comp_id

    def _get_root_component_id(self) -> Optional[int]:
        """Return the DB id of the diagram's root component, if any."""
        for shape in self.diagram.shapes:
            if isinstance(shape, ComponentBox):
                node_type = str(shape.properties.get("node_type", "")).strip().lower()
                if node_type == "root":
                    return self._ensure_component_db_id(shape)
        return None

    def _ensure_step_db_id(self, step_shape: ActionCircle, input_shape: Optional[ComponentBox] = None) -> Optional[int]:
        """Return the step's DB id, creating the DB row if needed."""
        step_id = getattr(step_shape, "db_step_id", None)
        if input_shape is None:
            input_shape = self._resolve_input_shape_for_step(step_shape)

        if step_id:
            if input_shape is not None:
                component_id = self._ensure_component_db_id(input_shape)
                self.db.update_step(int(step_id), component_id=component_id)
            return int(step_id)

        if input_shape is None:
            for shape in self.diagram.shapes:
                if isinstance(shape, ComponentBox) and str(shape.properties.get("node_type", "")).strip().lower() == "root":
                    input_shape = shape
                    break

        if input_shape is None:
            raise ValueError("Step needs an input component (connect a component to the circle first)")

        component_id = self._ensure_component_db_id(input_shape)
        step_order = self.db.get_next_step_order(component_id)
        title = str(step_shape.text or "Disassembly Step").strip()
        description = str(step_shape.step_description or "").strip()
        image_path = str(step_shape.image_path or "").strip()

        step_id = self.db.create_step(
            component_id=component_id,
            step_order=step_order,
            description=description,
            image_path=image_path,
            action_id=None,
            title=title,
        )
        # Keep display text/title aligned.
        step_shape.text = title
        step_shape.db_step_id = step_id
        return step_id

    def _resolve_input_shape_for_step(self, step_shape: ActionCircle) -> Optional[ComponentBox]:
        """Find the component feeding into a step, falling back to the root."""
        for conn in self.diagram.connections:
            if conn.to_shape == step_shape and isinstance(conn.from_shape, ComponentBox):
                return conn.from_shape

        for shape in self.diagram.shapes:
            if isinstance(shape, ComponentBox) and str(shape.properties.get("node_type", "")).strip().lower() == "root":
                return shape
        return None

    def _ensure_action_db_id(self, action_shape: DiamondStep) -> Optional[int]:
        """Return the action's DB id, creating the DB row if needed."""
        action_id = getattr(action_shape, "db_action_id", None)
        if action_id:
            return int(action_id)

        action_name = str(action_shape.name or action_shape.text or "Action").strip()
        tool_val = str(action_shape.tools or "").strip()
        action_id = self.db.create_action(name=action_name, description="", tool_id=None)
        action_shape.db_action_id = action_id
        if action_shape.name:
            action_shape.text = action_shape.name
        else:
            action_shape.name = action_name
            action_shape.text = action_name
        if tool_val:
            action_shape.tools = tool_val
        return action_id

    def _resolve_step_id_for_diamond(self, diamond_shape: DiamondStep) -> Optional[int]:
        """Return the step a diamond belongs to, inferring from connections."""
        step_id = getattr(diamond_shape, "db_step_id", None)
        if step_id:
            return int(step_id)

        # Try to infer from an incoming circle->diamond connection.
        for conn in self.diagram.connections:
            if conn.to_shape == diamond_shape and isinstance(conn.from_shape, ActionCircle):
                inferred = self._ensure_step_db_id(conn.from_shape)
                if inferred:
                    diamond_shape.db_step_id = inferred
                    return inferred
        return None

    def _edit_shape_properties(self, shape):
        """Select a shape so its properties show in the panel."""
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()

    def _duplicate_shape(self, shape):
        """Create a copy of a shape offset from the original."""
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
        self.view.set_status(f"Duplicated {shape.shape_type}")

    def _delete_shape(self, shape):
        """Delete a shape, removing any arrows/connections attached to it."""
        if not self._delete_shape_from_db(shape):
            return

        commands = [RemoveShapeCommand(self.diagram, arrow)
                    for arrow in self._get_attached_arrows(shape)]
        commands.append(RemoveShapeCommand(self.diagram, shape))
        if len(commands) == 1:
            self.command_history.execute(commands[0])
        else:
            self.command_history.execute(MultiCommand(commands, f"Remove {shape.shape_type}"))
        self._update_view()
        self.view.set_status(f"Deleted {shape.shape_type}")

    def _get_attached_arrows(self, shape) -> list:
        """Return the arrow shapes whose endpoints reference the given shape."""
        if isinstance(shape, ArrowShape):
            return []
        return [s for s in self.diagram.shapes
                if isinstance(s, ArrowShape) and (s.from_shape == shape or s.to_shape == shape)]

    def _delete_shape_from_db(self, shape) -> bool:
        """Delete corresponding DB entity for a shape if it exists.

        Action ordering is not compacted after deletes. If an action link is removed,
        remaining action_order values keep their original numbers and future inserts append.
        """
        try:
            if isinstance(shape, ComponentBox):
                db_id = shape.properties.get("db_id")
                if db_id:
                    self.db.delete_component(int(db_id))
            elif isinstance(shape, ActionCircle):
                step_id = getattr(shape, "db_step_id", None)
                if step_id:
                    self.db.delete_step(int(step_id))
            elif isinstance(shape, DiamondStep):
                action_id = getattr(shape, "db_action_id", None)
                if action_id:
                    self.db.delete_action(int(action_id))
            return True
        except sqlite3.IntegrityError:
            self.view.set_status("Cannot delete in DB due to existing references.")
            return False
        except Exception as exc:
            self.view.set_status(f"DB delete failed: {exc}")
            return False

    def _start_connection_from(self, shape):
        """Enter connect mode starting from the given shape."""
        self.connect_mode = True
        self.connecting_from = shape
        self.view.set_status(f"Connection started from {shape.shape_type}. Click target shape.")

    def add_shape(self, shape_type: str):
        """Add a new shape of the given type to the diagram."""
        if shape_type == "product":
            shape_type = "component_root"

        if shape_type == "arrow":
            self.arrow_mode = True
            self.connecting_from = None
            self.view.canvas.config(cursor="crosshair")
            self.view.set_status("⚡ ARROW MODE: Click source shape, then target shape (Press ESC to cancel)")
            return

        x, y = self._get_next_shape_position()
        shape = self._create_shape_instance(shape_type, x, y)

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
            self.view.set_status(f"Added {requested.capitalize()} Component")
        else:
            self.view.set_status(f"Added {shape_type}")

        command = AddShapeCommand(self.diagram, shape)
        self.command_history.execute(command)
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()

    def _get_next_shape_position(self) -> Tuple[float, float]:
        """
        Return a position for new shape in visible viewport area.
        Tries to place shapes in visible area, staggers if multiple shapes added.
        """
        # Get current viewport (visible area)
        x_view = self.view.canvas.xview()
        y_view = self.view.canvas.yview()
        
        canvas_width = self.view.canvas.canvas_width
        canvas_height = self.view.canvas.canvas_height
        visible_width = self.view.canvas.winfo_width()
        visible_height = self.view.canvas.winfo_height()
        
        # If canvas not rendered yet, use default
        if visible_width <= 1 or visible_height <= 1:
            base_x, base_y = 700, 400
            index = len(self.diagram.shapes)
            col = index % 4
            row = index // 4
            return base_x + (col * 220), base_y + (row * 140)
        
        # Calculate visible area in canvas coordinates
        visible_x1 = x_view[0] * canvas_width
        visible_y1 = y_view[0] * canvas_height
        
        # Place shape in center of visible area with stagger
        center_x = visible_x1 + (visible_width / 2)
        center_y = visible_y1 + (visible_height / 2)
        
        # Add stagger based on recent shapes (last 10)
        recent_shapes = self.diagram.shapes[-10:]
        stagger_offset = len(recent_shapes) % 5
        
        x = center_x + (stagger_offset * 50)
        y = center_y + (stagger_offset * 40)
        
        return x, y

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
            self.arrow_mode = False
            self.connect_mode = False
            self.connecting_from = None

        selected = list(self.diagram.selected_shapes)

        for shape in selected:
            if not self._delete_shape_from_db(shape):
                return

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
        self.view.set_status("Deleted selected shapes")

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
            self.view.canvas.config(cursor="crosshair")
        else:
            self.view.set_status("Connection mode disabled")
            self.view.canvas.config(cursor="")
            self.view.root.after(1500, lambda: self.view.set_status("Ready"))

    def apply_properties(self, shape, old_properties, new_properties):
        """Apply edited properties to a shape and persist them to the DB."""
        command = EditShapePropertiesCommand(shape, old_properties, new_properties)
        self.command_history.execute(command)
        self._persist_shape_properties(shape)
        self.diagram.select_shape(shape, multi_select=False)
        self._update_view()
        self.view.set_status("Properties updated")

    def _persist_diagram_to_db(self):
        """Flush current in-memory shapes to DB before file save/export."""
        roots = []
        others = []
        for shape in self.diagram.shapes:
            if isinstance(shape, ComponentBox) and str(shape.properties.get("node_type", "")).strip().lower() == "root":
                roots.append(shape)
            else:
                others.append(shape)

        for shape in roots + others:
            try:
                self._persist_shape_properties(shape)
            except Exception:
                # Keep file save resilient; DB sync for relationships is handled separately.
                continue

    def _persist_shape_properties(self, shape):
        """Persist edited shape properties to the backing database when possible."""
        if isinstance(shape, ComponentBox):
            component_id = self._ensure_component_db_id(shape)
            updates = dict(shape.properties)
            updates.pop("db_id", None)

            safe_updates = {k: v for k, v in updates.items() if not (k == 'root_component_id' and (v is None or str(v).strip() in ('', 'None')))}
            self.db.update_component(int(component_id), **safe_updates)
            shape.properties["db_id"] = int(component_id)
            
        if 'root_component_id' in updates:
            val = updates['root_component_id']
            node_type = shape.properties.get('node_type', '')
            
            if node_type == 'Root':
                updates['root_component_id'] = ""
            else:
                # For Leaf or Composite nodes, if the value comes as None or "None",
                # try to salvage the actual ID stored in the object's memory.
                if val is None or str(val).strip() in ('', 'None'):
                    real_id = shape.properties.get('root_component_id')
                    if real_id and str(real_id).strip() not in ('', 'None'):
                        updates['root_component_id'] = int(real_id)
                    else:
                        # If there is absolutely no real ID, send "" so the DB
                        # triggers its 'else None' and avoids throwing a TypeError
                        updates['root_component_id'] = ""

        if isinstance(shape, ActionCircle):
            try:
                step_id = self._ensure_step_db_id(shape)
            except ValueError:
                return
            self.db.update_step(
                int(step_id),
                title=str(shape.text or "").strip(),
                description=str(shape.step_description or "").strip(),
                image_path=str(shape.image_path or "").strip(),
            )
            shape.db_step_id = int(step_id)
            return

        if isinstance(shape, DiamondStep):
            action_id = self._ensure_action_db_id(shape)
            self.db.update_action(
                int(action_id),
                name=str(shape.name or shape.text or "").strip(),
                description=str(shape.description or "").strip(),
                tool_id=shape.tool_id or None,
            )
            shape.db_action_id = int(action_id)

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
        """Create a new diagram. Existing database entries are preserved."""
        if not self.check_unsaved_changes():
            return
        self.diagram.clear()
        self.command_history.clear()
        self.current_product_id = None
        # Reset canvas to minimum size
        self.view.canvas.update_scroll_region_from_shapes([])
        self._update_view()
        self.view.set_status("New diagram created (Database preserved - use 'Load Product' to see saved diagrams)")

    def open_diagram(self):
        """Load a diagram from a JSON file chosen by the user."""
        if not self.check_unsaved_changes():
            return

        file_path = self.view.ask_file_path(save=False)
        if not file_path:
            return

        diagram = DiagramSerializer.load_from_file(file_path)
        if diagram:
            self.diagram = diagram
            self.command_history.clear()
            # Update canvas scroll region to fit loaded shapes
            self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
            self._update_view()
            self.view.set_status(f"Opened: {os.path.basename(file_path)}")
        else:
            self.view.show_error("Error", "Failed to open file")

    def save_diagram(self):
        """Save diagram to database only. Use Export for JSON."""
        try:
            # Save to database
            self._persist_diagram_to_db()
            
            # Get product name for status message
            product_name = "Diagram"
            if self.current_product_id:
                product = self.db.get_product(self.current_product_id)
                if product:
                    product_name = product.get('name', 'Diagram')
            
            self.view.set_status(f"💾 Saved to database: {product_name}")
            return True
        except Exception as e:
            self.view.show_error("Save Error", f"Failed to save to database: {e}")
            return False

    def save_diagram_as(self):
        """
        Legacy JSON save function (for backward compatibility).
        Prefer using save_diagram() for DB and export_diagram_enhanced() for JSON.
        """
        file_path = self.view.ask_file_path(save=True)
        if not file_path:
            return False

        self.diagram.file_path = file_path

        try:
            # Save to JSON file (legacy format)
            if DiagramSerializer.save_to_file(self.diagram, file_path):
                self.view.set_status(f"💾 Saved JSON: {os.path.basename(file_path)} (Legacy format)")
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

        from tkinter import messagebox
        if not messagebox.askyesno("Clear Canvas", "Are you sure you want to clear the canvas?"):
            return

        self.diagram.clear()
        self.command_history.clear()
        # Reset canvas to minimum size
        self.view.canvas.update_scroll_region_from_shapes([])
        self._update_view()
        self.view.set_status("Canvas cleared")

    def check_unsaved_changes(self) -> bool:
        """Prompt to save unsaved changes; return False to cancel the action."""
        if not self.diagram.modified:
            return True

        result = self.view.ask_save_changes()

        if result == 'save':
            return self.save_diagram()
        elif result == 'discard':
            return True
        else:
            return False

    def show_add_color_dialog(self):
        """Open the dialog for adding a new color."""
        AddColorDialog(self.view.root, self)

    def show_manage_colors_dialog(self):
        """Open the dialog for managing colors."""
        ManageColorsDialog(self.view.root, self)

    def add_new_color(self, name, hex_code, r, g, b):
        """Create a new color in the DB and refresh the panel."""
        self.db.create_color(name, hex_code, r, g, b)
        self.view.refresh_properties_panel()
        self.view.set_status(f"Added new color: {name}")

    def delete_color(self, color_id: int) -> bool:
        """Deletes a color and refreshes the properties panel if needed."""
        try:
            success = self.db.delete_color(color_id)
            if success:
                # If the property panel is open, we refresh it
                if hasattr(self.view, 'refresh_properties_panel'):
                    self.view.refresh_properties_panel()
            return success
        except sqlite3.IntegrityError:
            raise ValueError("The color cannot be deleted because it is already assigned to a component.")
        except Exception as e:
            raise Exception(f"Error when deleting the color: {e}")

    def show_add_material_dialog(self):
        """Open the dialog for adding a new material."""
        AddMaterialDialog(self.view.root, self)

    def show_manage_materials_dialog(self):
        """Open the dialog for managing materials."""
        ManageMaterialsDialog(self.view.root, self)

    def add_new_material(self, name, sci_name, color_id):
        """Create a new material in the DB and refresh the panel."""
        self.db.create_material(name, sci_name, color_id)
        self.view.refresh_properties_panel()
        self.view.set_status(f"Added new material: {name}")

    def delete_material(self, material_id: int) -> bool:
        """Deletes a material and refreshes the view."""
        try:
            success = self.db.delete_material(material_id)
            if success:
                if hasattr(self.view, 'refresh_properties_panel'):
                    self.view.refresh_properties_panel()
            return success
        except sqlite3.IntegrityError:
            raise ValueError("The material cannot be deleted because it is already assigned to a component.")
        except Exception as e:
            raise Exception(f"Error when deleting a material: {e}")

    def show_add_tool_dialog(self):
        """Open the dialog for adding a new tool."""
        AddToolDialog(self.view.root, self)

    def add_new_tool(self, name, category):
        """Create a new tool in the DB and refresh the panel."""
        self.db.create_tool(name, category)
        self.view.refresh_properties_panel()
        self.view.set_status(f"Added new tool: {name}")

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

        self.view.update_ui_state()
    
    # ==================== NEW: PRODUCT LIST & LOAD ====================
    
    def show_product_list(self):
        """Show product list dialog to load a saved diagram."""
        from ..views.product_list_dialog import ProductListDialog
        ProductListDialog(self.view.root, self.db, self.load_product_diagram)
    
    def load_product_diagram(self, product_id: int):
        """
        Load complete diagram for a product from database.
        
        Args:
            product_id: Root component ID to load
        """
        if not self.check_unsaved_changes():
            return
        
        try:
            # Load diagram from database
            diagram = self.diagram_loader.load_product_diagram(product_id)
            
            if diagram:
                self.diagram = diagram
                self.current_product_id = product_id
                self.command_history.clear()
                
                # Update canvas scroll region to fit loaded shapes
                self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
                self._update_view()
                
                # Get product info for status
                product = self.db.get_product(product_id)
                product_name = product.get('name', 'Product') if product else 'Product'
                self.view.set_status(f"Loaded: {product_name} (ID: {product_id})")
            else:
                self.view.show_error("Error", f"Failed to load product diagram (ID: {product_id})")
                
        except Exception as e:
            self.view.show_error("Error", f"Failed to load diagram: {e}")
            import traceback
            traceback.print_exc()
    
    def export_diagram_enhanced(self):
        """Export diagram with full database information."""
        file_path = self.view.ask_file_path(save=True)
        if not file_path:
            return
        
        # Ensure .json extension
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        try:
            self._persist_diagram_to_db()
            success = self.json_exporter.export_diagram(
                self.diagram, 
                file_path, 
                self.current_product_id
            )
            
            if success:
                self.view.set_status(f"Exported: {os.path.basename(file_path)}")
            else:
                self.view.show_error("Error", "Failed to export diagram")
                
        except Exception as e:
            self.view.show_error("Error", f"Export failed: {e}")
    
    def import_diagram_enhanced(self):
        """Import diagram from JSON and sync to database."""
        if not self.check_unsaved_changes():
            return
        
        file_path = self.view.ask_file_path(save=False)
        if not file_path:
            return
        
        try:
            diagram = self.json_exporter.import_diagram(file_path, create_in_db=True)
            
            if diagram:
                self.diagram = diagram
                self.command_history.clear()
                
                # Sync to database
                self._persist_diagram_to_db()
                
                # Find and set current product ID
                for shape in self.diagram.shapes:
                    if isinstance(shape, ComponentBox):
                        if shape.properties.get('node_type') == 'Root':
                            self.current_product_id = shape.properties.get('db_id')
                            break
                
                # Update canvas scroll region
                self.view.canvas.update_scroll_region_from_shapes(self.diagram.shapes)
                self._update_view()
                self.view.set_status(f"Imported: {os.path.basename(file_path)}")
            else:
                self.view.show_error("Error", "Failed to import diagram")
                
        except Exception as e:
            self.view.show_error("Error", f"Import failed: {e}")
            import traceback
            traceback.print_exc()
