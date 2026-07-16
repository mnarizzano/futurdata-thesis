import tkinter as tk
from tkinter import ttk, messagebox

class ManageMaterialsDialog(tk.Toplevel):
    """
    A modal dialog window for managing the catalog of available materials, categories, and types.

    This dialog displays all existing materials and custom types retrieved from the database,
    allowing the user to delete individual records if they are not currently in use.
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
        self.title("Manage Materials & Categories")
        self.geometry("525x400")  # Slightly taller to accommodate types section
        self.controller = controller

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ttk.Label(frame, text="Material Hierarchy & Types (Duplicates Hidden):", font=('', 10, 'bold')).pack(anchor="w", pady=(0, 5))

        self.listbox = tk.Listbox(frame, width=50, height=18, font=('Courier', 10))
        self.listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", fill="y", padx=(5, 0))

        ttk.Button(btn_frame, text="Delete", command=self.on_delete).pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Refresh", command=self.load_data).pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(pady=5, fill="x")

        self.item_data = {} 
        self.load_data()
        self._set_modal()  # FIX: Triggers the modal focus loop automatically

    def _set_modal(self):
        """Ensures the window is visible and focused before grabbing input."""
        self.deiconify()
        self.focus_set()
        self.grab_set()
        self.wait_window(self)

    def load_data(self):
        """Displays materials grouped under categories, followed by registered types."""
        self.listbox.delete(0, tk.END)
        self.item_data.clear()

        try:
            categories = self.controller.db.get_all_material_categories()
            materials = self.controller.db.get_all_materials()

            # Create a lookup for duplicate names
            cat_names = {cat['name'].lower(): cat['id'] for cat in categories}

            for cat in categories:
                cat_name_lower = cat['name'].lower()
                cat_text = f"[CAT] {cat['name']}"
                self.listbox.insert(tk.END, cat_text)
                self.listbox.itemconfig(tk.END, {'fg': 'blue'})
                
                # Check if a material with the EXACT same name exists
                duplicate_mat = next((m for m in materials if m['name'].lower() == cat_name_lower), None)
                
                # Store mapping: if duplicate exists, store both IDs to delete together
                self.item_data[cat_text] = {
                    'type': 'category',
                    'id': cat['id'],
                    'duplicate_material_id': duplicate_mat['id'] if duplicate_mat else None
                }

                # Insert Materials belonging to this category (excluding the duplicate name one)
                cat_materials = [m for m in materials if m.get('category_id') == cat['id']]
                for m in cat_materials:
                    if m['name'].lower() == cat_name_lower:
                        continue # Already handled by the category entry
                    
                    mat_text = f"      ↳ [MAT] {m['name']}"
                    self.listbox.insert(tk.END, mat_text)
                    self.item_data[mat_text] = {'type': 'material', 'id': m['id']}
            
            # Handle uncategorized materials (excluding duplicates)
            uncategorized = [m for m in materials if not m.get('category_id') and m['name'].lower() not in cat_names]
            if uncategorized:
                self.listbox.insert(tk.END, "[UNCATEGORIZED]")
                for m in uncategorized:
                    mat_text = f"      ↳ [MAT] {m['name']}"
                    self.listbox.insert(tk.END, mat_text)
                    self.item_data[mat_text] = {'type': 'material', 'id': m['id']}

            # ==================== NEW: LOAD MATERIAL TYPES ====================
            material_types = []
            if hasattr(self.controller.db, 'get_all_material_types'):
                material_types = self.controller.db.get_all_material_types()
            else:
                # Direct DB execution fallback if explicit method isn't in database.py
                with self.controller.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name FROM material_type ORDER BY name")
                    material_types = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

            if material_types:
                self.listbox.insert(tk.END, "")  # Blank separator line
                self.listbox.insert(tk.END, "[REGISTERED MATERIAL TYPES]")
                self.listbox.itemconfig(tk.END, {'fg': '#800080'})  # Purple header
                
                for t in material_types:
                    type_text = f"      ↳ [TYPE] {t['name']}"
                    self.listbox.insert(tk.END, type_text)
                    self.item_data[type_text] = {'type': 'type', 'id': t['id']}

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def on_delete(self):
        """
        Deletes an already-existing material upon confirmation.
        It does not delete a material if it is already being used by a component.
        """
        selection = self.listbox.curselection()
        if not selection:
            return

        display_text = self.listbox.get(selection[0])
        if display_text not in self.item_data:
            return

        info = self.item_data[display_text]
        item_type = info['type']
        item_id = info['id']
        
        if messagebox.askyesno("Confirm",f"Are you sure you want to delete '{display_text}'?", parent=self):
            try:
                success = False
                if item_type == 'category':
                    success = self.controller.delete_material_category(item_id)
                    if info.get('duplicate_material_id'):
                        self.controller.delete_material(info['duplicate_material_id'])
                
                elif item_type == 'type':
                    # ==================== NEW: HANDLE TYPE DELETION ====================
                    if hasattr(self.controller, 'delete_material_type'):
                        success = self.controller.delete_material_type(item_id)
                    else:
                        # Direct execution fallback if app_controller wrapper is missing
                        with self.controller.db._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM material_type WHERE id = ?", (item_id,))
                            conn.commit()
                        success = True
                
                else:
                    success = self.controller.delete_material(item_id)

                if success:
                    self.load_data()
                else:
                    messagebox.showwarning("Warning", "Deletion failed. Item might be in use by an active material combination.")
            except Exception as e:
                messagebox.showerror("Error", str(e))