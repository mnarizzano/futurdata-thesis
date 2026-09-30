"""Integrity regression tests using isolated repositories and real converters."""
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import zipfile
import pytest
from PIL import Image
from src.main.controllers.app_controller import AppController
from src.main.models import Diagram, ComponentBox, ActionCircle, DiamondStep, ArrowShape
from src.main.repositories import JsonRepository
from src.main.repositories.migration import OWNED
from src.main.services.archive_service import ProjectArchiveService
from src.main.services.document_export_service import DocumentExportService
from src.main.utils.diagram_loader import DiagramLoader
from src.main.utils.image_handler import ImageHandler
from src.main.utils.json_exporter import EnhancedJSONExporter
from src.main.loader_se.disassembly_loader import build_guide


def graph():
    diagram = Diagram()
    root = ComponentBox(100, 50)
    root.text = "Machine"
    root.properties.update(name="Machine", node_type="Root")
    step = ActionCircle(300, 150)
    step.text = "Remove screws"
    action = DiamondStep(100, 150)
    action.text = action.name = "Open housing"
    leaf = ComponentBox(100, 300)
    leaf.text = "Housing"
    leaf.properties.update(name="Housing", node_type="Leaf", material_id=2, color_id=3)
    diagram.shapes.extend((root, step, action, leaf))
    for source, target in ((root, action), (action, step), (action, leaf)):
        diagram.shapes.append(ArrowShape(0, 0, source, target))
    return diagram


def controller(repo, diagram):
    with patch("src.main.controllers.app_controller.get_repository", return_value=repo):
        app = AppController()
    app.view = MagicMock()
    app.diagram = diagram
    return app


@pytest.fixture
def setup(tmp_path, monkeypatch):
    repo = JsonRepository(str(tmp_path / "store.json"))
    handler = ImageHandler(str(tmp_path / "assets"))
    for module in ("src.main.utils.image_handler", "src.main.services.archive_service", "src.main.services.document_export_service", "src.main.services.presentation_service"):
        monkeypatch.setattr(module + ".get_image_handler", lambda: handler)
    return repo, handler


def image_refs(diagram):
    return {s.text:(s.properties.get("image_path") if isinstance(s, ComponentBox) else getattr(s, "image_path", None)) for s in diagram.shapes if not isinstance(s, ArrowShape)}


def test_zip_image_roundtrip_sha256(setup, tmp_path):
    repo, handler = setup
    diagram = graph()
    expected = {}
    for i, shape in enumerate(diagram.shapes[:4]):
        path = tmp_path / str(i) / "same.png"
        path.parent.mkdir()
        Image.new("RGB", (20, 20), (i * 50, 10, 220)).save(path)
        expected[shape.text] = hashlib.sha256(path.read_bytes()).hexdigest()
        if isinstance(shape, ComponentBox):
            shape.properties["image_path"] = str(path)
        else:
            shape.image_path = str(path)
    archive = ProjectArchiveService(EnhancedJSONExporter(repo))
    archive.export_zip(diagram, str(tmp_path / "project.zip"))
    imported = archive.import_zip(str(tmp_path / "project.zip"))
    assert imported is not None
    actual = {label:hashlib.sha256(Path(handler.get_full_path(ref)).read_bytes()).hexdigest() for label, ref in image_refs(imported).items()}
    assert actual == expected
    assert len(set(image_refs(imported).values())) == 4
    imported_again = archive.import_zip(str(tmp_path / "project.zip"))
    assert image_refs(imported_again) == image_refs(imported)


