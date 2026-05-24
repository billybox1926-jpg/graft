# Contributing to Graft

Graft is a small Python CLI that scans a directory, writes a JSON manifest, and refreshes Markdown inventory tables. Zero runtime dependencies.

**Note:** The Python package name is `graft-inventory` while the console command is `graft`. This is documented in the README and should be preserved.

## Local setup

Python 3.10+ required. No runtime dependencies.

```bash
python -m unittest discover -s tests -v
python graft.py --help
```

For editable install testing:

```bash
python -m venv .venv
. .venv/bin/activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
graft --help
```

## Development rules

- Keep changes dependency-free unless there is a strong reason not to.
- Graft should stay easy to run in a fresh checkout and on small machines.
- Keep generated output (`manifest.json`) deterministic.
- Avoid committing local manifests unless the project intentionally tracks them.

## Licensing

Graft is licensed under Apache-2.0. Contributions are provided under the same license.

## Pull request checklist

- Describe the behavior change in plain language.
- Add or update tests for CLI behavior changes.
- Run `python -m unittest discover -s tests -v`.
- Confirm `graft --help` still works.
