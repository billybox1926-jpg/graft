#!/usr/bin/env python3
"""
graft — Auto-generate directory inventories and JSON manifests.

Scans a folder, writes a JSON manifest, and regenerates inventory sections
in Markdown files between configurable markers.

Example:
    graft ./src --readme ./src/README.md --notes ./src/CHANGELOG.md
    graft ./tools --check
    graft . --manifest ./dist/manifest.json --exclude "*.pyc" --exclude "node_modules"
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


VERSION = "0.1.0"
DEFAULT_BEGIN = "<!-- BEGIN INVENTORY -->"
DEFAULT_END = "<!-- END INVENTORY -->"


@dataclass(frozen=True)
class FileEntry:
    path: str
    kind: str
    size_bytes: int
    mtime_iso: str
    summary: str
    usage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "size_bytes": self.size_bytes,
            "mtime_iso": self.mtime_iso,
            "summary": self.summary,
            "usage": self.usage,
        }


class InventoryGenerator:
    def __init__(
        self,
        root: Path,
        *,
        begin_marker: str = DEFAULT_BEGIN,
        end_marker: str = DEFAULT_END,
        exclude_names: set[str] | None = None,
        exclude_files: set[str] | None = None,
        exclude_patterns: Sequence[str] = (),
        extra_ignore_file: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self.begin = begin_marker
        self.end = end_marker
        self.exclude_names = exclude_names or {"__pycache__", ".git", ".hg", ".svn", ".DS_Store"}
        self.exclude_files = exclude_files or {"manifest.json"}
        self.exclude_patterns = list(exclude_patterns)
        self._gitignore_patterns: list[str] = []

        ignore_source = extra_ignore_file or (self.root / ".gitignore")
        if ignore_source.exists():
            self._gitignore_patterns = [
                line.strip()
                for line in ignore_source.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    @staticmethod
    def _mtime_iso(path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")

    @staticmethod
    def _kind_for(path: Path) -> str:
        ext = path.suffix.lower()
        mapping = {
            ".bash": "shell",
            ".css": "css",
            ".go": "go",
            ".html": "html",
            ".js": "javascript",
            ".json": "json",
            ".md": "markdown",
            ".py": "python",
            ".rs": "rust",
            ".sh": "shell",
            ".toml": "toml",
            ".ts": "typescript",
            ".txt": "text",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        return mapping.get(ext, "file")

    @staticmethod
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _is_ignored(self, rel_path: str) -> bool:
        rel = rel_path.replace("\\", "/")
        parts = Path(rel).parts
        if any(part in self.exclude_names for part in parts):
            return True
        if Path(rel).name in self.exclude_files:
            return True

        for pattern in [*self.exclude_patterns, *self._gitignore_patterns]:
            pattern = pattern.replace("\\", "/")
            if not pattern or pattern.startswith("!"):
                continue
            if pattern.endswith("/") and (rel.startswith(pattern.rstrip("/") + "/") or rel == pattern.rstrip("/")):
                return True
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(Path(rel).name, pattern):
                return True
            if fnmatch.fnmatch(rel, f"*/{pattern}") or fnmatch.fnmatch(rel, f"{pattern}/*"):
                return True
        return False

    @classmethod
    def _py_docstring_summary_and_usage(cls, py_path: Path) -> tuple[str, str]:
        try:
            source = cls._read_text(py_path)
            module = ast.parse(source)
            doc = ast.get_docstring(module) or ""
        except (OSError, SyntaxError, UnicodeError):
            return "", ""

        summary = cls._first_line(doc)
        usage = ""
        lines = doc.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower().startswith("usage:"):
                rest = stripped[6:].strip()
                if rest:
                    usage = "Usage: " + rest
                    break
                for next_line in lines[index + 1 :]:
                    candidate = next_line.strip()
                    if candidate:
                        usage = "Usage: " + candidate
                        break
                break
        return summary, usage

    @classmethod
    def _markdown_summary(cls, md_path: Path) -> tuple[str, str]:
        text = cls._read_text(md_path)
        in_generated_block = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line == DEFAULT_BEGIN:
                in_generated_block = True
                continue
            if line == DEFAULT_END:
                in_generated_block = False
                continue
            if in_generated_block or not line:
                continue
            if line.startswith("#"):
                continue
            return line[:140], ""
        return "", ""

    @classmethod
    def _shell_header_summary_and_usage(cls, sh_path: Path) -> tuple[str, str]:
        text = cls._read_text(sh_path)
        summary = ""
        usage = ""
        for line in text.splitlines()[:40]:
            stripped = line.strip()
            if stripped.startswith("#!"):
                continue
            if stripped.startswith("#"):
                content = stripped.lstrip("#").strip()
                if content and not summary:
                    summary = content
                if content.lower().startswith("usage:") and not usage:
                    usage = "Usage: " + content[len("usage:") :].strip()
            elif summary or usage:
                break
        return summary, usage

    @staticmethod
    def _default_usage(rel_path: Path) -> str:
        if str(rel_path).endswith(".py"):
            return f"Usage: python {rel_path} --help"
        if str(rel_path).endswith(".sh"):
            return f"Usage: bash {rel_path}"
        return ""

    def scan(self) -> list[FileEntry]:
        entries: list[FileEntry] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(self.root).as_posix()
            if self._is_ignored(rel):
                continue

            kind = self._kind_for(path)
            summary = ""
            usage = ""

            if kind == "python":
                summary, usage = self._py_docstring_summary_and_usage(path)
            elif kind == "shell":
                summary, usage = self._shell_header_summary_and_usage(path)
            elif kind == "markdown":
                summary, usage = self._markdown_summary(path)

            entries.append(
                FileEntry(
                    path=rel,
                    kind=kind,
                    size_bytes=path.stat().st_size,
                    mtime_iso=self._mtime_iso(path),
                    summary=summary,
                    usage=usage or self._default_usage(rel),
                )
            )
        return entries

    def render_inventory_md(self, entries: list[FileEntry]) -> str:
        lines = [
            "## Inventory",
            "",
            "| File | Type | Description | How to run |",
            "|------|------|-------------|------------|",
        ]
        for entry in entries:
            desc = entry.summary or "(no summary yet)"
            run = entry.usage or ""
            lines.append(f"| `{entry.path}` | {entry.kind} | {desc} | {run} |")
        lines.append("")
        lines.append(f"_Generated: {datetime.now().isoformat(timespec='seconds')}_")
        return "\n".join(lines)

    @staticmethod
    def _strip_generated_line(block_md: str) -> str:
        lines = [line for line in block_md.strip().splitlines() if not line.startswith("_Generated:")]
        return "\n".join(lines).strip()

    @classmethod
    def _stable_manifest_files(cls, entries: list[FileEntry]) -> list[dict[str, str]]:
        return [
            {
                "path": entry.path,
                "kind": entry.kind,
                "summary": entry.summary,
                "usage": entry.usage,
            }
            for entry in entries
        ]

    def _extract_block(self, text: str) -> str:
        if self.begin not in text or self.end not in text:
            return ""
        _, rest = text.split(self.begin, 1)
        block, _ = rest.split(self.end, 1)
        return block

    def replace_block(self, text: str, block_md: str) -> str:
        if self.begin not in text or self.end not in text:
            return text.rstrip() + "\n\n" + self.begin + "\n" + block_md + "\n" + self.end + "\n"
        before, rest = text.split(self.begin, 1)
        _, after = rest.split(self.end, 1)
        return before.rstrip() + "\n\n" + self.begin + "\n" + block_md + "\n" + self.end + after

    def check_targets(
        self,
        entries: list[FileEntry],
        inventory_md: str,
        targets: Sequence[Path],
        manifest_path: Path,
    ) -> int:
        errors: list[str] = []
        expected = self._strip_generated_line(inventory_md)

        for target in targets:
            if not target.exists():
                errors.append(f"missing target: {target}")
                continue
            actual = self._strip_generated_line(self._extract_block(self._read_text(target)))
            if actual != expected:
                errors.append(f"{target.name} inventory is out of date")

        if not manifest_path.exists():
            errors.append(f"{manifest_path.name} is missing")
        else:
            try:
                manifest = json.loads(self._read_text(manifest_path))
                actual_files = manifest.get("files", [])
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {manifest_path.name}: {exc}")
            else:
                stable_actual = [
                    {
                        "path": item.get("path", ""),
                        "kind": item.get("kind", ""),
                        "summary": item.get("summary", ""),
                        "usage": item.get("usage", ""),
                    }
                    for item in actual_files
                ]
                if stable_actual != self._stable_manifest_files(entries):
                    errors.append(f"{manifest_path.name} file inventory is out of date")

        if errors:
            for error in errors:
                print(f"[error] {error}", file=sys.stderr)
            return 1

        print("Generated inventory and manifest are up to date.")
        return 0


    def dry_run_targets(
        self,
        entries: list[FileEntry],
        targets: Sequence[Path],
        manifest_path: Path,
    ) -> None:
        inventory_md = self.render_inventory_md(entries)
        print("Dry run: no files will be written.")

        if manifest_path.exists():
            current = self._read_text(manifest_path)
            manifest = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "root": str(self.root),
                "files": [entry.to_dict() for entry in entries],
            }
            proposed = json.dumps(manifest, indent=2, ensure_ascii=True) + "\n"
            if current == proposed:
                print(f"  unchanged {manifest_path}")
            else:
                print(f"  would update {manifest_path}")
        else:
            print(f"  would create {manifest_path}")

        for target in targets:
            if target.exists():
                original = self._read_text(target)
                updated = self.replace_block(original, inventory_md)
                if original == updated:
                    print(f"  unchanged {target}")
                else:
                    print(f"  would update {target}")
            else:
                print(f"  would create {target}")

    def write_manifest(self, entries: list[FileEntry], manifest_path: Path) -> None:
        manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "root": str(self.root),
            "files": [entry.to_dict() for entry in entries],
        }
        self._write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")

    def update_targets(self, entries: list[FileEntry], targets: Sequence[Path]) -> None:
        inventory_md = self.render_inventory_md(entries)
        for target in targets:
            if target.exists():
                original = self._read_text(target)
                updated = self.replace_block(original, inventory_md)
                self._write_text(target, updated)
                print(f"  updated {target}")
            else:
                self._write_text(target, f"# {target.stem}\n\n{self.begin}\n{inventory_md}\n{self.end}\n")
                print(f"  created {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-generate directory inventory and manifest.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s ./projects
  %(prog)s ./projects --check
  %(prog)s ./src --manifest ./docs/manifest.json
  %(prog)s . --exclude "*.pyc" --exclude "node_modules" --readme README.md --notes docs/notes.md
        """,
    )
    parser.add_argument("directory", type=Path, help="Root directory to scan")
    parser.add_argument("--version", action="version", version=f"graft {VERSION}")
    parser.add_argument("--readme", type=Path, default=None, help="Markdown file to update")
    parser.add_argument("--notes", type=Path, default=None, help="Second Markdown file to update")
    parser.add_argument("--manifest", type=Path, default=None, help="Output JSON manifest path")
    parser.add_argument("--check", action="store_true", help="Validate targets without rewriting files")
    parser.add_argument("--dry-run", action="store_true", help="Preview target changes without writing files")
    parser.add_argument("--begin-marker", default=DEFAULT_BEGIN, help="Opening marker")
    parser.add_argument("--end-marker", default=DEFAULT_END, help="Closing marker")
    parser.add_argument("--exclude", action="append", default=[], help="Additional fnmatch pattern to exclude")
    parser.add_argument("--ignore-file", type=Path, default=None, help="Gitignore-style file to use for exclusions")
    parser.add_argument("--no-gitignore", action="store_true", help="Do not read .gitignore")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root: Path = args.directory
    if not root.is_dir():
        print(f"[error] Not a directory: {root}", file=sys.stderr)
        return 1

    readme = args.readme or (root / "README.md")
    notes = args.notes or (root / "docs/notes.md")
    manifest = args.manifest or (root / "manifest.json")

    generator = InventoryGenerator(
        root,
        begin_marker=args.begin_marker,
        end_marker=args.end_marker,
        exclude_patterns=args.exclude,
        extra_ignore_file=None if args.no_gitignore else (args.ignore_file or (root / ".gitignore")),
    )

    print(f"Scanning {root} ...")
    entries = generator.scan()
    print(f"Found {len(entries)} file(s).")

    inventory_md = generator.render_inventory_md(entries)
    if args.check:
        return generator.check_targets(entries, inventory_md, [readme, notes], manifest)

    if args.dry_run:
        generator.dry_run_targets(entries, [readme, notes], manifest)
        print("Done (dry-run).")
        return 0

    generator.write_manifest(entries, manifest)
    print(f"Wrote {manifest}")
    generator.update_targets(entries, [readme, notes])
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