@pytest.mark.parametrize("mode", ["exact", "unique", "ambiguous", "missing"])
def test_image_lookup_priority(setup, tmp_path, mode):
    repo, handler = setup
    payload = EnhancedJSONExporter(repo).serialize_active_diagram(graph())
    payload["shapes"][0]["image_path"] = "images/nested/photo.png" if mode == "exact" else "images/old/photo.png"
    archive_path = tmp_path / "legacy.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("diagram.json", json.dumps(payload))
        if mode != "missing": zf.writestr("images/nested/photo.png", b"correct")
        if mode in ("exact", "ambiguous"): zf.writestr("images/photo.png", b"wrong")
    imported = ProjectArchiveService(EnhancedJSONExporter(repo)).import_zip(str(archive_path))
    assert imported
    ref = imported.shapes[0].properties["image_path"]
    if mode in ("exact", "unique"):
        assert Path(handler.get_full_path(ref)).read_bytes() == b"correct"
        assert not imported.import_warnings
    else:
        assert ref == ""
        assert any(mode.capitalize() in w for w in imported.import_warnings)
        assert imported.shapes[0].properties["unresolved_image_path"]


def test_repeated_save_reload_import_are_stable_and_isolated(setup, tmp_path):
    repo, _ = setup
    app = controller(repo, graph())
    app._persist_diagram()
    counts = repo.get_statistics()
    for _ in range(3):
        app._persist_diagram()
        assert repo.get_statistics() == counts
    root_id, owner = app.current_product_id, app.diagram.diagram_id
    loaded = DiagramLoader(repo).load_product_diagram(root_id)
    assert loaded.diagram_id == owner
    assert len(loaded.shapes) == len(app.diagram.shapes)
    app.diagram = loaded
    app._persist_diagram()
    assert repo.get_statistics() == counts
    archive = ProjectArchiveService(EnhancedJSONExporter(repo))
    archive.export_zip(app.diagram, str(tmp_path / "project.zip"))
    imported = archive.import_zip(str(tmp_path / "project.zip"))
    app._detach_imported_diagram(imported)
    app.diagram = imported
    app._persist_diagram()
    assert app.diagram.diagram_id != owner
    assert app.current_product_id != root_id
    twice = repo.get_statistics()
    for name in ("root_components", "leaf_components", "disassembly_steps", "actions"):
        assert twice[name] == 2 * counts[name]
    for _ in range(3):
        app._persist_diagram()
        assert repo.get_statistics() == twice
    for name in OWNED:
        assert all(row["diagram_id"] in {owner, app.diagram.diagram_id} for row in repo.export_snapshot()[name])
    repo.delete_product(app.current_product_id)
    assert repo.get_statistics() == counts
    assert repo.get_product(root_id)


def test_cross_diagram_relations_and_bad_catalog_ids_rejected(setup):
    repo, _ = setup
    a, b = repo.create_product("same"), repo.create_product("same")
    step = repo.create_step(a, 1)
    action = repo.create_action("unscrew", diagram_id=repo.get_product(b)["diagram_id"])
    leaf = repo.create_component("part", product_id=b, node_type="Leaf")
    before = repo.export_snapshot()
    for operation in (lambda:repo.add_action_to_step(step, action), lambda:repo.add_component_to_step(step, leaf), lambda:repo.update_step(step, component_id=b), lambda:repo.update_component(leaf, material_id=99999), lambda:repo.update_component(leaf, color_id=99999), lambda:repo.update_action(action, tool_id=99999), lambda:repo.update_component(leaf, root_component_id=a)):
        with pytest.raises(ValueError): operation()
    assert repo.export_snapshot() == before


def test_failed_save_rolls_back_records_and_assigned_ids(setup):
    repo, _ = setup
    diagram = graph()
    diagram.shapes[3].properties["material_id"] = 99999
    app = controller(repo, diagram)
    before = repo.export_snapshot()
    with pytest.raises(ValueError): app._persist_diagram()
    assert repo.export_snapshot() == before
    assert not diagram.shapes[0].properties.get("db_id")
    assert not getattr(diagram.shapes[2], "db_action_id", None)


