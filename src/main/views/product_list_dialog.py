"""
Product List Dialog - Shows all saved products/diagrams
User can select a product to load its complete disassembly diagram
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from typing import Optional, Dict, Any, Callable


class ProductListDialog:
    """Dialog to display and select from saved products."""
    
    def __init__(self, parent, database, on_load_callback: Callable[[int], None]):
        """
        Initialize product list dialog.
        
        Args:
            parent: Parent window
            database: DatabaseManager instance
            on_load_callback: Function to call when loading a product (receives product_id)
        """
        self.parent = parent
        self.db = database
        self.on_load_callback = on_load_callback
        self.selected_product_id = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Load Product Diagram")
        self.dialog.geometry("800x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._setup_ui()
        self._load_products()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Title
        title_frame = tk.Frame(self.dialog, bg="#2c3e50", height=60)
        title_frame.pack(fill=tk.X, side=tk.TOP)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="📦 Saved Products",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Main content frame
        content_frame = tk.Frame(self.dialog, bg="white")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Search frame
        search_frame = tk.Frame(content_frame, bg="white")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", bg="white").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_products())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Treeview with scrollbar
        tree_frame = tk.Frame(content_frame, bg="white")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "brand", "model", "components", "steps", "modified"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="browse"
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Column headings
        self.tree.heading("name", text="Product Name", anchor=tk.W)
        self.tree.heading("brand", text="Brand", anchor=tk.W)
        self.tree.heading("model", text="Model", anchor=tk.W)
        self.tree.heading("components", text="Components", anchor=tk.CENTER)
        self.tree.heading("steps", text="Steps", anchor=tk.CENTER)
        self.tree.heading("modified", text="Last Modified", anchor=tk.W)
        
        # Column widths
        self.tree.column("name", width=250)
        self.tree.column("brand", width=150)
        self.tree.column("model", width=120)
        self.tree.column("components", width=100)
        self.tree.column("steps", width=80)
        self.tree.column("modified", width=180)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Double-click to load
        self.tree.bind("<Double-Button-1>", lambda e: self._load_selected())
        
        # Info panel
        info_frame = tk.Frame(content_frame, bg="#ecf0f1", relief=tk.SUNKEN, bd=1)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_label = tk.Label(
            info_frame,
            text="Select a product to view details",
            bg="#ecf0f1",
            fg="#7f8c8d",
            anchor=tk.W,
            padx=10,
            pady=5
        )
        self.info_label.pack(fill=tk.X)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Button frame
        button_frame = tk.Frame(self.dialog, bg="white")
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Buttons
        load_btn = tk.Button(
            button_frame,
            text="Load Diagram",
            command=self._load_selected,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        load_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        delete_btn = tk.Button(
            button_frame,
            text="Delete",
            command=self._delete_selected,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10),
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        stats_label = tk.Label(
            button_frame,
            text="",
            bg="white",
            fg="#7f8c8d"
        )
        stats_label.pack(side=tk.LEFT)
        self.stats_label = stats_label
    
    def _load_products(self):
        """Load all products from database."""
        try:
            products = self.db.get_all_products()
            self.all_products = products
            self._display_products(products)
        except sqlite3.DatabaseError as exc:
            messagebox.showerror("Error", f"Failed to load products from the database: {exc}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {e}")
    
    def _display_products(self, products):
        """Display products in treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add products
        for product in products:
            # Get component and step counts
            components = self.db.get_components_by_product(product['id'])
            
            # Count steps for this product (from root component)
            steps_count = 0
            try:
                # This is a simplified count - you might want to count all steps recursively
                conn = self.db._get_connection()
                cursor = conn.__enter__().cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM disassembly_step WHERE input_root_component_id = ?",
                    (product['id'],)
                )
                steps_count = cursor.fetchone()[0]
                conn.__exit__(None, None, None)
            except:
                pass
            
            # Format modified date
            modified = product.get('modified_at', '')
            if modified:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified)
                    modified = dt.strftime("%Y-%m-%d %H:%M")
                except (TypeError, ValueError):
                    pass
            
            self.tree.insert(
                "",
                tk.END,
                iid=str(product['id']),
                values=(
                    product.get('name', 'Untitled'),
                    product.get('brand', ''),
                    product.get('model', ''),
                    len(components),
                    steps_count,
                    modified
                )
            )
        
        # Update stats
        self.stats_label.config(text=f"Total Products: {len(products)}")
    
    def _filter_products(self):
        """Filter products based on search text."""
        search_text = self.search_var.get().lower()
        if not search_text:
            self._display_products(self.all_products)
            return
        
        filtered = [
            p for p in self.all_products
            if search_text in p.get('name', '').lower()
            or search_text in p.get('brand', '').lower()
            or search_text in p.get('model', '').lower()
        ]
        self._display_products(filtered)
    
    def _on_select(self, event):
        """Handle product selection."""
        selection = self.tree.selection()
        if not selection:
            self.info_label.config(text="Select a product to view details")
            return
        
        product_id = int(selection[0])
        product = self.db.get_product(product_id)
        
        if product:
            info = (
                f"📦 {product['name']} | "
                f"Brand: {product.get('brand', 'N/A')} | "
                f"Model: {product.get('model', 'N/A')}"
            )
            if product.get('description'):
                info += f" | {product['description']}"
            
            self.info_label.config(text=info)
    
    def _load_selected(self):
        """Load the selected product diagram."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a product to load")
            return
        
        product_id = int(selection[0])
        self.dialog.destroy()
        
        # Call the callback to load the diagram
        if self.on_load_callback:
            self.on_load_callback(product_id)
    
    def _delete_selected(self):
        """Delete the selected product."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a product to delete")
            return
        
        product_id = int(selection[0])
        product = self.db.get_product(product_id)
        
        if not product:
            return
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{product['name']}'?\n\n"
            f"This will delete all associated components, steps, and actions.\n"
            f"This action cannot be undone."
        )
        
        if result:
            try:
                self.db.delete_product(product_id)
                self._load_products()
                messagebox.showinfo("Success", f"Product '{product['name']}' deleted successfully")
            except sqlite3.DatabaseError as exc:
                messagebox.showerror("Error", f"Failed to delete product from the database: {exc}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete product: {e}")
