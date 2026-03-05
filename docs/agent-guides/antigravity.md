---
last_updated: 2026-03-05
compatible_scripts: v2.1.x
skill: facebook-personal-ai-automation
---

# Antigravity Integration Guide
**Version:** 2.1.0 · **Compatible scripts:** v2.1.x · **Last updated:** 2026-03-05

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

Antigravity loads the skill via `SKILL.md` in the repo root. The file contains full capability description, CLI reference, and output contract — read it before calling any command.

---

## Skill Loading

```
Read SKILL.md in the current directory.
Use the CLI contract defined there for all Facebook posting operations.
Working directory for all commands is the repo root.
```

Antigravity uses `run_command` tool to execute scripts:

```python
# Pattern for all commands
result = run_command(
    command=["python", "scripts/post.py", "--account", account_id, ...],
    cwd=str(SKILL_ROOT),
    capture_output=True,
    text=True
)
status_line = [l for l in result.stdout.splitlines() if l.strip()][-1]
```

---

## Intent → Workflow

### Feed post
```python
# Step 1: Validate inputs
validate_account(account_id)
validate_media(media_paths)
validate_schedule(schedule)

# Step 2: Build command
cmd = ["python", "scripts/post.py", "--account", account_id]
if text:     cmd += ["--text", text]
for m in media: cmd += ["--media", m]
if link:     cmd += ["--link", link]
if schedule: cmd += ["--schedule", schedule]
if auto_approve: cmd.append("--auto-approve")

# Step 3: Run
result = run_command(cmd, cwd=SKILL_ROOT)

# Step 4: Parse output contract
parse_output(result.stdout)
```

### Story
```python
cookie_file = f"accounts/{account_id}/cookies.json"
cmd = ["python", "scripts/test_story.py",
       "--cookie-file", cookie_file, "--media", media_path]
result = run_command(cmd, cwd=SKILL_ROOT)
```

### Reel
```python
cookie_file = f"accounts/{account_id}/cookies.json"
cmd = ["python", "scripts/test_reel.py",
       "--cookie-file", cookie_file, "--media", video_path]
if caption: cmd += ["--caption", caption]
result = run_command(cmd, cwd=SKILL_ROOT)
```

### DOM self-heal
```python
cmd = ["python", "scripts/dom_learner.py",
       "--cookie-file", f"accounts/{account_id}/cookies.json",
       "--account", account_id]
result = run_command(cmd, cwd=SKILL_ROOT)
```

---

## Input Validation Rules

```python
import json
from pathlib import Path
from datetime import datetime, timezone

SKILL_ROOT = Path(".")  # adjust if needed
ALLOWED_MEDIA = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".webm", ".avi"}

def validate_account(account_id: str):
    accounts_file = SKILL_ROOT / "accounts" / "accounts.json"
    if not accounts_file.exists():
        raise ValueError("accounts.json not found. Run account_manager.py init first.")
    data = json.loads(accounts_file.read_text())
    ids = [a["id"] for a in data.get("accounts", [])]
    if account_id not in ids:
        raise ValueError(f"Account '{account_id}' not registered. Available: {ids}")
    account = next(a for a in data["accounts"] if a["id"] == account_id)
    if not account.get("active", True):
        raise ValueError(f"Account '{account_id}' is marked inactive.")

def validate_media(paths: list[str]):
    for p in paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {p}")
        if path.suffix.lower() not in ALLOWED_MEDIA:
            raise ValueError(f"Unsupported format '{path.suffix}'. Allowed: {ALLOWED_MEDIA}")

def validate_schedule(schedule: str | None):
    if not schedule:
        return
    dt = datetime.fromisoformat(schedule)
    if dt.tzinfo is None:
        raise ValueError("Schedule must include timezone offset. Example: 2026-03-06T10:00:00+07:00")
    if dt <= datetime.now(tz=timezone.utc):
        raise ValueError(f"Schedule {schedule!r} is in the past.")
```

---

## Confirmation Policy (No Surprise Publish)

- **Không bao giờ publish tự động** khi không có approval flag rõ ràng từ user hoặc workflow.
- Khi trạng thái approval không rõ → dùng `--dry-run` (trả về `WAIT_APPROVAL`, không publish).
- Khi phát hiện rủi ro compliance hoặc policy → escalate ngay lên operator, không tự quyết.

```python
def decide_approve(user_intent: str, workflow_flags: dict) -> bool:
    """Return True only if explicitly approved."""
    explicit_approve = workflow_flags.get("auto_approve", False)
    user_said_yes = any(w in user_intent.lower() for w in ["approve", "đăng ngay", "ok publish"])
    return explicit_approve or user_said_yes
    # Default: False → use dry-run
```

---

## Output Contract Parser