def test_v1_migration_backup_orphans_and_idempotence(tmp_path):
    path = tmp_path / "store.json"
    repo = JsonRepository(str(path))
    root = repo.create_product("Old")
    leaf = repo.create_component("Part", product_id=root, node_type="Leaf", material_id=2)
    step = repo.create_step(root, 1)
    action = repo.create_action("Turn")
    repo.add_action_to_step(step, action)
    repo.add_component_to_step(step, leaf)
    data = repo.export_snapshot()
    data["schema_version"] = 1
    data.pop("diagrams")
    for name in OWNED:
        for row in data[name]: row.pop("diagram_id", None)
    data["actions"].append({"id":999, "name":"orphan", "tool_id":None})
    data["leaf_components"][0]["color_id"] = 999
    original = json.dumps(data).encode()
    path.write_bytes(original)
    with pytest.warns(RuntimeWarning): migrated = JsonRepository(str(path))
    snapshot = migrated.export_snapshot()
    assert snapshot["schema_version"] == 2
    assert snapshot["legacy_unresolved"]["actions"][0]["id"] == 999
    assert snapshot["leaf_components"][0]["color_id"] is None
    assert snapshot["leaf_components"][0]["legacy_references"]["color_id"] == 999
    assert len(snapshot["diagrams"]) == 1
    assert all(row["diagram_id"] == snapshot["diagrams"][0]["id"] for name in OWNED for row in snapshot[name])
    assert list(tmp_path.glob("*.bak"))[0].read_bytes() == original
    assert JsonRepository(str(path)).export_snapshot() == snapshot
    assert len(list(tmp_path.glob("*.bak"))) == 1
    assert snapshot["counters"]["actions"] >= 999


def test_future_schema_and_corrupt_json_are_never_overwritten(tmp_path):
    path = tmp_path / "store.json"
    for original in (b'{"schema_version": 500}', b'{bad json'):
        path.write_bytes(original)
        with pytest.raises(ValueError): JsonRepository(str(path))
        assert path.read_bytes() == original


@pytest.mark.parametrize("fmt", ["docx", "pptx", "html", "md", "txt"])
def test_catalog_names_and_details_survive_foreign_zip_and_conversion(setup, tmp_path, fmt):
    source, _ = setup
    material_id = source.create_material("Titanium special", category_id=2, subcategory_id=4, technical_name="Ti-6Al-4V", surface="Brushed")
    color_id = source.create_color("Ocean custom", "#123456", 18, 52, 86)
    diagram = graph()
    diagram.shapes[3].properties.update(material_id=material_id, color_id=color_id)
    archive = tmp_path / "project.zip"
    ProjectArchiveService(EnhancedJSONExporter(source)).export_zip(diagram, str(archive))
    target = JsonRepository(str(tmp_path / "other.json"))
    target.create_material("Different material")
    target.create_color("Different color", "#654321")
    exporter = EnhancedJSONExporter(target)
    imported = ProjectArchiveService(exporter).import_zip(str(archive))
    assert imported
    leaf = next(s for s in imported.shapes if isinstance(s, ComponentBox) and s.properties.get("node_type") == "Leaf")
    assert target.get_material(leaf.properties["material_id"])["name"] == "Titanium special"
    assert target.get_color(leaf.properties["color_id"])["name"] == "Ocean custom"
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(exporter.serialize_active_diagram(imported)), encoding="utf-8")
    guide = build_guide(str(model_path), include_bom=True)
    assert guide.bill_of_materials[0].material == "Titanium special"
    assert guide.bill_of_materials[0].color == "Ocean custom"
    assert guide.bill_of_materials[0].material_details["surface"] == "Brushed"
    path = Path(DocumentExportService(exporter).export(imported, str(tmp_path / "out" / "guide"), fmt))
    if fmt in ("docx", "pptx"):
        with zipfile.ZipFile(path) as zf:
            text = " ".join(zf.read(n).decode() for n in zf.namelist() if n.endswith(".xml"))
    else: text = path.read_text(encoding="utf-8")
    for value in ("Titanium special", "Ocean custom", "Brushed"): assert value in text
    assert "Different material" not in text
    assert "Different color" not in text


