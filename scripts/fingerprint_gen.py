#!/usr/bin/env python3
"""
fingerprint_gen.py — Generate and manage browser fingerprints per account.

Each account gets a STABLE fingerprint (same every session) to avoid
detection from inconsistent browser characteristics.

Usage:
  python scripts/fingerprint_gen.py generate --account pham_thanh
  python scripts/fingerprint_gen.py show --account pham_thanh
  python scripts/fingerprint_gen.py list
"""

from __future__ import annotations
import json
import random
import argparse
import sys
from pathlib import Path
from datetime import datetime

SKILL_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = SKILL_ROOT / "accounts" / "accounts.json"

# ── Common real-world UA pool ─────────────────────────────────────────────────
UA_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

VIEWPORT_POOL = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 800},
    {"width": 1600, "height": 900},
]

WEBGL_POOL = [
    {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"},
]

PLATFORM_POOL = ["Win32", "Win64"]

# ── Fingerprint generation ────────────────────────────────────────────────────

def generate_fingerprint(seed: int | None = None) -> dict:
    """
    Generate a randomized but internally consistent fingerprint.
    If seed is provided, the output is deterministic (same seed = same fingerprint).
    """
    rng = random.Random(seed)

    ua = rng.choice(UA_POOL)
    viewport = rng.choice(VIEWPORT_POOL)
    webgl = rng.choice(WEBGL_POOL)
    platform = rng.choice(PLATFORM_POOL)
    timezone_id = "Asia/Ho_Chi_Minh"  # Keep VN timezone for consistency
    locale = rng.choice(["vi-VN", "vi-VN", "en-US"])  # Bias toward vi-VN

    # Screen res = viewport + some extras (taskbar etc.)
    screen_w = viewport["width"]
    screen_h = viewport["height"] + rng.choice([40, 48, 56])

    # Canvas & audio noise — tiny and stable per account
    canvas_noise = round(rng.uniform(0.00005, 0.0002), 6)
    audio_noise = round(rng.uniform(0.000001, 0.000005), 7)

    # Determine browser from UA
    if "Firefox" in ua:
        browser = "firefox"
        accept_lang = f"{locale},en;q=0.5"
    elif "Edg/" in ua:
        browser = "edge"
        accept_lang = f"{locale},en;q=0.9,en-US;q=0.8"
    else:
        browser = "chrome"
        accept_lang = f"{locale},en-US;q=0.9,en;q=0.8"

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "seed": seed,
        "browser": browser,
        "user_agent": ua,
        "viewport": viewport,
        "screen": {"width": screen_w, "height": screen_h},
        "device_scale_factor": rng.choice([1, 1, 1, 1.25]),  # mostly 1
        "color_scheme": "light",
        "locale": locale,
        "accept_language": accept_lang,
        "timezone_id": timezone_id,
        "platform": platform,
        "webgl_vendor": webgl["vendor"],
        "webgl_renderer": webgl["renderer"],
        "canvas_noise": canvas_noise,
        "audio_noise": audio_noise,
        "js_overrides": {
            "navigator.platform": platform,
            "navigator.webdriver": "undefined",
            "navigator.languages": [locale, "en-US", "en"],
            "screen.width": screen_w,
            "screen.height": screen_h,
        }
    }


def get_account_path(account_id: str) -> Path:
    return SKILL_ROOT / "accounts" / account_id


def load_accounts() -> dict:
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_account(account_id: str) -> dict | None:
    data = load_accounts()
    for acc in data["accounts"]:
        if acc["id"] == account_id:
            return acc
    return None


# ── JS init script for Playwright ────────────────────────────────────────────

