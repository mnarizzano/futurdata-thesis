"""Application service for exporting the active ARIADNE diagram to PowerPoint.

The controller passes the in-memory model to this service. The service creates
an ephemeral, self-contained JSON snapshot (plus referenced images) for the
converter. Referenced catalogs are resolved read-only; export never writes
application records.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from ..utils.image_handler import get_image_handler


class PresentationExportService:
    def __init__(self, diagram_exporter):
        self.diagram_exporter = diagram_exporter

    def export(self, diagram, output_path: str, **options) -> str:
        destination = Path(output_path).expanduser()
        if destination.suffix.lower() != ".pptx":
            destination = destination.with_suffix(".pptx")
        destination.parent.mkdir(parents=True, exist_ok=True)

        snapshot = self.diagram_exporter.serialize_active_diagram(diagram)
        with tempfile.TemporaryDirectory(prefix="ariadne_pptx_") as temp_dir:
            temp_root = Path(temp_dir)
            self._stage_images(snapshot, temp_root)
            json_path = temp_root / "diagram.json"
            json_path.write_text(
                json.dumps(snapshot, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            from .pptx_converter import export_to_pptx
            return export_to_pptx(
                json_path=json_path,
                output_path=destination,
                **options,
            )

    @staticmethod
    def _stage_images(snapshot: dict, temp_root: Path) -> None:
        """Copy available referenced images beside the temporary JSON snapshot."""
        from .image_staging import stage_images
        stage_images(snapshot, temp_root, get_image_handler())
