"""Portable diagram archive service.

An exported archive is deliberately independent from ARIADNE's internal JSON
repository.  It contains only the active diagram snapshot and image files that
are referenced by shapes in that diagram.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from ..utils.image_handler import get_image_handler


class ProjectArchiveService:
    def __init__(self, exporter):
        self.exporter = exporter
        self.last_export_warnings: list[str] = []

    def export_zip(self, diagram, zip_path: str, product_id=None) -> bool:
        """Export *diagram* as ``diagram.json`` plus its available images.

        ``product_id`` is accepted for backwards compatibility, but is
        intentionally ignored: exporting does not write application data. Referenced catalogs
        are resolved read-only for portability.

        Missing referenced images are skipped and recorded in
        ``last_export_warnings``.  Real export errors are allowed to propagate
        so the controller can show the user the actual exception.
        """
        self.last_export_warnings = []

        target = Path(zip_path).expanduser()
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        target.parent.mkdir(parents=True, exist_ok=True)

        # The graph comes from memory; catalog definitions are resolved read-only.
        data = self.exporter.serialize_active_diagram(diagram)

        handler = get_image_handler()
        import hashlib
        assets = {}
        for shape in data["shapes"]:
            ref = shape.get("image_path")
            if not ref:
                continue
            source = Path(handler.get_full_path(ref))
            if not source.is_file():
                self.last_export_warnings.append(f"Missing image skipped: {ref}")
                continue
            content = source.read_bytes()
            # Portable paths are content-addressed, including absolute/legacy inputs.
            arcname = f"images/{hashlib.sha256(content).hexdigest()}{source.suffix.lower()}"
            if arcname in assets and assets[arcname] != content:
                raise ValueError("Conflicting image contents for archive path")
            assets[arcname] = content
            shape["image_path"] = arcname
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("diagram.json", json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
            for arcname, content in assets.items():
                zf.writestr(arcname, content)

        return True

    @staticmethod
    def _referenced_image_paths(diagram):
        """Yield non-empty image references from active diagram shapes."""
        seen = set()
        for shape in diagram.shapes:
            image_path = ""
            properties = getattr(shape, "properties", None)
            if isinstance(properties, dict):
                image_path = properties.get("image_path", "") or ""
            if not image_path:
                image_path = getattr(shape, "image_path", "") or ""
            if image_path and image_path not in seen:
                seen.add(image_path)
                yield image_path

    def import_zip(self, zip_path: str):
        """Extract a portable archive, restore its images, and return a Diagram."""
        try:
            handler = get_image_handler()
            with tempfile.TemporaryDirectory(prefix="ariadne_import_") as temp:
                temp_dir = Path(temp)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    root = temp_dir.resolve()
                    for member in zf.infolist():
                        dest = (temp_dir / member.filename).resolve()
                        if dest != root and root not in dest.parents:
                            raise ValueError("Unsafe archive path")
                    zf.extractall(temp_dir)

                json_path = temp_dir / "diagram.json"
                if not json_path.exists():
                    return None

                return self.exporter.import_diagram(
                    str(json_path), create_in_repository=False
                )
        except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError):
            return None
