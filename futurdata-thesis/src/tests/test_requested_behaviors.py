"""Regression tests for image lifecycle, feedback, scrolling, and discard semantics."""
import copy
import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.main.controllers.app_controller import AppController
from src.main.controllers.catalog_controller import CatalogController
from src.main.models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape, Connection
from src.main.repositories.json_repository import JsonRepository
from src.main.utils.commands import MoveShapeCommand
from src.main.utils.feedback import FeedbackType
from src.main.utils.serializer import DiagramSerializer
from src.main.views.canvas_view import DiagramCanvas
from src.main.views.main_window import MainWindow
from src.main.views.properties_panel import PropertiesPanel
from src.main.views.selector_wheel import create_combobox


@pytest.fixture
def app(tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    with patch("src.main.controllers.app_controller.get_repository", return_value=repo):
        app = AppController()
    app.view = MagicMock()
    root = ComponentBox(200, 200)
    root.properties.update(node_type="Root", name="Original")
    child = ComponentBox(500, 200)
    child.properties.update(node_type="Leaf", name="Child")
    circle, diamond = ActionCircle(200, 500), DiamondStep(500, 500)
    app.diagram.shapes = [root, child, circle, diamond]
    app._persist_diagram()
    return app


@pytest.fixture(scope="module")
def tkroot():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def edit_name(app, name="Edited"):
    node = app.diagram.shapes[0]
    old = {"name": node.properties["name"], "text": node.text}
    assert app.apply_properties(node, old, {"name": name, "text": name})
    assert app.diagram.modified


@pytest.mark.parametrize("operation", ["new", "open", "load"])
@pytest.mark.parametrize("answer", ["discard", "cancel", "save"])
def test_confirmation_semantics_reopen_actual_storage(app, tmp_path, operation, answer):
    old_diagram = app.diagram
    root_id = app.current_product_id
    path = app.repository.file_path
    before = path.read_bytes()
    edit_name(app)
    # A callback queued by an earlier version must be cancelled before prompting.
    app.auto_save_timer = "pending"
    app.view.ask_save_changes.return_value = answer
    if operation == "open":
        target = Diagram()
        node = ComponentBox(100, 100)
        node.properties.update(node_type="Root", name="Opened")
        target.add_shape(node)
        file = tmp_path / "open.json"
        assert DiagramSerializer.save_to_file(target, str(file))
        app.view.ask_file_path.return_value = str(file)
        app.open_diagram()
    elif operation == "load":
        app.load_product_diagram(root_id)
    else:
        app.new_diagram()
    app.view.root.after_cancel.assert_called_once_with("pending")
    stored = JsonRepository(str(path)).get_product(root_id)
    assert stored["name"] == ("Edited" if answer == "save" else "Original")
    if answer != "save":
        assert path.read_bytes() == before
    if answer == "cancel":
        assert app.diagram is old_diagram
        assert app.diagram.shapes[0].properties["name"] == "Edited"
        assert app.diagram.modified
        app.view.ask_file_path.assert_not_called()
    else:
        assert not app.diagram.modified


def test_failed_yes_save_aborts_new(app):
    edit_name(app)
    app.view.ask_save_changes.return_value = "save"
    diagram = app.diagram
    with patch.object(app.repository, "save_diagram_snapshot", side_effect=OSError("disk full")):
        app.new_diagram()
    assert app.diagram is diagram and app.diagram.modified
    assert JsonRepository(str(app.repository.file_path)).get_product(app.current_product_id)["name"] == "Original"


def test_catalog_create_delete_is_independent_of_unsaved_project(app):
    edit_name(app)
    owner = app.diagram.diagram_id
    snapshot = copy.deepcopy(app.repository.get_diagram(owner))
    keys = [
        ("material", app.add_new_material("Persistent material")),
        ("color", app.add_new_color("Persistent color", "#112233", 17, 34, 51)),
        ("tool", app.add_new_tool("Persistent tool", "Driver")),
    ]
    reopened = JsonRepository(str(app.repository.file_path))
    for kind, key in keys:
        assert getattr(reopened, "get_" + kind)(key)
    assert reopened.get_diagram(owner) == snapshot
    assert app.diagram.modified
    for kind, key in keys:
        assert getattr(app, "delete_" + kind)(key)
    reopened = JsonRepository(str(app.repository.file_path))
    for kind, key in keys:
        assert getattr(reopened, "get_" + kind)(key) is None
    assert reopened.get_diagram(owner) == snapshot


@pytest.mark.parametrize("kind", ["material", "color", "tool"])
def test_delete_protects_unsaved_and_saved_reference_assignments(app, kind):
    key = (app.add_new_color("In use", "#123456", 18, 52, 86) if kind == "color"
           else app.add_new_tool("In use", "Driver") if kind == "tool"
           else app.add_new_material("In use"))
    node = app.diagram.shapes[3] if kind == "tool" else app.diagram.shapes[1]
    if kind == "tool":
        node.tool_id = key
    else:
        node.properties[kind + "_id"] = key
    with pytest.raises(ValueError, match="assigned"):
        getattr(app, "delete_" + kind)(key)
    app._persist_diagram()
    app.diagram = Diagram()
    with pytest.raises(ValueError, match="assigned"):
        getattr(app, "delete_" + kind)(key)
    assert getattr(JsonRepository(str(app.repository.file_path)), "get_" + kind)(key)


def test_delete_and_clear_only_persist_on_save(app):
    before = app.repository.file_path.read_bytes()
    node = app.diagram.shapes[1]
    app.diagram.select_shape(node)
    app.delete_selected()
    assert app.diagram.modified and app.repository.file_path.read_bytes() == before
    app.undo()
    assert node in app.diagram.shapes
    app.redo()
    app._persist_diagram()
    assert app.repository.get_component(node.properties["db_id"]) is None
    owner = app.diagram.diagram_id
    before = app.repository.file_path.read_bytes()
    with patch("tkinter.messagebox.askyesno", return_value=True):
        app.clear_canvas()
    assert app.diagram.diagram_id == owner and app.diagram.modified
    assert app.repository.file_path.read_bytes() == before
    app._persist_diagram()
    assert not app.diagram.modified
    assert app.repository.get_diagram(owner) is None
    assert JsonRepository(str(app.repository.file_path)).get_diagram(owner) is None
    with patch.object(app, "_get_next_shape_position", return_value=(200, 200)):
        app.add_shape("component_root")
    assert app.save_diagram()


def test_move_edit_connection_dirty_and_no_implicit_write(app):
    before = app.repository.file_path.read_bytes()
    node, child, circle, diamond = app.diagram.shapes
    app.command_history.execute(MoveShapeCommand(node, 20, 20, app.diagram))
    assert app.diagram.modified
    app.diagram.modified = False
    app._create_connection(node, diamond)
    assert app.diagram.modified
    app.diagram.modified = False
    app.diagram.remove_connection(app.diagram.connections[0])
    assert app.diagram.modified
    app.diagram.modified = False
    app._create_arrow_connection(diamond, circle)
    assert app.diagram.modified
    app.diagram.modified = False
    app.diagram.select_shape(app.diagram.shapes[-1])
    app.delete_selected()
    assert app.diagram.modified
    assert app.repository.file_path.read_bytes() == before
    app.diagram.modified = False
    assert app.apply_properties(circle, {"image_path": ""}, {"image_path": "new.png"})
    assert app.diagram.modified
    app._persist_diagram()
    assert not app.diagram.modified
    app.undo()
    assert app.diagram.modified


@pytest.mark.parametrize("shape_class", [ComponentBox, ActionCircle, DiamondStep])
@pytest.mark.parametrize("size", [(200, 100), (100, 200)])
def test_all_node_images_lifecycle(tkroot, tmp_path, shape_class, size):
    path = tmp_path / "node.png"
    Image.new("RGB", size, "red").save(path)
    canvas = DiagramCanvas(tkroot)
    node = shape_class(300, 300)
    node.text = "Readable node label"
    if isinstance(node, ComponentBox):
        node.properties["image_path"] = str(path)
    else:
        node.image_path = str(path)
    diagram = Diagram()
    diagram.shapes = [node]
    canvas.redraw_all(diagram)
    item, _, width, height, photo = canvas._component_images[node]
    pixels = photo._PhotoImage__photo
    red = [(x, y) for y in range(photo.height()) for x in range(photo.width())
           if pixels.get(x, y) == (255, 0, 0)]
    xs, ys = zip(*red)
    assert (max(xs)-min(xs)+1)/(max(ys)-min(ys)+1) == pytest.approx(size[0]/size[1], rel=.05)
    assert canvas.bbox(item)[3] <= canvas.bbox(canvas._canvas_items[node]['text'])[1]
    for selected in (True, False):
        node.selected = selected
        canvas.draw_shape(node)
        assert sum(canvas.type(i) == "image" for i in canvas.find_all()) == 1
    before = canvas.coords(canvas._component_images[node][0])
    node.move(15, 20)
    canvas.move_items(node, 15, 20)
    assert canvas.coords(canvas._component_images[node][0]) == pytest.approx([before[0]+15, before[1]+20])
    canvas._apply_zoom(2, 0, 0)
    diagram = Diagram.from_dict(diagram.to_dict())
    canvas.redraw_all(diagram)
    assert sum(canvas.type(i) == "image" for i in canvas.find_all()) == 1
    canvas.configure(width=900, height=600)
    canvas.redraw_all(diagram)
    assert len(canvas._component_images) == 1
    node = diagram.shapes[0]
    if isinstance(node, ComponentBox):
        node.properties["image_path"] = ""
    else:
        node.image_path = ""
    canvas.draw_shape(node)
    assert not canvas._component_images


@pytest.mark.parametrize("shape_class", [ActionCircle, DiamondStep])
def test_missing_image_falls_back(tkroot, tmp_path, shape_class):
    canvas = DiagramCanvas(tkroot)
    node = shape_class(300, 300)
    node.image_path = str(tmp_path / "missing.png")
    canvas.draw_shape(node)
    assert not canvas._component_images
    assert canvas.type(canvas._canvas_items[node]['body']) in ("oval", "polygon")


def test_connection_selection_has_no_form(tkroot, app):
    panel = PropertiesPanel(tkroot, data_provider=CatalogController(app.repository))
    panel.load_shape(app.diagram.shapes[0])
    for edge in (ArrowShape(0, 0), Connection(*app.diagram.shapes[:2]), None):
        panel.load_shape(edge)
        assert not panel.apply_button.grid_info()
        assert not panel.properties_frame.grid_info()
        assert not panel.image_preview_frame.grid_info()
    panel.load_shape(app.diagram.shapes[0])
    assert panel.apply_button.grid_info() and panel.dynamic_fields


def test_popup_wheel_scrolls_without_selecting(tkroot):
    tkroot.deiconify()
    widget = create_combobox(tkroot, values=tuple(f"Option {i}" for i in range(80)), state="readonly")
    widget.pack()
    widget.current(0)
    tkroot.update()
    widget.tk.call("ttk::combobox::Post", str(widget))
    tkroot.update()
    listing = str(widget.tk.call("ttk::combobox::PopdownWindow", str(widget))) + ".f.l"
    selected = widget.tk.call(listing, "curselection")
    before = widget.tk.call(listing, "yview")
    widget.tk.call("event", "generate", listing, "<MouseWheel>", "-delta", -120)
    tkroot.update()
    assert widget.tk.call(listing, "yview") != before
    assert widget.get() == "Option 0"
    assert widget.tk.call(listing, "curselection") == selected
    x, y, w, h = map(int, widget.tk.call(listing, "bbox", 4))
    for event in ("<Motion>", "<ButtonPress-1>", "<ButtonRelease-1>"):
        widget.tk.call("event", "generate", listing, event, "-x", x+2, "-y", y+h//2)
    tkroot.update()
    assert widget.get() == "Option 4"


def test_feedback_resets_colors_in_compact_bottom_bar(tkroot):
    controller = MagicMock()
    controller.diagram.shapes = []
    window = MainWindow(tkroot, controller)
    tkroot.deiconify()
    for resolution in ("800x600", "1280x720"):
        tkroot.geometry(resolution)
        tkroot.update()
        height = window.status_bar.winfo_height()
        for kind in (FeedbackType.ERROR, FeedbackType.SUCCESS, FeedbackType.WARNING, FeedbackType.INFO):
            window.set_status("Visible feedback " * 15, kind)
            tkroot.update()
            assert window.status_bar.winfo_height() == height < 35
            assert window.status_bar.winfo_rooty() >= window.paned_window.winfo_rooty() + window.paned_window.winfo_height()
            assert str(window.status_label.cget("foreground")) == {
                FeedbackType.ERROR: "red", FeedbackType.SUCCESS: "#176534",
                FeedbackType.WARNING: "#855600", FeedbackType.INFO: "black"}[kind]
    window.show_error("Error", "Failed")
    window.set_status("Normal message")
    assert str(window.status_label.cget("foreground")) == "black"


@pytest.mark.parametrize("mode", ["arrow", "connection"])
def test_rejected_connection_keeps_error_feedback(app, mode):
    source, _, target, _ = app.diagram.shapes
    app.connecting_from = source
    with patch("tkinter.messagebox.showerror"):
        if mode == "arrow":
            app._handle_arrow_connection_click(target)
        else:
            app._handle_connection_click(target)
    assert app.view.set_status.call_args.args[1] == FeedbackType.ERROR
    assert not app.diagram.connections
    assert not any(isinstance(node, ArrowShape) for node in app.diagram.shapes)


def test_drag_dirty_and_undo_track_each_snapped_node(app):
    from types import SimpleNamespace
    a, b = app.diagram.shapes[:2]
    app.diagram.snap_to_grid = False
    app.dragging = True
    app.drag_shapes = [a, b]
    app.drag_initial_positions = {a: (a.x, a.y), b: (b.x, b.y)}
    old = (b.x, b.y)
    b.move(7, 11)
    app.on_canvas_release(SimpleNamespace(x=0, y=0))
    assert app.diagram.modified
    app.undo()
    assert (b.x, b.y) == old
