"""Legacy Word entry point, sharing the application's DOCX renderer."""
from pathlib import Path
from ...loader_se.disassembly_loader import build_guide
from ..document_export_service import DocumentExportService


def export_to_word(json_path, depth=None, include_bom=False):
    guide = build_guide(json_path, depth=depth, include_bom=include_bom)
    output = Path(Path(json_path).stem + ".docx").resolve()
    DocumentExportService._export_docx(guide, output, Path(json_path).resolve().parent)
    return str(output)
