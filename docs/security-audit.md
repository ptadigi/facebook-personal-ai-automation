# Security & Architecture Audit
**Repo:** `ptadigi/facebook-personal-ai-automation`  
**Date:** 2026-03-05  
**Role:** Senior Security Engineer + Senior Python Architect  
**Scope:** Full codebase — 7 scripts, config, references

---

## (A) Executive Summary — For Founder

1. 🔴 **Cookie file path is logged to run-log** — `cookie_file` field in `schedule-queue.json` is a plain path, no encryption. If log is exposed, attacker knows session cookie location.
2. 🔴 **Scheduler builds `subprocess.run` command with raw user-supplied text** — `--text`, `--link`, `--media` values from queue JSON go directly into `cmd[]` list. Currently safe (list form), but one future refactor to string concatenation creates shell injection.
3. 🔴 **`cookies.json` stored in root of repo** — `.gitignore` protects it, but it's co-located with code. One accidental `git add .` without `.gitignore` = full session leak.
4. 🟠 **No file permission hardening** — `accounts/*/cookies.json` and `fingerprint.json` are world-readable (0644) on Linux/Mac. Should be 0600.
5. 🟠 **`except Exception: pass` in `update_account_stats`** — silently swallows write failures. If `accounts.json` is corrupted or locked, stats are lost with no alert.
6. 🟠 **`schedule-queue.json` has no schema validation** — malformed entries cause silent `status=failed` with unclear error message. No UUID deduplication check.
7. 🟠 **`dom_learner.py` does not inject fingerprint** — runs with default Playwright UA, exposing a bot fingerprint during selector discovery.
8. 🟠 **Single `run-log.jsonl` for all accounts** — no account-level log isolation. Multi-account debugging is painful; log grows unbounded.
9. 🟡 **No version pinning in `requirements.txt`** — `playwright>=1.42.0` allows any future breaking version. Should pin exact: `playwright==1.42.0`.
10. 🟡 **`scheduler.py` subprocess timeout is 120s hardcoded** — no configurable override. A slow video upload can timeout the scheduler.
11. 🟡 **`fingerprint_gen.py` seeds hash from account ID string** — deterministic, but predictable. Adversary who knows account ID can precompute fingerprint.
12. 🟡 **`proxy_manager.py` stores proxy passwords in plaintext JSON** — `proxy-list.json` is in repo root. Currently gitignored, but no encryption at rest.
13. 🟡 **No idempotency on scheduler queue** — duplicate entries with same text/time can be added without conflict detection.
14. 🟡 **`dom_learner.py` has no rate-limit guard** — rapid re-execution of selector probing triggers FB bot signals.
15. 🟡 **`open_composer` click in `dom_learner.py` uses wrong branch** — line 225: `if action.startswith("//")` should be `if primary.startswith("//")`.
16. 🟢 **No `__version__` or semver tracking in scripts** — impossible to trace which deployed version produced a specific log entry.
17. 🟢 **`scheduler.py` daemon has no health-check endpoint** — no way to verify daemon is alive without reading process list.
18. 🟢 **`test_all_formats.py` is not a proper test suite** — no assertions, no exit codes per test, no isolation. Runs as integration demo, not CI-ready.
19. 🟢 **No `conftest.py` or pytest setup** — unit tests nonexistent. Only manual test scripts.
20. 🟢 **`config.example.json` is not actually loaded by any script** — all scripts use `argparse` defaults, ignoring config file. Config file is decorative.

---

## (B) Technical Findings — Detailed

### A. Security

---

#### A1 — Cookie file exposure in queue JSON
- **Severity:** 🔴 Critical
- **Evidence:** `scheduler.py:239` — `"cookie_file": args.cookie_file` stored in `schedule-queue.json`
- **Impact:** `schedule-queue.json` is NOT in `.gitignore`. Accidental commit exposes cookie file path. If queue contains old absolute paths (e.g. `C:\Users\Admin\...`), it reveals system structure.
- **Fix short-term:** Add `schedule-queue.json` to `.gitignore`
- **Fix long-term:** Store cookie_file as relative path only; reference via account_id instead
- **Effort:** S

---

