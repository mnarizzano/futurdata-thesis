import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any

from .selector_wheel import create_combobox

from ..models import Shape, ActionCircle, DiamondStep, ComponentBox


class PropertiesPanel(ttk.Frame):
    """
    Properties editor using controller-provided schemas and catalogs.

    Benefits:
    - Add new column to JSON repository = new field appears in UI automatically
    - No code changes needed for new properties
    - Consistent with JSON schema
    """

    def __init__(self, parent, on_apply_callback: Optional[Callable] = None, data_provider=None, on_add_catalog=None):
        """Initialize the properties panel and build its widgets."""
        super().__init__(parent, padding=10)
        self.on_apply_callback = on_apply_callback
        self.on_add_catalog = on_add_catalog
        self.current_shape: Optional[Shape] = None
        if data_provider is None:
            raise ValueError("PropertiesPanel requires a controller data_provider")
        self.data_provider = data_provider

        # Store dynamic field widgets
        self.dynamic_fields: Dict[str, Any] = {}
        
        # Image preview
        self.current_image = None
        self.current_photo = None

        self._create_widgets()

    def _create_widgets(self):
        """Create the title, properties frame, apply button and empty label."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.viewport = tk.Canvas(self, width=300, height=200, highlightthickness=0)
        self.viewport.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.viewport.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.viewport.configure(yscrollcommand=scrollbar.set)
        self.content = ttk.Frame(self.viewport)
        self.content.columnconfigure(0, weight=1)
        self.content_window = self.viewport.create_window(0, 0, window=self.content, anchor="nw")
        self.viewport.bind("<Configure>", lambda e: self.viewport.itemconfigure(self.content_window, width=e.width))
        self.content.bind("<Configure>", lambda e: self.viewport.configure(scrollregion=self.viewport.bbox("all")))

        # Title
        title = ttk.Label(self.content, text="Properties", font=("Arial", 12, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Dynamic properties frame - will be populated based on shape type
        self.properties_frame = ttk.LabelFrame(self.content, text="Properties", padding=5)

        self.properties_frame.columnconfigure(1, weight=1)

        # Apply button
        self.apply_button = ttk.Button(self.content, text="Apply Changes", command=self._on_apply)
        
        # Image preview frame (below apply button)
        self.image_preview_frame = ttk.LabelFrame(self.content, text="Image Preview", padding=5)
        self.image_label = ttk.Label(self.image_preview_frame, text="No image", foreground="gray")
        self.image_label.pack(pady=5)

        # Empty state label
        self.empty_label = ttk.Label(
            self.content, text="Select a shape to\nedit its properties", foreground="gray", justify="center"
        )

        self._show_empty_state()

    def _create_combobox(self, parent, **options):
        return create_combobox(parent, **options)

    def _show_empty_state(self):
        """Show empty state when no shape is selected."""
        self.properties_frame.grid_remove()
        self.apply_button.grid_remove()
        self.image_preview_frame.grid_remove()
        self.empty_label.grid(row=5, column=0, columnspan=2, pady=20)

    def _clear_dynamic_fields(self):
        """Clear all dynamic field widgets."""
        for widget in self.properties_frame.winfo_children():
            widget.destroy()
        self.dynamic_fields.clear()

    def _create_field_widget(self, parent, field: Dict[str, Any], row: int, value: Any = "") -> Any:
        """
        Create appropriate widget based on field type from JSON repository.

        Args:
            parent: Parent frame
            field: Field info from JSON schema
            row: Grid row number
            value: Current value to populate

        Returns:
            The created widget
        """
        field_name = field['name']
        field_type = field['type'].upper()
        display_name = field['display_name']
        widget_type = field.get('widget_type', 'default')

        # Label (customize for special fields)
        if field_name == 'tool_id':
            label_text = "Tool:"
        elif field_name == 'image_path':
            label_text = "Image:"
        elif field_name == 'material_id':
            label_text = "Material:"
        else:
            label_text = f"{display_name}:"
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=3)

        # Handle dropdown widget type (from JSON schema)
        if widget_type == 'dropdown' and field_name == 'color_id':
            widget = self._create_combobox(parent, width=22, state="readonly")
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self._refresh_catalog_choices(widget, 'color', value)

        elif widget_type == 'dropdown' and field_name == 'material_id':
            # Material -> Sub Category -> Type selector. The selected type resolves to material_id.
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=1, sticky="ew", pady=3)
            frame.columnconfigure(0, weight=1)

            widget = self._create_combobox(frame, values=[], width=22, state="readonly")
            ttk.Label(frame, text="Category:").grid(row=0, column=0, sticky="w", padx=(0, 6))
            widget.grid(row=1, column=0, sticky="ew")
            widget.material_selector = True

            widget.category_var = tk.StringVar()
            widget.subcategory_var = tk.StringVar()
            widget.type_var = tk.StringVar()
            widget.configure(textvariable=widget.category_var)

            widget.subcategory_frame = ttk.Frame(frame)
            widget.subcategory_frame.grid(row=2, column=0, sticky="ew", pady=(4, 0))
            widget.subcategory_frame.columnconfigure(0, weight=1)
            ttk.Label(widget.subcategory_frame, text="Sub-Category:").grid(row=0, column=0, sticky="w", padx=(0, 6))
            widget.subcategory_combo = self._create_combobox(
                widget.subcategory_frame,
                textvariable=widget.subcategory_var,
                state="readonly",
                width=22,
            )
            widget.subcategory_combo.grid(row=1, column=0, sticky="ew")

            widget.type_frame = ttk.Frame(frame)
            widget.type_frame.grid(row=3, column=0, sticky="ew", pady=(4, 0))
            widget.type_frame.columnconfigure(0, weight=1)
            ttk.Label(widget.type_frame, text="Type:").grid(row=0, column=0, sticky="w", padx=(0, 6))
            widget.type_combo = self._create_combobox(
                widget.type_frame,
                textvariable=widget.type_var,
                state="readonly",
                width=22,
            )
            widget.type_combo.grid(row=1, column=0, sticky="ew")

            widget.bind("<<ComboboxSelected>>", lambda e, w=widget: self._on_material_category_changed(w))
            widget.subcategory_combo.bind("<<ComboboxSelected>>", lambda e, w=widget: self._on_material_subcategory_changed(w))

            widget.type_combo.bind("<<ComboboxSelected>>", lambda e, w=widget: self._clear_saved_material(w))
            self._refresh_saved_materials(widget)
            self._setup_material_hierarchy_widget(widget)

            if value and int(value) in widget.material_data:
                self._load_material_hierarchy_from_material(widget, int(value))

        elif field_name == 'tool_id':
            widget = self._create_combobox(parent, width=22, state="readonly")
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self._refresh_catalog_choices(widget, 'tool', value)

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
            widget = self._create_combobox(
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

        if field_name in ('color_id', 'material_id', 'tool_id') and self.on_add_catalog:
            self._install_catalog_action(widget, field_name[:-3])
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
            # Handle category/subcategory/type material selector.
            if hasattr(widget, 'material_selector'):
                return self._get_selected_material_id(widget)
            # Handle color dropdown - return color_id
            if hasattr(widget, 'color_map'):
                return widget.color_map.get(value)
            # Handle tool dropdown - return tool_id
            if hasattr(widget, 'tool_map'):
                return widget.tool_map.get(value, value or None)
            return value
        elif isinstance(widget, ttk.Entry):
            return widget.get()
        return None

    def _catalog_choices(self, widget, values):
        values = list(values)
        if self.on_add_catalog:
            label = 'Add new...'
            while label in values:
                label += ' (+)'
            widget.add_new_label = label
            values.append(label)
        return values

    def _install_catalog_action(self, widget, kind):
        variable = getattr(widget, 'category_var', None)
        if variable is None:
            variable = tk.StringVar(value=widget.get())
            widget.configure(textvariable=variable)
        widget.catalog_variable = variable
        widget.catalog_previous = variable.get()

        def remember(*args):
            value = variable.get()
            if value != widget.add_new_label:
                widget.catalog_previous = value

        variable.trace_add('write', remember)
        widget.bind('<<ComboboxSelected>>',
                    lambda event: self._on_catalog_selection(widget, kind))

    def _on_catalog_selection(self, widget, kind):
        if widget.get() != widget.add_new_label:
            if kind == 'material':
                self._on_material_category_changed(widget)
            return
        # Restore the selection before opening the modal dialog. Its save path
        # refreshes all catalogs, and Cancel must leave the draft intact.
        widget.set(widget.catalog_previous)
        selected = self.on_add_catalog(kind)
        if not widget.winfo_exists():
            return
        self.refresh()
        if selected is not None:
            if kind == 'material':
                self._load_material_hierarchy_from_material(widget, selected)
            else:
                self._refresh_catalog_choices(widget, kind, selected)

    def _refresh_catalog_choices(self, widget, kind, selected=None):
        """Read current catalog rows while preserving a selection by its stable ID."""
        old_names = getattr(widget, f'{kind}_map', {})
        if selected is None:
            selected = old_names.get(widget.get(), widget.get())
        rows = getattr(self.data_provider, f'get_all_{kind}s')()
        names = {row['name']: row['id'] for row in rows}
        reverse = {row['id']: row['name'] for row in rows}
        setattr(widget, f'{kind}_map', names)
        setattr(widget, f'{kind}_map_reverse', reverse)
        if kind == 'color':
            widget.color_hex_map = {row['name']: row.get('hex_code', '#ffffff') for row in rows}
        widget['values'] = self._catalog_choices(widget, list(names))
        label = reverse.get(selected, selected if selected in names else '')
        # Preserve legacy tool text for display until the user selects a catalog item.
        if kind == 'tool' and selected and not label and isinstance(selected, str):
            label = selected
        widget.set(label)

    def _refresh_saved_materials(self, widget):
        rows = self.data_provider.get_all_materials()
        widget.material_rows = rows
        widget.material_data = {row['id']: row for row in rows}
        counts = {}
        for row in rows:
            counts[row['name']] = counts.get(row['name'], 0) + 1
        widget.material_map = {
            (row['name'] if counts[row['name']] == 1 else f"{row['name']} (#{row['id']})"): row['id']
            for row in rows
        }

    def _clear_saved_material(self, widget):
        widget.selected_material_id = None
        category_id = widget.category_map.get(widget.category_var.get())
        widget.category_var.set(widget.category_map_reverse.get(category_id, ''))

    def _on_saved_material_changed(self, widget):
        material_id = widget.material_map.get(widget.get())
        if material_id is not None:
            self._load_material_hierarchy_from_material(widget, material_id)
        else:
            self._setup_material_hierarchy_widget(widget)
            widget.category_var.set('')
            widget.subcategory_var.set('')
            widget.type_var.set('')

    def _setup_material_hierarchy_widget(self, widget):
        """Configure category/subcategory/type controls for component material selection."""
        widget.selected_material_id = None
        categories = self.data_provider.get_all_material_categories()
        widget.category_map = {c["name"]: c["id"] for c in categories}
        widget.category_map_reverse = {c["id"]: c["name"] for c in categories}
        # Keep the original hierarchy and expose named materials in the same selector.
        for label, material_id in widget.material_map.items():
            material = widget.material_data[material_id]
            if label not in widget.category_map:
                widget.category_map[label] = material.get("category_id")
        widget["values"] = self._catalog_choices(widget, list(dict.fromkeys(
            [c["name"] for c in categories] + list(widget.material_map))))
        widget.subcategory_map = {}
        widget.subcategory_map_reverse = {}
        widget.type_map = {}
        widget.type_map_reverse = {}
        widget.subcategory_frame.grid_remove()
        widget.type_frame.grid_remove()

    def _load_material_hierarchy_from_material(self, widget, material_id: int):
        """Load hierarchy controls from a selected material row."""
        material = widget.material_data.get(material_id)
        if not material:
            self._setup_material_hierarchy_widget(widget)
            return

        widget.selected_material_id = material_id
        category_name = material.get("category_name") or (material.get("name") if material.get("name") in widget.category_map else "")
        label = next((name for name, key in widget.material_map.items() if key == material_id), category_name)
        widget.category_var.set(label)
        self._refresh_material_subcategories(widget, material.get("subcategory_id"))
        self._refresh_material_types(widget, material.get("type_id"))

    def _refresh_material_subcategories(self, widget, select_id=None):
        """Refresh subcategory options for the selected category."""
        category_id = widget.category_map.get(widget.category_var.get())
        subcategories = self.data_provider.get_subcategories_by_category(category_id) if category_id else []
        widget.subcategory_map = {s["name"]: s["id"] for s in subcategories}
        widget.subcategory_map_reverse = {s["id"]: s["name"] for s in subcategories}

        if subcategories:
            widget.subcategory_frame.grid()
            widget.subcategory_combo["values"] = [s["name"] for s in subcategories]
            if select_id and select_id in widget.subcategory_map_reverse:
                widget.subcategory_var.set(widget.subcategory_map_reverse[select_id])
            else:
                widget.subcategory_var.set("")
        else:
            widget.subcategory_var.set("")
            widget.subcategory_frame.grid_remove()

    def _refresh_material_types(self, widget, select_id=None):
        """Refresh type options based on selected category/subcategory."""
        category_id = widget.category_map.get(widget.category_var.get())
        subcategory_id = widget.subcategory_map.get(widget.subcategory_var.get()) if widget.subcategory_var.get() else None

        types = []
        if category_id:
            types = self.data_provider.get_types_by_category(category_id, subcategory_id)
            if not types and subcategory_id is None:
                types = self.data_provider.get_types_by_category(category_id, None)

        widget.type_map = {t["name"]: t["id"] for t in types}
        widget.type_map_reverse = {t["id"]: t["name"] for t in types}

        if types:
            widget.type_frame.grid()
            widget.type_combo["values"] = [t["name"] for t in types]
            if select_id and select_id in widget.type_map_reverse:
                widget.type_var.set(widget.type_map_reverse[select_id])
            else:
                widget.type_var.set("")
        else:
            widget.type_var.set("")
            widget.type_frame.grid_remove()

    def _on_material_category_changed(self, widget):
        """Select a named material or refresh the original category hierarchy."""
        material_id = widget.material_map.get(widget.get())
        if material_id is not None:
            self._load_material_hierarchy_from_material(widget, material_id)
            return
        self._clear_saved_material(widget)
        self._refresh_material_subcategories(widget)
        self._refresh_material_types(widget)

    def _on_material_subcategory_changed(self, widget):
        """When subcategory changes, refresh type field."""
        self._clear_saved_material(widget)
        self._refresh_material_types(widget)

    def _get_selected_material_id(self, widget):
        """Resolve selected category/subcategory/type back to a material row."""
        category_id = widget.category_map.get(widget.category_var.get())
        subcategory_id = widget.subcategory_map.get(widget.subcategory_var.get()) if widget.subcategory_var.get() else None
        type_id = widget.type_map.get(widget.type_var.get()) if widget.type_var.get() else None

        selected_id = getattr(widget, "selected_material_id", None)
        selected = widget.material_data.get(selected_id) if selected_id else None
        if selected:
            selected_category = selected.get("category_id") or widget.category_map.get(selected.get("name"))
            if (selected_category, selected.get("subcategory_id"), selected.get("type_id")) == (category_id, subcategory_id, type_id):
                return selected_id
        if not category_id:
            return selected_id

        return self.data_provider.resolve_material_selection(category_id, subcategory_id, type_id)

    def _load_component_properties(self, shape: ComponentBox):
        """Load component properties dynamically from JSON schema."""
        self._clear_dynamic_fields()

        node_type = str(shape.properties.get('node_type', '')).strip().lower()
        if node_type == "root":
            component_kind = "root"
        elif node_type == "leaf":
            component_kind = "leaf"
        else:
            # "composite" and empty both map to intermediate table schema.
            component_kind = "intermediate"

        # Load fields from the correct JSON repository component table.
        fields = self.data_provider.get_component_fields(component_kind)
        fields_by_name = {field['name']: field for field in fields}
        show_material_field = node_type == "leaf"
        show_color_field = node_type == "leaf"
        ordered_fields = [
            field for field in fields
            if field['name'] not in {'material_id', 'color_id'}
        ]
        insert_at = next(
            (idx for idx, field in enumerate(ordered_fields) if field['name'] == 'weight'),
            len(ordered_fields),
        )
        hierarchy_fields = [
            fields_by_name[name]
            for name in ('material_id', 'color_id')
            if (name == 'material_id' and show_material_field)
            or (name == 'color_id' and show_color_field)
            if name in fields_by_name
        ]
        fields = ordered_fields[:insert_at] + hierarchy_fields + ordered_fields[insert_at:]

        # Create widgets for each field - directly from shape.properties dict
        # No hardcoded mapping needed!
        for row, field in enumerate(fields):
            field_name = field['name']
            # Get value directly from shape's properties dict
            value = shape.properties.get(field_name, "")
            widget = self._create_field_widget(self.properties_frame, field, row, value)
            self.dynamic_fields[field_name] = widget

    def _load_action_properties(self, shape: DiamondStep):
        """Load action properties dynamically from JSON schema."""
        self._clear_dynamic_fields()

        fields = self.data_provider.get_action_fields()

        shape_values = {
            'name': shape.name,
            'description': shape.description,
            'tool_id': shape.tool_id,
            'image_path': shape.image_path
        }

        shape_values['tool_id'] = shape.tool_id or shape.tools or ""

        for row, field in enumerate(fields):
            field_name = field['name']
            value = shape_values.get(field_name, "")
            widget = self._create_field_widget(self.properties_frame, field, row, value)
            self.dynamic_fields[field_name] = widget

    def _load_step_properties(self, shape: ActionCircle):
        """Load step properties dynamically from JSON schema."""
        self._clear_dynamic_fields()

        fields = self.data_provider.get_step_fields()

        shape_values = {
            'title': shape.text,
            'description': shape.step_description,
            'image_path': shape.image_path
        }

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

        if not isinstance(shape, (ComponentBox, ActionCircle, DiamondStep)):
            self._clear_dynamic_fields()
            self.empty_label.configure(text=("Select a shape to\nedit its properties" if shape is None
                                             else "No editable properties for this connection."))
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
        
        # Update image preview if image path exists
        image_path = self._get_image_path_from_shape()
        if image_path:
            self._update_image_preview(image_path)
        else:
            self.image_preview_frame.grid_remove()

    def _on_apply(self):
        """Apply changes to the shape."""
        if self.current_shape is None:
            return

        old_properties = self._get_current_properties()
        new_properties = self._collect_proposed_properties()

        if self.on_apply_callback:
            self.on_apply_callback(self.current_shape, old_properties, new_properties)

    def _get_current_properties(self) -> dict:
        """Get current properties of the shape."""
        if self.current_shape is None:
            return {}

        properties = {"text": self.current_shape.text}

        if isinstance(self.current_shape, ActionCircle):
            properties.update({
                "step_description": self.current_shape.step_description,
                "image_path": self.current_shape.image_path
            })
        elif isinstance(self.current_shape, DiamondStep):
            properties.update({
                "action_id": self.current_shape.action_id,
                "name": self.current_shape.name,
                "description": self.current_shape.description,
                "tool_id": self.current_shape.tool_id,
                "tools": self.current_shape.tools,
                "image_path": self.current_shape.image_path
            })
        elif isinstance(self.current_shape, ComponentBox):
            # FULLY DYNAMIC - get all properties from shape's properties dict
            properties.update(self.current_shape.properties)
        return properties

    def _collect_proposed_properties(self):
        """Read form input without changing the active shape."""
        proposed = {}
        shape = self.current_shape
        for field, widget in self.dynamic_fields.items():
            if field in ('node_type', 'id', 'parent_id'):
                continue
            value = self._get_widget_value(widget)
            if isinstance(shape, ComponentBox):
                proposed[field] = value
                if field == 'color_id':
                    proposed['hex_code'] = getattr(widget, 'color_hex_map', {}).get(widget.get())
            elif isinstance(shape, ActionCircle):
                proposed[{'title': 'text', 'description': 'step_description'}.get(field, field)] = value
            elif isinstance(shape, DiamondStep):
                proposed[field] = value
                if field == 'tool_id':
                    proposed['tools'] = widget.get()
                    proposed['tool_id'] = next(
                        (key for key, label in getattr(widget, 'tool_map_reverse', {}).items()
                         if label == widget.get()), None)
        if isinstance(shape, ComponentBox) and 'name' in self.dynamic_fields and proposed.get('name'):
            proposed['text'] = str(proposed['name'])
        elif isinstance(shape, DiamondStep) and 'name' in self.dynamic_fields:
            proposed['text'] = proposed['name']
        return proposed

    def _update_image_preview(self, image_path: str):
        """Update the image preview with the given path."""
        if not image_path:
            self.image_label.config(image="", text="No image", foreground="gray")
            self.current_photo = None
            self.image_preview_frame.grid_remove()
            return
        
        try:
            from PIL import Image, ImageTk
            from ..utils.image_handler import get_image_handler
            
            # Get full path
            handler = get_image_handler()
            full_path = handler.get_full_path(image_path)
            
            # Check if file exists
            if not handler.image_exists(image_path):
                self.image_label.config(image="", text="Image not found", foreground="red")
                self.current_photo = None
                self.image_preview_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)
                return
            
            # Load and resize image
            image = Image.open(full_path)
            
            # Resize to fit in preview (max 200x200)
            max_size = (200, 200)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_photo = ImageTk.PhotoImage(image)
            
            # Update label
            self.image_label.config(image=self.current_photo, text="", foreground="black")
            
            # Show preview frame
            self.image_preview_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)
            
        except ImportError:
            # PIL not installed
            self.image_label.config(image="", text="PIL/Pillow not installed", foreground="orange")
            self.current_photo = None
            self.image_preview_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)
        except Exception as e:
            # Error loading image
            self.image_label.config(image="", text=f"Error: {str(e)[:30]}", foreground="red")
            self.current_photo = None
            self.image_preview_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)

    def _get_image_path_from_shape(self) -> str:
        """Get image path from current shape."""
        if not self.current_shape:
            return ""
        
        if isinstance(self.current_shape, ComponentBox):
            return self.current_shape.properties.get('image_path', '')
        elif isinstance(self.current_shape, ActionCircle):
            return self.current_shape.image_path or ''
        elif isinstance(self.current_shape, DiamondStep):
            return self.current_shape.image_path or ''
        
        return ""

    def refresh(self):
        """Refresh catalog options in place without losing unapplied form edits."""
        for field, widget in self.dynamic_fields.items():
            if field in ('color_id', 'tool_id'):
                self._refresh_catalog_choices(widget, field[:-3])
            elif field == 'material_id':
                selected = widget.selected_material_id
                category = widget.category_map.get(widget.category_var.get())
                subcategory = widget.subcategory_map.get(widget.subcategory_var.get())
                material_type = widget.type_map.get(widget.type_var.get())
                self._refresh_saved_materials(widget)
                self._setup_material_hierarchy_widget(widget)
                if selected in widget.material_data:
                    self._load_material_hierarchy_from_material(widget, selected)
                else:
                    widget.category_var.set(widget.category_map_reverse.get(category, ''))
                    self._refresh_material_subcategories(widget, subcategory)
                    self._refresh_material_types(widget, material_type)

    def clear(self):
        """Clear the properties panel."""
        self.load_shape(None)
