"""
emitter.py — serialize a Guide into the IR JSON contract.

RESPONSIBILITY: turn the in-memory Guide into the JSON that the 7 generators
consume. This is the public boundary of the load phase, so the JSON SHAPE is a
contract: its schema is documented separately and versioned (schema_version).
The emitter does NOT compute anything about the disassembly — it receives a
finished Guide and writes it. Any logic here would be logic in the wrong place.

DESIGN CHOICES (all decided against the consumers' needs):

  - EXPLICIT NULLS. Optional fields with no value are emitted as `null`, never
    omitted. With 7 heterogeneous consumers (Python and JavaScript), a field
    that is sometimes present and sometimes absent is a source of bugs; a field
    that is always present (null or value) is predictable. So every optional
    field appears in every object.

  - STABLE FIELD ORDER & ensure_ascii. We build plain dicts in a fixed key order
    and serialize with ensure_ascii=True. ensure_ascii avoids any encoding
    surprise in downstream tools that mishandle UTF-8; stable order makes the
    output diffable in version control (a contract people review by eye).

  - IMAGE PATHS AS-IS. Images are passed as their path/URL exactly as the source
    gave them (FR 4.1), not embedded. Each image entry is tagged is_url so a
    consumer knows whether to fetch a remote URL (e.g. nespresso's http images)
    or load a local/relative path (Bialetti). We do not download or rewrite
    them — that keeps the load phase non-destructive and side-effect free.

We deliberately build dicts by hand rather than dataclasses.asdict(), because
asdict() would couple the JSON shape to the field names and nesting of the
dataclasses; an explicit mapping lets the internal models evolve without
silently changing the public contract.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .models import Action, Component, Guide, Step


def guide_to_dict(guide: Guide) -> dict[str, Any]:
    """
    Convert a Guide into a plain dict matching the IR JSON schema.

    This is the single source of the JSON shape. The JSON Schema deliverable
    documents exactly this structure, and a test validates this function's
    output against that schema so the two cannot drift apart.
    """
    return {
        "schema_version": guide.schema_version,
        "product": _component_to_dict(guide.product),
        "depth": _depth_to_dict(guide),
        # Guide-level tool union (schema 1.1, FR 1.3): placed before `steps`
        # because it is "top of the guide" information, like the product.
        "tools": list(guide.tools),
        "steps": [_step_to_dict(s) for s in guide.steps],
        "warnings": [_warning_to_dict(w) for w in guide.warnings],
        # Always present (explicit-null policy): null if not requested, else a list.
        "bill_of_materials": (
            None if guide.bill_of_materials is None
            else [_component_to_dict(c) for c in guide.bill_of_materials]
        ),
    }


def emit_json(guide: Guide, indent: int = 2) -> str:
    """Serialize a Guide to a JSON string (stable order, ASCII-safe)."""
    return json.dumps(
        guide_to_dict(guide),
        indent=indent,
        ensure_ascii=True,
        sort_keys=False,  # we control order explicitly in the *_to_dict helpers
    )


def write_json(guide: Guide, out_path: str, indent: int = 2) -> None:
    """
    Write a Guide as IR JSON to `out_path`.

    Writes only to the output path; never touches the source model (NFR 2.1).
    """
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(emit_json(guide, indent=indent))


# =============================================================================
# Per-object serializers (each produces an explicit, fixed-order dict)
# =============================================================================

def _component_to_dict(c: Component) -> dict[str, Any]:
    """Serialize a Component with all optional fields explicit (null if unset)."""
    return {
        "node_id": c.node_id,
        "name": c.name,
        "weight": c.weight,
        "weight_unit": c.weight_unit,
        "material": c.material,
        "material_details": c.material_details,
        "color": c.color,
        "image": _image_to_dict(c.image_path),
        "kept_whole": c.kept_whole,
        "contained_leaf_count": c.contained_leaf_count,
    }


def _action_to_dict(a: Action) -> dict[str, Any]:
    """Serialize an Action (one micro-instruction in a step's chain)."""
    return {
        "node_id": a.node_id,
        "text": a.text,
        "tools": a.tools,
        "image": _image_to_dict(a.image_path),
    }


def _step_to_dict(s: Step) -> dict[str, Any]:
    """Serialize a Step: input + operation + action chain + outputs + continuations."""
    return {
        "index": s.index,
        "operation": s.operation,
        "image": _image_to_dict(s.image_path),
        # schema 1.1: the component this operation is performed ON. Always
        # present — it is what lets a consumer narrate "now disassembling X"
        # on a branched model instead of treating the step as a black box.
        "input": _component_to_dict(s.input),
        "actions": [_action_to_dict(a) for a in s.actions],
        "outputs": [_component_to_dict(o) for o in s.outputs],
        # schema 1.1: ALL continuing components (a list, possibly empty). The
        # step that opens each entry is the one whose input.node_id matches.
        "continues_as": [_component_to_dict(c) for c in s.continues_as],
        "tools_required": list(s.tools_required),
    }


def _warning_to_dict(w) -> dict[str, Any]:
    """Serialize a ValidationWarning; severity becomes its string value."""
    return {
        "rule": w.rule,
        "severity": w.severity.value,
        "message": w.message,
        "node_ids": list(w.node_ids),
    }


def _depth_to_dict(guide: Guide) -> dict[str, Any]:
    """Serialize the applied DepthSpec for provenance."""
    if guide.depth is None:
        return {"mode": "full", "keep_whole_ids": []}
    return {
        "mode": guide.depth.mode.value,
        "keep_whole_ids": list(guide.depth.keep_whole_ids),
    }


def _image_to_dict(image_path: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Serialize an image reference, or null if there is none.

    Returns {"path": ..., "is_url": bool} so a consumer knows whether to fetch a
    remote URL or load a local/relative path. We classify by scheme: anything
    starting with http:// or https:// is a URL (e.g. nespresso's images),
    otherwise it is treated as a local/relative path (e.g. Bialetti's). The path
    is passed through unchanged — the emitter never downloads or rewrites it.
    """
    if not image_path:
        return None
    is_url = image_path.startswith(("http://", "https://"))
    return {"path": image_path, "is_url": is_url}