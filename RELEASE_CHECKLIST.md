# Release Checklist

Use this checklist before every release (merge to `main` and version tag).

---

## Pre-Release (before branch freeze)

### Code Quality
- [ ] `make test` — all 48 unit tests pass, 0 failures
- [ ] `make lint` — 0 ruff warnings
- [ ] No `TODO` / `FIXME` / `HACK` comments left unresolved for this release
- [ ] `scripts/*.py` output contract unchanged (see [contract](#output-contract-check))

### Output Contract Check
```bash
# Dry-run to confirm contract format still intact
python scripts/post.py --account <test_id> --text "release test" --dry-run
# Must output exactly: WAIT_APPROVAL
```

### Security
- [ ] `accounts/` not in git tracking (`git status accounts/` should show nothing)
- [ ] `proxies/proxy-list.json` not in git tracking
- [ ] `references/schedule-queue.json` not in git tracking
- [ ] No hardcoded credentials in any new files
- [ ] File permissions check: `stat accounts/*/cookies.json` shows `0600`

### Documentation
- [ ] `CHANGELOG.md` updated with new version entry (Added/Changed/Fixed/Security)
- [ ] `README.md` version badge or quickstart reflects any new CLI flags
- [ ] All new features documented in `docs/`
- [ ] `docs/INDEX.md` references all new docs
- [ ] Agent guides updated if CLI or output contract changed (even if backward-compatible)

### Backward Compatibility
- [ ] All existing `--account`, `--text`, `--media`, `--schedule`, `--dry-run`, `--auto-approve` flags still work
- [ ] `account_manager.py` subcommands (`init`, `list`, `test`, `assign`, `remove`) unchanged
- [ ] `scheduler.py` queue JSON schema unchanged (all existing fields still present)

---

## Release Steps

```bash
# 1. Update version references
# - CHANGELOG.md: move [Unreleased] → [X.Y.Z] - YYYY-MM-DD
# - README.md: update Version badge if shown
# - Each script: update __version__ = "X.Y.Z"

# 2. Commit version bump
git add CHANGELOG.md README.md scripts/*.py
git commit -m "chore: bump version to X.Y.Z"

# 3. Tag the release
git tag -a vX.Y.Z -m "Release X.Y.Z - <summary>"
git push origin main --tags

# 4. Create GitHub Release
# Go to: https://github.com/ptadigi/facebook-personal-ai-automation/releases/new
# - Tag: vX.Y.Z
# - Title: vX.Y.Z — <one-line summary>
# - Body: copy relevant section from CHANGELOG.md
```

---

## Post-Release

- [ ] GitHub Release published with correct CHANGELOG notes
- [ ] CI badge on README still reflects `main` branch status
- [ ] All open issues addressed or labeled `next-release`
- [ ] Update `docs/ROADMAP_NEXT_FEATURES.md` — mark completed items, add post-release next steps

---

## Rollback Plan

If a critical bug is discovered after release:

```bash
# Revert to previous tag
git revert HEAD
git push origin main

# Or cherry-pick fix to release branch
git checkout -b hotfix/vX.Y.Z-1
git cherry-pick <fix-commit>
git tag vX.Y.Z-1 -m "Hotfix: <description>"
git push origin hotfix/vX.Y.Z-1 --tags
```

---

## Output Contract Reference (must not change)

```
OK: published | url: https://www.facebook.com/<user>/posts/<id> | account: <id>
OK: scheduled <ISO8601>
WAIT_APPROVAL
FAIL: AUTH_REQUIRED - <reason>
FAIL: DOM_CHANGED - <reason>
FAIL: RATE_LIMIT - <reason>
FAIL: PUBLISH_FAILED - <reason>
```
