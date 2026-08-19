import json
import tempfile
import unittest
from pathlib import Path

from graft import (
    GraftError,
    GraftPathError,
    GraftWriteError,
    InventoryGenerator,
    main,
    resolve_output,
)


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


    def test_scan_extracts_json_summary_from_description_like_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            config.write_text('{\"name\": \"Demo config\", \"description\": \"Readable summary from json.\"}\n', encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "json")
            self.assertEqual(entries[0].summary, "Readable summary from json.")

    def test_scan_extracts_toml_summary_from_description_like_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "pyproject.toml"
            project.write_text('[project]\nname = "demo"\ndescription = "Project summary from toml."\n', encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "toml")
            self.assertEqual(entries[0].summary, "Project summary from toml.")

    def test_scan_extracts_toml_summary_from_dotted_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "pyproject.toml"
            project.write_text('project.description = "Dotted key summary."\n', encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "toml")
            self.assertEqual(entries[0].summary, "Dotted key summary.")

    def test_scan_extracts_javascript_leading_comment_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "app.js"
            script.write_text('// User-facing behavior summary.\nconst x = 1;\n', encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "javascript")
            self.assertEqual(entries[0].summary, "User-facing behavior summary.")


    def test_scan_extracts_yaml_summary_from_description_like_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.yaml"
            config.write_text("description: Useful yaml summary.\n", encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "yaml")
            self.assertEqual(entries[0].summary, "Useful yaml summary.")

    def test_scan_yaml_keeps_fallback_when_no_clear_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "settings.yml"
            data.write_text("items:\n  - one\n  - two\n", encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "yaml")
            self.assertEqual(entries[0].summary, "")

    def test_scan_extracts_jsdoc_style_block_comment_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "app.js"
            script.write_text("/**\n * JSDoc style header summary.\n */\nconst x = 1;\n", encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "javascript")
            self.assertEqual(entries[0].summary, "JSDoc style header summary.")

    def test_scan_keeps_fallback_when_no_clear_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data.json"
            data.write_text('{\"items\": [1, 2, 3]}\n', encoding="utf-8")

            entries = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore").scan()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].summary, "")

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
            notes = root / "docs" / "notes.md"
            (root / ".gitignore").write_text("manifest.json\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root)])

            self.assertEqual(exit_code, 0)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            paths = {item["path"] for item in manifest["files"]}
            self.assertIn("demo.py", paths)
            self.assertIn("<!-- BEGIN INVENTORY -->", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("<!-- BEGIN INVENTORY -->", notes.read_text(encoding="utf-8"))
            self.assertFalse((root / "notes.md").exists())


class CustomTargetTests(unittest.TestCase):
    def test_custom_manifest_output_path_writes_without_default_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_manifest = root / "artifacts" / "manifest.json"
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root), "--manifest", str(custom_manifest)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(custom_manifest.exists())
            self.assertFalse((root / "manifest.json").exists())

    def test_custom_readme_target_writes_without_default_readme_or_default_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_readme = root / "docs" / "INVENTORY.md"
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root), "--readme", str(custom_readme), "--notes", str(root / "docs" / "STATUS.md")])

            self.assertEqual(exit_code, 0)
            self.assertTrue(custom_readme.exists())
            self.assertIn("<!-- BEGIN INVENTORY -->", custom_readme.read_text(encoding="utf-8"))
            self.assertFalse((root / "README.md").exists())
            self.assertFalse((root / "docs" / "notes.md").exists())

    def test_custom_notes_target_writes_without_default_notes_or_default_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_notes = root / "docs" / "STATUS.md"
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root), "--notes", str(custom_notes), "--readme", str(root / "docs" / "INVENTORY.md")])

            self.assertEqual(exit_code, 0)
            self.assertTrue(custom_notes.exists())
            self.assertIn("<!-- BEGIN INVENTORY -->", custom_notes.read_text(encoding="utf-8"))
            self.assertFalse((root / "docs" / "notes.md").exists())
            self.assertFalse((root / "README.md").exists())



