"""
linearizer.py — turn a normalized graph into an ordered list of Steps.

RESPONSIBILITY: walk the disassembly graph from its root and produce the flat,
ordered `Guide.steps`, applying the depth cut chosen by the user (FR 3.0). This
is the half of the load phase that encodes the disassembly grammar; validation
(validation.py) is the other half. The two are separate because they answer
different questions: validation asks "is this graph well-formed?", linearization
asks "in what order does one take it apart?".

THE GRAMMAR THIS ENCODES (confirmed empirically on Bialetti / Maria / Epson):
  - A diamond is a MACRO operation. Its ACTION children form a linear CHAIN
    (action_1 -> action_2 -> ...) describing HOW to perform it; the chain never
    branches and never mixes with components, so its order is purely topological.
  - A diamond's COMPONENT children are the RESULTS. At most ONE of them
    "continues" (leads onward to a further diamond); the rest are leaf outputs.
    Components are siblings with no topological order among them, so they are
    ordered by canvas geometry (x, then y) — the only ordering signal available.
  - Every diamond is reachable from the single root by following continuations.

TRAVERSAL ORDER: depth-first (DFS), one branch fully before the next. A
disassembly guide is executed one sub-system at a time, so DFS reads naturally;
breadth-first would interleave unrelated sub-systems step by step. (The URS says
"BFS with limited depth"; that phrase concerns the depth-CUT concept — stopping
at a level — not the order in which finished steps are listed. Depth is the
number of nested operations from the root, which we track with a counter
regardless of visitation order; we list steps branch-by-branch for readability.)

IMPLEMENTATION: an explicit stack, not recursion. This matches the cycle
detector in validation.py (one traversal technique across the package) and
cannot hit Python's recursion limit on a very deep model — the "survives the
course / reused by a later group" requirement makes deep inputs a real future
case, not a hypothetical. The cost is small and well-understood for a DFS.

NON-BLOCKING: like validation, linearization never raises on a malformed graph.
A cycle is broken by a visited-set; a missing piece yields a best-effort step.
The user may always proceed (FR 2.3).
"""

from __future__ import annotations

from .models import (
    Action,
    Component,
    DepthMode,
    DepthSpec,
    DisassemblyGraph,
    GraphNode,
    NodeType,
    Step,
    TraversalMode,
)


def linearize(
    graph: DisassemblyGraph,
    depth: DepthSpec,
    traversal: TraversalMode = TraversalMode.STRICT,
) -> tuple[Step, ...]:
    """
    Produce the ordered tuple of Steps for the given graph and depth choice.

    `traversal` controls how a grammar-violating graph is handled (orthogonal to
    depth): STRICT (default) follows only the grammatical continuation chain;
    LENIENT (not yet implemented) would maximize coverage on malformed graphs.

    Returns an empty tuple for an empty graph (validation reports that
    separately). Never raises on a malformed-but-parsable graph in STRICT mode;
    never mutates the graph.
    """
    if traversal is TraversalMode.LENIENT:
        raise NotImplementedError(
            "LENIENT traversal is reserved for a future need and not yet "
            "implemented. Use TraversalMode.STRICT (the default), which follows "
            "the grammatical continuation chain. LENIENT would visit all reachable "
            "diamonds including non-grammatical parallel branches; it was left "
            "unimplemented deliberately to avoid an untested second traversal "
            "until a real use case requires it."
        )

    root = find_root(graph)
    if root is None:
        return ()

    steps: list[Step] = []
    visited: set[int] = set()  # diamond ids already turned into a step (anti-cycle)

    # The traversal stack holds (diamond_id, depth, source_component_id):
    # `source` is the component the operation is performed ON — the root for
    # the start diamonds, the continuing composite afterwards. We thread it
    # through the traversal because the step must DECLARE its input (schema
    # 1.1): on a branched model a flat step list cannot otherwise tell which
    # piece a step opens. The stack is seeded in REVERSE order: it is LIFO, so
    # pushing the first-by-geometry diamond LAST makes it pop FIRST, giving
    # left-to-right DFS order. This reversed() is the classic stack-for-DFS
    # subtlety — without it the branches come out mirrored.
    start_diamonds = _ordered_next_diamonds(graph, root)
    stack: list[tuple[int, int, int]] = [
        (d, 0, root) for d in reversed(start_diamonds)
    ]

    while stack:
        diamond_id, depth_level, source_id = stack.pop()
        if diamond_id in visited:
            continue  # cycle or shared sub-graph: break here, do not loop
        visited.add(diamond_id)

        step, continuations = _build_step(
            graph, diamond_id, source_id,
            index=len(steps) + 1, depth=depth, depth_level=depth_level,
        )
        steps.append(step)

        # Push the children we will descend into. `continuations` lists
        # (next_diamond_id, its_source_component_id) pairs we did NOT cut;
        # pushed reversed for DFS order.
        for next_diamond, next_source in reversed(continuations):
            stack.append((next_diamond, depth_level + 1, next_source))

    return tuple(steps)


