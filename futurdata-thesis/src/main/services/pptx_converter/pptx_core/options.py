"""Configuration object for PowerPoint generation.

All user-facing settings are normalized before rendering so invalid GUI values
cannot create malformed slide layouts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json


@dataclass(slots=True)
class ExportOptions:
    start_step: int | None = None
    end_step: int | None = None
    max_action_groups: int | None = None
    groups_per_slide: int = 1
    bom_rows_per_slide: int = 9

    include_title: bool = True
    include_overview: bool = True
    include_warnings: bool = True
    include_bom: bool = True
    include_tools_summary: bool = True
    include_safety_summary: bool = True
    include_component_details: bool = True
    include_images: bool = True
    include_closing: bool = True

    def normalized(self) -> "ExportOptions":
        start = int(self.start_step) if self.start_step not in (None, "") else None
        end = int(self.end_step) if self.end_step not in (None, "") else None
        if start is not None and end is not None and start > end:
            start, end = end, start
        maximum = int(self.max_action_groups) if self.max_action_groups not in (None, "", 0) else None
        return ExportOptions(
            start_step=start,
            end_step=end,
            max_action_groups=max(1, maximum) if maximum is not None else None,
            groups_per_slide=min(4, max(1, int(self.groups_per_slide or 1))),
            bom_rows_per_slide=min(12, max(5, int(self.bom_rows_per_slide or 9))),
            include_title=bool(self.include_title),
            include_overview=bool(self.include_overview),
            include_warnings=bool(self.include_warnings),
            include_bom=bool(self.include_bom),
            include_tools_summary=bool(self.include_tools_summary),
            include_safety_summary=bool(self.include_safety_summary),
            include_component_details=bool(self.include_component_details),
            include_images=bool(self.include_images),
            include_closing=bool(self.include_closing),
        )

    def save(self, path: str | Path) -> Path:
        destination = Path(path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(asdict(self.normalized()), indent=2), encoding="utf-8")
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "ExportOptions":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data).normalized()
