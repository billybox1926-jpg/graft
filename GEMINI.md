# Graft Project Instructions

## Project Vision
Graft is a "Sovereign Computing" utility designed to be a lightweight, surgical, and dependency-free documentation tool. It "grafts" directory inventories into existing Markdown files using AST parsing and marker-based injection.

## Mandatory Standards

- **Standard Library Only**: NEVER use third-party dependencies (no `pip install`). All logic must rely solely on the Python standard library.
- **CLI-First**: The application must be executable directly from the command line using `argparse`.
- **Self-Documenting**: Every change to the codebase MUST be followed by a run of `graft.py .` to keep the `README.md`, `notes.md`, and `manifest.json` in sync.
- **Cross-Platform**: Maintain compatibility for Windows, macOS, and Linux. Handle pathing and encoding (UTF-8) carefully.

## Architectural Mandates

- **AST-Based Extraction**: Prefer `ast` module for extracting Python docstrings over regex.
- **Plugin-Ready**: Maintain the `InventoryGenerator` class structure to allow for future language-specific extraction logic.
- **Surgical Injection**: Content must be injected only between the `<!-- BEGIN INVENTORY -->` and `<!-- END INVENTORY -->` markers.

## Workflow Rules

- **Verification**: After modifying `graft.py`, always run a syntax check (`python -m py_compile graft.py`) and a self-check (`python graft.py . --check`).
- **CI Consistency**: Ensure the GitHub Actions workflow in `.github/workflows/ci.yml` passes before pushing changes.
- **Zero Drift**: The `manifest.json` is the source of truth for file inventory; ensure it is updated alongside the README.
