# Graft

Graft is a small Python command-line tool that scans a directory, writes a JSON manifest, and refreshes Markdown inventory tables between stable markers.

## Features

- Scans a target folder.
- Respects common ignored folders and gitignore patterns.
- Extracts simple summaries from Python docstrings, shell headers, and Markdown prose.
- Writes a JSON manifest.
- Updates README and notes inventory sections.
- Supports check mode for CI.

## Requirements

Python 3.10 or newer. No runtime dependencies.

## Packaging and contributor installs

- The intended Python package name is **`graft-inventory`**, as defined in `pyproject.toml`.
- The installed console command remains **`graft`**.
- For local contributor setup, use an editable install from the repository root:

```bash
python -m pip install -e .
```

- Publishing to PyPI is intentionally deferred. Do not add publishing automation unless a maintainer explicitly chooses to handle that in a later issue.

## Quick start

```bash
python graft.py .
python graft.py . --dry-run
python graft.py . --check
python graft.py ./src --readme ./src/README.md --notes ./docs/INVENTORY.md --manifest ./docs/manifest.json
```

## Generated manifest policy

`manifest.json` is generated output and is ignored by default. Keep it untracked unless a project intentionally wants to review manifest changes.

## Documentation

- [Examples](docs/examples.md)
- [Architecture](docs/architecture.md)
- [Contributing](docs/CONTRIBUTING.md)

## Development

```bash
python -m py_compile graft.py
python -m unittest discover -s tests -v
python graft.py --help
```

## License

Graft is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Status

Early setup. The CLI is usable, tests are in place, CI checks the basic Python workflow, and the project is licensed under Apache-2.0.

<!-- BEGIN INVENTORY -->
## Inventory

| File | Type | Description | How to run |
|------|------|-------------|------------|
| `.github/workflows/ci.yml` | yaml | CI |  |
| `.gitignore` | file | (no summary yet) |  |
| `LICENSE` | file | (no summary yet) |  |
| `README.md` | markdown | Graft is a small Python command-line tool that scans a directory, writes a JSON manifest, and refreshes Markdown inventory tables between st |  |
| `docs/CONTRIBUTING.md` | markdown | Thanks for taking a look at Graft. This project is intentionally small: one Python CLI, no runtime dependencies, and a clear job—keep a fold |  |
| `docs/ROADMAP.md` | markdown | Graft is a small documentation utility for keeping repository inventories honest. The core CLI is stable; release readiness comes next. |  |
| `docs/architecture.md` | markdown | Graft is intentionally small: a single Python CLI that scans a directory, extracts lightweight file summaries, writes a JSON manifest, and u |  |
| `docs/examples.md` | markdown | Copy, paste, and run these examples from your repository root. |  |
| `docs/issue_labels.md` | markdown | This file documents the labels used for Graft issues to guide contributors and maintainers. |  |
| `docs/maintainer_workflow.md` | markdown | This document describes how maintainers of Graft should handle issues, pull requests, releases, and repository upkeep. |  |
| `docs/notes.md` | markdown | Notes for the Graft CLI project. |  |
| `docs/suggestions.json` | json | Current project map for keeping Graft small, dependency-free, contributor-friendly, and release-ready. |  |
| `graft.py` | python | graft — Auto-generate directory inventories and JSON manifests. | Usage: python graft.py --help |
| `pyproject.toml` | toml | Generate Markdown inventories and JSON manifests for small codebases. |  |
| `tests/test_graft.py` | python | (no summary yet) | Usage: python tests/test_graft.py --help |

_Generated: 2026-05-19T20:10:00_
<!-- END INVENTORY -->
