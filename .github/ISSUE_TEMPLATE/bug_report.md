---
name: Bug Report
about: Report a bug or unexpected behavior
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

A clear and concise description of what the bug is.

## Steps to Reproduce

```bash
# Exact command you ran:
python scripts/post.py --account <id> --text "..." --auto-approve

# Or tell us what you did step by step:
1. ...
2. ...
3. ...
```

## Expected Output

What you expected `stdout` to print (last line):
```
OK: published | url: https://...
```

## Actual Output

What actually happened (copy full stdout + stderr):
```
FAIL: DOM_CHANGED - All selectors failed for open_composer
```

## Environment

| Item | Value |
|---|---|
| OS | Windows 11 / Ubuntu 22.04 / macOS |
| Python version | `python --version` |
| Playwright version | `pip show playwright` |
| Script version | `grep __version__ scripts/post.py` |

## Screenshots / Logs

If applicable, attach:
- Screenshot: `test_result_*_after_publish.png` in repo root
- Log: last 20 lines of `references/run-log.jsonl`
- Console output

## Additional Context

- Is this the first time this happens, or is it reproducible every time?
- Does it affect all accounts or just one?
- Did Facebook change its UI recently?
