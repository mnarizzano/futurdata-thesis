import tkinter as tk
from tkinter import ttk, messagebox

class ManageColorsDialog(tk.Toplevel):
    """
    A modal dialog window for managing the catalog of available colors.

    This dialog displays all existing colors retrieved from the database,
    showing their names and hex codes, and allows the user to delete an
    individual color if it is not currently in use by any diagram components.
    """

    def __init__(self, parent, controller):
        """
        Initializes the color management dialog window.

        Args:
            parent: The parent Tkinter window.
            controller: The main application controller instance for database interaction.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Manage Colors")
        self.geometry("350x300")
        self.controller = controller
        
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(frame, width=30, height=10)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", fill="y", padx=(5, 0))
        
        ttk.Button(btn_frame, text="Delete", command=self.on_delete).pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(pady=5, fill="x")
        
        self.color_records = {}
        self.load_colors()
        
        self.grab_set()
        self.wait_window(self)

    def load_colors(self):
        "Displays a list of the already-existing colors."
        self.listbox.delete(0, tk.END)
        self.color_records.clear()
        colors = self.controller.db.get_all_colors()
        for c in colors:
            display_text = f"{c['name']} ({c['hex_code']})"
            self.listbox.insert(tk.END, display_text)
            self.color_records[display_text] = c['id']

    def on_delete(self):
        """
        Deletes an already-existing color upon confirmation.
        It does not delete a color if it is already being used by a component.
        """
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a color to delete.", parent=self)
            return
            
        selected_text = self.listbox.get(selection[0])
        color_id = self.color_records[selected_text]
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{selected_text}'?", parent=self):
            try:
                self.controller.delete_color(color_id)
                self.load_colors()
                messagebox.showinfo("Success", "Color deleted successfully.", parent=self)
            except ValueError as e:
                messagebox.showerror("Constraint Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)