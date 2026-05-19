# Roadmap

Graft is a small documentation utility for keeping repository inventories honest. The current setup is deliberately modest so it can grow without becoming a dependency magnet.

## Now

- Keep the single-file CLI reliable.
- Maintain unit tests for scanning, ignoring, Markdown updates, and manifest writing.
- Use GitHub Actions as the basic quality gate.
- Keep runtime dependencies at zero.

## Next

- Decide whether generated `manifest.json` should remain ignored or become a tracked artifact for example projects.
- Add examples that show common workflows: scan current repo, scan a subfolder, write a custom manifest path, and run check mode in CI.
- Improve summaries for more file types without adding heavyweight parsers.
- Consider a dry-run mode that prints proposed file changes without writing them.

## Later

- Add a small comparison mode for old/new manifests.
- Support optional machine-readable check output for CI dashboards.
- Publish as a package once the license, name, and command surface are final.
