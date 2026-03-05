## PR Summary

<!-- One-line description of what this PR does -->

**Type:** `fix` / `feat` / `docs` / `test` / `refactor` / `chore`

---

## Motivation

<!-- Why is this change needed? Link to the issue if applicable -->
Closes #

---

## Changes Made

<!-- List the specific files changed and what was done -->

| File | Change |
|---|---|
| `scripts/post.py` | ... |
| `docs/...` | ... |

---

## Output Contract Check

> All PRs that touch `scripts/*.py` must verify the contract is unchanged.

- [ ] I have verified that `post.py` stdout still follows the contract:
  ```
  OK: published | url: ... | account: ...
  OK: scheduled <ISO8601>
  WAIT_APPROVAL
  FAIL: <ERROR_CODE> - <reason>
  ```
- [ ] **OR** this PR does not touch runtime scripts (docs/test/chore only)

---

## Testing

```bash
# Commands you ran:
make test        # must pass
make lint        # must be clean
```

- [ ] `make test` — all 48 tests pass
- [ ] `make lint` — 0 ruff warnings
- [ ] New tests added for new behavior (if applicable)
- [ ] Manual test performed with: `python scripts/post.py --account <id> --text "test" --dry-run`

---

## Documentation

- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Agent guides updated if CLI or behavior changed
- [ ] `docs/INDEX.md` updated if new docs were added

---

## Security Checklist

- [ ] No credentials, cookies, API keys committed
- [ ] No sensitive paths hardcoded
- [ ] File permissions maintained (`0o600` for cookie files)

---

## Reviewer Notes

<!-- Anything specific you want the reviewer to focus on or verify -->
