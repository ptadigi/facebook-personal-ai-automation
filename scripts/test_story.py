#!/usr/bin/env python3
"""
test_story.py — Complete Facebook Story post flow via Playwright.
Uploads a photo to Facebook Story and publishes it.

Flow:
  1. Navigate to facebook.com/stories/create
  2. Click "Tạo tin dạng ảnh" (upload photo story)
  3. set_input_files on the hidden file input
  4. Wait for image to load in Story editor
  5. Click "Chia sẻ lên tin" to publish
  6. Verify success

Usage:
  python scripts/test_story.py --cookie-file cookies.json --media test_image_1.jpg
"""

from __future__ import annotations
import json, sys, time, argparse
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent


def load_cookies(path):
    with open(path) as f:
        data = json.load(f)
    cookies = data["cookies"] if isinstance(data, dict) else data
    result = []
    for c in cookies:
        pc = {k: c[k] for k in ("name", "value", "domain", "path", "httpOnly", "secure") if k in c}
        pc.setdefault("domain", ".facebook.com")
        pc.setdefault("path", "/")
        ss = c.get("sameSite", "None")
        pc["sameSite"] = ss if ss in ("Strict", "Lax", "None") else "None"
        if c.get("expirationDate"):
            pc["expires"] = int(c["expirationDate"])
        result.append(pc)
    return result


def screenshot(page, name):
    path = SKILL_ROOT / f"test_result_story_{name}.png"
    page.screenshot(path=str(path))
    print(f"  📸 {path.name}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie-file", required=True)
    parser.add_argument("--media", default="test_image_1.jpg", help="Image/video to upload as Story")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    media_path = Path(args.media)
    if not media_path.is_absolute():
        media_path = SKILL_ROOT / media_path
    if not media_path.exists():
        print(f"ERROR: Media file not found: {media_path}")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: pip install playwright && playwright install chromium")
        sys.exit(1)

    cookies = load_cookies(args.cookie_file)

    print(f"\n{'='*55}")
    print("TEST: Story Post (Full Flow)")
    print(f"  Media: {media_path.name}")
    print(f"{'='*55}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # ── Step 1: Navigate to Story Creator ─────────────────────
        print("  → Navigating to Story Creator...")
        page.goto("https://www.facebook.com/stories/create", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        if "login" in page.url:
            browser.close()
            print("FAIL: AUTH_REQUIRED - Not logged in")
            sys.exit(1)

        screenshot(page, "01_creator_page")
        print(f"  ✓ Story creator loaded | URL: {page.url}")

        # ── Step 2: Click "Tạo tin dạng ảnh" ──────────────────────
        print("  → Clicking 'Tải ảnh lên / Tạo tin dạng ảnh'...")
        upload_btn_sels = [
            "[aria-label='Tải ảnh lên']",
            "[aria-label='Tạo tin dạng ảnh']",
            "div[role='button']:has-text('Tạo tin dạng ảnh')",
            "div[role='button']:has-text('Tải ảnh lên')",
        ]
        clicked = False
        for sel in upload_btn_sels:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=4000)
                btn.click()
                clicked = True
                print(f"  ✓ Clicked via: {sel}")
                time.sleep(1.5)
                break
            except Exception:
                pass

        if not clicked:
            # Pixel fallback — left card "Tạo tin dạng ảnh"
            page.mouse.click(535, 397)
            time.sleep(1.5)
            print("  → Pixel click fallback on photo story card")

        screenshot(page, "02_after_click_photo")

        # ── Step 3: Find and use file input ───────────────────────
        print(f"  → Uploading: {media_path.name}")

        # Expose the hidden file input
        page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input[type="file"]');
                inputs.forEach(inp => {
                    inp.style.display = 'block';
                    inp.style.visibility = 'visible';
                    inp.style.opacity = '1';
                    inp.style.position = 'fixed';
                    inp.style.top = '0';
                    inp.style.left = '0';
                    inp.style.width = '10px';
                    inp.style.height = '10px';
                    inp.style.zIndex = '9999';
                });
            }
        """)

        file_sels = [
            "input[type='file'][accept*='image']",
            "input[type='file'][accept*='video']",
            "input.x1s85apg",        # FB-specific class captured by browser subagent
            "input[type='file']",
        ]
        uploaded = False
        for sel in file_sels:
            try:
                inp = page.locator(sel).first
                inp.wait_for(state="attached", timeout=5000)
                inp.set_input_files(str(media_path))
                uploaded = True
                print(f"  ✓ File set via: {sel}")
                time.sleep(4)  # wait for FB to process/render the image
                break
            except Exception as e:
                print(f"    ✗ {sel} failed: {e}")

        if not uploaded:
            screenshot(page, "03_upload_fail")
            browser.close()
            print("FAIL: DOM_CHANGED - Could not set file input for Story upload")
            sys.exit(1)

        screenshot(page, "03_image_in_editor")
        print("  ✓ Image loaded in Story editor")

        # ── Step 4: Publish — "Chia sẻ lên tin" ───────────────────
        print("  → Clicking 'Chia sẻ lên tin'...")
        publish_sels = [
            "[aria-label='Chia sẻ lên tin']",
            "div[role='button']:has-text('Chia sẻ lên tin')",
            "[aria-label='Share to story']",
            "div[role='button']:has-text('Đăng tin')",
            "div[role='button']:has-text('Share to story')",
        ]
        published = False
        for sel in publish_sels:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=8000)
                btn.click()
                published = True
                print(f"  ✓ Publish button clicked via: {sel}")
                break
            except Exception:
                pass

        if published:
            # Wait for "Đang đăng" to appear then disappear
            print("  → Waiting for upload to complete...")
            upload_confirmed = False
            for i in range(15):   # up to 15s
                time.sleep(1)
                try:
                    body = page.inner_text("body")
                    if "Đang đăng" in body:
                        print(f"    [{i+1}s] Uploading (Đang đăng)...")
                        upload_confirmed = True
                    elif upload_confirmed:
                        # Was uploading, now it's gone → success
                        print(f"    [{i+1}s] Upload complete!")
                        break
                except Exception:
                    pass
            # Extra wait then screenshot
            time.sleep(3)

        screenshot(page, "04_after_publish")
        final_url = page.url
        print(f"  → Final URL: {final_url}")
        # Also check if we returned to home feed (another success indicator)
        time.sleep(2)
        screenshot(page, "05_final_state")

        browser.close()

    if published:
        # Extract story URL — try to find user's story link on /stories page
        story_url = None
        try:
            # Look for a story link belonging to this user
            story_links = page.query_selector_all("a[href*='/stories/']")
            for lnk in story_links:
                href = lnk.get_attribute("href") or ""
                if "/stories/" in href and href != "/stories/":
                    story_url = ("https://www.facebook.com" + href) if href.startswith("/") else href
                    break
        except Exception:
            pass

        if "stories/create" not in final_url:
            url_label = story_url or final_url
            print("\n✅ RESULT: OK: story published")
            print(f"   🔗 URL: {url_label}")
        else:
            print("\n⚠  RESULT: Publish button clicked but page didn't change — check screenshot 04")
    else:
        print("\n❌ RESULT: FAIL: PUBLISH_FAILED - Could not find publish button")
        print("   Check test_result_story_03_image_in_editor.png for current state")


if __name__ == "__main__":
    main()
