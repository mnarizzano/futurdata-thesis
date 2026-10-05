"""Keep persistence and UI dependencies on their established MVC sides."""

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1] / "main"


@pytest.mark.parametrize(
    "layer,forbidden",
    [
        ("models", {"tkinter", "views", "controllers", "repositories"}),
        ("views", {"repositories", "sqlite3"}),
        ("services", {"tkinter", "views", "controllers", "repositories"}),
    ],
)
def test_layer_import_boundaries(layer, forbidden):
    for path in (ROOT / layer).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not forbidden.intersection(module.split(".")), (
                    f"{path}: {module}"
                )


def test_views_do_not_perform_attachment_or_filesystem_persistence():
    forbidden = {"upload_image", "save_to_file", "write_text", "write_bytes",
                 "makedirs", "mkdir", "copyfile", "copyfileobj"}
    for path in (ROOT / "views").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden, f"{path}: {node.func.attr}"


def test_model_constructors_have_no_canvas_ids():
    from src.main.models import ComponentBox, Connection
    shape = ComponentBox(0, 0)
    assert not {"shape_id", "text_id"}.intersection(vars(shape))
    assert "arrow_id" not in vars(Connection(shape, shape))


def test_app_controller_has_no_tk_or_view_implementation_imports():
    tree = ast.parse((ROOT / "controllers" / "app_controller.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [item.name for item in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        assert all(not {"tkinter", "views"}.intersection(module.split(".")) for module in modules)
