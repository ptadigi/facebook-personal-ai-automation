#!/usr/bin/env python3
"""
facebook-personal-browser-post — Main posting script
Posts text, images, videos, and links to a personal Facebook profile via Playwright.

Usage:
  python scripts/post.py --cookie-file cookies.json --text "Hello!" [OPTIONS]

Output contract (single line to stdout):
  OK: published | url: https://www.facebook.com/...
  OK: scheduled <ISO8601>
  WAIT_APPROVAL
  FAIL: <ERROR_CODE> - <reason>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

__version__ = "2.1.0"

# ---------------------------------------------------------------------------
# Paths (relative to this script's parent directory = skill root)
# ---------------------------------------------------------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SELECTOR_MAP = SKILL_ROOT / "references" / "selector-map.json"
DEFAULT_RUN_LOG = SKILL_ROOT / "references" / "run-log.jsonl"

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------
AUTH_REQUIRED = "AUTH_REQUIRED"
DOM_CHANGED = "DOM_CHANGED"
RATE_LIMIT = "RATE_LIMIT"
PUBLISH_FAILED = "PUBLISH_FAILED"

# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------
RETRY_BACKOFFS = [0, 2, 5]   # wait before attempt 1 / 2 / 3
MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log_event(
    run_log_path: Path,
    phase: str,
    status: str,
    note: str,
    error_code: str | None = None,
    *,
    run_id: str = "",
    account_id: str = "",
    url: str | None = None,
):
    """P2-2: Append a structured JSON line to run-log.jsonl with run_id + account_id trace."""
    record = {
        "timestamp":  _now_iso(),
        "version":    __version__,
        "run_id":     run_id,
        "account_id": account_id,
        "phase":      phase,
        "status":     status,
        "note":       note,
        "error_code": error_code,
        "url":        url,
    }
    try:
        run_log_path.parent.mkdir(parents=True, exist_ok=True)
        with run_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        # P2-3: log rotation — keep last 2000 lines to prevent unbounded growth
        _rotate_log_if_needed(run_log_path, max_lines=2000)
    except Exception as exc:
        print(f"[WARN] Could not write to run log: {exc}", file=sys.stderr)


def _rotate_log_if_needed(path: Path, max_lines: int = 2000) -> None:
    """P2-3: Trim run-log.jsonl to the most recent max_lines entries."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if len(lines) > max_lines:
            path.write_text("".join(lines[-max_lines:]), encoding="utf-8")
    except Exception:
        pass  # rotation is best-effort


def fail(msg: str, error_code: str, run_log: Path):
    log_event(run_log, "error", "fail", msg, error_code=error_code)
    print(f"FAIL: {error_code} - {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Selector loading
# ---------------------------------------------------------------------------

def load_selectors(selector_map_path: Path) -> dict:
    try:
        with selector_map_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("selectors", {})
    except Exception as exc:
        raise RuntimeError(f"Cannot load selector map: {exc}") from exc


def try_selector(page, action: str, selectors: dict, timeout: int = 5000):
    """
    Try primary + fallbacks for an action. Returns (locator, selector_used) or raises DOM_CHANGED.
    """
    entry = selectors.get(action)
    if not entry:
        raise ValueError(f"No selector entry for action: {action}")

    candidates = [entry["primary"]] + entry.get("fallbacks", [])
    for sel in candidates:
        try:
            if sel.startswith("//"):
                # XPath
                loc = page.locator(f"xpath={sel}")
            else:
                loc = page.locator(sel)
            loc.first.wait_for(state="visible", timeout=timeout)
            return loc.first, sel
        except Exception:
            continue
    raise RuntimeError(DOM_CHANGED)


# ---------------------------------------------------------------------------
# Cookie injection
# ---------------------------------------------------------------------------

def load_cookies(cookie_file: str) -> list[dict]:
    """Load cookies from a JSON file (Cookie-Editor export format or Playwright format)."""
    path = Path(cookie_file)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Support both flat list and {"cookies": [...]} wrapper
    if isinstance(data, dict) and "cookies" in data:
        cookies = data["cookies"]
    elif isinstance(data, list):
        cookies = data
    else:
        raise ValueError("Unrecognised cookie format. Expected list or {'cookies': [...]}")
    return cookies


def inject_cookies(context, cookies: list[dict]):
    """Add cookies to a Playwright browser context, normalising common export formats."""
    pw_cookies = []
    for c in cookies:
        pw_c = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".facebook.com"),
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
        }
        # sameSite must be one of Strict, Lax, None — default None
        raw_ss = c.get("sameSite", "None")
        pw_c["sameSite"] = raw_ss if raw_ss in ("Strict", "Lax", "None") else "None"
        if c.get("expirationDate"):
            pw_c["expires"] = int(c["expirationDate"])
        elif c.get("expires"):
            pw_c["expires"] = int(c["expires"])
        pw_cookies.append(pw_c)
    context.add_cookies(pw_cookies)


