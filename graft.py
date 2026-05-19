#!/usr/bin/env python3
"""
inventory-manifest — Auto-generate directory inventory and manifest.

Scans any folder, writes a JSON manifest, and regenerates inventory
sections in Markdown files between configurable markers.

Example:
    inventory-manifest ./src --readme ./src/README.md --notes ./src/CHANGELOG.md
    inventory-manifest ./tools --check
    inventory-manifest . --manifest ./dist/manifest.json --exclude "*.pyc" --exclude "node_modules"
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


DEFAULT_BEGIN = "<!-- BEGIN INVENTORY -->"
DEFAULT_END = "<!-- END INVENTORY -->"


@dataclass
class FileEntry:
    path: str          # relative to scan root
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
    ):
        self.root = root.resolve()
        self.begin = begin_marker
        self.end = end_marker
        self.exclude_names = exclude_names or {"__pycache__", ".git", ".hg", ".svn", ".DS_Store"}
        self.exclude_files = exclude_files or {"manifest.json"}
        self.exclude_patterns = list(exclude_patterns)
        self._gitignore_patterns: list[str] = []

        # Load ignore patterns from .gitignore if present and requested
        ignore_source = extra_ignore_file or (self.root / ".gitignore")
        if ignore_source.exists():
            self._gitignore_patterns = [
                line.strip()
                for line in ignore_source.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _read_text(p: Path) -> str:
        return p.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _write_text(p: Path, s: str) -> None:
        p.write_text(s, encoding="utf-8", newline="\n")

    @staticmethod
    def _mtime_iso(p: Path) -> str:
        return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")

    @staticmethod
    def _kind_for(p: Path) -> str:
        if p.is_dir():
            return "dir"
        ext = p.suffix.lower()
        mapping = {
            ".py": "python",
            ".sh": "shell", ".bash": "shell",
            ".md": "markdown",
            ".json": "json",
            ".yml": "yaml", ".yaml": "yaml",
            ".txt": "text",
            ".js": "javascript", ".ts": "typescript",
            ".html": "html", ".css": "css",
            ".rs": "rust", ".go": "go",
        }
        return mapping.get(ext, "file")

    @staticmethod
    def _first_line(s: str) -> str:
        for line in s.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _is_ignored(self, rel_path: str) -> bool:
        """Check path against name, file, pattern, and gitignore exclusions."""
        parts = Path(rel_path).parts
        if any(part in self.exclude_names for part in parts):
            return True
        if Path(rel_path).name in self.exclude_files:
            return True

        for pat in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(Path(rel_path).name, pat):
                return True

        for pat in self._gitignore_patterns:
            if fnmatch.fnmatch(rel_path, pat):
                return True
            # Directory-style patterns
            if pat.endswith("/") and rel_path.startswith(pat.rstrip("/")):
                return True
            # Common gitignore directory wildcards
            if fnmatch.fnmatch(rel_path, f"*/{pat}") or fnmatch.fnmatch(rel_path, f"{pat}/*"):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Extractors
    # ------------------------------------------------------------------ #
    @classmethod
    def _py_docstring_summary_and_usage(cls, py_path: Path) -> tuple[str, str]:
        try:
            src = cls._read_text(py_path)
            mod = ast.parse(src)
            doc = ast.get_docstring(mod) or ""
        except Exception:
            return ("", "")

        summary = cls._first_line(doc)
        usage = ""
        lines = doc.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower().startswith("usage:"):
                rest = stripped[6:].strip()
                if rest:
                    usage = "Usage: " + rest
                    break
                for next_line in lines[i + 1:]:
                    ns = next_line.strip()
                    if ns:
                        usage = "Usage: " + ns
                        break
                break
        return summary, usage

    @classmethod
    def _shell_header_summary_and_usage(cls, sh_path: Path) -> tuple[str, str]:
        text = cls._read_text(sh_path)
        summary = ""
        usage = ""
        for line in text.splitlines()[:40]:
            ls = line.strip()
            if ls.startswith("#!"):
                continue
            if ls.startswith("#"):
                content = ls.lstrip("#").strip()
                if content and not summary:
                    summary = content
                if content.lower().startswith("usage:") and not usage:
                    usage = "Usage: " + content[len("usage:"):].strip()
            else:
                if summary or usage:
                    break
        return summary, usage

    @staticmethod
    def _default_usage(rel_path: str) -> str:
        if rel_path.endswith(".py"):
            return f"Usage: python {rel_path} --help"
        if rel_path.endswith(".sh"):
            return f"Usage: bash {rel_path}"
        return ""

    # ------------------------------------------------------------------ #
    # Core scan
    # ------------------------------------------------------------------ #
    def scan(self) -> list[FileEntry]:
        entries: list[FileEntry] = []
        for p in sorted(self.root.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(self.root).as_posix()
            if self._is_ignored(rel):
                continue

            kind = self._kind_for(p)
            summary, usage = "", ""

            if kind == "python":
                summary, usage = self._py_docstring_summary_and_usage(p)
            elif kind == "shell":
                summary, usage = self._shell_header_summary_and_usage(p)

            if not usage:
                usage = self._default_usage(rel)

            entries.append(
                FileEntry(
                    path=rel,
                    kind=kind,
                    size_bytes=p.stat().st_size,
                    mtime_iso=self._mtime_iso(p),
                    summary=summary,
                    usage=usage,
                )
            )
        return entries

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def render_inventory_md(self, entries: list[FileEntry]) -> str:
        lines = [
            "## Inventory",
            "",
            "| File | Type | Description | How to run |",
            "|------|------|-------------|------------|",
        ]
        for e in entries:
            desc = e.summary if e.summary else "(no summary yet)"
            run = e.usage if e.usage else ""
            lines.append(f"| `{e.path}` | {e.kind} | {desc} | {run} |")
        lines.append("")
        lines.append(f"_Generated: {datetime.now().isoformat(timespec='seconds')}_")
        return "\n".join(lines)

    @staticmethod
    def _strip_generated_line(block_md: str) -> str:
        lines = [
            line for line in block_md.strip().splitlines()
            if not line.startswith("_Generated:")
        ]
        return "\n".join(lines).strip()

    @classmethod
    def _stable_manifest_files(cls, entries: list[FileEntry]) -> list[dict[str, str]]:
        return [
            {
                "path": e.path,
                "kind": e.kind,
                "summary": e.summary,
                "usage": e.usage,
            }
            for e in entries
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

    # ------------------------------------------------------------------ #
    # Validation / Write
    # ------------------------------------------------------------------ #
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

        print("✅ Generated inventory and manifest are up to date.")
        return 0

    def write_manifest(self, entries: list[FileEntry], manifest_path: Path) -> None:
        manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "root": str(self.root),
            "files": [e.to_dict() for e in entries],
        }
        self._write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")

    def update_targets(self, entries: list[FileEntry], targets: Sequence[Path]) -> None:
        inventory_md = self.render_inventory_md(entries)
        for target in targets:
            if target.exists():
                original = self._read_text(target)
                updated = self.replace_block(original, inventory_md)
                self._write_text(target, updated)
                print(f"  ✓ updated {target.relative_to(Path.cwd()) if target.is_relative_to(Path.cwd()) else target}")
            else:
                # Create with markers if missing
                target.write_text(
                    f"# {target.stem}\n\n"
                    f"{self.begin}\n{inventory_md}\n{self.end}\n",
                    encoding="utf-8",
                    newline="\n",
                )
                print(f"  ✓ created {target.relative_to(Path.cwd()) if target.is_relative_to(Path.cwd()) else target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-generate directory inventory and manifest.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s ./projects
  %(prog)s ./projects --check
  %(prog)s ./src --manifest ./docs/manifest.json
  %(prog)s . --exclude "*.pyc" --exclude "node_modules" --readme README.md
        """,
    )
    parser.add_argument("directory", type=Path, help="Root directory to scan")
    parser.add_argument(
        "--readme", type=Path, default=None,
        help="Markdown file to inject inventory into (default: <directory>/README.md)"
    )
    parser.add_argument(
        "--notes", type=Path, default=None,
        help="Second Markdown file to inject inventory into (default: <directory>/notes.md)"
    )
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="Output JSON manifest path (default: <directory>/manifest.json)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Validate targets without rewriting files"
    )
    parser.add_argument(
        "--begin-marker", default=DEFAULT_BEGIN,
        help=f"Opening marker (default: '{DEFAULT_BEGIN}')"
    )
    parser.add_argument(
        "--end-marker", default=DEFAULT_END,
        help=f"Closing marker (default: '{DEFAULT_END}')"
    )
    parser.add_argument(
        "--exclude", action="append", default=[],
        help="Additional fnmatch patterns to exclude (can be used multiple times)"
    )
    parser.add_argument(
        "--ignore-file", type=Path, default=None,
        help="Path to a gitignore-style file to use for exclusions (defaults to .gitignore in scanned directory)"
    )
    parser.add_argument(
        "--no-gitignore", action="store_true",
        help="Do not read .gitignore from the scanned directory"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root: Path = args.directory
    if not root.is_dir():
        print(f"[error] Not a directory: {root}", file=sys.stderr)
        return 1

    readme = args.readme or (root / "README.md")
    notes = args.notes or (root / "notes.md")
    manifest = args.manifest or (root / "manifest.json")

    generator = InventoryGenerator(
        root,
        begin_marker=args.begin_marker,
        end_marker=args.end_marker,
        exclude_patterns=args.exclude,
        extra_ignore_file=None if args.no_gitignore else (args.ignore_file or (root / ".gitignore")),
    )

    print(f"🔍 Scanning {root} …")
    entries = generator.scan()
    print(f"   Found {len(entries)} file(s).")

    inventory_md = generator.render_inventory_md(entries)

    if args.check:
        return generator.check_targets(entries, inventory_md, [readme, notes], manifest)

    generator.write_manifest(entries, manifest)
    try:
        display_manifest = manifest.relative_to(Path.cwd()) if manifest.is_relative_to(Path.cwd()) else manifest
    except ValueError:
        display_manifest = manifest
    print(f"   Wrote {display_manifest}")

    generator.update_targets(entries, [readme, notes])
    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
