import json
import tempfile
import unittest
from pathlib import Path

from graft import InventoryGenerator, main


class InventoryGeneratorTests(unittest.TestCase):
    def test_scan_extracts_markdown_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            readme.write_text("# Demo\n\nFirst useful line.\n", encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].path, "README.md")
            self.assertEqual(entries[0].kind, "markdown")
            self.assertEqual(entries[0].summary, "First useful line.")

    def test_scan_respects_ignored_file_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("private.md\n", encoding="utf-8")
            (root / "private.md").write_text("# Private\n", encoding="utf-8")
            (root / "public.md").write_text("# Public\nVisible summary.\n", encoding="utf-8")

            paths = {entry.path for entry in InventoryGenerator(root).scan()}

            self.assertIn("public.md", paths)
            self.assertNotIn("private.md", paths)

    def test_main_writes_manifest_and_markdown_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("manifest.json\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "notes.md").write_text("# Notes\n", encoding="utf-8")
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root)])

            self.assertEqual(exit_code, 0)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            paths = {item["path"] for item in manifest["files"]}
            self.assertIn("demo.py", paths)
            self.assertIn("<!-- BEGIN INVENTORY -->", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("<!-- BEGIN INVENTORY -->", (root / "notes.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
