"""Load and normalize disassembly guides for the PPTX converter.

The Futurdata application owns a shared :mod:`disassembly_loader` package.
The PPTX converter uses that package whenever it is importable so every export
format receives the same validated intermediate representation (IR).

For development and automated tests, this module also supports already-
normalized IR JSON files directly. The direct fallback is intentionally kept
separate from graph parsing: the converter never reconstructs Builder graph
logic on its own.
"""

from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .models import WizardDocument


def _candidate_loader_directories() -> list[Path]:
    """Return repository locations that may contain ``disassembly_loader``.

    In the professor repository the converter is stored at
    ``src/main/pptx-converter`` while the shared loader is stored at
    ``src/main/loader_se/disassembly_loader``. Some older repository layouts
    placed ``loader_se`` at the repository root. Both locations are checked.
    """

    converter_dir = Path(__file__).resolve().parents[1]
    services_dir = converter_dir.parent
    main_dir = services_dir.parent
    repository_root = main_dir.parents[1]
    candidate_roots = [main_dir, services_dir, repository_root]
    if repository_root.parent != repository_root:
        candidate_roots.append(repository_root.parent)

    return [root / "loader_se" for root in candidate_roots]


def _import_loader_module() -> ModuleType | None:
    """Import the shared loader without requiring users to set ``PYTHONPATH``.

    A normal import is attempted first because the desktop application may
    already have configured its module search path. If that fails, known
    sibling directories are appended to ``sys.path`` one at a time.
    """

    try:
        return importlib.import_module("disassembly_loader")
    except ImportError:
        pass

    for directory in _candidate_loader_directories():
        if not directory.is_dir():
            continue
        directory_text = str(directory)
        if directory_text not in sys.path:
            sys.path.insert(0, directory_text)
        try:
            return importlib.import_module("disassembly_loader")
        except ImportError:
            continue

    return None


def _accepted_loader_arguments(
    build_guide: Callable[..., Any],
    *,
    depth: Any | None,
    include_bom: bool,
) -> dict[str, Any]:
    """Build keyword arguments supported by the installed loader version.

    Signature inspection is safer than repeatedly catching ``TypeError``.
    A ``TypeError`` raised *inside* the loader must remain visible instead of
    being mistaken for an old function signature.
    """

    signature = inspect.signature(build_guide)
    parameters = signature.parameters
    accepts_arbitrary_keywords = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )

    arguments: dict[str, Any] = {}
    if accepts_arbitrary_keywords or "depth" in parameters:
        arguments["depth"] = depth
    if accepts_arbitrary_keywords or "include_bom" in parameters:
        arguments["include_bom"] = include_bom
    return arguments


def _call_external_loader(
    path: Path,
    *,
    depth: Any | None,
    include_bom: bool,
) -> Any | None:
    """Return the guide created by the shared loader, or ``None`` if absent."""

    module = _import_loader_module()
    if module is None:
        return None

    build_guide = getattr(module, "build_guide", None)
    if not callable(build_guide):
        raise ImportError(
            "The 'disassembly_loader' module was found, but it does not expose "
            "a callable build_guide function."
        )

    keyword_arguments = _accepted_loader_arguments(
        build_guide,
        depth=depth,
        include_bom=include_bom,
    )
    return build_guide(str(path), **keyword_arguments)


def load_document(
    json_path: str | Path,
    *,
    prefer_external_loader: bool = True,
    depth: Any | None = None,
    include_bom: bool = True,
) -> WizardDocument:
    """Load a source file and convert it into :class:`WizardDocument`.

    The file is inspected first to distinguish a normalized Loader IR from a
    Builder graph. Normalized IR is read directly, even when the shared Loader
    is installed. Builder graphs are passed to ``build_guide``. This prevents
    the included IR example from being incorrectly parsed as Builder input.
    """

    path = Path(json_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")
    if path.suffix.lower() != ".json":
        raise ValueError(f"Expected a .json input file, received: {path.name}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"The input is not valid JSON: line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("The top-level JSON value must be an object.")

    # Loader IR files have product/steps, while Builder graph files expose
    # shapes/connections. A normalized guide should not be sent back through
    # the graph loader because it no longer contains Builder shapes.
    looks_like_ir = (
        isinstance(payload.get("product"), dict)
        and isinstance(payload.get("steps"), list)
        and "shapes" not in payload
    )

    if prefer_external_loader and not looks_like_ir:
        source = _call_external_loader(
            path,
            depth=depth,
            include_bom=include_bom,
        )
        if source is not None:
            return WizardDocument.from_any(source, source_dir=str(path.parent))

        raise ImportError(
            "This file looks like a Builder graph, but the shared "
            "'disassembly_loader' package could not be imported. Keep the "
            "converter inside the professor repository or add "
            "src/main/loader_se to PYTHONPATH."
        )

    document = WizardDocument.from_any(payload, source_dir=str(path.parent))

    # An IR file may already contain a BoM. Respect the UI switch by clearing
    # it only in memory; the original JSON remains unchanged.
    if not include_bom:
        document.bill_of_materials = []

    return document
