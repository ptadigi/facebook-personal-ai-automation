# Roadmap — Next Features
**Skill:** `facebook-personal-ai-automation` · **Version:** 2.1.0  
**Last updated:** 2026-03-05

---

## Summary

15 tính năng tiếp theo, chia theo thời gian thực hiện và mức độ ưu tiên.

| Priority | Feature | Group | Effort | Risk |
|---|---|---|---|---|
| 🔴 P0 | Mouse movement simulation | Reliability | S | Low |
| 🔴 P0 | `window.chrome` injection | Security | S | Low |
| 🔴 P0 | Schedule time jitter | Reliability | S | Low |
| 🟠 P1 | Pytest CI với real account test | Anti-regression | M | Medium |
| 🟠 P1 | Scroll before interact | Reliability | S | Low |
| 🟠 P1 | Post result webhook | Observability | M | Low |
| 🟡 P2 | account.list table đẹp hơn | Multi-agent UX | S | Low |
| 🟡 P2 | Smart scheduling (peak hours) | Scheduling intelligence | M | Low |
| 🟡 P2 | Per-account log isolation | Observability | M | Low |
| 🟡 P2 | Load config.json (hiện tại là dummy) | Reliability | M | Medium |
| 🟣 P3 | Split post.py thành modules | Architecture | L | High |
| 🟣 P3 | Proxy credential encryption | Security | L | Medium |
| 🟣 P3 | Real browser binary (non-Playwright) | Security | L | High |
| 🟣 P3 | Rate-limit adaptive backoff | Scheduling intelligence | L | Medium |
| 🟣 P3 | Multi-account A/B content rotation | Multi-agent UX | L | Medium |

---

## Quick Wins (1–3 ngày)

### F01 — Mouse movement simulation
**Group:** Reliability + Security  
**Mục tiêu:** Thêm `page.mouse.move(x, y)` trước mỗi click để giả lập mouse movement thật

**Lợi ích:**
- Zero mouse movement là bot signal rất cao (🔴 Very High theo audit)
- Giảm đáng kể nguy cơ bị Facebook flag behavior bất thường
- Không cần thay đổi output contract hay API

**Effort:** S (Small — ~30 LOC)  
**Risk:** Thấp — thêm delay nhỏ, không ảnh hưởng kết quả

**Phụ thuộc kỹ thuật:**
- Playwright `page.mouse.move(x, y, steps=10)` 
- Cần inject trước `el.click()` trong `open_composer`, `text_input`, `submit_button`

**Tiêu chí Done:**
- [ ] Mouse moves to element center ± random offset trước mỗi click
- [ ] Delay 200-500ms (random) giữa move và click
- [ ] Unit test kiểm tra mouse.move được gọi

---

### F02 — `window.chrome` injection
**Group:** Security  
**Mục tiêu:** Inject `window.chrome = { runtime: {} }` vào init_script để che headless indicator

**Lợi ích:**
- `window.chrome` missing là red flag cho Facebook's integrity system
- Fix nhanh, không cần đổi kiến trúc

**Effort:** S  
**Risk:** Thấp — init script đã có sẵn trong fingerprint_gen.py

**Phụ thuộc kỹ thuật:**
- Thêm 3 dòng vào `fingerprint_gen.py` init script string

**Tiêu chí Done:**
- [ ] `window.chrome` defined trong every browser context
- [ ] Verify via `page.evaluate("window.chrome")` không trả None

---

### F03 — Schedule time jitter
**Group:** Scheduling intelligence + Security  
**Mục tiêu:** Thêm ±5-15 phút random vào mỗi scheduled post để tránh machine-perfect intervals

**Lợi ích:**
- Post đúng giờ tròn (10:00, 11:00...) là inauthentic behavior signal
- Easy fix trong scheduler.py khi tính fire time

**Effort:** S  
**Risk:** Thấp — chỉ ảnh hưởng exact fire time, không đổi contract

**Phụ thuộc kỹ thuật:**
- `random.uniform(-900, 900)` seconds added to scheduled_at when computing sched_dt
- Configurable: `SCHEDULE_JITTER_SECONDS=900` env var

