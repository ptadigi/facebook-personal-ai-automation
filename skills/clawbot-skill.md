# Facebook Personal Browser Post — Clawbot Skill Definition

```yaml
skill:
  name: facebook-personal-browser-post
  version: "2.0.0"
  description: >
    Post to a Facebook personal profile via Playwright browser automation.
    Supports feed posts (text/image/video), stories, and reels.
    Multi-account with proxy and fingerprint spoofing.
  author: yourname
  tags: [facebook, social, automation, playwright, multi-account]
  requires:
    python: ">=3.11"
    packages:
      - playwright>=1.40.0
      - pytz>=2024.1
    setup:
      - playwright install chromium
```

---

## Skill Actions

### `post` — Post to Facebook feed

**Trigger phrases:**
- "post on facebook", "đăng facebook", "post lên fb", "đăng bài fb"

**Command:**
```bash
python scripts/post.py \
  --account {account_id} \
  --text {text} \
  [--media {media_path}] \
  [--schedule {iso_datetime}] \
  --auto-approve
```

**Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `account_id` | string | yes | Account ID from `accounts.json` |
| `text` | string | no | Post text content |
| `media_path` | string/list | no | Path(s) to image or video files |
| `schedule` | datetime | no | ISO 8601 schedule time |
| `auto_approve` | bool | no | Auto-publish without confirmation |

**Expected output:**
```
OK: published | url: https://www.facebook.com/... | account: {id}
WAIT_APPROVAL
FAIL: {error_code} - {reason}
```

---

### `story` — Post a Facebook Story

**Trigger phrases:**
- "đăng story", "post story", "lên story"

**Command:**
```bash
python scripts/test_story.py \
  --cookie-file accounts/{account_id}/cookies.json \
  --media {media_path}
```

---

### `reel` — Post a Facebook Reel

**Trigger phrases:**
- "đăng reel", "post reel", "lên reel"

**Command:**
```bash
python scripts/test_reel.py \
  --cookie-file accounts/{account_id}/cookies.json \
  --media {video_path} \
  --caption {text}
```

---

### `account.list` — List all accounts

```bash
python scripts/account_manager.py list
```

### `account.init` — Initialize new account

```bash
python scripts/account_manager.py init --id {account_id} --cookies {cookies_path}
```

### `account.test` — Verify session

```bash
python scripts/account_manager.py test --id {account_id}
```

### `proxy.add` — Add proxy

```bash
python scripts/proxy_manager.py add \
  --host {host} --port {port} \
  --user {user} --pass {password} \
  --country {country_code}
```

### `proxy.health` — Check all proxies

```bash
python scripts/proxy_manager.py health
```

---

## Error Handling

Clawbot should handle these exit patterns:

```yaml
error_handlers:
  AUTH_REQUIRED:
    message: "Session expired. Re-export cookies and run account_manager.py init"
    action: notify_user

  DOM_CHANGED:
    message: "Facebook UI changed. Running dom_learner.py to re-learn selectors."
    action:
      run: python scripts/dom_learner.py --cookie-file accounts/{account_id}/cookies.json
      then: retry

  RATE_LIMIT:
    message: "Rate limited. Waiting 30 minutes before retry."
    action: wait_and_retry
    wait_minutes: 30

  PUBLISH_FAILED:
    message: "Publish failed after 3 retries. Check test screenshots."
    action: notify_user
```

---

## Example Conversations

**User:** "Đăng bài lên fb account pham_thanh với nội dung 'Hello world'"

**Clawbot:**
1. Verify account exists: `account_manager.py test --id pham_thanh`
2. Run: `post.py --account pham_thanh --text "Hello world" --auto-approve`
3. Report: "✅ Đã đăng thành công: https://facebook.com/..."

---

**User:** "Lên story với ảnh /path/to/photo.jpg"

**Clawbot:**
1. Run: `test_story.py --cookie-file accounts/pham_thanh/cookies.json --media /path/to/photo.jpg`
2. Report result from stdout

---

## Setup Guide for Clawbot Users

```bash
# 1. Clone and install
git clone <repo>
cd facebook-personal-browser-post
pip install -r requirements.txt
playwright install chromium

# 2. Export cookies from your browser (Cookie-Editor → JSON)

# 3. Initialize account
python scripts/account_manager.py init --id myaccount --cookies cookies.json

# 4. Test session
python scripts/account_manager.py test --id myaccount

# 5. Configure Clawbot skill path
# Add to your Clawbot config:
#   skill_path: /path/to/facebook-personal-browser-post
#   skill_definition: skills/clawbot-skill.md
```
