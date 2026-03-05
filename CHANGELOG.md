# Changelog

All notable changes to `facebook-personal-ai-automation` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Adaptive rate-limit backoff (F01)
- Per-account log isolation (F02)
- Proxy credential encryption via OS keyring (F03)
- HTTP health-check endpoint for scheduler daemon (F06)

---

## [2.1.0] — 2026-03-05

### Added
- **48 unit tests** across `cookies.py`, `scheduler.py`, `account_manager.py`, `post.py`
- **GitHub Actions CI** — ruff lint + pytest on Python 3.11/3.12
- **Makefile** — `make install`, `make test`, `make lint`, `make dom-learn`
- **`pytest.ini`** — project-level test config
- **docs/agent-guides/** — Clawbot, Claude Code, Antigravity integration guides
- **docs/USAGE_MULTI_AGENT.md** — Decision matrix, orchestration patterns, shared error protocol
- **docs/acceptance-tests/multi-agent-uat.md** — 26 UAT test cases including TC-REG-001 regression guard
- **docs/ROADMAP_NEXT_FEATURES.md** — 15 future features with priority, effort, risk ratings
- **docs/INDEX.md** — Central documentation map
- **CONTRIBUTING.md**, **SECURITY.md**, **CODE_OF_CONDUCT.md** — Community standard files
- **Confirmation Policy** in all 3 agent guides (no surprise publish)
- **Known Limitations** section in USAGE_MULTI_AGENT.md
- **Metadata headers** (`last_updated`, `compatible_scripts`) in all docs
- **`scripts/lib/cookies.py`** — Shared cookie normalization module (extracted from 4 files)

### Changed
- **README.md** — Rewritten with natural Vietnamese developer tone, storytelling opener
- **`scheduler.py`** — `POST_TIMEOUT_SECONDS` env var (default 300s, was hardcoded 120s)
- **`scheduler.py`** — `MIN_POST_GAP_MINUTES` env var (default 15 min between posts per account)
- **`scheduler.py`** — `SCHEDULER_MAX_WORKERS` env var (default 3 concurrent posts)
- **`scheduler.py`** — `ThreadPoolExecutor` for concurrent account posting
- **`post.py`** — Added `run_id` to all log events, `account_id` and `version` fields
- **`post.py`** — `datr` cookie presence warning
- **`post.py`** — `extract_post_url` polling loop (10s wait for `/posts/` permalink)
- **File permissions** — `os.chmod(0o600)` on cookies and fingerprint files after write
- **`requirements.txt`** — Pinned exact versions (`playwright==1.42.0`, `pytz==2024.1`)

### Fixed
- **`dom_learner.py:225`** — `action.startswith("//")` → `primary.startswith("//")` (XPath branch bug)
- **`update_account_stats`** — `except Exception: pass` → `log_event(warn)` (silent fail fixed)
- **`extract_post_url`** — Added polling loop to handle video posts where URL renders late

### Security
- Added `proxies/proxy-list.json` to `.gitignore`
- Added `references/schedule-queue.json` to `.gitignore`
- Cookie file permissions hardened to `0o600`
- Sensitive data redacted from log output

---

## [2.0.0] — 2026-01-15

### Added
- Multi-account support with `accounts/accounts.json`
- Proxy rotation via `scripts/proxy_manager.py`
- Browser fingerprint spoofing via `scripts/fingerprint_gen.py`
- `dom_learner.py` — self-healing selector discovery
- Structured logging to `references/run-log.jsonl`
- Story post support (`scripts/test_story.py`)
- Reel post support (`scripts/test_reel.py`)
- `scripts/scheduler.py` — queue-based scheduling daemon

### Changed
- Output contract standardized: `OK: published | url: ... | account: ...`
- All scripts now use `argparse` CLI interface

---

## [1.0.0] — 2025-11-01

### Added
- Initial release: single-account Facebook post automation
- `scripts/post.py` — basic text + image posting
- `scripts/account_manager.py` — account init and session test
- Playwright-based browser automation (Chromium headless)
