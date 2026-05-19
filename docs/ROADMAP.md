# Roadmap

Graft is a small documentation utility for keeping repository inventories honest. The current setup is deliberately modest so it can grow without becoming a dependency magnet.

## Now

- Keep the single-file CLI reliable.
- Maintain unit tests for scanning and summary extraction, ignore behavior, Markdown updates, manifest writing, custom target paths, dry-run behavior, and check-mode pass/fail paths.
- Use GitHub Actions as the basic quality gate.
- Keep runtime dependencies at zero.

## Next

- Decide whether generated `manifest.json` should remain ignored or become a tracked artifact for example projects.
- Add examples that show common workflows: scan current repo, scan a subfolder, write a custom manifest path, and run check mode in CI.
- Continue refining summary heuristics for edge cases while keeping the parser lightweight and standard-library only.

## Later

- Add a small comparison mode for old/new manifests.
- Support optional machine-readable check output for CI dashboards.
- Publish as a package once the license, name, and command surface are final.
