# facebook-personal-browser-post

> **Post to Facebook personal profile via browser automation** — supports text, images, videos, stories, reels, multi-account, proxy, fingerprint spoofing, and persistent sessions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Playwright](https://img.shields.io/badge/playwright-chromium-green.svg)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Feature | Details |
|---|---|
| **6 content types** | Text, single image, multiple images, video, story, reel |
| **Multi-account** | N accounts, each with own cookies + fingerprint + proxy |
| **Proxy support** | HTTP/HTTPS/SOCKS5, auto health-check, auto-rotate on fail |
| **Browser fingerprint** | Stable per-account: UA, viewport, WebGL, Canvas, Audio noise |
| **Persistent profile** | `launch_persistent_context` — session survives restarts |
| **URL reporting** | Every post returns `OK: published | url: https://...` |
| **Retry logic** | 3 attempts with backoff on publish failure |
| **DOM self-healing** | `dom_learner.py` re-discovers selectors after FB UI updates |
| **Scheduling** | Post at specific datetime (ISO 8601 + timezone) |
| **Structured logging** | All runs appended to `references/run-log.jsonl` |

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/yourname/facebook-personal-browser-post
cd facebook-personal-browser-post
pip install -r requirements.txt
playwright install chromium
```

### 2. Get session cookies

Install the **Cookie-Editor** browser extension → Login to Facebook → Export cookies as JSON → save as `cookies.json`

### 3. Initialize your account

```bash
# First-time setup: copy cookies + create fingerprint
python scripts/account_manager.py init --id myaccount --cookies cookies.json

# Verify session is active
python scripts/account_manager.py test --id myaccount
```

### 4. Post!

```bash
# Text post
python scripts/post.py --account myaccount --text "Hello world!" --auto-approve

# Image post
python scripts/post.py --account myaccount --text "Nice photo!" --media photo.jpg --auto-approve

# Story
python scripts/test_story.py --cookie-file accounts/myaccount/cookies.json --media photo.jpg

# Reel
python scripts/test_reel.py --cookie-file accounts/myaccount/cookies.json --media video.mp4
```

---

## 📁 File Structure

```
facebook-personal-browser-post/
├── README.md
├── SKILL.md                          # AI-agent skill definition (Antigravity)
├── skills/
│   ├── claude-skill.md               # Claude (MCP tool definition)
│   ├── clawbot-skill.md              # Clawbot skill definition
│   └── openai-function.json          # OpenAI function calling spec
├── requirements.txt
├── config.example.json
├── accounts/
│   └── accounts.json                 # Account registry
├── proxies/
│   └── proxy-list.json               # Proxy registry
├── references/
│   ├── rotation-rules.json           # Proxy rotation policy
│   ├── selector-map.json             # Facebook DOM selectors
│   ├── selector-map.history.jsonl    # Selector change history
│   ├── run-log.jsonl                 # Run history
│   └── dom-capture-playbook.md       # How to re-learn selectors
└── scripts/
    ├── post.py                       # Main posting script
    ├── account_manager.py            # Manage accounts
    ├── proxy_manager.py              # Manage proxies
    ├── fingerprint_gen.py            # Browser fingerprint management
    ├── dom_learner.py                # DOM selector discovery
    ├── scheduler.py                  # Schedule daemon
    ├── test_all_formats.py           # Test all feed formats
    ├── test_story.py                 # Story test flow
    └── test_reel.py                  # Reel test flow
```

---

## 📋 CLI Reference

### `post.py` — Main Poster

```bash
python scripts/post.py --account <id> --text "Hello!" --auto-approve
python scripts/post.py --cookie-file cookies.json --text "Hello!" --auto-approve  # legacy

Options:
  --account ID          Account ID from accounts.json (recommended)
  --cookie-file PATH    Path to cookies.json (legacy mode)
  --text TEXT           Post text content
  --media PATH          Media file path (repeat for multiple)
  --link URL            URL to attach as link preview
  --schedule ISO8601    Schedule datetime (e.g. 2026-03-06T10:00:00+07:00)
  --dry-run             Preview only — never publishes
  --auto-approve        Skip approval prompt
  --headless            Run in headless mode
  --timeout INT         Per-action timeout in ms (default: 10000)
```

**Output contract:**
```
OK: published | url: https://www.facebook.com/<user>/posts/<id> | account: myaccount
OK: scheduled 2026-03-06T10:00:00+07:00
WAIT_APPROVAL
FAIL: DOM_CHANGED - All selectors failed — run dom_learner.py
FAIL: AUTH_REQUIRED - Session expired
FAIL: RATE_LIMIT - Facebook rate limit detected
FAIL: PUBLISH_FAILED - Retry exhausted
```

---

### `account_manager.py` — Account Management

```bash
python scripts/account_manager.py init   --id myaccount --cookies /path/to/cookies.json
python scripts/account_manager.py add    --id myaccount --name "My Name" --profile-url https://facebook.com/me
python scripts/account_manager.py list
python scripts/account_manager.py test   --id myaccount
python scripts/account_manager.py assign --id myaccount --proxy proxy_vn_01
python scripts/account_manager.py remove --id myaccount [--delete-files]
```

---

### `proxy_manager.py` — Proxy Management

```bash
python scripts/proxy_manager.py add     --host 1.2.3.4 --port 3128 --user u --pass p --country VN
python scripts/proxy_manager.py list
python scripts/proxy_manager.py test    --id proxy_vn_01
python scripts/proxy_manager.py health                    # Check all proxies
python scripts/proxy_manager.py rotate  --account myaccount
python scripts/proxy_manager.py remove  --id proxy_vn_01
```

---

### `fingerprint_gen.py` — Browser Fingerprint

```bash
python scripts/fingerprint_gen.py generate --account myaccount    # Stable/deterministic
python scripts/fingerprint_gen.py generate --account myaccount --random
python scripts/fingerprint_gen.py show     --account myaccount
python scripts/fingerprint_gen.py list
```

---

### `dom_learner.py` — Re-learn Selectors

```bash
# Run after Facebook updates its UI and posts start failing with DOM_CHANGED
python scripts/dom_learner.py --cookie-file cookies.json
```

---

### `scheduler.py` — Schedule Daemon

```bash
python scripts/scheduler.py --cookie-file cookies.json
python scripts/scheduler.py --cookie-file cookies.json --interval 60  # check every 60s
```

---

## 🔐 Multi-Account + Proxy Setup

```bash
# 1. Add account
python scripts/account_manager.py init --id acc_vn_01 --cookies cookies_vn01.json

# 2. Add proxy
python scripts/proxy_manager.py add --host 103.x.x.x --port 3128 --user u --pass p --country VN

# 3. Assign proxy to account
python scripts/account_manager.py assign --id acc_vn_01 --proxy proxy_103_x_x_x_3128

# 4. Test everything
python scripts/account_manager.py test --id acc_vn_01

# 5. Post via account (proxy + fingerprint auto-loaded)
python scripts/post.py --account acc_vn_01 --text "Hello!" --auto-approve
```

---

## 🧬 Browser Fingerprint Spoofing

Each account gets a **stable, deterministic fingerprint** generated from the account ID as seed:

| Property | Spoofed via |
|---|---|
| User-Agent | Playwright `user_agent=` |
| Viewport | Playwright `viewport=` |
| Locale | Playwright `locale=` |
| Timezone | Playwright `timezone_id=` |
| `navigator.platform` | `Object.defineProperty` override |
| `navigator.webdriver` | Set to `undefined` |
| WebGL vendor/renderer | `getParameter()` patch |
| Canvas fingerprint | Per-pixel noise injection |
| Audio context | AudioBuffer noise injection |

---

## ⚙️ Proxy Rotation Policy

Configured in `references/rotation-rules.json`:

```json
{
  "strategy": "sticky_per_account",
  "rotate_on_fail": true,
  "fail_threshold": 2,
  "blacklist_after_fails": 5,
  "cooldown_minutes": 30,
  "prefer_same_country": true,
  "fallback_to_direct": false
}
```

---

## 🛡️ Safety Rules

1. `--auto-approve` is **OFF by default** — every run stops at `WAIT_APPROVAL` without it
2. `--dry-run` **never publishes**, even with `--auto-approve`
3. `DOM_CHANGED` immediately halts — no partial publish
4. All cookies stay **local only** — never uploaded or shared
5. Personal profile only — **no Pages, Groups, or API**

---

## 📊 Error Codes

| Code | Meaning | Fix |
|---|---|---|
| `AUTH_REQUIRED` | Session invalid | Re-export cookies, run `account_manager.py init` |
| `DOM_CHANGED` | FB UI updated | Run `dom_learner.py` |
| `RATE_LIMIT` | FB throttle detected | Wait and retry later |
| `PUBLISH_FAILED` | Publish button click not confirmed | Check screenshot, retry |

---

## 📦 Requirements

```
playwright>=1.40.0
pytz>=2024.1
```

Python 3.11+ required.

---

## 🔬 Risk Factors & Account Safety Research

> **Research Purpose Only.** The following section documents behavioral signals that Facebook's
> automated systems use to detect non-human activity. This analysis is provided for **defensive
> research** — to understand how detection works so developers can build safer, more human-like
> automation for legitimate use cases (personal tools, accessibility, research).
> This is **not** a guide to evade moderation for malicious purposes.

---

### 1. 🌐 Network-Level Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **IP reputation** | 🔴 Very High | Datacenter IPs (AWS, DO, Vultr) are flagged immediately. Use residential or mobile proxies. |
| **IP geolocation mismatch** | 🟠 High | IP country ≠ account's historical country → suspicious. Always use same-country proxies. |
| **IP change frequency** | 🟠 High | Switching IP every session signals proxy rotation. `sticky_per_account` strategy mitigates this. |
| **IPv6 vs IPv4 inconsistency** | 🟡 Medium | Browser leaks IPv6 while proxy routes IPv4 → detectable. |
| **DNS leak** | 🟠 High | System DNS differs from proxy DNS → reveals VPN/proxy usage. |
| **ASN (Autonomous System)** | 🔴 Very High | Shared proxy ASN with other flagged accounts → guilt by association. |
| **Request timing from IP** | 🟡 Medium | Multiple accounts from same IP posting simultaneously → coordinated inauthentic behavior. |

---

### 2. 🖥️ Browser Fingerprint Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **`navigator.webdriver = true`** | 🔴 Very High | Default in headless Playwright/Selenium. **This skill patches it to `undefined`.** |
| **User-Agent mismatch** | 🔴 Very High | Headless Chrome UA (contains "HeadlessChrome") is an instant flag. Use a real UA. |
| **Viewport too small/unusual** | 🟠 High | `800x600` or `0x0` from headless → not human. Use realistic viewports (1366×768, 1920×1080, etc.). |
| **Screen vs viewport mismatch** | 🟡 Medium | `screen.width > viewport.width` is expected (taskbar). Equal values suggest headless. |
| **WebGL fingerprint** | 🟠 High | Headless has no GPU → `SWIFTSHADER` renderer is a known bot indicator. **This skill injects real GPU strings.** |
| **Canvas fingerprint** | 🟠 High | Identical canvas hashes across sessions → same bot. **This skill adds per-account pixel noise.** |
| **AudioContext fingerprint** | 🟡 Medium | Headless audio differs from real browser. **This skill adds AudioBuffer noise.** |
| **Font enumeration** | 🟡 Medium | Headless has fewer installed fonts. Difficult to fix without OS-level changes. |
| **Plugin list** | 🟡 Medium | Headless has 0 plugins. Real Chrome has 2+ (PDF Viewer, etc.). |
| **`navigator.languages` length** | 🟡 Medium | Headless often returns single-language array. **This skill sets `[vi-VN, en-US, en]`.** |
| **`navigator.hardwareConcurrency`** | 🟢 Low | Headless correctly inherits host CPU count. Usually fine. |
| **`navigator.deviceMemory`** | 🟢 Low | Reported as 8 in headless. Realistic. |
| **`window.chrome` object** | 🟠 High | Missing in headless Chromium by default. Facebook checks for this. |
| **CSS media features** | 🟡 Medium | `prefers-color-scheme`, `pointer: fine` help distinguish human vs bot. |
| **Permission states** | 🟡 Medium | Headless permissions behave differently than browser. |

---

### 3. ⏱️ Behavioral / Timing Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **Typing speed** | 🟠 High | Instantaneous `fill()` → bot. Use `type(delay=30)` for realistic keystroke timing. **This skill uses `el.type(text, delay=30)`.** |
| **Click precision** | 🟡 Medium | Automated clicks are pixel-perfect center. Real users click slightly off-center. |
| **Mouse movement (none)** | 🔴 Very High | Zero mouse movement before clicking is a classic bot signal. Consider `page.mouse.move()` before interactions. |
| **Scroll behavior** | 🟡 Medium | Real users scroll before reading and interacting. No scroll → suspicious. |
| **Time between actions** | 🟠 High | Actions under 500ms apart (open modal → immediately type) → not human. Add `wait_for_timeout()` between steps. |
| **Session duration** | 🟡 Medium | Sessions under 30 seconds performing complex tasks → bot. |
| **Tab focus** | 🟡 Medium | Headless tabs never gain/lose focus. Real users switch tabs. |
| **Paste events** | 🟡 Medium | Pasting a full post vs typing it differs in event sequence. `type()` simulates natural keystrokes. |
| **Posting frequency** | 🔴 Very High | >5-10 posts/day from automation patterns → high risk. Use `daily_post_limit` in `accounts.json`. |
| **Posting at exact intervals** | 🟠 High | Machine-perfect scheduling (every 60 minutes exactly) is unnatural. Add ±5-15 min jitter. |
| **Post content repetition** | 🔴 Very High | Identical or near-identical posts across accounts → coordinated inauthentic behavior policy. |

---

### 4. 🍪 Session & Cookie Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **Missing `fr` cookie** | 🔴 Very High | Facebook's main tracking cookie. Missing = suspicious or cleared. Ensure full cookie export. |
| **Cookie age** | 🟠 High | New cookies (account < 30 days old) + automation = high risk. |
| **Cookie domain scope** | 🟡 Medium | Missing `.facebook.com` domain cookies vs subdomain-specific ones. |
| **Cookie rotation** | 🟠 High | Cookies completely replaced between sessions → not organic. Use persistent profiles instead. |
| **`datr` cookie** | 🔴 Very High | Facebook's device tracking cookie set on first visit. Changing it = new device signal. |
| **Session persistence** | 🟢 Low | `launch_persistent_context` preserves all cookies naturally. **This skill uses persistent profiles.** |

---

### 5. 📍 Account-Level Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **Account age** | 🟠 High | New accounts + automation = immediate flag. Prefer accounts >6 months old. |
| **Profile completeness** | 🟡 Medium | Bare profiles (no photo, no friends) posting content → suspicious. |
| **Friend activity** | 🟡 Medium | Accounts with no friend interactions posting frequently → unusual. |
| **Historical posting pattern** | 🟠 High | Sudden jump from 0 posts/month to 20+ posts/month → anomaly. |
| **Login history** | 🟠 High | Account always logged in from same IP/device except suddenly in automation context. |
| **Two-factor authentication** | 🟢 Low | 2FA-protected accounts are less likely to be flagged (shows real ownership). |
| **Account associations** | 🔴 Very High | Multiple accounts from same device/IP = linked accounts policy violation. |

---

### 6. 📝 Content-Level Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **Spam patterns in text** | 🔴 Very High | URLs, hashtag spam, promotional language → NLP spam classification. |
| **Duplicate content** | 🔴 Very High | Same image hash or text across multiple posts/accounts → content policy. |
| **Image metadata (EXIF)** | 🟡 Medium | AI-generated images lack EXIF data. Photos from same camera every time → suspicious uniformity. |
| **Video encoding signature** | 🟡 Medium | Same video re-uploaded → duplicate detection hash. |
| **External link reputation** | 🟠 High | Links to flagged domains → immediate content review. |
| **Mention/tag spam** | 🟠 High | Tagging many users not in friend list → report trigger. |
| **Engagement rate anomaly** | 🟡 Medium | Posts with 0 engagement despite active posting → low trust score. |

---

### 7. 🏗️ Infrastructure Signals

| Signal | Risk Level | Notes |
|---|---|---|
| **Headless flag in HTTP headers** | 🔴 Very High | `Sec-CH-UA` header includes `"Headless"`. Must be overridden. |
| **Automation tool detection via CDP** | 🔴 Very High | Chrome DevTools Protocol (CDP) connection = Playwright/Selenium signature. Use stealth patches. |
| **`X-Forwarded-For` header leaks** | 🟠 High | Some proxies forward real IP in headers. Use anonymous proxies only. |
| **TLS fingerprint (JA3)** | 🟡 Medium | Playwright's TLS handshake differs from real Chrome. Advanced detection only. |
| **HTTP/2 fingerprint** | 🟡 Medium | Browser-level HTTP/2 settings (HPACK, priorities) differ across clients. |
| **Request ordering** | 🟡 Medium | Bots often skip sub-resource requests (fonts, tracking pixels) that real browsers load. |

---

### 8. ✅ Mitigations Implemented in This Skill

| Risk | Mitigation |
|---|---|
| `webdriver` flag | Patched to `undefined` via init script |
| WebGL bot signature | Real GPU vendor/renderer injected per account |
| Canvas fingerprint | Per-account pixel noise added |
| Audio fingerprint | Per-account AudioBuffer noise |
| User-Agent headless | Real Chrome/Edge/Firefox UA per account |
| Typing speed | `el.type(delay=30)` for natural keystrokes |
| IP risk | Per-account sticky proxy with health checks |
| Session persistence | `launch_persistent_context` preserves cookies |
| Posting frequency | `daily_post_limit` per account in `accounts.json` |
| Fingerprint stability | Deterministic seed → same fingerprint every session |

---

### 9. ⚠️ Remaining Risks (Not Yet Mitigated)

| Risk | Difficulty | Recommendation |
|---|---|---|
| Mouse movement | Medium | Add `page.mouse.move(x, y)` before each click |
| `window.chrome` object | Medium | Inject `window.chrome = { runtime: {} }` in init script |
| Scroll before interact | Easy | Add `page.evaluate("window.scrollBy(0, 300)")` on page load |
| Posting time jitter | Easy | Add `random.uniform(-900, 900)` seconds to scheduled times |
| TLS/JA3 fingerprint | Hard | Use real Chrome binary instead of Playwright Chromium |
| CDP detection | Hard | Use `playwright-extra` + `puppeteer-extra-plugin-stealth` port |
| Font list | Hard | Requires OS-level font installation matching real Windows install |

---

## ⚠️ Disclaimer

This tool automates a browser session on your personal Facebook account for **research and
personal productivity purposes only**. The risk analysis above is provided for educational
understanding of how platform integrity systems work — not to circumvent them maliciously.

Use responsibly and in accordance with [Facebook's Terms of Service](https://www.facebook.com/terms).
The authors are not responsible for any account restrictions that may result from use of this tool.

---

## License

MIT