def test_material_selection_creates_once(setup):
    repo, _ = setup
    first = repo.resolve_material_selection(1, 1, 1)
    assert repo.resolve_material_selection(1, 1, 1) == first
    assert repo.get_material(first)["name"] == "ABS"
    assert repo.get_material(first)["scientific_name"] == ""
    assert repo.resolve_material_selection(2) == 2


def test_component_delete_does_not_delete_other_type_steps(setup):
    repo, _ = setup
    root = repo.create_product("Product")
    intermediate = repo.create_component("Composite", product_id=root)
    leaf = repo.create_component("Leaf", product_id=root, node_type="Leaf")
    first, second = repo.create_step(intermediate, 1), repo.create_step(leaf, 1)
    repo.delete_component(intermediate)
    assert repo.get_step(first) is None
    assert repo.get_step(second) is not None


def test_save_cannot_erase_child_root_and_removes_obsolete_links(setup):
    repo, _ = setup
    app = controller(repo, graph())
    app._persist_diagram()
    leaf = app.diagram.shapes[3]
    assert repo.get_component(leaf.properties["db_id"])["root_component_id"] == app.current_product_id
    assert len(repo.export_snapshot()["step_output_leaf"]) == 1
    assert len(repo.export_snapshot()["disassembly_step_actions"]) == 1
    app.diagram.shapes = [s for s in app.diagram.shapes if not isinstance(s, ArrowShape) or s.to_shape is not leaf]
    app._persist_diagram()
    assert not repo.export_snapshot()["step_output_leaf"]
    assert len(repo.export_snapshot()["disassembly_step_actions"]) == 1
    with pytest.raises(ValueError):
        repo.update_component(leaf.properties["db_id"], root_component_id=None)


def test_load_uses_current_normalized_properties(setup):
    repo, _ = setup
    app = controller(repo, graph())
    app._persist_diagram()
    leaf = app.diagram.shapes[3]
    repo.update_component(leaf.properties["db_id"], name="Changed", material_id=3)
    loaded = DiagramLoader(repo).load_product_diagram(app.current_product_id)
    found = next(s for s in loaded.shapes if isinstance(s, ComponentBox) and s.properties.get("node_type") == "Leaf")
    assert found.text == "Changed"
    assert found.properties["material_id"] == 3


def test_migration_recovers_only_unambiguous_output_ownership(setup):
    from src.main.repositories.migration import migrate_v1
    repo, _ = setup
    a, b = repo.create_product("A"), repo.create_product("B")
    leaf = repo.create_component("part", product_id=a, node_type="Leaf")
    sa, sb = repo.create_step(a, 1), repo.create_step(b, 1)
    repo.add_component_to_step(sa, leaf)
    data = repo.export_snapshot()
    data["leaf_components"][0]["root_component_id"] = None
    result = migrate_v1(data)
    assert result["leaf_components"][0]["root_component_id"] == a
    data["step_output_leaf"].append({"id":999, "disassembly_step_id":sb, "leaf_component_id":1})
    result = migrate_v1(data)
    assert not result["leaf_components"]
    assert result["legacy_unresolved"]["leaf_components"][0]["name"] == "part"


@pytest.mark.parametrize("fmt", ["docx", "pptx"])
def test_imported_images_embedded_with_original_hashes(setup, tmp_path, fmt):
    repo, handler = setup
    diagram = graph()
    expected = set()
    for i, shape in enumerate(diagram.shapes[:4]):
        path = tmp_path / f"original{i}.png"
        Image.new("RGB", (40, 50), (i * 60, 40, 100)).save(path)
        if i != 2: expected.add(hashlib.sha256(path.read_bytes()).hexdigest())
        if isinstance(shape, ComponentBox): shape.properties["image_path"] = str(path)
        else: shape.image_path = str(path)
    archive = ProjectArchiveService(EnhancedJSONExporter(repo))
    archive.export_zip(diagram, str(tmp_path / "project.zip"))
    imported = archive.import_zip(str(tmp_path / "project.zip"))
    output = DocumentExportService(EnhancedJSONExporter(repo)).export(imported, str(tmp_path / "guide"), fmt)
    with zipfile.ZipFile(output) as zf:
        actual = {hashlib.sha256(zf.read(n)).hexdigest() for n in zf.namelist() if "/media/" in n}
    assert expected <= actual


