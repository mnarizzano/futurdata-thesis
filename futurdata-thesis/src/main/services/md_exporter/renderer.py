"""
renderer.py — pure Guide -> Markdown text transformation.

Given a Guide (or a page of its steps) and the options, returns the Markdown
text. No file I/O, no pagination decisions,that's exporter.py's job.
Keeping this module pure (data in, string out) makes it trivially testable: a
test just calls render_document and asserts on the string.

What a page contains, in order:

Page 1                                  Pages 2+ (paginated exports only)
  title + product card                    compact title
  [page navigation]                       [page navigation]
  validation warnings   (option)          steps of this page
  bill of materials     (option)          [page navigation]
  table of contents     (option)
  steps of this page
  [page navigation]

The global sections (product card, warnings, BoM) only show up on page 1 —
they describe the whole guide, and repeating them on every page would bury
the steps. The TOC lists the steps of the current page (all of them when not
paginating): a cross-page TOC would need to know which page every step
landed on, which is exactly the pagination coupling this module is meant to
avoid.

Safety notes (design D4): an action whose text carries a danger keyword
("WARNING", ...) gets a warning sign and bold inside the
numbered list, so the numbering stays unbroken while the operator's eye is
drawn to the risk.
"""

from __future__ import annotations

import re
from ...utils.material_display import material_text
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ...loader_se.disassembly_loader import Component, Guide, Severity, Step

from . import md_utils as md
from ...utils.text_layout import normalize_export_titles

if TYPE_CHECKING:  #Imported for type hints only and avoids a circular import
    from .exporter import ExportOptions


#Danger keywords that flag a safety-relevant action (case-insensitive).
#English only: input models are English-only going forward.
_SAFETY_RE = re.compile(
    r"\b(WARNING|CAUTION|DANGER)\b", re.IGNORECASE
)

# Icon per warning severity — icons sort the eye faster than words, and the
# textual severity is still printed for grep-ability.
_SEVERITY_ICON = {
    Severity.ERROR: "🛑",
    Severity.WARNING: "⚠️",
    Severity.INFO: "ℹ️",
}


@dataclass(frozen=True)
class PageInfo:
    """
    Where the rendered page sits in a paginated export (FR 19.0).

    For a single-file export: page_number=1, page_count=1, both paths None —
    the renderer then emits no navigation at all.

    prev_path / next_path are basenames, not full paths: the pages sit in the
    same directory, and relative links keep the folder relocatable.
    """

    page_number: int = 1
    page_count: int = 1
    prev_path: Optional[str] = None
    next_path: Optional[str] = None


# =============================================================================
# ENTRY POINT
# =============================================================================

def render_document(
    guide: Guide,
    page_steps: tuple[Step, ...],
    options: "ExportOptions",
    page: PageInfo,
    step_links=None,
) -> str:
    """
    Render one page of the guide as a Markdown string (ends with a newline).

    guide      : the full Guide (global sections come from here).
    page_steps : the steps belonging to THIS page (all steps when not paginating).
    options    : what to include (TOC, warnings, BoM, images).
    page       : position/navigation info for paginated exports.
    """
    guide = normalize_export_titles(guide)
    page_steps = normalize_export_titles(page_steps)
    lines: list[str] = []

    lines += _render_header(guide, options, page)
    lines += _render_navigation(page)

    if page.page_number == 1:
        if options.include_warnings and guide.warnings:
            lines += _render_warnings(guide)
        if options.include_bom and guide.bill_of_materials:
            lines += _render_bom(guide)

    if options.include_toc and page_steps:
        lines += _render_toc(page_steps)

    if page_steps:
        targets = {s.input.node_id: s.index for s in guide.steps}
        for step in page_steps:
            lines += _render_step(step, options, targets=targets, step_links=step_links)
    elif page.page_number == 1:
        #Empty guide (best-effort on a malformed model, FR 2.3): say so
        #explicitly, an empty document would look like an export bug.
        lines += [
            "> **No disassembly steps could be generated from this model.**",
            "> See the validation warnings above for the reason.",
            "",
        ]

    lines += _render_navigation(page)
    #Drop a possible trailing blank line, then close with exactly one newline.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


# =============================================================================
# SECTIONS 
# =============================================================================

def _render_header(
    guide: Guide, options: "ExportOptions", page: PageInfo
) -> list[str]:
    """Title; on page 1 also the product card (weight, image — FR 4.0/4.1)."""
    title = f"Disassembly Guide — {md.escape_md(guide.product.name)}"
    if page.page_count > 1:
        title += f" (page {page.page_number}/{page.page_count})"
    lines = [md.heading(1, title), ""]

    if page.page_number > 1:
        return lines

    product = guide.product
    facts: list[str] = []
    if product.weight is not None:
        facts.append(f"**Total weight:** {md.format_weight(product.weight, product.weight_unit)}")
    if product.material:
        facts.append(f"**Material:** {md.escape_md(material_text(product.material, product.material_details))}")
    if guide.depth is not None:
        facts.append(f"**Disassembly depth:** `{guide.depth.mode.value}`")
    facts.append(f"**Steps:** {len(guide.steps)}")
    lines += [" · ".join(facts), ""]

    if options.include_images and product.image_path:
        lines += [md.image(product.name, product.image_path), ""]
    return lines