```python
def parse_output(stdout: str) -> dict:
    """Parse the output contract from post.py / story / reel stdout."""
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]
    if not lines:
        return {"status": "unknown", "raw": stdout}
    last = lines[-1]

    if last.startswith("OK: published"):
        parts = dict(p.split(": ", 1) for p in last.split(" | ") if ": " in p)
        return {"status": "published", "url": parts.get("url"), "account": parts.get("account")}

    if last.startswith("OK: scheduled"):
        return {"status": "scheduled", "scheduled_at": last.replace("OK: scheduled ", "")}

    if last == "WAIT_APPROVAL":
        return {"status": "wait_approval"}

    if last.startswith("FAIL:"):
        body = last[len("FAIL: "):]
        code, _, reason = body.partition(" - ")
        return {"status": "failed", "error_code": code.strip(), "reason": reason.strip()}

    return {"status": "unknown", "raw": last}
```

---

## Error Handling Runbook

### AUTH_REQUIRED
```
parse_output → error_code == "AUTH_REQUIRED"

Antigravity response:
  1. Log: f"[fb-autoposter] AUTH_REQUIRED for account {account_id}"
  2. Đánh dấu account status = "expired" trong working memory
  3. Trả về user:
     "Session expired for '{account_id}'. Please:
      1. Re-login to Facebook in Chrome
      2. Export cookies (Cookie-Editor → JSON)
      3. Run: python scripts/account_manager.py init --id {account_id} --cookies new.json"
  4. Do NOT retry.
```

### DOM_CHANGED
```
parse_output → error_code == "DOM_CHANGED"

Antigravity response:
  1. Attempt auto-heal:
     result = run_command(["python", "scripts/dom_learner.py",
                           "--cookie-file", f"accounts/{account_id}/cookies.json",
                           "--account", account_id])
  2. If returncode == 0:
     → Retry original post once
     → If retry OK: report success + note "selectors auto-updated"
     → If retry fails: escalate
  3. If returncode != 0:
     → Escalate: "dom_learner failed. Manual fix required."
```

### RATE_LIMIT
```
parse_output → error_code == "RATE_LIMIT"

Antigravity response:
  1. Compute retry_at = now + 45 minutes (ISO 8601 với +07:00)
  2. Chạy scheduler --add để queue retry
  3. Notify: "Rate limited. Retry queued at {retry_at}"
  4. Nếu cùng account RATE_LIMIT 3+ lần trong ngày → escalate
```

### PUBLISH_FAILED
```
parse_output → error_code == "PUBLISH_FAILED"

Antigravity response:
  1. Chờ 10 giây
  2. Retry một lần
  3. Nếu thành công → báo kết quả
  4. Nếu vẫn thất bại:
     → Liệt kê screenshot: run_command(["dir", "*.png"])
     → Gợi ý: test session, kiểm tra trạng thái FB
     → Escalate to user
```

---

## Example Antigravity Sessions

### VN — Đăng text
```
User:    đăng "Chào buổi sáng!" lên Facebook dùng account pham_thanh
Agent:   validate_account("pham_thanh") → ✅
         cmd = ["python", "scripts/post.py", "--account", "pham_thanh",
                "--text", "Chào buổi sáng!", "--auto-approve"]
         run_command(cmd) → OK: published | url: https://... | account: pham_thanh
         Response: ✅ Đã đăng: https://facebook.com/pham.thanh/posts/...
```

### EN — Multi-image post
```
User:    Post 3 photos to Facebook: pic1.jpg pic2.jpg pic3.jpg (account pham_thanh)
Agent:   validate_media(["pic1.jpg", "pic2.jpg", "pic3.jpg"]) → ✅ all exist
         cmd = ["python", "scripts/post.py", "--account", "pham_thanh",
                "--media", "pic1.jpg", "--media", "pic2.jpg", "--media", "pic3.jpg",
                "--auto-approve"]
         → OK: published | url: https://...
         Response: ✅ Posted 3 photos: https://...
```

### VN — DOM_CHANGED auto-heal
```
Agent:   [run post] → FAIL: DOM_CHANGED - All selectors failed for open_composer
         [auto-heal] run dom_learner.py → exit 0, selector-map.json updated
         [retry post] → OK: published | url: https://...
         Response: ✅ Đã đăng (tự động cập nhật selectors do FB đổi giao diện)
```

---

## Operator Checklist

```
[ ] SKILL.md in repo root đã được load vào Antigravity context
[ ] Working directory là repo root trước tất cả run_command calls
[ ] accounts/accounts.json có ít nhất 1 active account
[ ] accounts/<id>/cookies.json và accounts/<id>/fingerprint.json tồn tại
[ ] account_manager.py test --id <id> → ACTIVE
[ ] references/selector-map.json tồn tại với key "open_composer"
[ ] POST_TIMEOUT_SECONDS=300 nếu post video > 50MB
[ ] validate_account() được gọi trước mọi post command
[ ] parse_output() được dùng để interpret tất cả stdout results
```

---

## Log Schema

All runs append to `references/run-log.jsonl`:

```json
{
  "timestamp": "2026-03-05T18:30:00+07:00",
  "version": "2.1.0",
  "run_id": "a1b2c3d4",
  "account_id": "pham_thanh",
  "phase": "publish",
  "status": "ok",
  "note": "Post published",
  "error_code": null,
  "url": "https://facebook.com/pham.thanh/posts/123"
}
```

Antigravity có thể đọc file này để cung cấp operation history cho user.
