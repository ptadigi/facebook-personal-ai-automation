#!/usr/bin/env python3
"""
account_manager.py — Manage Facebook accounts for multi-account posting.

Commands:
  add     — Register a new account
  list    — Show all accounts and their status
  test    — Verify session is active (auth check via Playwright)
  assign  — Assign a proxy to an account
  remove  — Delete an account from registry
  init    — First-time setup: import cookies + generate fingerprint

Usage:
  python scripts/account_manager.py add --id acc_02 --cookies path/to/c.json --name "Nguyen A"
  python scripts/account_manager.py list
  python scripts/account_manager.py test --id pham_thanh
  python scripts/account_manager.py assign --id pham_thanh --proxy proxy_vn_01
  python scripts/account_manager.py init --id pham_thanh --cookies cookies.json
"""

from __future__ import annotations
import json
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = SKILL_ROOT / "accounts" / "accounts.json"
PROXIES_FILE = SKILL_ROOT / "proxies" / "proxy-list.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_accounts() -> dict:
    if not ACCOUNTS_FILE.exists():
        return {"version": "1.0.0", "accounts": []}
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_accounts(data: dict):
    data["updated_at"] = _now()
    ACCOUNTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_proxies() -> dict:
    if not PROXIES_FILE.exists():
        return {"proxies": []}
    with open(PROXIES_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_account_dir(account_id: str) -> Path:
    return SKILL_ROOT / "accounts" / account_id


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(args):
    data = load_accounts()

    # Check duplicate
    if any(a["id"] == args.id for a in data["accounts"]):
        print(f"ERROR: Account '{args.id}' already exists.")
        sys.exit(1)

    # Prepare account directory
    acc_dir = get_account_dir(args.id)
    acc_dir.mkdir(parents=True, exist_ok=True)
    (acc_dir / "profile").mkdir(exist_ok=True)

    # Copy cookies if provided
    cookies_rel = f"accounts/{args.id}/cookies.json"
    if args.cookies:
        src = Path(args.cookies)
        if not src.exists():
            print(f"ERROR: Cookies file not found: {args.cookies}")
            sys.exit(1)
        dst = acc_dir / "cookies.json"
        shutil.copy2(src, dst)
        print(f"  ✓ Cookies copied to: {dst}")
    else:
        cookies_rel = ""
        print(f"  ⚠  No cookies file provided — add later with 'init' command")

    account = {
        "id": args.id,
        "display_name": args.name or args.id,
        "profile_url": args.profile_url or "",
        # Bug fix: ensure proper slash between profile_url and 'reels/'
        "reels_url": (args.profile_url.rstrip("/") + "/reels/") if args.profile_url else "",
        "cookies_path": cookies_rel,
        "fingerprint_path": f"accounts/{args.id}/fingerprint.json",
        "profile_dir": f"accounts/{args.id}/profile",
        "proxy_id": args.proxy or None,
        "active": True,
        "daily_post_limit": 20,
        "daily_post_count": 0,
        "daily_post_reset_date": None,
        "last_post": None,
        "added_at": _now(),
        "notes": args.notes or "",
    }

    data["accounts"].append(account)
    save_accounts(data)

    print(f"\n✅ Account '{args.id}' added")
    print(f"   Name:    {account['display_name']}")
    print(f"   Dir:     {acc_dir}")
    print(f"   Proxy:   {account['proxy_id'] or 'none (direct)'}")
    print(f"\nNext steps:")
    print(f"  python scripts/fingerprint_gen.py generate --account {args.id}")
    if not args.cookies:
        print(f"  python scripts/account_manager.py init --id {args.id} --cookies /path/to/cookies.json")


def cmd_list(args):
    data = load_accounts()
    accounts = data["accounts"]

    if not accounts:
        print("No accounts registered. Use: account_manager.py add --id ... --cookies ...")
        return

    print(f"\n{'ID':<20} {'Name':<20} {'Active':<8} {'Proxy':<20} {'Cookies':<10} {'Fingerprint':<12} {'Last Post'}")
    print("─" * 110)
    for a in accounts:
        # Bug fix: cookies_path may be empty string when account was added without cookies
        cookies_ok = False
        if a.get("cookies_path"):
            cookies_ok = (SKILL_ROOT / a["cookies_path"]).exists()
        has_cookies = "✅" if cookies_ok else "❌"
        fp_path = SKILL_ROOT / a["fingerprint_path"]
        has_fp = "✅" if fp_path.exists() else "❌"
        active_str = "✅" if a.get("active") else "❌"
        proxy = a.get("proxy_id") or "direct"
        last_post = a.get("last_post") or "never"
        if len(last_post) > 19:
            last_post = last_post[:19]
        print(f"{a['id']:<20} {a['display_name']:<20} {active_str:<8} {proxy:<20} {has_cookies:<10} {has_fp:<12} {last_post}")

    print(f"\nTotal: {len(accounts)} accounts")


def cmd_test(args):
    """
    Verify that the account session is still active by loading Facebook
    and checking if we stay logged in (not redirected to login page).
    Uses Playwright with the account's stored cookies and fingerprint.
    """
    data = load_accounts()
    account = next((a for a in data["accounts"] if a["id"] == args.id), None)
    if not account:
        print(f"ERROR: Account '{args.id}' not found")
        sys.exit(1)

    print(f"Testing account: {args.id} ({account['display_name']})")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: pip install playwright && playwright install chromium")
        sys.exit(1)

    # Load fingerprint
    fp_path = SKILL_ROOT / account["fingerprint_path"]
    fp = None
    if fp_path.exists():
        fp = json.loads(fp_path.read_text(encoding="utf-8"))
        print(f"  ✓ Fingerprint loaded: {fp['browser']} / {fp['viewport']['width']}x{fp['viewport']['height']}")
    else:
        print(f"  ⚠  No fingerprint found — using defaults")

    # Load proxy
    proxy_config = None
    proxies_data = load_proxies()
    proxy_id = account.get("proxy_id")
    if proxy_id:
        proxy_obj = next((p for p in proxies_data["proxies"] if p["id"] == proxy_id), None)
        if proxy_obj:
            ptype = proxy_obj.get("type", "http")
            host = proxy_obj["host"]
            port = proxy_obj["port"]
            proxy_config = {"server": f"{ptype}://{host}:{port}"}
            if proxy_obj.get("username"):
                proxy_config["username"] = proxy_obj["username"]
                proxy_config["password"] = proxy_obj.get("password", "")
            print(f"  ✓ Proxy: {host}:{port} ({proxy_obj['country']})")
        else:
            print(f"  ⚠  Proxy '{proxy_id}' not found in proxy list")

    # Build context options
    ctx_opts = {
        "viewport": fp["viewport"] if fp else {"width": 1280, "height": 800},
        "user_agent": fp["user_agent"] if fp else "Mozilla/5.0",
        "locale": fp["locale"] if fp else "vi-VN",
        "timezone_id": fp["timezone_id"] if fp else "Asia/Ho_Chi_Minh",
        "device_scale_factor": fp.get("device_scale_factor", 1) if fp else 1,
        "color_scheme": "light",
    }
    if proxy_config:
        ctx_opts["proxy"] = proxy_config

    profile_dir = SKILL_ROOT / account["profile_dir"]
    use_persistent = profile_dir.exists() and any(profile_dir.iterdir())

    with sync_playwright() as pw:
        if use_persistent:
            print(f"  ✓ Using persistent profile: {profile_dir}")
            context = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
                **ctx_opts
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            print(f"  ✓ Using cookies injection (no profile yet)")
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(**ctx_opts)

            cookies_path = SKILL_ROOT / account["cookies_path"]
            if cookies_path.exists():
                raw = json.loads(cookies_path.read_text(encoding="utf-8"))
                cookies = raw["cookies"] if isinstance(raw, dict) else raw
                # Normalize
                pw_cookies = []
                for c in cookies:
                    pc = {k: c[k] for k in ("name","value","domain","path","httpOnly","secure") if k in c}
                    pc.setdefault("domain", ".facebook.com")
                    pc.setdefault("path", "/")
                    ss = c.get("sameSite", "None")
                    pc["sameSite"] = ss if ss in ("Strict","Lax","None") else "None"
                    if c.get("expirationDate"):
                        pc["expires"] = int(c["expirationDate"])
                    elif c.get("expires"):
                        pc["expires"] = int(c["expires"])
                    pw_cookies.append(pc)
                context.add_cookies(pw_cookies)
            page = context.new_page()

        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
        url = page.url
        title = page.title()

        if "login" in url or "checkpoint" in url:
            print(f"\n❌ AUTH FAILED — Session expired or invalid cookies")
            print(f"   URL: {url}")
            context.close()
            sys.exit(1)
        else:
            print(f"  ✓ URL: {url}")
            print(f"  ✓ Title: {title[:60]}")
            print(f"\n✅ Account '{args.id}' session is ACTIVE")
            context.close()


def cmd_assign(args):
    data = load_accounts()
    account = next((a for a in data["accounts"] if a["id"] == args.id), None)
    if not account:
        print(f"ERROR: Account '{args.id}' not found")
        sys.exit(1)

    proxies_data = load_proxies()
    if args.proxy:
        proxy = next((p for p in proxies_data["proxies"] if p["id"] == args.proxy), None)
        if not proxy:
            print(f"ERROR: Proxy '{args.proxy}' not found. Run: proxy_manager.py list")
            sys.exit(1)
        old_proxy = account.get("proxy_id", "none")
        account["proxy_id"] = args.proxy
        save_accounts(data)
        print(f"✅ Assigned proxy '{args.proxy}' to account '{args.id}'")
        print(f"   ({proxy['host']}:{proxy['port']}, {proxy['country']})")
        print(f"   Previous: {old_proxy}")
    elif args.clear:
        account["proxy_id"] = None
        save_accounts(data)
        print(f"✅ Cleared proxy for account '{args.id}' — will use direct connection")


def cmd_remove(args):
    data = load_accounts()
    before = len(data["accounts"])
    data["accounts"] = [a for a in data["accounts"] if a["id"] != args.id]
    if len(data["accounts"]) == before:
        print(f"ERROR: Account '{args.id}' not found")
        sys.exit(1)

    if args.delete_files:
        acc_dir = get_account_dir(args.id)
        if acc_dir.exists():
            shutil.rmtree(acc_dir)
            print(f"  ✓ Deleted account directory: {acc_dir}")

    save_accounts(data)
    print(f"✅ Account '{args.id}' removed from registry")


def _warn_if_datr_missing(cookies_path: Path):
    """Fix 4: Warn if datr cookie is absent — missing datr is a strong bot-detection signal."""
    try:
        raw = json.loads(cookies_path.read_text(encoding="utf-8"))
        cookies = raw["cookies"] if isinstance(raw, dict) else raw
        names = {c.get("name", "") for c in cookies}
        if "datr" not in names:
            print("  ⚠  WARNING: 'datr' cookie not found in cookie file.")
            print("     Facebook uses 'datr' as a device fingerprint. Missing it increases bot-detection risk.")
            print("     Fix: Clear browser cookies, visit facebook.com, then re-export with Cookie-Editor.")
        else:
            print("  ✓ 'datr' cookie present ✅")
    except Exception:
        pass  # Non-critical check


def cmd_init(args):
    """
    First-time init: copy cookies + generate fingerprint for an account.
    """
    data = load_accounts()
    account = next((a for a in data["accounts"] if a["id"] == args.id), None)
    if not account:
        print(f"ERROR: Account '{args.id}' not found. Add it first: account_manager.py add --id {args.id}")
        sys.exit(1)

    acc_dir = get_account_dir(args.id)
    acc_dir.mkdir(parents=True, exist_ok=True)
    (acc_dir / "profile").mkdir(exist_ok=True)

    # Copy cookies
    if args.cookies:
        src = Path(args.cookies)
        if not src.exists():
            print(f"ERROR: Cookies file not found: {args.cookies}")
            sys.exit(1)
        dst = acc_dir / "cookies.json"
        shutil.copy2(src, dst)
        # Fix 3: restrict file permissions — cookies contain session tokens
        try:
            os.chmod(dst, 0o600)
        except Exception:
            pass  # Windows doesn't support full POSIX chmod — silently skip
        account["cookies_path"] = f"accounts/{args.id}/cookies.json"
        print(f"  ✓ Cookies copied to: {dst}")
        # Fix 4: warn if datr cookie missing (high bot-detection risk)
        _warn_if_datr_missing(dst)

    save_accounts(data)

    # Auto-generate fingerprint
    print(f"  → Generating fingerprint for '{args.id}'...")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "fingerprint_gen.py"), "generate", "--account", args.id],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"  ⚠  Fingerprint generation failed: {result.stderr.strip()}")

    print(f"\n✅ Account '{args.id}' initialized")
    print(f"   Next: python scripts/account_manager.py test --id {args.id}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage Facebook accounts for multi-account posting")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Register a new account")
    p_add.add_argument("--id", required=True, help="Unique account ID (e.g. pham_thanh)")
    p_add.add_argument("--name", default="", help="Display name")
    p_add.add_argument("--profile-url", "--profile_url", dest="profile_url", default="")
    p_add.add_argument("--cookies", default="", help="Path to cookies.json")
    p_add.add_argument("--proxy", default=None, help="Proxy ID to assign")
    p_add.add_argument("--notes", default="")

    sub.add_parser("list", help="List all accounts")

    p_test = sub.add_parser("test", help="Test account session (loads Facebook)")
    p_test.add_argument("--id", required=True)

    p_assign = sub.add_parser("assign", help="Assign proxy to account")
    p_assign.add_argument("--id", required=True)
    p_assign.add_argument("--proxy", default=None)
    p_assign.add_argument("--clear", action="store_true", help="Remove proxy assignment")

    p_remove = sub.add_parser("remove", help="Remove an account")
    p_remove.add_argument("--id", required=True)
    p_remove.add_argument("--delete-files", action="store_true", help="Also delete account directory")

    p_init = sub.add_parser("init", help="Initialize account: import cookies + generate fingerprint")
    p_init.add_argument("--id", required=True)
    p_init.add_argument("--cookies", required=True, help="Path to cookies.json")

    args = parser.parse_args()
    cmds = {
        "add": cmd_add, "list": cmd_list, "test": cmd_test,
        "assign": cmd_assign, "remove": cmd_remove, "init": cmd_init,
    }
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
