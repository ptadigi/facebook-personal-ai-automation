# Claude Code Integration Guide
**Skill:** `facebook-personal-ai-automation` · **Version:** 2.1.0

---

## Quickstart (copy-paste)

```bash
# 1. Clone & install
git clone https://github.com/ptadigi/facebook-personal-ai-automation
cd facebook-personal-ai-automation
pip install -r requirements.txt && playwright install chromium

# 2. Init account
python scripts/account_manager.py init --id pham_thanh --cookies /path/to/cookies.json
python scripts/account_manager.py test --id pham_thanh
```

Claude Code sử dụng `bash_tool` để gọi scripts trực tiếp. Không cần MCP server riêng — Claude đọc `skills/claude-skill.md` để biết tool schema.

Load context cho Claude:
```
Read the file skills/claude-skill.md and use it as your tool contract for all Facebook posting operations.
```

---

## Tool Schema (Claude MCP format)

```json
{
  "name": "facebook_post",
  "description": "Post content to a Facebook personal profile via browser automation.",
  "input_schema": {
    "type": "object",
    "properties": {
      "account":      { "type": "string",  "description": "Account ID from accounts.json" },
      "text":         { "type": "string",  "description": "Post text content" },
      "media":        { "type": "array",   "items": {"type": "string"}, "description": "Media file paths" },
      "link":         { "type": "string",  "description": "URL to attach as link preview" },
      "schedule":     { "type": "string",  "description": "ISO 8601 datetime with timezone" },
      "auto_approve": { "type": "boolean", "default": false },
      "dry_run":      { "type": "boolean", "default": false }
    },
    "required": ["account"]
  }
}
```

---

## Intent → Command Mapping

| Intent | Claude command |
|---|---|
| Text post | `python scripts/post.py --account {id} --text "{text}" --auto-approve` |
| Image post | `python scripts/post.py --account {id} --text "{text}" --media "{path}" --auto-approve` |
| Multi-image | `... --media img1.jpg --media img2.jpg --media img3.jpg ...` |
| Video post | `python scripts/post.py --account {id} --media "{video.mp4}" --auto-approve` |
| Story | `python scripts/test_story.py --cookie-file accounts/{id}/cookies.json --media "{path}"` |
| Reel | `python scripts/test_reel.py --cookie-file accounts/{id}/cookies.json --media "{path}"` |
| Schedule | `... --schedule "2026-03-06T10:00:00+07:00" --auto-approve` |
| Dry run | `... --dry-run` (returns WAIT_APPROVAL — never publishes) |
| List accounts | `python scripts/account_manager.py list` |
| Test session | `python scripts/account_manager.py test --id {id}` |
| Add proxy | `python scripts/proxy_manager.py add --host {h} --port {p} --country {c}` |
| Proxy health | `python scripts/proxy_manager.py health` |
| Re-learn DOM | `python scripts/dom_learner.py --cookie-file accounts/{id}/cookies.json --account {id}` |

---

## Input Validation (Claude MUST check before calling bash)

```python
# Claude sends this to bash_tool before the actual post command:

import json, os
from pathlib import Path
from datetime import datetime, timezone

def validate_post_inputs(account, text=None, media=None, schedule=None):
    # 1. Account
    data = json.loads(Path("accounts/accounts.json").read_text())
    ids = [a["id"] for a in data["accounts"]]
    assert account in ids, f"Account '{account}' not found. Available: {ids}"

    # 2. Media
    for m in (media or []):
        assert Path(m).exists(), f"Media file not found: {m}"
        ext = Path(m).suffix.lower()
        assert ext in {'.jpg','.jpeg','.png','.gif','.mp4','.mov','.webm'}, \
            f"Unsupported format: {ext}"

    # 3. Schedule
    if schedule:
        dt = datetime.fromisoformat(schedule)
        assert dt.tzinfo is not None, "Schedule needs timezone. Example: +07:00"
        assert dt > datetime.now(tz=timezone.utc), "Schedule must be in the future"

    # 4. Content
    assert text or media, "Need at least text or media"
    print("✅ Validation passed")
```

---

## Output Contract

Claude MUST parse the last non-empty stdout line:

