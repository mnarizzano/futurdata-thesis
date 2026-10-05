"""Tests for compact status, cancellation, palette terminology, and cursor restoration."""
import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from src.main.controllers.app_controller import AppController
from src.main.controllers.catalog_controller import CatalogController
from src.main.models import ComponentBox, ActionCircle, DiamondStep, ArrowShape
from src.main.repositories.json_repository import JsonRepository
from src.main.utils.feedback import FeedbackType
from src.main.views.main_window import MainWindow


@pytest.fixture(scope="module")
def root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(root, tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    with patch("src.main.controllers.app_controller.get_repository", return_value=repo):
        controller = AppController()
    view = MainWindow(root, controller)
    controller.set_view(view)
    yield controller, view
    for widget in root.winfo_children():
        widget.destroy()


def palette_button(view, text):
    palette = view.sidebar_tabs.nametowidget(view.sidebar_tabs.tabs()[0])
    return next(widget for widget in palette.winfo_children()
                if widget.winfo_class() == "TButton" and widget.cget("text").endswith(text))


@pytest.mark.parametrize("label,model,message", [
    ("Root Component", ComponentBox, "Added Root Component"),
    ("Leaf Component", ComponentBox, "Added Leaf Component"),
    ("Composite Comp.", ComponentBox, "Added Composite Component"),
    ("Step", DiamondStep, "Added Step"),
    ("Action", ActionCircle, "Added Action"),
])
def test_palette_feedback_matches_created_node(app, label, model, message):
    controller, view = app
    palette_button(view, label).invoke()
    assert isinstance(controller.diagram.selected_shapes[0], model)
    assert view.status_label.cget("text") == message
    assert str(view.status_label.cget("foreground")) == "#176534"
    assert view.canvas.cget("cursor") == ""


@pytest.mark.parametrize("operation", ["new", "open", "load", "import"])
def test_cancel_aborts_without_save_clear_or_success_status(app, operation):
    controller, view = app
    controller.add_shape("component_root")
    controller.diagram.shapes[0].properties["name"] = "Original"
    controller.diagram.shapes[0].text = "Original"
    assert controller.save_diagram()
    node = controller.diagram.shapes[0]
    controller.apply_properties(node, {"name": node.properties["name"]}, {"name": "Unsaved edit"})
    diagram = controller.diagram
    owner = diagram.diagram_id
    nodes = list(diagram.shapes)
    product = controller.current_product_id
    history = list(controller.command_history.history)
    before = controller.repository.file_path.read_bytes()
    # Reproduce a previous New success remaining on screen before Cancel.
    view.set_status("New diagram created", FeedbackType.SUCCESS)
    with patch("tkinter.messagebox.askyesnocancel", return_value=None), \
         patch.object(controller, "save_diagram", wraps=controller.save_diagram) as save, \
         patch.object(diagram, "clear", wraps=diagram.clear) as clear, \
         patch.object(view, "ask_file_path") as choose:
        {"new": controller.new_diagram, "open": controller.open_diagram,
         "load": lambda: controller.load_product_diagram(product),
         "import": controller.import_diagram_enhanced}[operation]()
        save.assert_not_called()
        clear.assert_not_called()
        choose.assert_not_called()
    assert controller.diagram is diagram and diagram.diagram_id == owner
    assert diagram.shapes == nodes and node.properties["name"] == "Unsaved edit"
    assert diagram.modified and controller.command_history.history == history
    assert controller.repository.file_path.read_bytes() == before
    assert view.status_label.cget("text") == "Operation cancelled."
    assert str(view.status_label.cget("foreground")) == "black"


@pytest.mark.parametrize("answer", [True, False])
def test_new_save_and_discard_semantics(app, answer):
    controller, view = app
    controller.add_shape("component_root")
    controller.diagram.shapes[0].properties["name"] = "Original"
    controller.diagram.shapes[0].text = "Original"
    assert controller.save_diagram()
    product = controller.current_product_id
    node = controller.diagram.shapes[0]
    controller.apply_properties(node, {"name": node.properties["name"]}, {"name": "Unsaved edit"})
    before = controller.repository.file_path.read_bytes()
    with patch("tkinter.messagebox.askyesnocancel", return_value=answer):
        controller.new_diagram()
    reopened = JsonRepository(str(controller.repository.file_path))
    assert reopened.get_product(product)["name"] == ("Unsaved edit" if answer else "Original")
    if not answer:
        assert controller.repository.file_path.read_bytes() == before
    assert not controller.diagram.shapes and not controller.diagram.modified
    assert view.status_label.cget("text") == "New diagram created"


def test_failed_yes_save_keeps_error_and_current_diagram(app):
    controller, view = app
    controller.add_shape("component_root")
    diagram = controller.diagram
    with patch("tkinter.messagebox.askyesnocancel", return_value=True), \
         patch.object(controller.repository, "save_diagram_snapshot", side_effect=OSError("disk full")):
        controller.new_diagram()
    assert controller.diagram is diagram and diagram.modified
    assert str(view.status_label.cget("foreground")) == "red"
    assert "New diagram created" not in view.status_label.cget("text")


def test_cursor_modes_creation_and_arrow_completion(app):
    controller, view = app
    assert view.canvas.cget("cursor") == ""
    palette_button(view, "Arrow").invoke()
    assert controller.arrow_mode and view.canvas.cget("cursor") == ""
    controller.on_escape(MagicMock())
    assert not controller.arrow_mode and view.canvas.cget("cursor") == ""
    # Switching from arrow mode to a node must not leave a pending arrow mode.
    controller.add_shape("arrow")
    palette_button(view, "Root Component").invoke()
    assert not controller.arrow_mode and view.canvas.cget("cursor") == ""
    palette_button(view, "Step").invoke()
    source, target = controller.diagram.shapes[:2]
    controller.add_shape("arrow")
    controller._handle_arrow_connection_click(source)
    controller._handle_arrow_connection_click(target)
    assert isinstance(controller.diagram.shapes[-1], ArrowShape)
    assert view.status_label.cget("text") == "Arrow created."
    assert not controller.arrow_mode and view.canvas.cget("cursor") == ""
    controller.toggle_connect_mode()
    assert controller.connect_mode and view.canvas.cget("cursor") == ""
    controller.toggle_connect_mode()
    assert not controller.connect_mode and view.canvas.cget("cursor") == ""


@pytest.mark.parametrize("kind", ["component_root", "action", "diamond"])
def test_properties_refresh_preserves_unsaved_node_values(app, kind):
    controller, view = app
    controller.add_shape("component_root")
    if kind != "component_root":
        controller.add_shape(kind)
    assert controller.save_diagram()
    node = controller.diagram.selected_shapes[0]
    if isinstance(node, ComponentBox):
        old, new = {"name": node.properties["name"], "text": node.text}, {"name": "Changed", "text": "Changed"}
    elif isinstance(node, ActionCircle):
        old, new = {"text": node.text, "image_path": node.image_path}, {"text": "Changed", "image_path": "missing.png"}
    else:
        old, new = {"name": node.name, "text": node.text}, {"name": "Changed", "text": "Changed"}
    before = controller.repository.file_path.read_bytes()
    assert controller.apply_properties(node, old, new)
    view.update_properties_panel(node)
    assert node.text == "Changed" and controller.diagram.modified
    assert controller.repository.file_path.read_bytes() == before
