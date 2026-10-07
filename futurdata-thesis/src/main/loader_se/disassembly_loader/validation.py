"""
validation.py — grammar and topology validation (URS FR 2.0, FR 2.2, NFR 3.1).

WHAT THIS MODULE DOES
---------------------
Given a normalized DisassemblyGraph, it checks the AND/OR-graph grammar and
topology required by FR 2.0 (single root, valid node types, role-consistent
connections, and topological anomalies: cycles, multiple roots, orphans) and
returns a flat list of point-by-point findings (FR 2.2 / NFR 1.1): each finding
names the exact node id(s) affected and explains why.

WHAT IT DOES NOT DO
-------------------
It never blocks. Per FR 2.3 the user may always proceed despite warnings, so
validation only *reports*; it raises nothing. (The un-parsable-input case is
handled earlier, in the adapter, with UnparsableModelError — by the time a
graph reaches here, it exists and can be inspected.) It also does not fix or
mutate the graph (NFR 2.1).

DESIGN: EXTENSIBLE RULE ENGINE (NFR 3.1)
----------------------------------------
A validation rule is a function with a uniform signature:

    def rule_x(graph: DisassemblyGraph) -> list[ValidationWarning]

The engine (`validate`) simply iterates an explicit list of rules and
concatenates their findings. Adding a rule = write a function + add one line to
ALL_RULES.

Why an explicit list and NOT a self-registering @rule decorator: a decorator
that auto-collects rules into a global registry is more "magic" — to know which
rules run you must know a registry is populated at import time, and rule order
becomes implicit. An explicit list shows every active rule in one place, in a
controlled order, and is trivial to explain and test. A decorator pays off when
rules are many and spread across files; here they are eight in one module, so
the registry solves a problem we do not have. This is the "scalable but not
over-engineered" line the supervisor drew.

SEVERITY POLICY
---------------
Severity is FIXED per rule (each rule always emits the same severity), which
makes every rule predictable and testable. The single exception is
`rule_single_root`: it detects two conditions of genuinely different gravity
with one inspection — zero roots (ERROR: nowhere to start, implies a
total cycle/degenerate graph) vs. multiple roots (WARNING: several entry
points, a guide can still be produced from one). Splitting it into two rules
would inspect the same thing twice; varying severity *within* the rule is
cleaner. No rule takes severity as an external parameter — severities are
decided inside the rules.
"""

from __future__ import annotations

from .linearizer import find_roots
from .models import (
    DisassemblyGraph,
    NodeType,
    Severity,
    ValidationWarning,
)


# =============================================================================
# THE ENGINE
# =============================================================================

