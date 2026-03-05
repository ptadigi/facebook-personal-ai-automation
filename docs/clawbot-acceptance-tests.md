# Clawbot Skill — Acceptance Test Matrix
**Skill:** `facebook-personal-ai-automation`  
**File:** `skills/clawbot-skill.md v2.1`  
**Purpose:** Verify Clawbot correctly maps user intent → command → expected output

---

## How to Run

```bash
# Manual test runner (execute each command, compare output to Expected)
# Automated (future): pytest tests/clawbot/ with mocked subprocess

cd /path/to/facebook-personal-ai-automation
```

---

## 1. Happy Path — `post` Action

### TC-P-001: Text-only post, auto-approve
```
Input trigger: "đăng facebook Hello world bằng account pham_thanh"
Resolved params:
  account = "pham_thanh"
  text    = "Hello world"
  auto_approve = true

Command:
  python scripts/post.py --account pham_thanh --text "Hello world" --auto-approve

Expected output (stdout last line):
  OK: published | url: https://www.facebook.com/pham.thanh.756452/posts/pfbid0... | account: pham_thanh

Clawbot response:
  ✅ Đã đăng thành công: https://www.facebook.com/pham.thanh.756452/posts/pfbid0...
```

---

### TC-P-002: Single image post
```
Input: "post ảnh /path/to/photo.jpg lên fb với caption Hôm nay đẹp trời"
Params:
  account = "pham_thanh" (default or last used)
  text    = "Hôm nay đẹp trời"
  media   = ["/path/to/photo.jpg"]

Command:
  python scripts/post.py --account pham_thanh --text "Hôm nay đẹp trời" --media "/path/to/photo.jpg" --auto-approve

Expected: OK: published | url: https://...
```

---

### TC-P-003: Multiple images
```
Input: "đăng 3 ảnh lên fb: img1.jpg img2.jpg img3.jpg"
Command:
  python scripts/post.py --account pham_thanh \
    --media img1.jpg --media img2.jpg --media img3.jpg \
    --auto-approve

Expected: OK: published | url: https://...
```

---

### TC-P-004: Video post
```
Input: "post video clip.mp4 lên facebook"
Command:
  python scripts/post.py --account pham_thanh --media clip.mp4 --auto-approve

Expected: OK: published | url: https://...
Note: URL capture may show "URL not captured — check feed" for some video posts (known limitation)
```

---

### TC-P-005: Scheduled post with timezone
```
Input: "schedule bài 'Flash sale' lên fb lúc 10:00 sáng mai"
Clawbot resolves datetime:
  schedule = "2026-03-06T10:00:00+07:00"  # must include +07:00

Command:
  python scripts/post.py --account pham_thanh --text "Flash sale" \
    --schedule "2026-03-06T10:00:00+07:00" --auto-approve

Expected: OK: scheduled 2026-03-06T10:00:00+07:00
```

---

### TC-P-006: Dry run (no publish)
```
Input: "xem trước bài đăng Hello world không đăng"
Command:
  python scripts/post.py --account pham_thanh --text "Hello world" --dry-run

Expected: WAIT_APPROVAL
Clawbot response: "Bài đăng đã được soạn nhưng chưa đăng (dry-run mode)."
```

---

### TC-P-007: Story post
```
Input: "lên story với ảnh photo.jpg"
Command:
  python scripts/test_story.py --cookie-file accounts/pham_thanh/cookies.json --media photo.jpg

Expected stdout last line:
  ✅ RESULT: OK: story published
  or
  ⚠ RESULT: Published — verify on profile
```

---

### TC-P-008: Reel post
```
Input: "đăng reel video clip.mp4 caption Reel của tôi"
Command:
  python scripts/test_reel.py --cookie-file accounts/pham_thanh/cookies.json \
    --media clip.mp4 --caption "Reel của tôi"

Expected:
  ✅ RESULT: OK: reel published
  🔗 URL: https://www.facebook.com/reel/?s=tab

Note: Final reel URL available after Facebook processing (1-5 min)
```

---

## 2. Account Management Happy Path

### TC-A-001: List accounts
```
Command: python scripts/account_manager.py list
Expected: Table with columns ID | Name | Active | Proxy | Cookies | Fingerprint | Last Post
          At least 1 row visible
Exit code: 0
```

### TC-A-002: Init new account
```
Command: python scripts/account_manager.py init --id test_acc --cookies /path/to/cookies.json
Expected:
  ✅ Account 'test_acc' initialized
  📋 Fingerprint generated: chrome / 1600x900
Exit code: 0
Side effect: accounts/test_acc/cookies.json created, accounts/test_acc/fingerprint.json created
```

### TC-A-003: Test active session
```
Command: python scripts/account_manager.py test --id pham_thanh
Expected: ✅ Account 'pham_thanh' session is ACTIVE
Exit code: 0
```

