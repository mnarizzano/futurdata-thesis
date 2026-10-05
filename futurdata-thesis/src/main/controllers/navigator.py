"""Transient topology projection of the active diagram; no exporter dependencies."""
from dataclasses import dataclass
from ..models import ArrowShape, ComponentBox, DiamondStep, ActionCircle


@dataclass(frozen=True)
class OutlineRow:
    item_id: str
    parent_id: str
    shape_id: int
    label: str


def topology_snapshot(diagram):
    """Use live endpoints from both supported edge stores, in persisted list order."""
    shapes = {shape.id: shape for shape in diagram.shapes}
    nodes = {key: shape for key, shape in shapes.items() if not isinstance(shape, ArrowShape)}
    edges, seen = [], set()
    unattached = []
    arrows = [shape for shape in diagram.shapes if isinstance(shape, ArrowShape)]
    for edge in list(diagram.connections) + arrows:
        source = getattr(getattr(edge, 'from_shape', None), 'id', None)
        target = getattr(getattr(edge, 'to_shape', None), 'id', None)
        if source not in nodes or target not in nodes:
            if isinstance(edge, ArrowShape):
                unattached.append(edge)
            continue
        pair = (source, target)
        if pair not in seen:
            seen.add(pair)
            edges.append(pair)
    rows = []
    for shape in list(nodes.values()) + unattached:
        root = False
        if isinstance(shape, ComponentBox):
            subtype = str(shape.properties.get('node_type', '')).strip()
            kind = f'{subtype} component' if subtype else 'Component'
            name = shape.properties.get('name') or shape.text
            root = subtype.lower() == 'root'
        elif isinstance(shape, DiamondStep):
            kind, name = 'Operation (diamond)', shape.name or shape.text
        elif isinstance(shape, ActionCircle):
            kind, name = 'Instruction (circle)', shape.text or shape.step_description
        else:
            kind, name = 'Unattached arrow', shape.text
        name = ' '.join(str(name or 'Unnamed').split())
        rows.append((shape.id, f'{kind}: {name}', root))
    return tuple(rows), tuple(edges)


def build_outline(snapshot):
    """Iterative, O(V+E) spanning forest with terminal shared/cycle references."""
    nodes, edges = snapshot
    labels = {key: label for key, label, _ in nodes}
    children = {key: [] for key in labels}
    incoming = set()
    for source, target in edges:
        children[source].append(target)
        incoming.add(target)
    # Topological roots first; Root semantics break ties without discarding others.
    ordered = sorted(nodes, key=lambda node: not node[2])
    roots = [key for key, _, _ in ordered if key not in incoming]
    roots.extend(key for key, _, _ in ordered if key in incoming)
    visited, active, rows = set(), set(), []
    for root in roots:
        if root in visited:
            continue
        stack = [(root, '', False)]
        while stack:
            key, parent, leaving = stack.pop()
            if leaving:
                active.remove(key)
                continue
            if key in visited:
                suffix = 'cycle' if key in active else 'reference'
                item = f'ref:{parent}:{key}'
                rows.append(OutlineRow(item, parent, key, f'{labels[key]} [{suffix}]'))
                continue
            item = f'node:{key}'
            rows.append(OutlineRow(item, parent, key, labels[key]))
            visited.add(key)
            active.add(key)
            stack.append((key, parent, True))
            stack.extend((child, item, False) for child in reversed(children[key]))
    return rows
