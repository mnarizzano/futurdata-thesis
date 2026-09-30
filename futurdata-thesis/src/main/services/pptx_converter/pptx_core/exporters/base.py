"""Abstract exporter contract used by the Futurdata export architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import WizardDocument
from ..options import ExportOptions


class Exporter(ABC):
    """Common exporter contract used by the Wizard export panel."""

    format_id: str
    display_name: str
    extension: str

    @abstractmethod
    def export(self, document: WizardDocument, output_path: Path, options: ExportOptions) -> Path:
        raise NotImplementedError

    def ensure_extension(self, output_path: Path) -> Path:
        extension = self.extension if self.extension.startswith(".") else f".{self.extension}"
        return output_path if output_path.suffix.lower() == extension.lower() else output_path.with_suffix(extension)