class DryRunTests(unittest.TestCase):
    def test_dry_run_does_not_create_missing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main([str(root), "--dry-run"])

            self.assertEqual(exit_code, 0)
            self.assertFalse((root / "manifest.json").exists())
            self.assertFalse((root / "README.md").exists())
            self.assertFalse((root / "docs" / "notes.md").exists())

    def test_dry_run_does_not_modify_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            notes = root / "docs" / "notes.md"
            manifest = root / "manifest.json"
            notes.parent.mkdir(parents=True, exist_ok=True)
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")
            readme.write_text("# Demo\n", encoding="utf-8")
            notes.write_text("# Notes\n", encoding="utf-8")
            manifest.write_text('{"files": []}\n', encoding="utf-8")

            before_readme = readme.read_text(encoding="utf-8")
            before_notes = notes.read_text(encoding="utf-8")
            before_manifest = manifest.read_text(encoding="utf-8")

            exit_code = main([str(root), "--dry-run"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(before_readme, readme.read_text(encoding="utf-8"))
            self.assertEqual(before_notes, notes.read_text(encoding="utf-8"))
            self.assertEqual(before_manifest, manifest.read_text(encoding="utf-8"))

    def test_dry_run_with_custom_targets_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_readme = root / "docs" / "INVENTORY.md"
            custom_notes = root / "docs" / "STATUS.md"
            custom_manifest = root / "artifacts" / "manifest.json"
            (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")

            exit_code = main(
                [
                    str(root),
                    "--dry-run",
                    "--readme",
                    str(custom_readme),
                    "--notes",
                    str(custom_notes),
                    "--manifest",
                    str(custom_manifest),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(custom_readme.exists())
            self.assertFalse(custom_notes.exists())
            self.assertFalse(custom_manifest.exists())


class CheckModeTests(unittest.TestCase):
    def _prepare_generated_outputs(self, root: Path) -> tuple[Path, Path, Path]:
        readme = root / "README.md"
        notes = root / "docs" / "notes.md"
        manifest = root / "manifest.json"
        (root / "demo.py").write_text("print('demo')\n", encoding="utf-8")
        readme.write_text("# Demo\n", encoding="utf-8")
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text("# Notes\n", encoding="utf-8")
        exit_code = main([str(root)])
        self.assertEqual(exit_code, 0)
        return readme, notes, manifest

    def test_check_mode_passes_when_outputs_are_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme, notes, manifest = self._prepare_generated_outputs(root)
            before_readme = readme.read_text(encoding="utf-8")
            before_notes = notes.read_text(encoding="utf-8")
            before_manifest = manifest.read_text(encoding="utf-8")

            exit_code = main([str(root), "--check"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(before_readme, readme.read_text(encoding="utf-8"))
            self.assertEqual(before_notes, notes.read_text(encoding="utf-8"))
            self.assertEqual(before_manifest, manifest.read_text(encoding="utf-8"))

    def test_check_mode_fails_when_readme_inventory_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme, notes, manifest = self._prepare_generated_outputs(root)
            readme.write_text("# Demo\n\nStale inventory text.\n", encoding="utf-8")
            before_readme = readme.read_text(encoding="utf-8")
            before_notes = notes.read_text(encoding="utf-8")
            before_manifest = manifest.read_text(encoding="utf-8")

            exit_code = main([str(root), "--check"])

            self.assertEqual(exit_code, 1)
            self.assertEqual(before_readme, readme.read_text(encoding="utf-8"))
            self.assertEqual(before_notes, notes.read_text(encoding="utf-8"))
            self.assertEqual(before_manifest, manifest.read_text(encoding="utf-8"))

    def test_check_mode_fails_when_manifest_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme, notes, manifest = self._prepare_generated_outputs(root)
            manifest.unlink()
            before_readme = readme.read_text(encoding="utf-8")
            before_notes = notes.read_text(encoding="utf-8")

            exit_code = main([str(root), "--check"])

            self.assertEqual(exit_code, 1)
            self.assertFalse(manifest.exists())
            self.assertEqual(before_readme, readme.read_text(encoding="utf-8"))
            self.assertEqual(before_notes, notes.read_text(encoding="utf-8"))


class OutputPathContainmentTests(unittest.TestCase):
    """graft writes files, so output paths must stay inside the scanned root
    unless the caller explicitly opts out."""

    def test_resolve_output_allows_paths_inside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            resolved = resolve_output(root, Path("docs/notes.md"), allow_outside=False)
            self.assertEqual(resolved, root / "docs" / "notes.md")

    def test_resolve_output_rejects_escaping_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = (Path(tmp) / "proj").resolve()
            root.mkdir()
            with self.assertRaises(GraftPathError):
                resolve_output(root, Path("../escaped.json"), allow_outside=False)

    def test_resolve_output_rejects_escaping_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = (Path(tmp) / "proj").resolve()
            root.mkdir()
            outside = Path(tmp).resolve() / "escaped.json"
            with self.assertRaises(GraftPathError):
                resolve_output(root, outside, allow_outside=False)

    def test_resolve_output_permits_escape_with_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = (Path(tmp) / "proj").resolve()
            root.mkdir()
            outside = Path(tmp).resolve() / "escaped.json"
            resolved = resolve_output(root, outside, allow_outside=True)
            self.assertEqual(resolved, outside)

    def test_cli_refuses_escaping_manifest_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            (root / "a.py").write_text("x\n", encoding="utf-8")
            escaped = Path(tmp) / "escaped.json"

            exit_code = main([str(root), "--manifest", str(escaped)])

            self.assertEqual(exit_code, 2)
            self.assertFalse(escaped.exists())

    def test_cli_allows_escaping_manifest_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            (root / "a.py").write_text("x\n", encoding="utf-8")
            escaped = Path(tmp) / "escaped.json"

            exit_code = main([
                str(root), "--manifest", str(escaped), "--allow-outside-root",
            ])

            self.assertEqual(exit_code, 0)
            self.assertTrue(escaped.exists())


class SymlinkContainmentTests(unittest.TestCase):
    """A symlink pointing outside the scanned tree would pull unrelated file
    content into the manifest. Creating real symlinks needs privileges that are
    not available on every CI runner, so the containment predicate is tested
    directly as well as end to end."""

    def _generator(self, root: Path) -> InventoryGenerator:
        return InventoryGenerator(root, extra_ignore_file=root / "missing.ignore")

    def test_escapes_root_detects_inside_and_outside(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = (Path(tmp) / "proj").resolve()
            (root / "sub").mkdir(parents=True)
            gen = self._generator(root)

            inside = root / "sub" / "a.py"
            inside.write_text("x\n", encoding="utf-8")
            self.assertFalse(gen._escapes_root(inside))

            outside = Path(tmp).resolve() / "secret.txt"
            outside.write_text("secret\n", encoding="utf-8")
            self.assertTrue(gen._escapes_root(outside))

    def test_escapes_root_treats_unresolvable_paths_as_escaping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            gen = self._generator(root)

            class Unresolvable:
                def resolve(self):
                    raise OSError("dangling link")

            # Fail safe: if we cannot tell where it points, do not index it.
            self.assertTrue(gen._escapes_root(Unresolvable()))

    def test_no_follow_symlinks_flag_is_wired_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x\n", encoding="utf-8")

            default_gen = self._generator(root)
            self.assertTrue(default_gen.follow_symlinks)

            strict = InventoryGenerator(
                root,
                extra_ignore_file=root / "missing.ignore",
                follow_symlinks=False,
            )
            self.assertFalse(strict.follow_symlinks)
            # Regular files are unaffected by the flag.
            self.assertEqual([e.path for e in strict.scan()], ["a.py"])

    @unittest.skipUnless(hasattr(__import__("os"), "symlink"), "symlink unsupported")
    def test_symlink_escaping_root_is_skipped(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            (root / "a.py").write_text("x\n", encoding="utf-8")
            outside = Path(tmp) / "secret.txt"
            outside.write_text("secret\n", encoding="utf-8")

            try:
                os.symlink(outside, root / "link.txt")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"cannot create symlink: {exc}")

            paths = [e.path for e in self._generator(root).scan()]
            self.assertIn("a.py", paths)
            self.assertNotIn("link.txt", paths)


class WriteErrorTests(unittest.TestCase):
    """An unwritable target should produce a readable error and a non-zero
    exit code rather than an unhandled traceback."""

    def test_write_text_raises_graft_write_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blocker = root / "a.py"
            blocker.write_text("x\n", encoding="utf-8")
            gen = InventoryGenerator(root, extra_ignore_file=root / "missing.ignore")

            # Treating an existing file as a directory cannot succeed on any
            # platform, so this exercises the OSError path deterministically.
            with self.assertRaises(GraftWriteError) as ctx:
                gen._write_text(blocker / "nested" / "out.json", "data")

            self.assertIn("cannot write", str(ctx.exception))

    def test_graft_write_error_is_a_graft_error(self):
        self.assertTrue(issubclass(GraftWriteError, GraftError))
        self.assertTrue(issubclass(GraftPathError, GraftError))

    def test_cli_reports_write_failure_with_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x\n", encoding="utf-8")
            blocker = root / "blocked"
            blocker.write_text("not a directory\n", encoding="utf-8")

            exit_code = main([
                str(root), "--manifest", str(blocker / "nested" / "m.json"),
            ])

            self.assertEqual(exit_code, 3)


if __name__ == "__main__":
    unittest.main()
