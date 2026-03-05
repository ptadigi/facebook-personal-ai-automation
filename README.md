<div align="center">

# 🤖 fb-autoposter

**Tự động đăng bài Facebook cá nhân qua browser — không cần API, không cần token.**

Viết bằng Python + Playwright. Chạy được trên máy local, VPS, hay bất kỳ đâu có Chrome.

[![Tests](https://github.com/ptadigi/facebook-personal-ai-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/ptadigi/facebook-personal-ai-automation/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/playwright-chromium-45BA4B?style=flat&logo=playwright&logoColor=white)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat)](LICENSE)

</div>

---

## Tại sao có tool này?

Facebook không có API công khai cho personal profile. Mọi công cụ đăng bài đều dùng Page API (cần business account) hoặc dùng browser automation. Cái này thuộc loại thứ hai — nó điều khiển Chromium như một người thật, bao gồm fingerprint, proxy, session persistence, và một cơ chế tự học lại selector khi Facebook đổi UI.

Mục đích: nghiên cứu và sử dụng cá nhân.

---

## Tính năng

- **Feed post** — text, ảnh đơn, nhiều ảnh (max 4), video
- **Story** — ảnh hoặc video 24h
- **Reel** — short video
- **Multi-account** — mỗi account có cookies riêng, fingerprint riêng, proxy riêng
- **Browser fingerprint spoofing** — UA, viewport, WebGL, Canvas, AudioContext
- **Proxy** — HTTP/HTTPS/SOCKS5, health check, auto-rotate khi lỗi
- **Scheduler** — đặt lịch đăng theo ISO 8601 + timezone, daemon chạy nền
- **DOM self-healing** — `dom_learner.py` tự học lại selector khi FB đổi giao diện
- **Output contract** — stdout luôn là `OK:` / `WAIT_APPROVAL` / `FAIL:` — dễ parse từ script khác

---

## Cài đặt

```bash
git clone https://github.com/ptadigi/facebook-personal-ai-automation
cd facebook-personal-ai-automation

pip install -r requirements.txt
playwright install chromium
```

Hoặc dùng Makefile:

```bash
make install
```

---

## Dùng nhanh

### Bước 1 — Lấy cookie

1. Cài extension [Cookie-Editor](https://cookie-editor.com/) trên Chrome
2. Đăng nhập Facebook
3. Click Cookie-Editor → **Export** → **Export as JSON** → lưu thành `cookies.json`

### Bước 2 — Khởi tạo account

```bash
python scripts/account_manager.py init --id myaccount --cookies cookies.json
# → copy cookies, tạo fingerprint, kiểm tra datr

python scripts/account_manager.py test --id myaccount
# → ✅ Account 'myaccount' session is ACTIVE
```

### Bước 3 — Đăng!

```bash
# Text
python scripts/post.py --account myaccount --text "Hôm nay mưa quá" --auto-approve

# Ảnh
python scripts/post.py --account myaccount --text "Check-in" --media photo.jpg --auto-approve

# Video
python scripts/post.py --account myaccount --media clip.mp4 --auto-approve

# Story
python scripts/test_story.py --cookie-file accounts/myaccount/cookies.json --media photo.jpg

# Reel
python scripts/test_reel.py --cookie-file accounts/myaccount/cookies.json --media video.mp4

# Đặt lịch (10h sáng mai)
python scripts/post.py --account myaccount --text "Good morning!" \
  --schedule "2026-03-06T10:00:00+07:00" --auto-approve
```

Output mẫu:

```
OK: published | url: https://www.facebook.com/pham.thanh.756452/posts/pfbid0... | account: myaccount
```

---

## Output contract

Mọi script đều in đúng một trong ba dạng ra stdout:

```
OK: published | url: https://...
OK: scheduled 2026-03-06T10:00:00+07:00
WAIT_APPROVAL
FAIL: AUTH_REQUIRED - Session expired
FAIL: DOM_CHANGED - All selectors failed — run dom_learner.py
FAIL: RATE_LIMIT - Facebook rate limit detected
FAIL: PUBLISH_FAILED - Retry exhausted
```

Thiết kế này cho phép gọi từ shell script, AI agent, hay bất kỳ orchestrator nào mà không cần parse HTML hay log.

---

## Cấu trúc project

```
├── scripts/
│   ├── post.py                # Main — đăng feed post
│   ├── test_story.py          # Đăng story
│   ├── test_reel.py           # Đăng reel
│   ├── account_manager.py     # Quản lý accounts
│   ├── proxy_manager.py       # Quản lý proxies
│   ├── fingerprint_gen.py     # Tạo/quản lý fingerprint
│   ├── dom_learner.py         # Tự học lại FB selectors
│   ├── scheduler.py           # Daemon schedule
│   └── lib/
│       └── cookies.py         # Shared cookie utilities
├── scripts/tests/             # Dùng test_all_formats.py để test thủ công
├── tests/                     # Pytest unit tests (48 tests, chạy offline)
├── accounts/                  # accounts.json + per-account cookies & fingerprint
├── proxies/                   # proxy-list.json
├── references/
│   ├── selector-map.json      # Facebook DOM selectors
│   └── run-log.jsonl          # Structured run history (JSONL)
├── skills/                    # AI agent integration (Clawbot, Claude, OpenAI)
├── docs/
│   ├── security-audit.md      # Audit findings & remediation roadmap
│   └── clawbot-acceptance-tests.md
├── Makefile
├── pytest.ini
└── requirements.txt
```

---

## Multi-account + Proxy

```bash
# Thêm proxy
python scripts/proxy_manager.py add \
  --host 103.x.x.x --port 3128 --user user --pass pass --country VN

# Gán proxy cho account
python scripts/account_manager.py assign --id myaccount --proxy proxy_103_x_x_x_3128

# Từ lúc này post.py tự load proxy + fingerprint cho account đó
python scripts/post.py --account myaccount --text "Hello!" --auto-approve
```

Proxy policy nằm ở `references/rotation-rules.json`:

```json
{
  "strategy": "sticky_per_account",
  "rotate_on_fail": true,
  "fail_threshold": 2,
  "cooldown_minutes": 30,
  "prefer_same_country": true
}
```

---

## Browser fingerprint

Mỗi account có fingerprint stable, deterministic từ account ID:

| Property | Method |
|---|---|
| User-Agent | Real Chrome/Edge UA, không có "HeadlessChrome" |
| Viewport | Random realistic (1366×768, 1920×1080...) |
| `navigator.webdriver` | Patch về `undefined` |
| WebGL vendor/renderer | Inject GPU strings thật |
| Canvas | Per-account pixel noise |
| AudioContext | Per-account buffer noise |
| Locale + Timezone | Mapped theo proxy country |

Để tạo/xem fingerprint:

```bash
python scripts/fingerprint_gen.py generate --account myaccount
python scripts/fingerprint_gen.py show --account myaccount
```

---

## Khi nào dùng dom_learner?

Facebook thỉnh thoảng đổi UI. Khi đó post.py sẽ ra `FAIL: DOM_CHANGED`. Chạy:

```bash
python scripts/dom_learner.py --cookie-file accounts/myaccount/cookies.json --account myaccount
```

Script sẽ tự probe lại các selectors và cập nhật `references/selector-map.json`. Sau đó thử lại là được.

---

## Tests

```bash
# Chạy 48 unit tests (không cần browser, không cần internet)
make test

# Hoặc trực tiếp
pytest tests/ -v
```

Coverage: `lib/cookies`, `scheduler`, `account_manager`, `post`.

---

## Scheduler daemon

```bash
# Đặt lịch
python scripts/scheduler.py --cookie-file accounts/myaccount/cookies.json \
  --add --text "Bài buổi sáng" --schedule "2026-03-06T08:00:00+07:00"

# Xem queue
python scripts/scheduler.py --list

# Chạy daemon (kiểm tra mỗi 60s, tối đa 3 post song song)
python scripts/scheduler.py --daemon
```

Cấu hình qua env:

```bash
POST_TIMEOUT_SECONDS=300   # timeout mỗi post (default: 300s)
MIN_POST_GAP_MINUTES=15    # khoảng cách tối thiểu giữa 2 post cùng account (default: 15)
SCHEDULER_MAX_WORKERS=3    # số post song song (default: 3)
```

---

## AI Agent Integration

Folder `skills/` chứa định nghĩa skill cho các AI agent:

| File | Dùng cho |
|---|---|
| `skills/clawbot-skill.md` | Clawbot (VN + EN triggers, error runbooks) |
| `skills/claude-skill.md` | Claude (MCP tool definition) |
| `skills/openai-function.json` | OpenAI function calling |
| `SKILL.md` | Antigravity |

---

## Error codes

| Code | Nguyên nhân | Fix |
|---|---|---|
| `AUTH_REQUIRED` | Cookie hết hạn | Export lại cookies, chạy `account_manager.py init` |
| `DOM_CHANGED` | FB đổi UI | Chạy `dom_learner.py` |
| `RATE_LIMIT` | FB giới hạn tốc độ | Chờ 45 phút, scheduler tự retry |
| `PUBLISH_FAILED` | Không confirm được publish | Xem screenshot trong thư mục gốc |

---

## Giới hạn & Rủi ro

Tool này mô phỏng hành vi trình duyệt nên vẫn có thể bị phát hiện. Các yếu tố rủi ro cao nhất:

- IP datacenter (dùng residential proxy thay thế)
- Đăng quá nhiều trong thời gian ngắn (`daily_post_limit` trong `accounts.json`)
- Nội dung trùng lặp giữa các lần đăng
- Account mới (< 3 tháng tuổi) + automation

Xem đầy đủ trong [`docs/security-audit.md`](docs/security-audit.md).

---

## Makefile shortcuts

```bash
make install       # pip + playwright install
make test          # pytest tests/
make lint          # ruff check
make dom-learn     # tự học lại selectors
make list-accounts # xem danh sách accounts
make check-proxy   # kiểm tra proxy
make daemon        # chạy scheduler
```

---

## License

MIT — dùng cho nghiên cứu và mục đích cá nhân. Không sử dụng để spam, scam, hay vi phạm Terms of Service của Facebook.
