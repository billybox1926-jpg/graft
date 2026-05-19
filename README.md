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

## Quick start

```bash
python graft.py .
python graft.py . --check
python graft.py ./src --readme ./src/README.md --notes ./docs/INVENTORY.md --manifest ./docs/manifest.json
```

## Development

```bash
python -m py_compile graft.py
python -m unittest discover -s tests -v
python graft.py --help
```

## Status

Early setup. The CLI is usable, tests are in place, and CI checks the basic Python workflow. A project license has not been selected yet.

<!-- BEGIN INVENTORY -->
## Inventory

| File | Type | Description | How to run |
|------|------|-------------|------------|
| `.github/workflows/ci.yml` | yaml | (no summary yet) |  |
| `.gitignore` | file | (no summary yet) |  |
| `CONTRIBUTING.md` | markdown | Thanks for taking a look at Graft. This project is intentionally small: one Python CLI, no runtime dependencies, and a clear job |  |
| `README.md` | markdown | Graft is a small Python command-line tool that scans a directory, writes a JSON manifest, and refreshes Markdown inventory tables between stable markers. |  |
| `docs/ROADMAP.md` | markdown | Graft is a small documentation utility for keeping repository inventories honest. The current setup is deliberately modest so it can grow without becoming a dependency |  |
| `graft.py` | python | graft - Auto-generate directory inventories and JSON manifests. | Usage: python graft.py --help |
| `notes.md` | markdown | (no summary yet) |  |
| `pyproject.toml` | toml | (no summary yet) |  |
| `tests/test_graft.py` | python | (no summary yet) | Usage: python tests/test_graft.py --help |

_Generated: 2026-05-19T07:25:00_
<!-- END INVENTORY -->