**Tiêu chí Done:**
- [ ] Actual fire time = scheduled_at ± N seconds (configurable)
- [ ] Jitter amount logged in run-log.jsonl
- [ ] Default jitter ≤ 15 phút (900s)

---

### F04 — Scroll before interact
**Group:** Reliability  
**Mục tiêu:** Thêm `page.evaluate("window.scrollBy(0, 300)")` sau mỗi page load trước khi interact

**Lợi ích:**
- No-scroll behavior là bot signal
- Real users scroll to read before clicking

**Effort:** S  
**Risk:** Thấp — thêm 500ms delay, no functional change

**Phụ thuộc kỹ thuật:**
- Thêm vào `post.py` sau `page.goto("https://www.facebook.com", ...)`

**Tiêu chí Done:**
- [ ] Scroll called on every new page load
- [ ] Scroll amount: random 200-400px
- [ ] Optional: tắt được qua `--no-scroll` flag

---

### F05 — account.list table đẹp hơn
**Group:** Multi-agent UX  
**Mục tiêu:** Cải thiện output của `account_manager.py list` với màu sắc, status icon rõ ràng hơn

**Lợi ích:**
- Operator dễ đọc hơn khi có nhiều accounts
- CI/agent parse dễ hơn nếu support `--json` flag

**Effort:** S  
**Risk:** Thấp — chỉ đổi display, không đổi data

**Phụ thuộc kỹ thuật:**
- Thêm `--json` flag → output JSON array
- Thêm color codes via ANSI escape codes (hoặc `colorama`)

**Tiêu chí Done:**
- [ ] `account_manager.py list` hiển thị ✅/❌ cho mỗi field
- [ ] `account_manager.py list --json` trả về JSON array
- [ ] Không break output khi không có terminal (pipe-safe)

---

## Mid-term (1–2 tuần)

### F06 — Pytest CI với real account tests
**Group:** Anti-regression testing  
**Mục tiêu:** Tạo integration test suite chạy live với real Facebook account trên CI/CD (gated)

**Lợi ích:**
- Catch regressions trước khi lên production
- Phát hiện DOM_CHANGED sớm (test chạy theo lịch, alert nếu fail)

**Effort:** M  
**Risk:** Medium — cần secure cookie storage trên CI

**Phụ thuộc kỹ thuật:**
- GitHub Actions secret: `FB_COOKIES_BASE64` (cookie JSON encoded)
- Separate test job với `--dry-run` flag để không post thật
- Scheduled workflow: chạy mỗi ngày lúc 7am để detect FB UI changes sớm

**Tiêu chí Done:**
- [ ] `tests/integration/` với test_live_post.py (dry-run only on CI)
- [ ] GitHub Actions job "integration" runs daily
- [ ] Alert nếu DOM_CHANGED detected
- [ ] Secrets management documented

---

### F07 — Post result webhook
**Group:** Observability  
**Mục tiêu:** `post.py` có thể gửi POST request đến webhook URL sau khi đăng xong

**Lợi ích:**
- Integration với Slack, Discord, Telegram, n8n, Zapier
- Operators nhận notification tức thì
- Dễ integrate vào workflow automation

**Effort:** M  
**Risk:** Thấp — opt-in qua `--webhook URL`

**Phụ thuộc kỹ thuật:**
- `--webhook URL` arg trong post.py
- Send POST request với payload: `{status, url, account_id, timestamp}`
- Retry webhook 2 lần nếu fail (non-blocking)

**Tiêu chí Done:**
- [ ] `--webhook https://hooks.xxx.com/...` arg works
- [ ] Payload schema documented
- [ ] Webhook failure does NOT fail the post
- [ ] Unit test mocks webhook call

---

### F08 — Smart scheduling (peak hours)
**Group:** Scheduling intelligence  
**Mục tiêu:** Scheduler tự chọn giờ post trong khung giờ "peak engagement" thay vì giờ cố định

**Lợi ích:**
- Engagement cao hơn (VN peak: 6-9am, 12-1pm, 7-10pm)
- Giảm pattern detection (không còn exact interval)
- Useful cho multi-account campaigns

**Effort:** M  
**Risk:** Thấp — feature mới, không đổi existing

