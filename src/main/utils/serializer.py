import json
import os
from pathlib import Path
from typing import Optional


class DiagramSerializer:
    @staticmethod
    def save_to_file(diagram, file_path: str) -> bool:
        try:
            data = diagram.to_dict()
            parent_dir = Path(file_path).parent
            if str(parent_dir) and str(parent_dir) != ".":
                parent_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            diagram.file_path = file_path
            diagram.modified = False
            return True
        except (OSError, TypeError, ValueError) as e:
            return False

    @staticmethod
    def load_from_file(file_path: str):
        try:
            from ..models.diagram import Diagram
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not DiagramSerializer.validate_structure(data):
                raise ValueError("Invalid diagram file structure")
            diagram = Diagram.from_dict(data)
            diagram.file_path = file_path
            diagram.modified = False
            return diagram
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            return None
        except (OSError, TypeError, ValueError) as e:
            return None

    @staticmethod
    def validate_structure(data: dict) -> bool:
        required_keys = ["metadata", "shapes", "connections"]
        for key in required_keys:
            if key not in data:
                return False
        if not isinstance(data["metadata"], dict):
            return False
        if not isinstance(data["shapes"], list):
            return False
        if not isinstance(data["connections"], list):
            return False
        return True

    @staticmethod
    def export_to_json(diagram, file_path: str, pretty: bool = True) -> bool:
        return DiagramSerializer.save_to_file(diagram, file_path)
