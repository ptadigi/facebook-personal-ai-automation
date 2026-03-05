# Facebook Personal AI Automation — Clawbot Skill (v2.1)

```yaml
skill:
  name: facebook-personal-ai-automation
  version: "2.1.0"
  description: >
    Post to Facebook personal profile via Playwright browser automation.
    Supports feed posts (text/image/video), stories, reels.
    Multi-account with proxy and browser fingerprint spoofing.
    Deterministic output contract: OK/WAIT_APPROVAL/FAIL for all actions.
  author: ptadigi
  tags: [facebook, social, automation, playwright, multi-account, proxy]
  requires:
    python: ">=3.11"
    packages:
      - playwright>=1.42.0
      - pytz>=2024.1
    setup:
      - playwright install chromium
  working_directory: "<skill_root>"
  output_contract:
    success: "^OK: (published|scheduled)"
    wait: "^WAIT_APPROVAL$"
    failure: "^FAIL: (AUTH_REQUIRED|DOM_CHANGED|RATE_LIMIT|PUBLISH_FAILED) - .+"
```

---

## Section 1 — Action Catalog

### Action: `post`

Post text, image(s), or video to Facebook feed.

**Trigger phrases (Vietnamese + English):**
```
Vietnamese: đăng bài, đăng facebook, đăng lên fb, post facebook, viết bài, 
            đăng ảnh, đăng video, đăng nội dung, chia sẻ bài viết, lên bài
English:    post to facebook, share on facebook, create facebook post, 
            post image, post video, facebook post, publish to fb
```

**Parameters:**

| Param | Type | Required | Default | Validation |
|---|---|---|---|---|
| `account` | string | ✅ | — | Must exist in `accounts.json`. Run `account.list` to verify. |
| `text` | string | ⚠️ (or media) | — | Max 63,206 chars. Warn if contains spam patterns. |
| `media` | list[path] | ⚠️ (or text) | `[]` | Each path must exist. Accept: jpg/png/gif/mp4/mov. Max 4 images or 1 video. |
| `link` | string | ❌ | — | Must start with `http://` or `https://`. |
| `schedule` | ISO8601 | ❌ | — | Must be future datetime with timezone. Format: `2026-03-06T10:00:00+07:00` |
| `auto_approve` | bool | ❌ | `false` | Set `true` to publish without confirmation. |
| `dry_run` | bool | ❌ | `false` | Preview only. Returns `WAIT_APPROVAL`. |

**Command template:**
```bash
python scripts/post.py \
  --account "{account}" \
  [--text "{text}"] \
  [--media "{media[0]}" [--media "{media[1]}"]] \
  [--link "{link}"] \
  [--schedule "{schedule}"] \
  [--auto-approve] \
  [--dry-run]
```

**Input validation (run before command):**
```python
# Validate account exists
if account not in accounts_json["accounts"]:
    raise ClawbotInputError("Account '{account}' not found. Use account.list to see available accounts.")

# Validate media paths
for path in media:
    if not os.path.exists(path):
        raise ClawbotInputError(f"Media file not found: {path}")
    if not path.lower().endswith(('.jpg','.jpeg','.png','.gif','.mp4','.mov','.webm')):
        raise ClawbotInputError(f"Unsupported media format: {path}")

# Validate schedule
if schedule:
    try:
        dt = datetime.fromisoformat(schedule)
        if dt.tzinfo is None:
            raise ClawbotInputError("schedule must include timezone, e.g. 2026-03-06T10:00:00+07:00")
        if dt <= datetime.now(tz=timezone.utc):
            raise ClawbotInputError("schedule must be a future datetime")
    except ValueError:
        raise ClawbotInputError("Invalid schedule format. Use ISO 8601: 2026-03-06T10:00:00+07:00")

# Validate content
if not text and not media:
    raise ClawbotInputError("At least one of 'text' or 'media' is required")
```

---

### Action: `story`

Post an image or video as a Facebook Story (24h).

**Trigger phrases:**
```
Vietnamese: đăng story, lên story, post story, thêm story, đăng vào story, 
            story facebook, ảnh story, video story, lên ảnh story
English:    post story, facebook story, add to story, share story, create story
```

**Parameters:**

| Param | Type | Required | Default | Validation |
|---|---|---|---|---|
| `account` | string | ✅ | — | Must exist in `accounts.json` |
| `media` | string (path) | ✅ | — | File must exist. Accept: jpg/png/mp4/mov |

**Command template:**
```bash
python scripts/test_story.py \
  --cookie-file "accounts/{account}/cookies.json" \
  --media "{media}"
```

---

### Action: `reel`

Upload and publish a Facebook Reel (short video).

