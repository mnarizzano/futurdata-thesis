import json
import zipfile

from src.main.models import ComponentBox, Diagram
from src.main.repositories import JsonRepository
from src.main.services import ProjectArchiveService
from src.main.utils.json_exporter import EnhancedJSONExporter


def test_json_repository_persists_complete_relationships(tmp_path):
    path = tmp_path / "store.json"
    repo = JsonRepository(str(path))
    root = repo.create_component("Coffee machine", node_type="Root")
    leaf = repo.create_component("Pump", product_id=root, node_type="Leaf")
    step = repo.create_step(root, 1, title="Open")
    action = repo.create_action("Unscrew")
    repo.add_action_to_step(step, action)
    repo.add_component_to_step(step, leaf)

    reloaded = JsonRepository(str(path))
    assert reloaded.get_product(root)["name"] == "Coffee machine"
    assert reloaded.get_components_from_step(step)[0]["name"] == "Pump"
    assert reloaded.get_actions_for_step(step)[0]["action"]["name"] == "Unscrew"
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2


def test_export_is_zip_with_json_and_images_directory(tmp_path):
    repo = JsonRepository(str(tmp_path / "store.json"))
    exporter = EnhancedJSONExporter(repo)
    archive = ProjectArchiveService(exporter)
    diagram = Diagram()
    root = ComponentBox(10, 20)
    root.text = "Root"
    root.properties["node_type"] = "Root"
    root.properties["name"] = "Root"
    diagram.shapes.append(root)

    target = tmp_path / "project.zip"
    assert archive.export_zip(diagram, str(target))
    with zipfile.ZipFile(target) as zf:
        assert "diagram.json" in zf.namelist()
        # No empty images directory is added when the diagram has no images.
        assert "images/" not in zf.namelist()


def test_zip_export_does_not_read_repository_and_skips_missing_images(tmp_path):
    class RepositoryMustNotBeUsed:
        def __getattr__(self, name):
            raise AssertionError(f"repository accessed during ZIP export: {name}")

    exporter = EnhancedJSONExporter(RepositoryMustNotBeUsed())
    archive = ProjectArchiveService(exporter)
    diagram = Diagram()
    root = ComponentBox(10, 20)
    root.text = "Standalone"
    root.properties["node_type"] = "Root"
    root.properties["name"] = "Standalone"
    root.properties["image_path"] = "images/does/not/exist.png"
    diagram.shapes.append(root)

    target = tmp_path / "standalone.zip"
    assert archive.export_zip(diagram, str(target))
    assert archive.last_export_warnings == [
        "Missing image skipped: images/does/not/exist.png"
    ]

    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
        assert names == ["diagram.json"]
        payload = json.loads(zf.read("diagram.json"))
        assert "repository" not in payload
        assert payload["shapes"][0]["name"] == "Standalone"
        assert payload["shapes"][0]["image_path"] == "images/does/not/exist.png"