# ---------------------------------------------------------------------------
# Auth verification
# ---------------------------------------------------------------------------

def verify_auth(page, run_log: Path) -> bool:
    """Return True if logged in, False if redirected to login."""
    page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
    url = page.url
    if "login" in url or "checkpoint" in url:
        log_event(run_log, "auth", "fail", "Redirected to login/checkpoint", AUTH_REQUIRED)
        return False
    log_event(run_log, "auth", "ok", "Session verified")
    return True


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------

def open_composer(page, selectors: dict, timeout: int, run_log: Path):
    """Click the 'What's on your mind?' area to open the composer dialog."""
    log_event(run_log, "compose", "ok", "Opening composer")
    try:
        el, sel = try_selector(page, "open_composer", selectors, timeout)
        el.click()
        page.wait_for_timeout(1500)
        log_event(run_log, "compose", "ok", f"Composer opened via: {sel}")
    except RuntimeError:
        raise


def enter_text(page, text: str, selectors: dict, timeout: int, run_log: Path):
    """Type text into the composer text area."""
    if not text:
        return
    log_event(run_log, "compose", "ok", "Entering text")
    el, sel = try_selector(page, "text_input", selectors, timeout)
    el.click()
    el.type(text, delay=30)
    log_event(run_log, "compose", "ok", f"Text entered via: {sel}")