**Trigger phrases:**
```
Vietnamese: đăng reel, lên reel, post reel, tạo reel, đăng video ngắn,
            reel facebook, thước phim, tạo thước phim, video reel
English:    post reel, facebook reel, create reel, upload reel, share reel
```

**Parameters:**

| Param | Type | Required | Default | Validation |
|---|---|---|---|---|
| `account` | string | ✅ | — | Must exist in `accounts.json` |
| `media` | string (path) | ✅ | — | Must be video: mp4/mov/avi/webm |
| `caption` | string | ❌ | — | Reel caption text |

**Command template:**
```bash
python scripts/test_reel.py \
  --cookie-file "accounts/{account}/cookies.json" \
  --media "{media}" \
  [--caption "{caption}"]
```

**Note:** Reel URL is `https://www.facebook.com/reel/?s=tab` immediately after publish. Full permalink available after Facebook processes the video (1-5 min).

---

### Action: `account.list`

List all registered accounts with status.

**Trigger phrases:**
```
Vietnamese: danh sách tài khoản, xem tài khoản, liệt kê tài khoản, 
            tài khoản nào, account nào, kiểm tra tài khoản
English:    list accounts, show accounts, which accounts, account list
```

**Command:**
```bash
python scripts/account_manager.py list
```

**Expected output columns:** ID | Name | Active | Proxy | Cookies ✅/❌ | Fingerprint ✅/❌ | Last Post

---

### Action: `account.init`

Initialize a new account (import cookies + generate fingerprint).

**Trigger phrases:**
```
Vietnamese: thêm tài khoản, khởi tạo tài khoản, import cookies, 
            đăng nhập account mới, add account, setup account
English:    init account, add account, import cookies, setup new account
```

**Parameters:**

| Param | Type | Required | Validation |
|---|---|---|---|
| `account_id` | string | ✅ | Alphanumeric + underscore only, no spaces |
| `cookies_path` | string | ✅ | File must exist, must be valid JSON |

**Command:**
```bash
python scripts/account_manager.py init \
  --id "{account_id}" \
  --cookies "{cookies_path}"
```

---

### Action: `account.test`

Verify an account's session is still active.

**Trigger phrases:**
```
Vietnamese: kiểm tra session, test account, session còn không, 
            cookies còn hạn không, account still active
English:    test account, check session, verify account, is account active
```

**Command:**
```bash
python scripts/account_manager.py test --id "{account_id}"
```

**Expected outputs:**
- `✅ Account '{id}' session is ACTIVE`
- `❌ Account '{id}' session is EXPIRED` → trigger AUTH_REQUIRED runbook

---

### Action: `proxy.add`

Register a new proxy.

**Trigger phrases:**
```
Vietnamese: thêm proxy, add proxy, cấu hình proxy, đặt proxy, 
            nhập proxy, proxy mới
English:    add proxy, register proxy, configure proxy, new proxy
```

**Parameters:**

| Param | Type | Required | Validation |
|---|---|---|---|
| `host` | string | ✅ | Valid IP or hostname |
| `port` | int | ✅ | 1-65535 |
| `user` | string | ❌ | — |
| `password` | string | ❌ | — |
| `country` | string | ❌ | 2-letter ISO (VN, US, SG) |
| `proxy_type` | string | ❌ | http/https/socks5 (default: http) |

**Command:**
```bash
python scripts/proxy_manager.py add \
  --host "{host}" --port {port} \
  [--user "{user}" --pass "{password}"] \
  [--country "{country}"] \
  [--type "{proxy_type}"]
```

---

### Action: `proxy.health`

Check health of all registered proxies.

**Trigger phrases:**
```
Vietnamese: kiểm tra proxy, check proxy, proxy nào sống, 
            test proxy, trạng thái proxy, proxy health
English:    check proxy health, test proxies, proxy status, health check
```

**Command:**
```bash
python scripts/proxy_manager.py health
```

---

## Section 2 — Error Handling Runbook

### AUTH_REQUIRED

**Detection:** Output contains `FAIL: AUTH_REQUIRED`

**Automatic handling:**
```
1. Log error with account_id and timestamp
2. Mark account as "session_expired" in accounts.json
3. Print diagnostic: "Session expired for account '{id}'. Cookies need to be refreshed."
```

**Escalate to user when:**
- First occurrence on any account

**User message template:**
```
❌ Phiên đăng nhập của tài khoản '{account}' đã hết hạn.

Cách fix:
1. Mở Chrome, đăng nhập lại Facebook
2. Dùng Cookie-Editor extension → Export → JSON
3. Chạy: python scripts/account_manager.py init --id {account} --cookies /path/to/new_cookies.json
4. Kiểm tra: python scripts/account_manager.py test --id {account}
```

