"""Behavioral protection for MVC refresh, Apply, and rendering."""
import copy
import tkinter as tk
from unittest.mock import MagicMock, patch
import pytest
from src.main.controllers.app_controller import AppController
from src.main.controllers.catalog_controller import CatalogController
from src.main.models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape, Connection
from src.main.repositories.json_repository import JsonRepository
from src.main.utils.commands import CommandHistory, EditShapePropertiesCommand
from src.main.views.canvas_view import DiagramCanvas
from src.main.views.properties_panel import PropertiesPanel

@pytest.fixture(scope='module')
def root():
    widget = tk.Tk()
    widget.withdraw()
    yield widget
    widget.destroy()

@pytest.mark.parametrize("kind", [ComponentBox, ActionCircle, DiamondStep])
def test_edit_undo_refresh_redo_refresh(root, tmp_path, kind):
    repo = JsonRepository(str(tmp_path / "store.json"))
    shape = kind(100, 100)
    key = "text" if kind is ActionCircle else "name"
    if kind is ComponentBox:
        shape.properties["name"] = "Old"
    else:
        setattr(shape, key, "Old")
    diagram = Diagram()
    diagram.shapes.append(shape)
    history = CommandHistory()
    panel = PropertiesPanel(root, data_provider=CatalogController(repo))
    history.execute(EditShapePropertiesCommand(shape, {key: "Old"}, {key: "New"}, diagram))
    for action, expected in [(history.undo, "Old"), (history.redo, "New")]:
        action()
        before = copy.deepcopy(shape.__dict__)
        with patch.object(repo, "get_component", side_effect=AssertionError("persisted refresh")), patch.object(repo, "get_action", side_effect=AssertionError("persisted refresh")), patch.object(repo, "get_step", side_effect=AssertionError("persisted refresh")):
            panel.load_shape(shape)
            panel.refresh()
        assert shape.__dict__ == before
        assert (shape.properties[key] if kind is ComponentBox else getattr(shape, key)) == expected