def _render_navigation(page: PageInfo) -> list[str]:
    """Prev/next links between pages. Nothing at all for single-file exports."""
    if page.page_count <= 1:
        return []
    parts: list[str] = []
    if page.prev_path:
        parts.append(f"[← Previous page]({page.prev_path})")
    parts.append(f"*Page {page.page_number} of {page.page_count}*")
    if page.next_path:
        parts.append(f"[Next page →]({page.next_path})")
    return [" | ".join(parts), ""]


def _render_warnings(guide: Guide) -> list[str]:
    """
    Validation findings (FR 2.2) as a blockquote list.

    The user proceeded despite these (FR 2.3); the document must record that
    the guide was generated from a flawed model — it shifts responsibility to
    the user exactly as the URS states. node_ids are printed so a modeller can
    jump back to the offending elements (NFR 1.1).
    """
    lines = [md.anchor("warnings"), md.heading(2, "⚠ Validation warnings"), ""]
    for w in guide.warnings:
        icon = _SEVERITY_ICON.get(w.severity, "•")
        loc = f" *(nodes: {', '.join(map(str, w.node_ids))})*" if w.node_ids else ""
        lines.append(
            f"> {icon} **{w.severity.value.upper()}** — `{w.rule}`: "
            f"{md.escape_md(w.message)}{loc}"
        )
    lines.append("")
    return lines


def _render_bom(guide: Guide) -> list[str]:
    """Bill of Materials as a real Markdown table (FR 1.3 / FR 9.1)."""
    lines = [md.anchor("bom"), md.heading(2, "Bill of Materials"), ""]
    rows = []
    for c in guide.bill_of_materials:
        name = md.escape_cell(c.name)
        if c.kept_whole:
            name += " 📦"
        rows.append([
            name,
            md.format_weight(c.weight, c.weight_unit),
            md.escape_cell(material_text(c.material, c.material_details)) or "—",
            md.escape_cell(c.color) or "—",
        ])
    lines += md.table(["Component", "Weight", "Material", "Color"], rows)
    if any(c.kept_whole for c in guide.bill_of_materials):
        lines += ["", "📦 = assembly kept whole (not disassembled further)"]
    lines.append("")
    return lines


def _render_toc(page_steps: tuple[Step, ...]) -> list[str]:
    """Table of contents: one link per step on this page."""
    lines = [md.heading(2, "Contents"), ""]
    for step in page_steps:
        lines.append(
            f"{step.index}. [{md.escape_md(step.operation)}](#step-{step.index})"
        )
    lines.append("")
    return lines


def _render_step(
    step: Step, options: "ExportOptions", link_prefix: str = "", targets=None, step_links=None
) -> list[str]:
    """
    One disassembly operation (= one diamond, FR 10.0) as one grouped section:
    heading, tools, numbered actions, parts obtained, continuation pointer.
    """
    lines = [
        "---",
        "",
        md.anchor(f"step-{step.index}"),
        md.heading(2, f"Step {step.index} — {md.escape_md(step.operation)}"),
        "",
    ]

    lines += [f"**Input:** {md.escape_md(step.input.name)}", ""]
    if options.include_images and step.input.image_path:
        lines += [md.image(step.input.name, step.input.image_path), ""]
    if options.include_images and step.image_path:
        lines += ["Operation illustration", md.image(step.operation, step.image_path), ""]

    if step.tools_required:
        tools = ", ".join(md.escape_md(t) for t in step.tools_required)
        lines += [f"**Tools required:** {tools}", ""]

    if step.actions:
        for n, action in enumerate(step.actions, start=1):
            text = md.escape_md(action.text)
            if _SAFETY_RE.search(action.text or ""):
                text = f"⚠️ **{text}**"
            lines.append(f"{n}. {text}")
            if options.include_images and action.image_path:
                # Indented under the list item so it belongs to this action.
                lines.append(f"   {md.image(action.text, action.image_path)}")
        lines.append("")

    if step.outputs:
        lines += [md.heading(3, "Parts obtained"), ""]
        for part in step.outputs:
            lines.append(_render_part_line(part))
            if options.include_images and part.image_path:
                lines.append(f"  {md.image(part.name, part.image_path)}")
        lines.append("")

    if step.continues_as:
        for target in step.continues_as:
            target_index = (targets or {}).get(target.node_id)
            label = f"Remaining assembly: **{md.escape_md(target.name)}**"
            if target_index is not None:
                href = (step_links or {}).get(target_index, f"#step-{target_index}")
                label += f" ([Step {target_index}]({href}))"
            lines += [label, ""]
    else:
        lines += ["🏁 *End of this disassembly branch.*", ""]
    return lines


def _render_part_line(part: Component) -> str:
    """One bullet for an extracted part, with its known attributes (FR 4.0)."""
    bits = [f"- **{md.escape_md(part.name)}**"]
    details: list[str] = []
    if part.weight is not None:
        details.append(md.format_weight(part.weight, part.weight_unit))
    if part.material:
        details.append(md.escape_md(material_text(part.material, part.material_details)))
    if part.color:
        details.append(md.escape_md(part.color))
    if details:
        bits.append(f"({', '.join(details)})")
    if part.kept_whole:
        contained = (
            f" — contains {part.contained_leaf_count} parts"
            if part.contained_leaf_count is not None else ""
        )
        bits.append(f"📦 *kept whole{contained}*")
    return " ".join(bits)