def validate(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    Run every rule in ALL_RULES against the graph and collect all findings.

    Returns a flat list of ValidationWarning (possibly empty). Order is stable:
    findings appear grouped by rule, in the order rules are listed in ALL_RULES.
    Never raises; never mutates the graph.
    """
    findings: list[ValidationWarning] = []
    for rule in ALL_RULES:
        findings.extend(rule(graph))
    return findings


# =============================================================================
# HELPERS shared by rules
# =============================================================================

def _roots(graph: DisassemblyGraph) -> list[int]:
    """Node ids that are candidate roots of the disassembly.

    Delegates to linearizer.find_roots — the SINGLE definition of "root" in
    the package (no incoming edge from an existing node, at least one outgoing
    edge to an existing node; isolated nodes and dangling edges do not count).
    Validation and linearization must never disagree on who the root is: the
    dishwasher stress-test (an isolated node counted as a second root) was
    precisely such a divergence, so the definition now lives in one place.
    This import direction (validation -> linearizer) is safe: linearizer
    depends only on models, so no cycle exists."""
    return find_roots(graph)


def _in_degree(graph: DisassemblyGraph, nid: int) -> int:
    return len(graph.inc_adj.get(nid, ()))


def _out_degree(graph: DisassemblyGraph, nid: int) -> int:
    return len(graph.out_adj.get(nid, ()))


# Relative tolerance for the mass-balance check: leaf weights summing to within
# this fraction of the product weight are considered balanced. A small tolerance
# absorbs realistic rounding (Bialetti happens to balance exactly, but real
# models may round). Named so it is visible and easy to tune.
MASS_BALANCE_TOLERANCE = 0.01  # 1%


def _single_root_id(graph: DisassemblyGraph) -> int | None:
    """The unique root id, or None if there is not exactly one."""
    roots = _roots(graph)
    return roots[0] if len(roots) == 1 else None


def _weight_of(node) -> float | None:
    """Parse a node's raw weight string to float; None/blank/garbage -> None."""
    if node.weight is None:
        return None
    try:
        return float(node.weight)
    except (TypeError, ValueError):
        return None


def _leaf_components(graph: DisassemblyGraph) -> list[int]:
    """
    Ids of leaf component nodes: components with no onward component or diamond
    (the final physical parts). Excludes intermediate composites, whose weight
    would double-count.
    """
    leaves = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.COMPONENT:
            continue
        onward = [
            k for k in graph.out_adj.get(nid, ())
            if k in graph.nodes
            and graph.nodes[k].type in (NodeType.COMPONENT, NodeType.DIAMOND)
        ]
        if not onward:
            leaves.append(nid)
    return leaves


# =============================================================================
# RULES  (each: DisassemblyGraph -> list[ValidationWarning])
# =============================================================================

def rule_non_empty(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    The graph must contain at least one node.

    A syntactically valid file can still describe an empty model (shapes: []).
    That is parsable (the adapter builds an empty graph), so it is a validation
    finding, not an exception. Severity ERROR: there is nothing to disassemble.
    node_ids is empty because the finding is graph-global (no element to point
    at).
    """
    if not graph.nodes:
        return [ValidationWarning(
            rule="non_empty",
            severity=Severity.ERROR,
            message="The model contains no nodes; there is nothing to disassemble.",
        )]
    return []


def rule_dangling_edges(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    Every edge must connect two nodes that exist in the model.

    An edge whose source or destination id is absent from `nodes` (a "dangling"
    edge) is syntactically buildable — the Builder can save it — but cannot be
    interpreted: it points into nothing. This is the ERROR-severity finding
    promised by the Edge docstring in models.py (FR 2.0: connections consistent
    with the node roles — an endpoint that is no node at all is the extreme
    case). Non-blocking as always (FR 2.3): the linearizer and the other rules
    filter edges by node existence, and root detection (find_roots) counts only
    edges between existing nodes, so a single ghost edge cannot erase the true
    root and empty the guide.

    One finding listing every dangling edge (FR 2.2 / NFR 1.1: name the exact
    elements and why). node_ids carries every id involved: the existing
    endpoints can be highlighted by a GUI; the missing ids tell the modeller
    what the edges point at.
    """
    dangling = [
        (e.src, e.dst) for e in graph.edges
        if e.src not in graph.nodes or e.dst not in graph.nodes
    ]
    if not dangling:
        return []
    missing = sorted({i for pair in dangling for i in pair if i not in graph.nodes})
    listed = ", ".join(f"{s}->{d}" for s, d in dangling)
    return [ValidationWarning(
        rule="dangling_edges",
        severity=Severity.ERROR,
        message=f"{len(dangling)} edge(s) reference non-existent node id(s) "
                f"{missing}: {listed}. These edges cannot be interpreted and "
                f"are ignored by linearization.",
        node_ids=tuple(sorted({i for pair in dangling for i in pair})),
    )]


def rule_single_root(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    The graph must have exactly one root.

    A root is a node with no incoming edge from an existing node AND at least
    one outgoing edge to an existing node — the point where disassembly starts
    (the single definition lives in linearizer.find_roots). A fully isolated
    node (no edges at all) is NOT a root; it is an orphan, reported by
    rule_no_orphans. (This separation stops an isolated node being reported
    both as a spurious root here and as an orphan there — observed on the
    dishwasher model, node 60.) Dangling edges do not count either — they are
    rule_dangling_edges' concern and must not shift the root.

    THE ONE RULE WITH VARIABLE SEVERITY (see module docstring):
      - 0 roots  -> ERROR: no valid starting point (every node has a predecessor,
                    e.g. a total cycle, or only isolated nodes exist).
      - >1 roots -> WARNING: multiple entry points; linearization can still start
                    from one and produce a (partial) guide.
    """
    roots = _roots(graph)
    if not graph.nodes:
        return []  # emptiness is rule_non_empty's job, not ours
    if len(roots) == 0:
        return [ValidationWarning(
            rule="single_root",
            severity=Severity.ERROR,
            message="No valid root found: no node both lacks an incoming edge "
                    "and has an outgoing edge (the graph is fully cyclic, or has "
                    "only isolated nodes).",
        )]
    if len(roots) > 1:
        return [ValidationWarning(
            rule="single_root",
            severity=Severity.WARNING,
            message=f"Expected exactly one root, found {len(roots)}: "
                    f"nodes {sorted(roots)} start a disassembly path.",
            node_ids=tuple(sorted(roots)),
        )]
    return []


def rule_valid_node_types(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    Every node must have a recognized role (component / diamond / action).

    The adapter maps an unrecognized source `type` to NodeType.UNKNOWN rather
    than crashing, precisely so this rule can report it (FR 2.0: "valid node
    types"). Severity ERROR: an unknown node cannot be placed in the grammar.
    """
    bad = [nid for nid, n in graph.nodes.items() if n.type is NodeType.UNKNOWN]
    if bad:
        return [ValidationWarning(
            rule="valid_node_types",
            severity=Severity.ERROR,
            message=f"Nodes {sorted(bad)} have an unrecognized type and cannot "
                    f"be interpreted in the disassembly grammar.",
            node_ids=tuple(sorted(bad)),
        )]
    return []


def rule_no_orphans(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    No node may be isolated (no incoming AND no outgoing edge).

    An orphan is disconnected from the procedure: it cannot be reached during
    disassembly. The root legitimately has no incoming edge, so the root is NOT
    an orphan (it has outgoing edges). Severity WARNING: the rest of the guide
    is still usable; the orphan is simply unreachable. One finding per orphan
    is unnecessary — we report them together but list every id (FR 2.2).
    """
    orphans = [
        nid for nid in graph.nodes
        if _in_degree(graph, nid) == 0 and _out_degree(graph, nid) == 0
    ]
    if orphans:
        return [ValidationWarning(
            rule="no_orphans",
            severity=Severity.WARNING,
            message=f"Nodes {sorted(orphans)} are disconnected (no edges) and "
                    f"will not appear in the disassembly procedure.",
            node_ids=tuple(sorted(orphans)),
        )]
    return []


def rule_no_cycles(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    The disassembly graph must be acyclic (a DAG): you take things apart, you do
    not reassemble, so the procedure cannot loop (consistent with the URS scope).

    Detection: iterative DFS with a three-colour marking (white=unseen,
    grey=on the current path, black=finished). An edge to a grey node closes a
    cycle. Iterative (an explicit stack) rather than recursive so a large or
    pathological graph cannot hit Python's recursion limit (NFR 4.0 robustness).

    Severity WARNING, not ERROR: per FR 2.3 the user may still proceed, and the
    linearizer has its own cycle protection (a visited-set) so a cycle does not
    crash it — it is reported here and broken there.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[int, int] = {nid: WHITE for nid in graph.nodes}
    cycle_nodes: set[int] = set()

    for start in graph.nodes:
        if color[start] != WHITE:
            continue
        # stack holds (node, iterator over its successors)
        stack: list[tuple[int, iter]] = [(start, iter(graph.out_adj.get(start, ())))]
        color[start] = GREY
        on_path: list[int] = [start]
        while stack:
            node, succ = stack[-1]
            advanced = False
            for nxt in succ:
                if nxt not in color:
                    continue  # dangling edge target; reported by rule_dangling_edges
                if color[nxt] == GREY:
                    cycle_nodes.add(nxt)  # back-edge: nxt closes a cycle
                elif color[nxt] == WHITE:
                    color[nxt] = GREY
                    on_path.append(nxt)
                    stack.append((nxt, iter(graph.out_adj.get(nxt, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                if on_path and on_path[-1] == node:
                    on_path.pop()

    if cycle_nodes:
        return [ValidationWarning(
            rule="no_cycles",
            severity=Severity.WARNING,
            message=f"The graph contains at least one cycle involving "
                    f"node(s) {sorted(cycle_nodes)}; a disassembly graph must be "
                    f"acyclic. Linearization will break the cycle.",
            node_ids=tuple(sorted(cycle_nodes)),
        )]
    return []


def rule_action_degree(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """An instruction has one owner/predecessor and at most one next instruction.

    Component children describe parts produced by that instruction. They do
    not contribute to the action-chain degree and may coexist with a successor.
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.ACTION:
            continue
        indeg = _in_degree(graph, nid)
        action_successors = {
            child for child in graph.out_adj.get(nid, ())
            if child in graph.nodes and graph.nodes[child].type is NodeType.ACTION
        }
        outdeg = len(action_successors)
        if indeg > 1 or outdeg > 1:
            findings.append(ValidationWarning(
                rule="action_degree",
                severity=Severity.WARNING,
                message=f"Action node {nid} has {indeg} incoming edges and "
                        f"{outdeg} successor instructions; an instruction must "
                        f"have at most one predecessor and one next instruction.",
                node_ids=(nid,),
            ))
    return findings


def rule_diamond_grammar(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    A diamond (composite operation) must be executable: it either carries its own
    instructions, OR it is self-explanatory (its name is the instruction).

    GRAMMAR: a diamond is a MACRO operation. Optionally, steps hanging
    off it describe HOW to perform it (a chain action_1 -> action_2 -> ..., or a
    fan-out of direct action children — both supported). Its component children
    are the RESULTS.

    Actions are OPTIONAL. Some operations are self-explanatory from their name
    alone ("unscrew 4 screws", "remove the tray") and need no separate
    instructions — observed on the well-formed Air fryer model, where 12 of 16
    diamonds legitimately have no action and produce components directly. So a
    diamond with no action is NOT flagged as long as it is a real, executable
    operation: it has a non-empty name/operation AND produces at least one output.

    A diamond is only anomalous when it has no action AND is empty/incomplete —
    no name to act as the instruction, or no output produced (it does nothing).
    That is a genuine modelling gap, not a stylistic choice. Severity WARNING:
    best-effort linearization still yields a step regardless.
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.DIAMOND:
            continue
        has_action = any(
            k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
            for k in graph.out_adj.get(nid, ())
        )
        if has_action:
            continue  # has explicit instructions — fine

        # No action: acceptable only if the operation is self-explanatory, i.e.
        # it has a name AND produces at least one component output.
        has_name = bool(node.text and node.text.strip())
        produces_output = any(
            k in graph.nodes and graph.nodes[k].type is NodeType.COMPONENT
            for k in graph.out_adj.get(nid, ())
        )
        if has_name and produces_output:
            continue  # self-explanatory operation — valid, no instructions needed

        findings.append(ValidationWarning(
            rule="diamond_grammar",
            severity=Severity.WARNING,
            message=f"Diamond node {nid} has no instructions and is not "
                    f"self-explanatory (missing a name or producing no output); "
                    f"the operation cannot be carried out as modelled.",
            node_ids=(nid,),
        ))
    return findings


def rule_diamond_continuation(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    A diamond's outputs must be COMPONENTS, not another diamond directly.

    Per the grammar (supervisor-confirmed): a diamond is connected to its
    results, which are components — one or more of which may continue into a
    FURTHER diamond, but only THROUGH a component, never diamond-to-diamond
    directly. A direct diamond -> diamond edge (seen 5x in Epson, 0x in the
    clean reference files) skips the intermediate component that represents the
    partially disassembled assembly. It is NOT admitted by the grammar.

    CONSEQUENCE FOR THE GUIDE (this is what the finding must say honestly):
    the linearizer follows continuations only through components, so it does
    NOT traverse a diamond -> diamond edge. Every operation and part reachable
    ONLY through such an edge is absent from the generated guide (on Epson:
    2 of 13 operations linearized, 5 of 38 components appear). Severity ERROR:
    like an unknown node type, the edge cannot be placed in the grammar, and
    silent-looking content loss in all 7 outputs is a serious malformation —
    the model must be fixed upstream. Non-blocking as always (FR 2.3): the
    partial guide is still produced.
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.DIAMOND:
            continue
        diamond_children = [
            k for k in graph.out_adj.get(nid, ())
            if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
        ]
        if diamond_children:
            findings.append(ValidationWarning(
                rule="diamond_continuation",
                severity=Severity.ERROR,
                message=f"Diamond node {nid} connects directly to diamond(s) "
                        f"{sorted(diamond_children)}; a diamond's outputs must "
                        f"be components (an intermediate composite is missing). "
                        f"This edge is not traversed: any operation reachable "
                        f"only through it will NOT appear in the guide.",
                node_ids=(nid, *sorted(diamond_children)),
            ))
    return findings


def rule_composite_continuation_type(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    A component's outgoing edges must point to DIAMONDS, nothing else.

    Per the grammar (supervisor-confirmed): a component that is not yet fully
    taken apart continues into exactly ONE diamond. There is no grammatical
    edge component -> component (containment is expressed THROUGH operations,
    not directly) and no edge component -> action (actions hang off diamonds).
    This rule is the type-check that composite_single_continuation does not do:
    that rule counts diamond children and flags MORE than one, but a composite
    with ZERO diamond children and other children passed silently — the
    capsule-coffee-machine model (components as a containment hierarchy,
    actions as connectors) produced an EMPTY guide with no ERROR explaining
    why. Symmetric to rule_diamond_continuation, on the composite side.

    CONSEQUENCE FOR THE GUIDE (stated honestly, like diamond_continuation):
    the linearizer descends only through component -> diamond edges, so
    everything reachable only through a component -> component or
    component -> action edge is absent from the generated guide. Severity
    ERROR; non-blocking as always (FR 2.3).
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.COMPONENT:
            continue
        bad_children = [
            k for k in graph.out_adj.get(nid, ())
            if k in graph.nodes and graph.nodes[k].type is not NodeType.DIAMOND
        ]
        if bad_children:
            kinds = sorted({graph.nodes[k].type.value for k in bad_children})
            findings.append(ValidationWarning(
                rule="composite_continuation_type",
                severity=Severity.ERROR,
                message=f"Component node {nid} connects to {kinds} node(s) "
                        f"{sorted(bad_children)}; a component may only continue "
                        f"into a diamond (one operation). These edges are not "
                        f"traversed: anything reachable only through them will "
                        f"NOT appear in the guide.",
                node_ids=(nid, *sorted(bad_children)),
            ))
    return findings


def rule_composite_single_continuation(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """Describe operation fan-out without treating it as an invalid graph.

    All connected operations are exported; sibling execution order is not
    specified by topology. Keep the existing rule identifier for compatibility.
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.COMPONENT:
            continue
        onward = [
            k for k in graph.out_adj.get(nid, ())
            if k in graph.nodes and graph.nodes[k].type is NodeType.DIAMOND
        ]
        if len(onward) > 1:
            findings.append(ValidationWarning(
                rule="composite_single_continuation",
                severity=Severity.INFO,
                message=f"Component {nid} feeds {len(onward)} operations "
                        f"{sorted(onward)}. All operations are included with this "
                        f"component as input; sibling execution order is unspecified.",
                node_ids=(nid, *sorted(onward)),
            ))
    return findings


def rule_mass_balance(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    Mass-balance check (URS FR 2.4): the sum of the LEAF component weights should
    equal the product (root) weight.

    THREE outcomes, because weights are often unknown (FR 4.0 explicitly allows
    this — Maria's components carry no weight at all), and a naive two-way check
    would fire false positives on every weightless model:

      1. NOT VERIFIABLE — the root has no weight, or any leaf lacks a weight, so
         the sum is incomplete. We cannot judge balance. Severity INFO: this is
         information ("balance not checkable, N weights missing"), not a model
         error. The vast majority of real graphs may land here.
      2. BALANCED — all weights present and the leaf sum matches the root within
         MASS_BALANCE_TOLERANCE. No finding.
      3. IMBALANCED — all weights present but the sum does NOT match. THIS is the
         real anomaly. Severity WARNING, reporting the two totals and the gap.

    "Verifiable" is strict: it requires the root weight AND every leaf weight to
    be present. A single missing leaf weight makes the sum incomplete (observed:
    Epson's root has a weight but its leaves do not -> not verifiable).

    Leaves are component nodes with no onward component/diamond (the final
    physical parts); intermediate composites are excluded, as including them
    would double-count mass.
    """
    root_id = _single_root_id(graph)
    if root_id is None:
        return []  # root issues are rule_single_root's concern
    root_weight = _weight_of(graph.nodes[root_id])

    leaves = _leaf_components(graph)
    if not leaves:
        return []  # nothing to sum (e.g. a degenerate or all-hub graph)

    missing = [nid for nid in leaves if _weight_of(graph.nodes[nid]) is None]

    # Outcome 1: not verifiable
    if root_weight is None or missing:
        reason = []
        if root_weight is None:
            reason.append("the product has no weight")
        if missing:
            reason.append(f"{len(missing)} component(s) have no weight")
        return [ValidationWarning(
            rule="mass_balance",
            severity=Severity.INFO,
            message="Mass balance not verifiable: " + "; ".join(reason) + ".",
            node_ids=tuple(sorted(missing)),
        )]

    leaf_sum = sum(_weight_of(graph.nodes[nid]) for nid in leaves)

    # Outcome 2: balanced (within tolerance)
    if root_weight == 0:
        relative_gap = 0.0 if leaf_sum == 0 else 1.0
    else:
        relative_gap = abs(leaf_sum - root_weight) / root_weight
    if relative_gap <= MASS_BALANCE_TOLERANCE:
        return []

    # Outcome 3: imbalanced
    return [ValidationWarning(
        rule="mass_balance",
        severity=Severity.WARNING,
        message=f"Mass imbalance: leaf components sum to {leaf_sum:g} but the "
                f"product weighs {root_weight:g} "
                f"({relative_gap * 100:.1f}% off).",
        node_ids=(root_id,),
    )]


def rule_action_fanout(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    INFORMATIONAL note (not an anomaly): a diamond whose instructions are modelled
    as a FAN-OUT (several action children hanging directly off the diamond) rather
    than a CHAIN (action -> action -> ...).

    Both layouts are valid and fully supported by the linearizer — it collects all
    actions either way. This finding exists only to make the topological choice
    visible (severity INFO, like a missing-weight note), NOT to flag a problem. It
    does not say the model is wrong; it says "this operation lists its steps in
    parallel". Reported once per diamond that uses the fan-out layout.

    A diamond uses fan-out when it has more than one action child directly. (One
    action child, possibly followed by a chain, is the chained layout and gets no
    note.)
    """
    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        if node.type is not NodeType.DIAMOND:
            continue
        action_children = [
            k for k in graph.out_adj.get(nid, ())
            if k in graph.nodes and graph.nodes[k].type is NodeType.ACTION
        ]
        if len(action_children) > 1:
            findings.append(ValidationWarning(
                rule="action_fanout",
                severity=Severity.INFO,
                message=f"Diamond {nid} lists its {len(action_children)} "
                        f"instructions as a fan-out (parallel) rather than a chain; "
                        f"both layouts are supported and all instructions are kept.",
                node_ids=(nid,),
            ))
    return findings


def rule_root_declaration(graph: DisassemblyGraph) -> list[ValidationWarning]:
    """
    Coherence check (NOT a hard rule): the node identified as root by TOPOLOGY
    (no incoming edge) should agree with any `root_component_id` the source
    declares. Topology is authoritative; the declared field is only a
    cross-check, so a mismatch is INFO severity — informative, never blocking.

    We never trust the declared field to decide the root; we only flag when it
    contradicts the topology, so the modeller can notice an inconsistency in
    their model. The declared id lives in GraphNode.extra (the adapter preserves
    it there without interpreting it).
    """
    roots = _roots(graph)
    if len(roots) != 1:
        return []  # not our concern; rule_single_root handles root count
    topo_root = roots[0]

    findings: list[ValidationWarning] = []
    for nid, node in graph.nodes.items():
        declared = node.extra.get("root_component_id")
        # A node declares itself root when root_component_id points to its own id.
        if declared in (None, "", 0):
            continue
        try:
            declares_self = int(declared) == nid
        except (TypeError, ValueError):
            continue
        if declares_self and nid != topo_root:
            findings.append(ValidationWarning(
                rule="root_declaration",
                severity=Severity.INFO,
                message=f"Node {nid} declares itself root (root_component_id) "
                        f"but topology makes node {topo_root} the root.",
                node_ids=(nid, topo_root),
            ))
    return findings


# =============================================================================
# THE EXPLICIT RULE LIST  (extend by adding a function above and a line here)
# =============================================================================
# Order matters only for the order findings appear in; rules are independent.
# Structural/global checks first, then node-role checks, then the soft coherence
# check last.

ALL_RULES = [
    rule_non_empty,
    rule_dangling_edges,
    rule_single_root,
    rule_valid_node_types,
    rule_no_orphans,
    rule_no_cycles,
    rule_action_degree,
    rule_diamond_grammar,
    rule_diamond_continuation,
    rule_composite_continuation_type,
    rule_composite_single_continuation,
    rule_mass_balance,
    rule_action_fanout,
    rule_root_declaration,
]