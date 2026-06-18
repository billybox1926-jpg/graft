# Graft CLI examples

Copy, paste, and run these examples from your repository root.

## 1) Scan a full repository

```bash
python graft.py .
```

What this does with defaults:

- Scans all files under `.` (except ignored paths).
- Writes `manifest.json` in the repo root.
- Refreshes inventory blocks in `README.md` and `docs/notes.md`.

## 2) Scan only a subfolder

```bash
python graft.py ./docs
```

What this does:

- Scans only the `docs/` tree.
- Writes `docs/manifest.json`.
- Tries to refresh inventory in `docs/README.md` and `docs/docs/notes.md` (only if those files exist).

Tip: for subfolder scans, explicitly set output targets so updates go where you expect.

```bash
python graft.py ./docs \
  --readme ./README.md \
  --notes ./docs/notes.md \
  --manifest ./docs/manifest.json
```

## 3) Use custom README / notes / manifest targets

```bash
python graft.py . \
  --readme ./docs/INVENTORY.md \
  --notes ./docs/STATUS.md \
  --manifest ./artifacts/manifest.json
```

What this does:

- Writes manifest to `artifacts/manifest.json`.
- Updates inventory blocks in `docs/INVENTORY.md` and `docs/STATUS.md`.
- Leaves default files unchanged unless you target them.

## 4) Use `--check` in CI (no files written)

`--check` verifies whether generated output is already up to date.

```bash
python graft.py . --check
```

Exit behavior:

- `0` when no changes would be needed.
- `1` when manifest and/or inventory content is out of date.

Example CI step:

```bash
python graft.py . --check
```

If this fails, run `python graft.py .` locally, commit the updated generated files, and push.
