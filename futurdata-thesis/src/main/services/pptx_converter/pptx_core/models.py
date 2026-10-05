"""Normalized data model used by the PPTX pipeline.

The adapter accepts dictionaries, dataclasses and ordinary objects returned by
the shared disassembly loader, then exposes one stable representation to the
validator and renderer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Iterable, Mapping


def _plain(value: Any) -> Any:
    """Convert dict/dataclass/ordinary loader objects into plain Python values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if is_dataclass(value):
        return _plain(asdict(value))
    if hasattr(value, "__dict__"):
        return {
            key: _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _mapping(value: Any) -> dict[str, Any]:
    result = _plain(value)
    if not isinstance(result, dict):
        raise TypeError(f"Expected an object/dictionary, received {type(value).__name__}.")
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]




def _image_reference(value: Any) -> str | None:
    """Normalize image metadata to a path, URL, or data-URI string.

    The shared loader may expose images as strings, dictionaries such as
    ``{"path": "images/step.jpg", "is_url": false}``, dataclasses, or
    small objects. Keeping one string representation prevents renderer errors
    when different loader revisions are used.
    """

    plain = _plain(value)
    if plain in (None, ""):
        return None
    if isinstance(plain, str):
        return plain.strip() or None
    if isinstance(plain, Mapping):
        for key in ("path", "url", "src", "data", "value"):
            candidate = plain.get(key)
            if candidate not in (None, ""):
                return str(candidate).strip() or None
    return str(plain).strip() or None

def _labels(value: Any) -> list[str]:
    values: list[str] = []
    for item in _as_list(value):
        if item is None:
            continue
        if isinstance(item, Mapping):
            label = item.get("name") or item.get("label") or item.get("text")
        else:
            label = item
        if label is not None and str(label).strip():
            values.append(str(label).strip())
    return values


def _material_text(name, details):
    parts = [str(name)] if name else []
    parts.extend(f"{k.replace('_name', '').replace('_', ' ').title()}: {v}" for k,v in (details or {}).items() if v is not None and str(v).strip())
    return "; ".join(parts) or None


@dataclass(slots=True)
class Component:
    node_id: int | str | None
    name: str
    weight: float | int | None = None
    weight_unit: str | None = None
    measured_weight: float | int | None = None
    material: Any = None
    color: Any = None
    quality: str | None = None
    destination: str | None = None
    image: str | None = None
    kept_whole: bool = False
    contained_leaf_count: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "Component | None":
        if value in (None, {}):
            return None
        data = _mapping(value)
        known = {
            "node_id", "id", "name", "weight", "weight_unit", "measured_weight",
            "actual_weight", "material", "color", "quality", "grading", "destination",
            "image", "image_path", "kept_whole", "contained_leaf_count",
        }
        return cls(
            node_id=data.get("node_id", data.get("id")),
            name=str(data.get("name") or data.get("label") or "Unnamed component").strip(),
            weight=data.get("weight"),
            weight_unit=data.get("weight_unit"),
            measured_weight=data.get("measured_weight", data.get("actual_weight")),
            material=_material_text(data.get("material"), data.get("material_details")),
            color=data.get("color"),
            quality=data.get("quality", data.get("grading")),
            destination=data.get("destination"),
            image=_image_reference(data.get("image") or data.get("image_path")),
            kept_whole=bool(data.get("kept_whole", False)),
            contained_leaf_count=data.get("contained_leaf_count"),
            extra={key: item for key, item in data.items() if key not in known},
        )

    @property
    def weight_label(self) -> str:
        if self.weight is None:
            return "Unknown"
        try:
            value = f"{float(self.weight):g}"
        except (TypeError, ValueError):
            value = str(self.weight)
        return f"{value} {self.weight_unit or ''}".strip()

    @property
    def measured_weight_label(self) -> str:
        if self.measured_weight is None:
            return "Not recorded"
        try:
            value = f"{float(self.measured_weight):g}"
        except (TypeError, ValueError):
            value = str(self.measured_weight)
        return f"{value} {self.weight_unit or ''}".strip()


