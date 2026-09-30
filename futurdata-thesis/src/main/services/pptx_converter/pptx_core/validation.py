"""Extensible validation rules for normalized disassembly guides.

Rules report precise locations and distinguish blocking errors from warnings
that can safely be printed in the presentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import Component, WizardDocument


@dataclass(slots=True)
class ValidationIssue:
    rule: str
    severity: str
    message: str
    location: str = ""
    node_ids: list[int | str] | None = None

    def __str__(self) -> str:
        location = f" ({self.location})" if self.location else ""
        return f"[{self.severity.upper()}] {self.rule}{location}: {self.message}"


class ValidationRule(Protocol):
    name: str

    def validate(self, document: WizardDocument) -> list[ValidationIssue]: ...


class CoreStructureRule:
    name = "core_structure"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if not document.product.name:
            issues.append(ValidationIssue(self.name, "error", "Product name is empty.", "product.name"))
        if not document.steps:
            issues.append(ValidationIssue(self.name, "error", "No disassembly steps were found.", "steps"))
        if not document.schema_version or document.schema_version == "unknown":
            issues.append(ValidationIssue(self.name, "warning", "Schema version is missing.", "schema_version"))
        return issues


class StepIndexRule:
    name = "step_indexes"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        indexes = [step.index for step in document.steps]
        duplicates = sorted({index for index in indexes if indexes.count(index) > 1})
        if duplicates:
            issues.append(ValidationIssue(self.name, "error", f"Duplicate step indexes: {duplicates}.", "steps"))
        if indexes != sorted(indexes):
            issues.append(ValidationIssue(self.name, "warning", "Steps are not sorted by index; JSON order is preserved.", "steps"))
        for position, step in enumerate(document.steps):
            if step.index <= 0:
                issues.append(ValidationIssue(self.name, "error", "Step index must be greater than zero.", f"steps[{position}].index"))
            if not step.operation:
                issues.append(ValidationIssue(self.name, "error", "Operation text is empty.", f"steps[{position}].operation"))
        return issues


class ComponentRule:
    name = "components"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ids: dict[str, tuple[str, str]] = {}

        def inspect(component: Component | None, location: str) -> None:
            if component is None:
                return
            if not component.name:
                issues.append(ValidationIssue(self.name, "error", "Component name is empty.", f"{location}.name"))
            for field, value in (("weight", component.weight), ("measured_weight", component.measured_weight)):
                if value is None:
                    continue
                try:
                    if float(value) < 0:
                        issues.append(ValidationIssue(self.name, "error", f"{field} cannot be negative.", f"{location}.{field}"))
                except (TypeError, ValueError):
                    issues.append(ValidationIssue(self.name, "error", f"{field} is not numeric.", f"{location}.{field}"))
            if component.node_id is not None:
                key = str(component.node_id)
                if key in ids and ids[key][0] != component.name:
                    earlier_name, earlier_location = ids[key]
                    issues.append(ValidationIssue(
                        self.name,
                        "warning",
                        f"Node ID {component.node_id} is associated with both '{earlier_name}' and '{component.name}'.",
                        f"{earlier_location}; {location}",
                        [component.node_id],
                    ))
                ids[key] = (component.name, location)

        inspect(document.product, "product")
        for index, component in enumerate(document.bill_of_materials):
            inspect(component, f"bill_of_materials[{index}]")
        for step_index, step in enumerate(document.steps):
            inspect(step.source, f"steps[{step_index}].source")
            for output_index, component in enumerate(step.outputs):
                inspect(component, f"steps[{step_index}].outputs[{output_index}]")
            for continuation_index, component in enumerate(step.continues_as):
                inspect(component, f"steps[{step_index}].continues_as[{continuation_index}]")
        return issues


class ActionRule:
    name = "actions"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for step_position, step in enumerate(document.steps):
            for action_position, action in enumerate(step.actions):
                if not action.text:
                    issues.append(ValidationIssue(
                        self.name,
                        "warning",
                        "Atomic action text is empty.",
                        f"steps[{step_position}].actions[{action_position}].text",
                        [action.node_id] if action.node_id is not None else None,
                    ))
        return issues


class BranchSourceRule:
    name = "branch_source"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for position, step in enumerate(document.steps):
            source, method = document.source_for_step(position)
            if source is None and method == "unspecified_branch":
                issues.append(ValidationIssue(
                    self.name,
                    "warning",
                    "A new disassembly branch starts here, but its source component is not encoded. "
                    "Add a 'source' object to this step for exact tree continuity.",
                    f"steps[{position}].source",
                ))
        return issues


class ProductMassBalanceRule:
    name = "mass_balance"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        if document.product.weight is None or document.total_bom_weight is None:
            return []
        try:
            product_weight = float(document.product.weight)
            bom_weight = float(document.total_bom_weight)
        except (TypeError, ValueError):
            return []
        if product_weight == 0:
            return []
        percentage = abs(product_weight - bom_weight) / abs(product_weight) * 100
        if percentage <= 1.0:
            return []
        return [ValidationIssue(
            self.name,
            "warning",
            f"Bill of Materials weighs {bom_weight:g} {document.product.weight_unit or ''}; "
            f"product weighs {product_weight:g} {document.product.weight_unit or ''} "
            f"({percentage:.1f}% difference).",
            "bill_of_materials",
            [document.product.node_id] if document.product.node_id is not None else None,
        )]


class StepMassBalanceRule:
    name = "step_mass_balance"

    def __init__(self, tolerance_percent: float = 1.0):
        self.tolerance_percent = tolerance_percent

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for position, step in enumerate(document.steps):
            source, _ = document.source_for_step(position)
            if source is None or source.weight is None:
                continue
            children = [*step.outputs]
            children.extend(step.continues_as)
            if not children or any(component.weight is None for component in children):
                continue
            try:
                source_weight = float(source.weight)
                children_weight = sum(float(component.weight) for component in children)
            except (TypeError, ValueError):
                continue
            if source_weight == 0:
                continue
            percentage = abs(source_weight - children_weight) / abs(source_weight) * 100
            if percentage > self.tolerance_percent:
                issues.append(ValidationIssue(
                    self.name,
                    "warning",
                    f"Input '{source.name}' weighs {source_weight:g}; outputs plus continuation weigh "
                    f"{children_weight:g} ({percentage:.1f}% difference).",
                    f"steps[{position}]",
                    [source.node_id] if source.node_id is not None else None,
                ))
        return issues


class ImagePathRule:
    name = "images"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        base = Path(document.source_dir) if document.source_dir else Path.cwd()

        def inspect(value: str | None, location: str) -> None:
            if not value or value.startswith("data:image/") or value.startswith(("http://", "https://")):
                return
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = base / path
            if not path.exists():
                issues.append(ValidationIssue(self.name, "warning", f"Image file not found: {value}", location))

        inspect(document.product.image, "product.image")
        for step_position, step in enumerate(document.steps):
            inspect(step.image, f"steps[{step_position}].image")
            for action_position, action in enumerate(step.actions):
                inspect(action.image, f"steps[{step_position}].actions[{action_position}].image")
            for output_position, component in enumerate(step.outputs):
                inspect(component.image, f"steps[{step_position}].outputs[{output_position}].image")
            for continuation_index, component in enumerate(step.continues_as):
                inspect(component.image, f"steps[{step_position}].continues_as[{continuation_index}].image")
        return issues


class KeepWholeRule:
    name = "depth_selection"

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        if not document.keep_whole_ids:
            return []
        known = {str(component.node_id) for component in document.all_known_components() if component.node_id is not None}
        missing = [item for item in document.keep_whole_ids if str(item) not in known]
        if not missing:
            return []
        return [ValidationIssue(
            self.name,
            "warning",
            f"The selected keep-whole IDs are not present in the normalized guide: {missing}.",
            "depth.keep_whole_ids",
            missing,
        )]


class Validator:
    def __init__(self, rules: list[ValidationRule] | None = None):
        self.rules = rules or [
            CoreStructureRule(),
            StepIndexRule(),
            ComponentRule(),
            ActionRule(),
            BranchSourceRule(),
            ProductMassBalanceRule(),
            StepMassBalanceRule(),
            ImagePathRule(),
            KeepWholeRule(),
        ]

    def register_rule(self, rule: ValidationRule) -> None:
        self.rules.append(rule)

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = [
            ValidationIssue(
                warning.rule,
                warning.severity,
                warning.message,
                warning.location or (f"node_ids={warning.node_ids}" if warning.node_ids else ""),
                warning.node_ids,
            )
            for warning in document.warnings
        ]
        imported_rules = {warning.rule for warning in document.warnings}
        for rule in self.rules:
            if rule.name == "mass_balance" and rule.name in imported_rules:
                continue
            issues.extend(rule.validate(document))
        unique: dict[tuple[str, str, str, str], ValidationIssue] = {}
        for issue in issues:
            unique[(issue.rule, issue.severity, issue.message, issue.location)] = issue
        result = list(unique.values())
        document.validation_issues = result
        return result