---

## 3. Error Path — Invalid Input

### TC-E-001: Account not found
```
Input: "đăng bài Hello world bằng account nonexistent_acc"
Clawbot pre-validation:
  Check accounts.json → "nonexistent_acc" not found
  → DO NOT run command
  
Expected Clawbot response:
  ❌ Không tìm thấy account 'nonexistent_acc'.
  Các account hiện có: pham_thanh, acc_vn_01
  Dùng account.list để kiểm tra.
```

### TC-E-002: Media file not found
```
Input: "đăng ảnh /nonexistent/photo.jpg"
Clawbot pre-validation:
  os.path.exists("/nonexistent/photo.jpg") → False
  → DO NOT run command

Expected Clawbot response:
  ❌ Không tìm thấy file: /nonexistent/photo.jpg
  Kiểm tra lại đường dẫn.
```

### TC-E-003: Unsupported media format
```
Input: "đăng file document.pdf lên fb"
Clawbot pre-validation:
  extension ".pdf" not in allowed list
  → reject

Expected Clawbot response:
  ❌ Định dạng file không được hỗ trợ: .pdf
  Hỗ trợ: jpg, jpeg, png, gif, mp4, mov, webm
```

### TC-E-004: Schedule in the past
```
Input: "schedule bài Hello lúc 10:00 sáng hôm qua"
Clawbot validation:
  dt = 2026-03-04T10:00:00+07:00 < now
  → reject

Expected: ❌ Thời gian schedule phải là tương lai. Nhập lại thời gian.
```

### TC-E-005: Schedule without timezone
```
Input: "schedule bài Hello lúc 2026-03-06T10:00:00"
Clawbot validation:
  datetime.fromisoformat("2026-03-06T10:00:00").tzinfo is None
  → reject

Expected: ❌ Cần chỉ định múi giờ. Ví dụ: 2026-03-06T10:00:00+07:00
```

### TC-E-006: Empty post (no text, no media)
```
Input: "đăng facebook" (no content)
Clawbot validation: text=None, media=[]
  → reject

Expected: ❌ Bài đăng cần có nội dung. Thêm text hoặc ảnh/video.
```

---

## 4. Error Path — Runtime Errors

### TC-R-001: AUTH_REQUIRED
```
Scenario: Cookies expired, session invalid
Command output: FAIL: AUTH_REQUIRED - Redirected to login/checkpoint

Clawbot auto-action:
  1. Log account as session_expired
  2. Display fix instructions

Expected Clawbot response:
  ❌ Phiên đăng nhập hết hạn cho tài khoản 'pham_thanh'.
  
  Cách fix:
  1. Đăng nhập lại Facebook trong Chrome
  2. Export cookies mới (Cookie-Editor → JSON)
  3. Chạy: python scripts/account_manager.py init --id pham_thanh --cookies /path/new_cookies.json
  4. Kiểm tra: python scripts/account_manager.py test --id pham_thanh
  
Auto-retry: KHÔNG (cần cookies mới)
```

### TC-R-002: DOM_CHANGED
```
Scenario: Facebook updated UI, selectors broken
Command output: FAIL: DOM_CHANGED - All selectors failed for open_composer

Clawbot auto-action:
  1. Auto-run: python scripts/dom_learner.py --cookie-file accounts/pham_thanh/cookies.json
  2. [dom_learner exits 0] → Retry original post once
  3. [retry OK] → Report success
  4. [retry fails] → Escalate

Expected Clawbot response (auto-fix succeeded):
  ⚠️ Facebook cập nhật UI. Đã học lại selectors tự động.
  ✅ Đã đăng thành công sau khi fix: https://...

Expected Clawbot response (escalate):
  ❌ Facebook cập nhật UI và cần sửa thủ công.
  Chạy: python scripts/dom_learner.py --interactive --cookie-file accounts/pham_thanh/cookies.json
```

### TC-R-003: RATE_LIMIT
```
Scenario: Facebook throttling account
Command output: FAIL: RATE_LIMIT - Facebook rate limit detected

Clawbot auto-action:
  1. Schedule retry: now + 45 minutes
  2. Notify user

Expected Clawbot response:
  ⏳ Facebook đang giới hạn tốc độ đăng bài.
  Bài viết đã được đặt lịch đăng lại sau 45 phút: 13:15 +07:00
  
Auto-retry: CÓ (sau 45 phút, 1 lần)
```

### TC-R-004: PUBLISH_FAILED
```
Scenario: Post button clicked but no confirmation
Command output: FAIL: PUBLISH_FAILED - Retry exhausted without confirmed post

Clawbot auto-action:
  1. Wait 10s, retry once
  2. If still fails → escalate

Expected Clawbot response:
  ❌ Không thể đăng bài sau nhiều lần thử.
  
  Kiểm tra:
  - Screenshot: test_result_*_after_publish.png trong thư mục skill
  - Facebook có bảo trì không?
  - Chạy account.test để kiểm tra session
  
Auto-retry: 1 lần (thêm vào 3 lần nội bộ của post.py)
```

