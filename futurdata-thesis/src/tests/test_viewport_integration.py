import tkinter as tk
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from src.main.views.canvas_view import DiagramCanvas
from src.main.views.properties_panel import PropertiesPanel
from src.main.models import Diagram, ComponentBox, Connection
from src.main.controllers.app_controller import AppController


@pytest.fixture
def root():
    root = tk.Tk()
    root.geometry("800x600")
    yield root
    root.destroy()


def test_zoom_preserves_model_and_cursor_and_connections(root):
    canvas = DiagramCanvas(root, width=500, height=400)
    canvas.pack(fill="both", expand=True)
    diagram = Diagram()
    a, b = ComponentBox(300, 300), ComponentBox(600, 600)
    diagram.shapes = [a, b]
    connection = Connection(a, b)
    diagram.connections = [connection]
    canvas.redraw_all(diagram)
    root.update()
    before = diagram.to_dict()
    canvas.xview_moveto(.15)
    canvas.yview_moveto(.15)
    anchor = canvas.model_x(200), canvas.model_y(150)
    canvas._apply_zoom(2, 200, 150)
    assert (canvas.model_x(200), canvas.model_y(150)) == pytest.approx(anchor, abs=1)
    assert diagram.to_dict() == before
    restored = Diagram.from_dict(diagram.to_dict())
    assert [(s.x, s.y) for s in restored.shapes] == [(s.x, s.y) for s in diagram.shapes]
    a.move(25, 30)
    canvas.move_items(a, 25, 30)
    canvas.update_connections_for_shapes([a], diagram)
    expected = [v * 2 for point in connection.get_endpoints() for v in point]
    assert canvas.coords(canvas._connection_items[connection]) == pytest.approx(expected)
    canvas.redraw_all(diagram)
    assert canvas.coords(canvas._canvas_items[a]['body']) == pytest.approx([v * 2 for v in a.get_bounds()])
    canvas._apply_zoom(100)
    assert canvas.zoom_factor == 4
    canvas._apply_zoom(.001)
    assert canvas.zoom_factor == .25
    canvas.reset_zoom()
    assert canvas.coords(canvas._canvas_items[a]['body']) == pytest.approx(a.get_bounds())


def test_controller_drag_uses_model_coordinates(root):
    canvas = DiagramCanvas(root)
    canvas.pack(fill="both", expand=True)
    diagram = Diagram()
    shape = ComponentBox(200, 200)
    diagram.shapes = [shape]
    canvas.redraw_all(diagram)
    root.update()
    canvas._apply_zoom(2, 0, 0)
    controller = AppController.__new__(AppController)
    controller.view = SimpleNamespace(canvas=canvas)
    controller.diagram = diagram
    controller.dragging = True
    controller.drag_shapes = [shape]
    controller.drag_start = (200, 200)
    controller._auto_scroll_viewport = lambda *args: None
    controller.on_canvas_drag(SimpleNamespace(x=440, y=420))
    assert (shape.x, shape.y) == pytest.approx((220, 210))
    assert canvas.coords(canvas._canvas_items[shape]['body']) == pytest.approx([v * 2 for v in shape.get_bounds()])


def test_properties_content_scrolls_without_growing_panel(root):
    panel = PropertiesPanel(root, data_provider=MagicMock())
    panel.pack(fill="both", expand=True)
    panel.properties_frame.grid(row=4, column=0, sticky="ew")
    root.update()
    requested = panel.winfo_reqwidth(), panel.winfo_reqheight()
    for row in range(30):
        panel._create_field_widget(panel.properties_frame, dict(name="description", type="TEXT", display_name="Description"), row, "material " * 100)
    root.update()
    assert (panel.winfo_reqwidth(), panel.winfo_reqheight()) == requested
    assert panel.content.winfo_height() > panel.viewport.winfo_height()
    assert panel.content.winfo_width() == panel.viewport.winfo_width()
    before = panel.viewport.yview()
    for target in (panel, panel.content, panel.viewport, panel.properties_frame):
        for delta in (-120, 120):
            target.event_generate("<MouseWheel>", delta=delta)
            root.update()
            assert panel.viewport.yview() == before
    scrollbar = next(child for child in panel.winfo_children()
                     if child.winfo_class() == 'TScrollbar')
    panel.tk.call(*panel.tk.splitlist(scrollbar.cget('command')), 'moveto', 1)
    assert panel.viewport.yview()[0] > 0


def test_main_window_remains_usable_at_different_sizes(root):
    from src.main.views.main_window import MainWindow
    controller = MagicMock()
    window = MainWindow(root, controller)
    for width, height in ((640, 480), (1024, 768), (1400, 800)):
        root.geometry(f"{width}x{height}")
        root.update()
        assert window.canvas.winfo_width() > 100
        assert window.canvas.winfo_height() > 100
        assert window.properties_panel.winfo_width() > 200
        toolbar = window.snap_btn.master
        for control in toolbar.winfo_children():
            assert control.winfo_x() + control.winfo_width() <= toolbar.winfo_width()
            assert control.winfo_y() + control.winfo_height() <= toolbar.winfo_height()
