---
name: facebook-personal-browser-post
version: "2.0.0"
description: >
  Post to a Facebook personal profile via Playwright browser automation.
  Supports text, images, videos, stories, and reels. Multi-account with
  proxy management, browser fingerprint spoofing, and persistent sessions.
  Returns post URL on success.
triggers:
  - "post on facebook"
  - "đăng facebook"
  - "đăng bài fb"
  - "post story fb"
  - "đăng reel"
  - "lên story"
  - "quản lý tài khoản facebook"
  - "thêm proxy"
working_directory: "<skill_root>"
---

# facebook-personal-browser-post — Antigravity Skill

## When to Use This Skill

Use this skill when the user wants to:
- Post text, images, or videos to their Facebook personal profile
- Upload a Facebook Story (image/video, 24h)
- Upload a Facebook Reel (short video)
- Manage multiple Facebook accounts
- Add/test/rotate proxies for accounts
- Check if an account session is still active

---

## Workflow

### 1. Feed Post (text / image / video)

```bash
# Check session first
python scripts/account_manager.py test --id {account_id}

# Post
python scripts/post.py \
  --account {account_id} \
  --text "{post_text}" \
  [--media "{media_path}"] \
  --auto-approve
```

**Parse output:**
- `OK: published | url: ...` → success, report URL to user
- `FAIL: AUTH_REQUIRED` → session expired, guide user to re-import cookies
- `FAIL: DOM_CHANGED` → run dom_learner.py

### 2. Story Post

```bash
python scripts/test_story.py \
  --cookie-file accounts/{account_id}/cookies.json \
  --media "{image_or_video_path}"
```

### 3. Reel Post

```bash
python scripts/test_reel.py \
  --cookie-file accounts/{account_id}/cookies.json \
  --media "{video_path}" \
  [--caption "{caption_text}"]
```

---

## Account Management

```bash
# List all accounts (check health)
python scripts/account_manager.py list

# Initialize new account (first time)
python scripts/account_manager.py init --id {id} --cookies {cookies_path}

# Test session
python scripts/account_manager.py test --id {id}

# Assign proxy
python scripts/account_manager.py assign --id {id} --proxy {proxy_id}
```

---

## Proxy Management

```bash
# Add proxy
python scripts/proxy_manager.py add \
  --host {host} --port {port} \
  --user {user} --pass {password} \
  --country {country_code}

# Check all proxies
python scripts/proxy_manager.py health

# Rotate proxy for an account
python scripts/proxy_manager.py rotate --account {account_id}
```

---

## Fingerprint Management

```bash
# Generate/regenerate fingerprint for account
python scripts/fingerprint_gen.py generate --account {account_id}

# Show current fingerprint
python scripts/fingerprint_gen.py show --account {account_id}
```

---

## Re-learn Facebook DOM Selectors

Run this after Facebook updates its UI (when DOM_CHANGED errors appear):

```bash
python scripts/dom_learner.py --cookie-file accounts/{account_id}/cookies.json
```

---

## Output Contract

```
OK: published | url: https://www.facebook.com/<user>/posts/<id> | account: <id>
OK: scheduled 2026-03-06T10:00:00+07:00
WAIT_APPROVAL
FAIL: AUTH_REQUIRED - Session expired
FAIL: DOM_CHANGED - All selectors failed
FAIL: RATE_LIMIT - Facebook rate limit
FAIL: PUBLISH_FAILED - Retry exhausted
```

---

## Error Handling Guide

| Error | Antigravity should do |
|---|---|
| `AUTH_REQUIRED` | Tell user to re-export cookies, run `account_manager.py init` |
| `DOM_CHANGED` | Auto-run `dom_learner.py` then retry |
| `RATE_LIMIT` | Wait 30 min, then retry |
| `PUBLISH_FAILED` | Show screenshot, ask user to check profile |

---

## Quick Setup for New Users

```bash
# 1. Install
pip install playwright pytz && playwright install chromium

# 2. Export cookies from browser (Cookie-Editor extension)

# 3. Init account
python scripts/account_manager.py init --id myaccount --cookies cookies.json

# 4. Test
python scripts/account_manager.py test --id myaccount

# 5. Post!
python scripts/post.py --account myaccount --text "Hello!" --auto-approve
```

---

## Config Files

| File | Purpose |
|---|---|
| `accounts/accounts.json` | Account registry |
| `proxies/proxy-list.json` | Proxy registry |
| `references/rotation-rules.json` | Proxy rotation policy |
| `references/selector-map.json` | Facebook DOM selectors |
| `references/run-log.jsonl` | Run history log |
