"""Runtime registry for exporter implementations.

Only PPTX is implemented in this thesis contribution, while the generic
registry preserves compatibility with the application architecture."""

from __future__ import annotations

from .base import Exporter


class ExporterRegistry:
    """Registry kept generic so additional formats can be registered later."""

    def __init__(self):
        self._exporters: dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        key = exporter.format_id.lower().strip()
        if not key:
            raise ValueError("Exporter format_id cannot be empty.")
        self._exporters[key] = exporter

    def get(self, format_id: str) -> Exporter:
        key = format_id.lower().strip()
        if key not in self._exporters:
            raise KeyError(f"No exporter is registered for format '{format_id}'.")
        return self._exporters[key]

    def all(self) -> list[Exporter]:
        return list(self._exporters.values())
