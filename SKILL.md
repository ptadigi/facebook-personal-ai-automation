---
name: facebook-personal-browser-post
version: "2.0.0"
description: >
  Post content to a Facebook personal profile via Playwright browser automation.
  Supports text, images, videos, stories, reels. Multi-account with proxy management,
  browser fingerprint spoofing, persistent browser profiles, and URL reporting.
  Auto-publish is OFF by default — requires explicit --auto-approve.

tags:
  - facebook
  - social-media
  - browser-automation
  - playwright
  - multi-account
  - proxy

requires:
  - python >= "3.11"
  - pip: ["playwright>=1.40.0", "pytz>=2024.1"]
  - system: ["playwright install chromium"]
---

# facebook-personal-browser-post

## Scope

> **Personal profile only.** This skill does NOT support Facebook Pages, Groups, or any
> API-based posting. All interactions go through a real browser session authenticated via
> session cookies. No credentials are ever sent to external services.

---

## Architecture

### Modules

| Module | File | Responsibility |
|---|---|---|
| **Main Poster** | `scripts/post.py` | Auth, compose, media, publish, URL extraction |
| **Account Manager** | `scripts/account_manager.py` | Add/list/test/remove accounts, import cookies |
| **Proxy Manager** | `scripts/proxy_manager.py` | Add/test/health-check/rotate proxies |
| **Fingerprint** | `scripts/fingerprint_gen.py` | Generate stable per-account browser fingerprints |
| **DOM Learner** | `scripts/dom_learner.py` | Re-discover selectors after FB UI updates |
| **Scheduler** | `scripts/scheduler.py` | Queue + time-based post execution |

### Multi-Account Data Flow

```
accounts.json
     │  (proxy_id, fingerprint_path, cookies_path, profile_dir)
     ▼
post.py --account <id>
     │
     ├── load_account_config()     → account dict
     ├── load_proxy_config()       → Playwright proxy= option
     ├── load_fingerprint()        → JS init script overrides
     │
     ├── launch_persistent_context()   ← if profile_dir exists (session saved)
     │   OR
     │   new_context() + inject_cookies()  ← first run
     │
     ▼
  Compose → Media Upload → Publish → extract_post_url()
     │
     ▼
  OK: published | url: https://... | account: <id>
     │
     ▼
  update_account_stats()  → accounts.json (daily_post_count, last_post, last_post_url)
```

---

## Usage

### Recommended: Account-based mode

```bash
# First-time setup
python scripts/account_manager.py init --id pham_thanh --cookies cookies.json
python scripts/account_manager.py test --id pham_thanh

# Post
python scripts/post.py --account pham_thanh --text "Hello!" --auto-approve
python scripts/post.py --account pham_thanh --text "Photo!" --media photo.jpg --auto-approve
python scripts/post.py --account pham_thanh --text "Video!" --media clip.mp4 --auto-approve

# Story
python scripts/test_story.py --cookie-file accounts/pham_thanh/cookies.json --media story.jpg

# Reel
python scripts/test_reel.py --cookie-file accounts/pham_thanh/cookies.json --media reel.mp4
```

### Legacy: Cookie-file mode

```bash
python scripts/post.py --cookie-file cookies.json --text "Hello!" --auto-approve
```

---

## Output Contract

Every run prints a **single final-status line** to stdout:

| Output | Meaning |
|---|---|
| `OK: published \| url: <url> \| account: <id>` | Post published successfully |
| `OK: scheduled <ISO8601-time>` | Post queued for scheduling |
| `WAIT_APPROVAL` | Dry-run or awaiting user approval |
| `FAIL: <error_code> - <reason>` | Failure with reason |

---

## Error Codes

| Code | Meaning | Fix |
|---|---|---|
| `AUTH_REQUIRED` | Session expired | Re-import cookies via `account_manager.py init` |
| `DOM_CHANGED` | All selectors failed | Run `dom_learner.py --cookie-file` |
| `RATE_LIMIT` | Facebook throttle | Wait and retry |
| `PUBLISH_FAILED` | Publish not confirmed after 3 retries | Check screenshots |

---

## Retry Policy

| Attempt | Wait Before |
|---|---|
| 1st | Immediate |
| 2nd | 2 seconds |
| 3rd | 5 seconds |

