import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3


class _SimpleNameDialog(tk.Toplevel):
    def __init__(self, parent, title: str, label_text: str, on_submit):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.resizable(False, False)
        self.on_submit = on_submit

        self.value_var = tk.StringVar()

        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text=label_text).grid(row=0, column=0, sticky="w", pady=(0, 6))
        entry = ttk.Entry(frame, textvariable=self.value_var, width=36)
        entry.grid(row=1, column=0, sticky="ew")
        entry.focus_set()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Button(button_frame, text="Add", command=self._submit).pack(side="left", padx=(0, 6))
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")

        self.grab_set()
        self.wait_window(self)

    def _submit(self):
        value = self.value_var.get().strip()
        if not value:
            messagebox.showerror("Error", "Name is required.")
            return
        try:
            self.on_submit(value)
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))


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
        self.resizable(False, False)
        self.controller = controller
        self.db = controller.db
        self._apply_combobox_style()

        self.name_var = tk.StringVar()
        self.technical_name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.subcategory_var = tk.StringVar()
        self.type_var = tk.StringVar()

        self._build_ui()
        self._load_categories()
        self._bind_events()

        self.grab_set()
        self.wait_window(self)

    def _apply_combobox_style(self):
        """Use a neutral combobox selection style for this dialog."""
        style = ttk.Style(self)
        self.combo_style_name = "MaterialDialog.TCombobox"
        try:
            style.configure(
                self.combo_style_name,
                fieldbackground="white",
                background="white",
                foreground="black",
                arrowcolor="black",
            )
            style.map(
                self.combo_style_name,
                fieldbackground=[("readonly", "white"), ("active", "white"), ("focus", "white")],
                background=[("readonly", "white"), ("active", "white"), ("focus", "white")],
                foreground=[("readonly", "black"), ("active", "black"), ("focus", "black")],
            )
        except Exception:
            pass

        # Reduce the blue highlight in the dropdown list itself.
        self.option_add("*TCombobox*Listbox.selectBackground", "#d9d9d9")
        self.option_add("*TCombobox*Listbox.selectForeground", "black")
        self.option_add("*TCombobox*Listbox.background", "white")
        self.option_add("*TCombobox*Listbox.foreground", "black")

    def _build_ui(self):
        frame = ttk.Frame(self, padding="12")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        row = 0

        ttk.Label(frame, text="Category:").grid(row=row, column=0, sticky="w", pady=4)
        category_frame = ttk.Frame(frame)
        category_frame.grid(row=row, column=1, sticky="ew", pady=4)
        category_frame.columnconfigure(0, weight=1)
        self.category_combo = ttk.Combobox(category_frame, textvariable=self.category_var, state="readonly", style=self.combo_style_name)
        self.category_combo.grid(row=0, column=0, sticky="ew")
        ttk.Button(category_frame, text="+", width=3, command=self._add_category).grid(row=0, column=1, padx=(6, 0))

        row += 1
        self.subcategory_label = ttk.Label(frame, text="Sub Category:")
        self.subcategory_label.grid(row=row, column=0, sticky="w", pady=4)
        self.subcategory_frame = ttk.Frame(frame)
        self.subcategory_frame.grid(row=row, column=1, sticky="ew", pady=4)
        self.subcategory_frame.columnconfigure(0, weight=1)
        self.subcategory_combo = ttk.Combobox(self.subcategory_frame, textvariable=self.subcategory_var, state="readonly", style=self.combo_style_name)
        self.subcategory_combo.grid(row=0, column=0, sticky="ew")
        ttk.Button(self.subcategory_frame, text="+", width=3, command=self._add_subcategory).grid(row=0, column=1, padx=(6, 0))

        row += 1
        self.type_label = ttk.Label(frame, text="Type:")
        self.type_label.grid(row=row, column=0, sticky="w", pady=4)
        self.type_frame = ttk.Frame(frame)
        self.type_frame.grid(row=row, column=1, sticky="ew", pady=4)
        self.type_frame.columnconfigure(0, weight=1)
        self.type_combo = ttk.Combobox(self.type_frame, textvariable=self.type_var, state="readonly", style=self.combo_style_name)
        self.type_combo.grid(row=0, column=0, sticky="ew")
        ttk.Button(self.type_frame, text="+", width=3, command=self._add_type).grid(row=0, column=1, padx=(6, 0))

        row += 1
        ttk.Label(frame, text="Material Name:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.name_var, width=34).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Technical Name:").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.technical_name_var, width=34).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(button_frame, text="Save", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left")

    def _bind_events(self):
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._on_category_change())
        self.subcategory_combo.bind("<<ComboboxSelected>>", lambda e: self._on_subcategory_change())

    def _load_categories(self, select_id=None):
        categories = self.db.get_all_material_categories()
        self.category_map = {c["name"]: c["id"] for c in categories}
        self.category_map_reverse = {c["id"]: c["name"] for c in categories}
        names = [c["name"] for c in categories]
        self.category_combo["values"] = names
        if select_id and select_id in self.category_map_reverse:
            self.category_var.set(self.category_map_reverse[select_id])
        elif names and not self.category_var.get():
            self.category_var.set(names[0])
        self._load_subcategories()

    def _load_subcategories(self, select_id=None):
        category_id = self.category_map.get(self.category_var.get())
        subcategories = self.db.get_subcategories_by_category(category_id) if category_id else []
        self.subcategory_map = {s["name"]: s["id"] for s in subcategories}
        self.subcategory_map_reverse = {s["id"]: s["name"] for s in subcategories}
        names = [""] + [s["name"] for s in subcategories]
        self.subcategory_combo["values"] = names
        if select_id and select_id in self.subcategory_map_reverse:
            self.subcategory_var.set(self.subcategory_map_reverse[select_id])
        else:
            self.subcategory_var.set("")
        self._load_types()

    def _load_types(self, select_id=None):
        category_id = self.category_map.get(self.category_var.get())
        subcategory_id = self.subcategory_map.get(self.subcategory_var.get()) if self.subcategory_var.get() else None
        types = self.db.get_types_by_category(category_id, subcategory_id) if category_id else []
        self.type_map = {t["name"]: t["id"] for t in types}
        self.type_map_reverse = {t["id"]: t["name"] for t in types}
        names = [""] + [t["name"] for t in types]
        self.type_combo["values"] = names
        if select_id and select_id in self.type_map_reverse:
            self.type_var.set(self.type_map_reverse[select_id])
        else:
            self.type_var.set("")

    def _on_category_change(self):
        self._load_subcategories()

    def _on_subcategory_change(self):
        self._load_types()

    def _add_category(self):
        def submit(name):
            category_id = self.db.create_material_category(name)
            self._load_categories(select_id=category_id)
            self.category_var.set(name)
            self._load_subcategories()

        _SimpleNameDialog(self, "Add Material Category", "Category Name:", submit)

    def _add_subcategory(self):
        category_id = self.category_map.get(self.category_var.get())
        if not category_id:
            messagebox.showerror("Error", "Please select a category first.")
            return

        def submit(name):
            subcategory_id = self.db.create_material_subcategory(category_id, name)
            self._load_subcategories(select_id=subcategory_id)
            self.subcategory_var.set(name)
            self._load_types()

        _SimpleNameDialog(self, "Add Material Sub Category", "Sub Category Name:", submit)

    def _add_type(self):
        category_id = self.category_map.get(self.category_var.get())
        if not category_id:
            messagebox.showerror("Error", "Please select a category first.")
            return

        subcategory_id = self.subcategory_map.get(self.subcategory_var.get()) if self.subcategory_var.get() else None

        def submit(name):
            type_id = self.db.create_material_type(category_id, name, subcategory_id)
            self._load_types(select_id=type_id)
            self.type_var.set(name)

        _SimpleNameDialog(self, "Add Material Type", "Type Name:", submit)

    def on_save(self):
        """
        Validates input constraints, maps descriptive combobox labels back to 
        relational database primary key integers and dispatches structural changes 
        to the orchestrating application controller.
        """
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Material Name is required.")
            return

        category_id = self.category_map.get(self.category_var.get())
        subcategory_id = self.subcategory_map.get(self.subcategory_var.get()) if self.subcategory_var.get() else None
        type_id = self.type_map.get(self.type_var.get()) if self.type_var.get() else None
        technical_name = self.technical_name_var.get().strip()
        try:
            self.controller.add_new_material(
                name=name,
                category_id=category_id,
                subcategory_id=subcategory_id,
                type_id=type_id,
                technical_name=technical_name,
            )
            self.destroy()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "This material combination already exists or violates a database rule.")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving material: {e}")
