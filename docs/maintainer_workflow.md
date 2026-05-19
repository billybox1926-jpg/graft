# Maintainer Workflow

This document describes how maintainers of Graft should handle issues, pull requests, releases, and repository upkeep.

## Pull Requests

1. Ensure the branch is up to date with `master`.
2. Verify tests pass locally and in CI.
3. Check that the inventory and manifest updates are correct.
4. Review code style and consistency.
5. Merge with a descriptive commit message once approved.

## Issues

- Apply appropriate labels from `docs/issue_labels.md`.
- Close issues when PRs are merged that resolve them.
- Use `good first issue` and `help wanted` to guide contributors.

## Releases

- Update `pyproject.toml` version.
- Ensure tests and CI pass for all targeted Python versions.
- Tag the release and update CHANGELOG or notes as needed.

## CI

- GitHub Actions runs syntax checks, unit tests, and CLI help verification.
- Check CI logs when reviewing PRs.
- Update workflows if Python version matrix or tooling changes.

## Documentation

- Keep all `docs/` files updated with new features or changes.
- Maintain `docs/suggestions.json` for contributor-friendly suggestions.
- Update inventory blocks in README and notes using the CLI or verify with `--check`.

## Best Practices

- Keep the repository dependency-free for end users.
- Ensure generated content does not overwrite human-authored text outside inventory blocks.
- Use clear commit messages and keep PRs small and focused.
- Review contribution rules in `docs/CONTRIBUTING.md` regularly.
