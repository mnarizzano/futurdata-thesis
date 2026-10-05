"""Stage actual referenced bytes without flattening distinct source images."""
import hashlib
from pathlib import Path

def stage_images(snapshot, root, handler):
    root = Path(root).resolve()
    for shape in snapshot.get("shapes", []):
        ref = shape.get("image_path")
        if not ref:
            continue
        source = Path(handler.get_full_path(ref))
        if not source.is_file():
            continue
        content = source.read_bytes()
        normalized = str(ref).replace("\\", "/")
        relative = normalized if normalized.startswith("images/") else f"images/{hashlib.sha256(content).hexdigest()}{source.suffix.lower()}"
        dest = (root / relative).resolve()
        if root not in dest.parents or (dest.exists() and dest.read_bytes() != content):
            relative = f"images/{hashlib.sha256(content).hexdigest()}{source.suffix.lower()}"
            dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        shape["image_path"] = relative
