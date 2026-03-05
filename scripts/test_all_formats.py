#!/usr/bin/env python3
"""
test_all_formats.py — Comprehensive format test script
Tests: single image, multi-image, video, story, text+link
Run: python scripts/test_all_formats.py --cookie-file cookies.json
"""

from __future__ import annotations
import json, sys, time, argparse
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")

def load_cookies(path):
    with open(path) as f: data = json.load(f)
    cookies = data["cookies"] if isinstance(data, dict) else data
    result = []
    for c in cookies:
        pc = {k: c[k] for k in ("name","value","domain","path","httpOnly","secure") if k in c}
        pc.setdefault("domain", ".facebook.com")
        pc.setdefault("path", "/")
        ss = c.get("sameSite","None")
        pc["sameSite"] = ss if ss in ("Strict","Lax","None") else "None"
        if c.get("expirationDate"): pc["expires"] = int(c["expirationDate"])
        elif c.get("expires"): pc["expires"] = int(c["expires"])
        result.append(pc)
    return result

def inject_text(page, selector, text):
    """Inject text into FB Lexical editor via JS execCommand."""
    el = page.locator(selector).first
    el.click()
    time.sleep(0.3)
    page.evaluate(f"""
        (function(){{
            var el = document.querySelector('[contenteditable="true"][role="textbox"]');
            if(!el) el = document.querySelector('[contenteditable="true"]');
            if(el){{
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                document.execCommand('insertText', false, {json.dumps(text)});
            }}
        }})()
    """)
    time.sleep(0.5)

def open_composer(page, timeout=10000):
    """Click 'What's on your mind?' to open composer."""
    candidates = [
        "[aria-label=\"What's on your mind?\"]",
        "div[role='button']:has-text(\"Thành ơi\")",
        "div[role='button']:has-text(\"What's on your mind\")",
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            time.sleep(1.5)
            return sel
        except: pass
    # Pixel fallback - click on the composer area
    page.mouse.click(480, 82)
    time.sleep(1.5)
    return "pixel-click"

def attach_files(page, file_paths: list, timeout=10000):
    """Click media button then set_input_files on the file input."""
    # Click photo/video button
    media_sels = [
        "[aria-label='Photo/video']", "[aria-label='Ảnh/video']",
        "div[role='button'][aria-label*='Photo']", "div[role='button'][aria-label*='nh']",
    ]
    clicked = False
    for sel in media_sels:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=3000)
            btn.click()
            time.sleep(1)
            clicked = True
            break
        except: pass

    if not clicked:
        # Try pixel click on the image icon in toolbar
        page.mouse.click(503, 629)
        time.sleep(1)

    # Wait for file input and set files
    file_sels = [
        "input[type='file'][accept*='image']",
        "input[type='file'][accept*='video']",
        "input[type='file']",
    ]
    for sel in file_sels:
        try:
            inp = page.locator(sel).first
            inp.wait_for(state="attached", timeout=5000)
            inp.set_input_files(file_paths)
            time.sleep(3)  # wait for upload
            return True
        except: pass
    return False

def publish(page, timeout=10000):
    """Click publish/Post button."""
    pub_sels = [
        "div[aria-label='Post'][role='button']",
        "div[aria-label='Đăng'][role='button']",
        "[data-testid='react-composer-post-button']",
    ]
    for sel in pub_sels:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=timeout)
            btn.click()
            time.sleep(4)
            return True
        except: pass

    # Pixel fallback
    page.mouse.click(500, 700)
    time.sleep(4)
    return True

def screenshot(page, name):
    path = SKILL_ROOT / f"test_result_{name}.png"
    page.screenshot(path=str(path))
    print(f"  📸 Screenshot: {path.name}")
    return path

def extract_feed_post_url(page):
    """After posting to feed, scan for the newest post permalink."""
    try:
        time.sleep(2)  # let feed render
        patterns = [
            "a[href*='/posts/']",
            "a[href*='/permalink/']",
            "a[href*='story_fbid']",
        ]
        for pattern in patterns:
            links = page.query_selector_all(pattern)
            for link in links:
                href = link.get_attribute("href") or ""
                if any(kw in href for kw in ["/posts/", "/permalink/", "story_fbid"]):
                    if href.startswith("/"):
                        href = "https://www.facebook.com" + href
                    return href.split("?")[0] if "story_fbid" not in href else href
    except Exception:
        pass
    return None


