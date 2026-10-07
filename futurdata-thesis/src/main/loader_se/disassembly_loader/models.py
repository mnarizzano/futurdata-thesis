"""
models.py — the data vocabulary of the Disassembly Wizard load phase.

This module defines *only* data structures, no logic. It is the shared
vocabulary that every other module (adapter, loader, emitter) and every
downstream generator (PDF, TXT, MD, HTML, PPTX, DOCX, VIDEO) speaks.

WHY THIS FILE EXISTS AND WHY IT IS SPLIT IN TWO LEVELS
------------------------------------------------------
There are two independent axes along which these structures change:

  1. The INPUT format (the Builder's JSON) can change: a new field, a new
     convention from a teammate's graph. This affects the GRAPH-LEVEL objects.
  2. The OUTPUT contract (what the 7 generators consume) can change: a
     teammate asks for one more field in a step. This affects the IR-LEVEL
     objects.

These two axes move independently — we have already observed the input axis
move twice (edges stored as `arrow` shapes vs. a `connections` array;
`from_shape_id`/`to_shape_id` vs. `from_id`/`to_id`). Keeping graph objects and
IR objects separate means a change on one axis never forces a change on the
other. This is the Single Responsibility Principle applied because the two
responsibilities genuinely exist here, not for doctrine.

A second reason: the GRAPH level must be able to represent *invalid* graphs
(a cycle, an action node with 4 children, a dangling edge), because we must
first represent a broken graph in order to validate and report it. The IR
level, by contrast, represents *only* well-formed, linearized guides — once
you hold a `Step`, it is correct by construction. Mixing the two would force
`Step` to also model malformation, losing that guarantee.

IMMUTABILITY (frozen dataclasses)
---------------------------------
Every object here is `frozen=True`. The rule we follow: freeze when the object
is born complete. All of these are constructed fully in one shot (the adapter
builds each GraphNode complete; the loader builds each Step complete), so
freezing costs nothing in construction verbosity and buys us safety — 7
downstream consumers receive these objects (or their JSON dump) and none of
them can mutate a guide by accident. This also honours NFR 2.1 (no destructive
operations on the model).

NOTE ON frozen + collections: `frozen=True` makes the *field binding*
immutable, not the object it points to. A frozen dataclass with a `list` field
still allows `obj.mylist.append(...)`. To get real immutability for
collections we use `tuple`, not `list`, for every multi-value field in the IR
objects. This is a deliberate choice, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# =============================================================================
# EXCEPTIONS
# =============================================================================

class UnparsableModelError(Exception):
    """
    Raised ONLY when the input cannot be interpreted as a model graph at all.

    The boundary (decided against URS FR 2.0/2.2/2.3): if we can build a graph,
    any defect in it (cycle, multiple roots, orphan node, action-as-hub, even an
    edge pointing to a non-existent id) is a *validation warning* — never an
    exception — because FR 2.3 grants the user the right to proceed despite
    validation warnings. An exception is reserved for the case where there is no
    graph to validate in the first place:
      - the JSON is syntactically corrupt and does not parse;
      - the top-level `shapes` key is missing;
      - `shapes` is present but is not a list.

    Rule of thumb: "if I can construct a graph, every defect is a warning;
    if I cannot even construct it, that is an UnparsableModelError."

    The message must always state precisely what is missing or malformed, so the
    user knows what to fix (consistent with the spirit of FR 2.2).
    """


# =============================================================================
# VALIDATION WARNINGS
# =============================================================================

class Severity(str, Enum):
    """
    Severity of a validation finding.

    Inherits from `str` so it serializes directly to a readable JSON string
    ("info"/"warning"/"error") without a custom encoder.

    CRITICAL: severity grades *how bad* a finding is, it does NOT control flow.
    All three levels are NON-BLOCKING — even ERROR findings let the user proceed
    (URS FR 2.3). Severity exists so the GUI can colour/sort findings and the
    user can make an informed decision, satisfying FR 2.2 (precise reporting)
    without violating FR 2.3 (always allow proceeding).
    """

    INFO = "info"        # cosmetic / advisory, e.g. mass imbalance (FR 2.4)
    WARNING = "warning"  # real anomaly, guide still usable, e.g. a cycle
    ERROR = "error"      # serious malformation, e.g. edge to a non-existent id


@dataclass(frozen=True)
class ValidationWarning:
    """
    A single, point-by-point validation finding (URS FR 2.2, NFR 1.1).

    FR 2.2 and NFR 1.1 require that every finding localizes the exact element(s)
    of the JSON it refers to and explains why. That is why this is a structured
    object carrying `node_ids`, not a free-text string: a downstream GUI can
    highlight precisely those nodes, and the message explains the rule violated.

    Named `ValidationWarning` rather than `Warning` to avoid shadowing Python's
    built-in `Warning` class.

    Fields:
      rule      : short stable identifier of the rule that fired
                  (e.g. "single_root", "no_cycles", "action_out_degree").
                  Stable so tests can assert on it without matching prose.
      severity  : how serious — info / warning / error (all non-blocking).
      message   : human-readable explanation of what is wrong and why.
      node_ids  : the id(s) of the offending node(s)/edge(s) in the source JSON.
                  A tuple (immutable). Empty tuple only if the finding is truly
                  graph-global with no locatable element.
    """

    rule: str
    severity: Severity
    message: str
    node_ids: tuple[int, ...] = ()


# =============================================================================
# GRAPH LEVEL  (internal; produced by the adapter, consumed by the loader)
# =============================================================================

class NodeType(str, Enum):
    """
    The role of a graph node, per the URS grammar (section 1.2):
      - COMPONENT : a part (Root / Composite / Leaf — the distinction is
                    topological, not a separate type here).
      - DIAMOND   : a composite disassembly operation that produces components.
      - ACTION    : an atomic sub-step describing how a diamond's operation is
                    performed (a "step").

    UNKNOWN captures any node whose `type` we do not recognize. We keep it as a
    value rather than rejecting it, so the validator can *report* an unknown
    type (FR 2.0 requires "valid node types" to be checked) instead of crashing
    on it. This is the graph level's job: represent even the invalid.
    """

    COMPONENT = "component"
    DIAMOND = "diamond"
    ACTION = "action"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GraphNode:
    """
    One node of the disassembly graph, AFTER the adapter has normalized it.

    A single class with a `type` field, not one subclass per role. During
    parsing a node is just "a shape with a type"; splitting roles into
    subclasses here would complicate the adapter (it would have to decide the
    subclass while reading) with no benefit, because the loader dispatches on
    `type` anyway. Role-specific *meaning* is applied later, at the IR level.

    WHY WE KEEP COORDINATES (x, y)
    ------------------------------
    The IR we hand to teammates does NOT carry coordinates — there the step
    order is already resolved. But the loader *internally* needs them in one
    real case: when a node fans out to several children that are siblings (e.g.
    nespresso's action id=2 has 4 component children), the edges tell us "these
    4 are children" but give no order among them. The only residual ordering
    signal is geometry: left-to-right / top-to-bottom (x, then y). Observed in
    nespresso: Water Tank x=100, Drip Tray x=300, Capsule Bin x=500, Main
    Housing x=700 — ascending x yields the natural reading order. If we dropped
    coordinates in the adapter (which runs BEFORE the loader), the loader could
    no longer disambiguate. So coordinates live at the graph level and are
    dropped only when building the IR.

    WHY THE `extra` DICT
    --------------------
    Teammate formats already diverge, and FR 11.0 / NFR 2.0 call for future
    extensibility and interoperability. Any source field we don't explicitly
    model is preserved in `extra` rather than discarded, so a future format with
    a new attribute loses no information and does not break parsing. Costs one
    field; protects against silently dropping a field that turns out to matter
    downstream.

    Fields:
      id          : the node id from the source JSON (authoritative key).
      type        : the normalized NodeType.
      text        : the label/description shown to the operator. Treated as an
                    OPAQUE string — we never parse meaning out of it. (Confirmed
                    empirically: ordering lives in topology/geometry, not in
                    label text.)
      x, y        : canvas coordinates; loader-only, used to order sibling
                    fan-outs. May be None if a source omits them.
      weight      : nominal weight as given by the source. Kept as the raw
                    string here (sources store it as a string, sometimes ""),
                    parsed to a number only at the IR level where it is needed,
                    so the graph layer stays a faithful, lossless mirror of input.
      weight_unit : unit string (e.g. "g").
      material    : material identifier/name if present (component attribute we
                    DO need — feeds FR 4.0 material info downstream).
      color       : colour identifier if present (component attribute, FR 4.0).
      image_path  : path or URL to the node's image (FR 4.1). Kept as-is; not
                    embedded. The emitter decides path-vs-URL handling.
      tools       : the tools string as given by the source, on actions AND on
                    diamonds. First-class (not `extra`) because the IR contract
                    consumes it: actions carry individual tools; diamonds carry
                    a comma-separated aggregate, which is the ONLY tool source
                    when a self-explanatory diamond has no actions. Kept raw
                    here; splitting/deduplication happens at the IR level.
      extra       : any unrecognized source fields, preserved verbatim.
    """

    id: int
    type: NodeType
    text: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    weight: Optional[str] = None
    weight_unit: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    image_path: Optional[str] = None
    tools: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """
    A directed edge of the graph, AFTER normalization.

    The adapter's whole reason to exist is to produce these with canonical
    field names regardless of where the source stored edges:
      - teammate "Maria" stores edges as shapes of type "arrow" with
        `from_shape_id` / `to_shape_id`;
      - the Bialetti file stores them in a `connections` array with
        `from_id` / `to_id`.
    Both collapse to `src` -> `dst` here. From this point on, no other module
    knows those two formats ever existed.

    `src` and `dst` are node ids (ints), not GraphNode references, so an edge
    can point at an id that does not exist — which is exactly the dangling-edge
    anomaly the validator must detect and report as an ERROR-severity finding
    (not an exception).
    """

    src: int
    dst: int


@dataclass(frozen=True)
class DisassemblyGraph:
    """
    The complete normalized graph: the adapter's output, the loader's input.

    Construction note on immutability: individual GraphNode and Edge objects are
    born complete and frozen. This container, however, is assembled in steps
    (we accumulate adjacency while reading edges). We therefore build the
    adjacency maps in local mutable variables inside the adapter and freeze them
    into this object only once, at the end. The graph is "immutable after
    construction", not "immutable during construction".

    Fields:
      nodes      : mapping id -> GraphNode. A dict for O(1) lookup by id, which
                   the loader does constantly while traversing.
      edges      : tuple of all edges (immutable).
      out_adj    : id -> tuple of successor ids. Precomputed by the adapter so
                   the loader does not rebuild adjacency on every traversal
                   (helps NFR 4.0, interactive response times).
      inc_adj    : id -> tuple of predecessor ids. Used to find roots
                   (no predecessors) and to detect orphans / multiple roots.
      product_name : from metadata, if present.
      source_path  : where this graph was loaded from (for messages/provenance).

    out_adj/inc_adj use plain dicts of tuples. They are derived data (computable
    from `edges`), cached here purely for performance and convenience.
    """

    nodes: dict[int, GraphNode]
    edges: tuple[Edge, ...]
    out_adj: dict[int, tuple[int, ...]]
    inc_adj: dict[int, tuple[int, ...]]
    product_name: Optional[str] = None
    source_path: Optional[str] = None


# =============================================================================
# CONTROL PARAMETERS  (loader input)
# =============================================================================

class TraversalMode(str, Enum):
    """
    How the linearizer treats a graph that violates the disassembly grammar
    (orthogonal to DepthSpec, which controls how DEEP to go).

      STRICT  : follow every role-valid operation branch (a component may
                feed multiple operations). Invalid edge types are reported
                by validation; cycles are guarded during traversal.
                This is the default and the only mode implemented for now.
      LENIENT : maximize coverage on a malformed graph by visiting all reachable
                diamonds, even via non-grammatical parallel branches. Reserved
                for a future need; not yet implemented (the linearizer raises
                NotImplementedError) because no current use case requires it, and
                implementing an untested second traversal now would be
                over-engineering. The interface exists so it can be added later
                without changing call sites.
    """

    STRICT = "strict"
    LENIENT = "lenient"


class DepthMode(str, Enum):
    """
    The mutually-exclusive disassembly-depth options of URS FR 3.0.

      FULL      : full disassembly — descend to the deepest leaves.
      KEEP_MAIN : keep main assemblies whole — stop the descent at the first
                  level of major sub-assemblies (a fixed shallow cut).
      MANUAL    : the operator designates specific nodes to keep united; their
                  subtrees are pruned (the "sub-root" idea from section 1.2).
    """

    FULL = "full"
    KEEP_MAIN = "keep_main"
    MANUAL = "manual"


@dataclass(frozen=True)
class DepthSpec:
    """
    The depth parameter the loader receives (URS FR 3.0).

    OWNERSHIP: this type is owned by the load phase (us). Alhareth's GUI
    *populates* it from the user's choice, but the shape of the parameter is our
    contract — the GUI collects the value, we define what it means and how it is
    applied. Defining it here, rather than letting the GUI invent a format, keeps
    the boundary clean and defensible.

    Semantics of a cut: a node kept whole stops being a "Composite to be
    decomposed" and becomes a terminal Leaf output. The BFS that linearizes the
    graph simply stops descending at that node and emits it as a final block.
    No extra IR field is needed — the cut reuses the existing leaf/output
    representation.

    Fields:
      mode           : which of the three FR 3.0 options.
      keep_whole_ids : for MANUAL mode, the node ids the operator wants kept as
                       single blocks (subtrees below them are pruned). A tuple
                       (immutable); empty for FULL / KEEP_MAIN.

    INVARIANT (asserted in __post_init__): keep_whole_ids is meaningful only in
    MANUAL mode. We do not silently ignore a misuse — better to fail loudly
    during development than to produce a guide that quietly ignored the user's
    selection.
    """

    mode: DepthMode
    keep_whole_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.mode is not DepthMode.MANUAL and self.keep_whole_ids:
            raise ValueError(
                "keep_whole_ids is only valid with DepthMode.MANUAL "
                f"(got mode={self.mode.value} with ids={self.keep_whole_ids})"
            )


# =============================================================================
# IR LEVEL  (output; produced by the loader, serialized by the emitter,
#            consumed by all 7 generators)
# =============================================================================

@dataclass(frozen=True)
class Component:
    """
    A component as it appears in the IR — an output extracted during a step, or
    the product itself, or a block kept whole.

    This is NOT the same as GraphNode: GraphNode mirrors the raw input (weight as
    a string, coordinates, extra fields); Component is the cleaned, consumer-
    facing view (weight parsed to a number, no coordinates, only what a generator
    needs to print). The loader performs the GraphNode -> Component translation.
    This is a real transformation (parse, drop, rename), not a 1:1 copy — which
    is what justifies having two levels rather than one.

    Fields:
      node_id     : the source id, kept so a generator/GUI can cross-reference
                    back to the original node (e.g. for highlighting).
      name        : display name.
      weight      : nominal weight as a float, or None if the source left it
                    blank. Parsed here once so no generator has to.
      weight_unit : unit string (e.g. "g").
      material    : material name/id if known (FR 4.0).
      color       : colour if known (FR 4.0).
      image_path  : path or URL to the image (FR 4.1).
      kept_whole  : True when this output is a sub-assembly the user chose to
                    keep intact via a depth cut (FR 3.0), rather than a natural
                    leaf. A generator can render it distinctly ("kept whole — not
                    disassembled further"). False for ordinary leaves. Making the
                    depth choice VISIBLE in the output is the whole point of
                    FR 3.0; without this flag the cut would be invisible.
      contained_leaf_count : for a kept-whole block, how many leaf components it
                    would yield if fully disassembled — i.e. the physical pieces
                    hidden inside. Counts LEAVES (real final parts), not all
                    component nodes, because that is what tells the user whether
                    opening the block is worthwhile. None for ordinary leaves.
    """

    node_id: int
    name: str
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    image_path: Optional[str] = None
    kept_whole: bool = False
    contained_leaf_count: Optional[int] = None
    material_details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """
    One atomic sub-step (circle) within a disassembly operation.

    A diamond's operation may be described by a step telling the
    operator *how* to perform it. We keep actions as their own small object so a
    Step can carry its action with its own text, tools and image, which several
    output formats render distinctly from the component list.

    Fields:
      node_id     : source id (cross-reference).
      text        : the instruction text (opaque label).
      tools       : tools required for this action, as given by the source
                    (may be empty).
      image_path  : optional image for the action (FR 4.1).
    """

    node_id: int
    text: str = ""
    tools: Optional[str] = None
    image_path: Optional[str] = None


@dataclass(frozen=True)
class Step:
    """
    One disassembly operation in the linearized guide.

    GRANULARITY = ONE DIAMOND (URS FR 10.0). FR 10.0 asks to group steps sharing
    the same diamond-parent into a single paragraph/list. We honour that at the
    data level: a Step corresponds to one diamond, carrying its action(s) and the
    components that operation produces. Generators thus iterate Steps and render
    each as one grouped unit, with no grouping logic of their own.

    The role of each child is decided by node TYPE, never by position in the
    source arrays. (Observed: some diamonds list the component before the action;
    ordering by array position would emit steps in the wrong order, silently, in
    all 7 outputs.) `continues_as` vs `outputs` is decided by TOPOLOGY: the child
    that has an outgoing edge toward a further diamond is the one that continues;
    children without an outgoing edge are the extracted leaf outputs.

    Fields:
      index        : 1-based position of this step in the global execution order.
      operation    : the diamond's label (e.g. "Open outer shell"). Opaque text.
      input        : the component this operation is performed ON — the piece
                     entering the diamond (the root for the first step, a
                     continuing composite afterwards). Added in schema 1.1: on a
                     BRANCHED model (air fryer) a flat step list cannot otherwise
                     tell the reader which piece a step opens; generators need it
                     to say "now disassembling X" instead of treating each step
                     as a black box. On a linear chain, step[k].input equals
                     step[k-1]'s continuing component — the field makes that
                     explicit and branch-safe.
      actions      : the atomic sub-steps for this operation, in order. A tuple
                     (immutable). Usually one; modeled as many for robustness and
                     to absorb anomalies like an action-hub without losing data.
      outputs      : the components extracted by this operation (the leaves). A
                     tuple (immutable).
      continues_as : ALL components that carry the disassembly forward, in
                     descent order (schema 1.1: a tuple, because a diamond may
                     produce several continuing composites — output branching).
                     Empty for a terminal step or when every continuation was
                     kept whole by a depth cut. The step that opens each entry is
                     the later step whose `input.node_id` matches; consumers
                     reconstruct the branch structure from that key, not from
                     adjacency in the list.
      tools_required : union of tools across this step's actions (falling back
                     to the diamond's own aggregate when the actions carry
                     none), split on ',' and deduplicated case-insensitively —
                     a convenience so generators need not recompute it. A tuple
                     (immutable).
    """

    index: int
    operation: str
    input: Component
    actions: tuple[Action, ...] = ()
    outputs: tuple[Component, ...] = ()
    continues_as: tuple[Component, ...] = ()
    tools_required: tuple[str, ...] = ()
    image_path: Optional[str] = None


@dataclass(frozen=True)
class Guide:
    """
    The complete in-memory result of the load phase — what the emitter
    serializes to the IR JSON and what the 7 generators consume.

    SCHEMA INVARIANCE UNDER DEPTH: the *shape* of a Guide does not depend on the
    chosen DepthSpec; only its *content* (how many steps) does. full disassembly
    yields more steps, "keep main assemblies" yields fewer, but every Step has
    the same schema. Generators know nothing about depth — they receive an
    ordered list of steps. (This invariant is worth a dedicated test.)

    Fields:
      product       : the Root component (the whole product being disassembled).
      steps         : the ordered list of disassembly steps. A tuple (immutable);
                      order IS the execution order.
      warnings      : all validation findings (FR 2.0/2.2). Carried WITH the
                      guide, not raised, so the user can inspect them and still
                      proceed (FR 2.3). A tuple (immutable).
      depth         : the DepthSpec actually applied, recorded for provenance so
                      a consumer/report knows how this guide was cut.
      schema_version : version of the IR contract. Bumped only when the IR schema
                      changes, so the 7 consumers can detect an incompatible
                      guide. Frozen-early discipline + this field together protect
                      the downstream contract.
      tools         : union of tools_required across every step, deduplicated
                      case-insensitively, in first-appearance order. Added in
                      schema 1.1 for FR 1.3 (show the tools needed for the whole
                      disassembly at the top of the guide): computed once here
                      instead of 7 times in 7 generators.
      bill_of_materials : LEAF-ONLY tuple of the final extracted parts (including
                      kept-whole blocks under a depth cut), deduplicated by
                      node_id — intermediate composites are transition states and
                      would double-count mass (FR 2.4 spirit). None when not
                      requested (include_bom=False), emitted as null; an empty
                      tuple means "requested, and there are no parts". Serves
                      FR 1.3 (BoM at the top) and FR 9.1 (structured BoM export).
    """

    product: Component
    steps: tuple[Step, ...] = ()
    warnings: tuple[ValidationWarning, ...] = ()
    depth: Optional[DepthSpec] = None
    schema_version: str = "1.2"
    tools: tuple[str, ...] = ()
    bill_of_materials: Optional[tuple[Component, ...]] = None