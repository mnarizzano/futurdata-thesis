import textwrap
from ...utils.text_layout import normalize_export_titles, normalize_title

def render_txt(ir):
    ir = normalize_export_titles(ir)
    lines = []

    product = ir.get("product", {})

    # TITLE
    lines.append("=" * 70)
    lines.append(
        f"{product.get('name', 'Disassembly Wizard')} — DISASSEMBLY WIZARD"
    )
    lines.append("=" * 70)
    lines.append("")

    # PRODUCT
    lines.append("PRODUCT")
    lines.append("-" * 70)

    for key, value in product.items():
        if key == "image":
            image = value

            if isinstance(image, dict) and image.get("path"):
                lines.append(f"Image: {image['path']}")

        else:
            lines.append(
                f"{format_key(key)}: {format_value(value)}"
            )

    lines.append("")

    # DEPTH
    if "depth" in ir:
        lines.append("DEPTH")
        lines.append("-" * 70)
        lines.append(format_value(ir["depth"]))
        lines.append("")

    # WARNINGS
    warnings = ir.get("warnings", [])

    if warnings:
        lines.append("WARNINGS")
        lines.append("-" * 70)

        for index, warning in enumerate(warnings, start=1):
            lines.append(
                f"{index}. {format_value(warning)}"
            )

        lines.append("")

    # STEPS
    lines.append("DISASSEMBLY STEPS")
    lines.append("=" * 70)
    lines.append("")

    for position, step in enumerate(
        ir.get("steps", []),
        start=1
    ):
        number = step.get("index", position)

        lines.append(f"STEP {number}")
        lines.append("-" * 70)

        if step.get("operation"):
            lines.append(
                f"Operation: {step['operation']}"
            )

        source = step.get("input") or {}
        lines.append("Input: " + str(source.get("name", "Unknown")))
        if source.get("image"):
            lines.append("Starting assembly image: " + format_value(source["image"]))
        if step.get("image"):
            lines.append("Operation illustration: " + format_value(step["image"]))

        # ACTIONS
        actions = step.get("actions", [])

        if actions:
            lines.append("")
            lines.append("Actions:")

            for index, action in enumerate(
                actions,
                start=1
            ):
                if isinstance(action, dict):
                    text = (
                        action.get("text")
                        or action.get("description")
                        or action.get("name")
                        or "Action"
                    )

                    lines.append(
                        f"  {index}. {text}"
                    )

                    image = action.get("image")

                    if (
                        isinstance(image, dict)
                        and image.get("path")
                    ):
                        lines.append(
                            f"     Image: {image['path']}"
                        )

                else:
                    lines.append(
                        f"  {index}. {action}"
                    )

        # TOOLS
        tools = (
            step.get("tools_required")
            or step.get("tools")
            or step.get("required_tools")
            or []
        )

        if tools:
            lines.append("")
            lines.append("Tools:")

            for tool in tools:
                if isinstance(tool, dict):
                    name = (
                        tool.get("name")
                        or tool.get("type")
                        or format_value(tool)
                    )
                else:
                    name = str(tool)

                lines.append(f"  - {name}")

        # OUTPUTS
        outputs = step.get("outputs", [])

        if outputs:
            lines.append("")
            lines.append("Removed components:")

            for index, output in enumerate(
                outputs,
                start=1
            ):
                if isinstance(output, dict):
                    name = (
                        output.get("name")
                        or output.get("label")
                        or f"Component {index}"
                    )

                    lines.append(
                        f"  {index}. {name}"
                    )

                    for key, value in output.items():
                        if key in (
                            "name",
                            "label",
                            "image"
                        ):
                            continue

                        lines.append(
                            f"     {format_key(key)}: "
                            f"{format_value(value)}"
                        )

                    image = output.get("image")

                    if (
                        isinstance(image, dict)
                        and image.get("path")
                    ):
                        lines.append(
                            f"     Image: {image['path']}"
                        )

                else:
                    lines.append(
                        f"  {index}. {output}"
                    )

        # CONTINUES AS
        continues_as = step.get("continues_as")

        if continues_as:
            lines.append("")
            lines.append("Remaining assembly:")

            if isinstance(continues_as, list):
                for component in continues_as:
                    lines.append("  - " + str(component.get("name", "Unknown")))
                    if component.get("image"):
                        lines.append("    Image: " + format_value(component["image"]))
            elif isinstance(continues_as, dict):

                for key, value in continues_as.items():

                    if key == "image":
                        image = value

                        if (
                            isinstance(image, dict)
                            and image.get("path")
                        ):
                            lines.append(
                                f"  Image: {image['path']}"
                            )

                    else:
                        lines.append(
                            f"  {format_key(key)}: "
                            f"{format_value(value)}"
                        )

            else:
                lines.append(
                    f"  {continues_as}"
                )

        lines.append("")
        lines.append("")

    # BILL OF MATERIALS
    bom = ir.get("bill_of_materials", [])

    if bom:
        lines.append("BILL OF MATERIALS")
        lines.append("=" * 70)
        lines.append("")

        for index, part in enumerate(
            bom,
            start=1
        ):
            if isinstance(part, dict):

                name = (
                    part.get("name")
                    or part.get("label")
                    or f"Part {index}"
                )

                lines.append(
                    f"{index}. {name}"
                )

                for key, value in part.items():

                    if key in (
                        "name",
                        "label",
                        "image"
                    ):
                        continue

                    lines.append(
                        f"   {format_key(key)}: "
                        f"{format_value(value)}"
                    )

                image = part.get("image")

                if (
                    isinstance(image, dict)
                    and image.get("path")
                ):
                    lines.append(
                        f"   Image: {image['path']}"
                    )

            else:
                lines.append(
                    f"{index}. {part}"
                )

            lines.append("")

    return "\n".join(textwrap.fill(line, width=88, replace_whitespace=False, drop_whitespace=False) if line else "" for line in lines)


def format_key(key):
    return normalize_title(str(key).replace("_", " "))


def format_value(value):

    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            format_value(item)
            for item in value
        )

    if isinstance(value, dict):
        return ", ".join(
            f"{format_key(key)}: {format_value(val)}"
            for key, val in value.items()
            if key != "image"
        )

    return str(value)