def attach_media(page, media_paths: list[str], selectors: dict, timeout: int, run_log: Path):
    """Attach one or more image/video files to the post."""
    if not media_paths:
        return
    log_event(run_log, "compose", "ok", f"Attaching {len(media_paths)} media file(s)")

    # Click the media button to reveal the file input
    try:
        btn, sel = try_selector(page, "media_button", selectors, timeout)
        btn.click()
        page.wait_for_timeout(1000)
        log_event(run_log, "compose", "ok", f"Media button clicked via: {sel}")
    except RuntimeError:
        raise  # DOM_CHANGED

    # Use file_input selector to upload
    try:
        inp, sel = try_selector(page, "file_input", selectors, timeout)
        inp.set_input_files(media_paths)
        log_event(run_log, "compose", "ok", f"Media files set via: {sel}")
    except RuntimeError:
        raise  # DOM_CHANGED

    # Bug fix: wait for upload to actually process before continuing.
    # Images: thumbnail appears quickly (~2s). Videos: encoding takes longer (~10s).
    has_video = any(p.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")) for p in media_paths)
    upload_wait_ms = 10000 if has_video else 3000
    log_event(run_log, "compose", "ok", f"Waiting {upload_wait_ms}ms for media upload to process...")
    page.wait_for_timeout(upload_wait_ms)


# ---------------------------------------------------------------------------
# Schedule UI
# ---------------------------------------------------------------------------

def open_schedule_ui(page, selectors: dict, timeout: int, run_log: Path):
    """Open the schedule post panel in the composer."""
    log_event(run_log, "schedule", "ok", "Opening schedule UI")
    el, sel = try_selector(page, "schedule_entry", selectors, timeout)
    el.click()
    page.wait_for_timeout(1000)
    log_event(run_log, "schedule", "ok", f"Schedule entry clicked via: {sel}")


def fill_schedule_datetime(page, schedule_iso: str, timezone: str, run_log: Path):
    """
    Fill in the date/time pickers in the Facebook scheduling dialog.
    FB's date/time inputs are highly variable — this attempts to fill them
    via visible input fields or by typing directly.
    """
    from datetime import timezone as dt_tz
    try:
        import pytz
        tz = pytz.timezone(timezone)
        dt_naive = datetime.fromisoformat(schedule_iso.replace("Z", "+00:00"))
        dt_local = dt_naive.astimezone(tz)
    except Exception:
        dt_local = datetime.fromisoformat(schedule_iso)

    log_event(run_log, "schedule", "ok", f"Scheduling for: {dt_local.isoformat()}")

    # Try to find date / time inputs inside the dialog
    dialog = page.locator("div[role='dialog']")
    # Fill date field
    date_str = dt_local.strftime("%m/%d/%Y")
    time_str = dt_local.strftime("%I:%M %p")

    for input_sel in ["input[type='date']", "input[placeholder*='date' i]", "input[aria-label*='date' i]"]:
        inp = dialog.locator(input_sel)
        if inp.count() > 0:
            inp.first.fill(date_str)
            break

    for input_sel in ["input[type='time']", "input[placeholder*='time' i]", "input[aria-label*='time' i]"]:
        inp = dialog.locator(input_sel)
        if inp.count() > 0:
            inp.first.fill(time_str)
            break

    page.wait_for_timeout(500)


def confirm_schedule(page, selectors: dict, timeout: int, run_log: Path):
    """Click the confirm/Schedule button in the scheduling dialog."""
    el, sel = try_selector(page, "schedule_confirm", selectors, timeout)
    el.click()
    page.wait_for_timeout(1500)
    log_event(run_log, "schedule", "ok", f"Schedule confirmed via: {sel}")


# ---------------------------------------------------------------------------
# Publish with retry
# ---------------------------------------------------------------------------

def publish_post(page, selectors: dict, timeout: int, run_log: Path) -> bool:
    """
    Click the Post/Publish button with retry logic.
    Returns True on success, raises on final failure.
    """
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        wait = RETRY_BACKOFFS[attempt]
        if wait > 0:
            log_event(run_log, "publish", "retry", f"Waiting {wait}s before attempt {attempt + 1}")
            time.sleep(wait)

        try:
            btn, sel = try_selector(page, "publish_button", selectors, timeout)
            btn.click()
            # Wait for post confirmation: composer should close or a confirmation shown
            page.wait_for_timeout(3000)

            # Simple heuristic: if the composer dialog is gone, assume success
            dialog = page.locator("div[role='dialog']")
            if dialog.count() == 0:
                log_event(run_log, "publish", "ok", f"Post published (attempt {attempt + 1}) via: {sel}")
                return True

            # Try to detect error / rate limit in page text
            page_text = page.inner_text("body")
            if "limit" in page_text.lower() or "temporarily blocked" in page_text.lower():
                raise RuntimeError(RATE_LIMIT)

            # Composer still open — treat as failure, retry
            last_error = "Composer still open after clicking Post"

        except RuntimeError as exc:
            err_str = str(exc)
            if DOM_CHANGED in err_str:
                raise  # Propagate immediately — no retry
            if RATE_LIMIT in err_str:
                log_event(run_log, "publish", "fail", "Rate limit detected", RATE_LIMIT)
                raise RuntimeError(RATE_LIMIT)
            last_error = err_str

    raise RuntimeError(f"{PUBLISH_FAILED}: {last_error}")


# ---------------------------------------------------------------------------
# Extract post URL after publish
# ---------------------------------------------------------------------------

def extract_post_url(page) -> str | None:
    """
    P2-6: After publishing, poll for up to 10s for the newest post permalink.

    Strategy:
    1. Poll every 1s for up to 10s for feed links matching /posts/, /permalink/, etc.
    2. Fallback: return current page URL if it contains a post identifier.
    """
    post_link_patterns = [
        "a[href*='/posts/']",
        "a[href*='/permalink/']",
        "a[href*='story_fbid']",
        "a[href*='/videos/']",
        "a[href*='/photo/']",
    ]
    keywords = ["/posts/", "/permalink/", "story_fbid", "/videos/", "/photo/"]

    deadline = time.time() + 10  # poll for up to 10 seconds
    while time.time() < deadline:
        try:
            for pattern in post_link_patterns:
                links = page.query_selector_all(pattern)
                for link in links:
                    href = link.get_attribute("href") or ""
                    if any(kw in href for kw in keywords):
                        if href.startswith("/"):
                            href = "https://www.facebook.com" + href
                        return href.split("?")[0] if "story_fbid" not in href else href

            # Fallback: check current URL
            current = page.url
            if any(kw in current for kw in keywords):
                return current
        except Exception:
            pass
        time.sleep(1)

    return None  # URL not found after 10s polling


def extract_story_url(page, username: str = "") -> str | None:
    """
    After Story publish, FB redirects to /stories.
    Try to find the user's own story URL or return the /stories page URL.
    """
    try:
        current = page.url
        if "/stories" in current:
            # Try to find a link to the user's own story
            own_story = page.query_selector("a[href*='/stories/'][role='link']")
            if own_story:
                href = own_story.get_attribute("href") or ""
                if href.startswith("/"):
                    href = "https://www.facebook.com" + href
                return href
            # Return generic stories URL
            return "https://www.facebook.com/stories" + (f"/{username}" if username else "")
        return current
    except Exception:
        return None


def extract_reel_url(page, username: str = "") -> str | None:
    """
    After Reel publish, FB returns to the profile/reels page.
    Try to find the newest reel link.
    """
    try:
        # Look for reel permalinks on the page
        reel_links = page.query_selector_all("a[href*='/reel/']")
        if reel_links:
            href = reel_links[0].get_attribute("href") or ""
            if href.startswith("/"):
                href = "https://www.facebook.com" + href
            return href
        current = page.url
        return current if "reel" in current else f"https://www.facebook.com/{username}/reels/"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Approval / preview
# ---------------------------------------------------------------------------

def build_preview(args) -> dict:
    return {
        "preview_timestamp": _now_iso(),
        "action": "schedule" if args.schedule else "publish",
        "text": args.text or "",
        "media": args.media or [],
        "link": args.link or None,
        "schedule": args.schedule or None,
        "dry_run": args.dry_run,
        "auto_approve": args.auto_approve,
    }


def request_approval(preview: dict) -> bool:
    """
    Print the preview payload and ask user to approve via stdin.
    Returns True if approved.
    """
    print("\n" + "=" * 60)
    print("POST PREVIEW — Review before publishing:")
    print("=" * 60)
    print(json.dumps(preview, indent=2, ensure_ascii=False))
    print("=" * 60)
    try:
        answer = input("Approve and publish? [y/N]: ").strip().lower()
        return answer in ("y", "yes")
    except EOFError:
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Post to Facebook personal profile via browser automation."
    )
    # Account-based mode (recommended)
    p.add_argument("--account", default=None,
                   help="Account ID from accounts.json (e.g. pham_thanh). Loads proxy+fingerprint automatically.")
    # Legacy mode (direct cookie file, no proxy/fingerprint)
    p.add_argument("--cookie-file", default=None,
                   help="Path to cookies JSON (legacy mode — use --account instead)")
    # Content
    p.add_argument("--text", default="", help="Post text content")
    p.add_argument("--media", action="append", default=[], metavar="PATH",
                   help="Media file path (repeat for multiple)")
    p.add_argument("--link", default=None, help="URL to attach as link preview")
    p.add_argument("--schedule", default=None, metavar="ISO8601",
                   help="Schedule datetime (e.g. 2026-03-06T10:00:00+07:00)")
    p.add_argument("--dry-run", action="store_true",
                   help="Compose but do NOT publish — always outputs WAIT_APPROVAL")
    p.add_argument("--auto-approve", action="store_true",
                   help="Skip approval prompt and publish immediately")
    p.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    p.add_argument("--timeout", type=int, default=10000, help="Per-action timeout in ms")
    p.add_argument("--selector-map", default=str(DEFAULT_SELECTOR_MAP))
    p.add_argument("--run-log", default=str(DEFAULT_RUN_LOG))
    p.add_argument("--timezone", default=os.environ.get("TZ", "Asia/Ho_Chi_Minh"))
    args = p.parse_args()
    if not args.account and not args.cookie_file:
        p.error("Either --account or --cookie-file is required")
    return args


