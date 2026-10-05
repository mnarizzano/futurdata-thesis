"""Resolve normalized catalog references at the portable/presentation boundary."""
import copy

class CatalogResolver:
    def __init__(self, repository):
        self.repository = repository

    def enrich(self, snapshot):
        catalogs = {name:{} for name in ("colors", "materials", "tools", "material_categories", "material_subcategories", "material_types")}
        for shape in snapshot["shapes"]:
            for field, collection, getter, label in (("color_id", "colors", "get_color", "color"), ("material_id", "materials", "get_material", "material"), ("tool_id", "tools", "get_tool", "tools")):
                value = shape.get(field)
                if value is None:
                    continue
                record = getattr(self.repository, getter)(value)
                if not isinstance(record, dict):
                    snapshot.setdefault("catalog_warnings", []).append(f"Unresolved {field}: {value}")
                    shape[label] = None
                    continue
                catalogs[collection][record["id"]] = copy.deepcopy(record)
                shape[label] = record.get("name") or None
                if collection == "materials":
                    shape["material_details"] = {k:record.get(k) for k in ("category_name", "subcategory_name", "type_name", "scientific_name", "technical_name", "surface")}
                    # Portable catalogs carry dependencies once, not per component.
                    for key, target in (("category_id", "material_categories"), ("subcategory_id", "material_subcategories"), ("type_id", "material_types")):
                        if record.get(key) is not None:
                            row = self.repository.get_catalog_record(target, record[key])
                            if row:
                                catalogs[target][row["id"]] = row
        # Include transitive hierarchy dependencies, even for sparse legacy materials.
        for collection in ("material_types", "material_subcategories"):
            for record in list(catalogs[collection].values()):
                for key, target in (("category_id", "material_categories"), ("subcategory_id", "material_subcategories")):
                    if record.get(key) is not None:
                        row = self.repository.get_catalog_record(target, record[key])
                        if row:
                            catalogs[target][row["id"]] = row
        snapshot["catalogs"] = {k:list(v.values()) for k,v in catalogs.items() if v}
        return snapshot
