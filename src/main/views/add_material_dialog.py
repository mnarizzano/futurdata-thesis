import tkinter as tk
from tkinter import ttk

class AddMaterialDialog(tk.Toplevel):
    """
    A modal dialog window that allows users to register a new material entry.
    
    Provides entry fields for the material's common name and scientific name, 
    and incorporates a read-only Combobox drop-down dynamically populated with 
    pre-existing color entries fetched from the database layer.
    """

    def __init__(self, parent, controller):
        """
        Initializes the dialog view, fetches reference data from the database,
        binds input reactive variables and builds the graphical grid layout.

        Args:
            parent (tk.Misc): The parent container or main window launching this dialog.
            controller (any): The application controller handling data delegation and models.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Add New Material")
        self.controller = controller
        self.db = controller.db

        self.name_var = tk.StringVar()
        self.sci_name_var = tk.StringVar()
        self.color_var = tk.StringVar()

        self.color_map = {c['name']: c['id'] for c in self.db.get_all_colors()}

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Material Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Scientific Name:").grid(row=1, column=0, sticky="w", pady=5)
        sci_name_entry = ttk.Entry(frame, textvariable=self.sci_name_var, width=30)
        sci_name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Color:").grid(row=2, column=0, sticky="w", pady=5)
        color_combo = ttk.Combobox(frame, textvariable=self.color_var, values=list(self.color_map.keys()), state="readonly")
        color_combo.grid(row=2, column=1, sticky="ew", pady=5)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(button_frame, text="Save", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")

        self.grab_set()
        self.wait_window(self)

    def on_save(self):
        """
        Validates input constraints, maps descriptive combobox labels back to 
        relational database primary key integers and dispatches structural changes 
        to the orchestrating application controller.
        """
        name = self.name_var.get()
        sci_name = self.sci_name_var.get()
        color_name = self.color_var.get()
        color_id = self.color_map.get(color_name)

        if not name:
            # In a real app, you would show a proper error message
            print("Error: Material Name is required.")
            return

        try:
            self.controller.add_new_material(name, sci_name, color_id)
            self.destroy()
        except Exception as e:
            # In a real app, you whould show a proper error message
            print(f"Error saving material: {e}")
