# Contributing Guide

Thank you for your interest in contributing to `facebook-personal-ai-automation`!

---

## 🚨 Hard Rules (Read First)

1. **Do NOT modify runtime logic** in `scripts/*.py` without a corresponding test
2. **Do NOT change the output contract** of `post.py` — backward compatibility is critical
3. **All markdown must be UTF-8 clean** — no mojibake
4. **All PRs need a passing CI** (`pytest tests/` + `ruff` lint) before merge

---

## 🛠️ Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/facebook-personal-ai-automation.git
cd facebook-personal-ai-automation

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
make install
# or: pip install -r requirements.txt && playwright install chromium

# 4. Run tests
make test
# Expected: 48 passed, 0 failed
```

---

## 📋 Types of Contributions

### 🐛 Bug Fixes
- Open an issue first with the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
- Check that the bug is reproducible with the exact command and output
- Write a test that fails before your fix and passes after

### ✨ Features
- Open a [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) issue first
- Check [ROADMAP_NEXT_FEATURES.md](docs/ROADMAP_NEXT_FEATURES.md) — it may already be planned
- Discuss approach before writing code

### 📖 Documentation
- Fix typos, improve clarity, add examples
- All Vietnamese text must have correct diacritics (UTF-8)
- Keep command examples and output contract unchanged

### 🔒 Security Issues
- **Do NOT open public issues for security vulnerabilities**
- See [SECURITY.md](SECURITY.md) for responsible disclosure

---

## 🔄 Pull Request Process

1. **Branch from `main`** — not from other feature branches
   ```bash
   git checkout main && git pull
   git checkout -b fix/your-fix-name
   ```

2. **Write tests** for any code changes
   ```bash
   make test        # must pass
   make lint        # must be clean
   ```

3. **Use conventional commit messages:**
   ```
   fix: correct dom_learner XPath branch condition
   feat: add idempotency hash to scheduler queue
   docs: update antigravity integration guide
   test: add AUTH_REQUIRED retry unit test
   refactor: extract shared cookie module
   ```

4. **Open PR** using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)

5. **CI must pass** — GitHub Actions runs `ruff` + `pytest` automatically

---

## 🧪 Testing Standards

```bash
make test          # run all 48 unit tests
make test-cov      # with coverage report (target: >70%)
make lint          # ruff check
```

- Tests go in `tests/` directory
- Test file naming: `test_<module_name>.py`
- Each test function: `test_<what>_<scenario>()`
- Use `unittest.mock` to mock Playwright, filesystem, and subprocess calls
- No real Facebook credentials in tests

---

## 📁 Code Organization

```
scripts/          # Runtime scripts (stable API, requires test coverage)
scripts/lib/      # Shared utilities (cookies, etc.)
skills/           # Agent skill definitions (docs, not code)
docs/             # Documentation
tests/            # pytest test suite
```

---

## 🌐 Language Guidelines

- **Vietnamese:** Use full diacritics. Run: `python -c "open('file.md').read()"` to check encoding
- **Code:** English (variable names, function names, error codes)
- **Comments:** English or Vietnamese (both acceptable)
- **Commit messages:** English preferred

---

## ✅ Contributor Checklist

Before submitting a PR:
```
[ ] Tests pass: make test
[ ] Lint clean: make lint
[ ] No output contract changes (post.py stdout format unchanged)
[ ] No credentials or cookies in commits
[ ] Docs updated if behavior changed
[ ] UTF-8 clean markdown (no Ã, Â, □ characters)
```
