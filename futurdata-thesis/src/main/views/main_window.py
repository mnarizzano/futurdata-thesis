import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

from ..utils.feedback import FeedbackType

from .canvas_view import DiagramCanvas
from .properties_panel import PropertiesPanel
from .navigator import Navigator


class MainWindow:
    """
    The main application window for the Disassembly Flow Diagram Builder.

    This class serves as the View orchestrating the layout, menu system, 
    toolbars, interactive canvas, properties panel, status bar, and keyboard 
    shortcuts. It visualizes the program's UI and delegates user interactions 
    to the assigned controller.
    """

    def __init__(self, root: tk.Tk, controller):
        """
        Initializes the main application window and constructs all UI layouts.

        Args:
            root (tk.Tk): The root Tkinter application instance window.
            controller (AppController): The core application controller handling business logic.
        """
        self.root = root
        self.controller = controller
        self.root.title("ARIADNE Disassembly Workflow Builder")
        width = min(1400, int(self.root.winfo_screenwidth() * 0.9))
        height = min(800, int(self.root.winfo_screenheight() * 0.85))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(640, width), min(400, height))

        self._create_menu()
        self._create_toolbar()
        self._create_status_bar()
        self._create_main_area()
        self._bind_shortcuts()
        self.update_ui_state()

    def _create_menu(self):
        """
        Creates and configures the top dropdown menu bar.

        Assembles File, Edit and Help cascades, linking their respective commands
        and structural menu accelerators directly to the app controller.
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.controller.new_diagram)
        file_menu.add_separator()
        file_menu.add_command(label="Load Product...", accelerator="Ctrl+L", command=self.controller.show_product_list)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.controller.save_diagram)
        file_menu.add_separator()
        file_menu.add_command(label="Export Project ZIP...", command=self.controller.export_diagram_enhanced)
        export_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Export Document", menu=export_menu)
        export_menu.add_command(label="PowerPoint (.pptx)...", command=lambda: self.controller.export_document("pptx"))
        export_menu.add_command(label="Word (.docx)...", command=lambda: self.controller.export_document("docx"))
        export_menu.add_command(label="Markdown (.md)...", command=lambda: self.controller.export_document("md"))
        export_menu.add_command(label="Text (.txt)...", command=lambda: self.controller.export_document("txt"))
        export_menu.add_command(label="HTML/Web (.html)...", command=lambda: self.controller.export_document("html"))
        file_menu.add_command(label="Import Project...", command=self.controller.import_diagram_enhanced)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.controller.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.controller.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete", accelerator="Del", command=self.controller.delete_selected)
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.controller.select_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Color...", command=self.controller.show_add_color_dialog)
        edit_menu.add_command(label="Add Material...", command=self.controller.show_add_material_dialog)
        edit_menu.add_command(label="Add Tool...", command=self.controller.show_add_tool_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="Manage Colors...", command=self.controller.show_manage_colors_dialog)
        edit_menu.add_command(label="Manage Materials...", command=self.controller.show_manage_materials_dialog)
        edit_menu.add_command(label="Manage Tools...", command=self.controller.show_manage_tools_dialog)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Canvas", command=self.controller.clear_canvas)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def _create_toolbar(self):
        """
        Creates and positions the top toolbar for quick action access.

        Instantiates primary buttons for rapid diagrams interaction like New,
        Load, Export, Undo, Redo, Delete and Clear operations.
        """
        toolbar = ttk.Frame(self.root, relief="raised", padding=5)
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="New", width=8, command=self.controller.new_diagram).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Load", width=8, command=self.controller.show_product_list).pack(side="left", padx=2)
        ttk.Button(toolbar, text="ZIP Export", width=10, command=self.controller.export_diagram_enhanced).pack(side="left", padx=2)
        ttk.Button(toolbar, text="PPTX Export", width=10, command=self.controller.export_presentation).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

        self.undo_button = ttk.Button(toolbar, text="Undo", width=8, command=self.controller.undo)
        self.undo_button.pack(side="left", padx=2)
        self.redo_button = ttk.Button(toolbar, text="Redo", width=8, command=self.controller.redo)
        self.redo_button.pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

        ttk.Button(toolbar, text="Delete", width=8, command=self.controller.delete_selected).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

        ttk.Button(toolbar, text="Clear", width=8, command=self.controller.clear_canvas).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

        self.snap_btn = tk.Button(
            toolbar,
            text = "Snap to Grid: = ON",
            width = 18,
            font = ("Arial", 9),
            bg = "#e0e0e0",
            relief = tk.SUNKEN,
            command = self.controller.toggle_snap_mode
        )

        self.snap_btn.pack(side="left", padx=2)
        for label, command in (("Zoom +", self.controller.zoom_in), ("Zoom -", self.controller.zoom_out), ("100%", self.controller.reset_zoom)):
            ttk.Button(toolbar, text=label, width=7, command=command).pack(side="left", padx=2)
        controls = list(toolbar.winfo_children())
        for widget in controls:
            widget.pack_forget()
        def wrap_toolbar(event):
            row, column, used = 0, 0, 0
            row_height = max(w.winfo_reqheight() for w in controls) + 4
            for widget in controls:
                width = widget.winfo_reqwidth() + 4
                if used and used + width > event.width - 10:
                    row, column, used = row + 1, 0, 0
                widget.place(x=used + 2, y=row * row_height + 2)
                column += 1
                used += width
            toolbar.configure(height=(row + 1) * row_height + 10)
        toolbar.bind("<Configure>", wrap_toolbar)


    def _create_main_area(self):
        """
        Builds the central three-pane layout of the application workspace.

        Assembles the Left Shape Palette for inserting nodes, the Center interactive
        scrolling DiagramCanvas and the Right dynamic PropertiesPanel layout.
        """
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side="top", fill="both", expand=True)

        self.paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)
        sidebar = ttk.Frame(self.paned_window, width=150)
        sidebar.pack_propagate(False)
        self.sidebar_tabs = ttk.Notebook(sidebar)
        self.sidebar_tabs.pack(fill="both", expand=True)
        palette_frame = ttk.Frame(self.sidebar_tabs, padding=6)
        self.sidebar_tabs.add(palette_frame, text="Shapes")
        self.navigator = Navigator(self.sidebar_tabs, self.controller.navigate_to_shape)
        self.sidebar_tabs.add(self.navigator, text="Navigator")
        self.paned_window.add(sidebar, weight=0)

        ttk.Label(palette_frame, text="Click to add:").pack(anchor="w", pady=(0, 10))
        ttk.Button(palette_frame, text="▭ Root Component", command=lambda: self.controller.add_shape("component_root")).pack(fill="x", pady=2)
        ttk.Button(palette_frame, text="▭ Leaf Component", command=lambda: self.controller.add_shape("component_leaf")).pack(fill="x", pady=2)
        ttk.Button(palette_frame, text="▭ Composite Comp.", command=lambda: self.controller.add_shape("component_composite")).pack(fill="x", pady=2)
        ttk.Button(palette_frame, text="○ Step", command=lambda: self.controller.add_shape("action")).pack(fill="x", pady=2)
        ttk.Button(palette_frame, text="◇ Action", command=lambda: self.controller.add_shape("diamond")).pack(fill="x", pady=2)
        ttk.Button(palette_frame, text="→ Arrow", command=lambda: self.controller.add_shape("arrow")).pack(fill="x", pady=2)

        canvas_frame = ttk.Frame(self.paned_window, width=200)

        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=lambda *args: self.canvas_view_scroll_x if hasattr(self, 'canvas_view_scroll_x') else None)
        h_scroll.pack(side="bottom", fill="x")

        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")

        self.canvas = DiagramCanvas(canvas_frame, bg="white", width=200, height=200)
        self.canvas.color_resolver = self.controller.catalog.get_color
        self.canvas.pack(side="left", fill="both", expand=True)

        v_scroll.config(command=self.canvas.yview)
        h_scroll.config(command=self.canvas.xview)
        self.canvas.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.paned_window.add(canvas_frame, weight=4)

        self.properties_panel = PropertiesPanel(
            self.paned_window,
            on_apply_callback=self.controller.apply_properties,
            on_add_catalog=self.controller.show_add_catalog_dialog,
            data_provider=self.controller.catalog,
        )

        self.paned_window.add(self.properties_panel, weight=0)

    def _create_status_bar(self):
        """
        Creates the bottom status bar window attachment.

        Establishes labels to provide system status logs on the bottom-left
        and active shape metrics counters on the bottom-right.
        """
        self.status_bar = ttk.Frame(self.root, relief="sunken")
        self.status_bar.pack(side="bottom", fill="x")
        self.status_icon = ttk.Label(self.status_bar, padding=(5, 2))
        self.status_icon.pack(side="left")
        self.shape_count_label = ttk.Label(self.status_bar, text="Shapes: 0", padding=(5, 2))
        self.shape_count_label.pack(side="right")
        self.status_label = ttk.Label(self.status_bar, text="Ready", padding=(0, 2), anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.set_status("Ready")

    def _bind_shortcuts(self):
        """
        Binds global and widget-specific event configurations and hotkeys.

        Handles key triggers (Ctrl+S, Ctrl+Z, etc.), map navigation hotkeys, zoom
        and ensures interception protocols for OS close event requests.
        """
        self.root.bind('<Control-n>', lambda e: self.controller.new_diagram())
        self.root.bind('<Control-l>', lambda e: self.controller.show_product_list())
        self.root.bind('<Control-o>', lambda e: self.controller.open_diagram())
        self.root.bind('<Control-s>', lambda e: self.controller.save_diagram())
        self.root.bind('<Control-Shift-S>', lambda e: self.controller.save_diagram_as())
        self.root.bind('<Control-z>', lambda e: self.controller.undo())
        self.root.bind('<Control-y>', lambda e: self.controller.redo())
        self.root.bind('<Delete>', lambda e: self.controller.delete_selected())
        self.root.bind('<Control-plus>', lambda e: self.controller.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.controller.zoom_out())
        self.root.bind('<Control-0>', lambda e: self.controller.reset_zoom())
        self.root.bind('<Escape>', lambda e: self.controller.on_escape(e))
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        # Bind Ctrl+A only to canvas (not globally) so text widgets can handle it
        self.canvas.bind('<Control-a>', lambda e: self.controller.select_all())
        
        # Explicitly bind Ctrl+A for Entry and Text widgets to select all text
        # Bind for both tk.Entry and ttk.Entry (class names: Entry and TEntry)
        self.root.bind_class("Entry", "<Control-a>", self._select_all_text)
        self.root.bind_class("TEntry", "<Control-a>", self._select_all_text)
        self.root.bind_class("Text", "<Control-a>", self._select_all_text)
        
        # Also bind for Combobox entry field
        self.root.bind_class("TCombobox", "<Control-a>", self._select_all_text)

        # Clear any default selection when widgets receive focus.
        self.root.bind_class("Entry", "<FocusIn>", self._clear_default_selection, add="+")
        self.root.bind_class("TEntry", "<FocusIn>", self._clear_default_selection, add="+")
        self.root.bind_class("Text", "<FocusIn>", self._clear_default_selection, add="+")
        self.root.bind_class("TCombobox", "<FocusIn>", self._clear_default_selection, add="+")
    
    def _select_all_text(self, event):
        """
        Event handler that intercepts Ctrl+A inside input fields to select text.

        Prevents triggering the global diagram 'Select All' function when the user 
        is actively editing a text-based properties widget.

        Args:
            event: The Tkinter keyboard event context.

        Returns:
            str: "break" string sequence to stop event propagation in Tkinter.
        """
        widget = event.widget
        try:
            if isinstance(widget, tk.Text):
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "end-1c")
                return "break"
            elif isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
                return "break"
        except tk.TclError:
            pass

    def _clear_default_selection(self, event):
        """Remove any preselected text so focus doesn't keep blue highlighting."""
        widget = event.widget
        try:
            if isinstance(widget, tk.Text):
                widget.tag_remove("sel", "1.0", "end")
            elif isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
                widget.selection_clear()
        except tk.TclError:
            pass

    def update_ui_state(self):
        """
        Refreshes dynamic interface states based on current application history.

        Evaluates the undo/redo stack accessibility metrics to enable or disable
        their buttons contextually and updates total layout elements counters.
        """
        can_undo = self.controller.can_undo()
        can_redo = self.controller.can_redo()
        self.undo_button.config(state="normal" if can_undo else "disabled")
        self.redo_button.config(state="normal" if can_redo else "disabled")
        shape_count = len(self.controller.diagram.shapes)
        self.shape_count_label.config(text=f"Shapes: {shape_count}")

    def set_status(self, message: str, feedback_type=FeedbackType.INFO):
        """Set the complete visual state for each message, independent of prior feedback."""
        feedback_type = FeedbackType(feedback_type)
        colors = {
            FeedbackType.SUCCESS: ("#176534", "✓"),
            FeedbackType.ERROR: ("red", "✕"),
            FeedbackType.INFO: ("black", ""),
            FeedbackType.WARNING: ("#855600", "!"),
        }
        foreground, icon = colors[feedback_type]
        self.status_label.configure(text=message, foreground=foreground)
        self.status_icon.configure(text=icon, foreground=foreground)

    def update_properties_panel(self, shape=None):
        """
        Loads a designated shape model context into the properties panel.

        Args:
            shape (Shape, optional): The target shape schema to load. Defaults to None.
        """
        self.properties_panel.load_shape(shape)

    def refresh_properties_panel(self):
        """
        Triggers a state refresh sequence on the properties panel.

        Forces synchronization updates on custom form values following a JSON repository 
        transaction or manual properties injection.
        """
        self.properties_panel.refresh()
        # Existing controller callbacks also update any open catalog dialogs.
        def refresh_dialogs(parent):
            for child in parent.winfo_children():
                if isinstance(child, tk.Toplevel):
                    refresh = getattr(child, 'refresh_catalogs', None)
                    if refresh is not None:
                        refresh()
                    refresh_dialogs(child)
        refresh_dialogs(self.root)

    def show_about(self):
        """
        Displays an informational standard popup dialog crediting the application.
        """
        messagebox.showinfo(
            "About",
            "ARIADNE Disassembly Workflow Builder\n\n"
            "Version 1.0\n\n"
            "A visual tool for creating disassembly workflows\n"
            "for product documentation and analysis.\n\n"
            "Created as part of a thesis project."
        )

    def on_exit(self):
        """
        Intercepts closure attempts to evaluate outstanding file operations.

        Ensures that unsaved layout data is checked before letting the user 
        terminate the execution loop runtime.
        """
        if self.controller.check_unsaved_changes():
            self.root.quit()

    def ask_save_changes(self) -> Optional[str]:
        """
        Prompts a confirmation warning asking whether unsaved data should be backed up.

        Returns:
            Optional[str]: 'save' to confirm, 'discard' to ignore or 'cancel' to halt termination.
        """
        result = messagebox.askyesnocancel("Unsaved Changes", "You have unsaved changes. Do you want to save them?", parent=self.root)
        if result is True:
            return 'save'
        elif result is False:
            return 'discard'
        else:
            return 'cancel'

    def ask_file_path(self, save=True, file_types=None) -> Optional[str]:
        """
        Launches operational system prompt widgets for managing storage IO paths.

        Args:
            save (bool): True to deploy a save dialog box. False to launch an open file box.
            file_types (list, optional): Filter tuples defining valid extensions. Defaults to JSON.

        Returns:
            Optional[str]: Selected absolute string target file path, or None if cancelled.
        """
        if file_types is None:
            file_types = [("JSON files", "*.json"), ("All files", "*.*")]
        if save:
            default_ext = ".zip" if any("*.zip" in pattern for _, pattern in file_types) else ".json"
            return filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=file_types)
        return filedialog.askopenfilename(filetypes=file_types)

    def show_error(self, title: str, message: str):
        """
        Deploys a standardized modal dialog presenting an error report.

        Args:
            title (str): The header string context title of the popup window.
            message (str): Explicit error summary log description.
        """
        self.set_status(f"Error [{title}]: {message}", FeedbackType.ERROR)

    def show_info(self, title: str, message: str):
        """
        Deploys a standardized modal dialog presenting informative notification summaries.

        Args:
            title (str): The header string context title of the popup window.
            message (str): Core notice text description details.
        """
        self.set_status(f"Info: {message}", FeedbackType.INFO)
    
    def update_snap_button(self, snap_enabled: bool):
        if snap_enabled:
            self.snap_btn.config(text="Snap to Grid: ON", relief=tk.SUNKEN, bg="#e0e0e0")
        else:
            self.snap_btn.config(text="Snap to Grid: OFF", relief=tk.RAISED, bg="#f0f0f0")

    def show_shape_context_menu(self, event, edit, duplicate, delete):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Edit Properties", command=edit)
        menu.add_separator()
        menu.add_command(label="Duplicate", command=duplicate)
        menu.add_command(label="Delete", command=delete)
        menu.post(event.x_root, event.y_root)

    def ask_confirmation(self, title, message):
        return messagebox.askyesno(title, message, parent=self.root)

    def show_workflow_error(self, title, message):
        messagebox.showerror(title, message, parent=self.root)

    def show_catalog_dialog(self, kind, controller, manage=False):
        if manage:
            from .manage_colors_dialog import ManageColorsDialog
            from .manage_materials_dialog import ManageMaterialsDialog
            from .manage_tools_dialog import ManageToolsDialog
            dialogs = {'color': ManageColorsDialog, 'material': ManageMaterialsDialog,
                       'tool': ManageToolsDialog}
            dialogs[kind](self.root, controller)
            return None
        from .add_color_dialog import AddColorDialog
        from .add_material_dialog import AddMaterialDialog
        from .add_tool_dialog import AddToolDialog
        dialogs = {'color': AddColorDialog, 'material': AddMaterialDialog, 'tool': AddToolDialog}
        return dialogs[kind](self.root, controller).result

    def show_product_list(self, controller, on_load):
        from .product_list_dialog import ProductListDialog
        ProductListDialog(self.root, controller, on_load)