**Phụ thuộc kỹ thuật:**
- `references/rotation-rules.json` thêm `"peak_hours": [[6,9],[12,13],[19,22]]`
- Scheduler mode: `--smart-schedule` tính giờ tốt nhất trong window
- Timezone-aware computation

**Tiêu chí Done:**
- [ ] `scheduler.py --add --smart-schedule --window "2026-03-06"` picks optimal time
- [ ] Peak hours configurable per-account in accounts.json
- [ ] Jitter applied within peak window

---

### F09 — Per-account log isolation
**Group:** Observability  
**Mục tiêu:** Log mỗi account vào folder riêng: `references/logs/<account_id>/run-log.jsonl`

**Lợi ích:**
- Dễ debug từng account riêng lẻ
- Shared log file hiện tại khó filter khi có nhiều accounts
- Tránh single log file lớn

**Effort:** M  
**Risk:** Medium — cần backward compat với existing log path

**Phụ thuộc kỹ thuật:**
- Thêm `--log-dir` arg vào post.py
- Default: `references/logs/<account_id>/run-log.jsonl`
- Fallback: `references/run-log.jsonl` nếu không có account_id (legacy)
- Rotation vẫn hoạt động per-file

**Tiêu chí Done:**
- [ ] Per-account log file created automatically
- [ ] Global log still works (backward compat)
- [ ] `make logs ACCOUNT=pham_thanh` shows account-specific log
- [ ] Log rotation per file, not global

---

### F10 — config.json thực sự được đọc
**Group:** Reliability  
**Mục tiêu:** Implement `load_config()` đọc `config.json` và merge với argparse args

**Lợi ích:**
- config.json hiện tại là "đồ trang trí" — không ai đọc nó
- Operators muốn default headless=true, default account, etc.
- Giảm số lượng CLI args phải gõ mỗi lần

**Effort:** M  
**Risk:** Medium — cần test không break existing arg behavior

**Priority order:** argparse > env var > config.json

**Tiêu chí Done:**
- [ ] `load_config()` helper trong `scripts/lib/config.py`
- [ ] `post.py` reads config.json for defaults
- [ ] Explicit args always override config
- [ ] config.example.json updated to match actual loaded fields

---

## Scale / Advanced (1–2 tháng)

### F11 — Split post.py thành modules
**Group:** Architecture  
**Mục tiêu:** Tách post.py (816 dòng) thành `lib/auth.py`, `lib/compose.py`, `lib/publish.py`

**Lợi ích:**
- Testability tốt hơn (unit test từng module)
- Onboarding dev mới dễ hơn
- Reuse auth và compose logic cho story/reel

**Effort:** L  
**Risk:** Cao — cần test đầy đủ sau refactor, output contract phải giữ nguyên

**Phụ thuộc kỹ thuật:**
- `lib/auth.py`: load_cookies, inject_cookies, verify_auth
- `lib/compose.py`: open_composer, enter_text, attach_media, set_schedule
- `lib/publish.py`: click_publish, extract_post_url, update_account_stats
- `post.py` becomes thin orchestrator importing from lib/

**Tiêu chí Done:**
- [ ] 48 existing tests still pass
- [ ] Output contract unchanged (verified by UAT-REGR-001)
- [ ] Each module has own test file
- [ ] Coverage ≥ 80% per module

---

### F12 — Proxy credential encryption
**Group:** Security  
**Mục tiêu:** Mã hóa proxy password trong proxy-list.json bằng OS keyring

**Lợi ích:**
- Proxy credentials hiện tại plaintext trong JSON
- Nếu file bị lộ → all proxies compromised

**Effort:** L  
**Risk:** Medium — keyring behavior khác nhau trên Windows/Linux/Mac

**Phụ thuộc kỹ thuật:**
- `keyring` library: `pip install keyring`
- Store key: `keyring.set_password("fb-autoposter", proxy_id, password)`
- Fetch: `keyring.get_password("fb-autoposter", proxy_id)`
- Migration script: encrypt existing plaintext passwords