#### A2 — Proxy passwords stored in plaintext
- **Severity:** 🟠 High
- **Evidence:** `proxy_manager.py` — `proxy-list.json` contains `"password": "plaintext"`
- **Impact:** If `proxy-list.json` is accidentally committed or leaked, all proxy credentials are exposed
- **Fix short-term:** Add `proxies/proxy-list.json` to `.gitignore`
- **Fix long-term:** Use OS keyring (`keyring` library) or env-var-based credential injection
- **Effort:** M

---

#### A3 — File permissions not enforced
- **Severity:** 🟠 High
- **Evidence:** `account_manager.py:cmd_init` — files created with default umask (0644)
- **Impact:** On shared Linux systems, cookies and fingerprints are readable by all users in same group
- **Fix short-term:** Add `os.chmod(path, 0o600)` after writing any cookies/fingerprint file
- **Fix long-term:** Create an `accounts/` directory with `chmod 700`
- **Effort:** S

---

#### A4 — `dom_learner.py` no-fingerprint risk
- **Severity:** 🟠 High
- **Evidence:** `dom_learner.py:203` — `browser.new_context(viewport={"width": 1280, "height": 800})` — no UA, no fingerprint, no cookies injected into context (only page-level)
- **Impact:** Running dom_learner with default headless UA sends a clear bot signal to Facebook during the probing session
- **Fix:** Load fingerprint from account's `fingerprint.json` and apply to `new_context()` before probing
- **Effort:** M

---

#### A5 — Log contains post text content
- **Severity:** 🟡 Medium
- **Evidence:** `scheduler.py:155` — `log_event(..., f"post.py stderr: {stderr[:200]}")` — stderr may include post text
- **Impact:** Log files may contain PII or sensitive post content
- **Fix:** Sanitize log output — strip post text from stderr before logging
- **Effort:** S

---

### B. Reliability

---

#### B1 — Silent failure in `update_account_stats`
- **Severity:** 🟠 High
- **Evidence:** `post.py:update_account_stats` — `except Exception: pass`
- **Impact:** If `accounts.json` is write-locked or corrupted, stat update is silently dropped. `daily_post_count` and `last_post_url` become stale.
- **Fix:** Log warning to `run-log.jsonl` on failure: `log_event(run_log, "stats", "warn", f"Failed to update stats: {exc}")`
- **Effort:** S

---

#### B2 — Scheduler timeout too short for large videos
- **Severity:** 🟠 High
- **Evidence:** `scheduler.py:149` — `timeout=120`
- **Impact:** Posting a large video (>50MB) takes 120-180s upload. Scheduler kills the process mid-upload.
- **Fix:** Make timeout configurable: `--post-timeout` arg, default 300s for video
- **Effort:** S

---

#### B3 — No idempotency guard in scheduler
- **Severity:** 🟡 Medium
- **Evidence:** `scheduler.py:cmd_add` — no duplicate detection
- **Impact:** If `scheduler.py --add` is run twice by mistake, same post is queued and submitted twice
- **Fix:** Hash `(text[:100] + scheduled_at)` and check for existing entry before appending
- **Effort:** S

---

#### B4 — `open_composer` bug in `dom_learner.py`
- **Severity:** 🟠 High (functional bug)
- **Evidence:** `dom_learner.py:225` — `if action.startswith("//")` should be `if primary.startswith("//")`
- **Impact:** If the working primary selector is an XPath, it's passed as CSS selector → click fails silently, all subsequent probes probe an un-opened composer
- **Fix:** Change `action.startswith` → `primary.startswith`
- **Effort:** S (1 line)

---

#### B5 — `extract_post_url` is best-effort with no timeout
- **Severity:** 🟡 Medium
- **Evidence:** `post.py:extract_post_url` — uses `page.query_selector_all()` with no wait
- **Impact:** For video posts, Facebook takes up to 60s to render the post permalink. URL extraction runs immediately → "URL not captured" is logged even though post succeeded.
- **Fix:** Add a 10s polling loop waiting for `a[href*='/posts/']` to appear before giving up
- **Effort:** M

---

### C. Observability

---

#### C1 — No `run_id` / trace correlation
- **Severity:** 🟠 High
- **Evidence:** All log events (auth, compose, publish) lack a shared `run_id`
- **Impact:** Impossible to correlate a sequence of log events from a single run in multi-account scenarios
- **Fix:** Generate `run_id = uuid4()[:8]` at start of `main()`, pass to all `log_event()` calls, add as field in log schema
- **Effort:** M

---

