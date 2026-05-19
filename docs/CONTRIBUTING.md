# Contributing

Thanks for taking a look at Graft. This project is intentionally small: one Python CLI, no runtime dependencies, and a clear job—keep a folder's inventory and manifest current.

## Local setup

Use Python 3.10 or newer.

```bash
python --version
python -m unittest discover -s tests -v
python graft.py --help
```

No package install is required for basic development. To test the console script packaging path, use an editable install in a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
graft --help
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Development rules

Keep changes dependency-free unless there is a strong reason not to. Graft should stay easy to run in a fresh checkout, on small machines, and inside lightweight automation.

### Lint and format policy (lightweight)

Graft uses [Ruff](https://docs.astral.sh/ruff/) as optional **developer tooling** for lint and format checks. Ruff is configured in `pyproject.toml`, but it is **not** required for basic CLI usage and is currently **not enforced in CI**.

Policy:

- Runtime dependencies must remain zero.
- Lint/format checks are local, opt-in quality checks for contributors.
- CI continues to validate syntax, tests, and CLI behavior only.
- Python compatibility remains 3.10+.

If you want to run lint/format checks locally, use:

```bash
python -m pip install ruff
python -m ruff check .
python -m ruff format --check .
```

To apply formatting changes:

```bash
python -m ruff format .
```

Before opening a pull request, run:

```bash
python -m py_compile graft.py
python -m unittest discover -s tests -v
python graft.py --help
```

## Licensing

Graft is licensed under the Apache License, Version 2.0. Unless explicitly stated otherwise, contributions submitted to this repository are provided under the same Apache-2.0 license.

## Pull request checklist

- Explain the behavior change in plain language.
- Add or update tests for CLI behavior changes.
- Keep generated output deterministic where possible.
- Avoid committing local manifests unless the project intentionally decides to track them.
