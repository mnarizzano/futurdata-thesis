"""Public JSON-to-PPTX entry point used by PresentationExportService.

Import ``export_to_pptx`` from ``main.services.pptx_converter`` (or the equivalent
``src.main`` package when running from the project root). The direct CLI fallback
is retained. Supplying an already-built guide avoids invoking the shared loader
again.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

# Support both package imports and direct execution from this directory.
try:  # pragma: no cover - the selected branch depends on how the app is started.
    from .pptx_core import ExportOptions, PPTXExportEngine, WizardDocument
except ImportError:  # pragma: no cover
    from pptx_core import ExportOptions, PPTXExportEngine, WizardDocument  # type: ignore


def _default_output_path(json_path: str | Path | None, guide: Any | None) -> Path:
    """Return a predictable default destination for the generated presentation.

    When a JSON path exists, the PPTX is saved next to that file with the same
    stem. When only an in-memory guide is provided, a generic name is used in
    the current working directory.
    """

    if json_path is not None:
        return Path(json_path).expanduser().resolve().with_suffix(".pptx")

    # The loader object may expose a product name, but it is not guaranteed to
    # be safe as a filename. A stable generic name is therefore preferable.
    return Path.cwd() / "disassembly_guide.pptx"


def export_to_pptx(
    json_path: str | Path | None = None,
    output_path: str | Path | None = None,
    *,
    guide: Any | None = None,
    depth: Any | None = None,
    include_bom: bool = True,
    start_step: int | None = None,
    end_step: int | None = None,
    max_action_groups: int | None = None,
    groups_per_slide: int = 1,
    include_title: bool = True,
    include_overview: bool = True,
    include_warnings: bool = True,
    include_tools_summary: bool = True,
    include_safety_summary: bool = True,
    include_component_details: bool = True,
    include_images: bool = True,
    include_closing: bool = True,
    stop_on_error: bool = True,
) -> str:
    """Export a normalized disassembly guide as an editable PowerPoint file.

    Parameters
    ----------
    json_path:
        Path of the source JSON model. It is required when ``guide`` is not
        supplied. The source file is opened read-only and is never modified.
    output_path:
        Destination of the generated presentation. If omitted, the exporter
        uses the JSON filename and changes only the extension to ``.pptx``.
    guide:
        Optional guide object already produced by ``build_guide``. Passing it
        avoids parsing the same JSON a second time in the desktop application.
    depth:
        Optional ``DepthSpec`` produced by the GUI. It is forwarded unchanged
        to the external loader and is deliberately not interpreted here.
    include_bom:
        Controls both loader-side BoM generation and BoM slide generation.
    start_step, end_step:
        Optional inclusive range of disassembly operation indexes.
    max_action_groups:
        Optional maximum number of parent operations to export.
    groups_per_slide:
        Number of parent operations shown on each step slide, from 1 to 4.
        A value of 1 generates the most detailed presentation.
    include_*:
        Feature switches used to include or suppress front matter, images,
        component metadata and the closing slide.
    stop_on_error:
        When true, blocking validation issues stop the export. Non-blocking
        warnings are included in the presentation and returned in the logs.

    Returns
    -------
    str
        Absolute path of the generated ``.pptx`` file.

    Raises
    ------
    ValueError
        If neither ``json_path`` nor ``guide`` is supplied, or if validation
        detects a blocking model error.
    FileNotFoundError
        If the JSON file does not exist.
    PermissionError
        If the destination cannot be written, commonly because it is open in
        PowerPoint.
    """

    if guide is None and json_path is None:
        raise ValueError("Either 'json_path' or an already-built 'guide' must be provided.")

    destination = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else _default_output_path(json_path, guide)
    )

    # Normalise all GUI choices into one immutable-like options object. The
    # renderer receives no Tkinter objects and remains reusable from tests,
    # scripts, and future interfaces.
    options = ExportOptions(
        start_step=start_step,
        end_step=end_step,
        max_action_groups=max_action_groups,
        groups_per_slide=groups_per_slide,
        include_title=include_title,
        include_overview=include_overview,
        include_warnings=include_warnings,
        include_bom=include_bom,
        include_tools_summary=include_tools_summary,
        include_safety_summary=include_safety_summary,
        include_component_details=include_component_details,
        include_images=include_images,
        include_closing=include_closing,
    )

    engine = PPTXExportEngine()

    if guide is not None:
        # Convert Rubin's dataclass/object to the exporter's stable internal
        # representation. This adapter keeps the PPTX module independent of
        # future implementation changes in the loader package.
        source_dir = (
            str(Path(json_path).expanduser().resolve().parent)
            if json_path is not None
            else None
        )
        document = (
            guide
            if isinstance(guide, WizardDocument)
            else WizardDocument.from_any(guide, source_dir=source_dir)
        )
        issues = engine.validate(document)

        if stop_on_error and any(issue.severity.lower() == "error" for issue in issues):
            details = "\n".join(str(issue) for issue in issues)
            raise ValueError(f"The guide contains blocking validation errors:\n{details}")

        result = engine.export(document, destination, options)
    else:
        # Let the loading layer call the team loader with the exact depth and
        # BoM options selected in the GUI. If the external loader is absent,
        # the same function safely falls back to reading normalized JSON.
        result, _issues = engine.load_validate_export(
            json_path=json_path,
            output_path=destination,
            options=options,
            stop_on_error=stop_on_error,
            prefer_external_loader=True,
            depth=depth,
            include_bom=include_bom,
        )

    return str(result.resolve())


def _build_argument_parser() -> argparse.ArgumentParser:
    """Create the small command-line interface used for manual verification."""

    parser = argparse.ArgumentParser(
        description="Convert a normalized Futurdata disassembly JSON file to PPTX."
    )
    parser.add_argument("json_path", help="Path of the source JSON file.")
    parser.add_argument("output_path", nargs="?", help="Optional .pptx destination.")
    parser.add_argument("--no-bom", action="store_true", help="Do not add Bill of Materials slides.")
    parser.add_argument("--start-step", type=int, default=None)
    parser.add_argument("--end-step", type=int, default=None)
    parser.add_argument("--max-action-groups", type=int, default=None)
    parser.add_argument("--groups-per-slide", type=int, default=1, choices=(1, 2, 3, 4))
    parser.add_argument("--no-images", action="store_true", help="Do not insert model images.")
    return parser


def main() -> int:
    """Run a standalone export and print the generated file path."""

    args = _build_argument_parser().parse_args()
    generated = export_to_pptx(
        args.json_path,
        args.output_path,
        include_bom=not args.no_bom,
        start_step=args.start_step,
        end_step=args.end_step,
        max_action_groups=args.max_action_groups,
        groups_per_slide=args.groups_per_slide,
        include_images=not args.no_images,
    )
    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