```python
lines = [l.strip() for l in stdout.splitlines() if l.strip()]
status_line = lines[-1] if lines else ""

if status_line.startswith("OK: published"):
    url = status_line.split("url: ")[-1].split(" | ")[0]
    return {"status": "success", "url": url}
elif status_line.startswith("OK: scheduled"):
    dt = status_line.replace("OK: scheduled ", "")
    return {"status": "scheduled", "scheduled_at": dt}
elif status_line == "WAIT_APPROVAL":
    return {"status": "pending_approval"}
elif status_line.startswith("FAIL:"):
    error_code = status_line.split(":")[1].strip().split(" - ")[0]
    reason = status_line.split(" - ", 1)[-1]
    return {"status": "failed", "error_code": error_code, "reason": reason}
```

---

## Error Handling Runbook

### AUTH_REQUIRED
```
Trigger: status_line contains "FAIL: AUTH_REQUIRED"

Claude action:
  1. Tell user: "Session expired for account '{id}'. Need new cookies."
  2. Provide step-by-step:
     a. Open Chrome, login to Facebook
     b. Cookie-Editor → Export → JSON → save as new_cookies.json
     c. python scripts/account_manager.py init --id {id} --cookies new_cookies.json
     d. python scripts/account_manager.py test --id {id}
  3. Do NOT retry with same cookies.
```

### DOM_CHANGED
```
Trigger: status_line contains "FAIL: DOM_CHANGED"

Claude action:
  1. Run dom_learner:
     python scripts/dom_learner.py \
       --cookie-file accounts/{id}/cookies.json \
       --account {id}
  2. If exit code 0 → retry original post
  3. If exit code != 0 → tell user to run dom_learner manually
```

### RATE_LIMIT
```
Trigger: status_line contains "FAIL: RATE_LIMIT"

Claude action:
  1. Calculate retry_time = now + 45 minutes
  2. python scripts/scheduler.py --add --account {id} \
       --text "{original_text}" --schedule "{retry_time}"
  3. Tell user: "Queued retry at {retry_time}"
```

### PUBLISH_FAILED
```
Trigger: status_line contains "FAIL: PUBLISH_FAILED"

Claude action:
  1. Wait 10 seconds
  2. Retry once
  3. If still fails:
     - Tell user to check screenshot: ls *.png
     - Suggest: python scripts/account_manager.py test --id {id}
```

---

## Example Claude Sessions

### EN — Simple text post
```
User:    Post "Morning routine ☀️" to my Facebook, use account pham_thanh
Claude:  Running validation...
         ✅ Account pham_thanh is registered
         ✅ No media validation needed

         Executing post...
         $ python scripts/post.py --account pham_thanh \
             --text "Morning routine ☀️" --auto-approve

         Result: OK: published | url: https://facebook.com/.../posts/123 | account: pham_thanh
         ✅ Posted successfully: https://facebook.com/.../posts/123
```

### VN — Đặt lịch với media
```
User:    Lên lịch đăng ảnh sunset.jpg lúc 6 giờ tối mai, dùng account pham_thanh
Claude:  [Tính datetime: 2026-03-06T18:00:00+07:00]
         Kiểm tra đầu vào...
         ✅ File sunset.jpg tồn tại
         ✅ Account pham_thanh đăng ký rồi
         ✅ Thời gian 18:00 ngày mai là tương lai

         $ python scripts/post.py --account pham_thanh \
             --media sunset.jpg \
             --schedule "2026-03-06T18:00:00+07:00" --auto-approve
         
         → OK: scheduled 2026-03-06T18:00:00+07:00
         ✅ Đã đặt lịch lúc 18:00 ngày 06/03/2026
```

---

## Operator Checklist

```
[ ] Python 3.11+ installed
[ ] playwright install chromium ran successfully
[ ] accounts/accounts.json populated
[ ] account_manager.py test --id <id> → ACTIVE
[ ] references/selector-map.json present
[ ] Claude has read skills/claude-skill.md for tool schema
[ ] Working directory is repo root when running commands
[ ] For videos: POST_TIMEOUT_SECONDS=300 env var set
```

---

## Escalation Rules

| Error | Claude action | Escalate to user? |
|---|---|---|
| AUTH_REQUIRED | Show cookie refresh steps | ✅ Always |
| DOM_CHANGED, dom_learner OK | Auto-retry | ❌ Silent fix |
| DOM_CHANGED, dom_learner fails | Ask user for manual fix | ✅ |
| RATE_LIMIT | Auto-schedule retry +45min | ❌ Notify only |
| PUBLISH_FAILED (all retries) | Show troubleshoot checklist | ✅ |
| Input invalid | Reject before running command | ✅ Explain error |
| Missing `datr` cookie warning | Log warning, continue | ❌ |
