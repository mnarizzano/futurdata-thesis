"""Reusable helpers for pagination, text cleanup, filenames and images."""

from __future__ import annotations

import base64
import io
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterator, TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen

from PIL import Image

T = TypeVar("T")


def chunks(items: list[T], size: int) -> Iterator[list[T]]:
    """Yield fixed-size slices without mutating the source list."""

    size = max(1, int(size))
    for index in range(0, len(items), size):
        yield items[index:index + size]


def normalize_text(value: Any) -> str:
    """Collapse line breaks and repeated spaces for compact slide labels."""

    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def safe_filename(value: str, fallback: str = "disassembly_guide") -> str:
    """Return a filesystem-safe filename stem."""

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned or fallback


def _image_text(value: Any) -> str | None:
    """Extract a path or URL from common loader image representations."""

    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("path", "url", "src", "data", "value"):
            candidate = value.get(key)
            if candidate not in (None, ""):
                return str(candidate).strip() or None
    if hasattr(value, "path"):
        candidate = getattr(value, "path")
        return str(candidate).strip() if candidate not in (None, "") else None
    return str(value).strip() or None


def _download_image(url: str, timeout_seconds: float = 5.0) -> io.BytesIO | None:
    """Download an optional remote image into memory.

    Network images are non-critical presentation metadata. Any connection,
    HTTP, or decoding failure therefore returns ``None`` and lets the renderer
    draw its normal placeholder instead of failing the complete export.
    """

    request = Request(url, headers={"User-Agent": "Futurdata-PPTX-Converter/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                return None
            return io.BytesIO(response.read())
    except (OSError, URLError, ValueError):
        return None


def resolve_image(
    value: Any,
    source_dir: str | None = None,
) -> Path | io.BytesIO | None:
    """Resolve local, remote, or data-URI image metadata.

    Relative paths are resolved against the directory containing the source
    JSON. The function never raises for a missing optional image.
    """

    reference = _image_text(value)
    if not reference:
        return None

    if reference.startswith("data:image/"):
        try:
            _, encoded = reference.split(",", 1)
            return io.BytesIO(base64.b64decode(encoded, validate=True))
        except (ValueError, base64.binascii.Error):
            return None

    if reference.startswith(("http://", "https://")):
        return _download_image(reference)

    path = Path(reference).expanduser()
    if not path.is_absolute() and source_dir:
        path = Path(source_dir) / path
    return path.resolve() if path.exists() and path.is_file() else None


def image_dimensions(source: Path | io.BytesIO) -> tuple[int, int]:
    """Read image dimensions while restoring in-memory stream position."""

    if isinstance(source, io.BytesIO):
        source.seek(0)
        with Image.open(source) as image:
            size = image.size
        source.seek(0)
        return size
    with Image.open(source) as image:
        return image.size


def fit_rect(
    image_width: int,
    image_height: int,
    box_width: float,
    box_height: float,
) -> tuple[float, float]:
    """Fit an image inside a box while preserving its aspect ratio."""

    if image_width <= 0 or image_height <= 0:
        return box_width, box_height
    image_ratio = image_width / image_height
    box_ratio = box_width / box_height
    if image_ratio >= box_ratio:
        return box_width, box_width / image_ratio
    return box_height * image_ratio, box_height