# ---------------------------------------------------------------------------
# Multi-account helpers
# ---------------------------------------------------------------------------

def load_account_config(account_id: str) -> dict:
    """Load account entry from accounts/accounts.json."""
    accounts_file = SKILL_ROOT / "accounts" / "accounts.json"
    if not accounts_file.exists():
        raise FileNotFoundError(f"accounts.json not found: {accounts_file}")
    with accounts_file.open(encoding="utf-8") as f:
        data = json.load(f)
    account = next((a for a in data["accounts"] if a["id"] == account_id), None)
    if not account:
        raise ValueError(f"Account '{account_id}' not found in accounts.json")
    return account


def load_fingerprint(account: dict) -> dict | None:
    """Load saved fingerprint for an account."""
    fp_path = SKILL_ROOT / account["fingerprint_path"]
    if not fp_path.exists():
        return None
    with fp_path.open(encoding="utf-8") as f:
        return json.load(f)


def load_proxy_config(account: dict) -> dict | None:
    """Load proxy settings for an account and return Playwright proxy dict."""
    proxy_id = account.get("proxy_id")
    if not proxy_id:
        return None
    proxies_file = SKILL_ROOT / "proxies" / "proxy-list.json"
    if not proxies_file.exists():
        return None
    with proxies_file.open(encoding="utf-8") as f:
        data = json.load(f)
    proxy = next((p for p in data["proxies"] if p["id"] == proxy_id), None)
    if not proxy:
        return None
    ptype = proxy.get("type", "http")
    pw_proxy = {"server": f"{ptype}://{proxy['host']}:{proxy['port']}"}
    if proxy.get("username"):
        pw_proxy["username"] = proxy["username"]
        pw_proxy["password"] = proxy.get("password", "")
    return pw_proxy


