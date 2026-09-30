"""Orchestration layer for the PPTX export pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exporters.pptx_exporter import PPTXExporter
from .exporters.registry import ExporterRegistry
from .loader import load_document
from .models import WizardDocument
from .options import ExportOptions
from .validation import ValidationIssue, Validator


class PPTXExportEngine:
    """Coordinate loading, validation and PowerPoint rendering.

    Keeping orchestration outside the renderer makes every phase testable on
    its own and prevents the graphical interface from containing export logic.
    """

    def __init__(
        self,
        exporter: PPTXExporter | None = None,
        validator: Validator | None = None,
    ) -> None:
        self.registry = ExporterRegistry()
        self.registry.register(exporter or PPTXExporter())
        self.validator = validator or Validator()

    def load(
        self,
        json_path: str | Path,
        *,
        prefer_external_loader: bool = True,
        depth: Any | None = None,
        include_bom: bool = True,
    ) -> WizardDocument:
        """Load a JSON model through the shared loader or direct fallback."""

        return load_document(
            json_path,
            prefer_external_loader=prefer_external_loader,
            depth=depth,
            include_bom=include_bom,
        )

    def validate(self, document: WizardDocument) -> list[ValidationIssue]:
        """Run all registered validation rules and attach issues to the model."""

        return self.validator.validate(document)

    def export(
        self,
        document: WizardDocument,
        output_path: str | Path,
        options: ExportOptions | None = None,
    ) -> Path:
        """Render a previously loaded and validated model to PowerPoint."""

        exporter = self.registry.get("pptx")
        return exporter.export(document, Path(output_path), options or ExportOptions())

    def load_validate_export(
        self,
        json_path: str | Path,
        output_path: str | Path,
        options: ExportOptions | None = None,
        *,
        stop_on_error: bool = True,
        prefer_external_loader: bool = True,
        depth: Any | None = None,
        include_bom: bool = True,
    ) -> tuple[Path, list[ValidationIssue]]:
        """Execute the complete pipeline and return the output plus issues."""

        document = self.load(
            json_path,
            prefer_external_loader=prefer_external_loader,
            depth=depth,
            include_bom=include_bom,
        )
        issues = self.validate(document)

        # Warnings remain visible in the generated deck. Only errors stop the
        # pipeline, and only when the caller explicitly requests strict mode.
        if stop_on_error and any(issue.severity.lower() == "error" for issue in issues):
            details = "\n".join(str(issue) for issue in issues)
            raise ValueError(f"The JSON contains blocking validation errors:\n{details}")

        result = self.export(document, output_path, options)
        return result, issues
