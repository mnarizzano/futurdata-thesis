from .dialog_layout import center_on_workspace
import tkinter as tk
from tkinter import ttk, messagebox

class ManageToolsDialog(tk.Toplevel):
    """
    A modal dialog window for managing the catalog of available tools.

    This dialog displays all existing tools retrieved from the JSON repository,
    showing their names, and allows the user to delete an individual tool
    if they are not currently in use by any diagram actions.
    """

    def __init__(self, parent, controller):
        """
        Initializes the tool management dialog window.

        Args:
            parent: The parent Tkinter window.
            controller: The main application controller instance for repository interaction.
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Manage Tools")
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
        
        self.tool_records = {}
        self.load_tools()
        
        center_on_workspace(self, parent)
        self.grab_set()
        self.wait_window(self)

    def load_tools(self):
        "Displays a list of the already-existing tools."
        self.listbox.delete(0, tk.END)
        self.tool_records.clear()
        tools = self.controller.catalog.get_all_tools()
        for m in tools:
            category = m.get('category') or ''
            display_text = f"{m['name']} ({category})" if category else m['name']
            self.listbox.insert(tk.END, display_text)
            self.tool_records[display_text] = m['id']

    def refresh_catalogs(self):
        self.load_tools()

    def on_delete(self):
        """
        Deletes an already-existing tool upon confirmation.
        It does not delete a tool if it is already being used by an action.
        """
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a tool to delete.", parent=self)
            return
            
        selected_text = self.listbox.get(selection[0])
        tool_id = self.tool_records[selected_text]
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{selected_text}'?", parent=self):
            try:
                self.controller.delete_tool(tool_id)
                self.load_tools()
            except ValueError as e:
                messagebox.showerror("Constraint Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)