def build_init_script_from_fp(fp: dict) -> str:
    """Build JS init script for fingerprint spoofing from fingerprint.json."""
    try:
        from scripts.fingerprint_gen import build_init_script
        return build_init_script(fp)
    except ImportError:
        pass
    # Inline minimal version if fingerprint_gen not importable
    webgl_v = fp.get("webgl_vendor", "Google Inc. (Intel)")
    webgl_r = fp.get("webgl_renderer", "ANGLE (Intel, Intel(R) UHD Graphics)")
    platform = fp.get("platform", "Win32")
    canvas_noise = fp.get("canvas_noise", 0.0001)
    return f"""
    (() => {{
        const overrideProp = (obj, prop, value) => {{
            try {{ Object.defineProperty(obj, prop, {{ get: () => value, configurable: true }}); }} catch(e) {{}}
        }};
        overrideProp(navigator, 'platform', '{platform}');
        overrideProp(navigator, 'webdriver', undefined);
        const origGetParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(p) {{
            if (p === 37445) return '{webgl_v}';
            if (p === 37446) return '{webgl_r}';
            return origGetParam.call(this, p);
        }};
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                const d = ctx.getImageData(0,0,this.width,this.height);
                for (let i=0;i<d.data.length;i+=4) d.data[i] += Math.floor({canvas_noise}*255*(Math.random()-.5));
                ctx.putImageData(d,0,0);
            }}
            return origToDataURL.apply(this,args);
        }};
    }})();
    """