**Never auto-retry** without new cookies.

---

### DOM_CHANGED

**Detection:** Output contains `FAIL: DOM_CHANGED`

**Automatic handling:**
```
1. Log error with timestamp
2. Auto-run dom_learner.py (non-destructive probe):
   python scripts/dom_learner.py --cookie-file accounts/{account}/cookies.json
3. If dom_learner succeeds (exit 0), retry original post once
4. If dom_learner fails or retry also fails → escalate
```

**Escalate to user when:**
- `dom_learner.py` itself fails
- Second consecutive `DOM_CHANGED` after dom_learner fix

**User message template:**
```
⚠️ Facebook đã cập nhật giao diện. Đã chạy dom_learner.py để học lại selectors.
[Nếu vẫn lỗi] Cần cập nhật selectors thủ công:
python scripts/dom_learner.py --cookie-file accounts/{account}/cookies.json --interactive
```

---

### RATE_LIMIT

**Detection:** Output contains `FAIL: RATE_LIMIT`

**Automatic handling:**
```
1. Log error with account_id
2. Set cooldown timer: 45 minutes for this account
3. Queue the post for retry after cooldown:
   python scripts/scheduler.py --add --account {account} --text "{text}" \
     --schedule "$(date -d '+45 minutes' -Iseconds)"
4. Notify user: "Post queued for retry in 45 minutes"
```

**Escalate to user when:**
- 3 consecutive RATE_LIMIT on same account in same day → possible account flag

---

### PUBLISH_FAILED

**Detection:** Output contains `FAIL: PUBLISH_FAILED`

**Automatic handling:**
```
1. Wait 10 seconds
2. Retry once (max 1 auto-retry by Clawbot, post.py already does 3 internal retries)
3. If retry also fails → escalate
```

**Escalate to user when:**
- All retries exhausted
- Check screenshot file: `test_result_*.png` in skill root

**User message template:**
```
❌ Không thể đăng bài sau nhiều lần thử.
Screenshot trạng thái: {skill_root}/test_result_*_after_publish.png

Kiểm tra:
- Facebook có đang bảo trì không?
- Bài viết có vi phạm chính sách không?
- Cookie có còn hạn không? (chạy account.test)
```

---

## Section 3 — Clawbot Conversation Examples

**Ví dụ 1 — Đăng bài text:**
```
User: đăng facebook "Chào buổi sáng mọi người!" bằng account pham_thanh
Clawbot:
  1. Kiểm tra account: account_manager.py test --id pham_thanh ✅ ACTIVE
  2. Xác nhận: "Đăng bài: 'Chào buổi sáng mọi người!' bằng pham_thanh?"
  3. [User OK]
  4. Chạy: post.py --account pham_thanh --text "Chào buổi sáng mọi người!" --auto-approve
  5. Báo kết quả: ✅ Đã đăng: https://www.facebook.com/pham.thanh.756452/posts/pfbid0...
```

**Ví dụ 2 — Đăng story:**
```
User: lên story với ảnh /Users/me/photo.jpg
Clawbot:
  1. Kiểm tra file tồn tại ✅
  2. Xác nhận account (nếu chưa chỉ định): "Dùng account nào?"
  3. Chạy: test_story.py --cookie-file accounts/pham_thanh/cookies.json --media /Users/me/photo.jpg
  4. Báo kết quả
```

**Ví dụ 3 — Schedule post:**
```
User: lên bài "Flash sale!" lúc 10 giờ sáng ngày mai
Clawbot:
  1. Tính datetime: 2026-03-06T10:00:00+07:00
  2. Xác nhận: "Schedule 'Flash sale!' vào 10:00 ngày 06/03/2026?"
  3. [User OK]
  4. Chạy: post.py --account pham_thanh --text "Flash sale!" --schedule "2026-03-06T10:00:00+07:00" --auto-approve
  5. Báo: ✅ OK: scheduled 2026-03-06T10:00:00+07:00
```

---

## Section 4 — Migration Notes (v2.0 → v2.1)

| Change | Impact | Action Required |
|---|---|---|
| Input validation added | `account` must exist before command runs | None — improvement only |
| Trigger phrases expanded | Vietnamese + English both supported | Update Clawbot phrase register |
| Error runbook with auto-remediation | DOM_CHANGED triggers auto dom_learner | None — new feature |
| `--media` for story/reel validated before run | Faster failure on missing files | None — improvement only |
| `account.test` before every `post` | Adds ~30s per post (browser launch) | Optional: cache test result for 10 min |
| Proxy type parameter added | `--type http/https/socks5` | Update any proxy.add automations |
