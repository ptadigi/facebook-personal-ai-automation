# Clawbot Integration Guide
**Skill:** `facebook-personal-ai-automation` · **Version:** 2.1.0

---

## Quickstart (copy-paste)

```bash
# 1. Clone & install
git clone https://github.com/ptadigi/facebook-personal-ai-automation
cd facebook-personal-ai-automation
pip install -r requirements.txt && playwright install chromium

# 2. Import cookies & init account
python scripts/account_manager.py init --id pham_thanh --cookies /path/to/cookies.json

# 3. Verify session
python scripts/account_manager.py test --id pham_thanh
```

Load skill file vào Clawbot:
```
/skill load facebook-personal-ai-automation
```

---

## Intent → Action Mapping

| User says (VN) | User says (EN) | Clawbot action | Command |
|---|---|---|---|
| đăng bài, lên fb, post facebook | post to facebook, share on fb | `post` | `post.py --account X --text "..." --auto-approve` |
| đăng ảnh, gửi ảnh lên fb | post image, share photo | `post` + `--media` | `post.py --account X --media img.jpg` |
| đăng video, up clip lên fb | post video, upload clip | `post` + `--media video.mp4` | same |
| lên story, đăng story | post story, add to story | `story` | `test_story.py --cookie-file ... --media` |
| đăng reel, tạo reel | post reel, create reel | `reel` | `test_reel.py --cookie-file ... --media` |
| lên lịch đăng, hẹn giờ | schedule post, post later | `post` + `--schedule` | `post.py ... --schedule "ISO8601"` |
| xem tài khoản, list account | list accounts, which accounts | `account.list` | `account_manager.py list` |
| kiểm tra session, test account | test account, check session | `account.test` | `account_manager.py test --id X` |
| thêm proxy, add proxy | add proxy, configure proxy | `proxy.add` | `proxy_manager.py add --host ...` |
| kiểm tra proxy | check proxy health | `proxy.health` | `proxy_manager.py health` |

---

## Input Validation Rules

Run these checks **before** executing any command:

```python
# 1. Account must exist
with open("accounts/accounts.json") as f:
    accounts = json.load(f)["accounts"]
if not any(a["id"] == account_id for a in accounts):
    raise InputError(f"Account '{account_id}' not found. Run account.list.")

# 2. Media file must exist and be supported format
ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm', '.avi'}
for path in media_paths:
    if not Path(path).exists():
        raise InputError(f"File not found: {path}")
    if Path(path).suffix.lower() not in ALLOWED_EXTS:
        raise InputError(f"Unsupported format: {path}")

# 3. Schedule must be future + have timezone
if schedule:
    dt = datetime.fromisoformat(schedule)
    if dt.tzinfo is None:
        raise InputError("Schedule must include timezone. Example: 2026-03-06T10:00:00+07:00")
    if dt <= datetime.now(tz=timezone.utc):
        raise InputError("Schedule must be a future time.")

# 4. Content required
if not text and not media_paths:
    raise InputError("Need at least text or media.")
```

---

## Error Handling Runbook

### AUTH_REQUIRED
```
Detected:   stdout contains "FAIL: AUTH_REQUIRED"
Auto-action: Mark account as expired in local state
             Display fix instructions to user
Escalate:   Always — needs new cookies from user

User message:
  ❌ Phiên đăng nhập hết hạn cho account '{id}'.
  Fix:
    1. Đăng nhập Facebook trên Chrome
    2. Export cookies (Cookie-Editor → JSON)
    3. python scripts/account_manager.py init --id {id} --cookies /path/new.json
    4. python scripts/account_manager.py test --id {id}
```

### DOM_CHANGED
```
Detected:   stdout contains "FAIL: DOM_CHANGED"
Auto-action:
  1. Run dom_learner.py:
     python scripts/dom_learner.py --cookie-file accounts/{id}/cookies.json --account {id}
  2. If exit 0 → retry original post once
  3. If retry fails → escalate

Escalate when: dom_learner itself fails OR second DOM_CHANGED in a row

User message (if escalate):
  ⚠️ Facebook đổi giao diện, cần fix thủ công:
  python scripts/dom_learner.py --account {id} --cookie-file accounts/{id}/cookies.json
```

