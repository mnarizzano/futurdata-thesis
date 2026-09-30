"""
builder.py — orchestration of the load pipeline into a complete Guide.

This module ties the three stages together into the in-memory result:

    raw JSON  --adapter-->  graph  --validate-->  warnings
                                   --linearize-->  steps
                                   --assemble--->  Guide

It is the single place that knows the ORDER of the pipeline. Keeping it separate
from the linearizer matters: the linearizer answers "in what order do we take it
apart?" and returns steps; the builder answers "what is the complete load
result?" and returns the Guide (product + steps + warnings + depth + optional
bill of materials). Different responsibilities, different modules.

The public entry points (build_guide / build_ir_file) live in the package
__init__; this module provides the function they call.
"""

from __future__ import annotations

from . import linearizer, validation
from .adapter import normalize_file
from .models import (
    Component,
    DepthMode,
    DepthSpec,
    DisassemblyGraph,
    Guide,
    Step,
    TraversalMode,
)

# The IR schema version. Bump ONLY when the JSON shape changes in a way that
# could break a consumer. This is the contract marker the 7 generators can check.
# 1.1: Step gains `input` (the component the operation is performed on);
#      `continues_as` becomes the LIST of all continuing components; the Guide
#      gains a top-level `tools` union (FR 1.3: tools shown at the top).
SCHEMA_VERSION = "1.1"


def build_guide(
    source_path: str,
    depth: DepthSpec | None = None,
    traversal: TraversalMode = TraversalMode.STRICT,
    include_bom: bool = False,
) -> Guide:
    """
    Run the full load pipeline on a Builder JSON file and return the Guide.

    Parameters:
      source_path : path to the Builder JSON model (read-only; NFR 2.1).
      depth       : the disassembly depth (FR 3.0). Defaults to full disassembly.
      traversal   : STRICT (default) or LENIENT (reserved; raises NotImplemented).
      include_bom : if True, compute the leaf-only bill of materials; otherwise
                    the Guide's bill_of_materials stays None (the field is always
                    present in the JSON, as null or a list — never omitted).

    Never raises on a malformed-but-parsable model (warnings carry the problems,
    FR 2.3); raises UnparsableModelError only if there is no graph to build.
    """
    if depth is None:
        depth = DepthSpec(mode=DepthMode.FULL)

    graph = normalize_file(source_path)
    warnings = validation.validate(graph)
    steps = linearizer.linearize(graph, depth, traversal)

    product = _build_product(graph)
    bom = _build_bill_of_materials(steps) if include_bom else None

    return Guide(
        product=product,
        steps=steps,
        warnings=tuple(warnings),
        depth=depth,
        schema_version=SCHEMA_VERSION,
        tools=_collect_guide_tools(steps),
        bill_of_materials=bom,
    )


# =============================================================================
# Helpers
# =============================================================================

def _build_product(graph: DisassemblyGraph) -> Component:
    """
    Build the Component describing the whole product (the Root).

    The root is the single node with no incoming edge (topology, not the id=1
    assumption — Epson's root is id=3). If the graph is empty or rootless, we
    return a minimal placeholder so the Guide is still well-formed; validation
    reports the underlying problem separately (FR 2.3).
    """
    root_id = linearizer.find_root(graph)
    if root_id is None:
        return Component(node_id=-1, name="(empty model)")
    node = graph.nodes[root_id]
    return Component(
        node_id=node.id,
        name=node.text,
        weight=_parse_weight(node.weight),
        weight_unit=node.weight_unit,
        material=node.material,
        material_details=node.extra.get("material_details", {}),
        color=node.color,
        image_path=node.image_path,
    )


def _build_bill_of_materials(steps: tuple[Step, ...]) -> tuple[Component, ...]:
    """
    Compute the leaf-only bill of materials from the linearized steps.

    The BoM is the set of LEAF components — the final physical parts — NOT the
    intermediate composites. Rationale, confirmed on Bialetti: the 18 leaf parts
    sum to exactly the product weight (2500 g); including the 6 intermediate
    composites (the chassis as it is progressively stripped) would double-count
    mass and break the mass balance (FR 2.4). Intermediate composites are
    transition states, not distinct line items.

    Concretely: every output across all steps is a leaf (the linearizer puts the
    single continuing composite in `continues_as`, not in `outputs`). A kept-whole
    block (depth cut) is also a leaf for BoM purposes — it is a final part the
    user chose not to open. So the BoM is simply the union of all step outputs,
    de-duplicated by node_id (a part is listed once).
    """
    seen: dict[int, Component] = {}
    for step in steps:
        for output in step.outputs:
            seen.setdefault(output.node_id, output)
    return tuple(seen.values())


def _collect_guide_tools(steps: tuple[Step, ...]) -> tuple[str, ...]:
    """Union of tools_required across every step (FR 1.3: the tools needed to
    disassemble the whole product, shown at the top of the guide).

    Deduplicated case-insensitively, first-appearance order — same policy as
    the per-step list, computed once here instead of 7 times in 7 generators.
    Always present (possibly empty), unlike the OPTIONAL bill_of_materials:
    it costs one pass over data already in memory."""
    seen: dict[str, str] = {}
    for step in steps:
        for tool in step.tools_required:
            seen.setdefault(tool.casefold(), tool)
    return tuple(seen.values())


def _parse_weight(weight: str | None) -> float | None:
    """Parse a raw weight string to float; None/blank/garbage -> None."""
    if weight is None:
        return None
    try:
        return float(weight)
    except (TypeError, ValueError):
        return None