**Tiêu chí Done:**
- [ ] Proxy passwords stored in OS keyring, not JSON
- [ ] Migration script for existing proxy-list.json
- [ ] Fallback to plaintext if keyring unavailable (with warning)
- [ ] Document setup for keyring on Windows/Linux

---

### F13 — Real Chrome binary (non-Playwright Chromium)
**Group:** Security  
**Mục tiêu:** Option dùng real Chrome binary thay vì Playwright's bundled Chromium

**Lợi ích:**
- Real Chrome có different TLS fingerprint, real extension list, different CDP behavior
- Giảm JA3 fingerprint risk đáng kể
- `Sec-CH-UA` header matches real Chrome

**Effort:** L  
**Risk:** Cao — CDP API compatibility, version mismatch risks

**Phụ thuộc kỹ thuật:**
- `playwright.chromium.launch(executable_path="/usr/bin/google-chrome")`
- `--channel=chrome` flag in Playwright
- Detect Chrome installation path cross-platform

**Tiêu chí Done:**
- [ ] `--browser-path` arg in post.py
- [ ] Auto-detect Chrome on Windows/Mac/Linux
- [ ] Fallback to Playwright Chromium if Chrome not found
- [ ] Document pros/cons in README

---

### F14 — Rate-limit adaptive backoff
**Group:** Scheduling intelligence  
**Mục tiêu:** Scheduler tự học từ RATE_LIMIT history và tự điều chỉnh MIN_POST_GAP

**Lợi ích:**
- Account bị rate limit nhiều → tự tăng gap
- Account ổn → có thể giảm gap thận trọng
- Không cần operator tự điều chỉnh thủ công

**Effort:** L  
**Risk:** Medium — cần careful tuning để không quá conservative

**Phụ thuộc kỹ thuật:**
- Track RATE_LIMIT history per account trong accounts.json
- Adaptive algorithm: nếu N rate limits trong M giờ → double MIN_POST_GAP
- Cool-down reset: nếu 24h không có rate limit → giảm gap về default

**Tiêu chí Done:**
- [ ] Rate limit history stored per account
- [ ] MIN_POST_GAP auto-adjusted based on history
- [ ] Max gap cap: 60 phút (configurable)
- [ ] Operator can override với `--force-gap`

---

### F15 — Multi-account A/B content rotation
**Group:** Multi-agent UX  
**Mục tiêu:** Campaign system: 1 nội dung, tự rotate qua N accounts với variation

**Lợi ích:**
- Marketer muốn test content variation across accounts
- Avoid cross-account duplicate detection (slight text variation per account)
- Centralized campaign management

**Effort:** L  
**Risk:** Medium — content policy risk nếu variation quá nhỏ

**Phụ thuộc kỹ thuật:**
- `scripts/campaign.py` mới: đọc campaign config JSON
- Campaign config: `{accounts: [...], text_template: "...", media_pool: [...]}`
- Per-account variation: thêm variation string nhỏ (timestamp, emoji khác nhau)
- Schedule phân phối đều qua accounts với gap

**Tiêu chí Done:**
- [ ] `campaign.py --config campaign.json` hoạt động
- [ ] Mỗi account nhận variation nhỏ khác nhau
- [ ] Campaign progress tracked trong JSON file
- [ ] Cancel individual account from campaign without affecting others

---

## Ưu tiên phát triển

```
Tháng 1:  F01 (mouse), F02 (window.chrome), F03 (jitter), F04 (scroll), F05 (list UI)
Tháng 2:  F06 (CI tests), F07 (webhook), F08 (smart schedule), F09 (per-account log), F10 (config.json)
Tháng 3+: F11 (split post.py), F12 (proxy crypto), F13 (real Chrome), F14 (adaptive), F15 (campaigns)
```

---

## Anti-regression Policy

Mọi feature mới phải:
1. Giữ nguyên output contract của `post.py` (OK/WAIT_APPROVAL/FAIL)
2. Pass toàn bộ 48 unit tests hiện có (thêm test mới nếu cần)
3. Backward compatible với existing CLI args (thêm arg mới, KHÔNG đổi arg cũ)
4. Được document trong CHANGELOG.md
5. Có reviewer sign-off ở multi-agent-uat.md trước khi merge