def test_apply_only_proposes_until_controller_executes(root, tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    with patch("src.main.controllers.app_controller.get_repository", return_value=repo):
        controller = AppController()
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(100, 100)
    shape.properties["name"] = shape.text = "Old"
    controller.diagram.shapes.append(shape)
    observed = []
    def apply(node, old, proposed):
        assert node.properties["name"] == node.text == "Old"
        observed.append(proposed)
        return controller.apply_properties(node, old, proposed)
    panel = PropertiesPanel(root, data_provider=CatalogController(repo), on_apply_callback=apply)
    panel.load_shape(shape)
    panel.dynamic_fields["name"].delete("1.0", "end")
    panel.dynamic_fields["name"].insert("1.0", "New")
    panel._on_apply()
    assert len(observed) == len(controller.command_history.history) == 1
    assert shape.properties["name"] == shape.text == "New"
    controller.undo()
    assert shape.properties["name"] == shape.text == "Old"

@pytest.mark.parametrize("dirty", [False, True])
def test_redraw_zoom_and_arrows_preserve_entire_model(root, dirty):
    diagram = Diagram()
    a, b = ComponentBox(100, 100), DiamondStep(100, 100)
    a.text = "Long label " + "W" * 250
    arrow = ArrowShape(0, 0)
    arrow.from_shape, arrow.to_shape = a, b
    diagram.shapes = [a, b, arrow]
    diagram.connections = [Connection(a, b)]
    diagram.modified = dirty
    before = copy.deepcopy(diagram.to_dict())
    states = [copy.deepcopy(s.__dict__) for s in (a, b)]
    arrow_state = dict(arrow.__dict__)
    canvas = DiagramCanvas(root)
    for _ in range(2):
        canvas.redraw_all(diagram)
        canvas.zoom_in()
        canvas.reset_zoom()
        assert diagram.to_dict() == before
        assert [s.__dict__ for s in (a, b)] == states
        assert arrow.__dict__ == arrow_state
        assert diagram.modified is dirty


def test_invalid_apply_does_not_mutate_and_controller_captures_old_state(tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    controller = AppController(repository=repo)
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(100, 100)
    shape.properties["name"] = shape.text = "Old"
    controller.diagram.shapes.append(shape)
    before = copy.deepcopy(shape.__dict__)
    assert not controller.apply_properties(shape, {"name": "Spoofed"}, {"weight": "invalid"})
    assert shape.__dict__ == before
    assert not controller.diagram.modified
    assert not controller.command_history.history
    assert controller.apply_properties(shape, {"name": "Spoofed"}, {"name": "New"})
    controller.undo()
    assert shape.properties["name"] == "Old"


def test_new_dynamic_property_and_mutable_command_values_undo(tmp_path):
    shape = ComponentBox(0, 0)
    diagram = Diagram()
    controller = AppController(repository=JsonRepository(str(tmp_path / "store.json")))
    controller.diagram = diagram
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    diagram.shapes.append(shape)
    proposed = {"extra_schema_field": ["one"], "hex_code": "#ffffff"}
    assert controller.apply_properties(shape, {}, proposed)
    proposed["extra_schema_field"].append("two")
    assert shape.properties["extra_schema_field"] == ["one"]
    controller.undo()
    assert "extra_schema_field" not in shape.properties
    assert "hex_code" not in shape.properties
    controller.redo()
    assert shape.properties["extra_schema_field"] == ["one"]


def test_image_paths_are_read_only_and_apply_manages_attachment(tmp_path):
    from PIL import Image
    from src.main.utils.image_handler import ImageHandler
    handler = ImageHandler(str(tmp_path / "managed"))
    assert not __import__("pathlib").Path(handler.images_dir).exists()
    handler.get_full_path("images/missing.png")
    handler.image_exists("images/missing.png")
    assert not __import__("pathlib").Path(handler.images_dir).exists()
    source = tmp_path / "source.png"
    Image.new("RGB", (20, 20), "blue").save(source)
    repo = JsonRepository(str(tmp_path / "store.json"))
    controller = AppController(repository=repo, image_handler=handler)
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(100, 100)
    controller.diagram.shapes.append(shape)
    with patch.object(handler, "upload_image", wraps=handler.upload_image) as upload:
        assert controller.apply_properties(shape, {}, {"image_path": str(source)})
        upload.assert_called_once()
    stored = shape.properties["image_path"]
    assert stored.startswith("images/") and handler.image_exists(stored)
    controller.undo()
    assert shape.properties["image_path"] == ""
    controller.redo()
    assert shape.properties["image_path"] == stored


def test_arrow_read_queries_are_nonmutating():
    a, b = ComponentBox(100, 100), DiamondStep(300, 100)
    arrow = ArrowShape(0, 0, a, b)
    a.move(0, 300)
    before = dict(arrow.__dict__)
    arrow.get_bounds()
    arrow.get_connection_points()
    arrow.contains_point(100, 200)
    assert arrow.__dict__ == before


def test_workflow_validation_imports_without_tkinter():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-B", "-c",
        "import sys; from src.main.services.workflow_validation import connection_error; "
        "from src.main.models import ComponentBox, ActionCircle, DiamondStep; "
        "assert 'tkinter' not in sys.modules; "
        "assert connection_error(ComponentBox(0,0), ActionCircle(0,0)); "
        "assert connection_error(DiamondStep(0,0), DiamondStep(0,0)); "
        "assert connection_error(ComponentBox(0,0), DiamondStep(0,0)) is None"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_render_hit_testing_anchors_and_multiple_canvas_ownership(root):
    diagram = Diagram()
    a, b = ComponentBox(100, 100), DiamondStep(100, 100)
    a.text = "W" * 300
    edge = Connection(a, b)
    diagram.shapes = [a, b]
    diagram.connections = [edge]
    before = copy.deepcopy(diagram.to_dict())
    first, second = DiagramCanvas(root), DiagramCanvas(root)
    first.redraw_all(diagram)
    second.redraw_all(diagram)
    rendered = first.render_shape(b)
    assert first.find_shape_at_point(diagram, rendered.x, rendered.y) is b
    points = [v for point in first.render_endpoints(edge) for v in point]
    assert first.coords(first._connection_items[edge]) == pytest.approx(points)
    first.clear_canvas()
    assert second._canvas_items[b]['body'] in second.find_all()
    assert diagram.to_dict() == before
    assert not hasattr(a, "shape_id") and not hasattr(a, "text_id")
    assert not hasattr(edge, "arrow_id")


def test_negative_imported_geometry_survives_zoom(root):
    diagram = Diagram()
    shape = ComponentBox(-500, -500)
    diagram.shapes = [shape]
    canvas = DiagramCanvas(root)
    canvas.redraw_all(diagram)
    before = copy.deepcopy(diagram.to_dict())
    canvas.zoom_in()
    region = list(map(float, canvas.tk.splitlist(canvas.cget("scrollregion"))))
    assert region[0] < 0 and region[1] < 0
    assert diagram.to_dict() == before


@pytest.mark.parametrize("source", [ComponentBox, ActionCircle, DiamondStep, ArrowShape])
@pytest.mark.parametrize("target", [ComponentBox, ActionCircle, DiamondStep, ArrowShape])
def test_workflow_characterizes_existing_rules(source, target):
    from src.main.services.workflow_validation import connection_error
    rejected = (source, target) in {(ComponentBox, ActionCircle), (DiamondStep, DiamondStep)}
    assert (connection_error(source(0, 0), target(0, 0)) is not None) == rejected


def test_attachment_failure_leaves_model_and_history_unchanged(tmp_path):
    from PIL import Image
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10)).save(source)
    handler = MagicMock()
    handler.upload_image.side_effect = OSError("disk full")
    controller = AppController(repository=JsonRepository(str(tmp_path / "store.json")), image_handler=handler)
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(0, 0)
    controller.diagram.shapes.append(shape)
    before = copy.deepcopy(shape.__dict__)
    assert not controller.apply_properties(shape, {}, {"image_path": str(source)})
    assert shape.__dict__ == before and not controller.diagram.modified
    assert not controller.command_history.history