### RATE_LIMIT
```
Detected:   stdout contains "FAIL: RATE_LIMIT"
Auto-action:
  1. Queue post for retry in 45 minutes:
     python scripts/scheduler.py --add --account {id} --text "..." \
       --schedule "{now + 45min in ISO8601}"
  2. Notify user: "Queued retry at {time}"

Escalate when: 3 consecutive RATE_LIMIT on same account in one day

User message:
  ⏳ Facebook đang giới hạn tốc độ. Đã đặt lịch đăng lại sau 45 phút: {time}
```

### PUBLISH_FAILED
```
Detected:   stdout contains "FAIL: PUBLISH_FAILED"
Auto-action:
  1. Wait 10 seconds
  2. Retry once (post.py already did 3 internal retries)
  3. If still fails → escalate

Escalate when: all retries exhausted

User message:
  ❌ Không thể đăng bài sau nhiều lần thử.
  Kiểm tra:
  - Screenshot: test_result_*_after_publish.png
  - Facebook có bảo trì không?
  - Chạy account.test để kiểm tra session
```

---

## Example Conversations

### VN — Đăng ảnh
```
User:    đăng ảnh /home/me/photo.jpg lên fb bằng account pham_thanh
Clawbot: [Validate: file exists ✅, account exists ✅]
         "Đăng ảnh photo.jpg bằng pham_thanh?"
User:    ok
Clawbot: [Execute]
         python scripts/post.py --account pham_thanh --media /home/me/photo.jpg --auto-approve
         → OK: published | url: https://facebook.com/pham.thanh/posts/... | account: pham_thanh
         ✅ Đã đăng: https://facebook.com/pham.thanh/posts/...
```

### EN — Schedule post
```
User:    schedule a post "Good morning!" for tomorrow 9am
Clawbot: [Resolve datetime: 2026-03-06T09:00:00+07:00]
         "Schedule 'Good morning!' at 09:00 2026-03-06?"
User:    yes
Clawbot: python scripts/post.py --account pham_thanh --text "Good morning!" \
           --schedule "2026-03-06T09:00:00+07:00" --auto-approve
         → OK: scheduled 2026-03-06T09:00:00+07:00
         ✅ Scheduled for 09:00 tomorrow.
```

### VN — Lỗi AUTH_REQUIRED
```
User:    đăng bài "Hello"
Clawbot: [Execute...]
         → FAIL: AUTH_REQUIRED - Session expired
Clawbot: ❌ Phiên đăng nhập hết hạn.
         [Hiển thị hướng dẫn refresh cookies]
```

---

## Operator Checklist

Trước khi deploy skill vào production:

```
[ ] accounts/accounts.json có ít nhất 1 account active
[ ] Mỗi account có cookies.json + fingerprint.json trong accounts/<id>/
[ ] account_manager.py test --id <id> → ✅ ACTIVE
[ ] references/selector-map.json tồn tại và có key "open_composer"
[ ] (Optional) proxies/proxy-list.json có proxies nếu dùng proxy
[ ] POST_TIMEOUT_SECONDS=300 nếu dùng video lớn
[ ] MIN_POST_GAP_MINUTES=15 (default) để tránh rate limit
```

---

## Escalation Rules

| Tình huống | Hành động Clawbot | Escalate? |
|---|---|---|
| AUTH_REQUIRED lần đầu | Hiển thị hướng dẫn | ✅ Luôn |
| DOM_CHANGED — dom_learner fix được | Retry tự động | ❌ |
| DOM_CHANGED — dom_learner thất bại | Hướng dẫn sửa tay | ✅ |
| RATE_LIMIT (< 3 lần/ngày) | Auto-queue retry 45min | ❌ |
| RATE_LIMIT (≥ 3 lần/ngày) | Cảnh báo account bị flag | ✅ |
| PUBLISH_FAILED sau retry | Screenshot + hướng dẫn | ✅ |
| Input validation fail | Thông báo lỗi input | ❌ (không run command) |
