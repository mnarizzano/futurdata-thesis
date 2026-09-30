"""
md_utils.py — Markdown syntax building blocks.

The mechanical bits of Markdown (escaping, anchors, tables, image links), so
renderer.py reads as document structure rather than string plumbing. Every
function here is pure (string in, string out) and knows nothing about the
Wizard's domain, nothing in this file knows what a Step is.

Why escaping isn't optional: node texts come from the source JSON and are
opaque (the loader guarantees nothing about their content). Markdown assigns
meaning to ordinary characters — a component named "Vite_M3*2" would render
with stray emphasis, and a "|" inside a table cell would split the row.
Escaping at the last moment, here, when text becomes Markdown, is the same
output-encoding rule web apps use when they HTML-escape at template time.
"""

from __future__ import annotations

import re
from typing import Optional

#Characters that can change meaning in inline Markdown text. Escaping the
#conservative set: emphasis (* _), links ([ ]), headers (#), code (`),
#escapes themselves (\), and HTML openers (<). Over-escaping harms
#readability of the raw .md, so we don't escape every ASCII symbol — only
#those with a rendering effect where we actually emit text.
_INLINE_SPECIALS = re.compile(r"([\\`*_\[\]<#])")


def escape_md(text: Optional[str]) -> str:
    """
    Escape a string for use in ordinary Markdown prose. None -> ''.

    Also flattens embedded newlines to a single space: source texts
    (observed in real models) sometimes carry a literal '\\n' from manual
    word-wrap in the modelling GUI, which would otherwise split a numbered
    list item into a stray lazy-continuation line.
    """
    if not text:
        return ""
    # HTML break opportunities are supported by Markdown renderers; link targets
    # are generated separately and remain byte-for-byte intact.
    text = re.sub(r"\S{33,}", lambda match: "<wbr>".join(
        match.group()[i:i + 32] for i in range(0, len(match.group()), 32)), text)
    escaped = _INLINE_SPECIALS.sub(r"\\\1", text).replace(r"\<wbr>", "<wbr>")
    return re.sub(r"\s*\n\s*", " ", escaped)


def escape_cell(text: Optional[str]) -> str:
    """
    Escape a string for use inside a table cell.

    Same as escape_md, plus the one thing that would otherwise break a table
    row: the cell separator '|'.
    """
    return escape_md(text).replace("|", "\\|")


def anchor(anchor_id: str) -> str:
    """
    An HTML anchor target, placed on the line before a heading.

    Style chosen to match the project's own URS document (<a name=...>), and
    because explicit ids are portable: heading auto-slugs differ between
    GitHub, GitLab and local previewers, while an explicit id works the same
    everywhere a link '[...](#id)' does.
    """
    return f'<a id="{anchor_id}"></a>'


def heading(level: int, text: str) -> str:
    """A '#'-style heading of the given level (1..6), text already escaped by caller."""
    level = max(1, min(6, level))
    return f"{'#' * level} {text}"


def image(alt: Optional[str], path: str) -> str:
    """
    A native Markdown image link (FR 4.1).

    The path/URL is passed through unchanged — same policy as the loader's
    emitter: we're not responsible for fetching or relocating images, only
    for referencing them. Alt text is escaped since it's node-derived.
    """
    return f"![{escape_md(alt) or 'image'}]({path})"


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """
    A GitHub-flavored Markdown table as a list of lines.

    Cells must already be escaped with escape_cell by the caller (the caller
    knows which cells are node-derived and which are literals like units).
    Returns lines rather than a joined string so the caller can splice them
    into its own line list uniformly.
    """
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(" --- " for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def format_weight(weight: Optional[float], unit: Optional[str]) -> str:
    """
    Human formatting of a nominal weight: '260 g', '2.5 kg', or '—' if unknown.

    An integer-valued float prints without the trailing '.0' (the sources
    store grams as whole numbers; '260.0 g' would look machine-made).
    """
    if weight is None:
        return "—"
    number = str(int(weight)) if float(weight).is_integer() else str(weight)
    return f"{number} {unit}" if unit else number