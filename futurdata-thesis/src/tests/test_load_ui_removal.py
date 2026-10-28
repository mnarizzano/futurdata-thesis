"""Manual loading is absent; import, persistence and editor controls remain."""
import tkinter as tk
from unittest.mock import patch

import pytest

from src.main.controllers.app_controller import AppController
from src.main.repositories.json_repository import JsonRepository
from src.main.views.main_window import MainWindow


@pytest.fixture
def window(tmp_path):
    root = tk.Tk()
    root.withdraw()
    repo = JsonRepository(str(tmp_path / "store.json"))
    app = AppController(repository=repo)
    before = repo.file_path.read_bytes()
    view = MainWindow(root, app)
    app.set_view(view)
    assert repo.file_path.read_bytes() == before
    yield view, app
    root.destroy()


def file_entries(view):
    menubar = view.root.nametowidget(view.root.cget("menu"))
    file_index = next(i for i in range(menubar.index("end") + 1)
                      if menubar.type(i) == "cascade" and menubar.entrycget(i, "label") == "File")
    menu = view.root.nametowidget(menubar.entrycget(file_index, "menu"))
    return menu, [(menu.type(i), menu.entrycget(i, "label") if menu.type(i) != "separator" else "")
                  for i in range(menu.index("end") + 1)]


def test_file_menu_and_toolbar_have_no_manual_loading_or_orphan_separators(window):
    view, app = window
    menu, entries = file_entries(view)
    labels = [label for kind, label in entries if kind != "separator"]
    assert labels == ["New", "Save", "Export Project ZIP...", "Export Document", "Import Project...", "Exit"]
    kinds = [kind for kind, label in entries]
    assert kinds[0] != "separator" and kinds[-1] != "separator"
    assert not any(a == b == "separator" for a, b in zip(kinds, kinds[1:]))
    toolbar = next(child for child in view.root.winfo_children()
                   if child.winfo_class() == "TFrame" and str(child.cget("relief")) == "raised")
    buttons = [child.cget("text") for child in toolbar.winfo_children()
               if child.winfo_class() in {"TButton", "Button"}]
    assert not any(label.startswith(("Load", "Open")) for label in buttons)
    assert {"New", "ZIP Export", "PPTX Export", "Undo", "Redo"} <= set(buttons)
    assert view.sidebar_tabs.tab(0, "text") == "Shapes"
    assert view.sidebar_tabs.tab(1, "text") == "Navigator"
    assert not hasattr(app, "show_product_list")
    assert not hasattr(app, "open_diagram")
    assert not hasattr(app, "load_product_diagram")
    assert not hasattr(view, "show_product_list")


def test_load_open_shortcuts_removed_and_supported_shortcuts_retained(window):
    view, app = window
    assert not view.root.bind("<Control-l>")
    assert not view.root.bind("<Control-o>")
    for shortcut in ("<Control-n>", "<Control-s>", "<Control-z>", "<Control-y>"):
        assert view.root.bind(shortcut)


def test_import_menu_remains_connected_to_supported_workflow(window):
    view, app = window
    with patch.object(app, "import_diagram_enhanced") as import_project:
        view._create_menu()
        menu, entries = file_entries(view)
        menu.invoke(next(i for i, (_, label) in enumerate(entries) if label == "Import Project..."))
        import_project.assert_called_once_with()