@dataclass(slots=True)
class Action:
    node_id: int | str | None
    text: str
    tools: list[str] = field(default_factory=list)
    image: str | None = None
    safety_notices: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "Action":
        data = _mapping(value)
        known = {"node_id", "id", "text", "name", "tools", "image", "image_path", "safety", "safety_notices"}
        return cls(
            node_id=data.get("node_id", data.get("id")),
            text=str(data.get("text") or data.get("name") or "").strip(),
            tools=_labels(data.get("tools")),
            image=_image_reference(data.get("image") or data.get("image_path")),
            safety_notices=_labels(data.get("safety_notices", data.get("safety"))),
            extra={key: item for key, item in data.items() if key not in known},
        )


@dataclass(slots=True)
class Step:
    index: int
    operation: str
    source: Component | None = None
    source_explicit: bool = False
    actions: list[Action] = field(default_factory=list)
    outputs: list[Component] = field(default_factory=list)
    continues_as: list[Component] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    safety_notices: list[str] = field(default_factory=list)
    image: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "Step":
        data = _mapping(value)
        source_keys = ("source", "source_component", "input", "input_component", "parent_component")
        source_value = next((data.get(key) for key in source_keys if data.get(key) is not None), None)
        known = {
            "index", "operation", "name", *source_keys, "actions", "outputs", "continues_as",
            "tools_required", "tools", "safety", "safety_notices", "image", "image_path",
        }
        return cls(
            index=int(data.get("index", 0)),
            operation=str(data.get("operation") or data.get("name") or "Unnamed operation").strip(),
            source=Component.from_any(source_value),
            source_explicit=source_value is not None,
            actions=[Action.from_any(item) for item in _as_list(data.get("actions")) if item is not None],
            outputs=[
                component
                for item in _as_list(data.get("outputs"))
                if item is not None
                and (component := Component.from_any(item)) is not None
            ],
            continues_as=[component for item in _as_list(data.get("continues_as")) if item is not None and (component := Component.from_any(item)) is not None],
            tools_required=_labels(data.get("tools_required", data.get("tools"))),
            safety_notices=_labels(data.get("safety_notices", data.get("safety"))),
            image=_image_reference(data.get("image") or data.get("image_path")),
            extra={key: item for key, item in data.items() if key not in known},
        )

    @property
    def all_tools(self) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for tool in [*self.tools_required, *(tool for action in self.actions for tool in action.tools)]:
            key = tool.casefold()
            if key not in seen:
                seen.add(key)
                result.append(tool)
        return result

    @property
    def all_safety_notices(self) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for notice in [*self.safety_notices, *(item for action in self.actions for item in action.safety_notices)]:
            key = notice.casefold()
            if key not in seen:
                seen.add(key)
                result.append(notice)
        return result


@dataclass(slots=True)
class WarningItem:
    rule: str
    severity: str
    message: str
    node_ids: list[int | str] = field(default_factory=list)
    location: str = ""

    @classmethod
    def from_any(cls, value: Any) -> "WarningItem":
        data = _mapping(value)
        return cls(
            rule=str(data.get("rule", "unknown")),
            severity=str(data.get("severity", "warning")),
            message=str(data.get("message", "")),
            node_ids=[item for item in _as_list(data.get("node_ids")) if item is not None],
            location=str(data.get("location", "")),
        )


