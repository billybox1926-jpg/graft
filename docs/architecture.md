# Architecture

Graft is intentionally small: a single Python CLI that scans a directory, extracts lightweight file summaries, writes a JSON manifest, and updates Markdown inventory blocks.

## Design goals

- Keep the runtime dependency-free.
- Make the tool easy to run in fresh checkouts, Codespaces, and CI.
- Prefer predictable text output over hidden state.
- Keep generated sections clearly bounded by stable markers.
- Make failures easy to understand from command-line output.

## Main flow

1. Parse CLI options in `build_parser()`.
2. Resolve the scan root and output targets in `main()`.
3. Build an `InventoryGenerator` for the scan root.
4. Scan files with `InventoryGenerator.scan()`.
5. Render an inventory table with `render_inventory_md()`.
6. In normal mode, write the JSON manifest and update Markdown targets.
7. In check mode, compare generated output against existing files and return a non-zero exit code when anything is stale.
8. In dry-run mode, print the proposed file changes without writing files.

## Core components

### `FileEntry`

`FileEntry` is the small data model for discovered files. It stores the relative path, detected kind, file size, modified time, summary, and usage string. The `to_dict()` method provides the manifest representation.

### `InventoryGenerator`

`InventoryGenerator` owns the scanning, summary extraction, rendering, manifest writing, dry-run previews, and check-mode validation logic. Keeping this behavior together makes the command-line entry point thin and keeps the tests simple.

### Summary extraction

Summary extraction is deliberately conservative while covering the file types commonly used in this repository:

- Python files use module docstrings and optional `Usage:` lines.
- Shell files use leading comment headers and optional `Usage:` lines.
- Markdown files use the first non-heading prose line outside generated inventory blocks.
- JSON files use description-like fields (`description`, `title`, `name`, `purpose`) with recursive lookup in nested objects.
- TOML files use description-like string keys, including dotted keys such as `project.description`.
- YAML files use description-like top-level scalar fields when available.
- JavaScript, TypeScript, and CSS files use leading `//`, `/* ... */`, and JSDoc-style `/** ... */` header comments.
- Unknown files are listed without summaries.

This keeps the parser fast and safe while still making the inventory useful.

## Generated content

Graft updates Markdown between these markers:

```markdown
<!-- BEGIN INVENTORY -->
<!-- END INVENTORY -->
```

Anything outside those markers is treated as human-authored content and should be preserved.

The JSON manifest is generated from the same scan data as the Markdown table. By default, `manifest.json` is ignored so normal runs do not create noisy repository diffs unless a maintainer intentionally tracks a manifest example.

## Defaults

- README target: `README.md`
- Notes target: `docs/notes.md`
- Manifest target: `manifest.json`

The notes default lives in `docs/` so support material stays grouped away from the public project landing page.

## Testing strategy

The current tests cover:

- Summary extraction for Markdown, JSON, TOML, YAML, JavaScript/TypeScript/CSS leading comments, and JSDoc-style block comments.
- Ignore pattern behavior.
- Manifest writing and default target behavior.
- Markdown inventory block creation.
- Custom README, notes, and manifest output target paths.
- Dry-run behavior, including custom output targets.
- Check-mode pass/fail behavior for stale and current generated outputs.

Additional future tests can focus on edge cases and larger fixture-style repositories, but the primary CLI guardrails are now under unit-test coverage.

## Constraints

Graft should stay friendly to low-resource environments. Avoid adding dependencies for parsing or formatting unless the feature clearly cannot be implemented with the Python standard library.
