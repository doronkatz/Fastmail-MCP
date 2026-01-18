# Git Hooks

This repository ships git hooks under `githooks/`.

Enable them locally:
```bash
git config core.hooksPath githooks
```

The `pre-commit` hook runs unit tests with coverage and enforces the minimum
threshold. Override the threshold per commit if needed:
```bash
COVERAGE_THRESHOLD=85 git commit
```