@dataclass(slots=True)
class WizardDocument:
    schema_version: str
    product: Component
    depth_mode: str = "full"
    keep_whole_ids: list[int | str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    bill_of_materials: list[Component] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_dir: str | None = None
    validation_issues: list[Any] = field(default_factory=list)

    @classmethod
    def from_any(cls, value: Any, source_dir: str | None = None) -> "WizardDocument":
        data = _mapping(value)
        product = Component.from_any(data.get("product"))
        if product is None:
            raise ValueError("The input does not contain a valid 'product' object.")
        depth_raw = _plain(data.get("depth") or {})
        depth = depth_raw if isinstance(depth_raw, dict) else {}
        return cls(
            schema_version=str(data.get("schema_version", "unknown")),
            product=product,
            depth_mode=str(depth.get("mode", data.get("depth_mode", "full"))),
            keep_whole_ids=list(depth.get("keep_whole_ids", data.get("keep_whole_ids", [])) or []),
            steps=[Step.from_any(item) for item in _as_list(data.get("steps")) if item is not None],
            warnings=[WarningItem.from_any(item) for item in _as_list(data.get("warnings")) if item is not None],
            bill_of_materials=[
                component
                for item in _as_list(data.get("bill_of_materials"))
                if item is not None
                and (component := Component.from_any(item)) is not None
            ],
            metadata=dict(_plain(data.get("metadata") or {})),
            source_dir=source_dir,
        )

    def selected_steps(
        self,
        start_step: int | None = None,
        end_step: int | None = None,
        max_action_groups: int | None = None,
    ) -> list[Step]:
        selected = [
            step for step in self.steps
            if (start_step is None or step.index >= start_step)
            and (end_step is None or step.index <= end_step)
        ]
        return selected[:max_action_groups] if max_action_groups else selected

    def source_for_step(self, position: int) -> tuple[Component | None, str]:
        """Resolve a step source without inventing a branch connection.

        Explicit source data is authoritative. The immediately previous
        ``continues_as`` is used only for a linear continuation. When the
        previous operation ended its branch, the source is intentionally left
        unknown rather than incorrectly reset to the product root.
        """
        step = self.steps[position]
        if step.source is not None:
            return step.source, "explicit"
        if position == 0:
            return self.product, "product_root"
        previous = self.steps[position - 1]
        if len(previous.continues_as) == 1:
            return previous.continues_as[0], "previous_continuation"
        return None, "unspecified_branch"

    def position_of(self, target: Step) -> int:
        for index, step in enumerate(self.steps):
            if step is target:
                return index
        for index, step in enumerate(self.steps):
            if step.index == target.index:
                return index
        raise ValueError(f"Step {target.index} is not part of this document.")

    @property
    def tools_summary(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for step in self.steps:
            for tool in step.all_tools:
                key = tool.casefold()
                if key not in seen:
                    seen.add(key)
                    result.append(tool)
        return result

    @property
    def safety_summary(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for step in self.steps:
            for notice in step.all_safety_notices:
                key = notice.casefold()
                if key not in seen:
                    seen.add(key)
                    result.append(notice)
        return result

    @property
    def total_bom_weight(self) -> float | None:
        values: list[float] = []
        for component in self.bill_of_materials:
            if component.weight is None:
                continue
            try:
                values.append(float(component.weight))
            except (TypeError, ValueError):
                continue
        return sum(values) if values else None

    def lookup_label(self, kind: str, value: Any) -> str:
        if value in (None, ""):
            return "Unknown"
        singular = kind[:-1] if kind.endswith("s") else kind
        candidates = [
            self.metadata.get(kind),
            self.metadata.get(singular),
            self.metadata.get(f"{kind}_lookup"),
            self.metadata.get(f"{singular}_lookup"),
            (self.metadata.get("lookups") or {}).get(kind),
            (self.metadata.get("lookups") or {}).get(singular),
        ]
        for mapping in candidates:
            if isinstance(mapping, dict):
                return str(mapping.get(str(value), mapping.get(value, value)))
            if isinstance(mapping, list):
                for item in mapping:
                    if isinstance(item, dict) and str(item.get("id")) == str(value):
                        return str(item.get("name") or item.get("label") or value)
        return str(value)

    def all_known_components(self) -> Iterable[Component]:
        yield self.product
        yield from self.bill_of_materials
        for step in self.steps:
            if step.source:
                yield step.source
            yield from step.outputs
            if step.continues_as:
                yield from step.continues_as
