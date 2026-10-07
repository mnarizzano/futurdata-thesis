"""
exporter.py — the MDExporter class: orchestration of a Markdown export run.

In one line: given a Guide and the user's options, decide what gets written
where (one file or several pages, FR 19.0) and write it. What a step actually
looks like in Markdown is renderer.py's job, not this module's.

The split mirrors the loader's own discipline (builder orchestrates,
linearizer/emitter do the work): orchestration and rendering change for
different reasons. Pagination policy changes if the export panel grows a new
option, the look of a step changes if a reviewer wants nicer output. Keeping
them apart means one kind of change never risks breaking the other.

Pluggability (FR 11.0): the export panel needs to list formats it's never
heard of, so the exporter declares its identity as class attributes
(format_id, display_name, file_extension) — a registry can do
`[cls.display_name for cls in exporters]` without special-casing anyone.
Adding a format later is just writing a class with the same surface and
appending it to the registry list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ...loader_se.disassembly_loader import DepthSpec, Guide, Step, build_guide

from . import renderer


# =============================================================================
# OPTIONS
# =============================================================================

@dataclass(frozen=True)
class ExportOptions:
    """
    Configuration of one export run.

    A frozen dataclass, not loose keyword arguments, for the same reasons the
    loader's DepthSpec is one: the GUI's export panel can build this object
    from its widgets and hand it over as a single value; adding an option
    tomorrow does not change any method signature; and freezing guarantees the
    options cannot drift mid-run.

    Fields:
      include_toc      : emit a table of contents with anchor links to each
                         step (Markdown-native navigation).
      include_warnings : emit the validation findings section (FR 2.2 — the
                         user chose to proceed despite them, FR 2.3, so the
                         document should say so; but a "clean copy" for the
                         workshop floor may switch them off).
      include_bom      : emit the Bill of Materials table (FR 1.3 / FR 9.1).
                         Only possible if the Guide was built with
                         include_bom=True; if the Guide carries no BoM this
                         option is silently a no-op (nothing to render).
      include_images   : emit image links (FR 4.1). Off = text-only document,
                         e.g. for printing.
      steps_per_page   : FR 19.0 — how many steps ("group of actions") go into
                         each exported file. None = everything in ONE file
                         (the default, and the common case). N>=1 = split into
                         ceil(len(steps)/N) files, chained with prev/next
                         links so the reader can navigate between pages.
    """

    include_toc: bool = True
    include_warnings: bool = True
    include_bom: bool = True
    include_images: bool = True
    steps_per_page: Optional[int] = None

    def __post_init__(self) -> None:
        #Fail loudly on a nonsensical value instead of producing 0-step pages.
        if self.steps_per_page is not None and self.steps_per_page < 1:
            raise ValueError(
                f"steps_per_page must be >= 1 or None, got {self.steps_per_page}"
            )


# =============================================================================
# EXPORTER
# =============================================================================

class MDExporter:
    """
    The Markdown export method of the Disassembly Wizard (URS FR 14.0).

    Usage (what the export panel or a script does):

        from disassembly_loader import build_guide
        from md_exporter import MDExporter, ExportOptions

        guide = build_guide("model.json", include_bom=True)
        files = MDExporter().export(guide, "out/guide.md",
                                    ExportOptions(steps_per_page=None))

    The exporter consumes only the Guide (the IR). It never reads the source
    JSON and never touches the loader's internals — the IR is the contract.
    """

    #Identity for the export panel registry (FR 11.0) 
    format_id: str = "md"
    display_name: str = "Markdown (.md)"
    file_extension: str = ".md"

    def export(
        self,
        guide: Guide,
        out_path: str,
        options: ExportOptions | None = None,
    ) -> list[str]:
        """
        Render `guide` to Markdown and write it under `out_path`.

        Parameters:
          guide    : the Guide from disassembly_loader.build_guide (read-only).
          out_path : the target .md path. With pagination, page k is written
                     next to it as `<stem>_pageK.md` (page 1 keeps the plain
                     name, so the "entry point" file is always out_path).
          options  : the run configuration; defaults to ExportOptions().

        Returns the list of paths actually written, in reading order. Always
        at least one element.
        """
        if options is None:
            options = ExportOptions()

        pages = self._split_into_pages(guide.steps, options.steps_per_page)
        paths = self._page_paths(out_path, len(pages))

        written: list[str] = []
        for page_number, page_steps in enumerate(pages, start=1):
            nav = renderer.PageInfo(
                page_number=page_number,
                page_count=len(pages),
                prev_path=(
                    os.path.basename(paths[page_number - 2])
                    if page_number > 1 else None
                ),
                next_path=(
                    os.path.basename(paths[page_number])
                    if page_number < len(pages) else None
                ),
            )
            links = {step.index: (("" if page_index == page_number-1 else os.path.basename(paths[page_index]))
                                  + f"#step-{step.index}")
                     for page_index, steps in enumerate(pages) for step in steps}
            text = renderer.render_document(guide, page_steps, options, nav, links)
            path = paths[page_number - 1]
            self._write(text, path)
            written.append(path)
        return written

    # -------------------------------------------------------------------------
    # Internal helpers 
    # -------------------------------------------------------------------------

    @staticmethod
    def _split_into_pages(
        steps: tuple[Step, ...], steps_per_page: Optional[int]
    ) -> list[tuple[Step, ...]]:
        """
        Chunk the steps per FR 19.0. None -> one page with everything.

        An empty guide (malformed model, FR 2.3 best-effort) still yields one
        page: the document with header/warnings and no steps is itself useful —
        it tells the user why the guide is empty. Zero files would look like a
        crash.
        """
        if steps_per_page is None or not steps:
            return [steps]
        return [
            steps[i:i + steps_per_page]
            for i in range(0, len(steps), steps_per_page)
        ]

    @staticmethod
    def _page_paths(out_path: str, page_count: int) -> list[str]:
        """
        Compute the file path of each page.

        Page 1 keeps the caller's exact path (single-file exports and the
        entry point of multi-file exports are the same name — predictable for
        the caller). Further pages get a `_pageK` suffix before the extension.
        """
        if page_count == 1:
            return [out_path]
        stem, ext = os.path.splitext(out_path)
        ext = ext or ".md"
        return [stem + ext] + [
            f"{stem}_page{k}{ext}" for k in range(2, page_count + 1)
        ]

    @staticmethod
    def _write(text: str, path: str) -> None:
        """
        Write one page. Creates the parent directory if needed (UTF-8).

        newline="" disables Python's universal-newline translation, so the
        '\\n' already in `text` reaches disk unchanged instead of becoming
        '\\r\\n' on Windows — output is byte-identical across platforms.
        """
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)


# =============================================================================
# FUNCTIONAL WRAPPER 
# =============================================================================

def export_to_md(
    json_path: str | Guide,
    output_path: str,
    depth: DepthSpec | None = None,
    include_bom: bool = True,
    options: ExportOptions | None = None,
) -> list[str]:
    """
    Thin functional entry point over MDExporter, for callers (e.g. app.py)
    that want a plain `export_to_md(...)` call instead of instantiating the
    class directly.

    Parameters:
      json_path   : path to the Builder JSON model, or an already-built Guide
                    (skips the build step if the caller already has one).
      output_path : the target .md path (see MDExporter.export).
      depth       : disassembly depth (FR 3.0); ignored if json_path is a Guide.
      include_bom : whether to compute the Bill of Materials data (passed to
                    build_guide); ignored if json_path is a Guide. Independent
                    from options.include_bom, which controls whether the BoM
                    is rendered once computed.
      options     : the run configuration; defaults to ExportOptions().

    Returns the list of paths written (see MDExporter.export).
    """
    guide = (
        build_guide(json_path, depth=depth, include_bom=include_bom)
        if isinstance(json_path, str) else json_path
    )
    return MDExporter().export(guide, output_path, options)