def test_invalid_import_rolls_back_new_catalog_records(setup, tmp_path):
    repo, _ = setup
    data = EnhancedJSONExporter(repo).serialize_active_diagram(graph())
    data["catalogs"]["colors"][0]["name"] = "New color"
    data["connections"] = [{"from_id":1}]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(data))
    before = repo.export_snapshot()
    assert EnhancedJSONExporter(repo).import_diagram(str(path)) is None
    assert repo.export_snapshot() == before


def test_direct_staging_does_not_flatten_same_basenames(setup, tmp_path):
    from src.main.services.image_staging import stage_images
    _, handler = setup
    shapes = []
    for i in range(2):
        source = tmp_path / str(i) / "photo.png"
        source.parent.mkdir()
        source.write_bytes(bytes([i]))
        shapes.append({"image_path":str(source)})
    snapshot = {"shapes":shapes}
    stage_images(snapshot, tmp_path / "staging", handler)
    assert shapes[0]["image_path"] != shapes[1]["image_path"]
    assert [(tmp_path / "staging" / s["image_path"]).read_bytes() for s in shapes] == [bytes([0]), bytes([1])]


def test_default_material_and_color_resolve_without_numeric_labels(setup):
    repo, _ = setup
    payload = EnhancedJSONExporter(repo).serialize_active_diagram(graph())
    leaf = next(s for s in payload["shapes"] if s.get("node_type") == "Leaf")
    assert leaf["material_id"] == 2 and leaf["material"] == "Metal"
    assert leaf["color_id"] == 3 and leaf["color"] == "Blue"


def test_guide_ir_matches_versioned_schema(setup, tmp_path):
    import jsonschema
    from src.main.loader_se.disassembly_loader import guide_to_dict
    repo, _ = setup
    path = tmp_path / "model.json"
    path.write_text(json.dumps(EnhancedJSONExporter(repo).serialize_active_diagram(graph())))
    guide = build_guide(str(path), include_bom=True)
    schema = json.loads((Path(__file__).parents[1] / "main/loader_se/disassembly_loader/ir_schema.json").read_text())
    jsonschema.validate(guide_to_dict(guide), schema)


def test_editing_other_properties_keeps_exact_custom_material(setup):
    from types import SimpleNamespace
    from src.main.views.properties_panel import PropertiesPanel
    repo, _ = setup
    mid = repo.create_material("Custom alloy", category_id=2, subcategory_id=4)
    panel = PropertiesPanel.__new__(PropertiesPanel)
    panel.repository = repo
    value = lambda text: SimpleNamespace(get=lambda: text)
    widget = SimpleNamespace(category_map={"Metal":2}, subcategory_map={"Non-Ferrous":4}, type_map={}, category_var=value("Metal"), subcategory_var=value("Non-Ferrous"), type_var=value(""), selected_material_id=mid, material_data={mid:repo.get_material(mid)})
    assert panel._get_selected_material_id(widget) == mid


def test_failed_migration_validation_keeps_original_file(tmp_path):
    repo = JsonRepository(str(tmp_path / "seed.json"))
    data = repo.export_snapshot()
    data["schema_version"] = 1
    data["colors"].append(dict(data["colors"][0]))
    path = tmp_path / "store.json"
    original = json.dumps(data).encode()
    path.write_bytes(original)
    with pytest.raises(ValueError, match="Duplicate IDs"):
        JsonRepository(str(path))
    assert path.read_bytes() == original
