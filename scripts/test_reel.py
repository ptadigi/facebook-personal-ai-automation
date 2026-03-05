#!/usr/bin/env python3
"""
test_reel.py — Complete Facebook Reel (Thước phim) post flow via Playwright.

Flow:
  1. Navigate to profile/reels page
  2. Click "Tạo thước phim" button
  3. Upload video via hidden file input
  4. Wait for video to process/preview
  5. Click "Tiếp" (Next) if needed, then "Chia sẻ" / "Đăng" to publish
  6. Verify success

Usage:
  python scripts/test_reel.py --cookie-file cookies.json --media Use_attached_az_1080p_202602081417.mp4
"""

from __future__ import annotations
import json, sys, time, argparse
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROFILE_REELS_URL = "https://www.facebook.com/pham.thanh.756452/reels/"


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
    path = SKILL_ROOT / f"test_result_reel_{name}.png"
    page.screenshot(path=str(path))
    print(f"  📸 {path.name}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie-file", required=True)
    parser.add_argument("--media", default="Use_attached_az_1080p_202602081417.mp4")
    parser.add_argument("--caption", default="[TEST-REEL] Auto-post Reel test - facebook-personal-browser-post skill")
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
    print("TEST: Reel Post (Full Flow - Tao thuoc phim)")
    print(f"  Video: {media_path.name}")
    print(f"{'='*55}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # ── Step 1: Navigate to profile Reels page ────────────────
        print(f"  → Navigating to: {PROFILE_REELS_URL}")
        page.goto(PROFILE_REELS_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        if "login" in page.url:
            browser.close()
            print("FAIL: AUTH_REQUIRED")
            sys.exit(1)

        screenshot(page, "01_reels_page")
        print(f"  ✓ Reels page loaded")

        # ── Step 2: Click "Tạo thước phim" ────────────────────────
        print("  → Clicking 'Tao thuoc phim' (Create Reel)...")
        create_sels = [
            "[aria-label='Tao thuoc phim']",
            "[aria-label='Tạo thước phim']",
            "div[role='button']:has-text('Tao thuoc phim')",
            "div[role='button']:has-text('Create reel')",
            "a[href*='reels/create']",
        ]
        clicked = False
        for sel in create_sels:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=4000)
                btn.click()
                clicked = True
                print(f"  ✓ Clicked via: {sel}")
                time.sleep(2)
                break
            except Exception:
                pass

        if not clicked:
            # Try JS click on any button with 'tao' or 'create' text
            result = page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('[role="button"]'));
                    const btn = btns.find(b => b.textContent.toLowerCase().includes('thu') || 
                                               b.textContent.toLowerCase().includes('reel') ||
                                               (b.getAttribute('aria-label') || '').toLowerCase().includes('thu'));
                    if (btn) { btn.click(); return btn.textContent.trim(); }
                    return null;
                }
            """)
            if result:
                print(f"  → JS click on: {result[:40]}")
                time.sleep(2)
                clicked = True

        screenshot(page, "02_reel_modal")

        # ── Step 3: Upload video via file input ───────────────────
        print(f"  → Uploading video: {media_path.name}")

        # Make hidden file inputs visible
        page.evaluate("""
            () => {
                document.querySelectorAll('input[type="file"]').forEach(inp => {
                    inp.style.cssText = 'display:block!important;visibility:visible!important;opacity:1!important;position:fixed;top:0;left:0;width:1px;height:1px;z-index:9999';
                });
            }
        """)

        video_input_sels = [
            "input[type='file'][accept*='video']",
            "input[type='file'][accept*='mp4']",
            "input[type='file']",
        ]
        uploaded = False
        for sel in video_input_sels:
            try:
                inp = page.locator(sel).first
                inp.wait_for(state="attached", timeout=5000)
                inp.set_input_files(str(media_path))
                uploaded = True
                print(f"  ✓ Video file set via: {sel}")
                break
            except Exception as e:
                print(f"    ✗ {sel}: {e}")

        # Also try clicking "Tai len" button which might trigger file dialog
        if not uploaded:
            tai_len_sels = [
                "[aria-label='Tai video len cho Thuoc phim']",
                "div[role='button']:has-text('Tai len')",
                "div[role='button']:has-text('Tải lên')",
            ]
            for sel in tai_len_sels:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state="visible", timeout=3000)
                    btn.click()
                    time.sleep(1)
                    # Now try file input again
                    page.evaluate("document.querySelectorAll('input[type=\"file\"]').forEach(i=>{i.style.display='block'})")
                    inp = page.locator("input[type='file']").first
                    inp.set_input_files(str(media_path))
                    uploaded = True
                    print(f"  ✓ Video uploaded after clicking: {sel}")
                    break
                except Exception:
                    pass

        if not uploaded:
            screenshot(page, "03_upload_fail")
            browser.close()
            print("FAIL: DOM_CHANGED - Cannot upload video to Reel")
            sys.exit(1)

        # ── Step 4: Wait for video to process ─────────────────────
        print("  → Waiting for video to process (up to 30s)...")
        for i in range(30):
            time.sleep(1)
            try:
                body = page.inner_text("body")
                # Look for processing complete signals
                if any(kw in body for kw in ["Xem truoc", "Xem trước", "Next", "Tiep"]):
                    print(f"    [{i+1}s] Video preview ready!")
                    break
                if i % 5 == 0:
                    print(f"    [{i+1}s] Processing...")
            except Exception:
                pass

        screenshot(page, "03_video_preview")

        # ── Step 5: Add caption ────────────────────────────────────
        print("  → Adding caption...")
        caption_sels = [
            "textarea[placeholder*='caption']",
            "div[contenteditable='true'][aria-label*='caption']",
            "div[contenteditable='true'][aria-label*='mo ta']",
            "textarea",
        ]
        for sel in caption_sels:
            try:
                inp = page.locator(sel).first
                inp.wait_for(state="visible", timeout=3000)
                inp.click()
                inp.fill(args.caption)
                print(f"  ✓ Caption added via: {sel}")
                break
            except Exception:
                pass

        # ── Step 6: Navigate through multi-step flow ──────────────
        # Reel flow: Edit (Chỉnh sửa) → Next → Details → Next → Share
        # Click "Tiếp" up to 3 times until we reach the Chia sẻ/Share screen
        print("  → Navigating through Reel steps (may need multiple Tiep clicks)...")
        next_sels = [
            "div[role='button']:has-text('Tiep')",
            "div[role='button']:has-text('Tiếp')",
            "div[role='button']:has-text('Next')",
        ]
        for step_num in range(3):
            # First check if publish button is already visible
            publish_visible = False
            for pub_check in ["Chia se", "Chia sẻ", "Share", "Dang", "Đăng", "Publish"]:
                try:
                    btns = page.query_selector_all(f"div[role='button']")
                    for b in btns:
                        txt = (b.inner_text() or "").strip()
                        if pub_check.lower() in txt.lower() and len(txt) < 20:
                            print(f"    → Publish button found: '{txt}' — stopping navigation")
                            publish_visible = True
                            break
                    if publish_visible:
                        break
                except Exception:
                    pass
            if publish_visible:
                break

            # Click next/Tiep
            clicked_next = False
            for sel in next_sels:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state="visible", timeout=3000)
                    txt = btn.inner_text().strip()
                    btn.click()
                    clicked_next = True
                    print(f"    → Step {step_num+1}: Clicked '{txt}'")
                    time.sleep(2)
                    screenshot(page, f"step{step_num+1}_tiep")
                    break
                except Exception:
                    pass
            if not clicked_next:
                print(f"    → Step {step_num+1}: No 'Tiếp' button found — reached final screen")
                break

        screenshot(page, "04_before_publish")

        # ── Step 7: Publish Reel ───────────────────────────────────
        print("  → Publishing Reel...")
        publish_sels = [
            "div[role='button']:has-text('Chia se')",
            "div[role='button']:has-text('Chia sẻ')",
            "div[role='button']:has-text('Dang')",
            "div[role='button']:has-text('Đăng')",
            "div[role='button']:has-text('Share')",
            "div[role='button']:has-text('Publish')",
            "[aria-label='Chia se']",
            "[aria-label='Dang']",
        ]
        published = False
        for sel in publish_sels:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="visible", timeout=5000)
                btn.click()
                published = True
                print(f"  ✓ Publish clicked via: {sel}")
                break
            except Exception:
                pass

        if published:
            print("  → Waiting for Reel to upload (up to 30s)...")
            uploading = False
            for i in range(30):
                time.sleep(1)
                try:
                    # FB may open a new page/tab after publish — check all pages
                    pages = ctx.pages
                    active_page = pages[-1]  # use the newest page
                    body = active_page.inner_text("body")
                    if any(kw in body for kw in ["Dang dang", "Dang xuat ban", "Publishing"]):
                        print(f"    [{i+1}s] Uploading...")
                        uploading = True
                    elif uploading:
                        print(f"    [{i+1}s] Upload done!")
                        break
                    elif i % 5 == 0:
                        print(f"    [{i+1}s] Waiting...")
                except Exception:
                    pass
            time.sleep(3)

        # Use the last active page for screenshot/URL
        try:
            active_page = ctx.pages[-1]
            active_page.screenshot(path=str(SKILL_ROOT / "test_result_reel_05_after_publish.png"))
            print(f"  📸 test_result_reel_05_after_publish.png")
            final_url = active_page.url
        except Exception as e:
            print(f"  ⚠ Could not screenshot final state: {e}")
            final_url = "unknown (browser may have navigated away)"

        print(f"  → Final URL: {final_url}")

        # Bug fix: extract reel URL BEFORE closing browser (ctx.pages is inaccessible after close)
        reel_url = None
        if published:
            try:
                active_page = ctx.pages[-1] if ctx.pages else page
                reel_links = active_page.query_selector_all("a[href*='/reel/']")
                for lnk in reel_links:
                    href = lnk.get_attribute("href") or ""
                    if "/reel/" in href:
                        reel_url = ("https://www.facebook.com" + href) if href.startswith("/") else href
                        break
            except Exception:
                pass

        browser.close()

    if published:
        if "reels" in final_url and "create" not in final_url:
            url_label = reel_url or "https://www.facebook.com/pham.thanh.756452/reels/"
            print("\n✅ RESULT: OK: reel published")
            print(f"   🔗 URL: {url_label}")
            print("   ℹ️  Note: Facebook is processing the video. Full reel URL available after processing.")
        else:
            print("\n⚠  RESULT: Publish clicked — verify on profile. Check screenshot 05.")
    else:
        print("\n❌ RESULT: FAIL: PUBLISH_FAILED - Could not find publish button")


if __name__ == "__main__":
    main()
