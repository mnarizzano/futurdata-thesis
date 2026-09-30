"""Lossless v1 migration: infer only from explicit root/input relationships."""
import copy
from uuid import uuid4

OWNED = ("root_components", "intermediate_components", "leaf_components", "disassembly_steps", "actions", "disassembly_step_actions", "step_output_intermediate", "step_output_leaf")

def migrate_v1(original):
    data = copy.deepcopy(original)
    data["diagrams"] = []
    data["migration_report"] = []
    data["legacy_unresolved"] = {}
    report = data["migration_report"]
    def quarantine(collection, row, reason):
        data[collection].remove(row)
        data["legacy_unresolved"].setdefault(collection, []).append(row)
        report.append(f"{collection}/{row.get('id')}: {reason}; preserved in legacy_unresolved")
    def index(name):
        return {r["id"]: r for r in data[name]}
    for root in data["root_components"]:
        owner = str(uuid4())
        root["diagram_id"] = owner
        data["diagrams"].append({"id": owner, "root_component_id": root["id"], "name": root.get("name", "")})
    roots = index("root_components")
    # Recover erased root IDs only from explicit, unambiguous step-output paths.
    all_components = {"root": roots, "intermediate": index("intermediate_components"), "leaf": index("leaf_components")}
    owners = {(kind, rid):({rid} if kind == "root" else {row["root_component_id"]} if row.get("root_component_id") in roots else set()) for kind, rows in all_components.items() for rid,row in rows.items()}
    for _ in range(len(owners) + 1):
        changed = False
        for step in data["disassembly_steps"]:
            inputs = [(kind, step.get(f"input_{kind}_component_id")) for kind in all_components if step.get(f"input_{kind}_component_id") is not None]
            candidates = owners.get(inputs[0], set()) if len(inputs) == 1 else set()
            for collection, kind, key in (("step_output_intermediate", "intermediate", "intermediate_component_id"), ("step_output_leaf", "leaf", "leaf_component_id")):
                for link in data[collection]:
                    row = all_components[kind].get(link.get(key))
                    if link.get("disassembly_step_id") != step["id"] or not row or row.get("root_component_id") is not None:
                        continue
                    found = owners[(kind, row["id"])]
                    before = len(found)
                    found.update(candidates)
                    changed |= len(found) != before
        if not changed:
            break
    for kind in ("intermediate", "leaf"):
        for rid, row in all_components[kind].items():
            candidates = owners[(kind, rid)]
            if row.get("root_component_id") is None and len(candidates) == 1:
                row["root_component_id"] = next(iter(candidates))
                report.append(f"{kind}_components/{rid}: recovered root from step-output relationship")
    for collection in ("intermediate_components", "leaf_components"):
        for row in list(data[collection]):
            root = roots.get(row.get("root_component_id"))
            if root:
                row["diagram_id"] = root["diagram_id"]
            else:
                quarantine(collection, row, "missing root")
    components = {"root": roots, "intermediate": index("intermediate_components"), "leaf": index("leaf_components")}
    for row in list(data["disassembly_steps"]):
        inputs = [(kind, row.get(f"input_{kind}_component_id")) for kind in components if row.get(f"input_{kind}_component_id") is not None]
        parent = components[inputs[0][0]].get(inputs[0][1]) if len(inputs) == 1 else None
        if parent:
            row["diagram_id"] = parent["diagram_id"]
        else:
            quarantine("disassembly_steps", row, "missing or ambiguous input")
    steps = index("disassembly_steps")
    for action in list(data["actions"]):
        owners = {steps[l["disassembly_step_id"]]["diagram_id"] for l in data["disassembly_step_actions"] if l.get("action_id") == action["id"] and l.get("disassembly_step_id") in steps}
        if len(owners) == 1:
            action["diagram_id"] = owners.pop()
        else:
            quarantine("actions", action, "orphan action" if not owners else "action shared by multiple diagrams")
    actions = index("actions")
    for collection, target, key in (("disassembly_step_actions", actions, "action_id"), ("step_output_intermediate", components["intermediate"], "intermediate_component_id"), ("step_output_leaf", components["leaf"], "leaf_component_id")):
        for row in list(data[collection]):
            step = steps.get(row.get("disassembly_step_id"))
            other = target.get(row.get(key))
            if step and other and step["diagram_id"] == other["diagram_id"]:
                row["diagram_id"] = step["diagram_id"]
            else:
                quarantine(collection, row, "dangling or cross-diagram relationship")
    for collection in OWNED + ("materials", "material_subcategories", "material_types"):
        for row in data[collection]:
            for field, catalog in (("material_id", "materials"), ("color_id", "colors"), ("tool_id", "tools"), ("category_id", "material_categories"), ("subcategory_id", "material_subcategories"), ("type_id", "material_types")):
                value = row.get(field)
                if value is not None and value not in index(catalog):
                    row.setdefault("legacy_references", {})[field] = value
                    row[field] = None
                    report.append(f"{collection}/{row['id']}: unresolved {field}={value}; original retained")
    data["schema_version"] = 2
    return data