Maximum **3 attempts** per publish. `DOM_CHANGED` and `AUTH_REQUIRED` abort immediately — no retry.

---

## CLI Arguments — `post.py`

```
--account ID         Account ID from accounts.json [recommended]
--cookie-file PATH   Path to cookies.json [legacy]
--text TEXT          Post text
--media PATH         Media file (repeat for multiple files)
--link URL           Link preview URL
--schedule ISO8601   Schedule datetime
--dry-run            Preview only, never publishes
--auto-approve       Skip approval prompt, publish immediately
--headless           Headless browser (default: headed)
--timeout INT        Per-action timeout ms (default: 10000)
```

---

## Multi-Account Manager — `account_manager.py`

```
init   --id <id> --cookies <path>      # Copy cookies + generate fingerprint
add    --id <id> --name <name> [...]   # Register account
list                                   # Show all accounts + status
test   --id <id>                       # Verify session alive
assign --id <id> --proxy <proxy_id>   # Assign proxy
remove --id <id> [--delete-files]     # Remove account
```

---

## Proxy Manager — `proxy_manager.py`

```
add    --host <ip> --port <n> [--user <u> --pass <p> --country VN --type http]
list
test   --id <proxy_id>
health                                 # Check all proxies
rotate --account <id>                 # Auto-assign best proxy to account
remove --id <proxy_id>
```

**Rotation rules** (`references/rotation-rules.json`):
- Strategy: `sticky_per_account`
- Rotate on: 2 consecutive failures
- Blacklist after: 5 failures
- Cooldown: 30 minutes
- Prefer same country: yes

---

## Fingerprint Manager — `fingerprint_gen.py`

```
generate --account <id> [--random]    # Stable deterministic (default) or random
show     --account <id>               # Print fingerprint JSON
list                                  # List all accounts + fingerprint status
```

**Spoofed properties:** User-Agent, viewport, screen, locale, timezone, `navigator.platform`,
`navigator.webdriver`, WebGL vendor/renderer, Canvas pixel noise, AudioContext buffer noise.

---

## Safety Rules

1. `--auto-approve` is OFF by default — every run stops at `WAIT_APPROVAL` without it
2. `--dry-run` never publishes, even with `--auto-approve`
3. `DOM_CHANGED` immediately halts — no partial publish
4. All cookies stay local — never sent to external services
5. Personal profile only — no Pages, Groups, or API

---

## Logging

Every phase appends to `references/run-log.jsonl`:

```jsonc
{
  "timestamp": "2026-03-05T12:30:00+07:00",
  "phase": "publish",           // auth | compose | publish | schedule | error
  "status": "ok",               // ok | fail | retry | skipped
  "note": "Post published",
  "error_code": null            // or AUTH_REQUIRED | DOM_CHANGED | RATE_LIMIT | PUBLISH_FAILED
}
```

---

## File Structure

```
facebook-personal-browser-post/
├── README.md
├── SKILL.md                          ← Antigravity skill definition
├── skills/
│   ├── claude-skill.md               ← Claude MCP tool definition
│   ├── clawbot-skill.md              ← Clawbot skill definition
│   └── openai-function.json          ← OpenAI function calling spec
├── requirements.txt
├── config.example.json
├── accounts/
│   ├── accounts.json                 ← Account registry
│   └── <account_id>/
│       ├── cookies.json              ← Session cookies (gitignored)
│       ├── fingerprint.json          ← Browser fingerprint
│       └── profile/                  ← Persistent browser profile (gitignored)
├── proxies/
│   ├── proxy-list.json               ← Proxy registry
│   └── proxy-usage.jsonl             ← Proxy event log (gitignored)
└── references/
    ├── rotation-rules.json           ← Proxy rotation policy
    ├── selector-map.json             ← Facebook DOM selectors
    └── run-log.jsonl                 ← Run history (gitignored)
└── scripts/
    ├── post.py                       ← Main posting script
    ├── account_manager.py            ← Account management
    ├── proxy_manager.py              ← Proxy management
    ├── fingerprint_gen.py            ← Fingerprint generation
    ├── dom_learner.py                ← Selector re-discovery
    ├── scheduler.py                  ← Schedule daemon
    ├── test_all_formats.py           ← Regression tests (all feeds)
    ├── test_story.py                 ← Story test
    └── test_reel.py                  ← Reel test
```