#### C2 — Log schema inconsistency between scripts
- **Severity:** 🟡 Medium
- **Evidence:** `post.py` logs `{timestamp, phase, status, note, error_code}` but `scheduler.py` logs `{timestamp, phase, status, note, error_code: null}` — never sets `error_code` from subprocess result
- **Fix:** Parse `FAIL: <CODE>` from subprocess stdout and populate `error_code` field in scheduler log
- **Effort:** S

---

#### C3 — `run-log.jsonl` grows unbounded
- **Severity:** 🟡 Medium
- **Evidence:** No rotation logic anywhere
- **Impact:** On long-running servers, log file grows indefinitely
- **Fix:** Add log rotation: keep last N=1000 lines, or integrate Python `logging.handlers.RotatingFileHandler`
- **Effort:** M

---

#### C4 — Recommended log schema (standardized)

```jsonc
{
  "timestamp":  "2026-03-05T12:30:00+07:00",   // ISO 8601 with tz
  "run_id":     "a1b2c3d4",                      // 8-char uuid, per-invocation
  "account_id": "pham_thanh",                    // or null for legacy mode
  "phase":      "publish",                        // auth|compose|media|publish|schedule|error|stats
  "status":     "ok",                             // ok|fail|retry|warn|skipped
  "note":       "Post published",
  "error_code": null,                             // AUTH_REQUIRED|DOM_CHANGED|RATE_LIMIT|PUBLISH_FAILED
  "url":        "https://facebook.com/posts/..." // when available
}
```

---

### D. Architecture

---

#### D1 — `config.example.json` is never loaded
- **Severity:** 🟡 Medium
- **Evidence:** No script calls `json.load("config.json")` — all use `argparse` defaults
- **Impact:** Config file is misleading; operators edit it thinking it has effect
- **Fix:** Implement `load_config()` that merges `config.json` → env vars → argparse. Priority: argparse > env > config.

---

#### D2 — Cookie inject logic duplicated in 4 files
- **Severity:** 🟡 Medium
- **Evidence:** `post.py:inject_cookies`, `dom_learner.py:inject_cookies`, `test_story.py`, `test_reel.py` — all copy the same cookie normalization logic
- **Fix:** Extract to `scripts/shared/cookies.py` module
- **Effort:** M

---

#### D3 — Story and Reel flows are test scripts, not production modules
- **Severity:** 🟡 Medium
- **Evidence:** `test_story.py`, `test_reel.py` — named "test_" but used in production flows
- **Impact:** Naming is confusing; test scripts should not be production entry points
- **Fix:** Rename to `story.py` and `reel.py`; create `tests/` directory for actual test harnesses
- **Effort:** M

---

#### D4 — `post.py` is 816 lines — too large
- **Severity:** 🟡 Medium
- **Evidence:** `post.py` contains: cookie load, fingerprint, proxy, auth, compose, media, publish, URL extract, stats, multi-account — all in one file
- **Fix:** Split into modules: `lib/auth.py`, `lib/compose.py`, `lib/publish.py`, `lib/media.py`
- **Effort:** L

---

### E. Performance

---

#### E1 — Sequential account execution
- **Severity:** 🟡 Medium
- **Evidence:** `scheduler.py:run_daemon` — processes queue entries one-by-one in a `for` loop
- **Impact:** 5 accounts scheduled at 10:00 → they execute sequentially, last one runs at 10:08+
- **Fix:** Use `concurrent.futures.ThreadPoolExecutor(max_workers=3)` with one thread per account
- **Effort:** M

---

#### E2 — `time.sleep(60)` polling in scheduler
- **Severity:** 🟢 Low
- **Evidence:** `scheduler.py:211`
- **Impact:** Posts can fire up to 60s late; not suitable for time-sensitive campaigns
- **Fix:** Heapq-based next-fire-time scheduler: sleep exactly until next post time instead of polling
- **Effort:** L

---

### F. Maintainability

---

#### F1 — No version tracking in scripts
- **Severity:** 🟢 Low
- **Fix:** Add `__version__ = "2.0.0"` to each script; include in log schema

---

#### F2 — `requirements.txt` unpinned
- **Severity:** 🟡 Medium
- **Evidence:** `playwright>=1.42.0` — allows any future version
- **Fix:** Pin: `playwright==1.42.0`, `pytz==2024.1`. Add `pip-tools` for reproducible builds.

---

