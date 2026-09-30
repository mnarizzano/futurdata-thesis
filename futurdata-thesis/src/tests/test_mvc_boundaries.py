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
