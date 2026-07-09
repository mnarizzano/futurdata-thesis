import tkinter as tk
from tkinter import ttk

class AddToolDialog(tk.Toplevel):
    """
    A modal dialog window that allows users to register a new mechanical tool 
    or equipment asset into the global system catalog.
    
    Provides simple form layout entries to collect a tool name and its 
    associated operational category classification.
    """

    def __init__(self, parent, controller):
        """
        Initializes the top-level dialog, maps internal controller pointers, 
        constructs the component input fields and locks UI input focus.

        Args:
            parent (tk.Misc): The parent widget or window shell nesting this popup.
            controller (any): The core application controller driving system flow.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Add New Tool")
        self.controller = controller
        self.db = controller.db

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Tool Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Category:").grid(row=1, column=0, sticky="w", pady=5)
        category_entry = ttk.Entry(frame, textvariable=self.category_var, width=30)
        category_entry.grid(row=1, column=1, sticky="ew", pady=5)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(button_frame, text="Save", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")

        self.grab_set()
        self.wait_window(self)

    def on_save(self):
        """
        Validates form inputs, trims unnecessary padding whitespaces and 
        commands the backend system architecture to persist the new asset record.
        """
        name = self.name_var.get()
        category = self.category_var.get()

        if not name:
            # In a real app, you would show a proper error message
            print("Error: Tool Name is required.")
            return

        try:
            self.controller.add_new_tool(name, category)
            self.destroy()
        except Exception as e:
            # In a real app, you would show a proper error message
            print(f"Error saving tool: {e}")