#### F3 — No `Makefile` or task runner
- **Severity:** 🟢 Low
- **Fix:** Add `Makefile` with: `make test`, `make lint`, `make install`, `make dom-learn`

---

### G. Compliance Risk

---

#### G1 — Post content repetition risk
- **Severity:** 🔴 Critical (platform ToS)
- **Evidence:** Scheduler enqueues identical text with no deduplication
- **Impact:** Duplicate content detection → account restriction
- **Fix:** MD5 hash of `(text + media_hash)` stored in queue; block re-queue of same hash within 24h

---

#### G2 — No posting frequency limiter
- **Severity:** 🟠 High
- **Evidence:** Scheduler fires all due posts immediately, no inter-post delay
- **Impact:** 10 posts scheduled at 10:00 execute within 5 minutes → rate limit + bot detection
- **Fix:** Enforce minimum 15-30 minute gap between posts per account; configurable in `rotation-rules.json`

---

#### G3 — Missing `datr` cookie validation
- **Severity:** 🟠 High
- **Evidence:** `inject_cookies()` does not validate that `datr` cookie is present
- **Impact:** Sessions without `datr` cookie are instantly suspicious to Facebook's integrity systems
- **Fix:** Add warning if `datr` is missing from cookie set: `if not any(c["name"] == "datr" for c in cookies): log WARN`

---

## (C) Remediation Roadmap

### Phase 1 — 48 Hours (Production Blocking)

| # | Action | Severity | Effort | Owner |
|---|---|---|---|---|
| 1 | Add `schedule-queue.json` to `.gitignore` | 🔴 | S | Dev |
| 2 | Fix `dom_learner.py:225` `action` → `primary` variable bug | 🔴 | S | Dev |
| 3 | `os.chmod(0o600)` on cookies/fingerprint files after write | 🟠 | S | Dev |
| 4 | Add `datr` cookie presence warning | 🟠 | S | Dev |
| 5 | Silent `except pass` → `log_event(warn)` in `update_account_stats` | 🟠 | S | Dev |
| 6 | Make scheduler post timeout configurable (default 300s) | 🟠 | S | Dev |
| 7 | Add minimum inter-post delay (15 min) per account in scheduler | 🟠 | S | Dev |
| 8 | Add duplicate content hash check in scheduler `cmd_add` | 🔴 | S | Dev |
| 9 | Pin exact versions in `requirements.txt` | 🟡 | S | Dev |
| 10 | Strip post text from stderr before logging in scheduler | 🟡 | S | Dev |

---

### Phase 2 — 2 Weeks (Reliability + Observability)

| # | Action | Severity | Effort |
|---|---|---|---|
| 11 | Add `run_id` to all log events | 🟠 | M |
| 12 | Standardize log schema across all scripts | 🟡 | M |
| 13 | Implement `extract_post_url` polling loop (10s wait for `/posts/`) | 🟡 | M |
| 14 | Inject fingerprint in `dom_learner.py` context | 🟠 | M |
| 15 | Extract shared `cookies.py` module, remove 4× duplication | 🟡 | M |
| 16 | Parse scheduler subprocess stdout → populate `error_code` in log | 🟡 | S |
| 17 | `ThreadPoolExecutor` for concurrent account posting in scheduler | 🟡 | M |
| 18 | Log rotation: max 1000 lines in `run-log.jsonl` | 🟡 | M |
| 19 | Implement `load_config()` that actually reads `config.json` | 🟡 | M |
| 20 | Add `__version__` to each script, include in log | 🟢 | S |

---

### Phase 3 — 1-2 Months (Architecture + Scale)

| # | Action | Severity | Effort |
|---|---|---|---|
| 21 | Split `post.py` (816 lines) into `lib/auth.py`, `lib/compose.py`, `lib/publish.py` | 🟡 | L |
| 22 | Rename `test_story.py` → `story.py`, `test_reel.py` → `reel.py` | 🟡 | S |
| 23 | Implement heapq-based scheduler (exact-time fire, no polling) | 🟢 | L |
| 24 | Add proxy credential encryption via OS keyring | 🟠 | L |
| 25 | Build CI pipeline: `pytest tests/` + `ruff` linting on push | 🟢 | M |
| 26 | Write unit tests (see test cases below) | 🟢 | L |
| 27 | Add `Makefile` with `make test`, `make lint`, `make dom-learn` | 🟢 | S |
| 28 | Account-level log isolation: `references/logs/<account_id>/run-log.jsonl` | 🟡 | M |

