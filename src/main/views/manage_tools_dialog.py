import tkinter as tk
from tkinter import ttk, messagebox

class ManageToolsDialog(tk.Toplevel):
    """
    A modal dialog window for managing the catalog of available mechanical tools.
    Displays tools grouped by their categories and handles asset deletion safely.
    """

    def __init__(self, parent, controller):
        """
        Initializes the tool management dialog window.

        Args:
            parent: The parent Tkinter window.
            controller: The main application controller instance for database interaction.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Manage Tools Catalog")
        self.geometry("525x400")
        self.controller = controller

        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ttk.Label(frame, text="Registered Tools (Grouped by Category):", font=('', 10, 'bold')).pack(anchor="w", pady=(0, 5))

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
        self._set_modal()

    def _set_modal(self):
        """Ensures the window is visible and focused before grabbing input focus."""
        self.deiconify()
        self.focus_set()
        self.grab_set()
        self.wait_window(self)

    def load_data(self):
        """Fetches registered tools and sorts them clean into category headers."""
        self.listbox.delete(0, tk.END)
        self.item_data.clear()

        try:
            tools = []
            # 1. Attempt to call an explicit database wrapper if available
            if hasattr(self.controller.db, 'get_all_tools'):
                tools = self.controller.db.get_all_tools()
            else:
                # Fallback: Query the database tool table directly
                with self.controller.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, category FROM tool ORDER BY category, name")
                    tools = [{'id': row[0], 'name': row[1], 'category': row[2]} for row in cursor.fetchall()]

            # Group our tools dictionary by category string
            grouped_tools = {}
            for t in tools:
                cat = t.get('category', '').strip() or "Uncategorized"
                if cat not in grouped_tools:
                    grouped_tools[cat] = []
                grouped_tools[cat].append(t)

            # Insert into the Listbox with standard layout tree formatting
            for category, tool_list in sorted(grouped_tools.items()):
                cat_text = f"[CAT] {category}"
                self.listbox.insert(tk.END, cat_text)
                self.listbox.itemconfig(tk.END, {'fg': 'blue'})
                self.item_data[cat_text] = {'type': 'category', 'name': category}

                for t in tool_list:
                    tool_text = f"      ↳ [TOOL] {t['name']}"
                    self.listbox.insert(tk.END, tool_text)
                    self.item_data[tool_text] = {'type': 'tool', 'id': t['id'], 'name': t['name']}

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tools: {e}")

    def on_delete(self):
        """Validates the selection item context and deletes the target row asset."""
        selection = self.listbox.curselection()
        if not selection:
            return

        display_text = self.listbox.get(selection[0])
        if display_text not in self.item_data:
            return

        info = self.item_data[display_text]
        
        # Intercept if they click a pure structural text category header
        if info['type'] == 'category':
            messagebox.showinfo("Info", "To clear an entire category, delete all of its underlying tools individual records.")
            return

        item_id = info['id']
        item_name = info['name']
        
        msg = f"Delete this tool asset permanently from catalog?\n\n{item_name}"
        if messagebox.askyesno("Confirm Deletion", msg):
            try:
                success = False
                # 1. Attempt to call an explicit application controller wrapper
                if hasattr(self.controller, 'delete_tool'):
                    success = self.controller.delete_tool(item_id)
                else:
                    # Fallback: Drop down to running a direct SQL delete operation query safely
                    with self.controller.db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM tool WHERE id = ?", (item_id,))
                        conn.commit()
                    success = True

                if success:
                    self.load_data()
                else:
                    messagebox.showwarning("Warning", "Deletion failed. Tool might currently be used by active workflow actions.")
            except Exception as e:
                messagebox.showerror("Error", f"Database transaction failed:\n{e}")