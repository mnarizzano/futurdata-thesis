"""
Database Migration Utility

This module provides utilities to migrate existing JSON diagram files
to the SQLite database.
"""

import os
import json
import glob
from typing import List, Tuple
from ..models.database import DatabaseManager, get_database


def import_json_file(json_path: str, db: DatabaseManager = None) -> Tuple[bool, int, str]:
    """
    Import a single JSON diagram file into the database.

    Args:
        json_path: Path to the JSON file
        db: Optional DatabaseManager instance (uses default if not provided)

    Returns:
        Tuple of (success: bool, diagram_id: int, message: str)
    """
    if db is None:
        db = get_database()

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate the JSON structure
        if 'shapes' not in data:
            return False, 0, f"Invalid diagram file: missing 'shapes' key"

        # Save to database
        diagram_id = db.save_full_diagram(data)

        filename = os.path.basename(json_path)
        return True, diagram_id, f"Successfully imported '{filename}' (ID: {diagram_id})"

    except json.JSONDecodeError as e:
        return False, 0, f"JSON parse error: {e}"
    except FileNotFoundError:
        return False, 0, f"File not found: {json_path}"
    except OSError as e:
        return False, 0, f"File access error: {e}"
    except Exception as e:
        return False, 0, f"Error importing file: {e}"


def import_json_directory(directory: str, pattern: str = "*.json",
                          db: DatabaseManager = None) -> List[Tuple[str, bool, int, str]]:
    """
    Import all JSON diagram files from a directory.

    Args:
        directory: Path to the directory containing JSON files
        pattern: Glob pattern for JSON files (default: "*.json")
        db: Optional DatabaseManager instance

    Returns:
        List of tuples: (filename, success, diagram_id, message)
    """
    if db is None:
        db = get_database()

    results = []
    json_files = glob.glob(os.path.join(directory, pattern))

    for json_path in json_files:
        filename = os.path.basename(json_path)
        success, diagram_id, message = import_json_file(json_path, db)
        results.append((filename, success, diagram_id, message))

    return results


def export_to_json(diagram_id: int, output_path: str,
                   db: DatabaseManager = None) -> Tuple[bool, str]:
    """
    Export a diagram from the database to a JSON file.

    Args:
        diagram_id: The database ID of the diagram
        output_path: Path for the output JSON file
        db: Optional DatabaseManager instance

    Returns:
        Tuple of (success: bool, message: str)
    """
    if db is None:
        db = get_database()

    try:
        data = db.load_full_diagram(diagram_id)
        if data is None:
            return False, f"Diagram with ID {diagram_id} not found"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, f"Successfully exported to '{output_path}'"

    except (OSError, ValueError, TypeError) as e:
        return False, f"Error exporting diagram: {e}"


def migrate_all_json_files(source_dir: str, db_path: str = None) -> dict:
    """
    Migrate all JSON files from a directory to a new database.

    Args:
        source_dir: Directory containing JSON diagram files
        db_path: Optional path for the database file

    Returns:
        Migration report dictionary
    """
    db = DatabaseManager(db_path) if db_path else get_database()

    results = import_json_directory(source_dir, db=db)

    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    report = {
        'total_files': len(results),
        'successful': len(successful),
        'failed': len(failed),
        'database_path': db.db_path,
        'details': {
            'imported': [(r[0], r[2]) for r in successful],
            'errors': [(r[0], r[3]) for r in failed]
        }
    }

    return report


# CLI interface for migration
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate JSON diagram files to SQLite database"
    )
    parser.add_argument(
        "source",
        help="JSON file or directory to import"
    )
    parser.add_argument(
        "-d", "--database",
        help="Path to the SQLite database file",
        default=None
    )
    parser.add_argument(
        "-e", "--export",
        help="Export diagram ID to JSON instead of importing",
        type=int
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path for export",
        default="exported_diagram.json"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all diagrams in the database"
    )
    parser.add_argument(
        "-s", "--stats",
        action="store_true",
        help="Show database statistics"
    )

    args = parser.parse_args()

    db = DatabaseManager(args.database) if args.database else get_database()

    if args.list:
        print("\n=== Diagrams in Database ===\n")
        diagrams = db.get_all_diagrams()
        if not diagrams:
            print("No diagrams found.")
        else:
            for d in diagrams:
                meta = d['metadata']
                print(f"ID: {d['id']}")
                print(f"  Name: {meta['product_name']}")
                print(f"  Author: {meta['author'] or '(none)'}")
                print(f"  Modified: {meta['modified']}")
                print()
        sys.exit(0)

    if args.stats:
        print("\n=== Database Statistics ===\n")
        stats = db.get_statistics()
        print(f"Total Diagrams: {stats['total_diagrams']}")
        print(f"Total Shapes: {stats['total_shapes']}")
        print(f"Total Connections: {stats['total_connections']}")
        print("\nShapes by Type:")
        for shape_type, count in stats['shapes_by_type'].items():
            print(f"  {shape_type}: {count}")
        sys.exit(0)

    if args.export:
        success, message = export_to_json(args.export, args.output, db)
        print(message)
        sys.exit(0 if success else 1)

    # Import mode
    source = args.source

    if os.path.isfile(source):
        success, diagram_id, message = import_json_file(source, db)
        print(message)
        sys.exit(0 if success else 1)

    elif os.path.isdir(source):
        report = migrate_all_json_files(source, args.database)
        print(f"\n=== Migration Report ===")
        print(f"Database: {report['database_path']}")
        print(f"Total files: {report['total_files']}")
        print(f"Successful: {report['successful']}")
        print(f"Failed: {report['failed']}")

        if report['details']['imported']:
            print("\nImported:")
            for filename, diagram_id in report['details']['imported']:
                print(f"  {filename} -> ID: {diagram_id}")

        if report['details']['errors']:
            print("\nErrors:")
            for filename, error in report['details']['errors']:
                print(f"  {filename}: {error}")

        sys.exit(0 if report['failed'] == 0 else 1)

    else:
        print(f"Error: '{source}' is not a valid file or directory")
        sys.exit(1)