---

## 5. Edge Cases

### TC-X-001: Schedule timezone mismatch (UTC vs +07:00)
```
Scenario: User schedules at "10:00 sáng" but doesn't specify timezone
Clawbot must: Ask for timezone confirmation OR default to +07:00 (VN)

Test:
  Input: schedule "2026-03-06T10:00:00" (no tz)
  Expected: Clawbot adds +07:00 → "2026-03-06T10:00:00+07:00"
  OR Clawbot asks: "Bạn muốn đăng lúc 10:00 theo múi giờ nào? (mặc định: +07:00 Việt Nam)"
```

### TC-X-002: Large video upload (>50MB)
```
Scenario: Clip 200MB → upload takes ~180s
Test:
  Command: test_reel.py --media large_clip_200mb.mp4
  Expected: No timeout before 180s (scheduler uses 300s timeout)
  Expected: ✅ RESULT: OK: reel published
```

### TC-X-003: Concurrent account posts
```
Scenario: 2 accounts scheduled at same time
Expected: Both execute (may be sequential in current version)
Verify: Both post URLs returned, both accounts' last_post_url updated in accounts.json
```

### TC-X-004: Expired cookies — `account.list` no crash
```
Scenario: Account with empty cookies_path in accounts.json
Command: python scripts/account_manager.py list
Expected: Table shows ❌ for Cookies column — NO crash (bug was fixed)
Exit code: 0
```

### TC-X-005: Same content posted twice (deduplication)
```
Scenario: Scheduler --add called twice with same text + schedule
Expected (current): Two entries created (known gap — see security-audit.md B3)
Expected (after fix): Second add blocked with message:
  "⚠️ Bài đăng tương tự đã có trong queue: id=xxxx, lúc 10:00. Bỏ qua."
```

---

## 6. Proxy Tests

### TC-PR-001: Add proxy
```
Command: python scripts/proxy_manager.py add --host 1.2.3.4 --port 3128 --country VN
Expected:
  ✅ Proxy 'proxy_1_2_3_4_3128' added (direct mode, type=http)
Exit code: 0
Side effects: proxies/proxy-list.json updated
```

### TC-PR-002: Health check — all proxies
```
Command: python scripts/proxy_manager.py health
Expected: Table with proxy ID, status (✅ healthy / ❌ unreachable), latency
Exit code: 0 even if some proxies fail
```

### TC-PR-003: Unreachable proxy → rotate
```
Scenario: Account's proxy is down, post fails with connection error
Expected Clawbot flow:
  1. Detect proxy connection error in stderr
  2. Auto-run: python scripts/proxy_manager.py rotate --account pham_thanh
  3. Retry post with new proxy
  4. Notify user: "Proxy cũ lỗi, đã chuyển sang proxy mới và đăng thành công"
```

---

## 7. Execution Checklist

```markdown
## Pre-Production Acceptance Checklist

### Account Management
- [ ] TC-A-001: account.list shows all accounts without crash
- [ ] TC-A-002: account.init creates cookies + fingerprint files
- [ ] TC-A-003: account.test confirms active session

### Feed Posts
- [ ] TC-P-001: text-only post returns OK: published with URL
- [ ] TC-P-002: single image post with URL captured
- [ ] TC-P-003: multi-image post successful
- [ ] TC-P-004: video post successful (URL may say "not captured")
- [ ] TC-P-005: scheduled post returns OK: scheduled
- [ ] TC-P-006: dry-run returns WAIT_APPROVAL

### Story & Reel
- [ ] TC-P-007: story post completes without crash
- [ ] TC-P-008: reel post completes without ctx-after-close crash

### Input Validation
- [ ] TC-E-001: missing account → blocked before command
- [ ] TC-E-002: missing media file → blocked before command
- [ ] TC-E-003: unsupported format → rejected
- [ ] TC-E-004: past schedule → rejected
- [ ] TC-E-005: no-tz schedule → rejected or auto-fixed
- [ ] TC-E-006: empty post → rejected

### Runtime Error Handling
- [ ] TC-R-001: AUTH_REQUIRED → user instructions shown
- [ ] TC-R-002: DOM_CHANGED → auto dom_learner + retry
- [ ] TC-R-003: RATE_LIMIT → auto-schedule retry 45min
- [ ] TC-R-004: PUBLISH_FAILED → escalate with screenshot hint

### Edge Cases
- [ ] TC-X-004: account list no crash with empty cookies_path
- [ ] TC-X-002: large video no timeout (requires 300s timeout fix)
```
