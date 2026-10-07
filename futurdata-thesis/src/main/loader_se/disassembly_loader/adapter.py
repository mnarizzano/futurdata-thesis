"""
adapter.py — format normalization.

RESPONSIBILITY (one sentence): take the raw JSON dict produced by the Builder
and return a canonical `DisassemblyGraph`, absorbing every format divergence,
WITHOUT judging whether the graph is valid.

This is the ONLY module that knows different input formats exist. It is
deliberately "dumb": it normalizes shape, it does not interpret meaning. It
does not decide what a Composite is, it does not order anything, it does not
check the grammar. The less logic lives here, the less breaks when a 7th
teammate's format shows up.

WHAT "ABSORB DIVERGENCES" MEANS — confirmed empirically on all 5 real files:

  1. WHERE EDGES LIVE. Two mutually exclusive storage locations:
       - a populated `connections` array (Bialetti), or
       - shapes of type "arrow" carrying the edge (Maria, nespresso,
         capsule, washing_machine).
     The adapter reads whichever is populated. If both are populated (never
     seen yet, but possible), it reads `connections` and records that the file
     is unusual — but note: the adapter does not emit ValidationWarnings (that
     is the validator's job). It simply will not crash.

  2. EDGE FIELD NAMES. `from_id`/`to_id` (Bialetti) vs
     `from_shape_id`/`to_shape_id` (the arrow-based files). Both collapse to
     Edge.src / Edge.dst. After the adapter, no other module knows these two
     namings ever existed.

  3. WEIGHT TYPE. `int` in Bialetti, `str` in the others. The adapter does NOT
     normalize this — it keeps `weight` as given (stringified for storage in
     GraphNode, which models weight as an optional string). The loader parses it
     to a number only at the IR level, where it is needed. Keeping the graph
     layer a faithful mirror of input is the point.

WHAT THE ADAPTER MAY RAISE: only `UnparsableModelError`, and only when there is
no graph to build at all — the JSON did not parse, `shapes` is missing or not a
list, a shape is not an object, a node shape has no `id`, or an edge entry
(connection / arrow) lacks an endpoint. Every *graph-level* defect (cycle,
dangling edge, unknown node type, multiple roots) is left intact in the returned
graph for the validator to find and report. The adapter never decides "this
graph is too broken to return".

DESIGN NOTE — why a function, not a class hierarchy:
We have two input shapes and a handful of `if` branches. A `normalize(raw) ->
DisassemblyGraph` function with clear branches is more readable than an
AbstractAdapter with MariaAdapter/BialettiAdapter subclasses. IF the formats
ever grow to many with genuinely divergent logic, THEN refactor toward a
strategy — when the pain is real, not in anticipation. This honours the
"scalable but not over-engineered" guidance.
"""

from __future__ import annotations

import json
import os
import warnings
from typing import Any

from .models import (
    DisassemblyGraph,
    Edge,
    GraphNode,
    NodeType,
    UnparsableModelError,
)


# Source `type` values that denote an EDGE rather than a node. Everything else
# is treated as a node (with its type mapped via NodeType, UNKNOWN as fallback).
_ARROW_TYPE = "arrow"

# The set of source field names we map onto canonical GraphNode fields. Listed
# explicitly so that any *other* source field is routed into `extra` rather than
# silently lost (FR 11.0 / NFR 2.0 extensibility).
_KNOWN_NODE_FIELDS = {
    "id", "type", "text", "name", "component_name", "step_description",
    "x", "y", "weight", "weight_unit",
    "material_id", "material", "color_id", "color",
    "image_path", "tools",
}


