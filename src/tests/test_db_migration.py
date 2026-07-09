"""
Unit tests for src/main/utils/db_migration.py

Functions covered: import_json_file, import_json_directory, export_to_json,
migrate_all_json_files. The DatabaseManager is a MagicMock; JSON I/O uses real
temp files. CLI (__main__) is not tested.

Run from the project root (futurdata-thesis/):
    python -m unittest src.tests.test_db_migration -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main.utils import db_migration


def write_json(path, data):
    Path(path).write_text(json.dumps(data), encoding="utf-8")


class ImportJsonFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = MagicMock()
        self.db.save_full_diagram.return_value = 99

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_file_imports_and_returns_id(self):
        path = self.dir / "d.json"
        write_json(path, {"shapes": []})
        ok, diagram_id, msg = db_migration.import_json_file(str(path), self.db)
        self.assertTrue(ok)
        self.assertEqual(diagram_id, 99)
        self.db.save_full_diagram.assert_called_once()
        self.assertIn("d.json", msg)

    def test_missing_shapes_key_rejected(self):
        path = self.dir / "bad.json"
        write_json(path, {"nope": 1})
        ok, diagram_id, msg = db_migration.import_json_file(str(path), self.db)
        self.assertFalse(ok)
        self.assertEqual(diagram_id, 0)
        self.db.save_full_diagram.assert_not_called()

    def test_malformed_json_returns_parse_error(self):
        path = self.dir / "broken.json"
        path.write_text("{ not json", encoding="utf-8")
        ok, diagram_id, msg = db_migration.import_json_file(str(path), self.db)
        self.assertFalse(ok)
        self.assertIn("JSON parse error", msg)

    def test_missing_file_returns_error(self):
        ok, diagram_id, msg = db_migration.import_json_file(
            str(self.dir / "nope.json"), self.db
        )
        self.assertFalse(ok)
        self.assertIn("Error importing file", msg)

    def test_db_exception_is_caught(self):
        path = self.dir / "d.json"
        write_json(path, {"shapes": []})
        self.db.save_full_diagram.side_effect = RuntimeError("boom")
        ok, diagram_id, msg = db_migration.import_json_file(str(path), self.db)
        self.assertFalse(ok)
        self.assertIn("boom", msg)


class ImportJsonDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = MagicMock()
        self.db.save_full_diagram.return_value = 1

    def tearDown(self):
        self.tmp.cleanup()

    def test_imports_all_matching_files(self):
        write_json(self.dir / "a.json", {"shapes": []})
        write_json(self.dir / "b.json", {"shapes": []})
        results = db_migration.import_json_directory(str(self.dir), db=self.db)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r[1] for r in results))

    def test_empty_directory_returns_empty_list(self):
        results = db_migration.import_json_directory(str(self.dir), db=self.db)
        self.assertEqual(results, [])

    def test_mixed_success_and_failure(self):
        write_json(self.dir / "good.json", {"shapes": []})
        write_json(self.dir / "bad.json", {"nope": 1})
        results = db_migration.import_json_directory(str(self.dir), db=self.db)
        statuses = {r[0]: r[1] for r in results}
        self.assertTrue(statuses["good.json"])
        self.assertFalse(statuses["bad.json"])


class ExportToJsonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = MagicMock()

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_writes_file(self):
        self.db.load_full_diagram.return_value = {"shapes": [1, 2]}
        out = self.dir / "out.json"
        ok, msg = db_migration.export_to_json(5, str(out), self.db)
        self.assertTrue(ok)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), {"shapes": [1, 2]})

    def test_missing_diagram_returns_error(self):
        self.db.load_full_diagram.return_value = None
        ok, msg = db_migration.export_to_json(5, str(self.dir / "out.json"), self.db)
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_write_failure_is_caught(self):
        self.db.load_full_diagram.return_value = {"shapes": []}
        # Point output at a non-existent directory to force an OS error.
        ok, msg = db_migration.export_to_json(
            5, str(self.dir / "nope" / "out.json"), self.db
        )
        self.assertFalse(ok)
        self.assertIn("Error exporting diagram", msg)


class MigrateAllJsonFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_counts_and_details(self):
        write_json(self.dir / "good.json", {"shapes": []})
        write_json(self.dir / "bad.json", {"nope": 1})

        db = MagicMock()
        db.db_path = "/tmp/test.db"
        db.save_full_diagram.return_value = 7

        # db_path is None -> the function calls get_database(); patch it to our mock.
        with patch.object(db_migration, "get_database", return_value=db):
            report = db_migration.migrate_all_json_files(str(self.dir))

        self.assertEqual(report["total_files"], 2)
        self.assertEqual(report["successful"], 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["database_path"], "/tmp/test.db")
        self.assertEqual(len(report["details"]["imported"]), 1)
        self.assertEqual(len(report["details"]["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