---

## Top 10 — Do Immediately to Reduce Production Risk

```
[ ] 1. git add references/schedule-queue.json to .gitignore
[ ] 2. Fix dom_learner.py:225 action → primary (1 line bug)
[ ] 3. chmod 0600 on cookies and fingerprint files
[ ] 4. Add datr cookie presence warning in inject_cookies()
[ ] 5. Replace except pass → log_event(warn) in update_account_stats
[ ] 6. Set scheduler subprocess timeout to 300s (configurable)
[ ] 7. Add minimum 15-min inter-post delay per account
[ ] 8. Add content hash deduplication in scheduler cmd_add
[ ] 9. Pin playwright==1.42.0 in requirements.txt
[ ] 10. Strip post text from run-log before writing
```

---

## Required Test Cases

### Unit Tests (pytest)

```python
# test_cookies.py
test_load_cookies_flat_list()           # valid JSON array
test_load_cookies_wrapped()             # {"cookies": [...]} format
test_load_cookies_missing_file()        # FileNotFoundError
test_load_cookies_invalid_json()        # ValueError
test_inject_cookies_sameSite_norm()     # invalid sameSite → "None"
test_datr_missing_warning()             # warn if datr not in cookies

# test_scheduler.py
test_parse_dt_with_timezone()           # "+07:00" preserved
test_parse_dt_naive_fallback()          # no tz → local tz
test_parse_dt_invalid()                 # raises ValueError
test_load_queue_empty_file()            # returns []
test_load_queue_corrupt_json()          # returns []
test_cmd_add_duplicate_hash()           # blocks re-queue of same content
test_cmd_cancel_pending()               # status → cancelled
test_cmd_cancel_not_found()             # prints error, no crash

# test_account_manager.py
test_init_empty_cookies_path()          # no crash on empty path
test_list_missing_fingerprint()         # ❌ shown, no crash
test_reels_url_no_trailing_slash()      # profile_url + /reels/ correct

# test_fingerprint_gen.py
test_js_str_escape_single_quote()       # ' → \'
test_js_str_escape_backslash()          # \ → \\
test_generate_deterministic()           # same seed → same fingerprint
test_canvas_noise_injected()            # ctx2d used, not ctx
```

### Integration Tests

```python
test_post_text_only_live()              # requires valid cookies
test_post_single_image_live()
test_post_video_url_captured()          # URL not "not captured"
test_story_post_complete()
test_reel_post_no_crash_after_close()   # ctx-after-close fix
test_scheduler_fires_due_post()
test_dom_learner_updates_selector_map()
```

### E2E / Negative Tests

```python
test_auth_expired_cookies()             # FAIL: AUTH_REQUIRED
test_dom_changed_no_selector()          # FAIL: DOM_CHANGED
test_rate_limit_detection()             # FAIL: RATE_LIMIT
test_schedule_timezone_mismatch()       # UTC post at +07:00 time
test_proxy_unreachable()                # rotate to next proxy
test_duplicate_schedule_blocked()       # content hash check
test_large_video_upload_no_timeout()    # 300s timeout holds
```

---

## Logging Standard

### Taxonomy

| `phase` | `status` | `error_code` | When |
|---|---|---|---|
| `auth` | `ok/fail` | `AUTH_REQUIRED` | Cookie injection + verify |
| `compose` | `ok/fail` | `DOM_CHANGED` | Open composer, text, media |
| `media` | `ok/fail/retry` | `PUBLISH_FAILED` | File upload, wait |
| `publish` | `ok/fail/retry` | `PUBLISH_FAILED/RATE_LIMIT` | Post button click |
| `schedule` | `ok/fail` | — | Queue add/fire |
| `stats` | `ok/warn` | — | Update accounts.json |
| `error` | `fail` | any | Unhandled exception |

### Schema

```python
{
    "timestamp":  str,       # ISO 8601 with tz
    "run_id":     str,       # 8-char uuid4 per invocation
    "account_id": str|None,  # account id or null
    "phase":      str,       # see taxonomy above
    "status":     str,       # ok|fail|retry|warn|skipped
    "note":       str,       # human-readable description
    "error_code": str|None,  # error enum or null
    "url":        str|None,  # post URL when published
    "version":    str,       # script __version__
}
```