def load_json(path: str) -> dict[str, Any]:
    """
    Read and parse a JSON file from disk, read-only.

    Honours FR 1.2 / NFR 2.1 (never modify the source): we only open for
    reading. A syntactically invalid file is the canonical "no graph to build"
    case, so a JSON decode error is re-raised as UnparsableModelError with a
    precise message (FR 2.2 spirit: say what is wrong).

    Separated from `normalize` so that callers who already hold a dict (e.g.
    tests, or a GUI that parsed the file itself) can normalize without touching
    the filesystem.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise UnparsableModelError(f"Model file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UnparsableModelError(
            f"Model file is not valid JSON ({path}): {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise UnparsableModelError(
            f"Model root must be a JSON object, got {type(raw).__name__} ({path})"
        )
    return raw


def normalize(raw: dict[str, Any], source_path: str | None = None) -> DisassemblyGraph:
    """
    Turn a raw Builder JSON dict into a canonical DisassemblyGraph.

    Steps:
      1. Validate that there is a graph to build at all (else UnparsableModelError).
      2. Split shapes into nodes and edges; map each node to a GraphNode.
      3. Read edges from whichever location is populated; canonicalize fields.
      4. Precompute out/inc adjacency for the loader.

    Defects in the graph (dangling edges, cycles, etc.) are preserved, not
    rejected — the validator handles them later.
    """
    # Resolve only explicit portable catalog definitions; local numeric IDs have
    # no universal meaning and must never be printed as material/color names.
    import copy
    raw = copy.deepcopy(raw)
    catalogs = raw.get("catalogs", raw.get("repository", {}).get("catalogs", raw.get("repository", {})))
    for item in raw.get("shapes", []) if isinstance(raw.get("shapes"), list) else []:
        if not isinstance(item, dict):
            continue
        for label, field, collection in (("material", "material_id", "materials"), ("color", "color_id", "colors")):
            record = next((r for r in catalogs.get(collection, []) if str(r.get("id")) == str(item.get(field))), None)
            if item.get(field) is not None and not record and not item.get(label):
                warnings.warn(f"Unresolved {field}={item[field]}; portable catalog definition missing", RuntimeWarning)
            if record:
                item[label] = record.get("name")
                if label == "material":
                    item["material_details"] = {k:record.get(k) for k in ("category_name", "subcategory_name", "type_name", "scientific_name", "technical_name", "surface")}
    shapes = raw.get("shapes")
    if shapes is None:
        raise UnparsableModelError("Model is missing the required 'shapes' key.")
    if not isinstance(shapes, list):
        raise UnparsableModelError(
            f"'shapes' must be a list, got {type(shapes).__name__}."
        )

    nodes: dict[int, GraphNode] = {}
    node_shapes: list[dict[str, Any]] = []
    arrow_shapes: list[dict[str, Any]] = []

    # --- 2. partition shapes into nodes vs arrow-edges -----------------------
    # BOUNDARY ENFORCEMENT. This loop is where the "if I cannot construct the
    # graph, that is an UnparsableModelError" rule of thumb (models.py) is
    # actually enforced. A shape that is not an object, a node without an `id`,
    # or an arrow without both endpoints leaves us with no graph element to
    # build — there is nothing to hand to the validator, so this is parse
    # failure, not a validation finding. (Contrast: an edge whose endpoint ids
    # exist syntactically but point to no node IS buildable — a dangling edge —
    # and is left for validation.rule_dangling_edges.) Messages carry the
    # shapes[i] index so the problem is localized in the source JSON
    # (FR 2.2 spirit / NFR 1.1).
    for i, shape in enumerate(shapes):
        if not isinstance(shape, dict):
            raise UnparsableModelError(
                f"shapes[{i}] must be a JSON object, got {type(shape).__name__}."
            )
        if shape.get("type") == _ARROW_TYPE:
            for key in ("from_shape_id", "to_shape_id"):
                if shape.get(key) is None:
                    raise UnparsableModelError(
                        f"Arrow shape at shapes[{i}] is missing '{key}'; an "
                        f"edge without both endpoints cannot be part of a graph."
                    )
            arrow_shapes.append(shape)
        else:
            if shape.get("id") is None:
                raise UnparsableModelError(
                    f"Shape at shapes[{i}] has no 'id'; a node without an "
                    f"identity cannot be placed in a graph."
                )
            node_shapes.append(shape)

    for shape in node_shapes:
        node = _build_node(shape)
        nodes[node.id] = node

    # --- 3. read edges from whichever location is populated ------------------
    # Bialetti stores edges in a top-level `connections` array; the arrow-based
    # files store them as `arrow` shapes. We prefer a populated `connections`
    # array; otherwise we use the arrow shapes. (If neither is populated, the
    # graph simply has no edges — a defect the validator will report, not a
    # parse failure.)
    connections = raw.get("connections") or []
    if not isinstance(connections, list):
        raise UnparsableModelError(
            f"'connections' must be a list, got {type(connections).__name__}."
        )
    for i, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise UnparsableModelError(
                f"connections[{i}] must be a JSON object, "
                f"got {type(conn).__name__}."
            )
        src = conn.get("from_shape_id", conn.get("from_id"))
        dst = conn.get("to_shape_id", conn.get("to_id"))
        if src is None or dst is None:
            raise UnparsableModelError(
                f"connections[{i}] is missing an endpoint; expected either "
                "'from_shape_id'/'to_shape_id' or 'from_id'/'to_id'."
            )
    edges = tuple(dict.fromkeys(
        [_edge_from_connection(c) for c in connections]
        + [_edge_from_arrow(a) for a in arrow_shapes]
    ))

    # --- 4. precompute adjacency --------------------------------------------
    out_acc: dict[int, list[int]] = {}
    inc_acc: dict[int, list[int]] = {}
    for edge in edges:
        out_acc.setdefault(edge.src, []).append(edge.dst)
        inc_acc.setdefault(edge.dst, []).append(edge.src)

    # Freeze adjacency lists into tuples. Every node id gets an entry (possibly
    # empty) so the loader can look up any node without KeyError handling.
    out_adj = {nid: tuple(out_acc.get(nid, ())) for nid in nodes}
    inc_adj = {nid: tuple(inc_acc.get(nid, ())) for nid in nodes}
    # Edges may reference ids absent from `nodes` (dangling edges). Keep their
    # adjacency too, so the validator can see them; absence from `nodes` is what
    # flags them as dangling later.
    for edge in edges:
        out_adj.setdefault(edge.src, tuple(out_acc.get(edge.src, ())))
        inc_adj.setdefault(edge.dst, tuple(inc_acc.get(edge.dst, ())))

    metadata = raw.get("metadata") or {}
    product_name = metadata.get("product_name") or None

    return DisassemblyGraph(
        nodes=nodes,
        edges=edges,
        out_adj=out_adj,
        inc_adj=inc_adj,
        product_name=product_name,
        source_path=source_path,
    )


def normalize_file(path: str) -> DisassemblyGraph:
    """Convenience: load a file from disk and normalize it in one call."""
    raw = load_json(path)
    return normalize(raw, source_path=os.fspath(path))


# =============================================================================
# INTERNAL HELPERS  (one small, testable function per concern)
# =============================================================================

def _build_node(shape: dict[str, Any]) -> GraphNode:
    """
    Map one raw node shape onto a canonical GraphNode.

    - `type` is mapped onto NodeType; an unrecognized value becomes
      NodeType.UNKNOWN (the validator reports it; we do not crash — FR 2.0
      requires checking for valid node types, which means we must be able to
      represent an invalid one).
    - The display label is taken from `text`, falling back to `name` /
      `component_name` (different source fields seen across files).
    - `weight` is kept as a string regardless of source type (int in Bialetti,
      str elsewhere); stringifying here keeps GraphNode's type contract simple
      and defers numeric parsing to the IR layer.
    - Any field not in _KNOWN_NODE_FIELDS is preserved in `extra`.
    """
    raw_type = shape.get("type")
    # The desktop exporter writes root ComponentBox nodes as legacy products.
    if raw_type == "product":
        raw_type = "component"
    try:
        node_type = NodeType(raw_type)
    except ValueError:
        node_type = NodeType.UNKNOWN

    # The label source differs BY ROLE:
    #  - ACTION nodes: the human-readable instruction lives in `step_description`
    #    (in Bialetti `text` is only a code like "D1.1"; in other files the two
    #    coincide). step_description is present for every action across all six
    #    files, so it is the safe primary, falling back to text/name.
    #  - other nodes (component/diamond): the name lives in text/name.
    if node_type is NodeType.ACTION:
        text = (shape.get("step_description") or shape.get("text")
                or shape.get("name") or "")
    else:
        text = shape.get("text") or shape.get("name") or shape.get("component_name") or ""

    weight = shape.get("weight")
    weight_str = None if weight is None or weight == "" else str(weight)

    # Coordinates: keep as float when present (loader uses them to order
    # sibling fan-outs); tolerate missing/None.
    x = _as_float(shape.get("x"))
    y = _as_float(shape.get("y"))

    # material/color: sources carry either an id (material_id/color_id) or a
    # name. We keep whatever is present as a string; resolving ids to names is
    # out of scope for the load phase.
    material = _first_present(shape, ("material",))
    color = _first_present(shape, ("color",))

    # tools: kept as the raw string the source gives (actions carry individual
    # tools, diamonds carry a comma-separated aggregate — verified on Bialetti/
    # Oranfresh/Epson: always a string). First-class because the IR consumes it;
    # leaving it in `extra` would mean a contract field fished out of the
    # "unrecognized" bag. Defensive: a list (never seen) is joined, anything
    # else is stringified; splitting/dedup is the IR layer's job.
    raw_tools = shape.get("tools")
    if raw_tools in (None, ""):
        tools = None
    elif isinstance(raw_tools, (list, tuple)):
        tools = ", ".join(str(t) for t in raw_tools)
    else:
        tools = str(raw_tools)

    extra = {k: v for k, v in shape.items() if k not in _KNOWN_NODE_FIELDS}

    return GraphNode(
        id=shape["id"],
        type=node_type,
        text=text,
        x=x,
        y=y,
        weight=weight_str,
        weight_unit=shape.get("weight_unit") or None,
        material=material,
        color=color,
        image_path=shape.get("image_path") or None,
        tools=tools,
        extra=extra,
    )


def _edge_from_connection(conn: dict[str, Any]) -> Edge:
    """Canonicalize either supported connection endpoint naming convention."""
    src = conn.get("from_shape_id", conn.get("from_id"))
    dst = conn.get("to_shape_id", conn.get("to_id"))
    return Edge(src=src, dst=dst)


def _edge_from_arrow(arrow: dict[str, Any]) -> Edge:
    """Canonicalize an arrow-shape edge (from_shape_id/to_shape_id)."""
    return Edge(src=arrow["from_shape_id"], dst=arrow["to_shape_id"])


def _as_float(value: Any) -> float | None:
    """Best-effort float conversion; None stays None, garbage becomes None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(shape: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty value among `keys`, as a string, or None."""
    for key in keys:
        val = shape.get(key)
        if val not in (None, ""):
            return str(val)
    return None