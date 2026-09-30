"""Formatting of resolved material metadata; never interprets numeric IDs."""
def material_text(name, details=None):
    parts = [str(name)] if name else []
    for key, value in (details or {}).items():
        if value is not None and str(value).strip():
            parts.append(f"{key.replace('_name', '').replace('_', ' ').title()}: {value}")
    return "; ".join(parts)
