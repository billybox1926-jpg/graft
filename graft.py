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
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


VERSION = "0.1.0"
DEFAULT_BEGIN = "<!-- BEGIN INVENTORY -->"
DEFAULT_END = "<!-- END INVENTORY -->"


class GraftError(Exception):
    """Base class for graft failures that should exit cleanly."""


class GraftWriteError(GraftError):
    """Raised when a target file cannot be written."""


class GraftPathError(GraftError):
    """Raised when an output path is outside the scanned root."""


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
        follow_symlinks: bool = True,
    ) -> None:
        self.root = root.resolve()
        self.follow_symlinks = follow_symlinks
        self.begin = begin_marker
        self.end = end_marker
        explicit_exclude_names = set(exclude_names or ())
        default_exclude_names = {
            "__pycache__",
            ".git",
            ".hg",
            ".svn",
            ".DS_Store",
            "__pypackages__",
            "node_modules",
            "dist",
            "build",
            "out",
            "target",
            "proof",
        }
        self.exclude_names = explicit_exclude_names | default_exclude_names

        explicit_exclude_files = set(exclude_files or ())
        default_exclude_files = {"manifest.json"}
        self.exclude_files = explicit_exclude_files | default_exclude_files
        self.exclude_patterns = list(exclude_patterns)
        self._ignore_rules: list[tuple[bool, str]] = []
        self._load_ignore_rules(extra_ignore_file)

    def _load_ignore_rules(self, extra_ignore_file: Path | None) -> None:
        sources: list[Path] = []
        gitignore = self.root / ".gitignore"
        if gitignore.exists():
            sources.append(gitignore)
        if extra_ignore_file and extra_ignore_file.exists() and extra_ignore_file != gitignore:
            sources.append(extra_ignore_file)
        self._ignore_rules = []
        for source in sources:
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                negated = line.startswith("!")
                pattern = line[1:] if negated else line
                self._ignore_rules.append((negated, pattern))

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    def _write_text(self, path: Path, text: str) -> None:
        newline = "\n"
        if path.exists():
            try:
                original = path.read_bytes()
                if original.count(b"\r\n") >= max(1, original.count(b"\n") // 2):
                    newline = "\r\n"
            except OSError:
                pass
        # Surface a readable error instead of an unhandled traceback when the
        # target is read-only, on a full disk, or otherwise unwritable.
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline=newline)
        except OSError as exc:
            raise GraftWriteError(f"cannot write {path}: {exc}") from exc

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

        matched = False
        for negated, raw in [*self._ignore_rules, *[(False, p) for p in self.exclude_patterns]]:
            pattern = raw.replace("\\", "/")
            if not pattern:
                continue
            if pattern.endswith("/") and (rel.startswith(pattern.rstrip("/") + "/") or rel == pattern.rstrip("/")):
                matched = not negated
                continue
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(Path(rel).name, pattern):
                matched = not negated
                continue
            if fnmatch.fnmatch(rel, f"*/{pattern}") or fnmatch.fnmatch(rel, f"{pattern}/*"):
                matched = not negated
                continue
        return bool(matched)

    @classmethod
    def _py_docstring_summary_and_usage(cls, py_path: Path) -> tuple[str, str]:
        try:
            source = cls._read_text(py_path)
            module = ast.parse(source)
            doc = ast.get_docstring(module) or ""
        except (OSError, SyntaxError, UnicodeError):
            return "", ""

        summary = cls._first_line(doc)
        usage_hint = ""
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.lower() in {"usage", "description"}:
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            usage_hint = node.value.value.strip()
                        elif isinstance(node.value, ast.JoinedStr):
                            passage = []
                            for value in node.value.values:
                                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                                    passage.append(value.value)
                            usage_hint = "".join(passage).strip()
                        if usage_hint:
                            break
        usage = ""
        if usage_hint:
            usage = f"Usage: {usage_hint[:140]}"
        else:
            usage = cls._usage_from_doc(doc)

        fallback_usage = f"Usage: python {py_path.name} --help"
        return summary or "", usage or fallback_usage

    @classmethod
    def _usage_from_doc(cls, doc: str) -> str:
        lines = doc.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower().startswith("usage:"):
                rest = stripped[6:].strip()
                if rest:
                    return f"Usage: {rest[:140]}"
                for next_line in lines[index + 1 :]:
                    candidate = next_line.strip()
                    if candidate:
                        return f"Usage: {candidate[:140]}"
                break
        return ""

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
    def _truncate_summary(text: str, limit: int = 140) -> str:
        normalized = " ".join(text.split())
        return normalized[:limit]

    @classmethod
    def _mapping_summary(cls, data: dict[str, Any]) -> str:
        preferred_keys = ("description", "title", "name", "purpose")
        for key in preferred_keys:
            value = data.get(key)
            if isinstance(value, str):
                summary = cls._truncate_summary(value)
                if summary:
                    return summary
        for value in data.values():
            if isinstance(value, dict):
                summary = cls._mapping_summary(value)
                if summary:
                    return summary
        return ""

    @classmethod
    def _json_summary(cls, json_path: Path) -> tuple[str, str]:
        try:
            data = json.loads(cls._read_text(json_path))
        except (OSError, ValueError, UnicodeError):
            return "", ""
        if isinstance(data, dict):
            return cls._mapping_summary(data), ""
        return "", ""

    @classmethod
    def _toml_summary(cls, toml_path: Path) -> tuple[str, str]:
        try:
            text = cls._read_text(toml_path)
        except (OSError, UnicodeError):
            return "", ""
        preferred_keys = ("description", "title", "name", "purpose")
        pattern = re.compile(r'^\s*([A-Za-z0-9_.-]+)\s*=\s*"([^"]*)"')
        matches: dict[str, str] = {}
        for line in text.splitlines()[:300]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = pattern.match(line)
            if not match:
                continue
            dotted_key, value = match.groups()
            key = dotted_key.rsplit(".", 1)[-1].lower()
            if key in preferred_keys:
                summary = cls._truncate_summary(value)
                if summary and key not in matches:
                    matches[key] = summary
        for key in preferred_keys:
            summary = matches.get(key, "")
            if summary:
                return summary, ""
        return "", ""

    @classmethod
    def _yaml_summary(cls, yaml_path: Path) -> tuple[str, str]:
        try:
            text = cls._read_text(yaml_path)
        except (OSError, UnicodeError):
            return "", ""

        preferred_keys = ("description", "title", "name", "purpose")
        scalar_pattern = re.compile(r'^\s*([A-Za-z0-9_.-]+)\s*:\s*(.+?)\s*$')

        for line in text.splitlines()[:300]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if line.startswith((" ", "\t")):
                continue

            match = scalar_pattern.match(line)
            if not match:
                continue
            key, raw_value = match.groups()
            lowered = key.lower()
            if lowered not in preferred_keys:
                continue

            value = raw_value.split(" #", 1)[0].strip()
            if value in {"", "|", ">"} or value.startswith(("[", "{", "- ")):
                continue
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1].strip()

            summary = cls._truncate_summary(value)
            if summary:
                return summary, ""

        return "", ""

    @classmethod
    def _leading_comment_summary(cls, source_path: Path) -> tuple[str, str]:
        text = cls._read_text(source_path)
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("#!"):
            lines = lines[1:]

        for line in lines[:40]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("//"):
                summary = cls._truncate_summary(stripped[2:].strip())
                return summary, ""
            break

        if lines:
            first = lines[0].strip()
            if first.startswith("/*"):
                comment_lines: list[str] = []
                inline_rest = first[first.find("/*") + 2 :]
                if inline_rest:
                    inline_content = inline_rest.replace("*/", "").lstrip("*").strip()
                    if inline_content:
                        comment_lines.append(inline_content)
                if "*/" not in first:
                    for line in lines[1:40]:
                        stripped = line.strip()
                        if "*/" in stripped:
                            before_close = stripped.split("*/", 1)[0]
                            content = before_close.lstrip("*").strip()
                            if content:
                                comment_lines.append(content)
                            break
                        content = stripped.lstrip("*").strip()
                        if content:
                            comment_lines.append(content)
                if comment_lines:
                    return cls._truncate_summary(" ".join(comment_lines)), ""
        return "", ""

    @staticmethod
    def _default_usage(rel_path: Path) -> str:
        if str(rel_path).endswith(".py"):
            return f"Usage: python {rel_path} --help"
        if str(rel_path).endswith(".sh"):
            return f"Usage: bash {rel_path}"
        return ""

    def _escapes_root(self, path: Path) -> bool:
        """True when path resolves outside the scan root (symlink escape)."""
        try:
            resolved = path.resolve()
        except OSError:
            return True
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return True
        return False

    def scan(self) -> list[FileEntry]:
        entries: list[FileEntry] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(self.root).as_posix()
            if self._is_ignored(rel):
                continue
            # A symlink can point outside the scanned tree, which would pull
            # unrelated file content into the manifest. Skip those unless the
            # caller explicitly opts in.
            if not self.follow_symlinks and path.is_symlink():
                continue
            if self.follow_symlinks and path.is_symlink() and self._escapes_root(path):
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
            elif kind == "json":
                summary, usage = self._json_summary(path)
            elif kind == "toml":
                summary, usage = self._toml_summary(path)
            elif kind == "yaml":
                summary, usage = self._yaml_summary(path)
            elif kind in {"javascript", "typescript", "css"}:
                summary, usage = self._leading_comment_summary(path)

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
        begin_index = text.index(self.begin) + len(self.begin)
        end_index = text.index(self.end, begin_index)
        return text[begin_index:end_index]

    def replace_block(self, text: str, block_md: str) -> str:
        if self.begin not in text or self.end not in text:
            return text.rstrip() + "\n\n" + self.begin + "\n" + block_md + "\n" + self.end + "\n"
        begin_index = text.index(self.begin)
        end_index = text.index(self.end, begin_index + len(self.begin))
        return text[:begin_index].rstrip() + "\n\n" + self.begin + "\n" + block_md + "\n" + self.end + text[end_index + len(self.end):]


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
    parser.add_argument(
        "--no-follow-symlinks",
        action="store_true",
        help="Skip symlinked files entirely instead of following them",
    )
    parser.add_argument(
        "--allow-outside-root",
        action="store_true",
        help="Permit --readme/--notes/--manifest paths outside the scanned directory",
    )
    return parser