def update_account_stats(account_id: str, post_url: str | None = None):
    """Update last_post timestamp and daily_post_count after a successful post.
    Resets daily_post_count to 0 if the last post was on a previous calendar day.
    """
    try:
        accounts_file = SKILL_ROOT / "accounts" / "accounts.json"
        with accounts_file.open(encoding="utf-8") as f:
            data = json.load(f)
        today = datetime.now().astimezone().date().isoformat()
        for acc in data["accounts"]:
            if acc["id"] == account_id:
                # Bug fix: reset counter if it's a new day
                last_post = acc.get("last_post") or ""
                last_post_date = last_post[:10] if last_post else ""
                if last_post_date != today:
                    acc["daily_post_count"] = 0
                acc["last_post"] = _now_iso()
                acc["daily_post_count"] = acc.get("daily_post_count", 0) + 1
                if post_url:
                    acc["last_post_url"] = post_url
                break
        data["updated_at"] = _now_iso()
        accounts_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as exc:
        # Fix 5: don't silently swallow write failures — warn so operators can investigate
        log_event(run_log, "stats", "warn", f"Failed to update account stats: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    run_log = Path(args.run_log)
    selector_map_path = Path(args.selector_map)

    # ── Resolve account vs legacy cookie-file mode ─────────────────────────
    account_id = None
    account_cfg = None
    fp = None
    proxy_config = None
    use_persistent_profile = False
    profile_dir = None

    if args.account:
        try:
            account_cfg = load_account_config(args.account)
        except Exception as exc:
            fail(str(exc), AUTH_REQUIRED, run_log)

        account_id = account_cfg["id"]
        fp = load_fingerprint(account_cfg)
        proxy_config = load_proxy_config(account_cfg)

        # Check if persistent profile exists
        profile_dir = SKILL_ROOT / account_cfg["profile_dir"]
        profile_dir.mkdir(parents=True, exist_ok=True)
        use_persistent_profile = any(profile_dir.iterdir()) if profile_dir.exists() else False

        # Fall back to cookies path from account config
        if not args.cookie_file:
            args.cookie_file = str(SKILL_ROOT / account_cfg["cookies_path"])

        log_event(run_log, "startup", "ok",
                  f"post.py | account={account_id} | proxy={'yes' if proxy_config else 'no'} "
                  f"| fp={'yes' if fp else 'no'} | profile={'persistent' if use_persistent_profile else 'cookies'}")
    else:
        log_event(run_log, "startup", "ok",
                  f"post.py | legacy mode | dry_run={args.dry_run} | schedule={args.schedule}")

    # ── Load selectors ─────────────────────────────────────────────────────
    try:
        selectors = load_selectors(selector_map_path)
    except Exception as exc:
        fail(str(exc), DOM_CHANGED, run_log)

    # ── Load cookies (always needed for first-run or legacy) ───────────────
    cookies = []
    if not use_persistent_profile:
        try:
            cookies = load_cookies(args.cookie_file)
        except Exception as exc:
            fail(str(exc), AUTH_REQUIRED, run_log)

    # ── Approval flow ──────────────────────────────────────────────────────
    preview = build_preview(args)

    if args.dry_run:
        log_event(run_log, "approval", "skipped", "Dry-run mode")
        print("\n" + "=" * 60)
        print("DRY-RUN — Post preview (nothing will be published):")
        print("=" * 60)
        if account_id:
            preview["account"] = account_id
            if proxy_config:
                preview["proxy"] = proxy_config.get("server")
            if fp:
                preview["fingerprint"] = {"browser": fp["browser"], "ua": fp["user_agent"][:60]}
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        print("=" * 60)
        print("WAIT_APPROVAL")
        sys.exit(0)

    if not args.auto_approve:
        approved = request_approval(preview)
        if not approved:
            log_event(run_log, "approval", "skipped", "User did not approve")
            print("WAIT_APPROVAL")
            sys.exit(0)
    else:
        log_event(run_log, "approval", "ok", "Auto-approved")

    # ── Launch Playwright ──────────────────────────────────────────────────
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("Playwright not installed. Run: pip install playwright && playwright install chromium",
             AUTH_REQUIRED, run_log)

    with sync_playwright() as pw:

        # ── Build context options from fingerprint ─────────────────────────
        if fp:
            ctx_opts = {
                "viewport": fp["viewport"],
                "user_agent": fp["user_agent"],
                "locale": fp["locale"],
                "timezone_id": fp["timezone_id"],
                "device_scale_factor": fp.get("device_scale_factor", 1),
                "color_scheme": fp.get("color_scheme", "light"),
            }
        else:
            ctx_opts = {
                "viewport": {"width": 1280, "height": 800},
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "locale": "vi-VN",
                "timezone_id": "Asia/Ho_Chi_Minh",
            }

        if proxy_config:
            ctx_opts["proxy"] = proxy_config
            log_event(run_log, "proxy", "ok", f"Using proxy: {proxy_config['server']}")

        # ── Launch: persistent profile or fresh context ────────────────────
        if use_persistent_profile and account_cfg:
            log_event(run_log, "browser", "ok", f"Using persistent profile: {profile_dir}")
            context = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=args.headless,
                **ctx_opts
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(**ctx_opts)

            # Inject fingerprint JS overrides
            if fp:
                init_js = build_init_script_from_fp(fp)
                context.add_init_script(init_js)
                log_event(run_log, "fingerprint", "ok",
                          f"Injected: UA={fp['user_agent'][:40]}... | WebGL={fp['webgl_vendor']}")

            # Inject cookies
            try:
                inject_cookies(context, cookies)
            except Exception as exc:
                context.close()
                fail(str(exc), AUTH_REQUIRED, run_log)

            page = context.new_page()

        # ── Auth check ─────────────────────────────────────────────────────
        if not verify_auth(page, run_log):
            context.close()
            fail("Could not verify login after cookie injection", AUTH_REQUIRED, run_log)

        # ── Compose ────────────────────────────────────────────────────────
        try:
            open_composer(page, selectors, args.timeout, run_log)
            enter_text(page, args.text, selectors, args.timeout, run_log)
            if args.media:
                attach_media(page, args.media, selectors, args.timeout, run_log)
        except RuntimeError as exc:
            context.close()
            if DOM_CHANGED in str(exc):
                fail("All selectors failed — run dom_learner.py to update", DOM_CHANGED, run_log)
            fail(str(exc), PUBLISH_FAILED, run_log)

        # ── Schedule or Publish ────────────────────────────────────────────
        if args.schedule:
            try:
                open_schedule_ui(page, selectors, args.timeout, run_log)
                fill_schedule_datetime(page, args.schedule, args.timezone, run_log)
                confirm_schedule(page, selectors, args.timeout, run_log)
                context.close()
                log_event(run_log, "schedule", "ok", f"Post scheduled for {args.schedule}")
                print(f"OK: scheduled {args.schedule}")
                sys.exit(0)
            except RuntimeError as exc:
                context.close()
                if DOM_CHANGED in str(exc):
                    fail("DOM_CHANGED during scheduling", DOM_CHANGED, run_log)
                fail(str(exc), PUBLISH_FAILED, run_log)
        else:
            try:
                publish_post(page, selectors, args.timeout, run_log)
                post_url = extract_post_url(page)
                context.close()
                # Update account stats
                if account_id:
                    update_account_stats(account_id, post_url)
                url_part = f" | url: {post_url}" if post_url else ""
                account_part = f" | account: {account_id}" if account_id else ""
                log_event(run_log, "publish", "ok", f"Published{url_part}{account_part}")
                print(f"OK: published{url_part}{account_part}")
                sys.exit(0)
            except RuntimeError as exc:
                context.close()
                err_str = str(exc)
                if RATE_LIMIT in err_str:
                    fail("Facebook rate limit detected", RATE_LIMIT, run_log)
                if DOM_CHANGED in err_str:
                    fail("DOM_CHANGED during publish — run dom_learner.py", DOM_CHANGED, run_log)
                fail(err_str, PUBLISH_FAILED, run_log)


if __name__ == "__main__":
    main()
