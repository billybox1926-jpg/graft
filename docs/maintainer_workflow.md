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

### Versioning policy (lightweight SemVer)

Use a lightweight Semantic Versioning approach for this small CLI project:

- **Patch release (`x.y.Z`)**: bug fixes, docs-only corrections, and low-risk internal fixes that do not change CLI behavior in a breaking way.
- **Minor release (`x.Y.z`)**: backward-compatible feature additions or notable CLI improvements.
- **Major release (`X.y.z`)**: breaking changes to behavior, interfaces, or expectations that require user adjustment.

Guidelines:

- Keep the project lightweight: no new runtime dependencies for release process changes.
- Keep Python compatibility at **3.10+** when preparing releases.
- Do not change the package name or console command as part of routine release work (tracked separately).

### Release checklist

Use this checklist for every intentional release:

1. **Pre-release checks**
   - Confirm the target branch is current and CI is green.
   - Run local verification commands:
     - `python -m unittest discover -s tests -v`
     - `python graft.py . --check`
2. **Version update**
   - Decide patch/minor/major bump using the rules above.
   - Update `pyproject.toml` version to the selected release version.
3. **Tagging**
   - Create the Git tag **after** version updates and verification pass.
   - Use a `v`-prefixed tag format, for example: `v0.1.0`.
4. **GitHub release notes**
   - Create a GitHub Release for the tag and summarize key user-facing changes.
5. **Post-release cleanup**
   - Verify repository docs remain accurate after the release.
   - Open follow-up issues for deferred work discovered during release prep.

### Version and tag alignment

- The version in `pyproject.toml` must match the Git release tag version (`vX.Y.Z`).
- If the tag is `v0.1.0`, `pyproject.toml` must contain version `0.1.0`.

### Publishing status

- Publishing to PyPI is **not required** by this workflow and remains deferred unless intentionally planned in a future change.
- Do not add package publishing automation as part of this issue.

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
