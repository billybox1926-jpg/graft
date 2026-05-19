# Roadmap

Graft is a small documentation utility for keeping repository inventories honest. The core CLI is stable; release readiness comes next.

## Current posture

- Keep the single-file CLI reliable and dependency-free.
- Maintain unit tests for scanning and summary extraction, ignore behavior, Markdown updates, manifest writing, custom target paths, dry-run behavior, and check-mode pass/fail paths.
- Use GitHub Actions as the basic quality gate with smoke checks and the Python unit-test matrix.
- Keep Python 3.10+ compatibility and Windows/PowerShell-friendly workflows.

## Next

- Define the versioning and release process in issue #15.
- Confirm package name, console command, install guidance, and publication readiness in issue #16.
- Keep generated inventory blocks current whenever docs or project layout changes.

## Later

- Add a small comparison mode for old/new manifests if it proves useful.
- Support optional machine-readable check output for CI dashboards.
- Publish beyond GitHub only after release and package-readiness decisions are documented.
