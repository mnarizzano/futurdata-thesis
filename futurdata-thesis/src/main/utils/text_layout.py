"""Presentation-only title normalization and lossless measured text wrapping."""
from dataclasses import fields, is_dataclass, replace
from functools import lru_cache
from PIL import ImageFont


def normalize_title(value):
    """Uppercase only the first alphabetic character, preserving all other text."""
    text = str(value) if value is not None else ""
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.upper() + text[index + 1:]
    return text


def normalize_export_titles(value):
    """Copy guide objects/IR; normalize semantic titles, never paths or prose."""
    title_fields = {"name", "title", "operation"}
    opaque_fields = {"metadata", "extra", "lookups", "tools", "tools_required"}
    def field_value(key, item):
        if key in title_fields and isinstance(item, str):
            return normalize_title(item)
        return item if key in opaque_fields else normalize_export_titles(item)
    if is_dataclass(value) and not isinstance(value, type):
        return replace(value, **{f.name: field_value(f.name, getattr(value, f.name))
                                 for f in fields(value) if f.init})
    if isinstance(value, dict):
        return {key: field_value(key, item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(normalize_export_titles(item) for item in value)
    return value


def wrap_measured(value, width, measure):
    """Wrap at spaces, breaking oversized tokens. No characters are discarded."""
    result = []
    for paragraph in str(value).split("\n"):
        if not paragraph:
            result.append("")
        while paragraph:
            lo, hi = 1, len(paragraph)
            while lo <= hi:
                mid = (lo + hi) // 2
                if measure(paragraph[:mid]) <= width:
                    lo = mid + 1
                else:
                    hi = mid - 1
            end = max(1, hi)
            if end < len(paragraph):
                space = paragraph.rfind(" ", 0, end)
                if space >= 0:
                    end = space + 1
            result.append(paragraph[:end])
            paragraph = paragraph[end:]
    return result


@lru_cache(maxsize=64)
def _font(size, bold=False):
    # Use the same Arial face as Office output, with portable metric fallbacks.
    for name in (("arialbd.ttf", "DejaVuSans-Bold.ttf") if bold else
                 ("arial.ttf", "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size * 4)
        except OSError:
            pass
    return ImageFont.load_default(size=size * 4)


def office_lines(value, width_points, size, bold=False):
    font = _font(size, bold)
    return wrap_measured(value, max(1, width_points),
                         lambda text: font.getlength(text) / 4 * 1.08)


def fit_office_text(value, width_points, height_points, size, bold=False):
    """Fit at readable sizes; return None when pagination is required."""
    for candidate in range(int(size), min(9, int(size)) - 1, -1):
        lines = office_lines(value, width_points, candidate, bold)
        if len(lines) * candidate * 1.25 <= height_points:
            return "\n".join(lines), candidate
    return None
