"""
disassembly_loader — load phase of the Disassembly Wizard.

Public API (information hiding): downstream generators should import ONLY the
high-level entry points and the IR data types they consume. The internal
modules (adapter, validation, linearizer, builder, emitter) are implementation
detail and may change without breaking consumers, as long as the IR schema
(documented separately and versioned) stays stable.

Two doors onto the same IR (one logical schema, two ways to access it):
  - build_guide(...)  -> Guide   : the in-memory object, for Python consumers.
  - build_ir_file(...)           : writes the IR JSON file, for any consumer
                                   (including the non-Python generators: HTML+JS,
                                   VIDEO).
"""

from .builder import build_guide  # noqa: F401
from .emitter import emit_json, guide_to_dict, write_json  # noqa: F401
from .models import (  # noqa: F401  (re-exported for consumers)
    Action,
    Component,
    DepthMode,
    DepthSpec,
    DisassemblyGraph,
    Edge,
    GraphNode,
    Guide,
    NodeType,
    Severity,
    Step,
    TraversalMode,
    UnparsableModelError,
    ValidationWarning,
)


def build_ir_file(
    source_path: str,
    out_path: str,
    depth: "DepthSpec | None" = None,
    traversal: "TraversalMode" = TraversalMode.STRICT,
    include_bom: bool = False,
    indent: int = 2,
) -> None:
    """
    Run the full load pipeline and write the IR JSON to `out_path`.

    Convenience wrapper combining build_guide + write_json: the single call a
    non-Python consumer's toolchain (or a build script) needs. Reads the source
    model read-only; writes only to out_path (NFR 2.1).
    """
    guide = build_guide(
        source_path, depth=depth, traversal=traversal, include_bom=include_bom
    )
    write_json(guide, out_path, indent=indent)