# =============================================================================
# STEP CONSTRUCTION
# =============================================================================

def _build_step(
    graph: DisassemblyGraph,
    diamond_id: int,
    source_id: int,
    index: int,
    depth: DepthSpec,
    depth_level: int,
) -> tuple[Step, list[tuple[int, int]]]:
    """
    Build one Step from a diamond, and return (step, continuations), where
    continuations is a list of (next_diamond_id, source_component_id) pairs to
    descend into. `source_id` is the component this operation is performed ON
    (the step's `input`): the root for a start diamond, the continuing
    composite the traversal arrived through otherwise.

    Separates the diamond's children by ROLE (by NodeType, never by array
    position): the action child opens the instruction chain; the component
    children are the results. Among the components, the one that continues is
    found by TOPOLOGY (it leads onward to a diamond); the rest are leaves.

    GRAMMAR (supervisor-confirmed): a composite continues into EXACTLY ONE
    operation — disassembly is a linear chain ("extract one, the rest
    continues"), not a tree. So at most one component continues, and that
    component leads to exactly one onward diamond. A component feeding several
    diamonds is an anomaly (reported by rule_composite_single_continuation); here
    we proceed best-effort by following ONE continuation (the first by geometry)
    and ignoring the rest — following them all would encode the wrong grammar.

    Depth cut: for the continuing component, ask should_stop(). If we stop, the
    component is emitted as a kept-whole leaf output (with its hidden-leaf count)
    and we do NOT descend.
    """
    diamond = graph.nodes[diamond_id]

    # --- the action chain (linear, topological order) ----------------------
    actions = _collect_action_chain(graph, diamond_id)

    # --- the component children, ordered by geometry ------------------------
    component_children = [
        k for k in graph.out_adj.get(diamond_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.COMPONENT
    ]
    component_children = _order_by_geometry(graph, component_children)

    outputs: list[Component] = []
    continues_as: list[Component] = []
    next_diamonds_to_descend: list[tuple[int, int]] = []

    for comp_id in component_children:
        onward_diamond = _continuation_diamond(graph, comp_id)

        if onward_diamond is None:
            # natural leaf: a final extracted part
            outputs.append(_to_component(graph.nodes[comp_id]))
            continue

        # This component continues the disassembly. Per the supervisor-confirmed
        # grammar, a single DIAMOND may produce SEVERAL continuing composites,
        # each disassembled along its own branch (the structure is a tree that
        # branches on a diamond's OUTPUTS — not a composite feeding two diamonds,
        # which remains forbidden and is flagged by validation). So we descend
        # into EVERY continuing output, not just the first. The traversal is DFS
        # (one branch fully before the next), so the flat step list stays
        # readable; the IR shape is unchanged.
        if should_stop(depth, graph.nodes[comp_id], depth_level + 1):
            # depth cut: keep this sub-assembly whole, count what is hidden inside
            leaf_count = _count_hidden_leaves(graph, comp_id)
            outputs.append(_to_component(
                graph.nodes[comp_id], kept_whole=True, contained_leaf_count=leaf_count
            ))
        else:
            comp = _to_component(graph.nodes[comp_id])
            # EVERY continuing composite is recorded (schema 1.1): before, only
            # the first went into continues_as and the others appeared nowhere
            # in the step — on a branched model the reader could not see that a
            # second sub-assembly continues. The step that opens each entry is
            # the later step whose input.node_id matches comp.node_id.
            continues_as.append(comp)
            next_diamonds_to_descend.append((onward_diamond, comp_id))

    step = Step(
        index=index,
        operation=diamond.text,
        input=_to_component(graph.nodes[source_id]),
        actions=tuple(actions),
        outputs=tuple(outputs),
        continues_as=tuple(continues_as),
        tools_required=_collect_tools(actions, diamond),
    )
    return step, next_diamonds_to_descend


# =============================================================================
# DEPTH CUT PREDICATE
# =============================================================================

def should_stop(depth: DepthSpec, node: GraphNode, depth_level: int) -> bool:
    """
    Decide whether to STOP descending at a continuing component (keep it whole).

    One predicate, parametric on DepthSpec — the traversal is identical for all
    modes; only this answer changes. Adding a future depth mode means adding a
    branch here, not rewriting the traversal.

      FULL      : never stop (no limit at all — not "a large limit"; we do not
                  even look at depth_level).
      KEEP_MAIN : stop once we are past the first level of operations
                  (depth_level >= 1) — keep main assemblies whole.
      MANUAL    : stop at the specific nodes the user designated.
    """
    if depth.mode is DepthMode.FULL:
        return False
    if depth.mode is DepthMode.KEEP_MAIN:
        return depth_level >= 1
    if depth.mode is DepthMode.MANUAL:
        return node.id in depth.keep_whole_ids
    return False  # unknown mode: safest is to not cut


# =============================================================================
# GRAPH-WALKING HELPERS  (small, pure, individually testable)
# =============================================================================

def find_roots(graph: DisassemblyGraph) -> list[int]:
    """All candidate roots: nodes with no incoming edge FROM AN EXISTING NODE
    and at least one outgoing edge TO an existing node.

    Only edges between nodes that actually exist confer parent/child status.
    A dangling edge (an endpoint id absent from the model — reported by
    validation's `dangling_edges` rule) must not alter who the root is:
    without this filter, a single ghost edge pointing AT the true root gives
    it a phantom predecessor, no root is found, and the whole guide comes out
    empty — the opposite of best-effort (FR 2.3). A fully isolated node is
    still not a root (it starts nothing).

    Defined ONCE, here, and reused by validation (validation._roots delegates
    to this function): "what is a root" is a single concept, and the
    dishwasher stress-test showed that duplicating its definition is exactly
    how the two halves of the load phase drift apart.
    """
    return [
        nid for nid in graph.nodes
        if not any(p in graph.nodes for p in graph.inc_adj.get(nid, ()))
        and any(k in graph.nodes for k in graph.out_adj.get(nid, ()))
    ]


def find_root(graph: DisassemblyGraph) -> int | None:
    """The node where disassembly starts, per find_roots. None if there is none.

    Public because more than one stage needs the root (linearization and the
    builder's product extraction). If several nodes qualify (multiple roots — a
    validation warning), we pick the first deterministically so linearization
    still produces a guide (FR 2.3)."""
    roots = find_roots(graph)
    if not roots:
        return None
    return sorted(roots)[0]


def _ordered_next_diamonds(graph: DisassemblyGraph, node_id: int) -> list[int]:
    """Diamonds directly reachable from a node, ordered by geometry."""
    diamonds = [
        k for k in graph.out_adj.get(node_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
    ]
    return _order_by_geometry(graph, diamonds)


def _continuation_diamond(graph: DisassemblyGraph, component_id: int) -> int | None:
    """The diamond a component leads onward to, or None if it is a leaf.

    By the grammar a continuing component has exactly one onward diamond; if a
    malformed graph gives several, we take the first by geometry so we still
    descend somewhere (best-effort)."""
    onward = [
        k for k in graph.out_adj.get(component_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
    ]
    if not onward:
        return None
    return _order_by_geometry(graph, onward)[0]


def _collect_action_chain(graph: DisassemblyGraph, diamond_id: int) -> list[Action]:
    """
    Collect every action node belonging to a diamond's operation, in order.

    A diamond's instructions may be modelled two ways (both valid — they only
    differ topologically):
      - CHAINED: one action child, then action -> action -> ... in sequence
        (Bialetti / Maria / Epson). Order is topological.
      - FAN-OUT: several action children hanging directly off the diamond, not
        linked to each other (Oranfresh). Siblings have no topological order, so
        they are ordered by geometry (x, then y) — exactly as component fan-outs
        are (nespresso). A mix of the two is handled too.

    Algorithm: do a small traversal from the diamond following ONLY action edges,
    collecting every action reachable. Within the traversal, siblings are visited
    in geometry order, so both a chain and a fan-out come out in a sensible
    reading order. A `seen` set guards against a malformed cyclic action graph.

    This replaces the earlier chain-only logic, which silently collected just the
    first action when the others were fan-out children — losing most of the
    instructions with no warning (observed on Oranfresh: 7 instructions, 1 kept).
    """
    # All action children directly under the diamond, in geometry order.
    heads = _order_by_geometry(graph, [
        k for k in graph.out_adj.get(diamond_id, ())
        if k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
    ])
    if not heads:
        return []

    actions: list[Action] = []
    seen: set[int] = set()
    # Stack-based DFS over action edges. Push heads reversed so the first by
    # geometry is processed first (LIFO), keeping reading order.
    stack: list[int] = list(reversed(heads))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        actions.append(_to_action(graph.nodes[current]))
        # follow any action successors of this action (the chained case), in
        # geometry order
        successors = _order_by_geometry(graph, [
            k for k in graph.out_adj.get(current, ())
            if k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
        ])
        for nxt in reversed(successors):
            if nxt not in seen:
                stack.append(nxt)
    return actions


def _count_hidden_leaves(graph: DisassemblyGraph, component_id: int) -> int:
    """
    Count the leaf components hidden under a kept-whole sub-assembly.

    Explores the sub-graph below `component_id` (following all edges) and counts
    component nodes that are themselves leaves (no further component output). A
    visited-set guards against cycles. This is what tells the user how many real
    parts are inside a block they chose not to open.
    """
    leaves = 0
    seen: set[int] = set()
    stack = [component_id]
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in graph.nodes:
            continue
        seen.add(nid)
        children = [k for k in graph.out_adj.get(nid, ()) if k in graph.nodes]
        # a component with no onward component/diamond is a physical leaf
        has_onward = any(
            graph.nodes[k].type in (NodeType.COMPONENT, NodeType.DIAMOND)
            for k in children
        )
        if graph.nodes[nid].type is NodeType.COMPONENT and not has_onward \
                and nid != component_id:
            leaves += 1
        stack.extend(children)
    return leaves


def _order_by_geometry(graph: DisassemblyGraph, node_ids: list[int]) -> list[int]:
    """
    Order sibling node ids by canvas position: left-to-right (x), then top-to-
    bottom (y). This is the only ordering signal for component fan-outs, whose
    siblings have no topological order (confirmed on nespresso, where edge
    arrival order is meaningless and x gives the natural reading order). Nodes
    with missing coordinates sort first (treated as 0) deterministically.
    """
    def key(nid: int) -> tuple[float, float]:
        node = graph.nodes[nid]
        return (node.x if node.x is not None else 0.0,
                node.y if node.y is not None else 0.0)
    return sorted(node_ids, key=key)


# =============================================================================
# GraphNode -> IR translation
# =============================================================================

def _to_component(
    node: GraphNode,
    kept_whole: bool = False,
    contained_leaf_count: int | None = None,
) -> Component:
    """Translate a graph component node into an IR Component (parse weight here)."""
    return Component(
        node_id=node.id,
        name=node.text,
        weight=_parse_weight(node.weight),
        weight_unit=node.weight_unit,
        material=node.material,
        material_details=node.extra.get("material_details", {}),
        color=node.color,
        image_path=node.image_path,
        kept_whole=kept_whole,
        contained_leaf_count=contained_leaf_count,
    )


def _to_action(node: GraphNode) -> Action:
    """Translate a graph action node into an IR Action.

    `tools` is the raw string as the source gave it (the adapter models it
    first-class on GraphNode); splitting and deduplication happen only at the
    step level (_collect_tools), so the per-action value stays a faithful
    mirror of the input."""
    return Action(
        node_id=node.id,
        text=node.text,
        tools=node.tools,
        image_path=node.image_path,
    )


def _parse_weight(weight: str | None) -> float | None:
    """Parse the raw weight string into a float; None/blank/garbage -> None."""
    if weight is None:
        return None
    try:
        return float(weight)
    except (TypeError, ValueError):
        return None


def _split_tools(raw: str | None) -> list[str]:
    """Split a source tools string into individual tool names.

    The Builder writes tool LISTS as comma-separated strings (verified on
    Bialetti: every diamond carries e.g. "Torx T10, Phillips PH1, plastic pry
    tool"). Treating ',' as the list separator is a documented assumption about
    the Builder's serialization, not an interpretation of the label's meaning;
    a tool name containing a comma would be split wrongly (none observed in
    any real file)."""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _collect_tools(actions: list[Action], diamond: GraphNode) -> tuple[str, ...]:
    """The step's tool list: split, deduplicated, action-first.

    Sources carry tools at TWO levels (verified on Bialetti/Oranfresh/Epson):
    each action carries its own tools, and the diamond carries a comma-separated
    AGGREGATE of them. The action tools are authoritative when present — they
    are more complete than the aggregate (Bialetti: "Soft cloth" and "Hands"
    appear only on actions) — so unioning both would double near-duplicates
    ("Torx T10" + "Torx T10 screwdriver") and bloat every generator's tool list.
    The diamond aggregate is used only as a FALLBACK, which is exactly the
    self-explanatory-diamond case (0 actions, air fryer: 12/16 diamonds): there
    it is the only tool source and was previously dropped silently.

    Deduplication is case-insensitive (first spelling wins) to avoid
    "Hands"/"hands" style duplicates; order is first-appearance."""
    seen: dict[str, str] = {}
    for action in actions:
        for tool in _split_tools(action.tools):
            seen.setdefault(tool.casefold(), tool)
    if not seen:
        for tool in _split_tools(diamond.tools):
            seen.setdefault(tool.casefold(), tool)
    return tuple(seen.values())