def build_init_script(fp: dict) -> str:
    """
    Returns a JavaScript string to inject as init_script via Playwright.
    Overrides WebGL, Canvas, Audio, and navigator properties.
    All injected strings are sanitised to prevent JS injection via single-quoted literals.
    """
    def _js_str(s: str) -> str:
        """Escape a Python string for safe use inside a JS single-quoted string."""
        return s.replace("\\", "\\\\").replace("'", "\\'")

    webgl_vendor = _js_str(fp["webgl_vendor"])
    webgl_renderer = _js_str(fp["webgl_renderer"])
    canvas_noise = fp["canvas_noise"]
    audio_noise = fp["audio_noise"]
    platform = _js_str(fp["platform"])
    locale = _js_str(fp["locale"])

    return f"""
    (() => {{
        // ======================
        // 1. navigator overrides
        // ======================
        const overrideProp = (obj, prop, value) => {{
            try {{
                Object.defineProperty(obj, prop, {{
                    get: () => value,
                    configurable: true,
                }});
            }} catch(e) {{}}
        }};

        overrideProp(navigator, 'platform', '{platform}');
        overrideProp(navigator, 'webdriver', undefined);
        overrideProp(navigator, 'languages', ['{locale}', 'en-US', 'en']);

        // ======================
        // 2. WebGL fingerprint
        // ======================
        const origGetParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return '{webgl_vendor}';   // UNMASKED_VENDOR_WEBGL
            if (param === 37446) return '{webgl_renderer}'; // UNMASKED_RENDERER_WEBGL
            return origGetParam.call(this, param);
        }};
        if (typeof WebGL2RenderingContext !== 'undefined') {{
            const origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return '{webgl_vendor}';
                if (param === 37446) return '{webgl_renderer}';
                return origGetParam2.call(this, param);
            }};
        }}

        // ======================
        // 3. Canvas noise
        // ======================
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const ctx2d = this.getContext('2d');
            if (ctx2d) {{
                const imageData = ctx2d.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] += Math.floor({canvas_noise} * 255 * (Math.random() - 0.5));
                }}
                ctx2d.putImageData(imageData, 0, 0);
            }}
            return origToDataURL.apply(this, args);
        }};

        // ======================
        // 4. Audio context noise
        // ======================
        try {{
            const origCreateBuffer = AudioContext.prototype.createBuffer;
            AudioContext.prototype.createBuffer = function(...args) {{
                const buffer = origCreateBuffer.apply(this, args);
                for (let c = 0; c < buffer.numberOfChannels; c++) {{
                    const data = buffer.getChannelData(c);
                    for (let i = 0; i < data.length; i++) {{
                        data[i] += {audio_noise} * (Math.random() - 0.5);
                    }}
                }}
                return buffer;
            }};
        }} catch(e) {{}}

    }})();
    """


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_generate(args):
    account = get_account(args.account)
    if not account:
        print(f"ERROR: Account '{args.account}' not found in accounts.json")
        sys.exit(1)

    # Use account_id as deterministic seed for stable fingerprint
    seed = int.from_bytes(args.account.encode(), "big") % (2**31)
    if args.random:
        seed = None

    fp = generate_fingerprint(seed=seed)

    # Save to account folder
    fp_path = SKILL_ROOT / account["fingerprint_path"]
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(json.dumps(fp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✅ Fingerprint generated for account: {args.account}")
    print(f"   Saved to: {fp_path}")
    print(f"   Browser:  {fp['browser']}")
    print(f"   UA:       {fp['user_agent'][:80]}...")
    print(f"   Viewport: {fp['viewport']['width']}x{fp['viewport']['height']}")
    print(f"   Timezone: {fp['timezone_id']}")
    print(f"   WebGL:    {fp['webgl_renderer'][:60]}...")
    print(f"   Canvas noise: {fp['canvas_noise']}")


def cmd_show(args):
    account = get_account(args.account)
    if not account:
        print(f"ERROR: Account '{args.account}' not found")
        sys.exit(1)
    fp_path = SKILL_ROOT / account["fingerprint_path"]
    if not fp_path.exists():
        print(f"No fingerprint found for '{args.account}'. Run: fingerprint_gen.py generate --account {args.account}")
        sys.exit(1)
    fp = json.loads(fp_path.read_text(encoding="utf-8"))
    print(json.dumps(fp, indent=2, ensure_ascii=False))


def cmd_list(args):
    data = load_accounts()
    print(f"{'Account ID':<20} {'Fingerprint':<12} {'Browser':<10} Viewport")
    print("-" * 65)
    for acc in data["accounts"]:
        fp_path = SKILL_ROOT / acc["fingerprint_path"]
        if fp_path.exists():
            fp = json.loads(fp_path.read_text(encoding="utf-8"))
            vp = fp["viewport"]
            print(f"{acc['id']:<20} {'✅ exists':<12} {fp['browser']:<10} {vp['width']}x{vp['height']}")
        else:
            print(f"{acc['id']:<20} {'❌ missing':<12} {'—':<10} —")


def main():
    parser = argparse.ArgumentParser(description="Manage browser fingerprints per account")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generate", help="Generate and save fingerprint for an account")
    p_gen.add_argument("--account", required=True)
    p_gen.add_argument("--random", action="store_true", help="Use random seed instead of deterministic")

    p_show = sub.add_parser("show", help="Print fingerprint JSON for an account")
    p_show.add_argument("--account", required=True)

    sub.add_parser("list", help="List all accounts and their fingerprint status")

    args = parser.parse_args()

    if args.cmd == "generate":
        cmd_generate(args)
    elif args.cmd == "show":
        cmd_show(args)
    elif args.cmd == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