def resolve_output(root: Path, candidate: Path, *, allow_outside: bool) -> Path:
    """Resolve an output path, refusing to escape the scan root by default.

    graft writes files, so an unconstrained --manifest/--readme/--notes lets a
    caller redirect output anywhere on disk. That is fine for interactive local
    use but undesirable in automation, so escaping the root now requires an
    explicit opt-in.
    """
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if allow_outside:
        return resolved
    try:
        resolved.relative_to(root)
    except ValueError:
        raise GraftPathError(
            f"output path escapes the scanned root: {resolved}\n"
            f"  root: {root}\n"
            f"  pass --allow-outside-root to write here anyway"
        ) from None
    return resolved


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root: Path = args.directory
    if not root.is_dir():
        print(f"[error] Not a directory: {root}", file=sys.stderr)
        return 1
    root = root.resolve()

    try:
        readme = resolve_output(
            root, args.readme or Path("README.md"), allow_outside=args.allow_outside_root
        )
        notes = resolve_output(
            root, args.notes or Path("docs/notes.md"), allow_outside=args.allow_outside_root
        )
        manifest = resolve_output(
            root, args.manifest or Path("manifest.json"), allow_outside=args.allow_outside_root
        )
    except GraftPathError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    generator = InventoryGenerator(
        root,
        begin_marker=args.begin_marker,
        end_marker=args.end_marker,
        exclude_patterns=args.exclude,
        extra_ignore_file=None if args.no_gitignore else (args.ignore_file or (root / ".gitignore")),
        follow_symlinks=not args.no_follow_symlinks,
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

    try:
        generator.write_manifest(entries, manifest)
        print(f"Wrote {manifest}")
        generator.update_targets(entries, [readme, notes])
    except GraftWriteError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 3
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