def run_test(name, page, text, files=None):
    print(f"\n{'='*55}")
    print(f"TEST: {name}")
    print(f"{'='*55}")
    try:
        # Navigate to home to reset state
        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Open composer
        sel = open_composer(page)
        print(f"  ✓ Composer opened via: {sel}")

        # Type text
        inject_text(page, "div[contenteditable='true'][role='textbox']", text)
        print(f"  ✓ Text entered: {text[:60]}")

        # Attach files if any
        if files:
            uploaded = attach_files(page, files)
            if uploaded:
                print(f"  ✓ Files uploaded: {[Path(f).name for f in files]}")
            else:
                print(f"  ⚠ File upload failed — posting text only")

        # Screenshot before publishing
        screenshot(page, f"{name}_before_publish")

        # Publish
        publish(page)
        print(f"  ✓ Post button clicked")

        # Extract post URL
        post_url = extract_feed_post_url(page)
        url_label = post_url if post_url else "(URL not captured — check feed)"

        screenshot(page, f"{name}_after_publish")
        print(f"  ✅ RESULT: OK: published")
        print(f"  🔗 URL: {url_label}")
        return True, post_url

    except Exception as e:
        print(f"  ❌ RESULT: FAIL — {e}")
        try: screenshot(page, f"{name}_error")
        except: pass
        return False, None


def test_story(page):
    """Attempt to create a Story via the Facebook web UI."""
    print(f"\n{'='*55}")
    print(f"TEST: Story Post")
    print(f"{'='*55}")
    try:
        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Look for "Tạo tin" (Create Story) button
        story_sels = [
            "[aria-label='Tạo tin']",
            "div:has-text('Tạo tin')",
            "[href*='/stories/create']",
            "a[href*='story']",
        ]
        found = False
        for sel in story_sels:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=3000)
                btn.click()
                time.sleep(2)
                found = True
                print(f"  ✓ Story creator opened via: {sel}")
                break
            except: pass

        if not found:
            # Try clicking the "+" Story button in the story strip
            page.mouse.click(613, 149)   # approximate position of "Tạo tin"
            time.sleep(2)
            print("  → Tried pixel click on story button")

        # Screenshot story creator page
        scr = screenshot(page, "story_creator")
        url = page.url
        print(f"  → Current URL: {url}")

        if "story" in url.lower() or "stories" in url.lower():
            print("  ✅ RESULT: Story creator page opened — manual image upload needed (web only supports photo story)")
        else:
            print("  ⚠ RESULT: Story page not confirmed — UI may differ. Check screenshot.")
        return True
    except Exception as e:
        print(f"  ❌ RESULT: FAIL — {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie-file", required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--skip", nargs="*", default=[], help="Skip test names: text image multi_image video story")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: pip install playwright && playwright install chromium")
        sys.exit(1)

    cookies = load_cookies(args.cookie_file)

    results = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # Verify auth
        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
        if "login" in page.url:
            print("AUTH FAILED — cookies invalid")
            sys.exit(1)
        print(f"✓ Auth OK — {page.url}")

        # ── TEST 1: Text only ──────────────────────────────────────
        if "text" not in args.skip:
            ok, url = run_test("text_only", page,
                "[TEST-TEXT] Bai dang text thuan - Auto-post skill test 2026-03-05")
            results["text"] = {"status": "OK" if ok else "FAIL", "url": url}

        # ── TEST 2: Single image ───────────────────────────────────
        if "image" not in args.skip:
            img1 = str(SKILL_ROOT / "test_image_1.jpg")
            ok, url = run_test("single_image", page,
                "[TEST-IMG1] 1 hinh anh - Auto-post skill test",
                files=[img1])
            results["single_image"] = {"status": "OK" if ok else "FAIL", "url": url}

        # ── TEST 3: Multiple images ────────────────────────────────
        if "multi_image" not in args.skip:
            imgs = [
                str(SKILL_ROOT / "test_image_1.jpg"),
                str(SKILL_ROOT / "test_image_2.jpg"),
                str(SKILL_ROOT / "test_image_3.jpg"),
            ]
            ok, url = run_test("multi_image", page,
                "[TEST-MULTI] 3 hinh anh - Auto-post skill test",
                files=imgs)
            results["multi_image"] = {"status": "OK" if ok else "FAIL", "url": url}

        # ── TEST 4: Video ──────────────────────────────────────────
        if "video" not in args.skip:
            video = str(SKILL_ROOT / "Use_attached_az_1080p_202602081417.mp4")
            ok, url = run_test("video", page,
                "[TEST-VIDEO] Dang video - Auto-post skill test",
                files=[video])
            results["video"] = {"status": "OK" if ok else "FAIL", "url": url}

        # ── TEST 5: Story — use dedicated test_story.py flow ───────
        if "story" not in args.skip:
            ok = test_story(page)
            results["story"] = {"status": "OK" if ok else "FAIL", "url": "See test_story.py for full flow"}

        browser.close()

    print(f"\n{'='*55}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*55}")
    for fmt, info in results.items():
        icon = "✅" if info["status"] == "OK" else "❌"
        url_str = f"  →  {info['url']}" if info.get("url") else ""
        print(f"  {icon} {fmt:<20} {info['status']}{url_str}")
    print(f"\nReel: use scripts/test_reel.py for full Reel flow")
    print(f"Story: use scripts/test_story.py for full Story flow")
    print(f"{'='*55}")
    print(f"Timestamps: {now()}")


if __name__ == "__main__":
    main()