def test_failed_save_restores_ids_titles_and_dirty_state(tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    controller = AppController(repository=repo)
    controller.view = MagicMock()
    root, instruction, operation = ComponentBox(100, 100), ActionCircle(100, 300), DiamondStep(300, 100)
    root.properties.update(node_type="Root", name="Machine")
    instruction.text = ""
    operation.name = operation.text = ""
    operation.tools = "Legacy tool"
    controller.diagram.shapes = [root, instruction, operation]
    controller.diagram.modified = True
    before = copy.deepcopy(controller.diagram.to_dict())
    with patch.object(repo, "save_diagram_snapshot", side_effect=OSError("disk full")):
        assert not controller.save_diagram()
    assert controller.diagram.to_dict() == before
    assert controller.diagram.modified and controller.current_product_id is None
    assert repo.get_all_products() == []


from pathlib import Path
PROJECTS = list((Path(__file__).resolve().parents[2] / "use-cases").rglob("*.zip"))

@pytest.mark.parametrize("project", PROJECTS, ids=lambda path: path.stem)
def test_available_bundled_project_import_and_redraw(root, tmp_path, project):
    import zipfile
    from src.main.utils.json_exporter import EnhancedJSONExporter
    from src.main.controllers.navigator import topology_snapshot, build_outline
    with zipfile.ZipFile(project) as archive:
        files = [name for name in archive.namelist() if name.endswith(".json")]
        selected = next((name for name in files if name.endswith("diagram.json")), files[0])
        source = tmp_path / "project.json"
        source.write_bytes(archive.read(selected))
    importer = EnhancedJSONExporter(JsonRepository(str(tmp_path / "store.json")))
    diagram = importer.import_diagram(str(source), create_in_repository=False)
    assert diagram is not None
    before = copy.deepcopy(diagram.to_dict())
    canvas = DiagramCanvas(root)
    canvas.redraw_all(diagram)
    assert diagram.to_dict() == before
    rows = build_outline(topology_snapshot(diagram))
    assert {row.shape_id for row in rows} >= {s.id for s in diagram.shapes if not isinstance(s, ArrowShape)}
    restored = Diagram.from_dict(before)
    assert [s.to_dict() for s in restored.shapes] == before["shapes"]


def test_save_then_undo_refresh_retains_owned_record_ids(root, tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    controller = AppController(repository=repo)
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(100, 100)
    shape.properties.update(node_type="Root", name="Old")
    shape.text = "Old"
    controller.diagram.shapes.append(shape)
    panel = PropertiesPanel(root, data_provider=controller.catalog, on_apply_callback=controller.apply_properties)
    panel.load_shape(shape)
    panel.dynamic_fields["name"].delete("1.0", "end")
    panel.dynamic_fields["name"].insert("1.0", "New")
    panel._on_apply()
    assert controller.save_diagram()
    owned = shape.properties["db_id"]
    controller.undo()
    panel.load_shape(shape)
    assert shape.properties["name"] == shape.text == "Old"
    assert shape.properties["db_id"] == owned
    assert repo.get_product(owned)["name"] == "New"
    assert controller.save_diagram()
    assert repo.get_product(owned)["name"] == "Old"
    assert len(repo.get_all_products()) == 1


def test_noop_apply_does_not_dirty_or_add_history(tmp_path):
    controller = AppController(repository=JsonRepository(str(tmp_path / "store.json")))
    controller.view = MagicMock()
    controller._update_view = MagicMock()
    shape = ComponentBox(100, 100)
    assert controller.apply_properties(shape, {}, {"text": shape.text, "db_id": 123, "node_type": "Root"})
    assert not controller.diagram.modified and not controller.command_history.history
    assert "db_id" not in shape.properties and shape.properties["node_type"] == ""
