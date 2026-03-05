#!/usr/bin/env python3
"""
proxy_manager.py — Manage proxies for multi-account Facebook posting.

Commands:
  add     — Add a proxy to the registry
  list    — Show all proxies with status
  test    — Test a specific proxy (connectivity + IP check)
  health  — Test ALL proxies, update status
  rotate  — Assign a new proxy to an account
  remove  — Delete a proxy from registry

Usage:
  python scripts/proxy_manager.py add --host 1.2.3.4 --port 3128 --user u --pass p --country VN
  python scripts/proxy_manager.py list
  python scripts/proxy_manager.py test --id proxy_vn_01
  python scripts/proxy_manager.py health
  python scripts/proxy_manager.py rotate --account pham_thanh
  python scripts/proxy_manager.py remove --id proxy_vn_01
"""

from __future__ import annotations
import json
import sys
import argparse
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent
PROXY_FILE = SKILL_ROOT / "proxies" / "proxy-list.json"
PROXY_USAGE_LOG = SKILL_ROOT / "proxies" / "proxy-usage.jsonl"
ACCOUNTS_FILE = SKILL_ROOT / "accounts" / "accounts.json"
ROTATION_RULES_FILE = SKILL_ROOT / "references" / "rotation-rules.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_proxies() -> dict:
    if not PROXY_FILE.exists():
        return {"version": "1.0.0", "proxies": []}
    with open(PROXY_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_proxies(data: dict):
    data["updated_at"] = _now()
    PROXY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_accounts() -> dict:
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_accounts(data: dict):
    data["updated_at"] = _now()
    ACCOUNTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_rotation_rules() -> dict:
    with open(ROTATION_RULES_FILE, encoding="utf-8") as f:
        return json.load(f)


def log_usage(proxy_id: str, event: str, note: str):
    record = {"timestamp": _now(), "proxy_id": proxy_id, "event": event, "note": note}
    PROXY_USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROXY_USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_proxy_id(host: str, port: int) -> str:
    """Generate a stable proxy ID from host:port."""
    safe = host.replace(".", "_").replace(":", "_")
    return f"proxy_{safe}_{port}"


def build_proxy_url(proxy: dict) -> str:
    """Build proxy URL string: http://user:pass@host:port"""
    ptype = proxy.get("type", "http")
    host = proxy["host"]
    port = proxy["port"]
    user = proxy.get("username", "")
    pwd = proxy.get("password", "")
    if user and pwd:
        return f"{ptype}://{urllib.parse.quote(user)}:{urllib.parse.quote(pwd)}@{host}:{port}"
    return f"{ptype}://{host}:{port}"


def test_proxy(proxy: dict, timeout: int = 10) -> tuple[bool, str]:
    """
    Test proxy by fetching api.ipify.org through it.
    Returns (success: bool, ip_or_error: str).
    """
    proxy_url = build_proxy_url(proxy)
    rules = load_rotation_rules()
    check_url = rules.get("health_check_url", "https://api.ipify.org?format=json")
    timeout_s = rules.get("health_check_timeout_s", 10)

    try:
        proxy_handler = urllib.request.ProxyHandler({
            proxy.get("type", "http"): proxy_url
        })
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        response = opener.open(check_url, timeout=timeout_s)
        data = json.loads(response.read().decode())
        ip = data.get("ip", "unknown")
        return True, ip
    except Exception as e:
        return False, str(e)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(args):
    data = load_proxies()
    proxy_id = args.id or make_proxy_id(args.host, args.port)

    # Check for duplicate
    for p in data["proxies"]:
        if p["id"] == proxy_id:
            print(f"ERROR: Proxy '{proxy_id}' already exists. Use --id to specify a different ID.")
            sys.exit(1)

    proxy = {
        "id": proxy_id,
        "type": args.type,
        "host": args.host,
        "port": args.port,
        "username": args.user or "",
        "password": args.password or "",
        "country": args.country.upper() if args.country else "XX",
        "status": "unknown",
        "fail_count": 0,
        "last_checked": None,
        "last_ip": None,
        "added_at": _now(),
        "notes": args.notes or "",
    }

    # Auto-test on add
    print(f"  Testing proxy {args.host}:{args.port}...")
    ok, result = test_proxy(proxy)
    if ok:
        proxy["status"] = "active"
        proxy["last_ip"] = result
        proxy["last_checked"] = _now()
        print(f"  ✅ Proxy OK — External IP: {result}")
        log_usage(proxy_id, "added_and_tested", f"IP={result}")
    else:
        proxy["status"] = "untested"
        print(f"  ⚠  Proxy test failed: {result}")
        print(f"     Added anyway with status 'untested'")
        log_usage(proxy_id, "added_failed_test", result)

    data["proxies"].append(proxy)
    save_proxies(data)
    print(f"\n✅ Proxy '{proxy_id}' added ({args.host}:{args.port}, {proxy['country']})")


def cmd_list(args):
    data = load_proxies()
    proxies = data["proxies"]

    if not proxies:
        print("No proxies registered. Use: proxy_manager.py add --host ... --port ...")
        return

    print(f"\n{'ID':<25} {'Type':<7} {'Host':<18} {'Port':<7} {'Country':<8} {'Status':<10} {'Fails':<6} {'Last IP'}")
    print("─" * 100)
    for p in proxies:
        status_icon = {"active": "✅", "blacklisted": "❌", "untested": "⚠️ ", "unknown": "❓"}.get(p["status"], "❓")
        print(f"{p['id']:<25} {p['type']:<7} {p['host']:<18} {p['port']:<7} {p['country']:<8} "
              f"{status_icon}{p['status']:<9} {p['fail_count']:<6} {p.get('last_ip', '—')}")
    print(f"\nTotal: {len(proxies)} proxies")


def cmd_test(args):
    data = load_proxies()
    proxy = next((p for p in data["proxies"] if p["id"] == args.id), None)
    if not proxy:
        print(f"ERROR: Proxy '{args.id}' not found")
        sys.exit(1)

    print(f"Testing proxy: {args.id} ({proxy['host']}:{proxy['port']})...")
    ok, result = test_proxy(proxy)

    rules = load_rotation_rules()
    if ok:
        proxy["status"] = "active"
        proxy["fail_count"] = 0
        proxy["last_ip"] = result
        proxy["last_checked"] = _now()
        print(f"✅ PASS — External IP: {result}")
        log_usage(args.id, "test_pass", f"IP={result}")
    else:
        proxy["fail_count"] = proxy.get("fail_count", 0) + 1
        proxy["last_checked"] = _now()
        if proxy["fail_count"] >= rules.get("blacklist_after_fails", 5):
            proxy["status"] = "blacklisted"
            print(f"❌ FAIL — {result}")
            print(f"   ⛔ Proxy BLACKLISTED after {proxy['fail_count']} failures")
            log_usage(args.id, "blacklisted", result)
        else:
            proxy["status"] = "failing"
            print(f"❌ FAIL ({proxy['fail_count']}/{rules.get('blacklist_after_fails', 5)} before blacklist) — {result}")
            log_usage(args.id, "test_fail", result)

    save_proxies(data)


def cmd_health(args):
    data = load_proxies()
    proxies = data["proxies"]

    if not proxies:
        print("No proxies to check.")
        return

    print(f"Health checking {len(proxies)} proxies...\n")
    rules = load_rotation_rules()
    pass_count = 0

    for proxy in proxies:
        if proxy["status"] == "blacklisted":
            print(f"  ⛔ {proxy['id']:<25} SKIPPED (blacklisted)")
            continue

        print(f"  Testing {proxy['id']:<25}...", end=" ", flush=True)
        ok, result = test_proxy(proxy)

        if ok:
            proxy["status"] = "active"
            proxy["fail_count"] = 0
            proxy["last_ip"] = result
            proxy["last_checked"] = _now()
            print(f"✅ {result}")
            pass_count += 1
            log_usage(proxy["id"], "health_pass", f"IP={result}")
        else:
            proxy["fail_count"] = proxy.get("fail_count", 0) + 1
            proxy["last_checked"] = _now()
            if proxy["fail_count"] >= rules.get("blacklist_after_fails", 5):
                proxy["status"] = "blacklisted"
                print(f"❌ BLACKLISTED — {result[:60]}")
                log_usage(proxy["id"], "blacklisted", result)
            else:
                proxy["status"] = "failing"
                print(f"❌ fail #{proxy['fail_count']} — {result[:60]}")
                log_usage(proxy["id"], "health_fail", result)

    save_proxies(data)
    print(f"\n✅ {pass_count}/{len(proxies)} proxies healthy")


def cmd_rotate(args):
    """Assign a new (healthy) proxy to an account."""
    accounts_data = load_accounts()
    account = next((a for a in accounts_data["accounts"] if a["id"] == args.account), None)
    if not account:
        print(f"ERROR: Account '{args.account}' not found")
        sys.exit(1)

    proxies_data = load_proxies()
    rules = load_rotation_rules()
    current_proxy_id = account.get("proxy_id")

    # Find healthy proxies, prefer same country if rule says so
    active = [p for p in proxies_data["proxies"] if p["status"] == "active" and p["id"] != current_proxy_id]

    # Try to match country first
    if rules.get("prefer_same_country") and current_proxy_id:
        current_proxy = next((p for p in proxies_data["proxies"] if p["id"] == current_proxy_id), None)
        if current_proxy:
            same_country = [p for p in active if p["country"] == current_proxy["country"]]
            if same_country:
                active = same_country

    if not active:
        if rules.get("fallback_to_direct", False):
            account["proxy_id"] = None
            save_accounts(accounts_data)
            print(f"⚠  No active proxies — falling back to direct connection for '{args.account}'")
            log_usage("none", "fallback_direct", f"account={args.account}")
        else:
            print(f"❌ No active proxies available for rotation. Run: proxy_manager.py health")
            sys.exit(1)
        return

    new_proxy = active[0]
    old_proxy_id = account.get("proxy_id", "none")
    account["proxy_id"] = new_proxy["id"]
    save_accounts(accounts_data)

    print(f"✅ Rotated proxy for '{args.account}'")
    print(f"   Old: {old_proxy_id}")
    print(f"   New: {new_proxy['id']} ({new_proxy['host']}:{new_proxy['port']}, {new_proxy['country']})")
    log_usage(new_proxy["id"], "rotated", f"account={args.account}, old={old_proxy_id}")


def cmd_remove(args):
    data = load_proxies()
    before = len(data["proxies"])
    data["proxies"] = [p for p in data["proxies"] if p["id"] != args.id]
    if len(data["proxies"]) == before:
        print(f"ERROR: Proxy '{args.id}' not found")
        sys.exit(1)
    save_proxies(data)
    print(f"✅ Proxy '{args.id}' removed")
    log_usage(args.id, "removed", "")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage proxies for Facebook posting")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a proxy")
    p_add.add_argument("--host", required=True)
    p_add.add_argument("--port", required=True, type=int)
    p_add.add_argument("--user", default="")
    p_add.add_argument("--pass", dest="password", default="")
    p_add.add_argument("--type", default="http", choices=["http", "https", "socks5"])
    p_add.add_argument("--country", default="XX")
    p_add.add_argument("--id", default=None, help="Custom proxy ID (auto-generated if omitted)")
    p_add.add_argument("--notes", default="")

    # list
    sub.add_parser("list", help="List all proxies")

    # test
    p_test = sub.add_parser("test", help="Test a specific proxy")
    p_test.add_argument("--id", required=True)

    # health
    sub.add_parser("health", help="Health-check all proxies")

    # rotate
    p_rotate = sub.add_parser("rotate", help="Assign new proxy to account")
    p_rotate.add_argument("--account", required=True)

    # remove
    p_remove = sub.add_parser("remove", help="Remove a proxy")
    p_remove.add_argument("--id", required=True)

    args = parser.parse_args()

    cmds = {
        "add": cmd_add,
        "list": cmd_list,
        "test": cmd_test,
        "health": cmd_health,
        "rotate": cmd_rotate,
        "remove": cmd_remove,
    }
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
