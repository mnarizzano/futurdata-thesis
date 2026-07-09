import json
import os
from typing import Optional


class DiagramSerializer:
    """
    A utility catalog class containing static methods to manage disk persistence 
    and document translation workflows for Diagram data models.

    Handles file I/O tracking, robust safety layout validation, and bidirectional 
    JSON parsing protocols using standard dictionary bindings.
    """

    @staticmethod
    def save_to_file(diagram, file_path: str) -> bool:
        """
        Serializes a diagram instance into a formatted JSON document on disk 
        and resets its application modified flags.

        Args:
            diagram (any): The active Diagram instance to serialize and save.
            file_path (str): The target file path location on the local file system.

        Returns:
            bool: True if serialization and disk write succeeded, False otherwise.
        """
        try:
            data = diagram.to_dict()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            diagram.file_path = file_path
            diagram.modified = False
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    @staticmethod
    def load_from_file(file_path: str):
        """
        Reads a saved JSON configuration file from disk, verifies its structure 
        and instantiates a fresh tracking Diagram model mapping its contents.

        Args:
            file_path (str): The absolute or relative system path pointing to the JSON file.

        Returns:
            Diagram or None: An instantiated Diagram model object with populated elements if loading succeeded; None if file errors or validation failures occur.
        """
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
            print(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            print(f"Error loading file: {e}")
            return None

    @staticmethod
    def validate_structure(data: dict) -> bool:
        """
        Validates whether a raw dictionary payload contains the required root keys 
        and structural data types expected for schema integration.

        Args:
            data (dict): The unmarshalled raw data dictionary mapping schema properties.

        Returns:
            bool: True if all structural requirements and data type tests match, False otherwise.
        """
        required_keys = ["metadata", "shapes", "connections"]
        for key in required_keys:
            if key not in data:
                print(f"Missing required key: {key}")
                return False
        if not isinstance(data["metadata"], dict):
            print("Invalid metadata")
            return False
        if not isinstance(data["shapes"], list):
            print("Invalid shapes")
            return False
        if not isinstance(data["connections"], list):
            print("Invalid connections")
            return False
        return True

    @staticmethod
    def export_to_json(diagram, file_path: str, pretty: bool = True) -> bool:
        """
        A wrapper convenience operation that delegates diagram export requests 
        directly over to the standard save file routine pipeline.

        Args:
            diagram (any): The active Diagram object selected for exporting.
            file_path (str): The destination file system location for output delivery.
            pretty (bool): Formatting toggle flag indicating structural pretty printing layout. Defaults to True.

        Returns:
            bool: True if the file was written out smoothly without interruptions, False otherwise.
        """
        return DiagramSerializer.save_to_file(diagram, file_path)
