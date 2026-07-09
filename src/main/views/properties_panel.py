import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any, List

from ..models import Shape, ActionCircle, DiamondStep, ComponentBox
from ..models.database import get_database


class PropertiesPanel(ttk.Frame):
    """
    Dynamic Properties Panel that loads fields from database schema.

    Benefits:
    - Add new column to database = new field appears in UI automatically
    - No code changes needed for new properties
    - Consistent with database schema
    """

    def __init__(self, parent, on_apply_callback: Optional[Callable] = None):
        """Initialize the properties panel and build its widgets."""
        super().__init__(parent, padding=10)
        self.on_apply_callback = on_apply_callback
        self.current_shape: Optional[Shape] = None
        self.db = get_database()

        # Store dynamic field widgets
        self.dynamic_fields: Dict[str, Any] = {}

        self._create_widgets()

    def _create_widgets(self):
        """Create the title, properties frame, apply button and empty label."""
        # Title
        title = ttk.Label(self, text="Properties", font=("Arial", 12, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Dynamic properties frame - will be populated based on shape type
        self.properties_frame = ttk.LabelFrame(self, text="Properties", padding=5)

        # Apply button
        self.apply_button = ttk.Button(self, text="Apply Changes", command=self._on_apply)

        # Empty state label
        self.empty_label = ttk.Label(
            self, text="Select a shape to\nedit its properties", foreground="gray", justify="center"
        )

        self._show_empty_state()

    def _show_empty_state(self):
        """Show empty state when no shape is selected."""
        self.properties_frame.grid_remove()
        self.apply_button.grid_remove()
        self.empty_label.grid(row=5, column=0, columnspan=2, pady=20)

    def _clear_dynamic_fields(self):
        """Clear all dynamic field widgets."""
        for widget in self.properties_frame.winfo_children():
            widget.destroy()
        self.dynamic_fields.clear()

    def _create_field_widget(self, parent, field: Dict[str, Any], row: int, value: Any = "") -> Any:
        """
        Create appropriate widget based on field type from database.

        Args:
            parent: Parent frame
            field: Field info from database schema
            row: Grid row number
            value: Current value to populate

        Returns:
            The created widget
        """
        field_name = field['name']
        field_type = field['type'].upper()
        display_name = field['display_name']
        widget_type = field.get('widget_type', 'default')

        # Label
        ttk.Label(parent, text=f"{display_name}:").grid(row=row, column=0, sticky="w", pady=3)

        # Handle dropdown widget type (from database schema)
        if widget_type == 'dropdown' and field_name == 'color_id':
            # Color dropdown populated from database
            colors = self.db.get_all_colors()
            color_names = [c['name'] for c in colors]
            widget = ttk.Combobox(parent, values=color_names, width=22, state="readonly")
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            # Store color mapping for lookup
            widget.color_map = {c['name']: c['id'] for c in colors}
            widget.color_map_reverse = {c['id']: c['name'] for c in colors}

            # Map color names to hex codes for the UI dropdown
            widget.color_hex_map = {c['name']: c.get('hex_code', '#ffffff') for c in colors}

            # Set current value by color_id
            if value and value in widget.color_map_reverse:
                widget.set(widget.color_map_reverse[value])
            elif colors:
                widget.set("")  # Empty by default
        
        elif widget_type == 'dropdown' and field_name == 'material_id':
            # Material dropdown populated from database
            materials = self.db.get_all_materials()
            material_names = [m['name'] for m in materials]
            widget = ttk.Combobox(parent, values=material_names, width=22, state="readonly")
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            # Store material mapping for lookup
            widget.material_map = {m['name']: m['id'] for m in materials}
            widget.material_map_reverse = {m['id']: m['name'] for m in materials}
            # Set current value by material_id
            if value and value in widget.material_map_reverse:
                widget.set(widget.material_map_reverse[value])
            elif materials:
                widget.set("")  # Empty by default

        elif widget_type == 'dropdown' and field_name == 'tool_id':
            tools = self.db.get_all_tools()
            tool_names = [t['name'] for t in tools]
            widget = ttk.Combobox(parent, values=tool_names, width=22, state="readonly")
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            widget.tool_map = {t['name']: t['id'] for t in tools}
            widget.tool_map_reverse = {t['id']: t['name'] for t in tools}
            if value and value in widget.tool_map_reverse:
                widget.set(widget.tool_map_reverse[value])
            elif tools:
                widget.set("")

        elif field_name == 'node_type':
            # Read-only label for node type
            widget = ttk.Label(parent, text=str(value) if value else "Intermediate", font=("Arial", 9, "italic"))
            widget.grid(row=row, column=1, sticky="ew", pady=3)

        elif field_name == 'image_path':
            # Plain text field for image path entry
            widget = ttk.Entry(parent, width=25)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            widget.insert(0, str(value) if value else "")

        # Create appropriate widget based on type
        elif field_type == 'BOOLEAN':
            # Checkbox for boolean
            var = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(parent, variable=var)
            widget.grid(row=row, column=1, sticky="w", pady=3)
            widget.var = var  # Store reference to variable

        elif field_type == 'TEXT':
            # Multi-line text for TEXT type
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=1, sticky="ew", pady=3)
            widget = tk.Text(frame, height=3, width=20, font=("Arial", 9))
            widget.pack(side="left", fill="both", expand=True)
            scroll = ttk.Scrollbar(frame, command=widget.yview)
            scroll.pack(side="right", fill="y")
            widget.config(yscrollcommand=scroll.set)
            widget.insert("1.0", str(value) if value else "")

        elif 'DECIMAL' in field_type or 'REAL' in field_type:
            # Number entry (but not INT since color_id is INT with dropdown)
            widget = ttk.Entry(parent, width=25)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            widget.insert(0, str(value) if value else "")

        elif field_name == 'weight_unit':
            # Combobox for weight unit
            widget = ttk.Combobox(
                parent,
                values=["g", "kg", "mg", "lb", "oz"],
                width=22
            )
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            widget.set(str(value) if value else "g")

        else:
            # Default: Entry widget
            widget = ttk.Entry(parent, width=25)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            widget.insert(0, str(value) if value else "")

        return widget

    def _get_widget_value(self, widget, field_name: str = None) -> Any:
        """Get value from a widget regardless of type."""
        if isinstance(widget, ttk.Checkbutton):
            return widget.var.get()
        elif isinstance(widget, ttk.Label):
            return widget.cget("text")
        elif isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c")
        elif isinstance(widget, ttk.Combobox):
            value = widget.get()
            # Handle color dropdown - return color_id
            if hasattr(widget, 'color_map') and value in widget.color_map:
                return widget.color_map[value]
            # Handle material dropdown - return material_id
            if hasattr(widget, 'material_map') and value in widget.material_map:
                return widget.material_map[value]
            # Handle tool dropdown - return tool_id
            if hasattr(widget, 'tool_map') and value in widget.tool_map:
                return widget.tool_map[value]
            return value
        elif isinstance(widget, ttk.Entry):
            return widget.get()
        return None

    def _load_component_properties(self, shape: ComponentBox):
        """Load component properties dynamically from database schema."""
        self._clear_dynamic_fields()

        db_id = shape.properties.get("db_id")
        if db_id:
            db_row = self.db.get_component(int(db_id))
            if db_row:
                for key, value in db_row.items():
                    if key in shape.properties:
                        shape.properties[key] = value

        node_type = str(shape.properties.get('node_type', '')).strip().lower()
        if node_type == "root":
            component_kind = "root"
        elif node_type == "leaf":
            component_kind = "leaf"
        else:
            # "composite" and empty both map to intermediate table schema.
            component_kind = "intermediate"

        # Load fields from the correct database component table.
        fields = self.db.get_component_fields(component_kind)

        # Create widgets for each field - directly from shape.properties dict
        # No hardcoded mapping needed!
        for row, field in enumerate(fields):
            field_name = field['name']
            # Get value directly from shape's properties dict
            value = shape.properties.get(field_name, "")
            widget = self._create_field_widget(self.properties_frame, field, row, value)
            self.dynamic_fields[field_name] = widget

        """This code adds a label to display the component type
        (Root, Leaf or Composite) based on the node_type value."""
        
        display_type = {
            "root": "Root Component",
            "leaf": "Leaf Component",
            "intermediate": "Composite Component"
        }[component_kind]

        #creates the first row of the table with the "Component Type" label
        component_type_label = ttk.Label(
            self.properties_frame,
            text="Component Type:"
        )
        component_type_label.grid(row=0, column=0, sticky="w", pady=3)

        #creates the second row of the table with the component type (Root, Leaf or Composite)
        component_type_value = ttk.Label(
            self.properties_frame,
            text=display_type,
            foreground="blue",
            font=("Arial", 9, "bold")
        )
        component_type_value.grid(row=0, column=1, sticky="w", pady=3)

        # Shift existing dynamic property rows down by one so the read-only
        # component type label stays at the top and does not overlap fields.
        for widget in self.properties_frame.winfo_children():
            if widget in (component_type_label, component_type_value):
                continue
            grid_info = widget.grid_info()
            if 'row' in grid_info:
                widget.grid_configure(row=grid_info['row'] + 1)

    def _load_action_properties(self, shape: DiamondStep):
        """Load action properties dynamically from database schema."""
        self._clear_dynamic_fields()

        fields = self.db.get_action_fields()

        shape_values = {
            'name': shape.name,
            'description': shape.description,
            'tool_id': shape.tool_id
        }

        action_db_id = getattr(shape, "db_action_id", None)
        if action_db_id:
            db_row = self.db.get_action(int(action_db_id))
            if db_row:
                shape_values.update(db_row)
                shape.name = db_row.get('name', shape.name)
                shape.description = db_row.get('description', shape.description)
                shape.tool_id = db_row.get('tool_id', shape.tool_id)
                shape.tools = db_row.get('tool_name', shape.tools)
                shape.text = shape.name or shape.text

        for row, field in enumerate(fields):
            field_name = field['name']
            value = shape_values.get(field_name, "")
            widget = self._create_field_widget(self.properties_frame, field, row, value)
            self.dynamic_fields[field_name] = widget

    def _load_step_properties(self, shape: ActionCircle):
        """Load step properties dynamically from database schema."""
        self._clear_dynamic_fields()

        fields = self.db.get_step_fields()

        shape_values = {
            'title': shape.text,
            'description': shape.step_description,
            'image_path': shape.image_path
        }

        step_db_id = getattr(shape, "db_step_id", None)
        if step_db_id:
            db_row = self.db.get_step(int(step_db_id))
            if db_row:
                shape_values.update(db_row)
                shape.step_description = db_row.get('description', shape.step_description)
                shape.text = db_row.get('title', shape.text) or shape.text
                shape.image_path = db_row.get('image_path', shape.image_path)

        row_num = 0

        # Add editable fields
        for field in fields:
            field_name = field['name']
            value = shape_values.get(field_name, "")
            widget = self._create_field_widget(self.properties_frame, field, row_num, value)
            self.dynamic_fields[field_name] = widget
            row_num += 1

    def load_shape(self, shape: Optional[Shape]):
        """Load shape properties into the panel."""
        self.current_shape = shape

        if shape is None:
            self._show_empty_state()
            return

        self.empty_label.grid_remove()

        # Show properties frame
        self.properties_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        self.apply_button.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")

        # Load properties based on shape type
        if isinstance(shape, ComponentBox):
            self.properties_frame.config(text="Component Properties")
            self._load_component_properties(shape)
        elif isinstance(shape, ActionCircle):
            self.properties_frame.config(text="Step Properties")
            self._load_step_properties(shape)
        elif isinstance(shape, DiamondStep):
            self.properties_frame.config(text="Action Properties")
            self._load_action_properties(shape)
        else:
            # Arrow or unknown type - no editable properties, so hide Apply button
            self._clear_dynamic_fields()
            self.properties_frame.config(text="Properties")
            self.apply_button.grid_remove()

    def _on_apply(self):
        """Apply changes to the shape."""
        if self.current_shape is None:
            return

        old_properties = self._get_current_properties()
        self._update_shape_properties()
        new_properties = self._get_current_properties()

        if self.on_apply_callback:
            self.on_apply_callback(self.current_shape, old_properties, new_properties)

    def _get_current_properties(self) -> dict:
        """Get current properties of the shape."""
        if self.current_shape is None:
            return {}

        properties = {"text": self.current_shape.text}

        if isinstance(self.current_shape, ActionCircle):
            properties.update({
                "title": self.current_shape.text,
                "step_description": self.current_shape.step_description,
                "image_path": self.current_shape.image_path
            })
        elif isinstance(self.current_shape, DiamondStep):
            properties.update({
                "action_id": self.current_shape.action_id,
                "name": self.current_shape.name,
                "description": self.current_shape.description,
                "tool_id": self.current_shape.tool_id,
                "tools": self.current_shape.tools
            })
        elif isinstance(self.current_shape, ComponentBox):
            # FULLY DYNAMIC - get all properties from shape's properties dict
            properties.update(self.current_shape.properties)
        return properties

    def _update_shape_properties(self):
        """Update shape properties from widget values."""
        if self.current_shape is None:
            return

        if isinstance(self.current_shape, ComponentBox):
            # We save the original node type before updating 
            original_node_type = self.current_shape.properties.get('node_type')

            for field_name, widget in self.dynamic_fields.items():
                # Avoid processing structural control fields like UI Labels
                if field_name in ['node_type', 'id', 'parent_id']:
                    continue

                value = self._get_widget_value(widget)
                self.current_shape.properties[field_name] = value
                
                # Update the current shape's hex code based on the color selected in the dropdown
                if field_name == 'color_id' and isinstance(widget, ttk.Combobox):
                    color_name = widget.get()
                    if hasattr(widget, 'color_hex_map') and color_name in widget.color_hex_map:
                        self.current_shape.properties['hex_code'] = widget.color_hex_map[color_name]
                    else:
                        self.current_shape.properties['hex_code'] = None

            # We safely restore the real node type in the properties dictionary
            if original_node_type is not None:
                self.current_shape.properties['node_type'] = original_node_type

            # We synchronize the text of the graphical object so that the name never disappears
            if 'name' in self.current_shape.properties and self.current_shape.properties['name']:
                self.current_shape.text = str(self.current_shape.properties['name'])

        elif isinstance(self.current_shape, ActionCircle):
            if 'title' in self.dynamic_fields:
                self.current_shape.text = self._get_widget_value(self.dynamic_fields['title'])
            if 'description' in self.dynamic_fields:
                self.current_shape.step_description = self._get_widget_value(self.dynamic_fields['description'])
            if 'image_path' in self.dynamic_fields:
                self.current_shape.image_path = self._get_widget_value(self.dynamic_fields['image_path'])

        elif isinstance(self.current_shape, DiamondStep):
            if 'name' in self.dynamic_fields:
                self.current_shape.name = self._get_widget_value(self.dynamic_fields['name'])
                self.current_shape.text = self.current_shape.name
            if 'description' in self.dynamic_fields:
                self.current_shape.description = self._get_widget_value(self.dynamic_fields['description'])
            if 'tool_id' in self.dynamic_fields:
                self.current_shape.tool_id = self._get_widget_value(self.dynamic_fields['tool_id'])
                tool_widget = self.dynamic_fields['tool_id']
                if hasattr(tool_widget, 'tool_map_reverse') and self.current_shape.tool_id in tool_widget.tool_map_reverse:
                    self.current_shape.tools = tool_widget.tool_map_reverse[self.current_shape.tool_id]

    def refresh(self):
        """Reload the properties for the current shape to reflect DB changes."""
        self.load_shape(self.current_shape)

    def clear(self):
        """Clear the properties panel."""
        self.load_shape(None)
