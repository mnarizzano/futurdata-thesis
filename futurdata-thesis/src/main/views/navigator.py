"""Tree widget holding display rows and shape IDs, never a diagram copy."""
from tkinter import ttk
from tkinter import font as tkfont


class Navigator(ttk.Frame):
    def __init__(self, parent, on_select):
        super().__init__(parent, width=150, height=200)
        self.grid_propagate(False)
        self.on_select = on_select
        self.item_shapes = {}
        self.shape_items = {}
        self._selection = ()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, show='tree', selectmode='browse', height=8)
        self.tree.column('#0', width=140, minwidth=40, stretch=False)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind('<<TreeviewSelect>>', self._on_selection)
        self.tree.bind('<Button-1>', self._on_click)

    def show_rows(self, rows, reset=False):
        opened = {item for item in self.item_shapes
                  if self.tree.item(item, 'open')} if not reset else set()
        old_items = set(self.item_shapes) if not reset else set()
        scroll = self.tree.yview()[0] if not reset else 0
        roots = self.tree.get_children('')
        if roots:
            self.tree.delete(*roots)
        self.item_shapes.clear()
        self.shape_items.clear()
        font = tkfont.nametofont(ttk.Style(self).lookup('Treeview', 'font') or 'TkDefaultFont')
        depth, width = {}, 140
        for row in rows:
            self.tree.insert(row.parent_id, 'end', iid=row.item_id, text=row.label,
                             open=row.item_id in opened or (not row.parent_id and row.item_id not in old_items))
            self.item_shapes[row.item_id] = row.shape_id
            self.shape_items.setdefault(row.shape_id, []).append(row.item_id)
            depth[row.item_id] = depth.get(row.parent_id, -1) + 1
            width = max(width, font.measure(row.label) + 24 * (depth[row.item_id] + 1) + 16)
        self.tree.column('#0', width=width)
        self.tree.yview_moveto(scroll)
        self._selection = ()

    def select_shapes(self, shape_ids):
        current = self.tree.selection()
        items = []
        for shape_id in shape_ids:
            candidates = self.shape_items.get(shape_id, [])
            if candidates:
                items.append(next((item for item in current if item in candidates), candidates[0]))
        self._selection = tuple(items)
        if current != self._selection:
            self.tree.selection_set(items)
        if items:
            item = items[-1]
            parent = self.tree.parent(item)
            while parent:
                self.tree.item(parent, open=True)
                parent = self.tree.parent(parent)
            self.tree.focus(item)
            self.tree.see(item)

    def _on_selection(self, event):
        selected = self.tree.selection()
        # Tk queues selection events, so compare actual state instead of a
        # temporary boolean guard that would be cleared before delivery.
        if selected == self._selection:
            return
        self._selection = selected
        if selected:
            shape_id = self.item_shapes.get(selected[-1])
            if shape_id is not None:
                self.on_select(shape_id)

    def _on_click(self, event):
        # Clicking an already-selected row should navigate again after panning.
        item = self.tree.identify_row(event.y)
        element = self.tree.identify_element(event.x, event.y)
        if item in self.tree.selection() and 'indicator' not in element:
            shape_id = self.item_shapes.get(item)
            if shape_id is not None:
                self.on_select(shape_id)
