import json
import shutil
from pathlib import Path

from .renderer import render_txt


class TXTExporter:

    def export(self, ir_path: str, output_path: str) -> None:
        ir = self._load_ir(ir_path)

        out = Path(output_path)

        out.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._copy_local_images(
            ir,
            Path(ir_path).parent,
            out.parent
        )

        out.write_text(
            self._build_txt(ir),
            encoding="utf-8"
        )

        print(
            f"TXT wizard exported successfully to: {out}"
        )

    def _load_ir(self, ir_path):
        with Path(ir_path).open(
            encoding="utf-8"
        ) as f:
            return json.load(f)

    def _copy_local_images(self, ir, root, out):
        paths = set()

        def collect(obj):
            if isinstance(obj, dict):
                image = obj.get("image")

                if (
                    isinstance(image, dict)
                    and image.get("path")
                    and not image.get("is_url", False)
                ):
                    paths.add(
                        image["path"]
                    )

        # Product image
        collect(
            ir.get("product", {})
        )

        # Step images
        for step in ir.get("steps", []):

            for action in step.get(
                "actions",
                []
            ):
                collect(action)

            for output in step.get(
                "outputs",
                []
            ):
                collect(output)

            collect(
                step.get("continues_as") or {}
            )

        # Bill of materials images
        for part in ir.get(
            "bill_of_materials",
            []
        ):
            collect(part)

        # Copy local images
        for relative_path in paths:

            src = root / relative_path
            dst = out / relative_path

            if src.exists():

                dst.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(
                    src,
                    dst
                )

    def _build_txt(self, ir):
        return render_txt(ir)