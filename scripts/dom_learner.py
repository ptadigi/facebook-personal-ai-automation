#!/usr/bin/env python3
"""
dom_learner.py — DOM selector discovery and update tool.

Launches a browser with your Facebook cookies, navigates to Facebook,
and probes each action step to discover working selectors. Updates
references/selector-map.json and appends changes to
references/selector-map.history.jsonl.

Usage:
  python scripts/dom_learner.py --cookie-file cookies.json [--headless] [--interactive]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

__version__ = "2.1.0"

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SELECTOR_MAP = SKILL_ROOT / "references" / "selector-map.json"
DEFAULT_HISTORY = SKILL_ROOT / "references" / "selector-map.history.jsonl"

# ---------------------------------------------------------------------------
# Probe configurations: each action has candidate selectors in priority order.
# Priority: 1=aria/role, 2=data-*, 3=text, 4=xpath
# ---------------------------------------------------------------------------

PROBE_CANDIDATES: dict[str, list[str]] = {
    "open_composer": [
        "[aria-label=\"What's on your mind?\"]",
        "[data-testid='status-attachment-mentions-input']",
        "div[role='button']:has-text(\"What's on your mind\")",
        "//div[@role='button'][contains(., \"What's on your mind\")]",
    ],
    "text_input": [
        "div[contenteditable='true'][role='textbox']",
        "[data-testid='react-composer-root'] div[contenteditable='true']",
        "[aria-label*='post'][contenteditable='true']",
        "//div[@role='textbox' and @contenteditable='true']",
    ],
    "media_button": [
        "[aria-label='Photo/video']",
        "[aria-label='Photo']",
        "[data-testid='photo-video-button']",
        "div[role='button'][aria-label*='Photo']",
        "//div[@role='button'][contains(@aria-label,'Photo')]",
    ],
    "file_input": [
        "input[type='file'][accept*='image']",
        "input[type='file'][accept*='video']",
        "input[type='file']",
        "//input[@type='file']",
    ],
    "schedule_entry": [
        "[aria-label='Schedule post']",
        "[aria-label*='Schedule']",
        "div[role='menuitem']:has-text('Schedule')",
        "div[role='button']:has-text('Schedule post')",
        "//div[@role='menuitem'][contains(.,'Schedule')]",
    ],
    "publish_button": [
        "div[aria-label='Post'][role='button']",
        "[data-testid='react-composer-post-button']",
        "div[role='button']:has-text('Post')",
        "//div[@role='button'][@aria-label='Post']",
    ],
    "schedule_confirm": [
        "div[role='dialog'] div[role='button'][aria-label='Schedule']",
        "div[role='dialog'] div[role='button']:has-text('Schedule')",
        "[data-testid='schedule-confirm-button']",
        "//div[@role='dialog']//div[@role='button'][contains(.,'Schedule')]",
    ],
}

# Actions that require the composer to be open first
REQUIRES_COMPOSER = {"text_input", "media_button", "schedule_entry", "publish_button", "schedule_confirm"}
# Actions probed after opening schedule panel
REQUIRES_SCHEDULE_PANEL = {"schedule_confirm"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_cookies(cookie_file: str) -> list[dict]:
    path = Path(cookie_file)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cookies" in data:
        return data["cookies"]
    return data


def load_fingerprint(account_id: str | None) -> dict | None:
    """
    P2-5: Load saved fingerprint for an account so dom_learner can use
    the real account UA/viewport instead of the default headless signature.
    Returns None if no fingerprint file is found.
    """
    if not account_id:
        return None
    fp_path = SKILL_ROOT / "accounts" / account_id / "fingerprint.json"
    if not fp_path.exists():
        return None
    try:
        with fp_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def inject_cookies(context, cookies: list[dict]):
    pw_cookies = []
    for c in cookies:
        pw_c = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ".facebook.com"),
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", "None") if c.get("sameSite") in ("Strict", "Lax", "None") else "None",
        }
        if c.get("expirationDate"):
            pw_c["expires"] = int(c["expirationDate"])
        pw_cookies.append(pw_c)
    context.add_cookies(pw_cookies)


def probe_action(page, action: str, candidates: list[str], timeout: int = 5000) -> tuple[str | None, list[str]]:
    """
    Probe each candidate selector for an action.
    Returns (working_primary, working_fallbacks) or (None, []) if none found.
    """
    working = []
    for sel in candidates:
        try:
            if sel.startswith("//"):
                loc = page.locator(f"xpath={sel}")
            else:
                loc = page.locator(sel)
            loc.first.wait_for(state="attached", timeout=timeout)
            working.append(sel)
        except Exception:
            pass

    if working:
        return working[0], working[1:]
    return None, []


def load_existing_map(map_path: Path) -> dict:
    if map_path.exists():
        with map_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "1.0.0",
        "updated_at": _now_iso(),
        "selectors": {},
    }


def bump_version(version: str) -> str:
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def save_selector_map(map_path: Path, data: dict):
    map_path.parent.mkdir(parents=True, exist_ok=True)
    with map_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def append_history(history_path: Path, record: dict):
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Discover and update Facebook DOM selectors")
    parser.add_argument("--cookie-file", required=True, help="Path to Facebook session cookie JSON")
    parser.add_argument("--account", default=None,
                        help="P2-5: Account ID to load fingerprint from (e.g. pham_thanh). "
                             "Uses account UA/viewport instead of default headless signature.")
    parser.add_argument("--headless", action="store_true", help="Run browser headlessly")
    parser.add_argument("--interactive", action="store_true",
                        help="Pause at each action for manual verification")
    parser.add_argument("--timeout", type=int, default=5000, help="Per-selector wait timeout ms")
    parser.add_argument("--selector-map", default=str(DEFAULT_SELECTOR_MAP))
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    args = parser.parse_args()

    map_path = Path(args.selector_map)
    history_path = Path(args.history)

    # Load existing state
    existing_map = load_existing_map(map_path)
    existing_selectors = existing_map.get("selectors", {})

    print(f"[dom_learner] Loading cookies from: {args.cookie_file}")
    try:
        cookies = load_cookies(args.cookie_file)
    except Exception as exc:
        print(f"[ERROR] Cannot load cookies: {exc}")
        sys.exit(1)

    # P2-5: Load fingerprint for realistic browser context
    fp = load_fingerprint(args.account)
    if fp:
        print(f"[dom_learner] Fingerprint loaded for account '{args.account}': {fp.get('user_agent', '')[:60]}...")
        ctx_opts = {
            "viewport": {"width": fp.get("viewport_width", 1280), "height": fp.get("viewport_height", 800)},
            "user_agent": fp.get("user_agent", ""),
            "locale": fp.get("locale", "vi-VN"),
            "timezone_id": fp.get("timezone_id", "Asia/Ho_Chi_Minh"),
        }
        if fp.get("init_script"):
            _fp_init_script = fp["init_script"]
        else:
            _fp_init_script = None
    else:
        if args.account:
            print(f"[dom_learner] ⚠  No fingerprint found for '{args.account}' — using defaults.")
        else:
            print("[dom_learner] ⚠  No --account specified — using default viewport/UA (bot-detection risk!).")
        ctx_opts = {"viewport": {"width": 1280, "height": 800}}
        _fp_init_script = None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    changes: dict[str, dict] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(**ctx_opts)
        if _fp_init_script:
            context.add_init_script(_fp_init_script)
        inject_cookies(context, cookies)
        page = context.new_page()

        print("[dom_learner] Navigating to facebook.com ...")
        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)

        if "login" in page.url:
            browser.close()
            print("[ERROR] Not logged in. Provide valid cookies.")
            sys.exit(1)

        print("[dom_learner] Logged in. Starting selector probing...\n")

        # --- 1. Probe open_composer (always first, from feed) ---
        action = "open_composer"
        print(f"  Probing: {action}")
        primary, fallbacks = probe_action(page, action, PROBE_CANDIDATES[action], args.timeout)

        if primary:
            print(f"    ✓ primary: {primary}")
            # Open the composer for subsequent probes
            # Fix: check primary (the selector string), not action (the key name)
            if primary.startswith("//"):
                page.locator(f"xpath={primary}").first.click()
            else:
                page.locator(primary).first.click()
            page.wait_for_timeout(1500)
        else:
            print(f"    ✗ No working selector found for {action}")

        _record_change(action, primary, fallbacks, existing_selectors, changes, args)

        if args.interactive:
            input("    [INTERACTIVE] Composer should be open. Press Enter to continue...")

        # --- 2. Probe actions that require the composer open ---
        for action in ["text_input", "media_button", "file_input"]:
            print(f"  Probing: {action}")
            primary, fallbacks = probe_action(page, action, PROBE_CANDIDATES[action], args.timeout)
            if primary:
                print(f"    ✓ primary: {primary}")
            else:
                print(f"    ✗ No working selector found for {action}")
            _record_change(action, primary, fallbacks, existing_selectors, changes, args)

            if args.interactive:
                input(f"    [INTERACTIVE] Verified {action}. Press Enter to continue...")

        # --- 3. Probe schedule_entry (may need to open a menu) ---
        print("  Probing: schedule_entry")
        primary, fallbacks = probe_action(page, "schedule_entry", PROBE_CANDIDATES["schedule_entry"], args.timeout)
        if primary:
            print(f"    ✓ primary: {primary}")
        else:
            print("    ✗ No working selector (may require clicking '...' menu first)")
        _record_change("schedule_entry", primary, fallbacks, existing_selectors, changes, args)

        # --- 4. Probe publish_button ---
        print("  Probing: publish_button")
        primary, fallbacks = probe_action(page, "publish_button", PROBE_CANDIDATES["publish_button"], args.timeout)
        if primary:
            print(f"    ✓ primary: {primary}")
        else:
            print("    ✗ No working selector for publish_button")
        _record_change("publish_button", primary, fallbacks, existing_selectors, changes, args)

        # --- 5. schedule_confirm — only probe if schedule panel is open ---
        print("  Probing: schedule_confirm (requires schedule panel open)")
        primary, fallbacks = probe_action(page, "schedule_confirm", PROBE_CANDIDATES["schedule_confirm"], args.timeout)
        if primary:
            print(f"    ✓ primary: {primary}")
        else:
            print("    ✗ No working selector for schedule_confirm (expected if schedule panel not open)")
        _record_change("schedule_confirm", primary, fallbacks, existing_selectors, changes, args)

        browser.close()

    # --- Build updated selector map ---
    new_selectors = dict(existing_selectors)
    for action, info in changes.items():
        if info["primary"] is not None:
            new_selectors[action] = {
                "description": existing_selectors.get(action, {}).get("description", action),
                "primary": info["primary"],
                "fallbacks": info["fallbacks"],
                "last_verified": _now_iso(),
            }

    if changes:
        new_version = bump_version(existing_map.get("version", "1.0.0"))
        updated_map = {
            "version": new_version,
            "updated_at": _now_iso(),
            "note": existing_map.get("note", ""),
            "selectors": new_selectors,
        }
        save_selector_map(map_path, updated_map)
        print(f"\n[dom_learner] Saved updated selector-map.json (version {new_version})")

        # Append history entries
        for action, info in changes.items():
            history_record = {
                "timestamp": _now_iso(),
                "version": new_version,
                "action": action,
                "old_primary": info["old_primary"],
                "new_primary": info["primary"],
                "reason": "dom_learner.py re-probe",
                "fallbacks": info["fallbacks"],
            }
            append_history(history_path, history_record)
        print(f"[dom_learner] Appended {len(changes)} record(s) to selector-map.history.jsonl")
    else:
        print("\n[dom_learner] No selector changes detected.")

    print("[dom_learner] Done.")


def _record_change(action, primary, fallbacks, existing_selectors, changes, args):
    """Compare discovered selector with existing one. Record if changed or new."""
    old_entry = existing_selectors.get(action, {})
    old_primary = old_entry.get("primary") if old_entry else None
    if primary != old_primary:
        changes[action] = {
            "primary": primary,
            "fallbacks": fallbacks,
            "old_primary": old_primary,
        }
        if old_primary is not None:
            print(f"    → Changed from: {old_primary}")


if __name__ == "__main__":
    main()
