"""Topology, native Tk selection, viewport navigation, and refresh regressions."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import copy
import zipfile
from pathlib import Path
import tkinter as tk
import pytest

from src.main.models import Diagram, ComponentBox, DiamondStep, ActionCircle, ArrowShape, Connection
from src.main.controllers.navigator import topology_snapshot, build_outline
from src.main.controllers.app_controller import AppController
from src.main.views.navigator import Navigator
from src.main.views.canvas_view import DiagramCanvas
from src.main.utils.commands import CommandHistory, AddShapeCommand, RemoveShapeCommand, AddConnectionCommand


def graph():
    diagram = Diagram()
    root = ComponentBox(500, 500)
    root.properties.update(name='Machine', node_type='Root')
    operation = DiamondStep(1000, 900)
    operation.name = 'Remove housing'
    left, right = ComponentBox(1500, 1200), ComponentBox(2500, 2400)
    left.properties['name'] = right.properties['name'] = 'Screw'
    instruction, next_instruction = ActionCircle(1600, 1800), ActionCircle(1600, 2200)
    diagram.shapes = [right, instruction, root, operation, left, next_instruction]
    pairs = [(root, operation), (operation, left), (operation, right),
             (operation, instruction), (instruction, next_instruction)]
    diagram.connections = [Connection(a, b) for a, b in pairs]
    return diagram, (root, operation, left, right, instruction, next_instruction)


def test_topology_mixed_edges_roots_labels_and_coordinate_independence():
    diagram, (root, operation, left, right, instruction, last) = graph()
    diagram.add_shape(ArrowShape(0, 0, root, operation))  # duplicate representation
    diagram.add_shape(ArrowShape(0, 0, left, right))      # shared node
    orphan = ComponentBox(-1000, -1000)
    diagram.add_shape(orphan)
    diagram.add_connection(Connection(last, root))      # cycle
    diagram.add_connection(Connection(root, ComponentBox(0, 0)))  # dangling
    arrow = ArrowShape(0, 0)
    diagram.add_shape(arrow)
    snapshot = topology_snapshot(diagram)
    rows = build_outline(snapshot)
    assert len(snapshot[1]) == 7
    assert {row.shape_id for row in rows} == {s.id for s in diagram.shapes if not isinstance(s, ArrowShape)} | {arrow.id}
    assert any('[cycle]' in row.label for row in rows)
    assert any('[reference]' in row.label for row in rows)
    by_id = {row.item_id: row for row in rows}
    assert by_id[f'node:{operation.id}'].parent_id == f'node:{root.id}'
    assert 'Operation (diamond)' in by_id[f'node:{operation.id}'].label
    assert 'Instruction (circle)' in by_id[f'node:{instruction.id}'].label
    assert by_id[f'node:{orphan.id}'].parent_id == ''
    for shape in diagram.shapes:
        shape.x, shape.y = -shape.y, shape.x * 7
    assert topology_snapshot(diagram) == snapshot
    assert build_outline(snapshot) == rows


def test_topological_roots_order_and_deep_graph():
    diagram, nodes = graph()
    rows = build_outline(topology_snapshot(diagram))
    assert rows[0].shape_id == nodes[0].id
    assert [row.shape_id for row in rows if row.parent_id == f'node:{nodes[1].id}'] == [nodes[2].id, nodes[3].id, nodes[4].id]
    diagram = Diagram()
    diagram.shapes = [ActionCircle(0, 0) for _ in range(2500)]
    diagram.connections = [Connection(a, b) for a, b in zip(diagram.shapes, diagram.shapes[1:])]
    diagram.connections.append(Connection(diagram.shapes[-1], diagram.shapes[0]))
    assert len(build_outline(topology_snapshot(diagram))) == 2501


@pytest.fixture(scope='module')
def root():
    root = tk.Tk()
    root.geometry('900x650')
    yield root
    root.destroy()


@pytest.fixture
def app(root):
    controller = AppController.__new__(AppController)
    controller.diagram, nodes = graph()
    controller.command_history = CommandHistory()
    controller.arrow_mode = controller.connect_mode = controller.dragging = False
    controller.preview_line_id = None
    canvas = DiagramCanvas(root, width=500, height=400)
    canvas.pack(side='right', fill='both', expand=True)
    navigator = Navigator(root, controller.navigate_to_shape)
    navigator.pack(side='left', fill='y')
    view = SimpleNamespace(canvas=canvas, navigator=navigator, root=root,
                           update_properties_panel=MagicMock(), update_ui_state=MagicMock(), set_status=MagicMock())
    controller.view = view
    canvas.update_scroll_region_from_shapes(controller.diagram.shapes)
    canvas.redraw_all(controller.diagram)
    controller._sync_navigator()
    root.update()
    yield controller, nodes
    navigator.destroy()
    canvas.destroy()
    root.update()


@pytest.mark.parametrize('zoom', [.5, .75, .83, 1, 1.25, 1.5, 2])
def test_navigator_selects_centers_without_mutating_geometry_or_zoom(app, root, zoom):
    controller, nodes = app
    canvas, nav = controller.view.canvas, controller.view.navigator
    canvas._apply_zoom(zoom / canvas.zoom_factor)
    before = [(s.id, s.x, s.y) for s in controller.diagram.shapes]
    node = nodes[2]  # interior node, same name as another shape with a different ID
    nav.tree.selection_set(f'node:{node.id}')
    root.update()
    assert controller.diagram.selected_shapes == [node]
    controller.view.update_properties_panel.assert_called_with(node)
    assert canvas.zoom_factor == zoom
    assert [(s.id, s.x, s.y) for s in controller.diagram.shapes] == before
    assert canvas.canvasx(canvas.winfo_width() / 2) == pytest.approx(node.x * zoom, abs=2)
    assert canvas.canvasy(canvas.winfo_height() / 2) == pytest.approx(node.y * zoom, abs=2)
    assert nav.tree.item(f'node:{nodes[0].id}', 'open')
    assert nav.tree.item(f'node:{nodes[1].id}', 'open')
    with patch.object(controller, 'navigate_to_shape') as navigate:
        nav.on_select = navigate
        controller._sync_navigator()
        root.update()
        navigate.assert_not_called()


def test_canvas_click_sync_and_structural_updates_without_drag_rebuild(app, root):
    controller, nodes = app
    canvas, nav = controller.view.canvas, controller.view.navigator
    node = nodes[2]
    canvas.center_on_shape(node)
    event = SimpleNamespace(x=node.x * canvas.zoom_factor - canvas.canvasx(0),
                            y=node.y * canvas.zoom_factor - canvas.canvasy(0), state=0)
    with patch.object(nav, 'show_rows', wraps=nav.show_rows) as rebuild:
        controller.on_canvas_click(event)
        root.update()
        assert nav.tree.selection() == (f'node:{node.id}',)
        rebuild.assert_not_called()
        controller.on_canvas_drag(SimpleNamespace(x=event.x + 20, y=event.y + 10))
        rebuild.assert_not_called()
        controller.diagram.snap_to_grid = False
        controller.on_canvas_release(event)
        rebuild.assert_not_called()
        node.properties['name'] = 'Renamed'
        controller._update_view()
        assert 'Renamed' in nav.tree.item(f'node:{node.id}', 'text')
        assert rebuild.call_count == 1
        controller.command_history.execute(RemoveShapeCommand(controller.diagram, node))
        controller._update_view()
        assert node.id not in nav.shape_items
        controller.undo()
        assert node.id in nav.shape_items
        controller.redo()
        assert node.id not in nav.shape_items
        extra = ComponentBox(1200, 1000)
        controller.command_history.execute(AddShapeCommand(controller.diagram, extra))
        controller._update_view()
        assert nav.tree.parent(f'node:{extra.id}') == ''
        edge = Connection(nodes[1], extra)
        controller.command_history.execute(AddConnectionCommand(controller.diagram, edge))
        controller._update_view()
        assert nav.tree.parent(f'node:{extra.id}') == f'node:{nodes[1].id}'
        controller.undo()
        assert nav.tree.parent(f'node:{extra.id}') == ''
        controller.diagram.clear()
        controller._update_view()
        root.update()
        assert not nav.tree.get_children('')


def test_reference_selection_and_new_project_with_reused_ids(app, root):
    controller, nodes = app
    nav = controller.view.navigator
    controller.diagram.add_connection(Connection(nodes[2], nodes[3]))
    controller._sync_navigator()
    reference = nav.shape_items[nodes[3].id][-1]
    nav.tree.selection_set(reference)
    root.update()
    assert controller.diagram.selected_shapes == [nodes[3]]
    assert nav.tree.selection() == (reference,)
    controller.diagram = Diagram.from_dict(controller.diagram.to_dict())
    controller._update_view()
    root.update()
    assert not nav.tree.selection()


def test_center_clamps_at_edges_and_supports_negative_coordinates(app):
    controller, nodes = app
    canvas = controller.view.canvas
    node = nodes[0]
    for x, y in [(0, 0), (-500, -500), (5000, 5000)]:
        node.x, node.y = x, y
        canvas.redraw_all(controller.diagram)
        canvas.center_on_shape(node)
        assert (node.x, node.y) == (x, y)
        rendered = canvas.render_shape(node)
        assert canvas.canvasx(0) <= rendered.x * canvas.zoom_factor <= canvas.canvasx(canvas.winfo_width())
        assert canvas.canvasy(0) <= rendered.y * canvas.zoom_factor <= canvas.canvasy(canvas.winfo_height())


def test_bundled_projects_project_every_node_and_preserve_data(tmp_path):
    from src.main.utils.json_exporter import EnhancedJSONExporter
    from src.main.repositories.json_repository import JsonRepository
    repository = JsonRepository(str(tmp_path / 'repository.json'))
    importer = EnhancedJSONExporter(repository)
    projects = list((Path(__file__).resolve().parents[2] / 'use-cases').rglob('*.zip'))
    assert len(projects) >= 12
    for path in projects:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith('.json')]
            name = next((name for name in names if name.endswith('diagram.json')), names[0])
            project_json = tmp_path / 'project.json'
            project_json.write_bytes(archive.read(name))
        diagram = importer.import_diagram(str(project_json), create_in_repository=False)
        assert diagram is not None, path
        before = copy.deepcopy([shape.to_dict() for shape in diagram.shapes])
        rows = build_outline(topology_snapshot(diagram))
        assert {row.shape_id for row in rows} >= {shape.id for shape in diagram.shapes if not isinstance(shape, ArrowShape)}, path
        assert before == [shape.to_dict() for shape in diagram.shapes]


def test_tabbed_sidebar_stays_responsive_with_long_names(root):
    from src.main.views.main_window import MainWindow
    controller = MagicMock()
    window = MainWindow(root, controller)
    diagram, nodes = graph()
    nodes[0].properties['name'] = 'Very long node name ' * 50
    window.navigator.show_rows(build_outline(topology_snapshot(diagram)))
    assert [window.sidebar_tabs.tab(tab, 'text') for tab in window.sidebar_tabs.tabs()] == ['Shapes', 'Navigator']
    for width, height in ((640, 480), (1024, 768), (1400, 800)):
        root.geometry(f'{width}x{height}')
        for tab in window.sidebar_tabs.tabs():
            window.sidebar_tabs.select(tab)
            root.update()
            assert window.canvas.winfo_width() > 100
            assert window.properties_panel.winfo_width() > 200
            assert window.navigator.winfo_reqwidth() < 250
    window.sidebar_tabs.select(window.navigator)
    root.update()
    assert window.navigator.tree.xview()[1] < 1
    window.paned_window.sashpos(0, 240)
    root.update()
    assert window.sidebar_tabs.winfo_width() >= 230
    for child in root.winfo_children():
        child.destroy()


def test_click_selected_row_recenters_after_manual_pan(app, root):
    controller, nodes = app
    navigator, canvas = controller.view.navigator, controller.view.canvas
    node = nodes[0]
    controller.navigate_to_shape(node.id)
    root.update()
    canvas.xview_moveto(.8)
    canvas.yview_moveto(.8)
    x, y, width, height = navigator.tree.bbox(f'node:{node.id}')
    with patch.object(canvas, 'center_on_shape', wraps=canvas.center_on_shape) as center:
        navigator.tree.event_generate('<Button-1>', x=x + 30, y=y + height // 2)
        root.update()
        center.assert_called_once_with(node)
