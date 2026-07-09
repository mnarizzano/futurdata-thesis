import tkinter as tk
from tkinter import ttk, messagebox

class ManageMaterialsDialog(tk.Toplevel):
    """
    A modal dialog window for managing the catalog of available materials.

    This dialog displays all existing materials retrieved from the database,
    showing their names, and allows the user to delete an individual material
    if they are not currently in use by any diagram components.
    """

    def __init__(self, parent, controller):
        """
        Initializes the material management dialog window.

        Args:
            parent: The parent Tkinter window.
            controller: The main application controller instance for database interaction.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Manage Materials")
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
        
        self.material_records = {}
        self.load_materials()
        
        self.grab_set()
        self.wait_window(self)

    def load_materials(self):
        "Displays a list of the already-existing materials."
        self.listbox.delete(0, tk.END)
        self.material_records.clear()
        materials = self.controller.db.get_all_materials()
        for m in materials:
            display_text = m['name']
            self.listbox.insert(tk.END, display_text)
            self.material_records[display_text] = m['id']

    def on_delete(self):
        """
        Deletes an already-existing material upon confirmation.
        It does not delete a material if it is already being used by a component.
        """
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a material to delete.", parent=self)
            return
            
        selected_text = self.listbox.get(selection[0])
        material_id = self.material_records[selected_text]
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{selected_text}'?", parent=self):
            try:
                self.controller.delete_material(material_id)
                self.load_materials()
                messagebox.showinfo("Success", "Material deleted successfully.", parent=self)
            except ValueError as e:
                messagebox.showerror("Constraint Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)